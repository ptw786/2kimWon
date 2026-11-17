import json

import httpx
import pytest

from app.services import welfare
from app.services.public_data import PublicDataClient, PublicDataError, read_key


def client_for(body, status=200):
    return PublicDataClient('secret-key', httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(status, text=body))))


def test_list_xml_and_service_id_are_not_api_key():
    client = client_for('<root><resultCode>0</resultCode><totalCount>1</totalCount>'
                        '<servList><servId>WLF00002572</servId><servNm>급식</servNm></servList></root>')
    rows, total = client.list_services('세종특별자치시')
    assert total == 1 and rows[0]['servId'] == 'WLF00002572'
    with pytest.raises(PublicDataError, match='WLF'):
        client.detail('secret-key')


def test_upstream_error_is_redacted_even_on_http_error():
    client = client_for('<root><returnReasonCode>12</returnReasonCode>'
                        '<resultMessage>secret-key</resultMessage></root>', 400)
    with pytest.raises(PublicDataError, match='12') as error:
        client.list_services('세종특별자치시')
    assert 'secret-key' not in str(error.value)


def test_key_file_is_decoded_once(tmp_path, monkeypatch):
    monkeypatch.delenv('DATA_GO_KR_SERVICE_KEY', raising=False)
    path = tmp_path / 'key.txt'
    path.write_text('a' * 40 + '%2B%2F%3D', encoding='utf-8-sig')
    assert read_key(path) == 'a' * 40 + '+/='


def test_cache_requires_review_and_detects_changed_content(tmp_path, monkeypatch):
    from app.domain.welfare_policy import fingerprint
    cache, reviews = tmp_path / 'cache.json', tmp_path / 'reviews.json'
    monkeypatch.setattr(welfare, 'LIVE_PATH', cache)
    monkeypatch.setattr(welfare, 'REVIEW_PATH', reviews)
    service = {'id': 'WLF_TEST', 'name': '노인급식지원', 'source': '지자체복지서비스',
               'ctpv': '세종특별자치시', 'sgg': None, 'checked_at': '2026-11-16'}
    cache.write_text(json.dumps({'data_as_of': '2026-11-16', 'services': [service]}), encoding='utf-8')
    needs = [{'type': 'meal_difficulty'}]
    assert welfare.matches(needs, '세종특별자치시')[0]['services'] == []
    reviews.write_text(json.dumps({'services': {'WLF_TEST': {
        'decision': 'include', 'needs': ['meal_difficulty'], 'source_sha256': fingerprint(service), 'reason': '직접 급식'
    }}}), encoding='utf-8')
    assert welfare.matches(needs, '세종특별자치시')[0]['services'][0]['id'] == 'WLF_TEST'
    service['target'] = '사업 지원대상이 변경됨'
    cache.write_text(json.dumps({'data_as_of': '2026-11-17', 'services': [service]}), encoding='utf-8')
    assert welfare.matches(needs, '세종특별자치시')[0]['services'] == []
