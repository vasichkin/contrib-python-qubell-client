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


class HierarchicalAppTest(base.BaseTestCase):
    _multiprocess_can_split_ = True
    #_multiprocess_shared_ = True

    @classmethod
    def setUpClass(cls):
        super(HierarchicalAppTest, cls).setUpClass()

    # Create applications for tests
        cls.parent = cls.organization.application(name="%s-test-hierapp-parent" % cls.prefix, manifest=cls.manifest)
        cls.child_one = cls.organization.application(name="%s-test-hierapp-child-one" % cls.prefix, manifest=cls.manifest)
        cls.child_two = cls.organization.application(name="%s-test-hierapp-child-two" % cls.prefix, manifest=cls.manifest)
        cls.child_three = cls.organization.application(name="%s-test-hierapp-child-tree" % cls.prefix, manifest=cls.manifest)

    # Create shared instance ONE to use in tests
        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), 'child.yml'))
        mnf.patch('application/components/child_app/configuration/configuration.workflows/launch/return/own/value', 'Child1 Ahoy!')
        cls.child_one.upload(mnf)
        cls.child_one_instance = cls.child_one.launch(destroyInterval=600000)
        assert cls.child_one_instance
        assert cls.child_one_instance.ready()
        cls.child_one_revision = cls.child_one.create_revision(name='%s-tests-basic-hierapp-shared-one' % cls.prefix, instance=cls.child_one_instance)


    # Create shared instance Two to use in tests
        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), 'child.yml'))
        mnf.patch('application/components/child_app/configuration/configuration.workflows/launch/return/own/value', 'Child2 Welcomes you')
        cls.child_two.upload(mnf)
        cls.child_two_instance = cls.child_two.launch(destroyInterval=600000)
        assert cls.child_two_instance
        assert cls.child_two_instance.ready()
        cls.child_two_revision = cls.child_two.create_revision(name='%s-tests-basic-hierapp-shared-two' % cls.prefix, instance=cls.child_two_instance)

        #cls.shared_service = cls.organization.create_shared_service(name='%s-HierarchicalAppTest-instance' % cls.prefix)
        cls.shared_service.add_shared_instance(cls.child_one_revision, cls.child_one_instance)
        cls.shared_service.add_shared_instance(cls.child_two_revision, cls.child_two_instance)


    # Create non shared instance Three to use in tests
        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), 'child.yml'))
        mnf.patch('application/components/child_app/configuration/configuration.workflows/launch/return/own/value', 'Child3 raises hands')
        cls.child_three.upload(mnf)
        cls.child_three_instance = cls.child_three.launch(destroyInterval=600000)
        assert cls.child_three_instance
        assert cls.child_three_instance.ready()

    @classmethod
    def tearDownClass(cls):
    # Remove created services
        cls.shared_service.remove_shared_instance(instance=cls.child_one_instance)
        cls.shared_service.remove_shared_instance(instance=cls.child_two_instance)

    # Clean apps
        cls.child_one_instance.delete()
        assert cls.child_one_instance.destroyed()
        cls.child_two_instance.delete()
        assert cls.child_two_instance.destroyed()
        cls.child_three_instance.delete()
        assert cls.child_three_instance.destroyed()
        #cls.parent.clean()
        #cls.child_one.clean()
        #cls.child_two.clean()
        #cls.child_three.clean()

        cls.parent.delete()
        cls.child_one.delete()
        cls.child_two.delete()
        cls.child_three.delete()
        super(HierarchicalAppTest, cls).tearDownClass()

    @attr('smoke')
    def test_launch_basic_non_shared_hierapp(self):
        """ Launch hierarchical app with child as not shared instance. Check that launching parent launches child instance.
        """
        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "parent_child1.yml")) #Todo: resolve paths
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.child_three.applicationId)
        self.parent.upload(pmnf)
        parent_instance = self.parent.launch(destroyInterval=300000)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        self.assertNotEqual(parent_instance.submodules[0]['id'], self.child_three_instance.instanceId)

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))


    def test_launch_hierapp_shared_instance(self):
        """ Launch hierarchical app with shared instance.
        """

        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "parent_child1.yml")) #Todo: resolve paths
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.child_one.applicationId)

        parameters = {self.child_one.name: {'revisionId': self.child_one_revision.revisionId}}

        # Api BUG?? TODO
        parameters = {
                "parent_in.child_input": "Hello from parent to child"}
        submodules = {
                "child": {
                    "revisionId": self.child_one_revision.revisionId}}


        self.parent.upload(pmnf)
        parent_instance = self.parent.launch(destroyInterval=600000, parameters=parameters, submodules=submodules)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        self.assertEqual(parent_instance.submodules[0]['id'], self.child_one_instance.instanceId)

        # Shouldn't be able to remove child while parent use it and should return error
        # TODO: BUG
        #self.assertFalse(child_instance.destroy())

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))


    @attr('smoke')
    def test_launch_hierapp_with_combined_child_instances(self):
        """ Launch hierarchical app with two shared and one non shared instance.
        """

        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "parent_childs.yml")) #Todo: resolve paths
        pmnf.patch('application/components/child-one/configuration/__locator.application-id', self.child_one.applicationId)
        pmnf.patch('application/components/child-two/configuration/__locator.application-id', self.child_two.applicationId)
        pmnf.patch('application/components/child-three/configuration/__locator.application-id', self.child_three.applicationId)

        # TODO: bug. Need to pass params
        parameters = {
                "parent_in.child_three_input": "Hello from parent to child3 BUG"}
        submodules = {
                "child-one": {
                    "revisionId": self.child_one_revision.revisionId},
                "child-two": {
                    "revisionId": self.child_two_revision.revisionId}}


        self.parent.upload(pmnf)
        parent_instance = self.parent.launch(destroyInterval=600000, parameters=parameters, submodules=submodules)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        sub = parent_instance.submodules

        self.assertTrue(len([sid for sid in sub if sid['id'] == self.child_one_instance.instanceId]))  # Way i search for id
        self.assertTrue(len([sid for sid in sub if sid['id'] == self.child_two_instance.instanceId]))
        self.assertFalse(len([sid for sid in sub if sid['id'] == self.child_three_instance.instanceId]))


        # Shouldn't be able to remove child while parent use it and should return error
        # TODO: BUG
        #self.assertFalse(child_instance.destroy())

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
