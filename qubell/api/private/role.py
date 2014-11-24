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
from qubell.api.private.common import QubellEntityList, Entity


class Role(Entity):

    def __init__(self, organization, id):
        self.organization = organization
        self.organizationId = self.organization.organizationId
        self.roleId = self.id = id

    @staticmethod
    def new(organization, name, permissions=""):
        log.info("Creating role: %s" % name)
        log.debug("Creating role: %s, permissions: %s" % (name, permissions))
        resp = router.post_roles(org_id=organization.id, data=json.dumps({"name": name,
                                                               "permissions": permissions}))
        role = Role(organization, resp.json()['id'])
        return role

    @property
    def name(self):
        return self.json()['name']

    @property
    def permissions(self):
        return self.json()['permissions']

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def json(self):
        return router.get_role(org_id=self.organizationId, role_id=self.roleId).json()

    def update(self, name=None, permissions=""):
        name = name or self.name
        permissions = permissions or self.permissions
        router.put_role(org_id=self.organization.id,
                        role_id=self.id,
                        data=json.dumps({"name": name,
                                         "permissions": permissions}))
        return True

    def delete(self):
        router.delete_role(org_id=self.organizationId, role_id=self.roleId)
        return True

class RoleList(QubellEntityList):
    base_clz = Role