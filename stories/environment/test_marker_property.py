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


class MarkerPropertyTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(MarkerPropertyTest, cls).setUpClass()

    # Create applications for tests
        cls.app = cls.organization.application(name="%s-test-marker-property" % cls.prefix, manifest=cls.manifest)
        assert cls.app
        cls.env = cls.organization.create_environment(name='MarkerPropertyTest-%s' % cls.prefix)
        assert cls.env
        cls.env.clean()

    @classmethod
    def tearDownClass(cls):
        # TODO: BUG here https://github.com/qubell/vermilion/issues/2085
        #cls.env.delete()
        cls.app.delete()
        #cls.delete_environment(cls.env.environmentId)
        super(MarkerPropertyTest, cls).tearDownClass()


    def test_marker_crud(self):
        self.assertTrue(self.env.add_marker('TEST-MARKER'))
        markers = self.env.json()['markers']
        mrk = [p for p in markers if p['name'] == 'TEST-MARKER']
        self.assertTrue(len(mrk))
        self.assertEqual(mrk[0]['name'], 'TEST-MARKER')
        self.assertTrue(self.env.remove_marker('TEST-MARKER'))
        markers = [p for p in self.env.json()['markers'] if p['name'] == 'TEST-MARKER']
        self.assertFalse(len(markers))

    def test_property_crud(self):
        self.assertTrue(self.env.add_property(name='test-property-crud', type='string', value='TEST-PROPERTY'))
        properties = self.env.json()['properties']
        prop = [p for p in properties if p['name'] == 'test-property-crud']
        self.assertTrue(len(prop))
        self.assertEqual(prop[0]['name'], 'test-property-crud')
        self.assertEqual(prop[0]['value'], 'TEST-PROPERTY')
        self.assertTrue(self.env.remove_property('test-property-crud'))
        properties = [p for p in self.env.json()['properties'] if p['name'] == 'test-property-crud']
        self.assertFalse(len(properties))

    def test_marker_property_usage(self):
        mnf = Manifest(file=os.path.join(os.path.dirname(__file__), "marker-property.yml")) #Todo: resolve paths
        self.app.upload(mnf)
        self.env.set_backend(self.organization.zone)

        self.assertTrue(self.env.add_property(name='sample-property-str', type='string', value='test-property-string'))
        self.assertTrue(self.env.add_property(name='sample-property-int', type='int', value='42'))
        self.assertTrue(self.env.add_property(name='sample-property-obj', type='object', value='aa:bb'))
        self.assertTrue(self.env.add_marker('test-marker'))

        self.env.add_service(self.wf_service)
        self.env.add_service(self.key_service)

        ins = self.app.launch(destroyInterval=300000, environmentId=self.env.environmentId)
        self.assertTrue(ins, "%s-%s: Instance failed to launch" % (self.prefix, self._testMethodName))
        self.assertTrue(ins.ready(),"%s-%s: Instance not in 'running' state after timeout" % (self.prefix, self._testMethodName))

        out = ins.returnValues
        self.assertEqual(out['output.str'], 'test-property-string')
        self.assertEqual(out['output.int'], '42')
        self.assertEqual(out['output.obj'], 'aa:bb')

        # TODO: instance should be destroyed before properties removed, otherwise it will be in inconsistent state and
        self.assertTrue(ins.delete(), "%s-%s: Instance failed to destroy" % (self.prefix, self._testMethodName))
        self.assertTrue(ins.destroyed(), "%s-%s: Instance not in 'destroyed' state after timeout" % (self.prefix, self._testMethodName))

        self.assertTrue(self.env.remove_property(name='sample-property-str'))
        self.assertTrue(self.env.remove_property(name='sample-property-int'))
        self.assertTrue(self.env.remove_property(name='sample-property-obj'))
        self.assertTrue(self.env.remove_marker('test-marker'))

