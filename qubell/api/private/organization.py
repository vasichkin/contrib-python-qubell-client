# Copyright (c) 2013 Qubell Inc., http://qubell.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import warnings
from qubell import deprecated
from qubell.api.private.common import EntityList, IdName
from qubell.api.private.service import system_application_types, system_application_parameters, COBALT_SECURE_STORE_TYPE, WORKFLOW_SERVICE_TYPE, \
    SHARED_INSTANCE_CATALOG_TYPE, STATIC_RESOURCE_POOL_TYPE
from qubell.api.tools import lazyproperty

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

import logging as log
import simplejson as json
import copy

from qubell.api.private.manifest import Manifest
from qubell.api.private import exceptions
from qubell.api.private.instance import InstanceList, DEAD_STATUS, Instance
from qubell.api.private.application import ApplicationList
from qubell.api.private.environment import EnvironmentList
from qubell.api.private.zone import ZoneList
from qubell.api.private.provider import ProviderList
from qubell.api.provider.router import ROUTER as router
from qubell.api.private.common import QubellEntityList, Entity


class Organization(Entity):

    def __init__(self, id, auth=None):
        self.organizationId = self.id = id

    @staticmethod
    def new(name):
        log.info("Creating organization: %s" % name)
        payload = json.dumps({'editable': 'true',
                              'name': name})
        resp = router.post_organization(data=payload)
        return Organization(resp.json()['id'])

    @lazyproperty
    def environments(self):
        return EnvironmentList(list_json_method=self.list_environments_json, organization=self)

    @lazyproperty
    def instances(self):
        return InstanceList(list_json_method=self.list_instances_json, organization=self)

    @lazyproperty
    def applications(self):
        return ApplicationList(list_json_method=self.list_applications_json, organization=self)

    @lazyproperty
    def services(self):
        return InstanceList(list_json_method=self.list_services_json, organization=self)

    @lazyproperty
    def zones(self): return ZoneList(self)

    @lazyproperty
    def providers(self): return ProviderList(self)

    @property
    def defaultEnvironment(self): return self.get_default_environment()

    @property
    def zone(self): return self.get_default_zone()

    @property
    def name(self): return self.json()['name']

    def json(self):
        return router.get_organization(org_id=self.organizationId).json()

    def restore(self, config):
        config = copy.deepcopy(config)
        for prov in config.get('cloudAccounts', []):
            self.get_or_create_provider(id=prov.pop('id', None),
                                        name=prov.pop('name'),
                                        parameters=prov)

        for serv in config.pop('services',[]):
            self.get_or_create_service(id=serv.pop('id', None),
                                       name=serv.pop('name'),
                                       type=serv.pop('type', None),
                                       parameters=serv.pop('parameters', None))

        for env in config.pop('environments',[]):
            restored_env = self.get_or_create_environment(id=env.pop('id', None),
                                                          name=env.pop('name', 'default'),
                                                          zone=env.pop('zone', None),
                                                          default=env.pop('default', False))
            #restored_env.clean()
            restored_env.restore(env)

        for app in config.pop('applications'):
            manifest = Manifest(**{k: v for k, v in app.iteritems() if k in ["content", "url", "file"]})
            #mnf = app.pop('manifest', None)
            restored_app = self.application(id=app.pop('id', None),
                                            manifest=manifest,
                                            name=app.pop('name'))

        for instance in config.pop('instances', []):
            launched = self.get_or_launch_instance(application=self.get_application(name=instance.pop('application')),
                                                   id=instance.pop('id', None),
                                                   name=instance.pop('name', None),
                                                   **instance)
            assert launched.ready()

### APPLICATION
    def create_application(self, name=None, manifest=None):
        """ Creates application and returns Application object.
        """
        if not manifest:
            raise exceptions.NotEnoughParams('Manifest not set')
        if not name:
            name = 'auto-generated-name'
        from qubell.api.private.application import Application
        return Application.new(self, name, manifest)

    def get_application(self, id=None, name=None):
        """ Get application object by name or id.
        """
        log.info("Picking application: %s" % (id or name))
        return self.applications[id or name]

    def list_applications_json(self):
        """ Return raw json
        """
        return router.get_applications(org_id=self.organizationId).json()

    def delete_application(self, id):
        app = self.get_application(id)
        self.applications.remove(app)
        return app.delete()

    def get_or_create_application(self, id=None, manifest=None, name=None):
        """ Get application by id or name.
        If not found: create with given or generated parameters
        """
        if id:
            return self.get_application(id=id)
        elif name:
            try:
                app = self.get_application(name=name)
            except exceptions.NotFoundError:
                app = self.create_application(name=name, manifest=manifest)
            return app
        raise exceptions.NotEnoughParams('Not enough parameters')

    def application(self, id=None, manifest=None, name=None):
        """ Smart method. Creates, picks or modifies application.
        If application found by name or id and manifest not changed: return app.
        If app found by id, but other parameters differs: change them.
        If no application found, create.
        """

        modify = False
        found = False

        # Try to find application by name or id
        if name and id:
            found = self.get_application(id=id)
            if not found.name == name:
                modify = True
        elif id:
            found = self.get_application(id=id)
            name = found.name
        elif name:
            try:
                found = self.get_application(name=name)
                id = found.applicationId
            except exceptions.NotFoundError:
                pass

        # If found - compare parameters
        if found:
            if manifest and not manifest == found.manifest:
                modify = True

        # We need to update application
        if found and modify:
            found.update(name=name, manifest=manifest)
        if not found:
            created = self.create_application(name=name, manifest=manifest)

        return found or created


# INSTANCE

    def create_instance(self, application, revision=None, environment=None, name=None, parameters=None,
                        destroyInterval=None):
        """ Launches instance in application and returns Instance object.
        """
        from qubell.api.private.instance import Instance
        return Instance.new(application, revision, environment, name, parameters, destroyInterval)

    def get_instance(self, id=None, name=None):
        """ Get instance object by name or id.
        If application set, search within the application.
        """
        log.info("Picking instance: %s" % (id or name))
        if id:  # submodule instances are invisible for lists
            return Instance(id=id, organization=self)
        return self.instances[id or name]

    def list_instances_json(self, application=None):
        """ Get list of instances in json format converted to list"""
        if application:  # todo: application should not be parameter here. Application should do its own list
            warnings.warn("organization.list_instances_json(app) is deprecated, use app.list_instances_json", DeprecationWarning, stacklevel=2)
            instances = application.list_instances_json()
        else:  # Return all instances in organization
            instances = router.get_instances(org_id=self.organizationId).json()
        return [ins for ins in instances if ins['status'] not in DEAD_STATUS]

    def get_or_create_instance(self, id=None, application=None, revision=None, environment=None, name=None, parameters=None,
                               destroyInterval=None):
        """ Get instance by id or name.
        If not found: create with given parameters
        """
        try:
            instance = self.get_instance(id=id, name=name)
            if name and name != instance.name:
                instance.rename(name)
                instance.ready()
            return instance
        except exceptions.NotFoundError:
            return self.create_instance(application, revision, environment, name, parameters, destroyInterval)
    get_or_launch_instance = get_or_create_instance

    def instance(self, id=None, application=None, name=None, revision=None, environment=None, parameters=None, destroyInterval=None):
        """ Smart method. It does everything, to return Instance with given parameters within the application.
        If instance found running and given parameters are actual: return it.
        If instance found, but parameters differs - reconfigure instance with new parameters.
        If instance not found: launch instance with given parameters.
        Return: Instance object.
        """
        instance = self.get_or_create_instance(id, application, revision, environment, name, parameters, destroyInterval)

        reconfigure = False
        # if found:
        #     if revision and revision is not found.revision:
        #         reconfigure = True
        #     if parameters and parameters is not found.parameters:
        #         reconfigure = True

        # We need to reconfigure instance
        if reconfigure:
            instance.reconfigure(revision=revision, parameters=parameters)

        return instance


### SERVICE
    def create_service(self, application=None, revision=None, environment=None, name=None, parameters=None, type=None):

        if type and system_application_types.has_key(type):
            if application: log.warning('Ignoring application parameter (%s) while creating system service' % application)
            application = self.applications[system_application_types[type]]

        instance = self.create_instance(application, revision, environment, name, parameters)
        instance.environment.add_service(instance)
        return instance

    get_service = get_instance

    def list_services_json(self):
        return router.get_services(org_id=self.organizationId).json()

    def get_or_create_service(self, id=None, application=None, revision=None, environment=None, name=None, parameters=None,
                              type=None, destroyInterval=None):
        """ Get by name or create service with given parameters"""
        try:
            return self.get_instance(id=id, name=name)
        except exceptions.NotFoundError:
            return self.create_service(application, revision, environment, name, parameters, type)

    service = get_or_create_service

    def remove_service(self, service):
        service.environment.remove_service(service)
        service.delete()

### ENVIRONMENT
    def create_environment(self, name, default=False, zone=None):
        """ Creates environment and returns Environment object.
        """
        from qubell.api.private.environment import Environment
        return Environment.new(organization=self,name=name, zone=zone, default=default)

    def list_environments_json(self):
        return router.get_environments(org_id=self.organizationId).json()

    def get_environment(self, id=None, name=None):
        """ Get environment object by name or id.
        """
        log.info("Picking environment: %s" % (id or name))
        return self.environments[id or name]

    def delete_environment(self, id):
        env = self.get_environment(id)
        return env.delete()

    def get_or_create_environment(self, id=None, name=None, zone=None, default=False):
        """ Get environment by id or name.
        If not found: create with given or generated parameters
        """
        if id:
            return self.get_environment(id=id)
        elif name:
            try:
                env = self.get_environment(name=name)
            except exceptions.NotFoundError:
                env = self.create_environment(name=name, zone=zone, default=default)
            return env
        else:
            name = 'auto-generated-env'
            return self.create_environment(name=name, zone=zone, default=default)

    def environment(self, id=None, name=None, zone=None, default=False):
        """ Smart method. Creates, picks or modifies environment.
        If environment found by name or id parameters not changed: return env.
        If env found by id, but other parameters differs: change them.
        If no environment found, create with given parameters.
        """

        modify = False
        found = False

        # Try to find environment by name or id
        if name and id:
            found = self.get_environment(id=id)
            if not found.name == name:
                modify = True
        elif id:
            found = self.get_environment(id=id)
            name = found.name
        elif name:
            try:
                found = self.get_environment(name=name)
                id = found.applicationId
            except exceptions.NotFoundError:
                pass

        # If found - compare parameters
        if found:
            if default and not found.isDefault:
                # We cannot set it to non default
                found.set_default()

            # TODO: add abilities to change zone and name.
            """
            if name and not name == found.name:
                found.rename(name)
            if zone and not zone == found.zone:
                modify = True
            """
        if not found:
            created = self.create_environment(name=name, zone=zone, default=default)
        return found or created


    def get_default_environment(self):
        def_envs = [x for x in self.environments if x.isDefault == True]
        if len(def_envs)>1:
            log.warning('Found more than one default environment. Picking last.')
            return def_envs[-1]
        elif len(def_envs)==1:
            return def_envs[0]
        raise exceptions.NotFoundError('Unable to get default environment')

    def set_default_environment(self, environment):
        return environment.set_as_default()


### PROVIDER
    def create_provider(self, name, parameters):
        log.info("Creating provider: %s" % name)
        parameters['name'] = name
        resp = router.post_provider(org_id=self.organizationId, data=json.dumps(parameters))
        return self.get_provider(resp.json()['id'])

    def list_providers_json(self):
        return router.get_providers(org_id=self.organizationId).json()

    def get_provider(self, id=None, name=None):
        log.info("Picking provider: %s" % (id or name))
        return self.providers[id or name]

    def delete_provider(self, id):
        prov = self.get_provider(id)
        return prov.delete()

    def get_or_create_provider(self, id=None, name=None, parameters=None):

        """ Smart object. Will create provider or pick one, if exists"""

        try:
            return self.get_provider(id=id, name=name)
        except exceptions.NotFoundError:
            return self.create_provider(name, parameters)

    def provider(self, id=None, name=None, parameters=None):
        """ Get , create or modify provider
        """
        return self.get_or_create_provider(id=id, name=name, parameters=parameters)

### ZONES

    def list_zones_json(self):
        return router.get_zones(org_id=self.organizationId).json()

    def get_zone(self, id=None, name=None):
        """ Get zone object by name or id.
        """
        log.info("Picking zone: %s" % (id or name))
        return self.zones[id or name]

    def get_default_zone(self):
        backends = self.get_default_environment().json()['backends']
        zones = [bk for bk in backends if bk['isDefault'] == True]
        if len(zones):
            zoneId = zones[0]['id']
            return self.get_zone(id=zoneId)
        raise exceptions.NotFoundError('Unable to get default zone')


class OrganizationList(QubellEntityList):
    base_clz = Organization

    """
    def __init__(self, list_json_method):
        self.json = list_json_method
        EntityList.__init__(self)
    def _id_name_list(self):
        self._list = [IdName(ent['id'], ent['name']) for ent in self.json()]
    def _get_item(self, id_name):
        return Organization(id=id_name.id)
    """
