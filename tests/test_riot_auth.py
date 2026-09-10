import pytest

import riot_auth
from conftest import FakeResponse, FakeTransport, FakeWindow, make_jwt

REDIRECT = 'https://playvalorant.com/fr-fr/opt_in/#access_token=aaa&id_token=bbb&expires_in=3600'


def test_module_exposes_its_interface():
    assert hasattr(riot_auth, 'AuthError')


@pytest.mark.parametrize('url', [
    REDIRECT,
    'https://playvalorant.com/opt_in#access_token=aaa',
    'https://playvalorant.com/opt_in/#access_token=aaa',
    'https://playvalorant.com/en-us/opt_in/#access_token=aaa',
    'https://playvalorant.com/pt-br/opt_in/#access_token=aaa',
])
def test_capture_accepted_on_official_redirect(url):
    assert riot_auth.is_capture_url(url) is True


@pytest.mark.parametrize('url', [
    'https://playvalorant.com/fr-fr/opt_in/',
    'http://playvalorant.com/fr-fr/opt_in/#access_token=aaa',
    'https://playvalorant.com.attaquant.fr/fr-fr/opt_in/#access_token=aaa',
    'https://attaquant.fr/fr-fr/opt_in/#access_token=aaa',
    'https://playvalorant.com/fr-fr/opt_in/evil#access_token=aaa',
    'https://auth.riotgames.com/login#access_token=aaa',
    '',
    None,
])
def test_capture_refused_anywhere_else(url):
    assert riot_auth.is_capture_url(url) is False


def test_fragment_read_out_of_order():
    url = 'https://playvalorant.com/fr-fr/opt_in/#expires_in=3600&id_token=bbb&access_token=aaa&scope=openid'
    assert riot_auth.parse_fragment(url) == {'access_token': 'aaa', 'id_token': 'bbb', 'expires_in': 3600}


def test_fragment_percent_encoded():
    url = 'https://playvalorant.com/fr-fr/opt_in/#access_token=a%2Bb&id_token=bbb&expires_in=3600'
    assert riot_auth.parse_fragment(url)['access_token'] == 'a+b'


def test_fragment_without_expires_in_defaults_to_one_hour():
    url = 'https://playvalorant.com/fr-fr/opt_in/#access_token=aaa&id_token=bbb'
    assert riot_auth.parse_fragment(url)['expires_in'] == 3600


def test_fragment_with_unreadable_expires_in_defaults_to_one_hour():
    url = 'https://playvalorant.com/fr-fr/opt_in/#access_token=aaa&id_token=bbb&expires_in=bientot'
    assert riot_auth.parse_fragment(url)['expires_in'] == 3600


def test_fragment_riot_error_reports_suspension():
    url = 'https://playvalorant.com/fr-fr/opt_in/#error=access_denied'
    with pytest.raises(riot_auth.AuthError) as capture:
        riot_auth.parse_fragment(url)
    assert capture.value.kind == 'refused'
    assert 'suspended' in str(capture.value)


def test_fragment_without_token_requires_sign_in():
    with pytest.raises(riot_auth.AuthError) as capture:
        riot_auth.parse_fragment('https://playvalorant.com/fr-fr/opt_in/')
    assert capture.value.kind == 'needs_login'


def test_puuid_extracted_from_id_token():
    token = make_jwt({'sub': '11111111-2222-3333-4444-555555555555'})
    assert riot_auth.puuid_from_id_token(token) == '11111111-2222-3333-4444-555555555555'


def test_puuid_handles_missing_base64_padding():
    token = make_jwt({'sub': '11111111-2222-3333-4444-555555555555', 'pad': 'x'})
    assert riot_auth.puuid_from_id_token(token).startswith('11111111')


@pytest.mark.parametrize('token', ['', 'aaa', 'a.b', 'a.!!!.c', make_jwt({'autre': 1})])
def test_puuid_rejects_invalid_token(token):
    with pytest.raises(riot_auth.AuthError):
        riot_auth.puuid_from_id_token(token)


def test_puuid_rejects_sub_that_is_not_a_uuid():
    with pytest.raises(riot_auth.AuthError):
        riot_auth.puuid_from_id_token(make_jwt({'sub': '../../etc/passwd'}))


def test_entitlements_returns_the_token():
    transport = FakeTransport({'https://entitlements.auth.riotgames.com':
                               FakeResponse(200, {'entitlements_token': 'jeton-ent'})})
    assert riot_auth.fetch_entitlements('acces', transport) == 'jeton-ent'
    assert transport.calls == [('POST', 'https://entitlements.auth.riotgames.com/api/token/v1')]


def test_entitlements_403_reports_suspension():
    transport = FakeTransport({'https://entitlements.auth.riotgames.com': FakeResponse(403)})
    with pytest.raises(riot_auth.AuthError) as capture:
        riot_auth.fetch_entitlements('acces', transport)
    assert capture.value.kind == 'refused'


def test_entitlements_401_requires_sign_in():
    transport = FakeTransport({'https://entitlements.auth.riotgames.com': FakeResponse(401)})
    with pytest.raises(riot_auth.AuthError) as capture:
        riot_auth.fetch_entitlements('acces', transport)
    assert capture.value.kind == 'needs_login'


def test_entitlements_200_without_token_is_a_refusal():
    transport = FakeTransport({'https://entitlements.auth.riotgames.com': FakeResponse(200, {})})
    with pytest.raises(riot_auth.AuthError) as capture:
        riot_auth.fetch_entitlements('acces', transport)
    assert capture.value.kind == 'refused'


@pytest.mark.parametrize('payload, expected', [
    ({'affinity': 'eu'}, 'eu'),
    ({'affinities': {'live': 'na'}}, 'na'),
    ({'affinity': 'EU'}, 'eu'),
])
def test_region_read_from_pas_token(payload, expected):
    assert riot_auth.region_from_pas(make_jwt(payload)) == expected


def test_region_ignores_desired_affinity():
    token = make_jwt({'affinity': 'eu', 'desired.affinity': 'na'})
    assert riot_auth.region_from_pas(token) == 'eu'


def test_region_missing_from_pas_token():
    with pytest.raises(riot_auth.AuthError):
        riot_auth.region_from_pas(make_jwt({'sub': 'x'}))


@pytest.mark.parametrize('region, shard', [
    ('eu', 'eu'), ('na', 'na'), ('br', 'na'), ('latam', 'na'),
    ('ap', 'ap'), ('kr', 'kr'), ('inconnue', 'eu'),
])
def test_shard_derived_from_region(region, shard):
    assert riot_auth.resolve_shard(region) == shard


def test_region_resolved_from_api():
    transport = FakeTransport({'https://riot-geo.pas.si.riotgames.com':
                               FakeResponse(200, text='"' + make_jwt({'affinity': 'br'}) + '"')})
    assert riot_auth.fetch_region('acces', transport) == ('br', 'na')


def test_region_falls_back_to_eu_when_pas_fails():
    transport = FakeTransport({'https://riot-geo.pas.si.riotgames.com': FakeResponse(500)})
    assert riot_auth.fetch_region('acces', transport) == ('eu', 'eu')


def test_region_falls_back_to_eu_when_pas_is_unreadable():
    transport = FakeTransport({'https://riot-geo.pas.si.riotgames.com':
                               FakeResponse(200, text='pas-un-jwt')})
    assert riot_auth.fetch_region('acces', transport) == ('eu', 'eu')


def test_watch_captures_the_redirect():
    window = FakeWindow(['https://auth.riotgames.com/login', REDIRECT])
    clock = iter([0.0, 0.5, 1.0])
    assert riot_auth.watch(window, 8.0, lambda: next(clock), lambda _: None) == REDIRECT
    assert window.destroyed is True


def test_watch_gives_up_after_the_deadline():
    window = FakeWindow(['https://auth.riotgames.com/login'] * 50)
    clock = iter([0.0, 4.0, 9.0])
    assert riot_auth.watch(window, 8.0, lambda: next(clock), lambda _: None) is None


def test_watch_ignores_a_foreign_origin():
    window = FakeWindow(['https://attaquant.fr/fr-fr/opt_in/#access_token=vole'] * 50)
    clock = iter([0.0, 9.0])
    assert riot_auth.watch(window, 8.0, lambda: next(clock), lambda _: None) is None
    assert window.destroyed is False


def test_credentials_expiry():
    valid_creds = riot_auth.Credentials('a', 'e', 'p', 'eu', 'eu', expires_at=10 ** 12)
    expired_creds = riot_auth.Credentials('a', 'e', 'p', 'eu', 'eu', expires_at=0)
    assert valid_creds.is_valid() is True
    assert expired_creds.is_valid() is False


def test_credentials_carry_a_stable_session_key():
    first = riot_auth.Credentials('a', 'e', '1111', 'eu', 'eu', expires_at=10 ** 12)
    second = riot_auth.Credentials('autre', 'e', '1111', 'eu', 'eu', expires_at=10 ** 12)
    assert first.key == second.key


def test_credentials_leak_no_token_in_their_repr():
    text = repr(riot_auth.Credentials('jeton-secret', 'ent-secret', '1111', 'eu', 'eu', expires_at=1))
    assert 'jeton-secret' not in text and 'ent-secret' not in text


def test_credentials_round_trip_through_dict():
    origin = riot_auth.Credentials('a', 'e', '1111', 'eu', 'eu', expires_at=42)
    copy_ = riot_auth.Credentials.from_dict(origin.as_dict())
    assert copy_.as_dict() == origin.as_dict()
    assert copy_.key == origin.key
