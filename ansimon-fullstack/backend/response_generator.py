from scenarios import CLARIFY
from conversation import EMERGENCY_GUIDANCE, LABELS, REPLIES

def generate(topic, action, intents, facts, checks):
    if action=='safety_pause':return EMERGENCY_GUIDANCE
    if action=='risk_confirmation':return '지금도 그런 상황이신가요? 현재 급박한 위험이 있다면 직접 119에 연락해 주세요.'
    if 'stt_error' in intents:return '음성 인식에 실패했어요. 마이크를 다시 켜거나 글자로 답변해 주세요.'
    if 'silence' in intents:return '천천히 답하셔도 괜찮아요. 글자로도 답변하실 수 있어요.'
    if action=='skip':return '지금 확인하기 어려운 항목은 확인되지 않음으로 남길게요.'
    if action=='daily_chat':return '가족이나 일상 이야기를 들려주셨군요. 말씀해 주셔서 감사해요.'
    if 'question_repeat' in intents:return '제가 조금 천천히 여쭤볼게요.'
    if 'ai_question' in intents:return '저는 안심온 돌봄전화예요. 어르신의 오늘 안부를 여쭙고 있어요.'
    if 'help_request' in intents:return '도움이 필요하시군요. 가까운 분이나 담당 생활지원사에게 직접 도움을 요청해 주세요.'
    if topic in facts:
        if facts[topic].get('quality')=='unconfirmed':return '잠은 주무셨군요. 말씀해 주신 내용으로 기록할게요.'
        return REPLIES[topic][facts[topic]['classification']]
    return '말씀하신 내용을 지금 상황으로 확정하기는 어려워요.' if checks==1 else '제가 조금 천천히 여쭤볼게요.'
