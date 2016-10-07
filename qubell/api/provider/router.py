import os
import requests
from qubell.api.globals import QUBELL as qubell_config
from qubell.api.private.exceptions import ApiUnauthorizedError
from qubell.api.provider import route, play_auth, basic_auth
from qubell.api.provider.jwtauth import HTTPBearerAuth
from requests.auth import HTTPBasicAuth


class Router(object):
    def __init__(self, base_url=None, verify_ssl=False, verify_codes=True):
        self.base_url = base_url or qubell_config['tenant']
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
        self.verify_ssl = verify_ssl
        self.verify_codes = verify_codes

        self._cookies = None
        self._auth = None
        self._jwt_auth = None
        self.public_api_in_use = False

        self._creds = None

        self._session = requests.Session()

    @property
    def is_connected(self):
        return (self._cookies and ('PLAY_SESSION' in self._cookies)) or (self._jwt_auth and (self._jwt_auth.token))

    def connect(self, email=None, password=None, token=None):
        token = token or qubell_config['token']
        if token:
            self._jwt_auth = HTTPBearerAuth(token)
        else:
            email = email or qubell_config['user']
            password = password or qubell_config['password']
            url = self.base_url + '/signIn'
            data = {
                'email': email,
                'password': password}

            with self._session as session:
                session.post(url=url, data=data, verify=self.verify_ssl)
                self._cookies = session.cookies

            if not self.is_connected:
                raise ApiUnauthorizedError("Authentication failed, please check settings")

            self._auth = HTTPBasicAuth(email, password)
            self._creds = email, password


class InstanceRouter(object):
    """
    Router dependency
    """
    _router = None

    def init_router(self, router):
        assert router, "router cannot be None"
        self._router = router
        return self


class PrivatePath(Router):
    @route("POST /signIn")
    def post_sign_in(self, body): pass

    @route("GET /404")
    def get_404(self): pass

    @play_auth
    @route("POST /validate{ctype}")
    def post_validate(self, data, auth, cookies, ctype=".json", content_type="yaml"): pass

    # Organization
    @play_auth
    @route("POST /organizations{ctype}")
    def post_organization(self, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations{ctype}")
    def get_organizations(self, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}{ctype}")
    def get_organization(self, org_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications{ctype}")
    def post_organization_application(self, org_id, data, files, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/defaultEnvironment{ctype}")
    def put_organization_default_environment(self, org_id, env_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/launch{ctype}")
    def post_organization_instance(self, org_id, app_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/launchParameters{ctype}")
    def post_organization_launch_parameters(self, org_id, app_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/environments{ctype}")
    def post_organization_environment(self, org_id, data, auth, cookies, ctype=".json"): pass

    # Application
    @play_auth
    @route("GET /organizations/{org_id}/applications{ctype}")
    def get_applications(self, org_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/applications/{app_id}{ctype}")
    def put_application(self, org_id, app_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/applications/{app_id}{ctype}")
    def get_application(self, org_id, app_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/applications/{app_id}{ctype}")
    def delete_application(self, org_id, app_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/refreshManifest{ctype}")
    def post_application_refresh(self, org_id, app_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/manifests{ctype}")
    def post_application_manifest(self, org_id, app_id, data, files, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/applications/{app_id}/manifests/latest{ctype}")
    def get_application_manifests_latest(self, org_id, app_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/applications/{app_id}/manifests/{version}{ctype}")
    def get_application_manifest_version(self, org_id, app_id, auth, cookies, version, ctype=".json"): pass

    # Revision
    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/createRevision{ctype}")
    def post_revision(self, org_id, app_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/createRevision{ctype}")
    def post_revision_fs(self, org_id, app_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/applications/{app_id}/revisions/{rev_id}{ctype}")
    def get_revision(self, org_id, app_id, rev_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/applications/{app_id}/revisions{ctype}")
    def get_revisions(self, org_id, app_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/applications/{app_id}/revisions/{rev_id}{ctype}?force={force}")
    def delete_revision(self, org_id, app_id, rev_id, auth, cookies, data="{}", force="true", ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/applications/{app_id}/destroyedInstances{ctype}")
    def delete_destroyed_instances(self, org_id, app_id, auth, cookies, data="{}", ctype=".json"): pass

    # Instance
    @play_auth
    @route("GET /organizations/{org_id}/dashboard{ctype}")
    def get_instances(self, org_id, auth, cookies, params=None, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/instances/{instance_id}{ctype}")
    def get_instance(self, org_id, instance_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/workflows/{wf_name}{ctype}")
    def post_instance_workflow(self, org_id, instance_id, wf_name, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/components/{component_path}/workflows/{wf_name}{ctype}")
    def post_instance_component_workflow(self, org_id, instance_id, component_path, wf_name, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/instances/{instance_id}/configuration{ctype}")
    def put_instance_configuration(self, org_id, instance_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/instances/{instance_id}/configuration{ctype}")
    def get_instance_configuration(self, org_id, instance_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/reconfigure{ctype}")
    def post_instance_reconfigure(self, org_id, instance_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/instances/{instance_id}/rename{ctype}")
    def put_instance_rename(self, org_id, instance_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/environments/updateServiceEnvs/{instance_id}{ctype}")
    def post_instance_services(self, org_id, instance_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/environments/{env_id}/addSharedInstance{ctype}")
    def post_instance_shared(self, org_id, env_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/instances/{instance_id}/activitylog{ctype}")
    def get_instance_activitylog(self, org_id, instance_id, auth, cookies, params=None, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/{action}{ctype}")
    def post_instance_action(self, org_id, instance_id, action, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/instances/{instance_id}{ctype}?force=1")
    def delete_instance_force(self, org_id, instance_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/workflows/{wf_name}/schedule{ctype}")
    def post_instance_workflow_schedule(self, org_id, instance_id, wf_name, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/storedWorkflows/{workflow_id}/reschedule{ctype}")
    def post_instance_reschedule(self, org_id, instance_id, workflow_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/runtimeComponents/{component_id}{ctype}")
    def get_component_details(self, org_id, component_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/runtimeComponents{ctype}")
    def get_components(self, org_id, auth, cookies, params=None, ctype=".json"): pass

    # Environment
    @play_auth
    @route("GET /organizations/{org_id}/environments{ctype}")
    def get_environments(self, org_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/environments/{env_id}{ctype}")
    def get_environment(self, org_id, env_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/environments/{env_id}/availableServices{ctype}")
    def get_environment_available_services(self, org_id, env_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/environments/{env_id}{ctype}")
    def put_environment(self, org_id, env_id, data, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/environments/{env_id}{ctype}")
    def delete_environment(self, org_id, env_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/environments/{env_id}/import{ctype}")
    def post_env_import(self, org_id, env_id, auth, cookies, data="{}", files="{}", ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/environments/{env_id}/export")
    def get_env_export(self, org_id, env_id, auth, cookies): pass

    @play_auth
    @route("POST /api/1/environments/{env_id}/clone")
    def post_env_clone(self, env_id, auth, cookies, json): pass

    # Zone
    @play_auth
    @route("GET /organizations/{org_id}/zones{ctype}")
    def get_zones(self, org_id, auth, cookies, ctype=".json"): pass

    # Service
    @play_auth
    @route("GET /organizations/{org_id}/services{ctype}")
    def get_services(self, org_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/services/{instance_id}/keys/generate{ctype}")
    def post_service_generate(self, org_id, instance_id, auth, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/services/{instance_id}/keys{ctype}")
    def get_service_keys(self, org_id, instance_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/services/{instance_id}/keys/{key_id}/id_rsa.pub")
    def get_service_public_key(self, org_id, instance_id, key_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/environments/{env_id}/id_rsa")
    def get_environment_default_private_key(self, org_id, env_id, auth, cookies): pass

    @play_auth
    @route("POST /organizations/{org_id}/services/{instance_id}/secrets/{secret_id}/upload{ctype}")
    def post_request_upload_secret(self, org_id, instance_id, secret_id, auth, cookies, data="{}", ctype=".json"): pass

    # Role
    @play_auth
    @route("POST /organizations/{org_id}/roles{ctype}")
    def post_roles(self, org_id, auth, cookies, data, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/roles{ctype}")
    def get_roles(self, org_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/roles/{role_id}{ctype}")
    def get_role(self, org_id, auth, cookies, role_id, ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/roles/{role_id}{ctype}")
    def put_role(self, org_id, auth, cookies, role_id, data="{}", ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/roles/{role_id}{ctype}")
    def delete_role(self, org_id, auth, cookies, role_id, data="{}", ctype=".json"): pass

    # Users
    @play_auth
    @route("GET /organizations/{org_id}/users{ctype}")
    def get_users(self, org_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/users/{user_id}{ctype}")
    def put_user(self, org_id, auth, cookies, user_id, data="{}", ctype=".json"): pass

    @play_auth
    @route("get /organizations/{org_id}/users/current{ctype}")
    def get_organization_info(self, org_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/users/{user_id}{ctype}")
    def evict_user(self, org_id, auth, cookies, user_id, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /invite{ctype}")
    def invite_user(self, auth, cookies, data="{}", ctype=".json"): pass

    @route("POST /quickSignUp")
    def post_quick_sign_up(self, data=None, params=None, files=None): pass

    @play_auth
    @route("POST /organizations/{org_id}/init.json")
    def post_init(self, org_id, data, auth, cookies): pass

    @play_auth
    @route("POST /organizations/{org_id}/initCustomCloudAccount.json")
    def post_init_custom_cloud_account(self, org_id, data, auth, cookies): pass

    @play_auth
    @route("GET /organizations/{org_id}/welcomeWizardComponents.json")
    def get_welcome_wizard_components(self, org_id, auth, cookies): pass

    @play_auth
    @route("POST /organizations/{org_id}/initDockerService.json")
    def post_init_docker_service(self, org_id, auth, cookies, data="{}"): pass

    @play_auth
    @route("GET /applications/upload{ctype}")
    def get_upload(self, params, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/categories{ctype}")
    def get_categories(self, org_id, auth, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/application-kits.json")
    def post_application_kits(self, org_id, data, auth, cookies): pass

    # yes it uses public api but this is only convenient way to call command and get json results
    @basic_auth
    @route("POST /api/1/services/{instance_id}/{command_name}")
    def post_service_command(self, org_id, instance_id, command_name, auth, data="{}"):
        """
        :param org_id: not yet used but added for compatibility with future private api
        """
        pass

    @route("POST /refreshToken/jwtBearer")
    def generate_session_token(self, json):
        pass


# TODO: We shouldn't use subclassing to substitute private API for public API. Instead we should
# TODO: use a flag inside the client to distinguish between APIs and select the approprate methods to call
# TODO: inside the client itself.
class PublicPath(PrivatePath):
    # TODO: Public api hack.
    # We replace private routes with public ones. Fixing response reaction in code.
    # Yes, it's hack, but it costs less and acceptable for now

    # Organization
    @basic_auth
    @route("GET /api/1/organizations")
    def get_organizations(self, auth): pass

    # Application
    @basic_auth
    @route("POST /api/1/applications/{app_id}/launch")
    def post_organization_instance(self, org_id, app_id, data, auth): pass

    # TODO: Error here!!!!
    @basic_auth
    @route("PUT /api/1/applications/{app_id}/manifest")
    def post_application_manifest(self, org_id, app_id, data, auth, content_type="yaml"): pass

    @basic_auth
    @route("GET /api/1/organizations/{org_id}/applications")
    def get_applications(self, org_id, auth, data="{}"): pass

    @basic_auth
    @route("GET /api/1/applications/{app_id}/revisions")
    def get_revisions(self, org_id, app_id, rev_id, auth): pass

    # Instance
    @basic_auth
    @route("GET /api/1/instances/{instance_id}")
    def get_instance(self, org_id, instance_id, auth): pass

    @basic_auth
    @route("POST /api/1/instances/{instance_id}/{wf_name}")
    def post_instance_workflow(self, org_id, instance_id, wf_name, auth, data="{}"): pass

    # Environment
    # It returns policies yaml... Not usable
    # @basic_auth
    # @route("GET /api/1/environments/{env_id}")
    # def get_environment(self, org_id, env_id, auth): pass

    # TODO: Expected Yaml as payload..
    # @basic_auth
    # @route("PUT /api/1/environments/{env_id}")
    # def put_environment(self, org_id, env_id, data, auth, content_type="yaml"): pass

    @basic_auth
    @route("GET /api/1/organizations/{org_id}/environments")
    def get_environments(self, org_id, auth): pass

    # Above methods are kept for backwards compatibility; when/if the client is refactored,
    # they should go away, as well as the extension of `PrivatePath`.

    # Applications

    @basic_auth
    @route("POST /api/1/applications/{app_id}/launch")
    def api1_application_launch(self, app_id, json, auth): pass

    @basic_auth
    @route("PUT /api/1/applications/{app_id}/manifest")
    def api1_application_put_manifest(self, app_id, data, auth, content_type="yaml"): pass

    @basic_auth
    @route("GET /api/1/applications/{app_id}/revisions")
    def api1_application_list_revisions(self, app_id, auth): pass

    # Instances

    @basic_auth
    @route("GET /api/1/instances/{instance_id}")
    def api1_instance_details(self, instance_id, auth): pass

    @basic_auth
    @route("DELETE /api/1/instances/{instance_id}")
    def api1_instance_delete(self, instance_id, auth, params): pass

    @basic_auth
    @route("POST /api/1/instances/{instance_id}/destroy")
    def api1_instance_run_destroy(self, instance_id, auth, json): pass

    @basic_auth
    @route("POST /api/1/instances/{instance_id}/{workflow}")
    def api1_instance_run_workflow(self, instance_id, workflow, auth, json): pass

    @basic_auth
    @route("PUT /api/1/instances/{instance_id}/userData")
    def api1_instance_set_user_data(self, instance_id, json, auth): pass

    # Environments

    @basic_auth
    @route("GET /api/1/environments/{env_id}")
    def api1_environment_export(self, env_id, auth): pass

    @basic_auth
    @route("PUT /api/1/environments/{env_id}")
    def api1_environment_import(self, env_id, json, auth): pass

    @basic_auth
    @route("GET /api/1/environments/{env_id}/instances")
    def api1_environment_list_instances(self, env_id, auth): pass

    @basic_auth
    @route("GET /api/1/environments/{env_id}/markers")
    def api1_environment_list_markers(self, env_id, auth): pass

    @basic_auth
    @route("PUT /api/1/environments/{env_id}/properties")
    def api1_environment_update_markers(self, env_id, json, auth): pass

    @basic_auth
    @route("GET /api/1/environments/{env_id}/properties")
    def api1_environment_list_properties(self, env_id, auth): pass

    @basic_auth
    @route("PUT /api/1/environments/{env_id}/properties")
    def api1_environment_update_properties(self, env_id, json, auth): pass

    # Organizations

    @basic_auth
    @route("POST /api/1/organizations/{org_id}/serviceTypes")
    def api1_organization_create_service_type(self, org_id, json, auth): pass

    @basic_auth
    @route("GET /api/1/organizations/{org_id}/applications")
    def api1_organization_list_applications(self, org_id, auth): pass

    @basic_auth
    @route("GET /api/1/organizations/{org_id}/environments")
    def api1_organization_list_environments(self, org_id, auth): pass

    @basic_auth
    @route("GET /api/1/organizations")
    def api1_organization_list(self, auth): pass

    # Users

    @basic_auth
    @route("GET /api/1/organizations/{org_id}/users")
    def api1_user_list(self, org_id, auth): pass

    @basic_auth
    @route("PUT /api/1/organizations/{org_id}/users/{user_id}/roles")
    def api1_user_roles_assign(self, org_id, user_id, json, auth): pass

    @basic_auth
    @route("DELETE /api/1/organizations/{org_id}/users/{user_id}/roles")
    def api1_user_roles_revoke(self, org_id, user_id, json, auth): pass

    # Revisions

    @basic_auth
    @route("GET /api/1/revisions/{rev_id}/instances")
    def api1_revision_list_instances(self, rev_id, auth): pass

    # Services

    @basic_auth
    @route("GET /api/1/services/{service_id}")
    def api1_service_get(self, service_id, auth): pass

    @basic_auth
    @route("PUT /api/1/services/{service_id}")
    def api1_service_update(self, service_id, json, auth): pass

    @basic_auth
    @route("POST /api/1/services/{service_id}/{command}")
    def api1_service_execute(self, service_id, command, json, auth): pass

    # Roles

    @basic_auth
    @route("GET /api/1/organizations/{org_id}/roles")
    def api1_role_list(self, org_id, auth): pass

    @basic_auth
    @route("GET /api/1/roles/{role_id}")
    def api1_role_details(self, role_id, auth): pass

    @basic_auth
    @route("POST /api/1/organizations/{org_id}/roles")
    def api1_role_create(self, org_id, json, auth): pass

    @basic_auth
    @route("PUT /api/1/roles/{role_id}")
    def api1_role_update(self, role_id, json, auth): pass

    @basic_auth
    @route("DELETE /api/1/roles/{role_id}")
    def api1_role_delete(self, role_id, auth): pass


# TODO: Public api hack.
# To use public api routes, set QUBELL_USE_PUBLIC env to not None
if os.environ.get('QUBELL_USE_PUBLIC', None):
    ROUTER = PublicPath(os.environ.get('QUBELL_TENANT'))
    ROUTER.public_api_in_use = True
else:
    ROUTER = PrivatePath(os.environ.get('QUBELL_TENANT'))
