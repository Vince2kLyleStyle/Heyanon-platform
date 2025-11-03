import os
import time
import requests
import sys

BASE = os.getenv("BASE_URL", "http://localhost:8000")
KEY = os.getenv("HEYANON_API_KEY", "")
HDRS = {"Authorization": f"Bearer {KEY}"} if KEY else {}
SID = "mtf-btc-1h-6h-16h"


def now_ms():
    return int(time.time() * 1000)


def post(path, body, idem=None):
    h = dict(HDRS)
    if idem:
        h["Idempotency-Key"] = idem
    r = requests.post(f"{BASE}{path}", json=body, headers=h, timeout=10)
    try:
        r.raise_for_status()
    except Exception:
        print("ERR", path, r.status_code, r.text)
        sys.exit(1)
    return r.json()


def main():
    trade_id = f"e2e-idem-{now_ms()}"
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    trade_body = {
        "orderId": trade_id,
        "ts": ts,
        "market": "BTC-PERP",
        "venue": "e2e",
        "strategyId": SID,
        "side": "buy",
        "type": "market",
        "status": "new",
        "entryPx": 61000.0,
        "fillPx": 61000.0,
        "qty": 0.002,
        "fees": 0.0,
        "leverage": 1.0,
        "idempotencyKey": trade_id,
        "meta": {"e2e": "1"},
    }

    # first post
    r1 = post("/v1/events/trade", trade_body, idem=trade_id)
    print("first:", r1)

    # duplicate post with same idempotency key
    r2 = post("/v1/events/trade", trade_body, idem=trade_id)
    print("second:", r2)

    # r2 should indicate deduped true or stored false
    if not (r2.get("deduped") or (r2.get("stored") is False)):
        print("idempotency failed", r1, r2)
        sys.exit(2)

    print("E2E IDEMPOTENCY OK")


if __name__ == "__main__":
    main()
