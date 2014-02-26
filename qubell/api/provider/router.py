import os

import requests
from requests.auth import HTTPBasicAuth

from qubell.api.private.exceptions import ApiUnauthorizedError
from qubell.api.provider import route, play_auth


class Router(object):
    def __init__(self, base_url, verify_ssl=False, verify_codes=True):
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.verify_codes = verify_codes

        self._cookies = None
        self._auth = None

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
    @route("POST /organizations/{org_id}/applications/{app_id}/revisions{ctype}")
    def post_revision(self, org_id, app_id, data, cookies, ctype=".json"): pass

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

    #CloudProvider
    @play_auth
    @route("GET /organizations/{org_id}/providers{ctype}")
    def get_providers(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/providers{ctype}")
    def post_provider(self, org_id, data, cookies, ctype=".json"): pass

    @play_auth
    @route("DELETE /organizations/{org_id}/providers/{prov_id}{ctype}")
    def delete_provider(self, org_id, prov_id, cookies, ctype=".json"): pass

    #Service
    @play_auth
    @route("GET /organizations/{org_id}/services{ctype}")
    def get_services(self, org_id, cookies, ctype=".json"): pass

    @play_auth
    @route("POST /organizations/{org_id}/services/{instance_id}/keys/generate{ctype}")
    def post_service_generate(self, org_id, instance_id, cookies, data="{}", ctype=".json"): pass


ROUTER = Router(os.environ.get('QUBELL_TENANT'))