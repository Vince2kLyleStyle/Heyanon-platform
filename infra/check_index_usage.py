#!/usr/bin/env python3
"""Check whether Postgres is using the symbol index for trades/positions.

Usage (from repo root):
  python infra/check_index_usage.py --table trades --symbol BTC-PERP

The script runs an EXPLAIN ANALYZE inside the postgres container via
`docker compose exec` and prints whether the planner used an Index Scan.
"""
import argparse
import subprocess
import shlex
import sys


def run_explain(table: str, symbol: str, limit: int = 10):
    sql = f"EXPLAIN ANALYZE SELECT * FROM {table} WHERE symbol = '{symbol}' LIMIT {limit};"
    # Use -T to avoid pty allocation which can alter output
    cmd = f"docker compose exec -T postgres psql -U postgres -c \"{sql}\""
    print(f"Running: {cmd}")
    try:
        proc = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("Command failed:", e)
        print(e.stdout)
        print(e.stderr)
        sys.exit(2)

    output = proc.stdout
    print("\n--- EXPLAIN ANALYZE output ---\n")
    print(output)

    # simple detection for index usage
    lowered = output.lower()
    if 'index scan' in lowered or 'bitmap index scan' in lowered:
        print("\nIndex usage detected (planner used an Index Scan or Bitmap Index Scan).\n")
        return 0
    else:
        print("\nNo index usage detected (planner likely did a Seq Scan). Consider running ANALYZE or inspecting planner cost settings.\n")
        return 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--table', default='trades', help='Table to test (trades or positions)')
    p.add_argument('--symbol', default='BTC-PERP', help='Symbol value to query')
    p.add_argument('--limit', type=int, default=10, help='LIMIT for the query')
    args = p.parse_args()
    rc = run_explain(args.table, args.symbol, args.limit)
    sys.exit(rc)


if __name__ == '__main__':
    main()
