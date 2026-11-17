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
YESTERDAY = {
    'completed': '어제는 통화 잘 하셨어요', 'interrupted': '어제는 통화가 중간에 끊겼어요',
    'missed': '어제는 전화를 못 받으셨어요', 'declined': '어제는 전화를 쉬셨어요',
}


class TurnIn(BaseModel):
    text: str = Field(default='', max_length=500)
    source: Literal['stt', 'text', 'option', 'silence']
    client_turn_id: str = Field(min_length=1, max_length=100)


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
def residents(conn=Depends(get_conn)):
    return [_brief(r) for r in conn.execute('SELECT id, code, name FROM residents ORDER BY id')]


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
    result, finished = calls.process_turn(conn, llm, cid, body.text, body.source, body.client_turn_id)
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
    c = calls.get_call(conn, cid)
    topic = None
    if c['status'] == 'in_progress':
        topic = dialogue.State(c['step_index']).topic
    return {'status': c['status'], 'step': calls.call_step(c), 'question': QUESTIONS[topic] if topic else None,
            'topic': topic, 'options': list(OPTIONS[topic]) if topic else [], 'turns': calls.turns_of(conn, cid)}
