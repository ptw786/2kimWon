"""실제 수집 캐시로 발신→벨→5문항→지원 안내를 검증 (임시 DB, AI 끔)."""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='ansimon-welfare-') as directory:
        os.environ.update(ANSIMON_DB=str(Path(directory) / 'test.db'), ANSIMON_LLM='off', ANSIMON_SCHEDULER='0', ANSIMON_STAFF_PIN='smoke-only-pin')
        from fastapi.testclient import TestClient
        from app.main import create_app

        with TestClient(create_app()) as client:
            login = client.post('/api/staff/login', json={'pin': 'smoke-only-pin'})
            assert login.status_code == 200, login.text
            client.headers.update({'Authorization': 'Bearer '+login.json()['token']})
            response = client.post('/api/staff/residents', json={
                'name': '세종 시연', 'age': 78, 'region': '세종특별자치시',
                'neighborhood': '세종시', 'call_time': '09:00',
            })
            assert response.status_code == 201, response.text
            resident = response.json()['id']
            call = client.post(f'/api/staff/residents/{resident}/call').json()['id']
            assert client.get(f'/api/elder/{resident}/incoming').json()['ringing']['call_id'] == call
            assert client.post(f'/api/elder/calls/{call}/answer').status_code == 200
            answers = ['몸은 괜찮아', '혼자 차려 먹기가 힘들어', '잘 잤어', '약은 먹었어', '기분 좋아']
            for index, answer in enumerate(answers):
                turn = client.post(f'/api/elder/calls/{call}/turn', json={
                    'text': answer, 'source': 'text', 'client_turn_id': f'welfare-{index}',
                })
                assert turn.status_code == 200, turn.text
            detail = client.get(f'/api/staff/calls/{call}').json()
            assert detail['status'] == 'completed'
            services = [s for match in detail['welfare'] for s in match['services']]
            meal = next(s for s in services if s['id'] == 'WLF00002572')
            assert meal['target_quote'] and meal['apply_quote']
            print(json.dumps({'status': detail['status'], 'questions': len(answers), 'service': meal}, ensure_ascii=True))


if __name__ == '__main__':
    main()
