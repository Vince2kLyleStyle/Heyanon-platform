"""
Summary and home page routes for Mico's World.
Provides /v1/summary, /v1/strategies, /v1/strategies/{id}/logs
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path

router = APIRouter(tags=["summary"])

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
TRADES_FILE = DATA_DIR / "trades.json"
LOGS_DIR = DATA_DIR / "strategy_logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def get_last_trade() -> Optional[Dict[str, Any]]:
    """Get the most recent trade from trades.json"""
    if not TRADES_FILE.exists():
        return None
    try:
        with open(TRADES_FILE, 'r') as f:
            trades = json.load(f)
        if not trades:
            return None
        # Return most recent (assuming sorted by ts desc)
        return trades[0] if isinstance(trades, list) else None
    except Exception:
        return None


def record_trade(trade: Dict[str, Any]) -> None:
    """Append a trade to trades.json, keep last 100"""
    trades = []
    if TRADES_FILE.exists():
        try:
            with open(TRADES_FILE, 'r') as f:
                trades = json.load(f)
        except Exception:
            trades = []
    
    trades.insert(0, trade)
    trades = trades[:100]  # Keep last 100
    
    with open(TRADES_FILE, 'w') as f:
        json.dump(trades, f, indent=2)


def append_log(strategy_id: str, log: Dict[str, Any]) -> None:
    """Append a log entry to strategy_logs/{strategy_id}.jsonl"""
    log_file = LOGS_DIR / f"{strategy_id}.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(log) + '\n')


def tail_logs(strategy_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Read last N logs from strategy_logs/{strategy_id}.jsonl"""
    log_file = LOGS_DIR / f"{strategy_id}.jsonl"
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Take last N lines
        lines = lines[-limit:]
        logs = []
        for line in lines:
            try:
                logs.append(json.loads(line.strip()))
            except Exception:
                continue
        
        # Reverse so newest first
        return list(reversed(logs))
    except Exception:
        return []


@router.get("/v1/summary")
async def get_summary():
    """
    Get home page summary: updated time, regime, status, errors, most recent trade.
    Returns graceful empty state if no data yet.
    """
    from .services.signals import state as signals_state
    
    # Get signals state
    last_updated = signals_state.get("last_updated")
    regime = signals_state.get("regime", "Neutral")
    errors = signals_state.get("errors", [])
    
    # Determine status
    error_count = len(errors) if errors else 0
    status = "degraded" if error_count > 0 else "ok"
    
    # Get most recent trade
    most_recent_trade = get_last_trade()
    
    # updatedAt must be epoch seconds per contract
    def iso_to_epoch(iso_val: Optional[str]) -> Optional[int]:
        if not iso_val:
            return None
        try:
            dt = datetime.fromisoformat(iso_val.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except Exception:
            return None

    return {
        "updatedAt": iso_to_epoch(last_updated),
        "regime": regime,
        "status": status,
        "errors": error_count,
        "mostRecentTrade": most_recent_trade,
    }


@router.get("/v1/strategies")
async def get_single_strategy():
    """
    Return a single-card strategy summary per minimal contract.
    Strategy ID: swing-atr (website-only)
    """
    from .services.signals import state as signals_state

    signals = signals_state.get("signals", {})
    last_updated_iso = signals_state.get("last_updated")

    # Choose a focus market: prefer SOL, then BTC, else any available
    focus_market = None
    for candidate in ("SOL", "BTC"):
        if candidate in signals:
            focus_market = candidate
            break
    if not focus_market and signals:
        focus_market = list(signals.keys())[0]

    latest_signal = None
    if focus_market and focus_market in signals:
        s = signals[focus_market]
        # Trend mapping: Up/Down based on SMA20 vs SMA50 (directional proxy)
        trend = {
            "sma20": "Up" if (s.get("sma20", 0) >= s.get("sma50", 0)) else "Down",
            "sma50": "Up" if (s.get("sma50", 0) <= s.get("sma20", 0)) else "Down",
            "rsi14": round(float(s.get("rsi14") or 0.0), 1),
        }
        zones = s.get("zones", {})
        latest_signal = {
            "label": s.get("label", "Observation"),
            "score": int(max(0, min(100, s.get("score", 0)))),
            "market": focus_market,
            "price": round(float(s.get("price", 0.0)), 2),
            "trend": trend,
            "zones": {
                "deepAccum": round(float(zones.get("deepAccum", 0.0)), 2),
                "accum": round(float(zones.get("accum", 0.0)), 2),
                "distrib": round(float(zones.get("distrib", 0.0)), 2),
                "safeDistrib": round(float(zones.get("safeDistrib", 0.0)), 2),
            },
        }

    return {
        "id": "swing-atr",
        "name": "Swing ATR",
        "status": "Active" if latest_signal else "Waiting",
        "lastEvaluated": last_updated_iso or datetime.now(timezone.utc).isoformat(),
        "latestSignal": latest_signal,
    }


# Provide an explicit route for the single-card strategy avoiding conflicts
@router.get("/v1/strategy")
async def get_single_strategy_card():
    return await get_single_strategy()


def _normalize_log_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize stored log rows to the public contract shape."""
    out: Dict[str, Any] = {
        "ts": row.get("ts"),
        "event": row.get("event") or row.get("level") or "event",
    }
    # Prefer explicit fields; fallback to nested details/note
    if "market" in row:
        out["market"] = row.get("market")
    elif isinstance(row.get("details"), dict) and "market" in row["details"]:
        out["market"] = row["details"].get("market")
    if "note" in row:
        out["note"] = row.get("note")
    elif isinstance(row.get("details"), dict):
        # Build a compact note from details if available
        d = row["details"]
        parts = []
        if "signal" in d:
            parts.append(f"label {d.get('signal')}")
        if "score" in d:
            parts.append(f"score {d.get('score')}")
        if "price" in d:
            parts.append(f"price {d.get('price')}")
        if parts:
            out["note"] = ", ".join(parts)
    if "score" in row:
        out["score"] = row.get("score")
    elif isinstance(row.get("details"), dict) and "score" in row["details"]:
        out["score"] = row["details"].get("score")
    return out


@router.get("/v1/strategies/{strategy_id}/logs")
async def get_strategy_logs(strategy_id: str, limit: int = 50):
    """
    Get recent logs for a specific strategy.
    Returns empty array if no logs yet.
    """
    rows = tail_logs(strategy_id, limit)
    return [_normalize_log_row(r) for r in rows]


# Exact path per minimal API contract
@router.get("/v1/strategies/swing-atr/logs")
async def get_swing_atr_logs(limit: int = 50):
    rows = tail_logs("swing-atr", limit)
    return [_normalize_log_row(r) for r in rows]


# Helper function to seed example data for demo purposes
@router.post("/v1/strategies/{strategy_id}/logs")
async def add_strategy_log(strategy_id: str, log: Dict[str, Any]):
    """
    Add a log entry for a strategy (for testing/demo).
    Body: { event, market?, note?, score? }
    """
    obj: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": log.get("event", "event"),
    }
    # Optional fields
    if log.get("market"):
        obj["market"] = log["market"]
    if log.get("note"):
        obj["note"] = log["note"]
    if "score" in log:
        try:
            obj["score"] = int(log["score"])  # normalize
        except Exception:
            pass

    append_log(strategy_id, obj)
    return {"ok": True}


@router.get("/v1/strategies/swing-atr/kpis")
async def get_swing_atr_kpis(window: str = Query("7d", description="Window like 7d, 24h")):
    """
    Compute tiny KPIs from recent logs, neutral and safe for public display.
    Returns { alertsIssued, avgScore, riskSuppressed, medianTimeBetweenSignalsMin }
    """
    # Parse window
    now = datetime.now(timezone.utc)
    delta = timedelta(days=7)
    try:
        if window.endswith("d"):
            delta = timedelta(days=int(window[:-1]))
        elif window.endswith("h"):
            delta = timedelta(hours=int(window[:-1]))
        elif window.endswith("m"):
            delta = timedelta(minutes=int(window[:-1]))
    except Exception:
        pass

    rows = tail_logs("swing-atr", 500)
    # Filter by time window
    def parse_ts(x: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(x.replace("Z", "+00:00"))
        except Exception:
            return None

    rows = [r for r in rows if (parse_ts(r.get("ts")) or now) >= now - delta]

    # alertsIssued: count of strategy_tick events
    alerts_issued = sum(1 for r in rows if (r.get("event") == "strategy_tick"))
    # avgScore: average of score when present
    scores = [int(r.get("score")) for r in rows if isinstance(r.get("score"), (int, float, str)) and str(r.get("score")).isdigit()]
    avg_score = int(sum(scores) / len(scores)) if scores else 0
    # riskSuppressed: count events explicitly marked risk_suppressed
    risk_suppressed = sum(1 for r in rows if r.get("event") == "risk_suppressed")
    # median time between signals in minutes
    signal_ts = [parse_ts(r.get("ts")) for r in rows if r.get("event") == "strategy_tick"]
    signal_ts = [t for t in signal_ts if t is not None]
    signal_ts.sort()
    gaps = []
    for i in range(1, len(signal_ts)):
        gaps.append((signal_ts[i] - signal_ts[i-1]).total_seconds() / 60.0)
    gaps.sort()
    if gaps:
        mid = len(gaps) // 2
        median_gap = gaps[mid] if len(gaps) % 2 == 1 else (gaps[mid-1] + gaps[mid]) / 2
    else:
        median_gap = 0

    return {
        "alertsIssued": alerts_issued,
        "avgScore": avg_score,
        "riskSuppressed": risk_suppressed,
        "medianTimeBetweenSignalsMin": int(median_gap),
    }


@router.post("/v1/trades")
async def add_trade(trade: Dict[str, Any]):
    """
    Add a trade record (for testing/demo).
    Body: { strategyId, name, market, action, price, ts }
    """
    if "ts" not in trade:
        trade["ts"] = datetime.now(timezone.utc).isoformat()
    
    record_trade(trade)
    return {"ok": True}
