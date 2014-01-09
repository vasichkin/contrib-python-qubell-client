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

class HierappReconfiguration(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(HierappReconfiguration, cls).setUpClass()
        cls.parent_app = cls.organization.application(name="%s-reconfiguration-hierapp-parent" % cls.prefix, manifest=cls.manifest)
        cls.child_app = cls.organization.application(name="%s-reconfiguration-hierapp-child" % cls.prefix, manifest=cls.manifest)
        cls.new_child_app = cls.organization.application(name="%s-reconfiguration-hierapp-child-new" % cls.prefix, manifest=cls.manifest)

        # Prepare child
        cmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "hier-child.one.yml"))
        cls.child_app.upload(cmnf)


        # Prepare shared child
        cls.child_instance = cls.child_app.launch(destroyInterval=3000000)
        assert cls.child_instance.ready()

        # Need to specify parameters, otherwise we'll get empty revision...
        parameters = [{
      "name": "parent_in.child_input",
      "value": "Hello from parent to child"}]

        cls.child_rev = cls.child_app.create_revision(name='tests-reconf-hierapp-shared', instance=cls.child_instance,parameters=parameters)
        cls.shared_service.add_shared_instance(cls.child_rev, cls.child_instance)

        # Prepare new_child
        cmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "hier-child.two.yml"))
        cls.new_child_app.upload(cmnf)


    @classmethod
    def tearDownClass(cls):
        super(HierappReconfiguration, cls).tearDownClass()
        cls.shared_service.remove_shared_instance(cls.child_instance)
        cls.child_rev.delete()

        cls.child_instance.delete()
        assert cls.child_instance.destroyed()

        #cls.parent_app.clean()
        #cls.child_app.clean()
        #cls.new_child_app.clean()

        cls.parent_app.delete()
        cls.child_app.delete()
        cls.new_child_app.delete()


    def test_new_child_application(self):
        """ Launch hierarchical app with child as not shared instance. Change __locator and check new child launched
        """

        # Run parent with child
        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "hier-parent.yml"))
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.child_app.applicationId)

        self.parent_app.upload(pmnf)
        parent_instance = self.parent_app.launch(destroyInterval=300000)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')


        # Run parent with new_child
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.new_child_app.applicationId)
        self.parent_app.upload(pmnf)
        new_parent_instance = self.parent_app.launch(destroyInterval=300000)
        self.assertTrue(new_parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(new_parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertEqual(new_parent_instance.submodules[0]['status'], 'Running')

        new_rev = self.parent_app.create_revision(name='tests-new-child', instance=new_parent_instance)

        # Reconfigure old parent with new revision
        parent_instance.reconfigure(revisionId=new_rev.revisionId)

        # Check results
        self.assertTrue(new_parent_instance.ready(), "Instance failed to reconfigure")
        self.assertNotEqual(parent_instance.submodules[0]['id'], new_parent_instance.submodules[0]['id'])
        self.assertEqual("Child2 welcomes you", new_parent_instance.returnValues['parent_out.child_out'])

        self.assertTrue(new_rev.delete)

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
        self.assertTrue(new_parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(new_parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))



    @attr('smoke')
    def test_switch_child_shared_standalone_and_back(self):
        """ Launch hierarchical app with non shared instance. Change child to shared, check. Switch back.
        """

        # Run parent with NON shared child
        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "hier-parent.yml"))
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.child_app.applicationId)
        self.parent_app.upload(pmnf)

        parent_instance = self.parent_app.launch(destroyInterval=3000000)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))


        non_shared_rev = self.parent_app.create_revision(name='non-shared-child', instance=parent_instance)

        # Ensure we use non shared instance
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        self.assertNotEqual(parent_instance.submodules[0]['id'], self.child_instance.instanceId)

        # Reconfigure parent to use shared child
        parameters = {
            'parent_in.child_input': 'Set on reconfiguration'}
        submodules = {
            'child': {
                'revisionId': self.child_rev.revisionId}}


        self.assertTrue(parent_instance.reconfigure(parameters=parameters, submodules=submodules))

        # Check we use shared instance
        self.assertTrue(parent_instance.ready(), "Instance failed to reconfigure")
        self.assertTrue(parent_instance.submodules, 'No submodules found')
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        self.assertEqual(parent_instance.submodules[0]['id'], self.child_instance.instanceId)

        # Switch back to non shared instance
        self.assertTrue(parent_instance.reconfigure(revisionId=non_shared_rev.revisionId))

        # Check we use shared instance again
        self.assertTrue(parent_instance.ready(), "Instance failed to reconfigure")
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        self.assertNotEqual(parent_instance.submodules[0]['id'], self.child_instance.instanceId)

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
