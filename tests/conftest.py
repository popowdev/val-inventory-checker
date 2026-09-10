import base64
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_jwt(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    return 'entete.' + body + '.signature'


class FakeWindow:
    def __init__(self, urls):
        self.urls = list(urls)
        self.destroyed = False
        self.shown = False

    def get_current_url(self):
        return self.urls.pop(0) if self.urls else None

    def destroy(self):
        self.destroyed = True

    def show(self):
        self.shown = True


class FakeResponse:
    def __init__(self, status_code, payload=None, text=''):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError('pas de JSON')
        return self._payload


class FakeTransport:
    def __init__(self, responses):
        self.responses = dict(responses)
        self.calls = []

    def __call__(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append((method, url))
        for prefix, response in self.responses.items():
            if url.startswith(prefix):
                return response
        raise AssertionError('URL non prevue par le test : ' + url)


@pytest.fixture
def jwt():
    return make_jwt
