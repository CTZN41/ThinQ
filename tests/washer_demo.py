"""Paid browser demo, synthetic comparison only. Leaves visible browser open."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=False)
    page=browser.new_page(viewport={'width':1440,'height':1050})
    requests=[]
    page.on('request',lambda r: requests.append(r.url) if r.method=='POST' else None)
    page.goto('http://127.0.0.1:8769/washer.html')
    page.locator('#experience').fill('이 모델로 물 온도 40도에서 40~50분 돌리니까 뽀송했어.')
    page.locator('#analyze').click()
    expect(page.locator('#progress')).to_contain_text('분석 완료',timeout=60000)
    facts=json.loads(page.locator('#facts').text_content())
    assert facts['temperature_c']==40
    assert facts['course'] is None and facts['drying_included'] is None
    assert '40' in facts['time_description'] and '50' in facts['time_description']
    assert all(url.endswith('/api/washer/analyze') for url in requests)
    page.screenshot(path='docs/screenshots/washer-transfer-demo.png',full_page=True)
    Path('docs/WASHER_DEMO_RESULT.json').write_text(json.dumps({'facts':facts,'execution_enabled':False,'actual_device_commands':0},ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: 40 C / time range preserved / unknown course and drying / no device command',flush=True)
    # Keep this development browser available for the user's inspection.
    while browser.is_connected() and not page.is_closed():
        page.wait_for_timeout(1000)
