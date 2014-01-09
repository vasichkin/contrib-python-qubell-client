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
from qubell.api.public.organization import Organization
from qubell.api.private import exceptions

class Application(Organization):
    """
    Base class for applications. It should create application and services+environment requested
    """
    rawResponse = None

    def __parse(self, values):
        ret = {}
        for val in values:
            ret[val['id']] = val['value']
        return ret

    def __init__(self, context, id):
        self.auth = context
        self.applicationId = id
        self.auth.applicationId = id

        my = self.json()
        self.name = my['name']
        #self.manifest = my['manifest']

    def delete(self):
        raise NotImplementedError

    def clean(self):
        from qubell.api.public import instance, revision

        instances = self.instances
        if instances:
            for ins in instances:
                obj = instance.Instance(context=self.auth, id=ins['id'])
                st = obj.status
                if st not in ['Destroyed', 'Destroying', 'Launching', 'Executing']: # Tests could fail and we can get any statye here
                    log.info("Destroying instance %s" % obj.name)
                    obj.delete()
                    assert obj.destroyed(timeout=10)

        revisions = self.revisions
        if revisions:
            for rev in revisions:
                obj = revision.Revision(context=self.auth, id=rev['id'])
                obj.delete()
        return True

    def json(self, key=None):
        url = self.auth.api+'/api/1/organizations/'+self.auth.organizationId+'/applications'
        resp = requests.get(url, auth=(self.auth.user, self.auth.password), verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            org = [x for x in resp.json() if x['id'] == self.applicationId]
            if len(org)>0:
                return org[0]
            raise exceptions.NotFoundError('Unable to find application by id: %s' % self.organizationId)
        raise exceptions.ApiError('Unable to get application by id: %s, got error: %s' % (self.organizationId, resp.text))

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def upload(self, manifest):
        log.info("Uploading manifest")
        url = self.auth.api+'/api/1/applications/'+self.applicationId+'/manifest'
        headers = {'Content-Type': 'application/x-yaml'}
        resp = requests.put(url, auth=(self.auth.user, self.auth.password), data=manifest.content, verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            self.manifest = manifest
            return resp.json()
        raise exceptions.ApiError('Unable to upload manifest to application id: %s, got error: %s' % (self.applicationId, resp.text))

    def launch(self, **argv):
        url = self.auth.api+'/api/1/applications/'+self.applicationId+'/launch'
        headers = {'Content-Type': 'application/json'}
        #if not 'environmentId' in argv.keys():
        #    argv['environmentId'] = self.context.environmentId
        data = json.dumps(argv)
        resp = requests.post(url, auth=(self.auth.user, self.auth.password), data=data, verify=False, headers=headers)

        log.debug('--- APPLICATION LAUNCH REQUEST ---')
        log.debug('REQUEST HEADERS: %s' % resp.request.headers)
        log.debug('REQUEST: %s' % resp.request.body)
        log.debug('RESPONSE: %s' % resp.text)
        if resp.status_code == 200:
            instance_id = resp.json()['id']
            return self.get_instance(id=instance_id)
        raise exceptions.ApiError('Unable to launch application id: %s, got error: %s' % (self.applicationId, resp.text))

    def get_instance(self, id):
        from qubell.api.public.instance import Instance
        return Instance(context=self.auth, id=id)

    def delete_instance(self, id):
        ins = self.get_instance(id)
        return ins.delete()

    def get_revision(self, id):
        from qubell.api.public.revision import Revision
        self.auth.applicationId = self.applicationId
        return Revision(context=self.auth, id=id)


    def list_revisions(self):
        url = self.auth.api+'/api/1/applications/'+self.applicationId+'/revisions'
        resp = requests.get(url, auth=(self.auth.user, self.auth.password), verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get revisions list, got error: %s' % resp.text)

    def create_revision(self, name, instance, parameters=[], version=None):
        raise NotImplementedError

    def delete_revision(self, id):
        raise NotImplementedError

    def get_manifest(self):
        raise NotImplementedError
