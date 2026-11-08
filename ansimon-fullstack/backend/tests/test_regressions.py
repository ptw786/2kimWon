from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
import main


def test_without_os_timezone_database(tmp_path):
    env = {**os.environ, 'ANSIMON_DB':str(tmp_path / 'no-zone.db'), 'PYTHONTZPATH':''}
    result = subprocess.run([sys.executable, '-c', "from fastapi.testclient import TestClient; from main import app; r=TestClient(app).get('/api/dashboard'); assert r.status_code==200; assert r.json()['total']==4"], env=env, cwd=Path(main.__file__).parent, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_retry_and_concurrent_writes():
    client = TestClient(main.app)
    key = {'Idempotency-Key':'start-1'}
    def start(_):
        return client.post('/api/residents/1/calls', headers=key)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(start, range(4)))
    assert all(r.status_code == 201 for r in results)
    cid = results[0].json()['id']
    assert {r.json()['id'] for r in results} == {cid}
    assert len(client.get('/api/calls').json()) == 1
    assert client.post('/api/residents/1/calls').status_code == 409
    assert client.post('/api/residents/2/calls', headers=key).status_code == 409
    for index,text in enumerate(['안 아파','밥 먹었어','잘 잤어','약 먹었어','기분 좋아']):
        def answer(_):
            return client.post(f'/api/calls/{cid}/turns', json={'index':index,'answer':text})
        with ThreadPoolExecutor(max_workers=4) as pool:
            answers = list(pool.map(answer, range(4)))
        assert all(r.status_code == 201 for r in answers)
        assert all(r.json()['count'] == index+1 for r in answers)
    assert len(client.get(f'/api/calls/{cid}').json()['turns']) == 5
    assert client.post(f'/api/calls/{cid}/turns', json={'index':0,'answer':'다른 답변'}).status_code == 409
    first = client.post(f'/api/calls/{cid}/finish', json={'status':'completed'})
    second = client.post(f'/api/calls/{cid}/finish', json={'status':'completed'})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert client.post(f'/api/calls/{cid}/finish', json={'status':'interrupted'}).status_code == 409
    assert len(client.get('/api/calls').json()) == 1


def test_decline_retry_and_validation():
    client = TestClient(main.app)
    headers = {'Idempotency-Key':'decline-1'}
    first = client.post('/api/residents/2/decline', headers=headers)
    assert first.status_code == 201
    assert client.post('/api/residents/2/decline', headers=headers).json() == first.json()
    assert len(client.get('/api/calls').json()) == 1
    assert client.post('/api/residents/999/calls').status_code == 404
    cid = client.post('/api/residents/1/calls').json()['id']
    for body in ({'answer':' '}, {'answer':'a'*501}, {'answer':'ok','index':3}):
        assert client.post(f'/api/calls/{cid}/turns', json=body).status_code in (409,422)
    assert client.get(f'/api/calls/{cid}').json()['turns'] == []


def test_persist_across_process_restart_and_backup():
    client = TestClient(main.app)
    cid = client.post('/api/residents/1/calls').json()['id']
    client.post(f'/api/calls/{cid}/turns',json={'answer':'오늘은 괜찮아요','index':0})
    client.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'})
    before = client.get(f'/api/calls/{cid}').json()
    env = {**os.environ,'ANSIMON_DB':str(main.DB_PATH)}
    script = f"from fastapi.testclient import TestClient; from main import app; import json; print(json.dumps(TestClient(app).get('/api/calls/{cid}').json()))"
    result = subprocess.run([sys.executable,'-c',script], env=env, cwd=Path(main.__file__).parent, capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    import json
    assert json.loads(result.stdout) == before
    backups = list(main.DB_PATH.parent.glob('test.db.backup-*'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as c:
        assert c.execute('SELECT answer FROM turns').fetchone()[0] == '오늘은 괜찮아요'


def test_migrate_original_schema_without_losing_rows(tmp_path, monkeypatch):
    path = tmp_path / 'legacy.db'
    # Portable fixture: current schema minus the added column and index.
    with sqlite3.connect(main.DB_PATH) as source, sqlite3.connect(path) as target:
        source.backup(target)
        target.execute('DROP INDEX calls_request_key')
        target.execute('ALTER TABLE calls DROP COLUMN request_key')
        target.execute("INSERT INTO calls(resident_id,started_at,status,summary) VALUES(1,?,'completed','보존할 기록')", (main.now(),))
    monkeypatch.setattr(main, 'DB_PATH', path)
    main.init_db()
    with sqlite3.connect(path) as c:
        assert c.execute('SELECT summary FROM calls').fetchone()[0] == '보존할 기록'
        assert 'request_key' in {r[1] for r in c.execute('PRAGMA table_info(calls)')}
    backup = next(tmp_path.glob('legacy.db.backup-*'))
    with sqlite3.connect(backup) as c:
        assert c.execute('SELECT summary FROM calls').fetchone()[0] == '보존할 기록'
        assert 'request_key' not in {r[1] for r in c.execute('PRAGMA table_info(calls)')}


def test_cors_and_database_error(monkeypatch):
    client = TestClient(main.app, raise_server_exceptions=False)
    for origin in ('http://localhost:5173','http://127.0.0.1:5173'):
        r = client.options('/api/residents/1/calls',headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type, Idempotency-Key'})
        assert r.status_code == 200
        assert r.headers['access-control-allow-origin'] == origin
    def broken(*args, **kwargs):
        raise sqlite3.OperationalError('no such table: calls')
    monkeypatch.setattr(main, 'db', broken)
    response = client.get('/api/calls',headers={'Origin':'http://localhost:5173'})
    assert response.status_code == 500
    assert '데이터베이스' in response.json()['detail']
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
