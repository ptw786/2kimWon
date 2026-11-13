"""안전 신호 정규식 (판정규칙.md §3). AI가 끄지 못한다.

부정·과거 표현("넘어질 뻔했는데 괜찮아")도 일부러 걸러내지 않는다 — 놓치는 것보다 한 번 더 보는 쪽.
패턴은 공백·문장부호를 뺀 글자열에 맞춘다 ("숨이 차" / "숨차" / "숨이차" 모두 같다).
"""
import re

from .textutil import clause_at, compact

CATEGORIES: list[tuple[str, list[str]]] = [
    ('낙상', [
        r'넘어졌', r'넘어져', r'넘어질뻔', r'넘어지', r'쓰러졌', r'쓰러져', r'쓰러질', r'자빠졌', r'엎어졌',
        r'미끄러져', r'미끄러졌', r'낙상', r'못일어나', r'못일어났', r'일어날수(가)?없', r'일어나지(를)?못',
    ]),
    ('호흡·가슴', [
        r'숨(이)?차', r'숨(을)?못쉬', r'숨(을)?잘못쉬', r'숨쉬기(가)?힘들', r'숨(이)?막', r'숨(이)?가빠',
        r'호흡(이)?곤란', r'호흡(이)?힘들', r'가슴(이)?(너무|많이|좀|막)?(아파|아프|아팠|답답|조여|쥐어|뻐근)',
        r'가슴통증', r'흉통',
    ]),
    ('의식·마비', [
        r'정신(이)?없', r'정신(을)?잃', r'의식(이)?없', r'기절', r'말(이)?(잘)?안나와', r'말(이)?안나온',
        r'혀(가)?꼬', r'마비', r'한쪽(이|에)?(안움직|힘이없|감각이없)', r'팔다리(가)?안움직', r'감각(이)?없',
    ]),
    ('자해·삶의 의지', [
        r'죽고싶', r'죽고만싶', r'살기싫', r'살고싶지않', r'죽어버리', r'자살', r'목숨(을)?끊', r'그만살',
        r'사는게의미없', r'죽는게나',
    ]),
    ('도움 요청', [
        r'119', r'살려줘', r'살려주', r'도와줘(?!서)', r'도와주세요', r'구급차', r'응급실',
    ]),
]

_COMPILED = [(cat, re.compile('|'.join(pats))) for cat, pats in CATEGORIES]


def detect(text: str) -> list[dict]:
    """[{category, quote}] — 분류마다 최대 1개. quote 는 원문 구절 그대로."""
    if not text:
        return []
    c, index = compact(text)
    found = []
    for cat, rx in _COMPILED:
        m = rx.search(c)
        if m:
            found.append({'category': cat, 'quote': clause_at(text, index[m.start()])})
    return found
