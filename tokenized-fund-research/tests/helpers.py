"""Shared test helpers: load scripts by path (they are not a package) and fake HTTP."""

import email.message
import importlib.util
import io
import json
import os
import sys
import urllib.error

# loading the scripts must not leave __pycache__ inside the skill directory
sys.dont_write_bytecode = True

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
FIXTURES = os.path.join(TESTS_DIR, "fixtures")


def load_script(name):
    path = os.path.join(SCRIPTS, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_path(*parts):
    return os.path.join(FIXTURES, *parts)


def read_fixture(*parts, mode="r"):
    with open(fixture_path(*parts), mode, **({} if "b" in mode else {"encoding": "utf-8"})) as fh:
        return fh.read()


class FakeResponse:
    def __init__(self, body, content_type="application/json", status=200):
        self._body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        self.status = status

    def read(self, amt=None):
        return self._body if amt is None else self._body[:amt]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(url, code, body=b"", headers=None):
    msg = email.message.Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    return urllib.error.HTTPError(url, code, f"HTTP {code}", msg, io.BytesIO(body))


def json_response(obj):
    return FakeResponse(json.dumps(obj))


class FakeOpener:
    """Callable replacing urllib.request.urlopen.

    routes: list of (predicate(url) -> bool, action). action is a FakeResponse, an
    exception instance (raised), or a list of those consumed one per call.
    Records every requested URL and the request headers in .calls.
    """

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        headers = dict(req.header_items()) if hasattr(req, "header_items") else {}
        self.calls.append((url, headers))
        for pred, action in self.routes:
            if pred(url):
                if isinstance(action, list):
                    if not action:
                        raise AssertionError(f"route exhausted for {url}")
                    action = action.pop(0) if len(action) > 1 else action[0]
                if isinstance(action, BaseException):
                    raise action
                return action
        raise AssertionError(f"unexpected URL {url}")

    def urls(self):
        return [u for u, _ in self.calls]
