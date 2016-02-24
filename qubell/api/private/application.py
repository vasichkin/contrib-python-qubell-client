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
import functools
from qubell.api.private.instance import InstanceList, Instance
from qubell.api.private.revision import RevisionList
from qubell.api.tools import lazyproperty, retry


__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

import logging as log
import simplejson as json

from qubell.api.private import exceptions
from qubell.api.private.common import QubellEntityList, Entity
from qubell.api.provider.router import InstanceRouter


class Application(Entity, InstanceRouter):
    """
    Base class for applications. It should create application and services+environment requested
    """

    # noinspection PyShadowingBuiltins
    def __init__(self, organization, id):
        self.organization = organization
        self.organizationId = self.organization.organizationId
        self.applicationId = self.id = id

        self.launch = self.create_instance = functools.partial(organization.create_instance, application=self)

    @lazyproperty
    def instances(self):
        return InstanceList(list_json_method=self.list_instances_json,
                            organization=self.organization).init_router(self._router)

    @lazyproperty
    def destroyed_instances(self):
        return InstanceList(list_json_method=self.list_destroyed_instances_json,
                            organization=self.organization).init_router(self._router)

    @lazyproperty
    def revisions(self):
        return RevisionList(list_json_method=self.list_revisions_json, application=self).init_router(self._router)

    @property
    def defaultEnvironment(self):
        return self.organization.get_default_environment()

    @property
    def name(self):
        return self.json()['name']

    @staticmethod
    def new(organization, name, manifest, router):
        log.info("Creating application: %s" % name)

        resp = router.post_organization_application(org_id=organization.organizationId,
                                                    files={'path': manifest.content},
                                                    data={'manifestSource': 'upload', 'name': name})
        app = Application(organization, resp.json()['id']).init_router(router)
        app.manifest = manifest
        log.info("Application %s created (%s)" % (name, app.applicationId))
        return app

    def delete(self, clean=False):
        log.info("Removing application: id=%s" % self.applicationId)
        if clean:
            self.clean()
        self._router.delete_application(org_id=self.organizationId, app_id=self.applicationId)
        return True

    def update(self, **kwargs):
        if kwargs.get('manifest'):
            self.upload(kwargs.pop('manifest'))
        log.info("Updating application: id=%s" % self.applicationId)

        data = json.dumps(kwargs)
        resp = self._router.put_application(org_id=self.organizationId, app_id=self.applicationId, data=data)
        return resp.json()

    def clean(self, timeout=None):
        if not timeout:
            timeout = [7, 1, 1.5]
        instances = self.instances
        log.info("Cleaning application: id=%s" % self.applicationId)
        for ins in instances:
            if ins.status not in ['Destroyed', 'Destroying']:
                ins.destroy()

        @retry(*timeout, retry_exception=AssertionError)
        def eventually_clean():
            # noinspection PyShadowingNames
            for ins in instances:
                assert ins.status == 'Destroyed'
        eventually_clean()

        for rev in self.revisions:
            rev.delete()
        return True

    def remove_destroyed_instances(self):
        return self._router.delete_destroyed_instances(org_id=self.organizationId, app_id=self.applicationId).json()

    def json(self):
        return self._router.get_application(org_id=self.organizationId, app_id=self.applicationId).json()

    def list_instances_json(self):
        return self.organization.list_instances_json(application=self)

    def list_destroyed_instances_json(self):
        return self.organization.list_instances_json(application=self, show_only_destroyed=True)

    def __getattr__(self, key):
        resp = self.json()
        if key not in resp:
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False


# REVISION
    # noinspection PyShadowingBuiltins
    def get_revision(self, id):
        from qubell.api.private.revision import Revision
        rev = Revision(application=self, id=id).init_router(self._router)
        return rev

    def list_revisions_json(self):
        # return self.json()['revisions']
        return self._router.get_revisions(org_id=self.organizationId, app_id=self.applicationId).json()

    def create_revision(self, name, instance=None, parameters=None, version=None, submodules=None):
        if not parameters:
            parameters = {}
        if not version:
            version = self.get_manifest()['manifestVersion']
        if not submodules:
            submodules = {}
        if instance:
            payload = json.dumps({'name': name,
                                  'parameters': parameters,
                                  'submoduleRevisions': {},
                                  'returnValues': [],
                                  'applicationId': self.applicationId,
                                  'applicationName': self.name,
                                  'manifestVersion': version,
                                  'instanceId': instance.instanceId})
            resp = self._router.post_revision(org_id=self.organizationId, app_id=self.applicationId, data=payload)
            return self.get_revision(id=resp.json()['id'])
        else:

            payload = json.dumps({'name': name,
                                  'parameters': parameters,
                                  'submodules': submodules,
                                  'applicationId': self.applicationId,
                                  'manifestVersion': version, })
            resp = self._router.post_revision_fs(org_id=self.organizationId, app_id=self.applicationId, data=payload)
            return self.get_revision(id=resp.json()['id'])

    # noinspection PyShadowingBuiltins
    def delete_revision(self, id):
        self.get_revision(id).delete()

# MANIFEST

    def get_manifest(self, version=None):
        if not version:
            return self._router.post_application_refresh(org_id=self.organizationId, app_id=self.applicationId).json()
        else:
            return self._router.get_application_manifest_version(org_id=self.organizationId, app_id=self.applicationId, version=version).json()

    def get_manifest_latest(self):
        return self._router.get_application_manifests_latest(org_id=self.organizationId, app_id=self.applicationId).json()

    def upload(self, manifest):
        log.info("Uploading manifest: %s to application: id=%s" % (manifest.source, self.applicationId))
        # noinspection PyAttributeOutsideInit
        self.manifest = manifest
        if self._router.public_api_in_use:
            return self._router.post_application_manifest(org_id=self.organizationId, app_id=self.applicationId,
                                                          data=manifest.content)

        return self._router.post_application_manifest(org_id=self.organizationId, app_id=self.applicationId,
                                                      files={'path': manifest.content},
                                                      data={'manifestSource': 'upload', 'name': self.name}).json()

    # noinspection PyShadowingBuiltins
    def get_instance(self, id=None, name=None):
        if id:  # submodules instances are invisible for lists
            return Instance(id=id, organization=self.organization).init_router(self._router)
        return Instance.get(self._router, self.organization, name, application=self)


class ApplicationList(QubellEntityList):
    base_clz = Application

