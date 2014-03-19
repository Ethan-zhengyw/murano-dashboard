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

import yaql
import yaml
from yaml.scanner import ScannerError
from django.utils.translation import ugettext_lazy as _
import copy
from muranodashboard.environments.consts import CACHE_REFRESH_SECONDS_INTERVAL

log = logging.getLogger(__name__)


class Service(object):
    """Class for keeping service persistent data, the most important are two:
    ``self.forms`` list of service's steps (as Django form classes) and
    ``self.cleaned_data`` dictionary of data from service validated steps.

    Attribute ``self.cleaned_data`` is needed for, e.g. ServiceA.Step2, be
    able to reference data at ServiceA.Step1 while actual form instance
    representing Step1 is already gone.

    Because the need to store this data per-user, sessions must be employed
    (actually, they are not the _only_ way of doing this, but the most simple
    one), and because every Django session backend uses pickle serialization,
    __getstate__/__setstate__ methods for custom pickle serialization must be
    implemented.
    """
    NON_SERIALIZABLE_ATTRS = ('forms', 'context')

    def __init__(self, forms=None, **kwargs):
        self.context = create_yaql_context()
        self.cleaned_data = {}
        self.forms = []
        self._forms = []
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        if forms:
            for data in forms:
                name, field_specs, validators = self.extract_form_data(data)
                self._add_form(name, field_specs, validators)

                # for pickling/unpickling
                self._forms.append((name, field_specs, validators))

    def __getstate__(self):
        log.debug("Pickling service '{service.type}'".format(
            service=self))
        dct = dict((k, v) for (k, v) in self.__dict__.iteritems()
                   if not k in self.NON_SERIALIZABLE_ATTRS)
        return dct

    def __setstate__(self, d):
        log.debug("Unpickling service '{type}'".format(**d))
        for k, v in d.iteritems():
            setattr(self, k, v)
        # dealing with the attributes which cannot be serialized (see
        # http://tinyurl.com/kxx3tam on pickle restrictions )
        # yaql context is not serializable because it contains lambda functions
        self.context = create_yaql_context()
        # form classes are not serializable 'cause they are defined dynamically
        self.forms = []
        for name, field_specs, validators in d.get('_forms', []):
            self._add_form(name, field_specs, validators)

    def _add_form(self, _name, _specs, _validators):
        import muranodashboard.dynamic_ui.forms as forms

        class Form(forms.ServiceConfigurationForm):
            __metaclass__ = forms.DynamicFormMetaclass

            service = self
            name = _name
            field_specs = _specs
            validators = _validators

        self.forms.append(Form)

    @staticmethod
    def extract_form_data(form_data):
        form_name = form_data.keys()[0]
        form_data = form_data[form_name]
        return form_name, form_data['fields'], form_data.get('validators', [])

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


def import_service(services, full_service_name, service_file):
    try:
        with open(service_file) as stream:
            yaml_desc = yaml.load(stream)
    except (OSError, ScannerError) as e:
        log.warn("Failed to import service definition from {0},"
                 " reason: {1!s}".format(service_file, e))
    else:
        service = dict((decamelize(k), v) for (k, v) in yaml_desc.iteritems())
        services[full_service_name] = Service(**service)
        log.info("Added service '{0}' from '{1}'".format(
            services[full_service_name].name, service_file))


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
    last_check_time = request.session.get('last_check_time', 0)
    if time.time() - last_check_time > CACHE_REFRESH_SECONDS_INTERVAL:
        request.session['last_check_time'] = time.time()
        directory, modified = metadata.get_ui_metadata(request)
        session_is_empty = not request.session.get('services', {})
        # check directory here in case metadata service is not available
        # and None is returned as directory value.
        # TODO: it is better to use redirect for that purpose (if possible)
        if directory is not None and (modified or session_is_empty):
            request.session['services'] = {}
            for full_service_name in os.listdir(directory):
                final_dir = os.path.join(directory, full_service_name)
                if os.path.isdir(final_dir) and len(os.listdir(final_dir)):
                    filename = os.listdir(final_dir)[0]
                    if filename.endswith('.yaml'):
                        import_service(request.session['services'],
                                       full_service_name,
                                       os.path.join(final_dir, filename))


def iterate_over_services(request):
    import_all_services(request)
    services = request.session.get('services', {})
    for service in sorted(services.values(), key=lambda v: v.name):
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
