"""Versioned demonstration review rules, never a clinical risk score."""
import re
from conversation import QUESTIONS,LABELS
VERSION='review-v2'
REASONS={'stt_error':'음성 인식 실패','interpretation':'답변 해석 불가','self_unknown':'본인 응답에 따른 미확인','degree':'정도 미확인','unanswered':'미응답 또는 질문 미진행'}
GUIDANCE='긴급한 상황이면 지금 직접 119에 연락하거나 가까운 분에게 도움을 요청해 주세요. 안심온은 실제 신고를 하지 않습니다.'
def degree(text):
 t=re.sub(r'\s+','',text)
 if re.search(r'혼자.{0,5}(?:못|어려)|생활.{0,5}(?:못|지장|어려)|움직.{0,3}못|도움.{0,4}필요|도와주세요',t):return 3
 if re.search(r'\d+일|이틀|사흘|며칠|계속|반복|매일|자주|일주일|여러날|지속',t):return 2
 if re.search(r'일시|가벼|잠깐|가끔|조금|살짝|가볍|오늘만|한번|하루만',t):return 1
 return None

def build(state):
 items=[]
 for topic,_ in QUESTIONS:
  item=state.get('review_items',{}).get(topic,{'score':None,'reason':'unanswered','evidence':'','classification':'unknown'})
  items.append({'topic':topic,'label':LABELS[topic],'version':VERSION,**item})
 count=sum(i['score'] is not None for i in items);total=sum(i['score'] for i in items if i['score'] is not None)
 missing=[i for i in items if i['score'] is None]
 negative_unknown=any(i.get('classification')=='negative' and i['score'] is None for i in items)
 grade='우선 확인' if total>=3 else '추가 확인' if total else '정보 부족' if not count or negative_unknown else '특이 표현 없음' if count==5 else '확인된 범위에서 특이 표현 없음'
 risk=state.get('emergency_state','none')
 if risk!='none':grade='긴급 표현 감지' if risk=='confirmed' else '긴급 가능성 · 의도 미확인'
 reason=REASONS[missing[0]['reason']] if len(missing)==1 else f'미확인 {len(missing)}개' if missing else ''
 return {'version':VERSION,'max_score':15,'score':total if count else None,'grade':grade,'confirmed_count':count,'items':items,'emergency_state':risk,'urgent':risk!='none','safety_guidance_provided':state.get('safety_guidance_provided',False),'secondary':f'{reason+" · " if reason else ""}{count}/5개 항목 확인','degree_missing':negative_unknown,'call_points':0,'problems':[]}
