"""원문 검토된 직접 지원만 지역·연령 자격과 비교한다. I/O 없는 F11 매칭."""
import re

from . import geography
from .scoring import rules
from .welfare_policy import accepted, age_matches, eligibility

CENTRAL_AREA = '전국(중앙부처)'
QUOTE_MAX = 80
split_region = geography.split


def trim_quote(text: str | None, limit: int = QUOTE_MAX) -> str | None:
    if not text:
        return None
    text = re.sub(r'\s+', ' ', text).strip().lstrip('*-○o·• ').strip()
    return (text if len(text) <= limit else text[:limit].rstrip() + '…') or None


def _area(service: dict) -> str:
    original = ' '.join(x for x in (service.get('ctpv'), service.get('sgg')) if x)
    return service.get('_review', {}).get('match_region') or original


def _tier(service: dict, region: str | None) -> int | None:
    if service['source'] == '중앙부처복지서비스':
        return 2
    code, district = geography.area_key(region)
    scode, sdistrict = geography.area_key(_area(service))
    if not code or code != scode:
        return None
    if district and sdistrict == district:
        return 0
    return 1 if not sdistrict else None


def _out(service: dict, age: int | None) -> dict:
    original = ' '.join(x for x in (service.get('ctpv'), service.get('sgg')) if x)
    return {
        'id': service['id'], 'name': service['name'], 'org': service.get('org'),
        'area': CENTRAL_AREA if service['source'] == '중앙부처복지서비스' else _area(service),
        'source_area': original, 'summary': service.get('summary'),
        'target_quote': trim_quote(service.get('target')), 'apply_quote': trim_quote(service.get('apply')),
        'target_text': service.get('target'), 'criteria_text': service.get('criteria'),
        'apply_text': service.get('apply'), 'contact': service.get('contact'),
        'link': service.get('link'), 'source': service['source'],
        'checked_at': service.get('checked_at'), 'eligibility': eligibility(service, age),
        'review_note': service['_review']['reason'],
        'missing_fields': [label for key, label in [('target', '지원대상'), ('apply', '신청방법'), ('contact', '연락처')]
                          if not service.get(key)],
    }


def match(need_type: str, region: str | None, services: list[dict], data_as_of: str,
          rule_set: dict | None = None, *, age: int | None = None) -> dict:
    r = rule_set or rules()
    ranked = []
    for s in services:
        review = s.get('_review')
        if not accepted(s, review) or need_type not in review['needs'] or not age_matches(age, review):
            continue
        tier = _tier(s, region)
        if tier is not None:
            # 지역 적합도 → 직접 지원 목적(검토된 needs) → 정보 완결성 → 서비스 ID.
            missing = sum(not s.get(k) for k in ('target', 'apply', 'contact'))
            ranked.append(((tier, missing, s['id']), s))
    ranked.sort(key=lambda x: x[0])
    picked = [s for _, s in ranked[:r['welfare']['max_services']]]
    label = r['need_labels'][need_type]
    note = None
    if not picked:
        note = f'{region or "등록된 지역"}에서 검토된 {label} 지원 후보를 찾지 못했어요. 주민센터나 129에 문의해 주세요.'
    elif all(s['source'] == '중앙부처복지서비스' for s in picked):
        note = '현재 검토된 지자체 후보가 없어 중앙부처 서비스를 보여 드려요. 신청 자격은 별도 확인이 필요해요.'
    return {'need': need_type, 'need_label': label, 'region': region or '',
            'services': [_out(s, age) for s in picked], 'note': note, 'data_as_of': data_as_of}
