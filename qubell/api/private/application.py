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


class Application(object):
    """
    Base class for applications. It should create application and services+environment requested
    """

    def __init__(self, organization, auth, id):
        self.instances = []
        self.revisions = []
        self.auth = auth
        self.organization = organization
        self.applicationId = id
        self.defaultEnvironment = self.organization.get_default_environment()

        my = self.json()
        self.name = my['name']


    def __parse(self, values):
        ret = {}
        for val in values:
            ret[val['id']] = val['value']
        return ret

    def restore(self, config):
        for instance in config.pop('instances',[]):
            launched = self.get_or_launch_instance(id=instance.pop('id', None), name=instance.pop('name'), **instance)
            assert launched.ready()

        #TODO: Think how to restore revisions

    def delete(self):
        log.info("Removing application: %s" % self.name)
        url = self.auth.api+'/organizations/'+self.organization.organizationId+'/applications/'+self.applicationId+'.json'
        resp = requests.delete(url, verify=False, cookies=self.auth.cookies)
        log.debug(resp.text)
        if resp.status_code == 200:
            return True
        raise exceptions.ApiError('Unable to delete application: %s' % resp.text)

    def update(self, **kwargs):
        log.info("Updating application: %s" % self.name)
        url = self.auth.api+'/organizations/'+self.organization.organizationId+'/applications/'+self.applicationId+'.json'
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(kwargs)
        resp = requests.put(url, headers=headers, verify=False, data=data, cookies=self.auth.cookies)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to update application %s, got error: %s' % (self.name, resp.text))

    def clean(self):
        #TODO: Needs refactor
        from qubell.api.private import instance, revision

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

    def json(self):
        url = self.auth.api+'/organizations/'+self.organization.organizationId+'/applications/'+self.applicationId+'.json'
        resp = requests.get(url, cookies=self.auth.cookies, data="{}", verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get application by url %s\n, got error: %s' % (url, resp.text))

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

# INSTANCE
    def launch(self, environment=None, **argv):
        url = self.auth.api+'/organizations/'+self.organization.organizationId+'/applications/'+self.applicationId+'/launch.json'
        headers = {'Content-Type': 'application/json'}
        if environment:
            argv['environmentId'] = environment.environmentId
        elif not 'environmentId' in argv.keys():
            argv['environmentId'] = self.defaultEnvironment.environmentId

        data = json.dumps(argv)
        resp = requests.post(url, cookies=self.auth.cookies, data=data, verify=False, headers=headers)

        log.debug('--- APPLICATION LAUNCH REQUEST ---')
        log.debug('REQUEST HEADERS: %s' % resp.request.headers)
        log.debug('REQUEST: %s' % resp.request.body)
        log.debug('RESPONSE: %s' % resp.text)

        if resp.status_code == 200:
            instance_id = resp.json()['id']
            return self.get_instance(id=instance_id)
        raise exceptions.ApiError('Unable to launch application id: %s, got error: %s' % (self.applicationId, resp.text))

    def get_instance(self, id):
        from qubell.api.private.instance import Instance
        instance = Instance(auth=self.auth, application=self, id=id)
        self.instances.append(instance)
        return instance

    def delete_instance(self, id):
        instance = self.get_instance(id)
        self.instances.remove(instance)
        return instance.delete()

    def get_or_launch_instance(self, id=None, **kwargs):
        if id:
            return self.get_instance(id)
        else:
            return self.launch(**kwargs)

# REVISION
    def get_revision(self, id):
        from qubell.api.private.revision import Revision
        rev = Revision(auth=self.auth, application=self, id=id)
        self.revisions.update({rev.name: rev})
        return rev

    def list_revisions(self):
        return self.revisions()

    def create_revision(self, name, instance, parameters=[], version=None):
        if not version:
            version=self.get_manifest()['version']
        url = self.auth.api+'/organizations/'+self.organization.organizationId+'/applications/'+self.applicationId+'/revisions.json'
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({ 'name': name,
                    'parameters': parameters,
                    'submoduleRevisions': {},
                    'returnValues': [],
                    'applicationId': self.applicationId,
                    'applicationName': self.name,
                    'version': version,
                    'instanceId': instance.instanceId})
        resp = requests.post(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return self.get_revision(id=resp.json()['id'])
        raise exceptions.ApiError('Unable to get revision, got error: %s' % resp.text)

    def delete_revision(self, id):
        rev = self.get_revision(id)
        self.revisions.remove(rev.name)
        rev.delete()

# MANIFEST

    def get_manifest(self):
        url = self.auth.api+'/organizations/'+self.organization.organizationId+'/applications/'+self.applicationId+'/refreshManifest.json'
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({})
        resp = requests.post(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get manifest, got error: %s' % resp.text)

    def upload(self, manifest):
        log.info("Uploading manifest")
        url = self.auth.api+'/organizations/'+self.organization.organizationId+'/applications/'+self.applicationId+'/manifests.json'
        resp = requests.post(url, files={'path': manifest.content}, data={'manifestSource': 'upload', 'name': self.name}, verify=False, cookies=self.auth.cookies)
        log.debug(resp.text)
        if resp.status_code == 200:
            self.manifest = manifest
            return resp.json()
        raise exceptions.ApiError('Unable to upload manifest, got error: %s' % resp.text)
