"""확인 점수·단계·이유 계산 (판정규칙.md §4~§6). 나이·성별은 입력에 없다.

assess() 입력은 전부 이미 읽어 온 값이다 — DB를 보지 않는다.
- items: {topic: {status, quote, origin}}  (이 통화)
- safety: [{category, quote}]               (이 통화)
- history: 어제부터 거슬러 6일, 각 날의 {topic: status} 또는 None(답을 들은 통화가 없던 날)
- call_status: 이 통화의 끝 상태 (completed | interrupted | missed | declined)
- prior_calls: 이 통화 앞의 끝난 통화들, 최근 것부터 [{status, days_ago}] (7일 안)
- needs: 이 통화에서 찾은 어려움 유형 [{type, label, quote, origin}] — 점수에 넣지 않고 그대로 싣는다
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import yaml

from .questions import STATUS_LABELS, TOPIC_LABELS, TOPICS

RULES_PATH = Path(__file__).with_name('rules.yaml')
PROBLEM = ('caution', 'risk')


@lru_cache(maxsize=1)
def _load_rules() -> dict:
    with open(RULES_PATH, encoding='utf-8') as f:
        return yaml.safe_load(f)


def rules() -> dict:
    return deepcopy(_load_rules())


def _reason(kind, chip, points, quote=None):
    return {'kind': kind, 'chip': chip, 'points': points, 'quote': quote}


def _cap(reasons: list[dict], cap: int) -> list[dict]:
    """합계가 상한을 넘으면 넘는 만큼 뒤쪽 이유에서 깎는다 → 이유 점수의 합 = 실제 점수."""
    out, left = [], cap
    for r in reasons:
        pts = min(r['points'], left)
        if pts <= 0:
            continue
        out.append({**r, 'points': pts})
        left -= pts
    return out


def trend_streak(today_status: str, past: list) -> int:
    """오늘부터 거슬러 '주의 이상'이 이어진 날 수. 답을 못 들은 날(None·unknown)은 건너뛰고, 양호가 나오면 끊는다."""
    n = 0
    for st in [today_status] + list(past):
        if st is None or st == 'unknown':
            continue
        if st in PROBLEM:
            n += 1
        else:
            break
    return n


def contact_reasons(call_status: str, prior_calls: list[dict], r: dict) -> list[dict]:
    c = r['contact']
    out = []
    lead = 0
    for pc in prior_calls:
        if pc['status'] != 'missed':
            break
        lead += 1
    if call_status == 'missed':
        run = 1 + lead
        if run >= 2:
            out.append(_reason('contact', f'연속 미응답 {run}회', c['missed_consecutive']))
        else:
            out.append(_reason('contact', '오늘 미응답', c['missed_once']))
    elif lead and prior_calls[0]['days_ago'] <= 1:
        if lead >= 2:
            out.append(_reason('contact', f'최근 연속 미응답 {lead}회', c['missed_consecutive']))
        else:
            when = '오늘' if prior_calls[0]['days_ago'] == 0 else '어제'
            out.append(_reason('contact', f'{when} 미응답', c['missed_once']))
    if call_status == 'interrupted':
        out.append(_reason('contact', '통화 중단', c['interrupted']))
    if call_status == 'declined':
        out.append(_reason('contact', '수신 거절', c['declined']))
    return _cap(out, c['cap'])


def assess(items: dict, safety: list[dict], history: list, call_status: str, prior_calls: list[dict],
           rule_set: dict | None = None, needs: list[dict] | None = None) -> dict:
    r = rule_set or _load_rules()
    reasons = [_reason('safety', f"안전 신호 · {s['category']}", 0, s['quote']) for s in safety]

    item_reasons = []
    for t in TOPICS:
        st = items[t]['status']
        if st in PROBLEM:
            item_reasons.append(_reason('item', f'{TOPIC_LABELS[t]} {STATUS_LABELS[st]}', r['item_points'][st],
                                        items[t]['quote']))

    trend = []
    tr = r['trend']
    for t in TOPICS:
        past = [(h or {}).get(t) if h else None for h in history[:tr['window_days'] - 1]]
        n = trend_streak(items[t]['status'], past)
        if n >= 3:
            trend.append(_reason('trend', f'{TOPIC_LABELS[t]} {n}일 연속', tr['three_plus_days']))
        elif n == 2:
            trend.append(_reason('trend', f'{TOPIC_LABELS[t]} 2일 연속', tr['two_days']))
    trend = _cap(trend, tr['cap'])

    contact = contact_reasons(call_status, prior_calls, r)
    reasons += item_reasons + trend + contact
    score = min(100, sum(x['points'] for x in reasons))

    unknown = [t for t in TOPICS if items[t]['status'] == 'unknown']
    risk_count = sum(1 for t in TOPICS if items[t]['status'] == 'risk')
    g = r['grades']
    if len(unknown) >= g['watch']['min_unknown_items']:
        reasons.append(_reason('item', f"미확인 {len(unknown)}개 ({'·'.join(TOPIC_LABELS[t] for t in unknown)})", 0))

    if safety:
        grade = 'urgent'
    elif score >= g['today']['min_score'] or risk_count >= g['today']['min_risk_items']:
        grade = 'today'
    elif score >= g['watch']['min_score'] or len(unknown) >= g['watch']['min_unknown_items']:
        grade = 'watch'
    else:
        grade = 'ok'

    return {
        'score': score,
        'grade': grade,
        'grade_label': r['grade_labels'][grade],
        'reasons': reasons,
        'items': {t: dict(items[t]) for t in TOPICS},
        'safety': [dict(s) for s in safety],
        'needs_check': unknown,
        'needs': [dict(n) for n in needs or []],
        'rule_version': r['version'],
    }


def grade_label(grade: str) -> str:
    return _load_rules()['grade_labels'][grade]


def empty_items() -> dict:
    return {t: {'status': 'unknown', 'quote': None, 'origin': 'none'} for t in TOPICS}


SEVERITY = {'unknown': -1, 'good': 0, 'caution': 1, 'risk': 2}


def merge_items(rows: list[dict]) -> dict:
    """한 통화(또는 하루)에 나온 항목 기록 → 주제마다 가장 나쁜 상태 하나. 아무 기록이 없으면 미확인."""
    out = empty_items()
    for row in rows:
        t = row['topic']
        if SEVERITY[row['status']] > SEVERITY[out[t]['status']]:   # 미확인 기록은 여기 들어오지 않는다
            out[t] = {'status': row['status'], 'quote': row.get('quote'), 'origin': row.get('origin') or 'rule'}
    return out


def rule_summary(items: dict, safety: list[dict], call_status: str) -> str:
    """AI 요약이 실패하거나 꺼졌을 때 쓰는 요약. 확정된 항목만 쓴다."""
    if call_status == 'missed':
        return '전화를 받지 않음(미응답).'
    if call_status == 'declined':
        return '전화를 거절함.'
    parts = []
    if call_status == 'interrupted':
        parts.append('통화가 중간에 끊김.')
    for s in safety:
        parts.append(f"안전 신호({s['category']}) — \"{s['quote']}\".")
    probs = []
    for t in TOPICS:
        it = items[t]
        if it['status'] in PROBLEM:
            q = f" \"{it['quote']}\"" if it['quote'] else ''
            probs.append(f"{TOPIC_LABELS[t]} {STATUS_LABELS[it['status']]}{q}")
    if probs:
        parts.append(', '.join(probs) + '.')
    good = [TOPIC_LABELS[t] for t in TOPICS if items[t]['status'] == 'good']
    unknown = [TOPIC_LABELS[t] for t in TOPICS if items[t]['status'] == 'unknown']
    if good:
        parts.append('·'.join(good) + ' 양호.')
    if unknown:
        parts.append('·'.join(unknown) + ' 확인 못 함.')
    return ' '.join(parts) or '확인된 내용 없음.'
