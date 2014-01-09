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


class Environment(Organization):

    def __init__(self, context, id):
        self.environmentId = id
        self.auth = context
        self.auth.environmentId = self.environmentId
        my = self.json()
        self.name = my['name']

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def json(self):
        url = self.auth.api+'/api/1/organizations/'+self.auth.organizationId+'/environments'
        resp = requests.get(url, auth=(self.auth.user, self.auth.password), verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            env = [x for x in resp.json() if x['id'] == self.environmentId]
            if len(env)>0:
                return env[0]
            raise exceptions.NotFoundError('Unable to find environment by id: %s' % self.organizationId)
        raise exceptions.ApiError('Unable to get environment by id: %s, got error: %s' % (self.organizationId, resp.text))


    def delete(self):
        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        headers = {'Content-Type': 'application/json'}
        resp = requests.delete(url, cookies=self.auth.cookies, data=json.dumps({}), verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return True
        raise exceptions.ApiError('Unable to delete environment %s, got error: %s' % (self.environmentId, resp.text))

    def servicesAvailable(self):
        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'/availableServices.json'
        resp = requests.get(url, cookies=self.auth.cookies, verify=False)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)


    def serviceAdd(self, service):
        data = self.json()
        data['serviceIds'].append(service.serviceId)
        data['services'].append(service.json())

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)


    def serviceRemove(self, service):
        data = self.json()
        data['serviceIds'].remove(service.serviceId)
        data['services'].remove(service.json())

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)

    def markerAdd(self, marker):
        data = self.json()
        data['markers'].append({'name': marker})

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)


    def markerRemove(self, marker):
        data = self.json()
        data['markers'].remove({'name': marker})

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)



    def propertyAdd(self, name, type, value):
        data = self.json()
        data['properties'].append({'name': name, 'type': type, 'value': value})

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)


    def propertyRemove(self, name):
        data = self.json()
        property = [p for p in data['properties'] if p['name'] == name]
        if len(property)<1:
            log.error('Unable to remove property %s. Not found.' % name)
        data['properties'].remove(property[0])

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)



    def clean(self):
        data = self.json()
        data['serviceIds'] = []
        data['services'] = []

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)


    def __getattr__(self, item):
        return self.json()[item]

    def policyAdd(self, new):
        data = self.json()
        data['policies'].append(new)

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)


    def providerAdd(self, provider):
        data = self.json()
        data.update({'providerId': provider.providerId})

        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        self.rawRespose = resp
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)

    def set_backend(self, zone):
        data = self.json()
        data.update({'backend': zone})
        url = self.auth.api+'/organizations/'+self.auth.organizationId+'/environments/'+self.environmentId+'.json'
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update environment, got error: %s' % resp.text)