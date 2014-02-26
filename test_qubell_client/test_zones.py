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


class ZonesClassTest(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(ZonesClassTest, cls).setUpClass()
        cls.org = cls.organization
        cls.zone = cls.org.get_default_zone()

    @classmethod
    def tearDownClass(cls):
        super(ZonesClassTest, cls).tearDownClass()

    def test_get_default_zone(self):
        zn = self.org.get_default_zone()
        self.assertTrue(zn in self.org.zones)
        self.assertEqual(self.org.zone.zoneId, zn.zoneId)


    def test_zones_sugar(self):
        org = self.org
        zn = self.zone

        self.assertTrue(zn in org.zones)
        self.assertEqual(org.zones['Qubell/us-east'], zn)
        self.assertEqual(org.zones['Qubell/us-east'].id, zn.id)
        self.assertEqual(org.zones['Qubell/us-east'].name, zn.name)
        self.assertEqual(org.zones['Qubell/us-east'].id, zn.id)

        for x in org.zones:
            self.assertTrue(x.name)
            self.assertTrue(x.id)

    def test_environment_create_method(self):
        # Check we can create environment
        my_env = self.org.create_environment(name='Self-test_environment_create_method')
        self.assertTrue(my_env.name)
        self.assertTrue(my_env.id)
        self.assertTrue(my_env in self.org.environments)

        same_env = self.org.get_environment(id=my_env.id)
        self.assertEqual(my_env.id, same_env.id)

        self.assertTrue(self.org.delete_environment(my_env.id))


    def test_get_or_create_environment_method(self):
        org = self.org
        env = org.defaultEnvironment
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
        env = self.org.defaultEnvironment
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
