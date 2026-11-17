"""Refresh three LG public catalogs; reuse LifeFit's Flight parser, no auth."""
import ast,csv,hashlib,json,math,re,time,urllib.request,sys
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parent
OUT=Path(__file__).resolve().parent
from flight_helpers import flight_records,dictionaries
CATS={'washing-machines':'세탁기','microwaves-and-ovens':'광파오븐·전자레인지','air-conditioners':'에어컨'}
def fetch(url):
 if not url.startswith('https://www.lge.co.kr/'):raise ValueError('official URL only')
 for attempt in range(3):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; LifeFit-product-refresh/1.0)','Accept-Language':'ko-KR'})
   with urllib.request.urlopen(req,timeout=30) as r:
    if not r.url.startswith('https://www.lge.co.kr/'):raise ValueError('unexpected redirect')
    return r.read(12000000).decode('utf-8'),r.url
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)
def plp(doc):
 for o in dictionaries(flight_records(doc)):
  if 'totalModelCnt' in o and isinstance(o.get('modelList'),list):return o
 raise ValueError('catalog missing')
def discover():
 records={};coverage=[]
 for cat in CATS:
  first,_=fetch('https://www.lge.co.kr/category/'+cat)
  initial=plp(first);total=initial['totalModelCnt'];size=len(initial['modelList']);found={}
  reqbase=next(o['plpModelInfoReq'] for o in dictionaries(flight_records(first)) if 'plpModelInfoReq' in o)
  cid=initial['modelList'][0]['categoryId']
  for page in range(1,math.ceil(total/size)+1):
   if page==1:data=initial
   else:
    req=urllib.request.Request(f'https://apiv2.lge.co.kr/plpsvc/ajax/v1/plp/category/{cid}/model',data=json.dumps({**reqbase,'page':page}).encode(),headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (compatible; LifeFit-product-refresh/1.0)','Origin':'https://www.lge.co.kr'})
    with urllib.request.urlopen(req,timeout=30) as response:data=json.loads(response.read())['data']
   (OUT/f'listing_{cat}_{page}.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   for m in data['modelList']:
    if m.get('modelName'):found[(m['modelName'],m.get('modelId'))]=m
   time.sleep(.2)
  coverage.append({'category':cat,'expected_listings':total,'collected_listings':len(found),'complete':len(found)==total})
  for (name,mid),m in found.items():records[(cat,name,mid)]=m
  print('CATALOG',coverage[-1],flush=True)
 (OUT/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
 (OUT/'catalog.json').write_text(json.dumps([{'category':k[0],**v} for k,v in records.items()],ensure_ascii=False),encoding='utf-8')
 return records,coverage
def full_flight(doc):
 parts=[]
 for script in re.findall(r'<script[^>]*>(.*?)</script>',doc,re.S|re.I):
  m=re.search(r'self\.__next_f\.push\((\[1,.*\])\)',script,re.S)
  if m:parts.append(json.loads(m[1])[1])
 return ''.join(parts)
def specs(doc):
 f=full_flight(doc);decoder=json.JSONDecoder();rows=[];seen=set()
 for m in re.finditer(r'\{"title":',f):
  try:g=decoder.raw_decode(f[m.start():])[0]
  except ValueError:continue
  if not isinstance(g,dict) or not isinstance(g.get('items'),list):continue
  for item in g['items']:
   if not isinstance(item,dict) or 'name' not in item or 'value' not in item:continue
   key=(g['title'],item['name'],str(item['value']))
   if key in seen:continue
   seen.add(key);rows.append({'group':g['title'],'name':item['name'],'value':item['value'],'description':(item.get('glossary') or {}).get('textContent')})
 return rows
def collect(key,m,old):
 cat,name,mid=key;safe=re.sub('[^A-Za-z0-9_-]','_',name+'_'+str(mid));dest=OUT/'products'/f'{cat}_{safe}.json'
 # A new run refreshes the page. Explicit --resume is only for interrupted runs.
 if '--resume' in sys.argv and dest.exists():
  cached=json.loads(dest.read_text(encoding='utf-8'))
  if cached.get('status')=='ok' and cached.get('listing_model_id')==mid:return cached
 url='https://www.lge.co.kr'+m['modelUrlPath'];stamp=datetime.now(timezone.utc).isoformat()
 row={'category':CATS[cat],'model':name,'name':m.get('modelDisplayName'),'source_url':url,'collected_at':stamp,'new_to_baseline':name not in old,'listing_status':m.get('modelStatusCode'),'listing_model_id':m.get('modelId'),'release_date_raw':m.get('modelReleaseDate'),'listing_price':m.get('priceInfo') or {'sale_price':m.get('obsSellingPrice')},'specs':[],'is_set':m.get('mixProductFlag'),'api_control_verified':False}
 try:
  doc,final=fetch(url);row.update(final_url=final,html_sha256=hashlib.sha256(doc.encode()).hexdigest())
  # Validate product identity using its schema.org Product, not recommendation widgets.
  products=[]
  for script in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',doc,re.S|re.I):
   try:products.extend(o for o in dictionaries(json.loads(script)) if o.get('@type')=='Product')
   except ValueError:pass
  product=next((p for p in products if str(p.get('model','')).upper()==name.upper() or str(p.get('sku','')).split('.')[0].upper()==name.upper()),None)
  if not product:raise ValueError('product identity not confirmed')
  row['product_schema']=product;row['specs']=specs(doc)
  if not row['specs']:raise ValueError('specifications missing')
  row['status']='ok'
 except Exception as e:row.update(status='error',error=str(e)[:250])
 dest.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8');time.sleep(.35)
 return row
def main():
 (OUT/'products').mkdir(exist_ok=True)
 olddata=json.loads((ROOT/'baseline.json').read_text(encoding='utf-8'));old={r[olddata['headers'].index('모델명')] for r in olddata['rows']}
 records,coverage=discover()
 if not all(c['complete'] for c in coverage):print('INCOMPLETE CATALOG: inspect pagination before details',flush=True);return
 rows=[]
 with ThreadPoolExecutor(max_workers=3) as pool:
  jobs=[pool.submit(collect,k,v,old) for k,v in records.items()]
  for i,f in enumerate(as_completed(jobs),1):
   rows.append(f.result())
   if i%20==0:print('DETAIL',i,'/',len(jobs),'errors',sum(r['status']!='ok' for r in rows),flush=True)
 rows.sort(key=lambda r:(r['category'],r['model']))
 (OUT/'products_current.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 with (OUT/'products_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
  fields=['category','model','name','new_to_baseline','listing_status','release_date_raw','source_url','collected_at','status'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
 with (OUT/'specifications.csv').open('w',encoding='utf-8-sig',newline='') as f:
  fields=['category','model','group','name','value','description','source_url'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:
   for sp in r['specs']:w.writerow({'category':r['category'],'model':r['model'],'source_url':r['source_url'],**sp})
 print('DONE',len(rows),'new',sum(r['new_to_baseline'] for r in rows),'ok',sum(r['status']=='ok' for r in rows),flush=True)
if __name__=='__main__':main()
