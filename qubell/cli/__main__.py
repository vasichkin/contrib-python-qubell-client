import click
import itertools
import logging as log
import os
import re
import sys
import time
import yaml
from colorama import Fore, Style
from os.path import join, basename
from qubell.api.globals import QUBELL, PROVIDER
from qubell.api.private.exceptions import NotFoundError
from qubell.api.private.instance import InstanceList
from qubell.api.private.manifest import Manifest
from qubell.api.private.platform import QubellPlatform
from qubell.api.private.service import system_application_types, CLOUD_ACCOUNT_TYPE
from qubell.api.tools import load_env, waitForStatus
from qubell.cli.yamlutils import DuplicateAnchorLoader

PROVIDER_CONFIG = None
CMD_LIST = [
    'instance',
    'application',
    'environment',
    'organization',
    'platform',
    'zone',
    'manifest',
    'token',
]

log.getLogger().setLevel(getattr(log, os.getenv('QUBELL_LOG_LEVEL', 'error').upper()))

STATUS_COLORS = {
    "ACTIVE": "GREEN",
    "RUNNING": "GREEN",
    "LAUNCHING": "CYAN",
    "DESTROYING": "CYAN",
    "EXECUTING": "CYAN",
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
def platform_cli():
    pass


@click.group()
def zone_cli():
    pass


@click.group()
def organization_cli():
    pass


@click.group()
def application_cli():
    pass


@click.group()
def environment_cli():
    pass


@click.group()
def instance_cli():
    pass


@click.group()
def manifest_cli():
    pass


@click.group()
def token_cli():
    pass


@click.group()
@click.option("--tenant", default="", help="Tenant url to use, QUBELL_TENANT by default")
@click.option("--token", default="", help="Session token to use, QUBELL_TOKEN by default")
@click.option("--user", default="", help="User to use, QUBELL_USER by default")
@click.option("--password", default="", help="Password to use, QUBELL_PASSWORD by default")
@click.option("--organization", default="", help="Organization to use, QUBELL_ORGANIZATION by default")
@click.option("--debug", is_flag=True, default=False, help="Debug mode, also QUBELL_LOG_LEVEL can be used.")
@click.option("--uncolorize", is_flag=True, default=False, help="Do not colorize output")
@click.pass_context
def entity(ctx, debug, uncolorize, **kwargs):
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
            self.unauthenticated_platform = None
            self.colorize = not (uncolorize)

        def get_platform(self):
            if not self.platform:
                assert QUBELL["tenant"], "No platform URL provided. Set QUBELL_TENANT or use --tenant option."
                if not QUBELL["token"]:
                    assert QUBELL["user"], "No username. Set QUBELL_USER or use --user option."
                    assert QUBELL["password"], "No password provided. Set QUBELL_PASSWORD or use --password option."

                self.platform = QubellPlatform.connect(
                    tenant=QUBELL["tenant"],
                    user=QUBELL["user"],
                    password=QUBELL["password"],
                    token=QUBELL["token"])
            return self.platform

        def get_unauthenticated_platform(self):
            if not self.unauthenticated_platform:
                assert QUBELL["tenant"], "No platform URL provided. Set QUBELL_TENANT or use --tenant option."

                self.unauthenticated_platform = QubellPlatform.connect(tenant=QUBELL["tenant"])

            return self.unauthenticated_platform

    ctx = click.get_current_context()
    ctx.obj = UserContext()


def list_commands(ctx):
    return CMD_LIST


def get_command(ctx, name):
    if name.startswith('man'):
        return manifest_cli
    elif name.startswith('ins'):
        return instance_cli
    elif name.startswith('app'):
        return application_cli
    elif name.startswith('env'):
        return environment_cli
    elif name.startswith('org'):
        return organization_cli
    elif name.startswith('zone'):
        return zone_cli
    elif name.startswith('pla'):
        return platform_cli
    elif name.startswith('tok'):
        return token_cli


entity.list_commands = list_commands
entity.get_command = get_command


def _get_platform(authenticated=True):
    context_obj = click.get_current_context().obj
    return context_obj.get_platform() if authenticated else context_obj.get_unauthenticated_platform()


def _color(color, text):
    colorize = click.get_current_context().obj.colorize
    if colorize:
        if not isinstance(text, basestring):
            text = str(text)
        return getattr(Fore, color) + text + Style.RESET_ALL
    else:
        return text


def _print_message(message, color="BLACK"):
    if "message" in message:
        click.echo(_color(color, message["message"]))
    elif isinstance(message, basestring):
        click.echo(_color(color, message))
    else:
        click.echo(_color(color, "<error format not supported by this version of cli>"))


##############################################################################
###############################  APPLICATION  ###############################
##############################################################################

@application_cli.command(name="list", help="List applications in organization")
@click.option('-v', '--verbose', is_flag=True, default=False, help="Verbose output")
def list_apps(verbose):
    _platform = _get_platform()

    assert QUBELL["organization"], "Organization should be provided"
    org = _platform.get_organization(QUBELL["organization"])
    json = org.list_applications_json()
    for app_id, app_name in [(a['id'], a['name']) for a in json]:

        if verbose:
            app = org.applications[app_name]
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
        else:
            click.echo(app_id + " " + _color("BLUE", app_name))


@application_cli.command(name="export", help="Save manifest of applications to files")
@click.argument("applications", nargs=-1)
@click.option("--recursive", is_flag=True, default=False, help="Recursively also dependencies")
@click.option("--output-dir", default="", help="Output directory for manifest files, current by default")
@click.option("--stdout", default=False, help="Print manifest to stdout instead of saving to file")
@click.option("--version", '-v', default=None, help="Manifest version to export. Default is last available")
def export_app(recursive, applications, output_dir, version, stdout):
    if stdout and recursive:
        click.echo("Using --recursive with --stdout is not supported")
        exit(1)

    platform = _get_platform()

    def echo_progress(*args, **kwargs):
        if not stdout:
            click.echo(*args, **kwargs)

    def _save_manifest(app, manifest, filename=None):
        if stdout:
            click.echo(manifest["manifest"])
        else:
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
        echo_progress("Saving " + _color("BLUE", current_app) + " ", nl=False)
        try:
            current_app = org.get_application(current_app)
            if not current_version:
                manifest = current_app.get_manifest_latest()
            else:
                manifest = current_app.get_manifest(current_version)
            echo_progress(_color("BLUE", "v" + str(manifest["version"])) + " ", nl=False)
            _save_manifest(current_app, manifest)
            echo_progress(_color("GREEN", " OK"))
            if recursive:
                app_names = _child_applications(yaml.load(manifest["manifest"], DuplicateAnchorLoader))
                for app_name in app_names:
                    do_export(app_name)
        except (IOError, NotFoundError):
            click.echo(_color("RED", " FAIL"))

    assert applications, "Application ID or name should be provided"
    for app in applications:
        do_export(app, version)


@application_cli.command(name="import",
                         help="Upload manifest to application. If no name or id provided, application will be created by file name")
@click.argument("files", nargs=-1)
@click.option("--category", default=None, help="Category name in which app will be created. "
                                               "If app already exists, its category will be updated.")
@click.option("--id", "-i", default=None,
              help="Application id, allowed only if one filename given. Disables --app-name if provided."
                   "If app with such id not found, new app won't be created.")
@click.option("--name", "-n", default=None,
              help="Application name, allowed only if one filename given. Is ignored if --app-id is provided."
                   "Has higher priority than file name.")
@click.option("--overwrite", "-w", is_flag=True, default=False,
              help="Upload manifest for already existing applications")
def import_app(files, category, overwrite, id, name):
    """ Upload application from file.

    By default, file name will be used as application name, with "-vXX.YYY" suffix stripped.
    Application is looked up by one of these classifiers, in order of priority:
    app-id, app-name, filename.

    If app-id is provided, looks up existing application and updates its manifest.
    If app-id is NOT specified, looks up by name, or creates new application.

    """
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    if category:
        category = org.categories[category]
    regex = re.compile(r"^(.*?)(-v(\d+)|)\.[^.]+$")
    if (id or name) and len(files) > 1:
        raise Exception("--id and --name are supported only for single-file mode")

    for filename in files:
        click.echo("Importing " + filename, nl=False)
        if not name:
            match = regex.match(basename(filename))
            if not match:
                click.echo(_color("RED", "FAIL") + " unknown filename format")
                break
            name = regex.match(basename(filename)).group(1)
        click.echo(" => ", nl=False)
        app = None
        try:
            app = org.get_application(id=id, name=name)
            if app and not overwrite:
                click.echo("%s %s already exists %s" % (
                    app.id, _color("BLUE", app and app.name or name), _color("RED", "FAIL")))
                break
        except NotFoundError:
            if id:
                click.echo("%s %s not found %s" % (
                    id or "", _color("BLUE", app and app.name or name), _color("RED", "FAIL")))
                break
        click.echo(_color("BLUE", app and app.name or name) + " ", nl=False)
        try:
            with file(filename, "r") as f:
                if app:
                    app.update(name=app.name,
                               category=category and category.id or app.category,
                               manifest=Manifest(content=f.read()))
                else:
                    app = org.application(id=id, name=name, manifest=Manifest(content=f.read()))
                    if category:
                        app.update(category=category.id)
            click.echo(app.id + _color("GREEN", " OK"))
        except IOError as e:
            click.echo(_color("RED", " FAIL") + " " + e.message)
            break


@application_cli.command(name="delete", help="Delete application")
@click.argument("applications", nargs=-1)
def delete_app(applications):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    for app in applications:
        click.echo("Deleting %s" % (_color("BLUE", app)), nl=False)
        org.delete_application(app)
        click.echo(_color("GREEN", " OK"))


##############################################################################
###############################  ORGANIZATION  ###############################
##############################################################################

@organization_cli.command(name="create", help="Create organization")
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


# TODO: Dup of env.init ??
@organization_cli.command(name="init", help="Initialize cloud account service")
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


@organization_cli.command("list", help="List organizations")
def list_orgs():
    platform = _get_platform()
    for app in platform.organizations:
        click.echo(app.id + " " + _color("BLUE", app.name))


@organization_cli.command(name="restore", help="Restore configuration from ENV file")
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


##############################################################################
###############################  INSTANCE  ###############################
##############################################################################

@instance_cli.command("list", help="List instances in current organization or application")
@click.argument("application", default=None, required=False)
@click.option("--status", default="!DESTROYED",
              help="Filter by statuses, one of "
                   "REQUESTED, LAUNCHING, ACTIVE, EXECUTING, FAILED, DESTROYING, DESTROYED."
                   "Several statuses can be listed using comma. !STATUS_NAME to invert match.")
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
    if any(map(lambda p: p("DESTROYED"), filters)):
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


@instance_cli.command("describe", help="Show details about instance")
@click.argument("instance")
@click.option("--json", is_flag=True, default=False, help="Print raw json")
def describe_instance(instance, json, localtime=True):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    inst = org.instances[instance]
    if json:
        click.echo(inst._router.get_instance(org_id=inst.organizationId, instance_id=inst.instanceId).text)
    else:
        _describe_instance(inst, localtime)


def _calc_title(items, template="%s (%s)"):
    for value in items:
        if value.get('id') != value.get('name') and value.get('name'):
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
        config = inst.config
        _calc_title(config)
        _columns(config, lambda o: pad + str(o['_title']), lambda o: pad + str(o['value']))
    if inst.return_values:
        click.echo("Return values: ")
        endpoints = [{'id': k, 'value': v} for k, v in inst.return_values.iteritems()]
        _calc_title(endpoints)
        _columns(endpoints, lambda o: pad + str(o['_title']), lambda o: str(o['value']))
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
    if inst.json().get("submodules", []):
        click.echo("Structure:")
        _describe_submodules("", inst.json().get("submodules", []), level=1)


_MODULE_TYPES = {
    "submodule": "Module"
}


def _describe_submodules(path, submodules, level):
    for submodule in submodules:
        if path:
            module_path = path + "." + submodule['componentId']
        else:
            module_path = submodule['componentId']
        name = submodule.get("name", "")
        instanceId = submodule.get("instanceId", "")
        moduleType = _MODULE_TYPES.get(submodule.get("moduleType"), submodule.get("moduleType").capitalize())
        click.echo("    " * level + "%s: %s %s %s" % (moduleType, module_path, _color("BLUE", name), instanceId))
        _describe_submodules(module_path, submodule.get("submodules", []), level + 1)


@instance_cli.command("launch", help="Launch instance in application")
@click.option("--revision", default=None, help="Revision to launch")
@click.option("--environment", default=None, help="Environment used to launch instance")
@click.option("--destroy", default=60 * 60, help="Schedule destroy (seconds)")
@click.option("--parameter", default=False, type=(unicode, unicode), multiple=True, help="Parameter value")
@click.argument("application")
@click.argument("name", default=None, required=False)
def launch_instance(revision, environment, destroy, application, name, parameter):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    app = org.get_application(application)
    env = _map_opt(environment, org.get_environment)
    parameters = dict()
    submodules = dict()

    def _get_module(modules, name):
        path = name.split(".", 1)
        module = modules['submodules'].get(path[0], {"submodules": {}, "parameters": {}})
        modules['submodules'][path[0]] = module
        if len(path) == 2:
            return _get_module(module, path[1])
        else:
            return module

    for (param_name, param_value) in parameter:
        if ":" in param_name:
            (module_name, module_param_name) = param_name.split(":", 1)
            module = _get_module({'submodules': submodules}, module_name)
            module['parameters'][module_param_name] = param_value
        else:
            parameters[param_name] = param_value

    inst = org.create_instance(application=app, revision=revision, environment=env,
                               name=name, parameters=parameters, destroyInterval=destroy * 1000,
                               submodules=submodules)
    _describe_instance(inst, True)


@instance_cli.command("parameters", help="Get default launch parameters for application")
@click.argument("application")
def show_instance_parameters(application):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    app = org.get_application(application)
    params = platform._router.post_organization_launch_parameters(org_id=org.id, app_id=app.id).json()

    def _render_parameters(path, module):
        parameters = module.get("parameters", [])
        submodules = module.get("submodules", [])
        child_instances = filter(lambda m: m["componentType"] == "Instance", submodules)
        if not parameters and not submodules:
            return
        if path:
            click.echo("Module: " + path)
        else:
            click.echo("Parameters:")
        if parameters:
            _columns(parameters,
                     lambda p: "  %(valueType)10s %(id)s" % p,
                     lambda p: p["value"])
        else:
            click.echo("    <no parameters>")
        click.echo()
        if path:
            path += "."
        for submodule in child_instances:
            _render_parameters(path + submodule["name"], submodule)

    _render_parameters("", params.get("componentTree", {}))


@instance_cli.command("destroy", help="Destroy instance")
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


@instance_cli.command("wait-status", help="Wait until instance status becomes 'Status' or timeout reached")
@click.option("--timeout", default=3, type=int, help="Timeout in minutes")
@click.option("--status", "-s", default="Active",
              help="Status to wait (Requested, Launching, Active, Executing, Destroying, Destroyed, Unknown)")
@click.argument("instance")
def wait_status(instance, status, timeout):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    inst = org.get_instance(instance)
    timeout = int(timeout)
    # TODO case-insensitive
    accepted_states = ['Launching', 'Destroying', 'Active', 'Running', 'Executing', 'Unknown', 'Requested']
    res = False
    try:
        res = waitForStatus(instance=inst, final=status, accepted=accepted_states, timeout=[timeout * 20, 3, 1])
    finally:
        _describe_instance_short(org.get_instance(instance))
    if not res:  # Exit non-zero if status not reached
        exit(1)


@instance_cli.command("remove", help="Force remove instance")
@click.option("--force", is_flag=True, default=False, help="Wait for DESTROYED status")
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


def _parse_timestamp(datetime, localtime=False):
    time_t = datetime
    try:
        time_t = int(datetime)
    except Exception:
        pass
    try:
        time_t = time.strptime(datetime, "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    if not time_t:
        raise ValueError("unknown timestamp format: " + str(datetime))
    if not localtime:
        time_shift = time.mktime(time.localtime()) - time.mktime(time.gmtime())
    else:
        time_shift = 0
    return time.mktime(time_t) + time_shift


@instance_cli.command("logs", help="Show instance activity log")
@click.option("--severity", default="INFO", help="Logs severity.")
@click.option("--localtime/--utctime", default=True, help="Use local or UTC time.")
@click.option("--sort-by", default="time",
              help="Sort by time/severity/source/eventTypeText/description. Prefix with minus for inverted order.")
@click.option("--hide-multiline", is_flag=True, default=True, help="Show only first line of multi-line message")
@click.option("--filter-text", default=None, help="Filter by full text, including source and event name")
@click.option("--max-items", default=30,
              help="Limit number of items to show. Positive integer for tail, negative integer for head.")
@click.option("--follow", is_flag=True, default=False, help="Wait for new messages to appear.")
@click.option("--show-all", is_flag=True, default=False, help="Show all messages, overrides --max-items.")
@click.option("--before", default=None, help="Show messages before TIMESTAMP")
@click.option("--after", default=None, help="Show messages after TIMESTAMP")
@click.argument("instance")
def show_logs(instance, localtime, severity, sort_by, hide_multiline, filter_text, max_items, show_all, follow,
              before, after):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    inst = org.get_instance(instance)
    accepted_severities = list(itertools.takewhile(lambda x: x != severity, SEVERITIES)) + [severity]

    if after:
        after = int(_parse_timestamp(after, localtime)) * 1000
    if before:
        before = int(_parse_timestamp(before, localtime)) * 1000

    def show_activitylog(after=None, before=before):
        activitylog = inst.get_activitylog(severity=accepted_severities, after=after, end=before)

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

    while True:
        last_log = show_activitylog(after=after, before=before)
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

@instance_cli.command("runworkflow", help="Run workflow on instance")
@click.option("--parameter", default=False, type=(unicode, unicode), multiple=True, help="Parameter for workflow run")
@click.option("--status", is_flag=True, default=False, help="Display instance status after workflow run")
@click.option("--schedule", default=None, help="Schedule workflow run (seconds)")
@click.argument("instance")
@click.argument("workflow")
def run_workflow(instance, workflow, parameter, status, schedule):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    ins = org.get_instance(instance)
    parameters = dict()

    for (param_name, param_value) in parameter:
            parameters[param_name] = param_value

    if schedule:
        ins.schedule_workflow(name=workflow, timestamp=schedule*1000, parameters=parameters)
    else:
        ins.run_workflow(name=workflow, parameters=parameters)
    if status:
        _describe_instance(ins, True)

##############################################################################
###############################  ENVIRONMENT  ###############################
##############################################################################


@environment_cli.command("list", help="List environments")
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


@environment_cli.command("clear", help="Clean environment. Remove all services in environment")
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


@environment_cli.command("init", help="Add basic services to environment (WF, CA, KS services)")
@click.option("--zone", default=None, help="In what zone services should be launched")
@click.option("--without-cloud-account", is_flag=True, default=False, help="Whether init-ca should be performed")
@click.argument("environment", default="default")
def init_env(environment, without_cloud_account, zone):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.init_common_services(with_cloud_account=not (without_cloud_account), zone_name=zone)
    click.echo(_color("GREEN", "OK"))


@environment_cli.command("create", help="Create environment")
@click.option("--default/--no-default", default=False, help="Make created environment default")
@click.option("--zone", default=None, help="Zone for environment. "
                                           "When performing init-env, services will be launched in that zone")
@click.option("--init", is_flag=True, default=False, help="Perform init-env after creation")
@click.option("--without-cloud-account", default=True,
              help="If performing init-env, whether init-ca should be performed")
@click.argument("name")
def create_env(name, init, zone, default, without_cloud_account):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.create_environment(name, default, zone)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    if init:
        env.init_common_services(with_cloud_account=not (without_cloud_account), zone_name=zone)
    click.echo(_color("GREEN", "CREATED"))


@environment_cli.command("delete", help="Delete environment")
@click.argument("environment")
def delete_env(environment):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.delete()
    click.echo(_color("GREEN", "DELETED"))


@environment_cli.command("clone", help="Copy environment")
@click.option("--wait", is_flag=True, default=False, help="Wait for environment to become ONLINE")
@click.option("--zone", default=None, help="Zone for environment")
@click.argument("environment")
@click.argument("newname", default=None, required=False)
def clone_env(environment, newname, wait, zone):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    orig_env = org.get_environment(environment)
    if not newname:
        newname = "Clone of " + orig_env.name
    env = org.create_environment(newname, False, zone or orig_env.zoneId)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.restore(orig_env.json())
    if wait:
        env.ready()
        click.echo(_color("GREEN", "ONLINE"))
    else:
        click.echo(_color("GREEN", "CREATED"))


@environment_cli.command("describe", help="Show services, markers and properties of environment")
@click.argument("environment", default="default")
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


@environment_cli.command("export", help="Save environment to file")
@click.argument("environment", default="default")
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


@environment_cli.command("import", help="Import environment from file")
@click.option("--merge", is_flag=True, default=True, help="Merge or replace file contents with existing environment.")
@click.option("--create", is_flag=True, default=True, help="")
@click.argument("environment")
@click.argument("filename", default=None, required=False)
def import_env(environment, filename, merge, create):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    if create:
        env = org.get_or_create_environment(environment)
    else:
        env = org.get_environment(environment)
    env_file = filename and open(filename, "r") or sys.stdin
    if not filename:
        filename = "stdin"
    click.echo("Importing %s to %s " % (filename, _color("BLUE", env.name),), nl=False)
    env.import_yaml(env_file, merge=merge)
    click.echo(_color("GREEN", "OK"))


@environment_cli.command("make-default", help="Set environment as 'default'")
@click.argument("environment", default='default')
def make_default(environment):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)
    click.echo(env.id + " " + _color("BLUE", env.name) + " ", nl=False)
    env.set_as_default()
    click.echo(_color("GREEN", "DEFAULT"))


@environment_cli.command("get-keypair", help="Get private key from environment")
@click.argument("environment", default='default')
@click.argument("filename", default=None, required=False)
def get_keypair(environment, filename):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    env = org.get_environment(environment)

    if filename:
        click.echo("Exporting %s to %s " % (_color("BLUE", env.name), filename), nl=False)
        f = open(filename, "w")
        f.write(env.get_default_private_key())
        click.echo(_color("GREEN", "OK"), err=True)
    else:
        sys.stdout.write(env.get_default_private_key())


##############################################################################
###############################  OTHER  ######################################
##############################################################################

@zone_cli.command("list", help="List available zones")
def list_zones():
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    _columns(org.list_zones_json(),
             lambda o: o['id'],
             lambda o: _color("BLUE", o['name']) + (o['isDefault'] and " DEFAULT" or ""))


@manifest_cli.command("validate", help="Perform manifest validation")
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


@organization_cli.command("import-kit", help="Import starter kit from ULR")
@click.option("--category", default=None, help="Category of uploaded applications")
@click.argument("metadata_url")
def import_kit(metadata_url, category):
    platform = _get_platform()
    org = platform.get_organization(QUBELL["organization"])
    if category:
        category = org.categories[category]
    click.echo("Importing from %s " % (_color("BLUE", metadata_url)), nl=False)
    org.upload_applications(metadata_url, category)
    click.echo(_color("GREEN", "OK"))


REVERSE_MAPPING = {
    'tenant': 'QUBELL_TENANT',
    'user': 'QUBELL_USER',
    'password': 'QUBELL_PASSWORD',
    'organization': 'QUBELL_ORGANIZATION'
}

REVERSE_PROVIDER_MAPPING = {
    'provider_name': 'PROVIDER_NAME',
    'provider_type': 'PROVIDER_TYPE',
    'provider_identity': 'PROVIDER_IDENTITY',
    'provider_credential': 'PROVIDER_CREDENTIAL',
    'provider_region': 'PROVIDER_REGION',
    'provider_security_group': 'PROVIDER_SECURITY_GROUP'
}


@platform_cli.command("show-account", help="Show credentials")
def show_account():
    """
    Exports current account configuration in
    shell-friendly form. Takes into account
    explicit top-level flags like --organization.
    """
    click.echo("# tonomi api")
    for (key, env) in REVERSE_MAPPING.items():
        value = QUBELL.get(key, None)
        if value:
            click.echo("export %s='%s'" % (env, value))
    if any(map(lambda x: PROVIDER.get(x), REVERSE_PROVIDER_MAPPING.keys())):
        click.echo("# cloud account")
        for (key, env) in REVERSE_PROVIDER_MAPPING.items():
            value = PROVIDER.get(key, None)
            if value:
                click.echo("export %s='%s'" % (env, value))


@token_cli.command('generate', help="Generate a new session token")
@click.option('--verbose', is_flag=True, default=False, help="Include expiration time into output")
@click.argument('refresh_token')
def generate_session_token(refresh_token, verbose):
    """
    Generates new session token from the given refresh token.
    :param refresh_token: refresh token to generate from
    :param verbose: whether expiration time should be added to output
    """

    platform = _get_platform(authenticated=False)
    session_token, expires_in = platform.generate_session_token(refresh_token)

    if verbose:
        click.echo("%s\n\n%s" % (session_token, _color('YELLOW', "Expires in %d seconds" % expires_in)))
    else:
        click.echo(session_token)


if __name__ == '__main__':
    entity(obj={})