"""어려움 유형 (판정규칙.md §8) — 항목 상태와 별개로 '지원이 필요할 수 있는 사정'을 찾는다.

- "아직 밥을 안 먹었어요"(미식사)는 어려움이 아니고, "먹을 게 없어서 못 먹었어요"(식사 어려움)는 어려움이다.
- 점수에 넣지 않는다. 생활지원사 화면과 복지서비스 연계(F11)의 입력이다.
- 119·살려줘 같은 긴급 도움 요청은 safety.py(안전 신호)가 맡는다. 여기 '도움 요청'은 일상 도움이다.
- 패턴은 공백·문장부호를 뺀 글자열에 맞춘다 ("먹을 게 없어" / "먹을게없어" 같다).
"""
import re

from .scoring import rules
from .textutil import clause_at, compact

NEED_TYPES = ('meal_difficulty', 'sleep_problem', 'help_request', 'loneliness')
MULTI_DAY = r'(이틀|사흘|삼일|며칠|몇일|일주일|한동안|계속|요며칠)'
_HARD = r'(너무|좀|많이|영)?(힘들|힘드|힘든|어렵|어려|버거|버겁)'

PATTERNS: dict[str, dict[str, list[str]]] = {
    'meal_difficulty': {
        'neg': [],
        'hit': [r'먹을(게|거|것|만한게|만한거)(이|가|도)?(하나도|아무것도|별로|통)?없',
                r'먹을(게|거|것)(이|가|도)?(다)?떨어',
                r'(반찬|밥|쌀|먹을거|먹을것|장|찬거리|식료품)(을|를)?(살|사먹을|볼)돈(이|도)?(없|부족)',
                r'돈(이|도)?없어서.{0,8}(못|안)먹',
                r'차려먹(기|는게|는거|는것|을힘)?(가|이|도)?' + _HARD,
                r'(밥|식사)?(을|를)?(해|챙겨)먹(기|는게|는거|는것)?(가|이|도)?' + _HARD,
                r'(밥|식사)(을|를)?(하기|차리기|챙기기)(가|도)?' + _HARD,
                r'장(보기|보는게|보는거|보러가기|보러가는게)(가|이|도)?' + _HARD,
                r'반찬(이|도)?(하나도|다)?(없|떨어)',
                r'쌀(이|도)?(다)?(없|떨어)'],
    },
    'sleep_problem': {
        'neg': [r'잠(이|을)?잘와', r'잠(이|은)?안오는건아니'],
        'hit': [MULTI_DAY + r'(째|동안|이나)?.{0,6}(못|안)(잤|자|잠|주무)',
                r'잠(이|을)?(통|도무지|전혀|잘)?안[와오온]',
                r'밤새.{0,6}(못|안|뒤척|깼|깨)', r'밤(을)?새웠', r'뜬눈', r'한숨도(못|안)', r'불면', r'수면제'],
    },
    'help_request': {
        'neg': [r'도움(은|이)?(필요)?없', r'도움(은|이)?필요(하지)?않', r'도움(은|이)?안필요'],
        'hit': [r'도움(이|을)?(좀|꼭)?필요', r'도움(을|이)?(좀)?받고싶', r'도와줄(사람|이|사람이|이가)(가|이)?(아무도)?없',
                r'누가(좀)?(와|와서)(줬|주|줘|봐|보)', r'누가좀와', r'누가왔으면', r'(손|일손)(이)?(좀)?필요',
                r'혼자(서는|서|선)?(못하겠|할수가없|어떻게할)'],
    },
    'loneliness': {
        'neg': [r'안외로', r'외롭지(는|도)?않', r'안쓸쓸', r'쓸쓸하지(는)?않', r'안적적', r'적적하지(는)?않'],
        'hit': [r'외로', r'외롭', r'쓸쓸', r'적적', r'아무도(안|없|오지|연락|찾아)',
                r'(말|이야기|얘기|대화)(할|붙일|나눌)(사람|데|곳)(이|도|가)?(아무도|하나도)?없',
                r'말동무(가|도)?없', r'혼자(라서|여서)?.{0,4}(심심|외로)'],
    },
}

_COMPILED = {t: {k: [re.compile(p) for p in v] for k, v in g.items()} for t, g in PATTERNS.items()}


def labels() -> dict[str, str]:
    return rules()['need_labels']


def detect(text: str) -> list[dict]:
    """[{type, label, quote, origin:'rule'}] — 유형마다 최대 1개. quote 는 답변 원문 구절 그대로."""
    if not text or not text.strip():
        return []
    c, index = compact(text)
    names = labels()
    found = []
    for t in NEED_TYPES:
        pats = _COMPILED[t]
        masked = c
        for rx in pats['neg']:
            masked = rx.sub(lambda m: '#' * len(m.group(0)), masked)
        for rx in pats['hit']:
            m = rx.search(masked)
            if m:
                found.append({'type': t, 'label': names[t], 'quote': clause_at(text, index[m.start()]), 'origin': 'rule'})
                break
    return found


def merge(lists: list[list[dict]]) -> list[dict]:
    """여러 턴의 어려움 → 유형마다 처음 나온 것 하나 (NEED_TYPES 순서가 아니라 나온 순서)."""
    out: dict[str, dict] = {}
    for needs in lists:
        for n in needs or []:
            out.setdefault(n['type'], dict(n))
    return list(out.values())
