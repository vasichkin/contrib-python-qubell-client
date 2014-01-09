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
from qubell.api.private.manifest import Manifest
from stories.base import attr


class BasicInstanceActionsTest(base.BaseTestCase):
    _multiprocess_can_split_ = True

# Here we prepare environment once for all tests in class.
    @classmethod
    def setUpClass(cls):
        # Call all parents setups
        super(BasicInstanceActionsTest, cls).setUpClass()
        # Cannot be done via public
        cls.app = cls.organization.application(name="%s-test-instance-actions" % cls.prefix, manifest=cls.manifest)
        cls.app_public = cls.organization_public.get_application(id=cls.app.applicationId)
# Here we cleaning our environment. Delete all created stuff
    @classmethod
    def tearDownClass(cls):
        # Call all parents teardowns
        super(BasicInstanceActionsTest, cls).tearDownClass()
        cls.app.delete()

# This would be executed for each test
    def setUp(self):
        super(BasicInstanceActionsTest, self).setUp()
        self.app_public.upload(self.manifest)
        self.instance = self.app_public.launch(destroyInterval=300000)

        self.assertTrue(self.instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(self.instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

# Also, clean after each test
    def tearDown(self):
        # Not implemented
        self.assertTrue(self.app.delete_instance(self.instance.instanceId))
        self.assertTrue(self.instance.destroyed())
        super(BasicInstanceActionsTest, self).tearDown()


# Tests
    @attr('skip') # This test would be skipped
    # Todo: Move to application actions
    def test_upload_manifest(self):
        """ Check uploading manifest to application works
        """
        self.assertTrue(self.app_public.upload(self.app.manifest), 'Failed to upload manifest')

    @attr('skip') # This test would be skipped
    # Todo: Move to application actions
    def test_upload_not_valid_manifest(self):
        """ Check uploading non-validatable manifest to application returns error
        """
        badm = Manifest()
        badm.content = """
        application:
          components:
            error:
        """
        self.assertFalse(self.app_public.upload(badm), 'Succeed uploading unvalidatable manifest')

    @attr('smoke')
    def test_workflow_launch(self):
        ''' We have instance launched by setUp. Now launch workflow there and check it works.
        '''

        self.assertEqual("This is default manifest", self.instance.returnValues['out.app_output'])
        self.instance.run_workflow(name='action.default')
        self.assertTrue(self.instance.ready(), 'Failed to execute workflow.')
        self.assertEqual('Action WF launched', self.instance.returnValues['out.app_output'])


    @attr('smoke')
    def test_revision(self):
        ''' Create new revision. Change latest manifest. Launch revision and check it uses not latest, but revisions manifest.
        '''
        # Not implemented via public api
        rev = self.app.create_revision(name='test-revision-launch', instance=self.instance)
        self.assertTrue(rev)

        manf1 = Manifest(file=os.path.join(os.path.dirname(__file__), 'simple_manifest.yml'))
        self.app_public.upload(manf1) # Upload new manifest. So, latest is not same as in our revision.


        inst1 = self.app_public.launch(destroyInterval=600000, revisionId=rev.revisionId)
        self.assertTrue(inst1.ready(), 'Failed to launch instance.')
        self.assertEqual('This is default manifest', inst1.returnValues['out.app_output'])

        self.assertTrue(self.app.delete_instance(inst1.instanceId))
        self.assertTrue(rev.delete())

