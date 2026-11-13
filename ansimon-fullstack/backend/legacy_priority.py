"""Taewon display weights, gated by the persisted conversation evidence.
These are demonstration review priorities, not medical risk scores.
"""
import json
from conversation import QUESTIONS, LABELS
from taewon_rules import judge_answer, TOPICS, WEIGHTS


def assessment_for(c, call):
    if call['status']=='in_progress':
        return {'score':None,'grade':'통화 중','urgent':False,'problems':[], 'call_points':0,'call_reason':''}
    state_row=c.execute('SELECT state_json FROM hybrid_state WHERE call_id=?',(call['id'],)).fetchone()
    state=json.loads(state_row[0]) if state_row else {}
    turns=[dict(r) for r in c.execute('SELECT * FROM turns WHERE call_id=? ORDER BY id',(call['id'],))]
    facts=state.get('facts')
    if facts is None:
        facts={t['topic']:{'classification':t['classification'],'evidence':t['answer']} for t in turns}
    urgent=bool(state.get('safety_paused')) if state_row else any(t['emergency'] for t in turns)
    problems=[]
    for index,(topic,_) in enumerate(QUESTIONS):
        fact=facts.get(topic);category=(fact or {}).get('classification','unknown')
        evidence=(fact or {}).get('evidence','')
        level=0;reason=''
        if category=='negative':
            signal=judge_answer(TOPICS[index],evidence)
            levels=[s['severity'] for s in signal['signals'] if s['topic']==TOPICS[index]]
            level=max(levels or [2]);reason='확인된 부정 답변'
        elif category not in ('positive','neutral') and topic in state.get('completed',[t['topic'] for t in turns]):
            level=1;reason='답변 확인 필요'
        if level:
            problems.append({'topic':LABELS[topic],'severity':level,'points':WEIGHTS[TOPICS[index]]*level,'reason':reason,'evidence':evidence})
    points=20 if not turns else 10 if call['status']=='interrupted' else 0
    score=100 if urgent else min(99,sum(p['points'] for p in problems)+points)
    return {'score':score,'grade':'즉시 확인' if urgent else '우선 확인' if score>=20 else '추가 확인' if score else '특이 표현 없음',
            'urgent':urgent,'problems':sorted(problems,key=lambda p:-p['points']), 'call_points':points,
            'call_reason':'수신 거절' if call['status']=='declined' else '답변 없음' if not turns else '통화 중단' if points else '',
            'notice':'시연용 확인 순서 지표입니다. 의료적 판단이나 실제 신고 결과가 아닙니다.'}
