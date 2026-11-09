"""Real FastAPI/SQLite scenarios with controlled speech completion and STT text."""
from pathlib import Path
from playwright.sync_api import expect
from e2e import ROOT,URL

HEALTH='안녕하세요, 안심온입니다. 오늘 몸은 좀 어떠세요?'
MEAL='오늘 식사는 잘 챙겨 드셨나요?'
SLEEP='어젯밤 잠은 편히 주무셨나요?'
MEDICINE='드시는 약은 잘 챙겨 드셨나요?'
MOOD='오늘 기분은 어떠세요? 불편한 곳은 없으세요?'


def create_page(browser,errors,elder=1,auto=False):
    page=browser.new_page(viewport={'width':1440,'height':1100})
    script=(ROOT/'frontend/tests/speech_probe.js').read_text()
    page.add_init_script(script+('\nwindow.__tts.auto=true' if auto else ''))
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(URL+f'/call/{elder}')
    page.get_by_role('button',name='전화 받기',exact=True).click()
    page.wait_for_function('window.__tts.pending!==null||window.__tts.calls.length>0')
    return page


def complete_speech(page):
    page.wait_for_function('window.__tts.pending!==null')
    page.evaluate('window.__tts.finish()')


def answer(page,text):
    field=page.get_by_label('답변 입력')
    expect(field).to_be_enabled()
    field.fill(text);field.press('Enter')


def detail(page,elder):
    cid=page.request.get(URL+f'/api/calls?resident_id={elder}').json()[0]['id']
    return page.request.get(URL+f'/api/calls/{cid}').json()


def wait_speech(page,text):
    page.wait_for_function('(text)=>window.__tts.pending?.text===text',arg=text)


def run_conversation_scenarios(browser,errors):
    page=create_page(browser,errors)
    wait_speech(page,HEALTH)
    expect(page.get_by_label('답변 입력')).to_be_disabled()
    complete_speech(page)
    answer(page,'안 아파')
    wait_speech(page,'몸이 괜찮으시다니 다행이에요.')
    expect(page.get_by_label('질문과 답변')).not_to_contain_text(MEAL)
    assert detail(page,1)['turns'][0]['classification']=='positive'
    complete_speech(page);wait_speech(page,MEAL);complete_speech(page)
    assert page.evaluate('window.__tts.calls')==[HEALTH,'몸이 괜찮으시다니 다행이에요.',MEAL]
    print('PASS: real saved classification; follow-up TTS completes before next question is displayed or spoken')

    def fail_turn(route):
        route.fulfill(status=500,content_type='application/json',body='{"detail":"테스트용 답변 저장 오류"}')
    page.route('**/api/calls/*/turns',fail_turn,times=1)
    answer(page,'밥 안 먹었어')
    expect(page.get_by_role('alert')).to_contain_text('테스트용 답변 저장 오류')
    expect(page.get_by_label('답변 입력')).to_have_value('밥 안 먹었어')
    expect(page.locator('.step-indicator')).to_have_text('1 / 5')
    assert len(detail(page,1)['attempts'])==1
    assert len(page.evaluate('window.__tts.calls'))==3
    page.get_by_role('button',name='다시 시도',exact=True).click()
    wait_speech(page,'아직 식사를 못 하셨군요. 식사를 챙기실 수 있으면 좋겠어요.')
    assert len(detail(page,1)['attempts'])==2
    complete_speech(page);wait_speech(page,SLEEP);complete_speech(page)

    # STT transcript is retained in the input even if server saving fails.
    page.route('**/api/calls/*/turns',fail_turn,times=1)
    page.get_by_role('button',name='말하기',exact=True).click()
    page.evaluate("window.__recognition.emitFinal('잠을 못 잤어')")
    expect(page.get_by_role('alert')).to_contain_text('테스트용 답변 저장 오류')
    expect(page.get_by_label('답변 입력')).to_have_value('잠을 못 잤어')
    assert page.evaluate('window.__recognition.aborted')
    page.get_by_role('button',name='다시 시도',exact=True).click()
    wait_speech(page,'잠을 편히 못 주무셨군요. 불편함이 계속되면 도움을 요청해 주세요.')
    complete_speech(page);wait_speech(page,MEDICINE);complete_speech(page)
    answer(page,'먹는 약 없어')
    wait_speech(page,'드시는 약이 없으시군요. 알려주셔서 감사합니다.')
    complete_speech(page);wait_speech(page,MOOD);complete_speech(page)
    answer(page,'외로워')
    wait_speech(page,'마음이나 몸이 편치 않으시군요. 가까운 분이나 담당 생활지원사에게 말씀해 주세요.')
    assert detail(page,1)['status']=='in_progress'
    complete_speech(page)
    wait_speech(page,'안부 확인을 마쳤습니다. 오늘도 편안한 하루 보내세요.')
    assert detail(page,1)['status']=='in_progress'
    complete_speech(page)
    expect(page.locator('.phone-ended')).to_contain_text('안부 확인 완료')
    saved=detail(page,1)
    assert len(saved['turns'])==len(saved['attempts'])==5
    assert [t['classification'] for t in saved['turns']]==['positive','negative','negative','neutral','negative']
    assert saved['summary']=='건강 상태: 안 아파 / 식사: 밥 안 먹었어 / 수면: 잠을 못 잤어 / 복약: 먹는 약 없어 / 기분: 외로워'
    assert len(page.evaluate('window.__tts.calls'))==11
    page.get_by_role('link',name='통화 기록',exact=True).first.click()
    page.locator('tbody tr').first.get_by_role('button',name='보기').click()
    expect(page.get_by_role('dialog')).to_contain_text('중립')
    expect(page.get_by_role('dialog')).to_contain_text('밥 안 먹었어')
    page.close()
    print('PASS: text/STT server errors preserve answers; safe retry, contextual replies, final TTS then finish, factual summary and record labels')

    retry=create_page(browser,errors,elder=2,auto=True)
    answer(retry,'qwerty-one')
    expect(retry.locator('.reask-count')).to_have_text('다시 확인 1/2')
    expect(retry.locator('.step-indicator')).to_have_text('0 / 5')
    assert detail(retry,2)['turns']==[]
    # Commit the second uncertain answer but drop its response.
    def lose_response(route):route.fetch();route.abort()
    retry.route('**/api/calls/*/turns',lose_response,times=1)
    answer(retry,'qwerty-two')
    expect(retry.get_by_role('alert')).to_contain_text('연결할 수 없습니다')
    expect(retry.get_by_label('답변 입력')).to_have_value('qwerty-two')
    assert len(detail(retry,2)['attempts'])==2
    retry.get_by_role('button',name='다시 시도',exact=True).click()
    expect(retry.locator('.reask-count')).to_have_text('다시 확인 2/2')
    assert len(detail(retry,2)['attempts'])==2
    retry.reload()
    expect(retry.locator('.reask-count')).to_have_text('다시 확인 2/2')
    answer(retry,'qwerty-three')
    expect(retry.locator('.step-indicator')).to_have_text('1 / 5')
    for count,text in enumerate(['밥 먹었어','잘 잤어','약 먹었어','기분 좋아'],start=2):
        answer(retry,text)
        expect(retry.locator('.step-indicator') if count<5 else retry.locator('.phone-ended')).to_contain_text(f'{count} / 5' if count<5 else '안부 확인 완료')
    saved=detail(retry,2)
    assert len(saved['attempts'])==7 and len(saved['turns'])==5
    assert saved['turns'][0]['classification']=='unknown'
    assert 'qwerty' not in saved['summary'] and '확인 불가 항목: 건강 상태' in saved['summary']
    retry.close()
    print('PASS: two persisted reasks, response-loss retry does not duplicate, reload keeps retry count, third unknown finalizes, summary excludes gibberish')

    urgent=create_page(browser,errors,elder=3,auto=True)
    answer(urgent,'숨을 못 쉬겠어')
    expect(urgent.locator('.emergency-notice')).to_contain_text('지금 직접 119에 연락')
    expect(urgent.locator('.emergency-notice')).to_contain_text('실제 119 신고를 하지 않습니다')
    expect(urgent.get_by_label('답변 입력')).to_be_enabled()
    urgent.get_by_role('button',name='통화 종료',exact=True).click()
    expect(urgent.locator('.phone-ended')).to_contain_text('통화 중단')
    saved=detail(urgent,3)
    assert saved['turns'][0]['emergency'] and '자동 신고 없음' in saved['summary']
    urgent.close()
    print('PASS: urgent text displays and queues direct 119 guidance; saved records never claim dispatch')

    interrupted=create_page(browser,errors,elder=4)
    complete_speech(interrupted)
    answer(interrupted,'안 아파')
    wait_speech(interrupted,'몸이 괜찮으시다니 다행이에요.')
    expect(interrupted.get_by_role('button',name='통화 종료',exact=True)).to_be_enabled()
    interrupted.get_by_role('button',name='통화 종료',exact=True).click()
    expect(interrupted.locator('.phone-ended')).to_contain_text('통화 중단')
    assert len(detail(interrupted,4)['turns'])==1
    assert detail(interrupted,4)['summary']=='건강 상태: 안 아파'
    assert interrupted.evaluate('window.__tts.pending===null')
    assert len(interrupted.evaluate('window.__tts.calls'))==2
    interrupted.close()
    print('PASS: interrupt during follow-up speech retains committed answer and cancels next-question sequence')

    fallback=create_page(browser,errors,elder=4)
    fallback.evaluate('window.__tts.fail()')
    expect(fallback.get_by_label('답변 입력')).to_be_enabled()
    expect(fallback.locator('.tts-notice')).to_contain_text('화면의 글')
    fallback.get_by_role('button',name='통화 종료',exact=True).click()
    expect(fallback.locator('.phone-ended')).to_contain_text('통화 중단')
    fallback.close()
    print('PASS: speech error falls back to text without blocking answers or call termination')
