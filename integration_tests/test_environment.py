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


class EnvironmentClassTest(BaseTestCase):
    name = 'Self-EnvironmentClassTest'

    # noinspection PyUnresolvedReferences
    def setup_once(self):
        super(EnvironmentClassTest, self).setup_once()
        self.org = self.organization
        self.app = self.org.create_application(manifest=self.manifest, name=self.name)
        self.env = self.org.create_environment(name=self.name)

    # noinspection PyUnresolvedReferences
    def teardown_once(self):
        self.env.delete()
        self.app.delete()
        super(EnvironmentClassTest, self).teardown_once()

    def test_environments_sugar(self):
        org = self.org
        env = self.env

        self.assertTrue(env in org.environments)
        self.assertEqual(org.environments[self.name], env)
        self.assertEqual(org.environments[self.name].name, env.name)
        self.assertEqual(org.environments[self.name].id, env.id)

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
        base_env = org.get_or_create_environment(name='Self-smart_environment_method')

        # Get environment
        self.assertEqual(base_env, org.environment(name='Self-smart_environment_method'))
        self.assertEqual(base_env, org.environment(id=base_env.id))
        self.assertEqual(base_env, org.environment(id=base_env.id, name='Self-smart_environment_method'))

        # Create environment
        new_environment = org.environment(name='Self-smart_environment_method-create')
        self.assertEqual('Self-smart_environment_method-create', new_environment.name)
        self.assertTrue(new_environment in org.environments)
        self.assertTrue(new_environment.delete())

        # Clean
        self.assertTrue(base_env.delete())

    def test_service_crud(self):
        env = self.env
        wf = self.org.get_instance(name="Default workflow service")
        env.add_service(wf)
        env.add_service(wf)  # operation idempotent
        assert len(env.services) == 1
        service = self.org.create_service(self.app, environment=env)
        assert len(env.services) == 2
        service.ready()
        assert service.id in env.services
        assert service.instanceId in env.services
        self.org.service(name=service.name)
        assert len(env.services) == 2
        self.org.service(service.id)
        self.org.service(service.instanceId)
        assert len(env.services) == 2
        service.destroy()
        assert service.destroyed()
        assert len(env.services) == 1  # WF still there.

    def test_replace_service_of_same_app(self):
        wf = self.org.get_instance(name="Default workflow service")
        self.env.add_service(wf)

        service = self.app.launch(environment=self.env)
        self.env.add_service(service, force=True)
        assert service in self.env.services

        service2 = self.app.launch(environment=self.env)
        self.env.add_service(service2, force=True)

        assert service2 in self.env.services
        assert service not in self.env.services

        service.destroy()
        service2.destroy()
        assert service.destroyed()
        assert service2.destroyed()

    def test_marker_crud(self):
        marker = "crud_test"
        self.env.add_marker(marker)
        assert self.marker_exists(self.env.json(), marker)
        self.env.remove_marker(marker)
        assert not self.marker_exists(self.env.json(), marker)

    def test_property_crud(self):
        property_name = "some-string"
        self.env.add_property(property_name, "string", "abc")
        assert self.property_exists(self.env.json(), property_name, "abc")
        self.env.add_property(property_name, "string", "cdf")  # edit/override
        assert self.property_exists(self.env.json(), property_name, "cdf")
        self.env.remove_property(property_name)
        assert not self.property_exists(self.env.json(), property_name)

    def test_policy_crud(self):
        self.env.add_policy({"action": "customAction", "parameter": "customParameter", "value": "foo"})
        assert self.policy_exists(self.env.json(), "customAction.customParameter", "foo")
        self.env.add_policy(action="customAction", parameter="customParameter", value="bar")  # edit/override
        assert self.policy_exists(self.env.json(), "customAction.customParameter", "bar")
        self.env.remove_policy("customAction.customParameter")
        assert not self.policy_exists(self.env.json(), "customAction.customParameter")

    def test_env_import(self):
        new_environment = self.org.create_environment(name='import-export')
        new_environment.ready()
        new_environment.import_yaml(file=os.path.join(os.path.dirname(__file__), './env_prop_pol_import.yml'))
        assert 'wcs-login' in [x['name'] for x in new_environment.json()['properties']]
        assert 'markerer' in [x['name'] for x in new_environment.json()['markers']]
        new_environment.delete()

    def test_env_bulk(self):
        with self.env as env:
            env.add_policy({"action": "bulkAction", "parameter": "bulkParameter", "value": "foo"})
            env.add_marker("bulk_marker")
            env.add_property("bulk-string", "string", "bulk")
        env_json = self.env.json()
        assert self.marker_exists(env_json, "bulk_marker")
        assert self.property_exists(env_json, "bulk-string", "bulk")
        assert self.policy_exists(env_json, "bulkAction.bulkParameter", "foo")

        with self.env as env:
            env.add_policy(action="bulkAction", parameter="bulkParameter", value="bar")
            env.add_property("bulk-string", "string", "bulk_new")
        env_json = self.env.json()
        assert self.property_exists(env_json, "bulk-string", "bulk_new")
        assert self.policy_exists(env_json, "bulkAction.bulkParameter", "bar")

        with self.env as env:
            env.remove_policy("bulkAction.bulkParameter")
            env.remove_marker("bulk_marker")
            env.remove_property("bulk-string")
        env_json = self.env.json()
        assert not self.marker_exists(env_json, "bulk_marker")
        assert not self.property_exists(env_json, "bulk-string")
        assert not self.policy_exists(env_json, "bulkAction.bulkParameter")

    def test_remove_absent_marker(self):
        self.env.remove_marker("transparent")

    def test_remove_absent_policy(self):
        self.env.remove_policy("none.none")

    def test_remove_absent_property(self):
        self.env.remove_property("ghost")

    def create_full_environment(self, name):
        environment = self.organization.create_environment(name)
        self.addCleanup(lambda: environment.delete())
        environment.init_common_services(with_cloud_account=False)
        with environment as env:
            env.add_marker("test_clone")
            env.add_property("foo", "string", "clone")
            env.add_policy(action="bar", parameter="baz", value="brr")
        return environment

    def assert_full_environment(self, env):
        assert len(env.services) == 2, "wrong number of services in env"
        env_json = env.json()
        assert self.marker_exists(env_json, "test_clone")
        assert self.property_exists(env_json, "foo", "clone")
        assert self.policy_exists(env_json, "bar.baz", "brr")


    def test_clone_environment_noname(self):
        env = self.create_full_environment("test clone unnamed")

        cloned_env = env.clone()
        self.addCleanup(lambda: cloned_env.delete())

        assert cloned_env.name.startswith("Copy of ")
        self.assert_full_environment(cloned_env)

    def test_clone_environment_custom_name(self):
        env = self.create_full_environment("test clone named")

        cloned_env = env.clone("clone name env")
        self.addCleanup(lambda: cloned_env.delete())

        assert cloned_env.name == "clone name env"
        self.assert_full_environment(cloned_env)

    # helpers

    def marker_exists(self, data, name):
        return name in [m['name'] for m in data['markers']]

    def property_exists(self, data, name, value=None):
        prop = [p for p in data['properties'] if p['name'] == name]
        if len(prop) == 0:
            return False
        elif not value:
            return True
        elif prop[0]['value'] == value:
            return True
        return False

    def policy_exists(self, data, name, value=None):
        # noinspection PyShadowingNames
        policy_name = lambda p: "{}.{}".format(p.get('action'), p.get('parameter'))
        pol = [p for p in data['policies'] if policy_name(p) == name]
        if len(pol) == 0:
            return False
        elif not value:
            return True
        elif pol[0]['value'] == value:
            return True
        return False

    def get_backend_version(self):
        assert float(self.environment.get_backend_version()) > 30.0
