import os
from requests import RequestException
from qubell.api.private import exceptions
from qubell.api.private.manifest import Manifest
from qubell.api.private.platform import QubellPlatform
from qubell.api.provider.router import PrivatePath
import argparse
import logging


help_string="""
Create organization, application and launch monitor.
Set environment variables QUBELL_USER, QUBELL_PASSWORD, QUBELL_TENANT or use options to provide access to organization.

Example:
  python monitor.py -v -o myorg -u 'user@tonomi.com' -p 'MyPass' -t 'https://express.tonomi.com'
"""
parser = argparse.ArgumentParser(description=help_string, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-v', '--verbose', help='Increase output verbosity', action='store_true')
parser.add_argument('-c', '--create-only', help='Do not launch application, only create organization if not exists', action='store_true')
parser.add_argument('-d', '--dryrun', help='[Deprecated] Do not launch application, only create organization if not exists', action='store_true')
parser.add_argument('-u', '--user', help='Email of registered user on tonomi platform')
parser.add_argument('-p', '--password', help='Password for user')
parser.add_argument('-t', '--tenant', help='Url to platform')
parser.add_argument('-o', '--org', help='Organization name to use. Default is -=Monitor=-')
parser.add_argument('-z', '--zone', help='Zone name to use. Default is root zone')


args = parser.parse_args()
if args.verbose:
    logger = logging.getLogger("qubell.stories")
    logging.getLogger().setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)

user = args.user or os.getenv('QUBELL_USER')
password = args.password or os.getenv('QUBELL_PASSWORD')
tenant = args.tenant or os.getenv('QUBELL_TENANT')
organization = args.org or os.getenv('QUBELL_ORGANIZATION') or '-=Monitor=-'
zone = args.zone or os.getenv('QUBELL_ZONE')

def prepare_monitor(tenant, user, password, organization, zone_name=None):
    """
    :param tenant: tenant url
    :param user: user's email
    :param password: user's password
    :param zone_name: (optional) zone_name
    :return:
    """
    router = PrivatePath(tenant, verify_codes=False)

    payload = {
        "firstName": "AllSeeingEye",
        "lastName": "Monitor",
        "email": user,
        "password": password,
        "accept": "true"
    }
    try:
        router.post_quick_sign_up(data=payload)
    except exceptions.ApiUnauthorizedError:
        pass

    platform = QubellPlatform.connect(tenant=tenant, user=user, password=password)
    org = platform.organization(name=organization)
    if zone_name:
        zone = org.zones[zone_name]
    else:
        zone = org.zone
    env = org.environment(name="Monitor for "+zone.name, zone=zone.id)
    env.init_common_services(with_cloud_account=False, zone_name=zone_name)

    # todo: move to env
    policy_name = lambda policy: "{}.{}".format(policy.get('action'), policy.get('parameter'))
    env_data = env.json()
    key_id = [p for p in env_data['policies'] if 'provisionVms.publicKeyId' == policy_name(p)][0].get('value')

    with env as envbulk:
        envbulk.add_marker('monitor')
        envbulk.add_property('publicKeyId', 'string', key_id)

    monitor = Manifest(file=os.path.join(os.path.dirname(__file__), './monitor_manifests/monitor.yml'))
    monitor_child = Manifest(file=os.path.join(os.path.dirname(__file__), './monitor_manifests/monitor_child.yml'))

    org.application(manifest=monitor_child, name='monitor-child')
    app = org.application(manifest=monitor, name='monitor')

    return platform, org.id, app.id, env.id



class Monitor(object):
    """
    This the minimum required to ensure that system works and configured properly.
    """

    destroy_interval = "10000"  # ms, keep it as a string

    def __init__(self, tenant, user, password, organization, zone):
        self.platform, org_id, app_id, env_id = prepare_monitor(tenant=tenant, user=user, password=password, organization=organization, zone_name=zone)
        self.org = self.platform.organizations[org_id]
        self.env = self.org.environments[env_id]
        self.app = self.org.applications[app_id]

    def launch_monitor(self):
        """
        Hierapp instance, with environment dependencies:
        - can be launched within short timeout
        - auto-destroys shortly
        """
        instance = self.app.launch(environment=self.env)
        assert instance.running(timeout=2), "Monitor didn't get Active state"
        instance.reschedule_workflow(workflow_name='destroy', timestamp=self.destroy_interval)
        assert instance.destroyed(timeout=1), "Monitor didn't get Destroyed after short time"
        instance.force_remove()

    def download_key(self):
        """
        Private key can be downloaded from environment
        """
        try:
            key = self.env.get_default_private_key()
        except RequestException:
            assert False, "Key cannot be downloaded outside"
        assert "RSA PRIVATE KEY" in key, "Key downloaded, but doesn't look as rsa key"

def main():
    if not user:
        parser.print_help()
        return 1
    errmsg = "User, password and tenant should be provided"
    assert password, errmsg
    assert tenant, errmsg
    mnt = Monitor(tenant=tenant, user=user, password=password, organization=organization, zone=zone)
    if not(args.create_only or args.dryrun):
        mnt.download_key()
        mnt.launch_monitor()

if __name__ == '__main__':
    main()