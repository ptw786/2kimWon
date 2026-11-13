"""Live call regression: short answers, exact history, draft recovery and conflicts."""
import sqlite3
from playwright.sync_api import expect
from conversation_scenarios import create_page,answer,detail
from e2e import URL


def run_repair_scenarios(browser,errors,database):
 page=create_page(browser,errors,elder=1,auto=True)
 field=page.get_by_label('답변 입력')
 expect(field).to_be_enabled();field.fill('새로고침 전 작성하던 답변')
 page.reload();expect(field).to_have_value('새로고침 전 작성하던 답변')
 answer(page,'안 아파');expect(page.locator('.step-indicator')).to_have_text('1 / 5')
 # A pending, uncommitted answer must still have a retry button after a reload.
 page.route('**/api/calls/*/turns',lambda r:r.fulfill(status=503,content_type='application/json',body='{"detail":"초안 복구 검사"}'),times=1)
 answer(page,'먹었어');expect(page.get_by_role('alert')).to_contain_text('초안 복구 검사')
 page.reload();expect(field).to_have_value('먹었어');expect(field).to_be_disabled()
 expect(page.get_by_role('alert')).to_contain_text('다시 시도')
 page.get_by_role('button',name='다시 시도',exact=True).click()
 expect(page.locator('.step-indicator')).to_have_text('2 / 5')
 answer(page,'어');expect(page.locator('.step-indicator')).to_have_text('3 / 5')
 answer(page,'약 먹었어');expect(page.locator('.step-indicator')).to_have_text('4 / 5')
 answer(page,'좋아');expect(page.locator('.phone-ended')).to_contain_text('안부 확인 완료')
 saved=detail(page,1);assert [t['classification'] for t in saved['turns']]==['positive']*5
 assert page.evaluate('(id)=>sessionStorage.getItem(`ansimon:draft:${id}`)',saved['id']) is None
 page.close()
 print('PASS: typed draft survives reload; failed submission restores retry controls; short 어/좋아 complete and persist without duplicate answers')

 page=create_page(browser,errors,elder=2,auto=True)
 expect(page.get_by_label('답변 입력')).to_be_enabled()
 cid=detail(page,2)['id']
 page.get_by_label('답변 입력').fill('몸이 많이 아파')
 r=page.request.post(URL+f'/api/calls/{cid}/turns',data={'answer':'안 아파','engine':'hybrid','index':0,'attempt':0});assert r.status==201
 page.get_by_label('답변 입력').press('Enter')
 expect(page.get_by_role('alert')).to_contain_text('최신 상태')
 expect(page.locator('.step-indicator')).to_have_text('1 / 5')
 expect(page.get_by_label('답변 입력')).to_be_enabled();expect(page.get_by_label('답변 입력')).to_have_value('')
 expect(page.get_by_role('region',name='이전 질문의 미전송 답변')).to_contain_text('몸이 많이 아파')
 assert detail(page,2)['turns'][0]['answer']=='안 아파'
 page.reload();expect(page.get_by_role('region',name='이전 질문의 미전송 답변')).to_contain_text('몸이 많이 아파')
 expect(page.get_by_label('답변 입력')).to_have_value('')
 answer(page,'먹었어');expect(page.locator('.step-indicator')).to_have_text('2 / 5')
 assert len(detail(page,2)['turns'])==2
 page.get_by_role('button',name='보관한 답변 지우기',exact=True).click()
 expect(page.get_by_role('region',name='이전 질문의 미전송 답변')).to_have_count(0)
 page.get_by_role('button',name='통화 종료',exact=True).click();expect(page.locator('.phone-ended')).to_be_visible();page.close()
 print('PASS: real 409 answer conflict reloads authoritative state, preserves old text separately and allows the next question')

 page=create_page(browser,errors,elder=3,auto=True)
 expect(page.get_by_label('답변 입력')).to_be_enabled();cid=detail(page,3)['id']
 page.get_by_label('답변 입력').fill('내가 작성 중인 이전 질문 답변')
 page.request.post(URL+f'/api/calls/{cid}/turns',data={'answer':'안 아파','engine':'hybrid','index':0,'attempt':0})
 page.reload();expect(page.locator('.step-indicator')).to_have_text('1 / 5')
 expect(page.get_by_label('답변 입력')).to_have_value('')
 expect(page.get_by_role('region',name='이전 질문의 미전송 답변')).to_contain_text('내가 작성 중인 이전 질문 답변')
 page.get_by_role('button',name='통화 종료',exact=True).click();expect(page.locator('.phone-ended')).to_be_visible();page.close()
 print('PASS: a draft for a stale question never becomes an automatic answer to a newer question after refresh')

 page=create_page(browser,errors,elder=4,auto=True)
 answer(page,'무슨 말인지 모르겠어');expect(page.locator('.reask-count')).to_have_text('다시 확인 1/2')
 expect(page.locator('.input-question')).to_contain_text('지금 몸 상태가 괜찮으세요?')
 answer(page,'어');expect(page.locator('.step-indicator')).to_have_text('1 / 5')
 assert detail(page,4)['attempts'][-1]['question']=='지금 몸 상태가 괜찮으세요?'
 answer(page,'먹었어');expect(page.locator('.step-indicator')).to_have_text('2 / 5')
 answer(page,'잤어');expect(page.locator('.step-indicator')).to_have_text('3 / 5')
 expect(page.get_by_label('질문과 답변')).to_contain_text('잠은 주무셨군요.')
 assert detail(page,4)['dialogue_state']['facts']['sleep']['quality']=='unconfirmed'
 answer(page,'먹는 약 없어');expect(page.locator('.step-indicator')).to_have_text('4 / 5')
 answer(page,'별로야');expect(page.locator('.phone-ended')).to_contain_text('안부 확인 완료')
 saved=detail(page,4);assert saved['turns'][2]['classification']=='neutral' and saved['turns'][4]['classification']=='negative'
 page.goto(URL+'/records');page.locator('tbody tr').filter(has_text='최복순').first.get_by_role('button',name='보기',exact=True).click()
 expect(page.get_by_role('dialog')).to_contain_text('지금 몸 상태가 괜찮으세요?')
 page.get_by_role('button',name='닫기',exact=True).click()
 page.goto(URL+'/');expect(page.get_by_role('link',name='안부전화 예약',exact=True)).to_have_count(0)
 page.goto(URL+'/schedules');expect(page.get_by_role('heading',name='페이지를 찾을 수 없습니다')).to_be_visible()
 page.goto(URL+'/call/1?queue=1');expect(page.get_by_role('heading',name='전화 예약 기능이 종료되었습니다')).to_be_visible()
 expect(page.get_by_role('button',name='전화 받기',exact=True)).to_have_count(0)
 assert page.request.get(URL+'/api/schedules').status==404
 with sqlite3.connect(database) as c:
  assert not c.execute("SELECT 1 FROM sqlite_master WHERE name IN ('care_schedules','scheduled_calls')").fetchall()
  assert not c.execute('PRAGMA foreign_key_check').fetchall()
 page.close()
 print('PASS: real clarification history, non-invented sleep quality and negative mood are saved; reservation routes/tables/menu are removed')
