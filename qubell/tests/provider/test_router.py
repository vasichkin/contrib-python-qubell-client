from mock import patch, Mock, MagicMock
import unittest

from qubell.api.private.exceptions import ApiUnauthorizedError
from qubell.api.provider.router import Router


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.router = Router("http://router.org")

    def test_no_connection_for_new(self):
        assert not self.router.is_connected

    def test_connection_identification(self):
        with patch.object(self.router, "_cookies", {"PLAY_SESSION": "any_val"}):
            assert self.router.is_connected

    def test_connection_fail_when_no_cookies(self):
        with patch.object(self.router, "_cookies", None):
            assert not self.router.is_connected

    def test_connection_fail_when_wrong_cookies(self):
        with patch.object(self.router, "_cookies", {"eat": "this"}):
            assert not self.router.is_connected

    def test_exception_if_not_get_connected(self):
        with patch.object(self.router, "_session"):
            with self.assertRaises(ApiUnauthorizedError) as context:
                self.router.connect("any@where", "**wrong**")
            assert str(context.exception) == "Authentication failed, please check settings"
    
    def test_url_trim(self):
        url = "http://my.router.org"
        router = Router(url + "/")
        assert router.base_url == url
