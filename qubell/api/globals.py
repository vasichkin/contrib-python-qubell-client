import os

__author__ = 'dmakhno'

# Global setting for zone
ZONE_NAME = os.getenv('QUBELL_ZONE')
zone_suffix = lambda: ' at '+ZONE_NAME if ZONE_NAME else ''

DEFAULT_ENV_NAME = lambda: 'default'+zone_suffix()
DEFAULT_WORKFLOW_SERVICE = lambda: 'Default workflow service'+zone_suffix()
DEFAULT_CREDENTIAL_SERVICE = lambda: 'Default credentials service'+zone_suffix()

QUBELL = {
    'user': os.getenv('QUBELL_USER'),
    'password': os.getenv('QUBELL_PASSWORD'),
    'tenant': os.getenv('QUBELL_TENANT', 'http://localhost:9000'),
    'organization': os.getenv('QUBELL_ORGANIZATION'),
}

PROVIDER = {
    'provider_name': os.getenv('PROVIDER_NAME', 'test-provider'),
    'provider_type': os.getenv('PROVIDER_TYPE', 'aws-ec2'),
    'provider_identity': os.getenv('PROVIDER_IDENTITY', 'FAKE'),
    'provider_credential': os.getenv('PROVIDER_CREDENTIAL', 'FAKE'),
    'provider_region': os.getenv('PROVIDER_REGION', 'us-east-1')
}