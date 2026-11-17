"""LG public catalog refresh. Python 3.10+, standard library only."""
import argparse
import sys
from pathlib import Path
import collect

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=Path(__file__).resolve().parents[1]/'inputs/baseline.json')
    parser.add_argument('--resume', action='store_true', help='Only resume the same interrupted snapshot')
    args = parser.parse_args()
    # Collector reads baseline.json from ROOT; do not modify source inputs.
    if args.baseline.name != 'baseline.json':
        parser.error('Baseline filename must be baseline.json')
    if not args.baseline.is_file():
        parser.error('Baseline file not found')
    if (args.output/'products_current.json').exists() and not args.resume:
        parser.error('Use a new output directory to preserve the previous snapshot')
    args.output.mkdir(parents=True, exist_ok=True)
    collect.ROOT = args.baseline.resolve().parent
    collect.OUT = args.output.resolve()
    collect.main()
    import json
    coverage = json.loads((args.output/'coverage.json').read_text(encoding='utf-8'))
    if not all(row['complete'] for row in coverage):
        sys.exit('Incomplete listing coverage; merge was not run')
    rows = json.loads((args.output/'products_current.json').read_text(encoding='utf-8'))
    if any(row['status'] != 'ok' for row in rows):
        sys.exit('Some detail requests failed; inspect results and resume before merging')

if __name__ == '__main__':
    main()
