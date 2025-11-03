import os
import time
import requests

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("E2E_TIMEOUT", "60"))


def wait_for_condition(fn, timeout=30, interval=1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ok, val = fn()
            if ok:
                return val
        except Exception:
            pass
        time.sleep(interval)
    raise RuntimeError("timeout waiting for condition")


def create_subscriber(strategy_id):
    payload = {
        "strategy_id": strategy_id,
        "risk_multiplier": 1.0,
        "max_leverage": 1.0,
        "enabled": True,
    }
    r = requests.post(f"{BASE}/v1/copy/subscribe", json=payload, timeout=5)
    r.raise_for_status()
    return r.json()


def post_trade(strategy_id, trade_id):
    payload = {
        "strategyId": strategy_id,
        "symbol": "BTC-PERP",
        "side": "buy",
        "qty": 0.001,
        "price": 60000,
        "ts": int(time.time() * 1000),
        "tradeId": trade_id,
    }
    r = requests.post(f"{BASE}/v1/events/trade", json=payload, timeout=5)
    r.raise_for_status()
    return r.json()


def find_execution(strategy_id, trade_id):
    r = requests.get(f"{BASE}/v1/copy/executions?strategyId={strategy_id}")
    r.raise_for_status()
    data = r.json()
    # API now returns { items: [...], total: N }
    items = data.get("items") if isinstance(data, dict) else data
    if items is None:
        items = data
    for e in items:
        if str(e.get("signal_trade_id") or e.get("signalTradeId") or e.get("signalTradeId")) == str(trade_id) or str(e.get("id")) == str(trade_id):
            return True, e
    return False, None


def main():
    strategy = os.environ.get("E2E_STRATEGY", "mtf-btc-1h-6h-16h")
    trade_id = f"e2e-copy-{int(time.time())}"

    print("creating subscriber for", strategy)
    create_subscriber(strategy)

    print("posting trade", trade_id)
    post_trade(strategy, trade_id)

    print("waiting for execution record...")
    exec_rec = wait_for_condition(lambda: find_execution(strategy, trade_id), timeout=TIMEOUT, interval=2)

    print("execution found:", exec_rec)
    # basic assertions
    if not exec_rec:
        raise RuntimeError("execution not found")
    e = exec_rec
    status = e.get("status") or e.get("Status")
    if not status:
        raise RuntimeError("execution missing status")
    if status not in ("pending", "success", "error"):
        raise RuntimeError(f"unexpected status: {status}")
    print("e2e copy succeeded")

    # cursor pagination smoke: fetch first page (limit=1) and if next_cursor present, fetch next and ensure no duplicate ids
    r1 = requests.get(f"{BASE}/v1/copy/executions?strategyId={strategy}&limit=1&sort=time&dir=desc", timeout=5)
    r1.raise_for_status()
    d1 = r1.json()
    items1 = d1.get('items') or []
    nextc = d1.get('next_cursor')
    if nextc:
        r2 = requests.get(f"{BASE}/v1/copy/executions?strategyId={strategy}&cursor={nextc}&limit=1&sort=time&dir=desc", timeout=5)
        r2.raise_for_status()
        d2 = r2.json()
        items2 = d2.get('items') or []
        ids = {str(i.get('id')) for i in items1}
        for it in items2:
            if str(it.get('id')) in ids:
                raise RuntimeError('cursor pagination returned duplicate id')
        print('cursor pagination sanity OK')


if __name__ == "__main__":
    main()
