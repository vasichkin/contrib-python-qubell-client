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
from qubell.api.private.platform import QubellPlatform
from qubell.api.tools import load_env
from qubell.api.globals import QUBELL, PROVIDER_CONFIG
import logging


"""
Example shows how to configure environment from scratch.
To use this script, setup environmnt variables or modify defauls (see bellow) 

Environment variables:
QUBELL_USER, QUBELL_PASSWORD - user to access qubell
QUBELL_TENANT - url to qubell platform
QUBELL_ORGANIZATION - name of organization to use. Will be created if not exists.

PROVIDER_TYPE, PROVIDER_REGION, PROVIDER_IDENTITY, PROVIDER_CREDENTIAL - credentials for amazon ec2. (will create provider)


To run script, set up environment variables and run script by:

python restore_env.py envfile.env
or
./restore_env.py
Will use default.env

"""

if os.getenv('QUBELL_LOG_LEVEL', 'info') == 'debug':
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)

default_env = os.path.join(os.path.dirname(__file__), 'default.env')

if len(sys.argv)>1:
    env = sys.argv[1]
else:
    env = default_env

cfg = load_env(env)

# Patch configuration to include provider and org info
cfg['organizations'][0].update({'providers': [PROVIDER_CONFIG]})
if QUBELL['organization']:
    cfg['organizations'][0].update({'name': QUBELL['organization']})

platform = QubellPlatform.connect(user=QUBELL['user'], password=QUBELL['password'], tenant=QUBELL['tenant'])
print "Authorization passed"

print "Restoring env: %s" % env
platform.restore(cfg)
print "Restore finished"

