"""어르신 앱용 (/api/elder)."""
import json
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import calls, db
from ..domain import dialogue
from ..domain.questions import ELDER_STATUS_LABELS, OPTIONS, QUESTIONS, TOPICS
from .deps import get_conn, get_llm

router = APIRouter(tags=['elder'])

# 기록 화면의 쉬운 말 (양호, 주의 이상)
CHIPS = {
    'body': ('몸 괜찮으셨어요', '몸이 불편하셨어요'),
    'meal': ('식사 잘 하셨어요', '식사를 잘 못 하셨어요'),
    'sleep': ('잘 주무셨어요', '잠을 설치셨어요'),
    'med': ('약 잘 챙기셨어요', '약을 못 챙기셨어요'),
    'mood': ('기분 괜찮으셨어요', '마음이 힘드셨어요'),
}
UNKNOWN_CHIP = {'body': '몸 상태는 못 여쭸어요', 'meal': '식사는 못 여쭸어요', 'sleep': '잠은 못 여쭸어요',
                'med': '약은 못 여쭸어요', 'mood': '기분은 못 여쭸어요'}
YESTERDAY = {
    'completed': '어제는 통화 잘 하셨어요', 'interrupted': '어제는 통화가 중간에 끊겼어요',
    'missed': '어제는 전화를 못 받으셨어요', 'declined': '어제는 전화를 쉬셨어요',
}


class TurnIn(BaseModel):
    text: str = Field(default='', max_length=500)
    source: Literal['stt', 'text', 'option', 'silence']
    client_turn_id: str = Field(min_length=1, max_length=100)
    topic: Literal['body', 'meal', 'sleep', 'med', 'mood'] | None = None   # 앱이 보고 있던 질문 (다르면 412)


def _brief(r) -> dict:
    return {'id': r['id'], 'code': r['code'], 'name': r['name']}


def _main_call(day_calls):
    """그날을 대표하는 통화: 답을 들은 마지막 통화, 없으면 마지막 통화."""
    for c in day_calls:
        if c['status'] in calls.ANSWERED:
            return c
    return day_calls[0] if day_calls else None


def _day_calls(conn, rid, day):
    return conn.execute('SELECT * FROM calls WHERE resident_id = ? AND kst_date = ? ORDER BY created_at DESC, id DESC',
                        (rid, day)).fetchall()


@router.get('/residents')
def residents(request: Request, conn=Depends(get_conn)):
    """어르신 고르기 목록 — 모든 이름이 보이므로 시연 모드에서만. 실제로는 QR·코드로만 연다."""
    if not request.app.state.settings.demo:
        raise HTTPException(403, '어르신 코드나 QR로 열어 주세요.')
    return [_brief(r) for r in conn.execute('SELECT id, code, name FROM residents ORDER BY id')]


@router.post('/{rid}/ring', status_code=201)
def ring_me(rid: int, conn=Depends(get_conn)):
    """어르신이 '지금 전화 받기'·'안심온과 지금 이야기하기'를 눌렀을 때. 생활지원사 로그인 없이 자기 전화만 건다."""
    cid = calls.create_call(conn, rid, origin='elder')
    return {'call_id': cid}


@router.get('/by-code/{code}')
def by_code(code: str, conn=Depends(get_conn)):
    r = conn.execute('SELECT id, code, name FROM residents WHERE code = ?', (code.strip().upper(),)).fetchone()
    if r is None:
        raise HTTPException(404, '등록된 어르신 코드가 아니에요.')
    return _brief(r)


@router.get('/{rid}/home')
def home(rid: int, conn=Depends(get_conn)):
    r = calls.get_resident(conn, rid)
    today = db.kst_today()
    today_calls = _day_calls(conn, rid, today.isoformat())
    status = today_calls[0]['status'] if today_calls else 'not_called'
    y = _main_call(_day_calls(conn, rid, (today - timedelta(days=1)).isoformat()))
    week = conn.execute("SELECT COUNT(DISTINCT kst_date) FROM calls WHERE resident_id = ? AND status = 'completed' "
                        "AND kst_date >= ?", (rid, (today - timedelta(days=6)).isoformat())).fetchone()[0]
    return {
        'name': r['name'], 'call_time': r['call_time'],
        'today': {'status': status, 'status_label': ELDER_STATUS_LABELS[status]},
        'yesterday_label': YESTERDAY.get(y['status'], '어제는 통화 기록이 없어요') if y else '어제는 통화 기록이 없어요',
        'week_count': week,
    }


@router.get('/{rid}/records')
def records(rid: int, conn=Depends(get_conn)):
    calls.get_resident(conn, rid)
    today = db.kst_today()
    out = []
    for k in range(14):
        day = (today - timedelta(days=k)).isoformat()
        c = _main_call(_day_calls(conn, rid, day))
        if c is None:
            out.append({'date': day, 'time': None, 'minutes': None,
                        'status_label': ELDER_STATUS_LABELS['not_called'] if k == 0 else '전화가 없던 날', 'chips': []})
            continue
        chips = []
        a = json.loads(c['assessment']) if c['assessment'] else None
        if a:
            if a['safety']:
                chips.append({'label': '생활지원사님께 알렸어요', 'tone': 'watch'})
            for t in TOPICS:
                st = a['items'][t]['status']
                if st == 'good':
                    chips.append({'label': CHIPS[t][0], 'tone': 'ok'})
                elif st in ('caution', 'risk'):
                    chips.append({'label': CHIPS[t][1], 'tone': 'watch'})
                elif c['status'] in calls.ANSWERED:   # 답을 못 들은 항목 — '모두 괜찮으셨어요'로 보이지 않게
                    chips.append({'label': UNKNOWN_CHIP[t], 'tone': 'unknown'})
        start = c['started_at'] or c['created_at']
        minutes = None
        if c['started_at'] and c['ended_at']:
            minutes = max(1, round((db.parse(c['ended_at']) - db.parse(c['started_at'])).total_seconds() / 60))
        out.append({'date': day, 'time': db.parse(start).astimezone(db.KST).strftime('%H:%M'), 'minutes': minutes,
                    'status_label': ELDER_STATUS_LABELS[c['status']], 'chips': chips})
    return out


@router.get('/{rid}/incoming')
def incoming(rid: int, conn=Depends(get_conn)):
    calls.get_resident(conn, rid)
    ring = conn.execute("SELECT id, created_at FROM calls WHERE resident_id = ? AND status = 'ringing' "
                        "ORDER BY created_at DESC LIMIT 1", (rid,)).fetchone()
    active = conn.execute("SELECT id FROM calls WHERE resident_id = ? AND status = 'in_progress' "
                          "ORDER BY created_at DESC LIMIT 1", (rid,)).fetchone()
    return {
        'ringing': {'call_id': ring['id'], 'ring_expires_at': db.kst(db.iso(
            db.parse(ring['created_at']) + timedelta(seconds=calls.RING_SECONDS)))} if ring else None,
        'active': {'call_id': active['id']} if active else None,
    }


@router.post('/calls/{cid}/answer')
def answer(cid: int, conn=Depends(get_conn)):
    return calls.answer_call(conn, cid)


@router.post('/calls/{cid}/decline')
def decline(cid: int, conn=Depends(get_conn)):
    return {'status': calls.decline_call(conn, cid)}


def _summary_job(request: Request, llm, cid: int):
    conn = db.connect(request.app.state.settings.db_path)
    try:
        calls.finalize_summary(conn, llm, cid)
    finally:
        conn.close()


@router.post('/calls/{cid}/turn')
def turn(cid: int, body: TurnIn, request: Request, background: BackgroundTasks, conn=Depends(get_conn),
         llm=Depends(get_llm)):
    result, finished = calls.process_turn(conn, llm, cid, body.text, body.source, body.client_turn_id, body.topic)
    if finished:
        background.add_task(_summary_job, request, llm, cid)
    return result


@router.post('/calls/{cid}/hangup')
def hangup(cid: int, request: Request, background: BackgroundTasks, conn=Depends(get_conn), llm=Depends(get_llm)):
    status, needs_summary = calls.hangup_call(conn, cid)
    if needs_summary:
        background.add_task(_summary_job, request, llm, cid)
    return {'status': status}


@router.get('/calls/{cid}')
def call_state(cid: int, conn=Depends(get_conn)):
    """통화 이어 받기용. 마지막으로 보낸 질문을 **그대로** 돌려준다 — 식사 재질문과 그 선택 버튼까지
    (새로고침하면 기본 질문으로 되돌아가던 문제)."""
    c = calls.get_call(conn, cid)
    topic, question, options, last = None, None, [], None
    if c['status'] == 'in_progress':
        topic = dialogue.State(c['step_index']).topic
        question, options = (QUESTIONS[topic], list(OPTIONS[topic])) if topic else (None, [])
        row = conn.execute('SELECT result FROM turns WHERE call_id = ? AND result IS NOT NULL ORDER BY id DESC LIMIT 1',
                           (cid,)).fetchone()
        last = json.loads(row['result']) if row else None
        if last and last.get('topic') == topic and not last.get('finished'):
            question, options = last.get('question') or question, list(last.get('options') or options)
    return {'status': c['status'], 'step': calls.call_step(c), 'question': question, 'topic': topic,
            'options': options, 'last_ai_text': last.get('ai_text') if last else None,
            'turns': calls.turns_of(conn, cid)}
