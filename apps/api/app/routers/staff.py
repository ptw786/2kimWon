"""생활지원사 웹용 (/api/staff)."""
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, StringConstraints

from .. import calls, db
from ..auth import check_login
from ..domain.questions import CALL_STATUS_LABELS, TOPICS
from ..seed import region_for, seed
from ..services import welfare
from .deps import get_conn

router = APIRouter(tags=['staff'])          # main.py 에서 require_staff 를 건다
public = APIRouter(tags=['staff'])          # 로그인 전에 부를 수 있는 것


class LoginIn(BaseModel):
    pin: str = Field(min_length=1, max_length=40)


@public.post('/login')
def login(body: LoginIn, request: Request):
    return {'token': check_login(request, body.pin), 'required': request.app.state.staff_pin is not None}

GRADE_ORDER = {'urgent': 0, 'today': 1, 'watch': 2, 'ok': 3}
CALL_TIME = r'^([01]\d|2[0-3]):[0-5]\d$'


def _text(n: int):   # 앞뒤 공백을 지운 뒤 길이를 본다 ('   ' 이름이 빈 이름으로 저장되지 않게)
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=n)]


class ResidentIn(BaseModel):
    name: _text(20)
    age: int = Field(ge=0, le=130)
    region: str | None = Field(default=None, max_length=40)   # 없으면 동네 이름으로 채움 ('중구 은행동' → '대전광역시 중구')
    neighborhood: _text(40)
    call_time: str = Field(pattern=CALL_TIME)
    memo: str | None = Field(default=None, max_length=300)


class ResidentPatch(BaseModel):
    name: _text(20) | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    region: _text(40) | None = None
    neighborhood: _text(40) | None = None
    call_time: str | None = Field(default=None, pattern=CALL_TIME)
    memo: str | None = Field(default=None, max_length=300)


class CheckIn(BaseModel):
    note: str = Field(default='', max_length=300)


def _calls_of_day(conn, rid: int, day: str):
    return conn.execute('SELECT c.*, r.name AS resident_name FROM calls c JOIN residents r ON r.id = c.resident_id '
                        'WHERE c.resident_id = ? AND c.kst_date = ? ORDER BY c.created_at DESC, c.id DESC',
                        (rid, day)).fetchall()


def _representative(day_calls):
    """그날을 대표하는 (통화, 판정). 최근 통화가 아니라 **가장 심한** 판정을 고른다 —
    안전 신호가 나온 뒤 다시 건 전화를 거절해도 '즉시 확인'이 목록에서 내려가지 않게 (판정규칙.md §5).
    같은 단계면 확인 기록이 없는 통화 → 점수 높은 통화 → 최근 통화. 통화 중 안전 신호(provisional)도 포함한다."""
    best = None
    for c in day_calls:   # 최근 것부터
        a = calls.assessment_out(c['assessment'])
        if a is None or (c['status'] not in calls.FINISHED and not a['provisional']):
            continue
        key = (GRADE_ORDER[a['grade']], 1 if c['staff_check_at'] else 0, -a['score'])
        if best is None or key < best[0]:
            best = (key, c, a)
    return (best[1], best[2]) if best else (None, None)


@router.get('/dashboard')
def dashboard(conn=Depends(get_conn)):
    today = db.kst_today().isoformat()
    rows = []
    for r in conn.execute('SELECT * FROM residents ORDER BY id').fetchall():
        day_calls = _calls_of_day(conn, r['id'], today)
        latest = day_calls[0] if day_calls else None
        status = latest['status'] if latest else 'not_called'
        rep, a = _representative(day_calls)
        rows.append({
            **calls.resident_out(r),
            'today': {'call_id': latest['id'] if latest else None, 'status': status,
                      'status_label': CALL_STATUS_LABELS[status], 'calls': len(day_calls)},
            'assessment': a,
            'assessment_call_id': rep['id'] if rep else None,
            # 확인 기록은 대표 판정을 만든 그 통화의 것만 — 예전 통화를 확인했다고 새 판정까지 확인한 것처럼 보이지 않게
            'staff_check': calls.staff_check_of(rep) if rep else None,
        })
    rows.sort(key=lambda x: (GRADE_ORDER[x['assessment']['grade']] if x['assessment'] else 4,
                             1 if x['staff_check'] else 0,
                             -(x['assessment']['score'] if x['assessment'] else 0), x['id']))
    counts = {'total': len(rows), 'urgent': 0, 'today': 0, 'watch': 0, 'ok': 0, 'missed': 0, 'not_called': 0}
    for x in rows:
        if x['assessment']:
            counts[x['assessment']['grade']] += 1
        if x['today']['status'] in ('missed', 'not_called'):
            counts[x['today']['status']] += 1
    return {'date': today, 'counts': counts, 'residents': rows}


@router.get('/alerts')
def alerts(conn=Depends(get_conn)):
    """오늘 나온 안전 신호 중 생활지원사가 아직 확인하지 않은 것 (통화 중인 것 포함). 웹이 몇 초마다 확인해 알림을 띄운다."""
    today = db.kst_today().isoformat()
    out = []
    for row in conn.execute(
            'SELECT s.id, s.call_id, s.category, s.quote, s.at, c.resident_id, c.status, r.name, r.code '
            'FROM safety_signals s JOIN calls c ON c.id = s.call_id JOIN residents r ON r.id = c.resident_id '
            'WHERE c.kst_date = ? AND (c.staff_check_at IS NULL OR s.at > c.staff_check_at) ORDER BY s.id DESC', (today,)):
        out.append({'id': row['id'], 'call_id': row['call_id'], 'resident_id': row['resident_id'],
                    'resident_name': row['name'], 'code': row['code'], 'category': row['category'],
                    'quote': row['quote'], 'at': db.kst(row['at']), 'live': row['status'] in calls.ACTIVE})
    return {'alerts': out}


def _day(conn, rid: int, day: str) -> dict:
    day_calls = _calls_of_day(conn, rid, day)
    merged = calls.day_items(conn, rid, day)
    _rep, a = _representative(day_calls)
    return {
        'date': day,
        'call_status': day_calls[0]['status'] if day_calls else 'not_called',
        'items': {t: merged[t]['status'] for t in TOPICS} if merged else None,
        'grade': a['grade'] if a else None,
        'score': a['score'] if a else None,
    }


@router.get('/residents/{rid}')
def resident_detail(rid: int, conn=Depends(get_conn)):
    r = calls.get_resident(conn, rid)
    today = db.kst_today()
    week = [_day(conn, rid, (today - timedelta(days=k)).isoformat()) for k in range(6, -1, -1)]
    rows = conn.execute('SELECT c.*, r.name AS resident_name FROM calls c JOIN residents r ON r.id = c.resident_id '
                        'WHERE c.resident_id = ? ORDER BY c.created_at DESC, c.id DESC LIMIT 30', (rid,)).fetchall()
    needs = calls.recent_needs(conn, rid, (today - timedelta(days=6)).isoformat())
    return {'resident': calls.resident_out(r), 'week': week, 'calls': [calls.call_summary(c) for c in rows],
            'welfare': welfare.matches(needs, r['region'], age=r['age'])}


@router.post('/residents', status_code=201)
def create_resident(body: ResidentIn, conn=Depends(get_conn)):
    with db.tx(conn):
        codes = [row['code'] for row in conn.execute("SELECT code FROM residents WHERE code LIKE 'KY-%'")]
        nums = [int(c[3:]) for c in codes if c[3:].isdigit()]
        code = f'KY-{(max(nums) if nums else 0) + 1:02d}'
        rid = conn.execute(
            'INSERT INTO residents (code, name, age, region, neighborhood, call_time, memo, is_virtual, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)',
            (code, body.name.strip(), body.age, (body.region or '').strip() or region_for(body.neighborhood),
             body.neighborhood.strip(), body.call_time, body.memo, db.now_iso())).lastrowid
    return calls.resident_out(calls.get_resident(conn, rid))


@router.patch('/residents/{rid}')
def update_resident(rid: int, body: ResidentPatch, conn=Depends(get_conn)):
    calls.get_resident(conn, rid)
    fields = body.model_dump(exclude_unset=True)
    for k in ('name', 'age', 'region', 'neighborhood', 'call_time'):
        if k in fields and fields[k] is None:
            raise HTTPException(422, '입력값을 확인해 주세요: 빈 값은 넣을 수 없어요.')
    if fields:
        with db.tx(conn):
            sets = ', '.join(f'{k} = ?' for k in fields)
            conn.execute(f'UPDATE residents SET {sets} WHERE id = ?', (*fields.values(), rid))
    return calls.resident_out(calls.get_resident(conn, rid))


@router.post('/residents/{rid}/call', status_code=201)
def start_call(rid: int, conn=Depends(get_conn)):
    cid = calls.create_call(conn, rid, origin='staff')
    return calls.call_summary(calls.get_call(conn, cid))


@router.get('/calls')
def list_calls(date: str | None = Query(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$'),
               resident_id: int | None = None, limit: int = Query(default=50, ge=1, le=200),
               offset: int = Query(default=0, ge=0),
               grade: Literal['urgent', 'today', 'watch', 'ok', 'none'] | None = None,
               conn=Depends(get_conn)):
    where, args = [], []
    if date:
        where.append('c.kst_date = ?')
        args.append(date)
    if resident_id is not None:
        where.append('c.resident_id = ?')
        args.append(resident_id)
    if grade == 'none':
        where.append('c.assessment IS NULL')
    elif grade is not None:
        where.append("json_extract(c.assessment, '$.grade') = ?")
        args.append(grade)
    sql = ('SELECT c.*, r.name AS resident_name FROM calls c JOIN residents r ON r.id = c.resident_id'
           + (' WHERE ' + ' AND '.join(where) if where else '') + ' ORDER BY c.created_at DESC, c.id DESC LIMIT ? OFFSET ?')
    return [calls.call_summary(c) for c in conn.execute(sql, (*args, limit, offset)).fetchall()]


@router.get('/calls/{cid}')
def call_detail(cid: int, conn=Depends(get_conn)):
    c = calls.get_call(conn, cid)
    region = conn.execute('SELECT region, age FROM residents WHERE id = ?', (c['resident_id'],)).fetchone()
    return {**calls.call_summary(c), 'turns': calls.turns_of(conn, cid), 'ai_runs': calls.ai_runs_of(conn, cid),
            'staff_check': calls.staff_check_of(c), 'step': calls.call_step(c),
            'welfare': welfare.matches(calls.call_needs(conn, cid), region['region'], age=region['age'])}


@router.get('/live')
def live(conn=Depends(get_conn)):
    rows = conn.execute("SELECT c.*, r.name AS resident_name FROM calls c JOIN residents r ON r.id = c.resident_id "
                        "WHERE c.status IN ('ringing', 'in_progress') ORDER BY c.created_at DESC").fetchall()
    return {'calls': [{**calls.call_summary(c), 'step': calls.call_step(c)} for c in rows]}


@router.post('/demo/reset')
def demo_reset(request: Request, conn=Depends(get_conn)):
    settings = request.app.state.settings
    if not settings.demo:
        raise HTTPException(403, '시연 모드(ANSIMON_DEMO=1)에서만 되돌릴 수 있어요.')
    with db.tx(conn):
        db.wipe(conn)
        seed(conn, model_name=settings.model)
    return {'ok': True}


@router.post('/calls/{cid}/check')
def staff_check(cid: int, body: CheckIn, conn=Depends(get_conn)):
    calls.get_call(conn, cid)
    at = db.now_iso()
    with db.tx(conn):
        conn.execute('UPDATE calls SET staff_check_note = ?, staff_check_at = ? WHERE id = ?', (body.note, at, cid))
    return {'checked': True, 'note': body.note, 'at': db.kst(at)}


@router.get('/public-data')
def public_data():
    return welfare.public_data_overview()
