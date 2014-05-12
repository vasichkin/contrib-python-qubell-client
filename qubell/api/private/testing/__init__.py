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

__author__ = "Anton Panasenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"

__email__ = "apanasenko@qubell.com"

import unittest
import yaml
import logging as log
import re
import os

from functools import wraps

from qubell.api.globals import *
from qubell.api.private.service import system_application_types, COBALT_SECURE_STORE_TYPE, WORKFLOW_SERVICE_TYPE

import logging
import types

logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.ERROR)


def format_as_api(data):
    """
    Accepts {'default':{},}
    returns [{'name':'default',}]
    """
    result = []
    if isinstance(data, dict):
        for name, value in data.items():
            key = str(re.sub("[^a-zA-Z0-9_]", "", name))
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
            instance = None
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

            assert instance.run_workflow(name, parameters)
            if not instance.ready(timeout):
                self.fail(
                    "Instance %s isn't ready in appropriate time: %s with parameters %s and timeout %s" % (
                        instance.instanceId, name, parameters, timeout
                    )
                )
            func(*args, **kwargs)
        return wrapped_func
    return wrapper


def environment(envdata):
    """
    Class decorator that allows to run tests in sandbox against different Qubell environments.
    Each test method in suite is converted to <test_name>_on_environemnt_<environment_name>
    :param params: dict
    """
    #assert isinstance(params, dict), "@environment decorator should take 'dict' with environments"

    def copy(func, name=None):
        return types.FunctionType(func.func_code, func.func_globals, name=name,
                                  argdefs=func.func_defaults,
                                  closure=func.func_closure)

    def wraps_class(clazz):
        if "environments" in clazz.__dict__:
            log.warn("Class {0} environment attribute is overridden".format(clazz.__name__))
        params = format_as_api(envdata)
        clazz.environments = params

        methods = [method
                   for _, method in clazz.__dict__.items()
                   if isinstance(method, types.FunctionType) and method.func_name.startswith("test")]
        for env in params:
            if env['name'] != DEFAULT_ENV_NAME():
                env['name'] += '_for_%s' % clazz.__name__   # Each test class should have it's own set of envs.

        for method in methods:
            delattr(clazz, method.func_name)
            log.info("Test '{0}' multiplied per environment in {1}".format(method.func_name, clazz.__name__))
            for env in params:
                new_name = method.func_name + "_on_environment_" + env['name']
                setattr(clazz, new_name, copy(method, new_name))

        return clazz
    return wraps_class


# noinspection PyPep8Naming
def instance(byApplication):
    def wrapper(func):
        def get_environment_name(self, f):
            separator = "_on_environment_"
            if len(f.__name__.split(separator)) > 1:
                env = f.__name__.split(separator)[1]
            elif "_testMethodName" in self.__dict__ and len(self._testMethodName.split(separator)) > 1:
                env = self._testMethodName.split(separator)[1]
            else:
                env = DEFAULT_ENV_NAME()
            return env

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            self = args[0]
            env = get_environment_name(self, func)

            def find_by_application_name(app):
                for inst in self.instances:
                    if inst.application.name == app and inst.environment.name == env:
                        return inst
                return None

            func(*args + (find_by_application_name(byApplication),), **kwargs)
        return wrapped_func
    return wrapper


class BaseTestCase(unittest.TestCase):
    platform = None
    parameters = None
    sandbox = None
    environments = None

    @classmethod
    def environment(cls, organization):

        # Default add-on for every env
        addon = {"provider": {"name": cls.parameters['provider_name']},
                 "services":
                    [{"name": DEFAULT_CREDENTIAL_SERVICE()},
                     {"name": DEFAULT_WORKFLOW_SERVICE()}
                    ]}

        envs = cls.environments or [{"name": DEFAULT_ENV_NAME()},]

        for env in envs:
            env.update(addon)  # Add provider, keystore, workflow to every env.

        servs = [{"type": COBALT_SECURE_STORE_TYPE, "name": DEFAULT_CREDENTIAL_SERVICE()},
                 {"type": WORKFLOW_SERVICE_TYPE, "name": DEFAULT_WORKFLOW_SERVICE()}]

        provs = [{"name": cls.parameters['provider_name'],
                  "provider": cls.parameters['provider_type'],
                  "usedEnvironments": [],
                  "ec2SecurityGroup": "default",
                  "providerCopy": cls.parameters['provider_type'],
                  "jcloudsIdentity": cls.parameters['provider_identity'],
                  "jcloudsCredential": cls.parameters['provider_credential'],
                  "jcloudsRegions": cls.parameters['provider_region']}]
        insts = []

        # Add provider, keystore, workflow to every env.
        envs = cls.environments or [{"name": "default"},]
        for env in envs:
            env.update(addon)

        return {
            "organization": {"name": organization},
            "services": servs,
            "instances": insts,
            "cloudAccounts": provs,
            "environments": envs}


    @classmethod
    def timeout(cls):
        return 15

    @classmethod
    def setUpClass(cls):
        super(BaseTestCase, cls).setUpClass()

        if cls.parameters['organization']:
            cls.prepare(cls.parameters['organization'], cls.timeout())
        else:
            cls.prepare(cls.__name__, cls.timeout())

    @classmethod
    def tearDownClass(cls):
        if os.getenv("QUBELL_DEBUG", None) and not('false' in os.getenv("QUBELL_DEBUG", None)):
            log.info("QUBELL_DEBUG is ON\n DO NOT clean sandbox")
        else:
            cls.clean()
        super(BaseTestCase, cls).tearDownClass()

    @classmethod
    def prepare(cls, organization, timeout=30):
        """ Create sandboxed test environment
        """
        log.info("\n\n\n---------------  Preparing sandbox...  ---------------")
        cls.sandbox = SandBox(cls.platform, cls.environment(organization))
        cls.organization = cls.sandbox.make()
        cls.regular_instances = []
        cls.service_instances = []


        def launch_in_env(app, env):
            environment = cls.organization.environments[env['name']]
            application = cls.organization.applications[app['name']]
            parameters = app.get('parameters', {})
            settings = app.get('settings', {})
            instance = cls.organization.create_instance(application=application,
                                                        environment=environment,
                                                        parameters=parameters,
                                                        **settings)
            if app.get('add_as_service', False):
                environment.add_service(instance)
            cls.sandbox.sandbox["instances"].append({
                "id": instance.instanceId,
                "name": instance.name,
            })
            return instance

        def check_instances(instances):
            for instance in instances:
                if not instance.ready(timeout=timeout):
                    error = instance.error.strip()

                    # TODO: if instance fails to start during tests, add proper unittest log
                    if os.getenv("QUBELL_DEBUG", None) and not('false' in os.getenv("QUBELL_DEBUG", None)):
                        pass
                    else:
                        cls.clean()
                    assert not error, "Instance %s didn't launch properly and has error '%s'" % (instance.instanceId, error)
                    assert False, "Instance %s is not ready after %s minutes and stop on timeout" % (instance.instanceId, timeout)

        # launch service instances first
        for app in cls.sandbox['applications']:
            for env in cls.sandbox['environments']:
                if app.get('launch', True) and app.get('add_as_service', False):
                    log.info("Sandbox: starting service in app: %s, env: %s" % (app['name'], env['name']))
                    cls.service_instances.append(launch_in_env(app, env))
        check_instances(cls.service_instances)

        # then launch non-service instances
        for app in cls.sandbox['applications']:
            for env in cls.sandbox['environments']:
                if app.get('launch', True) and not app.get('add_as_service', False):
                    log.info("Sandbox: starting instance in app: %s, env: %s" % (app['name'], env['name']))
                    cls.regular_instances.append(launch_in_env(app, env))
        check_instances(cls.regular_instances)
        
        cls.instances = cls.service_instances + cls.regular_instances
        log.info("\n---------------  Sandbox prepared  ---------------\n\n")


    @classmethod
    def clean(cls, timeout=10):
        log.info("\n---------------  Cleaning sandbox  ---------------")
        def destroy_instances(instances):
            for instance in instances:
                instance.destroy()
                if not instance.destroyed(timeout):
                    log.error(
                        "Instance was not destroyed properly {0}: {1}", instance.id, instance.name)

        destroy_instances(cls.regular_instances)
        destroy_instances(cls.service_instances)
        log.info("\n---------------  Sandbox cleaned  ---------------\n")

    # noinspection PyPep8Naming
    def findByApplicationName(self, name):
        for instance in self.instances:
            if instance.application.name == name:
                return instance


class SandBox(object):
    def __init__(self, platform, sandbox):
        self.sandbox = sandbox
        self.platform = platform
        self.organization = self.platform.organization(name=self.sandbox["organization"]["name"])
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
