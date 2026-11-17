"""모든 화면을 1440·1024·390에서 열어 스크린샷을 찍고, 가로 스크롤과 16px 미만 글자를 검사한다.

사용: python3 scripts/shots.py [기본주소=http://127.0.0.1:5180] [접두어=]
결과: screenshots/<접두어><화면>-<너비>.png, 문제는 표준 출력에 남기고 있으면 종료 코드 1.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5180"
PREFIX = sys.argv[2] if len(sys.argv) > 2 else ""
ONLY = sys.argv[3].split(",") if len(sys.argv) > 3 else None
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)

ROUTES = [
    ("landing", "/"),
    ("staff", "/staff"),
    ("call-detail", "/staff/calls/231"),
    ("live", "/staff/live"),
    ("residents", "/staff/residents"),
    ("calls", "/staff/calls"),
    ("rules", "/staff/rules"),
    ("principles", "/staff/principles"),
]
WIDTHS = [(1440, 900), (1024, 800), (390, 844)]

SCAN = """
() => {
  const small = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode;
    const t = n.textContent.trim();
    if (!t) continue;
    const el = n.parentElement;
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || el.closest('.sr,[aria-hidden="true"] .sr')) continue;
    const fs = parseFloat(cs.fontSize);
    if (fs < 16) small.push(`${fs}px <${el.tagName.toLowerCase()} class="${el.className}"> ${t.slice(0, 30)}`);
  }
  const de = document.documentElement;
  return { small: [...new Set(small)].slice(0, 20), sw: de.scrollWidth, cw: de.clientWidth };
}
"""

problems = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    for w, h in WIDTHS:
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, locale="ko-KR", timezone_id="Asia/Seoul")
        page = ctx.new_page()
        for name, path in ROUTES:
            if ONLY and name not in ONLY:
                continue
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(4500 if name == "landing" else 1800)
            res = page.evaluate(SCAN)
            if res["sw"] > res["cw"]:
                problems.append(f"[{w}] {name}: 가로 스크롤 {res['sw']} > {res['cw']}")
            for s in res["small"]:
                problems.append(f"[{w}] {name}: 작은 글자 {s}")
            if w != 1024:
                page.screenshot(path=str(OUT / f"{PREFIX}{name}-{w}.png"), full_page=True)
            print(f"ok {w} {name} scroll={res['sw']}/{res['cw']} small={len(res['small'])}")
        ctx.close()
    browser.close()

print("\n".join(problems) if problems else "문제 없음: 가로 스크롤 없음, 16px 미만 글자 없음")
sys.exit(1 if problems else 0)
