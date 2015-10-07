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
from collections import namedtuple
import logging as log
import copy

import requests
import yaml
import simplejson as json

from qubell import deprecated
from qubell.api.private.service import system_application_types
from qubell.api.tools import lazyproperty, retry
from qubell.api.private.manifest import Manifest
from qubell.api.private import exceptions
from qubell.api.private.instance import InstanceList, DEAD_STATUS, Instance
from qubell.api.private.application import ApplicationList
from qubell.api.private.environment import EnvironmentList
from qubell.api.private.zone import ZoneList
from qubell.api.private.role import RoleList
from qubell.api.private.user import UserList
from qubell.api.provider.router import InstanceRouter
from qubell.api.private.common import QubellEntityList, Entity
from qubell.api.globals import *

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"


class Organization(Entity, InstanceRouter):

    def __init__(self, id, auth=None):
        self.organizationId = self.id = id

    @staticmethod
    def new(name, router):
        log.info("Creating organization: %s" % name)
        payload = json.dumps({'editable': 'true',
                              'name': name})
        resp = router.post_organization(data=payload)
        org = Organization(resp.json()['id']).init_router(router)
        log.info("Organization created: %s (%s)" % (name, org.id))
        return org

    @lazyproperty
    def environments(self):
        return EnvironmentList(list_json_method=self.list_environments_json, organization=self).init_router(self._router)

    @lazyproperty
    def instances(self):
        return InstanceList(list_json_method=self.list_instances_json, organization=self).init_router(self._router)

    @lazyproperty
    def applications(self):
        return ApplicationList(list_json_method=self.list_applications_json, organization=self).init_router(self._router)

    @lazyproperty
    def services(self):
        return InstanceList(list_json_method=self.list_services_json, organization=self).init_router(self._router)

    @lazyproperty
    def zones(self): return ZoneList(self).init_router(self._router)

    @lazyproperty
    def roles(self):
        return RoleList(list_json_method=self.list_roles_json, organization=self).init_router(self._router)

    @lazyproperty
    def users(self):
        return UserList(list_json_method=self.list_users_json, organization=self).init_router(self._router)

    @lazyproperty
    def categories(self):
        return CategoryList(list_json_method=self.list_category_json, organization=self).init_router(self._router)

    @property
    def defaultEnvironment(self):
        return self.get_default_environment()

    @property
    def zone(self):
        return self.get_default_zone()

    @property
    def name(self):
        return self.json()['name']

    @property
    def current_user(self):
        return self._router.get_organization_info(org_id=self.organizationId).json()

    def json(self):
        return self._router.get_organization(org_id=self.organizationId).json()

    def ready(self):
        """
        Checks if organization properly created.
        Note: New organization must have 'default' environment and two default services
        running there. Cannot use DEFAULT_ENV_NAME, because zone could be added there.
        :rtype: bool
        """

        @retry(tries=3, retry_exception=exceptions.NotFoundError)  # org init, takes some times
        def check_init():
            env = self.environments['default']
            return env.services['Default workflow service'].running(timeout=1) and \
                   env.services['Default credentials service'].running(timeout=1)
        return check_init()

    def restore(self, config, clean=False, timeout=10):
        config = copy.deepcopy(config)

        for app in config.pop('applications'):
            manifest_param = dict([(k, v) for k, v in app.iteritems() if k in ["content", "url", "file"]])
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
            service = self.service(id=serv.pop('id', None),
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
        return Application.new(self, name, manifest, self._router)

    def get_application(self, id=None, name=None):
        """ Get application object by name or id.
        """
        log.info("Picking application: %s (%s)" % (name, id))
        return self.applications[id or name]

    def list_applications_json(self):
        """ Return raw json
        """
        return self._router.get_applications(org_id=self.organizationId).json()

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
        return Instance.new(self._router, application, revision, environment, name,
                            parameters, submodules, destroyInterval)

    def get_instance(self, id=None, name=None):
        """ Get instance object by name or id.
        If application set, search within the application.
        """
        log.info("Picking instance: %s (%s)" % (name, id))
        if id:  # submodule instances are invisible for lists
            return Instance(id=id, organization=self).init_router(self._router)
        return Instance.get(self._router, self, name)

    def list_instances_json(self, application=None, show_only_destroyed=False):
        """ Get list of instances in json format converted to list"""
        # todo: application should not be parameter here. Application should do its own list, just in sake of code reuse
        q_filter = {'sortBy': 'byCreation', 'descending': 'true',
                    'mode': 'short',
                    'from': '0', 'to': '10000'}
        if not show_only_destroyed:
            q_filter['showDestroyed'] = 'false'
        else:
            q_filter['showDestroyed'] = 'true'
            q_filter['showRunning'] = 'false'
            q_filter['showError'] = 'false'
            q_filter['showLaunching'] = 'false'
        if application:
            q_filter["applicationFilterId"] = application.applicationId
        resp_json = self._router.get_instances(org_id=self.organizationId, params=q_filter).json()
        if type(resp_json) == dict:
            instances = [instance for g in resp_json['groups'] for instance in g['records']]
        else:  # TODO: This is compatibility fix for platform < 37.1
            instances = resp_json

        return instances

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

### COMPONENTS
    #full components id, starts with instance id.
    def component_details(self, component):
        return self._router.get_component_details(org_id=self.organizationId, component_id=component).json()

    def list_components_json(self, application=None):

        q_filter = {'sortBy': 'byCreation','descending': 'true',
                    'from': '0', 'to': '10000'}
        if application:
            q_filter["applicationFilterId"] = application.applicationId

        return self._router.get_components(org_id=self.organizationId, params=q_filter).json()

### SERVICE
    def create_service(self, application=None, revision=None, environment=None, name=None, parameters=None, type=None):

        if type and type in system_application_types:
            if application: log.warning('Ignoring application parameter (%s) while creating system service' % application)
            application = self.applications[system_application_types[type]]

        instance = self.create_instance(application, revision, environment, name, parameters)
        instance.environment.add_service(instance)
        return instance

    def list_services_json(self):
        return self._router.get_services(org_id=self.organizationId).json()

    def service(self, id=None, application=None, revision=None, environment=None, name=None, parameters=None,
                              type=None, destroyInterval=None):
        try:
            instance = self.get_instance(id=id, name=name)
            return instance
        except exceptions.NotFoundError:
            return self.create_service(application, revision, environment, name, parameters, type)

    @deprecated("Use service method")
    def get_or_create_service(self, id=None, application=None, revision=None, environment=None, name=None,
                              parameters=None, type=None, destroyInterval=None):
        return self.service(id, application, revision, environment, name, parameters, type, destroyInterval)

    @deprecated("Use get_instance method")
    def get_service(self, id=None, name=None):
        return self.get_instance(id, name)

    def remove_service(self, service):
        service.environment.remove_service(service)
        service.delete()

### ENVIRONMENT
    def create_environment(self, name, default=False, zone=None):
        """ Creates environment and returns Environment object.
        """
        from qubell.api.private.environment import Environment
        return Environment.new(organization=self, name=name, zone_id=zone, default=default, router=self._router)

    def list_environments_json(self):
        return self._router.get_environments(org_id=self.organizationId).json()

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
        return self._router.get_zones(org_id=self.organizationId).json()

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
        return Role.new(self._router, organization=self, name=name, permissions=permissions)

    def list_roles_json(self):
        return self._router.get_roles(org_id=self.organizationId).json()

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
        return self._router.get_users(org_id=self.organizationId).json()

    def get_user(self, id=None, name=None, email=None):
        """ Get user object by email or id.
        """
        log.info("Picking user: %s (%s) (%s)" % (name, email, id))
        from qubell.api.private.user import User
        if email:
            user = User.get(self._router, organization=self, email=email)
        else:
            user = self.users[id or name]
        return user

    def evict_user(self, id):
        user = self.get_user(id)
        return user.evict()

    def invite(self, email, roles=None):
        """
        Send invitation to email with a list of roles
        :param email:
        :param roles: None or "ALL" or list of role_names
        :return:
        """
        if roles is None:
            role_ids = [self.roles['Guest'].roleId]
        elif roles == "ALL":
            role_ids = list([i.id for i in self.roles])
        else:
            if "Guest" not in roles:
                roles.append('Guest')
            role_ids = list([i.id for i in self.roles if i.name in roles])

        self._router.invite_user(data=json.dumps({
            "organizationId": self.organizationId,
            "email": email,
            "roles": role_ids}))

    def init(self, access_key=None, secret_key=None):
        """
        Mimics wizard's environment preparation
        """
        if not access_key and not secret_key:
            self._router.post_init(org_id=self.organizationId, data='{"initCloudAccount": true}')
        else:
            self._router.post_init(org_id=self.organizationId, data='{}')
            ca_data = dict(accessKey=access_key, secretKey=secret_key)
            self._router.post_init_custom_cloud_account(org_id=self.organizationId, data=json.dumps(ca_data))

    def set_applications_from_meta(self, metadata, exclude=None):
        """
        Parses meta and update or create each application
        :param str metadata: path or url to meta.yml
        :param list[str] exclude: List of application names, to exclude from meta.
                                  This might be need when you use meta as list of dependencies
        """
        if not exclude:
            exclude = []
        if metadata.startswith('http'):
            meta = yaml.safe_load(requests.get(url=metadata).content)
        else:
            # noinspection PyArgumentEqualDefault
            meta = yaml.safe_load(open(metadata, 'r').read())

        applications = []
        for app in meta['kit']['applications']:
            if app['name'] not in exclude:
                applications.append({
                    'name': app['name'],
                    'url': app['manifest']})
        self.restore({'applications': applications})

    def upload_applications(self, metadata, category=None):
        """
        Mimics get starter-kit and wizard functionality to create components
        Note: may create component duplicates, not idempotent
        :type metadata: str
        :type category: Category
        :param metadata: url to meta.yml
        :param category: category
        """
        upload_json = self._router.get_upload(params=dict(metadataUrl=metadata)).json()
        manifests = [dict(name=app['name'], manifest=app['url']) for app in upload_json['applications']]
        if not category:
            category = self.categories['Application']
        data = {'categoryId': category.id, 'applications': manifests}
        self._router.post_application_kits(org_id=self.organizationId, data=json.dumps(data))

    def wizard_components(self):
        return self._router.get_welcome_wizard_components(org_id=self.organizationId).json()

    def init_docker_service(self):
        self._router.post_init_docker_service(org_id=self.organizationId)

    def list_category_json(self):
        return self._router.get_categories(org_id=self.organizationId).json()


class OrganizationList(QubellEntityList):
    base_clz = Organization


class Category(Entity):
    # noinspection PyShadowingBuiltins
    def __init__(self, organization, id, raw):
        self.categoryId = self.id = id
        self.organization = organization
        self.__json = raw  # non-interactive entity

    @property
    def name(self):
        return self.json()['name']

    @property
    def readOnly(self):
        return self.json()['readOnly']

    def json(self):
        return self.__json


class CategoryList(QubellEntityList):
    def _id_name_list(self):
        self._list = []
        for ent in self.json():
            IdNameJson = namedtuple('IdName', 'id,name,raw')
            self._list.append(IdNameJson(ent['id'], ent['name'], ent))

    def _get_item(self, id_name):
        return Category(organization=self.organization, id=id_name.id, raw=id_name.raw)
