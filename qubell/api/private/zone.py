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

from qubell.api.private.common import QubellEntityList, Entity
from qubell.api.provider.router import InstanceRouter


class Zone(Entity, InstanceRouter):

    # noinspection PyShadowingBuiltins
    def __init__(self, organization, id):
        self.zoneId = self.id = id
        self.organizationId = organization.organizationId
        self.organization = organization

    @property
    def name(self):
        return self.json()['name']

    def json(self):
        resp = self._router.get_zones(org_id=self.organizationId)
        zone = [x for x in resp.json() if x['id'] == self.zoneId]
        if len(zone) > 0:
            return zone[0]


class ZoneList(QubellEntityList):
    base_clz = Zone

    def __init__(self, organization):
        QubellEntityList.__init__(self, organization.list_zones_json, organization)
