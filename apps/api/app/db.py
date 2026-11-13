"""SQLite 연결·스키마·시간 도우미.

- 저장은 UTC ISO, 응답은 한국 시간(+09:00) ISO. "오늘" = 한국 날짜.
- 쓰기는 tx() 안에서만 (BEGIN IMMEDIATE). LLM 호출은 tx() 밖에서 끝낸 뒤 짧게 저장한다.
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

UTC = timezone.utc
KST = timezone(timedelta(hours=9))

# ---- 시계 (테스트·시드에서 바꿀 수 있음) ----
_global_clock = None          # 테스트: set_clock(lambda: datetime(...))
_local = threading.local()    # 시드: 그 스레드에서만 시각을 바꿈


def set_clock(fn):
    global _global_clock
    _global_clock = fn


@contextmanager
def local_clock(fn):
    prev = getattr(_local, 'clock', None)
    _local.clock = fn
    try:
        yield
    finally:
        _local.clock = prev


def now() -> datetime:
    fn = getattr(_local, 'clock', None) or _global_clock
    dt = fn() if fn else datetime.now(UTC)
    return dt.astimezone(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec='seconds')


def now_iso() -> str:
    return iso(now())


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


def kst(s: str | None) -> str | None:
    return parse(s).astimezone(KST).isoformat(timespec='seconds') if s else None


def kst_today() -> date:
    return now().astimezone(KST).date()


def kst_date_of(s: str) -> str:
    return parse(s).astimezone(KST).date().isoformat()


# ---- 연결·트랜잭션 ----
_write_depth = 0
_depth_lock = threading.Lock()


def in_write_tx() -> bool:
    return _write_depth > 0


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 15000')
    return conn


@contextmanager
def tx(conn: sqlite3.Connection):
    """쓰기 트랜잭션. 이미 열려 있으면 그 안에서 이어 쓴다 (시드처럼 한 번에 묶을 때)."""
    global _write_depth
    if conn.in_transaction:
        yield conn
        return
    conn.execute('BEGIN IMMEDIATE')
    with _depth_lock:
        _write_depth += 1
    try:
        yield conn
        conn.execute('COMMIT')
    except BaseException:
        conn.execute('ROLLBACK')
        raise
    finally:
        with _depth_lock:
            _write_depth -= 1


SCHEMA = """
CREATE TABLE IF NOT EXISTS residents (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  age INTEGER NOT NULL,
  region TEXT NOT NULL DEFAULT '',
  neighborhood TEXT NOT NULL,
  call_time TEXT NOT NULL,
  memo TEXT,
  is_virtual INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calls (
  id INTEGER PRIMARY KEY,
  resident_id INTEGER NOT NULL REFERENCES residents(id) ON DELETE CASCADE,
  kst_date TEXT NOT NULL,
  status TEXT NOT NULL,
  origin TEXT NOT NULL,
  created_at TEXT NOT NULL,
  started_at TEXT,
  ended_at TEXT,
  last_activity_at TEXT NOT NULL,
  step_index INTEGER NOT NULL DEFAULT 0,
  reasks INTEGER NOT NULL DEFAULT 0,
  repeats INTEGER NOT NULL DEFAULT 0,
  summary TEXT,
  assessment TEXT,
  staff_check_note TEXT,
  staff_check_at TEXT
);
CREATE INDEX IF NOT EXISTS calls_resident_date ON calls(resident_id, kst_date);
CREATE INDEX IF NOT EXISTS calls_status ON calls(status);
CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY,
  call_id INTEGER NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  text TEXT NOT NULL,
  topic TEXT,
  at TEXT NOT NULL,
  source TEXT,
  judged TEXT,
  needs TEXT,
  ms INTEGER,
  client_turn_id TEXT,
  result TEXT,
  UNIQUE (call_id, client_turn_id)
);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY,
  call_id INTEGER NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
  turn_id INTEGER,
  topic TEXT NOT NULL,
  status TEXT NOT NULL,
  quote TEXT,
  origin TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS safety_signals (
  id INTEGER PRIMARY KEY,
  call_id INTEGER NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
  turn_id INTEGER,
  category TEXT NOT NULL,
  quote TEXT NOT NULL,
  at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_runs (
  id INTEGER PRIMARY KEY,
  call_id INTEGER NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
  at TEXT NOT NULL,
  step TEXT NOT NULL,
  model TEXT,
  ms INTEGER,
  outcome TEXT NOT NULL,
  note TEXT
);
"""

TABLES = ('ai_runs', 'safety_signals', 'items', 'turns', 'calls', 'residents')


# v2.1 에서 더한 열: 예전 DB 에는 없으므로 ALTER TABLE 로 더한다
_ADDED_COLUMNS = [
    ('residents', 'region', "TEXT NOT NULL DEFAULT ''"),
    ('turns', 'needs', 'TEXT'),
    ('turns', 'ms', 'INTEGER'),
]


def migrate(conn: sqlite3.Connection) -> None:
    """예전 DB 에 v2.1 열을 더하고, 비어 있는 region 을 동네 이름으로 채운다."""
    from .seed import region_for   # 순환 import 피함
    for table, col, decl in _ADDED_COLUMNS:
        cols = {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
        if col not in cols:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {decl}')
    for r in conn.execute("SELECT id, code, neighborhood FROM residents WHERE region = ''").fetchall():
        conn.execute('UPDATE residents SET region = ? WHERE id = ?', (region_for(r[2]), r[0]))


def init_db(path: str, *, model_name: str) -> None:
    """스키마를 만들고, 어르신이 한 명도 없으면(새 DB) 시드를 넣는다."""
    from .seed import seed   # 순환 import 피함
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        migrate(conn)
        if conn.execute('SELECT COUNT(*) FROM residents').fetchone()[0] == 0:
            seed(conn, model_name=model_name)
    finally:
        conn.close()


def wipe(conn: sqlite3.Connection) -> None:
    for t in TABLES:
        conn.execute(f'DELETE FROM {t}')
