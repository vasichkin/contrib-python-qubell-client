import requests
import urlparse
from requests.auth import AuthBase


class HTTPBearerAuth(AuthBase):
    """Attaches HTTP Bearer Authentication to the given Request object."""

    session = requests.Session()
    session_token = None

    def __init__(self, refresh_token):
        self.refresh_token = refresh_token

    def __call__(self, r):
        self.ensure_session_token(r)

        r.headers['Authorization'] = 'Bearer %s' % self.session_token
        return r

    def ensure_session_token(self, request):
        if self.session_token: return  # TODO: also ensure it is not expired yet

        # noinspection PyProtectedMember
        jwt_bearer_url = \
            urlparse.urlsplit(request.url)._replace(path='/refreshToken/jwtBearer', query='', fragment='').geturl()

        response = requests.post(jwt_bearer_url, json={'refreshToken': self.refresh_token})
        assert response.status_code == 200, "Failed to retrieve JWT bearer: %s" % response.text

        self.session_token = response.json()['jwtBearer']
