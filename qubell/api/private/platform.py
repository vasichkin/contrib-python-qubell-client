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
import copy
import logging as log
from qubell.api.private import exceptions
from qubell.api.private.common import Auth
from qubell.api.private.exceptions import ApiAuthenticationError
from qubell.api.private.organization import OrganizationList, Organization
from qubell.api.provider.router import InstanceRouter, PrivatePath, PublicPath
from qubell.api.tools import lazyproperty

Context = Auth
####################################################

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"


# noinspection PyShadowingBuiltins
class QubellPlatform(InstanceRouter):
    def __init__(self, auth=None, context=None):
        assert not (auth or context), "support of auth and context parameters is removed"

    @staticmethod
    def connect(tenant=None, user=None, password=None, token=None, is_public=False):
        """
        Authenticates user and returns new platform to user.
        This is an entry point to start working with Qubell Api.
        :rtype: QubellPlatform
        :param str tenant: url to tenant, default taken from 'QUBELL_TENANT'
        :param str user: user email, default taken from 'QUBELL_USER'
        :param str password: user password, default taken from 'QUBELL_PASSWORD'
        :param str token: session token, default taken from 'QUBELL_TOKEN'
        :param bool is_public: either to use public or private api (public is not fully supported use with caution)
        :return: New Platform instance
        """
        if not is_public:
            router = PrivatePath(tenant)
        else:
            router = PublicPath(tenant)
            router.public_api_in_use = is_public

        if token or (user and password):
            router.connect(user, password, token)

        return QubellPlatform().init_router(router)

    def connect_to_another_user(self, user, password, token=None, is_public=False):
        """
        Authenticates user with the same tenant as current platform using and returns new platform to user.
        :rtype: QubellPlatform
        :param str user: user email
        :param str password: user password
        :param str token: session token
        :param bool is_public: either to use public or private api (public is not fully supported use with caution)
        :return: New Platform instance
        """
        return QubellPlatform.connect(self._router.base_url, user, password, token, is_public)

    def list_organizations_json(self):
        resp = self._router.get_organizations()
        return resp.json()

    @lazyproperty
    def organizations(self):
        """
        Lists platform organizations, accessible to the user
        :rtype: OrganizationList
        """
        return OrganizationList(list_json_method=self.list_organizations_json).init_router(self._router)

    def create_organization(self, name):
        """
        Creates new organization
        :rtype: Organization
        """
        org = Organization.new(name, self._router)
        assert org.ready(), "Organization {} hasn't got ready after creation".format(name)
        return org

    def get_organization(self, id=None, name=None):
        """
        Gets existing and accessible organization
        :rtype: Organization
        """
        log.info("Picking organization: %s (%s)" % (name, id))
        return self.organizations[id or name]

    def get_or_create_organization(self, id=None, name=None):
        """
        Gets existing or creates new organization
        :rtype: Organization
        """
        if id:
            return self.get_organization(id)
        else:
            assert name
            try:
                return self.get_organization(name=name)
            except exceptions.NotFoundError:
                return self.create_organization(name)

    organization = get_or_create_organization

    def get_backends_versions(self):
        """
        Get backends versions
        :return: dict containing name of backend and version.
        """
        # We are not always have permission, so find open.
        for i in range(0, len(self.organizations)):
            try:
                backends = self.organizations[i].environments['default'].backends
            except ApiAuthenticationError:
                pass
            else:
                break
        versions = dict([(x['name'], x['version']) for x in backends])
        return versions

    def restore(self, config, clean=False, timeout=10):
        config = copy.deepcopy(config)
        for org in config.pop('organizations', []):
            restored_org = self.get_or_create_organization(id=org.get('id'), name=org.get('name'))
            restored_org.restore(org, clean, timeout)

    def validate(self, manifest):
        return self._router.post_validate(data=manifest.content).json()

    # noinspection PyMethodMayBeStatic
    def authenticate(self):
        assert False, 'use QubellPlatform.connect instead'

    def generate_session_token(self, refresh_token):
        response = self._router.generate_session_token(json={'refreshToken': refresh_token})
        assert response.status_code == 200

        json = response.json()

        return json['jwtBearer'], json['expiresIn']
