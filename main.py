"""ANSIMON local development API. No authentication: NOT safe for public deployment."""
from __future__ import annotations
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('ANSIMON_DB', str(APP_DIR / 'ansimon.db')))
app = FastAPI(title='안심온 API', version='1.0.0', description='로컬 개발용 규칙 기반 안부 확인 API')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

QUESTIONS = [
    ('condition', '안녕하세요. 안심온입니다. 오늘 몸 상태는 어떠세요?'),
    ('meal', '오늘 식사는 잘 챙겨 드셨나요?'),
    ('sleep', '어젯밤 잠은 편히 주무셨나요?'),
    ('medicine', '평소 드시는 약이 있다면 잘 챙겨 드셨나요?'),
    ('mood', '오늘 기분은 어떠세요?'),
]
LABELS = dict(condition='몸 상태', meal='식사', sleep='수면', medicine='복약', mood='기분')

@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def init_db():
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
        if c.execute('SELECT COUNT(*) FROM residents').fetchone()[0] == 0:
            c.executemany('INSERT INTO residents(id,name,age,neighborhood,call_time) VALUES(?,?,?,?,?)', [
                (1,'김영자',78,'중구 은행동','10:00'),(2,'이순희',82,'서구 둔산동','10:30'),(3,'박정호',75,'유성구 봉명동','11:00'),(4,'최복순',80,'동구 가양동','11:20')
            ])

init_db()

class TurnInput(BaseModel):
    answer: str = Field(min_length=1, max_length=500)

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


RULES_VERSION = '1'
UNKNOWN = 'unconfirmed'
ANSWER_LABELS = {
    'ate': '식사함', 'not_eaten': '미식사', 'meal_difficulty': '식사 어려움',
    'slept_well': '수면 어려움 없음', 'sleep_difficulty': '수면 어려움',
    UNKNOWN: '미확인',
}
REVIEW_LABELS = {
    'immediate': '즉시 확인', 'follow_up': '추가 확인', 'routine': '일반 기록',
    'pending': '통화 진행 중',
}
# Match explicit phrases in the answer to the corresponding question.
MEAL_RULES = (
    ('meal_difficulty', r'입맛이?없|먹을게없|먹을게하나도없|먹을것이없|삼키기(?:가)?힘들|식사하기(?:가)?어렵|먹기(?:가)?어렵'),
    ('not_eaten', r'못(?:먹|드셨)|안먹|굶었|아직(?:이야|이에요|요|안했|식사시간)|식사(?:전|안했|못했)|(?:아직|이따가).*먹을'),
    ('ate', r'먹었|먹엇|챙겨먹었|드셨|식사(?:를)?했|잘먹음'),
)
SLEEP_RULES = (
    ('sleep_difficulty', r'못잤|못주무|잘안잤|안잤|자주깼|자꾸깼|자꾸깨|잠(?:이)?안왔|잠(?:이)?안와|설쳤|뒤척였|잠들기힘들|잠(?:을)?(?:거의)?못자'),
    ('slept_well', r'잘잤|푹잤|편히잤|잘주무|푹주무'),
)
IMMEDIATE_REQUEST = re.compile(r'지금(?:당장)?도와(?:줘|주세요)|지금도움(?:이)?필요|(?:지금|당장|바로)(?:전화|연락)(?:해)?(?:줘|주세요)')
CONTACT_REQUEST = re.compile(r'(?:전화|연락)(?:좀)?(?:해달라|해줘|해주세요|부탁)|도움(?:이)?필요')
OTHER_PERSON = re.compile(r'친구|이웃|남편|아내|아들|딸|어머니|아버지|다른분')
FOLLOW_UP = {
    'meal': '오늘 식사는 아직 안 하신 건가요, 아니면 식사하기 어려운 이유가 있으신가요?',
    'sleep': '어젯밤에는 잠을 잘 주무셨나요, 아니면 주무시기 어려우셨나요?',
}

def compact(answer):
    return re.sub(r'\s+', '', answer)

def answer_status(topic, answer):
    if topic not in FOLLOW_UP:
        return UNKNOWN
    rules = MEAL_RULES if topic == 'meal' else SLEEP_RULES
    parts = re.split(r'[.!?。！？,;\n]+|아,?\s*아니(?:요|에요)?\s*|정정하면|그게\s*아니라', answer)
    result = UNKNOWN
    for part in parts:
        value = compact(part)
        if not value or OTHER_PERSON.search(value):
            continue
        if topic == 'meal':
            value = re.split(r'오늘(?:은|도)?', value)[-1] if '오늘' in value else value
            if re.search(r'어제|지난주|평소|내일', value):
                continue
            if re.search(r'먹을게없(?:지않|는건아니)|먹기어렵(?:지않|지는않)', value):
                continue
            if re.search(r'아침.*(?<!못)(?<!안)먹었.*점심.*(?:아직|못먹|안먹)', value):
                result = 'ate'
                continue
        elif re.search(r'그저께|지난주|평소|오늘밤|내일', value) and '어젯밤' not in value:
            continue
        if re.search(r'(?:못먹|안먹|못잤|안잤|못주무).*?(?:건아니|지는않|지않)', value):
            continue
        # A bare yes/no does not identify which answer the caller meant.
        for code, pattern in rules:
            if re.search(pattern, value):
                if topic == 'meal' and code == 'not_eaten' and result == 'ate' and re.match(r'점심|저녁', value):
                    break
                result = code
                break
    return result

def review_call(turns, call_status):
    answers = {topic: {'status': UNKNOWN, 'evidence': None} for topic in FOLLOW_UP}
    flags = []
    for turn in turns:
        topic, answer = turn['topic'], turn['answer']
        for clause in re.split(r'[.!?。！？,;\n]+', answer):
            value = compact(clause)
            if not value or OTHER_PERSON.search(value) or re.search(r'필요없|필요하지않|필요한건아니|연락하지마|연락안해도|전화안해도|해주지마', value):
                continue
            if IMMEDIATE_REQUEST.search(value):
                flags.append({'code': 'immediate_request', 'evidence': clause.strip()})
            elif CONTACT_REQUEST.search(value):
                flags.append({'code': 'contact_request', 'evidence': clause.strip()})
        if topic in answers:
            status = answer_status(topic, answer)
            if status != UNKNOWN or answers[topic]['status'] == UNKNOWN:
                answers[topic] = {'status': status, 'evidence': answer}
    if call_status != 'in_progress':
        if call_status == 'declined':
            flags.append({'code': 'call_declined', 'evidence': '수신 거절'})
        else:
            for topic, result in answers.items():
                status = result['status']
                if status in {'meal_difficulty', 'sleep_difficulty', UNKNOWN}:
                    flags.append({'code': f'{topic}_{status}',
                                  'evidence': result['evidence'] or f'{LABELS[topic]} 답변 없음'})
            if call_status == 'interrupted':
                flags.append({'code': 'call_interrupted', 'evidence': '통화 중단'})
    if any(flag['code'] == 'immediate_request' for flag in flags):
        level = 'immediate'
    elif flags:
        level = 'follow_up'
    else:
        level = 'pending' if call_status == 'in_progress' else 'routine'
    return {'rules_version': RULES_VERSION, 'level': level, 'answers': answers, 'flags': flags}

def summarize(review):
    topics = ' / '.join(f'{LABELS[topic]}: {ANSWER_LABELS[item["status"]]}' for topic, item in review['answers'].items())
    prefix = f'{REVIEW_LABELS[review["level"]]} · {topics}'
    if not review['flags']:
        return prefix
    reasons = dict.fromkeys(flag['evidence'] for flag in review['flags'])
    return f'{prefix} · 확인 이유: ' + ' / '.join(reasons)

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
def start_call(resident_id: int):
    with db() as c:
        if not resident_exists(c, resident_id):
            raise HTTPException(404, '어르신을 찾을 수 없습니다.')
        ongoing = c.execute("SELECT id FROM calls WHERE resident_id=? AND status='in_progress'", (resident_id,)).fetchone()
        if ongoing:
            raise HTTPException(409, '이미 진행 중인 통화가 있습니다. 해당 통화를 먼저 종료해 주세요.')
        cur = c.execute("INSERT INTO calls(resident_id,started_at,status) VALUES(?,?,'in_progress')", (resident_id, now()))
        return {'id': cur.lastrowid, 'resident_id': resident_id, 'status':'in_progress', 'question':QUESTIONS[0][1], 'topic':QUESTIONS[0][0]}

@app.post('/api/residents/{resident_id}/decline', status_code=201)
def decline_call(resident_id: int):
    with db() as c:
        if not resident_exists(c, resident_id):
            raise HTTPException(404, '어르신을 찾을 수 없습니다.')
        current = now()
        cur = c.execute("INSERT INTO calls(resident_id,started_at,ended_at,status,summary) VALUES(?,?,?,'declined',?)", (resident_id,current,current,'수신 거절'))
        return {'id':cur.lastrowid,'status':'declined'}

@app.post('/api/calls/{call_id}/turns', status_code=201)
def add_turn(call_id: int, body: TurnInput):
    answer = body.answer.strip()
    if not answer:
        raise HTTPException(422, '빈 답변은 저장할 수 없습니다.')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        call = fetch_call(c, call_id)
        if call['status'] != 'in_progress':
            raise HTTPException(409, '종료된 통화입니다.')
        turns = fetch_turns(c, call_id)
        topic_counts = {topic: sum(t['topic'] == topic for t in turns) for topic, _ in QUESTIONS}
        index = len({t['topic'] for t in turns})
        if turns and turns[-1]['topic'] in FOLLOW_UP:
            last = turns[-1]
            last_status = answer_status(last['topic'], last['answer'])
            if (topic_counts[last['topic']] == 1 and last_status in {UNKNOWN, 'not_eaten'}
                    and review_call(turns, 'in_progress')['level'] != 'immediate'):
                index -= 1
        if index >= len(QUESTIONS):
            raise HTTPException(409, '모든 질문이 완료되었습니다.')
        topic, question = QUESTIONS[index]
        if topic_counts[topic]:
            question = FOLLOW_UP[topic]
        c.execute('INSERT INTO turns(call_id,topic,question,answer,created_at) VALUES(?,?,?,?,?)',
                  (call_id, topic, question, answer, now()))
        turns.append({'topic': topic, 'answer': answer})
        review = review_call(turns, 'in_progress')
        status = answer_status(topic, answer)
        urgent = review['level'] == 'immediate'
        retry = (topic in FOLLOW_UP and topic_counts[topic] == 0
                 and status in {UNKNOWN, 'not_eaten'} and not urgent)
        if retry:
            return {'count': index, 'reply': '네, 한 번만 더 여쭤볼게요.', 'finished': False,
                    'next_question': FOLLOW_UP[topic], 'review': review}
        next_index = index + 1
        return {'count': next_index, 'reply': '네, 말씀 잘 들었습니다.',
                'finished': next_index == len(QUESTIONS),
                'next_question': QUESTIONS[next_index][1] if next_index < len(QUESTIONS) else None,
                'review': review}


@app.post('/api/calls/{call_id}/finish')
def finish_call(call_id: int, body: FinishInput):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        call = fetch_call(c, call_id)
        if call['status'] != 'in_progress':
            raise HTTPException(409,'이미 종료된 통화입니다.')
        turns = fetch_turns(c,call_id)
        answered = len({turn['topic'] for turn in turns})
        review = review_call(turns, body.status)
        summary = summarize(review)
        c.execute('UPDATE calls SET ended_at=?,status=?,summary=? WHERE id=?',(now(),body.status,summary,call_id))
        return {'id':call_id,'status':body.status,'summary':summary,'answered':answered,'review':review}

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
        turns = fetch_turns(c, call_id)
        return {**dict(row), 'turns': turns, 'review': review_call(turns, row['status'])}

@app.get('/api/dashboard')
def dashboard():
    # Today's date is based on local machine time (Asia/Seoul when used in Korea).
    from datetime import datetime as dt
    from zoneinfo import ZoneInfo
    today = dt.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    with db() as c:
        residents_data = [dict(row) for row in c.execute('SELECT * FROM residents ORDER BY id')]
        recent = [dict(row) for row in c.execute('SELECT * FROM calls ORDER BY id DESC')]
    latest = {}
    for call in recent:
        date = dt.fromisoformat(call['started_at']).astimezone(ZoneInfo('Asia/Seoul')).date().isoformat()
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


@app.get('/', include_in_schema=False)
def web_app():
    return FileResponse(APP_DIR / 'web' / 'index.html')


app.mount('/assets', StaticFiles(directory=APP_DIR / 'web'), name='assets')
