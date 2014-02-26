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

from qubell.api.private.platform import QubellPlatform, Auth
from qubell.api.public.platform import QubellPlatform as QubellPlatformPublic
from qubell.api.private.manifest import Manifest
from qubell.api.tools import rand
from qubell.api.provider.router import ROUTER as router

log.getLogger().setLevel(log.DEBUG)

user = os.environ.get('QUBELL_USER')
password = os.environ.get('QUBELL_PASSWORD')
tenant = os.environ.get('QUBELL_TENANT')
org = os.environ.get('QUBELL_ORGANIZATION', 'selfcheck_organization_name')
prefix = os.environ.get('QUBELL_PREFIX')
zone = os.environ.get('QUBELL_ZONE', '')
new_env = os.environ.get('QUBELL_NEW')

if not user: log.error('No username provided. Set QUBELL_USER env')
if not password: log.error('No password provided. Set QUBELL_PASSWORD env')
if not tenant: log.error('No tenant url provided. Set QUBELL_TENANT env')
if not org: log.error('No organization name provided. Set QUBELL_ORGANIZATION env')

def attr(*args, **kwargs):
    """A decorator which applies the nose and testtools attr decorator
    """
    def decorator(f):
        f = testtools.testcase.attr(args)(f)
        if not 'skip' in args:
            return nose.plugins.attrib.attr(*args, **kwargs)(f)
        # TODO: Should do something if test is skipped
    return decorator



_multiprocess_shared_ = True
class BaseTestCase(testtools.TestCase):
    ## TODO: Main preparation should be here
    """ Here we prepare global env. (load config, etc)
    """
    #_multiprocess_shared_ = True
    _multiprocess_can_split_ = True
    @classmethod
    def setUpClass(cls):
        cls.prefix = prefix or rand()
        #cls.auth = Auth(user=user, password=password, tenant=tenant)
        #cls.context_public = cls.auth

    # Initialize platform and check access
        cls.platform = QubellPlatform.connect(tenant, user, password)
        #assert cls.platform.authenticate()

        ###cls.platform_public = QubellPlatformPublic(context=cls.context_public)

    # Set default manifest for app creation
        cls.manifest = Manifest(file=os.path.join(os.path.dirname(__file__), 'default.yml'), name='BaseTestManifest')

    # Initialize organization
        cls.organization = cls.platform.organization(name=org)
        ###cls.organization_public = cls.platform_public.organization(name=org)

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
        """
        cls.environment_public = cls.organization_public.environment(id=cls.environment.environmentId)

        cls.shared_service = cls.organization.service(name='BaseTestSharedService'+zone)
        cls.wf_service = cls.organization.service(name='Workflow'+zone)
        cls.key_service = cls.organization.service(name='Keystore'+zone)

        # Cannot get services by Name (list not imlpemented)
        cls.shared_service_public = cls.organization_public.service(id=cls.shared_service.serviceId)
        cls.wf_service_public = cls.organization_public.service(id=cls.wf_service.serviceId)
        cls.key_service_public = cls.organization_public.service(id=cls.key_service.serviceId)
    """

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

