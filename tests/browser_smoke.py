"""Optional browser check against a running MOCK server; never run against LIVE."""
import json
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8765"
if json.load(urlopen(BASE + "/api/config"))["mode"] != "MOCK":
    raise SystemExit("Browser test only supports MOCK mode")

output = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
output.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    expect(page.locator(".device")).to_have_count(7)
    page.get_by_role("button", name="거실 에어컨", exact=False).click()
    expect(page.locator("form.control")).to_have_count(2)
    temperature = page.locator("form.control").filter(has=page.locator("input[type=number]"))
    temperature.locator("input").fill("24.5")
    select = page.locator('form.control select')
    select.select_option(index=2)
    page.get_by_role("button", name="설정 적용", exact=True).click()
    expect(page.locator("#result")).to_contain_text('변경 후: 24.5')
    page.screenshot(path=str(output / "desktop.png"), full_page=True)
    page.get_by_role("button", name="연결 끊긴 청정기", exact=False).click()
    expect(page.locator("#applySettings")).to_be_disabled()
    page.get_by_role("button", name="미지원 형식 제품", exact=False).click()
    expect(page.locator("#detail")).to_contain_text("현재 사용할 수 있는 제어 항목이 없습니다")
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("button", name="냉장고", exact=False).click()
    expect(page.locator("form.control")).to_have_count(2)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Horizontal overflow"
    page.screenshot(path=str(output / "mobile.png"), full_page=True)
    assert not errors, errors
    browser.close()
print("Browser smoke PASS: combined apply, offline, unknown profile, mobile layout, no JS errors")
