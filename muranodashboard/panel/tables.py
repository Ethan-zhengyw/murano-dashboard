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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django import shortcuts

from horizon import exceptions
from horizon import tables
from horizon import messages

from muranodashboard.panel import api

LOG = logging.getLogger(__name__)

STATUS_ID_READY = 'ready'
STATUS_ID_PENDING = 'pending'
STATUS_ID_DEPLOYING = 'deploying'
STATUS_ID_NEW = 'new'

STATUS_CHOICES = (
    (None, True),
    ('Ready to configure', True),
    ('Ready', True),
    ('Configuring', False),

)

STATUS_DISPLAY_CHOICES = (
    (STATUS_ID_READY, 'Ready'),
    (STATUS_ID_DEPLOYING, 'Deploy in progress'),
    (STATUS_ID_PENDING, 'Configuring'),
    (STATUS_ID_NEW, 'Ready to configure'),
    ('', 'Ready to configure'),
)


class CreateService(tables.LinkAction):
    name = 'CreateService'
    verbose_name = _('Create Service')
    url = 'horizon:project:murano:create'
    classes = ('btn-launch', 'ajax-modal')

    def allowed(self, request, environment):
        environment_id = self.table.kwargs['environment_id']
        status = api.get_environment_status(request, environment_id)
        if status not in [STATUS_ID_DEPLOYING]:
            return True
        return False


class CreateEnvironment(tables.LinkAction):
    name = 'CreateEnvironment'
    verbose_name = _('Create Environment')
    url = 'horizon:project:murano:create_environment'
    classes = ('btn-launch', 'ajax-modal')

    def allowed(self, request, datum):
        return True

    def action(self, request, environment):
        api.environment_create(request, environment)


class DeleteEnvironment(tables.DeleteAction):
    data_type_singular = _('Environment')
    data_type_plural = _('Environments')

    def allowed(self, request, environment):
        return True

    def action(self, request, environment_id):
        api.environment_delete(request, environment_id)


class EditEnvironment(tables.LinkAction):
    name = 'edit'
    verbose_name = _('Edit Environment')
    url = 'horizon:project:murano:update_environment'
    classes = ('ajax-modal', 'btn-edit')

    def allowed(self, request, environment):
        status = getattr(environment, 'status', None)
        if status not in [STATUS_ID_DEPLOYING]:
            return True
        else:
            return False


class DeleteService(tables.DeleteAction):
    data_type_singular = _('Service')
    data_type_plural = _('Services')

    def allowed(self, request, service=None):
        #TODO: Change this when services deletion on deployed env fixed
        environment_id = self.table.kwargs.get('environment_id')
        status = api.get_environment_status(request, environment_id)
        if status not in [STATUS_ID_DEPLOYING, STATUS_ID_READY]:
            return True
        return False

    def action(self, request, service_id):
        try:
            env_id = self.table.kwargs.get('environment_id')
            for service in self.table.data:
                if service.id == service_id:
                    api.service_delete(request, service_id, env_id,
                                       service.service_type)
        except:
            msg = _('Sorry, you can\'t delete service right now')
            redirect = reverse("horizon:project:murano:index")
            exceptions.handle(request, msg, redirect=redirect)


class DeployEnvironment(tables.BatchAction):
    name = 'deploy'
    action_present = _('Deploy')
    action_past = _('Deployed')
    data_type_singular = _('Environment')
    data_type_plural = _('Environment')
    classes = 'btn-launch'

    def allowed(self, request, environment):
        status = getattr(environment, 'status', None)
        if status not in [STATUS_ID_DEPLOYING] and environment.has_services:
            return True
        return False

    def action(self, request, environment_id):
        try:
            api.environment_deploy(request, environment_id)
        except:
            msg = _('Unable to deploy. Try again later')
            redirect = reverse('horizon:project:murano:index')
            exceptions.handle(request, msg, redirect=redirect)


class DeployThisEnvironment(tables.Action):
    name = 'deploy_env'
    verbose_name = _('Deploy This Environment')
    requires_input = False
    classes = ('btn-launch', 'ajax-modal')

    def allowed(self, request, service):
        environment_id = self.table.kwargs['environment_id']
        status = api.get_environment_status(request, environment_id)
        services = self.table.data
        if status not in [STATUS_ID_DEPLOYING, STATUS_ID_READY] and services:
            return True
        return False

    def single(self, data_table, request, service_id):
        environment_id = data_table.kwargs['environment_id']
        try:
            api.environment_deploy(request, environment_id)
            messages.success(request, _('Deploy started'))
        except:
            msg = _('Unable to deploy. Try again later')

            exceptions.handle(request, msg,
                              redirect=reverse('horizon:project:murano:index'))
        return shortcuts.redirect(
            reverse('horizon:project:murano:services', environment_id))


class ShowEnvironmentServices(tables.LinkAction):
    name = 'show'
    verbose_name = _('Services')
    url = 'horizon:project:murano:services'

    def allowed(self, request, environment):
        status = getattr(environment, 'status', None)
        if status not in [STATUS_ID_DEPLOYING]:
            return True
        else:
            return False


class UpdateEnvironmentRow(tables.Row):
    ajax = True

    def get_data(self, request, environment_id):
        return api.environment_get(request, environment_id)


class UpdateServiceRow(tables.Row):
    ajax = True

    def get_data(self, request, service_id):
        environment_id = self.table.kwargs['environment_id']
        return api.service_get(request, environment_id, service_id)


class EnvironmentsTable(tables.DataTable):
    name = tables.Column('name',
                         link='horizon:project:murano:services',
                         verbose_name=_('Name'))

    status = tables.Column('status', verbose_name=_('Status'),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)

    class Meta:
        name = 'murano'
        verbose_name = _('Environments')
        row_class = UpdateEnvironmentRow
        status_columns = ['status']
        table_actions = (CreateEnvironment, DeleteEnvironment)
        row_actions = (ShowEnvironmentServices, DeployEnvironment,
                       EditEnvironment, DeleteEnvironment)


def get_service_details_link(service):
    return reverse('horizon:project:murano:service_details',
                   args=(service.environment_id, service.id))


class ServicesTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Name'),
                         link=get_service_details_link)

    _type = tables.Column('service_type', verbose_name=_('Type'))

    status = tables.Column('status', verbose_name=_('Status'),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)

    operation = tables.Column('operation', verbose_name=_('Last operation'))

    class Meta:
        name = 'services'
        verbose_name = _('Services')
        row_class = UpdateServiceRow
        status_columns = ['status']
        table_actions = (CreateService, DeleteService, DeployThisEnvironment)
        row_actions = (DeleteService,)
