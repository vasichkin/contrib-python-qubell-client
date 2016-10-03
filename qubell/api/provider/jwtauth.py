from requests import Session
from requests.auth import AuthBase


class HTTPBearerAuth(AuthBase):
    """Attaches HTTP Bearer Authentication to the given Request object."""

    session = Session()

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'Bearer %s' % self.token
        return r
