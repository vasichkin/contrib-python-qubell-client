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
__version__ = "1.0.1"
__email__ = "vkhomenko@qubell.com"

from base import BaseTestCase


class ServiceClassTest(BaseTestCase):
    def setup_once(self):
        super(ServiceClassTest, self).setup_once()
        self.org = self.organization
        self.env = self.org.create_environment(name='Self-ServiceClassTest-Env')
        self.app = self.org.application(manifest=self.manifest, name='Self-ServiceClassTest')
        self.app.clean()

    def teardown_once(self):
        self.env.delete()
        super(ServiceClassTest, self).teardown_once()

    def test_create_service_method(self):
        """ Check basic service creation works
        """
        env_service = self.org.create_environment(name='Self-ServiceClassTest-ServiceEnv')
        self.addCleanup(lambda: env_service.delete())
        env_service.init_common_services(with_cloud_account=False)
        serv = self.org.create_service(application=self.app, environment=env_service)
        self.assertTrue(serv.ready())
        self.assertTrue(serv in self.org.services)
        self.assertTrue(serv in env_service.services)
        self.assertTrue(serv in self.org.instances)
        self.assertEqual('This is default manifest', serv.returnValues['out.app_output'])
        self.assertFalse(serv.destroyAt)

        my_serv = self.org.get_instance(id=serv.id)
        self.assertEqual(serv, my_serv)

        # Test Sugar
        self.assertEqual(self.org.services[my_serv.name], serv)
        self.assertEqual(self.org.services[my_serv.id].name, serv.name)
        self.assertEqual(self.org.services[my_serv.name].id, serv.id)
        self.assertEqual(self.org.services[my_serv.name].status, 'Active')

        for x in self.org.services:
            self.assertTrue(x.name)
            self.assertEqual(x.organizationId, self.org.organizationId)

        # clean
        self.assertTrue(serv.delete())
        self.assertTrue(serv.destroyed())
        self.assertFalse(serv in self.org.services)
        self.assertFalse(serv in env_service.services)

    def check_service(self, serv):
        self.assertTrue(serv.ready())
        self.assertTrue(serv in self.org.services)
        self.assertTrue(serv in self.org.instances)
        self.assertFalse(serv.destroyAt)  # Service has no destroy interval
        self.assertTrue(serv in self.env.services)

        # clean
        self.assertTrue(serv.delete())
        self.assertTrue(serv.destroyed())
        self.assertFalse(serv in self.org.services)
        self.assertFalse(serv in self.env.services)

    def test_create_keystore_service(self):
        """ Check keystore service could be created
        """
        from qubell.api.private.service import COBALT_SECURE_STORE_TYPE

        serv = self.org.create_service(type=COBALT_SECURE_STORE_TYPE, environment=self.env)
        self.check_service(serv)

    def test_create_workflow_service(self):
        """ Check workflow service could be created
        """
        from qubell.api.private.service import WORKFLOW_SERVICE_TYPE

        serv = self.org.create_service(type=WORKFLOW_SERVICE_TYPE, environment=self.env)
        self.check_service(serv)

    def test_create_shared_service(self):
        """ Check shared instance catalog service could be created
        """
        from qubell.api.private.service import SHARED_INSTANCE_CATALOG_TYPE

        serv = self.org.create_service(type=SHARED_INSTANCE_CATALOG_TYPE, environment=self.env,
                                       parameters={'configuration.shared-instances': {}})
        self.check_service(serv)

    def test_create_resource_pool_service(self):
        """ Check resource pool service could be created
        """
        from qubell.api.private.service import STATIC_RESOURCE_POOL_TYPE

        serv = self.org.create_service(type=STATIC_RESOURCE_POOL_TYPE, environment=self.env,
                                       parameters={'configuration.resources': {}})
        self.check_service(serv)

    def test_create_cloud_account_service(self):
        """ Check cloud account service could be created
        """
        from qubell.api.private.service import CLOUD_ACCOUNT_TYPE

        provider_config = {'configuration.provider': 'aws-ec2',
                           'configuration.legacy-regions': 'us-east-1',
                           'configuration.endpoint-url': '',
                           'configuration.legacy-security-group': '',
                           'configuration.identity': 'TEST_IDENT',
                           'configuration.credential': 'TEST_CRED'}
        serv = self.org.create_service(type=CLOUD_ACCOUNT_TYPE, environment=self.env, parameters=provider_config)
        self.check_service(serv)
