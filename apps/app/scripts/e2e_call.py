"""가짜 음성으로 전화 한 통을 끝까지 걸어 본다(가짜 API 모드).
확인: TTS가 끝나면 저절로 듣기 시작 · 10초 조용하면 source 'silence' · 버튼·글자 답 · TTS와 STT가 동시에 켜지지 않음.
실행: (npm run dev:mock 켠 뒤) python3 scripts/e2e_call.py [http://127.0.0.1:5181]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5181"
FAKE = (Path(__file__).resolve().parent / "fake_speech.js").read_text(encoding="utf-8")

# 듣기를 시작할 때마다 하나씩 쓴다(fake_speech.js 참고)
SCRIPT = [
    "몸은 괜찮아요",               # 1 몸: 말로 답
    "SILENT",                      # 2 식사: 크롬처럼 4초 뒤 no-speech → 앱이 조용히 다시 듣기
    "HOLD",                        #   … 10초가 되면 앱이 'silence'를 보냄
    "아침은 걸렀어. 입맛이 없어서.",  #   다시 물은 뒤 말로 답
    "HOLD",                        # 3 수면: 버튼으로 답
    "HOLD",                        # 4 약: 글자로 답
    "좋아요",                      # 5 기분: 말로 답 → 끝
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="ko-KR")
    ctx.add_init_script(FAKE)
    ctx.add_init_script("localStorage.setItem('ansimon.app.v2', JSON.stringify({residentId: 1, residentName: '김영자'}))")
    page = ctx.new_page()
    page.goto(BASE + "/")
    page.get_by_role("button", name="안심온과 통화하기").click()
    page.get_by_role("button", name="받기", exact=True).click(timeout=6000)
    page.evaluate(f"window.__say = {json.dumps(SCRIPT, ensure_ascii=False)}")

    page.get_by_role("button", name="조금 설쳤어요").wait_for(timeout=30000)  # 3 수면 질문까지 저절로 진행
    page.wait_for_timeout(800)
    page.get_by_role("button", name="조금 설쳤어요").click()
    page.get_by_role("button", name="아직 못 먹었어요").wait_for(timeout=8000)
    page.wait_for_timeout(800)
    page.get_by_role("button", name="글자로 답하기").click()
    page.get_by_label("답을 적는 칸").fill("아침 약은 먹었어요")
    page.get_by_role("button", name="보내기", exact=True).click()
    page.get_by_text("오늘도 고맙습니다").wait_for(timeout=15000)

    posts = page.evaluate("window.__ansimonMockLog")
    speech = page.evaluate("window.__speechLog")
    browser.close()

t0 = posts[0]["at"]
print("POST 순서:")
for e in posts:
    body = e.get("body")
    extra = f"  source={body['source']!r} text={body['text']!r}" if body else ""
    print(f"  +{(e['at'] - t0) / 1000:5.1f}s {e['req']}{extra}")

# TTS와 STT가 겹친 적이 있는지: tts-start~tts-end 사이에 stt가 켜져 있으면 안 된다
problems, tts_on, stt_on = [], False, False
for e in speech:
    ev = e["ev"]
    if ev == "tts-start":
        if stt_on:
            problems.append(f"t={e['t']} TTS started while STT active")
        tts_on = True
    elif ev == "tts-end":
        tts_on = False
    elif ev == "stt-start":
        if tts_on:
            problems.append(f"t={e['t']} STT started while TTS active")
        stt_on = True
    elif ev == "stt-stop":
        stt_on = False

# TTS가 끝난 뒤 저절로 듣기를 시작했는지
auto = sum(1 for a, b in zip(speech, speech[1:]) if a["ev"] == "tts-end" and b["ev"] == "stt-start" and b["t"] - a["t"] < 1500)
print("\n음성 순서:")
for e in speech:
    print(f"  {e['t']:>6}ms {e['ev']:<10} {e.get('text', '')[:40]} {('rate=' + str(e['rate'])) if 'rate' in e else ''}")
sources = [e["body"]["source"] for e in posts if e.get("body")]
print("\nsources:", sources)
print("TTS 끝 → 1.5초 안에 듣기 시작:", auto, "번")
silence = [e for e in posts if e.get("body", {}) and e["body"]["source"] == "silence"]
print("silence POST:", len(silence), "번")
print("겹침 문제:", problems or "없음")
ok = not problems and sources == ["stt", "silence", "stt", "option", "text", "stt"] and auto >= 5
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
