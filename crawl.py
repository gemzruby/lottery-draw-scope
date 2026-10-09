#!/usr/bin/env python3
"""Update Lotto 5/35, Mega 6/45 and Power 6/55 histories incrementally."""
import argparse
import csv
import json
import re
import ssl
import subprocess
import time
import urllib.request
import urllib.error
from datetime import datetime
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KINDS = {'535': 'ltoVM35', '645': 'ltoVM45', '655': 'ltoVM55'}
LIMITS = {'535': (35, 5, 12), '645': (45, 6, None), '655': (55, 6, 55)}
DISCOVERY_INDEX = 100000
API = 'https://www.lotto-8.com/Json_lto.asp?Lkind={}&Lindex={}&Ldesc=desc'


def fetch(url, method='GET'):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, method=method)
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return response.read().decode('utf-8-sig')
            except urllib.error.URLError as error:
                if not isinstance(error.reason, ssl.SSLCertVerificationError):
                    raise
                # macOS Python may lack CA roots; curl uses the system trust store.
                # Keep TLS verification enabled.
                return subprocess.run(
                    ['curl', '-sS', '-L', '--fail', '--max-time', '30', '-X', method, url],
                    check=True, capture_output=True).stdout.decode('utf-8-sig')
        except (OSError, UnicodeError, subprocess.CalledProcessError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def parse_row(date_text, numbers_text, product="645", bonus_text=""):
    parts = re.split(r'<br\s*/?>', date_text, flags=re.I)
    maximum, count, bonus_max = LIMITS[product]
    date_part = parts[1] if product == '535' else parts[0]
    date = datetime.strptime(date_part.strip() + '/' + parts[-1].strip(), '%d/%m/%y').date()
    code = int(parts[0].strip()) if product == '535' else int(date.strftime('%Y%m%d'))
    numbers = [int(n.strip()) for n in unescape(numbers_text).split(',')]
    if len(numbers) != count or len(set(numbers)) != count or any(n < 1 or n > maximum for n in numbers):
        raise ValueError(f'Invalid numbers for {date}: {numbers}')
    bonus_text = re.sub(r'<[^>]+>', '', unescape(bonus_text)).strip()
    bonus = int(bonus_text) if bonus_text else None
    if bonus_max is not None and (bonus is None or not 1 <= bonus <= bonus_max):
        raise ValueError(f'Invalid bonus for {date}: {bonus_text}')
    if product == '645' and bonus is not None:
        raise ValueError('645 must not contain a bonus')
    return {'draw_code': code, 'draw_date': date.isoformat(),
            'numbers': ' '.join(map(str, numbers)), 'bonus': str(bonus) if bonus is not None else ''}


def append_rows(accumulated, batch):
    for row in batch:
        key = row['draw_code']
        if key in accumulated and accumulated[key] != row:
            raise ValueError(f'Conflicting result for draw {key}')
        accumulated[key] = row


def read_csv(path):
    accumulated = {}
    if path.exists():
        with path.open(encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                row['draw_code'] = int(row['draw_code'])
                append_rows(accumulated, [row])
    return accumulated


def fetch_records(product, cursor):
    records = json.loads(fetch(API.format(KINDS[product], cursor), 'POST'))['lotto']
    if not records:
        raise ValueError(f'{product}: empty response at index {cursor}')
    indices = [int(r['dex']) for r in records]
    if indices != sorted(set(indices), reverse=True) or max(indices) >= cursor:
        raise ValueError(f'Invalid cursor batch: {indices}')
    return records, indices


def update_product(product, directory, end_index=9, delay=0.2):
    path = directory / f'{product}.csv'
    accumulated = read_csv(path)
    existing_codes = set(accumulated)
    latest_existing = max(existing_codes) if existing_codes else None
    discovery, indices = fetch_records(product, DISCOVERY_INDEX)
    cursor = max(indices)
    print(f'{product}: latest index {cursor}', flush=True)
    additions = {}

    def collect(batch):
        append_rows(accumulated, batch)  # Also detect conflicting stored results.
        for row in batch:
            if row['draw_code'] not in existing_codes:
                additions[row['draw_code']] = row

    # API excludes the cursor itself; keep the latest record from discovery.
    collect([parse_row(r['date'], r['num'], product, r.get('sp', ''))
             for r in discovery if int(r['dex']) == cursor and cursor >= end_index])
    # Query from the discovered index, then advance through each returned batch.
    overlap = False
    reached_end = cursor == end_index
    while not overlap and cursor > end_index:
        records, indices = fetch_records(product, cursor)
        batch = [parse_row(r['date'], r['num'], product, r.get('sp', ''))
                 for r in records if int(r['dex']) >= end_index]
        collect(batch)
        reached_end = reached_end or end_index in indices
        overlap = latest_existing is not None and any(r['draw_code'] <= latest_existing for r in batch)
        print(f'{product}: index {cursor} -> {min(indices)}, {len(additions)} new rows', flush=True)
        cursor = min(indices)
        time.sleep(delay)
    if not existing_codes and not reached_end:
        raise ValueError(f'{product}: requested index {end_index} missing')
    if existing_codes and not overlap:
        raise ValueError(f'{product}: no overlap with existing history')
    if not additions:
        print(f'{product}: no new draws; CSV unchanged ({len(accumulated)} rows)', flush=True)
        return 0
    directory.mkdir(parents=True, exist_ok=True)
    new_rows = sorted(additions.values(), key=lambda r: r['draw_code'])
    if existing_codes and all(r['draw_code'] > latest_existing for r in new_rows):
        # New draws only: append without rewriting any existing rows.
        with path.open('ab+') as f:
            f.seek(-1, 2)
            if f.read(1) not in (b'\n', b'\r'):
                f.write(b'\n')
        with path.open('a', encoding='utf-8', newline='') as f:
            csv.DictWriter(f, fieldnames=['draw_code', 'draw_date', 'numbers', 'bonus']).writerows(new_rows)
    else:
        # Bootstrap or fill missing rows in fetched overlap: atomic replacement.
        temporary = path.with_suffix('.csv.tmp')
        with temporary.open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['draw_code', 'draw_date', 'numbers', 'bonus'])
            writer.writeheader()
            writer.writerows(sorted(accumulated.values(), key=lambda r: r['draw_code']))
        temporary.replace(path)
    print(f'{product}: added {len(additions)}, total {len(accumulated)} -> {path}', flush=True)
    return len(additions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--products', nargs='+', choices=KINDS, default=list(KINDS))
    parser.add_argument('--end-index', type=int, default=9)
    parser.add_argument('--delay', type=float, default=0.2)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'databases')
    args = parser.parse_args()
    if args.end_index < 0 or args.delay < 0:
        parser.error('end-index and delay must be nonnegative')
    for product in dict.fromkeys(args.products):
        update_product(product, args.output_dir, args.end_index, args.delay)


if __name__ == '__main__':
    main()
