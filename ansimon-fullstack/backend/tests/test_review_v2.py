import pytest,json
from review import build,degree
from dialogue_manager import transition
from fastapi.testclient import TestClient
import main
@pytest.mark.parametrize('text,score',[('오늘만 조금 불편해',1),('여러 날 계속 불편해',2),('일상생활이 어려워 도움이 필요해',3),('별로야',None)])
def test_degree(text,score):assert degree(text)==score
@pytest.mark.parametrize('text,state',[('119 불러줘','confirmed'),('구급차 보내줘','confirmed'),('응급차 좀 불러주세요','confirmed'),('숨을 못 쉬겠어','confirmed'),('119','possible')])
def test_risk(text,state):
 s,r=transition({'index':0,'review_version':'review-v2'},text)
 assert s['emergency_state']==state and s['count']==0
 assert r['action']=='safety_pause' and '실제 신고' in r['reply']
 s,r=transition(s,'모르겠어',source='stt_error');assert s['count']==0 and s['safety_guidance_provided']
@pytest.mark.parametrize('text',['119 부를 정도는 아니야','어제 119를 불렀어','뉴스에서 구급차를 봤어','119가 무슨 번호야?'])
def test_non_current(text):
 s,r=transition({'index':0,'review_version':'review-v2'},text)
 assert s.get('emergency_state','none')=='none'
def test_partial_and_missing():
 items={k:{'score':0,'classification':'positive','evidence':'괜찮아','reason':None} for k in ['condition','meal','sleep','medicine','mood']}
 a=build({'review_items':items});assert a['score']==0 and a['confirmed_count']==5
 items['sleep']={'score':None,'classification':'unknown','reason':'interpretation'}
 a=build({'review_items':items});assert a['confirmed_count']==4 and a['grade']=='확인된 범위에서 특이 표현 없음'
 items['sleep']={'score':None,'classification':'negative','reason':'degree'}
 assert build({'review_items':items})['grade']=='정보 부족'
 items['condition']['score']=3;assert build({'review_items':items})['grade']=='우선 확인'
 assert build({})['score'] is None

def test_api_severity_prompt_storage_and_finish():
 c=TestClient(main.app);cid=c.post('/api/residents/1/calls').json()['id']
 for index,text in enumerate(['안 아파','밥 먹었어','잘 잤어','먹는 약 없어','별로야']):
  r=c.post(f'/api/calls/{cid}/turns',json={'engine':'hybrid','answer':text,'index':index,'attempt':0});assert r.status_code==201,r.text
 assert r.json()['count']==4
 r=c.post(f'/api/calls/{cid}/turns',json={'engine':'hybrid','answer':'오늘만 잠깐 가볍게 그래','index':4,'attempt':1});assert r.status_code==201
 assert r.json()['finished']
 assert c.post(f'/api/calls/{cid}/finish',json={'status':'completed'}).status_code==200
 a=c.get(f'/api/calls/{cid}').json()['assessment'];assert a['score']==1 and a['grade']=='추가 확인'
 main.init_db();assert c.get(f'/api/calls/{cid}').json()['assessment']==a
 assert c.post('/api/residents/2/decline').status_code==201
 assert c.get('/api/calls?resident_id=2').json()[0]['assessment']['score'] is None
@pytest.mark.parametrize('text,reason',[('모르겠어','self_unknown'),('zzzzz','interpretation')])
def test_reasons(text,reason):
 s,r=transition({'index':0,'review_version':'review-v2'},text)
 assert s['review_items']['condition']['reason']==reason

def test_stt_event_does_not_create_fake_answer_or_advance():
 c=TestClient(main.app);cid=c.post('/api/residents/1/calls').json()['id']
 assert c.post(f'/api/calls/{cid}/input-events',json={'source':'stt_error','message':'권한 거부','index':0,'attempt':0}).status_code==200
 d=c.get(f'/api/calls/{cid}').json();assert d['turns']==[] and d['dialogue_state']['count']==0
 assert d['assessment']['items'][0]['reason']=='stt_error'

def test_degree_unknown_bound_and_synonyms():
 for text in ['별로야','안 좋아']:
  s,r=transition({'index':4,'review_version':'review-v2'},text)
  assert s['index']==4 and s['review_items']['mood']['score'] is None
  for _ in range(2):s,r=transition(s,'잘 모르겠어')
  assert s['finished'] and build(s)['grade']=='정보 부족'

def test_legacy_snapshot_and_cross_version_sort():
 from priority import sort_key
 c=TestClient(main.app);cid=c.post('/api/residents/1/decline').json()['id']
 with main.db(write=True) as db:db.execute('DELETE FROM call_reviews WHERE call_id=?',(cid,))
 main.init_db();a=c.get(f'/api/calls/{cid}').json()['assessment'];assert a['version']=='legacy-v1' and a['score']==20
 main.init_db();assert c.get(f'/api/calls/{cid}').json()['assessment']==a
 assert sort_key({'assessment':{'version':'legacy-v1','urgent':True,'score':100}})>sort_key({'assessment':{'version':'review-v2','urgent':False,'score':15}})
@pytest.mark.parametrize('text,urgent',[('119 불러주지마',False),('119 부를 정도는 아니지만 숨을 못 쉬겠어',True)])
def test_request_denial_does_not_mask_other_danger(text,urgent):
 from risk_detector import detect
 assert detect(text)['urgent']==urgent

def test_health_checks_new_review_storage():
 with main.db(write=True) as db:db.execute('DROP TABLE call_reviews')
 assert TestClient(main.app).get('/api/health').status_code==503
