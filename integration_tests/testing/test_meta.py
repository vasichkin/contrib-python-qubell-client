
from unittest import TestCase
from qubell.api.private.organization import Organization
from qubell.api.testing import BaseComponentTestCase

import os


class TestMeta(TestCase):
    def restore(self, params):
        self.meta = params

    def setUp(self):
        self.cls = BaseComponentTestCase
        self.cls.organization = Organization(id="id")
        self.cls.organization.restore = self.restore

    def test_meta_url(self):
        self.cls.organization.set_applications_from_meta("https://raw.githubusercontent.com/qubell-bazaar/component-mysql-dev/1.1-35p/meta.yml")
        assert 'Database' in self.meta['applications'][0]['name']

    def test_meta_file(self):
        self.cls.organization.set_applications_from_meta(os.path.join(os.path.dirname(__file__), "./meta.yml"))
        assert 'Database' in self.meta['applications'][0]['name']
