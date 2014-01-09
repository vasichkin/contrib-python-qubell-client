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
__version__ = "1.0.14"
__email__ = "vkhomenko@qubell.com"

import logging as log

import requests

from qubell.api.private import exceptions


class QubellPlatform(object):

    def __init__(self, context, *args, **kwargs):
        self.context = context

    def authenticate(self):
        url = self.context.api+'/api/1/organizations'
        resp = requests.get(url, auth=(self.context.user, self.context.password), verify=False)
        log.debug(resp.text)
        if 200 == resp.status_code:
            return True
        else:
            return False

    def create_organization(self, name):
        raise NotImplementedError

    def get_organization(self, id):
        log.info("Picking organization: %s" % id)
        from qubell.api.public.organization import Organization
        return Organization(self.context, id=id)

    def organization(self, id=None, name=None):
        """ Smart object. Will create organization or pick one, if exists"""
        if name:
            orgz = [org for org in self.list_organizations() if org['name'] == name]
            # Org found by name
            if len(orgz):
                return self.get_organization(orgz[0]['id'])
            else:
                return self.create_organization(name)
        else:
            name = 'generated-org-name'
            if id:
                return self.get_organization(id)
            else:
                return self.create_organization(name)

    def list_organizations(self):
        url = self.context.api+'/api/1/organizations'
        resp = requests.get(url, auth=(self.context.user, self.context.password), verify=False)
        log.debug(resp.text)
        if 200 == resp.status_code:
            return resp.json()
        raise exceptions.ApiError('Unable to list organization, got error: %s' % resp.text)


    def rename_organization(self):
        raise NotImplementedError

    def delete_organization(self):
        raise NotImplementedError('Api does not support organization deletion')


class Context(object):
    def __init__(self, user, password, api):
        self.user = user
        self.password = password
        self.api = api