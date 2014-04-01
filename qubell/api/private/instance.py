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
from qubell.api.private.environment import EnvironmentList
from qubell.api.private.revision import Revision
from qubell.api.private.service import ServiceMixin

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

import logging as log
import simplejson as json
import time
from qubell.api.tools import lazyproperty

from qubell.api.tools import waitForStatus as waitForStatus
from qubell.api.private import exceptions
from qubell.api.private.common import QubellEntityList, Entity
from qubell.api.provider.router import ROUTER as router

DEAD_STATUS = ['Destroyed', 'Destroying']

class Instance(Entity, ServiceMixin):
    """
    Base class for application instance. Manifest required.
    """

    def __init__(self, organization, id):
        self.instanceId = self.id = id
        self.organization = organization
        self.organizationId = organization.organizationId

        self.__cached_json = None
        self._last_workflow_started_time = None

    @lazyproperty
    def application(self):
        return self.organization.applications[self.applicationId]

    @lazyproperty
    def environment(self):
        return self.organization.environments[self.environmentId]

    @lazyproperty
    def applicationId(self): return self.json()['applicationId']

    @lazyproperty
    def environmentId(self): return self.json()['environmentId']

    @lazyproperty
    def submodules(self):
        # TODO: Public api hack.
        # Private returns 'submodules', public returns 'components'
        if router.public_api_in_use:
            return InstanceList(list_json_method=lambda: self.json()['components'], organization=self.organization)
        return InstanceList(list_json_method=lambda: self.json()['submodules'], organization=self.organization)

    @property
    def status(self): return self.json()['status']

    @property
    def name(self): return self.json()['name']

    def __parse(self, values):
        return {val['id']: val['value'] for val in values}

    @property
    def return_values(self):
        """ Guess what api we are using and return as public api does.
        Private has {'id':'key', 'value':'keyvalue'} format, public has {'key':'keyvalue'}
        """
        # TODO: Public api hack.
        retvals = self.json()['returnValues']
        if router.public_api_in_use:
            return retvals
        return self.__parse(retvals)


    @property
    def error(self): return self.json()['errorMessage']

    #aliases
    returnValues = return_values
    errorMessage = error

    @property
    def parameters(self):
        ins = self.json()
        # TODO: Public api hack.
        # We do not have 'revision' in public api
        if router.public_api_in_use:
            return self.json()['parameters']
        return self.json()['revision']['parameters']

    def __getattr__(self, key):
        if key in ['instanceId',]:
            raise exceptions.NotFoundError('Unable to get instance property: %s' % key)
        if key == 'ready':
            log.debug('Checking instance status')
            return self.ready()
        else:
            log.debug('Getting instance attribute: %s' % key)
            return self.json()[key]

    def _cache_free(self):
        """Frees cache"""
        self.__cached_json = None

    def fresh(self):
        #todo: create decorator from this
        if self.__cached_json is None:
            return False
        now = time.time()
        elapsed = (now - self.__last_read_time) * 1000.0
        return elapsed < 300

    def json(self):
        '''
        return __cached_json, if accessed withing 300 ms.
        This allows to optimize calls when many parameters of entity requires withing short time.
        '''

        if self.fresh():
            return self.__cached_json
        self.__last_read_time = time.time()
        self.__cached_json = router.get_instance(org_id=self.organizationId, instance_id=self.instanceId).json()
        return self.__cached_json

    @staticmethod
    def new(application, revision=None, environment=None, name=None, parameters=None, destroyInterval=None):

        if not parameters: parameters = {}
        conf = {}
        conf['parameters'] = parameters
        if environment:  # if environment set, it overrides parameter
            conf['environmentId'] = environment.environmentId
        elif not 'environmentId' in parameters.keys():  # if not set and not in params, use default
            conf['environmentId'] = application.organization.defaultEnvironment.environmentId
        if name:
            conf['instanceName'] = name
        if destroyInterval:
            conf['destroyInterval'] = destroyInterval
        if revision:
            conf['revisionId'] = revision.revisionId
        log.info("Creating instance: %s" % name)
        log.debug("Instance configuration: %s" % conf)
        data = json.dumps(conf)
        before_creation = time.gmtime(time.time())
        resp = router.post_organization_instance(org_id=application.organizationId, app_id=application.applicationId, data=data)
        instance = Instance(organization=application.organization, id=resp.json()['id'])
        instance._last_workflow_started_time = before_creation
        return instance

    def ready(self, timeout=3):  # Shortcut for convinience. Timeout = 3 min (ask timeout*6 times every 10 sec)
        return waitForStatus(instance=self, final='Running', accepted=['Launching', 'Requested', 'Executing', 'Unknown'], timeout=[timeout*20, 3, 1])
        # TODO: Unknown status  should be removed

        #TODO: not available
    def destroyed(self, timeout=3):  # Shortcut for convinience. Temeout = 3 min (ask timeout*6 times every 10 sec)
        return waitForStatus(instance=self, final='Destroyed', accepted=['Destroying', 'Running'], timeout=[timeout*20, 3, 1])

    def run_workflow(self, name, parameters=None):
        if not parameters: parameters = {}
        log.info("Running workflow %s" % name)
        self._last_workflow_started_time = time.gmtime(time.time())
        router.post_instance_workflow(org_id=self.organizationId, instance_id=self.instanceId, wf_name=name, data=json.dumps(parameters))
        return True

    #alias
    run_command = run_workflow

    def get_manifest(self):
        return router.post_application_refresh(org_id=self.organizationId, app_id=self.applicationId).json()

    def reconfigure(self, revision=None, parameters=None):
        #note: be carefull refactoring this, or you might have unpredictable results
        #todo: private api seems requires at least presence of submodule names if exist
        payload = {}
        payload['parameters'] = self.parameters

        if revision:
            payload['revisionId'] = revision.revisionId

        submodules = (parameters or {}).pop('submodules', None)
        if submodules:
            payload['submodules'] = submodules
        if parameters is not None:
            payload['parameters'] = parameters

        resp = router.put_instance_configuration(org_id=self.organizationId, instance_id=self.instanceId, data=json.dumps(payload))
        return resp.json()

    def rename(self, name):
        payload = json.dumps({'instanceName': name})
        return router.put_instance_configuration(org_id=self.organizationId, instance_id=self.instanceId, data=payload)

    def force_remove(self):
        return router.delete_organizaton_instance_force(org_id=self.organizationId, instance_id=self.instanceId)

    def delete(self):
        self.destroy()
        #todo: remove, if destroyed
        return True

    def destroy(self):
        log.info("Destroying instance %s" % self.name)
        return self.run_workflow("destroy")

    @property
    def serve_environments(self):
        return EnvironmentList(lambda: self.json()["environments"], organization=self.organization)

    def add_as_service(self, environments=None, environment_ids=None):
        if not environments or environment_ids:
            # Use default if not set
            environments = [self.environment,]
        if environments:
            data = [env.environmentId for env in environments]
        else:
            assert isinstance(environment_ids, list)
            data = environment_ids
        router.post_instance_services(org_id=self.organizationId, instance_id=self.instanceId, data=json.dumps(data))

    def remove_as_service(self, environments=None):
        if not environments:
            # Use default if not set
            environments = [self.environment,]
        for env in environments:
            env.remove_service(self)

    @property
    def serviceId(self):
        raise AttributeError("Service is instance reference now, use instanceId")

    @property
    def most_recent_update_time(self):

        """
        Indicated most recent update of the instance, assumption based on:
        - if currentWorkflow exists, its startedAt time is most recent update.
        - else max of workflowHistory startedAt is most recent update.
        """
        parse_time = lambda t: time.gmtime(t/1000)
        j = self.json()
        cw_started_at = j.get('startedAt')
        if cw_started_at: return parse_time(cw_started_at)
        try:
            max_wf_started_at = max([i['startedAt'] for i in j['workflowHistory']])
            return parse_time(max_wf_started_at)
        except ValueError:
            return None

    def _is_projection_updated_instance(self):
        """
        This method tries to guess if instance was update since last time.
        If return True, definitely Yes, if False, this means more unknonw
        :return: bool
        """
        last = self._last_workflow_started_time
        if not router.public_api_in_use:
            most_recent = self.most_recent_update_time
        else:
            most_recent = None
        if last and most_recent:
            return last < most_recent
        return False  # can be more clever


class InstanceList(QubellEntityList):
    base_clz = Instance