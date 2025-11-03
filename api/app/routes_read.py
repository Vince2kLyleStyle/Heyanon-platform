from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from .db import get_db
from . import models
from datetime import datetime, timedelta, timezone
from fastapi import Response, HTTPException, Request, status
from typing import Optional
from fastapi import Body
from .models_status import StrategyStatus, Base as StatusBase
from sqlalchemy.exc import IntegrityError
from datetime import datetime

router = APIRouter(prefix="/v1", tags=["read"])

try:
    from .limits import limiter
    from .utils import limit_key_from_request
except Exception:
    limiter = None
    limit_key_from_request = None

try:
    from prometheus_client import Counter
    CSV_REQS = Counter("csv_export_requests_total", "CSV export requests", ["kind", "result"])
except Exception:
    CSV_REQS = None

@router.get("/strategies")
def list_strategies(db: Session = Depends(get_db)):
    items = db.query(models.Strategy).all()
    return {"items": [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "category": s.category,
            "status": s.status,
            "markets": s.markets,
            "lastHeartbeat": s.last_heartbeat.isoformat() if s.last_heartbeat else None
        } for s in items
    ]}


@router.get("/strategies/{strategy_id}")
def get_strategy(strategy_id: str, db: Session = Depends(get_db)):
    s = db.get(models.Strategy, strategy_id)
    if not s:
        return {"error": "not_found"}, 404
    return {
        "id": s.id, "name": s.name, "description": s.description,
        "category": s.category, "status": s.status, "markets": s.markets,
        "lastHeartbeat": s.last_heartbeat.isoformat() if s.last_heartbeat else None
    }


@router.get("/strategies/{strategy_id}/trades")
def get_trades(strategy_id: str, limit: int = 200, db: Session = Depends(get_db)):
    q = db.query(models.Trade).filter(models.Trade.strategy_id == strategy_id).order_by(models.Trade.ts.desc()).limit(limit)
    items = []
    for t in q:
        items.append({
            "orderId": t.order_id, "ts": t.ts.isoformat(), "market": t.market, "venue": t.venue,
            "side": t.side, "type": t.type, "status": t.status, "fillPx": t.fill_px,
            "qty": t.qty, "fees": t.fees, "leverage": t.leverage, "meta": t.meta
        })
    return {"items": items}


@router.get("/strategies/{strategy_id}/positions")
def get_positions(strategy_id: str, limit: int = 200, db: Session = Depends(get_db)):
    q = db.query(models.Position).filter(models.Position.strategy_id == strategy_id).order_by(models.Position.ts.desc()).limit(limit)
    items = []
    for p in q:
        items.append({
            "ts": p.ts.isoformat(), "market": p.market, "venue": p.venue,
            "qty": p.qty, "avgEntry": p.avg_entry, "mark": p.mark, "upnl": p.upnl,
            "fundingAccrued": p.funding_accrued, "leverage": p.leverage
        })
    return {"items": items}


@router.get("/strategies/{strategy_id}/performance")
def get_performance(strategy_id: str, window: str = "30d", db: Session = Depends(get_db)):
    # Basic sums for now (metrics job will enhance later)
    since = {"7d": 7, "30d": 30}.get(window, 365)
    cutoff = datetime.now(timezone.utc) - timedelta(days=since)
    realized = db.query(func.coalesce(func.sum(models.PnL.realized_pnl), 0.0)).filter(models.PnL.strategy_id == strategy_id, models.PnL.ts >= cutoff).scalar()
    fees = db.query(func.coalesce(func.sum(models.PnL.fees), 0.0)).filter(models.PnL.strategy_id == strategy_id, models.PnL.ts >= cutoff).scalar()
    funding = db.query(func.coalesce(func.sum(models.PnL.funding_pnl), 0.0)).filter(models.PnL.strategy_id == strategy_id, models.PnL.ts >= cutoff).scalar()
    trades = db.query(models.Trade).filter(models.Trade.strategy_id == strategy_id, models.Trade.ts >= cutoff, models.Trade.status == "FILLED").count()
    return {
        "equityCurve": [],
        "realizedPnL": float(realized or 0.0),
        "unrealizedPnL": 0.0,
        "roe": None,
        "maxDrawdown": None,
        "hitRate": None,
        "trades": int(trades or 0),
        "fees": float(fees or 0.0),
        "fundingPnL": float(funding or 0.0),
        "slippage": None
    }


@router.get("/strategies/{strategy_id}/trades.csv")
def export_trades_csv(strategy_id: str, start: Optional[str] = None, end: Optional[str] = None, side: Optional[str] = None, status: Optional[str] = None, sort: str = 'time', dir: str = 'desc', chunk_size: int = 5000, db: Session = Depends(get_db), request: Request = None):
    # Build base query with filters
    q = db.query(models.Trade).filter(models.Trade.strategy_id == strategy_id)
    # parse start/end
    def _parse_datetime_local(v: Optional[str]):
        if not v: return None
        try:
            if v.isdigit():
                vi = int(v)
                if vi > 10 ** 10: return datetime.utcfromtimestamp(vi/1000.0)
                return datetime.utcfromtimestamp(vi)
        except Exception:
            pass
        try:
            return datetime.fromisoformat(v)
        except Exception:
            return None

    start_dt = _parse_datetime_local(start)
    end_dt = _parse_datetime_local(end)
    if start and start_dt is None:
        raise HTTPException(status_code=400, detail=f"invalid start datetime: {start}")
    if end and end_dt is None:
        raise HTTPException(status_code=400, detail=f"invalid end datetime: {end}")
    if start_dt: q = q.filter(models.Trade.ts >= start_dt)
    if end_dt: q = q.filter(models.Trade.ts <= end_dt)
    if side: q = q.filter(models.Trade.side == side)
    if status: q = q.filter(models.Trade.status == status)

    # rate limiting per IP/API key
    try:
        if limiter and limit_key_from_request and request is not None:
            key = limit_key_from_request(request)
            if not limiter.allow(key):
                if CSV_REQS:
                    CSV_REQS.labels("trades", "rate_limited").inc()
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="CSV rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        # on any limiter error, allow the request (fail open) but record metric
        if CSV_REQS:
            CSV_REQS.labels("trades", "error").inc()

    # determine ordering
    order_dir = (dir or 'desc').lower()
    if order_dir not in ('asc', 'desc'):
        raise HTTPException(status_code=400, detail=f"invalid dir: {dir}")
    if sort == 'time':
        order_cols = [models.Trade.ts.asc(), models.Trade.id.asc()] if order_dir == 'asc' else [models.Trade.ts.desc(), models.Trade.id.desc()]
    elif sort == 'price':
        order_cols = [models.Trade.fill_px.asc(), models.Trade.id.asc()] if order_dir == 'asc' else [models.Trade.fill_px.desc(), models.Trade.id.desc()]
    elif sort == 'qty':
        order_cols = [models.Trade.qty.asc(), models.Trade.id.asc()] if order_dir == 'asc' else [models.Trade.qty.desc(), models.Trade.id.desc()]
    else:
        # fallback to time
        order_cols = [models.Trade.ts.desc(), models.Trade.id.desc()]

    def iter_rows():
        import csv, io
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        meta = {'strategyId': strategy_id, 'sort': sort, 'dir': dir, 'start': start, 'end': end, 'side': side, 'status': status, 'chunk_size': chunk_size}
        yield ("# " + ", ".join([f"{k}={v}" for k, v in meta.items() if v is not None]) + "\n")
        writer.writerow(['ts','side','status','qty','price','tradeId','fillPx','market','venue'])
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)

        last_ts = None
        last_id = None
        base_q = q
        while True:
            q_iter = base_q
            if last_ts is not None:
                if order_dir == 'asc':
                    q_iter = q_iter.filter((models.Trade.ts > last_ts) | ((models.Trade.ts == last_ts) & (models.Trade.id > last_id)))
                else:
                    q_iter = q_iter.filter((models.Trade.ts < last_ts) | ((models.Trade.ts == last_ts) & (models.Trade.id < last_id)))
            q_iter = q_iter.order_by(*order_cols).limit(chunk_size)
            rows = q_iter.all()
            if not rows: break
            for t in rows:
                writer.writerow([t.ts.isoformat() if t.ts else '', t.side or '', t.status or '', t.qty or '', t.price or '', t.trade_id or '', t.fill_px or '', t.market or '', t.venue or ''])
                yield buf.getvalue(); buf.seek(0); buf.truncate(0)
            last = rows[-1]
            last_ts = last.ts
            last_id = last.id
            if len(rows) < chunk_size: break

    filename = f"{strategy_id}-trades.csv"
    return Response(iter_rows(), media_type='text/csv', headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


@router.get("/leaderboard")
def leaderboard(window: str = "30d", db: Session = Depends(get_db)):
    since = {"7d": 7, "30d": 30}.get(window, 365)
    cutoff = datetime.now(timezone.utc) - timedelta(days=since)
    rows = db.query(
        models.PnL.strategy_id,
        func.coalesce(func.sum(models.PnL.realized_pnl), 0.0).label("pnl")
    ).filter(
        models.PnL.ts >= cutoff
    ).group_by(
        models.PnL.strategy_id
    ).order_by(
        desc("pnl")
    ).all()
    return {"items": [{"strategyId": r[0], "realizedPnL": float(r[1])} for r in rows]}


@router.post("/strategies/{strategy_id}/heartbeat")
def post_heartbeat(strategy_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    # payload: {ts: ISO8601 or epoch_ms, status: 'ok'|'warn'|'error', meta: {...}}
    ts = payload.get('ts')
    try:
        if isinstance(ts, (int, float)):
            last_seen = datetime.utcfromtimestamp(ts/1000.0) if ts > 1e10 else datetime.utcfromtimestamp(ts)
        else:
            last_seen = datetime.fromisoformat(ts) if ts else datetime.utcnow()
    except Exception:
        last_seen = datetime.utcnow()
    # upsert into strategy_status
    try:
        existing = db.get(StrategyStatus, strategy_id)
        if existing:
            existing.last_seen_ts = last_seen
            if payload.get('last_trade_ts'):
                try:
                    existing.last_trade_ts = datetime.fromisoformat(payload.get('last_trade_ts'))
                except Exception:
                    pass
            existing.open_position = payload.get('open_position')
            existing.pnl_realized = payload.get('pnl_realized')
            existing.pnl_unrealized = payload.get('pnl_unrealized')
            db.add(existing)
        else:
            ss = StrategyStatus(strategy_id=strategy_id, last_seen_ts=last_seen, open_position=payload.get('open_position'), pnl_realized=payload.get('pnl_realized'), pnl_unrealized=payload.get('pnl_unrealized'))
            db.add(ss)
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"ok": False, "error": "db_error"}
    return {"ok": True, "strategy_id": strategy_id, "last_seen": last_seen.isoformat()}


@router.get("/debug/fail")
def debug_fail(request: Request, fail: Optional[int] = None):
    """Return 500 when ?fail=1 or header X-Debug-Fail: 1 is present. Used for alert testing."""
    try:
        header_val = request.headers.get("x-debug-fail")
        if str(fail) == '1' or (header_val and header_val == '1'):
            raise HTTPException(status_code=500, detail="debug induced failure")
    except HTTPException:
        raise
    return {"ok": True, "debug": False}