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
__version__ = "1.0.13"
__email__ = "vkhomenko@qubell.com"


from stories import base
from stories.base import attr

"""
GET     /organizations$ctype<(\.json)?>                                             boot.Boot.organizations.list(ctype)
GET     /organizations/$id<[a-z0-9]*>$ctype<(\.json)?>                              boot.Boot.organizations.organizationGet(id, ctype)
POST    /organizations.json                                                         boot.Boot.organizations.create
POST    /organizations                                                              boot.Boot.organizations.create
"""

class InstanceTest(base.BaseTestCasePrivate):

    @classmethod
    def setUpClass(cls):
        super(InstanceTest, cls).setUpClass()

    def setUp(self):
        super(InstanceTest, self).setUp()

    def tearDown(self):
        super(InstanceTest, self).tearDown()

    def test_organization_crud(self):
        org_name = "ORG_CREATION_TEST"
        self.assertTrue(self.platform)
        org = self.platform.create_organization(org_name)
        self.assertTrue(org.organizationId) # org created

        orgs = self.platform.list_organizations()
        found_orgs = [x for x in orgs if x['id'] == org.organizationId]
        self.assertNotEqual(len(found_orgs), 0, 'Created organization not in list of organizations')
        self.assertEqual(org_name, found_orgs[0]['name'], 'Name of created organization differs form expected')

        new_org = self.platform.get_organization(org.organizationId)
        self.assertEqual(org.organizationId, new_org.organizationId, 'Cannot get organization by ID')
        self.assertEqual(org.name, new_org.name, 'Cannot get organization by ID')

        new_org = self.platform.organization(id = org.organizationId)
        self.assertEqual(org.organizationId, new_org.organizationId, 'Cannot get organization by id via smart obj')

        org_name+='-new'
        org = self.platform.organization(name=org_name)

        orgs = self.platform.list_organizations()
        found_orgs = [x for x in orgs if x['name'] == org_name]
        self.assertNotEqual(len(found_orgs), 0, 'Cannot create org by smart obj')

        new_org = self.platform.organization(name = org.name)
        self.assertEqual(org.organizationId, new_org.organizationId, 'Created organization not match found by name')
