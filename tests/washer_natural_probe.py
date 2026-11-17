"""Small paid extraction probe; never sends appliance commands."""
import asyncio
import json
from pathlib import Path
from thinq_demo.washer import analyze

async def main():
    cases=[
        ('전에 쓰던 것처럼 해줘.', {'purpose':None,'temperature_c':None,'spin':None}),
        ('전에는 그냥 표준으로 놓고 탈수 버튼만 한 번 더 눌렀어. 잘 말랐거든.', {'purpose':None,'temperature_c':None,'spin':None}),
        ('운동할 때 입는 옷은 어떻게 빨아? 망가질까 봐.', {'purpose':'functional','temperature_c':None,'spin':None,'request_kind':'usage_help'}),
        ('새 세탁기에서 빨면 너무 구겨져.', {'temperature_c':None,'spin':None,'request_kind':'result_problem'}),
    ]
    report=[]
    for phrase, expected in cases:
        result=await analyze('F14WQT',phrase)
        facts=result['facts']
        passed=all(facts.get(k)==v for k,v in expected.items())
        report.append({'input':phrase,'model':result['model'],'facts':facts,'passed':passed})
        print(json.dumps({'input':phrase,'passed':passed,'facts':facts},ensure_ascii=False),flush=True)
    Path('docs/WASHER_NATURAL_PROBE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert all(r['passed'] for r in report), 'See probe report'

if __name__=='__main__':
    asyncio.run(main())
