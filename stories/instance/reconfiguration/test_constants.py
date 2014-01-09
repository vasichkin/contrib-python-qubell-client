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
from qubell.api.private.manifest import Manifest


__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__version__ = "1.0.13"
__email__ = "vkhomenko@qubell.com"

class Constants(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(Constants, cls).setUpClass()
        cls.client = cls.organization.application(name="%s-constants-reconfiguration" % cls.prefix, manifest=cls.manifest)

    @classmethod
    def tearDownClass(cls):
        super(Constants, cls).tearDownClass()
        #cls.client.clean()
        cls.client.delete()

    def tearDown(self):
        super(Constants, self).tearDown()
        self.inst1.delete()
        assert self.inst1.destroyed()

        self.inst2.delete()
        assert self.inst2.destroyed()

    def reconf(self, base_manifest, target_manifest):
        self.client.upload(base_manifest)
        self.inst1 = self.client.launch(destroyInterval=300000)
        self.assertTrue(self.inst1, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst1.ready(), "Instance not 'running' after timeout")

        self.client.upload(target_manifest)
        self.inst2 = self.client.launch(destroyInterval=300000)
        self.assertTrue(self.inst2, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(self.inst2.ready(), "Instance not 'running' after timeout")

        rev2 = self.client.create_revision(name='%s-rev2' % self._testMethodName, instance=self.inst2)

        self.inst1.reconfigure(revisionId=rev2.revisionId)
        return self.inst1

    # May fail because "Unknown status"
    def test_parameter_added(self):
        """ Reconfigure app adding new parameter. It should be shown after reconfiguration.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "constants-base.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "constants-added_parameter.yml"))
        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())

        self.assertEqual("Hello old param", reconfigured_inst.returnValues['return.foo'])
        self.assertEqual("Hello NEW param", reconfigured_inst.returnValues['return.bar'])

    def test_parameter_removed(self):
        """ Reconfigure app removing parameter. Old returns should be removed after reconfiguration.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "constants-added_parameter.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "constants-base.yml"))
        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())

        self.assertEqual("Hello single param", reconfigured_inst.returnValues['return.foo'])
        self.assertFalse(reconfigured_inst.returnValues.has_key('return.bar'))

    def test_parameter_type_change(self):
        """ Reconfigure app changing parameter type.
        """
        src = Manifest(file=os.path.join(os.path.dirname(__file__), "constants-base.yml"))
        dst = Manifest(file=os.path.join(os.path.dirname(__file__), "constants-parameter_type_change.yml"))
        reconfigured_inst = self.reconf(src, dst)
        self.assertTrue(reconfigured_inst.ready())

        self.assertEqual("42", reconfigured_inst.returnValues['return.foo'])
