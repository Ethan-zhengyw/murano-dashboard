#    Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import os
import re
import time
import logging
from muranodashboard.dynamic_ui import metadata
from .helpers import decamelize, get_yaql_expr, create_yaql_context


try:
    from collections import OrderedDict
except ImportError:  # python2.6
    from ordereddict import OrderedDict
import yaql
import yaml
from yaml.scanner import ScannerError
from django.utils.translation import ugettext_lazy as _
import copy
from muranodashboard.environments.consts import CACHE_REFRESH_SECONDS_INTERVAL

log = logging.getLogger(__name__)
_all_services = OrderedDict()
_last_check_time = 0
_current_cache_hash = None


class Service(object):
    def __init__(self, **kwargs):
        import muranodashboard.dynamic_ui.forms as services
        self.context = create_yaql_context()
        self.cleaned_data = {}
        for key, value in kwargs.iteritems():
            if key == 'forms':
                self.forms = []
                for form_data in value:
                    form_name, form_data = self.extract_form_data(form_data)

                    class Form(services.ServiceConfigurationForm):
                        __metaclass__ = services.DynamicFormMetaclass
                        service = self
                        name = form_name
                        field_specs = form_data['fields']
                        validators = form_data.get('validators', [])

                    self.forms.append(Form)

            else:
                setattr(self, key, value)

    @staticmethod
    def extract_form_data(form_data):
        form_name = form_data.keys()[0]
        return form_name, form_data[form_name]

    def get_data(self, form_name, expr, data=None):
        """First try to get value from cleaned data, if none
        found, use raw data."""
        if data:
            self.update_cleaned_data(data, form_name=form_name)
        expr = get_yaql_expr(expr)
        data = self.cleaned_data
        value = data and yaql.parse(expr).evaluate(data, self.context)
        return data != {}, value

    def update_cleaned_data(self, data, form=None, form_name=None):
        form_name = form_name or form.__class__.__name__
        if data:
            self.cleaned_data[form_name] = data
        return self.cleaned_data


def import_service(full_service_name, service_file):
    try:
        with open(service_file) as stream:
            yaml_desc = yaml.load(stream)
    except (OSError, ScannerError) as e:
        log.warn("Failed to import service definition from {0},"
                 " reason: {1!s}".format(service_file, e))
    else:
        service = dict((decamelize(k), v) for (k, v) in yaml_desc.iteritems())
        _all_services[full_service_name] = Service(**service)
        log.info("Added service '{0}' from '{1}'".format(
            _all_services[full_service_name].name, service_file))


def are_caches_in_sync():
    are_in_sync = (_current_cache_hash == metadata.get_existing_hash())
    if not are_in_sync:
        log.debug('In-memory and on-disk caches are not in sync, '
                  'invalidating in-memory cache')
    return are_in_sync


def import_all_services(request):
    """Tries to import all metadata from repository, this includes calculating
    hash-sum of local metadata package, making HTTP-request and unpacking
    received package into cache directory. Calling this function several
    times for each form in dynamicUI is inevitable, so to avoid significant
    delays all metadata-related stuff is actually performed no more often than
    each CACHE_REFRESH_SECONDS_INTERVAL.

    Expected contents of metadata package is:
      - <full_service_name1>/<form_definitionA>.yaml
      - <full_service_name2>/<form_definitionB>.yaml
      ...
    If there is no YAMLs with form definitions inside <full_service_nameN>
    dir, then <full_service_nameN> won't be shown in Create Service first step.
    """
    global _last_check_time
    global _all_services
    global _current_cache_hash
    if time.time() - _last_check_time > CACHE_REFRESH_SECONDS_INTERVAL:
        _last_check_time = time.time()
        directory, modified = metadata.get_ui_metadata(request)
        # check directory here in case metadata service is not available
        # and None is returned as directory value.
        # TODO: it is better to use redirect for that purpose (if possible)
        if modified or (directory and not are_caches_in_sync()):
            _all_services = {}
            for full_service_name in os.listdir(directory):
                final_dir = os.path.join(directory, full_service_name)
                if os.path.isdir(final_dir) and len(os.listdir(final_dir)):
                    filename = os.listdir(final_dir)[0]
                    if filename.endswith('.yaml'):
                        import_service(full_service_name,
                                       os.path.join(final_dir, filename))
            _current_cache_hash = metadata.get_existing_hash()


def iterate_over_services(request):
    import_all_services(request)
    for service in sorted(_all_services.values(), key=lambda v: v.name):
        yield service.type, service


def make_forms_getter(initial_forms=lambda request: copy.copy([])):
    def _get_forms(request):
        _forms = initial_forms(request)
        for srv_type, service in iterate_over_services(request):
            for step, form in enumerate(service.forms):
                _forms.append(('{0}-{1}'.format(srv_type, step), form))
        return _forms
    return _get_forms


def service_type_from_id(service_id):
    match = re.match('(.*)-[0-9]+', service_id)
    if match:
        return match.group(1)
    else:  # if no number suffix found, it was service_type itself passed in
        return service_id


def with_service(request, service_id, getter, default):
    service_type = service_type_from_id(service_id)
    for srv_type, service in iterate_over_services(request):
        if srv_type == service_type:
            return getter(service)
    return default


def get_service_name(request, service_id):
    return with_service(request, service_id, lambda service: service.name, '')


def get_service_field_descriptions(request, service_id, index):
    def get_descriptions(service):
        form_cls = service.forms[index]
        descriptions = []
        for field in form_cls.base_fields.itervalues():
            title = field.description_title
            description = field.description
            if description:
                descriptions.append((title, description))
        return descriptions
    return with_service(request, service_id, get_descriptions, [])


def get_service_type(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step('service_choice') \
        or {'service': 'none'}
    return cleaned_data.get('service')


def get_service_choices(request, filter_func=None):
    filter_func = filter_func or (lambda srv: True, None)
    filtered, not_filtered = [], []
    for srv_type, service in iterate_over_services(request):
        has_filtered, message = filter_func(service, request)
        if has_filtered:
            filtered.append((srv_type, service.name))
        else:
            not_filtered.append((service.name, message))
    return filtered, not_filtered

get_forms = make_forms_getter()


def get_service_checkers(request):
    def make_comparator(srv_id):
        def compare(wizard):
            return service_type_from_id(srv_id) == get_service_type(wizard)
        return compare

    return [(srv_id, make_comparator(srv_id)) for srv_id, form
            in get_forms(request)]


def get_service_descriptions(request):
    descriptions = []
    for srv_type, service in iterate_over_services(request):
        description = getattr(service, 'description', _("<b>Default service \
        description</b>. If you want to see here something meaningful, please \
        provide `description' field in service markup."))
        descriptions.append((srv_type, description))
    return descriptions