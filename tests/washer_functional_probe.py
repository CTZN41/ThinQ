import asyncio,json,sys
from pathlib import Path
from thinq_demo.washer import analyze
async def main():
 rows=[]
 for phrase in ['의류는 좀 섞여있긴했는데, 기능성 의류가 좀 많아서 탈수는 약하게 하고, 3~40도 정도로 세탁하니까 좋았어.','기능성 의류 위주로 탈수 약, 수온 30도로 세탁하니 좋았어.']:
  r=await analyze('WW90J3000KW',phrase)
  row={'input':phrase,'facts':r['facts'],'status':r['recommendation_status'],'candidate_ids':[c['id'] for c in r['candidates']]}
  rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 Path('docs/FUNCTIONAL_'+sys.argv[1]+'.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
asyncio.run(main())
