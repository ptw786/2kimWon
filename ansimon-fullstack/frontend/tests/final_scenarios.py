"""Final regression checks for saved-response timeouts and physical SQLite rows."""
import json
import sqlite3
from playwright.sync_api import expect
from conversation_scenarios import create_page,answer,detail,MEAL,HEALTH
from e2e import URL


def run_timeout_recovery(browser,errors):
    page=create_page(browser,errors,elder=1,auto=True)
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    # Commit through the actual server, but stall decoding of the first response.
    page.evaluate('''()=>{
      const original=window.fetch;let first=true;
      window.fetch=async(url,options)=>{
        const response=await original(url,options);
        if(first&&options?.method==='POST'&&String(url).endsWith('/turns')){
          first=false;window.__responseCommitted=true;
          return {ok:response.ok,status:response.status,json:()=>new Promise((_resolve,reject)=>{
            const fail=()=>reject(new DOMException('Request timed out','AbortError'));
            if(options.signal.aborted)fail();else options.signal.addEventListener('abort',fail,{once:true});
          })};
        }
        return response;
      };
    }''')
    answer(page,'안 아파')
    page.wait_for_function('window.__responseCommitted===true')
    assert len(detail(page,1)['turns'])==1
    expect(page.locator('.step-indicator')).to_have_text('0 / 5')
    expect(page.get_by_role('alert')).to_contain_text('요청 시간이 초과되었습니다',timeout=18000)
    expect(page.get_by_label('답변 입력')).to_have_value('안 아파')
    expect(page.get_by_role('button',name='다시 시도',exact=True)).to_be_enabled()
    page.get_by_role('button',name='다시 시도',exact=True).click()
    expect(page.locator('.step-indicator')).to_have_text('1 / 5')
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    expect(page.locator('.input-question')).to_contain_text(MEAL)
    saved=detail(page,1)
    assert len(saved['attempts'])==len(saved['turns'])==1
    page.get_by_role('button',name='통화 종료',exact=True).click()
    expect(page.locator('.phone-ended')).to_contain_text('통화 중단')
    previous=detail(page,1)['id']
    page.get_by_role('button',name='다시 전화받기',exact=True).click()
    page.get_by_role('button',name='전화 받기',exact=True).click()
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    expect(page.locator('.step-indicator')).to_have_text('0 / 5')
    expect(page.get_by_label('답변 입력')).to_have_value('')
    expect(page.locator('.input-question')).to_contain_text(HEALTH)
    expect(page.locator('.chat.user')).to_have_count(0)
    expect(page.get_by_role('alert')).to_have_count(0)
    assert detail(page,1)['id']!=previous
    assert page.evaluate('(text)=>window.__tts.calls.filter(value=>value===text).length',HEALTH)==2
    page.get_by_role('button',name='통화 종료',exact=True).click()
    expect(page.locator('.phone-ended')).to_contain_text('통화 중단')
    assert detail(page,1)['turns']==[]
    page.close()
    print('PASS: real committed answer with stalled response times out, preserves draft and retries without duplicate SQLite rows')
    print('PASS: new call after ending resets question, draft, count, messages and errors while preserving previous records')


def audit_sqlite(db_path):
    with sqlite3.connect(db_path.resolve().as_uri()+'?mode=ro',uri=True) as conn:
        conn.row_factory=sqlite3.Row
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert not conn.execute('SELECT call_id,topic,COUNT(*) FROM turns GROUP BY call_id,topic HAVING COUNT(*)>1').fetchall()
        assert not conn.execute('SELECT call_id,question_index,attempt,COUNT(*) FROM turn_attempts GROUP BY call_id,question_index,attempt HAVING COUNT(*)>1').fetchall()
        rows=conn.execute('SELECT * FROM calls').fetchall()
        counts={status:0 for status in ('completed','declined','interrupted','in_progress')}
        for row in rows:
            counts[row['status']]+=1
            turns=conn.execute('SELECT COUNT(*) FROM turns WHERE call_id=?',(row['id'],)).fetchone()[0]
            if row['status']=='completed':assert turns==5 and row['summary'] and row['ended_at']
            if row['status']=='declined':assert turns==0 and row['summary']=='수신 거절' and row['ended_at']
            if row['status']=='interrupted':assert row['summary'] and row['ended_at']
        assert counts['completed']>0 and counts['declined']>0 and counts['interrupted']>0
        assert counts['in_progress']==0
        result={'integrity':'ok','foreign_key_violations':0,'duplicate_turns':0,'duplicate_attempts':0,
                'calls':len(rows),'statuses':counts,'turns':conn.execute('SELECT COUNT(*) FROM turns').fetchone()[0],
                'attempts':conn.execute('SELECT COUNT(*) FROM turn_attempts').fetchone()[0]}
    print('SQLITE_AUDIT: '+json.dumps(result,ensure_ascii=False))
    print('PASS: direct read-only SQLite audit verifies every completed/declined/interrupted record and zero duplicate/orphan rows')
    return result
