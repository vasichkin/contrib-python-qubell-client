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
PUT     /organizations/:id.json                                                     boot.Boot.organizations.rename(id: String)
PUT     /organizations/:id                                                          boot.Boot.organizations.rename(id: String)
PUT     /organizations/:id/defaultEnvironment.json                                  boot.Boot.organizations.setDefaultEnvironment(id)
PUT     /organizations/:id/defaultEnvironment                                       boot.Boot.organizations.setDefaultEnvironment(id)

GET     /organizations/:id/dashboard                                                boot.Boot.organizations.dashboard(id: String)
GET     /organizations/:id/dashboard.json                                           boot.Boot.organizations.dashboard(id: String)
POST    /organizations/:id/stripeId/:stripeToken.json                               boot.Boot.organizations.paymentFormSubmit(id, stripeToken)
GET     /organizations/:id/paymentDetails$ctype<(\.json)?>                          boot.Boot.organizations.paymentDetails(id, ctype)

GET     /organizations/:id/users$ctype<(\.json)?>                boot.Boot.organizations.listMembers(id, ctype)
DELETE  /organizations/:id/users/:userId.json                    boot.Boot.organizations.evictUser(id, userId)
DELETE  /organizations/:id/users/:userId                         boot.Boot.organizations.evictUser(id, userId)
PUT     /organizations/:id/users/:userId.json                    boot.Boot.organizations.setUserRoles(id, userId)
PUT     /organizations/:id/users/:userId                         boot.Boot.organizations.setUserRoles(id, userId)
GET     /organizations/:id/users/current$ctype<(\.json)?>        boot.Boot.organizations.getCurrentUser(id, ctype)
"""

class OrganizationClassTest(base.BaseTestCasePrivate):
    _multiprocess_can_split_ = True

    @classmethod
    def setUpClass(cls):
        super(OrganizationClassTest, cls).setUpClass()
        cls.org = cls.platform.organization(name='SELF-TEST')


    def setUp(self):
        super(OrganizationClassTest, self).setUp()

    def tearDown(self):
        super(OrganizationClassTest, self).tearDown()

    def test_application_crud(self):
        app_name = 'app-creation-test'

        # create
        app = self.org.create_application(app_name, self.manifest)
        self.assertTrue(app.name)
        self.assertTrue(app.applicationId)

        # list
        apps = self.org.list_applications()
        found_apps = [x for x in apps if x['id'] == app.applicationId]
        self.assertNotEqual(len(found_apps), 0, 'Created application not in list of applications')
        self.assertEqual(app_name, found_apps[0]['name'], 'Name of created applications differs form expected')

        # get
        new_app = self.org.get_application(app.applicationId)
        self.assertEqual(app.name, new_app.name)
        self.assertEqual(app.applicationId, new_app.applicationId)

        # get custom property
        self.assertEqual(0, app.instancesCount)

        # Smart obj
        # get by id
        new_app = self.org.application(id=app.applicationId)
        self.assertEqual(app.applicationId, new_app.applicationId)

        # delete
        self.assertTrue(self.org.delete_application(app.applicationId))
        apps = self.org.list_applications()
        found_apps = [x for x in apps if x['name'] == app_name]
        self.assertEqual(len(found_apps), 0, 'Application was not deleted')

        # create if not found
        app_name+='-new'
        app = self.org.application(name=app_name, manifest= self.manifest)
        apps = self.org.list_applications()
        found_apps = [x for x in apps if x['name'] == app_name]
        self.assertNotEqual(len(found_apps), 0, 'Cannot create app by smart obj')

        new_app = self.org.application(name=app_name)
        self.assertEqual(app.applicationId, new_app.applicationId)

        self.assertTrue(app.delete())

    def test_kservice_crud(self):
        name = 'keystore-service-creation-test'

        # create
        ksrv = self.org.create_keystore_service(name=name)
        self.assertEqual(name, ksrv.name)

        # list
        ss = [x for x in self.org.list_services() if x['name'] == ksrv.name]
        self.assertTrue(len(ss))

        # get by id
        new_srv = self.org.get_service(ksrv.serviceId)
        self.assertEqual(new_srv.name, ksrv.name)

        # get custom property
        self.assertTrue(ksrv.zoneName)

        # Smart obj
        # get by name
        new_srv = self.org.service(name=name)
        self.assertEqual(new_srv.serviceId, ksrv.serviceId)

        # get by id
        new_srv = self.org.service(id=ksrv.serviceId)
        self.assertEqual(new_srv.serviceId, ksrv.serviceId)

        # create if not found
        new_srv = self.org.service(name=name+'-new', type='builtin:cobalt_secure_store')
        self.assertNotEqual(new_srv.serviceId, ksrv.serviceId)
        self.assertTrue(new_srv.delete())

        # remove
        self.assertTrue(self.org.delete_service(ksrv.serviceId))

        ss = [x for x in self.org.list_services() if x['name'] == ksrv.name]
        self.assertFalse(len(ss))

    def test_environment_crud(self):
        name = 'env-creation-test'

        # create
        env = self.org.create_environment(name=name)
        self.assertEqual(name, env.name)
        self.assertTrue(env.environmentId)

        # list
        ss = [x for x in self.org.list_environments() if x['name'] == env.name]
        self.assertTrue(len(ss))

        # get by id
        new_env = self.org.get_environment(env.environmentId)
        self.assertEqual(new_env.name, env.name)

        # get custom property
        self.assertEqual(False, env.isStarred)

        # Smart obj
        # get by name
        new_env = self.org.environment(name=name)
        self.assertEqual(new_env.environmentId, env.environmentId)

        # get by id
        new_env = self.org.environment(id=env.environmentId)
        self.assertEqual(new_env.environmentId, env.environmentId)

        # create if not found
        new_env = self.org.environment(name=name+'-new')
        self.assertNotEqual(new_env.environmentId, env.environmentId)
        self.assertTrue(new_env.delete())

        # remove
        self.assertTrue(self.org.delete_environment(env.environmentId))

        ss = [x for x in self.org.list_environments() if x['name'] == env.name]
        self.assertFalse(len(ss))

    def test_provider_crud(self):
        name = 'provider-creation-test'
        parameters = {
              'provider': 'aws-ec2',
              'usedEnvironments': [],
              'ec2SecurityGroup': 'default',
              'providerCopy': 'aws-ec2',
              'name': 'generated-provider',
              'jcloudsIdentity': 'jcloudsIdentity',
              'jcloudsCredential': 'jcloudsCredential',
              'jcloudsRegions': 'jcloudsRegions'
            }

        # create
        prov = self.org.create_provider(name=name, parameters=parameters)
        self.assertEqual(name, prov.name)
        self.assertTrue(prov.providerId)

        # list
        ss = [x for x in self.org.list_providers() if x['name'] == prov.name]
        self.assertTrue(len(ss))

        # get by id
        new_prov = self.org.get_provider(prov.providerId)
        self.assertEqual(new_prov.name, prov.name)

        # get custom property
        self.assertTrue(prov.providerLabel)

        # Smart obj
        # get by name
        new_prov = self.org.provider(name=name)
        self.assertEqual(new_prov.providerId, prov.providerId)

        # get by id
        new_prov = self.org.provider(id=prov.providerId)
        self.assertEqual(new_prov.providerId, prov.providerId)

        # create if not found
        new_prov = self.org.provider(name=name+'-new', parameters=parameters)
        self.assertNotEqual(new_prov.providerId, prov.providerId)
        self.assertTrue(new_prov.delete())

        # remove
        self.assertTrue(self.org.delete_provider(prov.providerId))

        ss = [x for x in self.org.list_providers() if x['name'] == prov.name]
        self.assertFalse(len(ss))

    def test_wfservice_crud(self):
        name = 'workflow-service-creation-test'

        # create
        wsrv = self.org.create_workflow_service(name=name)
        self.assertEqual(name, wsrv.name)

        # list
        ss = [x for x in self.org.list_services() if x['name'] == wsrv.name]
        self.assertTrue(len(ss))

        # get by id
        new_srv = self.org.get_service(wsrv.serviceId)
        self.assertEqual(new_srv.name, wsrv.name)

        # get custom property
        self.assertTrue(wsrv.zoneName)

        # Smart obj
        # get by name
        new_srv = self.org.service(name=name)
        self.assertEqual(new_srv.serviceId, wsrv.serviceId)

        # get by id
        new_srv = self.org.service(id=wsrv.serviceId)
        self.assertEqual(new_srv.serviceId, wsrv.serviceId)

        # create if not found
        new_srv = self.org.service(name=name+'-new', type='builtin:workflow_service')
        self.assertNotEqual(new_srv.serviceId, wsrv.serviceId)
        self.assertTrue(new_srv.delete())

        # remove
        self.assertTrue(self.org.delete_service(wsrv.serviceId))

        ss = [x for x in self.org.list_services() if x['name'] == wsrv.name]
        self.assertFalse(len(ss))