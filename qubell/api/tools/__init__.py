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
import re

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"

from random import randrange
import yaml
import time
import os
import logging as log


def rand():
    return str(randrange(1000, 9999))

def cpath(file):
    return os.path.join(os.path.dirname(__file__), file)

def retry(tries=5, delay=3, backoff=2, retry_exception=None):
    """
    Retry "tries" times, with initial "delay", increasing delay "delay*backoff" each time.
    Without exception success means when function returns valid object.
    With exception success when no exceptions
    """

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay

            while mtries > 0:
                try:
                    rv = f(*args, **kwargs)
                except retry_exception:
                    rv = False
                else:
                    #if we expect to catch something, but f, doesn't return anything
                    #another word, nice indicator if no exceptions
                    if retry_exception:
                        rv = True
                if rv:
                    return True
                mtries -= 1
                log.debug("...{0} sleeping for {1} s in retry".format(f.__name__,mdelay))
                time.sleep(mdelay)
                mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry

def waitForStatus(instance, final='Running', accepted=None, timeout=(20, 10, 1)):
    if not accepted: accepted = ['Requested']

    log.debug('Waiting status: %s' % final)
    import time

    @retry(3, 1, 2) # max = 1 + 2 + 4 = 7 seconds + routes time
    def projection_update_monitor():
        """
        We have to deal with lag when projection updates instance.
        :return:
        """
        return instance.status != final and instance._is_projection_updated_instance()
    projection_update_monitor()

    @retry(*timeout) # ask status 20 times every 10 sec.
    def instance_status_waiter():
        cur_status = instance.status
        if cur_status in final:
            log.info('Got status: %s, continue' % cur_status)
            return True
        elif cur_status in accepted:
            log.info('Current status: %s, waiting...' % cur_status)
            return False
        else:
            log.error('Got unexpected instance status: %s' % cur_status)
            return True  # Let retry exit

    instance_status_waiter()
    # We here, means we reached timeout or got status we are waiting for.
    # Check it again to be sure

    cur_status = instance.status
    log.info('Final status: %s' % cur_status)
    instance._last_workflow_started_time = time.gmtime(time.time())
    if cur_status in final:
        return True
    else:
        log.error("Didn't get '{0}' stopped in '{1}' with error '''{2}'''".format(final, cur_status, instance.error))
        return False

def dump(node):
    """ Dump initialized object structure to yaml
    """

    from qubell.api.private.platform import Auth, QubellPlatform
    from qubell.api.private.organization import Organization
    from qubell.api.private.application import Application
    from qubell.api.private.instance import Instance
    from qubell.api.private.revision import Revision
    from qubell.api.private.provider import Provider
    from qubell.api.private.environment import Environment
    from qubell.api.private.zone import Zone
    from qubell.api.private.manifest import Manifest

    # Exclude keys from dump
    # Format: { 'ClassName': ['fields', 'to', 'exclude']}
    exclusion_list = {
        Auth: ['cookies'],
        QubellPlatform:['auth', ],
        Organization: ['auth', 'organizationId', 'zone'],
        Application: ['auth', 'applicationId', 'organization'],
        Instance: ['auth', 'instanceId', 'application'],
        Manifest: ['name', 'content'],
        Revision: ['auth', 'revisionId'],
        Provider: ['auth', 'providerId', 'organization'],
        Environment: ['auth', 'environmentId', 'organization'],
        Zone: ['auth', 'zoneId', 'organization'],
    }

    def obj_presenter(dumper, obj):
        for x in exclusion_list.keys():
            if isinstance(obj, x): # Find class
                fields = obj.__dict__.copy()
                for excl_item in exclusion_list[x]:
                    try:
                        fields.pop(excl_item)
                    except:
                        print 'No item %s in object %s' % (excl_item, x)
                return dumper.represent_mapping('tag:yaml.org,2002:map', fields)
        return dumper.represent_mapping('tag:yaml.org,2002:map', obj.__dict__)


    noalias_dumper = yaml.dumper.Dumper
    noalias_dumper.ignore_aliases = lambda self, data: True

    yaml.add_representer(unicode, lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:str', value))
    yaml.add_multi_representer(object, obj_presenter)
    serialized = yaml.dump(node, default_flow_style=False, Dumper=noalias_dumper)
    return serialized

def full_dump(org):
    """ TODO:  Dump all that reports by api
    """
    pass

def lazyproperty(fn):
    """
    Decorator, reads property once, on first use.
    :param fn:
    :return:
    """
    attr_name = '_lazy_' + fn.__name__
    @property
    def _lazyprop(self):
        if attr_name not in self.__dict__:  # don't use hasattr, due to call of __getattr__
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazyprop


def lazy(func):
    def lazyfunc(*args, **kwargs):
        wrapped = lambda x : func(*args, **kwargs)
        wrapped.__name__ = "lazy-" + func.__name__
        return wrapped
    return lazyfunc

def is_bson_id(bson_id):
    id_pattern = u'[A-Fa-f0-9]{24}'
    return re.match(id_pattern, unicode(bson_id))