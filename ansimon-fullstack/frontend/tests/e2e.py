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
PYTHON = os.environ.get('ANSIMON_PYTHON', str(ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')))
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
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page(viewport={'width':1440,'height':1000})
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
                    assert any('/api/calls' in u for u in requests)
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
                    page.get_by_role('button',name='전화 받기',exact=True).click()
                    expect(page.get_by_label('답변 입력')).to_be_enabled()
                    def answer(text):
                        field=page.get_by_label('답변 입력')
                        expect(field).to_be_enabled()
                        field.fill(text)
                        field.press('Enter')
                    answer('몸 상태 좋아요')
                    expect(page.locator('.step-indicator')).to_have_text('1 / 5')
                    page.reload()
                    expect(page.locator('tbody tr')).to_have_count(4)
                    page.get_by_role('button',name='전화 체험',exact=True).first.click()
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
                    page.locator('.sidebar').get_by_role('button',name='통화 기록',exact=True).click()
                    expect(page.locator('tbody tr')).to_have_count(1)
                    expect(page.locator('tbody tr')).to_contain_text('완료')
                    records=page.request.get(URL+'/api/calls').json()
                    cid=records[0]['id']
                    detail=page.request.get(URL+f'/api/calls/{cid}').json()
                    assert len(detail['turns'])==5 and detail['status']=='completed'
                    assert detail['summary'].startswith('몸 상태: 몸 상태 좋아요')
                    print('PASS: start, answers, in-call reload recovery, committed finish retry, saved summary/detail')
                    page.reload()
                    page.locator('.sidebar').get_by_role('button',name='통화 기록',exact=True).click()
                    expect(page.locator('tbody tr')).to_have_count(1)
                    page.get_by_role('button',name='보기',exact=True).click()
                    expect(page.get_by_role('dialog')).to_contain_text('기분 좋아요')
                    backend.terminate();backend.wait(timeout=10)
                    backend=start_backend()
                    assert page.request.get(URL+f'/api/calls/{cid}').json()==detail
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
