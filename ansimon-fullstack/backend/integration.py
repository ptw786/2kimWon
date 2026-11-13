"""Read-only adapters for preserved legacy call records."""
import json
from fastapi import HTTPException


def imported_view(payload):
    status={'수신 거절':'declined','안부 확인 완료':'completed','통화 중단':'interrupted'}.get(payload['status'],'interrupted')
    return {'id':'legacy:'+payload['id'],'resident_id':None,'resident_name':payload.get('recipient') or '이전 일반 시연',
            'started_at':payload['date'],'ended_at':payload['date'],'status':status,'summary':payload['summary'],
            'source':'taewon','assessment':{**payload['assessment'],'version':'legacy-v1'},'scheduled_at':payload.get('scheduled_at')}


def imported_rows(c):
    return [imported_view(json.loads(r[0])) for r in c.execute('SELECT payload_json FROM imported_records')]


def register(app,db):
    @app.get('/api/imported-records/{record_id}')
    def imported_detail(record_id:str):
        with db() as c:
            row=c.execute('SELECT payload_json FROM imported_records WHERE origin_key=?',('taewon:record:'+record_id,)).fetchone()
            if not row:raise HTTPException(404,'가져온 통화 기록을 찾을 수 없습니다.')
            p=json.loads(row[0]);view=imported_view(p)
            view['turns']=[{'id':i,'question':j.get('topic','이전 질문'),'answer':j.get('answer',''),'classification':'unclassified','reply':'','emergency':j.get('urgent',False)} for i,j in enumerate(p['assessment'].get('judgments',[]))]
            return {**view,'attempts':[],'original_record':p}
