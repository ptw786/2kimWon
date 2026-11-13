"""가상 어르신 7명 + 지난 6일·오늘 통화 시드.

통화는 실제 대화 흐름(calls.process_turn)을 그대로 돌려 만든다 → 턴·판정·점수가 실제 규칙과 같다.
AI 부분은 SeedLLM(키워드 판정을 AI 결과처럼 돌려줌)이 맡고, ai_runs 에는 '시드 데이터'라고 적는다.
"""
import hashlib
import json
from datetime import datetime, timedelta

from . import calls, db
from .domain import keywords, scoring
from .domain import questions as Q
from .services.llm import ExtractResult

RESIDENTS = [
    # code, name, age, region(시도 시군구 — 복지서비스 검색용), neighborhood, call_time, memo
    ('KY-01', '김영자', 78, '대전광역시 중구', '중구 은행동', '08:30', '무릎이 안 좋아 외출이 적음'),
    ('KY-02', '이순희', 82, '대전광역시 서구', '서구 둔산동', '09:00', None),
    ('KY-03', '박정호', 75, '대전광역시 유성구', '유성구 봉명동', '09:30', '화장실 미끄럼 주의'),
    ('KY-04', '최복순', 80, '대전광역시 동구', '동구 가양동', '10:00', '보청기 사용'),
    ('KY-05', '정말순', 77, '대전광역시 대덕구', '대덕구 법동', '10:30', None),
    ('KY-06', '한덕수', 84, '대전광역시 중구', '중구 대흥동', '11:00', '고혈압약 복용'),
    # 서대문구: 데이터에 '저소득 어르신 무료급식 지원 사업'(경로식당·도시락·밑반찬 배달)이 있는 구 → 연계 시연용
    ('KY-07', '윤옥순', 81, '서울특별시 서대문구', '서대문구 홍은동', '11:30', '혼자 식사 준비가 어려움'),
]
DAEJEON_GU = ('중구', '서구', '동구', '유성구', '대덕구')
SEOUL_GU = ('종로구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구',
            '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구',
            '송파구', '강동구')


def region_for(neighborhood: str | None) -> str:
    """동네 이름의 구 → 지역 ('중구 은행동' → '대전광역시 중구'). 중구·서구·동구는 대전으로 본다. 모르면 ''."""
    gu = (neighborhood or '').split()[0] if (neighborhood or '').split() else ''
    if gu in DAEJEON_GU:
        return f'대전광역시 {gu}'
    if gu in SEOUL_GU:
        return f'서울특별시 {gu}'
    return ''

GOOD = {
    'body': ['괜찮아요', '응, 안 아파', '그럭저럭 괜찮아'],
    'meal': ['네, 먹었어요', '아침 잘 먹었어', '응, 밥 먹었지'],
    'sleep': ['잘 잤어요', '푹 잤어', '응, 잘 잤어'],
    'med': ['네, 먹었어요', '약 챙겨 먹었어', '응, 먹었어'],
    'mood': ['좋아요', '괜찮아', '그럭저럭 괜찮아'],
}

# 날짜 오프셋(-6 … 0) → 'missed' | 'declined' | None(통화 없음) | dict
#   dict: {topic: 답변 또는 [답변들]}, 'hangup_after': n (n개 답한 뒤 끊음)
SCRIPTS = {
    'KY-01': {  # 식사 주의 → 위험, 어제 미응답 → 오늘 '오늘 확인'
        -3: {'meal': '아침은 걸렀어. 입맛이 없어서.'},
        -2: {'meal': '입맛이 없어서 조금 먹었어', 'sleep': '잠을 좀 설쳤어'},
        -1: 'missed',
        # 이유 없이 '못 먹었어' → 식사 재질문 → 식사 어려움 (대전 중구엔 식사 지원 사업이 없어 중앙부처로 안내)
        0: {'meal': ['이틀째 밥을 제대로 못 먹었어', '혼자 차려 먹기가 힘들어서 그래'], 'sleep': '잠은 좀 설쳤지'},
    },
    'KY-02': {  # 수면 주의 2일, 한 번 통화 중단
        -4: {'hangup_after': 2},
        -1: {'sleep': '잠을 설쳤어'},
        0: {'sleep': '자다가 자꾸 깼어', 'body': '허리가 좀 쑤셔'},
    },
    'KY-03': {  # 지난 안전 신호(낙상), 오늘은 아직
        -5: {'med': '약을 깜빡했어'},
        -2: {'body': '어제 화장실에서 넘어질 뻔했어. 지금은 괜찮아.'},
        0: None,
    },
    'KY-04': {  # 이틀 연속 미응답, 오늘은 아직
        -4: {'mood': '좀 적적해'},
        -2: 'missed',
        -1: 'missed',
        0: None,
    },
    'KY-05': {},  # 매일 양호
    'KY-06': {  # 복약 주의 → 위험, 기분 위험
        -5: 'declined',
        -3: {'meal': ['뭐라고?', '먹었어']},
        -1: {'med': '약을 깜빡했어'},
        0: {'med': '약을 며칠 안 먹었어', 'mood': '아무도 안 와서 적적해'},
    },
    'KY-07': {  # 식사 어려움이 며칠째 이어짐 → 서대문구 무료급식 연계. 오늘은 아직 (시연에서 직접 걸기)
        -5: {'meal': '먹을 게 없어서 못 먹었어'},
        -3: {'meal': '혼자 차려 먹기가 힘들어', 'mood': '말할 사람이 없어서 적적해'},
        -2: 'missed',
        -1: {'meal': ['아직 안 먹었어', '반찬 살 돈이 없어서 그래']},
        0: None,
    },
}


class SeedLLM:
    """키워드 판정을 AI 결과처럼 돌려주는 시드 전용 클라이언트 (네트워크 없음)."""
    mode = 'seed'
    seed_note = '시드 데이터'

    def __init__(self, model: str):
        self.model = model

    def seed_ms(self, step: str) -> int:
        base = {'extract': 280, 'empathy': 220, 'summary': 900}[step]
        return base + int(hashlib.md5(f'{step}{db.now_iso()}'.encode()).hexdigest()[:3], 16) % 400

    def extract(self, question_topic, question_text, answer):
        r = keywords.extract(question_topic, answer)
        return ExtractResult.model_validate({'intent': r.intent, 'items': r.items})

    def empathy(self, topic, answer, judged_items):
        return Q.fallback_empathy(topic, judged_items, answer)

    def summary(self, items, quotes):
        return scoring.rule_summary(items, [], 'completed')


def _kst(day, hhmm: str, plus_seconds: int = 0) -> datetime:
    hh, mm = map(int, hhmm.split(':'))
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=db.KST) + timedelta(seconds=plus_seconds)


def _run_call(conn, llm, rid: int, start: datetime, script, variant: int) -> None:
    clock = {'t': start}

    def tick(sec):
        clock['t'] += timedelta(seconds=sec)

    with db.local_clock(lambda: clock['t']):
        cid = calls.create_call(conn, rid, origin='seed')
        if script == 'missed':
            calls.finish_call(conn, cid, 'missed', db.iso(start + timedelta(seconds=calls.RING_SECONDS)))
            return
        if script == 'declined':
            tick(12)
            calls.decline_call(conn, cid)
            return
        tick(9)
        calls.answer_call(conn, cid)
        hangup_after = script.get('hangup_after')
        answered, n = 0, 0
        for topic in Q.TOPICS:
            answers = script.get(topic) or GOOD[topic][variant % 3]
            for ans in ([answers] if isinstance(answers, str) else answers):
                tick(14 + (n * 7) % 11)
                n += 1
                result, finished = calls.process_turn(conn, llm, cid, ans, 'stt', f'seed-{cid}-{n}')
            answered += 1
            if finished:
                calls.finalize_summary(conn, llm, cid)
                return
            if hangup_after and answered >= hangup_after:
                tick(10)
                calls.hangup_call(conn, cid)
                calls.finalize_summary(conn, llm, cid)
                return
        raise RuntimeError(f'seed call {cid} did not finish: {json.dumps(result, ensure_ascii=False)}')


def seed(conn, *, model_name: str) -> None:
    """빈 DB 에 시드를 넣는다. 한 트랜잭션으로 묶어 빠르게."""
    llm = SeedLLM(model_name)
    real_now = db.now()
    today = real_now.astimezone(db.KST).date()
    with db.tx(conn):
        ids = {}
        for code, name, age, region, hood, call_time, memo in RESIDENTS:
            ids[code] = conn.execute(
                'INSERT INTO residents (code, name, age, region, neighborhood, call_time, memo, is_virtual, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)',
                (code, name, age, region, hood, call_time, memo, db.iso(real_now - timedelta(days=30)))).lastrowid
        for offset in range(-6, 1):
            day = today + timedelta(days=offset)
            for i, (code, _name, _age, _region, _hood, call_time, _memo) in enumerate(RESIDENTS):
                script = SCRIPTS[code].get(offset, {})
                if script is None:
                    continue
                start = _kst(day, call_time, 20 + i * 3)
                if offset == 0:   # 오늘 통화는 지금보다 앞에 있어야 한다
                    latest = real_now - timedelta(minutes=40 - i * 5)
                    start = max(min(start, latest), _kst(day, '00:01'))
                _run_call(conn, llm, ids[code], start, script, variant=(offset + i) % 3)
