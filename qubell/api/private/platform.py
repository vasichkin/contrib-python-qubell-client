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
import simplejson as json

from qubell.api.private import exceptions

class QubellPlatform(object):

    def __init__(self, auth):
        self.organizations = []
        self.auth = auth
        self.user = auth.user
        self.password = auth.password
        self.tenant = auth.tenant

    def authenticate(self):
        url = self.auth.api+'/signIn'
        data = {
            'email': self.auth.user,
            'password': self.auth.password}
        # Use session to eliminate accidental falls
        rsession = requests.Session()
        rsession.post(url=url, data=data, verify=False)
        self.auth.cookies = rsession.cookies
        rsession.close()
        if 'PLAY_SESSION' in self.auth.cookies:
            return True
        else:
            return False

    def get_context(self):
        return self.auth

    def create_organization(self, name):
        log.info("Creating organization: %s" % name)
        url = self.auth.api+'/organizations.json'
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({'editable': 'true',
                              'name': name})
        resp = requests.post(url, cookies=self.auth.cookies, data=payload, verify=False, headers=headers)
        log.debug(resp.text)
        if resp.status_code == 200:
            return self.get_organization(resp.json()['id'])
        raise exceptions.ApiError('Unable to create organization %s, got error: %s' % (name, resp.text))

    def get_organization(self, id):
        log.info("Picking organization: %s" % id)
        from qubell.api.private.organization import Organization
        org = Organization(self.auth, id=id)
        self.organizations.append(org)
        return org

    def get_or_create_organization(self, id=None, name=None):
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

    def organization(self, id=None, name=None):
        """ Smart object. Will create organization, modify or pick one"""
        # TODO: Modify if parameters differs
        return self.get_or_create_organization(id, name)

    def list_organizations(self):
        url = self.auth.api+'/organizations.json'
        resp = requests.get(url, cookies=self.auth.cookies, verify=False)
        log.debug(resp.text)
        if resp.status_code == 200:
            return resp.json()
        raise exceptions.ApiError('Unable to get organizations list, got error: %s' % resp.text)


    def rename_organization(self):
        raise NotImplementedError

    def delete_organization(self):
        raise NotImplementedError('Api does not support organization deletion')

    def restore(self, config):
        for org in config.pop('organizations', []):
            restored_org = self.get_or_create_organization(id=org.get('id'), name=org.get('name'))
            restored_org.restore(org)


class Auth(object):
    def __init__(self, user, password, tenant):
        self.user = user
        self.password = password
        self.tenant = tenant

        # TODO: parse tenant to generate api url
        self.api = tenant


import warnings
import functools

warnings.simplefilter('always', DeprecationWarning)


def deprecated(func, msg=None):
    """
    A decorator which can be used to mark functions
    as deprecated.It will result in a deprecation warning being shown
    when the function is used.
    """

    message = msg or "Use of deprecated function '{}`.".format(func.__name__)

    @functools.wraps(func)
    def wrapper_func(*args, **kwargs):
        warnings.warn(message, DeprecationWarning, stacklevel=2)
        return func(*args, **kwargs)
    return wrapper_func


@deprecated
class Context(Auth):
    def __init__(self, user, password, api):
        super(Context, self).__init__(user, password, api)