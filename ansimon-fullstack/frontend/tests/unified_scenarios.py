"""Unified scheduling, scoring, imported-record UI against live FastAPI."""
import json
import sqlite3
from pathlib import Path
from playwright.sync_api import expect
from conversation_scenarios import answer
from e2e import ROOT,URL


def force_due(database,sid):
 with sqlite3.connect(database) as c:c.execute('UPDATE care_schedules SET next_at=? WHERE id=?',('2000-01-01T00:00:00+00:00',sid))


def run_unified_scenarios(browser,errors,database):
 page=browser.new_page(viewport={'width':1440,'height':1100})
 page.add_init_script((ROOT/'frontend/tests/speech_probe.js').read_text()+'\nwindow.__tts.auto=true')
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto(URL+'/schedules')
 expect(page.get_by_role('heading',name='안부전화 예약',exact=True)).to_be_visible()
 page.get_by_label('어르신',exact=True).select_option('2')
 page.get_by_label('대상 별칭 (선택)',exact=True).fill('통합 예약 시연')
 page.get_by_label('매일 통화 시간 (한국)',exact=True).fill('09:30')
 # First write fails: keep all form fields. Retry then double-click must not duplicate.
 page.route('**/api/schedules',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"예약 저장 재시도 확인"}') if route.request.method=='POST' else route.continue_(),times=1)
 page.get_by_role('button',name='예약 추가',exact=True).click()
 expect(page.get_by_role('alert')).to_contain_text('예약 저장 재시도 확인')
 expect(page.get_by_label('대상 별칭 (선택)',exact=True)).to_have_value('통합 예약 시연')
 page.get_by_role('button',name='예약 추가',exact=True).evaluate('(b)=>{b.click();b.click()}')
 expect(page.get_by_text('매일 반복 예약을 저장했습니다.',exact=True)).to_be_visible()
 schedules=page.request.get(URL+'/api/schedules').json()['schedules'];assert len(schedules)==1
 sid=schedules[0]['id']
 page.get_by_role('button',name='수정',exact=True).click()
 page.get_by_label('매일 통화 시간 (한국)',exact=True).fill('09:45')
 page.get_by_role('button',name='예약 수정 저장',exact=True).click()
 expect(page.locator('tbody')).to_contain_text('09:45')
 force_due(database,sid);page.get_by_role('button',name='새로고침',exact=True).click()
 page.get_by_role('link',name='예약 통화 열기',exact=True).click()
 expect(page).to_have_url(__import__('re').compile(r'/call/2\?queue=\d+$'))
 page.get_by_role('button',name='전화 받기',exact=True).click()
 answer(page,'안 아파');expect(page.locator('.step-indicator')).to_have_text('1 / 5')
 page.reload();expect(page.locator('.step-indicator')).to_have_text('1 / 5')
 for i,text in enumerate(['밥 못 먹었어','잠을 못 잤어','약은 챙겼어요','기분은 괜찮아요'],start=2):
  answer(page,text)
  expect(page.locator('.step-indicator') if i<5 else page.locator('.phone-ended')).to_contain_text(f'{i} / 5' if i<5 else '안부 확인 완료')
 records=page.request.get(URL+'/api/calls?resident_id=2').json();record=records[0]
 assert record['assessment']['score']==20 and record['queue_id'] is not None
 assert page.request.get(URL+'/api/schedules').json()['pending']==[]
 page.goto(URL+'/records');page.get_by_label('기록 정렬').select_option('priority')
 expect(page.locator('tbody')).to_contain_text('통합 예약 시연')
 ranked=page.request.get(URL+'/api/calls?sort=priority').json()
 scores=[r['assessment']['score'] for r in ranked if r['assessment']['score'] is not None]
 assert scores==sorted(scores,reverse=True)
 page.locator('tbody tr').filter(has_text='통합 예약 시연').get_by_role('button',name='보기',exact=True).click()
 expect(page.get_by_role('dialog')).to_contain_text('20점')
 expect(page.get_by_role('dialog')).to_contain_text('식사')
 page.get_by_role('button',name='닫기',exact=True).click()
 page.goto(URL+'/schedules');page.get_by_role('button',name='수정',exact=True).click()
 page.get_by_label('매일 통화 시간 (한국)',exact=True).fill('09:46')
 page.get_by_role('button',name='예약 수정 저장',exact=True).click()
 expect(page.locator('tbody')).to_contain_text('09:46')
 force_due(database,sid);page.get_by_role('button',name='새로고침',exact=True).click()
 page.get_by_role('link',name='예약 통화 열기',exact=True).click()
 page.get_by_role('button',name='수신 거절',exact=True).click()
 expect(page.locator('.phone-ended')).to_contain_text('수신 거절')
 declined=page.request.get(URL+'/api/calls?resident_id=2').json()[0]
 assert declined['assessment']['score']==20 and declined['queue_id']!=record['queue_id']
 page.goto(URL+'/schedules');page.on('dialog',lambda dialog:dialog.accept())
 page.get_by_role('button',name='예약 해제',exact=True).click()
 expect(page.get_by_text('등록한 예약이 없습니다.',exact=True)).to_be_visible()
 assert page.request.get(URL+f"/api/calls/{record['id']}").json()['status']=='completed'
 # A legacy record retains its source, original score, raw summary and detail.
 legacy_id='22222222-2222-2222-2222-222222222222'
 legacy={'id':legacy_id,'date':'2026-01-01T10:00:00+09:00','status':'수신 거절','summary':'보존된 이전 통화 기록','recipient':'이전 기록 시연','assessment':{'score':20,'grade':'우선 확인','urgent':False,'problems':[],'call_points':20,'call_reason':'수신 거절','judgments':[]}}
 with sqlite3.connect(database) as c:c.execute('INSERT INTO imported_records VALUES(?,?,?)',('taewon:record:'+legacy_id,json.dumps(legacy),'2026-01-01T01:00:00+00:00'))
 page.goto(URL+'/records')
 row=page.locator('tbody tr').filter(has_text='이전 기록 시연')
 expect(row).to_contain_text('이전 taewon 기록');row.get_by_role('button',name='보기',exact=True).click()
 expect(page.get_by_role('dialog')).to_contain_text('보존된 이전 통화 기록')
 page.reload();expect(page.locator('tbody')).to_contain_text('이전 기록 시연')
 page.goto(URL+'/');page.get_by_role('checkbox',name='확인 우선순위순',exact=True).check()
 expect(page.locator('tbody tr').first).to_contain_text('우선 확인')
 page.close()
 print('PASS: unified React schedule validation/retry/duplicate guard, edit, queued accept/reload/five answers, priority detail and sorting')
 print('PASS: second scheduled occurrence decline, schedule removal preserves completed calls, legacy record detail/reload and dashboard priorities')
