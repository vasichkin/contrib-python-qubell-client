import os

__author__ = 'dmakhno'

# Global setting for zone
ZONE_NAME = os.getenv('QUBELL_ZONE')
zone_suffix = lambda: ' at '+os.getenv('QUBELL_ZONE') if os.getenv('QUBELL_ZONE') else ''

DEFAULT_ENV_NAME = lambda: 'default'+zone_suffix()
DEFAULT_WORKFLOW_SERVICE = lambda: 'Default workflow service'+zone_suffix()
DEFAULT_CREDENTIAL_SERVICE = lambda: 'Default credentials service'+zone_suffix()
DEFAULT_CLOUD_ACCOUNT_SERVICE = lambda: 'CloudAccountService'+zone_suffix()
DEFAULT_SHARED_INSTANCE_CATALOG_SERVICE = lambda: 'BaseTestSharedService'+zone_suffix()


QUBELL = {
    'user': os.getenv('QUBELL_USER'),
    'password': os.getenv('QUBELL_PASSWORD'),
    'tenant': os.getenv('QUBELL_TENANT', 'http://localhost:9000'),
    'organization': os.getenv('QUBELL_ORGANIZATION'),
}

PROVIDER = {
    'provider_name': os.getenv('PROVIDER_NAME', DEFAULT_CLOUD_ACCOUNT_SERVICE()),
    'provider_type': os.getenv('PROVIDER_TYPE', 'aws-ec2'),
    'provider_identity': os.getenv('PROVIDER_IDENTITY', 'FAKE'),
    'provider_credential': os.getenv('PROVIDER_CREDENTIAL', 'FAKE'),
    'provider_region': os.getenv('PROVIDER_REGION', 'us-east-1'),
    'provider_security_group': os.getenv('PROVIDER_SECURITY_GROUP', '')
}