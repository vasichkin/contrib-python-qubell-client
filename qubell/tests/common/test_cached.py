import unittest
from qubell.api.private.common import Cached
import time
import random

class Stubs(object):
    def respond_random(self):
        return random.randint(1, 100)

class test_Cached(unittest.TestCase):

    def setUp(self):
        self.stubs = Stubs()

    def test_response_cached(self):
        resp = Cached(data_fn=lambda: self.stubs.respond_random())
        query = resp.get()
        assert resp.get() == query
        assert resp.get() == query
        time.sleep(3)
        assert resp.get() != query