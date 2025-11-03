#!/usr/bin/env python3
"""Validate trades CSV exported by the API.

Checks performed:
- exact header equality against expected list
- at least one data row
- basic type checks on the first data row: ts parseable (ISO or numeric), qty and price numeric

Exit code 0 on success, non-zero on validation failure.
"""
import sys
import csv
import argparse
from datetime import datetime


EXPECTED_HEADERS = ['ts', 'side', 'status', 'qty', 'price', 'tradeId', 'fillPx', 'market', 'venue']


def parse_ts(val: str):
    if not val:
        raise ValueError('empty ts')
    # allow numeric epoch
    try:
        float(val)
        return True
    except Exception:
        pass
    # attempt ISO parse; accept trailing Z
    try:
        v = val.replace('Z', '+00:00')
        datetime.fromisoformat(v)
        return True
    except Exception:
        raise


def is_number(val: str):
    if val is None or val == '':
        raise ValueError('empty number')
    try:
        float(val)
        return True
    except Exception:
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('path', help='path to CSV file')
    args = p.parse_args()

    path = args.path
    try:
        with open(path, newline='') as fh:
            reader = csv.reader(fh)
            # skip comment lines starting with '#'
            header = None
            for row in reader:
                if not row:
                    continue
                line = ','.join(row).strip()
                if line.startswith('#'):
                    continue
                # first non-comment row is header
                header = row
                break
            if header is None:
                print('No header found in CSV', file=sys.stderr)
                return 2
            # normalize header (strip)
            header = [h.strip() for h in header]
            if header != EXPECTED_HEADERS:
                print('Header mismatch', file=sys.stderr)
                print('Found :', header, file=sys.stderr)
                print('Expected:', EXPECTED_HEADERS, file=sys.stderr)
                return 3
            # read first data row
            data_row = None
            for row in reader:
                if row and any(cell.strip() for cell in row):
                    data_row = row
                    break
            if data_row is None:
                print('No data rows found after header', file=sys.stderr)
                return 4
            # type checks on first data row by header index
            mapping = dict(zip(header, data_row))
            try:
                parse_ts(mapping['ts'])
            except Exception as e:
                print('ts parse error:', e, file=sys.stderr)
                return 5
            try:
                is_number(mapping['qty'])
            except Exception as e:
                print('qty parse error:', e, file=sys.stderr)
                return 6
            try:
                is_number(mapping['price'])
            except Exception as e:
                print('price parse error:', e, file=sys.stderr)
                return 7

    except FileNotFoundError:
        print('CSV file not found:', path, file=sys.stderr)
        return 8
    except Exception as e:
        print('unexpected error while validating CSV:', e, file=sys.stderr)
        return 9

    print('CSV validation OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
