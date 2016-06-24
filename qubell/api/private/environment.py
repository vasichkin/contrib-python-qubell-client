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

import time
import logging as log
import copy
import os
import simplejson as json

from qubell.api.globals import *
from qubell.api.globals import ZoneConstants
from qubell.api.private.service import *
from qubell.api.private.service import system_application_types
from qubell.api.tools import lazyproperty, retry
from qubell.api.private import exceptions, operations
from qubell.api.private.common import QubellEntityList, Entity
from qubell.api.provider.router import InstanceRouter

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"


class Environment(Entity, InstanceRouter):
    # noinspection PyShadowingBuiltins
    def __init__(self, organization, id):
        self.organization = organization
        self.organizationId = self.organization.organizationId
        self.environmentId = self.id = id

    @lazyproperty
    def zoneId(self):
        return self.json()['backend']

    @lazyproperty
    def services(self):
        from qubell.api.private.instance import InstanceList

        return InstanceList(list_json_method=self.list_services_json, organization=self).init_router(self._router)

    @property
    def name(self):
        return self.json()['name']

    @property
    def isDefault(self):
        return self.json()['isDefault']

    def __getattr__(self, key):
        resp = self.json()
        if key not in resp:
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    @staticmethod
    def new(organization, name, router, zone_id=None, default=False):
        log.info("Creating environment: %s" % name)
        if not zone_id:
            zone_id = organization.zone.zoneId
        data = {'isDefault': default, 'name': name, 'backend': zone_id, 'organizationId': organization.organizationId}
        log.debug(data)
        resp = router.post_organization_environment(org_id=organization.organizationId, data=json.dumps(data)).json()
        env = Environment(organization, id=resp['id']).init_router(router)
        log.info("Environment created: %s (%s)" % (name, env.environmentId))
        return env

    # noinspection PyUnusedLocal
    def restore(self, config, clean=False, timeout=10):
        config = copy.deepcopy(config)
        with self as env:
            if clean:
                env.clean()
            for marker in config.pop('markers', []):
                env.add_marker(marker)
            for policy in config.pop('policies', []):
                env.add_policy(policy)
            for prop in config.pop('properties', []):
                env.add_property(**prop)
            for service in config.pop('services', []):
                instance = self.organization.get_instance(id=service.pop('id', None), name=service.pop('name'))
                env.add_service(instance)
            for component_policy in config.pop('componentPolicies', []):
                env.set_component_policy(**component_policy)
        for service in self.services:
            service.running()

    def ready(self, timeout=(20, 10, 1)):
        @retry(*timeout)  # ask status 20 times every 10 sec.
        def env_status_waiter():
            return self.isOnline
        return env_status_waiter()

    def json(self):
        return self._router.get_environment(org_id=self.organizationId, env_id=self.environmentId).json()

    def delete(self):
        self._router.delete_environment(org_id=self.organizationId, env_id=self.environmentId)
        return True

    def get_default_private_key(self):
        return self._router.get_environment_default_private_key(org_id=self.organizationId,
                                                                env_id=self.environmentId).text

    def set_as_default(self):
        data = json.dumps({'environmentId': self.id})
        return self._router.put_organization_default_environment(env_id=self.id, org_id=self.organizationId,
                                                                 data=data).json()

    def list_available_services_json(self):
        return self._router.get_environment_available_services(org_id=self.organizationId,
                                                               env_id=self.environmentId).json()

    def list_services_json(self):
        return self.json()['services']

    def _put_environment(self, data):
        # We could get 500 error here, if tests runs in parallel or strategy is not active
        try:
            return self._router.put_environment(org_id=self.organizationId, env_id=self.environmentId, data=data)
        except exceptions.ApiError:  # #4242
            from random import randint

            # noinspection PyArgumentEqualDefault
            @retry(3, 1, 1, exceptions.ApiError)
            def put_again():
                time.sleep(randint(1, 10))
                return self._router.put_environment(org_id=self.organizationId, env_id=self.environmentId, data=data)
            return put_again()

    # Operations

    def add_service(self, service, force=False):
        with self as env:
            env.add_service(service, force)

    def remove_service(self, service):
        with self as env:
            env.remove_service(service)

    def add_marker(self, marker):
        with self as env:
            env.add_marker(marker)

    def remove_marker(self, marker):
        with self as env:
            env.remove_marker(marker)

    # noinspection PyShadowingBuiltins
    def add_property(self, name, type, value):
        with self as env:
            env.add_property(name, type, value)

    set_property = add_property

    def remove_property(self, name):
        with self as env:
            env.remove_property(name)

    def clean(self):
        with self as env:
            env.clean()

    def add_policy(self, policy=None, action=None, parameter=None, value=None):
        with self as env:
            env.add_policy(policy, action, parameter, value)

    def remove_policy(self, policy_name):
        with self as env:
            env.remove_policy(policy_name)

    def set_component_policy(self, matchers, actions):
        with self as env:
            env.set_component_policy(matchers, actions)

    def remove_component_policy(self, matchers, actions):
        with self as env:
            env.set_component_policy(matchers, actions)

    # noinspection PyShadowingBuiltins
    def import_yaml(self, file, merge=False):
        data = {"merge": merge}
        if isinstance(file, basestring):
            assert os.path.exists(file)
            file = open(file)
        files = {'path': ("filename", file)}
        self._router.post_env_import(org_id=self.organizationId, env_id=self.environmentId, data=data, files=files)

    def export_yaml(self):
        return self._router.get_env_export(org_id=self.organizationId, env_id=self.environmentId).text

    def __bulk_update(self, env_operations):

        data = self.json()
        env_name = data['name']  # speedup

        policy_name = lambda policy: "{}.{}".format(policy.get('action'), policy.get('parameter'))

        def clean():
            data['serviceIds'] = []
            data['services'] = []
            log.info("Cleaning environment %s (%s)" % (env_name, self.id))

        # noinspection PyShadowingNames
        def set_policy(policy=None, action=None, parameter=None, value=None):
            if policy is None:
                assert action and parameter and value, "setting policy either action, parameter, value was not defined"
                policy = {"action": action, "parameter": parameter, "value": value}
            if policy_name(policy) in [policy_name(p) for p in data['policies']]:
                data['policies'].remove([p for p in data['policies'] if policy_name(policy) == policy_name(p)][0])
            data['policies'].append(policy)
            log.info("Adding policy {} to environment {} ({})".format(policy_name(policy), env_name, self.id))

        # noinspection PyUnusedLocal
        def remove_policy(name):
            policy = [p for p in data['policies'] if name == policy_name(p)]
            if len(policy) == 0:
                log.warn('Unable to remove policy %s. Not found.' % name)
                return
            data['policies'].remove(policy[0])
            log.info("Removing policy %s from environment %s (%s)" % (name, env_name, self.id))

        # noinspection PyShadowingNames
        def set_component_policy(matchers=list(), actions=list()):
            if len([p for p in data['componentPolicies'] if p['matchers'] == matchers]):
                data['componentPolicies'].remove([p for p in data['componentPolicies'] if p['matchers'] == matchers][0])
            data['componentPolicies'].append({'matchers': matchers, 'actions': actions})
            log.info("Adding component policy {} to environment {} ({})".format(matchers, env_name, self.id))

        def remove_component_policy(matchers):
            policy = [p for p in data['componentPolicies'] if p['matchers'] == matchers]
            if len(policy) == 0:
                log.warn('Unable to remove policy %s. Not found.' % matchers)
                return
            data['componentPolicies'].remove(policy[0])
            log.info("Removing policy %s from environment %s (%s)" % (matchers, env_name, self.id))

        def add_service(service, force=False):
            """
            :param bool force: if instance from the same application exists, it will be replaced by new service.
            """

            # remove service of the same applicationId if already in env
            if force:
                app_id = service.applicationId
                services_json = [s for s in data['services'] if 'applicationId' in s and s['applicationId'] == app_id]
                if len(services_json) > 0 \
                        and app_id == services_json[0]['applicationId'] \
                        and service.id != services_json[0]['id']:
                    from collections import namedtuple
                    FakeInstance = namedtuple("Instance", "id")  # Fake type that can be passed to remove_service
                    service_json = services_json[0]
                    wrong_service = FakeInstance(id=service_json['id'])
                    log.warn("'{}' service  from the same '{}' application found in environment and will be removed".
                             format(service_json['name'], service_json['applicationName']))
                    # noinspection PyTypeChecker
                    remove_service(wrong_service)

            if service.id not in data['serviceIds']:
                data['serviceIds'].append(service.id)
                data['services'].append(service.json())
                log.info("Adding service id=%s to environment %s (%s)" %
                         (service.id, env_name, self.id))

            if service.is_secure_vault:
                user_data = service.userData
                if 'defaultKey' in user_data:
                    key = user_data['defaultKey']
                else:
                    key = service.regenerate()['id']

                set_policy({"action": "provisionVms", "parameter": "publicKeyId", "value": key})

        def remove_service(service):
            data['serviceIds'].remove(service.id)
            data['services'] = [s for s in data['services'] if s['id'] != service.id]
            log.info("Removing service id=%s from environment %s (%s)" %
                     (service.id, env_name, self.id))

        # noinspection PyShadowingBuiltins
        def set_property(name, type, value):
            if name in [p['name'] for p in data['properties']]:
                data['properties'].remove([p for p in data['properties'] if p['name'] == name][0])
            data['properties'].append({'name': name, 'type': type, 'value': value})
            log.info("Adding property %s to environment %s (%s)" % (name, env_name, self.id))

        def remove_property(name):
            prop = [p for p in data['properties'] if p['name'] == name]
            if len(prop) == 0:
                log.warn('Unable to remove property %s. Not found.' % name)
                return
            data['properties'].remove(prop[0])
            log.info("Removing property %s from environment %s (%s)" % (name, env_name, self.id))

        def add_marker(marker):
            if {'name': marker} in data['markers']:
                log.info("Marker {} already in environment {} ({})".format(marker, env_name, self.id))
                return

            data['markers'].append({'name': marker})
            log.info("Adding marker %s to environment %s (%s)" % (marker, env_name, self.id))

        def remove_marker(marker):
            markers = [m for m in data['markers'] if m['name'] == marker]
            if len(markers) == 0:
                log.warn('Unable to remove marker %s. Not found.' % marker)
                return
            data['markers'].remove({'name': marker})
            log.info("Removing marker %s from environment %s (%s)" % (marker, env_name, self.id))

        actions = dict(clean=clean, add_policy=set_policy, remove_policy=remove_policy, add_marker=add_marker,
                       remove_marker=remove_marker, add_property=set_property, remove_property=remove_property,
                       add_service=add_service, remove_service=remove_service,
                       set_component_policy=set_component_policy, remove_component_policy=remove_component_policy)

        for operation in env_operations:
            action, args, kwargs = operation
            actions[action](*args, **kwargs)
        return self._put_environment(data=json.dumps(data)).json()

    def init_common_services(self, with_cloud_account=True, zone_name=None):
        """
        Initialize common service,
        When 'zone_name' is defined " at $zone_name" is added to service names
        :param bool with_cloud_account:
        :param str zone_name:
        :return: OR tuple(Workflow, Vault), OR tuple(Workflow, Vault, CloudAccount) with services
        """
        zone_names = ZoneConstants(zone_name)
        type_to_app = lambda t: self.organization.applications[system_application_types.get(t, t)]
        wf_service = self.organization.service(name=zone_names.DEFAULT_WORKFLOW_SERVICE,
                                               application=type_to_app(WORKFLOW_SERVICE_TYPE),
                                               environment=self)
        key_service = self.organization.service(name=zone_names.DEFAULT_CREDENTIAL_SERVICE,
                                                application=type_to_app(COBALT_SECURE_STORE_TYPE),
                                                environment=self)
        assert wf_service.running()
        assert key_service.running()
        if not with_cloud_account:
            with self as env:
                env.add_service(wf_service, force=True)
                env.add_service(key_service, force=True)
            return wf_service, key_service

        cloud_account_service = self.organization.instance(name=zone_names.DEFAULT_CLOUD_ACCOUNT_SERVICE,
                                                           application=type_to_app(CLOUD_ACCOUNT_TYPE),
                                                           environment=self,
                                                           parameters=PROVIDER_CONFIG,
                                                           destroyInterval=0)
        # Imidiate adding to env cause CA not to drop destroy interval. Known issue 6132. So, add service as instance with
        # destroyInterval set to 'never'
        assert cloud_account_service.running()

        with self as env:
            env.add_service(wf_service, force=True)
            env.add_service(key_service, force=True)
            env.add_service(cloud_account_service, force=True)
        return wf_service, key_service, cloud_account_service

    # noinspection PyMethodMayBeStatic
    def set_backend(self, zone):
        raise exceptions.ApiError("Change environment backend is not supported, since 24.x")

    def __enter__(self):
        """
        :rtype: EnvironmentOperations
        """
        self.__bulk = EnvironmentOperations()
        return self.__bulk

    # noinspection PyShadowingBuiltins,PyUnusedLocal
    def __exit__(self, type, value, traceback):
        self.__bulk.invalidate()
        self.__bulk_update(self.__bulk.operations)

    def get_backend_version(self):
        versions = dict([(x['name'], x['version']) for x in self.json()['backends']])
        if ZONE_NAME:
            return versions[ZONE_NAME]
        else:
            return versions[self.organization.get_default_zone().name]

    def clone(self, name=None):
        """
        :param name: new env name
        :rtype: Environment
        """
        resp = self._router.post_env_clone(env_id=self.environmentId, json=dict(name=name) if name else {}).json()
        return Environment(self.organization, id=resp['id']).init_router(self._router)


class EnvironmentList(QubellEntityList):
    base_clz = Environment

    @property
    def default(self):
        """
            Returns environment marked as default.
            When Zone is set marked default makes no sense, special env with proper Zone is returned.
        """
        if ZONE_NAME:
            log.info("Getting or creating default environment for zone with name '{0}'".format(DEFAULT_ENV_NAME()))
            zone_id = self.organization.zones[ZONE_NAME].id
            return self.organization.get_or_create_environment(name=DEFAULT_ENV_NAME(), zone=zone_id)

        def_envs = [env_j["id"] for env_j in self.json() if env_j["isDefault"]]

        if len(def_envs) > 1:
            log.warning('Found more than one default environment. Picking last.')
            return self[def_envs[-1]]
        elif len(def_envs) == 1:
            return self[def_envs[0]]
        raise exceptions.NotFoundError('Unable to get default environment')


@operations()
class EnvironmentOperations(object):
    def add_policy(self, policy=None, action=None, parameter=None, value=None):
        pass

    def remove_policy(self, policy_name):
        pass

    def set_component_policy(self, matchers, actions):
        pass

    def remove_component_policy(self, matchers):
        pass

    def add_marker(self, marker):
        pass

    def remove_marker(self, marker):
        pass

    # noinspection PyShadowingBuiltins
    def add_property(self, name, type, value):
        pass

    def remove_property(self, name):
        pass

    def add_service(self, service, force=False):
        pass

    def remove_service(self, service):
        pass

    def clean(self):
        pass
