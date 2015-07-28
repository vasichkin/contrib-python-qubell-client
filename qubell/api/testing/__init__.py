
import logging as log

from qubell.api.private.platform import QubellPlatform
from qubell.api.private.testing import applications, environment, environments, instance, values, workflow
from qubell.api.private.testing.sandbox_testcase import SandBoxTestCase
from qubell.api.globals import QUBELL as qubell_config, PROVIDER as cloud_config
from qubell.api.tools import retry, rand
import nose.plugins.attrib
import testtools

try:
    from requests.packages import urllib3
    urllib3.disable_warnings()
except:
    pass
# Define what users import by *
__all__ = ['BaseComponentTestCase', 'applications', 'environment', 'environments', 'instance', 'values', 'workflow', 'eventually', 'attr', 'unique']


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
            cls.__lazy_platform = QubellPlatform.connect()
            log.info('Authentication succeeded.')
        return cls.__lazy_platform

class BaseComponentTestCase(SandBoxTestCase):
    parameters = dict(qubell_config.items() + cloud_config.items())
    apps = []

    @classmethod
    def environment(cls, organization):
        base_env = super(BaseComponentTestCase, cls).environment(organization)
        base_env['applications'] = cls.apps or cls.applications
        return base_env

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
    """
    def decorator(f):
        f = testtools.testcase.attr(args)(f)
        if not 'skip' in args:
            return nose.plugins.attrib.attr(*args, **kwargs)(f)
        # TODO: Should do something if test is skipped
    return decorator

def unique(name):
    """
    Makes name unique. Used mainly if you do not want to pick old component, if exists.
    :param name: name of components
    :return: unique name
    """
    return '{0} - {1}'.format(name, rand())
