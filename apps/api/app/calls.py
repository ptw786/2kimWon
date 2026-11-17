"""통화 진행 (응용 계층): DB 읽기 → 순수 판단(domain) + LLM(services) → 짧은 쓰기 트랜잭션.

규칙: LLM 은 절대 tx() 안에서 부르지 않는다. 각 함수에서 LLM 단계는 tx() 블록보다 앞에 있다.
"""
import json
import sqlite3
import time
from datetime import date, timedelta

from fastapi import HTTPException

from . import db
from .db import iso, now, now_iso, parse, tx
from .domain import dialogue, keywords, needs, safety, scoring
from .domain import questions as Q
from .domain.questions import TOPICS
from .services.llm import LLMBadOutput, LLMError, clean_empathy, clean_summary

RULES = scoring.rules()
RING_SECONDS = RULES['timeouts']['ring_seconds']
IDLE_MINUTES = RULES['timeouts']['idle_minutes']
FINISHED = ('completed', 'interrupted', 'missed', 'declined')
ANSWERED = ('completed', 'interrupted')
ACTIVE = ('ringing', 'in_progress')


# ---------- 조회 도우미 ----------
def get_resident(conn, rid: int) -> sqlite3.Row:
    row = conn.execute('SELECT * FROM residents WHERE id = ?', (rid,)).fetchone()
    if row is None:
        raise HTTPException(404, '어르신을 찾을 수 없어요.')
    return row


def get_call(conn, call_id: int) -> sqlite3.Row:
    row = conn.execute('SELECT c.*, r.name AS resident_name FROM calls c JOIN residents r ON r.id = c.resident_id '
                       'WHERE c.id = ?', (call_id,)).fetchone()
    if row is None:
        raise HTTPException(404, '통화를 찾을 수 없어요.')
    return row


def resident_out(row) -> dict:
    return {'id': row['id'], 'code': row['code'], 'name': row['name'], 'age': row['age'], 'region': row['region'],
            'neighborhood': row['neighborhood'], 'call_time': row['call_time'], 'memo': row['memo'],
            'is_virtual': bool(row['is_virtual'])}


def call_step(row) -> dict:
    st = row['status']
    if st in ('ringing', 'missed', 'declined'):
        idx = 0
    elif st == 'completed':
        idx = dialogue.TOTAL
    else:
        idx = min(row['step_index'] + 1, dialogue.TOTAL)
    return {'index': idx, 'total': dialogue.TOTAL}


def assessment_out(raw: str | None) -> dict | None:
    """저장된 판정 JSON → 응답. 예전(v2) 기록도 지금 라벨·needs 모양으로 맞춘다 (점수는 그대로)."""
    if not raw:
        return None
    a = json.loads(raw)
    a['grade_label'] = scoring.grade_label(a['grade'])
    a.setdefault('needs', [])
    return a


def call_summary(row) -> dict:
    return {
        'id': row['id'], 'resident_id': row['resident_id'], 'resident_name': row['resident_name'],
        'status': row['status'], 'status_label': Q.CALL_STATUS_LABELS[row['status']],
        'created_at': db.kst(row['created_at']), 'started_at': db.kst(row['started_at']),
        'ended_at': db.kst(row['ended_at']), 'summary': row['summary'],
        'assessment': assessment_out(row['assessment']),
    }


def staff_check_of(row) -> dict | None:
    if not row['staff_check_at']:
        return None
    return {'checked': True, 'note': row['staff_check_note'] or '', 'at': db.kst(row['staff_check_at'])}


def turns_of(conn, call_id: int) -> list[dict]:
    out = []
    for t in conn.execute('SELECT * FROM turns WHERE call_id = ? ORDER BY id', (call_id,)):
        d = {'role': t['role'], 'text': t['text'], 'topic': t['topic'], 'at': db.kst(t['at'])}
        if t['role'] == 'elder':
            d['source'] = t['source']
            d['judged'] = json.loads(t['judged']) if t['judged'] else []
            d['needs'] = json.loads(t['needs']) if t['needs'] else []
        else:
            d['ms'] = t['ms']
        out.append(d)
    return out


def ai_runs_of(conn, call_id: int) -> list[dict]:
    return [{'at': db.kst(r['at']), 'step': r['step'], 'model': r['model'], 'ms': r['ms'], 'outcome': r['outcome'],
             'note': r['note']} for r in conn.execute('SELECT * FROM ai_runs WHERE call_id = ? ORDER BY id', (call_id,))]


# ---------- 어려움 유형 ----------
def call_needs(conn, call_id: int) -> list[dict]:
    """이 통화의 어르신 답변에서 찾은 어려움 → 유형마다 처음 나온 것 하나."""
    return needs.merge([json.loads(r['needs']) for r in conn.execute(
        "SELECT needs FROM turns WHERE call_id = ? AND role = 'elder' AND needs IS NOT NULL ORDER BY id", (call_id,))])


def recent_needs(conn, resident_id: int, since_day: str) -> list[dict]:
    """since_day 이후 통화들의 어려움 → 유형마다 가장 최근 것 하나 (최근 것부터)."""
    return needs.merge([json.loads(r['needs']) for r in conn.execute(
        "SELECT t.needs FROM turns t JOIN calls c ON c.id = t.call_id WHERE c.resident_id = ? AND c.kst_date >= ? "
        "AND t.role = 'elder' AND t.needs IS NOT NULL ORDER BY t.id DESC", (resident_id, since_day))])


# ---------- 점수 ----------
def day_items(conn, resident_id: int, day: str, exclude_call: int | None = None) -> dict | None:
    """그날 답을 들은 통화(완료·중단)의 항목을 합친 것. 그런 통화가 없으면 None."""
    calls = [r['id'] for r in conn.execute(
        f"SELECT id FROM calls WHERE resident_id = ? AND kst_date = ? AND status IN {ANSWERED} AND id != ?",
        (resident_id, day, exclude_call or -1))]
    if not calls:
        return None
    rows = conn.execute(f"SELECT topic, status, quote, origin FROM items WHERE call_id IN ({','.join('?' * len(calls))})",
                        calls).fetchall()
    return scoring.merge_items([dict(r) for r in rows])


def compute_assessment(conn, call, status: str, rule_set: dict | None = None) -> dict:
    items = scoring.merge_items([dict(r) for r in conn.execute(
        'SELECT topic, status, quote, origin FROM items WHERE call_id = ? ORDER BY id', (call['id'],))])
    sig = [{'category': r['category'], 'quote': r['quote']} for r in conn.execute(
        'SELECT category, quote FROM safety_signals WHERE call_id = ? ORDER BY id', (call['id'],))]
    d = date.fromisoformat(call['kst_date'])
    window = RULES['trend']['window_days']
    history = []
    for k in range(1, window):
        merged = day_items(conn, call['resident_id'], (d - timedelta(days=k)).isoformat())
        history.append({t: v['status'] for t, v in merged.items()} if merged else None)
    start = (d - timedelta(days=window - 1)).isoformat()
    prior = [{'status': r['status'], 'days_ago': (d - date.fromisoformat(r['kst_date'])).days} for r in conn.execute(
        f"SELECT status, kst_date FROM calls WHERE resident_id = ? AND id != ? AND status IN {FINISHED} "
        "AND kst_date >= ? AND (created_at < ? OR (created_at = ? AND id < ?)) ORDER BY created_at DESC, id DESC",
        (call['resident_id'], call['id'], start, call['created_at'], call['created_at'], call['id']))]
    return scoring.assess(items, sig, history, status, prior, rule_set, needs=call_needs(conn, call['id']))


def finish_call(conn, call_id: int, status: str, ended_at: str | None = None) -> dict:
    """tx() 안에서 부른다. 상태를 닫고 점수·규칙 요약을 저장한다 (AI 요약은 나중에 덮어씀)."""
    call = conn.execute('SELECT * FROM calls WHERE id = ?', (call_id,)).fetchone()
    a = compute_assessment(conn, call, status)
    summary = scoring.rule_summary(a['items'], a['safety'], status)
    conn.execute('UPDATE calls SET status = ?, ended_at = ?, assessment = ?, summary = ? WHERE id = ?',
                 (status, ended_at or now_iso(), json.dumps(a, ensure_ascii=False), summary, call_id))
    return a


def apply_timeouts(conn) -> int:
    """벨 30초 → missed, 통화 중 10분 무응답 → interrupted. 모든 읽기·쓰기 전에, 그리고 스케줄러에서."""
    n = now()
    ring_cut = iso(n - timedelta(seconds=RING_SECONDS))
    idle_cut = iso(n - timedelta(minutes=IDLE_MINUTES))
    q = ("SELECT id FROM calls WHERE (status = 'ringing' AND created_at < ?) "
         "OR (status = 'in_progress' AND last_activity_at < ?)")
    if not conn.execute(q, (ring_cut, idle_cut)).fetchall():
        return 0
    count = 0
    with tx(conn):
        for r in conn.execute(q, (ring_cut, idle_cut)).fetchall():
            call = conn.execute('SELECT * FROM calls WHERE id = ?', (r['id'],)).fetchone()
            if call['status'] == 'ringing':
                end = iso(parse(call['created_at']) + timedelta(seconds=RING_SECONDS))
                finish_call(conn, call['id'], 'missed', end)
            else:
                finish_call(conn, call['id'], 'interrupted', call['last_activity_at'])
            count += 1
    return count


# ---------- 통화 시작·끝 ----------
def create_call(conn, resident_id: int, origin: str = 'staff') -> int:
    with tx(conn):
        get_resident(conn, resident_id)
        if conn.execute(f"SELECT 1 FROM calls WHERE resident_id = ? AND status IN {ACTIVE}", (resident_id,)).fetchone():
            raise HTTPException(409, '이미 벨이 울리고 있거나 통화 중이에요.')
        t = now()
        cur = conn.execute(
            "INSERT INTO calls (resident_id, kst_date, status, origin, created_at, last_activity_at) "
            "VALUES (?, ?, 'ringing', ?, ?, ?)",
            (resident_id, t.astimezone(db.KST).date().isoformat(), origin, iso(t), iso(t)))
        return cur.lastrowid


def answer_call(conn, call_id: int) -> dict:
    call = get_call(conn, call_id)
    if call['status'] == 'in_progress':
        first = conn.execute("SELECT result FROM turns WHERE call_id = ? AND role = 'ai' ORDER BY id LIMIT 1",
                             (call_id,)).fetchone()
        elder = conn.execute("SELECT 1 FROM turns WHERE call_id = ? AND role = 'elder'", (call_id,)).fetchone()
        if first and first['result'] and not elder:
            return json.loads(first['result'])   # 같은 '받기'가 두 번 와도 같은 결과
        raise HTTPException(409, '이미 통화 중이에요.')
    if call['status'] != 'ringing':
        raise HTTPException(409, '이미 끝난 전화예요.')
    result = dialogue.start_result(call['resident_name'])
    with tx(conn):
        t = now_iso()
        if conn.execute("UPDATE calls SET status = 'in_progress', started_at = ?, last_activity_at = ? "
                        "WHERE id = ? AND status = 'ringing'", (t, t, call_id)).rowcount != 1:
            raise HTTPException(409, '이미 끝난 전화예요.')
        conn.execute("INSERT INTO turns (call_id, role, text, topic, at, result) VALUES (?, 'ai', ?, ?, ?, ?)",
                     (call_id, result['ai_text'], result['topic'], t, json.dumps(result, ensure_ascii=False)))
    return result


def decline_call(conn, call_id: int) -> str:
    call = get_call(conn, call_id)
    if call['status'] == 'declined':
        return 'declined'
    if call['status'] != 'ringing':
        raise HTTPException(409, '벨이 울리는 전화만 거절할 수 있어요.')
    with tx(conn):
        if conn.execute("SELECT status FROM calls WHERE id = ?", (call_id,)).fetchone()['status'] != 'ringing':
            raise HTTPException(409, '벨이 울리는 전화만 거절할 수 있어요.')
        finish_call(conn, call_id, 'declined')
    return 'declined'


def hangup_call(conn, call_id: int) -> tuple[str, bool]:
    """(상태, AI 요약 필요 여부). 마지막 질문 전에 끊으면 interrupted."""
    call = get_call(conn, call_id)
    if call['status'] == 'ringing':
        return decline_call(conn, call_id), False
    if call['status'] != 'in_progress':
        return call['status'], False
    with tx(conn):
        if conn.execute("SELECT status FROM calls WHERE id = ?", (call_id,)).fetchone()['status'] != 'in_progress':
            return get_call(conn, call_id)['status'], False
        finish_call(conn, call_id, 'interrupted')
    return 'interrupted', True


# ---------- LLM 시도 기록 ----------
def _attempt(llm, step: str, fn, validate=None):
    """LLM 한 번 시도 → (값 또는 None, ai_runs 행). 실패는 모두 None(=규칙이 대신)."""
    t0 = time.perf_counter()
    note = None
    try:
        value = fn()
        if validate is not None:
            value = validate(value)
            if value is None:
                raise LLMBadOutput('형식 오류 (검증 실패)')
        outcome = 'ok'
    except AssertionError:
        raise
    except LLMError as e:
        value, outcome, note = None, 'fallback', e.note
    except Exception as e:  # noqa: BLE001 — 어떤 실패든 통화는 규칙으로 계속한다
        value, outcome, note = None, 'fallback', f'오류 {type(e).__name__}'
    ms = int((time.perf_counter() - t0) * 1000)
    model = getattr(llm, 'model', None)
    if getattr(llm, 'mode', None) == 'rules':
        ms = None
    if getattr(llm, 'seed_note', None):
        note, ms = llm.seed_note, llm.seed_ms(step)
    return value, {'at': now_iso(), 'step': step, 'model': model, 'ms': ms, 'outcome': outcome, 'note': note}


def _insert_runs(conn, call_id, runs):
    for r in runs:
        conn.execute('INSERT INTO ai_runs (call_id, at, step, model, ms, outcome, note) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (call_id, r['at'], r['step'], r['model'], r['ms'], r['outcome'], r['note']))


# ---------- 한 턴 ----------
def process_turn(conn, llm, call_id: int, text: str, source: str, client_turn_id: str) -> tuple[dict, bool]:
    """(TurnResult, 통화가 이번에 끝났는지)."""
    # 0) 읽기 — 같은 client_turn_id 면 저장된 결과 그대로
    dup = conn.execute('SELECT result FROM turns WHERE call_id = ? AND client_turn_id = ?',
                       (call_id, client_turn_id)).fetchone()
    if dup:
        return json.loads(dup['result']), False
    call = get_call(conn, call_id)
    if call['status'] != 'in_progress':
        raise HTTPException(409, '지금 진행 중인 통화가 아니에요.')
    state = dialogue.State(call['step_index'], call['reasks'], call['repeats'])
    asked = state.topic
    text = (text or '').strip()
    silence = source == 'silence' or not text

    # 이 주제에서 식사 재질문을 이미 했는지 (했으면 이번 답변 뒤에는 무조건 넘어간다)
    in_followup = asked == 'meal' and any(
        r['result'] and json.loads(r['result']).get('question') == dialogue.FOLLOWUP_QUESTION
        for r in conn.execute("SELECT result FROM turns WHERE call_id = ? AND role = 'elder'", (call_id,)))

    # 1) 판단 — DB 잠금 없이 (LLM 은 여기서만)
    runs = []
    hits = [] if silence else safety.detect(text)
    rule = keywords.extract(asked, '' if silence else text)
    rule_needs = [] if silence else needs.detect(text)
    llm_items, llm_needs, intent = None, None, rule.intent
    if not silence and source != 'option':
        res, run = _attempt(llm, 'extract', lambda: llm.extract(asked, Q.QUESTIONS[asked], text))
        if res is not None:
            llm_items = [i.model_dump() for i in res.items]
            llm_needs = [n.model_dump() for n in res.needs]
            dropped = sum(1 for i in llm_items + llm_needs if not dialogue.quote_in_answer(i['quote'], text))
            if dropped:
                run['note'] = f'인용 불일치 {dropped}개 버림'
            intent = res.intent
        runs.append(run)
    items = dialogue.combine_extractions(asked, '' if silence else text, rule.items, llm_items)
    found_needs = dialogue.combine_needs(text, rule_needs, llm_needs, needs.labels())
    decision = dialogue.decide(state, intent=intent, judged_topics={i['topic'] for i in items},
                               safety_hit=bool(hits), silence=silence, in_followup=in_followup,
                               want_followup=dialogue.wants_meal_followup(asked, items, found_needs, text))
    empathy = None
    if (items or in_followup) and decision.action in ('next', 'finish', 'reask') and not decision.mark_unknown:
        empathy, run = _attempt(llm, 'empathy', lambda: llm.empathy(asked, text, items), validate=clean_empathy)
        runs.append(run)
        if empathy is None and in_followup:
            difficulty = any(n['type'] == 'meal_difficulty' for n in found_needs)
            empathy = Q.FOLLOWUP_EMPATHY['meal_difficulty' if difficulty else None]
        elif empathy is None:
            empathy = Q.fallback_empathy(asked, items, text)
    llm_used = any(r['outcome'] == 'ok' for r in runs)
    result = dialogue.compose(decision, empathy=empathy, silence=silence, safety_hit=bool(hits), llm_used=llm_used)
    timed = [r['ms'] for r in runs if r['step'] in ('extract', 'empathy') and r['ms'] is not None]
    ai_ms = sum(timed) if timed else None
    judged = [{'topic': i['topic'], 'status': i['status'], 'origin': i['origin']} for i in items]
    if decision.mark_unknown and asked not in {i['topic'] for i in items}:
        judged.append({'topic': asked, 'status': 'unknown', 'origin': 'rule'})

    # 2) 저장 — 짧은 쓰기 트랜잭션
    with tx(conn):
        dup = conn.execute('SELECT result FROM turns WHERE call_id = ? AND client_turn_id = ?',
                           (call_id, client_turn_id)).fetchone()
        if dup:
            return json.loads(dup['result']), False
        cur = conn.execute('SELECT status, step_index, reasks, repeats FROM calls WHERE id = ?', (call_id,)).fetchone()
        if cur['status'] != 'in_progress' or (cur['step_index'], cur['reasks'], cur['repeats']) != (
                state.index, state.reasks, state.repeats):
            raise HTTPException(409, '다른 답변이 먼저 처리됐어요. 화면을 새로 불러와 주세요.')
        t = now_iso()
        tid = conn.execute(
            "INSERT INTO turns (call_id, role, text, topic, at, source, judged, needs, client_turn_id, result) "
            "VALUES (?, 'elder', ?, ?, ?, ?, ?, ?, ?, ?)",
            (call_id, text, asked, t, source, json.dumps(judged, ensure_ascii=False),
             json.dumps(found_needs, ensure_ascii=False), client_turn_id,
             json.dumps(result, ensure_ascii=False))).lastrowid
        for i in items:
            conn.execute('INSERT INTO items (call_id, turn_id, topic, status, quote, origin) VALUES (?, ?, ?, ?, ?, ?)',
                         (call_id, tid, i['topic'], i['status'], i['quote'], i['origin']))
        if decision.mark_unknown:
            conn.execute("INSERT INTO items (call_id, turn_id, topic, status, quote, origin) "
                         "VALUES (?, ?, ?, 'unknown', NULL, 'rule')", (call_id, tid, asked))
        for h in hits:
            conn.execute('INSERT INTO safety_signals (call_id, turn_id, category, quote, at) VALUES (?, ?, ?, ?, ?)',
                         (call_id, tid, h['category'], h['quote'], t))
        conn.execute("INSERT INTO turns (call_id, role, text, topic, at, ms) VALUES (?, 'ai', ?, ?, ?, ?)",
                     (call_id, result['ai_text'], result['topic'], t, ai_ms))
        _insert_runs(conn, call_id, runs)
        ns = decision.state
        conn.execute('UPDATE calls SET step_index = ?, reasks = ?, repeats = ?, last_activity_at = ? WHERE id = ?',
                     (ns.index, ns.reasks, ns.repeats, t, call_id))
        if decision.finished:
            finish_call(conn, call_id, 'completed', t)
    return result, decision.finished


def finalize_summary(conn, llm, call_id: int) -> None:
    """통화가 끝난 뒤 AI 요약으로 규칙 요약을 덮어쓴다 (실패하면 규칙 요약 유지)."""
    call = conn.execute('SELECT status, assessment FROM calls WHERE id = ?', (call_id,)).fetchone()
    if call is None or call['status'] not in ANSWERED or not call['assessment']:
        return
    a = json.loads(call['assessment'])
    quotes = [f"안전 신호 {s['category']}: \"{s['quote']}\"" for s in a['safety']]
    quotes += [f"어려움 {n['label']}: \"{n['quote']}\"" for n in a.get('needs', [])]
    if call['status'] == 'interrupted':
        quotes.append('통화가 중간에 끊김')
    text, run = _attempt(llm, 'summary', lambda: llm.summary(a['items'], quotes), validate=clean_summary)
    with tx(conn):
        _insert_runs(conn, call_id, [run])
        if text:
            conn.execute('UPDATE calls SET summary = ? WHERE id = ?', (text, call_id))


# ---------- 스케줄러 ----------
def scheduler_tick(conn) -> list[int]:
    """정해진 시간에 전화: call_time ≤ 지금 < call_time+2시간, 오늘 통화가 없으면 벨. 미응답이면 10분 뒤 한 번 더."""
    apply_timeouts(conn)
    sc = RULES['scheduler']
    n = now()
    local = n.astimezone(db.KST)
    today = local.date().isoformat()
    created = []
    for r in conn.execute('SELECT id, call_time FROM residents ORDER BY id').fetchall():
        hh, mm = map(int, r['call_time'].split(':'))
        due = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if not (due <= local < due + timedelta(hours=sc['window_hours'])):
            continue
        calls = conn.execute('SELECT status, created_at, ended_at FROM calls WHERE resident_id = ? AND kst_date = ? '
                             'ORDER BY created_at DESC, id DESC', (r['id'], today)).fetchall()
        if calls:
            last = calls[0]
            if last['status'] != 'missed' or len(calls) >= sc['max_attempts_per_day']:
                continue
            if n - parse(last['ended_at'] or last['created_at']) < timedelta(minutes=sc['retry_after_minutes']):
                continue
        try:
            created.append(create_call(conn, r['id'], origin='scheduler'))
        except HTTPException:
            pass
    return created
