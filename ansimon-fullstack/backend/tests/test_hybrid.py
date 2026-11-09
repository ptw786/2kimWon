import pytest
from fastapi.testclient import TestClient
import main
from dialogue_manager import transition

@pytest.mark.parametrize('topic,text,expected',[
('meal','응','positive'),('meal','아니','negative'),('sleep','응','positive'),
('meal','그럭저럭','neutral'),('meal','밥 먹었어','positive'),('meal','밥 못 먹었어','negative'),
('meal','안 먹은 건 아니야','positive'),('meal','아침만 먹었어','neutral'),
('meal','이따 먹을 거야','unknown'),('meal','어제는 먹었어','unknown'),
('meal','딸이 반찬을 갖다 줬어','unknown'),('meal','밥도 먹고 약도 먹었어','positive'),
('medicine','약 먹었는지 모르겠어','unknown'),('medicine','약은 안 먹어도 된대','neutral'),
('sleep','어제 잠을 설쳤어','negative'),('sleep','새벽에 자꾸 깼어','negative'),
('sleep','그냥 그랬어','neutral'),('mood','외로워','negative'),
('meal','손자가 놀러 왔어','unknown'),('meal','오늘은 말하기 싫어','unknown'),
('meal','뭐라고?','unknown'),('meal','잘 안 들려','unknown'),
('meal','밥 먹었어. 아니, 안 먹었어','negative'),('condition','허리가 아파','negative'),
('meal','며칠째 밥을 못 먹어','negative'),('meal','의미없는말','unknown'),
('condition','안 아파','positive'),('mood','기분 좋아','positive'),
('medicine','먹는 약 없어','neutral'),('sleep','잘 잤어','positive'),
])
def test_examples(topic,text,expected):
 i=[t for t,_ in main.QUESTIONS].index(topic)
 _,r=transition({'index':i},text)
 assert r['classification']==expected

@pytest.mark.parametrize('text,urgent', [('숨쉬기 힘들어',True),('가슴이 심하게 아파',True),('죽고 싶어',True),('죽고 싶은 건 아니야',False),('작년에 가슴이 심하게 아파 쓰러졌어',False),('뉴스에서 죽고 싶다고 했대',False)])
def test_safety(text,urgent):
 s,r=transition({'index':0},text)
 assert r['risk']['urgent']==urgent
 if urgent:assert s['index']==0 and r['action']=='safety_pause'

def test_api_persistence_retry_finish():
 c=TestClient(main.app);cid=c.post('/api/residents/1/calls').json()['id']
 for i,a in enumerate(['응','밥 먹었어','잘 잤어','먹는 약 없어','기분 좋아']):
  body={'answer':a,'index':i,'attempt':0,'engine':'hybrid','source':'text'}
  r=c.post(f'/api/calls/{cid}/turns',json=body);assert r.status_code==201,r.text
  assert c.post(f'/api/calls/{cid}/turns',json=body).json()==r.json()
  d=c.get(f'/api/calls/{cid}').json();assert d['dialogue_state']['count']==i+1
 assert c.post(f'/api/calls/{cid}/finish',json={'status':'completed'}).status_code==200
 assert len(c.get(f'/api/calls/{cid}').json()['analysis_events'])==5
 assert c.get('/api/dashboard').status_code==200
 assert c.get('/api/calls').json()[0]['status']=='completed'

def test_unknown_story_limits_and_inputs():
 s={'index':1}
 for _ in range(2):
  s,r=transition(s,'손자가 놀러 왔어');assert r['action']=='daily_chat'
 for _ in range(3):s,r=transition(s,'의미없는말')
 assert s['index']==2 and 'meal' in s['unconfirmed']
 c=TestClient(main.app);cid=c.post('/api/residents/1/calls').json()['id']
 assert c.post(f'/api/calls/{cid}/turns',json={'answer':' ','engine':'hybrid'}).status_code==422
 for i,source in enumerate(['stt_error','silence']):
  r=c.post(f'/api/calls/{cid}/turns',json={'answer':'인식 실패' if i==0 else '침묵','engine':'hybrid','source':source,'index':0,'attempt':i})
  assert r.status_code==201 and source in r.json()['intents']
 assert c.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'}).status_code==200
 assert len(c.get(f'/api/calls/{cid}').json()['analysis_events'])==2

def test_multi_correction_past_and_resume():
 s,r=transition({'index':1},'밥은 먹었고 약도 먹었는데 잠을 못 잤어')
 assert set(r['facts'])=={'meal','medicine','sleep'}
 assert r['facts']['sleep']['classification']=='negative'
 s,r=transition({'index':1},'밥 먹었어. 아니, 안 먹었어')
 assert r['facts']['meal']['classification']=='negative'
 s,r=transition({'index':0},'작년에 가슴이 심하게 아파 쓰러졌어')
 assert r['action']=='risk_confirmation'
 s,r=transition(s,'응')
 assert r['action']=='safety_pause' and s['index']==0
 _,r=transition({'index':0},'죽고 싶은 건 아니지만 숨쉬기 힘들어')
 assert r['risk']['urgent']

def test_saved_state_restored_after_restart_and_failure(monkeypatch):
 c=TestClient(main.app);cid=c.post('/api/residents/1/calls').json()['id']
 body={'answer':'손자가 놀러 왔어','engine':'hybrid','index':0,'attempt':0}
 assert c.post(f'/api/calls/{cid}/turns',json=body).status_code==201
 before=c.get(f'/api/calls/{cid}').json()['dialogue_state']
 main.init_db()
 assert c.get(f'/api/calls/{cid}').json()['dialogue_state']==before
 original=main.transition
 def broken(*args):raise __import__('sqlite3').OperationalError('locked')
 monkeypatch.setattr(main,'transition',broken)
 body.update(answer='몸 괜찮아',attempt=1)
 assert c.post(f'/api/calls/{cid}/turns',json=body).status_code==500
 assert c.get(f'/api/calls/{cid}').json()['dialogue_state']==before
 monkeypatch.setattr(main,'transition',original)
 assert c.post(f'/api/calls/{cid}/turns',json=body).status_code==201

def test_legacy_call_upgrade_keeps_previous_answers():
 c=TestClient(main.app);cid=c.post('/api/residents/1/calls').json()['id']
 assert c.post(f'/api/calls/{cid}/turns',json={'answer':'안 아파'}).status_code==201
 r=c.post(f'/api/calls/{cid}/turns',json={'answer':'밥 먹었어','engine':'hybrid','index':1,'attempt':0})
 assert r.status_code==201
 assert r.json()['dialogue_state']['facts']['condition']['evidence']=='안 아파'
 assert 'condition' in r.json()['dialogue_state']['completed']
