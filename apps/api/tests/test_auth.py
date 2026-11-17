"""외부 리뷰 #6: 로그인 없이 개인정보 조회·데이터 초기화가 되면 안 된다."""
from .conftest import resident_id


def test_staff_api_requires_login(make_client):
    c = make_client(ANSIMON_STAFF_PIN='4821')
    assert c.get('/api/staff/dashboard').status_code == 401
    assert c.post('/api/staff/demo/reset').status_code == 401
    assert c.get('/api/staff/alerts').status_code == 401
    assert c.get('/api/health').json()['auth'] == {'required': True}
    assert c.post('/api/staff/login', json={'pin': '0000'}).status_code == 401
    tok = c.post('/api/staff/login', json={'pin': '4821'}).json()['token']
    h = {'Authorization': f'Bearer {tok}'}
    assert c.get('/api/staff/dashboard', headers=h).status_code == 200
    assert c.get('/api/staff/dashboard', headers={'Authorization': 'Bearer wrong'}).status_code == 401


def test_login_attempts_are_limited(make_client):
    c = make_client(ANSIMON_STAFF_PIN='777777')
    codes = [c.post('/api/staff/login', json={'pin': f'{i:06d}'}).status_code for i in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    assert c.post('/api/staff/login', json={'pin': '777777'}).status_code == 429


def test_generated_pin_when_not_set(make_client, monkeypatch):
    monkeypatch.delenv('ANSIMON_STAFF_PIN', raising=False)
    c = make_client()
    pin = c.app.state.staff_pin
    assert pin and len(pin) == 6 and pin.isdigit()
    assert c.get('/api/staff/dashboard').status_code == 401


def test_demo_features_off_by_default(make_client, monkeypatch):
    monkeypatch.delenv('ANSIMON_DEMO', raising=False)
    c = make_client()
    assert c.post('/api/staff/demo/reset').status_code == 403
    assert c.get('/api/elder/residents').status_code == 403
    assert c.get('/api/elder/by-code/KY-01').status_code == 200


def test_elder_can_ring_self_without_staff_login(make_client):
    c = make_client(ANSIMON_STAFF_PIN='4821')
    rid = c.get('/api/elder/by-code/KY-01').json()['id']
    r = c.post(f'/api/elder/{rid}/ring')
    assert r.status_code == 201
    assert c.get(f'/api/elder/{rid}/incoming').json()['ringing']['call_id'] == r.json()['call_id']
    assert c.post(f'/api/elder/{rid}/ring').status_code == 409
