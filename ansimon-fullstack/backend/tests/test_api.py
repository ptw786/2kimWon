from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

def test_complete_call():
    assert client.get('/api/health').json()['ok'] is True
    assert len(client.get('/api/residents').json()) == 4
    started = client.post('/api/residents/1/calls').json()
    cid = started['id']
    assert client.post('/api/calls/'+str(cid)+'/finish',json={'status':'completed'}).status_code == 422
    for i,answer in enumerate(['안 아파','밥 먹었어','잘 잤어','약 먹었어','기분 좋아']):
        r = client.post(f'/api/calls/{cid}/turns',json={'answer':answer})
        assert r.status_code == 201
        assert r.json()['finished'] == (i == 4)
    complete = client.post(f'/api/calls/{cid}/finish',json={'status':'completed'})
    assert complete.status_code == 200
    assert complete.json()['answered'] == 5
    assert '건강 상태:' in complete.json()['summary']
    assert len(client.get(f'/api/calls/{cid}').json()['turns']) == 5
    assert client.get('/api/dashboard').json()['completed'] == 1
    assert client.post(f'/api/calls/{cid}/turns',json={'answer':'다시'}).status_code == 409

def test_declined_and_interrupted():
    assert client.post('/api/residents/2/decline').json()['status'] == 'declined'
    cid = client.post('/api/residents/3/calls').json()['id']
    assert client.post(f'/api/calls/{cid}/finish',json={'status':'interrupted'}).status_code == 200
    assert client.get('/api/dashboard').json()['declined'] == 1
