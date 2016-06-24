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
from functools import wraps
import inspect
import logging as log
import os

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__email__ = "vkhomenko@qubell.com"


# Setup logging

log_opts={'format': '%(asctime)s %(levelname)s:%(name)s:%(message)s'}
if os.getenv('QUBELL_LOG_LEVEL', 'info') == 'debug':
    log_opts['level'] = log.INFO
else:
    log_opts['level'] = log.DEBUG

if os.getenv('QUBELL_LOG_TO_FILE'):
    log_opts['filename']=os.getenv('QUBELL_LOG_TO_FILE')
log.basicConfig(**log_opts)


def operations():
    """
    Class decorator stores all calls into list.
    Can be used until .invalidate() is called.
    :return: decorated class
    """
    def decorator(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):

            self = args[0]
            assert self.__can_use, "User operation queue only in 'with' block"

            def defaults_dict():
                f_args, varargs, keywords, defaults = inspect.getargspec(func)
                defaults = defaults or []
                return dict(zip(f_args[-len(defaults)+len(args[1:]):], defaults[len(args[1:]):]))

            route_args = dict(defaults_dict().items() + kwargs.items())

            func(*args, **kwargs)
            self.operations.append((func.__name__, args[1:], route_args, ))

        return wrapped_func
    def decorate(clazz):

        for attr in clazz.__dict__:
            if callable(getattr(clazz, attr)):
                setattr(clazz, attr, decorator(getattr(clazz, attr)))
        def __init__(self):  # simple parameter-less constructor
            self.operations = []
            self.__can_use = True
        def invalidate(self):
            self.__can_use = False
        clazz.__init__ = __init__
        clazz.invalidate = invalidate
        return clazz
    return decorate