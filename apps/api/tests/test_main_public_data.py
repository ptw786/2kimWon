"""최신 main(PIN·r3)와 제공 공공데이터를 결합할 때의 회귀 검증."""
from app.services import welfare


def _services(need, region, age):
    return welfare.matches([{'type': need}], region, age=age)[0]['services']


def test_county_program_does_not_expand_to_whole_province():
    sid = 'WLF00006261'
    assert sid not in {s['id'] for s in _services('help_request', '경상남도 거창군', 78)}
    assert sid in {s['id'] for s in _services('help_request', '경상남도 함양군', 78)}


def test_explicit_minimum_age_is_not_lost_for_food_program():
    sid = 'WLF00000806'
    assert sid not in {s['id'] for s in _services('meal_difficulty', '경기도 시흥시', 55)}
    assert sid in {s['id'] for s in _services('meal_difficulty', '경기도 시흥시', 60)}


def test_public_data_endpoint_keeps_main_staff_authentication(make_client, monkeypatch):
    from app import auth
    monkeypatch.setattr(auth, '_fails', {})
    with make_client(ANSIMON_STAFF_PIN='987654') as client:
        assert client.get('/api/staff/public-data').status_code == 401
        response = client.post('/api/staff/login', json={'pin': '987654'})
        assert response.status_code == 200
        data = client.get('/api/staff/public-data', headers={'Authorization': 'Bearer '+response.json()['token']})
        assert data.status_code == 200 and data.json()['catalog']['total'] == 134


def test_missing_ollama_model_is_not_reported_as_ready(monkeypatch):
    import httpx
    from app.services import llm
    monkeypatch.setattr(llm.httpx, 'get', lambda *args, **kwargs: httpx.Response(200, json={'models': []}))
    assert llm.OllamaClient('http://127.0.0.1:11434', 'not-installed:latest').reachable() is False


def test_ai_summary_cannot_erase_confirmed_safety_signal(make_client):
    from app.services.llm import FakeLLM
    from .conftest import start_call, say
    client = make_client(llm=FakeLLM(summary='안전 신호나 특이사항이 없고 건강하게 지내고 계십니다.'))
    rid = client.post('/api/staff/residents', json={'name': '요약검증', 'age': 78, 'neighborhood': '보람동', 'call_time': '09:00'}).json()['id']
    cid = start_call(client, rid)
    say(client, cid, '숨이 차요')
    client.post(f'/api/elder/calls/{cid}/hangup')
    detail = client.get(f'/api/staff/calls/{cid}').json()
    assert detail['assessment']['safety'] and '안전 신호나 특이사항이 없고' not in detail['summary']
    assert any(run['step']=='summary' and run['outcome']=='fallback' for run in detail['ai_runs'])


def test_call_history_can_page_and_filter_before_limiting(client):
    from .conftest import start_call, say
    rid = client.post('/api/staff/residents', json={'name':'기록검증','age':78,'neighborhood':'보람동','call_time':'09:00'}).json()['id']
    urgent = start_call(client, rid)
    say(client, urgent, '숨이 차요')
    client.post(f'/api/elder/calls/{urgent}/hangup')
    for _ in range(52):
        cid=client.post(f'/api/staff/residents/{rid}/call').json()['id']
        client.post(f'/api/elder/calls/{cid}/decline')
    first=client.get(f'/api/staff/calls?resident_id={rid}&limit=50&offset=0').json()
    second=client.get(f'/api/staff/calls?resident_id={rid}&limit=50&offset=50').json()
    filtered=client.get(f'/api/staff/calls?resident_id={rid}&grade=urgent&limit=50').json()
    assert len(first)==50 and len(second)==3
    assert not ({r['id'] for r in first} & {r['id'] for r in second})
    assert [r['id'] for r in filtered]==[urgent]


def test_re_review_keeps_explicit_region_and_age_constraints(tmp_path, monkeypatch):
    import json, sys
    from scripts import review_welfare
    services, _ = welfare.catalog()
    review_path = tmp_path / 'reviews.json'
    reviews = {s['id']: s['_review'] for s in services}
    review_path.write_text(json.dumps({'services': reviews}))
    monkeypatch.setattr(welfare, 'REVIEW_PATH', review_path)
    for sid in ['WLF00006261', 'WLF00000806']:
        raw = next(s for s in services if s['id'] == sid)
        before = reviews[sid]
        monkeypatch.setattr(sys, 'argv', ['review_welfare.py', sid, '--decision', 'include', '--needs', before['needs'][0],
                            '--reason', '조건 원문 재확인', '--evidence', raw['target'][:20], '--check', '기관에 신청 조건 확인'])
        review_welfare.main()
        after = json.loads(review_path.read_text())['services'][sid]
        assert after['match_region'] == before['match_region']
        assert after['min_age'] == before['min_age'] and after['max_age'] == before['max_age']


def test_missing_live_cache_does_not_revive_old_local_programs(tmp_path, monkeypatch):
    monkeypatch.setattr(welfare, 'LIVE_PATH', tmp_path / 'missing-cache.json')
    match = welfare.matches([{'type':'meal_difficulty'}], '서울특별시 서대문구', age=78)[0]
    assert all(s['source'] == '중앙부처복지서비스' for s in match['services'])
    assert 'warning' in welfare.public_data_overview()['catalog']


def test_real_daily_checkin_delivery_is_not_excluded_with_irrelevant_programs():
    sid='WLF00002181'
    assert sid in {s['id'] for s in _services('loneliness', '서울특별시 도봉구', 65)}
    assert sid not in {s['id'] for s in _services('loneliness', '서울특별시 도봉구', 64)}
    assert sid not in {s['id'] for s in _services('meal_difficulty', '서울특별시 도봉구', 78)}
