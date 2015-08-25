import unittest
from qubell.api.private.common import Cached
import time
import random

class Stubs(object):
    counter = 0
    def respond_random(self):
        self.counter += 1
        return random.randint(1, 100)

class test_cached(unittest.TestCase):

    def setUp(self):
        self.stubs = Stubs()

    def test_response_cached(self):
        resp = Cached(data_fn=lambda: self.stubs.respond_random())
        query = resp.get()

        # Second query should be cached, so must return same result.
        assert resp.get() == query
        assert resp.get() == query

        # Check that only one query to server was made. Caching at work.
        assert self.stubs.counter == 1
        time.sleep(3)

        # Check that cache expired after 3 sec.
        assert resp.get() != query
        assert self.stubs.counter == 2