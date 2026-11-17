"""Merge full legacy DB and verified public LG snapshots without losing source fields."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

SCOPE = {'세탁기', '광파오븐·전자레인지', '에어컨'}
ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def key(row):
    return (row['category'], row['model'].strip().upper(), row['listing_model_id'])

def merge(baseline, snapshots):
    headers = baseline['headers']
    legacy = {}
    for values in baseline['rows']:
        assert len(values) == len(headers), 'Baseline column count mismatch'
        row = dict(zip(headers, values))
        k = (row['카테고리'], row['모델명'].strip().upper())
        assert k not in legacy, f'Duplicate legacy model: {k}'
        legacy[k] = row
    current = {}
    for rows in snapshots:
        for row in rows:
            assert row['status'] == 'ok' and row['specs'], f'Unverified detail: {key(row)}'
            assert row['category'] in SCOPE and row['listing_model_id']
            assert row['product_schema'].get('model', '').upper() == row['model'].upper(), 'Identity mismatch'
            k = key(row)
            if k not in current or row['collected_at'] > current[k]['collected_at']:
                current[k] = dict(row)
    merged = []
    matched = set()
    for k, row in sorted(current.items()):
        legacy_key = k[:2]
        prior = legacy.get(legacy_key)
        row['new_to_baseline'] = prior is None
        matched.add(legacy_key)
        merged.append({'record_id': '|'.join(k), 'category': k[0], 'model': k[1],
                       'merge_status': '기존 모델 갱신' if prior else '기존 DB에 없는 모델 추가',
                       'legacy_match_level': '카테고리+모델명(판매 식별자 검증 아님)' if prior else None,
                       'current': row, 'legacy': prior})
    for k, prior in sorted(legacy.items()):
        if k not in matched:
            merged.append({'record_id': '|'.join((*k, 'LEGACY')), 'category': k[0], 'model': k[1],
                           'merge_status': '이번 목록 미확인(단종 판단 불가)' if k[0] in SCOPE else '이번 수집 범위 밖·기존 보존',
                           'legacy_match_level': None, 'current': None, 'legacy': prior})
    merged.sort(key=lambda r: (r['category'], r['model'], r['record_id']))
    assert len({r['record_id'] for r in merged}) == len(merged)
    assert {k for k in legacy} <= {(r['category'], r['model']) for r in merged}, 'Lost legacy models'
    for r in merged:
        if r['legacy']:
            assert r['legacy'] == legacy[(r['category'], r['model'])], 'Legacy fields changed'
    report = {'baseline_records': len(legacy), 'crawled_listing_records': len(current),
              'crawled_distinct_models': len({k[:2] for k in current}),
              'merged_records': len(merged), 'merged_distinct_models': len({(r['category'], r['model']) for r in merged}),
              'new_distinct_models': len({k[:2] for k in current} - set(legacy)),
              'matched_baseline_models': len(set(legacy) & matched),
              'unmatched_baseline_in_scope': len({k for k in legacy if k[0] in SCOPE} - matched),
              'current_listing_status_counts': dict(collections.Counter(r['listing_status'] for r in current.values())),
              'merge_status_counts': dict(collections.Counter(r['merge_status'] for r in merged)),
              'checks': {'unique_record_ids': True, 'all_legacy_models_preserved': True, 'all_legacy_fields_preserved': True,
                         'all_current_details_verified': True}}
    return merged, report

def cell(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    # Prevent spreadsheet execution when opening the CSV. JSON retains the exact original.
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'"+value
    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT/'inputs/baseline.json')
    parser.add_argument('--current', type=Path, default=ROOT/'inputs/products_current.json')
    parser.add_argument('--variants', type=Path, help='Optional audited corrections for the older 428-model snapshot')
    parser.add_argument('--output', type=Path, default=ROOT)
    args = parser.parse_args()
    inputs = [args.baseline, args.current]+([args.variants] if args.variants else [])
    baseline = read(args.baseline)
    rows, report = merge(baseline, [read(p) for p in inputs[1:]])
    report['input_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output/'products_merged.json', {'schema_version': 1,
          'source_notes': '기존 DB 스펙·가격·리뷰는 2026-09-30 기준, 판매 상태·이미지는 10-07 재확인. 최신 정보는 current 수집일 참조. legacy 원문 보존. API 제어 가능 여부 미검증.',
          'validation': report, 'products': rows})
    fields = ['통합ID', '카테고리', '모델명', '판매식별자', '최신 제품명', '병합 구분', '현재 판매상태',
              '현재 판매가(원)', '최신 수집일(UTC)', '최신 출처URL', '최신 출시일 원문', '최신 스펙(JSON)', '기존 연결 기준']
    fields += ['기존_'+h for h in baseline['headers']]
    with (args.output/'LG_제품DB_합본.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for row in rows:
            c, old = row['current'] or {}, row['legacy'] or {}
            price = c.get('listing_price') or {}
            values = [row['record_id'], row['category'], row['model'], c.get('listing_model_id'), c.get('name'),
                      row['merge_status'], c.get('listing_status'), price.get('obsSellingPrice', price.get('sale_price')),
                      c.get('collected_at'), c.get('final_url', c.get('source_url')), c.get('release_date_raw'), c.get('specs'),
                      row['legacy_match_level']]+[old.get(h) for h in baseline['headers']]
            writer.writerow([cell(v) for v in values])
    write(args.output/'validation.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
