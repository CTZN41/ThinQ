"""Opt-in paid visible browser test; synthetic washer only."""
from playwright.sync_api import sync_playwright,expect
import json
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=False)
 page=b.new_page(viewport={'width':1440,'height':1050})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8769/washer.html')
 page.locator('#experience').fill('일반 면 의류를 표준 코스, 수온 40도로 세탁했고 전체 소요 시간이 40~50분이었어.')
 page.locator('#analyze').click()
 expect(page.locator('#progress')).to_contain_text('분석 완료',timeout=60000)
 expect(page.locator('#simulate')).to_be_disabled()
 expect(page.locator('#questions')).to_contain_text('동등한 후보')
 page.locator('#experience').fill('일반 면 의류를 표준 코스에서 수온 40도, 헹굼 3회로 세탁했어. 세탁부터 탈수까지 전체 40~50분 걸렸고 뽀송했어. 양은 고려하지 마.')
 page.locator('#analyze').click()
 expect(page.locator('#simulate')).to_be_enabled(timeout=60000)
 facts=json.loads(page.locator('#facts').text_content())
 assert facts['temperature_c']==40 and facts['rinse_count']==3
 expect(page.locator('#rows')).to_contain_text('일반 의류 데모')
 expect(page.locator('#rows')).to_contain_text('5분 차이')
 page.locator('#simulate').click()
 expect(page.locator('#simulation')).to_contain_text('가상 세탁 시작',timeout=10000)
 expect(page.locator('#simulation')).to_contain_text('standard')
 page.screenshot(path='docs/screenshots/washer-match-simulation.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'
 page.set_viewport_size({'width':1440,'height':1050})
 assert not errors,errors
 print('PASS: tie held / rinse constraint / 40C preserved / time gap 5 / synthetic start / mobile',flush=True)
 while b.is_connected() and not page.is_closed():page.wait_for_timeout(1000)
