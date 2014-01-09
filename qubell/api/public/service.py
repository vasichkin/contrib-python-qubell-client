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

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__version__ = "1.0.13"
__email__ = "vkhomenko@qubell.com"

import logging as log

import requests
import simplejson as json
import yaml

from qubell.api.private.organization import Organization
from qubell.api.private import exceptions


class Service(Organization):

    def __init__(self, context, id):
        self.auth = context
        self.serviceId = id
        my = self.json()
        self.name = my['name']
        self.type = my['typeId']
        self.zone = my['zoneId']

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def json(self):
        url = self.auth.api+'/api/1/services/'+self.serviceId
        resp = requests.get(url, auth=(self.auth.user, self.auth.password), verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get service properties, got error: %s' % resp.text)

    # TODO: should be separate class
    def regenerate(self):
        raise NotImplementedError

    def modify(self, parameters):
        url = self.auth.api+'/api/1/services/'+self.serviceId
        headers = {'Content-Type': 'application/json'}
        payload = {#'id': self.serviceId,
                   'name': self.name,
                   'parameters': parameters}
        resp = requests.put(url, auth=(self.auth.user, self.auth.password), data=json.dumps(payload), verify=False, headers=headers)
        log.debug(resp.request.body)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to modify service %s: %s' % (self.name, resp.text))

    def add_shared_instance(self, revision, instance):
        params = self.json()['parameters']
        if params.has_key('configuration.shared-instances'):
            params['configuration.shared-instances'][revision.revisionId.split('-')[0]] = instance.instanceId
            self.modify(params)
        else:
            raise exceptions.ApiError('Unable to add shared instance %s to service %s' % (instance.name, self.name))

    def remove_shared_instance(self, instance=None, revision=None):
        params = self.json()['parameters']
        if params.has_key('configuration.shared-instances'):
            if instance.instanceId in params['configuration.shared-instances'].values():
                val = [x for x,y in params['configuration.shared-instances'].items() if y == instance.instanceId]
                del params['configuration.shared-instances'][val[0]]
            else:
                raise exceptions.ApiError('Unable find shared instance %s in service %s' % (instance.instanceId, self.name))
            self.modify(params)
        else:
            raise exceptions.ApiError('Unable to add shared instance %s to service %s' % (instance.name, self.name))

    def list_shared_instances(self):
        params = self.json()['parameters']
        return yaml.safe_load(params['configuration.shared-instances'])


    def delete(self):
        raise NotImplementedError
