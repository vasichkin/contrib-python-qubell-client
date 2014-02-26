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

from qubell.api.tools import is_bson_id
from qubell.api.private import exceptions
from qubell import deprecated


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
        self._id_name_list()

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

    @deprecated('Entity List is updated via _id_name_list, this is dangerous to use this method')
    def add(self, entry):
        self._list.append(IdName(entry.id, entry.name))

    @deprecated('Entity List is updated via _id_name_list, this is dangerous to use this method')
    def remove(self, entry):
        self._list.remove(IdName(entry.id, entry.name))

    def _id_name_list(self):
        """Returns list of IdName tuple"""
        raise AssertionError("'_id_name_list' method should be implemented in subclasses")
    def _get_item(self, id_name):
        """Returns item, having only id"""
        raise AssertionError("'_get_item' method should be implemented in subclasses")

class QubellEntityList(EntityList):
    """
    This is base class for entities that depends on organization
    """

    def __init__(self, list_json_method, organization):
        self.organization = organization
        self.organizationId = self.organization.organizationId
        self.json = list_json_method
        EntityList.__init__(self)


    def _id_name_list(self):
        # start = time.time()
        self._list = [IdName(ent['id'], ent['name']) for ent in self.json()]
        # end = time.time()
        # elapsed = int((end - start) * 1000.0)
        # log.debug(
        #     "  Listing Time: Fetching List {0} took {elapsed} ms".format(self.__class__.__name__, elapsed=elapsed))

    # noinspection PyUnresolvedReferences
    def _get_item(self, id_name):
        assert self.base_clz, "Define 'base_clz' in constructor or override this method"
        start = time.time()
        entity = self.base_clz(organization=self.organization, id=id_name.id)
        end = time.time()
        elapsed = int((end - start) * 1000.0)
        log.debug(
            "  Listing Time: Fetching {0}='{name}' with id={id} took {elapsed} ms".format(self.base_clz.__name__,
                                                                                          id=id_name.id,
                                                                                          name=id_name.name,
                                                                                          elapsed=elapsed))
        return entity


class Auth(object):
    @deprecated(msg="use global from qubell.api.provider.ROUTER as router instead")
    def __init__(self, user, password, tenant):
        self.user = user
        self.password = password
        self.tenant = tenant

        # TODO: parse tenant to generate api url
        self.api = tenant


class Context(Auth):
    @deprecated(msg="use global from qubell.api.provider.ROUTER as router instead")
    def __init__(self, user, password, api):
        Auth.__init__(self, user, password, api)
