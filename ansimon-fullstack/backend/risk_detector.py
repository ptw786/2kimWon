"""Rule signals only; deliberately no diagnosis or clinical score."""
import re
from normalizer import normalize

DANGER=r'119(?:좀)?(?:불러|신고해)|피가(?:안멈|멈추지않)|자해하고싶|살기싫|숨쉬기힘들|숨.{0,2}못쉬|호흡곤란|가슴.{0,5}심하게아[파프]|쓰러졌|의식.{0,2}없|크게넘어|죽고싶|자살|살려줘'
NEGATION=r'죽고싶은건아니|죽고싶지않|숨쉬기힘들지않|가슴.{0,5}안아파|호흡곤란.{0,3}없|자살.{0,3}생각없'

def detect(text):
    urgent=False;historical=False;negated=False;pending=False;evidence=[]
    # Analyze segments separately so denying self-harm cannot mask breathing difficulty.
    for clause in re.split(r'[.!?。,，;]|지만|그런데|근데',text):
        t=normalize(clause)
        if not re.search(DANGER,t):continue
        evidence.append(clause)
        matches=list(re.finditer(DANGER,t))
        denied=[bool(re.match(r'(?:지않|은건아니|은게아니|은것은아니)',t[m.end():])) or bool(re.search(r'안$',t[:m.start()])) for m in matches]
        denial=all(denied) or (len(matches)==1 and bool(re.search(NEGATION,t)))
        negated|=denial
        quoted=bool(re.search(r'뉴스|드라마|라고했|라는말|다고했',t))
        past=bool(re.search(r'어제|작년|예전에|지난주|옛날',t));historical|=past or quoted
        current=bool(re.search(r'지금|현재|오늘도',t))
        if not denial:
            if quoted or (past and not current):pending=True
            else:urgent=True
    return {'urgent':urgent,'needs_confirmation':pending and not urgent,'negated':negated,
            'historical':historical,'evidence':' / '.join(evidence)}
