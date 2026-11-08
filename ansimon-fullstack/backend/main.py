"""ANSIMON local development API. No authentication: NOT safe for public deployment."""
from __future__ import annotations
import os
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

DB_PATH = Path(os.getenv('ANSIMON_DB', str(Path(__file__).resolve().parent / 'ansimon.db'))).resolve()
# Korean service dates do not require an OS IANA timezone database (Windows).
KST = timezone(timedelta(hours=9), name='Asia/Seoul')
logger = logging.getLogger('uvicorn.error')
app = FastAPI(title='안심온 API', version='1.0.0', description='로컬 개발용 규칙 기반 안부 확인 API')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'Idempotency-Key'])

QUESTIONS = [
    ('condition', '안녕하세요. 안심온입니다. 오늘 몸 상태는 어떠세요?'),
    ('meal', '오늘 식사는 잘 챙겨 드셨나요?'),
    ('sleep', '어젯밤 잠은 편히 주무셨나요?'),
    ('medicine', '평소 드시는 약이 있다면 잘 챙겨 드셨나요?'),
    ('mood', '오늘 기분은 어떠세요?'),
]
LABELS = dict(condition='몸 상태', meal='식사', sleep='수면', medicine='복약', mood='기분')

@contextmanager
def db(write=False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        if write:
            conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def init_db():
    # Snapshot an existing DB with SQLite's backup API, including committed WAL data.
    if DB_PATH.exists():
        backup = DB_PATH.with_name(DB_PATH.name + '.backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        with sqlite3.connect(DB_PATH) as source, sqlite3.connect(backup) as target:
            source.backup(target)
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS residents (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL,
          neighborhood TEXT NOT NULL, call_time TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS calls (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          resident_id INTEGER NOT NULL REFERENCES residents(id),
          started_at TEXT NOT NULL, ended_at TEXT,
          status TEXT NOT NULL CHECK(status IN ('in_progress','completed','interrupted','declined')),
          summary TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS turns (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          call_id INTEGER NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
          topic TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        ''')
        for table in ('calls',):
            if 'request_key' not in {row['name'] for row in c.execute(f'PRAGMA table_info({table})')}:
                c.execute(f'ALTER TABLE {table} ADD COLUMN request_key TEXT')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS calls_request_key ON calls(request_key)')
        if c.execute('SELECT COUNT(*) FROM residents').fetchone()[0] == 0:
            c.executemany('INSERT INTO residents(id,name,age,neighborhood,call_time) VALUES(?,?,?,?,?)', [
                (1,'김영자',78,'중구 은행동','10:00'),(2,'이순희',82,'서구 둔산동','10:30'),(3,'박정호',75,'유성구 봉명동','11:00'),(4,'최복순',80,'동구 가양동','11:20')
            ])

init_db()

@app.exception_handler(sqlite3.Error)
async def database_error(request: Request, exc: sqlite3.Error):
    logger.error('SQLite failure at %s: %s', request.url.path, exc, exc_info=True)
    message = '데이터베이스 처리 오류입니다. 백엔드 로그에서 테이블 구조와 DB 경로·쓰기 권한을 확인하세요.'
    if 'locked' in str(exc).lower():
        message = '데이터베이스가 사용 중입니다. 잠시 후 다시 시도하세요.'
    return JSONResponse(status_code=500, content={'detail': message})

class TurnInput(BaseModel):
    answer: str = Field(min_length=1, max_length=500)
    index: int | None = Field(default=None, ge=0, lt=len(QUESTIONS))

class FinishInput(BaseModel):
    status: Literal['completed', 'interrupted']

def resident_exists(c, resident_id):
    return c.execute('SELECT 1 FROM residents WHERE id=?', (resident_id,)).fetchone() is not None

def fetch_call(c, call_id):
    row = c.execute('SELECT * FROM calls WHERE id=?', (call_id,)).fetchone()
    if not row:
        raise HTTPException(404, '통화 기록을 찾을 수 없습니다.')
    return row

def fetch_turns(c, call_id):
    return [dict(row) for row in c.execute('SELECT id,topic,question,answer,created_at FROM turns WHERE call_id=? ORDER BY id', (call_id,))]

def response_for(topic: str, answer: str) -> str:
    text = answer.replace(' ', '')
    if any(word in text for word in ['못먹', '안먹', '못잤', '아파', '힘들', '외로', '우울']):
        return '말씀해 주셔서 감사합니다. 필요한 도움이 있다면 담당 생활지원사에게 꼭 알려주세요.'
    if topic == 'meal':
        return '식사에 대해 알려주셔서 감사합니다.'
    if topic == 'sleep':
        return '잠은 충분히 주무시는 게 중요하지요. 알려주셔서 감사합니다.'
    return '네, 말씀 잘 들었습니다.'

def summarize(turns):
    if not turns:
        return '답변 없이 통화가 종료되었습니다.'
    return ' / '.join(f"{LABELS.get(t['topic'],t['topic'])}: {t['answer']}" for t in turns)

@app.get('/api/health')
def health():
    return {'ok': True, 'mode': 'local-rule-based'}

@app.get('/api/questions')
def questions():
    return [{'topic': k, 'text': v} for k, v in QUESTIONS]

@app.get('/api/residents')
def residents():
    with db() as c:
        return [dict(r) for r in c.execute('SELECT * FROM residents ORDER BY id')]

@app.post('/api/residents/{resident_id}/calls', status_code=201)
def start_call(resident_id: int, request_key: str | None = Header(default=None, alias='Idempotency-Key', max_length=128)):
    with db(write=True) as c:
        if request_key:
            existing = c.execute('SELECT * FROM calls WHERE request_key=?', (request_key,)).fetchone()
            if existing:
                if existing['resident_id'] != resident_id or existing['status'] == 'declined':
                    raise HTTPException(409, '다른 요청에 사용된 중복 방지 키입니다.')
                return {'id':existing['id'], 'resident_id':resident_id, 'status':existing['status'], 'question':QUESTIONS[0][1], 'topic':QUESTIONS[0][0]}
        if not resident_exists(c, resident_id):
            raise HTTPException(404, '어르신을 찾을 수 없습니다.')
        ongoing = c.execute("SELECT id FROM calls WHERE resident_id=? AND status='in_progress'", (resident_id,)).fetchone()
        if ongoing:
            raise HTTPException(409, '이미 진행 중인 통화가 있습니다. 해당 통화를 먼저 종료해 주세요.')
        cur = c.execute("INSERT INTO calls(resident_id,started_at,status,request_key) VALUES(?,?,'in_progress',?)", (resident_id, now(), request_key))
        return {'id': cur.lastrowid, 'resident_id': resident_id, 'status':'in_progress', 'question':QUESTIONS[0][1], 'topic':QUESTIONS[0][0]}

@app.post('/api/residents/{resident_id}/decline', status_code=201)
def decline_call(resident_id: int, request_key: str | None = Header(default=None, alias='Idempotency-Key', max_length=128)):
    with db(write=True) as c:
        if request_key:
            existing = c.execute('SELECT * FROM calls WHERE request_key=?', (request_key,)).fetchone()
            if existing:
                if existing['resident_id'] != resident_id or existing['status'] != 'declined':
                    raise HTTPException(409, '다른 요청에 사용된 중복 방지 키입니다.')
                return {'id':existing['id'], 'status':'declined'}
        if not resident_exists(c, resident_id):
            raise HTTPException(404, '어르신을 찾을 수 없습니다.')
        current = now()
        cur = c.execute("INSERT INTO calls(resident_id,started_at,ended_at,status,summary,request_key) VALUES(?,?,?,'declined',?,?)", (resident_id,current,current,'수신 거절',request_key))
        return {'id':cur.lastrowid,'status':'declined'}

@app.post('/api/calls/{call_id}/turns', status_code=201)
def add_turn(call_id: int, body: TurnInput):
    answer = body.answer.strip()
    if not answer:
        raise HTTPException(422, '빈 답변은 저장할 수 없습니다.')
    with db(write=True) as c:
        call = fetch_call(c, call_id)
        turns = fetch_turns(c, call_id)
        if body.index is not None and body.index < len(turns):
            old = turns[body.index]
            if old['answer'] != answer:
                raise HTTPException(409, '이미 저장된 질문입니다. 통화 상태를 새로 불러오세요.')
            return turn_result(body.index, answer)
        if body.index is not None and body.index != len(turns):
            raise HTTPException(409, '질문 순서가 다릅니다. 통화 상태를 새로 불러오세요.')
        if call['status'] != 'in_progress':
            raise HTTPException(409, '종료된 통화입니다.')
        index = c.execute('SELECT COUNT(*) FROM turns WHERE call_id=?', (call_id,)).fetchone()[0]
        if index >= len(QUESTIONS):
            raise HTTPException(409, '모든 질문이 완료되었습니다.')
        topic, question = QUESTIONS[index]
        c.execute('INSERT INTO turns(call_id,topic,question,answer,created_at) VALUES(?,?,?,?,?)', (call_id,topic,question,answer,now()))
        return turn_result(index, answer)

def turn_result(index, answer):
    next_index = index + 1
    return {'count':next_index, 'reply':response_for(QUESTIONS[index][0], answer),
            'finished':next_index == len(QUESTIONS),
            'next_question':QUESTIONS[next_index][1] if next_index < len(QUESTIONS) else None}

@app.post('/api/calls/{call_id}/finish')
def finish_call(call_id: int, body: FinishInput):
    with db(write=True) as c:
        call = fetch_call(c, call_id)
        if call['status'] != 'in_progress':
            if call['status'] == body.status:
                return {'id':call_id, 'status':call['status'], 'summary':call['summary'], 'answered':len(fetch_turns(c, call_id))}
            raise HTTPException(409,'이미 다른 상태로 종료된 통화입니다.')
        turns = fetch_turns(c,call_id)
        if body.status == 'completed' and len(turns) != len(QUESTIONS):
            raise HTTPException(422,'5개 질문에 모두 답해야 완료 처리할 수 있습니다.')
        summary = summarize(turns)
        c.execute('UPDATE calls SET ended_at=?,status=?,summary=? WHERE id=?',(now(),body.status,summary,call_id))
        return {'id':call_id,'status':body.status,'summary':summary,'answered':len(turns)}

@app.get('/api/calls')
def calls(limit: int = 100, resident_id: int | None = None):
    limit = min(max(limit,1),500)
    with db() as c:
        if resident_id is None:
            rows = c.execute('''SELECT calls.*,residents.name as resident_name FROM calls JOIN residents ON residents.id=calls.resident_id ORDER BY calls.id DESC LIMIT ?''',(limit,)).fetchall()
        else:
            rows = c.execute('''SELECT calls.*,residents.name as resident_name FROM calls JOIN residents ON residents.id=calls.resident_id WHERE resident_id=? ORDER BY calls.id DESC LIMIT ?''',(resident_id,limit)).fetchall()
        return [dict(row) for row in rows]

@app.get('/api/calls/{call_id}')
def call_detail(call_id: int):
    with db() as c:
        row = fetch_call(c, call_id)
        return {**dict(row),'turns':fetch_turns(c,call_id)}

@app.get('/api/dashboard')
def dashboard():
    today = datetime.now(KST).date().isoformat()
    with db() as c:
        residents_data = [dict(row) for row in c.execute('SELECT * FROM residents ORDER BY id')]
        recent = [dict(row) for row in c.execute('SELECT * FROM calls ORDER BY id DESC')]
    latest = {}
    for call in recent:
        date = datetime.fromisoformat(call['started_at']).astimezone(KST).date().isoformat()
        if date == today and call['resident_id'] not in latest:
            latest[call['resident_id']] = call
    for r in residents_data:
        last = latest.get(r['id'])
        r['status'] = last['status'] if last else 'pending'
        r['last_summary'] = last['summary'] if last else ''
        r['last_call_id'] = last['id'] if last else None
    return {'date':today,'total':len(residents_data), 'completed':sum(r['status']=='completed' for r in residents_data),
            'pending':sum(r['status']=='pending' for r in residents_data),
            'interrupted':sum(r['status']=='interrupted' for r in residents_data),
            'declined':sum(r['status']=='declined' for r in residents_data),
            'in_progress':sum(r['status']=='in_progress' for r in residents_data),
            'residents':residents_data}
