"""엔드포인트마다 (임시 DB, ANSIMON_LLM=off, 스케줄러 끔)."""
from datetime import datetime, timedelta

from app import calls, db
from app.domain import questions as Q

from .conftest import resident_id, say, start_call

KST_SUFFIX = '+09:00'


def test_health(client):
    h = client.get('/api/health').json()
    assert h == {'ok': True, 'db': True, 'llm': {'mode': 'rules', 'model': None, 'reachable': False}}


def test_full_call_flow_completes_with_assessment(client):
    rid = resident_id(client, '박정호')
    r = client.post(f'/api/staff/residents/{rid}/call')
    assert r.status_code == 201
    call = r.json()
    assert call['status'] == 'ringing' and call['status_label'] == '벨 울림' and call['created_at'].endswith(KST_SUFFIX)
    inc = client.get(f'/api/elder/{rid}/incoming').json()
    assert inc['ringing']['call_id'] == call['id'] and inc['ringing']['ring_expires_at'].endswith(KST_SUFFIX)
    assert inc['active'] is None
    start = client.post(f"/api/elder/calls/{call['id']}/answer").json()
    assert start['action'] == 'start' and start['ai_text'].startswith('박정호 어르신, 안녕하세요. 안심온이에요.')
    assert start['topic'] == 'body' and start['step'] == {'index': 1, 'total': 5} and len(start['options']) == 3
    assert client.get(f'/api/elder/{rid}/incoming').json()['active'] == {'call_id': call['id']}
    answers = ['괜찮아요', '아침은 걸렀어. 입맛이 없어서.', '잠은 좀 설쳤지', '약은 먹었어', '외로워']
    results = [say(client, call['id'], a) for a in answers]
    assert [x['action'] for x in results] == ['next', 'next', 'next', 'next', 'finish']
    assert [x['step']['index'] for x in results] == [2, 3, 4, 5, 5]
    last = results[-1]
    assert last['finished'] and last['question'] is None and last['topic'] is None and last['options'] == []
    assert last['ai_text'].endswith(Q.CLOSING) and '외로' in last['empathy']
    assert last['ai_text'].count('고마워요') == 1          # 공감 문장과 마무리 인사가 감사를 두 번 하지 않음
    d = client.get(f"/api/staff/calls/{call['id']}").json()
    assert d['status'] == 'completed' and d['step'] == {'index': 5, 'total': 5}
    a = d['assessment']
    assert {t: v['status'] for t, v in a['items'].items()} == {
        'body': 'good', 'meal': 'caution', 'sleep': 'caution', 'med': 'good', 'mood': 'caution'}
    assert a['score'] == 15 and a['grade'] == 'watch' and a['grade_label'] == '추가 확인' and a['rule_version'] == 'r2.1'
    assert [n['type'] for n in a['needs']] == ['loneliness']
    assert d['summary'] and d['ended_at'].endswith(KST_SUFFIX)
    assert len(d['turns']) == 11 and d['turns'][0]['role'] == 'ai'
    assert all('judged' in t and 'source' in t for t in d['turns'] if t['role'] == 'elder')
    assert {x['step'] for x in d['ai_runs']} == {'extract', 'empathy', 'summary'}
    assert all(x['outcome'] == 'fallback' and x['model'] is None for x in d['ai_runs'])
    assert d['staff_check'] is None
    e = client.get(f"/api/elder/calls/{call['id']}").json()
    assert e['status'] == 'completed' and e['question'] is None and len(e['turns']) == 11


def test_decline(client):
    rid = resident_id(client, '박정호')
    cid = client.post(f'/api/staff/residents/{rid}/call').json()['id']
    assert client.post(f'/api/elder/calls/{cid}/decline').json() == {'status': 'declined'}
    d = client.get(f'/api/staff/calls/{cid}').json()
    assert d['status'] == 'declined' and d['status_label'] == '수신 거절'
    assert any(r['chip'] == '수신 거절' for r in d['assessment']['reasons'])
    assert client.post(f'/api/elder/calls/{cid}/answer').status_code == 409


def test_hangup_before_last_question_is_interrupted(client):
    rid = resident_id(client, '박정호')
    cid = start_call(client, rid)
    say(client, cid, '괜찮아')
    say(client, cid, '못 먹었어')
    assert client.post(f'/api/elder/calls/{cid}/hangup').json() == {'status': 'interrupted'}
    d = client.get(f'/api/staff/calls/{cid}').json()
    a = d['assessment']
    assert d['status'] == 'interrupted' and a['items']['meal']['status'] == 'caution'
    assert a['needs_check'] == ['sleep', 'med', 'mood'] and a['grade'] == 'watch'
    assert any(r['chip'] == '통화 중단' and r['points'] == 5 for r in a['reasons'])
    assert d['summary'].startswith('통화가 중간에 끊김')
    assert client.post(f'/api/elder/calls/{cid}/turn',
                       json={'text': '네', 'source': 'text', 'client_turn_id': 'late'}).status_code == 409


def test_ringing_becomes_missed_after_30s(client, clock):
    rid = resident_id(client, '최복순')
    cid = client.post(f'/api/staff/residents/{rid}/call').json()['id']
    clock.advance(seconds=31)
    d = client.get(f'/api/staff/calls/{cid}').json()
    assert d['status'] == 'missed'
    # 최복순은 이틀 연속 미응답 → 오늘까지 3회 연속
    assert any(r['chip'] == '연속 미응답 3회' and r['points'] == 20 for r in d['assessment']['reasons'])
    dash = client.get('/api/staff/dashboard').json()
    assert dash['counts']['missed'] == 1


def test_idempotent_client_turn_id(client):
    cid = start_call(client, resident_id(client, '박정호'))
    r1 = say(client, cid, '괜찮아요', ctid='same-1')
    r2 = say(client, cid, '괜찮아요', ctid='same-1')
    assert r1 == r2
    r3 = say(client, cid, '전혀 다른 말', ctid='same-1')
    assert r3 == r1
    elder = [t for t in client.get(f'/api/staff/calls/{cid}').json()['turns'] if t['role'] == 'elder']
    assert len(elder) == 1
    assert client.post(f'/api/elder/calls/{cid}/answer').status_code == 409   # 이미 답이 시작된 통화


def test_answer_twice_before_first_turn_returns_same_start(client):
    rid = resident_id(client, '박정호')
    cid = client.post(f'/api/staff/residents/{rid}/call').json()['id']
    a1 = client.post(f'/api/elder/calls/{cid}/answer').json()
    a2 = client.post(f'/api/elder/calls/{cid}/answer').json()
    assert a1 == a2


def test_409_when_resident_already_ringing_or_in_progress(client):
    rid = resident_id(client, '박정호')
    cid = client.post(f'/api/staff/residents/{rid}/call').json()['id']
    r = client.post(f'/api/staff/residents/{rid}/call')
    assert r.status_code == 409 and '통화 중' in r.json()['detail']
    client.post(f'/api/elder/calls/{cid}/answer')
    assert client.post(f'/api/staff/residents/{rid}/call').status_code == 409
    assert client.post('/api/staff/residents/9999/call').status_code == 404


def test_dashboard_ordering_and_counts(client):
    d = client.get('/api/staff/dashboard').json()
    assert d['date'] == db.kst_today().isoformat()
    order = {'urgent': 0, 'today': 1, 'watch': 2, 'ok': 3}
    keys = [(order[r['assessment']['grade']] if r['assessment'] else 4, -(r['assessment'] or {'score': 0})['score'])
            for r in d['residents']]
    assert keys == sorted(keys)
    assert [r['name'] for r in d['residents']][:4] == ['김영자', '한덕수', '이순희', '정말순']
    c = d['counts']
    assert c['total'] == 7 and c['not_called'] == 3 and c['today'] == 2 and c['watch'] == 1 and c['ok'] == 1
    first = d['residents'][0]
    assert first['today']['status'] == 'completed' and first['today']['status_label'] == '통화 완료'
    assert first['is_virtual'] is True and first['code'] == 'KY-01'
    assert {x['kind'] for x in first['assessment']['reasons']} == {'item', 'trend', 'contact'}


def test_urgent_goes_to_top(client):
    cid = start_call(client, resident_id(client, '박정호'))
    for text in ['넘어져서 못 일어나겠어', '먹었어', '잘 잤어', '먹었어', '좋아']:
        say(client, cid, text)
    d = client.get('/api/staff/dashboard').json()
    assert d['residents'][0]['name'] == '박정호' and d['residents'][0]['assessment']['grade'] == 'urgent'
    assert d['counts']['urgent'] == 1


def test_resident_week_has_7_days_oldest_first(client):
    rid = resident_id(client, '김영자')
    d = client.get(f'/api/staff/residents/{rid}').json()
    week = d['week']
    today = db.kst_today()
    assert [w['date'] for w in week] == [(today - timedelta(days=k)).isoformat() for k in range(6, -1, -1)]
    assert week[-2]['call_status'] == 'missed' and week[-2]['items'] is None
    assert week[-1]['items']['meal'] == 'risk' and week[-1]['grade'] == 'today' and week[-1]['score'] == 40
    assert d['resident']['name'] == '김영자' and d['calls'][0]['created_at'] > d['calls'][-1]['created_at']
    assert client.get('/api/staff/residents/9999').status_code == 404


def test_create_and_patch_resident(client):
    r = client.post('/api/staff/residents', json={'name': '홍길동', 'age': 79, 'neighborhood': '서구 탄방동',
                                                 'call_time': '09:15'})
    assert r.status_code == 201
    res = r.json()
    assert res['code'] == 'KY-08' and res['is_virtual'] is False and res['memo'] is None
    assert res['region'] == '대전광역시 서구'                  # 지역을 안 보내면 동네 이름으로 채움
    p = client.patch(f"/api/staff/residents/{res['id']}", json={'call_time': '10:45', 'memo': '새 메모'})
    assert p.json()['call_time'] == '10:45' and p.json()['memo'] == '새 메모' and p.json()['name'] == '홍길동'
    bad = client.post('/api/staff/residents', json={'name': '', 'age': 79, 'neighborhood': 'x', 'call_time': '25:00'})
    assert bad.status_code == 422 and isinstance(bad.json()['detail'], str) and '전화 시각' in bad.json()['detail']
    assert client.patch(f"/api/staff/residents/{res['id']}", json={'name': None}).status_code == 422
    assert client.patch('/api/staff/residents/9999', json={'memo': 'x'}).status_code == 404


def test_list_calls_filters(client):
    rid = resident_id(client, '김영자')
    all_calls = client.get('/api/staff/calls').json()
    assert 30 <= len(all_calls) <= 50 and all_calls[0]['created_at'] >= all_calls[-1]['created_at']
    assert len(client.get('/api/staff/calls?limit=5').json()) == 5
    today = db.kst_today().isoformat()
    t = client.get(f'/api/staff/calls?date={today}').json()
    assert len(t) == 4 and all(c['created_at'].startswith(today) for c in t)
    mine = client.get(f'/api/staff/calls?resident_id={rid}&limit=3').json()
    assert len(mine) == 3 and all(c['resident_name'] == '김영자' for c in mine)
    assert client.get('/api/staff/calls?date=2026-1-1').status_code == 422


def test_call_detail_shape_and_seeded_ai_runs(client):
    rid = resident_id(client, '김영자')
    cid = client.get(f'/api/staff/calls?resident_id={rid}&limit=1').json()[0]['id']
    d = client.get(f'/api/staff/calls/{cid}').json()
    assert set(d) >= {'id', 'resident_id', 'resident_name', 'status', 'status_label', 'created_at', 'started_at',
                      'ended_at', 'summary', 'assessment', 'turns', 'ai_runs', 'staff_check', 'step'}
    assert d['ai_runs'] and all(x['model'] == 'ax4-light:q4_K_M' and x['note'] == '시드 데이터' for x in d['ai_runs'])
    elder = [t for t in d['turns'] if t['role'] == 'elder']
    assert all(t['judged'] for t in elder)
    assert client.get('/api/staff/calls/99999').status_code == 404


def test_live(client):
    assert client.get('/api/staff/live').json() == {'calls': []}
    rid = resident_id(client, '박정호')
    cid = client.post(f'/api/staff/residents/{rid}/call').json()['id']
    live = client.get('/api/staff/live').json()['calls']
    assert live[0]['id'] == cid and live[0]['step'] == {'index': 0, 'total': 5}
    client.post(f'/api/elder/calls/{cid}/answer')
    say(client, cid, '괜찮아')
    assert client.get('/api/staff/live').json()['calls'][0]['step'] == {'index': 2, 'total': 5}


def test_staff_check(client):
    rid = resident_id(client, '김영자')
    cid = client.get('/api/staff/dashboard').json()['residents'][0]['today']['call_id']
    r = client.post(f'/api/staff/calls/{cid}/check', json={'note': '오후에 방문함'}).json()
    assert r['checked'] is True and r['note'] == '오후에 방문함' and r['at'].endswith(KST_SUFFIX)
    assert client.get(f'/api/staff/calls/{cid}').json()['staff_check']['note'] == '오후에 방문함'
    row = next(x for x in client.get('/api/staff/dashboard').json()['residents'] if x['id'] == rid)
    assert row['staff_check']['checked'] is True
    assert client.post(f'/api/staff/calls/{cid}/check', json={'note': 'x' * 301}).status_code == 422


def test_demo_reset(client):
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아')
    client.post('/api/staff/residents', json={'name': '홍길동', 'age': 79, 'neighborhood': '서구', 'call_time': '09:15'})
    assert client.post('/api/staff/demo/reset').json() == {'ok': True}
    d = client.get('/api/staff/dashboard').json()
    assert d['counts']['total'] == 7 and d['counts']['not_called'] == 3
    assert client.get('/api/staff/live').json() == {'calls': []}


def test_demo_reset_disabled(make_client):
    client = make_client(ANSIMON_DEMO='0')
    r = client.post('/api/staff/demo/reset')
    assert r.status_code == 403 and 'ANSIMON_DEMO' in r.json()['detail']


def test_elder_residents_and_by_code(client):
    rs = client.get('/api/elder/residents').json()
    assert [r['code'] for r in rs] == [f'KY-0{i}' for i in range(1, 8)] and set(rs[0]) == {'id', 'code', 'name'}
    assert client.get('/api/elder/by-code/KY-03').json()['name'] == '박정호'
    assert client.get('/api/elder/by-code/ky-03').json()['name'] == '박정호'
    r = client.get('/api/elder/by-code/KY-99')
    assert r.status_code == 404 and r.json()['detail']


def test_elder_home(client):
    h = client.get(f"/api/elder/{resident_id(client, '김영자')}/home").json()
    assert h['name'] == '김영자' and h['call_time'] == '08:30'
    assert h['today'] == {'status': 'completed', 'status_label': '오늘 통화했어요'}
    assert h['yesterday_label'] == '어제는 전화를 못 받으셨어요' and h['week_count'] == 6
    h2 = client.get(f"/api/elder/{resident_id(client, '박정호')}/home").json()
    assert h2['today']['status'] == 'not_called'
    assert client.get('/api/elder/9999/home').status_code == 404


def test_elder_records_14_days(client):
    recs = client.get(f"/api/elder/{resident_id(client, '김영자')}/records").json()
    assert len(recs) == 14 and recs[0]['date'] == db.kst_today().isoformat()
    assert recs[0]['time'] and recs[0]['minutes'] >= 1
    assert {'label': '식사를 잘 못 하셨어요', 'tone': 'watch'} in recs[0]['chips']
    assert recs[1]['status_label'] == '전화를 못 받으셨어요' and recs[1]['chips'] == []
    assert recs[13]['time'] is None and recs[13]['chips'] == []
    safety_day = client.get(f"/api/elder/{resident_id(client, '박정호')}/records").json()[2]
    assert {'label': '생활지원사님께 알렸어요', 'tone': 'watch'} in safety_day['chips']


def test_elder_call_state_for_resume(client):
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아')
    s = client.get(f'/api/elder/calls/{cid}').json()
    assert s['status'] == 'in_progress' and s['step'] == {'index': 2, 'total': 5}
    assert s['question'] == Q.QUESTIONS['meal'] and s['topic'] == 'meal' and len(s['turns']) == 3


def test_silence_reasks_twice_then_unknown(client):
    cid = start_call(client, resident_id(client, '박정호'))
    r1 = say(client, cid, '', source='silence')
    assert r1['action'] == 'reask' and r1['ai_text'].startswith(Q.SILENCE_PREFIX) and r1['topic'] == 'body'
    r2 = say(client, cid, '음...', source='stt')
    assert r2['action'] == 'reask' and Q.OPTIONS['body'][0] in r2['ai_text']
    r3 = say(client, cid, '', source='silence')
    assert r3['action'] == 'next' and r3['topic'] == 'meal' and r3['empathy'] == Q.SKIP_LINE
    elder = [t for t in client.get(f'/api/staff/calls/{cid}').json()['turns'] if t['role'] == 'elder']
    assert elder[-1]['judged'] == [{'topic': 'body', 'status': 'unknown', 'origin': 'rule'}]


def test_option_source_uses_rules_without_llm_extract(client):
    cid = start_call(client, resident_id(client, '박정호'))
    for topic in Q.TOPICS:
        r = say(client, cid, Q.OPTIONS[topic][0], source='option')
    assert r['finished']
    d = client.get(f'/api/staff/calls/{cid}').json()
    assert d['assessment']['grade'] == 'ok' and not [x for x in d['ai_runs'] if x['step'] == 'extract']
    for topic in Q.TOPICS:   # 모든 버튼 문구가 의도한 상태로 판정되는지
        from app.domain.keywords import extract
        got = [next(i['status'] for i in extract(topic, o).items if i['topic'] == topic) for o in Q.OPTIONS[topic]]
        assert got[0] == 'good', (topic, got)
    assert any(o == '먹는 약 없어요' for o in Q.OPTIONS['med'])


def test_turn_validation(client):
    cid = start_call(client, resident_id(client, '박정호'))
    r = client.post(f'/api/elder/calls/{cid}/turn', json={'text': 'x' * 501, 'source': 'text', 'client_turn_id': 'a'})
    assert r.status_code == 422 and isinstance(r.json()['detail'], str)
    r = client.post(f'/api/elder/calls/{cid}/turn', json={'text': 'x', 'source': 'voice', 'client_turn_id': 'a'})
    assert r.status_code == 422


# ---- 스케줄러 ----
def _conn(client):
    return db.connect(client.app.state.settings.db_path)


def test_scheduler_rings_at_call_time_and_retries_once(client, clock):
    rid = resident_id(client, '박정호')        # 09:30, 오늘 통화 없음
    today = db.kst_today()
    clock.set(datetime(today.year, today.month, today.day, 9, 29, tzinfo=db.KST))
    conn = _conn(client)

    def mine(created):
        return [c for c in created if conn.execute('SELECT resident_id FROM calls WHERE id = ?', (c,)).fetchone()[0] == rid]

    assert mine(calls.scheduler_tick(conn)) == []          # 아직 시간 전
    clock.advance(minutes=1)
    assert len(mine(calls.scheduler_tick(conn))) == 1      # 09:30 → 벨
    assert mine(calls.scheduler_tick(conn)) == []          # 울리는 중엔 또 만들지 않음
    clock.advance(seconds=31)
    calls.scheduler_tick(conn)                             # 30초 → 미응답
    assert not _ringing(conn, rid)
    clock.advance(minutes=5)
    assert mine(calls.scheduler_tick(conn)) == []          # 10분 전엔 다시 걸지 않음
    clock.advance(minutes=6)
    assert len(mine(calls.scheduler_tick(conn))) == 1      # 10분 지나서 한 번 더
    clock.advance(seconds=31)
    calls.scheduler_tick(conn)
    clock.advance(minutes=15)
    assert mine(calls.scheduler_tick(conn)) == []          # 하루 2번까지
    n = conn.execute('SELECT COUNT(*) FROM calls WHERE resident_id = ? AND kst_date = ?',
                     (rid, today.isoformat())).fetchone()[0]
    assert n == 2
    conn.close()


def _ringing(conn, rid):
    return conn.execute("SELECT 1 FROM calls WHERE resident_id = ? AND status = 'ringing'", (rid,)).fetchone() is not None


def test_scheduler_outside_window_does_nothing(client, clock):
    rid = resident_id(client, '박정호')
    today = db.kst_today()
    clock.set(datetime(today.year, today.month, today.day, 11, 31, tzinfo=db.KST))   # 09:30 + 2시간 지남
    conn = _conn(client)
    created = calls.scheduler_tick(conn)
    assert rid not in [conn.execute('SELECT resident_id FROM calls WHERE id = ?', (c,)).fetchone()[0] for c in created]
    conn.close()
