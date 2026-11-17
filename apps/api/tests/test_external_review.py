"""외부 리뷰(2026-11-16)에서 확인된 문제 — 다시 생기지 않는지. 번호는 리뷰 번호."""
from app.domain import dialogue, keywords, safety
from app.domain import questions as Q

from .conftest import say, start_call


def _new_resident(client, name='테스트'):
    r = client.post('/api/staff/residents', json={'name': name, 'age': 80, 'neighborhood': '중구 은행동', 'call_time': '23:59'})
    assert r.status_code == 201, r.text
    return r.json()['id']


def _row(client, rid):
    return next(x for x in client.get('/api/staff/dashboard').json()['residents'] if x['id'] == rid)


# 1. 위급한 표현인데도 안전 신호를 놓침
def test_1_breathing_and_chest_pain_variants_are_safety_signals():
    for text in ['숨이 안 쉬어져요', '숨을 쉴 수가 없어요', '가슴에 통증이 있어요']:
        assert safety.detect(text), text
        body = [i for i in keywords.extract('body', text).items if i['topic'] == 'body']
        assert body and body[0]['status'] == 'risk', text


# 2. 통화 중 안전 신호가 대시보드에 바로 보여야 한다 (통화가 끝나기 전에)
def test_2_safety_during_call_shows_on_dashboard_and_alerts_immediately(client):
    rid = _new_resident(client)
    cid = start_call(client, rid)
    r = say(client, cid, '숨이 차요')
    assert r['safety'] and not r['finished']
    row = _row(client, rid)
    assert row['today']['status'] == 'in_progress'
    assert row['assessment']['grade'] == 'urgent' and row['assessment']['provisional'] is True
    assert row['assessment_call_id'] == cid
    assert client.get('/api/staff/dashboard').json()['residents'][0]['id'] == rid   # 맨 위
    alerts = client.get('/api/staff/alerts').json()['alerts']
    assert [(a['call_id'], a['category'], a['live']) for a in alerts] == [(cid, '호흡·가슴', True)]
    assert client.get(f'/api/staff/calls/{cid}').json()['assessment']['grade'] == 'urgent'
    # 통화가 끝나면 최종 판정으로 바뀐다
    for text in ['먹었어', '잘 잤어', '먹었어']:
        say(client, cid, text)
    r = say(client, cid, '괜찮아')
    assert r['finished']
    a = _row(client, rid)['assessment']
    assert a['grade'] == 'urgent' and a['provisional'] is False
    # 확인하면 알림이 사라진다
    client.post(f'/api/staff/calls/{cid}/check', json={'note': '전화함'})
    assert client.get('/api/staff/alerts').json()['alerts'] == []


# 3. 같은 날 다시 건 전화를 거절해도 앞선 '즉시 확인'이 내려가지 않는다
def test_3_later_declined_call_does_not_hide_earlier_urgent(client):
    rid = _new_resident(client)
    cid = start_call(client, rid)
    say(client, cid, '넘어져서 못 일어나')
    client.post(f'/api/elder/calls/{cid}/hangup')
    assert _row(client, rid)['assessment']['grade'] == 'urgent'
    c2 = client.post(f'/api/staff/residents/{rid}/call').json()['id']
    client.post(f'/api/elder/calls/{c2}/decline')
    row = _row(client, rid)
    assert row['today']['status'] == 'declined' and row['today']['call_id'] == c2
    assert row['assessment']['grade'] == 'urgent' and row['assessment']['safety']
    assert row['assessment_call_id'] == cid
    week = client.get(f'/api/staff/residents/{rid}').json()['week']
    assert week[-1]['grade'] == 'urgent'


# 4. 이전 통화의 확인 기록이 새 판정에 붙지 않는다
def test_4_staff_check_belongs_to_the_assessed_call_only(client):
    rid = _new_resident(client)
    c1 = start_call(client, rid)
    say(client, c1, '조금 피곤해')
    client.post(f'/api/elder/calls/{c1}/hangup')
    client.post(f'/api/staff/calls/{c1}/check', json={'note': '확인'})
    assert _row(client, rid)['staff_check']['checked']
    c2 = start_call(client, rid)
    say(client, c2, '넘어져서 못 일어나')                      # 새 위험
    client.post(f'/api/elder/calls/{c2}/hangup')
    row = _row(client, rid)
    assert row['assessment_call_id'] == c2 and row['assessment']['grade'] == 'urgent'
    assert row['staff_check'] is None


def test_4_same_grade_unchecked_call_wins_over_checked_one(client):
    rid = _new_resident(client)
    c1 = start_call(client, rid)
    say(client, c1, '넘어져서 못 일어나')
    client.post(f'/api/elder/calls/{c1}/hangup')
    client.post(f'/api/staff/calls/{c1}/check', json={'note': '방문함'})
    c2 = start_call(client, rid)
    say(client, c2, '숨이 차')
    client.post(f'/api/elder/calls/{c2}/hangup')
    row = _row(client, rid)
    assert row['assessment_call_id'] == c2 and row['staff_check'] is None


# 5. '위험'으로 판정한 답이 '특이 표현 없음'이 되지 않는다
def test_5_body_risk_is_not_ok(client):
    rid = _new_resident(client)
    cid = start_call(client, rid)
    for text in ['많이 아파요', '먹었어', '잘 잤어', '먹었어', '좋아']:
        r = say(client, cid, text, source='option' if text == '많이 아파요' else 'text')
    assert r['finished']
    a = _row(client, rid)['assessment']
    assert a['items']['body']['status'] == 'risk' and a['score'] == 10
    assert a['grade'] == 'today' and a['grade_label'] == '우선 확인' and a['grade_basis'] == '위험 항목 (몸 상태)'


# 9. 통화 중 새로고침해도 식사 재질문과 선택 버튼이 그대로
def test_9_resume_keeps_followup_question_and_options(client):
    rid = _new_resident(client)
    cid = start_call(client, rid)
    say(client, cid, '괜찮아요')
    r = say(client, cid, '못 먹었어요')
    assert r['question'] == dialogue.FOLLOWUP_QUESTION
    s = client.get(f'/api/elder/calls/{cid}').json()
    assert s['question'] == dialogue.FOLLOWUP_QUESTION and s['options'] == dialogue.FOLLOWUP_OPTIONS
    assert s['topic'] == 'meal' and s['last_ai_text'] == r['ai_text']
    # 재질문에 답하고 나면 다음 기본 질문
    say(client, cid, '아직 식사 전이에요', source='option')
    s = client.get(f'/api/elder/calls/{cid}').json()
    assert s['question'] == Q.QUESTIONS['sleep'] and s['options'] == Q.OPTIONS['sleep']


# ---- 독립 QA(2026-11-16)에서 추가로 찾은 것 ----
import pytest  # noqa: E402


def _st(topic, text):
    return next((i['status'] for i in keywords.extract(topic, text).items if i['topic'] == topic), None)


@pytest.mark.parametrize('topic,text,expected', [
    ('body', '괜찮지 않아요', 'caution'), ('body', '건강하지 않아', 'caution'), ('sleep', '잘 자지 못했어', 'caution'),
    ('sleep', '푹 자지 못했어', 'caution'), ('mood', '행복하지 않아', 'caution'), ('mood', '편안하지 않아', 'caution'),
    ('meal', '먹고 싶지 않아', 'caution'), ('meal', '식사 못 했어요', 'caution'), ('meal', '밥 먹지 못했어', 'caution'),
    ('med', '약 먹지 않았어', 'caution'), ('sleep', '잠을 자지 못했어', 'caution'), ('med', '복용 안 했어', 'caution'),
    ('body', '안 어지러워요', 'good'), ('body', '어지럽진 않아요', 'good'), ('body', '아프진 않아요', 'good'),
    ('body', '별로 안 아파', 'good'), ('med', '까먹지 않고 챙겼어', 'good'), ('meal', '못 먹은 건 아니고 먹었어', 'good'),
    ('mood', '혼자라서 외로워', 'risk'),
])
def test_qa_negation_forms(topic, text, expected):
    assert _st(topic, text) == expected


def test_qa_fall_mentioned_on_other_question_is_kept(client):
    rid = _new_resident(client)
    cid = start_call(client, rid)
    say(client, cid, '괜찮아요')
    r = say(client, cid, '어제 화장실에서 미끄러져서 넘어졌어')
    assert r['action'] == 'reask' and r['topic'] == 'meal'          # 식사 답은 아니니 다시 묻되, 넘어진 일은 남긴다
    elder = [t for t in client.get(f'/api/staff/calls/{cid}').json()['turns'] if t['role'] == 'elder']
    assert {'topic': 'body', 'status': 'risk', 'origin': 'rule'} in elder[-1]['judged']


def test_qa_all_silence_call_is_not_completed(client):
    rid = _new_resident(client)
    cid = start_call(client, rid)
    r = None
    for _ in range(15):
        r = say(client, cid, '', source='silence')
        if r['finished']:
            break
    assert r['finished'] and r['ai_text'] == Q.SILENT_CLOSING
    d = client.get(f'/api/staff/calls/{cid}').json()
    assert d['status'] == 'interrupted'
    assert any(x['chip'] == '받았지만 대답 없음' and x['points'] == 10 for x in d['assessment']['reasons'])
    assert d['assessment']['grade'] == 'watch'


def test_qa_answer_for_old_question_is_rejected_not_saved_to_next(client):
    rid = _new_resident(client)
    cid = start_call(client, rid)
    say(client, cid, '괜찮아요')                                     # 서버는 식사로 넘어감 (앱은 응답을 못 받았다고 가정)
    r = client.post(f'/api/elder/calls/{cid}/turn', json={'text': '많이 아파요', 'source': 'option',
                                                          'client_turn_id': 'late-1', 'topic': 'body'})
    assert r.status_code == 412
    s = client.get(f'/api/elder/calls/{cid}').json()
    assert s['topic'] == 'meal'
    assert all(t['text'] != '많이 아파요' for t in s['turns'])


def test_qa_blank_resident_name_is_rejected(client):
    r = client.post('/api/staff/residents', json={'name': '   ', 'age': 80, 'neighborhood': '중구', 'call_time': '09:00'})
    assert r.status_code == 422
    rid = _new_resident(client)
    assert client.patch(f'/api/staff/residents/{rid}', json={'name': '  '}).status_code == 422
    assert client.patch(f'/api/staff/residents/{rid}', json={'name': '  김순자 '}).json()['name'] == '김순자'


@pytest.mark.parametrize('text', ['그냥 확 죽어버릴까', '살 이유가 없어', '먼저 간 영감 따라가고 싶어', '가슴이 꽉 막힌 것 같아',
                                  '누가 나 좀 살려', '도와주라'])
def test_qa_more_safety_expressions(text):
    assert safety.detect(text)


def test_qa_mind_signal_adds_109_line(client):
    rid = _new_resident(client)
    cid = start_call(client, rid)
    r = say(client, cid, '살기 싫어')
    assert r['safety'] and Q.SAFETY_NOTICE in r['ai_text'] and '109' in r['ai_text']
