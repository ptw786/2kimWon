"""AI(Ollama)가 실패했을 때 쓰는 키워드 판정.

- 부정 표현을 먼저 지운다 ("안 아파" → 양호, 그 뒤에 "아파"를 찾지 않음).
- 위험 → 주의 → 양호 순으로 찾는다 ("이틀째 못 먹었어"는 '먹었'보다 '이틀째 못 먹'이 먼저).
- generic(괜찮아·별로 같은 두루뭉술한 말)과 짧은 대답(네·응·어·아니)은 지금 묻는 주제에만 쓴다.
- 다른 주제는 주의·위험만 기록한다 (확인 대상을 늘리는 쪽으로만).
"""
import re
from dataclasses import dataclass, field

from .questions import TOPICS
from .textutil import compact, segments

MULTI_DAY = r'(이틀|사흘|삼일|며칠|몇일|일주일|한동안|계속|어제부터|요며칠)'

PATTERNS: dict[str, dict[str, list[str]]] = {
    'body': {
        'neg_good': [r'안아[파프팠]', r'아프지(는)?않', r'아픈(데|곳)(는|은|이|가)?(하나도|별로)?없', r'안불편',
                     r'불편한(데|곳)(는|은)?없', r'불편하지(는)?않'],
        'risk': [r'어지러', r'어지럽', r'(많이|너무|심하게|엄청|무척)아[파프팠]', r'아파서못', r'못움직',
                 r'열이(많이|펄펄|심하)', r'토했', r'토하', r'구토', r'넘어', r'쓰러', r'숨(이)?차', r'숨쉬',
                 r'가슴(이)?(아파|아프|답답)', r'마비'],
        'caution': [r'아[파프팠]', r'쑤시', r'쑤셔', r'결리', r'결려', r'저리', r'저려', r'불편', r'감기', r'기침',
                    r'콧물', r'몸살', r'피곤', r'기운(이)?없', r'힘(이)?없', r'뻐근', r'부었', r'붓고', r'시려', r'시리'],
        'good': [r'건강', r'멀쩡', r'튼튼', r'개운', r'몸(은|이)?괜찮', r'몸(은|이)?좋'],
        'generic_caution': [r'안좋', r'좋지(는)?않', r'별로', r'힘들'],
        'generic_good': [r'괜찮', r'좋아', r'좋[다네습지]', r'그럭저럭', r'견딜만', r'살만', r'문제없', r'잘지내'],
    },
    'meal': {
        'neg_good': [],
        'risk': [MULTI_DAY + r'(째|동안|이나|을|를)?.{0,8}(못|안)먹', MULTI_DAY + r'(째|동안)?.{0,4}굶',
                 r'하루종일.{0,4}(못|안)먹', MULTI_DAY + r'(째|동안)?.{0,8}먹을(게|거|것)(이|가|도)?(하나도)?없'],
        'caution': [r'(못|안)먹', r'걸렀', r'거르', r'걸러', r'굶', r'입맛(이)?없', r'입맛(이)?떨어', r'밥맛(이)?없',
                    r'조금(밖에)?먹', r'조금만먹', r'대충', r'(밥|먹을)생각(이)?없', r'먹기싫', r'소화(가)?안', r'체했',
                    # 식사 어려움 (needs.py 와 같은 말): 먹을 게 없음 · 차려 먹기 힘듦 · 장보기 힘듦 · 반찬·쌀 없음 · 살 돈 없음
                    r'먹을(게|거|것)(이|가|도)?(하나도|아무것도|별로)?(없|떨어)', r'(차려|해|챙겨)먹.{0,4}(힘들|힘드|어렵|어려|버겁)',
                    r'장(보기|보는게|보러).{0,4}(힘들|힘드|어렵|어려)', r'(반찬|쌀)(이|도)?(하나도|다)?(없|떨어)',
                    r'(반찬|밥|쌀|먹을거|장)(을|를)?(살|볼)돈(이|도)?(없|부족)',
                    r'아직.{0,4}(식사|밥)(하기|먹기)?전'],
        'good': [r'먹었', r'먹음', r'잘먹', r'챙겨먹', r'드셨', r'식사했', r'밥했', r'먹고', r'든든', r'배불', r'맛있'],
        'generic_caution': [r'별로', r'안좋'],
        'generic_good': [r'그럼', r'당연'],
    },
    'sleep': {
        'neg_good': [r'안깼', r'한번도안깨', r'안깨고'],
        'risk': [MULTI_DAY + r'(째|동안)?.{0,6}(못|안)(잤|자)', r'한숨도(못|안)', r'밤새(한숨도|못|뜬눈)', r'뜬눈'],
        'caution': [r'설쳤', r'설치', r'설쳐', r'(못|안)잤', r'(못|안)자', r'잠(이|을)?(잘)?안[와오]', r'잠(이|을)?못',
                    r'깼', r'깨[서고]', r'뒤척', r'선잠', r'불면', r'자다가', r'뒤숭숭', r'꿈자리'],
        'good': [r'잘잤', r'푹', r'잘잠', r'잘자', r'잤', r'주무셨', r'숙면', r'꿀잠'],
        'generic_caution': [r'별로', r'안좋', r'피곤'],
        'generic_good': [r'괜찮', r'좋', r'그럭저럭'],
    },
    'med': {
        # '약 안 먹어도 돼'는 복약 대상 아님(양호)이라 '안먹'보다 먼저 지운다
        'neg_good': [r'약(을|은)?안먹어도', r'약(이|은)?필요없', r'약(은|을)?안먹는사람'],
        'risk': [MULTI_DAY + r'(째|동안|이나)?.{0,6}(못|안)(먹|챙|드)', r'약(이|을)?(다)?떨어진지'],
        'caution': [r'(못|안)(먹|챙|드)', r'깜빡', r'까먹', r'잊어', r'잊었', r'아직', r'떨어졌', r'떨어져', r'빼먹',
                    r'걸렀'],
        # 주의를 못 찾았을 때만: "약 없어" = 복약 대상 아님 → 양호
        'good': [r'약(은|이|도)?(하나도)?없(어|어요|습니다|지|다|음|는데|네|어서괜찮)?$', r'먹었', r'챙겨', r'챙겼', r'복용했',
                 r'드셨', r'먹고있', r'꼬박꼬박', r'잘먹'],
        'generic_caution': [],
        'generic_good': [r'그럼', r'당연'],
    },
    'mood': {
        'neg_good': [r'안외로', r'외롭지(는)?않', r'안우울', r'우울하지(는)?않', r'안심심', r'심심하지(는)?않',
                     r'안쓸쓸', r'걱정(은|이)?없', r'걱정(은)?안'],
        'risk': [r'아무도(안|없|오지|연락)', r'(너무|많이|정말|진짜|매일|맨날|항상|늘)(외로|외롭|우울|쓸쓸|적적|슬퍼|슬프|울적)',
                 r'(매일|맨날)울', r'살맛(이)?없', r'사는(게|것이)?(재미|낙)(가|이)?없', r'혼자(라서|라|여서)?.{0,4}(외로|무서)'],
        'caution': [r'외로', r'외롭', r'우울', r'울적', r'쓸쓸', r'적적', r'슬퍼', r'슬프', r'속상', r'서운', r'심심',
                    r'걱정', r'불안', r'무서', r'짜증', r'화가나', r'화나', r'눈물', r'울었', r'의욕(이)?없', r'그리워',
                    r'보고싶'],
        'good': [r'기분(이|은)?좋', r'즐거', r'행복', r'편안', r'기뻐', r'기쁘', r'신나', r'재미있', r'재밌'],
        'generic_caution': [r'안좋', r'좋지(는)?않', r'별로', r'답답', r'힘들'],
        'generic_good': [r'괜찮', r'좋', r'그럭저럭', r'그저그래', r'그냥그래', r'무난', r'평범'],
    },
}

# 지금 질문에 대한 짧은 대답 — 모든 질문은 '네 = 양호'가 되도록 만들어 두었다 (questions.py)
_YES = re.compile(r'(네|예|응|어|엉|웅|그래|그럼|그렇지|그렇죠|맞아|넵|네네|예예|당연하지|당연하죠|그럼요|ㅇㅇ)(요)?')
_NO = re.compile(r'(아니|아뇨|아니요|아니야|아니에요|아냐|아니오|ㄴㄴ)')
_SHORT = {'yes': 'good', 'no': 'caution'}

_REPEAT = re.compile(r'뭐라고|뭐라구|뭐라그|뭐라카|다시(한번|한번만)?(말|얘기|이야기|물어|해줘|해주)|다시요|잘안들|안들려|안들리|'
                     r'못들었|못알아듣|못알아들|무슨말|무슨소리|뭐라는')
_REPEAT_SHORT = re.compile(r'^\s*(네|예|응|뭐|뭐요|에|잉)\s*\?+\s*$')

_COMPILED = {
    t: {k: [re.compile(p) for p in v] for k, v in groups.items()} for t, groups in PATTERNS.items()
}


@dataclass
class KeywordResult:
    intent: str                               # answer | repeat_request | unclear
    items: list[dict] = field(default_factory=list)   # {topic, status, quote}


# 지금 주제: 이 말이 든 구절을 먼저 본다 ("약은 먹었는데 아침은 걸렀어" → 복약은 앞 구절로 판단)
ANCHORS = {
    'body': re.compile(r'몸|아[파프팠]|쑤|결리|결려|저려|저리|어지|머리|허리|다리|무릎|어깨|배가|열이|감기|기침|몸살|피곤|기운|힘이|토했|넘어|쓰러|숨|가슴'),
    'meal': re.compile(r'밥|식사|먹|끼니|입맛|굶|아침|점심|저녁|반찬|밥맛|걸렀|드셨'),
    'sleep': re.compile(r'잠|잤|자다|자고|잘자|깼|깨|주무|설쳤|설치|뒤척|밤'),
    'med': re.compile(r'약'),
    'mood': re.compile(r'.'),
}


# 다른 주제로 기록하려면 그 구절에 주제를 가리키는 '명사'가 있어야 한다
# ('먹다'는 식사·복약이 같이 써서 다른 주제의 근거로 쓰지 않는다)
STRONG_ANCHORS = {
    'body': re.compile(r'몸|아[파프팠]|쑤|결리|결려|저려|저리|어지|머리|허리|다리|무릎|어깨|배가|열이|감기|기침|몸살|기운|토했|숨|가슴'),
    'meal': re.compile(r'밥|식사|끼니|입맛|굶|아침|점심|저녁|반찬|밥맛|식욕'),
    'sleep': re.compile(r'잠|잤|주무|깼|설쳤|설치|뒤척'),
    'med': re.compile(r'약'),
    'mood': re.compile(r'.'),
}


def _mask(pats, c):
    first = None
    for rx in pats['neg_good']:
        for m in rx.finditer(c):
            first = m.start() if first is None else first
            c = c[:m.start()] + '#' * (m.end() - m.start()) + c[m.end():]
    return c, first is not None


def _judge_in(topic: str, segs: list[str], current: bool) -> dict | None:
    """구절 목록에서 위험 → 주의 → 양호 순으로 찾는다."""
    pats = _COMPILED[topic]
    masked = [(seg,) + _mask(pats, compact(seg)[0]) for seg in segs]
    order = [('risk', pats['risk']), ('caution', pats['caution'] + (pats['generic_caution'] if current else []))]
    if current:
        order.append(('good', pats['good'] + pats['generic_good']))
    for status, plist in order:
        for seg, c, _neg in masked:
            if any(rx.search(c) for rx in plist):
                return {'topic': topic, 'status': status, 'quote': seg}
    if current:
        for seg, _c, neg in masked:
            if neg:
                return {'topic': topic, 'status': 'good', 'quote': seg}
    return None


def _judge_topic(topic: str, text: str, segs: list[str], current: bool, allow_short: bool) -> dict | None:
    anchors = ANCHORS[topic] if current else STRONG_ANCHORS[topic]
    anchored = [s for s in segs if anchors.search(compact(s)[0])]
    found = _judge_in(topic, anchored, current)
    if found or not current:
        return found
    found = _judge_in(topic, [text.strip()], current)
    if found:
        return found
    c, _ = compact(text)
    if allow_short and _YES.fullmatch(c):
        return {'topic': topic, 'status': _SHORT['yes'], 'quote': text.strip()}
    if allow_short and (_NO.fullmatch(c) or re.fullmatch(r'(아니|아뇨|아니요)(요)?(못|안)(했|먹|잤)\w*', c)):
        return {'topic': topic, 'status': _SHORT['no'], 'quote': text.strip()}
    return None


def is_repeat_request(text: str) -> bool:
    c, _ = compact(text or '')
    return bool(_REPEAT.search(c) or _REPEAT_SHORT.match(text or ''))


def extract(current_topic: str, text: str) -> KeywordResult:
    text = text or ''
    if not text.strip():
        return KeywordResult('unclear')
    repeat = is_repeat_request(text)
    segs = segments(text)
    items = []
    for topic in TOPICS:
        it = _judge_topic(topic, text, segs, current=(topic == current_topic), allow_short=not repeat)
        if it:
            items.append(it)
    if repeat:
        return KeywordResult('repeat_request', items)
    return KeywordResult('answer' if items else 'unclear', items)
