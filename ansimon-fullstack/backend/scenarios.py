from conversation import QUESTIONS
# Each clarification asks one positive-polarity question; yes/no cannot refer to two alternatives.
CLARIFY = {
 'condition':'지금 몸 상태가 괜찮으세요?',
 'meal':'오늘 식사를 드셨나요?',
 'sleep':'어젯밤 잠을 편히 주무셨나요?',
 'medicine':'복용하실 약을 챙겨 드셨나요?',
 'mood':'오늘 기분이 좋으세요?'}
YES={'응','네','예','어','응응','네네','맞아','맞아요','그래','그래요','그럼요','그렇죠','그렇습니다'}
NO={'아니','아니요','아뇨','아니야','아니에요','아닙니다'}

def binary_question(question,topic):
    if not question or '아니면' in question or '또는' in question:return False
    if question=='그 이야기를 조금 더 들려주시겠어요?':return False
    if question==QUESTIONS[0][1] or question==QUESTIONS[4][1]:return False
    return question in CLARIFY.values() or topic in ('meal','sleep','medicine') or question=='지금도 위험한 상황이신가요?'
