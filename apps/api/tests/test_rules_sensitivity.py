"""가중치 민감도: 점수 하나씩 ±5 로 바꿔도 상위 3명이 크게 흔들리지 않는지 (판정규칙.md §7).

결과는 ROOT/docs/평가/<날짜>_rules_sensitivity.md·.json 에 남긴다.
※ 가상 시드 데이터 · 설계 검증용 · 일반화 불가.
"""
import json
from pathlib import Path

from app import calls, db
from app.domain import scoring

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / 'docs' / '평가'
GRADE_ORDER = {'urgent': 0, 'today': 1, 'watch': 2, 'ok': 3}
WEIGHTS = [
    ('item_points', 'caution', 'A 주의'), ('item_points', 'risk', 'A 위험'),
    ('trend', 'two_days', 'B 2일 연속'), ('trend', 'three_plus_days', 'B 3일 이상'),
    ('contact', 'missed_once', 'C 미응답 1회'), ('contact', 'missed_consecutive', 'C 연속 미응답'),
    ('contact', 'interrupted', 'C 통화 중단'), ('contact', 'declined', 'C 수신 거절'),
]
NOTE = '가상 시드 데이터 · 설계 검증용 · 일반화 불가'


def _population(conn):
    """(날짜, 어르신) 마다 그날 마지막으로 끝난 통화."""
    rows = conn.execute(f"SELECT c.*, r.name AS resident_name FROM calls c JOIN residents r ON r.id = c.resident_id "
                        f"WHERE c.status IN {calls.FINISHED} ORDER BY c.created_at, c.id").fetchall()
    last = {}
    for r in rows:
        last[(r['kst_date'], r['resident_id'])] = r
    return last


def _rank(conn, pop, rule_set):
    scored = {}
    for key, call in pop.items():
        a = calls.compute_assessment(conn, call, call['status'], rule_set)
        scored[key] = (GRADE_ORDER[a['grade']], -a['score'], call['resident_id'])
    by_day = {}
    for (day, rid), k in scored.items():
        by_day.setdefault(day, []).append((k, rid))
    days = {d: [rid for _k, rid in sorted(v)][:3] for d, v in by_day.items()}
    pooled = [key for key, _k in sorted(scored.items(), key=lambda kv: kv[1])][:3]
    return days, pooled


def test_rules_sensitivity(template_db):
    conn = db.connect(str(template_db))
    pop = _population(conn)
    base_rules = scoring.rules()
    base_days, base_pooled = _rank(conn, pop, base_rules)
    results = []
    for group, key, label in WEIGHTS:
        for delta in (-5, 5):
            r = scoring.rules()
            value = r[group][key] + delta
            if value < 0:
                continue
            r[group][key] = value
            days, pooled = _rank(conn, pop, r)
            overlaps = [len(set(days[d]) & set(base_days[d])) / max(1, len(base_days[d])) for d in base_days]
            same_set = sum(1 for d in base_days if set(days[d]) == set(base_days[d]))
            same_order = sum(1 for d in base_days if days[d] == base_days[d])
            results.append({
                'weight': f'{group}.{key}', 'label': label, 'base': base_rules[group][key], 'value': value,
                'days': len(base_days), 'top3_same_set_days': same_set, 'top3_same_order_days': same_order,
                'mean_top3_overlap': round(sum(overlaps) / len(overlaps), 3),
                'pooled_top3_same': set(pooled) == set(base_pooled),
            })
    conn.close()

    today = db.kst_today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {'note': NOTE, 'date': today, 'rule_version': base_rules['version'],
               'population': {'resident_days': len(pop), 'days': len(base_days)}, 'results': results}
    (OUT_DIR / f'{today}_rules_sensitivity.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                                            encoding='utf-8')
    lines = [
        f'# 판정 규칙 민감도 ({today}, 규칙 {base_rules["version"]})', '',
        f'> **{NOTE}.** 시드 어르신 6명 × 7일(끝난 통화 {len(pop)}건)만으로 본 결과다. 실제 현장 데이터가 아니므로 '
        '가중치가 맞다는 근거가 아니라, "값 하나를 조금 바꿨을 때 순위가 뒤집히는 구조인가"만 확인한다.', '',
        '방법: 가중치 하나를 ±5 바꾸고 나머지는 그대로 둔 채, 날마다 (단계 → 점수) 순 상위 3명을 기준값과 비교. '
        '`pooled`는 7일 전체 (어르신·날짜) 중 상위 3건이 같은지.', '',
        '| 가중치 | 기준 → 바꾼 값 | 상위 3명 같은 날 | 순서까지 같은 날 | 평균 겹침 | pooled 상위 3 |',
        '|---|---|---:|---:|---:|---|',
    ]
    for x in results:
        lines.append(f"| {x['label']} (`{x['weight']}`) | {x['base']} → {x['value']} | {x['top3_same_set_days']}/{x['days']} "
                     f"| {x['top3_same_order_days']}/{x['days']} | {x['mean_top3_overlap']:.2f} "
                     f"| {'같음' if x['pooled_top3_same'] else '바뀜'} |")
    worst = min(results, key=lambda x: x['mean_top3_overlap'])
    lines += ['', f"가장 크게 흔들린 경우: {worst['label']} {worst['base']}→{worst['value']} "
                  f"(평균 겹침 {worst['mean_top3_overlap']:.2f}).",
              '', '한계: 하루에 끝난 통화가 4~6건이라 상위 3명은 원래 바뀌기 어렵다. 어르신 수가 늘면 다시 돌려야 한다.', '']
    (OUT_DIR / f'{today}_rules_sensitivity.md').write_text('\n'.join(lines), encoding='utf-8')

    assert len(results) >= 15
    # 설계 목표: 어떤 가중치를 ±5 바꿔도 날마다 상위 3명 중 평균 2명 이상은 그대로
    assert all(x['mean_top3_overlap'] >= 2 / 3 for x in results), results
