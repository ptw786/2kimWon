import json
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import main
from conversation import QUESTIONS
from dialogue_manager import transition
from scenarios import CLARIFY

@pytest.mark.parametrize('topic,text,category',[
 ('sleep','어','positive'),('sleep','어.','positive'),('sleep','네네','positive'),
 ('sleep','잤어','neutral'),('sleep','잠은 잤어','neutral'),('sleep','조금 잤어','neutral'),
 ('sleep','잘 잤어','positive'),('sleep','못 잤어','negative'),
 ('mood','좋아','positive'),('mood','좋아요','positive'),('mood','기분은 좋아','positive'),
 ('mood','별로야','negative'),('mood','별로 안 좋아','negative'),('mood','안 좋아','negative'),
 ('mood','좋은 건 아니야','negative'),('mood','기분은 별로야','negative'),
 ('mood','그냥 그래','neutral'),('mood','안 좋은 건 아니야','neutral'),
 ('condition','별로야','negative'),('condition','좋아','positive'),
 ('meal','좋아','unknown'),('medicine','좋아','unknown'),
 ('condition','응','unknown'),('mood','응','unknown'),('mood','아니','unknown'),
])
def test_contextual_short_answers(topic,text,category):
 index=[k for k,_ in QUESTIONS].index(topic)
 s,r=transition({'index':index},text)
 assert r['classification']==category
 if category!='unknown':assert s['count']==index+1

@pytest.mark.parametrize('topic', ['condition','meal','sleep','medicine','mood'])
def test_old_choice_questions_do_not_infer_yes(topic):
 index=[k for k,_ in QUESTIONS].index(topic)
 s,r=transition({'index':index,'question':'좋으세요, 아니면 불편하세요?'},'어')
 assert s['index']==index and r['classification']=='unknown'
 assert s['question']==CLARIFY[topic] and '아니면' not in s['question']
 s,r=transition(s,'어')
 assert r['classification']=='positive' and s['index']==index+1


def test_daily_ack_does_not_confirm_health_and_sleep_has_no_invented_quality():
 s,r=transition({'index':0,'question':'그 이야기를 조금 더 들려주시겠어요?'},'어')
 assert r['classification']=='unknown' and s['index']==0
 s,r=transition({'index':2},'잤어')
 assert r['facts']['sleep']['quality']=='unconfirmed'
 assert '편히 주무셨다니' not in r['reply']


def test_api_actual_questions_restore_and_idempotency():
 c=TestClient(main.app);cid=c.post('/api/residents/1/calls').json()['id']
 first={'answer':'무슨말인지모르겠어','engine':'hybrid','index':0,'attempt':0}
 r=c.post(f'/api/calls/{cid}/turns',json=first);assert r.status_code==201
 assert r.json()['next_question']==CLARIFY['condition']
 body={**first,'answer':'어','attempt':1}
 r=c.post(f'/api/calls/{cid}/turns',json=body);assert r.status_code==201
 assert r.json()['count']==1
 assert c.post(f'/api/calls/{cid}/turns',json=body).json()==r.json()
 d=c.get(f'/api/calls/{cid}').json()
 assert d['attempts'][0]['question']==QUESTIONS[0][1]
 assert d['attempts'][1]['question']==d['turns'][0]['question']==CLARIFY['condition']
 main.init_db();assert c.get(f'/api/calls/{cid}').json()['dialogue_state']['count']==1


def test_old_reservation_database_migrates_without_losing_calls():
 c=TestClient(main.app)
 cid=c.post('/api/residents/1/calls',headers={'Idempotency-Key':'old-call'}).json()['id']
 c.post(f'/api/calls/{cid}/turns',json={'engine':'hybrid','answer':'안 아파','index':0,'attempt':0})
 c.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'})
 original=c.get(f'/api/calls/{cid}').json()
 with main.db(write=True) as conn:
  conn.executescript('''CREATE TABLE care_schedules(id INTEGER PRIMARY KEY,recipient TEXT);
   CREATE TABLE scheduled_calls(id INTEGER PRIMARY KEY,schedule_id INTEGER REFERENCES care_schedules(id),call_id INTEGER REFERENCES calls(id),recipient TEXT,scheduled_at TEXT);''')
  conn.execute('INSERT INTO care_schedules VALUES(1,?)',('과거 예약 별칭',))
  conn.execute('INSERT INTO scheduled_calls VALUES(1,1,?,?,?)',(cid,'과거 통화 별칭','2026-11-10T01:00:00+00:00'))
  conn.execute('INSERT INTO imported_records VALUES(?,?,?)',('keep',json.dumps({'id':'keep','date':main.now(),'status':'수신 거절','summary':'보존','assessment':{'score':20,'grade':'우선 확인'}}),main.now()))
  conn.execute('INSERT INTO legacy_archive VALUES(?,?,?)',('stats','statistics','{"count":17}'))
 main.init_db()
 restored=c.get(f'/api/calls/{cid}').json()
 assert restored['turns']==original['turns'] and restored['attempts']==original['attempts']
 assert restored['summary']==original['summary'] and restored['assessment']==original['assessment']
 assert restored['recipient']=='과거 통화 별칭' and restored['scheduled_at']=='2026-11-10T01:00:00+00:00'
 for _ in range(2):main.init_db()
 with main.db() as conn:
  assert not conn.execute("SELECT name FROM sqlite_master WHERE name IN ('scheduled_calls','care_schedules')").fetchall()
  assert conn.execute('SELECT COUNT(*) FROM imported_records').fetchone()[0]==1
  assert conn.execute('SELECT COUNT(*) FROM legacy_archive').fetchone()[0]==1
  assert not conn.execute('PRAGMA foreign_key_check').fetchall()
 assert c.get('/api/health').status_code==200
 snapshots=list(main.DB_PATH.parent.glob(main.DB_PATH.name+'.backup-*'))
 assert snapshots
 found=False
 for p in snapshots:
  with sqlite3.connect(p) as conn:
   if conn.execute("SELECT 1 FROM sqlite_master WHERE name='scheduled_calls'").fetchone():
    assert conn.execute('SELECT COUNT(*) FROM calls').fetchone()[0]==1;found=True
 assert found,'The pre-drop SQLite backup must include the original reservation tables'


def test_removed_apis_do_not_create_calls_or_start_worker():
 c=TestClient(main.app)
 for method in ('get','post','put','delete'):
  assert getattr(c,method)('/api/schedules').status_code==404
 assert c.post('/api/residents/1/calls',json={'queue_id':1}).status_code==422
 assert c.post('/api/residents/1/decline',json={'queue_id':1}).status_code==422
 assert c.get('/api/calls').json()==[]
 with TestClient(main.app) as running:
  assert running.get('/api/health').status_code==200
  with main.db() as conn:assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name IN ('care_schedules','scheduled_calls')").fetchall()


def test_reservation_drop_failure_rolls_back_metadata_and_tables():
 from schema_migrations import migrate
 cid=TestClient(main.app).post('/api/residents/1/decline').json()['id']
 with main.db(write=True) as conn:
  conn.executescript('''CREATE TABLE care_schedules(id INTEGER PRIMARY KEY);
   CREATE TABLE scheduled_calls(id INTEGER PRIMARY KEY,call_id INTEGER,recipient TEXT,scheduled_at TEXT);''')
  conn.execute('INSERT INTO care_schedules VALUES(1)')
  conn.execute('INSERT INTO scheduled_calls VALUES(1,?,?,?)',(cid,'보존 별칭','2026-01-01'))
  conn.commit()
  def deny_parent_drop(action,name,*args):
   return sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_DROP_TABLE and name=='care_schedules' else sqlite3.SQLITE_OK
  conn.set_authorizer(deny_parent_drop)
  with pytest.raises(sqlite3.DatabaseError):migrate(conn)
  conn.set_authorizer(None)
  assert conn.execute('SELECT recipient FROM calls WHERE id=?',(cid,)).fetchone()[0] is None
  assert conn.execute('SELECT COUNT(*) FROM scheduled_calls').fetchone()[0]==1
  assert conn.execute('SELECT COUNT(*) FROM care_schedules').fetchone()[0]==1
