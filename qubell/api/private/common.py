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
from collections import namedtuple
import logging as log
import time
from qubell.api.provider.router import InstanceRouter

from qubell.api.tools import is_bson_id, retry
from qubell.api.private import exceptions
from qubell import deprecated
import pprint

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__version__ = ""
__email__ = "vkhomenko@qubell.com"

IdName = namedtuple('IdName', 'id,name')


class Entity(object):
    def __eq__(self, other):
        return self.id == other.id
    def __ne__(self, other):
        return not self.__eq__(other)


class EntityList(object):
    """ Class to store qubell objects information (Instances, Applications, etc)
    Gives convenient way for searching and manipulating objects, it caches only id and names.
    """

    def __init__(self):
        self._list = []
        try:
            self._id_name_list()
        except KeyError:
            raise exceptions.ApiNotFoundError("Object not found")

    def __iter__(self):
        self._id_name_list()
        for i in self._list:
            yield self._get_item(i)

    def __len__(self):
        self._id_name_list()
        return len(self._list)

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, str(self._list))

    def __getitem__(self, item):
        self._id_name_list()
        if isinstance(item, int): return self._get_item(self._list[item])
        elif isinstance(item, slice): return [self._get_item(i) for i in self._list[item]]

        found = [x for x in self._list if (is_bson_id(item) and x.id == item) or x.name == item]
        if len(found) is 0:
            raise exceptions.NotFoundError("None of '{1}' in {0}".format(self.__class__.__name__, item))
        return self._get_item(found[-1])

    def __contains__(self, item):
        self._id_name_list()
        if isinstance(item, str) or isinstance(item, unicode):
            if is_bson_id(item):
                return item in [item.id for item in self._list]
            else:
                return item in [item.name for item in self._list]
        return item.id in [item.id for item in self._list]

    def add(self, entry):
        log.warn('Entity List is updated via _id_name_list, this is dangerous to use this method')
        self._list.append(IdName(entry.id, entry.name))

    def remove(self, entry):
        log.warn('Entity List is updated via _id_name_list, this is dangerous to use this method')
        self._list.remove(IdName(entry.id, entry.name))

    def _id_name_list(self):
        """Returns list of IdName tuple"""
        raise AssertionError("'_id_name_list' method should be implemented in subclasses")

    def _get_item(self, id_name):
        """Returns item, having only id"""
        raise AssertionError("'_get_item' method should be implemented in subclasses")


class QubellEntityList(EntityList, InstanceRouter):
    """
    This is base class for entities that depends on organization
    """

    def __init__(self, list_json_method, organization=None):
        if organization:
            self.organization = organization
            self.organizationId = self.organization.organizationId
        self.json = list_json_method
        EntityList.__init__(self)


    def _id_name_list(self):
        self._list = []
        for ent in self.json():
            if ent.get('id'):  # Normal behavior
                self._list.append(IdName(ent['id'], ent['name']))
            elif ent.get('instanceId'):  # public api in use
                self._list.append(IdName(ent['instanceId'], ent['name']))
            else:
                pass
                # We have NO id on element. That could be submodule info
                # Investigate and fix this.

    # noinspection PyUnresolvedReferences
    def _get_item(self, id_name):
        assert self.base_clz, "Define 'base_clz' in constructor or override this method"
        try:
            entity = self.base_clz(organization=self.organization, id=id_name.id)
        except AttributeError:
            entity = self.base_clz(id=id_name.id)
        if isinstance(entity, InstanceRouter):
            entity.init_router(self._router)
        return entity


class Auth(object):
    @deprecated(msg="use global from qubell.api.provider.ROUTER as router instead")
    def __init__(self, user, password, tenant=None, api=None):
        self.user = user
        self.password = password
        self.tenant = tenant or api

        # TODO: parse tenant to generate api url
        self.api = tenant


class Response(dict):
    """
    Base class for response object. This class provides retry capabilities for Router queries.
    Class mimics dict() in usage.
    If got KeyError, retry query until got key or timeout.

    Note, nested dicts (dict(dict(...)) are not processed separately, as KeyError thrown for internal dict, forcing us to retry.
    """
    tries_count = 0
    data = None

    def __init__(self, data_fn, retry_query=True):
        self.data_fn = data_fn
        self.retry = retry_query


    def get_data_retry(self, key, tries=10, delay=1, backoff=1.1, retry_exception=(KeyError, exceptions.NotFoundError)):
        """
        Retry "tries" times, with initial "delay", increasing delay "delay*backoff" each time.
        Without exception success means when function returns valid object.
        With exception success when no exceptions
        """
        mtries, mdelay = tries, delay
        log.debug("Response: Start retry (%s, %s, %s) for key: %s" % (tries, delay, backoff, key))
        while mtries > 0:
            mdelay *= backoff
            try:
                return self.get_key(key)
            except retry_exception:
                pass

            mtries -= 1
            if mtries <= 0:
                return self.get_key(key) # extra try, to avoid except-raise syntax
            log.debug("{0} try, sleeping for {1} sec".format(tries-mtries, mdelay))
            self.tries_count = tries-mtries
            time.sleep(mdelay)
        raise Exception("unreachable code")

    def get_key(self, key):
        log.debug("Response: Getting key: %s" % key)
        self.data = self.data_fn()
        resp = Response(data_fn=self.data_fn.__getitem__(key), retry_query=self.retry)
        print resp
        return resp

    def get_data(self):
        self.data = self.data_fn()
        return self.data

    def __iter__(self):
        for x in self.data:
            yield x

    def __repr__(self):
        return pprint.pformat(self.get_data())

    def __str__(self):
        return pprint.pformat(self.get_data())

    def __getitem__(self, key):
        print "GetItem %s" % key
        if self.retry:
            return self.get_data_retry(key)
        else:
            return self.get_key(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __call__(self, *args, **kwargs):
        return self.get_data()

