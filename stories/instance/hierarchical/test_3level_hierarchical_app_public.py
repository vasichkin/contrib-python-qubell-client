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


class ThreeLevelHierarchicalAppTest(base.BaseTestCase):
    _multiprocess_can_split_ = True
    #_multiprocess_shared_ = True

    @classmethod
    def setUpClass(cls):
        super(ThreeLevelHierarchicalAppTest, cls).setUpClass()

    # Create applications for tests
        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), "child.yml"))
        cls.last_child = cls.organization.application(name="%s-test-3lhierapp-last_child" % cls.prefix, manifest=mnf)
        cls.last_child_public = cls.organization_public.get_application(id=cls.last_child.applicationId)

        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), "middle_child.yml"))
        mnf.patch('application/components/last_child/configuration/__locator.application-id', cls.last_child.applicationId)
        cls.middle_child = cls.organization.application(name="%s-test-3lhierapp-middle-child" % cls.prefix, manifest=mnf)
        cls.middle_child_public = cls.organization_public.get_application(id=cls.middle_child.applicationId)

        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), "super_parent.yml"))
        mnf.patch('application/components/middle_child/configuration/__locator.application-id', cls.middle_child.applicationId)
        cls.parent = cls.organization.application(name="%s-test-3lhierapp-super-parent" % cls.prefix, manifest=mnf)
        cls.parent_public = cls.organization_public.get_application(id=cls.parent.applicationId)


    @classmethod
    def tearDownClass(cls):
        super(ThreeLevelHierarchicalAppTest, cls).tearDownClass()

        cls.parent.delete()
        cls.middle_child.delete()
        cls.last_child.delete()


    @attr('smoke')
    def test_launch_basic_non_shared_3level_hierapp(self):
        """ Launch hierarchical app with childs as not shared instance. Check that launching parent launches all childs instance.
        """

        parent_instance = self.parent_public.launch(destroyInterval=300000)
        self.assertTrue(parent_instance, "%s-%s: Parent instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Parent instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        # Check submodule exists
        self.assertTrue(len(parent_instance.components))
        self.assertTrue(parent_instance.components[0]['instanceId'])
        middle_child_instance = self.middle_child_public.get_instance(id=parent_instance.components[0]['instanceId'])

        self.assertEqual(middle_child_instance.status, 'Running')

        # Check submodule of submodule exists
        self.assertTrue(len(middle_child_instance.components))
        self.assertTrue(middle_child_instance.components[0]['instanceId'])
        last_child_instance = self.last_child_public.get_instance(id=middle_child_instance.components[0]['instanceId'])

        self.assertEqual(last_child_instance.status, 'Running')


        self.assertTrue(self.parent.delete_instance(id=parent_instance.instanceId), "%s-%s: Parent instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Parent instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

        #self.assertRaises(exceptions.ApiError, middle_child_instance.status) # Check submodule does not exists

    def test_launch_3level_hierapp_shared_last_child(self):
        """ Launch 3-level hierarchical app with last child as shared instance.
        """

    # Create shared last child
        shared_last_child_instance = self.last_child_public.launch(destroyInterval=600000)
        self.assertTrue(shared_last_child_instance)
        self.assertTrue(shared_last_child_instance.ready())

        rev = self.last_child.create_revision(name='%s-shared_last_child' % self._testMethodName, instance=shared_last_child_instance)
        last_child_revision = self.last_child_public.get_revision(id=rev.revisionId)

        self.shared_service_public.add_shared_instance(last_child_revision, shared_last_child_instance)

        parameters = {
             	'top_parent_in.last_child_input': 'UPD by test Hello from TOP parent to last child',
  		        'top_parent_in.middle_child_input': 'UPD by test Hello from TOP parent to middle child',}
        submodules = {
                'middle_child': {
                    'parameters': {},
                    'submodules': {
                        'last_child': {
                            'revisionId': last_child_revision.revisionId
            }}}}


        parent_instance = self.parent_public.launch(destroyInterval=300000, parameters=parameters, submodules=submodules)

        self.assertTrue(parent_instance, "%s-%s: Parent instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Parent instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        # Check submodule exists
        self.assertTrue(len(parent_instance.components))
        self.assertTrue(parent_instance.components[0]['instanceId'])
        middle_child_instance = self.middle_child_public.get_instance(id=parent_instance.components[0]['instanceId'])

        self.assertEqual(middle_child_instance.status, 'Running')

        # Check submodule of submodule exists
        self.assertTrue(len(middle_child_instance.components))
        self.assertTrue(middle_child_instance.components[0]['instanceId'])
        last_child_instance = self.last_child_public.get_instance(id=middle_child_instance.components[0]['instanceId'])

        # Check we use shared last instance
        self.assertEqual(last_child_instance.instanceId, shared_last_child_instance.instanceId, "Last child used is not shared one")

        self.assertTrue(self.parent.delete_instance(id=parent_instance.instanceId), "%s-%s: Parent instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Parent instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

    # Remove created services and instance
        self.shared_service_public.remove_shared_instance(shared_last_child_instance)
        self.assertTrue(self.last_child.delete_instance(id=shared_last_child_instance.instanceId), "%s-%s: Last child instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(last_child_instance.destroyed(), "%s-%s: Last child instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))


    def test_launch_3level_hierapp_shared_middle_child(self):
        """ Launch 3-level hierarchical app with middle child as shared instance and last child as shared instance.
        We create basic hierapp, set it as shared and then use it in another hierapp :)
        """
    # Create shared last child
        shared_last_child_instance = self.last_child_public.launch(destroyInterval=600000)
        self.assertTrue(shared_last_child_instance)
        self.assertTrue(shared_last_child_instance.ready())

        rev = self.last_child.create_revision(name='%s-shared_last_child' % self._testMethodName, instance=shared_last_child_instance)
        last_child_revision = self.last_child_public.get_revision(id=rev.revisionId)

        self.shared_service_public.add_shared_instance(last_child_revision, shared_last_child_instance)

    # Create shared middle child
        parameters = { 'last_child_in.app_input': 'Parent in to Last child',
                       'middle_child_in.app_input': 'Middle param'}
        submodules = {
            'last_child': {
                'revisionId': last_child_revision.revisionId}}

    # Create shared middle child
        shared_middle_child_instance = self.middle_child_public.launch(destroyInterval=600000, parameters=parameters, submodules=submodules)
        self.assertTrue(shared_middle_child_instance)
        self.assertTrue(shared_middle_child_instance.ready())

        rev = self.middle_child.create_revision(name='%s-shared_middle_child' % self._testMethodName, instance=shared_middle_child_instance)
        middle_child_revision = self.middle_child_public.get_revision(id=rev.revisionId)

        self.shared_service_public.add_shared_instance(middle_child_revision, shared_middle_child_instance)


    # Start parent
        parameters = {
                'top_parent_in.last_child_input': 'Hello from TOP parent to last child',
                'top_parent_in.middle_child_input': 'Hello from TOP parent to middle child'}
        submodules = {
                'middle_child': {
                    'revisionId': middle_child_revision.revisionId}}

        parent_instance = self.parent_public.launch(destroyInterval=300000, parameters=parameters, submodules=submodules)

        self.assertTrue(parent_instance, "%s-%s: Parent instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Parent instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

    # Check submodule exists
        self.assertTrue(len(parent_instance.components))
        self.assertTrue(parent_instance.components[0]['instanceId'])
        middle_child_instance = self.middle_child_public.get_instance(id=parent_instance.components[0]['instanceId'])
        self.assertEqual(middle_child_instance.status, 'Running')

    # Check we use shared instance
        self.assertEqual(middle_child_instance.instanceId, shared_middle_child_instance.instanceId, "Middle child used is not shared one")


    # Check submodule of submodule exists
        self.assertTrue(len(middle_child_instance.components))
        self.assertTrue(middle_child_instance.components[0]['instanceId'])
        last_child_instance = self.last_child_public.get_instance(id=middle_child_instance.components[0]['instanceId'])
        self.assertEqual(last_child_instance.status, 'Running')

    # Check we use shared instance
        self.assertEqual(last_child_instance.instanceId, shared_last_child_instance.instanceId, "Last child used is not shared one")

    # Clean
        self.assertTrue(self.parent.delete_instance(id=parent_instance.instanceId), "%s-%s: Parent instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Parent instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

    # Remove created services and middle instance
        self.shared_service_public.remove_shared_instance(shared_middle_child_instance)
        self.assertTrue(self.middle_child.delete_instance(id=shared_middle_child_instance.instanceId), "%s-%s: Last child instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(middle_child_instance.destroyed(), "%s-%s: Last child instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

    # Remove created services and last instance
        self.shared_service_public.remove_shared_instance(shared_last_child_instance)
        self.assertTrue(self.last_child.delete_instance(id=shared_last_child_instance.instanceId), "%s-%s: Last child instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(last_child_instance.destroyed(), "%s-%s: Last child instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

