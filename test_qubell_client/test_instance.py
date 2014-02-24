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
from qubell.api.private.instance import Instance


class InstanceClassTest(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(InstanceClassTest, cls).setUpClass()
        cls.org = cls.organization
        cls.app = cls.org.application(manifest=cls.manifest, name='Self-InstanceClassTest')
        cls.ins = cls.org.create_instance(application=cls.app, name='Self-InstanceClassTest-Instance', parameters={'destroyInterval':300000})
        assert cls.ins.ready()

    @classmethod
    def tearDownClass(cls):
        cls.ins.delete()
        super(InstanceClassTest, cls).tearDownClass()

    def test_instances_sugar(self):
        org = self.org
        ins = self.ins

        self.assertTrue(ins in org.instances)
        self.assertEqual(org.instances['Self-InstanceClassTest-Instance'], ins)
        self.assertEqual(org.instances['Self-InstanceClassTest-Instance'].name, ins.name)
        self.assertEqual(org.instances['Self-InstanceClassTest-Instance'].id, ins.id)

        for x in org.instances:
            self.assertEqual(x.status, 'Running')
            self.assertEqual(x.organizationId, org.organizationId)

    def test_create_instance_method(self):
        """ Check basic instance creation works
        """
        inst = self.org.create_instance(application=self.app)
        self.assertTrue(inst.ready())
        self.assertTrue(inst in self.org.instances)
        self.assertEqual('This is default manifest', inst.returnValues['out.app_output'])

        # check we cannot create already created instance
        my_inst = self.org.get_instance(application=self.app, id=inst.id).create(application=self.app)
        self.assertEqual(inst, my_inst)

        # clean
        self.assertTrue(inst.delete())
        self.assertFalse(inst in self.app.instances)

    def test_list_instances_json(self):
        """ Check list_instances method contains our instance
        """

        list = self.app.list_instances_json()
        self.assertTrue(self.ins.id in [x['id'] for x in list])
        list = self.org.list_instances_json()
        self.assertTrue(self.ins.id in [x['id'] for x in list])

    def test_get_instance_from_org(self):
        """ Check ways we can get existing instance
        """
        ins = self.ins
        org = self.org

        self.assertEqual(ins, org.get_instance(application=self.app, id=ins.id))
        self.assertEqual(ins, org.get_instance(application=self.app, name=ins.name))
        self.assertEqual(ins, org.get_instance(name=ins.name))
        self.assertEqual(ins, org.get_instance(id=ins.id))

    def test_get_instance_independently(self):
        """ Check ways we can get existing instance
        """
        ins = self.ins

        self.assertEqual(ins.id, Instance(auth=self.auth, organization=self.org).by_name(ins.name).id)
        self.assertEqual(ins.name, Instance(auth=self.auth, organization=self.org).by_id(ins.id).name)
        self.assertEqual(ins.name, Instance(auth=self.auth, organization=self.org, id=ins.id).name)

    def test_get_or_launch_instance_method(self):
        ins = self.ins
        org = self.org

        # Get tests
        self.assertEqual(ins, org.get_or_launch_instance(id=ins.id))
        self.assertEqual(ins, org.get_or_launch_instance(name=ins.name))

        # Create tests
        my = org.get_or_launch_instance(name='Self-test_get_or_launch_instance', application=self.app, parameters={'destroyInterval':100000})
        self.assertTrue(my.id)
        self.assertTrue(my.ready())
        self.assertTrue(my in org.instances)
        self.assertEqual('Self-test_get_or_launch_instance', my.name)
        self.assertTrue(my.delete())

        my = org.get_or_launch_instance(application=self.app, parameters={'destroyInterval':100000})
        self.assertTrue(my.id)
        self.assertTrue(my.ready())
        self.assertTrue(my in org.instances)
        self.assertTrue(my.delete())

    def test_smart_instance_method(self):
        org = self.org
        app = self.app
        base_inst = org.get_or_launch_instance(application=app, name='Self-smart_instance_method')
        self.assertTrue(base_inst.ready)

        # get instance
        self.assertEqual(base_inst, org.instance(name='Self-smart_instance_method'))
        self.assertEqual(base_inst, org.instance(id=base_inst.id))
        self.assertEqual(base_inst, org.instance(id=base_inst.id, name='Self-smart_instance_method'))

        # modify instance
        new_name_inst = org.instance(id=base_inst.id, name='Self-smart_instance_method-new-name')
        self.assertTrue(new_name_inst.ready)
        self.assertEqual(base_inst, new_name_inst)
        self.assertEqual('Self-smart_instance_method-new-name', new_name_inst.name)

        # Create instance
        new_instance = org.instance(name='Self-smart_instance_method-create', application=app)
        self.assertTrue(new_instance.ready)
        self.assertNotEqual(base_inst, new_instance)
        self.assertEqual('Self-smart_instance_method-create', new_instance.name)
        self.assertTrue(new_instance in org.instances)
        self.assertTrue(new_instance.delete())

        self.assertTrue(base_inst.delete())

    """
    def test_instance_launch_as_service(self):
        inst = self.org.create_instance(application=self.app, parameters={'asService': True})
        self.assertTrue(inst.ready())
        self.assertTrue(inst in self.org.instances)
        self.assertEqual('This is default manifest', inst.returnValues['out.app_output'])

        #SERVICE checks
        # TODO: Should be flag in api
        #self.assertTrue(inst.isService)
        servs = [serv for serv in self.environment.list_services() if serv['name'] == inst.name]
        # Check we found at least one instance with that name in environment
        self.assertTrue(len(servs))

        self.assertTrue(self.app.delete_instance(inst.instanceId))
    """