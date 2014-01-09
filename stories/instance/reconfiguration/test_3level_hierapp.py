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

import os

from stories import base
from stories.base import attr
from qubell.api.private.manifest import Manifest
from qubell.api.private.instance import Instance


class ThreeLevelHierappReconfiguration(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(ThreeLevelHierappReconfiguration, cls).setUpClass()

    # Create applications for tests
        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), "3level-child.yml"))
        cls.last_child = cls.organization.application(name="%s-reconfiguration-3lhierapp-last_child" % cls.prefix, manifest=mnf)

        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), "3level-middle-child.yml"))
        mnf.patch('application/components/last_child/configuration/__locator.application-id', cls.last_child.applicationId)
        cls.middle_child = cls.organization.application(name="%s-reconfiguration-3lhierapp-middle-child" % cls.prefix, manifest=mnf)

        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), "3level-super-parent.yml"))
        mnf.patch('application/components/middle_child/configuration/__locator.application-id', cls.middle_child.applicationId)
        cls.parent = cls.organization.application(name="%s-reconfiguration-3lhierapp-super-parent" % cls.prefix, manifest=mnf)


    # Create shared last_child
        cls.last_child_instance = cls.last_child.launch(destroyInterval=300000)
        assert cls.last_child_instance.ready()
        cls.last_child_rev = cls.last_child.create_revision(name='tests-reconf-3l-hierapp-shared', instance=cls.last_child_instance)
        cls.shared_service.add_shared_instance(cls.last_child_rev, cls.last_child_instance)

    @classmethod
    def tearDownClass(cls):
        assert cls.last_child_instance.delete()
        assert cls.last_child_instance.destroyed()
        cls.shared_service.remove_shared_instance(cls.last_child_instance)
        cls.last_child_rev.delete()

        cls.parent.delete()
        cls.middle_child.delete()
        cls.last_child.delete()

        super(ThreeLevelHierappReconfiguration, cls).tearDownClass()

    @attr('smoke')
    def test_switch_last_child_shared_standalone_and_back(self):
        """ Launch hierarchical app with non shared instance. Change last child to shared, check. Switch back.
        """

        # Run parent with NON shared child

        parent_instance = self.parent.launch(destroyInterval=3000000)
        self.assertTrue(parent_instance, "%s-%s: Parent instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Parent instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        non_shared_rev = self.parent.create_revision(name='non-shared-child', instance=parent_instance)


        middle_instance = self.middle_child.get_instance(id=parent_instance.submodules[0]['id']) # initialize middle instance (we can only get id from parent)

        # Ensure we use non shared instance
        self.assertEqual(middle_instance.submodules[0]['status'], 'Running')
        self.assertNotEqual(middle_instance.submodules[0]['id'], self.last_child_instance.instanceId)

        # Reconfigure parent to use shared child
        parameters = {
             	'top_parent_in.last_child_input': 'UPD by test',
  		        'top_parent_in.middle_child_input': 'UPD by test'}
        submodules = {
                'middle_child': {
                    'parameters': {
                        'last_child_in.app_input': 'UPD by test',
                        'middle_child_in.app_input': 'UPD by test'},
                    'submodules':{
                        'last_child': {
                            'revisionId': self.last_child_rev.revisionId
            }}}}


        self.assertTrue(parent_instance.reconfigure(parameters=parameters, submodules=submodules))

        # Check parent instance is ok
        self.assertTrue(parent_instance.ready(), "Instance failed to reconfigure")
        self.assertTrue(parent_instance.submodules, 'No submodules found')
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')

        self.assertEqual(parent_instance.submodules[0]['id'], middle_instance.instanceId)


        # Check last child is shared
        self.assertEqual(middle_instance.submodules[0]['status'], 'Running')
        self.assertEqual(middle_instance.submodules[0]['id'], self.last_child_instance.instanceId)

        # Switch back to non shared instance
        self.assertTrue(parent_instance.reconfigure(revisionId=non_shared_rev.revisionId))

        # Check parent is ok
        self.assertTrue(parent_instance.ready(), "Instance failed to reconfigure")
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        # Check we use non-shared last child again
        last_instance = self.middle_child.get_instance(id=middle_instance.submodules[0]['id'])
        self.assertTrue(last_instance.ready())
        self.assertEqual(middle_instance.submodules[0]['status'], 'Running')
        self.assertNotEqual(middle_instance.submodules[0]['id'], self.last_child_instance.instanceId)

        self.assertTrue(parent_instance.delete(), "%s-%s: Parent instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Parent instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
