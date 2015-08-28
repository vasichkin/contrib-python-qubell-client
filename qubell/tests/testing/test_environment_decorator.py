import unittest
from contextlib import contextmanager

from qubell.api import globals as qubell_globals
from qubell.api.private.testing import environment


@contextmanager
def zone(name):
    """
    Context manager changes Global Zone temporary
    """
    prev = qubell_globals.ZONE_NAME
    if name:
        qubell_globals.ZONE_NAME = name
    else:
        qubell_globals.ZONE_NAME = None
    yield
    qubell_globals.ZONE_NAME = prev


class DummyTests(object):
    applications = []
    #current_environment = 'default'

    def test_nothing(self):
        pass

    def test_fail(self):
        assert False

    def helper(self):
        pass

    @staticmethod
    def test_manager():
        pass

    @classmethod
    def test_factory(cls):
        pass


class ZoneDummyTests(object):
    applications = []

    def test_nothing(self):
        pass


class EnvironmentDecoratorTests(unittest.TestCase):
    def test_patch_multiplication_test_methods(self):
        with zone(None):
            environment({"a": {"A": "AA"}, "b - b": {"B": "BB"}, "default": {"C": "CC"}})(DummyTests)

            new_classes = ['DummyTests_a', 'DummyTests_b_b', 'DummyTests_default']
            new_tests = ['test_factory',
                         'test_fail',
                         'test_manager',
                         'test_nothing', ]

            for case in new_classes:
                assert case in globals()
                for test in new_tests:
                    assert test in globals()[case].__dict__

            assert globals()['DummyTests_a'].current_environment == 'a'
            assert globals()['DummyTests_b_b'].current_environment == 'b - b'
            assert globals()['DummyTests_default'].current_environment == 'default'

            assert not hasattr(globals()['DummyTests'], 'current_environment')

            assert not hasattr(globals()['DummyTests_a'], '_wait_for_prev')
            assert globals()['DummyTests_b_b']._wait_for_prev == 1
            assert globals()['DummyTests_default']._wait_for_prev == 2

    def test_patch_environment_with_zone(self):
        zone_name = "some-strange Zone"

        with zone(zone_name):
            zone_suffix = qubell_globals.ZoneConstants.zone_suffix()
            assert zone_suffix, "zone suffix cannot be empty"
            environment({"a": {"A": "AA"}, "b - b": {"B": "BB"}, "default": {"C": "CC"}})(ZoneDummyTests)
            assert globals()['ZoneDummyTests_a'].current_environment == 'a' + zone_suffix
            assert globals()['ZoneDummyTests_default'].current_environment == 'default' + zone_suffix
            assert globals()['ZoneDummyTests_b_b'].current_environment == 'b - b' + zone_suffix
