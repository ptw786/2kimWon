"""LLM 어댑터 — 외부 호출은 여기에만 있다.

LLMClient: extract / empathy / summary. 실패하면 LLMError 계열 예외를 던지고, 부르는 쪽이 규칙으로 대신한다.
- OllamaClient: 실제 Ollama (/api/chat, JSON 스키마 format)
- RuleOnly: 항상 거절 → 규칙만으로 동작 (ANSIMON_LLM=off, 테스트 기본값)
- FakeLLM: 테스트용 (지연·예외·응답을 마음대로, 쓰기 트랜잭션 안에서 불리면 실패)
"""
import json
import re
import threading
import time
from pathlib import Path
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field

PROMPTS = Path(__file__).with_name('prompts')
TIMEOUTS = {'extract': 4.0, 'empathy': 3.0, 'summary': 8.0}

Topic = Literal['body', 'meal', 'sleep', 'med', 'mood']


class ExtractItem(BaseModel):
    # 근거(quote)를 먼저 쓰고 값(status)을 나중에 쓰게 필드 순서를 둔다
    topic: Topic
    quote: str = Field(description='답변 원문에서 그대로 복사한 구절')
    status: Literal['good', 'caution', 'risk']


class ExtractNeed(BaseModel):
    type: Literal['meal_difficulty', 'sleep_problem', 'help_request', 'loneliness']
    quote: str = Field(description='답변 원문에서 그대로 복사한 구절')


class ExtractResult(BaseModel):
    intent: Literal['answer', 'repeat_request', 'unclear', 'off_topic']
    items: list[ExtractItem] = Field(default_factory=list)
    needs: list[ExtractNeed] = Field(default_factory=list)   # 선택: 어려움 유형 (판정규칙.md §8)


EXTRACT_SCHEMA = ExtractResult.model_json_schema()


class LLMError(Exception):
    note = '오류'


class LLMTimeout(LLMError):
    def __init__(self, seconds: float):
        super().__init__(f'시간 초과 {seconds:.1f}s')
        self.note = f'시간 초과 {seconds:.1f}s'


class LLMUnavailable(LLMError):
    def __init__(self, note='AI 꺼짐 · 규칙 사용'):
        super().__init__(note)
        self.note = note


class LLMBadOutput(LLMError):
    def __init__(self, note='형식 오류'):
        super().__init__(note)
        self.note = note


class LLMClient(Protocol):
    mode: str            # 'ollama' | 'rules' | 'fake'
    model: str | None

    def extract(self, question_topic: str, question_text: str, answer: str) -> ExtractResult: ...
    def empathy(self, topic: str, answer: str, judged_items: list[dict]) -> str: ...
    def summary(self, items: dict, quotes: list[str]) -> str: ...


# ---- 출력 검증 (어떤 클라이언트든 같은 기준) ----
_BANNED = ('병원', '의사', '진료', '처방', '복용하', '약을 드', '드릴게요', '해 드릴', '약속', '진단')


def clean_empathy(text: str | None) -> str | None:
    """한 문장, 80자 이하, 물음표·의료 조언·약속 없음. 아니면 None (→ 규칙 문장)."""
    if not text:
        return None
    t = text.strip().strip('"\'“”‘’').strip()
    t = re.sub(r'\s+', ' ', t)
    if not t or len(t) > 80 or '?' in t or '？' in t:
        return None
    if any(b in t for b in _BANNED):
        return None
    if not re.search(r'[가-힣]', t):
        return None
    return t


def clean_summary(text: str | None) -> str | None:
    if not text:
        return None
    t = re.sub(r'\s+', ' ', text.strip())
    if not t or len(t) > 200:
        return None
    # '주:', '위험:' 같은 상태 머리표나 목록 기호로 쓴 요약은 버리고 규칙 요약을 쓴다.
    if re.search(r'(^|[.\s])(주의?|위험|양호|미확인)\s*:', t) or re.match(r'^[-•*]', t):
        return None
    return t


def _prompt(name: str) -> str:
    return (PROMPTS / f'{name}.md').read_text(encoding='utf-8')


_TOPIC_KO = {'body': '몸 상태', 'meal': '식사', 'sleep': '수면', 'med': '복약', 'mood': '기분'}
_STATUS_KO = {'good': '양호', 'caution': '주의', 'risk': '위험', 'unknown': '미확인'}


class OllamaClient:
    mode = 'ollama'

    def __init__(self, host: str, model: str):
        self.host = host.rstrip('/')
        self.model = model
        self._reach_cache: tuple[float, bool] | None = None

    def _chat(self, messages, *, options, timeout, fmt=None) -> str:
        body = {'model': self.model, 'messages': messages, 'stream': False, 'keep_alive': '30m', 'options': options}
        if fmt is not None:
            body['format'] = fmt
        try:
            r = httpx.post(f'{self.host}/api/chat', json=body, timeout=timeout)
            r.raise_for_status()
            return r.json()['message']['content']
        except httpx.TimeoutException as e:
            raise LLMTimeout(timeout) from e
        except httpx.HTTPStatusError as e:
            raise LLMUnavailable(f'HTTP {e.response.status_code}') from e
        except httpx.HTTPError as e:
            raise LLMUnavailable('연결 실패') from e
        except (KeyError, ValueError) as e:
            raise LLMBadOutput() from e

    def extract(self, question_topic, question_text, answer) -> ExtractResult:
        user = json.dumps({'topic': question_topic, 'question': question_text, 'answer': answer}, ensure_ascii=False)
        content = self._chat(
            [{'role': 'system', 'content': _prompt('extract')}, {'role': 'user', 'content': user}],
            options={'temperature': 0, 'seed': 42, 'num_predict': 320}, timeout=TIMEOUTS['extract'],
            fmt=EXTRACT_SCHEMA)
        try:
            return ExtractResult.model_validate_json(content)
        except ValueError as e:
            raise LLMBadOutput() from e

    def empathy(self, topic, answer, judged_items) -> str:
        judged = ', '.join(f"{_TOPIC_KO[i['topic']]} {_STATUS_KO[i['status']]}" for i in judged_items) or '없음'
        user = f'질문 주제: {_TOPIC_KO.get(topic, topic)}\n어르신 답변: "{answer}"\n판정: {judged}'
        return self._chat(
            [{'role': 'system', 'content': _prompt('empathy')}, {'role': 'user', 'content': user}],
            options={'temperature': 0.3, 'seed': 42, 'num_predict': 60}, timeout=TIMEOUTS['empathy']).strip()

    def summary(self, items, quotes) -> str:
        lines = [f"- {_TOPIC_KO[t]}: {_STATUS_KO[v['status']]}" + (f" (\"{v['quote']}\")" if v.get('quote') else '')
                 for t, v in items.items()]
        extra = '\n'.join(f'- {q}' for q in quotes) or '- 없음'
        user = '확정된 항목:\n' + '\n'.join(lines) + '\n안전 신호·특이사항:\n' + extra
        return self._chat(
            [{'role': 'system', 'content': _prompt('summary')}, {'role': 'user', 'content': user}],
            options={'temperature': 0, 'seed': 42, 'num_predict': 160}, timeout=TIMEOUTS['summary']).strip()

    def warm(self) -> None:
        try:
            self._chat([{'role': 'user', 'content': '안녕'}], options={'num_predict': 1}, timeout=60)
        except LLMError:
            pass

    def reachable(self) -> bool:
        now = time.monotonic()
        if self._reach_cache and now - self._reach_cache[0] < 15:
            return self._reach_cache[1]
        try:
            ok = httpx.get(f'{self.host}/api/tags', timeout=1.0).status_code == 200
        except httpx.HTTPError:
            ok = False
        self._reach_cache = (now, ok)
        return ok


class RuleOnly:
    mode = 'rules'
    model = None

    def extract(self, question_topic, question_text, answer):
        raise LLMUnavailable()

    def empathy(self, topic, answer, judged_items):
        raise LLMUnavailable()

    def summary(self, items, quotes):
        raise LLMUnavailable()

    def warm(self):
        pass

    def reachable(self) -> bool:
        return False


class FakeLLM:
    """테스트용. 응답은 값 또는 함수, 예외를 넣으면 그 예외를 던진다.

    in_write_tx: 호출 순간 쓰기 트랜잭션이 열려 있는지 알려 주는 함수 — 열려 있으면 AssertionError.
    """
    mode = 'fake'

    def __init__(self, extract=None, empathy='말씀해 주셔서 고마워요.', summary='요약', model='fake-model',
                 in_write_tx=None, delay=0.0):
        self.model = model
        self._extract, self._empathy, self._summary = extract, empathy, summary
        self.in_write_tx = in_write_tx
        self.delay = delay
        self.calls: list[tuple] = []
        self.lock = threading.Lock()

    def _call(self, step, value, *args):
        if self.in_write_tx is not None:
            assert not self.in_write_tx(), f'LLM {step} called inside a write transaction'
        with self.lock:
            self.calls.append((step,) + args)
        if self.delay:
            time.sleep(self.delay)
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            value = value(*args)
            if isinstance(value, BaseException):
                raise value
        return value

    def extract(self, question_topic, question_text, answer):
        v = self._call('extract', self._extract, question_topic, question_text, answer)
        if v is None:
            raise LLMUnavailable('응답 없음')
        return v if isinstance(v, ExtractResult) else ExtractResult.model_validate(v)

    def empathy(self, topic, answer, judged_items):
        return self._call('empathy', self._empathy, topic, answer, judged_items)

    def summary(self, items, quotes):
        return self._call('summary', self._summary, items, quotes)

    def warm(self):
        pass

    def reachable(self) -> bool:
        return True
