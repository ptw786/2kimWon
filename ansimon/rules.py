"""안부전화 시연용 키워드 규칙과 우선순위 점수."""
import re

TOPICS = ('몸 상태', '식사', '수면', '복약', '기분')
WEIGHTS = dict(zip(TOPICS, (9, 6, 4, 8, 5)))
RULES = {
    '몸 상태': (
        (r'쓰러졌|넘어졌|낙상했|심하게\s*아프', 3, '넘어짐 또는 심한 불편 표현'),
        (r'어지럽|어지러|아파|아프|통증이?\s*있|열이\s*나', 2, '몸 상태 불편 표현'),
        (r'피곤|기운이\s*없', 1, '피로 표현'),
    ),
    '식사': ((r'(?:밥|식사|끼니|아침|점심|저녁)[^.!?;]{0,12}(?:못\s*먹|안\s*먹|거르|걸렀)|굶었', 2, '식사 거름 표현'),),
    '수면': ((r'(?:잠|수면)[^.!?;]{0,12}(?:못\s*[잤자]|안\s*[잤자]|설쳤)|밤을\s*샜|한숨도\s*못\s*잤', 2, '수면 부족 표현'),),
    '복약': ((r'약[^.!?;]{0,14}(?:못\s*(?:먹|챙기)|안\s*(?:먹|챙기)|빼먹|빠뜨|깜빡)', 2, '복약 누락 표현'),),
    '기분': ((r'우울|외로|외롭|불안', 2, '기분 불편 표현'),),
}
CONTEXT_NEGATIVE = {
    '식사': r'못\s*먹|안\s*먹|거르|걸렀',
    '수면': r'못\s*[잤자]|안\s*[잤자]|설쳤',
    '복약': r'못\s*(?:먹|챙기)|안\s*(?:먹|챙기)|빼먹|빠뜨|깜빡',
}
POSITIVE = {
    '몸 상태': r'괜찮|좋[아습]|아픈\s*곳\s*없|안\s*아파|안\s*아프',
    '식사': r'먹었|먹고|챙겨\s*먹',
    '수면': r'잘\s*[잤자]|푹\s*[잤자]|편히\s*[잤자]',
    '복약': r'먹었|챙겨\s*먹|챙겼|먹는\s*약[은이을]?\s*없|약[은이을]?\s*안\s*먹어도\s*돼',
    '기분': r'괜찮|좋[아습]|편안|불편한\s*곳\s*없',
}
URGENT = r'숨(?:이|을|도)?\s*(?:잘\s*)?(?:안\s*쉬어|못\s*쉬|막혀)|숨\s*쉬기(?:가|도)?\s*(?:너무\s*)?힘들|(?:가슴|흉부)[^.!?;]{0,12}(?:너무|심하게|심한)[^.!?;]{0,6}(?:아[파프]|통증)|(?:죽고|자해하고)\s*싶|살기\s*싫|피가\s*(?:안\s*멈|멈추지\s*않)|119\s*(?:좀\s*)?(?:불러|불러줘)'
CLAUSES = r'[.!?;,\n]|(?:는데|지만|그러나|그런데)|(?<=먹고)|(?<=잤고)|(?<=했고)'
UNCERTAIN = r'모르|기억[^ ]*\s*(?:안|못)|글쎄|아마|것\s*같|거\s*같|같기도'
PAST = r'(?:예전|작년|지난달|옛날|과거)(?:에|엔|에는)?'
DENIAL = r'(?:[건게]|것은|것도|적은|적이|일은|일이)?\s*(?:아니|없(?:어|습|었|다))'
YES = r'(?:네|예|응|그럼|그래요)'
NO = r'(?:아니|아니요|아뇨)'
TOPIC_WORDS = {
    '식사': r'밥|식사|끼니|아침|점심|저녁',
    '수면': r'잠|수면',
    '복약': r'약|복약',
}
NO_NEED_MEDICINE = r'먹는\s*약[은이을]?\s*없|약[은이을]?\s*안\s*먹어도\s*돼'


def signal_match(pattern, clause, allow_prefix=False):
    for match in re.finditer(pattern, clause):
        before = clause[:match.start()].rstrip()
        after = clause[match.end():]
        if re.match(r'[^\s]{0,8}\s*' + DENIAL, after) or re.match(r'지\s*(?:않|는\s*않)', after):
            continue
        if not allow_prefix and re.search(r'(?:안|못)\s*$', before):
            continue
        return True
    return False


def is_about_topic(topic, clause):
    return topic not in TOPIC_WORDS or re.search(TOPIC_WORDS[topic], clause) or not any(
        re.search(pattern, clause) for category, pattern in TOPIC_WORDS.items() if category != topic
    )


def judge_answer(topic, answer):
    signals = {}
    urgent = False
    uncertain = bool(re.search(UNCERTAIN, answer))
    for part in re.split(CLAUSES, answer):
        clause = part.strip()
        if not clause:
            continue
        historical = bool(re.search(PAST, clause))
        if signal_match(URGENT, clause):
            if historical or re.search(UNCERTAIN, clause):
                signals['몸 상태'] = (max(2, signals.get('몸 상태', (0, ''))[0]), '위험 표현의 시점 또는 의미 확인 필요')
            else:
                urgent = True
        for category, patterns in RULES.items():
            if category == '복약' and re.search(NO_NEED_MEDICINE, clause):
                continue
            matches = [
                (min(level, 2) if historical else level, '과거 언급 · ' + reason if historical else reason)
                for pattern, level, reason in patterns if signal_match(pattern, clause)
            ]
            if category == topic and category in CONTEXT_NEGATIVE and not matches:
                if is_about_topic(topic, clause) and signal_match(CONTEXT_NEGATIVE[category], clause):
                    matches.append((2, patterns[0][2]))
            if matches:
                strongest = max(matches, key=lambda item: item[0])
                if strongest[0] > signals.get(category, (0, ''))[0]:
                    signals[category] = strongest
    short = answer.strip(' .!?;,')
    if re.fullmatch(NO, short):
        if topic in CONTEXT_NEGATIVE:
            signals[topic] = (2, '질문에 부정 응답')
        else:
            uncertain = True
    positive = any(
        signal_match(POSITIVE[topic], clause, allow_prefix=topic in ('몸 상태', '기분'))
        and is_about_topic(topic, clause) and not re.search(PAST, clause)
        for clause in re.split(CLAUSES, answer)
    )
    positive |= topic in CONTEXT_NEGATIVE and bool(re.fullmatch(YES, short))
    needs_review = topic not in signals and (uncertain or not positive) and not urgent
    if needs_review:
        signals[topic] = (1, '질문에 대한 답변 확인 필요')
    level = '즉시 확인' if urgent else '이상 신호' if any(
        reason != '질문에 대한 답변 확인 필요' for _, reason in signals.values()
    ) else '답변 확인 필요' if needs_review else '특이 표현 없음'
    return {'topic': topic, 'answer': answer, 'result': level, 'urgent': urgent, 'signals': [
        {'topic': key, 'severity': severity, 'reason': reason, 'points': WEIGHTS[key] * severity}
        for key, (severity, reason) in signals.items()
    ]}


def assess(answers, rejected):
    judgments = [judge_answer(topic, answer) for topic, answer in zip(TOPICS, answers)]
    problems = {}
    for judgment in judgments:
        for signal in judgment['signals']:
            topic = signal['topic']
            if signal['points'] > problems.get(topic, {}).get('points', 0):
                problems[topic] = signal
    urgent = any(item['urgent'] for item in judgments)
    call_points = 20 if not answers else 10 if len(answers) < len(TOPICS) else 0
    score = 100 if urgent else min(99, sum(signal['points'] for signal in problems.values()) + call_points)
    grade = '즉시 확인' if urgent else '우선 확인' if score >= 20 else '추가 확인' if score else '특이 표현 없음'
    return {
        'score': score,
        'grade': grade,
        'urgent': urgent,
        'judgments': judgments,
        'problems': sorted(problems.values(), key=lambda signal: -signal['points']),
        'call_points': call_points,
        'call_reason': '수신 거절' if rejected else '답변 없음' if not answers else '통화 중단' if call_points else '',
    }
