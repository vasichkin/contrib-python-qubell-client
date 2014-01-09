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

from qubell.api.private.organization import Organization
from qubell.api.private import exceptions


class Provider(Organization):

    def __init__(self, context, id):
        self.auth = context
        self.providerId = id
        my = self.json()
        self.__dict__.update(my)

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def json(self):
        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/providers.json'
        resp = requests.get(url, cookies=self.auth.cookies, verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            provider = [x for x in resp.json() if x['id'] == self.providerId]
            if len(provider)>0:
                return provider[0]
        raise exceptions.ApiError('Unable to get provider %s properties, got error: %s' % (self.providerId, resp.text))

    def delete(self):
        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/providers/'+self.providerId+'.json'
        headers = {'Content-Type': 'application/json'}
        resp = requests.delete(url, cookies=self.auth.cookies, data=json.dumps({}), verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return True
        raise exceptions.ApiError('Unable to delete provider %s, got error: %s' % (self.providerId, resp.text))
