"""안심온 시연 서버. Python 표준 라이브러리와 SQLite를 사용한다."""
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread

from rules import TOPICS, assess

ROOT = Path(__file__).resolve().parent
DB_PATH = os.environ.get('ANSIMON_DB', ROOT / 'ansimon.sqlite3')
KST = timezone(timedelta(hours=9))
ONE_DAY = timedelta(days=1)


def connect():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def initialize():
    with closing(connect()) as db, db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                call_time TEXT NOT NULL,
                next_at TEXT NOT NULL,
                UNIQUE (recipient, call_time)
            );
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
                scheduled_at TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                UNIQUE (schedule_id, scheduled_at)
            );
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                recipient TEXT,
                scheduled_at TEXT,
                assessment TEXT NOT NULL,
                score INTEGER NOT NULL
            );
        """)


def stamp(moment):
    return moment.isoformat(timespec='seconds')


def next_run(now, call_time):
    hour, minute = map(int, call_time.split(':'))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target if target > now else target + ONE_DAY


def enqueue_due(now):
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        schedules = db.execute('SELECT * FROM schedules WHERE next_at <= ?', (stamp(now),)).fetchall()
        for schedule in schedules:
            next_at = next_run(now, schedule['call_time'])
            # 서버가 여러 날 꺼져 있었으면 가장 최근 회차만 복구한다.
            db.execute(
                'INSERT OR IGNORE INTO queue (schedule_id, scheduled_at) VALUES (?, ?)',
                (schedule['id'], stamp(next_at - ONE_DAY)),
            )
            db.execute('UPDATE schedules SET next_at = ? WHERE id = ?', (stamp(next_at), schedule['id']))


def run_scheduler(stop):
    while not stop.is_set():
        try:
            enqueue_due(datetime.now(KST))
        except sqlite3.Error as error:
            print(f'스케줄 처리 오류: {error}', flush=True)
        stop.wait(1)


def decode_record(row):
    record = dict(row)
    record['assessment'] = json.loads(record['assessment'])
    return record


class RequestError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def write_schedule(db, payload, schedule_id=None):
    recipient = payload.get('recipient')
    call_time = payload.get('call_time')
    if not isinstance(recipient, str) or not 1 <= len(recipient.strip()) <= 30:
        raise RequestError(400, '시연 대상 별칭을 1~30자로 입력하세요.')
    if not isinstance(call_time, str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', call_time):
        raise RequestError(400, '예약 시간을 HH:MM 형식으로 입력하세요.')
    values = (recipient.strip(), call_time, stamp(next_run(datetime.now(KST), call_time)))
    try:
        if schedule_id is None:
            return db.execute('INSERT INTO schedules (recipient, call_time, next_at) VALUES (?, ?, ?)', values).lastrowid
        previous = db.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
        if previous is None:
            raise RequestError(404, '스케줄이 이미 삭제되었습니다.')
        if (previous['recipient'], previous['call_time']) != values[:2]:
            db.execute('UPDATE schedules SET recipient = ?, call_time = ?, next_at = ? WHERE id = ?', (*values, schedule_id))
            db.execute('DELETE FROM queue WHERE schedule_id = ? AND completed = 0', (schedule_id,))
        return schedule_id
    except sqlite3.IntegrityError as error:
        raise RequestError(409, '같은 별칭과 시간의 스케줄이 이미 있습니다.') from error


def save_record(db, payload):
    record_id = payload.get('id')
    answers = payload.get('answers')
    rejected = payload.get('rejected')
    queue_id = payload.get('queue_id')
    if not isinstance(record_id, str) or not re.fullmatch(r'[0-9a-f-]{36}', record_id):
        raise RequestError(400, '통화 식별자가 올바르지 않습니다.')
    if not isinstance(answers, list) or len(answers) > len(TOPICS) or any(
        not isinstance(answer, str) or not 1 <= len(answer.strip()) <= 500 for answer in answers
    ):
        raise RequestError(400, '답변은 최대 5개이며 각 답변은 1~500자입니다.')
    if type(rejected) is not bool or (rejected and answers):
        raise RequestError(400, '통화 상태가 올바르지 않습니다.')
    if queue_id is not None and (type(queue_id) is not int or not 1 <= queue_id < 2**63):
        raise RequestError(400, '대기 통화 식별자가 올바르지 않습니다.')
    saved = db.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone()
    if saved is not None:
        return decode_record(saved)
    recipient = scheduled_at = None
    if queue_id is not None:
        queued = db.execute("""
            SELECT schedules.recipient, queue.scheduled_at, queue.completed
            FROM queue JOIN schedules ON schedules.id = queue.schedule_id
            WHERE queue.id = ?
        """, (queue_id,)).fetchone()
        if queued is None or queued['completed']:
            raise RequestError(409, '예약 통화가 이미 처리되었거나 스케줄이 변경되었습니다.')
        recipient, scheduled_at = queued['recipient'], queued['scheduled_at']
        db.execute('UPDATE queue SET completed = 1 WHERE id = ?', (queue_id,))
    answers = [answer.strip() for answer in answers]
    result = assess(answers, rejected)
    status = '수신 거절' if rejected else '안부 확인 완료' if len(answers) == len(TOPICS) else '통화 중단'
    summary = ' / '.join(f'{topic} · {answer}' for topic, answer in zip(TOPICS, answers))
    if not summary:
        summary = '전화를 받지 않았습니다.' if rejected else '답변 없이 통화가 종료되었습니다.'
    db.execute('INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (
        record_id, stamp(datetime.now(KST)), status, summary, recipient, scheduled_at,
        json.dumps(result, ensure_ascii=False), result['score'],
    ))
    return decode_record(db.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone())


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, mime='application/json; charset=utf-8'):
        body = json.dumps(data, ensure_ascii=False).encode() if not isinstance(data, bytes) else data
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def read_payload(self):
        if self.headers.get_content_type() != 'application/json':
            raise RequestError(415, 'JSON 형식으로 전송하세요.')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 32768:
                raise ValueError
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, RecursionError) as error:
            raise RequestError(400, '요청 데이터가 올바르지 않습니다.') from error
        return data

    def route(self):
        method, path = self.command, self.path.split('?', 1)[0]
        if method == 'GET' and path == '/':
            return self.reply(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        try:
            with closing(connect()) as db, db:
                if method == 'GET' and path == '/api/schedules':
                    db.execute('BEGIN')
                    schedules = db.execute('SELECT * FROM schedules ORDER BY next_at, id').fetchall()
                    pending = db.execute("""
                        SELECT queue.id, queue.scheduled_at, schedules.recipient
                        FROM queue JOIN schedules ON schedules.id = queue.schedule_id
                        WHERE queue.completed = 0 ORDER BY queue.scheduled_at, queue.id
                    """).fetchall()
                    result = {'schedules': list(map(dict, schedules)), 'pending': list(map(dict, pending))}
                elif method == 'GET' and path == '/api/records':
                    records = db.execute('SELECT * FROM records ORDER BY score DESC, date DESC, rowid DESC').fetchall()
                    result = list(map(decode_record, records))
                elif method == 'POST' and path == '/api/records':
                    payload = self.read_payload()
                    db.execute('BEGIN IMMEDIATE')
                    result = save_record(db, payload)
                elif method == 'DELETE' and path == '/api/records':
                    db.execute('DELETE FROM records')
                    result = {}
                elif method == 'POST' and path == '/api/schedules':
                    payload = self.read_payload()
                    db.execute('BEGIN IMMEDIATE')
                    result = {'id': write_schedule(db, payload)}
                elif re.fullmatch(r'/api/schedules/[0-9]{1,18}', path) and method in ('PUT', 'DELETE'):
                    schedule_id = int(path.rsplit('/', 1)[1])
                    if method == 'PUT':
                        payload = self.read_payload()
                        db.execute('BEGIN IMMEDIATE')
                        result = {'id': write_schedule(db, payload, schedule_id)}
                    else:
                        db.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
                        result = {}
                else:
                    raise RequestError(404, '요청한 경로를 찾을 수 없습니다.')
        except RequestError as error:
            return self.reply(error.status, {'error': str(error)})
        except sqlite3.Error as error:
            print(f'저장소 오류: {error}', flush=True)
            return self.reply(503, {'error': '저장소에 접근할 수 없습니다. 잠시 후 다시 시도하세요.'})
        return self.reply(200, result)

    do_GET = do_POST = do_PUT = do_DELETE = route


if __name__ == '__main__':
    initialize()
    address = ('127.0.0.1', int(os.environ.get('ANSIMON_PORT', '8000')))
    stop = Event()
    with ThreadingHTTPServer(address, Handler) as server:
        worker = Thread(target=run_scheduler, args=(stop,), daemon=True)
        worker.start()
        print(f'안심온을 열려면 http://{address[0]}:{address[1]} 에 접속하세요.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            worker.join()
