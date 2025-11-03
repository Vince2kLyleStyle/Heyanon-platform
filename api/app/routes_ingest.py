from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import get_db
from . import models, schemas
from .auth import require_api_key
from typing import Optional
import logging
from datetime import datetime, timezone
from prometheus_client import Gauge

# Gauge of last heartbeat timestamp per strategy
HEARTBEAT_GAUGE = Gauge("heyanon_strategy_last_heartbeat_unixtime", "Last heartbeat unix timestamp", ["strategy_id"])

logger = logging.getLogger("ingest")

router = APIRouter(prefix="/v1/events", tags=["ingest"])

@router.post("/trade")
def post_trade(e: schemas.TradeEvent, db: Session = Depends(get_db), _=Depends(require_api_key), idem: Optional[str] = Header(None, alias="Idempotency-Key")):
    # prefer explicit idempotency header if provided
    id_key = idem or e.idempotencyKey
    if not id_key:
        raise HTTPException(status_code=400, detail="missing idempotency key")

    # Normalize/validate symbol: prefer e.symbol, fallback to e.market
    symbol = None
    if getattr(e, 'symbol', None):
        symbol = e.symbol
    elif getattr(e, 'market', None):
        symbol = e.market
    if not symbol:
        raise HTTPException(status_code=400, detail="missing symbol for trade event")
    symbol = symbol.upper()

    rec = models.Trade(
        strategy_id=e.strategyId,
        order_id=e.orderId,
        ts=e.ts,
        market=symbol,
        symbol=symbol,
        venue=e.venue,
        side=e.side.value if hasattr(e.side, 'value') else e.side,
        type=e.type.value if hasattr(e.type, 'value') else e.type,
        status=e.status.value if hasattr(e.status, 'value') else e.status,
        entry_px=e.entryPx,
        fill_px=e.fillPx,
        qty=e.qty,
        fees=e.fees,
        leverage=e.leverage,
        idempotency_key=id_key,
        meta=e.meta or {}
    )
    db.add(rec)
    try:
        db.commit()
    except IntegrityError as ie:
        db.rollback()
        # likely a duplicate due to unique constraint
        logger.warning("deduped trade: %s %s", e.orderId, id_key)
        return {"ok": True, "stored": False, "deduped": True}
    return {"ok": True, "stored": True, "deduped": False}

@router.post("/position")
def post_position(p: schemas.PositionSnapshot, db: Session = Depends(get_db), _=Depends(require_api_key)):
    rec = models.Position(
        strategy_id=p.strategyId,
        ts=p.ts,
        market=p.market,
        symbol=(p.market.upper() if p.market else None),
        venue=p.venue,
        qty=p.qty,
        avg_entry=p.avgEntry,
        mark=p.mark,
        upnl=p.upnl,
        funding_accrued=p.fundingAccrued,
        leverage=p.leverage,
        snapshot={"riskCaps": p.riskCaps} if p.riskCaps else None
    )
    db.add(rec)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="db error")
    return {"ok": True}

@router.post("/pnl")
def post_pnl(x: schemas.PnLAttribution, db: Session = Depends(get_db), _=Depends(require_api_key)):
    rec = models.PnL(
        strategy_id=x.strategyId,
        ts=x.ts,
        realized_pnl=x.realizedPnL,
        unrealized_pnl=x.unrealizedPnL,
        fees=x.fees,
        funding_pnl=x.fundingPnL,
        slippage=x.slippage,
        basis=x.basis
    )
    db.add(rec)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="db error")
    return {"ok": True}


@router.post("/heartbeat")
def post_heartbeat(h: dict, db: Session = Depends(get_db), _=Depends(require_api_key)):
    # expect { "strategyId": "...", "ts": "..." }
    sid = h.get("strategyId")
    if not sid:
        raise HTTPException(status_code=400, detail="missing strategyId")
    s = db.get(models.Strategy, sid)
    if not s:
        raise HTTPException(status_code=404, detail="strategy not found")
    # use provided ts or now
    try:
        ts = h.get("ts")
        if ts:
            # try parse ISO
            tsval = datetime.fromisoformat(ts)
        else:
            tsval = datetime.now(timezone.utc)
    except Exception:
        tsval = datetime.now(timezone.utc)
    s.last_heartbeat = tsval
    db.add(s)
    db.commit()
    try:
        # set prometheus metric (seconds since epoch)
        HEARTBEAT_GAUGE.labels(strategy_id=sid).set(tsval.timestamp())
    except Exception:
        pass
    return {"ok": True}