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
import re

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

    @property
    def userData(self): return self.json()['userData']

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


    @property
    def activitylog(self):
        return self.get_activitylog()

    def get_activitylog(self, after=None, severity=None, start=None, end=None):
        """
        Returns activitylog object
        severity - filter severity ('INFO', DEBUG')
        start/end - time or log text

        """
        if after:
            log = router.get_instance_activitylog(org_id=self.organizationId, instance_id=self.instanceId, timestamp=after).json()
        log = router.get_instance_activitylog(org_id=self.organizationId, instance_id=self.instanceId).json()

        return activityLog(log, severity=severity, start=start, end=end)

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
            atr = self.json()[key]
            log.debug(atr)
            return atr

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
    def new(application, revision=None, environment=None, name=None, parameters=None, submodules=None, destroyInterval=None):

        if not environment:
            environment = application.organization.defaultEnvironment
        if not parameters: parameters = {}
        conf = {}
        conf['parameters'] = parameters
        conf['environmentId'] = environment.environmentId

        if name:
            conf['instanceName'] = name
        if destroyInterval:
            conf['destroyInterval'] = destroyInterval
        if revision:
            conf['revisionId'] = revision.id
        conf['submodules'] = submodules or {}
        log.info("Starting instance: %s\n    Application: %s (%s)\n    Environment: %s (%s)\n    Submodules: %s\n    destroyInterval: %s" %
                 (name,
                  application.name, application.applicationId,
                  environment.name, environment.environmentId,
                  submodules, destroyInterval))
        log.debug("Instance configuration: %s" % conf)
        data = json.dumps(conf)
        before_creation = time.gmtime(time.time())
        resp = router.post_organization_instance(org_id=application.organizationId, app_id=application.applicationId, data=data)
        instance = Instance(organization=application.organization, id=resp.json()['id'])
        instance._last_workflow_started_time = before_creation
        log.debug("Instance %s (%s) started." % (instance.name, instance.id))
        return instance

    def ready(self, timeout=3):  # Shortcut for convinience. Timeout = 3 min (ask timeout*6 times every 10 sec)
        return waitForStatus(instance=self, final='Running', accepted=['Launching', 'Requested', 'Executing', 'Unknown'], timeout=[timeout*20, 3, 1])
        # TODO: Unknown status  should be removed

        #TODO: not available
    def destroyed(self, timeout=3):  # Shortcut for convinience. Temeout = 3 min (ask timeout*6 times every 10 sec)
        return waitForStatus(instance=self, final='Destroyed', accepted=['Destroying', 'Running'], timeout=[timeout*20, 3, 1])

    def run_workflow(self, name, parameters=None):
        if not parameters: parameters = {}
        log.info("Running workflow %s on instance %s (%s)" % (name, self.name, self.id))
        log.debug("Parameters: %s" % parameters)
        self._last_workflow_started_time = time.gmtime(time.time())
        router.post_instance_workflow(org_id=self.organizationId, instance_id=self.instanceId, wf_name=name, data=json.dumps(parameters))
        return True

    #alias
    run_command = run_workflow

    def schedule_workflow(self, name, timestamp, parameters=None):
        if not parameters: parameters = {}
        log.info("Scheduling workflow %s on instance %s (%s), timestamp: %s" % (name, self.name, self.id, timestamp))
        log.debug("Parameters: %s" % parameters)
        payload = {'parameters': parameters, 'timestamp':timestamp}
        router.post_instance_workflow_schedule(org_id=self.organizationId, instance_id=self.instanceId, wf_name=name, data=json.dumps(payload))
        return True

    def reschedule_workflow(self, workflow_id, timestamp):
        log.info("ReScheduling workflow %s on instance %s (%s), timestamp: %s" % (workflow_id, self.name, self.id, timestamp))
        payload = {'timestamp':timestamp}
        router.post_instance_reschedule(org_id=self.organizationId, instance_id=self.instanceId, workflow_id=workflow_id, data=json.dumps(payload))
        return True

    def get_manifest(self):
        return router.post_application_refresh(org_id=self.organizationId, app_id=self.applicationId).json()

    def reconfigure(self, revision=None, parameters=None, submodules=None):
        #note: be carefull refactoring this, or you might have unpredictable results
        #todo: private api seems requires at least presence of submodule names if exist
        payload = {}
        payload['parameters'] = self.parameters

        if revision:
            payload['revisionId'] = revision.id

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
        return router.delete_instance_force(org_id=self.organizationId, instance_id=self.instanceId)

    def cancel_command(self):
        return router.post_instance_action(org_id=self.organizationId, instance_id=self.instanceId, action="cancel")
    def star(self):
        return router.post_instance_action(org_id=self.organizationId, instance_id=self.instanceId, action="star")
    def unstar(self):
        return router.post_instance_action(org_id=self.organizationId, instance_id=self.instanceId, action="unstar")

    def delete(self):
        self.destroy()
        #todo: remove, if destroyed
        return True

    def destroy(self):
        log.info("Destroying instance %s (%s)" % (self.name, self.id))
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

class activityLog(object):
    TYPES=['status updated', 'signals updated', 'dynamic links updated', 'command started', 'command finished', 'workflow started', 'workflow finished', 'step started', 'step finished']
    log=[]
    def __init__(self, log, severity=None, start=None, end=None):
        def sort(log):
            return sorted(log, key=lambda x: x['time'], reverse=False)

        self.log = sort(log)
        self.severity = severity
        if severity:
            self.log = [x for x in self.log if x['severity'] in severity]

        if start:
            self.log = [x for x in self.log if x['time']>=start]
        if end:
            self.log = [x for x in self.log if x['time']<=end]

    def __len__(self):
        return len(self.log)

    def __iter__(self):
        for i in self.log:
            yield i

    def __str__(self):
        text = 'Severity: %s' % self.severity or 'ALL'
        for x in self.log:
            try:
                text += '\n{0}: {1}: {2}'.format(x['time'], x['eventTypeText'], x['description'].replace('\n', '\n\t\t'))
            except KeyError:
                text += '\n{0}: {2}'.format(x['time'], x['description'].replace('\n', '\n\t\t'))
        return text

    def __contains__(self, item):
        return len(self.find(item))

    def __getitem__(self, item):
        """
        Guess what item to return: time, index or description
        log[0] will return first entry
        log[1402654329064] will return description of event with tis time
        log['Status is Running'] will return time of event, if found.
        """

        if isinstance(item, int):
            if item>1000000000000:
                return ['{0}: {1}'.format(x['eventTypeText'], x['description']) for x in self.log if x['time']==item][0]
            return '{0}: {1}'.format(self.log[item]['eventTypeText'], self.log[item]['description'])
        elif isinstance(item, str):
            return self.find(item)[0]
        return False

    def find(self, item, description='', event_type=''):
        """ Find regexp in activitylog
        find record as if type are in description.
        #TODO: should be refactored, dumb logic
        """
        if ': ' in item:
            splited = item.split(': ', 1)
            if splited[0] in self.TYPES:
                description = item.split(': ')[1]
                event_type = item.split(': ')[0]
            else:
                description = item
        else:
            if not description:
                description = item

        if event_type:
            found = [x['time'] for x in self.log if re.search(description, x['description']) and x['eventTypeText']==event_type]
        else:
            found = [x['time'] for x in self.log if re.search(description, x['description'])]

        if len(found):
            return found
        raise exceptions.ApiNotFoundError('Cannot find activity log entry: %s: %s' % (event_type, description))


    def get_interval(self, start_text=None, end_text=None):
        if start_text:
            begin = self.find(start_text)
            interval = activityLog(self.log, self.severity, start=begin[0])
        else:
            interval = self

        if end_text:
            end = interval.find(end_text)
            interval = activityLog(interval, self.severity, end=end[0])

        if len(interval):
            return interval
        raise exceptions.NotFoundError('Activitylog interval not found: [%s , %s]' % (start_text, end_text))

