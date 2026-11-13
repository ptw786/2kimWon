"""LLM 실패·이상 출력 → 규칙이 대신하는지, LLM 이 쓰기 트랜잭션 밖에서만 불리는지."""
import httpx
import pytest

from app import calls, db
from app.domain import questions as Q
from app.services import llm as llm_mod
from app.services.llm import ExtractResult, FakeLLM, LLMTimeout, OllamaClient, clean_empathy

from .conftest import resident_id, say, start_call


def _detail(client, cid):
    return client.get(f'/api/staff/calls/{cid}').json()


def _to_meal(client):
    cid = start_call(client, resident_id(client, '박정호'))
    say(client, cid, '괜찮아요', source='option')
    return cid


def test_timeout_falls_back_to_rules_and_is_recorded(make_client):
    client = make_client(llm=FakeLLM(extract=LLMTimeout(4.0), empathy=LLMTimeout(3.0)))
    cid = _to_meal(client)
    r = say(client, cid, '아침은 걸렀어. 입맛이 없어서')
    assert r['action'] == 'next' and r['llm_used'] is False
    assert r['empathy'] == Q.EMPATHY_TEMPLATES[('meal', 'caution')]
    d = _detail(client, cid)
    elder = [t for t in d['turns'] if t['role'] == 'elder'][-1]
    assert elder['judged'] == [{'topic': 'meal', 'status': 'caution', 'origin': 'rule'}]
    runs = [x for x in d['ai_runs'] if x['step'] == 'extract']
    assert runs[-1]['outcome'] == 'fallback' and runs[-1]['note'] == '시간 초과 4.0s'
    assert runs[-1]['model'] == 'fake-model'


def test_real_ollama_client_timeout_maps_to_fallback(monkeypatch):
    def boom(*a, **k):
        raise httpx.ReadTimeout('slow')
    monkeypatch.setattr(llm_mod.httpx, 'post', boom)
    c = OllamaClient('http://127.0.0.1:9', 'm')
    with pytest.raises(LLMTimeout):
        c.extract('meal', '질문', '답')
    value, run = calls._attempt(c, 'extract', lambda: c.extract('meal', '질문', '답'))
    assert value is None and run['outcome'] == 'fallback' and run['note'] == '시간 초과 4.0s'


def test_ollama_bad_json_is_fallback(monkeypatch):
    class R:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {'message': {'content': '{"intent": "maybe"}'}}
    monkeypatch.setattr(llm_mod.httpx, 'post', lambda *a, **k: R())
    c = OllamaClient('http://x:1', 'm')
    value, run = calls._attempt(c, 'extract', lambda: c.extract('meal', '질문', '답'))
    assert value is None and run['note'] == '형식 오류'


def test_quote_not_in_answer_is_discarded(make_client):
    llm = FakeLLM(extract=ExtractResult(intent='answer', items=[
        {'topic': 'meal', 'quote': '사흘을 굶었어', 'status': 'risk'},     # 원문에 없는 인용 → 버림
        {'topic': 'meal', 'quote': '밥 먹었어', 'status': 'good'}]))
    client = make_client(llm=llm)
    cid = _to_meal(client)
    say(client, cid, '밥 먹었어')
    d = _detail(client, cid)
    elder = [t for t in d['turns'] if t['role'] == 'elder'][-1]
    assert elder['judged'] == [{'topic': 'meal', 'status': 'good', 'origin': 'llm'}]
    assert [x for x in d['ai_runs'] if x['step'] == 'extract'][-1]['note'] == '인용 불일치 1개 버림'


def test_llm_good_cannot_override_safety_regex(make_client):
    llm = FakeLLM(extract=lambda t, q, a: ExtractResult(intent='answer', items=[{'topic': t, 'quote': a, 'status': 'good'}]))
    client = make_client(llm=llm)
    cid = start_call(client, resident_id(client, '박정호'))
    r = say(client, cid, '가슴이 답답해')
    assert r['safety'] is True and r['action'] == 'safety'
    for text in ['먹었어', '잘 잤어', '먹었어', '좋아']:
        r = say(client, cid, text)
    assert r['finished']
    a = _detail(client, cid)['assessment']
    assert a['grade'] == 'urgent' and a['safety'][0]['category'] == '호흡·가슴'


def test_llm_good_cannot_lower_rule_caution(make_client):
    llm = FakeLLM(extract=lambda t, q, a: ExtractResult(intent='answer', items=[{'topic': t, 'quote': a, 'status': 'good'}]))
    client = make_client(llm=llm)
    cid = _to_meal(client)
    say(client, cid, '못 먹었어')
    elder = [t for t in _detail(client, cid)['turns'] if t['role'] == 'elder'][-1]
    assert elder['judged'] == [{'topic': 'meal', 'status': 'caution', 'origin': 'rule'}]


def test_invalid_empathy_falls_back(make_client):
    client = make_client(llm=FakeLLM(extract=None, empathy='식사는 하셨나요?'))
    cid = _to_meal(client)
    r = say(client, cid, '네, 먹었어요', source='option')
    assert r['empathy'] == Q.EMPATHY_TEMPLATES[('meal', 'good')]
    run = [x for x in _detail(client, cid)['ai_runs'] if x['step'] == 'empathy'][-1]
    assert run['outcome'] == 'fallback' and run['note'].startswith('형식 오류')


@pytest.mark.parametrize('text,ok', [
    ('입맛이 없으셨군요.', True), ('', False), ('괜찮으세요?', False), ('병원에 꼭 가 보세요.', False),
    ('가' * 81, False), ('제가 알려 드릴게요.', False), ('"다행이에요."', True),
])
def test_clean_empathy(text, ok):
    assert (clean_empathy(text) is not None) is ok


def test_llm_is_never_called_inside_a_write_transaction(make_client):
    llm = FakeLLM(extract=lambda t, q, a: ExtractResult(intent='answer', items=[{'topic': t, 'quote': a, 'status': 'good'}]),
                  empathy='다행이에요.', summary='모두 양호함.', in_write_tx=db.in_write_tx)
    client = make_client(llm=llm)
    cid = start_call(client, resident_id(client, '박정호'))
    for text in ['괜찮아', '먹었어', '잘 잤어', '먹었어', '좋아']:
        r = say(client, cid, text)
    assert r['finished'] and r['llm_used']
    steps = [c[0] for c in llm.calls]
    assert steps.count('extract') == 5 and steps.count('empathy') == 5 and steps.count('summary') == 1
    d = _detail(client, cid)
    assert d['summary'] == '모두 양호함.'
    assert all(x['outcome'] == 'ok' for x in d['ai_runs'])
    # 구조 확인: in_write_tx 가 실제로 트랜잭션 안에서 True 가 되는지 (감시 장치가 살아 있는지)
    conn = db.connect(client.app.state.settings.db_path)
    with db.tx(conn):
        assert db.in_write_tx()
    assert not db.in_write_tx()
    conn.close()


def test_fake_llm_detects_call_inside_transaction():
    llm = FakeLLM(empathy='x', in_write_tx=db.in_write_tx)
    conn = db.connect(':memory:')
    with pytest.raises(AssertionError):
        with db.tx(conn):
            llm.empathy('meal', 'a', [])
    conn.close()


def test_summary_failure_keeps_rule_summary(make_client):
    client = make_client(llm=FakeLLM(extract=None, empathy=None, summary=LLMTimeout(8.0)))
    cid = start_call(client, resident_id(client, '박정호'))
    for text in ['괜찮아', '못 먹었어', '아직 식사 전이에요', '잘 잤어', '먹었어', '좋아']:   # 셋째 = 식사 재질문 대답
        say(client, cid, text)
    d = _detail(client, cid)
    assert '식사 주의' in d['summary']
    run = [x for x in d['ai_runs'] if x['step'] == 'summary'][-1]
    assert run['outcome'] == 'fallback' and run['note'] == '시간 초과 8.0s'


def test_clean_summary_rejects_status_label_prefixes():
    from app.services.llm import clean_summary
    assert clean_summary('주: 아직 식사를 하지 않았음. 위험: 혼자 있어 보임.') is None
    assert clean_summary('- 식사 주의') is None
    assert clean_summary('양호: 몸 상태 괜찮음') is None
    ok = '먹을 게 없어 식사를 못 했다고 함(식사 어려움). 몸 상태·수면은 양호함.'
    assert clean_summary(ok) == ok
