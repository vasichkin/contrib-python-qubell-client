import os

import requests
from requests.auth import HTTPBasicAuth

from qubell.api.private.exceptions import ApiUnauthorizedError
from qubell.api.provider import route, play_auth, basic_auth


class Router(object):
    def __init__(self, base_url, verify_ssl=False, verify_codes=True):
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.verify_codes = verify_codes

        self._cookies = None
        self._auth = None
        self.public_api_in_use = False

    @property
    def is_connected(self):
        return self._cookies and 'PLAY_SESSION' in self._cookies

    #todo: add integration test for this
    def connect(self, email, password):
        url = self.base_url + '/signIn'
        data = {
            'email': email,
            'password': password}
        with requests.session() as session:
            session.post(url=url, data=data, verify=self.verify_ssl)
            self._cookies = session.cookies

        if not self.is_connected:
            raise ApiUnauthorizedError("Authentication failed, please check settings")

        self._auth = HTTPBasicAuth(email, password)

class PrivatePath(Router):

    @route("POST /signIn")
    def post_sign_in(self, body): pass

    @route("GET /404")
    def get_404(self): pass

    #Organization
    @play_auth
    @route("POST /organizations{ctype}")
    def post_organization(self, data, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations{ctype}")
    def get_organizations(self, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}{ctype}")
    def get_organization(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications{ctype}")
    def post_organization_application(self, org_id, data, files, cookies, ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/defaultEnvironment{ctype}")
    def put_organization_default_environment(self, org_id, env_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/launch{ctype}")
    def post_organization_instance(self, org_id, app_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/environments{ctype}")
    def post_organization_environment(self, org_id, data, cookies, ctype=".json"): pass

    #Application
    @play_auth
    @route("GET /organizations/{org_id}/applications{ctype}")
    def get_applications(self, org_id, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/applications/{app_id}{ctype}")
    def put_application(self, org_id, app_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/applications/{app_id}{ctype}")
    def get_application(self, org_id, app_id, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/applications/{app_id}{ctype}")
    def delete_application(self, org_id, app_id, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/refreshManifest{ctype}")
    def post_application_refresh(self, org_id, app_id, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/manifests{ctype}")
    def post_application_manifest(self, org_id, app_id, data, files, cookies, ctype=".json"): pass

    #Revision
    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/createRevision{ctype}")
    def post_revision(self, org_id, app_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/applications/{app_id}/createRevision{ctype}")
    def post_revision_fs(self, org_id, app_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/applications/{app_id}/revisions/{rev_id}{ctype}")
    def get_revision(self, org_id, app_id, rev_id, cookies, ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/applications/{app_id}/revisions/{rev_id}{ctype}")
    def delete_revision(self, org_id, app_id, rev_id, cookies, data="{}", ctype=".json"): pass

    #Instance
    @play_auth
    @route("GET /organizations/{org_id}/dashboard{ctype}")
    def get_instances(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/instances/{instance_id}{ctype}")
    def get_instance(self, org_id, instance_id, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/workflows/{wf_name}{ctype}")
    def post_instance_workflow(self, org_id, instance_id, wf_name, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/instances/{instance_id}/configuration{ctype}")
    def put_instance_configuration(self, org_id, instance_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/environments/updateServiceEnvs/{instance_id}{ctype}")
    def post_instance_services(self, org_id, instance_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/environments/{env_id}/addSharedInstance{ctype}")
    def post_instance_shared(self, org_id, env_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/instances/{instance_id}/activitylog{ctype}")
    def get_instance_activitylog(self, org_id, instance_id, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/instances/{instance_id}/activitylog{ctype}?after={timestamp}")
    def get_instance_activitylog_after(self, org_id, instance_id, timestamp, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/{action}{ctype}")
    def post_instance_action(self, org_id, instance_id, action, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/instances/{instance_id}{ctype}?force=1")
    def delete_instance_force(self, org_id, instance_id, cookies, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/workflows/{wf_name}/schedule{ctype}")
    def post_instance_workflow_schedule(self, org_id, instance_id, wf_name, data, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/instances/{instance_id}/storedWorkflows/{workflow_id}/reschedule{ctype}")
    def post_instance_reschedule(self, org_id, instance_id, workflow_id, data, cookies, ctype=".json"): pass

    #Environment
    @play_auth
    @route("GET /organizations/{org_id}/environments{ctype}")
    def get_environments(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/environments/{env_id}{ctype}")
    def get_environment(self, org_id, env_id, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/environments/{env_id}/availableServices{ctype}")
    def get_environment_available_services(self, org_id, env_id, cookies, ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/environments/{env_id}{ctype}")
    def put_environment(self, org_id, env_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/environments/{env_id}{ctype}")
    def delete_environment(self, org_id, env_id, cookies, data="{}", ctype=".json"): pass

    #Zone
    @play_auth
    @route("GET /organizations/{org_id}/zones{ctype}")
    def get_zones(self, org_id, cookies, ctype=".json"): pass

    #Service
    @play_auth
    @route("GET /organizations/{org_id}/services{ctype}")
    def get_services(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/services/{instance_id}/keys/generate{ctype}")
    def post_service_generate(self, org_id, instance_id, cookies, data="{}", ctype=".json"): pass

    # Role
    @play_auth
    @route("POST /organizations/{org_id}/roles{ctype}")
    def post_roles(self, org_id, cookies, data, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/roles{ctype}")
    def get_roles(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("GET /organizations/{org_id}/roles/{role_id}{ctype}")
    def get_role(self, org_id, cookies, role_id, ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/roles/{role_id}{ctype}")
    def put_role(self, org_id, cookies, role_id, data="{}", ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/roles/{role_id}{ctype}")
    def delete_role(self, org_id, cookies, role_id, data="{}", ctype=".json"): pass

    # Users
    @play_auth
    @route("GET /organizations/{org_id}/users{ctype}")
    def get_users(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("PUT /organizations/{org_id}/users/{user_id}{ctype}")
    def put_user(self, org_id, cookies, user_id, data="{}", ctype=".json"): pass

    @play_auth
    @route("get /organizations/{org_id}/users/current{ctype}")
    def get_organization_info(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/users/{user_id}{ctype}")
    def evict_user(self, org_id, cookies, user_id, data="{}", ctype=".json"): pass

    @play_auth
    @route("POST /organizations/invite{ctype}")
    def invite_user(self, cookies, data="{}", ctype=".json"): pass

class PublicPath(PrivatePath):
# TODO: Public api hack.
# We replace private routes with public ones. Fixing response reaction in code.
# Yes, it's hack, but it costs less and acceptable for now

#Organization
    @basic_auth
    @route("GET /api/1/organizations")
    def get_organizations(self, auth): pass

#Application
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

#Instance
    @basic_auth
    @route("GET /api/1/instances/{instance_id}")
    def get_instance(self, org_id, instance_id, auth): pass

    @basic_auth
    @route("POST /api/1/instances/{instance_id}/{wf_name}")
    def post_instance_workflow(self, org_id, instance_id, wf_name, auth, data="{}"): pass

# Environment
    # It returns policies yaml... Not usable
    #@basic_auth
    #@route("GET /api/1/environments/{env_id}")
    #def get_environment(self, org_id, env_id, auth): pass

    # TODO: Expected Yaml as payload..
    #@basic_auth
    #@route("PUT /api/1/environments/{env_id}")
    #def put_environment(self, org_id, env_id, data, auth, content_type="yaml"): pass

    @basic_auth
    @route("GET /api/1/organizations/{org_id}/environments")
    def get_environments(self, org_id, auth): pass

# TODO: Public api hack.
# To use public api routes, set QUBELL_USE_PUBLIC env to not None
if os.environ.get('QUBELL_USE_PUBLIC', None):
    ROUTER = PublicPath(os.environ.get('QUBELL_TENANT'))
    ROUTER.public_api_in_use = True
else:
    ROUTER = PrivatePath(os.environ.get('QUBELL_TENANT'))
