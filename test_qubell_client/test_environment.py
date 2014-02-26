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

import os

from base import BaseTestCase
from qubell.api.private.manifest import Manifest


class EnvironmentClassTest(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(EnvironmentClassTest, cls).setUpClass()
        cls.org = cls.organization
        cls.app = cls.org.create_application(manifest=cls.manifest, name='Self-EnvironmentClassTest')
        cls.env = cls.org.create_environment(name='Self-EnvironmentClassTest')

    @classmethod
    def tearDownClass(cls):
        cls.env.delete()
        cls.app.delete()
        super(EnvironmentClassTest, cls).tearDownClass()


    def test_environments_sugar(self):
        org = self.org
        env = self.env

        self.assertTrue(env in org.environments)
        self.assertEqual(org.environments['Self-EnvironmentClassTest'], env)
        self.assertEqual(org.environments['Self-EnvironmentClassTest'].name, env.name)
        self.assertEqual(org.environments['Self-EnvironmentClassTest'].id, env.id)

        for x in org.environments:
            self.assertTrue(x.name)
            self.assertTrue(x.id)

    def test_environment_create_method(self):
        # Check we can create environment
        my_env = self.org.create_environment(name='Self-test_environment_create_method')
        self.assertTrue(my_env.name)
        self.assertTrue(my_env.id)
        self.assertTrue(my_env in self.org.environments)

        # check we cannot create already created application
        new_env = self.org.get_environment(id=my_env.id)
        self.assertEqual(my_env, new_env)

        self.assertTrue(self.org.delete_environment(my_env.id))


    def test_get_or_create_environment_method(self):
        org = self.org
        env = self.env
        # Get tests
        self.assertEqual(env, org.get_or_create_environment(id=env.id))
        self.assertEqual(env, org.get_or_create_environment(name=env.name))

        # Create tests
        new_env = org.get_or_create_environment(name='Self-get_or_create_environment_method')
        self.assertTrue(new_env in org.environments)
        self.assertTrue(new_env.id)
        self.assertEqual(new_env.name, 'Self-get_or_create_environment_method')
        self.assertTrue(new_env.delete())

    def test_smart_environment_method(self):
        org = self.org
        env = self.env
        base_env = org.get_or_create_environment(name='Self-smart_environment_method')

        # Get environment
        self.assertEqual(base_env, org.environment(name='Self-smart_environment_method'))
        self.assertEqual(base_env, org.environment(id=base_env.id))
        self.assertEqual(base_env, org.environment(id=base_env.id, name='Self-smart_environment_method'))

        """ TODO: check all variants
        # Modify environment
        new_name_env = org.environment(id=base_env.id, name='Self-smart_environment_method-new-name')
        self.assertEqual(base_env, new_name_env)
        self.assertEqual('Self-smart_environment_method-new-name', new_name_env.name)
        """

        # Create environment
        new_environment = org.environment(name='Self-smart_environment_method-create')
        self.assertEqual('Self-smart_environment_method-create', new_environment.name)
        self.assertTrue(new_environment in org.environments)
        self.assertTrue(new_environment.delete())


        # Clean
        self.assertTrue(base_env.delete())

    def test_service_crud(self):
        env = self.env
        initial_len = len(env.services)
        wf = self.org.get_service(name="Default workflow service")
        env.add_service(wf)
        env.add_service(wf) #operation idempotent
        assert len(env.services) == 1
        service = self.org.create_service(self.app, environment=env)
        assert len(env.services) == 2
        service.ready()
        assert service.id in env.services
        assert service.instanceId in env.services
        self.org.get_or_create_service(service.name)
        assert len(env.services) == 2
        self.org.get_or_create_service(service.id)
        self.org.get_or_create_service(service.instanceId)
        assert len(env.services) == 2
        env.remove_service(wf)
        assert len(env.services) == 1
        service.destroy()
        assert service.destroyed()
        assert len(env.services) == 0

    def test_policy_crud(self): pass

    def test_marker_crud(self): pass

    def test_property_crud(self): pass


