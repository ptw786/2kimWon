"""Daily KST scheduling; queued web demonstrations, no real phone dialer."""
import sqlite3
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
KST=timezone(timedelta(hours=9))
UTC=timezone.utc


def init_schema(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS care_schedules (
      id INTEGER PRIMARY KEY, resident_id INTEGER REFERENCES residents(id),
      recipient TEXT NOT NULL, call_time TEXT NOT NULL, next_at TEXT NOT NULL,
      enabled INTEGER NOT NULL DEFAULT 1, origin_key TEXT UNIQUE);
    CREATE UNIQUE INDEX IF NOT EXISTS care_schedule_active ON care_schedules(resident_id,call_time) WHERE enabled=1;
    CREATE TABLE IF NOT EXISTS scheduled_calls (
      id INTEGER PRIMARY KEY, schedule_id INTEGER NOT NULL REFERENCES care_schedules(id),
      scheduled_at TEXT NOT NULL, recipient TEXT NOT NULL, resident_id INTEGER REFERENCES residents(id),
      state TEXT NOT NULL DEFAULT 'pending', call_id INTEGER UNIQUE REFERENCES calls(id),
      origin_key TEXT UNIQUE, UNIQUE(schedule_id,scheduled_at));
    CREATE TABLE IF NOT EXISTS imported_records (
      origin_key TEXT PRIMARY KEY, payload_json TEXT NOT NULL, imported_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS legacy_archive (
      origin_key TEXT PRIMARY KEY, table_name TEXT NOT NULL, payload_json TEXT NOT NULL);
    ''')


def stamp(t):return t.astimezone(UTC).isoformat(timespec='seconds')

def next_run(moment,call_time):
    local=moment.astimezone(KST);hour,minute=map(int,call_time.split(':'))
    target=local.replace(hour=hour,minute=minute,second=0,microsecond=0)
    return target if target>local else target+timedelta(days=1)


def enqueue(c,moment=None):
    moment=moment or datetime.now(UTC)
    # Caller owns BEGIN IMMEDIATE; multiple workers cannot create duplicate occurrences.
    for s in c.execute('SELECT * FROM care_schedules WHERE enabled=1 AND next_at<=?',(stamp(moment),)).fetchall():
        future=next_run(moment,s['call_time'])
        c.execute('INSERT OR IGNORE INTO scheduled_calls(schedule_id,scheduled_at,recipient,resident_id) VALUES(?,?,?,?)',
                  (s['id'],stamp(future-timedelta(days=1)),s['recipient'],s['resident_id']))
        c.execute('UPDATE care_schedules SET next_at=? WHERE id=?',(stamp(future),s['id']))


def validate_queue(c,queue_id,resident_id):
    q=c.execute('SELECT * FROM scheduled_calls WHERE id=?',(queue_id,)).fetchone()
    if not q:raise HTTPException(404,'예약 대기 통화를 찾을 수 없습니다.')
    if q['resident_id']!=resident_id:raise HTTPException(409,'예약 대상과 어르신이 다릅니다. 예약 대상 연결을 확인하세요.')
    if q['state']!='pending':raise HTTPException(409,'이미 처리 중이거나 취소된 예약 통화입니다.')
    return q


def bind_queue(c,queue_id,resident_id,call_id,completed=False):
    if queue_id is None:return
    validate_queue(c,queue_id,resident_id)
    c.execute('UPDATE scheduled_calls SET call_id=?,state=? WHERE id=?',(call_id,'completed' if completed else 'claimed',queue_id))


def finish_queue(c,call_id):
    c.execute("UPDATE scheduled_calls SET state='completed' WHERE call_id=? AND state='claimed'",(call_id,))


def ensure_editable(c,schedule_id):
    if c.execute("SELECT 1 FROM scheduled_calls WHERE schedule_id=? AND state='claimed'",(schedule_id,)).fetchone():
        raise HTTPException(409,'진행 중인 예약 통화를 먼저 종료하세요.')
