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


class OrganizationClassTest(BaseTestCase):

    def test_organizations_sugar(self):
        platform = self.platform
        org = self.organization
        name = self.organization.name

        self.assertTrue(org in platform.organizations)
        self.assertEqual(platform.organizations[name], org)
        self.assertEqual(platform.organizations[name].name, org.name)
        self.assertEqual(platform.organizations[name].id, org.id)

        for x in platform.organizations:
            self.assertTrue(x.name)

    def test_get_or_create_organization_method(self):
        org = self.organization
        platform = self.platform
        # Get tests
        self.assertEqual(org, platform.get_or_create_organization(id=org.id))
        self.assertEqual(org, platform.get_or_create_organization(name=org.name))

    def test_current_user_info(self):
        org = self.organization
        self.assertTrue(org.current_user['name'])
        self.assertEqual(org.current_user['roles'], ["Administrator", "Guest"])
