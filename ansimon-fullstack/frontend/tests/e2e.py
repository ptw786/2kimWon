"""Live Uvicorn + Vite + Chromium regression checks. Uses a temporary database."""
import json
import os
from pathlib import Path
import subprocess
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
# Support the documented backend/.venv and the existing root .venv layout.
_python_tail=Path('Scripts/python.exe' if os.name=='nt' else 'bin/python')
_candidates=[ROOT/'backend'/'.venv'/_python_tail,ROOT/'.venv'/_python_tail]
PYTHON=os.environ.get('ANSIMON_PYTHON') or next((str(path) for path in _candidates if path.is_file()),sys.executable)
URL = 'http://127.0.0.1:5173'


def wait_server(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Server exited: {process.returncode}')
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(.1)
    raise RuntimeError(f'Server did not start: {url}')


def assert_audio_closed(page):
    page.wait_for_function("window.__audio.every(r=>r.context.state==='closed'&&r.oscillators.every(n=>n.stopped===1&&n.disconnected===1))")


def run_extra_scenarios(browser,page,errors):
    page.get_by_role('button',name='닫기',exact=True).click()
    for bad in ('abc','0','-1','1.5','999'):
        page.goto(URL+'/call/'+bad)
        expect(page.get_by_role('alert')).to_be_visible()
        expect(page.get_by_role('button',name='전화 받기',exact=True)).to_have_count(0)
        assert page.evaluate('window.__audio.length')==0
    page.goto(URL+'/unknown')
    expect(page.get_by_role('heading',name='페이지를 찾을 수 없습니다')).to_be_visible()
    print('PASS: malformed and missing elder IDs and unknown route')

    # Inject an autoplay block while still using real Chromium AudioContexts.
    fresh=browser.new_page(viewport={'width':390,'height':844})
    fresh.add_init_script('window.__simulateAutoplayBlock=true;\n'+(ROOT/'frontend/tests/audio_probe.js').read_text())
    fresh.on('pageerror',lambda error:errors.append(str(error)))
    fresh.goto(URL+'/call/2')
    enable=fresh.get_by_role('button',name='벨소리 켜기',exact=True)
    expect(enable).to_be_visible()
    assert fresh.evaluate("window.__audio[0].context.state")=='suspended'
    fresh.evaluate('window.__allowRingtoneResume=true')
    enable.click()
    fresh.wait_for_function("window.__audio[0].context.state==='running'")
    expect(fresh.get_by_text('전화가 울리고 있어요',exact=True)).to_be_visible()
    # Router re-render and another cadence must reuse the same context/nodes.
    fresh.evaluate("history.pushState({},'', '/call/2?render=1');window.dispatchEvent(new PopStateEvent('popstate'))")
    fresh.wait_for_function('window.__audio[0].levels.length>10',timeout=6000)
    assert fresh.evaluate('window.__audio.length')==1
    assert fresh.evaluate('window.__audio[0].oscillators.length')==2
    assert fresh.evaluate('Math.max(...window.__audio[0].levels)')<=.045
    assert fresh.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    for name in ('전화 받기','수신 거절'):
        button=fresh.get_by_role('button',name=name,exact=True)
        box=button.bounding_box()
        assert box['width']>=90 and box['height']>=90
    screenshot=os.environ.get('ANSIMON_SCREENSHOT_DIR')
    if screenshot:
        Path(screenshot).mkdir(parents=True,exist_ok=True)
        fresh.screenshot(path=str(Path(screenshot)/'incoming-mobile.png'),full_page=True)
    fresh.get_by_role('button',name='수신 거절',exact=True).evaluate('(button)=>{button.click();button.click()}')
    expect(fresh.locator('.phone-ended')).to_contain_text('수신 거절')
    assert_audio_closed(fresh)
    declined=fresh.request.get(URL+'/api/calls?resident_id=2').json()
    assert len(declined)==1 and declined[0]['status']=='declined'
    fresh.get_by_role('button',name='다시 전화받기',exact=True).click()
    expect(fresh.get_by_role('button',name='전화 받기',exact=True)).to_be_enabled()
    fresh.get_by_role('link',name='통화 기록',exact=True).click()
    expect(fresh).to_have_url(URL+'/records')
    assert_audio_closed(fresh)
    print('PASS: injected autoplay restriction with native audio, manual enable, cadence/re-render singleton, quiet volume, large mobile controls, decline/reset/navigation cleanup')

    page.goto(URL+'/call/3')
    page.get_by_role('button',name='전화 받기',exact=True).evaluate('(button)=>{button.click();button.click()}')
    expect(page.get_by_label('답변 입력')).to_be_enabled()
    assert_audio_closed(page)
    assert len(page.request.get(URL+'/api/calls?resident_id=3').json())==1
    page.get_by_label('답변 입력').fill('몸이 괜찮아요')
    page.get_by_label('답변 입력').press('Enter')
    expect(page.locator('.step-indicator')).to_have_text('1 / 5')
    if screenshot:
        page.screenshot(path=str(Path(screenshot)/'active-desktop.png'),full_page=True)
    page.get_by_role('link',name='통화 기록',exact=True).click()
    expect(page).to_have_url(URL+'/records')
    page.wait_for_function("![...window.__intervals.values()].some(name=>['tick','pulse'].includes(name))")
    assert_audio_closed(page)
    page.go_back()
    expect(page.locator('.step-indicator')).to_have_text('1 / 5')
    page.get_by_role('button',name='통화 종료',exact=True).click()
    expect(page.locator('.phone-ended')).to_contain_text('통화 중단')
    assert_audio_closed(page)
    interrupted=page.request.get(URL+'/api/calls?resident_id=3').json()
    assert len(interrupted)==1 and interrupted[0]['status']=='interrupted'
    print('PASS: rapid double accept creates one call; answer and interrupted finish persist')

    page.add_init_script('window.__holdQuestions=true')
    page.goto(URL+'/call/4')
    expect(page.get_by_role('status')).to_contain_text('불러오는 중')
    page.get_by_role('link',name='통화 기록',exact=True).click()
    expect(page).to_have_url(URL+'/records')
    page.wait_for_function('window.__abortedRequests>0')
    assert_audio_closed(page)
    page.evaluate('window.__holdQuestions=false')
    expect(page.locator('tbody tr')).to_have_count(3)
    page.reload()
    expect(page).to_have_url(URL+'/records')
    expect(page.locator('tbody tr')).to_have_count(3)
    print('PASS: navigation aborts pending API work; records URL reload persists completed/declined/interrupted calls')

    unsupported=browser.new_page()
    unsupported.add_init_script('window.AudioContext=undefined;window.webkitAudioContext=undefined')
    unsupported.goto(URL+'/call/4')
    expect(unsupported.get_by_text('이 브라우저에서는 벨소리를 사용할 수 없어요.',exact=False)).to_be_visible()
    expect(unsupported.get_by_role('button',name='전화 받기',exact=True)).to_be_enabled()
    unsupported.close();fresh.close()
    failure=browser.new_page()
    failure.add_init_script(path=str(ROOT/'frontend/tests/audio_probe.js'))
    failure.on('pageerror',lambda error:errors.append(str(error)))
    failure.route('**/api/questions',lambda route:route.fulfill(status=500,content_type='application/json',body=json.dumps({'detail':'테스트용 질문 조회 오류'})))
    failure.goto(URL+'/call/4')
    expect(failure.get_by_role('alert')).to_contain_text('테스트용 질문 조회 오류')
    assert failure.evaluate('window.__audio.length')==0
    failure.unroute('**/api/questions')
    failure.get_by_role('button',name='다시 시도',exact=True).click()
    expect(failure.get_by_role('button',name='전화 받기',exact=True)).to_be_enabled()
    def lose_start(route):
        route.fetch();route.abort()
    failure.route('**/api/residents/4/calls',lose_start,times=1)
    failure.get_by_role('button',name='전화 받기',exact=True).click()
    expect(failure.get_by_role('alert')).to_contain_text('연결할 수 없습니다')
    failure.get_by_role('button',name='다시 시도',exact=True).click()
    expect(failure.get_by_label('답변 입력')).to_be_enabled()
    assert_audio_closed(failure)
    assert len(failure.request.get(URL+'/api/calls?resident_id=4').json())==1
    failure.get_by_role('button',name='통화 종료',exact=True).click()
    expect(failure.locator('.phone-ended')).to_contain_text('통화 중단')
    failure.close()
    print('PASS: call loading API 500 retry and lost start response recovery without duplicate calls')
    print('PASS: unsupported Web Audio gives explanation without blocking receive controls')


def main():
    # Never run against an already running app or its real database.
    for port in (8000, 5173):
        try:
            with socket.create_connection(('127.0.0.1',port), timeout=.2):
                pass
        except OSError:
            continue
        raise RuntimeError(f'Port {port} is occupied. Stop your local server before testing.')
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, 'ANSIMON_DB': str(Path(tmp) / 'e2e.db'), 'PYTHONTZPATH':''}
        with open(Path(tmp) / 'servers.log', 'w+') as log:
            backend = None
            frontend = subprocess.Popen(['node',str(ROOT/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1'], cwd=ROOT/'frontend', env=env, stdout=log, stderr=log)
            def start_backend():
                proc = subprocess.Popen([PYTHON,'-m','uvicorn','main:app','--host','127.0.0.1','--port','8000'], cwd=ROOT/'backend', env=env, stdout=log, stderr=log)
                try:
                    wait_server('http://127.0.0.1:8000/api/health', proc)
                except Exception:
                    proc.terminate();proc.wait(timeout=10)
                    raise
                return proc
            try:
                wait_server(URL, frontend)
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True,args=['--autoplay-policy=document-user-activation-required'])
                    http500=[]
                    original_new_page=browser.new_page
                    def observed_page(*args,**kwargs):
                        created=original_new_page(*args,**kwargs)
                        def observe(response):
                            if response.status!=500:return
                            try:message=response.json().get('detail','')
                            except Exception:message='non-JSON HTTP 500'
                            http500.append({'url':response.url,'detail':message,'injected':isinstance(message,str) and message.startswith('테스트용')})
                        created.on('response',observe)
                        return created
                    browser.new_page=observed_page
                    page = browser.new_page(viewport={'width':1440,'height':1000})
                    page.add_init_script(path=str(ROOT/'frontend/tests/audio_probe.js'))
                    errors=[]
                    page.on('pageerror', lambda error:errors.append(str(error)))
                    page.goto(URL)
                    expect(page.get_by_role('alert')).to_contain_text('FastAPI에 연결할 수 없습니다')
                    assert page.request.get(URL+'/api/residents').status == 502
                    print('PASS: actual stopped-backend proxy returns 502 with explanation')
                    backend = start_backend()
                    requests=[]
                    page.on('request', lambda req:requests.append(req.url))
                    page.get_by_role('button',name='다시 시도',exact=True).click()
                    expect(page.locator('tbody tr')).to_have_count(4)
                    expect(page.get_by_role('alert')).to_have_count(0)
                    assert any('/api/dashboard' in u for u in requests)
                    assert any('/api/residents' in u for u in requests)
                    print('PASS: backend startup, resident list and real retry requests')
                    # Fault injection verifies that a dashboard-only failure cannot hide DB records.
                    page.route('**/api/dashboard',lambda route:route.fulfill(status=500,content_type='application/json',body=json.dumps({'detail':'테스트용 대시보드 장애'})))
                    page.get_by_role('button',name='새로고침',exact=True).click()
                    expect(page.get_by_role('alert')).to_contain_text('테스트용 대시보드 장애')
                    expect(page.locator('tbody tr')).to_have_count(4)
                    page.unroute('**/api/dashboard')
                    page.get_by_role('button',name='다시 시도',exact=True).click()
                    expect(page.get_by_role('alert')).to_have_count(0)
                    print('PASS: independent resident loading during injected dashboard 500')
                    page.get_by_role('button',name='전화 체험',exact=True).first.click()
                    expect(page).to_have_url(URL+'/call/1')
                    expect(page.locator('.sidebar')).to_have_count(0)
                    expect(page.get_by_role('heading',name='안심온 돌봄전화')).to_be_visible()
                    page.wait_for_function("window.__audio.length===1")
                    if page.get_by_role('button',name='벨소리 켜기').count():
                        page.get_by_role('button',name='벨소리 켜기').click()
                    page.wait_for_function("window.__audio[0].context.state==='running'")
                    page.get_by_role('button',name='전화 받기',exact=True).click()
                    page.wait_for_function("window.__audio.every(r=>r.context.state==='closed'&&r.oscillators.every(n=>n.stopped===1&&n.disconnected===1))")
                    print('PASS: elder route, real Web Audio ringtone and accept cleanup')
                    expect(page.get_by_label('답변 입력')).to_be_enabled()
                    def answer(text):
                        field=page.get_by_label('답변 입력')
                        expect(field).to_be_enabled()
                        field.fill(text)
                        field.press('Enter')
                    page.wait_for_function("document.querySelector('[aria-label=\"통화 시간\"]').textContent!=='00:00'")
                    answer('몸 상태 좋아요')
                    expect(page.locator('.step-indicator')).to_have_text('1 / 5')
                    page.reload()
                    expect(page).to_have_url(URL+'/call/1')
                    expect(page.locator('.step-indicator')).to_have_text('1 / 5')
                    answer('식사했어요')
                    expect(page.locator('.step-indicator')).to_have_text('2 / 5')
                    answer('잘 잤어요')
                    expect(page.locator('.step-indicator')).to_have_text('3 / 5')
                    answer('약 먹었어요')
                    expect(page.locator('.step-indicator')).to_have_text('4 / 5')
                    # Lose a finish response after the server has committed: retry must be safe.
                    def lose_finish(route):
                        route.fetch()
                        route.abort()
                    page.route('**/api/calls/*/finish',lose_finish,times=1)
                    answer('기분 좋아요')
                    expect(page.get_by_role('alert')).to_contain_text('연결할 수 없습니다')
                    expect(page.locator('.step-indicator')).to_have_text('5 / 5')
                    page.locator('.phone-end button').click()
                    expect(page.locator('.phone-ended')).to_contain_text('안부 확인 완료')
                    page.get_by_role('link',name='통화 기록',exact=True).first.click()
                    expect(page.locator('tbody tr')).to_have_count(1)
                    expect(page.locator('tbody tr')).to_contain_text('완료')
                    records=page.request.get(URL+'/api/calls').json()
                    cid=records[0]['id']
                    detail=page.request.get(URL+f'/api/calls/{cid}').json()
                    assert len(detail['turns'])==5 and detail['status']=='completed'
                    assert detail['summary'].startswith('건강 상태: 몸 상태 좋아요')
                    print('PASS: start, answers, in-call reload recovery, committed finish retry, saved summary/detail')
                    page.reload()
                    page.get_by_role('link',name='통화 기록',exact=True).first.click()
                    expect(page.locator('tbody tr')).to_have_count(1)
                    page.get_by_role('button',name='보기',exact=True).click()
                    expect(page.get_by_role('dialog')).to_contain_text('기분 좋아요')
                    backend.terminate();backend.wait(timeout=10)
                    backend=start_backend()
                    assert page.request.get(URL+f'/api/calls/{cid}').json()==detail
                    run_extra_scenarios(browser,page,errors)
                    from conversation_scenarios import run_conversation_scenarios
                    run_conversation_scenarios(browser,errors)
                    from hybrid_scenarios import run_hybrid_scenarios
                    run_hybrid_scenarios(browser,errors)
                    from speech_input_scenarios import run_speech_input_scenarios,run_native_speech_check
                    def stop_backend():
                        nonlocal backend
                        backend.terminate();backend.wait(timeout=10)
                    def recover_backend():
                        nonlocal backend
                        backend=start_backend()
                    run_speech_input_scenarios(browser,errors,stop_backend,recover_backend)
                    run_native_speech_check(browser,errors)
                    from unified_scenarios import run_unified_scenarios
                    run_unified_scenarios(browser,errors,Path(env['ANSIMON_DB']))
                    from final_scenarios import run_timeout_recovery,audit_sqlite
                    run_timeout_recovery(browser,errors)
                    audit_sqlite(Path(env['ANSIMON_DB']))
                    assert len(http500)==4,http500
                    assert all(record['injected'] for record in http500),http500
                    print('HTTP_500_AUDIT: '+json.dumps({'injected':len(http500),'unexpected':0},ensure_ascii=False))
                    print('PASS: every browser HTTP 500 is an explicit injected fault; no unexpected normal-flow HTTP 500')
                    assert not errors, errors
                    print('PASS: browser refresh and backend restart retain records; no browser JS errors')
                    browser.close()
            except Exception:
                log.flush();log.seek(0);print(log.read(),file=sys.stderr)
                raise
            finally:
                for proc in (backend,frontend):
                    if proc and proc.poll() is None:
                        proc.terminate()
                        try:proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:proc.kill();proc.wait()

if __name__ == '__main__':
    main()
