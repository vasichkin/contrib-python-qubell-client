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
from qubell.api.private.service import system_application_types
from qubell.api.tools import lazyproperty

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

import logging as log
import simplejson as json

from qubell.api.private.manifest import Manifest
from qubell.api.private import exceptions
from qubell.api.private.instance import InstanceList, DEAD_STATUS
from qubell.api.private.application import ApplicationList
from qubell.api.private.environment import EnvironmentList
from qubell.api.private.zone import ZoneList
from qubell.api.provider.router import ROUTER as router


class Organization(object):

    def __init__(self, id, auth=None):
        self.providers = []

        self.organizationId = id

        my = self.json()
        self.name = my['name']

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

    @property
    def defaultEnvironment(self): return self.get_default_environment()

    @property
    def zone(self): return self.get_default_zone()

    def json(self):
        resp = router.get_organizations()
        org = [x for x in resp.json() if x['id'] == self.organizationId]
        if len(org)>0:
            return org[0]
        return resp.json()

    def restore(self, config):
        for instance in config.pop('instances', []):
            launched = self.get_or_launch_instance(id=instance.pop('id', None), name=instance.pop('name'), **instance)
            assert launched.ready()
        for serv in config.pop('services',[]):
            self.get_or_create_service(id=serv.pop('id', None), name=serv.pop('name'), type=serv.pop('type', None))
        for prov in config.get('providers', []):
            self.get_or_create_provider(id=prov.pop('id', None), name=prov.pop('name'), parameters=prov)
        for env in config.pop('environments',[]):
            restored_env = self.get_or_create_environment(id=env.pop('id', None), name=env.pop('name', 'default'),zone=env.pop('zone', None), default=env.pop('default', False))
            restored_env.clean()
            restored_env.restore(env)
        for app in config.pop('applications'):
            mnf = app.pop('manifest', None)
            restored_app = self.application(id=app.pop('id', None), manifest=Manifest(**mnf), name=app.pop('name'))
            restored_app.restore(app)

### APPLICATION
    def create_application(self, name=None, manifest=None):
        """ Creates application and returns Application object.
        """
        if not manifest:
            raise exceptions.NotEnoughParams('Manifest not set')
        if not name:
            name = 'auto-generated-name'
        from qubell.api.private.application import Application
        app = Application(organization=self).create(name=name, manifest=manifest)
        self.applications.add(app)
        return app

    def get_application(self, id=None, name=None):
        """ Get application object by name or id.
        """
        if id:
            apps = [x for x in self.applications if x.id == id]
        elif name:
            apps = [x for x in self.applications if x.name == name]
        else:
            raise exceptions.NotEnoughParams('No name nor id given. Unable to get application')

        if len(apps) == 1:
            return apps[0]
        elif len(apps) > 1:
            log.warning('Found several applications with name %s. Picking last' % name)
            return apps[-1]
        raise exceptions.NotFoundError('Unable to get application by id: %s' % id)

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

    def create_instance(self, application, revision=None, environment=None, name=None, parameters={}, destroyInterval=None):
        """ Launches instance in application and returns Instance object.
        """
        if not application:
            raise exceptions.NotEnoughParams('Application not set')
        instance = application.create_instance(name=name,
                                    environment=environment,
                                    revision=revision,
                                    parameters=parameters,
                                    destroyInterval=destroyInterval)
        self.instances.add(instance)
        return instance

    def get_instance(self, application=None, id=None, name=None):
        """ Get instance object by name or id.
        If application set, search within the application.
        """

        if application:
            instances = [x for x in self.instances if x.applicationId == application.applicationId]
        else:
            instances = self.instances

        if id:
            instance = [x for x in instances if x.id == id]
        elif name:
            instance = [x for x in instances if x.name == name]
        else:
            raise exceptions.NotEnoughParams('No name nor id given. Unable to get instance')

        if len(instance) == 1:
            return instance[0]
        elif len(instance) > 1:
            log.warning('Found several instances with name %s. Picking last' % name)
            return instance[-1]
        raise exceptions.NotFoundError('Unable to get instance by id: %s' % id)

    #todo: application should not be parameter here. Application should do its own list
    def list_instances_json(self, application=None):
        """ Get list of instances in json format converted to list"""
        if application:
            warnings.warn("organization.list_instances_json(app) is deprecated, use app.list_instances_json", DeprecationWarning, stacklevel=2)
            instances = application.list_instances_json()
        else:  # Return all instances in organization
            instances = router.get_instances(org_id=self.organizationId).json()
        return [ins for ins in instances if ins['status'] not in DEAD_STATUS]

    def delete_instance(self, id):
        instance = self.get_instance(id)
        self.instances.remove(instance)
        return instance.delete()

    def get_or_launch_instance(self, id=None, application=None, name=None, **kwargs):
        """ Get instance by id or name.
        If not found: create with given application (name and params are optional)
        """
        if id:
            return self.get_instance(id=id)
        elif name:
            try:
                instance = self.get_instance(name=name)
            except exceptions.NotFoundError:
                instance = self.create_instance(application=application, name=name, **kwargs)
            return instance
        elif application:
            return self.create_instance(application=application, **kwargs)
        raise exceptions.NotEnoughParams('Not enough parameters')

    def instance(self, application=None, id=None, name=None, revision=None, environment=None,  parameters={}):
        """ Smart method. It does everything, to return Instance with given parameters within the application.
        If instance found running and given parameters are actual: return it.
        If instance found, but parameters differs - reconfigure instance with new parameters.
        If instance not found: launch instance with given parameters.
        Return: Instance object.
        """

        modify = False
        found = False

        # Try to find instance by name or id
        if name and id:
            found = self.get_instance(application=application, id=id)
            if not found.name == name:
                modify = True
        elif id:
            found = self.get_instance(application=application, id=id)
            name = found.name

        elif name:
            try:
                found = self.get_instance(application=application, name=name)
                id = found.instanceId
            except exceptions.NotFoundError:
                pass

        # If found - compare parameters
        # TODO:
        """
        if found:
            if revision and not revision == found.revision:
                modify = True
            if environment and not environment == found.environment:
                modify = True
            if parameters and not parameters == found.parameters:
                modify = True
        """

        # We need to reconfigure instance
        if found and modify:
            found.reconfigure(revision=revision, environment=environment, name=name, parameters=parameters)

        if not found:
            created = self.create_instance(application=application, revision=revision, environment=environment, name=name, parameters=parameters)

        return found or created


### SERVICE
    def create_service(self, name, type, parameters, zone=None, environment=None):
        assert not zone, "Api has changed, zone is deprecated and will be removed soon, define environment"
        assert environment, "Api has changed, please define environment"

        #try to map type to name or treat type as name
        application_name = system_application_types.get(type, type)
        if application_name in system_application_types.values():
            destroyInterval = -1  # never for system applications
        else:
            destroyInterval = 3600000  # magic number = 1 hour

        instance = self.create_instance(
            name=name,
            application=self.applications[application_name],
            environment=environment,
            parameters=parameters,
            destroyInterval=destroyInterval)

        environment.add_service(instance)
        return instance

    def create_keystore_service(self, name='generated-keystore', parameters={}, zone=None):
        parameters["destroyInterval"] = "-1"
        return self.create_service(name=name, type='builtin:cobalt_secure_store', parameters=parameters, zone=zone)

    def create_workflow_service(self, name='generated-workflow', policies={}, zone=None):
        parameters = {'configuration.policies': json.dumps(policies), "destroyInterval": "-1"}
        return self.create_service(name=name, type='builtin:workflow_service', parameters=parameters, zone=zone)

    def create_shared_service(self, name='generated-shared', instances={}, zone=None):
        parameters = {'configuration.shared-instances': json.dumps(instances), "destroyInterval": "-1"}
        return self.create_service(name=name, type='builtin:shared_instances_catalog', parameters=parameters, zone=zone)

    def get_service(self, id):
        log.info("Picking service: %s" % id)
        instance = self.get_instance(id=id)
        self.services.append(instance)
        return instance

    def list_services_json(self):
        return router.get_services(org_id=self.organizationId).json()

    @deprecated("use list_serivces_json instead")
    def list_services(self): return self.list_services_json()

    def delete_service(self, id):
        srv = self.get_service(id)
        self.services.remove(srv)
        return srv.delete()

    def get_or_create_service(self, id=None, name=None, type=None, parameters={}, zone=None, environment=None):
        """ Get by name or create service with given parameters"""
        assert id or name
        assert not zone, "Api has changed, zone is deprecated and will be removed soon, define environment"
        assert environment, "Api has changed, please define environment"
        if id: return self.get_service(id)
        if name:
            if name in self.services:
                service = self.services[name]
                assert service.status == "Running", "Found service-instance-{0} is not in Running state".format(service.instanceId)
                #if zones doesn't match, provide users with exhaustive information
                assert service.environment.zoneId is environment.zoneId, \
                    "Found service-instance-{0} zone, doesn't match environment-{1} zone. Zone {2} is not {3}".format(service.instanceId, environment.environmentId, service.environment.zoneId, environment.zoneId)
                return service
            else:
                return self.create_service(name, type, environment=environment, parameters=parameters)

    service = get_or_create_service

### ENVIRONMENT
    def create_environment(self, name, default=False, zone=None):
        """ Creates environment and returns Environment object.
        """
        from qubell.api.private.environment import Environment
        env = Environment(organization=self).create(name=name, zone=zone, default=default)
        self.environments.add(env)
        return env

    def list_environments_json(self):
        return router.get_environments(org_id=self.organizationId).json()

    def get_environment(self, id=None, name=None):
        """ Get environment object by name or id.
        """
        if id:
            envs = [x for x in self.environments if x.id == id]
        elif name:
            envs = [x for x in self.environments if x.name == name]
        else:
            raise exceptions.NotEnoughParams('No name nor id given. Unable to get application')
        if len(envs) == 1:
            return envs[0]
        elif len(envs) > 1:
            log.warning('Found several environments with name %s. Picking last' % name)
            return envs[-1]
        raise exceptions.NotFoundError('Unable to get environment by id: %s' % id)

    def delete_environment(self, id):
        env = self.get_environment(id)
        self.environments.remove(env)
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

    @deprecated("use list_providers_json instead")
    def list_providers(self): return self.list_providers_json()

    def get_provider(self, id):
        from qubell.api.private.provider import Provider
        prov = Provider(organization=self, id=id)
        self.providers.append(prov)
        return prov

    def delete_provider(self, id):
        prov = self.get_provider(id)
        self.providers.remove(prov)
        return prov.delete()

    def get_or_create_provider(self,id=None, name=None, parameters=None):

        """ Smart object. Will create provider or pick one, if exists"""
        if name:
            provs = [prov for prov in self.list_providers_json() if prov['name'] == name]
            # provider found by name
            if len(provs):
                return self.get_provider(provs[0]['id']) # pick first
            elif parameters:
                return self.create_provider(name=name, parameters=parameters)
        else:
            name = 'generated-provider'
            if id:
                return self.get_provider(id)
            elif parameters:
                return self.create_provider(name=name, parameters=parameters)
        raise exceptions.NotFoundError('Provider not found or not enough parameters to create provider: %s' % name)

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
        if id:
            zones = [x for x in self.zones if x.id == id]
        elif name:
            zones = [x for x in self.zones if x.name == name]
        else:
            raise exceptions.NotEnoughParams('No name nor id given. Unable to get application')
        if len(zones) == 1:
            return zones[0]
        elif len(zones) > 1:
            log.warning('Found several zones with name %s. Picking last' % name)
            return zones[-1]
        raise exceptions.NotFoundError('Unable to get zone by id: %s' % id)

    def get_default_zone(self):
    # Zones(backends) are factor we can't controll. So, get them.
        backends = self.json()['backends']
        zones = [bk for bk in backends if bk['isDefault']==True]
        if len(zones):
            zoneId = zones[0]['id']
            return self.get_zone(id=zoneId)
        raise exceptions.NotFoundError('Unable to get default zone')
