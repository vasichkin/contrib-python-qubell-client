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

from time import sleep
import os

from stories import base
from stories.base import attr
from qubell.api.private.manifest import Manifest


class ServiceCallTestApp(base.BaseTestCase):
    _multiprocess_can_split_ = True
    #_multiprocess_shared_ = True

    @classmethod
    def setUpClass(cls):
        super(ServiceCallTestApp, cls).setUpClass()

    # Create applications for tests
        cls.parent = cls.organization.application(name="%s-test-servicecall-parent" % cls.prefix, manifest=cls.manifest)
        cls.child = cls.organization.application(name="%s-test-servicecall-child" % cls.prefix, manifest=cls.manifest)

    # Create non shared instance to use in tests
        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), 'child.yml'))
        mnf.patch('application/components/child_app/configuration/configuration.workflows/launch/return/own/value', 'Service call child')
        cls.child.upload(mnf)
        cls.child_instance = cls.child.launch(destroyInterval=600000)
        assert cls.child_instance
        assert cls.child_instance.ready()
        cls.child_revision = cls.child.create_revision(name='%s-tests-servicecall-shared' % cls.prefix, instance=cls.child_instance)

        cls.shared_service.add_shared_instance(cls.child_revision, cls.child_instance)

    @classmethod
    def tearDownClass(cls):

    # Remove created services
        cls.shared_service.remove_shared_instance(cls.child_instance)

        cls.child_instance.delete()
        assert cls.child_instance.destroyed()

        cls.parent.delete()
        cls.child.delete()
        super(ServiceCallTestApp, cls).tearDownClass()


    @attr('smoke')
    def test_servicecall_hierapp_with_shared_child(self):
        """ Launch hierarchical app with shared instance and execute service call on child.
        """

        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "parent_servicecall.yml")) #Todo: resolve paths
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.child.applicationId)
        self.parent.upload(pmnf)

        submodules = {
                "child": {
                    "revisionId": self.child_revision.revisionId
            }}

        parent_instance = self.parent.launch(destroyInterval=600000, submodules=submodules)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        sub = parent_instance.submodules

        self.assertTrue(len([sid for sid in sub if sid['id'] == self.child_instance.instanceId]))  # Way i search for id

        # Instance ready. Execute workflow with servicecall

        parent_instance.run_workflow(name='actions.child_servicecall')
        self.assertTrue(parent_instance.ready(), "Parent instance failed to execute servicall workflow")
        sleep(10)
        self.assertEqual('child Update launched', parent_instance.returnValues['parent_out.child_workflow_status'])



        # Shouldn't be able to remove child while parent use it and should return error
        # TODO: BUG
        #self.assertFalse(child_instance.destroy())

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

    def test_servicecall_hierapp(self):
        """ Launch hierarchical with non shared instance and execute service call on child.
        """

        pmnf = Manifest(file=os.path.join(os.path.dirname(__file__), "parent_servicecall.yml")) #Todo: resolve paths
        pmnf.patch('application/components/child/configuration/__locator.application-id', self.child.applicationId)
        self.parent.upload(pmnf)

        parent_instance = self.parent.launch(destroyInterval=600000)
        self.assertTrue(parent_instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        self.assertTrue(parent_instance.submodules, 'Parent does not start submodules')
        self.assertEqual(parent_instance.submodules[0]['status'], 'Running')
        sub = parent_instance.submodules

        self.assertFalse(len([sid for sid in sub if sid['id'] == self.child_instance.instanceId]))  # Way i search for id

    # Instance ready. Execute workflow with servicecall

        parent_instance.run_workflow(name='actions.child_servicecall')
        self.assertTrue(parent_instance.ready(), "Parent instance failed to execute servicall workflow")
        sleep(10)
        self.assertEqual('child Update launched', parent_instance.returnValues['parent_out.child_workflow_status'])



        # Shouldn't be able to remove child while parent use it and should return error
        # TODO: BUG
        #self.assertFalse(child_instance.destroy())

        self.assertTrue(parent_instance.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(parent_instance.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
