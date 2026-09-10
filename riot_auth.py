import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import requests

AUTHORIZE_URL = ('https://auth.riotgames.com/authorize'
                 '?redirect_uri=https%3A%2F%2Fplayvalorant.com%2Fopt_in'
                 '&client_id=play-valorant-web-prod'
                 '&response_type=token%20id_token'
                 '&nonce=1&scope=account%20openid')
ENTITLEMENTS_URL = 'https://entitlements.auth.riotgames.com/api/token/v1'
PAS_URL = 'https://riot-geo.pas.si.riotgames.com/pas/v1/service/chat'
OPT_IN_PATH = re.compile(r'/(?:[a-z]{2}-[a-z]{2}/)?opt_in/?')
UUID_PATTERN = re.compile(r'[0-9a-fA-F-]{36}')
SHARDS = {'eu', 'na', 'ap', 'kr', 'pbe'}
REGION_TO_SHARD = {'br': 'na', 'latam': 'na'}
SILENT_TIMEOUT = 8.0
LOGIN_TIMEOUT = 3600.0
POLL_INTERVAL = 0.25
PROFILE_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ValorantInventory' / 'webview'
MODULE_PATH = str(Path(__file__).resolve())


class AuthError(Exception):
    def __init__(self, message, kind='unavailable'):
        super().__init__(message)
        self.kind = kind


def is_capture_url(url):
    if not url:
        return False
    parts = urlsplit(url)
    return (parts.scheme == 'https' and parts.hostname == 'playvalorant.com'
            and OPT_IN_PATH.fullmatch(parts.path) is not None
            and bool(parts.fragment))


def parse_fragment(url):
    fragment = urlsplit(url).fragment if url else ''
    values = dict(parse_qsl(fragment))
    if values.get('error'):
        raise AuthError('Riot refused the authorization. This is expected '
                        'if the account is suspended.', 'refused')
    if not values.get('access_token') or not values.get('id_token'):
        raise AuthError('Riot session expired.', 'needs_login')
    try:
        expires_in = int(values.get('expires_in', 3600))
    except ValueError:
        expires_in = 3600
    return {'access_token': values['access_token'], 'id_token': values['id_token'],
            'expires_in': expires_in}


def _jwt_payload(token):
    parts = (token or '').split('.')
    if len(parts) != 3:
        raise AuthError('Unreadable Riot token.', 'needs_login')
    segment = parts[1] + '=' * (-len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(segment))
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise AuthError('Unreadable Riot token.', 'needs_login') from None


def puuid_from_id_token(id_token):
    subject = _jwt_payload(id_token).get('sub', '')
    if not UUID_PATTERN.fullmatch(subject):
        raise AuthError('Invalid Riot account id.', 'needs_login')
    return subject


def _default_transport(method, url, headers=None, json=None, timeout=None):
    return requests.request(method, url, headers=headers, json=json, timeout=timeout)


def fetch_entitlements(access_token, transport=None):
    send = transport or _default_transport
    response = send('POST', ENTITLEMENTS_URL,
                    headers={'Authorization': 'Bearer ' + access_token,
                             'Content-Type': 'application/json'},
                    json={}, timeout=20)
    if response.status_code == 401:
        raise AuthError('Riot session expired.', 'needs_login')
    if response.status_code != 200:
        raise AuthError('Signed in successfully, but Riot denies access to the inventory. '
                        'This is expected if the account is suspended.', 'refused')
    try:
        token = response.json().get('entitlements_token')
    except ValueError:
        token = None
    if not token:
        raise AuthError('Unexpected Riot response for account entitlements.', 'refused')
    return token


def region_from_pas(pas_jwt):
    payload = _jwt_payload(pas_jwt)
    region = payload.get('affinity') or (payload.get('affinities') or {}).get('live')
    if not region:
        raise AuthError('Account region not found.', 'refused')
    return str(region).lower()


def resolve_shard(region):
    shard = REGION_TO_SHARD.get(region, region)
    return shard if shard in SHARDS else 'eu'


def fetch_region(access_token, transport=None):
    send = transport or _default_transport
    try:
        response = send('GET', PAS_URL, headers={'Authorization': 'Bearer ' + access_token},
                        timeout=20)
        if response.status_code != 200:
            return 'eu', 'eu'
        region = region_from_pas(response.text.strip().strip('"'))
    except (AuthError, requests.RequestException):
        return 'eu', 'eu'
    return region, resolve_shard(region)


class Credentials:
    def __init__(self, access_token, entitlements_token, puuid, region, shard, expires_at):
        self.access_token = access_token
        self.entitlements_token = entitlements_token
        self.puuid = puuid
        self.region = region
        self.shard = shard
        self.expires_at = expires_at
        self.key = hashlib.sha256((puuid + shard).encode()).hexdigest()[:24]

    def is_valid(self, now=None):
        return (now if now is not None else time.time()) < self.expires_at - 60

    def __repr__(self):
        return '<Credentials %s %s>' % (self.key, self.shard)

    def as_dict(self):
        return {'access_token': self.access_token, 'entitlements_token': self.entitlements_token,
                'puuid': self.puuid, 'region': self.region, 'shard': self.shard,
                'expires_at': self.expires_at}

    @classmethod
    def from_dict(cls, values):
        return cls(values['access_token'], values['entitlements_token'], values['puuid'],
                   values['region'], values['shard'], values['expires_at'])


def watch(window, deadline, clock=time.monotonic, sleep=time.sleep):
    start = clock()
    while clock() - start < deadline:
        url = window.get_current_url()
        if is_capture_url(url):
            window.destroy()
            return url
        sleep(POLL_INTERVAL)
    return None


def _credentials_from_url(url):
    values = parse_fragment(url)
    puuid = puuid_from_id_token(values['id_token'])
    entitlements = fetch_entitlements(values['access_token'])
    region, shard = fetch_region(values['access_token'])
    return Credentials(values['access_token'], entitlements, puuid, region, shard,
                       time.time() + values['expires_in'])


def logout():
    shutil.rmtree(PROFILE_DIR, ignore_errors=True)


def _run_gui(interactive):
    import webview
    captured = {}

    window = webview.create_window('Riot sign-in', AUTHORIZE_URL, width=980, height=860,
                                   min_size=(900, 700), hidden=not interactive)

    def watcher():
        url = watch(window, LOGIN_TIMEOUT if interactive else SILENT_TIMEOUT)
        if not url and interactive:
            window.show()
            url = watch(window, LOGIN_TIMEOUT)
        if url:
            captured['url'] = url
        else:
            try:
                window.destroy()
            except Exception:
                pass

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    webview.start(watcher, private_mode=False, storage_path=str(PROFILE_DIR),
                  debug=os.environ.get('RIOT_AUTH_DEBUG') == '1')
    return captured.get('url')


def authenticate(interactive):
    flag = '--login' if interactive else '--silent'
    try:
        result = subprocess.run([sys.executable, MODULE_PATH, flag], capture_output=True,
                                text=True, timeout=900 if interactive else 60)
    except subprocess.TimeoutExpired:
        raise AuthError('The Riot sign-in window is not responding.', 'cancelled') from None
    try:
        payload = json.loads(result.stdout or '{}')
    except ValueError:
        raise AuthError('WebView2 not found. Install the Microsoft Edge WebView2 Runtime.',
                        'unavailable') from None
    if not payload.get('ok'):
        raise AuthError(payload.get('message', 'Riot sign-in failed.'),
                        payload.get('kind', 'unavailable'))
    return Credentials.from_dict(payload['credentials'])


def _main():
    interactive = '--login' in sys.argv
    try:
        url = _run_gui(interactive)
        if not url:
            raise AuthError('Riot session expired.',
                            'cancelled' if interactive else 'needs_login')
        payload = {'ok': True, 'credentials': _credentials_from_url(url).as_dict()}
    except AuthError as error:
        payload = {'ok': False, 'kind': error.kind, 'message': str(error)}
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


if __name__ == '__main__':
    _main()
