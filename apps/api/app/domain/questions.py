"""질문 문장·선택 버튼·고정 문장·규칙 공감 문장 (I/O 없음)."""
import re

TOPICS = ('body', 'meal', 'sleep', 'med', 'mood')

TOPIC_LABELS = {'body': '몸 상태', 'meal': '식사', 'sleep': '수면', 'med': '복약', 'mood': '기분'}
STATUS_LABELS = {'good': '양호', 'caution': '주의', 'risk': '위험', 'unknown': '미확인'}
# 단계 라벨은 rules.yaml grade_labels 한 곳에 있다 (scoring.grade_label)
CALL_STATUS_LABELS = {
    'ringing': '벨 울림', 'in_progress': '통화 중', 'completed': '통화 완료',
    'interrupted': '통화 중단', 'missed': '미응답', 'declined': '수신 거절', 'not_called': '아직 안 함',
}
# 어르신 앱용 쉬운 말
ELDER_STATUS_LABELS = {
    'ringing': '전화가 오고 있어요', 'in_progress': '통화 중이에요', 'completed': '오늘 통화했어요',
    'interrupted': '통화가 중간에 끊겼어요', 'missed': '전화를 못 받으셨어요',
    'declined': '오늘은 전화를 쉬었어요', 'not_called': '아직 전화 전이에요',
}

QUESTIONS = {
    'body': '오늘 몸은 좀 어떠세요?',
    'meal': '오늘 식사는 챙겨 드셨어요?',
    'sleep': '어젯밤에는 잠을 잘 주무셨어요?',
    'med': '드시는 약은 오늘 챙겨 드셨어요?',
    'mood': '오늘 기분은 좀 괜찮으세요?',
}
# 다시 물을 때 쓰는 더 쉬운 말
REASK_QUESTIONS = {
    'body': '몸이 괜찮으세요, 아니면 불편하신 데가 있으세요?',
    'meal': '오늘 밥은 드셨어요?',
    'sleep': '어젯밤에 잠은 잘 주무셨어요?',
    'med': '오늘 약은 드셨어요? 드시는 약이 없으면 없다고 말씀해 주세요.',
    'mood': '오늘 마음은 좀 편하세요?',
}
OPTIONS = {
    'body': ['괜찮아요', '조금 불편해요', '많이 아파요'],
    'meal': ['네, 먹었어요', '조금 먹었어요', '못 먹었어요'],
    'sleep': ['잘 잤어요', '조금 설쳤어요', '거의 못 잤어요'],
    'med': ['네, 먹었어요', '아직 안 먹었어요', '먹는 약 없어요'],
    'mood': ['좋아요', '그저 그래요', '외롭고 울적해요'],
}

GREETING = '{name} 어르신, 안녕하세요. 안심온이에요.'
CLOSING = '오늘도 말씀해 주셔서 고마워요. 내일 또 전화드릴게요.'
SAFETY_NOTICE = '지금 바로 생활지원사님께 알려 드릴게요. 위급하시면 119에 전화하세요.'
REPEAT_PREFIX = '다시 여쭤볼게요.'
REASK_PREFIX = '제가 잘 못 알아들었어요.'
SILENCE_PREFIX = '잘 안 들렸어요.'
SKIP_LINE = '괜찮아요, 다음 질문으로 넘어갈게요.'
OPTION_HINT = "'{option}'처럼 짧게 말씀해 주셔도 돼요."

# 규칙 공감 문장: (주제, 상태)별
EMPATHY_TEMPLATES = {
    ('body', 'good'): '몸이 괜찮으시다니 다행이에요.',
    ('body', 'caution'): '몸이 좀 불편하셨군요. 말씀해 주셔서 고마워요.',
    ('body', 'risk'): '많이 힘드셨겠어요. 말씀해 주셔서 고마워요.',
    ('meal', 'good'): '식사를 챙겨 드셨다니 다행이에요.',
    ('meal', 'caution'): '식사를 제대로 못 하셨군요.',
    ('meal', 'risk'): '며칠째 식사를 잘 못 하셨다니 걱정돼요.',
    ('sleep', 'good'): '잘 주무셨다니 다행이에요.',
    ('sleep', 'caution'): '잠을 좀 설치셨군요.',
    ('sleep', 'risk'): '며칠째 잠을 못 주무셔서 많이 피곤하시겠어요.',
    ('med', 'good'): '약을 잘 챙기셨군요.',
    ('med', 'caution'): '약을 아직 못 챙기셨군요.',
    ('med', 'risk'): '약을 며칠 못 드셨다니 걱정돼요.',
    ('mood', 'good'): '기분이 괜찮으시다니 저도 기뻐요.',
    ('mood', 'caution'): '마음이 좀 가라앉으셨군요. 말씀해 주셔서 고마워요.',
    ('mood', 'risk'): '마음이 많이 힘드셨겠어요. 말씀해 주셔서 고마워요.',
}
MED_NONE_EMPATHY = '알겠어요, 드시는 약은 없으시군요.'
# 기분 신호는 어느 질문에서 나왔든 먼저 공감한다 (어떤 말을 했는지 반영)
MOOD_EMPATHY = [
    (r'외로|외롭|적적|쓸쓸|아무도', '많이 외로우셨겠어요. 말씀해 주셔서 고마워요.'),
    (r'우울|울적|슬프|슬퍼|눈물|울었', '마음이 많이 가라앉으셨군요. 말씀해 주셔서 고마워요.'),
    (r'걱정|불안|무서', '걱정이 많으셨군요. 이야기해 주셔서 고마워요.'),
    (r'심심', '하루가 많이 심심하셨군요. 말씀해 주셔서 고마워요.'),
    (r'속상|서운|짜증|화', '속상한 일이 있으셨군요. 말씀해 주셔서 고마워요.'),
]
GENERIC_EMPATHY = '말씀해 주셔서 고마워요.'
# 식사 재질문에 대한 대답 뒤 (같은 공감 문장을 두 번 하지 않게)
FOLLOWUP_EMPATHY = {
    'meal_difficulty': '식사 챙기기가 많이 어려우셨군요. 말씀해 주셔서 고마워요.',
    None: '알겠어요. 끼니 거르지 않게 꼭 챙겨 드세요.',
}

_MED_NONE = re.compile(r'약\s*(은|이)?\s*(없|안\s*먹어도|필요\s*없)')


def fallback_empathy(asked_topic: str, items: list[dict], answer: str) -> str:
    """LLM이 실패했을 때: 감지된 상태·주제로 고른다. 기분 신호가 있으면 그것부터."""
    for it in items:
        if it['topic'] == 'mood' and it['status'] in ('caution', 'risk'):
            for pattern, text in MOOD_EMPATHY:
                if re.search(pattern, answer):
                    return text
            return EMPATHY_TEMPLATES[('mood', it['status'])]
    current = [it for it in items if it['topic'] == asked_topic]
    if current:
        status = current[0]['status']
        if asked_topic == 'med' and status == 'good' and _MED_NONE.search(answer):
            return MED_NONE_EMPATHY
        return EMPATHY_TEMPLATES[(asked_topic, status)]
    worst = sorted(items, key=lambda i: {'risk': 0, 'caution': 1, 'good': 2}[i['status']])
    if worst:
        return EMPATHY_TEMPLATES[(worst[0]['topic'], worst[0]['status'])]
    return GENERIC_EMPATHY
