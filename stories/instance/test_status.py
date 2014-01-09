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


class InstanceStatusTest(base.BaseTestCase):
    _multiprocess_can_split_ = True

# Here we prepare environment once for all tests in class.
    @classmethod
    def setUpClass(cls):
        super(InstanceStatusTest, cls).setUpClass()
        cls.app = cls.organization.application(name="%s-test-instance-status" % cls.prefix, manifest=cls.manifest)

# Here we cleaning our environment. Delete all created stuff
    @classmethod
    def tearDownClass(cls):
        cls.app.delete()
        super(InstanceStatusTest, cls).tearDownClass()

# This would be executed for each test
    def setUp(self):
        super(InstanceStatusTest, self).setUp()
        manifest = Manifest(file=os.path.join(os.path.dirname(__file__), 'propagate_status.yml'))
        self.app.upload(manifest)
        self.instance = self.app.launch(destroyInterval=300000)

        self.assertTrue(self.instance, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(self.instance.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

# Also, clean after each test
    def tearDown(self):
        self.assertTrue(self.instance.destroy())
        self.assertTrue(self.instance.destroyed())
        super(InstanceStatusTest, self).tearDown()

# Tests
    def test_non_propogated_fail_is_local(self):
        # No errors at beginning
        self.assertFalse(self.instance.errorMessage)
        self.instance.run_workflow(name='action.local_fail')

        self.assertTrue(self.instance.ready(), 'Failed to execute workflow.')
        self.assertEqual('Running', self.instance.status)
        # Now we should see error message while instance got status running
        self.assertTrue(self.instance.errorMessage)

    def test_propogated_fail_is_global(self):
        # No errors at beginning
        self.assertFalse(self.instance.errorMessage)
        self.instance.run_workflow(name='action.global_fail')

        self.assertTrue(self.instance.waitForStatus(final='Failed', accepted=['Requested', 'Executing', 'Unknown']), 'Got wrong status: Running. Should be: Failed')
        self.assertEqual('Failed', self.instance.status)
        # Now we should see error message while instance got status running
        self.assertTrue(self.instance.errorMessage)

    def test_propogated_success_is_global(self):
        # Make Failed status at beginning
        self.instance.run_workflow(name='action.global_fail')
        self.assertTrue(self.instance.waitForStatus(final='Failed', accepted=['Requested', 'Executing', 'Unknown']), 'Got wrong status: Running. Should be: Failed')

        self.instance.run_workflow(name='action.global_success')

        self.assertTrue(self.instance.ready(), 'Instance should get Running status')
        self.assertEqual('Running', self.instance.status)

        # Error message stays there
        self.assertTrue(self.instance.errorMessage)

    def test_non_propogated_success_is_local(self):
        # Make Failed status at beginning
        self.instance.run_workflow(name='action.global_fail')
        self.assertTrue(self.instance.waitForStatus(final='Failed', accepted=['Requested', 'Executing', 'Unknown']), 'Got wrong status: Running. Should be: Failed')

        self.instance.run_workflow(name='action.local_success')
        self.assertTrue(self.instance.waitForStatus(final='Failed', accepted=['Requested', 'Executing', 'Unknown', 'Running']), 'Got wrong status: Running. Should be: Failed')

        self.assertEqual('Failed', self.instance.status)
        self.assertTrue(self.instance.errorMessage)
