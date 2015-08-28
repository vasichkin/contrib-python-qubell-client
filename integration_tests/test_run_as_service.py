import os

from qubell.api.testing import *


def manifest(name):
    return os.path.realpath(os.path.join(os.path.dirname(__file__), name))


@environment({"default": {}})
class RunAsServiceTest(BaseComponentTestCase):
    service_name = "service"
    client_name = "client"

    apps = [
        {"name": client_name, "file": manifest("client.yml")},
        {"name": service_name, "file": manifest("service.yml"), "add_as_service": True}
    ]

    # noinspection PyUnusedLocal,PyShadowingNames
    @instance(byApplication=client_name)
    @values({"serv.stringValue": "value"})
    def test_client_connected(self, instance, value):
        self.assertEqual(value, "hello")
