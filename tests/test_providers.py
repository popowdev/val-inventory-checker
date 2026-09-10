import pytest

import riot_auth
import valorant_inventory as tool


@pytest.fixture
def no_lockfile(monkeypatch):
    monkeypatch.setattr(tool, 'get_lockfile', lambda: None)


@pytest.fixture(autouse=True)
def clean_state():
    with tool._state_lock:
        tool._state.update({'status': 'waiting', 'session': None})
        tool._credentials = None
    yield


def _credentials():
    return riot_auth.Credentials('acces', 'ent', '11111111-2222-3333-4444-555555555555',
                                 'eu', 'eu', expires_at=10 ** 12)


def test_lockfile_takes_priority(monkeypatch):
    calls = []
    monkeypatch.setattr(tool, 'get_lockfile', lambda: {'port': 1, 'password': 'x'})
    monkeypatch.setattr(tool, '_credentials_from_lockfile',
                        lambda lockfile: (('cle', 'a', 'e', '1111', 'eu', 'eu'), True))
    monkeypatch.setattr(riot_auth, 'authenticate', lambda interactive: calls.append(interactive))
    result, active = tool.detect_riot_credentials()
    assert result[0] == 'cle'
    assert active is True
    assert calls == []


def test_broken_lockfile_falls_back_to_the_browser(monkeypatch):
    def broken_lockfile(lockfile):
        raise tool.ToolError('lockfile illisible', 503)

    monkeypatch.setattr(tool, 'get_lockfile', lambda: {'port': 1, 'password': 'x'})
    monkeypatch.setattr(tool, '_credentials_from_lockfile', broken_lockfile)
    monkeypatch.setattr(riot_auth, 'authenticate', lambda interactive: _credentials())
    result, active = tool.detect_riot_credentials()
    assert result[3] == '11111111-2222-3333-4444-555555555555'


def test_without_lockfile_the_silent_attempt_runs(monkeypatch, no_lockfile):
    calls = []

    def fake_auth(interactive):
        calls.append(interactive)
        return _credentials()

    monkeypatch.setattr(riot_auth, 'authenticate', fake_auth)
    result, active = tool.detect_riot_credentials()
    assert calls == [False]
    assert active is False
    assert result[4:] == ('eu', 'eu')


def test_failed_silent_attempt_never_shows_a_window(monkeypatch, no_lockfile):
    def fake_auth(interactive):
        raise riot_auth.AuthError('expired', 'needs_login')

    monkeypatch.setattr(riot_auth, 'authenticate', fake_auth)
    with pytest.raises(tool.ToolError) as capture:
        tool.detect_riot_credentials(interactive=False)
    assert capture.value.status == 401


def test_interactive_mode_opens_the_window(monkeypatch, no_lockfile):
    calls = []

    def fake_auth(interactive):
        calls.append(interactive)
        if interactive:
            return _credentials()
        raise riot_auth.AuthError('expired', 'needs_login')

    monkeypatch.setattr(riot_auth, 'authenticate', fake_auth)
    tool.detect_riot_credentials(interactive=True)
    assert calls == [False, True]


def test_a_riot_refusal_does_not_retry(monkeypatch, no_lockfile):
    calls = []

    def fake_auth(interactive):
        calls.append(interactive)
        raise riot_auth.AuthError('account suspended', 'refused')

    monkeypatch.setattr(riot_auth, 'authenticate', fake_auth)
    with pytest.raises(tool.ToolError) as capture:
        tool.detect_riot_credentials(interactive=True)
    assert calls == [False]
    assert 'suspended' in str(capture.value)
    assert capture.value.status == 403


def test_a_cancellation_is_not_a_failure(monkeypatch, no_lockfile):
    monkeypatch.setattr(riot_auth, 'authenticate',
                        lambda interactive: (_ for _ in ()).throw(
                            riot_auth.AuthError('Sign-in cancelled.', 'cancelled')))
    with pytest.raises(tool.ToolError) as capture:
        tool.detect_riot_credentials(interactive=True)
    assert capture.value.status == 503


@pytest.fixture
def client():
    tool.app.config['TESTING'] = True
    with tool.app.test_client() as client:
        yield client


def test_login_refused_outside_localhost(client):
    response = client.post('/api/login', headers={'Host': 'exemple.fr'})
    assert response.status_code == 403


def test_login_triggers_interactive_mode(client, monkeypatch, no_lockfile):
    calls = []

    def fake_detect(interactive=False):
        calls.append(interactive)
        return ('cle', 'a', 'e', '1111', 'eu', 'eu'), False

    monkeypatch.setattr(tool, 'detect_riot_credentials', fake_detect)
    response = client.post('/api/login', headers={'Host': 'localhost:8888'})
    assert response.status_code == 200
    assert calls == [True]
    assert tool._state['status'] == 'ready'


def test_logout_clears_the_session(client, monkeypatch):
    cleared = []
    monkeypatch.setattr(riot_auth, 'logout', lambda: cleared.append(True))
    response = client.post('/api/logout', headers={'Host': 'localhost:8888'})
    assert response.status_code == 200
    assert cleared == [True]
    assert tool._state['status'] == 'waiting'


def test_export_without_client_uses_interactive_mode(monkeypatch, tmp_path, no_lockfile):
    calls = []

    def fake_detect(interactive=False):
        calls.append(interactive)
        return ('cle', 'a', 'e', '1111', 'eu', 'eu'), False

    monkeypatch.setattr(tool, 'detect_riot_credentials', fake_detect)
    monkeypatch.setattr(tool, 'build_inventory', lambda refresh=False: {
        'skins': [], 'summary': {'skin_count': 0, 'total_vp': 0, 'total_eur': 0},
        'player': {'region': 'eu', 'shard': 'eu', 'puuid': '1111'}})
    monkeypatch.setattr(tool, 'EXPORT_DIR', tmp_path)
    data, json_path, csv_path, actif = tool.save_inventory()
    assert calls == [True]
    assert json_path.exists() and csv_path.exists()


def test_loop_reports_needs_login_without_lockfile(monkeypatch, no_lockfile):
    calls = []
    monkeypatch.setattr(riot_auth, 'authenticate', lambda interactive: calls.append(interactive))
    tool._monitor_tick()
    assert tool._state['status'] == 'needs_login'
    assert calls == [], 'la boucle ne doit jamais ouvrir de navigateur'


def test_loop_does_not_wipe_a_browser_session(monkeypatch, no_lockfile):
    with tool._state_lock:
        tool._credentials = ('cle-navigateur', 'a', 'e', '1111', 'eu', 'eu')
        tool._session_expiry = 10 ** 12
        tool._state.update({'status': 'ready', 'session': 'cle-navigateur'})
    tool._monitor_tick()
    assert tool._state['status'] == 'ready'
    assert tool._credentials[0] == 'cle-navigateur'


def test_loop_forgets_an_expired_browser_session(monkeypatch, no_lockfile):
    with tool._state_lock:
        tool._credentials = ('cle-navigateur', 'a', 'e', '1111', 'eu', 'eu')
        tool._session_expiry = 100.0
        tool._state.update({'status': 'ready', 'session': 'cle-navigateur'})
    tool._monitor_tick(now=10 ** 12)
    assert tool._state['status'] == 'needs_login'
    assert tool._credentials is None


def test_loop_prefers_the_lockfile(monkeypatch):
    monkeypatch.setattr(tool, 'get_lockfile', lambda: {'port': 1, 'password': 'x'})
    monkeypatch.setattr(tool, '_credentials_from_lockfile',
                        lambda lockfile: (('cle-lockfile', 'a', 'e', '1111', 'eu', 'eu'), True))
    tool._monitor_tick()
    assert tool._state['status'] == 'ready'
    assert tool._state['session'] == 'cle-lockfile'
