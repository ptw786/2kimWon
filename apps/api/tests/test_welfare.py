"""F11 복지서비스 연계: 순수 매칭 · 데이터 파일 · API · 예전 DB 이전."""
import sqlite3

from app import db
from app.domain import matching
from app.services import welfare

from .conftest import resident_id, say, start_call


def svc(id_, name, source='지자체복지서비스', ctpv='서울특별시', sgg='서대문구', summary='', target=None):
    return {'id': id_, 'name': name, 'source': source, 'ctpv': ctpv if source != '중앙부처복지서비스' else None,
            'sgg': sgg if source != '중앙부처복지서비스' else None, 'org': None, 'summary': summary,
            'target': target, 'apply': None, 'link': None}


SERVICES = [
    svc('C1', '농식품바우처', source='중앙부처복지서비스', summary='취약계층 식품 지원'),
    svc('O1', '다른 구 경로식당', sgg='마포구'),
    svc('S1', '서울 어르신 도시락', sgg=None),
    svc('L1', '어르신 무료급식', target='* 결식 우려가 있는 만 60세 이상 저소득 어르신 ' + '가' * 100),
    svc('L2', '노인맞춤돌봄서비스 반찬 지원'),
    svc('L3', '경로당 운영', summary='어르신 식사 제공'),
]


def test_match_ranks_same_district_then_province_then_central():
    m = matching.match('meal_difficulty', '서울특별시 서대문구', SERVICES, '2026-11-13')
    assert [s['id'] for s in m['services']] == ['L1', 'L3', 'S1']        # 이름에 낱말이 있는 것 먼저, 최대 3
    assert m['services'][0]['area'] == '서울특별시 서대문구' and m['services'][2]['area'] == '서울특별시'
    assert 'O1' not in [s['id'] for s in m['services']]                # 다른 구 사업은 받을 수 없다
    assert m['need_label'] == '식사 어려움' and m['data_as_of'] == '2026-11-13'


def test_match_excludes_existing_care_service_with_note():
    m = matching.match('meal_difficulty', '서울특별시 서대문구', SERVICES, 'd')
    assert 'L2' not in [s['id'] for s in m['services']] and '노인맞춤돌봄서비스' in m['note']


def test_match_falls_back_to_central_with_note():
    m = matching.match('meal_difficulty', '대전광역시 중구', SERVICES, 'd')
    assert [s['id'] for s in m['services']] == ['C1'] and m['services'][0]['area'] == '전국(중앙부처)'
    assert '중앙부처' in m['note']


def test_match_empty_has_helpful_note():
    m = matching.match('sleep_problem', '대전광역시 중구', SERVICES, 'd')
    assert m['services'] == [] and '129' in m['note']


def test_quotes_are_trimmed_source_text():
    m = matching.match('meal_difficulty', '서울특별시 서대문구', SERVICES, 'd')
    q = m['services'][0]['target_quote']
    assert len(q) <= 81 and q.endswith('…') and q[:-1] in SERVICES[3]['target']


def test_subset_file_is_small_offline_and_quotes_come_from_it():
    data = welfare.load()
    assert welfare.DATA_PATH.stat().st_size < 200 * 1024 and data['data_as_of'] == '2026-11-13'
    names = {s['name'] for s in data['services']}
    assert '저소득 어르신 무료급식 지원 사업' in names
    for s in data['services']:
        assert s['source'] in ('지자체복지서비스', '중앙부처복지서비스') and s['needs']


def test_resident_detail_welfare_seoul_local_service(client):
    d = client.get(f"/api/staff/residents/{resident_id(client, '윤옥순')}").json()
    assert d['resident']['region'] == '서울특별시 서대문구' and d['resident']['code'] == 'KY-07'
    meal = next(w for w in d['welfare'] if w['need'] == 'meal_difficulty')
    first = meal['services'][0]
    assert first['name'] == '저소득 어르신 무료급식 지원 사업' and first['area'] == '서울특별시 서대문구'
    assert first['source'] == '지자체복지서비스' and first['target_quote'] and first['link'].startswith('https://')
    assert meal['note'] is None


def test_resident_detail_welfare_daejeon_falls_back_to_central(client):
    d = client.get(f"/api/staff/residents/{resident_id(client, '김영자')}").json()
    meal = next(w for w in d['welfare'] if w['need'] == 'meal_difficulty')
    assert meal['region'] == '대전광역시 중구' and all(s['source'] == '중앙부처복지서비스' for s in meal['services'])
    assert meal['services'] and '중앙부처' in meal['note']


def test_resident_without_needs_has_empty_welfare(client):
    assert client.get(f"/api/staff/residents/{resident_id(client, '정말순')}").json()['welfare'] == []


def test_call_detail_welfare_from_that_call(client):
    rid = resident_id(client, '윤옥순')
    cid = start_call(client, rid)
    for text in ['몸은 괜찮아', '먹을 게 없어서 못 먹었어', '잘 잤어', '약은 먹었어', '외로워. 아무도 안 와']:
        say(client, cid, text)
    d = client.get(f'/api/staff/calls/{cid}').json()
    assert [w['need'] for w in d['welfare']] == ['meal_difficulty', 'loneliness']
    assert [n['type'] for n in d['assessment']['needs']] == ['meal_difficulty', 'loneliness']


def test_create_and_patch_region(client):
    r = client.post('/api/staff/residents', json={'name': '홍길동', 'age': 79, 'region': '서울특별시 마포구',
                                                 'neighborhood': '마포구 망원동', 'call_time': '09:15'}).json()
    assert r['region'] == '서울특별시 마포구'
    p = client.patch(f"/api/staff/residents/{r['id']}", json={'region': '대전광역시 서구'}).json()
    assert p['region'] == '대전광역시 서구'


def test_old_db_gets_region_column_and_backfill(tmp_path):
    path = tmp_path / 'old.db'
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE residents (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, age INTEGER NOT NULL,
          neighborhood TEXT NOT NULL, call_time TEXT NOT NULL, memo TEXT, is_virtual INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL);
        CREATE TABLE turns (id INTEGER PRIMARY KEY, call_id INTEGER NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL,
          topic TEXT, at TEXT NOT NULL, source TEXT, judged TEXT, client_turn_id TEXT, result TEXT);
        INSERT INTO residents VALUES (1, 'KY-01', '김영자', 78, '중구 은행동', '08:30', NULL, 1, '2026-01-01');
    """)
    conn.commit()
    conn.close()
    db.init_db(str(path), model_name='m')
    conn = db.connect(str(path))
    assert conn.execute('SELECT region FROM residents WHERE id = 1').fetchone()[0] == '대전광역시 중구'
    assert {'needs', 'ms'} <= {r[1] for r in conn.execute('PRAGMA table_info(turns)')}
    conn.close()
