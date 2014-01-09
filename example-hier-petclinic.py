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

__author__ = "Vasyl Khomenko"
__copyright__ = "Copyright 2013, Qubell.com"
__license__ = "Apache"
__version__ = "1.0.13"
__email__ = "vkhomenko@qubell.com"

""" Example shows how to run hierarchical petclinic using qubellclient """

import requests

from qubell.api.private.platform import QubellPlatform, Auth
from qubell.api.private.manifest import Manifest


# Provide credentials and link to api to use
context = Auth(user="tester@qubell.com", password="password", tenant="https://api.qubell.com")

# Amazon's credentials. Needed to setup environment
KEY =        "AAAA"
SECRET_KEY = "BBBB"


# New organization needs environment to be set up.
# Here we create all environment, needed to run petclinic
def prepare_env(org):
    """ Example shows how to configure environment from scratch """

    # Add services
    key_service = org.service(type='builtin:cobalt_secure_store', name='Keystore')
    wf_service = org.service(type='builtin:workflow_service', name='Workflow', parameters='{}')

    # Add services to environment
    env = org.environment(name='default')
    env.clean()
    env.add_service(key_service)
    env.add_service(wf_service)
    env.add_policy(
        {"action": "provisionVms",
         "parameter": "publicKeyId",
         "value": key_service.regenerate()['id']})

    # Add cloud provider account
    access = {
      "provider": "aws-ec2",
      "usedEnvironments": [],
      "ec2SecurityGroup": "default",
      "providerCopy": "aws-ec2",
      "name": "test-provider",
      "jcloudsIdentity": KEY,
      "jcloudsCredential": SECRET_KEY,
      "jcloudsRegions": "us-east-1"
    }
    prov = org.provider(access)
    env.add_provider(prov)
    return org.organizationId


# Define manifest. We take example from documentation.
# TODO: make manifests accessible from docs.qubell.com
app_manifest = Manifest(url="https://raw.github.com/qubell/contrib-python-qubell-client/master/qm/hierarchical-main.yml")
db_manifest = Manifest(url="https://raw.github.com/qubell/contrib-python-qubell-client/master/qm/hierarchical-db.yml")


# Initialize our qubell platform
platform = QubellPlatform(context=context)

# Try to login
assert platform.authenticate()
print "Authenticate passed"

# Create new organization
org = platform.organization(name="python-qubellclient")

# Use existing organization
# org = platform.organization(id="524f3028e4b0b12cd4de2759")

# Init environment (find by name "default")
env = org.environment(name='default')

# If env is not set up yet, do it. (dirty check)
if not env.json()['areProvidersAvailable']:
   prepare_env(org)
   print "Prepearing environment"
print "Environment initialized"

""" We need to create child application that runs database, using db_manifest.
After, wee need to create parent application that will use our DB application as a child"""

# Create new application for DB
db_app = org.application(manifest=db_manifest, name='database')
print "Creating DB app"

# Create main application. First, we need to patch manifest, telling where to find database. Place id of created db-application
app_manifest.patch('application/components/db/configuration/__locator.application-id', db_app.applicationId)
main_app = org.application(manifest=app_manifest, name='main_site')
print "Creating MAIN app"

# Now we can launch application.
instance = main_app.launch()
print "Launching..."

# This way we wait instance to came up in 15 minutes or break.
assert instance.ready(15)
print "Instance Running"

# Check our app could be accessed via http
site = requests.get(instance.returnValues['endpoint.url'])
assert site.text.find('PetClinic :: a Spring Framework demonstration')
print "Checking site: alive"

ha_resp = requests.get(instance.returnValues['endpoint.ha']+'/;csv').text

# Parse CSV from ha proxy status
def parse_csv(csv):
    head = 'pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max'.split(',')
    line = [x for x in csv.split('\n') if 'application,BACKEND' in x][0].split(',')
    return dict(zip(head, line))

# Check we have one worker node
assert parse_csv(ha_resp)['act'] == '1'
print 'Checking num of nodes in haproxy: 1'

# Now launch scale-up
instance.run_workflow(name='manage.scale-up')
print "Executing manage.scale-up..."
assert instance.ready(15)
print "Instance Ready"


# Check our app alive
site = requests.get(instance.returnValues['endpoint.url'])
assert site.text.find('PetClinic :: a Spring Framework demonstration')
print "Checking site: alive"

# Check we have two worker nodes
ha_resp = requests.get(instance.returnValues['endpoint.ha']+'/;csv').text
assert parse_csv(ha_resp)['act'] == '2'
print 'Checking num of nodes in haproxy: 2'


# launch scale-down
instance.run_workflow(name='manage.scale-down')
print "Executing manage.scale-down..."
assert instance.ready(15)
print "Instance Ready"

# Check our app still alive
site = requests.get(instance.returnValues['endpoint.url'])
assert site.text.find('PetClinic :: a Spring Framework demonstration')
print "Checking site: alive"

# Check we have one worker nodes
ha_resp = requests.get(instance.returnValues['endpoint.ha']+'/;csv').text
assert parse_csv(ha_resp)['act'] == '1'
print 'Checking num of nodes in haproxy: 1'
