from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from .db import get_db
from . import models
from pydantic import BaseModel
from datetime import datetime
from typing import Union
from fastapi import Path

router = APIRouter(prefix="/v1/copy", tags=["copy"])

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


class SubscriberIn(BaseModel):
    strategy_id: str
    risk_multiplier: float = 1.0
    max_leverage: float = 1.0
    enabled: bool = True
    notes: Optional[str] = None


class SubscriberOut(SubscriberIn):
    id: int


class ExecutionOut(BaseModel):
    id: int
    strategy_id: Optional[str]
    subscriber_id: Optional[int]
    signal_trade_id: Optional[int]
    side: Optional[str]
    qty: Optional[float]
    price: Optional[float]
    ts: Optional[datetime]
    status: Optional[str]
    error: Optional[str]
    latency_ms: Optional[int]
    notional_usd: Optional[float]
    copied_qty: Optional[float]


class ExecutionIn(BaseModel):
    strategy_id: str
    subscriber_id: int
    signal_trade_id: Optional[int]
    side: Optional[str]
    qty: Optional[float]
    price: Optional[float]
    status: Optional[str]
    error: Optional[str]
    notional_usd: Optional[float]
    copied_qty: Optional[float]



@router.post("/subscribe", response_model=SubscriberOut)
def create_subscriber(payload: SubscriberIn, db: Session = Depends(get_db)):
    sub = models.Subscriber(
        strategy_id=payload.strategy_id,
        risk_multiplier=payload.risk_multiplier,
        max_leverage=payload.max_leverage,
        enabled=1 if payload.enabled else 0,
        notes=payload.notes,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return SubscriberOut(id=sub.id, **payload.dict())


@router.get("/subscribers", response_model=List[SubscriberOut])
def list_subscribers(strategyId: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Subscriber)
    if strategyId:
        q = q.filter(models.Subscriber.strategy_id == strategyId)
    subs = q.limit(100).all()
    out = []
    for s in subs:
        out.append(SubscriberOut(id=s.id, strategy_id=s.strategy_id, risk_multiplier=s.risk_multiplier, max_leverage=s.max_leverage, enabled=bool(s.enabled), notes=s.notes))
    return out


@router.patch("/subscribers/{subscriber_id}")
def update_subscriber(subscriber_id: int = Path(...), payload: SubscriberIn = None, db: Session = Depends(get_db)):
    sub = db.query(models.Subscriber).filter(models.Subscriber.id == subscriber_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="subscriber not found")
    data = payload.dict(exclude_unset=True)
    # map API keys to model fields
    if "risk_multiplier" in data:
        sub.risk_multiplier = data["risk_multiplier"]
    if "max_leverage" in data:
        sub.max_leverage = data["max_leverage"]
    if "enabled" in data:
        sub.enabled = 1 if data["enabled"] else 0
    if "notes" in data:
        sub.notes = data["notes"]
    if "max_notional_usd" in data:
        sub.max_notional_usd = data["max_notional_usd"]
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return SubscriberOut(id=sub.id, strategy_id=sub.strategy_id, risk_multiplier=sub.risk_multiplier, max_leverage=sub.max_leverage, enabled=bool(sub.enabled), notes=sub.notes)


class ExecutionPage(BaseModel):
    items: List[ExecutionOut]
    total: Optional[int]
    has_next: bool
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None


def _parse_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    # Accept ISO string or epoch (seconds or milliseconds)
    val = str(val)
    # try integer epoch
    try:
        if val.isdigit():
            v = int(val)
            # ms if value looks > 10**10
            if v > 10 ** 10:
                return datetime.utcfromtimestamp(v / 1000.0)
            else:
                return datetime.utcfromtimestamp(v)
    except Exception:
        pass
    # try ISO parse
    try:
        return datetime.fromisoformat(val)
    except Exception:
        try:
            # fallback common format
            return datetime.strptime(val, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None


@router.get("/executions", response_model=ExecutionPage)
def list_executions(strategyId: Optional[str] = None, limit: int = 100, offset: int = 0, start: Optional[str] = None, end: Optional[str] = None, sort: Optional[str] = None, dir: Optional[str] = None, cursor: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Execution)
    if strategyId:
        q = q.filter(models.Execution.strategy_id == strategyId)
    # parse optional start/end filters (ISO or epoch seconds/ms)
    # Strict validation: if start/end supplied but invalid, return 400
    if start is not None:
        start_dt = _parse_datetime(start)
        if start_dt is None:
            raise HTTPException(status_code=400, detail=f"invalid start datetime: {start}")
        q = q.filter(models.Execution.ts >= start_dt)
    if end is not None:
        end_dt = _parse_datetime(end)
        if end_dt is None:
            raise HTTPException(status_code=400, detail=f"invalid end datetime: {end}")
        q = q.filter(models.Execution.ts <= end_dt)
    # server-side sorting
    if sort:
        sort = sort.lower()
        dir = (dir or 'desc').lower()
        if dir not in ('asc', 'desc'):
            raise HTTPException(status_code=400, detail=f"invalid sort dir: {dir}")
        col_map = {
            'time': models.Execution.ts,
            'side': models.Execution.side,
            'status': models.Execution.status,
            'notional': models.Execution.notional_usd,
        }
        col = col_map.get(sort)
        if not col:
            raise HTTPException(status_code=400, detail=f"invalid sort column: {sort}")
        if dir == 'asc':
            q = q.order_by(col.asc())
        else:
            q = q.order_by(col.desc())
    else:
        q = q.order_by(models.Execution.ts.desc())
    # Support keyset (cursor) pagination when cursor provided and sorting by time (or unspecified = time)
    total = None
    next_cursor = None
    prev_cursor = None
    # keep a base query (before cursor trickery) to compute prev/next existence
    q_base = q
    if cursor and (not sort or sort == 'time'):
        import base64
        try:
            decoded = base64.b64decode(cursor.encode()).decode()
            parts = decoded.split('::')
            cur_ts = datetime.fromisoformat(parts[0]) if parts[0] else None
            cur_id = int(parts[1]) if len(parts) > 1 and parts[1] else None
        except Exception:
            raise HTTPException(status_code=400, detail=f"invalid cursor: {cursor}")

        # for desc (default) fetch older than cursor; for asc fetch newer
        if (not dir) or dir.lower() == 'desc':
            if cur_ts is not None:
                if cur_id is not None:
                    q = q.filter((models.Execution.ts < cur_ts) | ((models.Execution.ts == cur_ts) & (models.Execution.id < cur_id)))
                else:
                    q = q.filter(models.Execution.ts < cur_ts)
            q = q.order_by(models.Execution.ts.desc(), models.Execution.id.desc())
        else:
            if cur_ts is not None:
                if cur_id is not None:
                    q = q.filter((models.Execution.ts > cur_ts) | ((models.Execution.ts == cur_ts) & (models.Execution.id > cur_id)))
                else:
                    q = q.filter(models.Execution.ts > cur_ts)
            q = q.order_by(models.Execution.ts.asc(), models.Execution.id.asc())

        rows = q.limit(limit + 1).all()
        execs = rows[:limit]
        has_next = len(rows) > limit
        total = None
        if has_next:
            last = execs[-1]
            token = f"{(last.ts.isoformat() if last.ts else '')}::{last.id}"
            next_cursor = base64.b64encode(token.encode()).decode()
        # compute deterministic prev_cursor by fetching the preceding page (reverse order)
        if len(execs) > 0:
            first = execs[0]
            try:
                # Build a query from the original base filters for the 'preceding' set.
                # For DESC ordering (default) the preceding rows are those NEWER than the current first (ts > first.ts or same ts and id > first.id).
                # For ASC ordering the preceding rows are those OLDER than the current first (ts < first.ts or same ts and id < first.id).
                preceding_q = q_base
                if (not dir) or dir.lower() == 'desc':
                    preceding_q = preceding_q.filter((models.Execution.ts > first.ts) | ((models.Execution.ts == first.ts) & (models.Execution.id > first.id)))
                    # order ascending so the last row of that ascending page is the immediate predecessor boundary
                    preceding_rows = preceding_q.order_by(models.Execution.ts.asc(), models.Execution.id.asc()).limit(limit).all()
                else:
                    preceding_q = preceding_q.filter((models.Execution.ts < first.ts) | ((models.Execution.ts == first.ts) & (models.Execution.id < first.id)))
                    # order descending so the last row of that descending page is the immediate predecessor boundary
                    preceding_rows = preceding_q.order_by(models.Execution.ts.desc(), models.Execution.id.desc()).limit(limit).all()

                if preceding_rows:
                    pred = preceding_rows[-1]
                    token_prev = f"{(pred.ts.isoformat() if pred.ts else '')}::{pred.id}"
                    prev_cursor = base64.b64encode(token_prev.encode()).decode()
            except Exception:
                prev_cursor = None
    else:
        total = q.count()
        q = q.offset(offset).limit(limit)
        execs = q.all()
    out = []
    for e in execs:
        out.append(ExecutionOut(
            id=e.id,
            strategy_id=e.strategy_id,
            subscriber_id=e.subscriber_id,
            signal_trade_id=e.signal_trade_id,
            side=e.side,
            qty=e.qty,
            price=e.price,
            ts=e.ts,
            status=e.status,
            error=e.error,
            latency_ms=e.latency_ms,
            notional_usd=e.notional_usd,
            copied_qty=e.copied_qty,
        ))
    # compute has_next when not using keyset
    if cursor and (not sort or sort == 'time'):
        return ExecutionPage(items=out, total=total or None, has_next=has_next, next_cursor=next_cursor or None, prev_cursor=prev_cursor or None)
    has_next = (offset + len(execs)) < total
    return ExecutionPage(items=out, total=total, has_next=has_next)


@router.get("/executions.csv")
def export_executions_csv(strategyId: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, sort: Optional[str] = None, dir: Optional[str] = None, side: Optional[str] = None, status: Optional[str] = None, chunk_size: int = 5000, db: Session = Depends(get_db), request: Request = None):
    q = db.query(models.Execution)
    if strategyId:
        q = q.filter(models.Execution.strategy_id == strategyId)
    # time filters
    start_dt = _parse_datetime(start) if start else None
    end_dt = _parse_datetime(end) if end else None
    if start and start_dt is None:
        raise HTTPException(status_code=400, detail=f"invalid start datetime: {start}")
    if end and end_dt is None:
        raise HTTPException(status_code=400, detail=f"invalid end datetime: {end}")
    if start_dt:
        q = q.filter(models.Execution.ts >= start_dt)
    if end_dt:
        q = q.filter(models.Execution.ts <= end_dt)
    # rate limiting per IP/API key
    try:
        if limiter and limit_key_from_request and request is not None:
            key = limit_key_from_request(request)
            if not limiter.allow(key):
                if CSV_REQS:
                    CSV_REQS.labels("executions", "rate_limited").inc()
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="CSV rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        if CSV_REQS:
            CSV_REQS.labels("executions", "error").inc()

    # optional side/status filters
    if side:
        q = q.filter(models.Execution.side == side)
    if status:
        q = q.filter(models.Execution.status == status)
    # cap chunk_size to a sane maximum to avoid excessive memory/IO pressure
    MAX_CHUNK = 10000
    try:
        # ensure chunk_size is a positive int
        chunk_size = int(chunk_size)
    except Exception:
        chunk_size = 5000
    if chunk_size < 1:
        chunk_size = 1
    if chunk_size > MAX_CHUNK:
        chunk_size = MAX_CHUNK
    # apply sort
    if sort:
        sort = sort.lower()
        dir = (dir or 'desc').lower()
        col_map = {
            'time': models.Execution.ts,
            'side': models.Execution.side,
            'status': models.Execution.status,
            'notional': models.Execution.notional_usd,
        }
        col = col_map.get(sort)
        if not col:
            raise HTTPException(status_code=400, detail=f"invalid sort column: {sort}")
        q = q.order_by(col.asc() if dir == 'asc' else col.desc())
    def iter_rows():
        import csv, io, base64
        buf = io.StringIO()
        # ensure proper RFC4180 quoting for commas/quotes/newlines
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)

        # comment header with filters/sort for auditing (many CSV readers skip leading # lines)
        meta = {
            'strategyId': strategyId,
            'sort': sort,
            'dir': dir,
            'start': start,
            'end': end,
            'side': side,
            'status': status,
            'chunk_size': chunk_size,
        }
        yield ("# " + ", ".join([f"{k}={v}" for k, v in meta.items() if v is not None]) + "\n")

        # header row
        writer.writerow(['ts','strategy_id','subscriber_id','signal_trade_id','side','qty','price','status','latency_ms','copied_qty','notional_usd','error'])
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)

        # We'll page using a simple keyset cursor (last_ts, last_id). Start with no cursor.
        last_ts = None
        last_id = None
        # If sorting by time asc/desc, we prefer to iterate in that order; otherwise default to desc.
        order_dir = (dir or 'desc').lower()

        base_q = q
        # apply ordering for chunking (we'll request chunk_size rows each iteration)
        if (not sort) or sort == 'time':
            if order_dir == 'asc':
                order_cols = [models.Execution.ts.asc(), models.Execution.id.asc()]
            else:
                order_cols = [models.Execution.ts.desc(), models.Execution.id.desc()]
        else:
            # non-time sorts: fall back to timestamp desc to preserve deterministic ordering
            order_cols = [models.Execution.ts.desc(), models.Execution.id.desc()]

        while True:
            q_iter = base_q
            # apply keyset condition if we have a last cursor
            if last_ts is not None:
                if order_dir == 'asc':
                    q_iter = q_iter.filter((models.Execution.ts > last_ts) | ((models.Execution.ts == last_ts) & (models.Execution.id > last_id)))
                else:
                    q_iter = q_iter.filter((models.Execution.ts < last_ts) | ((models.Execution.ts == last_ts) & (models.Execution.id < last_id)))

            q_iter = q_iter.order_by(*order_cols).limit(chunk_size)
            rows = q_iter.all()
            if not rows:
                break
            for e in rows:
                writer.writerow([
                    e.ts.isoformat() if e.ts else '',
                    e.strategy_id or '',
                    e.subscriber_id or '',
                    e.signal_trade_id or '',
                    e.side or '',
                    e.qty if e.qty is not None else '',
                    e.price if e.price is not None else '',
                    e.status or '',
                    e.latency_ms if e.latency_ms is not None else '',
                    e.copied_qty if e.copied_qty is not None else '',
                    e.notional_usd if e.notional_usd is not None else '',
                    e.error or '',
                ])
                yield buf.getvalue()
                buf.seek(0); buf.truncate(0)
            # set last_ts/last_id to the last row in this chunk for next iteration
            last = rows[-1]
            last_ts = last.ts
            last_id = last.id
            # if fewer than chunk_size rows returned, we've reached the end
            if len(rows) < chunk_size:
                break
            

    filename = f"{strategyId or 'executions'}-executions.csv"
    return StreamingResponse(iter_rows(), media_type='text/csv', headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


@router.post("/executions", response_model=ExecutionOut)
def create_execution(payload: ExecutionIn, db: Session = Depends(get_db)):
    # idempotent: avoid duplicate for same signal_trade_id + subscriber_id
    # Try to find existing execution (idempotent key)
    if payload.signal_trade_id:
        exists = db.query(models.Execution).filter(models.Execution.strategy_id == payload.strategy_id, models.Execution.signal_trade_id == payload.signal_trade_id, models.Execution.subscriber_id == payload.subscriber_id).first()
        if exists:
            # update status/error if provided
            updated = False
            if payload.status and payload.status != exists.status:
                exists.status = payload.status
                updated = True
            if payload.error and payload.error != exists.error:
                exists.error = payload.error
                updated = True
            if payload.notional_usd:
                exists.notional_usd = payload.notional_usd
                updated = True
            if payload.copied_qty:
                exists.copied_qty = payload.copied_qty
                updated = True
            if updated:
                db.add(exists)
                db.commit()
                db.refresh(exists)
            return ExecutionOut(
                id=exists.id,
                strategy_id=exists.strategy_id,
                subscriber_id=exists.subscriber_id,
                signal_trade_id=exists.signal_trade_id,
                side=exists.side,
                qty=exists.qty,
                price=exists.price,
                ts=exists.ts,
                status=exists.status,
                error=exists.error,
                latency_ms=exists.latency_ms,
                notional_usd=exists.notional_usd,
                copied_qty=exists.copied_qty,
            )

    e = models.Execution(
        strategy_id=payload.strategy_id,
        subscriber_id=payload.subscriber_id,
        signal_trade_id=payload.signal_trade_id,
        side=payload.side,
        qty=payload.qty,
        price=payload.price,
        status=payload.status or "pending",
        error=payload.error,
        notional_usd=payload.notional_usd,
        copied_qty=payload.copied_qty,
    )
    db.add(e)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # if unique constraint violated, return existing
        exists = db.query(models.Execution).filter(models.Execution.strategy_id == payload.strategy_id, models.Execution.signal_trade_id == payload.signal_trade_id, models.Execution.subscriber_id == payload.subscriber_id).first()
        if exists:
            return ExecutionOut(
                id=exists.id,
                strategy_id=exists.strategy_id,
                subscriber_id=exists.subscriber_id,
                signal_trade_id=exists.signal_trade_id,
                side=exists.side,
                qty=exists.qty,
                price=exists.price,
                ts=exists.ts,
                status=exists.status,
                error=exists.error,
                latency_ms=exists.latency_ms,
                notional_usd=exists.notional_usd,
                copied_qty=exists.copied_qty,
            )
        raise
    db.refresh(e)
    return ExecutionOut(
        id=e.id,
        strategy_id=e.strategy_id,
        subscriber_id=e.subscriber_id,
        signal_trade_id=e.signal_trade_id,
        side=e.side,
        qty=e.qty,
        price=e.price,
        ts=e.ts,
        status=e.status,
        error=e.error,
        latency_ms=e.latency_ms,
        notional_usd=e.notional_usd,
        copied_qty=e.copied_qty,
    )
