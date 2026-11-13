import re
from conversation import assess
from normalizer import normalize, corrected

PATTERNS={'condition':r'몸|허리|아파|아프|건강|피곤|어지|기운', 'meal':r'밥|식사|아침|점심|저녁|반찬',
 'sleep':r'잠|잤|깼|설쳤|새벽', 'medicine':r'약|복용', 'mood':r'기분|외로|기쁘|행복|우울'}

def extract(text, topic):
    facts={}; uncertain=[]
    clauses=re.split(r'[.。!?]|[,，]|고\s*약|는데\s*',text)
    # Keep conjunction topic markers ("밥도 먹고 약도 먹었어").
    clauses=re.split(r'[.。!?]|[,，]|(?<=고)\s+(?=약|잠|밥)|(?<=는데)\s*',corrected(text))
    for clause in clauses:
        t=normalize(clause)
        topics=[k for k,p in PATTERNS.items() if re.search(p,t)] or [topic]
        for k in topics:
            historical=bool(re.search(r'작년|예전|지난달|옛날'+('' if k=='sleep' else r'|어제'),t)) and not re.search(r'오늘|지금|현재',t)
            other_person=bool(re.search(r'(?:딸|아들|손자|친구|남편|아내|옆집).{0,2}(?:이|가|은|는)',t))
            if historical or other_person or re.search(r'이따|먹을거|내일|어제는먹|모르겠|먹었는지',t):
                uncertain.append({'topic':k,'evidence':clause});continue
            category=assess(k,clause).classification
            if t in ('응','네','예','맞아','맞아요'): category='positive'
            if t in ('아니','아니요','아뇨'): category='negative'
            if t in ('그럭저럭','그냥그랬어','보통'): category='neutral'
            if re.search(r'안먹은건아니',t) and k in ('meal','medicine'): category='positive'
            if k=='meal' and re.search(r'아침만먹|조금먹',t): category='neutral'
            if k=='medicine' and re.search(r'안먹어도[돼되된]',t): category='neutral'
            if k=='meal' and re.search(r'먹고$',t): category='positive'
            if k=='sleep' and re.search(r'설쳤|자꾸깼',t): category='negative'
            if k=='condition' and re.search(r'허리.{0,2}아파',t): category='negative'
            if k=='medicine' and re.search(r'약.{0,5}챙겼',t) and not re.search(r'못|안|않|모르',t): category='positive'
            if k=='condition' and re.search(r'피곤|기운이없',t) and not re.search(r'안피곤|피곤하지않|기운이없는건아니',t): category='negative'
            if k=='mood' and re.search(r'기분.{0,3}좋지않|기분.{0,3}안좋',t): category='negative'
            if k=='condition' and re.search(r'괜찮지않',t): category='negative'
            if category!='unknown': facts[k]={'classification':category,'evidence':clause.strip()}
    return facts,uncertain
