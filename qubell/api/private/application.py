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
from qubell.api.private.instance import InstanceList
from qubell.api.tools import lazyproperty


__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

import logging as log
import simplejson as json

from qubell.api.private import exceptions
from qubell.api.private.common import QubellEntityList
from qubell.api.provider.router import ROUTER as router


class Application(object):
    """
    Base class for applications. It should create application and services+environment requested
    """

    def __update(self):
        info = self.json()
        self.name = info['name']
        self.id = self.applicationId
        self.defaultEnvironment = self.organization.get_default_environment()


    def __init__(self, organization, auth=None, **kwargs):
        if hasattr(self, 'applicationId'):
            log.warning("Application reinitialized. Dangerous!")
        self.revisions = []
        self.auth = auth
        self.organization = organization
        self.organizationId = self.organization.organizationId
        self.defaultEnvironment = self.organization.get_default_environment()
        if 'id' in kwargs:
            self.applicationId = kwargs.get('id')
            self.__update()

    @lazyproperty
    def instances(self):
        return InstanceList(list_json_method=self.list_instances_json, organization=self)

    def __parse(self, values):
        ret = {}
        for val in values:
            ret[val['id']] = val['value']
        return ret

        #TODO: Think how to restore revisions

    def create(self, name, manifest):
        log.info("Creating application: %s" % name)
        resp = router.post_organization_application(org_id=self.organizationId, files={'path': manifest.content}, data={'manifestSource': 'upload', 'name': name})
        self.applicationId = resp.json()['id']
        self.manifest = manifest
        self.__update()
        return self

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
        self.__update() #todo: json called here
        return resp.json()

    def clean(self, timeout=3):
        raise NotImplementedError("Deprecated and no known usages")
        # for ins in self.instances:
        #     st = ins.status
        #     if st not in ['Destroyed', 'Destroying', 'Launching', 'Executing']:  # Tests could fail and we can get any state here
        #         log.info("Destroying instance %s" % ins.name)
        #         ins.delete()
        #         assert ins.destroyed(timeout=timeout)
        #         self.instances.remove(ins)
        #
        # for rev in self.revisions:
        #     self.revisions.remove(rev)
        #     rev.delete()
        # return True

    def json(self):
        return router.get_application(org_id=self.organizationId, app_id=self.applicationId).json()

    def list_instances_json(self):
        return self.json()['instances']

    def __getattr__(self, key):
        resp = self.json()
        if not resp.has_key(key):
            raise exceptions.NotFoundError('Cannot get property %s' % key)
        return resp[key] or False


# REVISION
    def get_revision(self, id):
        from qubell.api.private.revision import Revision
        rev = Revision(auth=self.auth, application=self, id=id)
        self.revisions.append(rev)
        return rev

    def list_revisions(self):
        return self.revisions()

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
        rev = self.get_revision(id)
        self.revisions.remove(rev.name)
        rev.delete()

# MANIFEST

    def get_manifest(self):
        return router.post_application_refresh(org_id=self.organizationId, app_id=self.applicationId).json()

    def upload(self, manifest):
        log.info("Uploading manifest")
        self.manifest = manifest
        return router.post_application_manifest(org_id=self.organizationId, app_id=self.applicationId,
                                    files={'path': manifest.content},
                                    data={'manifestSource': 'upload', 'name': self.name}).json()

    def create_instance(self, name=None, environment=None, revision=None, parameters={}, destroyInterval=None):
        from qubell.api.private.instance import Instance
        return Instance.new(name=name,
                            application=self,
                            environment=environment,
                            revision=revision,
                            parameters=parameters,
                            destroyInterval=destroyInterval)

    launch = create_instance


class ApplicationList(QubellEntityList):
    base_clz = Application
