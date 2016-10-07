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

import yaml
import simplejson as json

from qubell.api.private import exceptions
from qubell.api.tools import retry

__all__ = ['COBALT_SECURE_STORE_TYPE', 'WORKFLOW_SERVICE_TYPE', 'SHARED_INSTANCE_CATALOG_TYPE',
           'STATIC_RESOURCE_POOL_TYPE', 'CLOUD_ACCOUNT_TYPE', 'AMAZON_CLOUD_TYPE']

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

# ToDo: Move to Globals

COBALT_SECURE_STORE_TYPE = 'builtin:cobalt_secure_store'
WORKFLOW_SERVICE_TYPE = 'builtin:workflow_service'
SHARED_INSTANCE_CATALOG_TYPE = 'builtin:shared_instances_catalog'
STATIC_RESOURCE_POOL_TYPE = 'builtin:static_resource_pool'
CLOUD_ACCOUNT_TYPE = 'builtin:cloud_account'
AMAZON_CLOUD_TYPE = 'builtin:amazon_account'
GCE_CLOUD_TYPE = 'builtin:GCE_account'

system_application_types = {COBALT_SECURE_STORE_TYPE: 'Secure Vault 2.0', WORKFLOW_SERVICE_TYPE: 'Workflow Service',
                            SHARED_INSTANCE_CATALOG_TYPE: 'Shared Instances Catalog',
                            STATIC_RESOURCE_POOL_TYPE: 'Resource Pool',
                            CLOUD_ACCOUNT_TYPE: 'Cloud Account',
                            AMAZON_CLOUD_TYPE: 'Amazon Account',
                            GCE_CLOUD_TYPE:'GCE Account'}

system_application_parameters = {
    COBALT_SECURE_STORE_TYPE: None,
    WORKFLOW_SERVICE_TYPE: None,
    SHARED_INSTANCE_CATALOG_TYPE: 'configuration.shared-instances',
    STATIC_RESOURCE_POOL_TYPE: 'configuration.resources'}

SHARED_INSTANCES_PARAMETER_NAME = system_application_parameters[SHARED_INSTANCE_CATALOG_TYPE]


# noinspection PyUnresolvedReferences
class ServiceMixin(object):
    def regenerate(self):
        return self._router.post_service_generate(org_id=self.organizationId, instance_id=self.instanceId).json()

    def list_keys(self):
        return self._router.get_service_keys(org_id=self.organizationId, instance_id=self.instanceId).json()

    def get_public_key(self, key_id=None):
        if not key_id:
            key_id = self.userData['defaultKey']
        return self._router.get_service_public_key(org_id=self.organizationId,
                                                   instance_id=self.instanceId, key_id=key_id).text

    def add_shared_instance(self, revision, instance):
        payload = json.dumps({"revisionNameId": revision.nameId,
                              "instanceId": instance.instanceId})
        self._router.post_instance_shared(org_id=self.organizationId, env_id=instance.environment.id, data=payload)

        # noinspection PyArgumentEqualDefault
        @retry(5, 1, 2)
        def wait_config_propagate():
            return self.get_shared_instance_id(revision.nameId) == instance.instanceId
        wait_config_propagate()

    def get_shared_instance_id(self, revision):
        payload = json.dumps({"arguments": {"revision": revision}, "includeIntermediate": False})
        result = self._router.post_service_command(org_id=self.organizationId, instance_id=self.instanceId,
                                                   command_name="strategy.get-shared-instance", data=payload)
        return json.loads(result.content)[0].get("instance")

    def remove_shared_instance(self, instance):
        params = self.parameters
        if SHARED_INSTANCES_PARAMETER_NAME in params:
            # noinspection PyBroadException
            try:
                # Param could contain invalid yaml
                old = yaml.safe_load(params[SHARED_INSTANCES_PARAMETER_NAME])
            except:
                old = params[SHARED_INSTANCES_PARAMETER_NAME]
            if instance.instanceId in old.values():
                val = [x for x, y in old.items() if y == instance.instanceId]
                del old[val[0]]
            else:
                raise exceptions.ApiError(
                    "Unable to find shared instance %s in catalog '%s'" % (instance.instanceId, self.name))
            params[SHARED_INSTANCES_PARAMETER_NAME] = yaml.safe_dump(old, default_flow_style=False)
            self.reconfigure(parameters=params)
        else:
            raise exceptions.ApiError(
                "Unable to remove shared instance %s from catalog '%s'. No shared instances configured." % (
                    instance.name, self.name))

    def list_shared_instances(self):
        return yaml.safe_load(self.parameters[SHARED_INSTANCES_PARAMETER_NAME])

    @property
    def is_secure_vault(self):
        raw = self.json()
        if 'templateId' in raw:
            return raw['templateId'] == COBALT_SECURE_STORE_TYPE
        return False

    def request_upload_secret(self, secret_id):
        """
        :return: json with "keyId" as secret and "url" for posting key
        """
        return self._router.post_request_upload_secret(org_id=self.organizationId,
                                                       instance_id=self.instanceId,
                                                       secret_id=secret_id).json()
