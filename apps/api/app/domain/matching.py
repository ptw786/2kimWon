"""어려움 유형 + 거주 지역 → 연계할 만한 복지서비스 (F11). 순수 함수 — 데이터는 services/welfare.py 가 읽어 넘긴다.

- 낱말 표(rules.yaml welfare.keywords)로 이름·요약을 본다. 관심주제 태그는 품질이 낮아 쓰지 않는다.
- 순서: 같은 시군구 → 같은 시도(시도 전체 사업) → 중앙부처. 다른 시군구 사업은 그 주민만 받을 수 있어 보여 주지 않는다.
- 이미 받고 있는 노인맞춤돌봄서비스는 뺀다(note 에 적음). 인용은 원문을 자르기만 한다(지어내지 않음).
"""
import re

from .scoring import rules

CENTRAL_AREA = '전국(중앙부처)'
QUOTE_MAX = 80


def split_region(region: str | None) -> tuple[str, str]:
    """'서울특별시 서대문구' → ('서울특별시', '서대문구'). 시군구가 없으면 ''."""
    parts = (region or '').split()
    return (parts[0] if parts else ''), ' '.join(parts[1:])


def trim_quote(text: str | None, limit: int = QUOTE_MAX) -> str | None:
    """원문 앞부분을 잘라 쓴다 (글머리 기호·공백만 정리)."""
    if not text:
        return None
    t = re.sub(r'\s+', ' ', text).strip().lstrip('*-○o·• ').strip()
    if not t:
        return None
    return t if len(t) <= limit else t[:limit].rstrip() + '…'


def _hits(service: dict, words: list[str]) -> tuple[bool, bool]:
    name, summary = service.get('name') or '', service.get('summary') or ''
    return any(w in name for w in words), any(w in summary for w in words)


def _out(s: dict) -> dict:
    area = CENTRAL_AREA if s['source'] == '중앙부처복지서비스' else ' '.join(x for x in (s.get('ctpv'), s.get('sgg')) if x)
    return {
        'id': s['id'], 'name': s['name'], 'org': s.get('org'), 'area': area, 'summary': s.get('summary'),
        'target_quote': trim_quote(s.get('target')), 'apply_quote': trim_quote(s.get('apply')),
        'link': s.get('link'), 'source': s['source'],
    }


def match(need_type: str, region: str | None, services: list[dict], data_as_of: str,
          rule_set: dict | None = None) -> dict:
    """WelfareMatch (CONTRACT.md v2.1)."""
    r = rule_set or rules()
    w = r['welfare']
    words = w['keywords'][need_type]
    ctpv, sgg = split_region(region)
    excluded, ranked = [], []
    for i, s in enumerate(services):
        in_name, in_summary = _hits(s, words)
        if not (in_name or in_summary):
            continue
        if s['source'] == '중앙부처복지서비스':
            tier = 2
        elif s.get('ctpv') == ctpv and sgg and s.get('sgg') == sgg:
            tier = 0
        elif s.get('ctpv') == ctpv and not s.get('sgg'):
            tier = 1
        else:
            continue
        if any(x in s['name'] for x in w['exclude_names']):
            excluded.append(s['name'])
            continue
        ranked.append(((tier, 0 if in_name else 1, i), s))
    ranked.sort(key=lambda x: x[0])
    picked = [s for _k, s in ranked[:w['max_services']]]
    label = r['need_labels'][need_type]
    where = region or '등록된 지역'
    notes = []
    if not picked:
        notes.append(f'{where}에서 {label}에 맞는 서비스를 데이터에서 찾지 못했어요. 주민센터(행정복지센터)나 '
                     '보건복지상담센터(129)에 문의해 보세요.')
    elif all(s['source'] == '중앙부처복지서비스' for s in picked):
        notes.append(f'{where}에는 {label}에 맞는 지자체 사업이 데이터에 없어 중앙부처 서비스를 보여 드려요.')
    if excluded:
        notes.append('노인맞춤돌봄서비스는 이미 받고 계셔서 뺐어요.')
    return {
        'need': need_type, 'need_label': label, 'region': region or '',
        'services': [_out(s) for s in picked],
        'note': ' '.join(notes) or None,
        'data_as_of': data_as_of,
    }
