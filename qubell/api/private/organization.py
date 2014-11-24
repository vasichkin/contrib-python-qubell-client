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
from qubell.api.globals import DEFAULT_ENV_NAME, ZONE_NAME
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
from qubell.api.private.role import RoleList
from qubell.api.private.user import UserList
from qubell.api.provider.router import ROUTER as router
from qubell.api.private.common import QubellEntityList, Entity
from qubell.api.globals import *


class Organization(Entity):

    def __init__(self, id, auth=None):
        self.organizationId = self.id = id

    @staticmethod
    def new(name):
        log.info("Creating organization: %s" % name)
        payload = json.dumps({'editable': 'true',
                              'name': name})
        resp = router.post_organization(data=payload)
        org = Organization(resp.json()['id'])
        log.info("Organization created: %s (%s)" % (name, org.id))
        return org

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
    def roles(self):
        return RoleList(list_json_method=self.list_roles_json, organization=self)

    @lazyproperty
    def users(self):
        return UserList(list_json_method=self.list_users_json, organization=self)

    @property
    def defaultEnvironment(self): return self.get_default_environment()

    @property
    def zone(self): return self.get_default_zone()

    @property
    def name(self): return self.json()['name']

    @property
    def current_user(self): return router.get_organization_info(org_id=self.organizationId).json()

    def json(self):
        return router.get_organization(org_id=self.organizationId).json()

    def ready(self):
        env = self.environments[DEFAULT_ENV_NAME()]
        if env.services[DEFAULT_WORKFLOW_SERVICE()].running() and env.services[DEFAULT_CREDENTIAL_SERVICE()].running():
            return True
        return False

    def restore(self, config, clean=False, timeout=10):
        config = copy.deepcopy(config)

        for app in config.pop('applications'):
            manifest_param = {k: v for k, v in app.iteritems() if k in ["content", "url", "file"]}
            if manifest_param:
                manifest = Manifest(**manifest_param)
            else:
                manifest = None  # if application exists, manifest must be None
            self.application(id=app.pop('id', None),
                                            manifest=manifest,
                                            name=app.pop('name'))

        for serv in config.pop('services', []):
            app=serv.pop('application', None)
            if app:
                app = self.get_application(name=app)

            type = serv.pop('type', None)
            service = self.get_or_create_service(id=serv.pop('id', None),
                                       name=serv.pop('name'),
                                       type=type,
                                       application=app,
                                       parameters=serv.pop('parameters', None))
            assert service.running(timeout)

        for env in config.pop('environments', []):
            env_zone = env.pop('zone', None)
            if env_zone:
                zone_id = self.zones[env_zone].id
            elif ZONE_NAME:
                zone_id = self.zones[ZONE_NAME].id
            else:
                zone_id = None
            restored_env = self.get_or_create_environment(id=env.pop('id', None),
                                                          name=env.pop('name', DEFAULT_ENV_NAME()),
                                                          zone=zone_id,
                                                          default=env.pop('default', False))
            restored_env.restore(env, clean, timeout)

        #todo: make launch and ready async
        for instance in config.pop('instances', []):
            launched = self.get_or_launch_instance(application=self.get_application(name=instance.pop('application')),
                                                   id=instance.pop('id', None),
                                                   name=instance.pop('name', None),
                                                   environment=self.get_or_create_environment(name=instance.pop('environment', 'default')),
                                                   **instance)
            assert launched.running(timeout)

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
        log.info("Picking application: %s (%s)" % (name, id))
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

    def create_instance(self, application, revision=None, environment=None, name=None, parameters=None, submodules=None,
                        destroyInterval=None):
        """ Launches instance in application and returns Instance object.
        """
        from qubell.api.private.instance import Instance
        return Instance.new(application, revision, environment, name, parameters, submodules, destroyInterval)

    def get_instance(self, id=None, name=None):
        """ Get instance object by name or id.
        If application set, search within the application.
        """
        log.info("Picking instance: %s (%s)" % (name, id))
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

    def get_or_create_instance(self, id=None, application=None, revision=None, environment=None, name=None, parameters=None, submodules=None,
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
            return self.create_instance(application, revision, environment, name, parameters, submodules, destroyInterval)
    get_or_launch_instance = get_or_create_instance

    def instance(self, id=None, application=None, name=None, revision=None, environment=None, parameters=None, submodules=None, destroyInterval=None):
        """ Smart method. It does everything, to return Instance with given parameters within the application.
        If instance found running and given parameters are actual: return it.
        If instance found, but parameters differs - reconfigure instance with new parameters.
        If instance not found: launch instance with given parameters.
        Return: Instance object.
        """
        instance = self.get_or_create_instance(id, application, revision, environment, name, parameters, submodules, destroyInterval)

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

        if type and type in system_application_types:
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
            serv = self.get_instance(id=id, name=name)
            if environment:
                environment.add_service(serv)
            return serv
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
        return Environment.new(organization=self, name=name, zone_id=zone, default=default)

    def list_environments_json(self):
        return router.get_environments(org_id=self.organizationId).json()

    def get_environment(self, id=None, name=None):
        """ Get environment object by name or id.
        """
        log.info("Picking environment: %s (%s)" % (name, id))
        return self.environments[id or name]

    def delete_environment(self, id):
        env = self.get_environment(id)
        return env.delete()

    def _assert_env_and_zone(self, env, zone_id):
        if zone_id:
            assert env.zoneId == zone_id, "Found environment has wrong zone id"

    def get_or_create_environment(self, id=None, name=None, zone=None, default=False):
        """ Get environment by id or name.
        If not found: create with given or generated parameters
        """
        if id:
            return self.get_environment(id=id)
        elif name:
            try:
                env = self.get_environment(name=name)
                self._assert_env_and_zone(env, zone)
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

        found = False

        # Try to find environment by name or id
        if name and id:
            found = self.get_environment(id=id)
        elif id:
            found = self.get_environment(id=id)
            name = found.name
        elif name:
            try:
                found = self.get_environment(name=name)
            except exceptions.NotFoundError:
                pass

        # If found - compare parameters
        if found:
            self._assert_env_and_zone(found, zone)
            if default and not found.isDefault:
                found.set_as_default()
            # TODO: add abilities to change name.
        if not found:
            created = self.create_environment(name=name, zone=zone, default=default)
        return found or created


    def get_default_environment(self):
        return self.environments.default

    def set_default_environment(self, environment):
        return environment.set_as_default()


### ZONES

    def list_zones_json(self):
        return router.get_zones(org_id=self.organizationId).json()

    def get_zone(self, id=None, name=None):
        """ Get zone object by name or id.
        """
        log.info("Picking zone: %s (%s)" % (name, id))
        return self.zones[id or name]

    def get_default_zone(self):
        backends = self.get_default_environment().json()['backends']
        zones = [bk for bk in backends if bk['isDefault'] == True]
        if len(zones):
            zoneId = zones[-1]['id']
            return self.get_zone(id=zoneId)
        raise exceptions.NotFoundError('Unable to get default zone')

### PERMISSIONS

    def create_role(self, name=None, permissions=""):
        """ Creates role """
        name = name or "autocreated-role"
        from qubell.api.private.role import Role
        return Role.new(organization=self, name=name, permissions=permissions)

    def list_roles_json(self):
        return router.get_roles(org_id=self.organizationId).json()

    def get_role(self, id=None, name=None):
        """ Get role object by name or id.
        """
        log.info("Picking role: %s (%s)" % (name, id))
        return self.roles[id or name]

    def delete_role(self, id):
        role = self.get_role(id)
        return role.delete()

    def get_or_create_role(self, id=None, name=None, permissions=None):
        try:
            role = self.get_role(id, name)
        except:
            role = self.create_role(name, permissions)
        return role


### USERS

    def list_users_json(self):
        return router.get_users(org_id=self.organizationId).json()

    def get_user(self, id=None, name=None, email=None):
        """ Get user object by email or id.
        """
        log.info("Picking user: %s (%s) (%s)" % (name, email, id))
        from qubell.api.private.user import User
        if email:
            user = User.get_user(organization=self, email=email)
        else:
            user = self.users[id or name]
        return user

    def evict_user(self, id):
        user = self.get_user(id)
        return user.evict()


class OrganizationList(QubellEntityList):
    base_clz = Organization
