"""이전 버전(ansimon-fullstack/backend)에서 확인된 버그 5개 — 다시 생기지 않는지."""
from app.domain import questions as Q
from app.services.llm import ExtractResult, FakeLLM

from .conftest import resident_id, say, start_call


def _detail(client, cid):
    return client.get(f'/api/staff/calls/{cid}').json()


# 1. '다시 말해 달라'가 답과 섞이면 index 는 넘어가고 질문은 이전 주제를 다시 물어서, 다음 "네"가 엉뚱한 주제에 저장됨
def test_bug1_repeat_request_does_not_advance_and_answer_goes_to_asked_topic(client):
    cid = start_call(client, resident_id(client, '박정호'))
    assert say(client, cid, '괜찮아요')['topic'] == 'meal'
    r = say(client, cid, '뭐라고? 밥은 먹었어')            # 다시 말해 달라 + 답이 섞임
    assert r['action'] == 'repeat' and r['topic'] == 'meal' and r['step']['index'] == 2
    assert r['question'] == Q.QUESTIONS['meal'] and Q.QUESTIONS['meal'] in r['ai_text']
    r = say(client, cid, '네')
    assert r['action'] == 'next' and r['topic'] == 'sleep'
    turns = [t for t in _detail(client, cid)['turns'] if t['role'] == 'elder']
    assert turns[-1]['topic'] == 'meal'
    assert turns[-1]['judged'] == [{'topic': 'meal', 'status': 'good', 'origin': 'rule'}]
    # 질문(ai 턴)의 topic 과 그 다음 답(elder 턴)의 topic 이 언제나 같다
    all_turns = _detail(client, cid)['turns']
    for prev, nxt in zip(all_turns, all_turns[1:]):
        if prev['role'] == 'ai' and nxt['role'] == 'elder':
            assert prev['topic'] == nxt['topic']


def test_bug1_with_llm_repeat_intent(make_client):
    llm = FakeLLM(extract=lambda topic, q, a: ExtractResult(intent='repeat_request', items=[])
                  if '뭐' in a else ExtractResult(intent='answer', items=[{'topic': topic, 'quote': a, 'status': 'good'}]))
    client = make_client(llm=llm)
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아')
    r = say(client, cid, '뭐라고요?')
    assert r['action'] == 'repeat' and r['topic'] == 'meal'
    r = say(client, cid, '네')
    assert r['topic'] == 'sleep'
    elder = [t for t in _detail(client, cid)['turns'] if t['role'] == 'elder']
    assert elder[-1]['topic'] == 'meal' and elder[-1]['judged'][0]['topic'] == 'meal'


# 2. 위험 확인 상태에서 정확히 "아니요"가 아니면 빠져나올 수 없었음
def test_bug2_safety_signal_never_traps_the_call(client):
    cid = start_call(client, resident_id(client, '박정호'))
    r = say(client, cid, '어제 넘어졌어')
    assert r['action'] == 'safety' and r['safety'] is True
    assert r['ai_text'].startswith(Q.SAFETY_NOTICE) and r['topic'] == 'meal'
    r = say(client, cid, '응')                       # 아무 답이나 → 그대로 다음
    assert r['action'] == 'next' and r['topic'] == 'sleep'
    for text in ['잘 잤어', '약 먹었어', '좋아']:
        r = say(client, cid, text)
    assert r['finished'] is True
    d = _detail(client, cid)
    assert d['status'] == 'completed' and d['assessment']['grade'] == 'urgent'
    assert d['assessment']['safety'][0]['category'] == '낙상'


def test_bug2_safety_on_last_question_still_finishes(client):
    cid = start_call(client, resident_id(client, '박정호'))
    for text in ['괜찮아', '먹었어', '잘 잤어', '먹었어']:
        say(client, cid, text)
    r = say(client, cid, '죽고 싶어')
    assert r['finished'] is True and r['action'] == 'safety' and Q.CLOSING in r['ai_text']


# 3. 미응답 상태가 없었음 → 30초 넘게 울린 벨은 missed
def test_bug3_ringing_becomes_missed_after_30_seconds(client, clock):
    rid = resident_id(client, '박정호')
    cid = client.post(f'/api/staff/residents/{rid}/call').json()['id']
    clock.advance(seconds=29)
    assert client.get(f'/api/elder/{rid}/incoming').json()['ringing']['call_id'] == cid
    clock.advance(seconds=2)
    assert client.get(f'/api/elder/{rid}/incoming').json()['ringing'] is None
    d = _detail(client, cid)
    assert d['status'] == 'missed' and d['status_label'] == '미응답'
    assert any(r['chip'] == '오늘 미응답' and r['points'] == 10 for r in d['assessment']['reasons'])
    assert client.post(f'/api/elder/calls/{cid}/answer').status_code == 409


# 4. 버려진 in_progress 가 새 통화를 영원히 막았음 → 10분 무응답이면 interrupted
def test_bug4_abandoned_call_becomes_interrupted_and_unblocks(client, clock):
    rid = resident_id(client, '박정호')
    cid = start_call(client, rid)
    say(client, cid, '괜찮아요')
    assert client.post(f'/api/staff/residents/{rid}/call').status_code == 409
    clock.advance(minutes=10, seconds=1)
    d = _detail(client, cid)
    assert d['status'] == 'interrupted'
    assert any(r['chip'] == '통화 중단' for r in d['assessment']['reasons'])
    assert client.post(f'/api/staff/residents/{rid}/call').status_code == 201


# 5. 식사 질문에 "외로워요" → 엉뚱한 고정 문장. 공감은 실제로 한 말을 반영해야 한다
def test_bug5_mood_reply_to_meal_question_gets_relevant_fallback(client):
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아요')
    r = say(client, cid, '외로워요')
    assert '외로' in r['empathy'] and r['ai_text'].startswith(r['empathy'])
    assert '식사' not in r['empathy']
    elder = [t for t in _detail(client, cid)['turns'] if t['role'] == 'elder']
    assert {'topic': 'mood', 'status': 'caution', 'origin': 'rule'} in elder[-1]['judged']
    assert r['topic'] == 'meal'            # 식사는 아직 못 들었으니 다시 묻는다


def test_bug5_llm_empathy_reflects_answer(make_client):
    llm = FakeLLM(extract=lambda t, q, a: ExtractResult(intent='answer', items=[
        {'topic': 'meal', 'quote': '아침은 걸렀어', 'status': 'caution'},
        {'topic': 'mood', 'quote': '외로워서', 'status': 'caution'}]),
        empathy=lambda topic, answer, items: '외로우셔서 아침도 거르셨군요.')
    client = make_client(llm=llm)
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아요', source='option')
    r = say(client, cid, '아침은 걸렀어. 외로워서.')
    assert r['empathy'] == '외로우셔서 아침도 거르셨군요.' and r['llm_used'] is True
    assert r['ai_text'] == '외로우셔서 아침도 거르셨군요. ' + Q.QUESTIONS['sleep']
    empathy_call = [c for c in llm.calls if c[0] == 'empathy'][-1]
    assert {i['topic'] for i in empathy_call[3]} == {'meal', 'mood'}


def test_bug5_fallback_templates_keyed_by_topic_and_status():
    assert Q.fallback_empathy('meal', [{'topic': 'meal', 'status': 'caution'}], '못 먹었어') == \
        Q.EMPATHY_TEMPLATES[('meal', 'caution')]
    assert Q.fallback_empathy('med', [{'topic': 'med', 'status': 'good'}], '약 없어') == Q.MED_NONE_EMPATHY
    assert '외로' in Q.fallback_empathy('meal', [{'topic': 'meal', 'status': 'good'},
                                                {'topic': 'mood', 'status': 'caution'}], '먹었는데 외로워')
