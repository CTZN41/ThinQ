"""Read-only snapshot audit; separate current checks and ACTIVE-only views."""
import json,collections,hashlib,csv
from pathlib import Path
import collect as c
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'audit';OUT.mkdir(exist_ok=True)
rows=json.loads((ROOT/'products_current.json').read_text(encoding='utf-8'))
checks=[]
for category,slug in [('세탁기','washing-machines'),('광파오븐·전자레인지','microwaves-and-ovens'),('에어컨','air-conditioners')]:
 doc,_=c.fetch('https://www.lge.co.kr/category/'+slug)
 listing=c.plp(doc)
 checks.append({'category':category,'current_listing_total':listing['totalModelCnt']})
 selected=[]
 for active in [True,False]:
  selected.append(next(r for r in rows if r['category']==category and (r['listing_status']=='ACTIVE')==active))
 for row in selected:
  doc,url=c.fetch(row['source_url']);specs=c.specs(doc)
  def norm(sp):return sorted((x['group'],x['name'],str(x['value'])) for x in sp)
  checks.append({'model':row['model'],'source_url':url,'saved_status':row['listing_status'],'spec_fields':len(specs),'specs_unchanged':norm(specs)==norm(row['specs'])})
summary=[]
for category in sorted({r['category'] for r in rows}):
 subset=[r for r in rows if r['category']==category]
 summary.append({'category':category,'all':len(subset),'statuses':dict(collections.Counter(r['listing_status'] for r in subset)),'active_new_to_baseline':sum(r['listing_status']=='ACTIVE' and r['new_to_baseline'] for r in subset)})
active=[r for r in rows if r['listing_status']=='ACTIVE']
(OUT/'active_products.json').write_text(json.dumps(active,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'active_new_to_baseline.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=['category','model','name','source_url','release_date_raw'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(r for r in active if r['new_to_baseline'])
report={'snapshot_models':len(rows),'active_models':len(active),'active_new_to_baseline':sum(r['new_to_baseline'] for r in active),'categories':summary,'live_checks':checks,'identity_mismatches':[r['model'] for r in rows if r['product_schema'].get('model','').upper()!=r['model'].upper()]}
(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
