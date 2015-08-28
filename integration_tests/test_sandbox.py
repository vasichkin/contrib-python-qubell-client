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
__version__ = "1.0.1"
__email__ = "vkhomenko@qubell.com"

import os

from qubell.api.testing import *


def manifest(name):
    return os.path.realpath(os.path.join(os.path.dirname(__file__), name))


@environment({
    'default': {
        'policies': [{'action': 'provisionVms', 'parameter': 'imageId', 'value': 'reg/ami-777'},
                     {'action': 'provisionVms', 'parameter': 'vmIdentity', 'value': 'ubuntu7'}]
        },
    'custom': {
        'policies': [{'action': 'provisionVms', 'parameter': 'imageId', 'value': 'reg/ami-888'},
                     {'action': 'provisionVms', 'parameter': 'vmIdentity', 'value': 'ubuntu8'}],
        'markers': ['test-marker'],
        'properties': [{'name': 'testprop', 'type': 'string', 'value': 'test-prop value'}]
    }})
class SandboxClassTest(BaseComponentTestCase):
    name = 'SelfSandboxTest'
    apps = [{"name": name,
             "file": manifest('default.yml'),
             "settings": {"destroyInterval": 300000},
             "parameters": {
                 "in.app_input": "dddd"}
             }]

    # noinspection PyShadowingNames
    @instance(byApplication=name)
    def test_instance(self, instance):
        assert 'Active' == instance.status
        app = self.organization.applications[self.name]
        assert instance in app.instances

    def test_env(self):
        default_env = self.organization.environments['default'].json()
        custom_env = self.organization.environments['custom'].json()

        assert 'reg/ami-777' in [x['value'] for x in default_env['policies']]
        assert 'ubuntu7' in [x['value'] for x in default_env['policies']]

        assert 'ubuntu8' in [x['value'] for x in custom_env['policies']]
        assert 'reg/ami-888' in [x['value'] for x in custom_env['policies']]
        assert 'test-marker' in [x['name'] for x in custom_env['markers']]
        assert 'test-prop value' in [x['value'] for x in custom_env['properties']]
