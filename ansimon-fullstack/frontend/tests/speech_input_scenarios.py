"""Browser UI + actual API/DB with explicitly simulated STT/TTS lifecycle events."""
import json
import os
from pathlib import Path
from playwright.sync_api import expect
from e2e import ROOT,URL
from conversation_scenarios import answer,detail,complete_speech,wait_speech,HEALTH,MEAL

ANSWERS=['안 아파','밥 먹었어','잘 잤어','먹는 약 없어','기분 좋아']


def create(browser,errors,elder=1,auto=True,suffix=''):
    page=browser.new_page(viewport={'width':1440,'height':1100})
    script=(ROOT/'frontend/tests/speech_probe.js').read_text()
    page.add_init_script(script+('\nwindow.__tts.auto=true;' if auto else '')+'\n'+suffix)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(URL+f'/call/{elder}')
    page.get_by_role('button',name='전화 받기',exact=True).click()
    page.wait_for_function('window.__tts.calls.length>0')
    return page


def expect_count(page,count):expect(page.locator('.step-indicator')).to_have_text(f'{count} / 5')


def complete_text(page,answers=ANSWERS,start=0):
    for count,text in enumerate(answers,start=start+1):
        answer(page,text)
        if count==5:expect(page.locator('.phone-ended')).to_contain_text('안부 확인 완료')
        else:expect_count(page,count)


def run_speech_input_scenarios(browser,errors,stop_backend,recover_backend):
    page=create(browser,errors)
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    page.get_by_role('button',name='말하기',exact=True).click()
    assert page.evaluate('window.__recognition.lang')=='ko-KR'
    assert page.evaluate('window.__recognition.interimResults')
    expect(page.locator('.speech-input-status')).to_have_attribute('data-stt-status','listening')
    page.evaluate("window.__recognition.emitError('not-allowed')")
    expect(page.get_by_role('alert')).to_contain_text('마이크 사용 권한이 거부')
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    complete_text(page)
    page.get_by_role('link',name='통화 기록',exact=True).first.click()
    expect(page.locator('tbody tr').first).to_contain_text('완료')
    page.reload()
    expect(page.locator('tbody tr').first).to_contain_text('완료')
    page.locator('tbody tr').first.get_by_role('button',name='보기').click()
    expect(page.get_by_role('dialog')).to_contain_text('먹는 약 없어')
    page.close()
    print('PASS: simulated mic denial gives Korean guidance; text-only five-question completion, record detail and URL refresh persist')

    unsupported=create(browser,errors,elder=2,suffix='window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;')
    expect(unsupported.get_by_label('답변 입력')).to_be_enabled()
    unsupported.get_by_role('button',name='말하기',exact=True).click()
    expect(unsupported.get_by_role('alert')).to_contain_text('음성 인식을 지원하지 않습니다')
    complete_text(unsupported)
    assert len(detail(unsupported,2)['turns'])==5
    unsupported.close()
    print('PASS: STT unsupported browser simulation still completes every question by text')

    page=create(browser,errors,elder=3,suffix='window.webkitSpeechRecognition=window.SpeechRecognition;window.SpeechRecognition=undefined;')
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    for code,phrase in [('no-speech','음성을 인식하지 못했습니다'),('audio-capture','마이크를 찾지 못했습니다'),('network','연결할 수 없습니다'),('service-not-allowed','음성 인식 서비스를 사용할 수 없습니다')]:
        page.get_by_role('button',name='말하기',exact=True).click()
        page.evaluate('(code)=>window.__recognition.emitError(code)',code)
        expect(page.get_by_role('alert')).to_contain_text(phrase)
        expect(page.get_by_label('답변 입력')).to_be_enabled()
        assert detail(page,3)['attempts']==[]
    page.evaluate("window.__throwRecognitionStart='NotAllowedError'")
    page.get_by_role('button',name='말하기',exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('권한이 거부')
    page.evaluate('window.__throwRecognitionStart=null;window.__deferRecognitionStart=true')
    page.get_by_role('button',name='말하기',exact=True).click()
    expect(page.locator('.speech-input-status')).to_have_attribute('data-stt-status','starting')
    before=page.evaluate('window.__recognitionSessions.length')
    page.get_by_role('button',name='말하기 중지',exact=True).click()
    assert page.evaluate('window.__recognitionSessions.length')==before
    expect(page.locator('.speech-input-status')).to_have_attribute('data-stt-status','idle')
    page.evaluate('window.__deferRecognitionStart=false')
    page.get_by_role('button',name='말하기',exact=True).click()
    page.evaluate("window.__oldResult=window.__recognition.onresult;window.__recognition.emitInterim('안 아')")
    expect(page.locator('.transcript.interim')).to_contain_text('안 아')
    assert detail(page,3)['attempts']==[]
    if os.environ.get('ANSIMON_SCREENSHOT_DIR'):
        target=Path(os.environ['ANSIMON_SCREENSHOT_DIR']);target.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(target/'interim-transcript.png'),full_page=True)
    page.get_by_role('button',name='말하기 중지',exact=True).click()
    page.evaluate("window.__oldResult({results:[Object.assign([{transcript:'늦은 답변'}],{isFinal:true})]})")
    assert detail(page,3)['attempts']==[]
    # Typing while the mic listens cancels it; a late transcript cannot overwrite a draft.
    page.get_by_role('button',name='말하기',exact=True).click()
    page.evaluate('()=>{ window.__oldResult=window.__recognition.onresult }')
    page.get_by_label('답변 입력').fill('작성 중인 답변')
    assert page.evaluate('window.__recognition.aborted')
    page.evaluate("window.__oldResult({results:[Object.assign([{transcript:'덮어쓰기 금지'}],{isFinal:true})]})")
    expect(page.get_by_label('답변 입력')).to_have_value('작성 중인 답변')
    page.get_by_label('답변 입력').fill('')
    page.get_by_role('button',name='말하기',exact=True).click()
    page.evaluate("window.__recognition.emitFinal('가'.repeat(501))")
    expect(page.get_by_role('alert')).to_contain_text('500자 이내')
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    assert detail(page,3)['attempts']==[]
    page.get_by_label('답변 입력').fill('')
    page.get_by_role('button',name='말하기',exact=True).click()
    page.evaluate("window.__oldResult=window.__recognition.onresult;window.__recognition.emitFinal('안 아파')")
    expect_count(page,1)
    expect(page.locator('.transcript').last).to_contain_text('안 아파')
    page.evaluate("window.__oldResult({results:[Object.assign([{transcript:'안 아파'}],{isFinal:true})]})")
    assert len(detail(page,3)['attempts'])==1
    page.get_by_role('button',name='통화 종료',exact=True).click()
    expect(page.locator('.phone-ended')).to_contain_text('통화 중단')
    page.close()
    print('PASS: simulated webkit STT errors/start failure, starting lock, interim display, manual stop, typed-draft protection and one final submission')

    manual=create(browser,errors,elder=4,auto=False)
    wait_speech(manual,HEALTH)
    manual.get_by_role('button',name='말하기',exact=True).evaluate('(button)=>button.click()')
    assert manual.evaluate('window.__recognitionSessions.length')==0
    expect(manual.get_by_label('답변 입력')).to_be_disabled()
    complete_speech(manual)
    expect(manual.get_by_label('답변 입력')).to_be_enabled()
    # Re-renders from draft edits cannot replay the initial prompt.
    manual.get_by_label('답변 입력').fill('안 아파')
    manual.get_by_label('답변 입력').fill('')
    assert manual.evaluate('window.__tts.calls.length')==1
    manual.get_by_role('button',name='말하기',exact=True).click()
    manual.evaluate("window.__recognition.emitFinal('안 아파')")
    wait_speech(manual,'몸이 괜찮으시다니 다행이에요.')
    assert manual.evaluate('window.__recognition.aborted')
    manual.get_by_role('button',name='음성 끄기',exact=True).click()
    expect(manual.get_by_label('답변 입력')).to_be_enabled()
    assert manual.evaluate('window.__tts.pending===null')
    assert manual.evaluate('window.__tts.calls.length')==2
    expect(manual.locator('.input-question')).to_contain_text(MEAL)
    manual.get_by_role('button',name='음성 켜기',exact=True).click()
    assert manual.evaluate('window.__tts.calls.length')==2
    answer(manual,'밥 먹었어')
    wait_speech(manual,'식사를 챙겨 드셨군요. 알려주셔서 감사합니다.')
    manual.evaluate('()=>{ window.__lateEnd=window.__tts.pending.onend }')
    manual.get_by_role('button',name='통화 종료',exact=True).click()
    expect(manual.locator('.phone-ended')).to_contain_text('통화 중단')
    manual.evaluate('window.__lateEnd()')
    assert manual.evaluate('window.__tts.pending===null')
    assert len(detail(manual,4)['turns'])==2
    manual.close()
    print('PASS: simulated TTS blocks STT/input, cancels mic, does not repeat on renders, supports mute/unmute and safe mid-speech call end')

    listening=create(browser,errors,elder=4)
    expect(listening.get_by_label('답변 입력')).to_be_enabled()
    listening.get_by_role('button',name='말하기',exact=True).click()
    listening.evaluate('()=>{ window.__lateFinal=window.__recognition.onresult }')
    listening.get_by_role('button',name='통화 종료',exact=True).click()
    expect(listening.locator('.phone-ended')).to_contain_text('통화 중단')
    assert listening.evaluate('window.__recognition.aborted')
    listening.evaluate("window.__lateFinal({results:[Object.assign([{transcript:'늦은 답변'}],{isFinal:true})]})")
    assert detail(listening,4)['turns']==[]
    listening.close()
    print('PASS: call end aborts an active microphone and discards late results')

    # Observe loading with a delayed fetch, then actually stop and restart Uvicorn.
    network=create(browser,errors,elder=3)
    expect(network.get_by_label('답변 입력')).to_be_enabled()
    network.evaluate('''()=>{
      const nativeFetch=window.fetch;
      window.__holdAnswer=true;window.__answerRequests=0;
      window.fetch=(url,options)=>{
        if(options?.method==='POST'&&String(url).endsWith('/turns')){
          window.__answerRequests++;
          if(window.__holdAnswer)return new Promise((resolve,reject)=>{window.__releaseAnswer=()=>nativeFetch(url,options).then(resolve,reject)})
        }
        return nativeFetch(url,options)
      }
    }''')
    # Empty and IME-composing Enter must not submit.
    field=network.get_by_label('답변 입력')
    field.fill('   ');field.press('Enter')
    assert network.evaluate('window.__answerRequests')==0
    field.fill('안 아파')
    field.dispatch_event('compositionstart',{'data':'파'})
    field.dispatch_event('keydown',{'key':'Enter','code':'Enter','isComposing':True,'keyCode':229})
    assert network.evaluate('window.__answerRequests')==0
    field.dispatch_event('compositionend',{'data':'파'})
    field.press('Enter')
    expect(network.get_by_role('form',name='텍스트 답변')).to_have_attribute('aria-busy','true')
    expect(network.get_by_role('status').filter(has_text='답변을 저장하고 있습니다')).to_be_visible()
    expect(network.get_by_role('button',name='답변 보내기')).to_be_disabled()
    field.dispatch_event('keydown',{'key':'Enter','code':'Enter'})
    assert network.evaluate('window.__answerRequests')==1
    network.evaluate('window.__holdAnswer=false;window.__releaseAnswer()')
    expect_count(network,1)
    expect(network.get_by_label('답변 입력')).to_be_enabled()
    stop_backend()
    answer(network,'밥 안 먹었어')
    expect(network.get_by_role('alert')).to_contain_text('연결할 수 없습니다')
    expect(network.get_by_label('답변 입력')).to_have_value('밥 안 먹었어')
    expect(network.get_by_role('form',name='텍스트 답변')).to_have_attribute('aria-busy','false')
    expect_count(network,1)
    recover_backend()
    network.get_by_role('button',name='다시 시도',exact=True).click()
    expect_count(network,2)
    assert len(detail(network,3)['attempts'])==2
    complete_text(network,ANSWERS[2:],start=2)
    saved=detail(network,3)
    assert len(saved['turns'])==len(saved['attempts'])==5
    network.get_by_role('link',name='통화 기록',exact=True).first.click()
    network.reload()
    network.locator('tbody tr').first.get_by_role('button',name='보기').click()
    expect(network.get_by_role('dialog')).to_contain_text('밥 안 먹었어')
    network.close()
    print('PASS: IME/blank/duplicate submit guard and loading; real backend outage preserves input; server recovery safely retries and refreshed records persist')


def run_native_speech_check(browser,errors):
    """Do not replace SpeechRecognition or SpeechSynthesis in this page."""
    page=browser.new_page(viewport={'width':1440,'height':1100})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.add_init_script('''
      window.__nativeSpeechEvents=[];
      const Native=window.SpeechRecognition||window.webkitSpeechRecognition;
      if(Native){
        function ObservedRecognition(){
          const rec=new Native();window.__nativeRecognition=rec;
          for(const type of ['start','error','end','result'])rec.addEventListener(type,event=>window.__nativeSpeechEvents.push({type,error:event.error||null}));
          return rec;
        }
        if(window.SpeechRecognition)window.SpeechRecognition=ObservedRecognition;
        else window.webkitSpeechRecognition=ObservedRecognition;
      }
    ''')
    page.goto(URL+'/call/1')
    page.get_by_role('button',name='전화 받기',exact=True).click()
    expect(page.get_by_label('답변 입력')).to_be_enabled(timeout=65000)
    capabilities=page.evaluate('''async()=>({
      recognition:Boolean(window.SpeechRecognition||window.webkitSpeechRecognition),
      synthesis:Boolean(window.speechSynthesis),
      koreanVoices:window.speechSynthesis?.getVoices().filter(v=>v.lang.toLowerCase().startsWith('ko')).length||0,
      audioInputs:await navigator.mediaDevices.enumerateDevices().then(list=>list.filter(d=>d.kind==='audioinput').length).catch(()=>null)
    })''')
    page.get_by_role('button',name='말하기',exact=True).click()
    if capabilities['recognition']:
        try:page.wait_for_function("window.__nativeSpeechEvents.some(event=>['error','result','end'].includes(event.type))",timeout=12000)
        except Exception:pass
    result={**capabilities,'events':page.evaluate('window.__nativeSpeechEvents'),
            'koKR':page.evaluate("window.__nativeRecognition?.lang||null"),
            'sttMessage':page.locator('.speech-input-status').inner_text(),
            'ttsMessage':page.locator('.tts-notice').inner_text() if page.locator('.tts-notice').count() else None}
    if os.environ.get('ANSIMON_SCREENSHOT_DIR'):
        target=Path(os.environ['ANSIMON_SCREENSHOT_DIR']);target.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(target/'native-speech-fallback.png'),full_page=True)
    if page.get_by_role('button',name='말하기 중지',exact=True).count():
        page.get_by_role('button',name='말하기 중지',exact=True).click()
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    # Native browser text fallback uses actual FastAPI/SQLite through all questions.
    complete_text(page)
    saved=detail(page,1)
    assert len(saved['turns'])==5 and saved['status']=='completed'
    page.get_by_role('link',name='통화 기록',exact=True).first.click();page.reload()
    expect(page.locator('tbody tr').first).to_contain_text('완료')
    page.close()
    if os.environ.get('ANSIMON_NATIVE_REPORT'):
        report=Path(os.environ['ANSIMON_NATIVE_REPORT']);report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('NATIVE_BROWSER_OBSERVATION: '+json.dumps(result,ensure_ascii=False))
    print('PASS: native Chromium API attempt leaves text fallback usable; actual text-only five answers, completed records and refresh')
