import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import main
from scheduling import next_run, enqueue, stamp, KST
from import_taewon import import_database
from taewon_rules import assess as legacy_assess


def client():return TestClient(main.app)
def schedule(c,rid=1,at='10:00'):
 r=c.post('/api/schedules',json={'resident_id':rid,'call_time':at});assert r.status_code==201,r.text
 return r.json()['id']
def due(sid):
 now=datetime.now(timezone.utc)
 with main.db(write=True) as conn:
  conn.execute('UPDATE care_schedules SET next_at=? WHERE id=?',(stamp(now-timedelta(days=4)),sid))
  enqueue(conn,now)
 with main.db() as conn:return conn.execute("SELECT id FROM scheduled_calls WHERE schedule_id=? AND state='pending'",(sid,)).fetchone()[0]
def answer(c,cid,index,text):
 r=c.post(f'/api/calls/{cid}/turns',json={'engine':'hybrid','answer':text,'index':index,'attempt':0});assert r.status_code==201,r.text
 return r.json()
def complete(c,texts):
 cid=c.post('/api/residents/1/calls').json()['id']
 for i,t in enumerate(texts):answer(c,cid,i,t)
 assert c.post(f'/api/calls/{cid}/finish',json={'status':'completed'}).status_code==200
 return cid

@pytest.mark.parametrize('invalid',['25:00','1:00','12:60','','-1:00','12:00:00'])
def test_time_validation(invalid):
 assert client().post('/api/schedules',json={'resident_id':1,'call_time':invalid}).status_code==422


def test_schedule_crud_duplicates_cors_and_preservation():
 c=client();sid=schedule(c)
 assert c.post('/api/schedules',json={'resident_id':1,'call_time':'10:00'}).status_code==409
 assert c.post('/api/schedules',json={'resident_id':999,'call_time':'10:00'}).status_code==404
 assert c.post('/api/schedules',json={'resident_id':1,'call_time':'11:00','recipient':'   '}).status_code==422
 qid=due(sid)
 r=c.options(f'/api/schedules/{sid}',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'PUT'})
 assert r.status_code==200 and 'PUT' in r.headers['access-control-allow-methods']
 assert c.put(f'/api/schedules/{sid}',json={'resident_id':2,'call_time':'12:00'}).status_code==200
 with main.db() as conn:assert conn.execute('SELECT state FROM scheduled_calls WHERE id=?',(qid,)).fetchone()[0]=='canceled'
 assert c.delete(f'/api/schedules/{sid}').status_code==200
 assert c.get('/api/schedules').json()['schedules']==[]
 assert c.put(f'/api/schedules/{sid}',json={'resident_id':1,'call_time':'11:00'}).status_code==404


def test_due_concurrency_latest_catchup_and_next_day():
 c=client();sid=schedule(c)
 with main.db(write=True) as conn:conn.execute('UPDATE care_schedules SET next_at=? WHERE id=?',('2000-01-01T01:00:00+00:00',sid))
 now=datetime(2026,11,13,3,0,tzinfo=timezone.utc)
 def tick(_):
  with main.db(write=True) as conn:enqueue(conn,now)
 with ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(tick,range(10)))
 with main.db() as conn:
  assert conn.execute('SELECT COUNT(*) FROM scheduled_calls').fetchone()[0]==1
  assert conn.execute('SELECT scheduled_at FROM scheduled_calls').fetchone()[0]=='2026-11-13T01:00:00+00:00'
  assert conn.execute('SELECT next_at FROM care_schedules').fetchone()[0]=='2026-11-14T01:00:00+00:00'
 assert next_run(datetime(2026,11,13,0,59,tzinfo=timezone.utc),'10:00').date().isoformat()=='2026-11-13'
 assert next_run(datetime(2026,11,13,1,0,tzinfo=timezone.utc),'10:00').date().isoformat()=='2026-11-14'


def test_scheduled_call_atomic_claim_retry_resume_and_finish():
 c=client();sid=schedule(c);qid=due(sid)
 bad=c.post('/api/residents/2/calls',json={'queue_id':qid})
 assert bad.status_code==409 and c.get('/api/calls').json()==[]
 headers={'Idempotency-Key':'scheduled-call'}
 r=c.post('/api/residents/1/calls',json={'queue_id':qid},headers=headers);assert r.status_code==201
 cid=r.json()['id']
 assert c.post('/api/residents/1/calls',json={'queue_id':qid},headers=headers).json()['id']==cid
 assert c.post('/api/residents/1/calls',json={},headers=headers).status_code==409
 assert c.get(f'/api/calls/{cid}').json()['queue_id']==qid
 assert c.delete(f'/api/schedules/{sid}').status_code==409
 assert c.post('/api/residents/1/decline',json={'queue_id':qid}).status_code==409
 answer(c,cid,0,'응')
 main.init_db()
 assert c.get(f'/api/calls/{cid}').json()['dialogue_state']['count']==1
 assert c.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'}).status_code==200
 assert c.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'}).status_code==200
 assert c.get('/api/schedules').json()['pending']==[]
 assert c.post('/api/residents/1/calls',json={'queue_id':qid}).status_code==409
 assert c.delete(f'/api/schedules/{sid}').status_code==200
 assert c.get(f'/api/calls/{cid}').json()['status']=='interrupted'


def test_decline_concurrency_no_duplicate_occurrence():
 c=client();qid=due(schedule(c))
 def decline(_):return client().post('/api/residents/1/decline',json={'queue_id':qid}).status_code
 with ThreadPoolExecutor(max_workers=4) as pool:statuses=list(pool.map(decline,range(4)))
 assert statuses.count(201)==1 and statuses.count(409)==3
 assert len(c.get('/api/calls').json())==1
 assert c.get('/api/calls').json()[0]['assessment']['score']==20

@pytest.mark.parametrize('texts,score',[
 (['괜찮아요','밥 못 먹었어','잠을 못 잤어','약은 챙겼어요','기분 좋아'],20),
 (['안 아파','밥 먹었어','잘 잤어','먹는 약 없어','기분 좋아'],0),
 (['피곤해','밥 먹었어','잘 잤어','약 먹었어','기분 좋아'],9),
 (['피곤해','밥 먹었어','잘 잤어','약 먹었어','기분은 괜찮아요'],9),
 (['안 아파','밥 먹었어. 아니, 안 먹었어','잘 잤어','약 먹었어','기분 좋아'],12),
 (['안 아파','안 먹은 건 아니야','잘 잤어','약은 안 먹어도 된대','기분 좋아'],0),
])
def test_evidence_scoring_consistency(texts,score):
 c=client();cid=complete(c,texts)
 assert c.get(f'/api/calls/{cid}').json()['assessment']['score']==score
 assert c.get('/api/dashboard').json()['residents'][0]['assessment']['score']==score
 assert c.get('/api/calls?sort=priority').json()[0]['assessment']['score']==score

@pytest.mark.parametrize('text,urgent',[
 ('119 불러줘',True),('숨쉬기 힘들어',True),('가슴이 심하게 아프지 않아',False),
 ('뉴스에서 119 불러줘라고 했어',False),('죽고 싶은 건 아니, 숨쉬기 힘들어',True),
 ('작년에 숨쉬기 힘들었어',False),('약은 안 먹어도 된대',False)
])
def test_unified_risk_rules(text,urgent):
 from risk_detector import detect
 assert detect(text)['urgent']==urgent


def test_urgent_saved_as_attempt_still_scores_100():
 c=client();cid=c.post('/api/residents/1/calls').json()['id']
 answer(c,cid,0,'119 불러줘')
 assert c.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'}).status_code==200
 d=c.get(f'/api/calls/{cid}').json()
 assert d['turns']==[] and d['assessment']['score']==100


def create_legacy(path):
 c=sqlite3.connect(path)
 c.executescript('''CREATE TABLE schedules(id INTEGER PRIMARY KEY,recipient TEXT,call_time TEXT,next_at TEXT);
 CREATE TABLE queue(id INTEGER PRIMARY KEY,schedule_id INTEGER,scheduled_at TEXT,completed INTEGER);
 CREATE TABLE records(id TEXT PRIMARY KEY,date TEXT,status TEXT,summary TEXT,recipient TEXT,scheduled_at TEXT,assessment TEXT,score INTEGER);
 CREATE TABLE legacy_statistics(region TEXT,elder_count INTEGER);''')
 c.execute('INSERT INTO schedules VALUES(1,?,?,?)',('가상 별칭','10:00','2026-11-14T10:00:00+09:00'))
 c.execute('INSERT INTO queue VALUES(1,1,?,0)',('2026-11-13T10:00:00+09:00',))
 c.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?)',('11111111-1111-1111-1111-111111111111','2026-11-12T10:00:00+09:00','수신 거절','이전 기록','가상 별칭',None,json.dumps(legacy_assess([],True)),20))
 c.execute('INSERT INTO legacy_statistics VALUES(?,?)',('가상 지역',5));c.commit();c.close()


def test_migration_readonly_idempotent_unmapped_and_conflict(tmp_path):
 src=tmp_path/'source.sqlite3';create_legacy(src);before=src.read_bytes();target=main.DB_PATH
 dry=import_database(src,target,True);assert dry['source_counts']['records']==1 and src.read_bytes()==before
 native=client().post('/api/residents/1/decline').json()['id']
 first=import_database(src,target);second=import_database(src,target)
 assert first['imported_records']==second['imported_records']==1
 assert first['archive_rows']==second['archive_rows']==4 and src.read_bytes()==before
 c=client();records=c.get('/api/calls').json();assert len(records)==2
 imported=next(r for r in records if r['source']=='taewon')
 d=c.get('/api/imported-records/'+imported['id'][7:]).json();assert d['summary']=='이전 기록'
 assert c.get(f'/api/calls/{native}').json()['status']=='declined'
 sch=c.get('/api/schedules').json()['schedules'][0]
 assert sch['resident_id'] is None
 assert c.put(f"/api/schedules/{sch['id']}",json={'resident_id':2,'recipient':sch['recipient'],'call_time':sch['call_time']}).status_code==200
 assert c.get('/api/schedules').json()['pending'][0]['resident_id']==2
 with sqlite3.connect(src) as conn:conn.execute("UPDATE records SET summary='변경된 기록'")
 with pytest.raises(ValueError):import_database(src,target)
 assert c.get('/api/imported-records/'+imported['id'][7:]).json()['summary']=='이전 기록'
 assert list(tmp_path.glob('source.sqlite3.backup-*')) and list(tmp_path.glob('test.db.backup-*'))


def test_migration_invalid_or_same_paths(tmp_path):
 src=tmp_path/'source.sqlite3';create_legacy(src)
 with pytest.raises(ValueError):import_database(src,src)
 with pytest.raises(ValueError):import_database(tmp_path/'missing',main.DB_PATH)


def test_real_lifespan_worker_enqueue():
 # Actual scheduler task starts/stops with ASGI lifespan; no orphan thread.
 with TestClient(main.app) as c:
  sid=schedule(c)
  with main.db(write=True) as conn:conn.execute('UPDATE care_schedules SET next_at=? WHERE id=?',('2000-01-01T01:00:00+00:00',sid))
  deadline=time.monotonic()+4
  while time.monotonic()<deadline:
   with main.db() as conn:count=conn.execute('SELECT COUNT(*) FROM scheduled_calls').fetchone()[0]
   if count:break
   time.sleep(.05)
  assert count==1

@pytest.mark.parametrize('topic,text,category',[
 ('condition','어제 피곤했어','unknown'),('medicine','딸이 약 먹었어','unknown'),
 ('mood','기분이 좋지 않아','negative'),('condition','괜찮지 않아','negative'),
 ('sleep','어제 잠을 설쳤어','negative'),('sleep','작년에 잠을 못 잤어','unknown'),
])
def test_subject_time_and_negation_guard(topic,text,category):
 from dialogue_manager import transition
 index=[k for k,_ in main.QUESTIONS].index(topic)
 _,result=transition({'index':index},text)
 assert result['classification']==category
