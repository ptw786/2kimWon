import re
from conversation import assess
from normalizer import normalize, corrected
from scenarios import YES, NO

PATTERNS={'condition':r'몸|허리|아파|아프|건강|피곤|어지|기운', 'meal':r'밥|식사|아침|점심|저녁|반찬',
 'sleep':r'잠|잤|깼|설쳤|새벽', 'medicine':r'약|복용', 'mood':r'기분|외로|기쁘|행복|우울'}

def extract(text, topic, allow_confirmation=True):
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
            if t in YES: category='positive' if allow_confirmation else 'unknown'
            if t in NO: category='negative' if allow_confirmation else 'unknown'
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
            core=re.sub(r'^(?:오늘)?(?:기분[은이]?|몸상태[는가]?|몸[은이]?)','',t)
            if k in ('condition','mood','sleep'):
                if core in {'좋아','좋아요','좋습니다','괜찮아','괜찮아요','괜찮습니다','편안해','편안해요'}:category='positive'
                if core in {'별로','별로야','별로예요','별로에요','별로안좋아','별로안좋아요','안좋아','안좋아요','좋지않아','좋지않아요','좋은건아니야','좋지는않아'}:category='negative'
                if core in {'그냥그래','그저그래','그냥그래요','보통이야','보통이에요','안좋은건아니야','안좋지는않아'}:category='neutral'
            sleep_only=k=='sleep' and bool(re.fullmatch(r'(?:잠[은을]?)?(?:잤어|잤어요|잤습니다|잤지|자긴잤어|좀잤어|조금잤어)',t))
            if sleep_only:category='neutral'
            if category!='unknown':
                facts[k]={'classification':category,'evidence':clause.strip()}
                if sleep_only:facts[k].update(sleep_occurred=True,quality='unconfirmed')
    return facts,uncertain
