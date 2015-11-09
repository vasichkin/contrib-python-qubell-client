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
import sys
import unittest


class SetupOnceError(Exception):
    def __init__(self, cause):
        super(SetupOnceError, self).__init__('caused by ' + repr(cause))
        self.cause = cause

class TeardownOnceError(Exception):
    def __init__(self, cause):
        super(TeardownOnceError, self).__init__('caused by ' + repr(cause))
        self.cause = cause


# noinspection PyUnresolvedReferences
class SetupOnce(object):
    """
    Trait for unittest.TestCase
    Allows do not use test class methods, such as setUpClass or tearDownClass.

    This allows to avoid failed suites. And always each test has failed.
    """

    _counter = 0
    _test_count = 0

    _tear_down_called = False
    __self = None

    setup_error = None

    @classmethod
    def setUpClass(cls):
        super(SetupOnce, cls).setUpClass()
        # noinspection PyProtectedMember
        tests = unittest.TestLoader().loadTestsFromTestCase(cls)._tests

        cls._test_count = len(tests)

        # parse skip decorator, unittest has special logic for this avoiding running setUp or tearDown
        unitest_skip_count = 0
        for test in tests:
            # noinspection PyProtectedMember
            a = getattr(cls, test._testMethodName)
            if hasattr(a, '__unittest_skip__') and a.__unittest_skip__:
                unitest_skip_count += 1
        cls._test_count -= unitest_skip_count

    @classmethod
    def tearDownClass(cls):
        if not cls._tear_down_called:
            try:
                if cls.__self:
                    cls.__self.__wrapped_tearDown()
            finally:
                cls.__self = None  # release pointer
        super(SetupOnce, cls).tearDownClass()

    def setup_once(self):
        """
        Hook method for setting up fixture before running tests.
        Has instance scope.
        """

    def teardown_once(self):
        """
        Hook method for deconstructing the test fixture after testing it.
        Has instance scope.
        """

    def setUp(self):
        super(SetupOnce, self).setUp()
        if not self.__class__.__self:
            # When attributes are used, it is impossible to calculate number of tests
            # In this case tearDownClass will call teardown_once for sure, if it wasn't called.
            # Due to nature per one suite - one instance, this shouldn't be a memory issue
            self.__class__.__self = self  # hack, to call tearDown in class method.
        self.__class__._counter += 1
        if self.__class__._counter == 1:
            try:
                self.setup_once()
            except BaseException:
                self.__class__.setup_error = sys.exc_info()
            finally:
                # sugar, need to bypass new variables to class
                instanzz_attrs = dict(self.__dict__)
                for k, v in instanzz_attrs.items():
                    if not k.startswith('_'):
                        setattr(self.__class__, k, v)

        if self.__class__.setup_error:
            # do not wrap SkipTest
            if isinstance(self.__class__.setup_error[1], unittest.SkipTest):
                raise self.__class__.setup_error[1], None, self.__class__.setup_error[2]
            else:
                raise SetupOnceError(self.__class__.setup_error[1]), None, self.__class__.setup_error[2]

    def __wrapped_tearDown(self):
        try:
            self.__class__._tear_down_called = True
            self.teardown_once()
            self.__class__.__self = None
        except BaseException:
            teardown_error = sys.exc_info()
            raise TeardownOnceError(teardown_error[1]), None, teardown_error[2]

    def tearDown(self):
        if self.__class__._counter == self._test_count:
            self.__wrapped_tearDown()

        super(SetupOnce, self).tearDown()



if __name__ == '__main__':
# this block for testing purposes

    import logging

    logger = logging.getLogger("test")
    hdlr = logging.FileHandler('setup_once.log')
    logger.addHandler(hdlr)


    def attr_fake(*args, **kwargs):
        if 'skip' in args:
            return unittest.skip("")
        def decorator(f):
            if 'skip' in args:
                pass
        return decorator

    def log(cls_name, message):
        info = "{}: {}".format(cls_name, message)
        print info
        logger.error(info)

    class TestFullBase(SetupOnce, unittest.TestCase):

        def setUp(self):
            super(TestFullBase, self).setUp()
            def cleanup():
                log("TestFullBase", "cleaup")

            #self.addCleanup(cleanup)

        def setup_once(self):
            super(TestFullBase, self).setup_once()
            log("TestFullBase", "setup_once")
            self.top = 0

        def teardown_once(self):
            log("TestFullBase", "teardown_once")
            super(TestFullBase, self).teardown_once()

        @classmethod
        def setUpClass(cls):
            super(TestFullBase, cls).setUpClass()
            log("TestFullBase", "setUpClass")

        @classmethod
        def tearDownClass(cls):
            log("TestFullBase", "tearDownClass")
            super(TestFullBase, cls).tearDownClass()

    class ReuseVariableTest(TestFullBase):
        @classmethod
        def update_something(cls):
            cls.b = 0

        def setup_once(self):
            super(ReuseVariableTest, self).setup_once()
            self.a = 1
            assert self.top == 0
            self.top = 1
            self.b = 1
            self.update_something()
            log("ReuseVariableTest", "setup_once")

        def teardown_once(self):
            log("ReuseVariableTest", "teardown_once")
            super(ReuseVariableTest, self).teardown_once()

        def test_pass(self):
            log("DifferentTestCasesTest", "test_pass")
            assert self.a == 1

        def test_apass(self):
            log("DifferentTestCasesTest", "test_apass")
            assert self.a == 1

        def test_overriden_from_parent(self):
            assert self.top == 1

        # this is natural python scoping, this will always fail, since instance attr already exists
        def test_set_by_calling_class_method(self):
            assert self.b == 0


    class DifferentTestCasesTest(TestFullBase):
        def setup_once(self):
            super(DifferentTestCasesTest, self).setup_once()
            log("DifferentTestCasesTest", "setup_once")

        def teardown_once(self):
            log("DifferentTestCasesTest", "teardown_once")
            super(DifferentTestCasesTest, self).teardown_once()

        def test_pass(self):
            log("DifferentTestCasesTest", "test_pass")
            assert True

        def test_fail(self):
            log("DifferentTestCasesTest", "test_fail")
            assert False

        def test_error(self):
            log("DifferentTestCasesTest", "test_error")
            raise IndexError("oops")

        def test_apass(self):
            log("DifferentTestCasesTest", "test_apass")
            assert True

        @unittest.skip("skip attr")
        def test_skip(self):
            pass

        def test_skip_internal(self):
            raise unittest.SkipTest("skip internal")

        @attr_fake("skip")
        def test_skip_attr(self):
            pass


    class FailureInSetupTest(TestFullBase):
        def setup_once(self):
            super(FailureInSetupTest, self).setup_once()
            log("FailureInSetupTest", "setup_once")
            raise AttributeError("setup boom")

        def test_pass(self):
            log("FailureInSetupTest", "test_pass")
            assert True

        def test_apass(self):
            log("FailureInSetupTest", "test_apass")
            assert True

    class FailureInTeardownTest(TestFullBase):
        def teardown_once(self):
            super(FailureInTeardownTest, self).teardown_once()
            log("FailureInTeardownTest", "teardown_once")
            raise AttributeError("teardown boom")

        def test_pass(self):
            log("FailureInTeardownTest", "test_pass")
            assert True

        def test_apass(self):
            log("FailureInTeardownTest", "test_apass")
            assert True

    class SkipTestInSetupOnceTest(TestFullBase):
        def setup_once(self):
            raise unittest.SkipTest("skipping, requirements not met")

        def test_pass(self):
            pass

        def test_pass2(self):
            pass

    from nose.plugins.attrib import attr

    class TearDownOnceAttrTest(TestFullBase):
        def teardown_once(self):
            assert False, "this is good if with tag we've reached here"
            super(TearDownOnceAttrTest, self).teardown_once()

        @attr("pass")
        def test_pass(self):
            pass

        @attr("pass")
        def test_pass2(self):
            pass

        def test_fail(self):
            assert False
