"""Opt-in paid extraction regression using synthetic user examples."""
import asyncio,json
from pathlib import Path
from thinq_demo.washer import analyze
async def main():
 cases=[
  ('relative_only','세탁은 그대로 진행했는데, 탈수를 좀 쎄게 하니까 물기가 잘 말라서 냄새가 잘 안나고 잘 말랐어.',None),
  ('relative_context','일반 면 의류를 수온 40도, 헹굼 3회로 세탁했어. 전체 40~50분이야. 세탁은 그대로 진행했는데 탈수를 좀 쎄게 하니까 물기가 잘 말라서 냄새가 잘 안나고 잘 말랐어.',None),
  ('explicit_final','일반 면 의류를 수온 40도, 헹굼 3회로 세탁했어. 전체 40~50분이야. 세탁은 그대로 두고 탈수를 중 단계에서 강 단계로 바꿨더니 냄새가 덜 나고 잘 말랐어.','high')]
 results=[]
 for name,phrase,expected in cases:
  try:
   r=await analyze('WW90J3000KW',phrase);f=r['facts']
   ok=f['spin']==expected and f['drying_included'] is not True and bool(f['outcome'])
   if expected is None:ok=ok and f['spin_change']=='stronger' and not r['can_simulate']
   if name!='relative_only':ok=ok and f['temperature_c']==40 and f['rinse_count']==3
   results.append({'case':name,'passed':ok,'facts':f})
  except Exception as e:results.append({'case':name,'passed':False,'error_type':type(e).__name__,'reason':str(e) if isinstance(e,ValueError) else 'connection error'})
  print(json.dumps(results[-1],ensure_ascii=False),flush=True)
 Path('docs/WASHER_RELATIVE_EVALUATION.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 assert all(r['passed'] for r in results)
asyncio.run(main())
