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

from qubell.api.private.common import EntityList, Entity, IdName
from qubell.api.private import exceptions
from qubell.api.provider.router import InstanceRouter
from qubell.api.tools import lazyproperty

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"


class Revision(Entity, InstanceRouter):
    """
    Base class for revision
    """

    # noinspection PyShadowingBuiltins
    def __init__(self, application, id):
        self.id = id
        self.application = application
        self.organizationId = self.application.organizationId
        self.applicationId = self.application.applicationId

    @lazyproperty
    def name(self):
        return self.json()['name']

    @lazyproperty
    def revisionId(self):
        """
        revisionId differs from id, it is details of implementation use self.id
        :return: RevisionId
        """
        log.warning("'RevisionId' requested, ensure that you are don't need 'id'")
        revision_id = self.json()['revisionId']
        assert revision_id == self.id, "RevisionId differs id-{}!=revisionId-{}".format(self.id, revision_id)
        return revision_id

    def __getattr__(self, key):
        resp = self.json()
        if key in resp:
            return resp[key] or False
        raise exceptions.NotFoundError('Cannot get revision property %s' % key)

    def json(self):
        return self._router.get_revision(org_id=self.organizationId, app_id=self.applicationId, rev_id=self.id).json()

    def delete(self, force=True):
        if force:
            return self._router.delete_revision(org_id=self.organizationId, app_id=self.applicationId, rev_id=self.id, force="true")
        else:
            return self._router.delete_revision(org_id=self.organizationId, app_id=self.applicationId, rev_id=self.id, force="false")


class RevisionList(EntityList, InstanceRouter):

    def __init__(self, list_json_method, application):
        self.json = list_json_method
        self.application = application
        self.applicationId = application.id
        self.organization = application.organization
        self.organization = application.organization.organizationId
        EntityList.__init__(self)

    def _id_name_list(self):
        self._list = [IdName(ent['id'], ent['name']) for ent in self.json()]

    def _get_item(self, id_name):
        return Revision(id=id_name.id, application=self.application).init_router(self._router)
