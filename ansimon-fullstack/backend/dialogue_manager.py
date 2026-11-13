"""Pure transition interface: replace analyze/respond adapters for a future local model."""
import os
import copy
from conversation import QUESTIONS
from scenarios import CLARIFY, YES, NO, binary_question
from normalizer import normalize
from entity_extractor import extract
from intent_classifier import classify
from risk_detector import detect
from response_generator import generate
from review import degree, GUIDANCE

def daily_limit():
    try:return max(0,min(20,int(os.getenv('ANSIMON_DAILY_LIMIT','2'))))
    except ValueError:return 2

def transition(previous, answer, source='text'):
    s=copy.deepcopy(previous); index=s.get('index',0);topic=QUESTIONS[index][0]
    previous_question=s.get('question',QUESTIONS[index][1])
    short=normalize(answer).strip('.!?。')
    facts,uncertain=extract(answer,topic,allow_confirmation=binary_question(previous_question,topic));risk=detect(answer)
    if s.get('question')=='그 이야기를 조금 더 들려주시겠어요?' and short in YES|NO:
        facts={}
    intents=classify(answer,facts,uncertain,risk,source)
    s.setdefault('facts',{});s.setdefault('checks',0);s.setdefault('daily_count',0)
    s.setdefault('completed',[]);s.setdefault('unconfirmed',[])
    if source in ('stt_error','silence'):facts={}
    if risk['historical'] or risk['negated']:
        # Do not store quoted/negated emergency words as current health facts.
        if risk['evidence']: facts={}
    if s.get('risk_pending') and short in YES:
        risk['urgent']=True; facts={}
    elif s.get('risk_pending') and (short in NO or '지금은 괜찮' in answer):
        facts={};s['risk_pending']=False
    v2=s.get('review_version')=='review-v2'
    severity_prompt=False
    if v2:
        items={k:dict(v) for k,v in s.get('review_items',{}).items()}
        s['review_items']=items
        awaiting=s.get('degree_topic')==topic
        if awaiting and degree(answer) is not None:
            old=items.get(topic,{})
            facts[topic]={'classification':'negative','evidence':old.get('evidence','')+' / '+answer}
        for k,f in list(facts.items()):
            old=items.get(k)
            conflict=old and old.get('classification') in ('positive','negative') and old['classification']!=f['classification'] and not awaiting and not any(w in answer for w in ('아니,','아니 ','정정','지금은','이제는'))
            score=degree(f['evidence']) if f['classification']=='negative' else None if f.get('quality')=='unconfirmed' else 0
            items[k]={**f,'score':None if conflict else score,'reason':'interpretation' if conflict else 'degree' if score is None else None}
            if conflict:
                items[k].update(classification='unknown',evidence=old.get('evidence','')+' / '+answer)
                facts.pop(k,None);s['facts'].pop(k,None)
        item=items.get(topic)
        if not facts.get(topic) and not awaiting:
            reason='stt_error' if source=='stt_error' else 'unanswered' if source=='silence' else 'self_unknown' if any(w in short for w in ('모르','기억안')) else 'interpretation'
            items[topic]={'score':None,'reason':reason,'classification':'unknown','evidence':answer}
        if item and item.get('classification')=='negative' and item.get('score') is None and item.get('reason')=='degree':
            severity_prompt=True;s['degree_topic']=topic
            s['checks']+=1
        else:s.pop('degree_topic',None)
        if risk['urgent']:s['emergency_state']='confirmed'
        elif risk.get('possible') and s.get('emergency_state')!='confirmed':s['emergency_state']='possible'
        if s.get('emergency_state') in ('confirmed','possible'):
            s['safety_paused']=True;s['safety_guidance_provided']=True
    action='clarify'
    if risk['urgent']: action='safety_pause';s['safety_paused']=True
    elif s.get('safety_paused'):action='safety_pause'
    elif risk['needs_confirmation'] or s.get('risk_pending'):action='risk_confirmation';s['risk_pending']=True
    elif v2 and severity_prompt:action='clarify' if s['checks']<=2 else 'skip'
    elif v2 and s.get('review_items',{}).get(topic,{}).get('reason')=='interpretation' and topic in facts:
        s['checks']+=1;action='clarify' if s['checks']<=2 else 'skip'
    elif topic in facts: action='advance'
    elif 'refusal' in intents:action='skip'
    elif ('daily_story' in intents or ('emotion' in intents and topic!='mood')) and s['daily_count']<daily_limit():
        action='daily_chat';s['daily_count']+=1
    elif source in ('stt_error','silence'):action='input_retry'
    else:
        s['checks']+=1
        if s['checks']>2:action='skip'
    if risk['urgent']:facts={}
    s['facts']={**s['facts'],**facts}
    reply=GUIDANCE if v2 and s.get('safety_paused') else generate(topic,action,intents,facts,s['checks'])
    category=facts.get(topic,{}).get('classification','unknown')
    if action in ('advance','skip'):
        s['completed'].append(topic)
        if action=='skip':s['unconfirmed'].append(topic)
        s['index']=index+1;s['checks']=0
    else:s['index']=index
    s['attempt']=s.get('attempt',0)+1 if s['index']==index else 0
    s['count']=s['index'];s['finished']=s['index']==5
    s['question']=None if s['finished'] else ('' if action=='safety_pause' else QUESTIONS[s['index']][1])
    if action=='clarify' or 'question_repeat' in intents:s['question']=CLARIFY[topic]
    if action=='daily_chat' and s['daily_count']<daily_limit():s['question']='그 이야기를 조금 더 들려주시겠어요?'
    if action=='risk_confirmation':s['question']='지금도 위험한 상황이신가요?'
    if v2 and severity_prompt and action=='clarify':s['question']='불편함이 어느 정도이고 얼마나 계속되었는지 말씀해 주세요. 일상생활에 지장이 있거나 도움이 필요하신지도 알려주세요.'
    s['retry_count']=s['checks']
    s.update(last_ai=s['question'] or reply,last_utterance=answer,risk=risk,intents=intents,help_requested='help_request' in intents,
             emotion_signals=s.get('emotion_signals',[])+([answer] if 'emotion' in intents else []),
             help_requests=s.get('help_requests',[])+([answer] if 'help_request' in intents else []),
             risk_signals=s.get('risk_signals',[])+([risk] if risk['evidence'] else []))
    return s,{'intents':intents,'facts':facts,'uncertain':uncertain,'risk':risk,'action':action,
              'classification':category,'reply':reply,'emergency':risk['urgent'],'source':source}
