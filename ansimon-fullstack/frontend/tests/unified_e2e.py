"""Fast standalone runner for unified scheduling UI; uses an isolated database."""
import os
from pathlib import Path
import socket
import subprocess
import tempfile
from playwright.sync_api import sync_playwright
from e2e import ROOT,PYTHON,URL,wait_server
from unified_scenarios import run_unified_scenarios


def main():
 for port in (8000,5173):
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):pass
  except OSError:continue
  raise RuntimeError(f'Port {port} is occupied; stop your app before testing.')
 with tempfile.TemporaryDirectory() as tmp:
  env={**os.environ,'ANSIMON_DB':str(Path(tmp)/'unified.db')}
  with open(Path(tmp)/'servers.log','w+') as log:
   processes=[]
   try:
    backend=subprocess.Popen([PYTHON,'-m','uvicorn','main:app','--host','127.0.0.1','--port','8000'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log);processes.append(backend)
    frontend=subprocess.Popen(['node',str(ROOT/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1'],cwd=ROOT/'frontend',env=env,stdout=log,stderr=log);processes.append(frontend)
    wait_server('http://127.0.0.1:8000/api/health',backend);wait_server(URL,frontend)
    with sync_playwright() as p:
     browser=p.chromium.launch(headless=True,args=['--autoplay-policy=document-user-activation-required'])
     errors=[]
     run_unified_scenarios(browser,errors,Path(env['ANSIMON_DB']))
     assert not errors,errors
     browser.close()
   except Exception:
    log.flush();log.seek(0);print(log.read());raise
   finally:
    for process in processes:
     process.terminate()
     try:process.wait(timeout=10)
     except subprocess.TimeoutExpired:process.kill();process.wait()

if __name__=='__main__':main()
