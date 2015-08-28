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

from base import BaseTestCase


class RevisionClassTest(BaseTestCase):

    def setup_once(self):
        super(RevisionClassTest, self).setup_once()
        self.app = self.organization.create_application(manifest=self.manifest, name='Self-RevisionClassTest')

    def teardown_once(self):
        self.app.delete()
        super(RevisionClassTest, self).teardown_once()

    def test_revision_crud(self):
        revision_name = 'test-crud-revision'

        rev = self.app.create_revision(name=revision_name, parameters={})
        assert rev, "Revision was not created from sratch"

        instance = self.app.launch(destroyInterval=600000, revision=rev)
        assert instance.ready(), 'Failed to launch instance.'

        # Check that instance associated with revision
        rev_instances = [r for r in self.app.revisions if r.json()['instancesIds'][0] == instance.id]
        assert len(rev_instances), "Instance doesn't have revision"
        assert rev.id == self.app.revisions[revision_name].id, "Different revision Ids"

        instance.destroy()
        assert instance.destroyed(), "Instance with revision, cannot be destroyed"

        self.app.revisions[rev.id].delete()
        rev_instances = [r for r in self.app.revisions if r.json()['instancesIds'][0] == instance.id]
        assert len(rev_instances) == 0, "Revision was not deleted"
