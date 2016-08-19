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
import requests
import yaml
import os

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"


class Manifest(object):
    """
    Base class for manifest storage
    """

    # noinspection PyShadowingBuiltins
    def __init__(self, name=None, content=None, url=None, file=None):
        self.name = name

        self.url = url
        self._raw_content = content
        if content:
            self.source = 'Text'
        self._manifest_file = file

        self.source = None
        self.file = file

    @property
    def content(self):
        if self._raw_content:
            return self._raw_content
        # external data read only once
        if self.url:
            self.source = self.url  # todo: should be "Url"
            self._raw_content = requests.get(self.url).content
        elif self._manifest_file:
            if os.path.exists(self._manifest_file):
                self.file = self._manifest_file
            elif os.path.exists(os.path.join(os.path.dirname(__file__), self._manifest_file)):
                self.file = os.path.join(os.path.dirname(__file__), self._manifest_file)
            else:
                exit(u"No manifest found '{0}' at '{1}'".format(self.name, self._manifest_file))
            # noinspection PyArgumentEqualDefault
            self.source = self.file  # todo: should be 'File'
            self._raw_content = open(self.file).read()
        return self._raw_content

    def patch(self, path, value=None):
        """ Set specified value to yaml path.
        Example:
        patch('application/components/child/configuration/__locator.application-id','777')
        Will change child app ID to 777
        """
        # noinspection PyShadowingNames
        def pathGet(dictionary, path):
            for item in path.split("/"):
                dictionary = dictionary[item]
            return dictionary

        # noinspection PyShadowingNames
        def pathSet(dictionary, path, value):
            path = path.split("/")
            key = path[-1]
            dictionary = pathGet(dictionary, "/".join(path[:-1]))
            dictionary[key] = value

        # noinspection PyShadowingNames
        def pathRm(dictionary, path):
            path = path.split("/")
            key = path[-1]
            dictionary = pathGet(dictionary, "/".join(path[:-1]))
            del dictionary[key]

        src = yaml.load(self.content)
        if value:
            pathSet(src, path, value)
        else:
            pathRm(src, path)
        self._raw_content = yaml.safe_dump(src, default_flow_style=False)
        return True
