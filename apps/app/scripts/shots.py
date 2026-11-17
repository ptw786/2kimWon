"""가짜 API(VITE_MOCK=1) 화면을 두 크기(390×844, 소개 페이지 iframe 330×700)로 찍고 검사한다.
검사: 가로 스크롤 없음 · 기본 글자 크기에서 20px 미만 글자 없음 · 통화 화면 버튼 72px 이상.
실행: (앱 폴더에서 `npm run dev:mock` 켠 뒤) python3 scripts/shots.py [http://127.0.0.1:5181]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5181"
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "screenshots"
FAKE = (HERE / "fake_speech.js").read_text(encoding="utf-8")
SIZES = [("390x844", 390, 844), ("330x700", 330, 700)]

CHECK_JS = """
(minPx) => {
  const de = document.documentElement
  const problems = []
  if (de.scrollWidth > de.clientWidth + 1) problems.push(`page scrollWidth ${de.scrollWidth} > ${de.clientWidth}`)
  for (const el of document.querySelectorAll('.scroll, .pad, .dock, .ring, .sheet, .dialog')) {
    if (el.scrollWidth > el.clientWidth + 1) problems.push(`${el.className} scrollWidth ${el.scrollWidth} > ${el.clientWidth}`)
  }
  const small = new Set()
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  while (walker.nextNode()) {
    const node = walker.currentNode
    if (!node.textContent.trim()) continue
    const el = node.parentElement
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el)
    if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden' || cs.display === 'none') continue
    const size = parseFloat(cs.fontSize)
    if (size < minPx - 0.01) small.add(`${size}px "${node.textContent.trim().slice(0, 20)}"`)
  }
  for (const s of small) problems.push('small text ' + s)
  const short = []
  for (const el of document.querySelectorAll('.call .opt button, .call .listen, .call .btn-text, .call .btn-hang, .dialog .btn, .sheet .btn')) {
    const h = el.getBoundingClientRect().height
    if (h > 0 && h < 72) short.push(`${el.className || el.textContent.trim()} ${Math.round(h)}px`)
  }
  for (const el of document.querySelectorAll('.circle')) {
    const w = el.getBoundingClientRect().width
    if (w < 100) short.push(`circle ${w}px`)
  }
  for (const s of short) problems.push('short button ' + s)
  return problems
}
"""

report: dict[str, list[str]] = {}


def shot(page: Page, tag: str, name: str, check: bool = True) -> None:
    page.wait_for_timeout(250)
    page.screenshot(path=str(OUT / f"{tag}-{name}.png"))
    if check:
        report[f"{tag}-{name}"] = page.evaluate(CHECK_JS, 20)


def run(tag: str, w: int, h: int, browser) -> None:
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, locale="ko-KR", has_touch=True)
    ctx.add_init_script(FAKE)
    page = ctx.new_page()
    page.goto(BASE + "/")
    page.get_by_text("어느 어르신").wait_for()
    shot(page, tag, "01-picker")
    page.get_by_role("button", name="김영자 어르신").click()
    page.get_by_text("안심온과 통화하기").wait_for()
    page.wait_for_timeout(600)
    shot(page, tag, "02-home")

    page.get_by_role("button", name="안심온과 통화하기").click()
    page.get_by_text("전화가 왔어요").wait_for(timeout=6000)
    shot(page, tag, "03-ring")

    page.evaluate("window.__say = ['HOLD', 'INTERIM:아침은 걸렀어. 입맛이 없어서.']")
    page.get_by_role("button", name="받기", exact=True).click()
    page.get_by_role("button", name="괜찮아요").wait_for()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="괜찮아요").click()
    page.get_by_text("들은 말 (듣는 중)").wait_for(timeout=5000)
    page.wait_for_timeout(300)
    shot(page, tag, "04-call")

    page.get_by_role("button", name="끊기").click()
    page.get_by_text("전화를 끊을까요?").wait_for()
    shot(page, tag, "05-hangup-confirm")
    page.get_by_role("button", name="계속 이야기하기").click()

    page.get_by_role("button", name="글자로 답하기").click()
    page.get_by_label("답을 적는 칸").fill("아침은 걸렀어요")
    shot(page, tag, "05b-text-sheet")
    page.get_by_role("button", name="보내기", exact=True).click()
    for option in ["조금 설쳤어요", "네, 먹었어요", "좋아요"]:
        page.get_by_role("button", name=option, exact=True).wait_for(timeout=5000)
        page.wait_for_timeout(200)
        page.get_by_role("button", name=option, exact=True).click()
    page.get_by_text("오늘도 고맙습니다").wait_for(timeout=8000)
    shot(page, tag, "06-done")

    page.get_by_role("button", name="처음 화면으로").click()
    page.get_by_text("에 전화드려요").wait_for()
    page.wait_for_timeout(400)
    shot(page, tag, "06b-home-after")
    page.get_by_role("link", name="내 기록").click()
    page.get_by_text("오늘", exact=True).wait_for()
    shot(page, tag, "07-records")

    page.get_by_role("link", name="설정").click()
    page.get_by_text("글자 크기").wait_for()
    shot(page, tag, "08-settings-large")
    page.get_by_role("radio", name="아주 크게").click()
    shot(page, tag, "09-settings-xlarge", check=False)
    report[f"{tag}-09-settings-xlarge"] = [p for p in page.evaluate(CHECK_JS, 20) if not p.startswith("short")]
    page.get_by_role("link", name="거실").click()
    shot(page, tag, "10-home-xlarge", check=False)
    report[f"{tag}-10-home-xlarge"] = page.evaluate(CHECK_JS, 20)
    ctx.close()

    # 마이크를 못 쓰는 폰(iOS 사파리, 권한 없는 iframe 등): 버튼·글자로만 끝까지
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, locale="ko-KR")
    ctx.add_init_script("window.__noMic = true; delete window.webkitSpeechRecognition; delete window.SpeechRecognition;")
    ctx.add_init_script(FAKE)
    ctx.add_init_script("localStorage.setItem('ansimon.app.v2', JSON.stringify({residentId: 1, residentName: '김영자'}))")
    page = ctx.new_page()
    page.goto(BASE + "/")
    page.get_by_role("button", name="안심온과 통화하기").click()
    page.get_by_role("button", name="받기", exact=True).click(timeout=6000)
    page.get_by_text("마이크를 쓸 수 없어요").wait_for()
    page.get_by_role("button", name="괜찮아요").wait_for()
    page.wait_for_timeout(500)
    shot(page, tag, "11-call-nomic")
    ctx.close()

    # 못 받은 전화: 알림은 장면의 말풍선에 — 아래 판의 큰 버튼이 탭에 가리지 않아야 한다
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, locale="ko-KR")
    ctx.add_init_script(FAKE)
    ctx.add_init_script("localStorage.setItem('ansimon.app.v2', JSON.stringify({residentId: 1, residentName: '김영자'})); sessionStorage.setItem('ansimon.mock.ringMs', '1500')")
    page = ctx.new_page()
    page.goto(BASE + "/")
    page.get_by_role("button", name="안심온과 통화하기").click()
    page.get_by_text("전화가 왔어요").wait_for(timeout=6000)
    page.get_by_text("안심온 알림").wait_for(timeout=10000)
    page.wait_for_timeout(400)
    shot(page, tag, "12-home-missed")
    covered = page.evaluate("""() => {
      const tab = document.querySelector('.tabbar').getBoundingClientRect().top
      return [...document.querySelectorAll('.lv-panel > *')].filter(e => e.getBoundingClientRect().bottom > tab + 1).map(e => e.className || e.tagName)
    }""")
    report[f"{tag}-12-home-missed"] += [f"under tab bar: {c}" for c in covered]
    ctx.close()


OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    for tag, w, h in SIZES:
        run(tag, w, h, browser)
    browser.close()

print(json.dumps(report, ensure_ascii=False, indent=1))
bad = {k: v for k, v in report.items() if v}
print("PROBLEMS:", len(bad))
