"""사회보장 복지서비스 목록 → 안심온 시연용 일부(JSON) 만들기 (F11).

    python scripts/build_welfare_subset.py <cache_dir>

<cache_dir> 에 있어야 하는 파일 (한국사회보장정보원 · 공공데이터포털에서 내려받은 것):
- local_list_전국.json   지자체복지서비스 목록 (data.go.kr 15108347)
- local_서울특별시.json   서울 지자체복지서비스 목록 + 상세(detail)
- central.partial.json   중앙부처복지서비스 목록 일부 (data.go.kr 15090532)

고르는 규칙 (app/data/README.md 와 같다):
1. 어르신 대상: 생애주기(lifeNmArray)에 '노년'이 있거나, 이름·요약·지원대상에 노인·어르신·65세 이상·독거·홀로·홀몸이 있다.
   이름이 장애인·노숙인·한부모·아동·청소년·청년·보훈 등 다른 대상을 가리키면 (이름에 노인·어르신이 없는 한) 뺀다.
   기관 운영비 지원처럼 주민이 직접 받는 서비스가 아니면 뺀다.
2. 어려움 유형 낱말(rules.yaml welfare.keywords)이 이름·요약(servNm·servDgst)에 하나라도 있다 (상세 지원내용까지 보면 '경로잔치 식사 대접' 같은 잡음이 늘어 뺐다). 관심주제 태그는 품질이 낮아 쓰지 않는다.
3. 범위: 서울 전체(상세 포함) · 대전광역시 전체 · 중앙부처. 중앙부처 식사 지원은 노인 표시가 없어도 저소득·취약계층 전체 대상이면 넣는다.
"""
import ast
import json
import re
import sys
from pathlib import Path

import yaml

API_DIR = Path(__file__).resolve().parent.parent
OUT = API_DIR / 'app' / 'data' / 'welfare_subset.json'
RULES = yaml.safe_load((API_DIR / 'app' / 'domain' / 'rules.yaml').read_text(encoding='utf-8'))
KEYWORDS: dict[str, list[str]] = RULES['welfare']['keywords']

ELDERLY = re.compile(r'노인|어르신|65세\s*이상|독거|홀로|홀몸')
OTHER_TARGET = re.compile(r'장애인|노숙|부랑|한부모|아동|청소년|청년|학생|학교|보훈|국가유공자|성매매|취업|임신|출산|영유아|다문화')
# 주민이 직접 받는 서비스가 아니거나(기관 운영비·행사), 장기요양 등급이 있어야 받는 급여
NOT_A_SERVICE = re.compile(r'운영\s*지원|기관\s*운영|장수축하|가족요양비')
LOW_INCOME = re.compile(r'취약계층|저소득|생계급여')
TEXT_FIELDS = ('sprtTrgtCn', 'slctCritCn', 'alwServCn', 'aplyMtdCn')
MAX_TEXT = 400


def _clean(text) -> str:
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def _detail(row) -> dict:
    d = row.get('detail')
    if isinstance(d, str):
        try:
            d = ast.literal_eval(d)
        except (ValueError, SyntaxError):
            d = None
    return d if isinstance(d, dict) else {}


def _contact(d: dict) -> str | None:
    lst = d.get('inqplCtadrList')
    if isinstance(lst, dict):
        lst = [lst]
    for x in lst or []:
        if isinstance(x, dict) and x.get('wlfareInfoReldCn'):
            name = _clean(x.get('wlfareInfoReldNm'))
            return f"{name} {_clean(x['wlfareInfoReldCn'])}".strip()
    return None


def _needs_of(text: str) -> list[str]:
    return [need for need, words in KEYWORDS.items() if any(w in text for w in words)]


def _is_elderly(name: str, text: str, life: str) -> bool:
    if NOT_A_SERVICE.search(name):
        return False
    if OTHER_TARGET.search(name) and not re.search(r'노인|어르신', name):
        return False
    return '노년' in (life or '') or bool(ELDERLY.search(text))


def _local(row, detail: dict) -> dict | None:
    name = _clean(row['servNm'])
    summary = _clean(row.get('servDgst'))
    texts = {k: _clean(detail.get(k))[:MAX_TEXT] or None for k in TEXT_FIELDS}
    if not _is_elderly(name, ' '.join([name, summary, texts['sprtTrgtCn'] or '']), row.get('lifeNmArray')):
        return None
    needs = _needs_of(' '.join([name, summary]))
    if not needs:
        return None
    return {
        'id': row['servId'], 'name': name, 'source': '지자체복지서비스',
        'ctpv': _clean(row.get('ctpvNm')), 'sgg': _clean(row.get('sggNm')) or None,
        'org': _clean(row.get('bizChrDeptNm')) or None, 'summary': summary or None,
        'target': texts['sprtTrgtCn'], 'criteria': texts['slctCritCn'], 'content': texts['alwServCn'],
        'apply': texts['aplyMtdCn'], 'apply_method': _clean(row.get('aplyMtdNm')) or None,
        'contact': _contact(detail), 'link': row.get('servDtlLink') or None, 'needs': needs,
    }


def _central(row) -> dict | None:
    name = _clean(row['servNm'])
    summary = _clean(row.get('servDgst'))
    text = ' '.join([name, summary])
    needs = _needs_of(text)
    if not needs:
        return None
    broad_meal = ('meal_difficulty' in needs and LOW_INCOME.search(text + ' ' + (row.get('trgterIndvdlArray') or ''))
                  and not OTHER_TARGET.search(name))
    if not (_is_elderly(name, text, row.get('lifeArray')) or broad_meal):
        return None
    org = ' '.join(x for x in (_clean(row.get('jurMnofNm')), _clean(row.get('jurOrgNm'))) if x)
    return {
        'id': row['servId'], 'name': name, 'source': '중앙부처복지서비스', 'ctpv': None, 'sgg': None,
        'org': org or None, 'summary': summary or None, 'target': None, 'criteria': None, 'content': None,
        'apply': None, 'apply_method': None, 'contact': _clean(row.get('rprsCtadr')) or None,
        'link': row.get('servDtlLink') or None, 'needs': needs,
    }


def build(cache: Path) -> dict:
    nationwide = json.loads((cache / 'local_list_전국.json').read_text(encoding='utf-8'))
    seoul = json.loads((cache / 'local_서울특별시.json').read_text(encoding='utf-8'))
    central = json.loads((cache / 'central.partial.json').read_text(encoding='utf-8'))
    rows = []
    for r in seoul['items']:
        x = _local(r, _detail(r))
        if x:
            rows.append(x)
    for r in nationwide['items']:
        if r.get('ctpvNm') == '대전광역시':
            x = _local(r, {})
            if x:
                rows.append(x)
    for r in central if isinstance(central, list) else central.get('items', []):
        x = _central(r)
        if x:
            rows.append(x)
    seen, unique = set(), []
    for x in rows:
        if x['id'] not in seen:
            seen.add(x['id'])
            unique.append(x)
    return {
        'source': '한국사회보장정보원 지자체복지서비스(data.go.kr 15108347) · 중앙부처복지서비스(data.go.kr 15090532)',
        'data_as_of': (nationwide.get('saved_at') or seoul.get('fetched_at') or '')[:10],
        'selection': '어르신 대상 + 어려움 유형 낱말 일치 (app/data/README.md)',
        'services': unique,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    data = build(Path(argv[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    by = {}
    for s in data['services']:
        key = s['source'] if s['source'] != '지자체복지서비스' else s['ctpv']
        by[key] = by.get(key, 0) + 1
    print(f"{OUT.name}: {len(data['services'])}건 {by} · {OUT.stat().st_size // 1024} KB · 기준일 {data['data_as_of']}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
