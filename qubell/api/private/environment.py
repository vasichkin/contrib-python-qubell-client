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

import time
from qubell.api.globals import ZONE_NAME, DEFAULT_ENV_NAME
from qubell.api.tools import lazyproperty

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

import logging as log
import simplejson as json
import copy

from qubell.api.private import exceptions
from qubell.api.private.common import QubellEntityList, Entity
from qubell.api.provider.router import ROUTER as router

class Environment(Entity):

    def __init__(self, organization, id):
        self.organization = organization
        self.organizationId = self.organization.organizationId
        self.environmentId = self.id = id

        #todo: make as properties
        self.policies = []
        self.markers = []
        self.properties = []

    @lazyproperty
    def zoneId(self):
        return self.json()['backend']

    @lazyproperty
    def services(self):
        from qubell.api.private.instance import InstanceList
        return InstanceList(list_json_method=self.list_services_json, organization=self)

    @property
    def name(self):
        return self.json()['name']

    @property
    def isDefault(self):
        return self.json()['isDefault']

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    @staticmethod
    def new(organization, name, zone_id=None, default=False):
        log.info("Creating environment: %s" % name)
        if not zone_id:
            zone_id = organization.zone.zoneId
        data = {'isDefault': default,
                'name': name,
                'backend': zone_id,
                'organizationId': organization.organizationId}
        log.debug(data)
        resp = router.post_organization_environment(org_id=organization.organizationId, data=json.dumps(data)).json()
        env = Environment(organization, id=resp['id'])
        log.info("Environment created: %s (%s)" % (name,env.environmentId))
        return env

    def restore(self, config, clean=False, timeout=10):
        config = copy.deepcopy(config)
        if clean:
            self.clean()
        for marker in config.pop('markers', []):
            self.add_marker(marker)
        for policy in config.pop('policies', []):
            self.add_policy(policy)
        for property in config.pop('properties', []):
            self.add_property(**property)
        for service in config.pop('services', []):
            type=service.pop('type', None)
            serv = self.organization.get_service(id=service.pop('id', None), name=service.pop('name'))
            if not serv in self.services:
                self.add_service(serv)
        for service in self.services:
            service.running()

    def json(self):
        return router.get_environment(org_id=self.organizationId, env_id=self.environmentId).json()

    def delete(self):
        router.delete_environment(org_id=self.organizationId, env_id=self.environmentId)
        return True

    def set_as_default(self):
        data = json.dumps({'environmentId': self.id})
        return router.put_organization_default_environment(org_id=self.organizationId, data=data).json()

    def list_available_services_json(self):
        return router.get_environment_available_services(org_id=self.organizationId, env_id=self.environmentId).json()

    def list_services_json(self):
        return self.json()['services']

    _put_environment = lambda self, data: router.put_environment(org_id=self.organizationId, env_id=self.environmentId, data=data)

    def add_service(self, service):
        resp = None
        if service not in self.services:
            time.sleep(3)  # TODO: Need to wait until strategy comes up
            data = self.json()
            data['serviceIds'].append(service.instanceId)
            data['services'].append(service.json())
            log.info("Adding service %s (%s) to environment %s (%s)" % (service.name, service.id, self.name, self.id))
            resp = self._put_environment(data=json.dumps(data))

        if service.is_secure_vault:
            user_data = service.userData
            if 'defaultKey' in user_data:
                key = user_data['defaultKey']
            else:
                key = service.regenerate()['id']

            self.add_policy(
                {"action": "provisionVms",
                 "parameter": "publicKeyId",
                 "value": key})
        return resp.json() if resp else None

    def remove_service(self, service):
        data = self.json()
        data['serviceIds'].remove(service.instanceId)
        data['services']=[s for s in data['services'] if s['id'] != service.id]
        log.info("Removing service %s (%s) from environment %s (%s)" % (service.name, service.id, self.name, self.id))
        resp = self._put_environment(data=json.dumps(data))
        return resp.json()

    def add_marker(self, marker):
        time.sleep(0.5) # TODO: Need to wait until strategy comes up
        data = self.json()
        data['markers'].append({'name': marker})

        log.info("Adding marker %s to environment %s (%s)" % (marker, self.name, self.id))
        resp = self._put_environment(data=json.dumps(data))
        self.markers.append(marker)
        return resp.json()

    def remove_marker(self, marker):
        data = self.json()
        data['markers'].remove({'name': marker})

        log.info("Removing marker %s from environment %s (%s)" % (marker, self.name, self.id))
        resp = self._put_environment(data=json.dumps(data))
        self.markers.remove(marker)
        return resp.json()

    def add_property(self, name, type, value):
        time.sleep(0.5) # TODO: Need to wait until strategy comes up
        data = self.json()
        data['properties'].append({'name': name, 'type': type, 'value': value})

        log.info("Adding property %s to environment %s (%s)" % (name, self.name, self.id))
        resp = self._put_environment(data=json.dumps(data))
        self.properties.append({'name': name, 'type': type, 'value': value})
        return resp.json()
    set_property = add_property

    def remove_property(self, name):
        data = self.json()
        property = [p for p in data['properties'] if p['name'] == name]
        if len(property) < 1:
            log.error('Unable to remove property %s. Not found.' % name)
        data['properties'].remove(property[0])

        log.info("Removing property %s from environment %s (%s)" % (name, self.name, self.id))
        return self._put_environment(data=json.dumps(data)).json()

    def clean(self):
        data = self.json()
        data['serviceIds'] = []
        data['services'] = []

        log.info("Cleaning environment %s (%s)" % (self.name, self.id))
        return self._put_environment(data=json.dumps(data)).json()

    def add_policy(self, new):
        time.sleep(0.5) # TODO: Need to wait until strategy comes up
        data = self.json()
        data['policies'].append(new)

        log.info("Adding policy %s.%s to environment %s (%s)" % (new.get('action'), new.get('parameter'), self.name, self.id))
        resp = self._put_environment(data=json.dumps(data))
        self.policies.append(new)
        return resp.json()

    def remove_policy(self):
        raise NotImplementedError

    def set_backend(self, zone):
        raise exceptions.ApiError("Change environment backend is not supported, since 24.x")

class EnvironmentList(QubellEntityList):
    base_clz = Environment
    @property
    def default(self):
        """
            Returns environment marked as default.
            When Zone is set marked default makes no sense, special env with proper Zone is returned.
        """
        if ZONE_NAME:
            log.info("Getting or creating default environment for zone with name '{0}'".format(DEFAULT_ENV_NAME()))
            zone_id = self.organization.zones[ZONE_NAME].id
            return self.organization.get_or_create_environment(name=DEFAULT_ENV_NAME(), zone=zone_id)

        def_envs = [env_j["id"] for env_j in self.json() if env_j["isDefault"] == True]

        if len(def_envs)>1:
            log.warning('Found more than one default environment. Picking last.')
            return self[def_envs[-1]]
        elif len(def_envs) == 1:
            return self[def_envs[0]]
        raise exceptions.NotFoundError('Unable to get default environment')

