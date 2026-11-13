"""띄어쓰기·문장부호에 흔들리지 않게 비교하기 위한 도우미 (safety.py·keywords.py 공용)."""
import re

_SKIP = set(' \t\r\n.,!?~…·"\'“”‘’()[]-')
_CLAUSE_SPLIT = re.compile(r'[.!?\n,~…]+')


def compact(text: str) -> tuple[str, list[int]]:
    """공백·문장부호를 뺀 문자열과, 각 글자가 원문 어디였는지."""
    chars, index = [], []
    for i, ch in enumerate(text):
        if ch in _SKIP:
            continue
        chars.append(ch)
        index.append(i)
    return ''.join(chars), index


def clause_at(text: str, pos: int) -> str:
    """원문 pos 를 포함하는 구절(쉼표·마침표 사이)을 원문 그대로 돌려준다."""
    start = 0
    for m in _CLAUSE_SPLIT.finditer(text):
        if m.start() > pos:
            return text[start:m.start()].strip() or text.strip()
        start = m.end()
    return text[start:].strip() or text.strip()


_SEGMENT_SPLIT = re.compile(r'[.!?\n,~…]+|(?<=는데)\s+|(?<=은데)\s+|(?<=지만)\s+|(?<=면서)\s+|(?<=[고서며])\s+')


def segments(text: str) -> list[str]:
    """답변을 구절로 나눈다: 문장부호와 '~는데 / ~지만 / ~고 / ~서' 뒤에서."""
    parts, start = [], 0
    for m in _SEGMENT_SPLIT.finditer(text):
        parts.append(text[start:m.start()])
        start = m.end()
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def normalize_ws(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def quote_in_answer(quote: str, answer: str) -> bool:
    """quote 가 답변 원문 안에 실제로 있는지 (공백 차이는 무시)."""
    q = re.sub(r'\s+', '', quote or '')
    return bool(q) and q in re.sub(r'\s+', '', answer or '')
