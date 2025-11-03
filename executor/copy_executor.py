import os, time, uuid, math, logging, random, json
import requests
from typing import Dict, Any, List
from prometheus_client import Counter, Histogram, Gauge, start_http_server

API_BASE = os.getenv("BASE_URL", "http://api:8000")
STRATEGY_ID = os.getenv("STRATEGY_ID", "mtf-btc-1h-6h-16h")
STRATEGIES = os.getenv("STRATEGIES")  # comma-separated list, e.g. mtf-btc-...,mtf-eth-...
SYMBOL = os.getenv("SYMBOL", "BTC-PERP")
DISABLE_COPY = os.getenv("DISABLE_COPY", "1") == "1"
POLL_SEC = float(os.getenv("COPY_POLL_SEC", "10"))
METRICS_PORT = int(os.getenv("COPY_METRICS_PORT", "9102"))
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "5.0"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("copy-executor")

COPY_DISPATCH = Counter("copy_dispatch_total", "Total copy-dispatch attempts", ["strategy_id", "result"])
COPY_ERRORS = Counter("copy_dispatch_errors_total", "Copy-dispatch errors", ["strategy_id", "reason"])
COPY_LATENCY = Histogram("copy_dispatch_latency_seconds", "Copy-dispatch latency", buckets=(0.05,0.1,0.2,0.5,1,2,5))
COPY_DISABLED = Gauge("copy_executor_disabled", "Whether the copy executor is disabled (1=yes,0=no)")
COPY_UP = Gauge("copy_executor_up", "Copy executor up (1 = running)")
MISSING_SYMBOL_RULES = Counter("copy_missing_symbol_rules_total", "Number of times a trade referenced a symbol with no rules", ["strategy_id", "symbol"])

def now_ms(): return int(time.time() * 1000)


def load_symbol_rules():
    cfg_path = os.path.join(os.path.dirname(__file__), "config", "symbols.json")
    try:
        with open(cfg_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


SYMBOL_RULES = load_symbol_rules()


# debounce cache for missing symbol metric to avoid noisy repeats
_MSR_LAST: Dict[tuple, float] = {}
_MSR_TTL = 300.0  # 5 minutes


def apply_symbol_rounding(symbol: str, desired_qty: float, price: float):
    rules = SYMBOL_RULES.get(symbol, None)
    if not rules:
        # increment missing-symbol metric for visibility, debounced per (strategy_id, symbol)
        try:
            strategy_id = os.getenv('STRATEGY_ID', 'unknown')
            key = (strategy_id, symbol)
            now = time.time()
            last = _MSR_LAST.get(key, 0.0)
            if now - last >= _MSR_TTL:
                MISSING_SYMBOL_RULES.labels(strategy_id=strategy_id, symbol=symbol).inc()
                _MSR_LAST[key] = now
        except Exception:
            pass
        # default rounding: floor to 8 decimals
        qty = float(math.floor(desired_qty * 1e8) / 1e8)
        min_notional = 0.0
        return qty, min_notional
    step = float(rules.get("stepSize", 1e-8))
    precision = int(rules.get("precision", 8))
    min_notional = float(rules.get("minNotional", 0.0))
    # floor to nearest step
    steps = math.floor(desired_qty / step)
    qty = float(steps * step)
    # apply precision
    qty = float(round(qty, precision))
    return qty, min_notional

def _req(method: str, path: str, json: Dict[str, Any] | None = None, idem: str | None = None):
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if idem:
        headers["Idempotency-Key"] = idem
    rid = str(uuid.uuid4())
    headers["X-Request-Id"] = rid
    for attempt in range(5):
        t0 = time.perf_counter()
        try:
            r = requests.request(method, url, json=json, headers=headers, timeout=TIMEOUT)
            dt = time.perf_counter() - t0
            if r.status_code >= 500:
                raise RuntimeError(f"{r.status_code} {r.text}")
            r.raise_for_status()
            # attempt to return json, else raw text
            try:
                return r.json(), dt
            except Exception:
                return {"ok": True, "text": r.text}, dt
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep((0.2 + random.random() * 0.3) * (2 ** attempt))
    raise RuntimeError("unreachable")

def get_subscribers(strategy_id: str) -> List[Dict[str, Any]]:
    resp, _ = _req("GET", f"/v1/copy/subscribers?strategyId={strategy_id}")
    return resp.get("items", resp if isinstance(resp, list) else [])

def get_recent_trades(strategy_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    # Note: this endpoint may not exist; fallback to /v1/strategies/{id}/trades if implemented
    resp, _ = _req("GET", f"/v1/strategies/{strategy_id}/trades?limit={limit}")
    return resp.get("items", resp if isinstance(resp, list) else [])

def post_execution(strategy_id: str, subscriber_id: str, signal_trade_id: str, side: str, qty: float, price: float):
    payload = {
        "strategyId": strategy_id,
        "subscriberId": subscriber_id,
        "signalTradeId": signal_trade_id,
        "side": side,
        "qty": float(qty),
        "price": float(price),
        "ts": now_ms(),
    }
    idem = f"{strategy_id}:{subscriber_id}:{signal_trade_id}"
    with COPY_LATENCY.time():
        resp, dt = _req("POST", "/v1/copy/executions", payload, idem=idem)
    COPY_DISPATCH.labels(strategy_id=strategy_id, result="success").inc()
    return resp, dt

def main():
    start_http_server(METRICS_PORT)
    log.info(f"copy-executor starting DISABLE_COPY={DISABLE_COPY} strategy={STRATEGY_ID} metrics=:{METRICS_PORT}")
    # Set static gauges
    COPY_DISABLED.set(1 if DISABLE_COPY else 0)
    COPY_UP.set(1)
    # startup sanity check for symbol rules
    if SYMBOL_RULES:
        log.info(f"Loaded symbol rules: {list(SYMBOL_RULES.keys())}")
        for sym in list(SYMBOL_RULES.keys())[:5]:
            q, mn = apply_symbol_rounding(sym, 0.00123456, 60000)
            log.info(f"symbol sanity {sym} -> rounded_qty={q} minNotional={mn}")
    # build strategies list
    if STRATEGIES:
        strategies_list = [s.strip() for s in STRATEGIES.split(",") if s.strip()]
    else:
        strategies_list = [STRATEGY_ID]

    # per-strategy -> subscriber_id -> set(trade_ids)
    last_processed: Dict[str, Dict[str, set]] = {s: {} for s in strategies_list}

    while True:
        try:
            # iterate configured strategies
            for strategy in strategies_list:
                try:
                    subs = [s for s in get_subscribers(strategy) if s.get("enabled")]
                    trades = get_recent_trades(strategy, limit=10)
                    if DISABLE_COPY or not subs or not trades:
                        # skip this strategy
                        continue

                    # iterate newest->oldest to copy promptly
                    for tr in reversed(trades):
                        trade_id = tr.get("tradeId") or tr.get("orderId") or tr.get("id")
                        if not trade_id: continue
                        side = tr.get("side"); qty = float(tr.get("qty") or 0)
                        price = float(tr.get("price") or tr.get("fillPx") or 0)
                        # determine symbol per-trade if present, fallback to global SYMBOL
                        trade_symbol = tr.get("symbol") or tr.get("Symbol") or SYMBOL
                        if not side or qty <= 0 or price <= 0: continue

                        for s in subs:
                            sid = str(s.get("id") or s.get("subscriberId") or s.get("userId"))
                            if not sid: continue
                            seen = last_processed.setdefault(strategy, {}).setdefault(sid, set())
                            if trade_id in seen: continue

                            # compute copy size using symbol-specific rules
                            mult = float(s.get("risk_multiplier") or s.get("multiplier") or 1.0)
                            max_lev = float(s.get("max_leverage") or s.get("maxLeverage") or 0)
                            max_notional = float(s.get("max_notional_usd") or s.get("maxNotionalUsd") or 0)
                            desired_qty = qty * mult
                            # apply notional cap if provided
                            notional = desired_qty * price
                            if max_notional and notional > max_notional:
                                desired_qty = max_notional / price
                            # apply symbol rounding rules (stepSize, precision) and minNotional
                            copy_qty, min_notional = apply_symbol_rounding(trade_symbol, desired_qty, price)
                            copied_notional = copy_qty * price
                            # include symbol in logs
                            sym = trade_symbol
                            # skip if resulting notional is below exchange-configured minNotional
                            if min_notional and copied_notional < min_notional:
                                # skip this copy
                                continue

                            try:
                                # include notional and copied_qty in the POST and set status
                                payload = {
                                    "strategyId": strategy,
                                    "subscriberId": sid,
                                    "signalTradeId": trade_id,
                                    "side": side,
                                    "qty": copy_qty,
                                    "price": price,
                                    "ts": now_ms(),
                                    "status": "success",
                                    "notional_usd": copied_notional,
                                    "copied_qty": copy_qty,
                                }
                                idem = f"{strategy}:{sid}:{trade_id}"
                                with COPY_LATENCY.time():
                                    resp, dt = _req("POST", "/v1/copy/executions", payload, idem=idem)
                                COPY_DISPATCH.labels(strategy_id=strategy, result="success").inc()
                                seen.add(trade_id)
                                log.info(f'{"service":"copy-executor","event":"execution","strategyId":"{strategy}","subscriberId":"{sid}","tradeId":"{trade_id}","side":"{side}","qty":{copy_qty},"price":{price},"notional_usd":{copied_notional},"latency_ms":{dt*1000:.1f}}')
                            except Exception as e:
                                COPY_DISPATCH.labels(strategy_id=strategy, result="error").inc()
                                COPY_ERRORS.labels(strategy_id=strategy, reason=type(e).__name__).inc()
                                # attempt to record failed execution with error
                                try:
                                    payload = {
                                        "strategyId": strategy,
                                        "subscriberId": sid,
                                        "signalTradeId": trade_id,
                                        "side": side,
                                        "qty": copy_qty,
                                        "price": price,
                                        "ts": now_ms(),
                                        "status": "error",
                                        "error": str(e)[:1000],
                                        "notional_usd": copied_notional,
                                        "copied_qty": copy_qty,
                                    }
                                    idem = f"{strategy}:{sid}:{trade_id}:error"
                                    _req("POST", "/v1/copy/executions", payload, idem=idem)
                                except Exception:
                                    pass
                                log.error(f'{"service":"copy-executor","event":"execution_error","strategyId":"{strategy}","subscriberId":"{sid}","tradeId":"{trade_id}","error":"{str(e).replace(chr(34), chr(39))}"}')
                except Exception:
                    # protect per-strategy loop
                    log.exception(f"error processing strategy {strategy}")

        except Exception as e:
            COPY_ERRORS.labels(strategy_id=STRATEGY_ID, reason="loop").inc()
            log.error(f'{"service":"copy-executor","event":"loop_error","error":"{str(e).replace(chr(34), chr(39))}"}')

        time.sleep(POLL_SEC)

if __name__ == "__main__":
    main()
