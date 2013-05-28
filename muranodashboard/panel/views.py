# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from muranoclient.common.exceptions import CommunicationError
import re

from django.views import generic
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.formtools.wizard.views import SessionWizardView

from horizon import exceptions
from horizon import tabs
from horizon import tables
from horizon import workflows
from horizon.forms.views import ModalFormMixin

from muranodashboard.panel import api

from tables import EnvironmentsTable, ServicesTable
from workflows import CreateEnvironment
from tabs import ServicesTabs
from forms import WizardFormADConfiguration
from forms import WizardFormIISConfiguration
from forms import WizardFormAspNetAppConfiguration
from forms import WizardFormIISFarmConfiguration
from forms import WizardFormAspNetFarmConfiguration

from horizon import messages

from django.http import HttpResponseRedirect

LOG = logging.getLogger(__name__)


class Wizard(ModalFormMixin, SessionWizardView, generic.FormView):
    template_name = 'services_tabs.html'

    def done(self, form_list, **kwargs):
        link = self.request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search('murano/(\S+)', link).group(0)[7:-9]

        url = "/project/murano/%s/services" % environment_id

        service_type = form_list[0].data.get('0-service', '')
        parameters = {'service_type': service_type}
        data = form_list[1].data
        parameters['units'] = []
        if service_type == 'Active Directory':
            parameters['configuration'] = 'standalone'
            parameters['name'] = str(data.get('1-dc_name', 'noname'))
            parameters['domain'] = parameters['name']  # Fix Me in orchestrator
            parameters['adminPassword'] = str(data.get('1-adm_password', ''))
            recovery_password = str(data.get('1-recovery_password', ''))
            parameters['units'].append({'isMaster': True,
                                        'recoveryPassword': recovery_password,
                                        'location': 'west-dc'})
            dc_count = int(data.get('1-dc_count', 1))
            for dc in range(dc_count - 1):
                parameters['units'].append({
                    'isMaster': False,
                    'recoveryPassword': recovery_password
                })

        elif service_type in ['IIS', 'ASP.NET Application', 'IIS Farm', 'ASP.NET Farm']:
            password = data.get('1-adm_password', '')
            parameters['name'] = str(data.get('1-iis_name', 'noname'))
            parameters['credentials'] = {'username': 'Administrator',
                                         'password': password}
            parameters['domain'] = str(data.get('1-iis_domain', ''))
            password = form_list[1].data.get('1-adm_password', '')
            domain = form_list[1].data.get('1-iis_domain', '')
            dc_user = form_list[1].data.get('1-domain_user_name', '')
            dc_pass = form_list[1].data.get('1-domain_user_password', '')
            parameters['name'] = str(form_list[1].data.get('1-iis_name',
                                                           'noname'))
            parameters['domain'] = parameters['name']
            parameters['adminPassword'] = password
            parameters['domain'] = str(domain)

            if service_type == 'ASP.NET Application' or service_type == 'ASP.NET Farm':
                parameters['repository'] = form_list[1]\
                                           .data.get('1-repository', '')
            instance_count = 1
            if service_type == 'IIS Farm' or service_type == 'ASP.NET Farm':
                instance_count = int(data.get('1-instance_count', 1))
                parameters['loadBalancerPort'] = int(data.get('1-lb_port', 80))

            for unit in range(instance_count - 1):
                parameters['units'].append({})


        service = api.service_create(self.request, environment_id, parameters)

        message = "The %s service successfully created." % service_type
        messages.success(self.request, message)
        return HttpResponseRedirect(url)

    def get_form(self, step=None, data=None, files=None):
        form = super(Wizard, self).get_form(step, data, files)
        if data:
            self.service_type = data.get('0-service', '')
            if self.service_type == 'Active Directory':
                self.form_list['1'] = WizardFormADConfiguration
            elif self.service_type == 'IIS':
                self.form_list['1'] = WizardFormIISConfiguration
            elif self.service_type == 'ASP.NET Application':
                self.form_list['1'] = WizardFormAspNetAppConfiguration
            elif self.service_type == 'IIS Farm':
                self.form_list['1'] = WizardFormIISFarmConfiguration
            elif self.service_type == 'ASP.NET Farm':
                self.form_list['1'] = WizardFormAspNetFarmConfiguration

        return form

    def get_form_kwargs(self, step=None):
        return {'request': self.request} if step == u'1' else {}

    def get_form_step_data(self, form):
        LOG.debug(form.data)
        return form.data

    def get_context_data(self, form, **kwargs):
        context = super(Wizard, self).get_context_data(form=form, **kwargs)
        if self.steps.index > 0:
            context.update({'service_type': self.service_type})
        return context


class IndexView(tables.DataTableView):
    table_class = EnvironmentsTable
    template_name = 'index.html'

    def get_data(self):
        try:
            environments = api.environments_list(self.request)
        except CommunicationError:
            environments = []
            messages.error(self.request, 'Could not connect to Murano API '
                                         'Service, check connection details.')
        return environments


class Services(tables.DataTableView):
    table_class = ServicesTable
    template_name = 'services.html'

    def get_context_data(self, **kwargs):
        context = super(Services, self).get_context_data(**kwargs)
        context['environment_name'] = self.environment_name
        return context

    def get_data(self):
        try:
            self.environment_id = self.kwargs['environment_id']
            environment = api.environment_get(self.request, self.environment_id)
            self.environment_name = environment.name
            services = api.services_list(self.request, self.environment_id)
        except:
            services = []
            exceptions.handle(self.request,
                              _('Unable to retrieve list of services for '
                                'environment "%s".') % self.environment_id)
        self._services = services
        return self._services


class DetailServiceView(tabs.TabView):
    tab_group_class = ServicesTabs
    template_name = 'service_details.html'

    def get_context_data(self, **kwargs):
        context = super(DetailServiceView, self).get_context_data(**kwargs)
        context["service"] = self.get_data()
        context["service_name"] = self.get_data().name
        return context

    def get_data(self):
        if not hasattr(self, "_service"):
            try:
                service_id = self.kwargs['service_id']
                service = api.service_get(self.request, service_id)
            except:
                redirect = reverse('horizon:project:murano:index')
                exceptions.handle(self.request,
                                  _('Unable to retrieve details for '
                                    'service "%s".') % service_id,
                                  redirect=redirect)
            self._service = service
        return self._service

    def get_tabs(self, request, *args, **kwargs):
        service = self.get_data()
        return self.tab_group_class(request, service=service, **kwargs)


class CreateEnvironmentView(workflows.WorkflowView):
    workflow_class = CreateEnvironment
    template_name = 'create_dc.html'

    def get_initial(self):
        initial = super(CreateEnvironmentView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial
