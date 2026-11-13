"""판정규칙.md §8 어려움 유형 + 식사 재질문 (제안서 3.나.2)."""
import pytest

from app.domain import dialogue, keywords, needs
from app.domain import questions as Q
from app.services.llm import ExtractResult, FakeLLM

from .conftest import resident_id, say, start_call


def types(text):
    return [n['type'] for n in needs.detect(text)]


# ---- 유형마다 한 줄 ----
@pytest.mark.parametrize('text', ['먹을 게 없어서 못 먹었어', '혼자 차려 먹기가 힘들어', '반찬 살 돈이 없어',
                                  '장 보기가 힘들어', '반찬이 하나도 없어', '혼자 해 먹기 힘들어'])
def test_need_meal_difficulty(text):
    assert types(text) == ['meal_difficulty']


@pytest.mark.parametrize('text', ['며칠째 잠을 못 자', '잠이 안 와', '밤새 뒤척였어', '한숨도 못 잤어'])
def test_need_sleep_problem(text):
    assert types(text) == ['sleep_problem']


@pytest.mark.parametrize('text', ['도움이 필요해', '도와줄 사람이 없어', '누가 좀 와 줬으면 좋겠어'])
def test_need_help_request(text):
    assert types(text) == ['help_request']


@pytest.mark.parametrize('text', ['외로워', '아무도 안 와', '말할 사람이 없어'])
def test_need_loneliness(text):
    assert types(text) == ['loneliness']


@pytest.mark.parametrize('text', ['밥 잘 먹었어', '아직 밥을 안 먹었어요', '안 외로워', '도움은 필요 없어', '잘 잤어',
                                  '약 살 돈이 없어', '도와줘', '119 불러줘'])
def test_no_need_on_plain_or_negated_answers(text):
    assert types(text) == []          # 119·도와줘는 안전 신호(safety.py)가 맡는다


def test_need_quote_is_substring_and_labelled():
    text = '밥은… 먹을 게 없어서 못 먹었어'
    [n] = needs.detect(text)
    assert n['quote'] in text and n['label'] == '식사 어려움' and n['origin'] == 'rule'


def test_proposal_two_sentences():
    """제안서 3.나.2: 미식사 vs 식사 어려움 — 둘 다 식사 주의지만 어려움 유형은 뒤에만."""
    a, b = '아직 밥을 안 먹었어요', '먹을 게 없어서 밥을 못 먹었어요'
    assert keywords.extract('meal', a).items[0]['status'] == 'caution' and types(a) == []
    assert keywords.extract('meal', b).items[0]['status'] == 'caution' and types(b) == ['meal_difficulty']


@pytest.mark.parametrize('text,expected', [
    ('혼자 차려 먹기 힘들어', 'caution'), ('반찬 살 돈이 없어', 'caution'), ('장 보기가 힘들어', 'caution'),
    ('이틀째 먹을 게 없어', 'risk'), ('며칠째 먹을 게 없어서 굶었어', 'risk'), ('아직 식사 전이에요', 'caution'),
])
def test_meal_difficulty_phrases_are_judged_as_meal(text, expected):
    r = keywords.extract('meal', text)
    assert r.intent == 'answer' and r.items[0] == {'topic': 'meal', 'status': expected, 'quote': r.items[0]['quote']}


def test_followup_options_classify_as_intended():
    first, *difficulty = dialogue.FOLLOWUP_OPTIONS
    assert types(first) == [] and keywords.extract('meal', first).items[0]['status'] == 'caution'
    for text in difficulty:
        assert types(text) == ['meal_difficulty'] and keywords.extract('meal', text).intent == 'answer'


@pytest.mark.parametrize('text,want', [
    ('아직 안 먹었어', True), ('이틀째 밥을 제대로 못 먹었어', True), ('아니', True),
    ('아침은 걸렀어. 입맛이 없어서.', False),      # 이유가 있음
    ('먹을 게 없어서 못 먹었어', False),           # 어려움 유형이 이미 있음
    ('조금 먹었어', False), ('밥 먹었어', False),
])
def test_wants_meal_followup(text, want):
    items = keywords.extract('meal', text).items
    assert dialogue.wants_meal_followup('meal', items, needs.detect(text), text) is want


def test_combine_needs_rule_cannot_be_removed_and_llm_quote_checked():
    labels = needs.labels()
    rule = needs.detect('외로워')
    llm = [{'type': 'sleep_problem', 'quote': '잠이 안 와'}, {'type': 'help_request', 'quote': '지어낸 말'}]
    out = dialogue.combine_needs('외로워. 잠이 안 와', rule, llm, labels)
    assert [(n['type'], n['origin']) for n in out] == [('loneliness', 'rule'), ('sleep_problem', 'llm')]
    assert dialogue.combine_needs('외로워', rule, [], labels) == rule


def test_llm_cannot_call_plain_not_eaten_a_meal_difficulty():
    llm = [{'type': 'meal_difficulty', 'quote': '아직 안 먹었어'}]
    assert dialogue.combine_needs('아직 안 먹었어', [], llm, needs.labels()) == []
    llm = [{'type': 'meal_difficulty', 'quote': '혼자라서 차리기 귀찮아서 못 먹었어'}]
    assert len(dialogue.combine_needs('혼자라서 차리기 귀찮아서 못 먹었어', [], llm, needs.labels())) == 1


def test_merge_keeps_first_quote_per_type():
    a = [{'type': 'loneliness', 'label': '외로움', 'quote': '외로워', 'origin': 'rule'}]
    b = [{'type': 'loneliness', 'label': '외로움', 'quote': '아무도 안 와', 'origin': 'rule'}]
    assert needs.merge([a, b]) == a


# ---- 통화 흐름 ----
def _to_meal(client):
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아요')
    return cid


def test_reask_flow_no_reason_asks_once_then_advances(client):
    cid = _to_meal(client)
    r = say(client, cid, '아직 안 먹었어')
    assert r['action'] == 'reask' and r['question'] == dialogue.FOLLOWUP_QUESTION and r['topic'] == 'meal'
    assert r['options'] == dialogue.FOLLOWUP_OPTIONS and r['ai_text'].endswith(dialogue.FOLLOWUP_QUESTION)
    r = say(client, cid, '먹을 게 없어서 못 먹었어요', source='option')
    assert r['action'] == 'next' and r['topic'] == 'sleep'
    assert r['empathy'] == Q.FOLLOWUP_EMPATHY['meal_difficulty']
    for text in ['잘 잤어', '먹었어', '좋아']:
        r = say(client, cid, text)
    assert r['finished']
    d = client.get(f'/api/staff/calls/{cid}').json()
    elder = [t for t in d['turns'] if t['role'] == 'elder']
    assert elder[1]['needs'] == [] and [n['type'] for n in elder[2]['needs']] == ['meal_difficulty']
    a = d['assessment']
    assert a['items']['meal']['status'] == 'caution' and [n['type'] for n in a['needs']] == ['meal_difficulty']
    assert a['score'] == 5                                   # 어려움 유형은 점수에 넣지 않는다


def test_reask_flow_not_yet_eaten_records_no_need_and_keeps_risk(client):
    cid = _to_meal(client)
    assert say(client, cid, '이틀째 못 먹었어')['action'] == 'reask'
    r = say(client, cid, '아직 식사 전이에요', source='option')
    assert r['action'] == 'next' and r['empathy'] == Q.FOLLOWUP_EMPATHY[None]
    for text in ['잘 잤어', '먹었어', '좋아']:
        say(client, cid, text)
    a = client.get(f'/api/staff/calls/{cid}').json()['assessment']
    assert a['items']['meal']['status'] == 'risk' and a['needs'] == []     # 재질문 대답이 위험을 내리지 않음


def test_reask_flow_unclear_reply_still_advances(client):
    cid = _to_meal(client)
    say(client, cid, '안 먹었어')
    r = say(client, cid, '음…')
    assert r['action'] == 'next' and r['topic'] == 'sleep'


def test_no_followup_when_reason_or_need_given(client):
    cid = _to_meal(client)
    r = say(client, cid, '먹을 게 없어서 못 먹었어')
    assert r['action'] == 'next' and r['topic'] == 'sleep'


def test_followup_counts_toward_reask_limit(client):
    cid = _to_meal(client)
    assert say(client, cid, '', source='silence')['action'] == 'reask'
    assert say(client, cid, '', source='silence')['action'] == 'reask'
    assert say(client, cid, '안 먹었어')['action'] == 'next'    # 이미 두 번 다시 물어서 재질문 안 함


def test_llm_needs_are_merged_with_quote_check(make_client):
    llm = FakeLLM(extract=lambda t, q, a: ExtractResult.model_validate({
        'intent': 'answer', 'items': [{'topic': t, 'quote': a, 'status': 'good'}],
        'needs': [{'type': 'loneliness', 'quote': '혼자 있어'}, {'type': 'help_request', 'quote': '없는 말'}]}))
    client = make_client(llm=llm)
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아. 혼자 있어')
    d = client.get(f'/api/staff/calls/{cid}').json()
    elder = [t for t in d['turns'] if t['role'] == 'elder'][-1]
    assert elder['needs'] == [{'type': 'loneliness', 'label': '외로움', 'quote': '혼자 있어', 'origin': 'llm'}]
    assert [x for x in d['ai_runs'] if x['step'] == 'extract'][-1]['note'] == '인용 불일치 1개 버림'


def test_ai_turn_ms_is_sum_of_extract_and_empathy(make_client):
    client = make_client(llm=FakeLLM(extract=lambda t, q, a: ExtractResult(intent='answer', items=[
        {'topic': t, 'quote': a, 'status': 'good'}]), empathy='다행이에요.'))
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아')
    d = client.get(f'/api/staff/calls/{cid}').json()
    ai = [t for t in d['turns'] if t['role'] == 'ai']
    runs = [x['ms'] for x in d['ai_runs'] if x['step'] in ('extract', 'empathy')]
    assert ai[0]['ms'] is None and ai[1]['ms'] == sum(runs)


def test_ai_turn_ms_is_null_with_rules_only(client):
    cid = _to_meal(client)
    d = client.get(f'/api/staff/calls/{cid}').json()
    assert all(t['ms'] is None for t in d['turns'] if t['role'] == 'ai')


def test_closing_does_not_repeat_thanks():
    d = dialogue.Decision('finish', 'mood', dialogue.State(index=5), False, True)
    r = dialogue.compose(d, empathy='많이 외로우셨겠어요. 말씀해 주셔서 고마워요.', silence=False, safety_hit=False,
                         llm_used=False)
    assert r['ai_text'] == '많이 외로우셨겠어요. ' + Q.CLOSING and r['ai_text'].count('고마워요') == 1
    r = dialogue.compose(d, empathy=Q.GENERIC_EMPATHY, silence=False, safety_hit=False, llm_used=False)
    assert r['ai_text'] == Q.CLOSING and r['empathy'] is None
