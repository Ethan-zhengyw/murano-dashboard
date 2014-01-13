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

import logging
import re
import copy
import json
from functools import update_wrapper

from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.contrib.formtools.wizard.views import SessionWizardView
from django.http import HttpResponseRedirect
from horizon import exceptions
from horizon import tabs
from horizon import tables
from horizon import workflows
from horizon import messages
from horizon.forms.views import ModalFormMixin
from tables import EnvironmentsTable
from tables import ServicesTable
from tables import DeploymentsTable
from tables import EnvConfigTable
from workflows import CreateEnvironment, UpdateEnvironment
from tabs import ServicesTabs, DeploymentTabs
from . import api
from muranoclient.common.exceptions import HTTPUnauthorized, \
    CommunicationError, HTTPInternalServerError, HTTPForbidden, HTTPNotFound
from django.utils.decorators import classonlymethod
from muranodashboard.dynamic_ui.services import get_service_descriptions
from muranodashboard.dynamic_ui.services import get_service_name
from muranodashboard.dynamic_ui.services import get_service_field_descriptions


LOG = logging.getLogger(__name__)


class LazyWizard(SessionWizardView):
    """The class which defers evaluation of form_list and condition_dict
    until view method is called. So, each time we load a page with a dynamic
    UI form, it will have markup/logic from the newest YAML-file definition.
    """
    @classonlymethod
    def as_view(cls, initforms, *initargs, **initkwargs):
        """
        Main entry point for a request-response process.
        """
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(u"You tried to pass in the %s method name as a"
                                u" keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError(u"%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        def view(request, *args, **kwargs):
            forms = initforms
            if hasattr(initforms, '__call__'):
                forms = initforms(request)
            condition_dict = initkwargs.get('condition_dict', False)
            _kwargs = copy.copy(initkwargs)
            if condition_dict and hasattr(condition_dict, '__call__'):
                _kwargs.update(
                    {'condition_dict': dict(condition_dict(request))})
            _kwargs = cls.get_initkwargs(forms, *initargs, **_kwargs)
            self = cls(**_kwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view


class Wizard(ModalFormMixin, LazyWizard):
    template_name = 'services/wizard_create.html'

    def done(self, form_list, **kwargs):
        link = self.request.__dict__['META']['HTTP_REFERER']

        environment_id = re.search('murano/(\w+)', link).group(0)[7:]
        url = reverse('horizon:murano:environments:services',
                      args=(environment_id,))

        step0_data = form_list[0].cleaned_data
        service_type = step0_data.get('service', '')
        attributes = {'type': service_type}

        for form in form_list[1:]:
            form.extract_attributes(attributes)

        try:
            api.service_create(self.request, environment_id, attributes)
        except HTTPForbidden:
            msg = _('Sorry, you can\'t create service right now.'
                    'The environment is deploying.')
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        except Exception:
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request,
                              _('Sorry, you can\'t create service right now.'),
                              redirect=redirect)
        else:
            message = "The %s service successfully created." % \
                      get_service_name(self.request, service_type)
            messages.success(self.request, message)
            return HttpResponseRedirect(url)

    def get_form_initial(self, step):
        init_dict = {}
        if step != 'service_choice':
            init_dict.update({
                'request': self.request,
                'environment_id': self.kwargs.get('environment_id')
            })
        return self.initial_dict.get(step, init_dict)

    def get_context_data(self, form, **kwargs):
        context = super(Wizard, self).get_context_data(form=form, **kwargs)
        if self.steps.index > 0:
            data = self.get_cleaned_data_for_step('service_choice')
            service_type = data['service']
            context['field_descriptions'] = get_service_field_descriptions(
                self.request, service_type, self.steps.index - 1)
            service_name = get_service_name(self.request, service_type)
            context.update({'type': service_type,
                            'service_name': service_name,
                            'environment_id': self.kwargs.get('environment_id')
                            })
        else:
            extended_description = form.fields['description'].initial or ''
            if extended_description:
                data = json.loads(extended_description)
                if data:
                    unavailable_services, reasons = zip(*data)
                    services_msg = ', '.join(unavailable_services)
                    reasons_msg = '\n'.join(set(reasons))
                    extended_description = 'Services {0} are not available. ' \
                                           'Reasons: {1}'.format(services_msg,
                                                                 reasons_msg)
                else:
                    extended_description = ''

            context.update({
                'service_descriptions': get_service_descriptions(self.request),
                'extended_description': extended_description,
                'environment_id': self.kwargs.get('environment_id')
            })
        return context


class IndexView(tables.DataTableView):
    table_class = EnvironmentsTable
    template_name = 'environments/index.html'

    def get_data(self):
        environments = []
        try:
            environments = api.environments_list(self.request)
        except CommunicationError:
            exceptions.handle(self.request,
                              'Could not connect to Murano API \
                              Service, check connection details')
        except HTTPInternalServerError:
            exceptions.handle(self.request,
                              'Murano API Service is not responding. \
                              Try again later')
        except HTTPUnauthorized:
            exceptions.handle(self.request, ignore=True, escalate=True)

        return environments


class Services(tables.DataTableView):
    table_class = ServicesTable
    template_name = 'services/index.html'

    def get_context_data(self, **kwargs):
        context = super(Services, self).get_context_data(**kwargs)

        try:
            environment_name = api.get_environment_name(
                self.request,
                self.environment_id)
            context['environment_name'] = environment_name

        except:
            msg = _("Sorry, this environment does't exist anymore")
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        return context

    def get_data(self):
        services = []
        self.environment_id = self.kwargs['environment_id']
        ns_url = "horizon:murano:environments:index"
        try:
            services = api.services_list(self.request, self.environment_id)
        except HTTPForbidden:
            msg = _('Unable to retrieve list of services. This environment '
                    'is deploying or already deployed by other user.')
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))

        except HTTPInternalServerError:
            msg = _("Environment with id %s doesn't exist anymore"
                    % self.environment_id)
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))
        except HTTPUnauthorized:
            exceptions.handle(self.request)
        except HTTPNotFound:
            msg = _("Environment with id %s doesn't exist anymore"
                    % self.environment_id)
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))
        return services


class DetailServiceView(tabs.TabView):
    tab_group_class = ServicesTabs
    template_name = 'services/details.html'

    def get_context_data(self, **kwargs):
        context = super(DetailServiceView, self).get_context_data(**kwargs)
        context["service"] = self.get_data()
        context["service_name"] = self.service.name
        context["environment_name"] = \
            api.get_environment_name(self.request, self.environment_id)
        return context

    def get_data(self):
        service_id = self.kwargs['service_id']
        self.environment_id = self.kwargs['environment_id']
        try:
            self.service = api.service_get(self.request,
                                           self.environment_id,
                                           service_id)
        except HTTPUnauthorized:
            exceptions.handle(self.request)

        except HTTPForbidden:
            redirect = reverse('horizon:murano:environments:index')
            exceptions.handle(self.request,
                              _('Unable to retrieve details for '
                                'service'),
                              redirect=redirect)
        else:
            self._service = self.service
            return self._service

    def get_tabs(self, request, *args, **kwargs):
        service = self.get_data()
        return self.tab_group_class(request, service=service, **kwargs)


class CreateEnvironmentView(workflows.WorkflowView):
    workflow_class = CreateEnvironment
    template_name = 'environments/create.html'

    def get_initial(self):
        initial = super(CreateEnvironmentView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


class EditEnvironmentView(workflows.WorkflowView):
    workflow_class = UpdateEnvironment
    template_name = 'environments/update.html'
    success_url = reverse_lazy("horizon:murano:environments:index")

    def get_context_data(self, **kwargs):
        context = super(EditEnvironmentView, self).get_context_data(**kwargs)
        context["environment_id"] = self.kwargs['environment_id']
        return context

    def get_object(self, *args, **kwargs):
        if not hasattr(self, "_object"):
            environment_id = self.kwargs['environment_id']
            try:
                self._object = \
                    api.environment_get(self.request, environment_id)
            except:
                redirect = reverse("horizon:murano:environments:index")
                msg = _('Unable to retrieve environment details.')
                exceptions.handle(self.request, msg, redirect=redirect)
        return self._object

    def get_initial(self):
        initial = super(EditEnvironmentView, self).get_initial()
        initial.update({'environment_id': self.kwargs['environment_id'],
                        'name': getattr(self.get_object(), 'name', '')})
        return initial


class DeploymentsView(tables.DataTableView):
    table_class = DeploymentsTable
    template_name = 'deployments/index.html'

    def get_context_data(self, **kwargs):
        context = super(DeploymentsView, self).get_context_data(**kwargs)

        try:
            environment_name = api.get_environment_name(

                self.request,
                self.environment_id)
            context['environment_name'] = environment_name
        except:
            msg = _("Sorry, this environment doesn't exist anymore")
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        return context

    def get_data(self):
        deployments = []
        self.environment_id = self.kwargs['environment_id']
        ns_url = "horizon:murano:environments:index"
        try:
            deployments = api.deployments_list(self.request,
                                               self.environment_id)

        except HTTPForbidden:
            msg = _('Unable to retrieve list of deployments')
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))

        except HTTPInternalServerError:
            msg = _("Environment with id %s doesn't exist anymore"
                    % self.environment_id)
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))
        return deployments


class DeploymentDetailsView(tabs.TabbedTableView):
    tab_group_class = DeploymentTabs
    table_class = EnvConfigTable
    template_name = 'deployments/reports.html'

    def get_context_data(self, **kwargs):
        context = super(DeploymentDetailsView, self).get_context_data(**kwargs)
        context["environment_id"] = self.environment_id
        context["environment_name"] = \
            api.get_environment_name(self.request, self.environment_id)
        context["deployment_start_time"] = \
            api.get_deployment_start(self.request,
                                     self.environment_id,
                                     self.deployment_id)
        return context

    def get_deployment(self):
        deployment = None
        try:
            deployment = api.get_deployment_descr(self.request,
                                                  self.environment_id,
                                                  self.deployment_id)
        except (HTTPInternalServerError, HTTPNotFound):
            msg = _("Deployment with id %s doesn't exist anymore"
                    % self.deployment_id)
            redirect = reverse("horizon:murano:environments:deployments")
            exceptions.handle(self.request, msg, redirect=redirect)
        return deployment

    def get_logs(self):
        logs = []
        try:
            logs = api.deployment_reports(self.request,
                                          self.environment_id,
                                          self.deployment_id)
        except (HTTPInternalServerError, HTTPNotFound):
            msg = _('Deployment with id %s doesn\'t exist anymore'
                    % self.deployment_id)
            redirect = reverse("horizon:murano:environments:deployments")
            exceptions.handle(self.request, msg, redirect=redirect)
        return logs

    def get_tabs(self, request, *args, **kwargs):
        self.deployment_id = self.kwargs['deployment_id']
        self.environment_id = self.kwargs['environment_id']
        deployment = self.get_deployment()
        logs = self.get_logs()

        return self.tab_group_class(request, deployment=deployment, logs=logs,
                                    **kwargs)
