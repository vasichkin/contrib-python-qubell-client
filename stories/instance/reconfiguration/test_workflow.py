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



import os

from stories import base
from stories.base import attr
from qubell.api.private.manifest import Manifest
from qubell.api.tools import retry


__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__version__ = "1.0.13"
__email__ = "vkhomenko@qubell.com"



class WorkflowInstance(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkflowInstance, cls).setUpClass()
        cls.client = cls.organization.application(name="%s-workflow-reconfiguration" % cls.prefix, manifest=cls.manifest)

    @classmethod
    def tearDownClass(cls):
        super(WorkflowInstance, cls).tearDownClass()
        # Remove all revisions after tests
        #cls.client.clean()
        cls.client.delete()


    def reconf(self, base_manifest, target_manifest):
        self.client.upload(base_manifest)
        self.inst1 = self.client.launch(destroyInterval=300000)
        self.assertTrue(self.inst1, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst1.ready(), "Instance not 'running' after timeout")

        self.client.upload(target_manifest)
        self.inst2 = self.client.launch(destroyInterval=300000)
        self.assertTrue(self.inst2, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.ready(),"Instance not 'running' after timeout")
        rev2 = self.client.create_revision(name='%s-rev2' % self._testMethodName, instance=self.inst2)
        assert rev2
        self.inst1.reconfigure(revisionId=rev2.revisionId)
        return self.inst1

    @attr('smoke')
    def test_run_trigger_on_parameter_change(self):
        """ Reconfigure app changing input parameters. There is trigger on input parameter. Changing that parameter shous run trigger that updates output.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-trigger_on_param.yml"))
        self.client.upload(src)
        inst1 = self.client.launch(destroyInterval=300000)
        self.assertTrue(inst1, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(inst1.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))
        self.assertEqual("Hello from BASE WORKFLOW manifest", inst1.returnValues['out.app_output'])

        new_params = {'in.app_trigger': 'trig it'}
        inst1.reconfigure(parameters=new_params)
        self.assertTrue(inst1.ready(), "Instance failed to finish reconfiguration")

        @retry(5,2,1)
        def waitFor(): return "UPDATED by update workflow" in inst1.returnValues['out.app_output']
        waitFor()
        self.assertEqual("UPDATED by update workflow", inst1.returnValues['out.app_output'])

        self.assertTrue(inst1.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(inst1.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))


    def test_parameter_added(self):
        """ Reconfigure app adding new parameter. New parameter should be shown after reconfiguration.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-removed_param.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-base.yml"))
        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())

        @retry(5,2,1)
        def waitFor(): return reconfigured_inst.returnValues.has_key('out.app_output')
        waitFor()
        self.assertEqual("Hello from BASE WORKFLOW manifest", reconfigured_inst.returnValues['out.app_output'])

        self.assertTrue(self.inst1.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst1.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))


    def test_parameter_removed(self):
        """ Reconfigure app removing parameter. Old parameter should disappear after reconfiguration.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-base.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-removed_param.yml"))

        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())
        @retry(5,2,1)
        def waitFor(): return not reconfigured_inst.returnValues.has_key('out.app_output')
        waitFor()
        self.assertFalse(reconfigured_inst.returnValues.has_key('out.app_output'))

        self.assertTrue(self.inst1.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst1.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))


    def test_workflow_component_added(self):
        """ Reconfigure app adding new workflow. New workflow should be launched after reconfiguration.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-base.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-binding_added.yml"))
        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())

        @retry(5,2,1)
        def waitFor(): return reconfigured_inst.returnValues.has_key('out.app2_output')
        waitFor()

        self.assertEqual("Hello from BASE WORKFLOW manifest", reconfigured_inst.returnValues['out.app_output'])
        self.assertTrue('action.newgo' in [x['name'] for x in reconfigured_inst.availableWorkflows])
        self.assertTrue(reconfigured_inst.returnValues.has_key('out.app2_output'))
        self.assertEqual("Hi new binding", reconfigured_inst.returnValues['out.app2_output'])

        self.assertTrue(self.inst1.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst1.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

    def test_workflow_removed(self):
        """ Reconfigure app removing workflow. Workflow should be destroyed after reconfiguration.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-binding_added.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-base.yml"))

        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())

        @retry(5,2,1)
        def waitFor(): return not reconfigured_inst.returnValues.has_key('out.app2_output')
        waitFor()

        self.assertFalse(reconfigured_inst.returnValues.has_key('out.app2_output'))
        self.assertEqual("Hello from BASE WORKFLOW manifest", reconfigured_inst.returnValues['out.app_output'])
        self.assertFalse('action.newgo' in [x['name'] for x in reconfigured_inst.availableWorkflows])

        self.assertTrue(self.inst1.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst1.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

    def test_workflow_update(self):
        """ Reconfigure app changing workflow. Workflow should be updated.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-base.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-workflow_changed.yml"))

        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())

        reconfigured_inst.run_workflow(name='action.gogogo')
        self.assertTrue(reconfigured_inst.ready())

        @retry(5,2,1)
        def waitFor(): return "NEW GOGO launched" in reconfigured_inst.returnValues['out.app_output']
        waitFor()

        self.assertEqual("NEW GOGO launched", reconfigured_inst.returnValues['out.app_output'])

        self.assertTrue(self.inst1.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst1.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))


    @attr('smoke')
    def test_workflow_added(self):
        """ Reconfigure app with adding action to workflow.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-base.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "workflow-many_changes.yml"))

        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())

        @retry(5,2,1)
        def waitFor(): return reconfigured_inst.returnValues.has_key('out.new_output')
        waitFor()

        self.assertEqual("Hello from BASE WORKFLOW manifest", reconfigured_inst.returnValues['out.app_output'])
        self.assertTrue('action.stop' in [x['name'] for x in reconfigured_inst.availableWorkflows])
        self.assertTrue('action.gogo_new' in [x['name'] for x in reconfigured_inst.availableWorkflows])

        reconfigured_inst.run_workflow(name='action.gogo_new')
        self.assertTrue(reconfigured_inst.ready())
        self.assertEqual("Action GOGO-NEW launched", reconfigured_inst.returnValues['out.new_output'])

        reconfigured_inst.run_workflow(name='action.stop')
        self.assertTrue(reconfigured_inst.ready())
        self.assertEqual("Action STOP launched", reconfigured_inst.returnValues['out.new_output'])

        self.assertTrue(self.inst1.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst1.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))
