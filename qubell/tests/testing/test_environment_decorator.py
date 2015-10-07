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

    def test_nothing(self):
        pass

    # noinspection PyMethodMayBeStatic
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

    zone_name = "some-strange Zone"
    zone_suffix = qubell_globals.ZoneConstants.zone_suffix(zone_name)

    @classmethod
    def setupClass(cls):
        env_props = {"a": {"A": "AA"}, "b - b": {"B": "BB"}, "default": {"C": "CC"}}
        with zone(None):
            environment(env_props)(DummyTests)
        with zone(cls.zone_name):
            environment(env_props)(ZoneDummyTests)

    def test_patch_multiplication_test_methods(self):
        new_classes = ['DummyTests_a', 'DummyTests_b_b', 'DummyTests_default']
        new_tests = ['test_factory',
                     'test_fail',
                     'test_manager',
                     'test_nothing', ]

        for case in new_classes:
            assert case in globals()
            for test in new_tests:
                assert test in globals()[case].__dict__

    def test_current_environment(self):
        assert globals()['DummyTests_a'].current_environment == 'a'
        assert globals()['DummyTests_b_b'].current_environment == 'b - b'
        assert globals()['DummyTests_default'].current_environment == 'default'
        assert not hasattr(globals()['DummyTests'], 'current_environment')

    def test_current_environment_when_zone_is_set(self):
        assert self.zone_suffix, "zone suffix cannot be empty"
        assert globals()['ZoneDummyTests_a'].current_environment == 'a' + self.zone_suffix
        assert globals()['ZoneDummyTests_default'].current_environment == 'default' + self.zone_suffix
        assert globals()['ZoneDummyTests_b_b'].current_environment == 'b - b' + self.zone_suffix

    def test_environment_indexer(self):
        assert not hasattr(globals()['DummyTests_a'], '_wait_for_prev')
        assert globals()['DummyTests_b_b']._wait_for_prev == 1
        assert globals()['DummyTests_default']._wait_for_prev == 2

    def test_environments_are_filtered_per_class(self):
        assert globals()['ZoneDummyTests_a'].environments == [{"A": "AA", "name": 'a' + self.zone_suffix}]
        assert globals()['ZoneDummyTests_default'].environments == [{"C": "CC", "name": 'default' + self.zone_suffix}]
        assert globals()['ZoneDummyTests_b_b'].environments == [{"B": "BB", "name": 'b - b' + self.zone_suffix}]
