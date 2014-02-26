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
from qubell import deprecated
from qubell.api.private.instance import InstanceList, DEAD_STATUS, Instance
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
from qubell.api.provider.router import ROUTER as router


class Application(Entity):
    """
    Base class for applications. It should create application and services+environment requested
    """

    def __init__(self, organization, id):
        self.organization = organization
        self.organizationId = self.organization.organizationId
        self.applicationId = self.id = id

        self.launch = self.create_instance = functools.partial(organization.create_instance, application=self)

    @lazyproperty
    def instances(self):
        return InstanceList(list_json_method=self.list_instances_json, organization=self.organization)

    @lazyproperty
    def revisions(self):
        return RevisionList(list_json_method=self.list_revisions_json, application=self)

    @property
    def defaultEnvironment(self):
        return self.organization.get_default_environment()

    @property
    def name(self):
        return self.json()['name']



    #TODO: Is not used yet, think how to restore revisions
    def __parse(self, values):
        ret = {}
        for val in values:
            ret[val['id']] = val['value']
        return ret

    @staticmethod
    def new(organization, name, manifest):
        log.info("Creating application: %s" % name)

        resp = router.post_organization_application(org_id=organization.organizationId,
                                                    files={'path': manifest.content},
                                                    data={'manifestSource': 'upload', 'name': name})
        app = Application(organization, resp.json()['id'])
        app.manifest = manifest
        return app

    def delete(self):
        log.info("Removing application: %s" % self.name)
        router.delete_application(org_id=self.organizationId, app_id=self.applicationId)
        return True

    def update(self, **kwargs):
        if kwargs.get('manifest'):
            self.upload(kwargs.pop('manifest'))
        log.info("Updating application: %s" % self.name)

        data = json.dumps(kwargs)
        resp = router.put_application(org_id=self.organizationId, app_id=self.applicationId, data=data)
        return resp.json()

    def clean(self, timeout=3):
        for ins in self.instances:
            st = ins.status
            if st not in ['Destroyed', 'Destroying', 'Launching', 'Executing']: # Tests could fail and we can get any state here
                log.info("Destroying instance %s" % ins.name)
                ins.delete()
                assert ins.destroyed(timeout=timeout)
                self.instances.remove(ins)

        for rev in self.revisions:
            self.revisions.remove(rev)
            rev.delete()

        @retry(5, 1 , 2 , AssertionError)
        def eventually_clean():
            for ins in self.instances:
                assert ins.status == 'Destroyed'

        eventually_clean()
        return True

    def json(self):
        return router.get_application(org_id=self.organizationId, app_id=self.applicationId).json()

    def list_instances_json(self):
        instances = self.json()['instances']
        return [ins for ins in instances if ins['status'] not in DEAD_STATUS]

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False


# REVISION
    def get_revision(self, id):
        from qubell.api.private.revision import Revision
        rev = Revision(application=self, id=id)
        return rev

    def list_revisions_json(self):
        return self.json()['revisions']

    def create_revision(self, name, instance, parameters=[], version=None):
        if not version:
            version=self.get_manifest()['manifestVersion']
        payload = json.dumps({ 'name': name,
                    'parameters': parameters,
                    'submoduleRevisions': {},
                    'returnValues': [],
                    'applicationId': self.applicationId,
                    'applicationName': self.name,
                    'version': version,
                    'instanceId': instance.instanceId})
        resp = router.post_revision(org_id=self.organizationId, app_id=self.applicationId, data=payload)
        return self.get_revision(id=resp.json()['id'])

    def delete_revision(self, id):
        self.get_revision(id).delete()

# MANIFEST

    def get_manifest(self):
        return router.post_application_refresh(org_id=self.organizationId, app_id=self.applicationId).json()

    def upload(self, manifest):
        log.info("Uploading manifest")
        self.manifest = manifest
        return router.post_application_manifest(org_id=self.organizationId, app_id=self.applicationId,
                                    files={'path': manifest.content},
                                    data={'manifestSource': 'upload', 'name': self.name}).json()

    def get_instance(self, id=None, name=None):
        if id:  # submodule instances are invisible for lists
            return Instance(id=id, organization=self.organization)
        return self.instances[id or name]

    #def create_instance(self, name=None, environment=None, revision=None, parameters={}, destroyInterval=None):
    #    from qubell.api.private.instance import Instance
    #    return Instance.new(name=name,
    #                        application=self,
    #                        environment=environment,
    #                        revision=revision,
    #                        parameters=parameters,
    #                        destroyInterval=destroyInterval)


class ApplicationList(QubellEntityList):
    base_clz = Application
