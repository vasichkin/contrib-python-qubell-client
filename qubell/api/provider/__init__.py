from functools import wraps
import inspect
import logging as log

import requests
import time
import sys

from qubell.api.private.exceptions import ApiError, api_http_code_errors


log.getLogger("requests.packages.urllib3.connectionpool").setLevel(log.ERROR)

_routes_stat = {}

def route(route_str):  # decorator param
    """
    Provides play2 likes routes, with python formatter
    All string fileds should be named parameters
    :param route_str: a route "GET /parent/{parentID}/child/{childId}{ctype}"
    :return: the response of requests.request
    """
    def ilog(elapsed):
        #statistic
        last_stat = _routes_stat.get(route_str, {"count": 0, "min": sys.maxint, "max": 0, "avg": 0})
        last_count = last_stat["count"]
        _routes_stat[route_str] = {
            "count": last_count + 1,
            "min": min(elapsed, last_stat["min"]),
            "max": max(elapsed, last_stat["max"]),
            "avg": (last_count * last_stat["avg"] + elapsed) / (last_count + 1)
        }
        #log.debug('Route Time: {0} took {1} ms'.format(route_str, elapsed))


    def wrapper(f):  # decorated function
        @wraps(f)
        def wrapped_func(*args, **kwargs):  # params of function
            self = args[0]
            method, url = route_str.split(" ")

            def defaults_dict():
                f_args, varargs, keywords, defaults = inspect.getargspec(f)
                defaults = defaults or []
                return dict(zip(f_args[-len(defaults):], defaults))

            defs = defaults_dict()

            route_args = dict(defs.items() + kwargs.items())

            def get_destination_url():
                try:
                    return url.format(**route_args)
                except KeyError as e:
                    raise AttributeError("Define {0} as named argument for route.".format(e))  # KeyError in format have a message with key

            destination_url = self.base_url + get_destination_url()
            f(*args, **kwargs)  # generally this is "pass"

            bypass_args = {param: route_args[param] for param in ["data", "cookies", "auth", "files", "content_type"] if param in route_args}

            #add json content type for:
            # - all public api, meaning have basic auth
            # - private that ends with .json
            # - unless files are sent
            if "files" not in bypass_args and (destination_url.endswith('.json') or "auth" in route_args):
                bypass_args['headers'] = {'Content-Type': 'application/json'}

            if "content_type" in bypass_args and bypass_args['content_type']=="yaml":
                del bypass_args["content_type"]
                bypass_args['headers'] = {'Content-Type': 'application/x-yaml'}

            start = time.time()
            response = requests.request(method, destination_url, verify=self.verify_ssl, **bypass_args)
            end = time.time()
            elapsed = int((end - start) * 1000.0)
            ilog(elapsed)

            if self.verify_codes:
                if response.status_code is not 200:
                    msg = "Route {0} {1} returned code={2} and error: {3}".format(method, get_destination_url(), response.status_code,
                                                                              response.text)
                    if response.status_code in api_http_code_errors.keys():
                        raise api_http_code_errors[response.status_code](msg)
                    else:
                        log.debug(response.text)
                        log.debug(response.request.body)
                        raise ApiError(msg)
            return response

        return wrapped_func

    return wrapper


def play_auth(f):
    """
    Injects cookies, into requests call over route
    :return: route
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        if "cookies" in kwargs:
            raise AttributeError("don't set cookies explicitly")
        assert self.is_connected, "not connected, call router.connect(email, password) first"
        assert self._cookies, "no cookies and connected o_O"
        kwargs["cookies"] = self._cookies
        return f(*args, **kwargs)

    return wrapper


def basic_auth(f):
    """
    Injects auth, into requests call over route
    :return: route
    """

    def wrapper(*args, **kwargs):
        self = args[0]
        if "auth" in kwargs:
            raise AttributeError("don't set auth token explicitly")
        assert self.is_connected, "not connected, call router.connect(email, password) first"
        assert self._auth, "no basic token and connected o_O"
        kwargs["auth"] = self._auth
        return f(*args, **kwargs)

    return wrapper

def log_routes_stat():
    nice_stat = ["  count: {0:<4} min: {1:<6} avg: {2:<6} max: {3:<6}  {4}".format(stat["count"], stat["min"], stat["avg"], stat["max"], r) for r, stat in _routes_stat.items()]
    log.info("Route Statistic\n{0}".format("\n".join(nice_stat)))