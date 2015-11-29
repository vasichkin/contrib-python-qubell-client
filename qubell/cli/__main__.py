import logging as log
import os
from os.path import join, basename
import re
import sys
import time
import itertools

import click
from colorama import Fore, Style
import yaml

from qubell.api.globals import QUBELL, PROVIDER
from qubell.api.tools import load_env, waitForStatus
from qubell.api.private.instance import InstanceList
from qubell.api.private.platform import QubellPlatform
from qubell.api.private.exceptions import NotFoundError, ApiError
from qubell.api.private.manifest import Manifest
from qubell.api.private.service import system_application_types, CLOUD_ACCOUNT_TYPE
from qubell.cli.yamlutils import DuplicateAnchorLoader


PROVIDER_CONFIG = None


log.getLogger().setLevel(getattr(log, os.getenv('QUBELL_LOG_LEVEL', 'error').upper()))


STATUS_COLORS = {
    "ACTIVE": "GREEN",
    "RUNNING": "GREEN",
    "LAUNCHING": "BLUE",
    "DESTROYING": "BLUE",
    "EXECUTING": "BLUE",
    "FAILED": "RED",
    "ERROR": "RED",
    "DESTROYED": "LIGHTBLACK_EX",
}

SEVERITIES = ['ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE']

SEVERITY_COLORS = {
    "ERROR": "RED",
    "WARNING": "YELLOW",
    "INFO": "BLACK",
    "DEBUG": "LIGHTBLACK_EX",
    "TRACE": "LIGHTBLACK_EX"
}


def _color_status(status):
    return _color(STATUS_COLORS.get(status.upper(), "BLACK"), status)


def fmt_time(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", t)


def _columns(iterable, key, value):
    key_length = max(map(lambda o: len(str(key(o))), iterable) + [0])
    for item in iterable:
        key_string = str(key(item))
        value_string = str(value(item))
        click.echo(key_string + (key_length - len(key_string)) * " " + "  " + value_string)


def _map_opt(value_or_none, function):
    if value_or_none is None:
        return None
    else:
        return function(value_or_none)


@click.group()
@click.option("--tenant", default="", help="Tenant url to use, QUBELL_TENANT by default")
@click.option("--user", default="", help="User to use, QUBELL_USER by default")
@click.option("--password", default="", help="Password to use, QUBELL_PASSWORD by default")
@click.option("--organization", default="", help="Organization to use, QUBELL_ORGANIZATION by default")
@click.option("--debug/--no-debug", default=False, help="Debug mode, also QUBELL_LOG_LEVEL can be used.")
def cli(debug, **kwargs):
    """
    CLI for tonomi.com using contrib-python-qubell-client

    To enable completion:

      eval "$(_NOMI_COMPLETE=source nomi)"
    """
    global PROVIDER_CONFIG

    if debug:
        log.basicConfig(level=log.DEBUG)
        log.getLogger("requests.packages.urllib3.connectionpool").setLevel(log.DEBUG)
    for (k, v) in kwargs.iteritems():
        if v:
            QUBELL[k] = v
    PROVIDER_CONFIG = {
        'configuration.provider': PROVIDER['provider_type'],
        'configuration.legacy-regions': PROVIDER['provider_region'],
        'configuration.endpoint-url': '',
        'configuration.legacy-security-group': '',
        'configuration.identity': PROVIDER['provider_identity'],
        'configuration.credential': PROVIDER['provider_credential']
    }

    class UserContext(object):

        def __init__(self):
            self.platform = None

        def get_platform(self):
            if not self.platform:
                self.platform = QubellPlatform.connect(
                    tenant=QUBELL["tenant"],
                    user=QUBELL["user"],
                    password=QUBELL["password"])
            return self.platform

    ctx = click.get_current_context()
    ctx.obj = UserContext()


def _get_platform():
    return click.get_current_context().obj.get_platform()


@cli.command(name="list-apps")
def list_apps():
    _platform = _get_platform()

    org = _platform.get_organization(QUBELL["organization"])
    for app in org.applications:
        instances = app.instances
        by_status = {}
        by_status['DESTROYED'] = len(app.destroyed_instances)
        for instance in instances:
            key = instance.status.upper()
            by_status[key] = by_status.get(key, 0) + 1
        for (status, color) in STATUS_COLORS.iteritems():
            by_status[status] = _color(color, str(by_status.get(status, 0)))
        click.echo(app.id + " " +
                   "(%(ACTIVE)s/%(LAUNCHING)s/%(EXECUTING)s/%(DESTROYING)s/%(FAILED)s/%(DESTROYED)s) " % by_status +
                   _color("BLUE", app.name))


def _color(color, text):
    if not isinstance(text, basestring):
        text = str(text)
    return getattr(Fore, color) + text + Style.RESET_ALL


@cli.command(name="export-app")
@click.option("--recursive/--non-recursive", default=False, help="Export also dependencies.")
@click.option("--output-dir", default="", help="Output directory for manifest files, current by default.")
@click.option("--version", default=None, help="Manifest version to export.")
@click.argument("application")
def export_app(recursive, application, output_dir, version):
    platform = _get_platform()

    def _save_manifest(app, manifest, filename=None):
        filename = filename or "%s-v%s.yml" % (app.name, manifest["version"])
        if output_dir:
            filename = join(output_dir, filename)
        click.echo("=> " + filename, nl=False)
        with open(filename, "w") as f:
            f.write(manifest["manifest"])

    def _child_applications(manifest_yml):
        locator_attr = "__locator.application-id"
        if isinstance(manifest_yml, dict):
            if "__locator.application-id" in manifest_yml:
                return [manifest_yml[locator_attr]]
            else:
                result = []
                for value in manifest_yml.itervalues():
                    result.extend(_child_applications(value))
                return result
        elif isinstance(manifest_yml, list):
            result = []
            for item in manifest_yml:
                result.extend(_child_applications(item))
            return result
        else:
            return []

    org = platform.get_organization(QUBELL["organization"])

    def do_export(current_app, current_version=None):
        click.echo("Saving " + _color("BLUE", current_app) + " ", nl=False)
        try:
            current_app = org.get_application(current_app)
            if not current_version:
                manifest = current_app.get_manifest_latest()
            else:
                manifest = current_app.get_manifest(current_version)
            click.echo(_color("BLUE", "v" + str(manifest["version"])) + " ", nl=False)
            _save_manifest(current_app, manifest)
            click.echo(_color("GREEN", " OK"))
            if recursive:
                app_names = _child_applications(yaml.load(manifest["manifest"], DuplicateAnchorLoader))
                for app_name in app_names:
                    do_export(app_name)
        except (IOError, NotFoundError):
            click.echo(_color("RED", " FAIL"))

    do_export(application, version)


@cli.command(name="import-app")
@click.argument("filenames", nargs=-1)
def import_app(filenames):
    platform = _get_platform()

    regex = re.compile(r"^(.*?)(-v(\d+)|)\.[^.]+$")
    for filename in filenames:
        click.echo("Importing " + filename, nl=False)
        match = regex.match(basename(filename))
        if not match:
            click.echo(_color("RED", "FAIL") + " unknown filename format")
            break
        app_name = regex.match(basename(filename)).group(1)
        click.echo(" => " + _color("BLUE", app_name) + " ", nl=False)
        org = platform.get_organization(QUBELL["organization"])
        try:
            app = org.get_application(app_name)
            click.echo(app.id + _color("RED", " FAIL") + " already exists")
            break
        except NotFoundError:
            pass
        try:
            with file(filename, "r") as f:
                app = org.application(name=app_name, manifest=Manifest(content=f.read()))
            click.echo(app.id + _color("GREEN", " OK"))
        except IOError as e:
            click.echo(_color("RED", " FAIL") + " " + e.message)
            break


@cli.command(name="create-org")
@click.argument("organization")
def create_org(organization):
    platform = _get_platform()

    click.echo(organization + " ", nl=False)
    try:
        org = platform.get_organization(organization)
        click.echo(_color("YELLOW", org.id) + " already exists")
        return 1
    except NotFoundError:
        try:
            org = platform.create_organization(organization)
            click.echo(_color("GREEN", org.id))
        except AssertionError:
            org = platform.get_organization(organization)
            click.echo(_color("YELLOW", org.id) + " still initializing")


@cli.command(name="init-ca")
@click.option("--type", default="", help="Provider name (for example, aws-ec2, openstack, etc)")
@click.option("--identity", default="", help="Provider identity or login, PROVIDER_IDENTITY by default")
@click.option("--credential", default="",
              help="Provider credential or secrete key or password, PROVIDER_CREDENTIAL by default")
@click.option("--region", default="", help="Provider region (for example, us-east-1), PROVIDER_REGION by default")
@click.option("--security-group", default="default", help="Default security group, \"default\" if not set")
@click.option("--environment", default="default", help="Account environment")
@click.argument("account_name")
def init_ca(account_name, environment, **kwargs):
    platform = _get_platform()
    global PROVIDER_CONFIG

    for (k, v) in kwargs.iteritems():
        if v:
            PROVIDER["provider_" + k] = v
    click.echo(account_name + " ", nl=False)
    org = platform.get_organization(QUBELL["organization"])

    def type_to_app(t):
        return org.applications[system_application_types.get(t, t)]
    env = org.get_environment(environment)
    try:
        cloud_account_service = org.service(
            name=account_name,
            application=type_to_app(CLOUD_ACCOUNT_TYPE),
            environment=env,
            parameters=PROVIDER_CONFIG)
        click.echo(_color("GREEN", cloud_account_service.id))
    except IOError:
        click.echo(_color("RED", "FAILED"))


@cli.command(name="restore-env")
@click.argument("environment")
def restore_env(environment):
    platform = _get_platform()
    global PROVIDER_CONFIG

    cfg = load_env(environment)
    # Patch configuration to include provider and org info
    cfg['organizations'][0].update({'providers': [PROVIDER_CONFIG]})
    if QUBELL['organization']:
        cfg['organizations'][0].update({'name': QUBELL['organization']})

    click.echo("Restoring env: " + _color("BLUE", environment) + " ", nl=False)
    try:
        platform.restore(cfg)
        click.echo(_color("GREEN", "OK"))
    except Exception as e:
        click.echo(_color("RED", "FAIL"))
        log.error("Failed to restore env", exc_info=e)


@cli.command("list-orgs")
def list_orgs():
    platform = _get_platform()
    for app in platform.organizations:
        click.echo(app.id + " " + _color("BLUE", app.name))


@cli.command("list-envs")
def list_envs():
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    for env in org.environments:
        status = env.isOnline and _color("GREEN", "ONLINE") or _color("RED", "FAILED")
        click.echo(env.id + " " + _color("BLUE", env.name) + " " + status, nl=False)
        if env.isDefault:
            click.echo(" " + _color("BLUE", "DEFAULT"))
        else:
            click.echo()


@cli.command("list-instances")
@click.option("--status", default="!DESTROYED",
              help="Filter by statuses, one of "
                   "REQUESTED, LAUNCHING, ACTIVE, EXECUTING, FAILED, DESTROYING, DESTROYED."
                   "Several statuses can be listed using comma. !STATUS_NAME to invert match.")
@click.argument("application", default=None, required=False)
def list_instances(application, status):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    filters = []
    for status_filter in status.split(","):
        if not status_filter:
            continue
        if status_filter[0] == "!":
            filters.append(lambda s: s.upper() != status_filter[1:].upper())
        else:
            def match(f):
                return lambda s: s.upper() == f.upper()
            filters.append(match(status_filter))
    if application:
        application = org.get_application(application)

    def list_instances_json():
        return org.list_instances_json(application=application)

    def list_destroyed_instances():
        return org.list_instances_json(application=application, show_only_destroyed=True)
    instance_candidates = \
        InstanceList(list_json_method=list_instances_json,
                     organization=org).init_router(platform._router)
    if "DESTROYED" in status.upper() or "!" in status:
        destroyed_candidates = \
            InstanceList(list_json_method=list_destroyed_instances,
                         organization=org).init_router(platform._router)
        instance_candidates = itertools.chain(instance_candidates, destroyed_candidates)
    for inst in instance_candidates:
        if not any(map(lambda p: p(inst.status), filters)):
            continue
        _describe_instance_short(inst)


def _describe_instance_short(inst):
    click.echo(inst.id + " " +
               _color("BLUE", inst.name) + " " +
               _color(STATUS_COLORS.get(inst.status.upper(), "BLACK"), inst.status.upper()))


@cli.command("describe-instance")
@click.argument("instance")
def describe_instance(instance, localtime=True):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    inst = org.get_instance(instance)
    _describe_instance(inst, localtime)


def _calc_title(items, template="%s (%s)"):
    for value in items:
        if value['id'] != value['name']:
            value['_title'] = template % (value['id'], value['name'])
        else:
            value['_title'] = value['id']


def _describe_instance(inst, localtime=None):
    click.echo("Instance    %s  %s  %s" % (inst.id, _color("BLUE", inst.name), _color_status(inst.status)))
    app = inst.application
    click.echo("Application %s  %s" % (app.id, _color("BLUE", app.name)))
    env = inst.environment
    click.echo("Environment " + env.id + "  " + _color("BLUE", env.name))
    time_f = localtime and time.localtime or time.gmtime
    click.echo("Launched    " + fmt_time(time_f(inst.createdAt / 1000)))
    if inst.destroyAt:
        click.echo("Destroy     " + fmt_time(time_f(inst.destroyAt / 1000)))
    else:
        click.echo("Destroy     " + "not scheduled")
    pad = "    "
    if inst.config:
        click.echo("Config: ")
        _calc_title(inst.config)
        _columns(inst.config, lambda o: pad + o['_title'], lambda o: pad + o['value'])
    if inst.endpoints:
        click.echo("Return values: ")
        _calc_title(inst.endpoints)
        _columns(inst.endpoints, lambda o: pad + o['_title'], lambda o: o['value'])
    if inst.workflowsInfo.get('availableWorkflows', []):
        click.echo("Workflows: ")
        for workflow in inst.workflowsInfo.get('availableWorkflows', []):
            if workflow['parameters']:
                args = "(" + ", ".join(map(lambda param: "%(type)s %(id)s" % param, workflow['parameters'])) + ")"
            else:
                args = ""
            click.echo(pad + "%s%s" % (workflow['name'], args))
    if inst.serviceIn:
        click.echo("Service in:")
        _columns(inst.serviceIn, lambda o: pad + o['id'], lambda o: _color("BLUE", o['name']))


@cli.command("launch-instance")
@click.option("--revision", default=None, help="Revision to launch")
@click.option("--environment", default=None, help="Environment used to launch instance")
@click.option("--destroy", default=None, help="Schedule destroy (seconds)")
@click.option("--parameter", default=False, type=(unicode, unicode), multiple=True, help="Parameter value")
@click.argument("application")
@click.argument("name", default=None, required=False)
def launch_instance(revision, environment, destroy, application, name, parameter):
    print parameter
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    app = org.get_application(application)
    destroy_interval = _map_opt(destroy, lambda x: x / 1000)
    env = _map_opt(environment, org.get_environment)
    parameters = dict(parameter)
    inst = org.create_instance(application=app, revision=revision, environment=env,
                               name=name, parameters=parameters, destroyInterval=destroy_interval)
    _describe_instance(inst, True)


@cli.command("destroy-instance")
@click.option("--wait/--no-wait", default=False, help="Wait for DESTROYED status")
@click.option("--timeout", default=3, type=int, help="Timeout in minutes")
@click.argument("instance")
def destroy_instance(instance, timeout, wait):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    inst = org.get_instance(instance)
    inst.destroy()
    _describe_instance_short(inst)
    if wait:
        inst.destroyed(timeout)
        _describe_instance_short(inst)


@cli.command("wait-status")
@click.option("--timeout", default=3, type=int, help="Timeout in minutes")
@click.option("--status", default="Active",
              help="Status to wait (Requested, Launching, Active, Executing, Destroying, Destroyed, Unknown)")
@click.argument("instance")
def wait_status(instance, status, timeout):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    inst = org.get_instance(instance)
    timeout = int(timeout)
    # TODO case-insensitive
    accepted_states = ['Destroying', 'Active', 'Running', 'Executing', 'Unknown']
    try:
        waitForStatus(instance=inst, final=status, accepted=accepted_states, timeout=[timeout * 20, 3, 1])
    finally:
        _describe_instance_short(org.get_instance(instance))


@cli.command("remove-instance")
@click.option("--force/--no-force", default=False, help="Wait for DESTROYED status")
@click.argument("instance")
def destroy_instance(instance, force):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    inst = org.get_instance(instance)
    if not force:
        # TODO
        raise NotImplementedError("non-force removal is not supported yet")
    else:
        inst.force_remove()


def _pad(string, length):
    return ("%-" + str(length) + "s") % string


@cli.command("show-instance-logs")
@click.option("--severity", default="INFO", help="Logs severity.")
@click.option("--localtime/--utctime", default=True, help="Use local or UTC time.")
@click.option("--sort-by", default="time",
              help="Sort by time/severity/source/eventTypeText/description. Prefix with minus for inverted order.")
@click.option("--hide-multiline/--multiline", default=True, help="Show only first line of multi-line message")
@click.option("--filter-text", default=None, help="Filter by full text, including source and event name")
@click.option("--max-items", default=30,
              help="Limit number of items to show. Positive integer for tail, negative integer for head.")
@click.option("--follow/--no-follow", default=False, help="Wait for new messages to appear.")
@click.option("--show-all/--no-show-all", default=False, help="Show all messages, overrides --max-items.")
@click.argument("instance")
def show_logs(instance, localtime, severity, sort_by, hide_multiline, filter_text, max_items, show_all, follow):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    inst = org.get_instance(instance)
    accepted_severities = list(itertools.takewhile(lambda x: x != severity, SEVERITIES)) + [severity]

    def show_activitylog(after=None):
        activitylog = inst.get_activitylog(severity=accepted_severities, after=after)

        if not activitylog or not len(activitylog):
            return
        time_f = localtime and time.localtime or time.gmtime
        max_severity_length = max(map(lambda i: len(i['severity']), activitylog.log))
        max_source_length = max(map(lambda i: len(i.get('source', "self")), activitylog.log))
        max_type_length = max(map(lambda i: len(i['eventTypeText']), activitylog.log))
        if sort_by[0] == "-":
            reverse = True
            sort_by_key = sort_by[1:]
        else:
            reverse = False
            sort_by_key = sort_by
        if filter_text:
            activitylog.log = filter(lambda s: filter_text in str(s), activitylog.log)
        activitylog.log = sorted(activitylog.log, key=lambda i: i[sort_by_key], reverse=reverse)
        if not show_all and max_items:
            if max_items > 0:
                activitylog.log = activitylog.log[-max_items:]
            else:
                activitylog.log = activitylog.log[:-max_items]
        vertical_padding_before = False
        for item in activitylog:
            multiline = "\n" in item['description']
            if multiline and not vertical_padding_before and not hide_multiline:
                click.echo()
            padding = len(time.strftime("%Y-%m-%d %H:%M:%S", time_f(item['time'] / 1000))) + \
                max_severity_length + max_source_length + max_type_length + 8
            click.echo(
                "%s  %s  %s  %s  " % (
                    time.strftime("%Y-%m-%d %H:%M:%S", time_f(item['time'] / 1000)),
                    _color(SEVERITY_COLORS.get(item['severity'], "BLACK"), _pad(item['severity'], max_severity_length)),
                    _pad(item.get('source', "") or (item.get("self") and "self") or " ", max_source_length),
                    _pad(item['eventTypeText'], max_type_length)),
                nl=False)
            if not multiline:
                click.echo(item['description'])
                vertical_padding_before = False
            else:
                lines = item['description'].split("\n")
                click.echo(lines[0])
                if not hide_multiline:
                    for line in lines[1:]:
                        click.echo(padding * " " + line)
                    click.echo()
                    vertical_padding_before = True
        return activitylog

    after = None
    while True:
        last_log = show_activitylog(after=after)
        if last_log and len(last_log):
            after = max(map(lambda i: i['time'], last_log.log))
            after += 1  # add extra millisecond to avoid showning same line twice
        elif not after:
            after = int(time.time()) * 1000
            after += 1
        if follow:
            time.sleep(10)
        else:
            break


@cli.command("clear-env")
@click.option("--destroy-services/--keep-services", default=False, help="Destroy services")
@click.option("--fallback-force/--no-fallback-force", default=False, help="Use force-remove if destroy failed")
@click.option("--force/--no-force", default=False, help="Use force-remove instead of destroy")
@click.argument("environment")
def clear_env(environment, destroy_services, force, fallback_force):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    if destroy_services:
        for service in env.services:
            click.echo(service.id + " " + _color("BLUE", service.name) + " ", nl=False)
            env.remove_service(service)
            if not force:
                try:
                    service.destroy()
                    service.destroyed()
                except AssertionError:
                    if fallback_force:
                        service.force_remove()
            else:
                service.force_remove()
            click.echo(_color(STATUS_COLORS["DESTROYED"], "DESTROYED"))
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.clean()
    click.echo(_color("GREEN", "CLEANED"))


@cli.command("init-env")
@click.option("--zone", default=None, help="In what zone services should be launched")
@click.option("--with-cloud-account/--without-cloud-account", default=True, help="Whether init-ca should be performed")
@click.argument("environment")
def init_env(environment, with_cloud_account, zone):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.init_common_services(with_cloud_account=with_cloud_account, zone_name=zone)
    click.echo(_color("GREEN", "OK"))


@cli.command("create-env")
@click.option("--default/--no-default", default=False, help="Make created environment default")
@click.option("--zone", default=None, help="Zone for environment. "
                                           "When performing init-env, services will be launched in that zone")
@click.option("--init/--no-init", default=False, help="Perform init-env after creation")
@click.option("--with-cloud-account/--without-cloud-account", default=True,
              help="If performing init-env, whether init-ca should be performed")
@click.argument("name")
@click.pass_context
def create_env(ctx, name, init, zone, default, with_cloud_account):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.create_environment(name, default, zone)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    if init:
        env.init_common_services(with_cloud_account=with_cloud_account, zone_name=zone)
    click.echo(_color("GREEN", "CREATED"))


@cli.command("delete-env")
@click.argument("environment")
def delete_env(environment):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.delete()
    click.echo(_color("GREEN", "DELETED"))


@cli.command("clone-env")
@click.option("--wait/--no-wait", default=False, help="Wait for environment to become ONLINE")
@click.option("--zone", default=None, help="Zone for environment")
@click.argument("environment")
@click.argument("name", default=None, required=False)
def clone_env(environment, name, wait, zone):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    orig_env = org.get_environment(environment)
    if not name:
        name = orig_env.name + " clone"
    env = org.create_environment(name, False, zone or orig_env.zoneId)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.restore(orig_env.json())
    if wait:
        env.ready()
        click.echo(_color("GREEN", "ONLINE"))
    else:
        click.echo(_color("GREEN", "CREATED"))


@cli.command("describe-env")
@click.argument("environment")
def describe_env(environment):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    click.echo("Environment " + env.id + "  " + _color("BLUE", env.name))
    click.echo("Status      " + (env.isOnline and _color("GREEN", "ONLINE") or _color("RED", "OFFLINE")))
    click.echo("Backend     " + env.zoneId + "  " + _color("BLUE", org.zones[env.zoneId].name))
    if env.services:
        click.echo("Services")

        def service_text(s):
            try:
                env_text = s.json()['environment']['name']
            except Exception:
                env_text = ""
            return _color("BLUE", s.name) + " @ " + env_text
        _columns(env.services, lambda s: "    " + s.id, service_text)
    if env.policies:
        click.echo("Policies")
        _columns(env.policies, lambda s: "    %(action)s.%(parameter)s" % s, lambda s: s['value'])
    if env.markers:
        click.echo("Markers")
        _columns(env.markers, lambda s: "    %(name)s" % s, lambda s: "")
    if env.properties:
        click.echo("Properties")
        _columns(env.properties, lambda s: "    %(type)s %(name)s" % s, lambda s: s['value'])


@cli.command("export-env")
@click.argument("environment")
@click.argument("filename", default=None, required=False)
def export_env(environment, filename):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    if filename:
        click.echo("Exporting %s to %s " % (_color("BLUE", env.name), filename), nl=False)
        f = open(filename, "w")
        click.echo(_color("GREEN", "OK"), err=True)
    else:
        f = sys.stdout
    f.write(env.export_yaml())


@cli.command("import-env")
@click.option("--merge/--no-merge", default=True, help="Merge or replace file contents with existing environment.")
@click.argument("environment")
@click.argument("filename")
def import_env(environment, filename, merge):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    click.echo("Importing %s to %s " % (filename, _color("BLUE", env.name),), nl=False)
    env.import_yaml(filename, merge=merge)
    click.echo(_color("GREEN", "OK"))


@cli.command("list-zones")
def list_zones():
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    _columns(org.list_zones_json(),
             lambda o: o['id'],
             lambda o: _color("BLUE", o['name']) + (o['isDefault'] and " DEFAULT" or ""))


@cli.command("make-default")
@click.argument("environment")
def make_default(environment):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.set_as_default()
    click.echo(_color("GREEN", "DEFAULT"))


def _print_message(message, color="BLACK"):
    if "message" in message:
        click.echo(_color(color, message["message"]))
    elif isinstance(message, basestring):
        click.echo(_color(color, message))
    else:
        click.echo(_color(color, "<error format not supported by this version of cli>"))


@cli.command("validate-manifest")
@click.argument("filename", required=False, default=None)
def validate_manifest(filename):
    platform = _get_platform()
    if filename:
        manifest = Manifest(file=filename)
    else:
        manifest = Manifest(content=sys.stdin.read())
    result = platform.validate(manifest)
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    for error in errors:
        _print_message(error, "RED")
    for warning in result.get("warnings", []):
        _print_message(warning, "YELLOW")
    if not errors and not warnings:
        click.echo(_color("GREEN", "NO WARNINGS"))
    exit(errors and 1 or 0)

if __name__ == '__main__':
    cli()
