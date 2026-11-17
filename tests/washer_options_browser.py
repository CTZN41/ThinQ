"""Paid live extraction, mock washer option ablation; no real controls."""
from playwright.sync_api import sync_playwright,expect
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=False)
 page=b.new_page(viewport={'width':1280,'height':980})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8769/washer.html')
 page.locator('#experience').fill('일반 면 의류를 40도, 헹굼 3회로 전체 40~50분 세탁했어. 세탁은 그대로 진행했는데 탈수를 좀 쎄게 하니까 냄새가 잘 안나고 잘 말랐어.')
 page.locator('#analyze').click()
 expect(page.locator('#questions')).to_contain_text('어떤 단계',timeout=60000)
 expect(page.locator('#spin')).to_have_value('')
 for key in ['hard_temp','hard_rinse','hard_spin']:
  page.locator('#'+key).uncheck()
  page.locator('#update').click()
  expect(page.locator('#questions')).to_contain_text('어떤 단계')
  expect(page.locator('#simulate')).not_to_be_visible()
 page.locator('#spin').select_option('high')
 page.locator('#update').click()
 expect(page.locator('#questions')).not_to_contain_text('어떤 단계')
 page.locator('#candidates button').first.click()
 expect(page.locator('#simulate')).to_be_enabled()
 expect(page.locator('#candidates')).to_contain_text('탈수 강')
 page.screenshot(path='docs/screenshots/washer-option-check.png',full_page=True)
 assert not errors,errors
 print('PASS: relative question stays through each disabled lock; explicit spin enables selected method',flush=True)
 while b.is_connected() and not page.is_closed():page.wait_for_timeout(1000)
