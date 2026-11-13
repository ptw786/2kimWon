from playwright.sync_api import expect
from conversation_scenarios import create_page,answer,detail
from e2e import URL

def run_review_scenarios(browser,errors,database):
 for elder,answers,score in [(1,['안 아파','밥 먹었어','잘 잤어','먹는 약 없어','좋아'],0),(2,['몸이 조금 아파','밥 먹었어','잘 잤어','먹는 약 없어','좋아'],1)]:
  p=create_page(browser,errors,elder=elder,auto=True)
  for i,text in enumerate(answers):
   if elder==1 and i==0:
    p.route('**/api/calls/*/turns',lambda route:route.fulfill(status=500,content_type='application/json',body='{"detail":"테스트용 저장 실패"}'),times=1)
    answer(p,text);expect(p.get_by_role('alert')).to_contain_text('테스트용 저장 실패')
    expect(p.get_by_label('답변 입력')).to_have_value(text)
    p.get_by_role('button',name='다시 시도',exact=True).click()
   else:answer(p,text)
   expect(p.locator('.step-indicator') if i<4 else p.locator('.phone-ended')).to_contain_text(f'{i+1} / 5' if i<4 else '안부 확인 완료')
  a=detail(p,elder)['assessment'];assert a['score']==score and a['confirmed_count']==5
  p.close()
 p=create_page(browser,errors,elder=3,auto=True)
 for text in ['안 아파','밥 먹었어']:answer(p,text)
 for _ in range(3):answer(p,'zzzzz')
 expect(p.locator('.step-indicator')).to_have_text('3 / 5')
 answer(p,'먹는 약 없어');answer(p,'좋아');expect(p.locator('.phone-ended')).to_be_visible()
 a=detail(p,3)['assessment'];assert a['confirmed_count']==4 and a['score']==0
 p.goto(URL+'/records');expect(p.locator('thead')).to_contain_text('확인 우선순위 — 최대 15점')
 expect(p.locator('tbody')).to_contain_text('답변 해석 불가 · 4/5개 항목 확인');p.close()
 for text,state in [('119','possible'),('구급차 보내줘','confirmed')]:
  p=create_page(browser,errors,elder=4,auto=True);answer(p,text)
  expect(p.get_by_label('질문과 답변')).to_contain_text('실제 신고를 하지 않습니다')
  assert detail(p,4)['dialogue_state']['count']==0
  p.get_by_role('button',name='통화 종료',exact=True).click();expect(p.locator('.phone-ended')).to_be_visible()
  a=detail(p,4)['assessment'];assert a['emergency_state']==state and a['score'] is None
  p.goto(URL+'/records');expect(p.locator('tbody')).not_to_contain_text('100점');p.close()
 print('PASS: live v2 full/partial review, maximum-15 header, 119 possible/explicit safety pause, saved states and unchanged result statuses')
