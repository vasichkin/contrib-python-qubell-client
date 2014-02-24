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
from qubell import deprecated

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

import logging as log
import simplejson as json

from qubell.api.private import exceptions
from qubell.api.private.common import QubellEntityList
from qubell.api.provider.router import ROUTER as router

class Environment(object):
    def __update(self):
        info = self.json()
        self.name = info['name']
        self.id = self.environmentId
        self.zoneId = info['backends'][0]['id']
        self.isDefault = info['isDefault']

    def __init__(self, organization, auth=None, **kwargs):
        if 'environmentId' in locals():
            log.warning("Environment reinitialized. Dangerous!")
        self.services = []
        self.policies = []
        self.markers = []
        self.properties = []
        self.providers = []
        self.auth = auth
        self.organization = organization
        self.organizationId = self.organization.organizationId
        if 'id' in kwargs:
            self.environmentId = kwargs.get('id')
            self.__update()

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def create(self, name, zone=None, default=False):
        log.info("Creating environment: %s" % name)
        if not zone:
            zone = self.organization.zone.zoneId
        data = {'isDefault': default,
                'name': name,
                'backend': zone,
                'organizationId': self.organizationId}
        resp = router.post_organization_environment(org_id=self.organizationId, data=json.dumps(data))
        self.environmentId = resp.json()['id']
        self.__update()
        return self

    def restore(self, config):
        for marker in config.pop('markers', []):
            self.add_marker(marker)
        for policy in config.pop('policies', []):
            self.add_policy(policy)
        for property in config.pop('properties', []):
            self.add_property(**property)
        for provider in config.pop('providers', []):
            prov = self.organization.get_or_create_provider(id=provider.pop('id', None), name=provider.pop('name'), parameters=provider)
            self.add_provider(prov)
        for service in config.pop('services', []):
            serv = self.organization.get_or_create_service(id=service.pop('id', None), name=service.pop('name'), type=service.pop('type', None))
            self.add_service(serv)
            if serv.type == 'builtin:cobalt_secure_store':
                # TODO: We do not need to regenerate key every time. Find better way.
                myenv = self.organization.get_environment(self.environmentId)
                myenv.add_policy(
                    {"action": "provisionVms",
                     "parameter": "publicKeyId",
                     "value": serv.regenerate()['id']})

    def json(self):
        return router.get_environment(org_id=self.organizationId, env_id=self.environmentId).json()

    def delete(self):
        router.delete_environment(org_id=self.organizationId, env_id=self.environmentId)
        return True

    def set_as_default(self):
        data = json.dumps({'environmentId': self.id})
        return router.put_organization_default_environment(org_id=self.organizationId, data=data).json()

    def list_available_services(self):
        return router.get_environment_available_services(org_id=self.organizationId, env_id=self.environmentId).json()

    _put_environment = lambda self, data: router.put_environment(org_id=self.organizationId, env_id=self.environmentId, data=data)

    def add_service(self, service):
        data = self.json()
        data['serviceIds'].append(service.instanceId)
        data['services'].append(service.json())

        resp = self._put_environment(data=json.dumps(data))
        self.services.append(service)
        return resp.json()

    def remove_service(self, service):
        data = self.json()
        data['serviceIds'].remove(service.instanceId)
        data['services'].remove(service.json())

        resp = self._put_environment(data=json.dumps(data))
        self.services.remove(service)
        return resp.json()

    def add_marker(self, marker):
        data = self.json()
        data['markers'].append({'name': marker})

        resp = self._put_environment(data=json.dumps(data))
        self.markers.append(marker)
        return resp.json()

    def remove_marker(self, marker):
        data = self.json()
        data['markers'].remove({'name': marker})

        resp = self._put_environment(data=json.dumps(data))
        self.markers.remove(marker)
        return resp.json()

    def add_property(self, name, type, value):
        data = self.json()
        data['properties'].append({'name': name, 'type': type, 'value': value})

        resp = self._put_environment(data=json.dumps(data))
        self.properties.append({'name': name, 'type': type, 'value': value})
        return resp.json()

    def remove_property(self, name):
        data = self.json()
        property = [p for p in data['properties'] if p['name'] == name]
        if len(property)<1:
            log.error('Unable to remove property %s. Not found.' % name)
        data['properties'].remove(property[0])

        return self._put_environment(data=json.dumps(data)).json()

    def clean(self):
        data = self.json()
        data['serviceIds'] = []
        data['services'] = []

        return self._put_environment(data=json.dumps(data)).json()

    def add_policy(self, new):
        data = self.json()
        data['policies'].append(new)

        resp = self._put_environment(data=json.dumps(data))
        self.policies.append(new)
        return resp.json()

    def remove_policy(self):
        raise NotImplementedError

    def add_provider(self, provider):
        data = self.json()
        data.update({'providerId': provider.providerId})

        resp = self._put_environment(data=json.dumps(data))
        self.providers.append(provider)
        return resp.json()

    def remove_provider(self):
        raise NotImplementedError

    def set_backend(self, zone):
        raise exceptions.ApiError("Change environment backend is not supported, since 24.x")
        # data = self.json()
        # data.update({'backend': zone.zoneId})
        # return self._put_environment(data=json.dumps(data)).json()

class EnvironmentList(QubellEntityList):
    base_clz = Environment