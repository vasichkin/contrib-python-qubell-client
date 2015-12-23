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
from qubell.api.testing import eventually
from qubell.api.private.instance import Instance
from testtools.testcase import MismatchError


class InstanceClassTest(BaseTestCase):

    def setup_once(self):
        super(InstanceClassTest, self).setup_once()
        self.org = self.organization
        self.app = self.org.application(manifest=self.manifest, name='Self-InstanceClassTest')
        self.app.clean()
        self.ins = self.org.create_instance(application=self.app, name='Self-InstanceClassTest-Instance')
        assert self.ins.ready()

    def teardown_once(self):
        self.ins.delete()
        super(InstanceClassTest, self).teardown_once()

    def test_instances_sugar(self):
        org = self.org
        ins = self.ins

        self.assertTrue(ins in org.instances)
        self.assertEqual(org.instances['Self-InstanceClassTest-Instance'], ins)
        self.assertEqual(org.instances['Self-InstanceClassTest-Instance'].name, ins.name)
        self.assertEqual(org.instances['Self-InstanceClassTest-Instance'].id, ins.id)
        self.assertEqual(org.instances['Self-InstanceClassTest-Instance'].status, 'Active')

        for x in org.instances:
            self.assertTrue(x.name)
            self.assertEqual(x.organizationId, org.organizationId)

    def test_create_instance_method(self):
        """ Check basic instance creation works
        """
        inst = self.org.create_instance(application=self.app)
        self.assertTrue(inst.ready())
        self.assertTrue(inst in self.org.instances)
        self.assertEqual('This is default manifest', inst.returnValues['out.app_output'])

        my_inst = self.app.get_instance(id=inst.id)
        self.assertEqual(inst, my_inst)
        self.assertEqual('This is default manifest', inst.return_values['out.app_output'])

        # clean
        self.assertTrue(inst.delete())
        self.assertTrue(inst.destroyed())
        self.assertFalse(inst in self.app.instances)

    def test_list_instances_json(self):
        """ Check list_instances method contains our instance
        """
        instance_list = self.app.list_instances_json()
        self.assertTrue(self.ins.id in [x['id'] for x in instance_list])
        instance_list = self.org.list_instances_json()
        self.assertTrue(self.ins.id in [x['id'] for x in instance_list])

    def test_get_instance_from_org(self):
        """ Check ways we can get existing instance
        """
        ins = self.ins
        org = self.org
        app = self.app

        self.assertEqual(ins, app.get_instance(id=ins.id))
        self.assertEqual(ins, app.get_instance(name=ins.name))
        self.assertEqual(ins, org.get_instance(name=ins.name))
        self.assertEqual(ins, org.get_instance(id=ins.id))

    def test_get_instance_independently(self):
        """ Check ways we can get existing instance
        """
        ins = self.ins

        self.assertEqual(ins, Instance(self.org, ins.id))

    def test_get_or_launch_instance_method(self):
        ins = self.ins
        org = self.org

        # Get tests
        self.assertEqual(ins, org.get_or_launch_instance(id=ins.id))
        self.assertEqual(ins, org.get_or_launch_instance(name=ins.name))

        # Create tests
        my = org.get_or_launch_instance(name='Self-test_get_or_launch_instance',
                                        application=self.app, destroyInterval=100000)
        self.assertTrue(my.id)
        self.assertTrue(my.ready())
        self.assertTrue(my in org.instances)
        self.assertEqual('Self-test_get_or_launch_instance', my.name)
        self.assertTrue(my.delete())

        my = org.get_or_launch_instance(application=self.app, destroyInterval=100000)
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

    def test_activity_log(self):
        ins = self.ins

        all_logs = ins.activitylog
        info_logs = ins.get_activitylog(severity='INFO')

        for log in info_logs:
            assert log['severity'] == 'INFO'

        assert 'Active' in info_logs
        self.assertRegexpMatches(all_logs[0], r'command started: launch by (?:\(.*\))?.*')

        @eventually(AssertionError, MismatchError)
        def assert_eventually():
            # Last line could be one og this.
            self.assertTrue(all_logs[-1] == 'status updated: Active' or
                            all_logs[-1] == 'command finished: launch' or
                            all_logs[-1] == 'signals updated: This is default manifest')
        assert_eventually()

        @eventually(AssertionError, MismatchError)
        def assert_eventually():
            # example: 'command started: launch by Ivan Ivanov: in.app_input: This is default manifest'
            self.assertRegexpMatches(info_logs[0], r'command started: launch by (?:\(.*\))?.*')
            assert 'workflow started: launch' in info_logs
            assert 'signals updated: This is default manifest' in all_logs
            assert 'This is default manifest' in all_logs
        assert_eventually()

        interval = info_logs.get_interval(start_text="workflow started: launch",
                                          end_text="workflow finished: launch with status \'Succeeded\'")
        # there could be 3 or 4 messages
        self.assertTrue(len(interval) in [2, 3, 4], interval)
