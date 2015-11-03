import logging as log
from os.path import join, basename
import re

import click
from colorama import Fore, Style
import yaml

from qubell.api.globals import QUBELL as qubell_config, PROVIDER as provider_config
from qubell.api.private.platform import QubellPlatform
from qubell.api.private.exceptions import NotFoundError
from qubell.api.private.manifest import Manifest
from qubell.api.private.service import system_application_types, CLOUD_ACCOUNT_TYPE
from qubell.cli.yamlutils import DuplicateAnchorLoader

_platform = None


@click.group()
@click.option("--tenant", default="", help="Tenant url to use, QUBELL_TENANT by default")
@click.option("--user", default="", help="User to use, QUBELL_USER by default")
@click.option("--password", default="", help="Password to use, QUBELL_PASSWORD by default")
@click.option("--organization", default="", help="Organization to use, QUBELL_ORGANIZATION by default")
@click.option("--debug/--no-debug", default=False, help="Debug mode.")
def cli(debug, **kwargs):
    global _platform
    if debug:
        log.basicConfig(level=log.DEBUG)
        log.getLogger("requests.packages.urllib3.connectionpool").setLevel(log.DEBUG)
    for (k, v) in kwargs.iteritems():
        if v:
            qubell_config[k] = v
    _platform = QubellPlatform.connect(
        tenant=qubell_config["tenant"],
        user=qubell_config["user"],
        password=qubell_config["password"])


@cli.command()
def list_apps():
    global _platform

    org = _platform.get_organization(qubell_config["organization"])
    for app in org.applications:
        click.echo(app.id + " " + _color("BLUE", app.name))


def _color(color, text):
    return getattr(Fore, color) + str(text) + Style.RESET_ALL


@cli.command()
@click.option("--recursive/--non-recursive", default=False, help="Export also dependencies.")
@click.option("--output-dir", default="", help="Output directory for manifest files, current by default.")
@click.option("--version", default=None, help="Manifest version to export.")
@click.argument("application")
def export_app(recursive, application, output_dir, version):
    global _platform

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

    org = _platform.get_organization(qubell_config["organization"])

    def do_export(application, version=None):
        click.echo("Saving " + _color("BLUE", application) + " ", nl=False)
        try:
            app = org.get_application(application)
            if not version:
                manifest = app.get_manifest_latest()
            else:
                manifest = app.get_manifest(version)
            click.echo(_color("BLUE", "v" + str(manifest["version"])) + " ", nl=False)
            _save_manifest(app, manifest)
            click.echo(_color("GREEN", " OK"))
            if recursive:
                app_names = _child_applications(yaml.load(manifest["manifest"], DuplicateAnchorLoader))
                for app_name in app_names:
                    do_export(app_name)
        except (IOError, NotFoundError):
            click.echo(_color("RED", " FAIL"))

    do_export(application, version)


@cli.command()
@click.argument("filenames", nargs=-1)
def import_app(filenames):
    global _platform

    regex = re.compile(r"^(.*?)(-v(\d+)|)\.[^.]+$")
    for filename in filenames:
        click.echo("Importing " + filename, nl=False)
        match = regex.match(basename(filename))
        if not match:
            click.echo(_color("RED", "FAIL") + " unknown filename format")
            break
        app_name = regex.match(basename(filename)).group(1)
        click.echo(" => " + _color("BLUE", app_name) + " ", nl=False)
        org = _platform.get_organization(qubell_config["organization"])
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


@cli.command()
@click.argument("organization")
def create_org(organization):
    global _platform

    click.echo(organization + " ", nl=False)
    try:
        org = _platform.get_organization(organization)
        click.echo(_color("YELLOW", org.id) + " already exists")
        return 1
    except NotFoundError:
        try:
            org = _platform.create_organization(organization)
            click.echo(_color("GREEN", org.id))
        except AssertionError:
            org = _platform.get_organization(organization)
            click.echo(_color("YELLOW", org.id) + " still initializing")

@cli.command()
@click.option("--type", default="", help="Provider name (for example, aws-ec2, openstack, etc)")
@click.option("--identity", default="", help="Provider identity or login, PROVIDER_IDENTITY by default")
@click.option("--credential", default="", help="Provider credential or secrete key or password, PROVIDER_CREDENTIAL by default")
@click.option("--region", default="", help="Provider region (for example, us-east-1), PROVIDER_REGION by default")
@click.option("--security-group", default="default", help="Default security group, \"default\" if not set")
@click.option("--environment", default="default", help="Account environment")
@click.argument("account_name")
def init_ca(account_name, environment, **kwargs):
    global _platform
    for (k, v) in kwargs.iteritems():
        if v:
            provider_config["provider_" + k] = v
    PROVIDER_CONFIG = {
        'configuration.provider': provider_config['provider_type'],
        'configuration.legacy-regions': provider_config['provider_region'],
        'configuration.endpoint-url': '',
        'configuration.legacy-security-group': '',
        'configuration.identity': provider_config['provider_identity'],
        'configuration.credential': provider_config['provider_credential']
    }
    click.echo(account_name + " ", nl=False)
    org = _platform.get_organization(qubell_config["organization"])
    type_to_app = lambda t: org.applications[system_application_types.get(t, t)]
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




if __name__ == '__main__':
    cli()
