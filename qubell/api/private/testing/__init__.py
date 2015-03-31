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
import sys

from functools import wraps

from qubell.api.globals import *
from qubell.api.private.service import COBALT_SECURE_STORE_TYPE, WORKFLOW_SERVICE_TYPE, CLOUD_ACCOUNT_TYPE
from qubell.api.private.exceptions import NotFoundError

import logging

import requests
from nose.plugins.skip import SkipTest

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
def _parameterize(source_case, cases, tests):
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

        # Add tests to class if we got tests param
        for test_name, test_method in tests.items():
            setattr(source_case, test_name, test_method)

        # Multiply classes per environment
        if len(cases):
            case_mod = sys.modules[source_case.__module__]
            case_name = norm(source_case.__name__)
            attrs = dict(source_case.__dict__)
            clean_class(source_case)

            for env in cases.keys():
                env_name = norm(env)
                updated_case = type('{0}_{1}'.format(case_name, env_name), (source_case,), attrs)
                setattr(updated_case, 'className', env_name)
                setattr(case_mod, updated_case.__name__, updated_case)
                updated_case.current_environment = env_name
                updated_case.source_name = case_name
                yield updated_case
        else:
            yield source_case


def parameterize(source_case, cases={}, tests={}):
    return list(_parameterize(source_case, cases, tests))

def environment(params):
    def wraps_class(clazz):
        # If QUBELL_ZONE set we should change env names to corresponding. So, new would be created in zone or cached by existing by name
        zone = os.getenv('QUBELL_ZONE')
        parameterize(source_case=clazz, cases=params)
        if zone:

            for key, value in params.items():
                name = '{0} at {1}'.format(key, zone)
                params[name] = params.pop(key)
        clazz.environments = format_as_api(params)

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


class BaseTestCase(unittest.TestCase):
    platform = None
    parameters = None
    sandbox = None
    environments = None
    applications = []
    instances = []
    current_environment = DEFAULT_ENV_NAME()

    setup_error=None
    setup_error_trace=None

    @classmethod
    def environment(cls, organization):
        provider_config = {'configuration.provider': cls.parameters['provider_type'],
                           'configuration.legacy-regions': cls.parameters['provider_region'],
                           'configuration.endpoint-url': '',
                           'configuration.legacy-security-group': '',
                           'configuration.identity': cls.parameters['provider_identity'],
                           'configuration.credential': cls.parameters['provider_credential']}

        # Old style components tests declared name as 'test-provider'. Now we cannot add this provider to env where another provider set.
        if (cls.parameters['provider_name']=='test-provider') or (not(cls.parameters['provider_name'])):
            prov = PROVIDER['provider_name']
        else:
            prov = cls.parameters['provider_name']

        # Default add-on for every env
        addon = {"services":
                    [{"name": DEFAULT_CREDENTIAL_SERVICE()},
                     {"name": DEFAULT_WORKFLOW_SERVICE()},
                     {"name": prov}
                    ]}

        servs = [{"type": COBALT_SECURE_STORE_TYPE, "name": DEFAULT_CREDENTIAL_SERVICE()},
                 {"type": WORKFLOW_SERVICE_TYPE, "name": DEFAULT_WORKFLOW_SERVICE()},
                 {"type": CLOUD_ACCOUNT_TYPE, "name": prov, "parameters": provider_config}]

        insts = []

        # Add provider, keystore, workflow to every env.
        envs = cls.environments or [{"name": DEFAULT_ENV_NAME()},]
        for env in envs:
            env.update(addon)

        return {
            "organization": {"name": organization},
            "services": servs,
            "instances": insts,
            "environments": envs,
            "applications": cls.applications}

    @classmethod
    def timeout(cls):
        return 15

    @classmethod
    def setUpClass(cls):
        super(BaseTestCase, cls).setUpClass()

        log.info("\n\n\n---------------  Preparing sandbox...  ---------------")
        try:
            cls.service_instances = []
            cls.regular_instances = []
            org = cls.parameters.get('organization') or getattr(cls, 'source_name', False) or cls.__name__
            cls.sandbox = SandBox(cls.platform, cls.environment(org))
            cls.organization = cls.sandbox.make()

            ### Start ###
            # If 'meta' in sandbox, restore applications that comes in meta before.
            if cls.__dict__.get('meta'):
                cls.upload_metadata_applications(cls.__dict__.get('meta'))

            services_to_start = [x for x in cls.sandbox['applications'] if x.get('add_as_service', False)]
            instances_to_start = [x for x in cls.sandbox['applications'] if x.get('launch', True) and not x.get('add_as_service', False)]

            for appdata in services_to_start:
                ins = cls.launch_instance(appdata)
                cls.service_instances.append(ins)
                cls.organization.environments[cls.current_environment].add_service(ins)
            cls.check_instances(cls.service_instances)

            for appdata in instances_to_start:
                cls.regular_instances.append(cls.launch_instance(appdata))
            cls.check_instances(cls.regular_instances)

        except BaseException as e:
            import sys
            cls.setup_error = sys.exc_info()

            import traceback
            cls.setup_error_trace = traceback.format_exc()
            log.critical(e)
            log.critical(cls.setup_error_trace)
        log.info("\n---------------  Sandbox prepared  ---------------\n\n")

    @classmethod
    def tearDownClass(cls):
        log.info("\n---------------  Cleaning sandbox  ---------------")

        cls.destroy_instances(cls.regular_instances)
        cls.destroy_instances(cls.service_instances)
        cls.regular_instances = []
        cls.service_instances = []

        log.info("\n---------------  Sandbox cleaned  ---------------\n")
        super(BaseTestCase, cls).tearDownClass()

    def setUp(self):
        if self.setup_error:
            raise self.setup_error[1], None, self.setup_error[2]

    @classmethod
    def upload_metadata_applications(cls, metadata):
        cls.organization.set_applications_from_meta(metadata)

    @classmethod
    def launch_instance(cls, appdata):
        application = cls.organization.applications[appdata['name']]
        environment = cls.organization.environments[cls.current_environment]
        instance = cls.organization.create_instance(application=application,
                                                    environment=environment,
                                                    parameters=appdata.get('parameters', {}),
                                                    **appdata.get('settings',{}))
        return instance

    @classmethod
    def check_instances(cls, instances):
        for instance in instances:
            if not instance.running(timeout=cls.timeout()):
                error = instance.error.strip()

                # TODO: if instance fails to start during tests, add proper unittest log
                if os.getenv("QUBELL_DEBUG", None) and not('false' in os.getenv("QUBELL_DEBUG", None)):
                    pass

                assert not error, "Instance %s didn't launch properly and has error '%s'" % (instance.instanceId, error)
                assert False, "Instance %s is not ready after %s minutes and stop on timeout" % (instance.instanceId, cls.timeout())

    @classmethod
    def destroy_instances(cls, instances):
        if os.getenv("QUBELL_DEBUG", None) and not('false' in os.getenv("QUBELL_DEBUG", None)):
            log.info("QUBELL_DEBUG is ON\n DO NOT clean sandbox")
        else:
            for instance in instances:
                instance.destroy()
                if not instance.destroyed(cls.timeout()):
                    log.error("Instance was not destroyed properly {0}: {1}", instance.id, instance.name)

    def find_by_application_name(self, name):
        for inst in self.regular_instances+self.service_instances:
            if inst.application.name == name:
                return inst
        raise NotFoundError

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
