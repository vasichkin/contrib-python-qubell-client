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
import os
import unittest

from base import BaseTestCase
from qubell.api.private import exceptions
from qubell.api.provider.router import PrivatePath


class PlatformClassTest(BaseTestCase):

    @classmethod
    def register_user(cls, creds):
        email, password = creds
        payload = {"firstName": "Tester", "lastName": "Qubell", "email": email, "password": password,
                   "accept": "true"}
        try:
            router = PrivatePath(cls.platform._router.base_url, verify_codes=False)
            router.post_quick_sign_up(data=payload)
        except exceptions.ApiUnauthorizedError:
            pass

    def test_several_simultaneous_sessions(self):
        user, password = self.platform._router._creds
        minion_user, minion_password = minion_creds = ("minion."+user, password)
        self.register_user(minion_creds)
        minion_platform = self.platform.connect_to_another_user(minion_user, minion_password)
        ids = set([o.id for o in self.platform.organizations])
        minion_ids = set([o.id for o in minion_platform.organizations])
        assert ids != minion_ids
