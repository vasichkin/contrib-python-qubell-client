
import logging as log
import unittest
import functools
import nose.plugins.attrib
import testtools
import os


from qubell.api.private.platform import QubellPlatform
from qubell.api.private.testing import applications, environment, environments, instance, values, workflow
from qubell.api.private.testing.sandbox_testcase import SandBoxTestCase
from qubell.api.globals import QUBELL as qubell_config, PROVIDER as cloud_config
from qubell.api.tools import retry, rand

# noinspection PyBroadException
try:
    from requests.packages import urllib3
    urllib3.disable_warnings()
except:
    pass

__all__ = ['BaseComponentTestCase', 'applications', 'environment', 'environments', 'instance', 'values', 'workflow',
           'eventually', 'attr', 'unique']


logger = log.getLogger("qubell")
if os.getenv('QUBELL_LOG_LEVEL', 'info') == 'debug':
    log.getLogger().setLevel(log.DEBUG)
    logger.setLevel(log.DEBUG)
else:
    log.getLogger().setLevel(log.INFO)
    logger.setLevel(log.INFO)

class Qubell(object):
    """
    This class holds platform object.
    Platform is lazy.
    """
    __lazy_platform = None

    # noinspection PyMethodParameters
    @classmethod
    def platform(cls):
        """
        lazy property, to authenticate when needed
        """
        if not cls.__lazy_platform:
            cls.__lazy_platform = QubellPlatform.connect(user=qubell_config['user'], password=qubell_config['password'], token=qubell_config['token'])
            log.info('Authentication succeeded.')
        return cls.__lazy_platform


class BaseComponentTestCase(SandBoxTestCase):
    parameters = dict(qubell_config.items() + cloud_config.items())

    def setup_once(self):
        self.platform = Qubell.platform()
        super(BaseComponentTestCase, self).setup_once()


def eventually(*exceptions):
    """
    Method decorator, that waits when something inside eventually happens
    Note: 'sum([delay*backoff**i for i in range(tries)])' ~= 580 seconds ~= 10 minutes
    :param exceptions: same as except parameter, if not specified, valid return indicated success
    :return:
    """
    return retry(tries=50, delay=0.5, backoff=1.1, retry_exception=exceptions)


def attr(*args, **kwargs):
    """A decorator which applies the nose and testtools attr decorator
    usage:
    @attr("attribute1", "attribute2") - common usage
    @attr(issue=7777) or @attr("fail") - When issue reported and waiting for fix.
                                         Test will pass until it really fails.
                                         Test will fail when issue fixed.
    Most common: "smoke", "long", "unstable", "gui", "cloud"
    """
    if 'skip' in args:
        return unittest.skip("")

    def decorator(f):
        if 'bug' in kwargs or 'issue' in kwargs or 'fail' in args or 'bug' in args:
            bug_num = kwargs.get('bug') or kwargs.get('issue') or '0000'
            return bug(bug_num)(f)

        else:
            tt_dec = testtools.testcase.attr(*args)(f)
            nose_dec = nose.plugins.attrib.attr(*args, **kwargs)(tt_dec)
            return nose_dec

    return decorator


def bug(issue_id, text=''):
    """
    This is similar to unittest.expectedFailure decarator.
    That allows to enter issue_id and custom message.
    """

    def catch(test_method):
        @functools.wraps(test_method)
        def inner(*args, **kwargs):
            try:
                test_method(*args, **kwargs)
            except Exception:
                raise nose.SkipTest('ISSUE: #{}'.format(issue_id))
            else:
                raise AssertionError('Failure expected. Is issue #{} fixed? {}'.format(issue_id, text))
        return inner
    return catch


def unique(name):
    """
    Makes name unique. Used mainly if you do not want to pick old component, if exists.
    :param name: name of components
    :return: unique name
    """
    return '{0} - {1}'.format(name, rand())
