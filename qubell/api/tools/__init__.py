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
import functools
import requests

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

def retry(tries=10, delay=1, backoff=2, retry_exception=None):
    """
    Retry "tries" times, with initial "delay", increasing delay "delay*backoff" each time.
    Without exception success means when function returns valid object.
    With exception success when no exceptions
    """
    assert tries > 0, "tries must be 1 or greater"
    catching_mode = bool(retry_exception)

    def deco_retry(f):
        @functools.wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay

            while mtries > 0:
                time.sleep(mdelay)
                mdelay *= backoff
                try:
                    rv = f(*args, **kwargs)
                    if not catching_mode and rv:
                        return rv
                except retry_exception:
                    pass
                else:
                    if catching_mode:
                        return rv
                mtries -= 1
                if mtries is 0 and not catching_mode:
                    return False
                if mtries is 0 and catching_mode:
                    return f(*args, **kwargs)  # extra try, to avoid except-raise syntax
                log.debug("{0} try, sleeping for {1} sec".format(tries-mtries, mdelay))
            raise Exception("unreachable code")
        return f_retry
    return deco_retry

def waitForStatus(instance, final='Active', accepted=None, timeout=(20, 10, 1)):
    started = time.time()
    info = '%s (%s)' % (instance.name, instance.id)

    if not accepted: accepted = ['Requested']

    if not isinstance(final, list): final = [final]

    final = [x.upper() for x in final]
    accepted = [x.upper() for x in accepted]

    @retry(3, 1, 2)  # max = 1 + 2 + 4 = 7 seconds + routes time
    def projection_update_monitor():
        """
        We have to deal with lag when projection updates instance.
        :return:
        """
        return instance.status.upper() not in final or instance._is_projection_updated_instance()
    projection_update_monitor()

    @retry(*timeout)  # ask status 20 times every 10 sec.
    def instance_status_waiter():
        cur_status = instance.status.upper()
        if cur_status in final:
            log.debug('Instance %s got expected status: %s, continue' % (info, cur_status))
            return True
        elif cur_status in accepted:
            log.debug('Instance %s status: %s, waiting...' % (info, cur_status))
            return False
        else:
            log.error('Instance %s got unexpected status: %s, exiting' % (info, cur_status))
            return True  # Let retry exit

    instance_status_waiter()
    # We here, means we reached timeout or got status we are waiting for.
    # Check it again to be sure
    cur_status = instance.status.upper()
    log.info('Instance %s final status: %s, expected status: %s, elapsed time: %s sec.' % (info, cur_status, final, int(time.time()-started)))
    instance._last_workflow_started_time = time.gmtime(time.time())
    if cur_status in final:
        return True
    elif cur_status in ['Error']:
        log.error("\n\n\nInstance didn't get one of {0} statuses, current status :'{1}'. \n\n"
                  "Instance: {2} ({3})\n"
                  "Organization: {4} ({5})\n"
                  "Timeout: {6} sec\n"
                  "---------------- Error Text ---------------------\n"
                  "{7}"
                  "\n-------------- Error Text End -----------------\n".format(
            final, cur_status,
            instance.name, instance.id,
            instance.organization.name, instance.organization.id,
            timeout[0]*timeout[1]*timeout[2],
            instance.error))

        log.debug("\n------------------ ActivityLog -----------------\n"
                  "%s"
                  "\n------------------ End of ActivityLog -----------------\n"
                  % instance.get_activitylog(severity=['ERROR', 'INFO']))
    else:
        log.error("\n\n\nInstance didn't get one of {0} statuses, current status :'{1}'. \n\n"
                  "Instance: {2} ({3})\n"
                  "Organization: {4} ({5})\n"
                  "Timeout: {6} sec\n\n".format(
            final, cur_status,
            instance.name, instance.id,
            instance.organization.name, instance.organization.id,
            timeout[0]*timeout[1]*timeout[2]))
        log.debug(instance.get_activitylog(severity=['ERROR', 'INFO']))
    return False


def dump(node):
    """ Dump initialized object structure to yaml
    """

    from qubell.api.private.platform import Auth, QubellPlatform
    from qubell.api.private.organization import Organization
    from qubell.api.private.application import Application
    from qubell.api.private.instance import Instance
    from qubell.api.private.revision import Revision
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
                        log.warn('No item %s in object %s' % (excl_item, x))
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

def load_env(file):
    """
    Generate environment used for 'org.restore' method
    :param file: env file
    :return: env
    """

    env = yaml.load(open(file))

    for org in env.get('organizations', []):
        if not org.get('applications'):
            org['applications'] = []

        if org.get('starter-kit'):
            kit_meta = get_starter_kit_meta(org.get('starter-kit'))
            for meta_app in get_applications_from_metadata(kit_meta):
                org['applications'].append(meta_app)

        if org.get('meta'):
            for meta_app in get_applications_from_metadata(org.get('meta')):
                org['applications'].append(meta_app)

        for app in org.get('applications', []):
            if app.get('file'):
                app['file'] = os.path.realpath(os.path.join(os.path.dirname(file), app['file']))
    return env


def get_applications_from_metadata(metadata, base_path=''):
    # Treat meta as file or link?
    if metadata.startswith('http'):
        meta = yaml.safe_load(requests.get(url=metadata).content)
    else:
        meta = yaml.safe_load(open(metadata).read())
    applications = []

    for app in meta['kit']['applications']:
        if 'http' in app['manifest']:
            applications.append({
                'name': app['name'],
                'url': app['manifest']})
        else:
            path = str(base_path) + '/' + str(app['manifest'])
            applications.append({
                'name': app['name'],
                'file': path})
    return applications



def patch_env(env, path, value):
        """ Set specified value to yaml path.
        Example:
        patch('application/components/child/configuration/__locator.application-id','777')
        Will change child app ID to 777
        """
        def pathGet(dictionary, path):
            for item in path.split("/"):
                dictionary = dictionary[item]
            return dictionary

        def pathSet(dictionary, path, value):
            path = path.split("/")
            key = path[-1]
            dictionary = pathGet(dictionary, "/".join(path[:-1]))
            dictionary[key] = value

        pathSet(env, path, value)
        return True

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


# See https://github.com/qubell/vermilion/blob/master/deployment/docker/ui/application.conf
starter_kits_url = "https://s3.amazonaws.com/qubell-static/starter-kits-metadata.yml"

def get_starter_kit_meta(name):
    """
    Extract metadata link for starter kit from platform configs. Starter kit available on add component - starter kit menu.
    Beware, config could be changed by deploy scripts during deploy.
    :param name: Name of starter kit
    :return: Link to metadata
    """
    kits = yaml.safe_load(requests.get(url=starter_kits_url).content)['kits']
    kits_meta_url = [x['metaUrl'] for x in kits if x['name'] == name]

    assert len(kits_meta_url)==1, "No component %s found in meta:\n %s" % (name, kits)
    meta = yaml.safe_load(requests.get(url=kits_meta_url[0]).content)['download_url']
    return meta

def get_manifest_from_meta(metaurl, name):
    """
    Extact manifest url from metadata url
    :param metaurl: Url to metadata
    :param name: Name of application to extract
    :return:
    """
    if 'http' in metaurl:
        kit = yaml.safe_load(requests.get(url=metaurl).content)['kit']['applications']
    else:
        kit = yaml.safe_load(open(metaurl).read())['kit']['applications']
    app_urls = [x['manifest'] for x in kit if x['name'] == name]
    assert len(app_urls) == 1
    return app_urls[0]