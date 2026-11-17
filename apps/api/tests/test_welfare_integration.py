"""공유 ZIP에서 재현했던 부적합 추천·갱신·지역·원문 누락 회귀 검증."""
import json

import pytest
import httpx

from app.domain import geography
from app.domain.welfare_policy import age_matches, fingerprint
from app.services import welfare
from app.services.public_data import PublicDataClient
from scripts.build_welfare_subset import _contact, _local


def candidates(need, region, age=78):
    return welfare.matches([{'type': need}], region, age=age)[0]['services']


def test_sejong_loneliness_does_not_recommend_funeral():
    assert 'WLF00004834' not in {s['id'] for s in candidates('loneliness', '세종특별자치시')}


def test_ansan_meal_is_food_support_and_not_worker_allowance():
    rows = candidates('meal_difficulty', '경기도 안산시')
    assert rows and 'WLF00005620' not in {s['id'] for s in rows}
    assert any('식사배달' in s['name'] for s in rows)


def test_employee_allowances_and_school_housing_are_not_candidates():
    services, _ = welfare.catalog()
    for sid in ['WLF00000203','WLF00002884','WLF00005438','WLF00001863','WLF00004911','WLF00005420']:
        service = next(s for s in services if s['id'] == sid)
        assert service['_review']['decision'] == 'exclude'


def test_canteen_operator_name_is_kept_when_beneficiaries_receive_food():
    assert 'WLF00002352' in {s['id'] for s in candidates('meal_difficulty', '전북특별자치도 군산시')}


def test_middle_aged_meal_service_not_shown_to_elder():
    assert 'WLF00005663' not in {s['id'] for s in candidates('meal_difficulty', '서울특별시 강북구', 78)}
    assert 'WLF00005663' in {s['id'] for s in candidates('meal_difficulty', '서울특별시 강북구', 60)}


@pytest.mark.parametrize('age,expected', [(39,False),(40,True),(64,True),(65,False),(None,True)])
def test_age_boundaries(age, expected):
    assert age_matches(age, {'min_age':40,'max_age':64}) is expected


def test_geographic_aliases_and_merged_source_names_resolve_same_district():
    normal = {s['id'] for s in candidates('help_request', '광주광역시 동구')}
    legacy = {s['id'] for s in candidates('help_request', '전남광주통합특별시 동구')}
    assert normal == legacy and 'WLF00001257' in normal
    assert geography.area_key('전북특별자치도 군산시') == geography.area_key('전라북도 군산시')


def test_no_unknown_region_is_assumed_to_match_local():
    assert all(s['source']=='중앙부처복지서비스' for s in candidates('meal_difficulty', '알수없는지역 동구'))


def test_per_service_dates_and_missing_fields_are_explicit():
    row = next(s for s in candidates('meal_difficulty', '세종특별자치시') if s['id']=='WLF00002572')
    assert row['checked_at']=='2026-11-16' and row['eligibility']['status']=='needs_check'
    assert '연락처' in row['missing_fields'] and row['contact'] is None
    central = next(s for s in candidates('meal_difficulty', '대전광역시 중구') if s['id']=='WLF00003176')
    assert central['checked_at']=='2026-11-13'


def test_nested_xml_contacts_are_not_lost():
    xml = '<root><resultCode>0</resultCode><inqplCtadrList><item><wlfareInfoReldNm>시청</wlfareInfoReldNm><wlfareInfoReldCn>044-123-4567</wlfareInfoReldCn></item></inqplCtadrList></root>'
    http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200,text=xml)))
    assert _contact(PublicDataClient('placeholder',http).detail('WLF123'))=='시청 044-123-4567'


def test_full_source_conditions_are_preserved_without_400_character_cutoff():
    text = '가'*500+'단, 중복수혜자는 제외'
    s=_local({'servId':'WLF9','servNm':'노인 급식','ctpvNm':'세종특별자치시'}, {'sprtTrgtCn':text}, select=False)
    assert s['target']==text


def test_removed_services_never_revive_from_baseline_after_cache_corruption(tmp_path,monkeypatch):
    baseline = welfare.load()['services'][0]
    modified={**baseline,'target':'변경 조건','availability':'not_listed'}
    cache=tmp_path/'live.json'
    cache.write_text(json.dumps({'data_as_of':'2026-11-17','services':[modified]}))
    monkeypatch.setattr(welfare,'LIVE_PATH',cache)
    assert baseline['id'] not in {s['id'] for s in candidates('meal_difficulty','서울특별시 서대문구')}
    cache.write_text('broken')
    assert baseline['id'] not in {s['id'] for s in candidates('meal_difficulty','서울특별시 서대문구')}


def test_all_provided_records_have_content_bound_review_and_counts_reconcile():
    rows,_=welfare.catalog()
    assert len(rows)==134 and all(s['_review']['source_sha256']==fingerprint(s) for s in rows)
    c=welfare.public_data_overview()['catalog']
    assert c['reviewed']==107 and c['excluded']==27 and c['pending']==0


def test_kosis_province_totals_equal_national_without_hierarchy_double_count(client):
    data=client.get('/api/staff/public-data').json()['statistics']
    provinces=[r for r in data['regions'] if r['aggregation_level']=='province']
    national=next(r for r in data['regions'] if r['aggregation_level']=='national')
    assert len(provinces)==17
    for field in ['elderly_single_households','all_households']:
        assert sum(r[field] for r in provinces)==national[field]
    assert len({r['normalized_region'] for r in data['regions']})==len(data['regions'])


def test_corrupt_cache_on_fresh_start_does_not_revive_deleted_local_services(tmp_path, monkeypatch):
    cache = tmp_path / 'corrupt.json'
    cache.write_text('broken')
    monkeypatch.setattr(welfare, 'LIVE_PATH', cache)
    match = welfare.matches([{'type':'meal_difficulty'}], '서울특별시 서대문구', age=78)[0]
    assert all(s['source']=='중앙부처복지서비스' for s in match['services'])
    assert '캐시' in match['note']
    assert 'warning' in welfare.public_data_overview()['catalog']
