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

import requests
import yaml
import os

class Manifest(object):
    """
    Base class for manifest storage
    """

    def __init__(self, name=None, content=None, url=None, file=None):
        self.name = name
        if url:
            self.url = url
            self.content = requests.get(url).content
        elif content:
            self.source = 'Text'
            self.content = content
        elif file:
            if os.path.exists(file):
                self.file = file
            elif os.path.exists(os.path.join(os.path.dirname(__file__), file)):
                self.file = os.path.join(os.path.dirname(__file__), file)
            else:
                exit("No manifest found: %s " % self.name)
            self.content = open(self.file, 'r').read()

    def patch(self, path, value):
        """ Set specified value to yaml path.
        Example:
        patch('application/components/child/configuration/__locator.application-id','777')
        Will change child app ID to 777
        """
        def pathGet(dictionary, path):
            for item in path.split("/"):
                dictionary = dictionary[item]
            return dictionary

        def pathSet(dictionary, path, value):
            path = path.split("/")
            key = path[-1]
            dictionary = pathGet(dictionary, "/".join(path[:-1]))
            dictionary[key] = value

        src = yaml.load(self.content)
        pathSet(src, path, value)
        self.content = yaml.safe_dump(src, default_flow_style=False)
        return True
