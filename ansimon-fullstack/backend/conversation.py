"""Deterministic Korean check-in rules. No model, remote API, or diagnosis."""
import re
import unicodedata
from dataclasses import dataclass

QUESTIONS = [
    ('condition', '안녕하세요, 안심온입니다. 오늘 몸은 좀 어떠세요?'),
    ('meal', '오늘 식사는 잘 챙겨 드셨나요?'),
    ('sleep', '어젯밤 잠은 편히 주무셨나요?'),
    ('medicine', '드시는 약은 잘 챙겨 드셨나요?'),
    ('mood', '오늘 기분은 어떠세요? 불편한 곳은 없으세요?'),
]
LABELS = dict(condition='건강 상태', meal='식사', sleep='수면', medicine='복약', mood='기분')
CLASS_LABELS = dict(positive='긍정', negative='부정', neutral='중립', unknown='확인 불가', unclassified='기존 답변·미분류')
EMERGENCY_GUIDANCE = '긴급한 도움이 필요할 수 있습니다. 지금 직접 119에 연락하거나 가까운 분에게 도움을 요청해 주세요. 안심온은 실제 119 신고를 하지 않습니다.'
MAX_REASKS = 2

@dataclass(frozen=True)
class Assessment:
    classification: str
    reply: str
    emergency: bool = False


def normalize(answer):
    return re.sub(r'[\s\W_]+', '', unicodedata.normalize('NFKC', answer).lower())


def has(pattern, text):
    return re.search(pattern, text) is not None


# Negated symptoms must be masked before looking for adverse symptoms.
NO_SYMPTOM = r'안아[파프]|아프지않|아프지는않|아픈곳[은이]?없|통증[은이]?없|불편한곳[은이]?없|안불편|불편하지않'
NO_DISTRESS = r'외롭지않|외롭지는않|우울하지않|우울하지는않|불안하지않|슬프지않|걱정[은이]?없'
NEG_EAT = r'안먹|못먹|먹지않|먹지못|먹지는않|먹지는못|식사[를는]?안했|식사[를는]?못했|식사[를는]?하지않|굶|끼니.{0,4}거[르름]'
NEG_SLEEP = r'못잤|안잤|못자|안자|잠.{0,4}안와|잠.{0,4}못들|설쳤|설치|불면|자지못|자지않|잠.{0,3}깼'
NEG_HEALTH = r'아[파프팠]|통증|힘들|어지[러럽]|불편|몸살|기침|열[이가]?(?:나|있)'
NEG_MOOD = r'외[로롭]|우울|슬[퍼프]|쓸쓸|불안|기분.{0,2}나[빠쁘]|속상|답답|걱정|힘들|아[파프]|불편'


def urgent(text):
    text = re.sub(r'죽고싶지않|호흡곤란[은이]?없|숨[이가]?안차|가슴[이은]?안아[파프]', '', text)
    return has(r'숨[을이가]?못쉬|숨[이가]?안쉬|호흡곤란|가슴.{0,5}(?:너무|심하게).{0,3}아[파프]|의식.{0,2}잃|쓰러졌|살려[줘주]|죽고싶|극단적.{0,3}선택', text)


REPLIES = {
    'condition': {
        'positive':'몸이 괜찮으시다니 다행이에요.',
        'negative':'몸이 불편하시군요. 증상이 심하거나 계속되면 도움을 요청해 주세요.',
        'neutral':'오늘 몸 상태를 알려주셔서 감사합니다.',
    },
    'meal': {
        'positive':'식사를 챙겨 드셨군요. 알려주셔서 감사합니다.',
        'negative':'아직 식사를 못 하셨군요. 식사를 챙기실 수 있으면 좋겠어요.',
        'neutral':'식사하신 정도를 알려주셔서 감사합니다.',
    },
    'sleep': {
        'positive':'편히 주무셨다니 다행이에요.',
        'negative':'잠을 편히 못 주무셨군요. 불편함이 계속되면 도움을 요청해 주세요.',
        'neutral':'어젯밤 수면에 대해 알려주셔서 감사합니다.',
    },
    'medicine': {
        'positive':'약을 챙겨 드셨군요. 알려주셔서 감사합니다.',
        'negative':'약을 챙겨 드시지 못하셨군요. 복용 방법은 담당 의료진이나 약사에게 확인해 주세요.',
        'neutral':'드시는 약이 없으시군요. 알려주셔서 감사합니다.',
    },
    'mood': {
        'positive':'기분이 좋으시다니 다행이에요.',
        'negative':'마음이나 몸이 편치 않으시군요. 가까운 분이나 담당 생활지원사에게 말씀해 주세요.',
        'neutral':'오늘 기분을 알려주셔서 감사합니다.',
    },
}


def assess(topic, answer):
    """Unknown is deliberately conservative: unmatched text is never fabricated."""
    text = normalize(answer)
    if urgent(text):
        return Assessment('negative', EMERGENCY_GUIDANCE, True)
    category = 'unknown'
    if not text or has(r'모르겠|잘몰라|글쎄|기억[이은]?안나|기억나지않|말하기싫|대답하기싫|무슨말', text):
        return Assessment(category, '말씀을 이해하기 어려워요. 다시 한번 알려주시겠어요?')
    if topic == 'meal' and has(r'약|복용', text) and not has(r'밥|식사|끼니', text):
        return Assessment('unknown', '식사를 챙겨 드셨는지 다시 한번 알려주시겠어요?')
    if topic == 'medicine' and has(r'밥|식사|끼니', text) and not has(r'약|복용', text):
        return Assessment('unknown', '드시는 약을 챙기셨는지 다시 한번 알려주시겠어요?')
    if topic in ('meal','medicine') and has(r'(?:안먹은|못먹은|먹지않은)(?:건|게)아니', text):
        return Assessment('unknown', '챙겨 드셨는지 다시 한번 알려주시겠어요?')
    if topic == 'condition':
        masked = re.sub(NO_SYMPTOM, '', text)
        if has(r'안아픈(?:건|게)아니|안아프진않|아프지않은(?:건|게)아니', text) or has(NEG_HEALTH, masked): category = 'negative'
        elif has(NO_SYMPTOM + r'|괜찮|건강[해합]|몸.{0,3}좋|잘지[내냈]|별탈없', text): category = 'positive'
    elif topic == 'meal':
        if has(NEG_EAT, text): category = 'negative'
        elif has(r'조금.{0,3}먹|반만먹|간단히.{0,3}먹|대충먹', text): category = 'neutral'
        elif has(r'먹었|먹[고는]있|식사.{0,3}했|챙겨먹|잘먹', text): category = 'positive'
    elif topic == 'sleep':
        if has(NEG_SLEEP, text): category = 'negative'
        elif has(r'조금잤|그럭저럭잤|보통', text): category = 'neutral'
        elif has(r'잘잤|푹잤|편히.{0,3}잤|잘주무|편히주무|숙면|잘잤습', text): category = 'positive'
    elif topic == 'medicine':
        if has(r'약.{0,2}안먹어도[돼되]', text): category = 'neutral'
        elif has(NEG_EAT + r'|약.{0,3}빼먹|약.{0,3}깜빡|약.{0,3}잊', text): category = 'negative'
        elif has(r'먹는약[은이]?없|드시는약[은이]?없|복용.{0,3}약[은이]?없|약[은이]?없어|처방.{0,3}없|약.{0,2}안먹어도[돼되]', text): category = 'neutral'
        elif has(r'먹었|챙겨먹|복용했|복용중|잘먹', text): category = 'positive'
    elif topic == 'mood':
        masked = re.sub(NO_DISTRESS + '|' + NO_SYMPTOM, '', text)
        if has(NEG_MOOD, masked): category = 'negative'
        elif has(NO_DISTRESS + '|' + NO_SYMPTOM + r'|기분.{0,3}좋|행복|즐거|편안|괜찮|잘지[내냈]', text): category = 'positive'
    if category == 'unknown' and has(r'그저그래|보통|그냥그래|평소와같|평범', text):
        category = 'neutral'
    if category == 'unknown' and topic in ('meal','sleep','medicine'):
        if re.fullmatch(r'네|예|응|그럼요|그렇습니다|네그래요', text): category = 'positive'
        elif re.fullmatch(r'아니|아니요|아니오|아뇨', text): category = 'negative'
    if category == 'unknown':
        return Assessment(category, '말씀을 이해하기 어려워요. 다시 한번 알려주시겠어요?')
    reply = REPLIES[topic][category]
    # Neutral medication answers other than "no medication" are not inferred.
    if category == 'neutral' and topic == 'medicine' and not has(r'약.{0,5}없|안먹어도[돼되]|처방.{0,3}없', text):
        reply = '복약 상황을 알려주셔서 감사합니다.'
    return Assessment(category, reply)


def summary_for(turns):
    confirmed = [turn for turn in turns if turn.get('classification') in ('positive','negative','neutral')]
    # Quote only the actual accepted answers. No diagnosis or inferred medication.
    summary = ' / '.join(f"{LABELS.get(t['topic'],t['topic'])}: {t['answer']}" for t in confirmed)
    unknown = [LABELS.get(t['topic'],t['topic']) for t in turns if t.get('classification') == 'unknown']
    if not summary: summary = '확인된 답변이 없습니다.'
    if unknown: summary += ' / 확인 불가 항목: ' + ', '.join(unknown)
    if any(t.get('emergency') for t in turns): summary += ' / 직접 119 연락 안내문 생성(자동 신고 없음).'
    return summary
