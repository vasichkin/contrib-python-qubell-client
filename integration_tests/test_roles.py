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


class RolesClassTest(BaseTestCase):

    def test_create_role_method(self):
        """ Check basic role creation/deletion works
        """
        self.org = self.organization

        role = self.organization.create_role(name="role-creation-test", permissions="- CreateApplication:\n  - /*")

        self.assertTrue(role in self.org.roles)

        my_role = self.org.get_role(id=role.id)
        self.assertEqual(role, my_role)

        my_role = self.org.get_role(name=role.name)
        self.assertEqual(role, my_role)

        # Test Sugar
        self.assertEqual(self.org.roles[my_role.name], role)
        self.assertEqual(self.org.roles[my_role.id].name, role.name)
        self.assertEqual(self.org.roles[my_role.name].id, role.id)

        for x in self.org.roles:
            self.assertTrue(x.name)
            self.assertEqual(x.organizationId, self.org.organizationId)

        self.assertEqual("- CreateApplication:\n  - /*", role.permissions)
        role.update(name="role-creation-test-renamed", permissions="- EditEnvironment:\n  - /*")
        self.assertEqual("- EditEnvironment:\n  - /*", role.permissions)
        self.assertEqual("role-creation-test-renamed", role.name)

        # clean
        self.assertTrue(role.delete())
        self.assertFalse(role in self.org.roles)
