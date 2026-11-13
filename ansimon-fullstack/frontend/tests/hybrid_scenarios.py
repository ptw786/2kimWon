"""Hybrid flow against real FastAPI/SQLite; speech events are controlled."""
from playwright.sync_api import expect
from conversation_scenarios import create_page,answer,detail

def run_hybrid_scenarios(browser,errors):
 page=create_page(browser,errors,elder=4,auto=True)
 answer(page,'손자가 놀러 왔어')
 expect(page.locator('.phone-current')).to_contain_text('조금 더 들려')
 saved=detail(page,4)
 assert saved['dialogue_state']['daily_count']==1
 page.reload()
 expect(page.locator('.phone-current')).to_contain_text('조금 더 들려')
 answer(page,'오늘 손자가 상을 받았어')
 expect(page.locator('.phone-current')).to_contain_text('오늘 몸은')
 answer(page,'안 아파')
 expect(page.locator('.step-indicator')).to_have_text('1 / 5')
 answer(page,'밥은 먹었고 약도 먹었는데 잠을 못 잤어')
 expect(page.locator('.step-indicator')).to_have_text('2 / 5')
 saved=detail(page,4)
 assert set(saved['dialogue_state']['facts'])>={'condition','meal','medicine','sleep'}
 answer(page,'숨쉬기 힘들어')
 expect(page.locator('.emergency-notice')).to_be_visible()
 expect(page.locator('.phone-current')).to_contain_text('안전을 위해 질문을 멈췄습니다')
 assert detail(page,4)['dialogue_state']['count']==2
 page.reload()
 expect(page.locator('.phone-current')).to_contain_text('안전을 위해 질문을 멈췄습니다')
 page.get_by_role('button',name='통화 종료',exact=True).click()
 expect(page.locator('.phone-ended')).to_contain_text('통화 중단')
 assert detail(page,4)['analysis_events'][-1]['action']=='safety_pause'
 page.close()
 print('PASS: hybrid daily limit, reload state, explicit health answer, multiple facts, safety pause and persisted interrupted records')
