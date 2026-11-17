"""Paid, finite evaluation set; not an overall accuracy estimate."""
import asyncio,json
from pathlib import Path
from thinq_demo.washer import analyze
CASES=[
 ('correction','일반 면 의류를 40도가 아니라 30도, 헹굼 3회, 탈수 강 단계로 돌렸어.',{'temperature_c':30,'spin':'high'}),
 ('uncertain_temp','일반 면 의류인데 수온이 30도인지 40도인지 모르겠어. 헹굼은 3회.',{'temperature_c':None}),
 ('negated_spin','일반 면 의류를 40도에 헹굼 3회로 했어. 탈수는 강이 아니라 약 단계였어.',{'spin':'low'}),
 ('reservation','일반 면 의류 40도 헹굼 3회, 2시간 뒤 끝나도록 예약했어.',{'time_kind':'scheduled'}),
 ('mixed','울 니트랑 수건을 같이 넣었고 30도였어.',{'purpose':None}),
 ('rpm','일반 면 의류를 40도, 헹굼 3회, 탈수 1200rpm으로 했어.',{'spin':None,'spin_rpm':1200}),
 ('outcome_only','냄새가 안 나고 뽀송했어. 설정은 기억 안 나.',{'purpose':None,'temperature_c':None,'spin':None}),
 ('unsupported','울 니트를 60도, 강 단계로 세탁했어.',{'purpose':'wool','temperature_c':60,'spin':'high'})]
async def main():
 rows=[]
 for name,phrase,expected in CASES:
  try:
   r=await analyze('WW90J3000KW',phrase)
   ok=all(r['facts'][k]==v for k,v in expected.items())
   if name in ['uncertain_temp','mixed','rpm','outcome_only','unsupported']:ok=ok and r['recommended'] is None
   if name=='reservation':ok=ok and not r['time_compared']
   row={'case':name,'pass':ok,'expected':expected,'facts':r['facts'],'status':r['recommendation_status']}
  except Exception as e:row={'case':name,'pass':False,'error':type(e).__name__}
  rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 Path('docs/WASHER_EXTENDED_EVALUATION.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 assert all(r['pass'] for r in rows)
asyncio.run(main())
