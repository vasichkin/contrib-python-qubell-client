import os

__all__ = ['ZONE_NAME', 'DEFAULT_ENV_NAME',
           'DEFAULT_CLOUD_ACCOUNT_SERVICE', 'DEFAULT_WORKFLOW_SERVICE',
           'DEFAULT_SHARED_INSTANCE_CATALOG_SERVICE', 'DEFAULT_CREDENTIAL_SERVICE',
           'QUBELL', 'PROVIDER', 'PROVIDER_CONFIG']

# Global Zone
ZONE_NAME = os.getenv('QUBELL_ZONE')


class ZoneConstants(object):
    @staticmethod
    def zone_suffix(name=None):
        if not name:
            name = ZONE_NAME
        return ' at ' + name if name else ''

    def __init__(self, name):
        self.DEFAULT_ENV_NAME = 'default' + self.zone_suffix(name)
        self.DEFAULT_WORKFLOW_SERVICE = 'Default workflow service' + self.zone_suffix(name)
        self.DEFAULT_CREDENTIAL_SERVICE = 'Default credentials service' + self.zone_suffix(name)
        self.DEFAULT_CLOUD_ACCOUNT_SERVICE = 'CloudAccountService' + self.zone_suffix(name)
        self.DEFAULT_SHARED_INSTANCE_CATALOG_SERVICE = 'BaseTestSharedService' + self.zone_suffix(name)


global_zone_constants = ZoneConstants(ZONE_NAME)

zone_suffix = ZoneConstants.zone_suffix
# todo: one day remove lambdas everywhere
DEFAULT_ENV_NAME = lambda: global_zone_constants.DEFAULT_ENV_NAME
DEFAULT_WORKFLOW_SERVICE = lambda: global_zone_constants.DEFAULT_WORKFLOW_SERVICE
DEFAULT_CREDENTIAL_SERVICE = lambda: global_zone_constants.DEFAULT_CREDENTIAL_SERVICE
DEFAULT_CLOUD_ACCOUNT_SERVICE = lambda: global_zone_constants.DEFAULT_CLOUD_ACCOUNT_SERVICE
DEFAULT_SHARED_INSTANCE_CATALOG_SERVICE = lambda: global_zone_constants.DEFAULT_SHARED_INSTANCE_CATALOG_SERVICE

QUBELL = {
    'token': os.getenv('QUBELL_TOKEN'),
    'user': os.getenv('QUBELL_USER'),
    'password': os.getenv('QUBELL_PASSWORD'),
    'tenant': os.getenv('QUBELL_TENANT', 'http://localhost:9000').rstrip('/'),
    'organization': os.getenv('QUBELL_ORGANIZATION', None),
}

PROVIDER = {
    'provider_name': os.getenv('PROVIDER_NAME', DEFAULT_CLOUD_ACCOUNT_SERVICE()),
    'provider_type': os.getenv('PROVIDER_TYPE', 'aws-ec2'),
    'provider_identity': os.getenv('PROVIDER_IDENTITY', 'FAKE'),
    'provider_credential': os.getenv('PROVIDER_CREDENTIAL', 'FAKE'),
    'provider_region': os.getenv('PROVIDER_REGION', 'us-east-1'),
    'provider_security_group': os.getenv('PROVIDER_SECURITY_GROUP', '')
}

PROVIDER_CONFIG = {
    'configuration.provider': PROVIDER['provider_type'],
    'configuration.legacy-regions': PROVIDER['provider_region'],
    'configuration.endpoint-url': '',
    'configuration.legacy-security-group': '',
    'configuration.identity': PROVIDER['provider_identity'],
    'configuration.credential': PROVIDER['provider_credential']
}
