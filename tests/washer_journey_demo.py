"""Opt-in paid Luna browser check; mock devices only."""
import json
import os
from playwright.sync_api import sync_playwright,expect
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=False)
 page=b.new_page(viewport={'width':1440,'height':1000})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(os.environ.get('WASHER_TEST_URL','http://127.0.0.1:8769/washer.html'))
 page.locator('#experience').fill('일반 면 의류를 표준 코스에서 수온 40도, 헹굼 3회, 탈수 강으로 세탁했어. 전체 40~50분 걸렸어.')
 page.locator('#analyze').click()
 expect(page.locator('#journey')).to_be_visible(timeout=90000)
 expect(page.locator('#progress')).to_contain_text('완료')
 expect(page.locator('#simulate')).to_be_disabled()
 page.locator('#hard_rinse').uncheck();page.locator('#hard_spin').uncheck()
 page.locator('#priority').select_option('fast');page.locator('#update').click()
 expect(page.locator('#candidates')).to_contain_text('헹굼 3 → 2')
 page.locator('.candidate').filter(has_text='일반 의류 단축 데모').get_by_role('button').click()
 expect(page.locator('#simulate')).to_be_enabled()
 page.locator('#simulate').click()
 expect(page.locator('#simulation')).to_contain_text('가상 세탁 시작')
 before=json.loads(page.locator('#selected').text_content())
 page.locator('#feedback').click()
 expect(page.locator('#accept')).to_be_visible()
 assert json.loads(page.locator('#selected').text_content())==before
 page.locator('#accept').click()
 expect(page.locator('#selected')).to_contain_text('medium')
 page.locator('#cardName').fill('데모 · 면 의류 경험');page.locator('#save').click()
 expect(page.locator('#saved')).to_contain_text('저장했어요')
 page.reload()
 page.locator('#cards button').filter(has_text='데모 · 면 의류 경험').first.click()
 expect(page.locator('#selected')).to_contain_text('medium')
 page.screenshot(path='docs/screenshots/washer-journey.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'mobile overflow'
 page.screenshot(path='docs/screenshots/washer-journey-mobile.png',full_page=True)
 page.set_viewport_size({'width':1440,'height':1000})
 assert not errors,errors
 print('PASS: '+('fixture extraction' if os.environ.get('WASHER_TEST_URL') else 'Luna extraction')+' / preferences / explicit choice / simulation / feedback acceptance / persisted reload / mobile',flush=True)
 while b.is_connected() and not page.is_closed():page.wait_for_timeout(1000)
