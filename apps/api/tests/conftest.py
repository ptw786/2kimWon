import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# app.main 은 import 할 때 앱을 만든다 → 그 전에 테스트용 환경을 깐다 (실제 DB·Ollama·스케줄러를 건드리지 않게)
_TMP = Path(tempfile.mkdtemp(prefix='ansimon-test-'))
os.environ['ANSIMON_DB'] = str(_TMP / 'import.db')
os.environ['ANSIMON_LLM'] = 'off'
os.environ['ANSIMON_SCHEDULER'] = '0'
os.environ['ANSIMON_DEMO'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.main import create_app  # noqa: E402


class Clock:
    """실제 시각 + offset. advance() 로 시간을 흘린다."""

    def __init__(self):
        self.offset = timedelta(0)
        self.fixed: datetime | None = None

    def __call__(self):
        return (self.fixed or datetime.now(UTC)) + self.offset

    def advance(self, **kw):
        self.offset += timedelta(**kw)

    def set(self, dt: datetime):
        self.fixed, self.offset = dt, timedelta(0)


@pytest.fixture(scope='session')
def template_db():
    path = _TMP / 'template.db'
    db.init_db(str(path), model_name='ax4-light:q4_K_M')
    return path


@pytest.fixture
def clock():
    c = Clock()
    db.set_clock(c)
    yield c
    db.set_clock(None)


@pytest.fixture
def make_client(tmp_path, template_db, monkeypatch, clock):
    def _make(llm=None, **env):
        path = tmp_path / 'ansimon.db'
        if not path.exists():
            shutil.copy(template_db, path)
        monkeypatch.setenv('ANSIMON_DB', str(path))
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        app = create_app()
        if llm is not None:
            app.state.llm = llm
        return TestClient(app)
    return _make


@pytest.fixture
def client(make_client):
    return make_client()


def resident_id(client, name: str) -> int:
    return next(r['id'] for r in client.get('/api/elder/residents').json() if r['name'] == name)


def start_call(client, rid: int) -> int:
    r = client.post(f'/api/staff/residents/{rid}/call')
    assert r.status_code == 201, r.text
    cid = r.json()['id']
    a = client.post(f'/api/elder/calls/{cid}/answer')
    assert a.status_code == 200, a.text
    return cid


_n = {'i': 0}


def say(client, cid: int, text: str, source: str = 'text', ctid: str | None = None) -> dict:
    _n['i'] += 1
    r = client.post(f'/api/elder/calls/{cid}/turn',
                    json={'text': text, 'source': source, 'client_turn_id': ctid or f't{_n["i"]}'})
    assert r.status_code == 200, r.text
    return r.json()
