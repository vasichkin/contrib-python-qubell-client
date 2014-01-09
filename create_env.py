#!/usr/bin/python

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
import sys
import logging as log
from qubell.api.private.platform import QubellPlatform, Auth
from qubell.api.private.manifest import Manifest



"""
Example shows how to configure environment from scratch.
To use this script, setup environmnt variables or modify defauls (see bellow) 

Environment variables:
QUBELL_USER, QUBELL_PASSWORD - user to access qubell
QUBELL_API - url to qubell platform
QUBELL_ORG - name of organization to use. Will be created if not exists.

PROVIDER, REGION, JCLOUDS_IDENTITY, JCLOUDS_CREDENTIALS - credentials for amazon ec2. (will create provider)


To run script, set up environment variables and run script by:

python create_env.py

"""

user = os.environ.get('QUBELL_USER', 'user')
password = os.environ.get('QUBELL_PASSWORD', 'password')
api = os.environ.get('QUBELL_API', 'https://express.qubell.com')
org = os.environ.get('QUBELL_ORG', 'organization')
zone = os.environ.get('QUBELL_ZONE','')

provider = os.environ.get('PROVIDER', 'aws-ec2')
region = os.environ.get('REGION', 'us-east-1')
identity = os.environ.get('JCLOUDS_IDENTITY')
credentials = os.environ.get('JCLOUDS_CREDENTIALS')


__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__version__ = "1.0.13"
__email__ = "vkhomenko@qubell.com"


cloud_access = {
      "provider": provider,
      "usedEnvironments": [],
      "ec2SecurityGroup": "default",
      "providerCopy": provider,
      "name": "generated-provider-for-tests",
      "jcloudsIdentity": identity,
      "jcloudsCredential": credentials,
      "jcloudsRegions": region
    }


def start():
# Here we check existance of given credentials and create services if needed
    print "Creating ENV"
    exit = 0
    if not user:
        log.error('No username provided. Set QUBELL_USER env')
        exit = 1
    if not password:
        log.error('No password provided. Set QUBELL_PASSWORD env')
        exit = 1
    if not api:
        log.error('No api url provided. Set QUBELL_API env')
        exit = 1

    if exit:
        sys.exit(1)

# Setup access
    auth = Auth(user=user, password=password, tenant=api)

# Initialize platform and check access
    platform = QubellPlatform(auth=auth)
    assert platform.authenticate()
    print "Authorization passed"
# Initialize organization
    organization = platform.organization(name=org)
    print "Using orgainzation %s" % org

    if zone: # Need to run tests against zones. Create env for each
        z = [x for x in organization.list_zones() if x['name'] == zone]
        if len(z):
            print "Using zone %s" % zone
            create_env(organization, z[0]['id'])

    create_env(organization)
    create_launcher_apps(organization)
    print "ENV created"

def create_env(organization, agent=None):
    print "creating ZONE: %s" % agent

# Add services
    key_service = organization.service(type='builtin:cobalt_secure_store', name='Keystore'+zone, zone=agent)
    print "Keystore service %s initialized" % key_service.name
    wf_service = organization.service(type='builtin:workflow_service', name='Workflow'+zone, zone=agent)
    print "Workflow service %s initialized" % wf_service.name
    shared_service = organization.service(type='builtin:shared_instances_catalog', name='BaseTestSharedService'+zone, parameters= {'configuration.shared-instances': '{}'}, zone=agent)
    print "Shared instance service %s initialized" % shared_service.name

# Create independent environment
    environment = organization.environment(name='default', default='true', zone=agent) #TODO: create own
    if agent:
        environment.set_backend(agent)
    environment.clean()
    print "Setting default env"

# Add services to environment
    environment.add_service(key_service)
    print "Added keystore service"
    environment.add_service(wf_service)
    print "Added workflow service"
    environment.add_service(shared_service)
    print "Added shared service"

    environment.add_policy(
        {"action": "provisionVms",
         "parameter": "publicKeyId",
         "value": key_service.regenerate()['id']})
    print "Keystore generated key"
# Add cloud provider
    provider = organization.provider(name='test-provider', parameters=cloud_access)
    environment.add_provider(provider)
    print "Added provider %s" % provider.name

def create_launcher_apps(org):
    man = """
application:
  components:
    empty:
      type: cobalt.common.Constants
      interfaces:
        int1:
          pin1: publish-signal(string)
      configuration:
        configuration.values:
          int1.pin1: "Hello"
"""

    manifest = Manifest(content=man)
    apps = ['marker', 'simple-cobalt', 'starter-java-web', 'webdriver-grid', 'hier-db', 'hier-main']
    for app in apps:
        print "creating app: %s" % app
        org.application(name=app, manifest=manifest)

    env = org.environment(name='default')
    env.add_marker('has-internet-access')
    env.add_property(name='sample-property-green', type='int', value='42')
    env.add_property(name='sample-property-red', type='string', value='sample-property red')
    policy = {'action': 'provisionVms',
              'parameter': 'vmIdentity',
              'value': 'ubuntu'}
    env.add_policy(policy)
start()
