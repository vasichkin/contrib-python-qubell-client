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
__email__ = "vkhomenko@qubell.com"

import os
import logging as log

import testtools
import nose.plugins.attrib

from qubell.api.private.platform import QubellPlatform
from qubell.api.private.common import Auth

from qubell.api.private.manifest import Manifest
from qubell.api.tools import retry
from qubell.api.private.service import COBALT_SECURE_STORE_TYPE, WORKFLOW_SERVICE_TYPE, SHARED_INSTANCE_CATALOG_TYPE

log.getLogger().setLevel(log.DEBUG)


def attr(*args, **kwargs):
    """A decorator which applies the nose and testtools attr decorator
    """
    def decorator(f):
        f = testtools.testcase.attr(args)(f)
        if not 'skip' in args:
            return nose.plugins.attrib.attr(*args, **kwargs)(f)
        # TODO: Should do something if test is skipped
    return decorator

def eventually(*exceptions):
    """
    Method decorator, that waits when something inside eventually happens
    Note: 'sum([delay*backoff**i for i in range(tries)])' ~= 580 seconds ~= 10 minutes
    :param exceptions: same as except parameter, if not specified, valid return indicated success
    :return:
    """
    return retry(tries=50, delay=0.5, backoff=1.1, retry_exception=exceptions)


parameters = {
    'organization': os.getenv('QUBELL_ORGANIZATION', "selfcheck_organization_name"),
    'user': os.environ['QUBELL_USER'],
    'pass': os.environ['QUBELL_PASSWORD'],
    'tenant': os.environ['QUBELL_TENANT'],
    'provider_name': os.getenv('PROVIDER_NAME', "selfcheck_provider_name"),
    'provider_type': os.environ.get('PROVIDER_TYPE', 'aws-ec2'),
    'provider_identity': os.environ.get('PROVIDER_IDENTITY', 'No PROVIDER_IDENTITY'),
    'provider_credential': os.environ.get('PROVIDER_CREDENTIAL', 'PROVIDER_CREDENTIAL'),
    'provider_region': os.environ.get('PROVIDER_REGION', 'us-east-1'),
}
zone = os.environ.get('QUBELL_ZONE')

class BaseTestCase(testtools.TestCase):
    parameters=parameters
    ## TODO: Main preparation should be here
    """ Here we prepare global env. (load config, etc)
    """
    # Set default manifest for app creation
    manifest = Manifest(file=os.path.join(os.path.dirname(__file__), './default.yml'), name='BaseTestManifest')
    platform = QubellPlatform.connect(user=parameters['user'], password=parameters['pass'], tenant=parameters['tenant'])

    @classmethod
    def setUpClass(cls):
    # Initialize organization
        if os.getenv("QUBELL_IT_LOCAL"):
            cls.parameters['organization'] = cls.__name__
        cls.organization = cls.platform.organization(name=cls.parameters['organization'])

        if zone:
            z = [x for x in cls.organization.list_zones() if x['name'] == zone]
            if z:
                cls.organization.zoneId = z[0]['id']


    # Initialize environment
        if zone:
            cls.environment = cls.organization.environment(name='default', zone=cls.organization.zoneId)
            cls.environment.set_backend(cls.organization.zoneId)
        else:
            cls.environment = cls.organization.get_environment(name='default')
        cls.environment.clean()
        cls.shared_service = cls.organization.service(name='BaseTestSharedService', type=SHARED_INSTANCE_CATALOG_TYPE, environment=cls.environment, parameters={'configuration.shared-instances':{}})
        cls.wf_service = cls.organization.service(name='Default workflow service', type=WORKFLOW_SERVICE_TYPE, environment=cls.environment)
        cls.key_service = cls.organization.service(name='Default credentials service', type=COBALT_SECURE_STORE_TYPE, environment=cls.environment)

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
    # Run before each test
        super(BaseTestCase, self).setUp()
        pass

    def tearDown(self):
    # Run after each test
        super(BaseTestCase, self).tearDown()
        pass

