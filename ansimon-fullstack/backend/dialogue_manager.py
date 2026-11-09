"""Pure transition interface: replace analyze/respond adapters for a future local model."""
import os
from conversation import QUESTIONS
from scenarios import CLARIFY
from entity_extractor import extract
from intent_classifier import classify
from risk_detector import detect
from response_generator import generate

def daily_limit():
    try:return max(0,min(20,int(os.getenv('ANSIMON_DAILY_LIMIT','2'))))
    except ValueError:return 2

def transition(previous, answer, source='text'):
    s={**previous}; index=s.get('index',0);topic=QUESTIONS[index][0]
    facts,uncertain=extract(answer,topic);risk=detect(answer)
    if s.get('question')=='그 이야기를 조금 더 들려주시겠어요?' and answer.strip() in ('응','네','예','아니','아니요'):
        facts={}
    intents=classify(answer,facts,uncertain,risk,source)
    s.setdefault('facts',{});s.setdefault('checks',0);s.setdefault('daily_count',0)
    s.setdefault('completed',[]);s.setdefault('unconfirmed',[])
    if source in ('stt_error','silence'):facts={}
    if risk['historical'] or risk['negated']:
        # Do not store quoted/negated emergency words as current health facts.
        if risk['evidence']: facts={}
    if s.get('risk_pending') and answer.strip() in ('응','네','예','맞아'):
        risk['urgent']=True; facts={}
    elif s.get('risk_pending') and (answer.strip() in ('아니','아니요','아뇨') or '지금은 괜찮' in answer):
        facts={};s['risk_pending']=False
    action='clarify'
    if risk['urgent']: action='safety_pause';s['safety_paused']=True
    elif s.get('safety_paused'):action='safety_pause'
    elif risk['needs_confirmation'] or s.get('risk_pending'):action='risk_confirmation';s['risk_pending']=True
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
    reply=generate(topic,action,intents,facts,s['checks'])
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
    s['retry_count']=s['checks']
    s.update(last_ai=s['question'] or reply,last_utterance=answer,risk=risk,intents=intents,help_requested='help_request' in intents,
             emotion_signals=s.get('emotion_signals',[])+([answer] if 'emotion' in intents else []),
             help_requests=s.get('help_requests',[])+([answer] if 'help_request' in intents else []),
             risk_signals=s.get('risk_signals',[])+([risk] if risk['evidence'] else []))
    return s,{'intents':intents,'facts':facts,'uncertain':uncertain,'risk':risk,'action':action,
              'classification':category,'reply':reply,'emergency':risk['urgent'],'source':source}
