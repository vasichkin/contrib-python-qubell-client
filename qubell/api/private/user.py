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
__email__ = "vkhomenko@qubell.com"

import logging as log
import simplejson as json
from qubell.api.private import exceptions
from qubell.api.provider.router import ROUTER as router
from qubell.api.private.common import QubellEntityList, Entity, IdName


class User(Entity):

    def __init__(self, organization, id):
        self.organization = organization
        self.organizationId = self.organization.organizationId
        self.userId = self.id = id

    @staticmethod
    def get_user(organization, email):
        log.info("Getting user: %s" % email)
        resp = router.get_users(org_id=organization.id).json()
        ids = [ x['id'] for x in resp if x['email']==email]
        if len(ids):
            user = User(organization, ids[0])
            return user
        else:
            raise exceptions.NotFoundError('User with email: %s not found' % email)

    @property
    def name(self):
        return self.json()['name']

    @property
    def email(self):
        return self.json()['email']

    @property
    def roles(self):
        return self.json()['roles']

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def json(self):
        resp = router.get_users(org_id=self.organizationId).json()
        ids = [ x for x in resp if x['id']==self.id]
        if len(ids):
            return ids[0]
        else:
            raise exceptions.NotFoundError('User with email: %s not found' % self.email)

    def set_roles(self, roles):
        userdata = self.json()
        userdata['roles']= roles
        log.info("Updating user: %s" % userdata['id'])
        log.debug(userdata)
        router.put_user(org_id=self.organization.id, user_id=self.id, data=json.dumps(userdata))

    def evict(self):
        router.evict_user(org_id=self.organizationId, user_id=self.userId)
        return True

class UserList(QubellEntityList):
    base_clz = User

