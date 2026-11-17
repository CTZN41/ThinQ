"""Explicit paid UI demonstration against MOCK only."""
from playwright.sync_api import sync_playwright, expect

BASE='http://127.0.0.1:8767'
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True)
    page=b.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
    assert page.request.get(BASE+'/api/config').json()['mode']=='MOCK'
    page.goto(BASE)
    expect(page.locator('#aiRun')).to_be_enabled()
    prompt='에어컨 켜고 22도로 해줘. 아, 온도만 취소하고 지금 설정된 25도보다 1.5도 낮춰줘. 켜는 건 그대로 진행해.'
    page.locator('#aiPrompt').fill(prompt)
    page.locator('#aiRun').click()
    expect(page.locator('#result')).to_contain_text('모의 제품에 적용 완료',timeout=60000)
    state=page.request.get(BASE+'/api/devices/mock-ac').json()['state']
    assert state['/property/temperature/targetTemperature']==23.5
    assert state['/property/operation/airConOperationMode']=='POWER_ON'
    # Restore the submitted prompt visually after UI refresh; result is untouched.
    page.locator('#aiPrompt').fill(prompt)
    page.locator('#detail').screenshot(path='docs/screenshots/ai-luna-execution.png')
    page.screenshot(path='docs/screenshots/ai-luna-page.png',full_page=True)
    b.close()
print('UI execution verified: POWER_ON / 23.5 C')
