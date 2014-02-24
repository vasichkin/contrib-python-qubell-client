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

from qubell.api.private import exceptions
from qubell.api.provider.router import ROUTER as router


class Provider(object):

    def __init__(self, organization, id, auth=None):
        self.auth = auth
        self.providerId = id
        self.organization = organization
        self.organizationId = organization.organizationId
        my = self.json()
        #self.__dict__.update(my)

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False

    def json(self):
        resp = router.get_providers(org_id=self.organizationId)
        provider = [x for x in resp.json() if x['id'] == self.providerId]
        if len(provider)>0:
            return provider[0]

    def delete(self):
        router.delete_provider(org_id=self.organizationId,prov_id=self.providerId)
        return True