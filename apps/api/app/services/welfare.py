"""공유 스냅샷·갱신 캐시·원문 검토 기록을 읽는 F11 어댑터."""
import json
from functools import lru_cache
from pathlib import Path

from ..domain import geography, matching
from ..domain.welfare_policy import accepted, fingerprint

DATA_PATH = Path(__file__).resolve().parent.parent / 'data' / 'welfare_subset.json'
LIVE_PATH = DATA_PATH.with_name('public_data_cache.json')
REVIEW_PATH = DATA_PATH.with_name('welfare_reviews.json')
KOSIS_PATH = DATA_PATH.with_name('kosis_households.json')


_LAST_GOOD: dict[str, tuple[tuple, dict]] = {}

def _read(path: Path, fallback: dict) -> dict:
    try:
        stat = path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
        previous = _LAST_GOOD.get(str(path))
        if previous and previous[0] == signature:
            return previous[1]
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('객체가 아님')
        for key, expected in fallback.items():
            if key not in data or (expected is not None and not isinstance(data[key], type(expected))):
                raise ValueError('자료 구조가 맞지 않음')
        if isinstance(data.get('services'), list) and any(
                not isinstance(s, dict) or not all(isinstance(s.get(k), str) for k in ('id', 'name', 'source'))
                for s in data['services']):
            raise ValueError('사업 필드가 맞지 않음')
        _LAST_GOOD[str(path)] = (signature, data)
        return data
    except (OSError, ValueError):
        safe = {**fallback, '_read_error': path.exists()}
        return _LAST_GOOD.get(str(path), (None, safe))[1]


@lru_cache(maxsize=1)
def load() -> dict:
    return _read(DATA_PATH, {'data_as_of': '', 'services': []})


def catalog() -> tuple[list[dict], dict]:
    reviews = _read(REVIEW_PATH, {'services': {}}).get('services', {})
    combined = {}
    # 갱신 캐시가 기본 자료보다 우선한다. 삭제 표시도 우선해 예전 후보가 되살아나지 않게 한다.
    fresh = _read(LIVE_PATH, {'services': []})
    baseline = load()
    if fresh.get('_read_error'):
        # 재시작 뒤 마지막 정상 캐시가 없으면 삭제 이력을 모르는 지자체 후보를 되살리지 않는다.
        baseline = {**baseline, 'services': [
            {**s, 'availability': 'cache_unavailable'} if s['source'] == '지자체복지서비스' else s
            for s in baseline['services']]}
    for data in (baseline, fresh):
        for raw in data.get('services', []):
            if not isinstance(raw, dict) or not isinstance(raw.get('id'), str):
                continue
            s = dict(raw)
            s.setdefault('checked_at', data.get('data_as_of') or None)
            review = reviews.get(s['id'])
            s['_review'] = review if isinstance(review, dict) else {}
            combined[s['id']] = s
    return list(combined.values()), _read(REVIEW_PATH, {}).get('region_aliases', {})


def matches(needs: list[dict], region: str | None, *, age: int | None = None) -> list[dict]:
    services, aliases = catalog()
    resolved = geography.normalize(region, aliases)
    dates = [s['checked_at'] for s in services if accepted(s, s['_review']) and s.get('checked_at')]
    as_of = min(dates) if dates else ''
    out, seen = [], set()
    for n in needs:
        if n['type'] not in seen:
            seen.add(n['type'])
            result = matching.match(n['type'], resolved, services, as_of, age=age)
            if _read(LIVE_PATH, {'services': []}).get('_read_error'):
                result['note'] = '지자체 캐시를 읽지 못해 해당 후보를 보류했어요. 공식 기관에서 확인해 주세요.'
            out.append(result)
    return out


def public_data_overview() -> dict:
    services, _aliases = catalog()
    counts = {'total': len(services), 'reviewed': 0, 'pending': 0, 'excluded': 0, 'unavailable': 0}
    for s in services:
        review = s['_review']
        if s.get('availability', 'active') != 'active':
            counts['unavailable'] += 1
        elif not review or review.get('source_sha256') != fingerprint(s):
            counts['pending'] += 1
        elif review.get('decision') != 'include':
            counts['excluded'] += 1
        else:
            counts['reviewed'] += 1
    statistics = _read(KOSIS_PATH, {'source': '', 'year': None, 'source_file': '', 'regions': []})
    regions = []
    for row in statistics.get('regions', []):
        normalized = geography.normalize(row['region'])
        province, district = geography.split(normalized)
        level = row['level']
        if row['region'].startswith(geography.MERGED + ' '):
            level = 'district' if district else 'province'
        regions.append({**row, 'normalized_region': normalized, 'aggregation_level': level,
                        'province_code': geography.PROVINCES.get(province, ('',))[0]})
    if _read(LIVE_PATH, {'services': []}).get('_read_error'):
        counts['warning'] = '지원사업 캐시를 읽지 못해 지자체 추천을 보류했어요. 정상 자료로 복원해 주세요.'
    return {'catalog': counts, 'statistics': {**statistics, 'regions': regions}}
