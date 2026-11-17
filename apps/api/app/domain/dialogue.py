"""통화 흐름 상태 기계 (결정적, I/O 없음).

지키는 약속 (이전 버전 버그를 구조적으로 막음):
- 질문 문장은 언제나 state.index 하나에서만 나온다. 답변은 그 턴에 실제로 물은 주제(asked_topic)에 저장된다.
- '다시 말해 달라'는 index 를 바꾸지 않는다 → 다음 "네"는 다시 물은 그 주제에 저장된다.
- 안전 신호는 기록하고 고정 안내 후 다음 질문으로 넘어간다 — 확인 질문으로 붙잡지 않는다.
- 알아듣기 어려우면 최대 2번 다시 묻고, 그래도 안 되면 '미확인'으로 두고 넘어간다.
- 식사를 못 했다는데 이유가 없으면 한 번만 "아직 식사 전이신가요, 아니면 식사하기 어려운 이유가 있으신가요?"
  (제안서 3.나.2). 다시 묻기 횟수에 들어가고, 이미 기록한 상태는 내리지 않으며, 그 대답 뒤에는 무조건 넘어간다.
"""
import re
from dataclasses import dataclass, replace

from . import questions as Q
from .questions import TOPICS
from .scoring import SEVERITY, rules
from .textutil import compact, quote_in_answer

_R = rules()['dialogue']
MAX_REASKS = _R['max_reasks']
MAX_REPEATS = _R['max_repeats']
TOTAL = len(TOPICS)
_FU = rules()['meal_followup']
FOLLOWUP_QUESTION = _FU['question']
FOLLOWUP_OPTIONS = list(_FU['options'])
# '안 먹음' 쪽 표현일 때만 다시 묻는다 ("조금 먹었어"는 묻지 않음)
_NOT_EATEN = re.compile(r'(못|안)먹|굶|걸렀|거르|걸러|식사(하기)?전|밥(먹기)?전|아니')
# 이유를 말했으면 묻지 않는다 ("입맛이 없어서", "속이 안 좋아서" …)
_REASON = re.compile(r'입맛|밥맛|소화|체했|속(이|가)|아파|아퍼|아프|바빠|바쁘|늦잠|늦게|생각(이)?없|싫|입원|병원|이(가|빨)|틀니|'
                     r'약속|외출|나가|(어|아|워|와|해|여|져|러|라|빠|파|퍼|내|래)서|니까|길래|느라|때문')


@dataclass(frozen=True)
class State:
    index: int = 0      # 지금 묻고 있는 주제 번호 (0부터). TOTAL 이면 끝
    reasks: int = 0     # 이 주제에서 다시 물은 횟수
    repeats: int = 0    # 이 주제에서 '다시 말해 달라'를 받아 준 횟수

    @property
    def topic(self) -> str | None:
        return TOPICS[self.index] if self.index < TOTAL else None


@dataclass(frozen=True)
class Decision:
    action: str            # next | repeat | reask | safety | finish
    asked_topic: str       # 이 답변이 대답한 주제 (= 이번 턴에 물었던 주제)
    state: State           # 다음 상태
    mark_unknown: bool     # 물었던 주제를 미확인으로 두고 넘어감
    finished: bool
    followup: bool = False  # 다음 질문이 식사 재질문(FOLLOWUP_QUESTION)


def wants_meal_followup(asked: str, items: list[dict], needs: list[dict], answer: str) -> bool:
    """식사 질문에 '못/안 먹음'(주의·위험)인데 어려움 유형도 이유도 없으면 True."""
    if asked != 'meal' or any(n['type'] == 'meal_difficulty' for n in needs):
        return False
    meal = next((i for i in items if i['topic'] == 'meal'), None)
    if meal is None or meal['status'] not in ('caution', 'risk'):
        return False
    if any(i['topic'] != 'meal' and i['status'] in ('caution', 'risk') for i in items):
        return False   # 몸·기분 같은 다른 사정을 같이 말했으면 그게 이유다
    return _just_not_eaten(answer)


def _just_not_eaten(text: str) -> bool:
    c = compact(text or '')[0]
    return bool(_NOT_EATEN.search(c)) and not _REASON.search(c)


def decide(state: State, *, intent: str, judged_topics: set[str], safety_hit: bool, silence: bool,
           want_followup: bool = False, in_followup: bool = False) -> Decision:
    """want_followup: 이 답변 뒤에 식사 재질문을 하고 싶다 (wants_meal_followup).
    in_followup: 이 답변이 식사 재질문에 대한 대답이다 → 판정과 상관없이 넘어간다."""
    asked = state.topic
    if asked is None:
        raise ValueError('이미 끝난 통화')
    answered = asked in judged_topics and not silence

    def advance(action, mark_unknown=False):
        nxt = State(index=state.index + 1)
        finished = nxt.index >= TOTAL
        if finished and action == 'next':
            action = 'finish'
        return Decision(action, asked, nxt, mark_unknown, finished)

    if safety_hit:
        return advance('safety', mark_unknown=not answered)
    if not silence and intent == 'repeat_request' and state.repeats < MAX_REPEATS:
        return Decision('repeat', asked, replace(state, repeats=state.repeats + 1), False, False, in_followup)
    if in_followup:
        return advance('next')
    if answered:
        if want_followup and state.reasks < MAX_REASKS:
            return Decision('reask', asked, replace(state, reasks=state.reasks + 1), False, False, True)
        return advance('next')
    if state.reasks < MAX_REASKS:
        return Decision('reask', asked, replace(state, reasks=state.reasks + 1), False, False)
    return advance('next', mark_unknown=True)


def question_for(state: State, *, reask: bool = False) -> str | None:
    t = state.topic
    if t is None:
        return None
    if not reask:
        return Q.QUESTIONS[t]
    text = Q.REASK_QUESTIONS[t]
    if state.reasks >= MAX_REASKS:
        text += ' ' + Q.OPTION_HINT.format(option=Q.OPTIONS[t][0])
    return text


def step_of(state: State) -> dict:
    return {'index': min(state.index + 1, TOTAL), 'total': TOTAL}


def start_result(name: str) -> dict:
    s = State()
    question = Q.QUESTIONS[s.topic]
    return {
        'ai_text': Q.GREETING.format(name=name) + ' ' + question,
        'empathy': None, 'question': question, 'topic': s.topic, 'options': list(Q.OPTIONS[s.topic]),
        'step': step_of(s), 'action': 'start', 'safety': False, 'finished': False, 'llm_used': False,
    }


_THANKS = re.compile(r'고마|감사')


def _without_thanks(text: str | None) -> str | None:
    """마무리 인사(CLOSING)에 이미 감사가 있으니 공감 문장의 감사 문장은 뺀다."""
    if not text:
        return text
    kept = [s for s in re.split(r'(?<=[.!。])\s+', text.strip()) if s and not _THANKS.search(s)]
    return ' '.join(kept) or None


def compose(decision: Decision, *, empathy: str | None, silence: bool, safety_hit: bool, llm_used: bool) -> dict:
    """TurnResult (CONTRACT.md) 를 만든다. 질문 원문은 항상 decision.state 에서 나온다."""
    st = decision.state
    if decision.followup:
        question = FOLLOWUP_QUESTION
        if decision.action == 'repeat':
            lead, emp = Q.REPEAT_PREFIX, None
        else:
            lead = emp = empathy
    elif decision.action == 'repeat':
        question = question_for(st)
        lead, emp = Q.REPEAT_PREFIX, None
    elif decision.action == 'reask':
        question = question_for(st, reask=True)
        emp = empathy
        lead = empathy or (Q.SILENCE_PREFIX if silence else Q.REASK_PREFIX)
    elif decision.action == 'safety':
        question = question_for(st)
        lead = emp = Q.SAFETY_NOTICE
    else:  # next | finish
        question = question_for(st)
        emp = Q.SKIP_LINE if decision.mark_unknown else (empathy or Q.GENERIC_EMPATHY)
        if decision.finished:
            emp = _without_thanks(emp)
        lead = emp
    tail = question if question else Q.CLOSING
    topic = st.topic
    return {
        'ai_text': f'{lead or ""} {tail}'.strip(),
        'empathy': emp,
        'question': question,
        'topic': topic,
        'options': FOLLOWUP_OPTIONS[:] if decision.followup else (list(Q.OPTIONS[topic]) if topic else []),
        'step': step_of(st),
        'action': decision.action,
        'safety': safety_hit,
        'finished': decision.finished,
        'llm_used': llm_used,
    }


def combine_extractions(asked_topic: str, answer: str, rule_items: list[dict], llm_items: list[dict] | None) -> list[dict]:
    """AI 항목과 키워드 항목을 합친다 → 주제마다 하나, 더 나쁜 쪽 (AI가 규칙 신호를 내리지 못함).

    - AI 항목은 quote 가 답변 원문에 없으면 버린다.
    - 지금 묻지 않은 주제는 주의·위험만 남긴다 (양호는 그 질문을 할 때 듣는다).
    결과: [{topic, status, quote, origin}]
    """
    best: dict[str, dict] = {}
    cands = []
    for it in llm_items or []:
        if quote_in_answer(it.get('quote', ''), answer):
            cands.append({**it, 'origin': 'llm'})
    cands += [{**it, 'origin': 'rule'} for it in rule_items]
    for it in cands:
        if it['topic'] != asked_topic and it['status'] == 'good':
            continue
        cur = best.get(it['topic'])
        if cur is None or SEVERITY[it['status']] > SEVERITY[cur['status']]:
            best[it['topic']] = {'topic': it['topic'], 'status': it['status'], 'quote': it['quote'], 'origin': it['origin']}
    return [best[t] for t in TOPICS if t in best]


def combine_needs(answer: str, rule_needs: list[dict], llm_needs: list[dict] | None, labels: dict[str, str]) -> list[dict]:
    """규칙 어려움 ∪ AI 어려움. 규칙이 찾은 것은 AI가 지우지 못하고, AI 것은 인용이 답변 원문에 있을 때만 더한다.
    결과: [{type, label, quote, origin}] 유형마다 하나 (규칙 우선)."""
    out = {n['type']: dict(n) for n in rule_needs}
    for n in llm_needs or []:
        if n['type'] in out or n['type'] not in labels or not quote_in_answer(n.get('quote', ''), answer):
            continue
        if n['type'] == 'meal_difficulty' and _just_not_eaten(n['quote']):
            continue   # "아직 안 먹었어"는 미식사이지 식사 어려움이 아니다 (제안서 3.나.2)
        out[n['type']] = {'type': n['type'], 'label': labels[n['type']], 'quote': n['quote'], 'origin': 'llm'}
    return list(out.values())
