"""UI regression with deterministic session responses; no paid API or device calls."""
import json
from playwright.sync_api import sync_playwright, expect
from thinq_demo import washer_journey as j

with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':1000})
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.route('**/api/washer/cards',lambda route:route.fulfill(json={'cards':[]}))
    def flow(route):
        data=route.request.post_data_json
        if data['action']=='begin':
            response=j.create('F14WQT',dict(purpose=None,temperature_c=None,spin=None,spin_change='stronger',
                                          remembered_behavior='탈수 버튼을 한 번 더 눌렀어',request_kind='transfer'))
        else:
            response=j.act(data['session_id'],data['action'],data)
        route.fulfill(json=response)
    page.route('**/api/washer/flow',flow)
    page.goto('http://127.0.0.1:8769/washer.html')
    page.locator('#experience').fill('전에 쓰던 것처럼 하고 싶어')
    page.locator('#analyze').click()
    expect(page.locator('#questions')).to_contain_text('이번에는')
    assert not page.locator('#conditions').evaluate('(e)=>e.open')
    page.locator('#questions button').filter(has_text='운동복').click()
    page.locator('#questions button').filter(has_text='기억 안 나요').click()
    expect(page.locator('#questions')).to_contain_text('수온')
    page.locator('#questions button').filter(has_text='30℃').click()
    expect(page.locator('#summary')).to_contain_text('복원 아님')
    expect(page.locator('#candidates')).to_contain_text('코스 기본값')
    expect(page.locator('#candidates')).to_contain_text('세탁 → 헹굼 → 탈수 모두 포함')
    page.locator('#candidates button').first.click()
    expect(page.locator('#simulate')).to_be_enabled()
    page.locator('#simulate').click()
    expect(page.locator('#simulation')).to_contain_text('실제 세탁기는 작동하지 않아요')
    page.screenshot(path='docs/screenshots/washer-adaptation.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path='docs/screenshots/washer-adaptation-mobile.png',full_page=True)
    assert not errors,errors
    browser.close()
    print('PASS: one question, unknown spin, explicit new temperature, simulation, mobile layout')
