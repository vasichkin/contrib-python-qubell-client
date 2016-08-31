import os
from requests import RequestException
from qubell.api.private import exceptions
from qubell.api.private.manifest import Manifest
from qubell.api.private.platform import QubellPlatform
from qubell.api.provider.router import PrivatePath
import argparse
import logging
import time
import threading
import traceback
import sys


help_string="""
Create organization, application and launch monitor.
Set environment variables QUBELL_USER, QUBELL_PASSWORD, QUBELL_TENANT or use options to provide access to organization.

Example:
  python monitor.py -v -o myorg -u 'user@tonomi.com' -p 'MyPass' -t 'https://express.tonomi.com'

Performance monitor:
Monitor can act as continuous performance monitor. It measures time of monitor execution.
Use -x option to set number of monitor instances launched.
If set env var 'RESULT_DATADOG_API_KEY' and 'RESULT_DATADOG_APP_KEY' results will be pushed to datadog with name monitor.execution_duration.ZONE.
Also, results will be stored in 'perfrep.ZONE' file that file in csv format. Set 'RESULT_FILE' to ovveride file name.

"""
parser = argparse.ArgumentParser(description=help_string, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-v', '--verbose', help='Output INFO messages', action="store_true")
parser.add_argument('-vv', '--debug', help='Output DEBUG messages', action="store_true")
parser.add_argument('-c', '--create-only', help='Do not launch application, only create organization if not exists', action='store_true')
parser.add_argument('-d', '--dryrun', help='[Deprecated] Do not launch application, only create organization if not exists', action='store_true')
parser.add_argument('-u', '--user', help='Email of registered user on tonomi platform')
parser.add_argument('-p', '--password', help='Password for user')
parser.add_argument('-t', '--tenant', help='Url to platform')
parser.add_argument('-o', '--org', help='Organization name to use. Default is -=Monitor=-')
parser.add_argument('-z', '--zone', help='Zone name to use. Default is root zone')
parser.add_argument('-x', '--performance', help='Measure performance. Launch this number of instances in parallel and measure report time.')

loglevel = logging.WARNING
args = parser.parse_args()


if args.verbose:
    loglevel =logging.INFO
elif args.debug:
    loglevel =logging.DEBUG

#logger = logging.getLogger("qubell.stories")
logging.getLogger().setLevel(loglevel)

user = args.user or os.getenv('QUBELL_USER')
password = args.password or os.getenv('QUBELL_PASSWORD')
tenant = args.tenant or os.getenv('QUBELL_TENANT')
organization = args.org or os.getenv('QUBELL_ORGANIZATION') or '-=Monitor=-'
zone_name = args.zone or os.getenv('QUBELL_ZONE')


def log_exception(exc_class, exc, tb):
    logging.info('Got exception: %s' % exc)
    logging.info('Class: %s' % exc_class)
    logging.info('Trace: %s' % traceback.format_tb(tb))
    logging.error('Got exception while executing: %s' % exc)


def prepare_monitor(tenant=tenant, user=user, password=password, organization=organization, zone_name=zone_name):
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

    destroy_interval = "100000"  # ms, keep it as a string

    def __init__(self, org=None, app=None, env=None):
        if not all([org, app, env]):
            self.platform, org_id, app_id, env_id = prepare_monitor()
            self.org = self.platform.organizations[org_id]
            self.env = self.org.environments[env_id]
            self.app = self.org.applications[app_id]
        else:
            self.app = app
            self.org = org
            self.env = env
        self.status = False
        self.start_time = 0
        self.end_time = 0

    def launch(self, timeout=2):
        """
        Hierapp instance, with environment dependencies:
        - can be launched within short timeout
        - auto-destroys shortly
        """
        self.start_time = time.time()
        self.end_time = time.time()
        instance = self.app.launch(environment=self.env)
        time.sleep(2) # Instance need time to appear in ui

        assert instance.running(timeout=timeout), "Monitor didn't get Active state"
        launched = instance.status == 'Active'
        instance.reschedule_workflow(workflow_name='destroy', timestamp=self.destroy_interval)
        assert instance.destroyed(timeout=timeout), "Monitor didn't get Destroyed after short time"
        stopped = instance.status == 'Destroyed'
        instance.force_remove()
        self.end_time = time.time()
        self.status = launched and stopped

    def download_key(self):
        """
        Private key can be downloaded from environment
        """
        try:
            key = self.env.get_default_private_key()
        except RequestException:
            assert False, "Key cannot be downloaded outside"
        assert "RSA PRIVATE KEY" in key, "Key downloaded, but doesn't look as rsa key"

    def clone(self):
        """
        Do not initialize again since everything is ready to launch app.
        :return: Initialized monitor instance
        """
        return Monitor(org=self.org, app=self.app, env=self.env)



class LaunchThread(threading.Thread):
    def __init__(self, flow):
        super(LaunchThread, self).__init__()
        self.flow = flow

    def run(self):
        try:
            self.flow.launch(timeout=10)
        except:
            log_exception(*sys.exc_info())

    def __getattr__(self, key):
        return self.flow.__getattribute__(key)

class PerformanceMonitor(object):
    def __init__(self, monitor, count=5):
        """
        Launch N instances of monitor, measure execution time
        :param n: This number of monitors should be started
        :return:
        """
        self.count = count
        self.monitors = []
        self.statuses = []
        self.exec_time = []
        for x in range(0, int(count)):
            self.monitors.append(LaunchThread(monitor.clone()))

    def launch(self):
        for mon in self.monitors:
            mon.start()

        for mon in self.monitors:
            mon.join()
            self.statuses.append(mon.status)
            self.exec_time.append(mon.end_time - mon.start_time)

def publish_results(value):
    dd_api_key = os.environ.get('RESULT_DATADOG_API_KEY')
    dd_app_key = os.environ.get('RESULT_DATADOG_APP_KEY')
    file = os.environ.get('RESULT_FILE', 'perfrep.%s' % zone_name)


    if dd_api_key and dd_app_key:
        logging.info('Publishing results: %s' % value)
        from datadog import initialize, api
        now = time.time()
        initialize(api_key=dd_api_key, app_key=dd_app_key)
        api.Metric.send(metric='monitor.execution_duration.%s' % zone_name, points=(now, value), tags=["stack:dev", "tenant:staging"])

    if file:
        logging.info('Saving to file: %s' % value)
        f = open(file, 'w')
        f.write('seconds\n')
        f.write('%s\n' % value)
        f.close()



def main():
    if not user:
        parser.print_help()
        return 1
    errmsg = "User, password and tenant should be provided"
    assert password, errmsg
    assert tenant, errmsg
    status = -1

    if not(args.create_only or args.dryrun):
        mnt = Monitor()
        try:
            mnt.download_key()
            mnt.launch(timeout=10)
        except:
            log_exception(*sys.exc_info())

        status = 0 if mnt.status else 1

        if args.performance and status == 0:
            perfmnt = PerformanceMonitor(mnt, int(args.performance))
            perfmnt.launch()
            logging.info("statuses: %s" % perfmnt.statuses)
            logging.info("exec_times: %s" % perfmnt.exec_time)

            if all(perfmnt.statuses): # All monitors passed
                publish_results(int(sum(perfmnt.exec_time) / len(perfmnt.exec_time)))
                status = 0
            elif any(perfmnt.statuses):
                times = [x for x in perfmnt.exec_time if x > 0]
                publish_results(int(sum(times) / len(times)))
                status = 1
            else:
                publish_results(0)
                status = 2
    exit(status)
if __name__ == '__main__':
    main()