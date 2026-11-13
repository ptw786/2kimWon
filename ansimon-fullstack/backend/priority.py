import json
from legacy_priority import assessment_for as legacy_assessment
from review import build

def assessment_for(c,call):
 row=c.execute('SELECT payload_json FROM call_reviews WHERE call_id=?',(call['id'],)).fetchone()
 return json.loads(row[0]) if row else {**legacy_assessment(c,call),'version':'legacy-v1'}

def save_review(c,call_id,state):
 c.execute('INSERT INTO call_reviews VALUES(?,?) ON CONFLICT(call_id) DO UPDATE SET payload_json=excluded.payload_json',(call_id,json.dumps(build(state),ensure_ascii=False)))

def sort_key(record):
 a=record['assessment']
 # Separate versions; never compare the old 0-100 scores against new 0-15 scores.
 return (1 if a.get('urgent') else 0, 2 if a.get('version')=='review-v2' else 1,a.get('score') if a.get('score') is not None else -1)
