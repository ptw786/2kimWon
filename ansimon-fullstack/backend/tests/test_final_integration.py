from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient
import main

@pytest.mark.parametrize('invalid_db',['missing','empty'])
def test_health_rejects_missing_or_uninitialized_database(tmp_path,monkeypatch,invalid_db):
    path=tmp_path/'unavailable.db'
    if invalid_db=='empty':
        with sqlite3.connect(path) as conn:conn.execute('CREATE TABLE unrelated(id INTEGER)')
    before=path.read_bytes() if path.exists() else None
    monkeypatch.setattr(main,'DB_PATH',path)
    response=TestClient(main.app,raise_server_exceptions=False).get('/api/health')
    assert response.status_code==503,response.text
    assert '데이터베이스' in response.json()['detail']
    assert (path.read_bytes() if path.exists() else None)==before


def test_health_checks_schema_without_changing_records():
    client=TestClient(main.app)
    before=client.get('/api/calls').json()
    response=client.get('/api/health')
    assert response.status_code==200
    assert response.json()=={'ok':True,'mode':'local-rule-based'}
    assert client.get('/api/calls').json()==before


def test_cors_rejects_unconfigured_origin_and_allows_local_frontends():
    client=TestClient(main.app)
    for origin in ('http://localhost:5173','http://127.0.0.1:5173'):
        response=client.get('/api/residents',headers={'Origin':origin})
        assert response.status_code==200
        assert response.headers['access-control-allow-origin']==origin
    blocked=client.options('/api/residents/1/calls',headers={'Origin':'http://localhost:5174','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type, Idempotency-Key'})
    assert blocked.status_code==400
    assert 'access-control-allow-origin' not in blocked.headers


def test_actual_api_contract_and_sqlite_rows_match_after_completion():
    client=TestClient(main.app)
    residents=client.get('/api/residents')
    assert residents.status_code==200 and residents.headers['content-type'].startswith('application/json')
    assert {'id','name','age','neighborhood','call_time'}<=residents.json()[0].keys()
    dashboard=client.get('/api/dashboard')
    assert dashboard.status_code==200
    assert {'date','total','completed','pending','interrupted','declined','in_progress','residents'}<=dashboard.json().keys()
    start=client.post('/api/residents/1/calls',headers={'Idempotency-Key':'final-contract'})
    assert start.status_code==201
    cid=start.json()['id']
    assert isinstance(cid,int) and start.json()['status']=='in_progress'
    for index,text in enumerate(['안 아파','밥 먹었어','잘 잤어','먹는 약 없어','기분 좋아']):
        response=client.post(f'/api/calls/{cid}/turns',json={'index':index,'attempt':0,'answer':text})
        assert response.status_code==201
        body=response.json()
        assert {'count','question_index','attempt','classification','classification_label','reply','emergency','needs_retry','retry_count','next_attempt','finished','next_question'}<=body.keys()
        assert body['count']==index+1 and isinstance(body['finished'],bool)
        assert body['classification'] in ('positive','negative','neutral','unknown')
    finish=client.post(f'/api/calls/{cid}/finish',json={'status':'completed'})
    assert finish.status_code==200
    record=client.get(f'/api/calls/{cid}').json()
    listed=client.get('/api/calls?resident_id=1').json()[0]
    assert record['status']==listed['status']=='completed'
    assert record['summary']==listed['summary'] and record['summary']
    with sqlite3.connect(main.DB_PATH) as conn:
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
        row=conn.execute('SELECT status,summary,ended_at FROM calls WHERE id=?',(cid,)).fetchone()
        assert row[0]=='completed' and row[1]==record['summary'] and row[2]
        assert conn.execute('SELECT COUNT(*) FROM turns WHERE call_id=?',(cid,)).fetchone()[0]==5
        assert conn.execute('SELECT COUNT(*) FROM turn_attempts WHERE call_id=?',(cid,)).fetchone()[0]==5


def test_default_db_path_is_independent_of_process_working_directory(tmp_path):
    import json
    import os
    import shutil
    import subprocess
    import sys
    copied=tmp_path/'project'/'backend';copied.mkdir(parents=True)
    for name in ('main.py','conversation.py','normalizer.py','scenarios.py','intent_classifier.py','entity_extractor.py','risk_detector.py','dialogue_manager.py','response_generator.py'):
        shutil.copy2(Path(main.__file__).parent/name,copied/name)
    script='import sys,json;sys.path.insert(0,sys.argv[1]);from main import DB_PATH,app;from fastapi.testclient import TestClient;print(json.dumps({"db":str(DB_PATH),"calls":TestClient(app).get("/api/calls").json()}))'
    env={k:v for k,v in os.environ.items() if k!='ANSIMON_DB'}
    first=subprocess.run([sys.executable,'-c',script,str(copied)],cwd=tmp_path,env=env,capture_output=True,text=True)
    assert first.returncode==0,first.stderr
    db_path=copied/'ansimon.db'
    assert json.loads(first.stdout)['db']==str(db_path.resolve())
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO calls(resident_id,started_at,ended_at,status,summary) VALUES(1,?,?,'declined','보존 기록')",(main.now(),main.now()))
    elsewhere=tmp_path/'other';elsewhere.mkdir()
    second=subprocess.run([sys.executable,'-c',script,str(copied)],cwd=elsewhere,env=env,capture_output=True,text=True)
    assert second.returncode==0,second.stderr
    result=json.loads(second.stdout)
    assert result['db']==str(db_path.resolve())
    assert result['calls'][0]['summary']=='보존 기록'
