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
import logging as log
import warnings
import copy

import simplejson as json
from qubell.api.private import exceptions
from qubell.api.private.organization import OrganizationList, Organization

from qubell.api.provider.router import ROUTER as router
from qubell import deprecated

#todo: understood, that some people may use this object for authentication, need to move this to proper place

from qubell.api.tools import lazyproperty

### Backward compatibility for component testing ###
from qubell.api.private.common import Auth
Context = Auth
####################################################

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

class QubellPlatform(object):
    def __init__(self, auth=None, context=None):
        if context:
            warnings.warn("replace context with auth name, it is deprecated and will be removed", DeprecationWarning,
                          stacklevel=2)
        self.auth = auth or context

    @staticmethod
    def connect(tenant, user, password):

        router.base_url = tenant
        router.connect(user, password)

        #todo: remove auth mimics when routes are used everywhere
        router.tenant = tenant
        router.user = user
        router.password = password
        return QubellPlatform(auth=router)

    @deprecated('use QubellPlatform.connect instead')
    def authenticate(self):
        router.base_url = self.auth.tenant
        router.connect(self.auth.user, self.auth.password)
        #todo: remove following, left for compatibility
        self.auth.cookies = router._cookies
        return True

    def list_organizations_json(self):
        resp = router.get_organizations()
        return resp.json()

    @lazyproperty
    def organizations(self):
        return OrganizationList(list_json_method=self.list_organizations_json)

    def create_organization(self, name):
        org = Organization.new(name)
        assert org.ready()
        return org

    def get_organization(self, id=None, name=None):
        log.info("Picking organization: %s (%s)" % (name, id))
        return self.organizations[id or name]


    def get_or_create_organization(self, id=None, name=None):
        """ Smart object. Will create organization, modify or pick one"""
        if id: return self.get_organization(id)
        else:
            assert name
            try:
                return self.get_organization(name=name)
            except exceptions.NotFoundError:
                return self.create_organization(name)

    organization = get_or_create_organization

    def restore(self, config, clean=False, timeout=10):
        config = copy.deepcopy(config)
        for org in config.pop('organizations', []):
            restored_org = self.get_or_create_organization(id=org.get('id'), name=org.get('name'))
            restored_org.restore(org, clean, timeout)

    @property
    def info(self):
        return self.auth

