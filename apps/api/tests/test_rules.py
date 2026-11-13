"""판정규칙.md 표의 줄마다 하나씩."""
import inspect

import pytest

from app.domain import keywords, safety, scoring
from app.domain.dialogue import State, decide
from app.domain.questions import TOPICS


def status_of(topic, text):
    r = keywords.extract(topic, text)
    return next((i['status'] for i in r.items if i['topic'] == topic), None)


# ---- §2 항목별 상태 ----
@pytest.mark.parametrize('topic,text,expected', [
    # 양호
    ('meal', '밥 잘 먹었어', 'good'),
    ('med', '약 없어', 'good'),               # 복약 대상 아님도 양호
    ('med', '먹는 약 없어요', 'good'),
    # 주의
    ('body', '좀 피곤해', 'caution'),
    ('meal', '입맛이 없어 아침 걸렀어', 'caution'),
    ('sleep', '잠을 설쳤어', 'caution'),
    # 위험
    ('meal', '이틀째 못 먹었어', 'risk'),
    ('med', '약을 며칠 안 먹었어', 'risk'),
    ('body', '어지러워', 'risk'),
    ('mood', '아무도 안 와서 외로워', 'risk'),
])
def test_item_status_table(topic, text, expected):
    assert status_of(topic, text) == expected


@pytest.mark.parametrize('topic,text,expected', [
    ('body', '안 아파', 'good'), ('body', '아파', 'caution'), ('body', '아프지 않아', 'good'),
    ('meal', '못 먹었어', 'caution'), ('meal', '걸렀어', 'caution'), ('meal', '밥 먹었어', 'good'),
    ('mood', '안 외로워', 'good'), ('mood', '외로워', 'caution'), ('mood', '기분 안 좋아', 'caution'),
])
def test_negation(topic, text, expected):
    assert status_of(topic, text) == expected


@pytest.mark.parametrize('topic,text,expected', [
    ('meal', '어', 'good'), ('meal', '응', 'good'), ('meal', '네', 'good'), ('meal', '아니', 'caution'),
    ('med', '아니', 'caution'), ('sleep', '응', 'good'), ('body', '어', 'good'),
])
def test_short_answers_follow_current_question(topic, text, expected):
    assert status_of(topic, text) == expected


def test_short_answer_is_not_applied_to_other_topics():
    r = keywords.extract('meal', '응')
    assert [i['topic'] for i in r.items] == ['meal']


def test_unknown_when_no_answer_after_two_reasks():
    s = State(index=1)
    for _ in range(2):
        d = decide(s, intent='unclear', judged_topics=set(), safety_hit=False, silence=True)
        assert d.action == 'reask'
        s = d.state
    d = decide(s, intent='unclear', judged_topics=set(), safety_hit=False, silence=True)
    assert d.mark_unknown and d.asked_topic == 'meal' and d.state.index == 2


# ---- §3 안전 신호 ----
@pytest.mark.parametrize('category,text', [
    ('낙상', '넘어졌어'), ('낙상', '쓰러졌어'), ('낙상', '못 일어나'),
    ('호흡·가슴', '숨이 차'), ('호흡·가슴', '숨차'), ('호흡·가슴', '숨을 못 쉬겠어'),
    ('호흡·가슴', '가슴이 아파'), ('호흡·가슴', '가슴이 답답해'),
    ('의식·마비', '정신이 없어'), ('의식·마비', '말이 안 나와'), ('의식·마비', '한쪽이 마비된 것 같아'),
    ('자해·삶의 의지', '죽고 싶어'), ('자해·삶의 의지', '살기 싫어'),
    ('도움 요청', '119 불러줘'), ('도움 요청', '살려줘'), ('도움 요청', '도와줘'),
])
def test_safety_categories(category, text):
    assert category in [h['category'] for h in safety.detect(text)]


def test_safety_keeps_negated_or_past_expressions():
    hits = safety.detect('어제 넘어질 뻔했는데 괜찮아')
    assert hits and hits[0]['category'] == '낙상'
    assert hits[0]['quote'] in '어제 넘어질 뻔했는데 괜찮아'


def test_safety_no_false_hit_on_plain_answers():
    for t in ['괜찮아요', '밥 먹었어', '도와줘서 고마워', '잘 잤어']:
        assert safety.detect(t) == []


# ---- §4 점수 ----
def items(**st):
    out = scoring.empty_items()
    for t in TOPICS:
        out[t] = {'status': st.get(t, 'good'), 'quote': f'{t} 인용' if st.get(t, 'good') != 'unknown' else None,
                  'origin': 'rule'}
    return out


def A(**st):
    return scoring.assess(items(**st), [], [None] * 6, 'completed', [])


def test_score_a_caution_5():
    a = A(meal='caution')
    assert a['score'] == 5 and a['reasons'][0] == {'kind': 'item', 'chip': '식사 주의', 'points': 5, 'quote': 'meal 인용'}


def test_score_a_risk_10():
    assert A(meal='risk')['score'] == 10


def test_score_a_max_50():
    assert A(**{t: 'risk' for t in TOPICS})['score'] == 50


def hist(days, **st):
    return [{t: st.get(t, 'good') for t in TOPICS} for _ in range(days)] + [None] * (6 - days)


def test_score_b_two_days_plus_5():
    a = scoring.assess(items(sleep='caution'), [], hist(1, sleep='caution'), 'completed', [])
    assert a['score'] == 10 and {'kind': 'trend', 'chip': '수면 2일 연속', 'points': 5, 'quote': None} in a['reasons']


def test_score_b_three_days_plus_10():
    a = scoring.assess(items(meal='risk'), [], hist(2, meal='caution'), 'completed', [])
    assert a['score'] == 20 and any(r['chip'] == '식사 3일 연속' and r['points'] == 10 for r in a['reasons'])


def test_score_b_is_per_item_and_capped_at_30():
    st = {t: 'caution' for t in TOPICS}
    a = scoring.assess(items(**st), [], hist(3, **st), 'completed', [])
    trend = sum(r['points'] for r in a['reasons'] if r['kind'] == 'trend')
    assert trend == 30 and a['score'] == 25 + 30


def test_score_b_good_day_breaks_streak_missing_day_skipped():
    history = [None, {t: 'caution' for t in TOPICS}, {t: 'good' for t in TOPICS}, None, None, None]
    a = scoring.assess(items(meal='caution'), [], history, 'completed', [])
    assert any(r['chip'] == '식사 2일 연속' for r in a['reasons'])
    history = [{t: 'good' for t in TOPICS}, {t: 'caution' for t in TOPICS}, None, None, None, None]
    assert not any(r['kind'] == 'trend' for r in scoring.assess(items(meal='caution'), [], history, 'completed', [])['reasons'])


def unknown_items():
    return scoring.empty_items()


def test_score_c_missed_once_plus_10():
    a = scoring.assess(unknown_items(), [], [None] * 6, 'missed', [])
    assert {'kind': 'contact', 'chip': '오늘 미응답', 'points': 10, 'quote': None} in a['reasons'] and a['score'] == 10


def test_score_c_missed_consecutive_plus_20():
    a = scoring.assess(unknown_items(), [], [None] * 6, 'missed', [{'status': 'missed', 'days_ago': 1}])
    assert a['score'] == 20 and a['reasons'][0]['chip'] == '연속 미응답 2회'


def test_score_c_yesterday_missed_counts_on_todays_call():
    a = scoring.assess(items(), [], [None] * 6, 'completed', [{'status': 'missed', 'days_ago': 1}])
    assert a['score'] == 10 and a['reasons'][0]['chip'] == '어제 미응답'


def test_score_c_interrupted_plus_5():
    a = scoring.assess(items(), [], [None] * 6, 'interrupted', [])
    assert a['score'] == 5 and a['reasons'][0]['chip'] == '통화 중단'


def test_score_c_declined_plus_5():
    a = scoring.assess(unknown_items(), [], [None] * 6, 'declined', [])
    assert any(r['chip'] == '수신 거절' and r['points'] == 5 for r in a['reasons'])


def test_score_c_capped_at_20():
    prior = [{'status': 'missed', 'days_ago': 0}, {'status': 'missed', 'days_ago': 1}]
    a = scoring.assess(items(), [], [None] * 6, 'interrupted', prior)
    assert sum(r['points'] for r in a['reasons'] if r['kind'] == 'contact') == 20


def test_every_point_has_a_reason():
    a = scoring.assess(items(meal='risk', sleep='caution'), [], hist(2, meal='caution'), 'completed',
                       [{'status': 'missed', 'days_ago': 1}])
    assert sum(r['points'] for r in a['reasons']) == a['score']
    assert all(r['quote'] for r in a['reasons'] if r['kind'] == 'item' and r['points'])


def test_age_and_gender_are_not_inputs():
    params = set(inspect.signature(scoring.assess).parameters)
    assert not params & {'age', 'gender', 'resident'}


# ---- §5 단계 ----
def test_grade_urgent_on_any_safety_signal_regardless_of_score():
    a = scoring.assess(items(), [{'category': '낙상', 'quote': '넘어졌어'}], [None] * 6, 'completed', [])
    assert a['grade'] == 'urgent' and a['grade_label'] == '즉시 확인' and a['score'] == 0


def test_grade_today_at_40():
    st = {'body': 'risk', 'meal': 'risk', 'sleep': 'risk', 'med': 'risk'}
    a = A(**st)
    assert a['score'] == 40 and a['grade'] == 'today'


def test_grade_today_on_two_risk_items():
    a = A(meal='risk', med='risk')
    assert a['score'] == 20 and a['grade'] == 'today'


@pytest.mark.parametrize('st,expected', [
    ({'meal': 'risk', 'sleep': 'caution'}, 'watch'),                                       # 15
    ({'body': 'risk', 'meal': 'risk', 'sleep': 'risk'}, 'today'),                          # 30 이지만 위험 3개
    ({'meal': 'caution', 'sleep': 'caution'}, 'ok'),                                       # 10
    ({'meal': 'unknown', 'sleep': 'unknown'}, 'watch'),                                    # 미확인 2개
    ({'meal': 'unknown'}, 'ok'),                                                           # 미확인 1개
])
def test_grade_watch_and_ok(st, expected):
    a = A(**st)
    assert a['grade'] == expected


def test_grade_with_trend_and_contact_mixed():
    history = hist(2, body='caution', meal='caution', sleep='caution')
    a = scoring.assess(items(body='caution', meal='caution', sleep='risk'), [], history, 'completed', [])
    assert a['score'] == 50 and a['grade'] == 'today'
    a = scoring.assess(items(body='caution', meal='caution', sleep='caution'), [], hist(1, body='caution', meal='caution'),
                       'completed', [{'status': 'missed', 'days_ago': 1}])
    assert a['score'] == 15 + 10 + 10 and a['grade'] == 'watch'


def test_needs_check_lists_unknown_and_rule_version():
    a = A(meal='unknown', mood='unknown')
    assert a['needs_check'] == ['meal', 'mood'] and a['rule_version'] == 'r2.1'


def test_rules_yaml_matches_document_values():
    r = scoring.rules()
    assert r['item_points'] == {'caution': 5, 'risk': 10}
    assert (r['trend']['two_days'], r['trend']['three_plus_days'], r['trend']['cap']) == (5, 10, 30)
    c = r['contact']
    assert (c['missed_once'], c['missed_consecutive'], c['interrupted'], c['declined'], c['cap']) == (10, 20, 5, 5, 20)
    assert r['grades']['today'] == {'min_score': 40, 'min_risk_items': 2}
    assert r['grades']['watch'] == {'min_score': 15, 'min_unknown_items': 2}
    assert r['grade_labels'] == {'urgent': '즉시 확인', 'today': '우선 확인', 'watch': '추가 확인', 'ok': '특이 표현 없음'}
