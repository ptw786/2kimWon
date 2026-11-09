import re
from normalizer import normalize

def classify(text, facts, uncertain, risk, source):
    t=normalize(text); intents=[]
    rules={'question_repeat':r'뭐라고|안들려|다시말|다시질문', 'refusal':r'말하기싫|대답하기싫',
      'daily_story':r'손자|딸|아들|가족|산책|텔레비|친구', 'emotion':r'외로|기쁘|행복|슬퍼|우울',
      'symptom':r'아파|아프|어지|기침', 'help_request':r'도와|도움|살려',
      'future':r'이따|내일|할거|먹을거', 'past':r'어제|작년|지난|예전에',
      'correction':r'아니[,， ]|정정', 'double_negation':r'안먹은건아니',
      'indirect_answer':r'입맛|반찬|배고|배불', 'partial_answer':r'조금|아침만|반만',
      'ai_question':r'너는|당신은|몇살|누구|뭐해|몇시'}
    for k,p in rules.items():
        if re.search(p,text if k=='correction' else t):intents.append(k)
    if source=='stt_error':intents.append('stt_error')
    if source=='silence':intents.append('silence')
    if risk['urgent']:intents.append('urgent')
    if len(facts)>1:intents.append('multiple_facts')
    for f in facts.values():
        intents.append({'positive':'clear_positive','negative':'clear_negative','neutral':'partial_or_neutral'}[f['classification']])
    if uncertain:intents.append('needs_confirmation')
    return list(dict.fromkeys(intents)) or ['ambiguous']
