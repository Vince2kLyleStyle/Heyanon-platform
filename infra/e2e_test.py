import os
import time
import requests
import sys

BASE = os.getenv("BASE_URL", "http://localhost:8000")
KEY = os.getenv("HEYANON_API_KEY", "")
HDRS = {"Authorization": f"Bearer {KEY}"} if KEY else {}
SID = os.getenv("STRATEGY_ID", os.getenv("SID", "mtf-btc-1h-6h-16h"))


def now_ms():
    return int(time.time() * 1000)


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def get(path):
    r = requests.get(f"{BASE}{path}", headers=HDRS, timeout=10)
    try:
        r.raise_for_status()
    except Exception:
        print("ERR", path, r.status_code, r.text)
        sys.exit(1)
    return r.json()


def main():
    trade_id = f"e2e-{now_ms()}"
    ts = now_iso()

    # 1) open trade
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
    t = post("/v1/events/trade", trade_body, idem=trade_id)
    print("trade:", t)

    # 2) snapshot
    pos_body = {
        "ts": ts,
        "market": "BTC-PERP",
        "venue": "e2e",
        "strategyId": SID,
        "qty": 0.002,
        "avgEntry": 61000.0,
        "mark": 61000.0,
        "upnl": 0.0,
        "fundingAccrued": 0.0,
        "leverage": 3.0,
        "riskCaps": {},
    }
    p = post("/v1/events/position", pos_body, idem=f"{trade_id}-pos1")
    print("pos1:", p)

    # 3) pnl
    pnl_body = {
        "ts": ts,
        "strategyId": SID,
        "realizedPnL": 5.55,
        "unrealizedPnL": 0.0,
        "fees": 0.0,
        "fundingPnL": 0.0,
        "slippage": 0.0,
        "basis": "tp",
    }
    pnl = post("/v1/events/pnl", pnl_body, idem=f"{trade_id}-pnl")
    print("pnl:", pnl)

    # 4) verify reads
    trades = get(f"/v1/strategies/{SID}/trades")
    items = trades.get("items", [])
    print("trades_count:", len(items))
    if not any(x.get("orderId") == trade_id for x in items):
        print("trade not found", items[:5])
        sys.exit(2)

    print("E2E OK")


if __name__ == "__main__":
    main()
