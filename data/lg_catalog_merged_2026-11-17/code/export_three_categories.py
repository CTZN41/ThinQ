"""Export only washers, air conditioners and ovens/microwaves from the merged DB."""
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / 'lg_three_categories_2026-11-17'
SCOPE = {'세탁기', '에어컨', '광파오븐·전자레인지'}

def main():
    OUT.mkdir(exist_ok=True)
    source = ROOT / 'products_merged.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    products = [r for r in data['products'] if r['category'] in SCOPE]
    ids = {r['record_id'] for r in products}
    assert len(ids) == len(products)
    counts = dict(collections.Counter(r['category'] for r in products))
    result = {
        'schema_version': data['schema_version'],
        'source_notes': data['source_notes'],
        'selection': {
            'categories': sorted(SCOPE),
            'records': len(products),
            'distinct_models': len({(r['category'], r['model']) for r in products}),
            'category_counts': counts,
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        },
        'products': products,
    }
    (OUT / 'products_merged.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (ROOT / 'LG_제품DB_합본.csv').open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = [r for r in reader if r['카테고리'] in SCOPE]
    assert {r['통합ID'] for r in rows} == ids and len(rows) == len(products)
    with (OUT / '세탁기_에어컨_오븐전자레인지_합본.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result['selection'], ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
