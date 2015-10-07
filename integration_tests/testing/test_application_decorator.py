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
__email__ = "vkhomenko@qubell.com"
__copyright__ = "Copyright 2014, Qubell.com"
__license__ = "Apache"

import os

from qubell.api.testing import *

content = open((os.path.realpath(os.path.join(os.path.dirname(__file__), 'manifest.yml')))).read()


@environment({
    "default": {},
    "AmazonEC2_Ubuntu_1004": {
        "policies": [{
            "action": "provisionVms",
            "parameter": "imageId",
            "value": "us-east-1/ami-0fac7566"
        }, {
            "action": "provisionVms",
            "parameter": "vmIdentity",
            "value": "ubuntu"
        }]
    }
})
@applications([{
    "name": 'EnvsAppTest-Case App',
    "file": os.path.realpath(os.path.join(os.path.dirname(__file__), 'manifest.yml')),
    "parameters": {"in.app_input": 'bla-bla-bla'},
    "settings": {"destroyInterval": '300000'}
}])
class EnvsAppTestCase(BaseComponentTestCase):
    # noinspection PyShadowingNames
    @instance(byApplication='EnvsAppTest-Case App')
    @values({"app-output": "out"})
    def test_out(self, instance, out):
        assert instance.running()
        assert out == "bla-bla-bla"
