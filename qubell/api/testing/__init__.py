
import logging as log

from qubell.api.private.platform import QubellPlatform
from qubell.api.private.testing import BaseTestCase as SandBoxTestCase, environment, instance, values, workflow
from qubell.api.globals import QUBELL as qubell_config, PROVIDER as cloud_config
from qubell.api.tools import retry
import nose.plugins.attrib
import testtools

platform = QubellPlatform.connect(
                tenant=qubell_config['tenant'],
                user=qubell_config['user'],
                password=qubell_config['password'])
log.info('Authentication succeeded.')


class BaseComponentTestCase(SandBoxTestCase):
    parameters = dict(qubell_config.items() + cloud_config.items())
    apps = []

    @classmethod
    def environment(cls, organization):
        base_env = super(BaseComponentTestCase, cls).environment(organization)
        base_env['applications'] = cls.apps
        return base_env

    @classmethod
    def setUpClass(cls):
        cls.platform = platform
        super(BaseComponentTestCase, cls).setUpClass()

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