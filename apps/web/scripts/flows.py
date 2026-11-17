"""목업 모드에서 주요 동작을 눌러 본다: KPI 필터 · 확인 기록 · 전화 걸기→실시간 · 어르신 추가 · 다크 모드 · 데모 리셋.

사용: python3 scripts/flows.py [기본주소=http://127.0.0.1:5180]
"""
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5180"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
errors = []

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 900}, locale="ko-KR", timezone_id="Asia/Seoul")
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())

    page.goto(BASE + "/staff")
    expect(page.locator(".qi").first).to_be_visible()
    total = page.locator(".qi").count()
    # KPI 필터: 즉시 확인 → 1명, 다시 누르면 전체
    page.get_by_role("button", name="즉시 확인").first.click()
    expect(page.locator(".qi")).to_have_count(1)
    expect(page.locator(".kpi.on")).to_have_count(1)
    page.get_by_role("button", name="즉시 확인").first.click()
    expect(page.locator(".qi")).to_have_count(total)
    print("ok KPI 필터", total)

    # 카드 선택 → 패널 이름
    page.locator(".qi", has_text="김영자").click()
    expect(page.locator(".dpanel h3")).to_have_text("김영자 어르신")
    expect(page.locator(".week .c").first).to_be_visible()
    # 확인 기록 남기기
    page.locator(".dpanel").get_by_role("button", name="확인 기록 남기기").click()
    page.get_by_role("dialog").locator("textarea").fill("전화로 다시 여쭤 보니 죽을 조금 드셨대요.")
    page.get_by_role("dialog").get_by_role("button", name="기록 남기기").click()
    expect(page.locator(".k-ai.done")).to_be_visible(timeout=8000)
    print("ok 확인 기록")

    # 다크 모드
    page.get_by_role("button", name="어두운 화면으로").click()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.wait_for_timeout(700)
    page.screenshot(path=str(OUT / "staff-1440-dark.png"))
    page.get_by_role("button", name="밝은 화면으로").click()
    print("ok 다크 모드")

    # 전화 걸기 → 실시간 화면으로 이동, 벨 → 통화 중
    page.locator(".qi", has_text="오말녀").get_by_role("button", name="☎ 전화 걸기").click()
    page.wait_for_url("**/staff/live?call=*")
    expect(page.locator(".lane")).to_contain_text("오말녀 어르신")
    expect(page.locator(".lane .pill")).to_contain_text("실시간 연결", timeout=12000)
    expect(page.locator(".lane .bub").first).to_be_visible(timeout=10000)
    page.wait_for_timeout(6000)
    expect(page.locator(".lane .tx.arrive")).to_have_count(1, timeout=6000)
    page.screenshot(path=str(OUT / "live-1440-calling.png"))
    print("ok 전화 걸기 → 실시간")

    # 통화 상세: 확인 기록 표시
    page.goto(BASE + "/staff/calls/228")
    expect(page.locator(".st.safe")).to_be_visible()
    print("ok 통화 상세(안전 신호)")

    # 어르신 추가
    page.goto(BASE + "/staff/residents?new=1")
    d = page.get_by_role("dialog")
    d.get_by_label("이름").fill("문복례")
    d.get_by_label("나이").fill("81")
    d.get_by_label("지역(시도 + 시군구)").fill("대전광역시 중구")
    d.get_by_label("사는 곳(구·동)").fill("중구 선화동")
    d.get_by_role("button", name="추가하기").click()
    expect(page.locator(".rows.res")).to_contain_text("문복례")
    expect(page.locator(".rows.res")).to_contain_text("대전광역시 중구 선화동")
    print("ok 어르신 추가")

    # 데모 리셋
    page.get_by_role("button", name="데모 리셋").click()
    expect(page.locator(".rows.res")).not_to_contain_text("문복례", timeout=8000)
    print("ok 데모 리셋")
    b.close()

if errors:
    print("페이지 오류:", errors)
    sys.exit(1)
print("모든 동작 통과")
