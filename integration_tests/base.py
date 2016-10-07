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
import unittest
import os

from qubell.api.private.platform import QubellPlatform

from qubell.api.private.manifest import Manifest
from qubell.api.private.testing.setup_once import SetupOnce
from qubell.api.private.service import COBALT_SECURE_STORE_TYPE, WORKFLOW_SERVICE_TYPE, SHARED_INSTANCE_CATALOG_TYPE
from qubell.api.private.service import system_application_types


# this is required for used imports
# noinspection PyUnresolvedReferences
from qubell.api.testing import eventually, attr

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

parameters = {
    'organization': os.environ.get('QUBELL_ORGANIZATION', "selfcheck_organization_name"),
    'user': os.environ.get('QUBELL_USER'),
    'pass': os.environ.get('QUBELL_PASSWORD'),
    'tenant': os.environ.get('QUBELL_TENANT'),
    'token': os.environ.get('QUBELL_TOKEN'),
    'provider_name': os.environ.get('PROVIDER_NAME', "selfcheck_provider_name"),
    'provider_type': os.environ.get('PROVIDER_TYPE', 'aws-ec2'),
    'provider_identity': os.environ.get('PROVIDER_IDENTITY', 'No PROVIDER_IDENTITY'),
    'provider_credential': os.environ.get('PROVIDER_CREDENTIAL', 'PROVIDER_CREDENTIAL'),
    'provider_region': os.environ.get('PROVIDER_REGION', 'us-east-1'),
}
zone = os.environ.get('QUBELL_ZONE')

class BaseTestCase(SetupOnce, unittest.TestCase):
    parameters=parameters
    ## TODO: Main preparation should be here
    """ Here we prepare global env. (load config, etc)
    """
    # Set default manifest for app creation
    manifest = Manifest(file=os.path.join(os.path.dirname(__file__), './default.yml'), name='BaseTestManifest')
    platform = QubellPlatform.connect(user=parameters['user'], password=parameters['pass'], tenant=parameters['tenant'], token=parameters['token'])


    def setup_once(self):
        def type_to_app(t):
            return self.organization.applications[system_application_types.get(t, t)]
    # Initialize organization
        if os.getenv("QUBELL_IT_LOCAL"):
            self.parameters['organization'] = self.__class__.__name__
        self.organization = self.platform.organization(name=self.parameters['organization'])

        if zone:
            z = [x for x in self.organization.list_zones() if x['name'] == zone]
            if z:
                self.organization.zoneId = z[0]['id']


    # Initialize environment
        if zone:
            self.environment = self.organization.environment(name='default', zone=self.organization.zoneId)
            self.environment.set_backend(self.organization.zoneId)
        else:
            self.environment = self.organization.get_environment(name='default')

        self.shared_service = self.organization.service(name='BaseTestSharedService',
                                                        application=type_to_app(SHARED_INSTANCE_CATALOG_TYPE),
                                                        environment=self.environment,
                                                        parameters={'configuration.shared-instances': {}})
        self.wf_service, self.key_service, self.cloud_account_service = self.environment.init_common_services()
