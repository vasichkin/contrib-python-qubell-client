import unittest
from qubell.api.private.testing import environment
__author__ = 'dmakhno'


class DummyTests(object):
    applications = []
    current_environment='default'
    def test_nothing(self): pass
    def test_fail(self): assert False
    def helper(self): pass
    @staticmethod
    def test_manager(): pass
    @classmethod
    def test_factory(cls): pass


class EnvironmentDecoratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clazz = environment({"a":{"A":"AA"}, "b - b":{"B":"BB"}, "default":{"C":"CC"}})(DummyTests)


    def test_patch_multiplication_test_test_methods(self):
        new_classes = ['DummyTests_a', 'DummyTests_b_b', 'DummyTests_default']
        new_tests = ['test_factory',
                     'test_fail',
                     'test_manager',
                     'test_nothing',]

        for case in new_classes:
            assert case in globals()
            for test in new_tests:
                assert test in globals()[case].__dict__

        assert globals()['DummyTests_a'].current_environment == 'a'
        assert globals()['DummyTests_b_b'].current_environment == 'b_b'
        assert globals()['DummyTests'].current_environment == 'default'


