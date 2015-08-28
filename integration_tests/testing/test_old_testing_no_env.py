import os

from qubell.api.testing import *


class ApiTestingTestCase(BaseComponentTestCase):
    name = "manifest"
    apps = [{
        "name": name,
        "file": os.path.realpath(os.path.join(os.path.dirname(__file__), '%s.yml' % name))
    }]

    # noinspection PyShadowingNames
    @instance(byApplication=name)
    @values({"app-output": "out"})
    def test_out(self, instance, out):
        assert instance.running()
        assert out == "This is default manifest"

    # noinspection PyShadowingNames
    @instance(byApplication=name)
    @workflow("action.default")
    @values({"updated": "updated"})
    def test_wf(self, instance, updated):
        assert instance.running()
        assert updated == "Yaya"
