import json

import pytest

from app.services.public_data import PublicDataError
from scripts import sync_public_data as syncer


def _setup(tmp_path, monkeypatch, *, listed=None, broken=False, province=''):
    api = tmp_path / 'api'
    folder = api / 'app/data'
    folder.mkdir(parents=True)
    original = {'id': 'WLF1', 'name': '노인 급식', 'source': '지자체복지서비스',
                'ctpv': '세종특별자치시', 'summary': '급식 제공', 'target': '기존 대상'}
    gone = {**original, 'id': 'WLF2'}
    other = {**original, 'id': 'WLF3', 'ctpv': '서울특별시'}
    central = {**original, 'id': 'WLF4', 'source': '중앙부처복지서비스', 'ctpv': None}
    (folder / 'welfare_subset.json').write_text(json.dumps({'data_as_of': '2026-11-13', 'services': [original, gone, other, central]}))
    output = tmp_path / 'cache.json'
    output.write_text(json.dumps({'data_as_of': '2026-11-16', 'services': [original]}))
    called = []
    rows = listed if listed is not None else [{'servId': 'WLF1', 'servNm': '노인 급식', 'ctpvNm': '세종특별자치시'},
                                              {'servId': 'WLF5', 'servNm': '노인 반찬', 'ctpvNm': '세종특별자치시'}]
    class FakeClient:
        def __init__(self, key, client): pass
        def list_services(self, area, page):
            assert area == province
            return rows[(page-1)*100:page*100], len(rows)
        def detail(self, sid):
            called.append(sid)
            if broken: raise PublicDataError('실패')
            return {'sprtTrgtCn': '갱신한 대상', 'aplyMtdCn': '동주민센터 신청',
                    'inqplCtadrList': [{'wlfareInfoReldNm': '담당부서', 'wlfareInfoReldCn': '044-000-0000'}]}
    monkeypatch.setattr(syncer, 'API_DIR', api)
    monkeypatch.setattr(syncer, 'PublicDataClient', FakeClient)
    monkeypatch.setattr(syncer, 'read_key', lambda _: 'test-placeholder')
    return output, called


def test_refresh_existing_and_new_and_remove_missing_without_refreshing_central_date(tmp_path, monkeypatch):
    output, called = _setup(tmp_path, monkeypatch)
    syncer.sync('', tmp_path/'key', output)
    data = json.loads(output.read_text()); rows = {s['id']: s for s in data['services']}
    assert set(called) == {'WLF1', 'WLF5'}
    assert rows['WLF1']['target'] == '갱신한 대상'
    assert rows['WLF1']['contact'] == '담당부서 044-000-0000'
    assert rows['WLF2']['availability'] == rows['WLF3']['availability'] == 'not_listed'
    assert rows['WLF4']['checked_at'] == '2026-11-13'
    assert rows['WLF1']['checked_at'] != '2026-11-16'


def test_province_refresh_keeps_other_provinces(tmp_path, monkeypatch):
    output, _ = _setup(tmp_path, monkeypatch, province='세종특별자치시')
    syncer.sync('세종특별자치시', tmp_path/'key', output)
    rows = {s['id']: s for s in json.loads(output.read_text())['services']}
    assert rows['WLF3']['target'] == '기존 대상' and rows['WLF3'].get('availability') is None


def test_failed_detail_keeps_file_byte_for_byte(tmp_path, monkeypatch):
    output, _ = _setup(tmp_path, monkeypatch, broken=True)
    before = output.read_bytes()
    with pytest.raises(PublicDataError): syncer.sync('', tmp_path/'key', output)
    assert output.read_bytes() == before


def test_duplicate_or_truncated_listing_is_not_allowed_to_delete_records(tmp_path, monkeypatch):
    row = {'servId': 'WLF1', 'servNm': '노인 급식', 'ctpvNm': '세종특별자치시'}
    output, _ = _setup(tmp_path, monkeypatch, listed=[row, row])
    before = output.read_bytes()
    with pytest.raises(PublicDataError): syncer.sync('', tmp_path/'key', output)
    assert output.read_bytes() == before


def test_all_pages_are_collected_before_replacing(tmp_path, monkeypatch):
    rows = [{'servId': f'WLF{i}', 'servNm': '노인 급식', 'ctpvNm': '세종특별자치시'} for i in range(1, 102)]
    output, called = _setup(tmp_path, monkeypatch, listed=rows)
    syncer.sync('', tmp_path/'key', output)
    assert len(called) == 101
    assert json.loads(output.read_text())['collection']['listed'] == 101
