"""FastAPI scheduling and legacy-record adapters for the unified web app."""
import asyncio
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import HTTPException, Query
from pydantic import BaseModel, Field
from scheduling import enqueue, next_run, stamp, ensure_editable


class ScheduleInput(BaseModel):
    resident_id:int=Field(gt=0)
    call_time:str=Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    recipient:str|None=Field(default=None,min_length=1,max_length=30)


def imported_view(payload):
    status={'수신 거절':'declined','안부 확인 완료':'completed','통화 중단':'interrupted'}.get(payload['status'],'interrupted')
    return {'id':'legacy:'+payload['id'],'resident_id':None,'resident_name':payload.get('recipient') or '이전 일반 시연',
            'started_at':payload['date'],'ended_at':payload['date'],'status':status,'summary':payload['summary'],
            'source':'taewon','assessment':payload['assessment'],'scheduled_at':payload.get('scheduled_at')}


def imported_rows(c):
    return [imported_view(json.loads(r[0])) for r in c.execute('SELECT payload_json FROM imported_records')]


def register(app,db):
    @asynccontextmanager
    async def lifespan(app):
        async def tick():
            while True:
                try:
                    await asyncio.to_thread(run_enqueue)
                except sqlite3.Error:
                    logging.getLogger('uvicorn.error').exception('예약 처리 실패: DB 경로·권한·잠금을 확인하세요.')
                await asyncio.sleep(1)
        def run_enqueue():
            with db(write=True) as c:enqueue(c)
        task=asyncio.create_task(tick())
        try:yield
        finally:
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
    app.router.lifespan_context=lifespan

    @app.get('/api/schedules')
    def list_schedules():
        with db(write=True) as c:
            enqueue(c)
            schedules=[dict(r) for r in c.execute('SELECT * FROM care_schedules WHERE enabled=1 ORDER BY call_time,id')]
            pending=[dict(r) for r in c.execute("SELECT * FROM scheduled_calls WHERE state IN ('pending','claimed') ORDER BY scheduled_at,id")]
            return {'schedules':schedules,'pending':pending,'timezone':'Asia/Seoul'}

    def write(body,sid=None):
        with db(write=True) as c:
            resident=c.execute('SELECT * FROM residents WHERE id=?',(body.resident_id,)).fetchone()
            if not resident:raise HTTPException(404,'어르신을 찾을 수 없습니다.')
            recipient=body.recipient.strip() if body.recipient is not None else resident['name']
            if not recipient:raise HTTPException(422,'대상 별칭을 입력하세요.')
            if sid is not None:
                old=c.execute('SELECT * FROM care_schedules WHERE id=? AND enabled=1',(sid,)).fetchone()
                if not old:raise HTTPException(404,'예약을 찾을 수 없습니다.')
                ensure_editable(c,sid)
                if (old['resident_id'],old['recipient'],old['call_time'])==(body.resident_id,recipient,body.call_time):return {'id':sid}
            values=(body.resident_id,recipient,body.call_time,stamp(next_run(datetime.now(timezone.utc),body.call_time)))
            try:
                if sid is None:
                    sid=c.execute('INSERT INTO care_schedules(resident_id,recipient,call_time,next_at) VALUES(?,?,?,?)',values).lastrowid
                else:
                    mapping_only=old['resident_id'] is None and old['recipient']==recipient and old['call_time']==body.call_time
                    if mapping_only:values=(*values[:3],old['next_at'])
                    c.execute('UPDATE care_schedules SET resident_id=?,recipient=?,call_time=?,next_at=? WHERE id=?',(*values,sid))
                    if mapping_only:
                        c.execute("UPDATE scheduled_calls SET resident_id=? WHERE schedule_id=? AND state='pending'",(body.resident_id,sid))
                    else:
                        c.execute("UPDATE scheduled_calls SET state='canceled' WHERE schedule_id=? AND state='pending'",(sid,))
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409,'같은 어르신과 시각의 예약이 이미 있습니다.') from exc
            return {'id':sid}

    @app.post('/api/schedules',status_code=201)
    def create_schedule(body:ScheduleInput):return write(body)

    @app.put('/api/schedules/{sid}')
    def update_schedule(sid:int,body:ScheduleInput):return write(body,sid)

    @app.delete('/api/schedules/{sid}')
    def delete_schedule(sid:int):
        with db(write=True) as c:
            if not c.execute('SELECT 1 FROM care_schedules WHERE id=? AND enabled=1',(sid,)).fetchone():raise HTTPException(404,'예약을 찾을 수 없습니다.')
            ensure_editable(c,sid)
            c.execute('UPDATE care_schedules SET enabled=0 WHERE id=?',(sid,))
            c.execute("UPDATE scheduled_calls SET state='canceled' WHERE schedule_id=? AND state='pending'",(sid,))
            return {'ok':True}

    @app.get('/api/imported-records/{record_id}')
    def imported_detail(record_id:str):
        with db() as c:
            row=c.execute('SELECT payload_json FROM imported_records WHERE origin_key=?',('taewon:record:'+record_id,)).fetchone()
            if not row:raise HTTPException(404,'가져온 통화 기록을 찾을 수 없습니다.')
            p=json.loads(row[0]);view=imported_view(p)
            view['turns']=[{'id':i,'question':j.get('topic','이전 질문'),'answer':j.get('answer',''),'classification':'unclassified','reply':'','emergency':j.get('urgent',False)} for i,j in enumerate(p['assessment'].get('judgments',[]))]
            return {**view,'attempts':[],'original_record':p}
