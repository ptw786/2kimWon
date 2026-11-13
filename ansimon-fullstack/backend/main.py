"""ANSIMON local development API. No authentication: NOT safe for public deployment."""
from __future__ import annotations
import os
import logging
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from fastapi.responses import JSONResponse
from schema_migrations import migrate
from priority import assessment_for
from integration import register, imported_rows
from dialogue_manager import transition
from conversation import QUESTIONS, LABELS, CLASS_LABELS, MAX_REASKS, assess, summary_for

DB_PATH = Path(os.getenv('ANSIMON_DB', str(Path(__file__).resolve().parent / 'ansimon.db'))).resolve()
# Korean service dates do not require an OS IANA timezone database (Windows).
KST = timezone(timedelta(hours=9), name='Asia/Seoul')
logger = logging.getLogger('uvicorn.error')
app = FastAPI(title='안심온 API', version='1.0.0', description='로컬 개발용 규칙 기반 안부 확인 API')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'Idempotency-Key'])

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
        turn_columns = {row['name'] for row in c.execute('PRAGMA table_info(turns)')}
        for name, definition in [('classification', "TEXT NOT NULL DEFAULT 'unclassified'"),
                                 ('reply', "TEXT NOT NULL DEFAULT ''"), ('emergency', 'INTEGER NOT NULL DEFAULT 0')]:
            if name not in turn_columns:
                c.execute(f'ALTER TABLE turns ADD COLUMN {name} {definition}')
        c.execute('''CREATE TABLE IF NOT EXISTS turn_attempts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          call_id INTEGER NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
          question_index INTEGER NOT NULL, attempt INTEGER NOT NULL,
          request_key TEXT, question TEXT NOT NULL, answer TEXT NOT NULL,
          classification TEXT NOT NULL, reply TEXT NOT NULL,
          emergency INTEGER NOT NULL DEFAULT 0, result_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(call_id,question_index,attempt), UNIQUE(call_id,request_key)
        )''')
        if c.execute('SELECT COUNT(*) FROM residents').fetchone()[0] == 0:
            c.executemany('INSERT INTO residents(id,name,age,neighborhood,call_time) VALUES(?,?,?,?,?)', [
                (1,'김영자',78,'중구 은행동','10:00'),(2,'이순희',82,'서구 둔산동','10:30'),(3,'박정호',75,'유성구 봉명동','11:00'),(4,'최복순',80,'동구 가양동','11:20')
            ])

        c.execute('CREATE TABLE IF NOT EXISTS hybrid_state (call_id INTEGER PRIMARY KEY REFERENCES calls(id), state_json TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS hybrid_events (id INTEGER PRIMARY KEY, call_id INTEGER NOT NULL REFERENCES calls(id), analysis_json TEXT NOT NULL, created_at TEXT NOT NULL)')
        migrate(c)

init_db()
register(app, db)

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
    attempt: int | None = Field(default=None, ge=0, le=10000)
    engine: Literal["legacy", "hybrid"] = "legacy"
    source: Literal["text", "stt", "stt_error", "silence"] = "text"

class StartInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

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
    return [dict(row) for row in c.execute('SELECT id,topic,question,answer,classification,reply,emergency,created_at FROM turns WHERE call_id=? ORDER BY id', (call_id,))]

def fetch_attempts(c, call_id):
    return [dict(row) for row in c.execute('SELECT id,question_index,attempt,question,answer,classification,reply,emergency,created_at FROM turn_attempts WHERE call_id=? ORDER BY id', (call_id,))]

def dialogue_state(c, call_id):
    saved = c.execute('SELECT state_json FROM hybrid_state WHERE call_id=?',(call_id,)).fetchone()
    if saved:
        return json.loads(saved[0])
    count = c.execute('SELECT COUNT(*) FROM turns WHERE call_id=?', (call_id,)).fetchone()[0]
    attempts = c.execute('SELECT COUNT(*) FROM turn_attempts WHERE call_id=? AND question_index=?', (call_id,count)).fetchone()[0]
    return {'count':count, 'index':count, 'attempt':min(attempts,MAX_REASKS),
            'retry_count':min(attempts,MAX_REASKS), 'finished':count >= len(QUESTIONS),
            'question':QUESTIONS[count][1] if count < len(QUESTIONS) else None}

@app.get('/api/health')
def health():
    # Process liveness alone is not readiness: a missing/wrong DB would make
    # dashboard and call writes fail even though the original health was 200.
    if not DB_PATH.is_file():
        logger.error('Health check: database file missing at %s', DB_PATH)
        raise HTTPException(503, '데이터베이스 파일을 찾을 수 없습니다. ANSIMON_DB 경로와 기존 DB 보존 상태를 확인하세요.')
    try:
        with db() as c:
            for query in (
                'SELECT origin_key,payload_json FROM imported_records LIMIT 0',
                'SELECT call_id,state_json FROM hybrid_state LIMIT 0',
                'SELECT call_id,analysis_json,created_at FROM hybrid_events LIMIT 0',
                'SELECT id,name,age,neighborhood,call_time FROM residents LIMIT 0',
                'SELECT id,resident_id,started_at,ended_at,status,summary,request_key,recipient,scheduled_at FROM calls LIMIT 0',
                'SELECT id,call_id,topic,question,answer,classification,reply,emergency,created_at FROM turns LIMIT 0',
                'SELECT id,call_id,question_index,attempt,request_key,question,answer,classification,reply,emergency,result_json,created_at FROM turn_attempts LIMIT 0',
            ):
                c.execute(query)
    except sqlite3.Error as exc:
        logger.error('Health check: database not ready at %s: %s', DB_PATH, exc, exc_info=True)
        raise HTTPException(503, '데이터베이스에 연결하거나 필요한 테이블을 확인하지 못했습니다. 백엔드 로그·DB 경로·권한을 확인하세요.') from exc
    return {'ok': True, 'mode': 'local-rule-based'}

@app.get('/api/questions')
def questions():
    return [{'topic': k, 'text': v} for k, v in QUESTIONS]

@app.get('/api/residents')
def residents():
    with db() as c:
        return [dict(r) for r in c.execute('SELECT * FROM residents ORDER BY id')]

@app.post('/api/residents/{resident_id}/calls', status_code=201)
def start_call(resident_id: int, body: StartInput | None = None, request_key: str | None = Header(default=None, alias='Idempotency-Key', max_length=128)):
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
def decline_call(resident_id: int, body: StartInput | None = None, request_key: str | None = Header(default=None, alias='Idempotency-Key', max_length=128)):
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
def add_turn(call_id: int, body: TurnInput, request_key: str | None = Header(default=None, alias='Idempotency-Key', max_length=128)):
    answer = body.answer.strip()
    if not answer:
        raise HTTPException(422, '빈 답변은 저장할 수 없습니다.')
    with db(write=True) as c:
        call = fetch_call(c, call_id)
        state = dialogue_state(c, call_id)
        index = body.index if body.index is not None else state['index']
        attempt = body.attempt if body.attempt is not None else (state['attempt'] if index == state['index'] else 0)
        old = c.execute('SELECT * FROM turn_attempts WHERE call_id=? AND question_index=? AND attempt=?', (call_id,index,attempt)).fetchone()
        if request_key:
            keyed = c.execute('SELECT * FROM turn_attempts WHERE call_id=? AND request_key=?', (call_id,request_key)).fetchone()
            if keyed and (keyed['question_index'] != index or keyed['attempt'] != attempt):
                raise HTTPException(409, '다른 답변에 사용된 중복 방지 키입니다.')
        if old:
            if old['answer'] != answer:
                raise HTTPException(409, '이미 저장된 답변 순번입니다. 통화 상태를 새로 불러오세요.')
            return json.loads(old['result_json'])
        if call['status'] != 'in_progress':
            raise HTTPException(409, '종료된 통화입니다.')
        if index != state['index'] or attempt != state['attempt']:
            raise HTTPException(409, '질문 또는 재질문 순서가 다릅니다. 통화 상태를 새로 불러오세요.')
        if index >= len(QUESTIONS):
            raise HTTPException(409, '모든 질문이 완료되었습니다.')
        topic, question = QUESTIONS[index]
        question = state.get('question') or state.get('last_ai') or question
        if body.engine == 'hybrid' or c.execute('SELECT 1 FROM hybrid_state WHERE call_id=?',(call_id,)).fetchone():
            if 'facts' not in state:
                previous=fetch_turns(c,call_id)
                state['facts']={t['topic']:{'classification':t['classification'],'evidence':t['answer']} for t in previous if t['classification'] in ('positive','negative','neutral')}
                state['completed']=[t['topic'] for t in previous]
                state['unconfirmed']=[t['topic'] for t in previous if t['classification'] not in ('positive','negative','neutral')]
            state, analysis = transition(state, answer, body.source)
            result = {**analysis, 'count':state['count'], 'question_index':index, 'attempt':attempt,
                      'classification_label':CLASS_LABELS[analysis['classification']],
                      'needs_retry':state['index']==index, 'retry_count':state['checks'],
                      'next_attempt':state['attempt'], 'finished':state['finished'],
                      'next_question':state['question'], 'dialogue_state':state}
            c.execute('INSERT INTO turn_attempts(call_id,question_index,attempt,request_key,question,answer,classification,reply,emergency,result_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                      (call_id,index,attempt,request_key,question,answer,analysis['classification'],analysis['reply'],int(analysis['emergency']),json.dumps(result,ensure_ascii=False),now()))
            c.execute('INSERT INTO hybrid_state VALUES(?,?) ON CONFLICT(call_id) DO UPDATE SET state_json=excluded.state_json',(call_id,json.dumps(state,ensure_ascii=False)))
            c.execute('INSERT INTO hybrid_events(call_id,analysis_json,created_at) VALUES(?,?,?)',(call_id,json.dumps({'raw':answer,**analysis},ensure_ascii=False),now()))
            if state['index']!=index:
                c.execute('INSERT INTO turns(call_id,topic,question,answer,classification,reply,emergency,created_at) VALUES(?,?,?,?,?,?,?,?)',
                          (call_id,topic,question,answer,analysis['classification'],analysis['reply'],int(analysis['emergency']),now()))
            return result
        assessment = assess(topic, answer)
        needs_retry = assessment.classification == 'unknown' and attempt < MAX_REASKS
        reply = assessment.reply if assessment.classification != 'unknown' or needs_retry else '답변을 확인하기 어려워 이 항목은 확인 불가로 기록할게요.'
        count = index if needs_retry else index + 1
        result = {'count':count, 'question_index':index, 'attempt':attempt,
                  'classification':assessment.classification,
                  'classification_label':CLASS_LABELS[assessment.classification],
                  'reply':reply, 'emergency':assessment.emergency,
                  'needs_retry':needs_retry, 'retry_count':min(attempt+1,MAX_REASKS) if needs_retry else attempt,
                  'next_attempt':attempt+1 if needs_retry else 0,
                  'finished':count == len(QUESTIONS),
                  'next_question':QUESTIONS[count][1] if count < len(QUESTIONS) else None}
        # Both attempts and final answers commit atomically before the response.
        c.execute('INSERT INTO turn_attempts(call_id,question_index,attempt,request_key,question,answer,classification,reply,emergency,result_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                  (call_id,index,attempt,request_key,question,answer,assessment.classification,reply,int(assessment.emergency),json.dumps(result,ensure_ascii=False),now()))
        if not needs_retry:
            c.execute('INSERT INTO turns(call_id,topic,question,answer,classification,reply,emergency,created_at) VALUES(?,?,?,?,?,?,?,?)',
                      (call_id,topic,question,answer,assessment.classification,reply,int(assessment.emergency),now()))
        return result

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
        summary = summary_for(turns)
        saved=c.execute('SELECT state_json FROM hybrid_state WHERE call_id=?',(call_id,)).fetchone()
        if saved:
            state=json.loads(saved[0])
            summary=' / '.join(LABELS[k]+': '+v['evidence'] for k,v in state.get('facts',{}).items()) or '확인된 답변 없음'
            missing=[LABELS[k] for k,_ in QUESTIONS if k not in state.get('facts',{})]
            if missing: summary+=' / 확인되지 않음: '+', '.join(missing)
            if state.get('safety_paused'):summary+=' / 위험 표현: 직접 119 연락 안내, 자동 신고 없음'
        c.execute('UPDATE calls SET ended_at=?,status=?,summary=? WHERE id=?',(now(),body.status,summary,call_id))
        return {'id':call_id,'status':body.status,'summary':summary,'answered':len(turns)}

def enrich(c,row):
    return {**row,'assessment':assessment_for(c,row),'source':'minse'}

@app.get('/api/calls')
def calls(limit: int = 100, resident_id: int | None = None, sort: Literal['latest','priority'] = 'latest'):
    limit = min(max(limit,1),500)
    with db() as c:
        if resident_id is None:
            rows = c.execute('''SELECT calls.*,residents.name as resident_name FROM calls JOIN residents ON residents.id=calls.resident_id ORDER BY calls.id DESC''').fetchall()
        else:
            rows = c.execute('''SELECT calls.*,residents.name as resident_name FROM calls JOIN residents ON residents.id=calls.resident_id WHERE resident_id=? ORDER BY calls.id DESC''',(resident_id,)).fetchall()
        result=[enrich(c,dict(row)) for row in rows]
        if resident_id is None:result+=imported_rows(c)
        result.sort(key=lambda r:(r['assessment']['score'] if r['assessment']['score'] is not None else -1, datetime.fromisoformat(r['started_at']).timestamp()) if sort=='priority' else datetime.fromisoformat(r['started_at']).timestamp(),reverse=True)
        return result[:limit]

@app.get('/api/calls/{call_id}')
def call_detail(call_id: int):
    with db() as c:
        row = fetch_call(c, call_id)
        return {**enrich(c,dict(row)),'turns':fetch_turns(c,call_id), 'attempts':fetch_attempts(c,call_id), 'dialogue_state':dialogue_state(c,call_id), 'analysis_events':[json.loads(r[0]) for r in c.execute('SELECT analysis_json FROM hybrid_events WHERE call_id=? ORDER BY id',(call_id,))]}

@app.get('/api/dashboard')
def dashboard():
    today = datetime.now(KST).date().isoformat()
    with db() as c:
        residents_data = [dict(row) for row in c.execute('SELECT * FROM residents ORDER BY id')]
        recent = [enrich(c,dict(row)) for row in c.execute('SELECT * FROM calls ORDER BY id DESC')]
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
        r['assessment'] = last['assessment'] if last else None
    return {'date':today,'total':len(residents_data), 'completed':sum(r['status']=='completed' for r in residents_data),
            'pending':sum(r['status']=='pending' for r in residents_data),
            'interrupted':sum(r['status']=='interrupted' for r in residents_data),
            'declined':sum(r['status']=='declined' for r in residents_data),
            'in_progress':sum(r['status']=='in_progress' for r in residents_data),
            'residents':residents_data}
