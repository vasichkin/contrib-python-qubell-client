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

import logging as log

import requests

from qubell.api.public import exceptions, application


class Revision(application.Application):
    """
    Base class for revision
    """

    def __init__(self, context, id):
        self.revisionId = id
        self.auth = context
        my = self.json()
        self.name = my['name']

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def json(self):
        url = self.auth.api+'/api/1/applications/'+self.auth.applicationId+'/revisions'
        resp = requests.get(url, auth=(self.auth.user, self.auth.password), verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            resp.json()
            rev = [x for x in resp.json() if x['id'] == self.revisionId]
            if len(rev)>0:
                return rev[0]
            raise exceptions.NotFoundError('Unable to find revision by id: %s' % self.revisionId)
        raise exceptions.ApiError('Unable to get revision properties, got error: %s' % resp.text)


    def delete(self):
        raise NotImplementedError
