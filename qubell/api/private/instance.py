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

from qubell.api.tools import waitForStatus as waitForStatus
from qubell.api.private import exceptions



class Instance(object):
    """
    Base class for application instance. Manifest required.
    """

    def __parse(self, values):
        ret = {}
        for val in values:
            ret[val['id']] = val['value']
        return ret

    def __init__(self, auth, application, id):
        self.instanceId = id
        self.application = application
        self.auth = auth
        self.auth.instanceId = self.instanceId
        self.name = self.name

    def __getattr__(self, key):
        url = self.auth.api+'/organizations/'+self.application.organizationId+'/instances/'+self.instanceId+'.json'
        resp = requests.get(url, cookies=self.auth.cookies, data="{}", verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            # return same way old_public api does
            if key in ['returnValues', ]:
                return self.__parse(resp.json()[key])
            else:
                return resp.json()[key]
        raise exceptions.NotFoundError('Unable to get instance properties, got error: %s' % resp.text)

    def ready(self, timeout=3):  # Shortcut for convinience. Temeout = 3 min (ask timeout*6 times every 10 sec)
        return waitForStatus(instance=self, final='Running', accepted=['Launching', 'Requested', 'Executing', 'Unknown'], timeout=[timeout*6, 10, 1])
        # TODO: Unknown status  should be removed

        #TODO: not available
    def destroyed(self, timeout=3):  # Shortcut for convinience. Temeout = 3 min (ask timeout*6 times every 10 sec)
        return waitForStatus(instance=self, final='Destroyed', accepted=['Destroying', 'Running'], timeout=[timeout*6, 10, 1])

    def run_workflow(self, name, parameters={}):
        log.info("Running workflow %s" % name)

        url = self.auth.api+'/organizations/'+self.application.organizationId+'/instances/'+self.instanceId+'/workflows/'+name+'.json'
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps(parameters)
        resp = requests.post(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return True
        raise exceptions.ApiError('Unable to run workflow %s, got error: %s' % (name, resp.text))


    def get_manifest(self):
        url = self.auth.api+'/organizations/'+self.application.organizationId+'/applications/'+self.auth.applicationId+'/refreshManifest.json'
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({})
        resp = requests.post(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get manifest, got error: %s' % resp.text)



    def reconfigure(self, name='reconfigured', **kwargs):
        revisionId = kwargs.get('revisionId', '')
        parameters = kwargs.get('parameters', {})
        submodules = kwargs.get('submodules', {})
        url = self.auth.api+'/organizations/'+self.application.organizationId+'/instances/'+self.instanceId+'/configuration.json'
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({
                   'parameters': parameters,
                   'submodules': submodules,
                   'revisionId': revisionId,
                   'instanceName': name})
        resp = requests.put(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)

        log.debug('--- INSTANCE RECONFIGUREATION REQUEST ---')
        log.debug('REQUEST HEADERS: %s' % resp.request.headers)
        log.debug('REQUEST: %s' % resp.request.body)
        log.debug('RESPONSE: %s' % resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to reconfigure instance, got error: %s' % resp.text)


    def delete(self):
        return self.destroy()

    def destroy(self):
        log.info("Destroying")
        url = self.auth.api+'/organizations/'+self.application.organizationId+'/instances/'+self.instanceId+'/workflows/destroy.json'
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, cookies=self.auth.cookies, data=json.dumps({}), verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to destroy instance, got error: %s' % resp.text)

    def __del__(self):
        pass

