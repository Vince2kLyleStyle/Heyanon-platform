"""
Summary and home page routes for Mico's World.
Provides /v1/summary, /v1/strategies, /v1/strategies/{id}/logs
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
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
    
    return {
        "updatedAt": last_updated,
        "regime": regime,
        "status": status,
        "errors": error_count,
        "mostRecentTrade": most_recent_trade,
    }


@router.get("/v1/strategies")
async def list_strategies():
    """
    List all strategies with their latest signals and status.
    Derives from signals state and strategy definitions.
    """
    from .services.signals import state as signals_state
    from .db import SessionLocal
    from .models import Strategy
    
    db = SessionLocal()
    try:
        db_strategies = db.query(Strategy).all()
        
        result = []
        signals = signals_state.get("signals", {})
        
        for strat in db_strategies:
            # Try to find latest signal for this strategy's markets
            latest_signal = None
            for market in (strat.markets or []):
                if market in signals:
                    sig = signals[market]
                    latest_signal = {
                        "label": sig.get("label"),
                        "score": sig.get("score"),
                        "market": market,
                        "ts": signals_state.get("last_updated"),
                    }
                    break  # Use first matching market
            
            # Determine status (Active by default, check if logs show errors)
            status = strat.status or "Active"
            last_evaluated = signals_state.get("last_updated")
            
            result.append({
                "id": strat.id,
                "name": strat.name,
                "markets": strat.markets or [],
                "status": status,
                "lastEvaluated": last_evaluated,
                "latestSignal": latest_signal,
            })
        
        return result
    finally:
        db.close()


@router.get("/v1/strategies/{strategy_id}/logs")
async def get_strategy_logs(strategy_id: str, limit: int = 50):
    """
    Get recent logs for a specific strategy.
    Returns empty array if no logs yet.
    """
    logs = tail_logs(strategy_id, limit)
    return logs


# Helper function to seed example data for demo purposes
@router.post("/v1/strategies/{strategy_id}/logs")
async def add_strategy_log(strategy_id: str, log: Dict[str, Any]):
    """
    Add a log entry for a strategy (for testing/demo).
    Body: { ts, level, event, market?, action?, price?, size?, note? }
    """
    if "ts" not in log:
        log["ts"] = datetime.now(timezone.utc).isoformat()
    
    append_log(strategy_id, log)
    return {"ok": True}


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
