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


# from stories import base
# from stories.base import attr
# from qubell.api.private.manifest import Manifest
# from qubell.api.private.organization import Organization
#
#
# mnf = Manifest(content="""
# application:
#   components:
#     empty:
#       type: cobalt.common.Constants
#       interfaces:
#         int1:
#           pin1: publish-signal(string)
#       configuration:
#         configuration.values:
#           int1.pin1: "HIHIHI"
# """)
#
# class InstanceTest(base.BaseTestCase):
#
#     @classmethod
#     def setUpClass(cls):
#         super(InstanceTest, cls).setUpClass()
#         cls.org = cls.organization
#
#
#     def setUp(self):
#         super(InstanceTest, self).setUp()
#
#     def tearDown(self):
#         super(InstanceTest, self).tearDown()
#
#     def teRRRst_organization_create(self):
#         org = Organization(self.context)
#         self.assertTrue(org.name)
#         self.assertTrue(org.organizationId)
#
#     @attr('smoke')
#     def test_smoke(self):
#
#         print "Smoke TESTS"
#
#     @attr('long','smoke')
#     def test_long_smoke(self):
#         print "LONG SMOKE TESTS"
#
#
#     @attr('long')
#     def test_long(self):
#         print "LOnG TESTS"
#
#     @attr('skip')
#     def test_long(self):
#         print "SHOULD NOT SEE IT"
#
#
#     @attr('skip')
#     def test_application_create(self):
#         app = self.org.application(manifest=mnf)
#         self.assertTrue(app.name)
#         self.assertTrue(app.applicationId)
#
#         self.assertTrue(app.delete())
#         self.assertFalse(app.applicationId in self.org.json())
#     @attr('skip')
#     def test_revision_create(self):
#         app = self.org.application(manifest=mnf)
#
#         instance = app.launch(destroyInterval=600000)
#         self.assertTrue(instance.ready())
#
#         revision = app.create_revision(name='test-revision-create', instance=instance)
#
#         self.assertTrue(revision)
#         self.assertTrue(app.clean())
#         self.assertTrue(instance.destroyed())
#         self.assertTrue(app.delete())
#
#     @attr('skip')
#     def test_marker_crud(self):
#         self.assertTrue(self.environment.markerAdd('TEST-MARKER'))
#         self.assertEqual(self.environment.json()['markers'][0]['name'], 'TEST-MARKER')
#         self.assertTrue(self.environment.markerRemove('TEST-MARKER'))
#     @attr('skip')
#     def test_property_crud(self):
#         self.assertTrue(self.environment.propertyAdd(name='test-name', type='string', value='TEST-PROPERTY'))
#         self.assertEqual(self.environment.json()['properties'][0]['name'], 'test-name')
#         self.assertEqual(self.environment.json()['properties'][0]['value'], 'TEST-PROPERTY')
#         self.assertTrue(self.environment.propertyRemove('test-name'))
#
#     def test_service_crud(self):
#         service = self.organization.service.create(name="KEYSTORE", )
#
#
# if __name__ == '__main__':
#     unittest.main()
