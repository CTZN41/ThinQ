"""Export official product specifications only; recheck legacy-only products."""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collect import fetch, specs, dictionaries

ROOT = Path(__file__).resolve().parents[2] / 'lg_three_categories_2026-11-17'

def refresh(row):
    old = row['legacy']
    try:
        source = old['상품 URL']
        if source.startswith('/') and not source.startswith('//'):
            source = 'https://www.lge.co.kr' + source
        html, url = fetch(source)
        identities = []
        for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S|re.I):
            try:
                identities.extend(o for o in dictionaries(json.loads(raw)) if o.get('@type') == 'Product')
            except ValueError:
                pass
        product = next((p for p in identities if str(p.get('model', '')).upper() == row['model'].upper()), None)
        items = specs(html)
        if not product or not items:
            raise ValueError('Official product identity or specifications could not be confirmed')
        return row, {'name': product.get('name'), 'specs': items, 'final_url': url,
                     'collected_at': datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        return row, {'error': str(exc)}

def main():
    original = json.loads((ROOT/'products_merged.json').read_text(encoding='utf-8'))['products']
    missing = [r for r in original if not r['current']]
    with ThreadPoolExecutor(max_workers=3) as pool:
        refreshed = {r['record_id']: data for r, data in pool.map(refresh, missing)}
    products, excluded = [], []
    for row in original:
        current = row['current'] or refreshed[row['record_id']]
        if 'error' in current:
            excluded.append({'model': row['model'], 'reason': current['error']})
            continue
        products.append({'카테고리': row['category'], '모델명': row['model'], '제품명': current['name'],
                         '상세스펙': current['specs'], '공식출처URL': current.get('final_url', current.get('source_url')),
                         '수집일(UTC)': current['collected_at']})
    target = ROOT/'공홈_상세스펙_전용.csv'
    with target.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['카테고리','모델명','제품명','상세스펙','공식출처URL','수집일(UTC)'])
        writer.writeheader()
        for product in products:
            text = '\n'.join(f"[{s['group']}] {s['name']}: {s['value']}"+
                             (f"\n  설명: {s['description']}" if s.get('description') else '')
                             for s in product['상세스펙'])
            writer.writerow({**product, '상세스펙': text})
    (ROOT/'공홈_상세스펙_전용.json').write_text(json.dumps(products,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with target.open(encoding='utf-8-sig',newline='') as f:
        check = list(csv.DictReader(f))
    assert len(check) == len(products) and all(len(r)==6 for r in check)
    assert all(p['상세스펙'] and p['공식출처URL'].startswith('https://www.lge.co.kr/') for p in products)
    report = {'exported': len(products), 'columns': 6, 'legacy_only_rechecked': len(missing), 'excluded': excluded}
    (ROOT/'official_specs_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__ == '__main__':
    main()
