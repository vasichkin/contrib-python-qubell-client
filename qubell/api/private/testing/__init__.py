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
import yaml
import logging as log
import re
import sys

from functools import wraps

import logging

from nose.plugins.skip import SkipTest
from qubell.api.globals import ZoneConstants

logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.ERROR)


def norm(name):
    return str(re.sub("[^a-zA-Z0-9_]+", "_", name))

def format_as_api(data):
    """
    Accepts {'default':{},}
    returns [{'name':'default',}]
    """
    result = []
    if isinstance(data, dict):
        for name, value in data.items():
            key = norm(name)
            value.update({'name': name})
            result.append(value)
        return result
    else:
        return data

def values(names):
    """
    Method decorator that allows inject return values into method parameters.
    It tries to find desired value going deep. For convinience injects list with only one value as value.
    :param names: dict of "value-name": "method-parameter-name"
    """
    def wrapper(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            if len(args)>1:
                instance=args[1]
            else:
                instance = kwargs['instance']

            def findReturnValues(rvalues):
                for k, v in rvalues.iteritems():
                    if isinstance(v, dict):
                        findReturnValues(v) #go deep, to find desired name
                    if k in names.keys():
                        if isinstance(v,list) and len(v)==1:
                            kwargs.update({names[k]: v[0]})
                        else:
                            kwargs.update({names[k]: v})

            findReturnValues(instance.returnValues)

            #ensure all names was set
            missing_params = [k for k, v in names.items() if v not in kwargs]
            if missing_params:
                raise AttributeError("Parameters {0} for '{1}' were not found".format(missing_params, func.__name__), missing_params)

            func(*args, **kwargs)
        return wrapped_func
    return wrapper


def workflow(name, parameters=None, timeout=10):
    if not parameters:
        parameters = dict()

    def wrapper(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            self = args[0]
            instance = args[1]

            assert instance.run_workflow(name=name, parameters=parameters)
            if not instance.ready(timeout):
                self.fail(
                    "Instance %s isn't ready in appropriate time: %s with parameters %s and timeout %s" % (
                        instance.instanceId, name, parameters, timeout
                    )
                )
            func(*args, **kwargs)
        return wrapped_func
    return wrapper


def _parameterize(source_case, cases):
        '''This generates the classes (in the sense that it's a generator.)
        '''

        def clean_class(source):
            import types
            test_methods = [method.__name__ for _, method in source.__dict__.items()
                                if isinstance(method, types.FunctionType) and method.func_name.startswith("test")]
            setattr(source_case, '__name__', 'Source')
            setattr(source_case, 'className', 'Source')
            for test in test_methods:
                delattr(source_case, test)

        # Multiply classes per environment
        if len(cases):
            case_mod = sys.modules[source_case.__module__]
            case_name = norm(source_case.__name__)
            attrs = dict(source_case.__dict__)
            clean_class(source_case)

            for i, env in enumerate(cases.keys()):
                env_suffix = norm(env)
                updated_case = type('{0}_{1}'.format(case_name, env_suffix), (source_case,), attrs)
                setattr(updated_case, 'className', env_suffix)
                setattr(case_mod, updated_case.__name__, updated_case)
                if i > 0:
                    # this attribute helps to spread in time environment setup
                    updated_case._wait_for_prev = i

                # If ZONE_NAME set we should change env names to corresponding. So, new would be created in zone or cached by existing by name
                # fixme: this attribute should endswith _name
                updated_case.current_environment = env + ZoneConstants.zone_suffix()
                updated_case.environments = format_as_api({updated_case.current_environment: cases[env]})
                updated_case.source_name = case_name
                yield updated_case
        else:
            yield source_case


def parameterize(source_case, cases={}):
    return list(_parameterize(source_case, cases))

def environment(params):
    def wraps_class(clazz):
        parameterize(source_case=clazz, cases=params)

        return clazz
    return wraps_class
environments = environment

def applications(appsdata):
    """
    Class decorator that allows to crete applications and start instances there.
    If used with environment decorator, instances would be started for every env.
    :param appdata: list
    """
    def wraps_class(clazz):
        if "applications" in clazz.__dict__:
            log.warn("Class {0} applications attribute is overridden".format(clazz.__name__))
        clazz.applications=clazz.applications+appsdata # This needed to pass to environment
        return clazz
    return wraps_class
application = applications

# noinspection PyPep8Naming
def instance(byApplication):
    def wrapper(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            self = args[0]

            ins = self.find_by_application_name(byApplication)
            if not ins.running():
                raise SkipTest("Instance %s not in Running state" % ins.name)
            func(*args + (ins,), **kwargs)
        return wrapped_func
    return wrapper


class SandBox(object):
    def __init__(self, platform, sandbox):
        self.sandbox = sandbox
        self.platform = platform
        self.organization_name = sandbox["organization"]["name"]
        if self.organization_name not in self.platform.organizations:
            import time
            import random
            pause = random.randint(1, 10)
            time.sleep(pause*15)

        self.organization = self.platform.organization(name=self.organization_name)
        self.sandbox['instances'] = sandbox.get('instances', [])


    @staticmethod
    def load_yaml(platform, yaml_file):
        return SandBox(platform, yaml.safe_load(yaml_file))

    def make(self):
        self.organization.restore(self.sandbox)
        return self.organization

    def clean(self):
        # TODO: need cleaning mechanism
        pass

    def __check_environment_name(self, name):
        import re
        re.sub("")

    def __getitem__(self, name):
        if name in self.sandbox:
            return self.sandbox[name]
        else:
            return None

from sandbox_testcase import SandBoxTestCase
BaseTestCase = SandBoxTestCase  # for compatibility
