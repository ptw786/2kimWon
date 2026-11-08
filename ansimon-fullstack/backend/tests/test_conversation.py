from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sqlite3

from fastapi.testclient import TestClient
import pytest
import main
from conversation import assess, summary_for, QUESTIONS, EMERGENCY_GUIDANCE


@pytest.mark.parametrize('topic,text,classification', [
    ('meal','밥 먹었어','positive'),
    ('meal','밥 안 먹었어','negative'),
    ('condition','안 아파','positive'),
    ('condition','많이 아파','negative'),
    ('sleep','잘 잤어','positive'),
    ('sleep','잠을 못 잤어','negative'),
    ('medicine','약 먹었어','positive'),
    ('medicine','먹는 약 없어','neutral'),
    ('mood','기분 좋아','positive'),
    ('mood','외로워','negative'),
    ('condition','의미 없는 답변','unknown'),
    ('condition','','unknown'),
    ('condition','아프지 않아요','positive'),
    ('condition','통증이 없어요','positive'),
    ('condition','안 아픈데 어지러워','negative'),
    ('condition','기분은 좋은데 몸이 아파','negative'),
    ('meal','밥을 못 먹었어요','negative'),
    ('meal','조금 먹었어요','neutral'),
    ('meal','식사 안 했어요','negative'),
    ('meal','안녕','unknown'),
    ('meal','잠을 잘 잤어요','unknown'),
    ('meal','바나나','unknown'),
    ('sleep','잠을 잘 못 잤어요','negative'),
    ('sleep','보통이에요','neutral'),
    ('medicine','약 안 먹었어','negative'),
    ('medicine','약을 먹지 않았어요','negative'),
    ('medicine','약이 없어서 못 먹었어','negative'),
    ('medicine','복용하는 약이 없어요','neutral'),
    ('medicine','잘 모르겠어요','unknown'),
    ('mood','외롭지 않아요','positive'),
    ('mood','불안하지 않아요','positive'),
    ('mood','기분은 좋은데 외로워','negative'),
    ('mood','그저 그래요','neutral'),
    ('mood','ㅋㅋㅋㅋ 1234 abc','unknown'),
    ('medicine','약 안 먹어도 돼요','neutral'),
    ('medicine','밥 먹었어','unknown'),
    ('meal','약 먹었어','unknown'),
    ('meal','밥 안 먹은 건 아니야','unknown'),
    ('condition','안 아프진 않아','negative'),

])
def test_topic_specific_classification(topic,text,classification):
    result=assess(topic,text)
    assert result.classification==classification
    assert result.reply
    assert not result.emergency


@pytest.mark.parametrize('topic,text,reply', [
    ('meal','오늘 밥을 못 먹었어.','아직 식사를 못 하셨군요. 식사를 챙기실 수 있으면 좋겠어요.'),
    ('sleep','잠을 잘 잤어.','편히 주무셨다니 다행이에요.'),
    ('condition','오늘 몸이 아파.','몸이 불편하시군요. 증상이 심하거나 계속되면 도움을 요청해 주세요.'),
    ('medicine','먹는 약 없어','드시는 약이 없으시군요. 알려주셔서 감사합니다.'),
])
def test_contextual_replies(topic,text,reply):
    assert assess(topic,text).reply==reply


@pytest.mark.parametrize('text',['숨을 못 쉬겠어','호흡 곤란이 있어','가슴이 너무 아파','쓰러졌어 살려줘','죽고 싶어'])
def test_urgent_words_give_direct_guidance(text):
    result=assess('meal',text)
    assert result.emergency and result.classification=='negative'
    assert result.reply==EMERGENCY_GUIDANCE
    assert '직접 119' in result.reply and '실제 119 신고를 하지 않습니다' in result.reply


@pytest.mark.parametrize('text',['숨이 안 차요','호흡 곤란이 없어요','가슴이 안 아파','죽고 싶지 않아요'])
def test_negated_urgent_words_do_not_trigger(text):
    assert not assess('condition',text).emergency


def start(client):
    response=client.post('/api/residents/1/calls')
    assert response.status_code==201
    return response.json()['id']


def submit(client,cid,index,attempt,text,key=None):
    return client.post(f'/api/calls/{cid}/turns',json={'index':index,'attempt':attempt,'answer':text},headers={'Idempotency-Key':key} if key else {})


def test_exact_questions_and_required_sentences_over_real_api():
    client=TestClient(main.app)
    assert client.get('/api/questions').json()==[{'topic':topic,'text':text} for topic,text in QUESTIONS]
    cid=start(client)
    for index,(text,classification) in enumerate([('안 아파','positive'),('밥 안 먹었어','negative'),('잠을 못 잤어','negative'),('먹는 약 없어','neutral'),('외로워','negative')]):
        response=submit(client,cid,index,0,text)
        assert response.status_code==201
        body=response.json()
        assert body['count']==index+1 and body['classification']==classification
        assert body['classification_label'] in ('긍정','부정','중립','확인 불가')
    assert client.post(f'/api/calls/{cid}/finish',json={'status':'completed'}).status_code==200
    detail=client.get(f'/api/calls/{cid}').json()
    assert [turn['classification'] for turn in detail['turns']]==['positive','negative','negative','neutral','negative']
    assert len(detail['attempts'])==5


def test_unknown_two_reasks_then_one_unknown_turn():
    client=TestClient(main.app);cid=start(client)
    for attempt in range(3):
        response=submit(client,cid,0,attempt,'무의미 xyz '+str(attempt))
        assert response.status_code==201
        body=response.json()
        assert body['needs_retry']==(attempt<2)
        assert body['count']==(0 if attempt<2 else 1)
        state=client.get(f'/api/calls/{cid}').json()
        assert len(state['attempts'])==attempt+1
        assert len(state['turns'])==(0 if attempt<2 else 1)
        if attempt<2:
            assert state['dialogue_state']['attempt']==attempt+1
            assert state['dialogue_state']['question']==QUESTIONS[0][1]
    final=client.get(f'/api/calls/{cid}').json()
    assert final['turns'][0]['classification']=='unknown'
    assert final['dialogue_state']['index']==1
    finish=client.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'}).json()
    assert '무의미' not in finish['summary']
    assert '확인된 답변이 없습니다' in finish['summary']
    assert '확인 불가 항목: 건강 상태' in finish['summary']


def test_reask_answer_can_be_confirmed_and_replays_do_not_consume_retries():
    client=TestClient(main.app);cid=start(client)
    def unknown(_):return submit(client,cid,0,0,'qwerty',key='unknown-1')
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(unknown,range(4)))
    assert all(response.status_code==201 for response in responses)
    assert all(response.json()==responses[0].json() for response in responses)
    assert len(client.get(f'/api/calls/{cid}').json()['attempts'])==1
    assert submit(client,cid,0,0,'다른 답변').status_code==409
    assert submit(client,cid,0,2,'안 아파').status_code==409
    assert submit(client,cid,0,1,'안 아파',key='unknown-1').status_code==409
    good=submit(client,cid,0,1,'안 아파',key='confirmed-1')
    assert good.status_code==201 and good.json()['count']==1
    assert submit(client,cid,0,1,'안 아파',key='confirmed-1').json()==good.json()
    assert unknown(0).json()==responses[0].json()
    detail=client.get(f'/api/calls/{cid}').json()
    assert len(detail['attempts'])==2 and len(detail['turns'])==1
    assert detail['turns'][0]['answer']=='안 아파'
    summary=client.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'}).json()['summary']
    assert summary=='건강 상태: 안 아파'


def test_empty_answers_never_save_or_consume_attempts():
    client=TestClient(main.app);cid=start(client)
    for text in ('',' ','\t\n'):
        assert submit(client,cid,0,0,text).status_code==422
    detail=client.get(f'/api/calls/{cid}').json()
    assert detail['attempts']==detail['turns']==[]
    assert detail['dialogue_state']['attempt']==0


def test_all_unknown_can_complete_without_fabricated_summary():
    client=TestClient(main.app);cid=start(client)
    for index in range(5):
        for attempt in range(3):
            assert submit(client,cid,index,attempt,'xyz').status_code==201
    result=client.post(f'/api/calls/{cid}/finish',json={'status':'completed'})
    assert result.status_code==200
    assert 'xyz' not in result.json()['summary']
    detail=client.get(f'/api/calls/{cid}').json()
    assert len(detail['attempts'])==15 and len(detail['turns'])==5
    assert detail['dialogue_state']['finished']


def test_emergency_guidance_recorded_without_claiming_dispatch():
    client=TestClient(main.app);cid=start(client)
    body=submit(client,cid,0,0,'숨을 못 쉬겠어').json()
    assert body['emergency'] and not body['needs_retry']
    summary=client.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'}).json()['summary']
    assert '숨을 못 쉬겠어' in summary and '자동 신고 없음' in summary
    assert '신고 완료' not in summary


def test_database_failure_rolls_back_both_attempt_and_final_turn(monkeypatch):
    client=TestClient(main.app,raise_server_exceptions=False);cid=start(client)
    original_db=main.db
    class FailingConnection:
        def __init__(self,conn):self.conn=conn
        def execute(self,sql,*args):
            if sql.startswith('INSERT INTO turns('):raise sqlite3.OperationalError('simulated write failure')
            return self.conn.execute(sql,*args)
    @contextmanager
    def failing_db(write=False):
        with original_db(write=write) as conn:yield FailingConnection(conn)
    with monkeypatch.context() as patch:
        patch.setattr(main,'db',failing_db)
        assert submit(client,cid,0,0,'안 아파').status_code==500
    detail=client.get(f'/api/calls/{cid}').json()
    assert detail['turns']==detail['attempts']==[]
    assert submit(client,cid,0,0,'안 아파').json()['count']==1


def test_original_database_backup_and_non_destructive_migration(tmp_path,monkeypatch):
    path=tmp_path/'original.db'
    with sqlite3.connect(path) as c:
        c.executescript('''CREATE TABLE residents(id INTEGER PRIMARY KEY,name TEXT NOT NULL,age INTEGER NOT NULL,neighborhood TEXT NOT NULL,call_time TEXT NOT NULL);
        CREATE TABLE calls(id INTEGER PRIMARY KEY AUTOINCREMENT,resident_id INTEGER NOT NULL REFERENCES residents(id),started_at TEXT NOT NULL,ended_at TEXT,status TEXT NOT NULL,summary TEXT NOT NULL DEFAULT '');
        CREATE TABLE turns(id INTEGER PRIMARY KEY AUTOINCREMENT,call_id INTEGER NOT NULL REFERENCES calls(id),topic TEXT NOT NULL,question TEXT NOT NULL,answer TEXT NOT NULL,created_at TEXT NOT NULL);''')
        c.execute("INSERT INTO residents VALUES(1,'보존 어르신',78,'기존 지역','10:00')")
        c.execute("INSERT INTO calls VALUES(1,1,?,?,'completed','기존 요약 보존')",(main.now(),main.now()))
        c.execute("INSERT INTO turns VALUES(1,1,'condition','기존 질문','기존 답변',?)",(main.now(),))
    monkeypatch.setattr(main,'DB_PATH',path);main.init_db()
    detail=TestClient(main.app).get('/api/calls/1').json()
    assert detail['summary']=='기존 요약 보존'
    assert detail['turns'][0]['answer']=='기존 답변'
    assert detail['turns'][0]['classification']=='unclassified'
    assert detail['attempts']==[]
    backup=next(tmp_path.glob('original.db.backup-*'))
    with sqlite3.connect(backup) as c:
        assert c.execute('SELECT answer FROM turns').fetchone()[0]=='기존 답변'
        assert 'classification' not in {row[1] for row in c.execute('PRAGMA table_info(turns)')}


def test_unconfirmed_or_legacy_text_not_used_as_inferred_facts():
    turns=[{'topic':'condition','answer':'알수없는말','classification':'unknown'},
           {'topic':'meal','answer':'오래된말','classification':'unclassified'},
           {'topic':'medicine','answer':'먹는 약 없어','classification':'neutral'}]
    summary=summary_for(turns)
    assert '복약: 먹는 약 없어' in summary
    assert '알수없는말' not in summary and '오래된말' not in summary
    assert '정상' not in summary and '복용 완료' not in summary


def test_retry_state_survives_python_process_restart():
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    client=TestClient(main.app);cid=start(client)
    submit(client,cid,0,0,'xyz')
    expected=client.get(f'/api/calls/{cid}').json()
    script=f"import json; from fastapi.testclient import TestClient; from main import app; print(json.dumps(TestClient(app).get('/api/calls/{cid}').json()))"
    result=subprocess.run([sys.executable,'-c',script],cwd=Path(main.__file__).parent,env={**os.environ,'ANSIMON_DB':str(main.DB_PATH)},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)==expected
    assert expected['dialogue_state']['attempt']==1
    assert expected['dialogue_state']['count']==0
