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
from django.conf import settings
try:
    from collections import OrderedDict
except ImportError:  # python2.6
    from ordereddict import OrderedDict
import yaml
from yaml.scanner import ScannerError
from django.utils.translation import ugettext_lazy as _
import copy

log = logging.getLogger(__name__)
_all_services = OrderedDict()


class Service(object):
    def __init__(self, modified_on, **kwargs):
        import muranodashboard.panel.services.forms as services
        for key, value in kwargs.iteritems():
            if key == 'forms':
                self.forms = []
                for form_data in value:
                    form_name, form_data = self.extract_form_data(form_data)
                    self.forms.append(
                        type(form_name, (services.ServiceConfigurationForm,),
                             {'service': self,
                              'fields_template': form_data['fields'],
                              'validators': form_data.get('validators', [])}))
            else:
                setattr(self, key, value)
        self.modified_on = modified_on
        self.cleaned_data = {}

    @staticmethod
    def extract_form_data(form_data):
        form_name = form_data.keys()[0]
        return form_name, form_data[form_name]

    def update_cleaned_data(self, form, data):
        if data:
            # match = re.match('^.*-(\d)+$', form.prefix)
            # index = int(match.group(1)) if match else None
            # if index is not None:
            #     self.cleaned_data[index] = data
            self.cleaned_data[form.__class__.__name__] = data
        return self.cleaned_data


def import_all_services():
    from muranodashboard.panel.services.helpers import decamelize

    directory = getattr(settings, 'MURANO_SERVICES_DESC_PATH', None)
    if directory is None:
        directory = os.path.join(os.path.dirname(__file__), '../../services/')
    file_list = [f for f in os.listdir(directory) if f.endswith('.yaml')]

    log.debug("Removing non-existing service definitions from cache")
    # TODO: this has O(n^2) complexity, should fix it if there are many defs
    for filename in _all_services.keys():
        try:
            file_list.index(filename)
        except ValueError:
            del _all_services[filename]
            log.info("Removed service '{0}' from cache".format(filename))

    log.debug("Updating service definitions cache from '{0}'".format(
        directory))
    for filename in file_list:
        service_file = os.path.join(directory, filename)
        modified_on = os.path.getmtime(service_file)

        if filename in _all_services:
            if _all_services[filename].modified_on >= modified_on:
                continue

        try:
            with open(service_file) as stream:
                yaml_desc = yaml.load(stream)
        except (OSError, ScannerError) as e:
            log.warn("Failed to import service definition from {0},"
                     " reason: {1!s}".format(service_file, e))
            continue

        service = dict((decamelize(k), v) for (k, v) in yaml_desc.iteritems())
        _all_services[filename] = Service(modified_on, **service)
        log.info("Added service '{0}' from '{1}', modified on {2}".format(
            _all_services[filename].name, service_file,
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified_on))))


def iterate_over_services():
    import_all_services()

    for service in sorted(_all_services.values(), key=lambda v: v.name):
        yield service.type, service, service.forms


def make_forms_getter(initial_forms=[]):
    def _get_forms():
        _forms = copy.copy(initial_forms)
        for srv_type, service, forms in iterate_over_services():
            for step, form in enumerate(forms):
                _forms.append(('{0}-{1}'.format(srv_type, step), form))
        return _forms
    return _get_forms


def service_type_from_id(service_id):
    match = re.match('(.*)-[0-9]+', service_id)
    if match:
        return match.group(1)
    else:  # if no number suffix found, it was service_type itself passed in
        return service_id


def with_service(service_id, getter, default):
    import_all_services()
    service_type = service_type_from_id(service_id)
    for srv_type, service, forms in iterate_over_services():
        if srv_type == service_type:
            return getter(service)
    return default


def get_service_name(service_id):
    return with_service(service_id, lambda service: service.name, '')


def get_service_field_descriptions(service_id, index):
    def get_descriptions(service):
        Form = service.forms[index]
        descriptions = []
        for field in Form.fields_template:
            if 'description' in field:
                title = field.get('descriptionTitle', field.get('label', ''))
                descriptions.append((title, field['description']))
        return descriptions
    return with_service(service_id, get_descriptions, [])


def get_service_type(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step('service_choice') \
        or {'service': 'none'}
    return cleaned_data.get('service')


def get_service_choices():
    return [(srv_type, service.name) for srv_type, service, forms in
            iterate_over_services()]


get_forms = make_forms_getter()


def get_service_checkers():
    import_all_services()

    def make_comparator(srv_id):
        def compare(wizard):
            return service_type_from_id(srv_id) == get_service_type(wizard)
        return compare

    return [(srv_id, make_comparator(srv_id)) for srv_id, form
            in get_forms()]


def get_service_descriptions():
    descriptions = []
    for srv_type, service, forms in iterate_over_services():
        description = getattr(service, 'description', _("<b>Default service \
        description</b>. If you want to see here something meaningful, please \
        provide `description' field in service markup."))
        descriptions.append((srv_type, description))
    return descriptions
