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
__version__ = "1.0.13"
__email__ = "apanasenko@qubell.com"

import unittest
import yaml
import logging as log

from functools import wraps

from qubell.api.private.instance import Instance
from qubell.api.private.manifest import Manifest


def values(names):
    def wrapper(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            instance = args[1]

            def findReturnValues(rvalues):
                for k, v in rvalues.iteritems():
                    if isinstance(v, dict):
                        findReturnValues(v)
                    elif isinstance(v, unicode):
                        #TODO fix return values
                        try:
                            value = yaml.safe_load(v)
                        except Exception:
                            import re
                            try:
                                value = yaml.safe_load(re.sub(r': ([:/?a-zA-Z_0-9-\.]+)', r': "\1"', v))
                            except Exception:
                                value = None

                        if not isinstance(value, dict) and k in names.keys():
                            kwargs.update({names[k]: value})
                        elif isinstance(value, dict):
                            findReturnValues(value)
                    elif k in names.keys():
                        kwargs.update({names[k]: v})

            findReturnValues(instance.returnValues)

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

            assert instance.runWorkflow(name, parameters)
            if not instance.ready(timeout):
                self.fail(
                    "Instance %s don't ready after run workflow: %s with parameters %s and timeout %s".format(
                        instance.instanceId, name, parameters, timeout
                    )
                )
            func(*args, **kwargs)
        return wrapped_func
    return wrapper


def environment(params):
    def copy(func, name=None):
        import types

        if not name:
            name = func.func_name

        return types.FunctionType(func.func_code, func.func_globals, name=name,
                                  argdefs=func.func_defaults,
                                  closure=func.func_closure)

    def wraps_class(clazz):
        clazz.environments = params

        methods = filter(lambda (name, func): name.startswith("test"), clazz.__dict__.items())

        for name_method, _ in methods:
            delattr(clazz, name_method)

        for name in params.keys():
            for name_method, method in methods:
                new_name = name_method + "_on_environment_" + name
                method = copy(method, new_name)
                setattr(clazz, new_name, method)

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
                env = "default"
            return env

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            self = args[0]
            env = get_environment_name(self, func)

            def find_by_application_name(app):
                for inst in self.instances:
                    if inst.applicationName == app and inst.environmentName == env:
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
        import re
        if cls.environments:
            envs = {}
            for name, value in cls.environments.items():
                envs.update({str(re.sub("[^a-zA-Z0-9_]", "", name)): value})
        else:
            envs = {"default": {}}

        return {
            "organization": {"name": organization},
            "services": [
                {"type": 'builtin:cobalt_secure_store', "name": 'Keystore', "parameters": "{}"},
                {"type": 'builtin:workflow_service', "name": 'Workflow', "parameters": {'configuration.policies': '{}'}}
            ],
            "instances": [],
            "cloudAccounts": [{
                                  "name": cls.parameters['provider_name'],
                                  "provider": cls.parameters['provider_type'],
                                  "usedEnvironments": [],
                                  "ec2SecurityGroup": "default",
                                  "providerCopy": cls.parameters['provider_type'],
                                  "jcloudsIdentity": cls.parameters['provider_identity'],
                                  "jcloudsCredential": cls.parameters['provider_credential'],
                                  "jcloudsRegions": cls.parameters['provider_region']
            }],
            "environments": envs}

    @classmethod
    def apps(cls):
        return []

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
    def prepare(cls, organization, timeout=15):
        cls.sandbox = SandBox(cls.platform, cls.environment(organization))
        cls.organization = cls.sandbox.make()

        cls.instances = []
        for app in cls.sandbox['applications']:
            for env in cls.sandbox['environments']:
                if app.get('launch', True):
                    environment_id = cls.organization.environment(name=env).id
                    instance = cls.organization.application(name=app['name']).launch(environmentId=environment_id)
                    cls.instances.append(instance)
                    cls.sandbox.sandbox["instances"].append({"id": instance.instanceId, "name": instance.name})

        for instance in cls.instances:
            if not instance.ready(timeout=timeout):
                cls.sandbox.clean()
                assert False, "Instance %s don't ready".format(instance.instanceId)

    @classmethod
    def tearDownClass(cls):
        super(BaseTestCase, cls).tearDownClass()
        cls.clean()

    @classmethod
    def clean(cls):
        if cls.sandbox:
            cls.sandbox.clean()

    # noinspection PyPep8Naming
    def findByApplicationName(self, name):
        for instance in self.instances:
            if instance.applicationName == name:
                return instance


class SandBox(object):
    def __init__(self, platform, sandbox):
        self.sandbox = sandbox
        self.platform = platform
        self.organization = self.platform.organization(name=self.sandbox["organization"]["name"])

    @staticmethod
    def load_yaml(platform, yaml_file):
        return SandBox(platform, yaml.safe_load(yaml_file))

    def __service(self, environment, service_data):
        service = self.organization.service(type=service_data["type"], name=service_data["name"],
                                            parameters=(service_data["parameters"] or "{}"))
        environment.add_service(service)
        if 'builtin:cobalt_secure_store' in service_data["type"]:
            key_id = service.regenerate()['id']
            environment.add_policy({
                "action": "provisionVms",
                "parameter": "publicKeyId",
                "value": key_id
            })
        service_data["id"] = service.serviceId

    def __cloud_account(self, environment, provider):
        cloud = self.organization.provider(parameters=provider, name=provider["name"])
        environment.add_provider(cloud)
        provider["id"] = cloud.providerId

    def __application(self, app):
        manifest = Manifest(**{k: v for k, v in app.iteritems() if k in ["content", "url", "file"]})
        application = self.organization.application(manifest=manifest, name=app["name"])
        app["id"] = application.applicationId

    def make(self):
        log.info("preparing sandbox...")

        for name, env in self.sandbox["environments"].items():
            environment = self.organization.environment(name=name)
            environment.clean()

            for service in self.sandbox["services"] + env.get('services', []):
                self.__service(environment, service)

            for provider in self.sandbox["cloudAccounts"] + env.get('cloudAccounts', []):
                self.__cloud_account(environment, provider)

            for police in env.get('policies', []):
                environment.policyAdd(police)

            for app in self.sandbox["applications"]:
                self.__application(app)

        log.info("sandbox prepared")

        return self.organization

    def clean(self, timeout=3):
        log.info("cleaning sandbox...")
        for instanceData in self.sandbox['instances']:
            instance = Instance(context=self.platform.context, id=instanceData["id"])
            instance.destroy()
            if not instance.destroyed(timeout):
                log.error(
                    "Instance was not destroyed properly {0}: {1}".format(instanceData["id"], instanceData["name"])
                )
        log.info("sandbox cleaned")

    def __check_environment_name(self, name):
        import re
        re.sub("")

    def __getitem__(self, name):
        if name in self.sandbox:
            return self.sandbox[name]
        else:
            return None