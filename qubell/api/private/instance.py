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
import re
import logging as log
import time

import simplejson as json

from qubell.api.private.environment import EnvironmentList
from qubell.api.private.service import ServiceMixin
from qubell.api.tools import lazyproperty, retry
from qubell.api.tools import waitForStatus as waitForStatus
from qubell.api.private import exceptions
from qubell.api.private.common import QubellEntityList, Entity
from qubell.api.provider.router import InstanceRouter

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

DEAD_STATUS = ['Destroyed']


class Instance(Entity, ServiceMixin, InstanceRouter):
    """
    Base class for application instance. Manifest required.
    """

    # noinspection PyShadowingBuiltins
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
    def environments(self):
        #TODO: FIXME: get rid of old API when its support will be removed
        old_api_value = lambda: self.json().get('environments', [])
        new_api_value = lambda: self.json().get('serviceIn', [])
        list_environments_json = lambda: new_api_value() or old_api_value()
        return EnvironmentList(list_json_method=list_environments_json, organization=self).init_router(self._router)

    @lazyproperty
    def applicationId(self):
        j = self.json()
        #TODO: FIXME: get rid of old API when its support will be removed
        old_api_value = j.get('applicationId')
        new_api_value = j.get('application', {}).get('id')
        return new_api_value or old_api_value

    @lazyproperty
    def environmentId(self):
        j = self.json()
        #TODO: FIXME: get rid of old API when its support will be removed
        old_api_value = j.get('environmentId')
        new_api_value = j.get('environment', {}).get('id')
        return new_api_value or old_api_value

    @lazyproperty
    def submodules(self):
        # TODO: Public api hack.
        # Private returns 'submodules', public returns 'components'
        if self._router.public_api_in_use:
            return InstanceList(list_json_method=lambda: self.json()['components'], organization=self.organization).init_router(self._router)
        return InstanceList(list_json_method=lambda: self.json()['submodules'], organization=self.organization).init_router(self._router)

    @property
    def destroyAt(self):
        j = self.json()
        return j.get('destroyAt', False)

    @property
    def status(self):
        return self.json()['status']

    @property
    def name(self):
        return self.json()['name']

    @property
    def userData(self):
        return self.json()['userData']

    @staticmethod
    def __parse(values):
        return dict([(val['id'], val['value']) for val in values])

    @staticmethod
    def __collect_interfaces_return(interfaces):
        """Collect new style (44.1+) return values to old-style kv-list"""
        acc = []
        for (interfaceName, interfaceData) in interfaces.items():
            signalValues = interfaceData.get("signals", {})
            for (signalName, signalValue) in signalValues.items():
                pinName = "{0}.{1}".format(interfaceName, signalName)
                acc.append({'id': pinName, 'value': signalValue})
        return acc

    @property
    def return_values(self):
        """ Guess what api we are using and return as public api does.
        Private has {'id':'key', 'value':'keyvalue'} format, public has {'key':'keyvalue'}
        """

        j = self.json()
        #TODO: FIXME: get rid of old API when its support will be removed
        public_api_value = j.get('returnValues')
        old_private_value = j.get('endpoints')
        new_private_value = self.__collect_interfaces_return(j.get('interfaces', {}))

        retvals = new_private_value or old_private_value or public_api_value or []
        # TODO: Public api hack.
        if self._router.public_api_in_use:
            return retvals
        return self.__parse(retvals)

    @property
    def error(self):
        return self.json().get('errorMessage', False)

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
            log_raw = self._router.get_instance_activitylog(org_id=self.organizationId,
                                                            instance_id=self.instanceId,
                                                            params={"after": after}).json()
        else:
            log_raw = self._router.get_instance_activitylog(org_id=self.organizationId,
                                                            instance_id=self.instanceId).json()

        return ActivityLog(log_raw, severity=severity, start=start, end=end)

    # aliases
    returnValues = return_values
    errorMessage = error

    def get_configuration(self):
        return self._router.get_instance_configuration(org_id=self.organizationId,
                                                       instance_id=self.instanceId).json()

    @property
    def parameters(self):
        # todo: Public api hack.
        j = self.json()
        if self._router.public_api_in_use:  # We do not have 'revision' in public api
            return j['parameters']

        #TODO: FIXME: get rid of old API when its support will be removed
        old_api_value = j.get('revision', {}).get('parameters')
        new_api_value = j.get('config')
        # if not (j.get('revision') is None or j['revision'].get('parameters') is None):
        #     parameters = j['revision']['parameters']
        # else:
        #     parameters = j['config']

        parameters = new_api_value or old_api_value
        if type(parameters) == list:  # v39+ - list of dicts: id, title, value
            return self.__parse(parameters)
        else:  # <v39 - dict  todo: remove when 39+ is wide in production
            return parameters

    @property
    def currentWorkflow(self):
        j = self.json()
        #TODO: FIXME: get rid of old API when its support will be removed
        # We could get {} or None for both together. Dependant code expects dict(), so, returning dict.
        if j.get('currentWorkflow', {}):
            return j.get('currentWorkflow', {})
        elif j.get('workflowsInfo', {}).get('currentWorkflow', {}):
            return j.get('workflowsInfo', {}).get('currentWorkflow', {})
        else:
            return {}

    def __getattr__(self, key):
        if key in ['instanceId', ]:
            raise exceptions.NotFoundError('Unable to get instance property: %s' % key)
        if key == 'ready':
            log.debug('Checking instance status')
            return self.ready()
        #TODO: FIXME: old API support: remove when its support will be removed on server
        elif key in ['workflowHistory', 'scheduledWorkflows', 'availableWorkflows']:
            log.debug('Getting instance workflow attribute: %s' % key)
            j = self.json()
            old_api_value = j.get(key)
            new_api_value = j.get('workflowsInfo', {}).get(key, False)
            atr = new_api_value or old_api_value or []
            log.debug(atr)
            return atr
        else:
            log.debug('Getting instance attribute: %s' % key)
            atr = self.json()[key]
            log.debug(atr)
            return atr

    # TODO: make such behaviour default
    @property
    @retry(3, 1, 3, retry_exception=(KeyError, AssertionError))
    def technicalInfo(self): # This property is not always there. Waiting to appear
        ret = self.json()['technicalInfo']
        assert isinstance(ret, dict)
        return ret

    def _cache_free(self):
        """Frees cache"""
        self.__cached_json = None

    def fresh(self):
        # todo: create decorator from this
        if self.__cached_json is None:
            return False
        now = time.time()
        elapsed = (now - self.__last_read_time) * 1000.0
        return elapsed < 300

    def json(self):
        """
        return __cached_json, if accessed withing 300 ms.
        This allows to optimize calls when many parameters of entity requires withing short time.
        """

        if self.fresh():
            return self.__cached_json
        # noinspection PyAttributeOutsideInit
        self.__last_read_time = time.time()
        self.__cached_json = self._router.get_instance(org_id=self.organizationId, instance_id=self.instanceId).json()
        return self.__cached_json

    @staticmethod
    def new(router, application, revision=None, environment=None, name=None, parameters=None,
            submodules=None, destroyInterval=None):

        if not environment:
            environment = application.organization.defaultEnvironment

        if not environment.isOnline:
            # If environment offline for any reason, let it come up. Otherwise raise error
            @retry(tries=10, delay=1, backoff=1.5, retry_exception=AssertionError)
            def eventually_online():
                assert environment.isOnline, "Environment {name} didn't get Online status".format(name=environment.name)
            eventually_online()

        if not parameters:
            parameters = {}
        conf = {'parameters': parameters, 'environmentId': environment.environmentId}

        if name:
            conf['instanceName'] = name
        if destroyInterval is not None:
            conf['destroyInterval'] = int(destroyInterval)
        if revision:
            conf['revisionId'] = revision.id
        conf['submodules'] = submodules or {}
        log.info(("Starting instance: %s\n"
                  "    Application: id=%s\n"
                  "    Environment: id=%s\n"
                  "    Submodules: %s\n"
                  "    destroyInterval: %s") %
                 (name,
                  application.applicationId,
                  environment.environmentId,
                  submodules, destroyInterval))
        log.debug("Instance configuration: %s" % conf)
        data = json.dumps(conf)
        before_creation = time.gmtime(time.time())
        resp = router.post_organization_instance(org_id=application.organizationId, app_id=application.applicationId,
                                                 data=data)
        instance = Instance(organization=application.organization, id=resp.json()['id']).init_router(router)
        instance._last_workflow_started_time = before_creation
        log.debug("Instance id=%s started." % (instance.id))
        return instance

    @staticmethod
    def get(router, organization, name, application=None, environment=None):
        q_filter = {"query": name, "showDestroyed": "false",
                    "sortBy": "byCreation", "descending": "true",
                    "mode": "short"}
        if application:
            q_filter["applicationFilterId"] = application.applicationId
        if environment:
            q_filter["environmentFilterId"] = environment.environmentId
        resp_json = router.get_instances(org_id=organization.organizationId, params=q_filter).json()

        def instance_not_found_pretty():
            return exceptions.NotFoundError(
                "Instance with '{0}' not found in organization {1}".format(name, organization.name))
        if type(resp_json) == dict:
            instances = [instance for g in resp_json['groups'] for instance in g['records'] if instance['name'] == name]
            if len(instances) is 0:
                raise instance_not_found_pretty()
            return Instance(organization=organization, id=instances[0]['id']).init_router(router)
        else:  # TODO: This is compatibility fix for platform < 37.1
            instances = [instance for instance in resp_json if instance['name'] == name]
            if len(instances) is 0:
                raise instance_not_found_pretty()
            return Instance(organization=organization, id=sorted(instances, key=lambda i: i["createdAt"])[-1]['id']).init_router(router)

    def ready(self, timeout=3):  # Shortcut for convinience. Timeout = 3 min (ask timeout*6 times every 10 sec)
        accepted_states = ['Launching', 'Requested', 'Executing', 'Unknown']
        return waitForStatus(instance=self, final=['Active', 'Running'],
                             accepted=accepted_states, timeout=[timeout*20, 3, 1])
        # TODO: Unknown status  should be removed

    def launching(self, timeout=3):
        accepted_states = ['Active', 'Running', 'Unknown', 'Executing']
        return waitForStatus(instance=self, final='Launching', accepted=accepted_states, timeout=[timeout*20, 3, 1])

    def failed(self, timeout=3):
        accepted_states = ['Active', 'Running', 'Unknown', 'Executing']
        return waitForStatus(instance=self, final='Error', accepted=accepted_states, timeout=[timeout*20, 3, 1])

    def running(self, timeout=3):
        if self.status in ['Active', 'Running']:
            log.debug("Instance {} is Active right now".format(self.id))
            return True
        mrut = self.get_most_recent_update_time()
        if mrut:
            self._last_workflow_started_time = time.gmtime(time.mktime(mrut) - 1)  # skips projection check
        return self.ready(timeout)

    def destroyed(self, timeout=3):  # Shortcut for convenience. Timeout = 3 min (ask timeout*6 times every 10 sec)
        accepted_states = ['Destroying', 'Active', 'Running', 'Executing', 'Unknown', 'Error']
        return waitForStatus(instance=self, final='Destroyed', accepted=accepted_states, timeout=[timeout*20, 3, 1])

    _ALL_STATES = ('Destroying', 'Active', 'Running', 'Executing', 'Unknown', 'Error', 'Requested')

    def wait_status(self, final_status, accepted_status=_ALL_STATES, timeout=3):  # Shortcut for convenience. Timeout = 3 min (ask timeout*6 times every 10 sec)
        return waitForStatus(instance=self, final=final_status, accepted=accepted_status, timeout=[timeout * 20, 3, 1])

    def run_workflow(self, name, component_path=None, parameters=None):
        if not parameters:
            parameters = {}
        log.info("Running workflow %s on instance id=%s" % (name, self.id))
        log.debug("Parameters: %s" % parameters)
        self._last_workflow_started_time = time.gmtime(time.time())
        if component_path:
            self._router.post_instance_component_workflow(org_id=self.organizationId, instance_id=self.instanceId,
                                                          component_path=component_path,
                                                          wf_name=name, data=json.dumps(parameters))
        else:
            self._router.post_instance_workflow(org_id=self.organizationId, instance_id=self.instanceId,
                                                wf_name=name, data=json.dumps(parameters))
        return True

    # alias
    run_command = run_workflow

    def schedule_workflow(self, name, timestamp, parameters=None):
        if not parameters:
            parameters = {}
        log.info("Scheduling workflow %s on instance id=%s, timestamp: %s" % (name, self.id, timestamp))
        log.debug("Parameters: %s" % parameters)
        payload = {'parameters': parameters, 'timestamp': timestamp}
        self._router.post_instance_workflow_schedule(org_id=self.organizationId, instance_id=self.instanceId,
                                                     wf_name=name, data=json.dumps(payload))
        return True

    def reschedule_workflow(self, workflow_name=None, workflow_id=None, timestamp=None):
        if workflow_name:
            workflow_id = [x['id'] for x in self.scheduledWorkflows if x['name'] == workflow_name][0]

        log.info("ReScheduling workflow %s on instance id=%s, timestamp: %s"
                 % (workflow_id, self.id, timestamp))
        payload = {'timestamp': timestamp}
        self._router.post_instance_reschedule(org_id=self.organizationId, instance_id=self.instanceId,
                                              workflow_id=workflow_id, data=json.dumps(payload))
        return True

    def get_manifest(self):
        return self._router.post_application_refresh(org_id=self.organizationId, app_id=self.applicationId).json()

    def reconfigure(self, revision=None, parameters=None, submodules=None, manifestVersion=None):
        # if no parameters are specified, use an alternative, more concise API route
        if not revision \
           and parameters is None \
           and not submodules \
           and not manifestVersion:
            resp = self._router.post_instance_reconfigure(org_id=self.organizationId, instance_id=self.instanceId)
            return resp.json()

        else:
            # note: be carefull refactoring this, or you might have unpredictable results
            # todo: private api seems requires at least presence of submodule names if exist
            payload = {'parameters': self.parameters}

            if revision:
                payload['revisionId'] = revision.id

            if submodules:
                payload['submodules'] = submodules
            if parameters is not None:
                payload['parameters'] = parameters
            if manifestVersion:
                payload['manifestVersion'] = manifestVersion

            resp = self._router.put_instance_configuration(org_id=self.organizationId, instance_id=self.instanceId,
                                                           data=json.dumps(payload))
            return resp.json()

    def rename(self, name):
        payload = json.dumps({'name': name})
        return self._router.put_instance_rename(org_id=self.organizationId, instance_id=self.instanceId, data=payload)

    def force_remove(self):
        return self._router.delete_instance_force(org_id=self.organizationId, instance_id=self.instanceId)

    def cancel_command(self):
        return self._router.post_instance_action(org_id=self.organizationId, instance_id=self.instanceId,
                                                 action="cancel")

    def star(self):
        return self._router.post_instance_action(org_id=self.organizationId, instance_id=self.instanceId,
                                                 action="star")

    def unstar(self):
        return self._router.post_instance_action(org_id=self.organizationId, instance_id=self.instanceId,
                                                 action="unstar")

    def delete(self):
        self.destroy()
        # todo: remove, if destroyed
        return True

    def destroy(self):
        log.info("Destroying instance id=%s" % self.id)
        return self.run_workflow("destroy")

    @property
    def serve_environments(self):
        return EnvironmentList(lambda: self.environments, organization=self.organization)

    def add_as_service(self, environments=None, environment_ids=None):
        merged_ids = set()
        for environment in environments or []:
            merged_ids.add(environment.environmentId)
        for environment in self.environments:  # leave existing
            merged_ids.add(environment.environmentId)
        for env_id in environment_ids or []:
            merged_ids.add(env_id)
        if not (environments or environment_ids):  # as as service in its env, when None-s
            merged_ids.add(self.environmentId)
        log.critical("env ids... = \n{}".format(json.dumps(list(merged_ids), indent=4)))
        self._router.post_instance_services(org_id=self.organizationId, instance_id=self.instanceId,
                                            data=json.dumps(list(merged_ids)))

    def remove_as_service(self, environments=None):
        if not environments:
            # Use default if not set
            environments = [self.environment, ]
        for env in environments:
            env.remove_service(self)

    @property
    def serviceId(self):
        raise AttributeError("Service is instance reference now, use instanceId")

    def get_most_recent_update_time(self):
        """
        Indicated most recent update of the instance, assumption based on:
        - if currentWorkflow exists, its startedAt time is most recent update.
        - else max of workflowHistory startedAt is most recent update.
        """
        def parse_time(t):
            if t:
                return time.gmtime(t/1000)
            return None
        try:
            if self.currentWorkflow:
                cw_started_at = self.currentWorkflow.get('startedAt')
                if cw_started_at:
                    return parse_time(cw_started_at)

            max_wf_started_at = max([i.get('startedAt') for i in self.workflowHistory])
            return parse_time(max_wf_started_at)
        except ValueError:
            return None

    def _is_projection_updated_instance(self):
        """
        This method tries to guess if instance was update since last time.
        If return True, definitely Yes, if False, this means more unknown
        :return: bool
        """
        last = self._last_workflow_started_time
        if not self._router.public_api_in_use:
            most_recent = self.get_most_recent_update_time()
        else:
            most_recent = None
        if last and most_recent:
            return last < most_recent
        return False  # can be more clever


class InstanceList(QubellEntityList):
    base_clz = Instance


class ActivityLog(object):

    TYPES = ['status updated', 'signals updated', 'dynamic links updated', 'command started', 'command finished',
             'workflow started', 'workflow finished', 'step started', 'step finished']
    log = []

    def __init__(self, log_list, severity=None, start=None, end=None):
        def sort(log_unsorted):
            # noinspection PyArgumentEqualDefault
            return sorted(log_unsorted, key=lambda li: li['time'], reverse=False)

        self.log = sort(log_list)
        self.severity = severity
        if severity:
            self.log = [x for x in self.log if x['severity'] in severity]

        if start:
            self.log = [x for x in self.log if x['time'] >= start]
        if end:
            self.log = [x for x in self.log if x['time'] <= end]

    def __len__(self):
        return len(self.log)

    def __iter__(self):
        for i in self.log:
            yield i

    def __str__(self):
        text = 'Severity: %s' % self.severity or 'ALL'
        for x in self.log:
            try:
                text += '\n{0}: {1}: {2}'.format(x['time'], x['eventTypeText'],
                                                 x['description'].replace('\n', '\n\t\t'))
            except KeyError:
                text += '\n{0}: {2}'.format(x['time'], x['description'].replace('\n', '\n\t\t'))
        return text

    def __contains__(self, item):
        try:
            self.find(item)
            return True
        except exceptions.NotFoundError:
            return False

    def __getitem__(self, item):
        """
        Guess what item to return: time, index or description
        log[0] will return first entry as string
        log[1402654329064] will return description of FIRST event with this time as string
        log['Status is Active'] will return time of event, if found.
        log[1:4] will return subset of self
        """
        stringify = lambda i: '{0}: {1}'.format(i['eventTypeText'], i['description'])
        def not_found(hint=''):
            raise exceptions.NotFoundError(
                "Activitylog item not found: '{}', due to {}".format(item, hint))

        if isinstance(item, int):
            if item > 1000000000000:  # assume time
                items = [stringify(x) for x in self.log if x['time'] == item]
                if len(items) == 0:
                    not_found('absence as time')
                return items[0]
            try:
                return stringify(self.log[item])
            except IndexError:
                not_found('absence as index')
        elif isinstance(item, str):
            return self.find(item)[0]
        elif isinstance(item, slice):
            # noinspection PyTypeChecker
            return ActivityLog(self.log[item], severity=self.severity)
        # todo: check regression logs and replace with `raise LookupError`
        log.warning("Unknown lookup method '{}' for ActivityLog".format(item))
        return False

    def find(self, item, description='', event_type=''):
        """
        Find regexp in activitylog
        find record as if type are in description.
        """
        # TODO: should be refactored, dumb logic
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
            found = [x['time'] for x in self.log if re.search(description, x['description'])
                     and x['eventTypeText'] == event_type]
        else:
            found = [x['time'] for x in self.log if re.search(description, x['description'])]

        if len(found):
            return found
        raise exceptions.NotFoundError("Item '{}' is not found with (description='{}', event_type='{}')".
                                       format(item, description, event_type))

    def get_interval(self, start_text=None, end_text=None):

        # guard
        def not_found(hint=''):
            raise exceptions.NotFoundError(
                'Activitylog interval not found: [{} , {}], due to {}'.format(start_text, end_text, hint))
        if start_text and start_text not in self:
            not_found('start_text is absent')
        if end_text and end_text not in self:
            not_found('end_text is absent')

        if start_text:
            begin = self.find(start_text)
            interval = ActivityLog(self.log, self.severity, start=begin[0])
        else:
            interval = self

        if end_text:
            end = interval.find(end_text)
            interval = ActivityLog(interval, self.severity, end=end[0])

        if len(interval):
            return interval

        not_found('nothing within boundaries')


activityLog = ActivityLog  # todo: remove this