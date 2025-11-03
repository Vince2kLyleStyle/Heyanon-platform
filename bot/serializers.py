from datetime import datetime, timezone


def iso_now():
    # return an ISO8601 Z string
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_lower_enum(v):
    return v.lower() if isinstance(v, str) else v


def build_trade_event(e: dict) -> dict:
    # Build a TradeEvent matching api/app/schemas.TradeEvent
    strategy = e.get("strategy_id") or e.get("strategyId")
    order_id = e.get("order_id") or e.get("orderId") or e.get("trade_id") or e.get("tradeId") or ""
    symbol = e.get("symbol") or e.get("market") or None
    venue = e.get("exchange") or e.get("venue") or ""
    # map possible order type values to api TradeType (market/limit)
    ot = (e.get("order_type") or e.get("type") or "market")
    ttype = ot.lower() if isinstance(ot, str) else ot
    status = (e.get("status") or "new").lower() if isinstance(e.get("status") or "new", str) else e.get("status")

    return {
        "orderId": str(order_id),
        "ts": e.get("ts") or iso_now(),
        "symbol": str(symbol) if symbol is not None else None,
        "market": str(symbol) if symbol is not None else None,
        "venue": venue,
        "strategyId": str(strategy) if strategy is not None else "",
        "side": safe_lower_enum(e.get("side")),
        "type": ttype,
        "status": status,
        "entryPx": float(e.get("entry_px") or e.get("entryPx")) if (e.get("entry_px") or e.get("entryPx")) is not None else None,
        "fillPx": float(e.get("fill_px") or e.get("fillPx") or e.get("price") or e.get("fillPrice")) if (e.get("fill_px") or e.get("fillPx") or e.get("price") or e.get("fillPrice")) is not None else None,
        "qty": float(e.get("qty") or 0.0),
        "fees": float(e.get("fee") or e.get("fees") or 0.0),
        "leverage": float(e.get("leverage")) if e.get("leverage") is not None else None,
        "idempotencyKey": e.get("idempotency_key") or e.get("idempotencyKey") or None,
        "meta": e.get("meta", {})
    }


def build_position_event(p: dict) -> dict:
    # Build a PositionSnapshot matching api/app/schemas.PositionSnapshot
    strategy = p.get("strategy_id") or p.get("strategyId")
    market = p.get("market") or p.get("symbol")
    venue = p.get("exchange") or p.get("venue") or ""

    return {
        "ts": p.get("ts") or iso_now(),
        "market": str(market) if market is not None else "",
        "venue": venue,
        "strategyId": str(strategy) if strategy is not None else "",
        "qty": float(p.get("qty") or p.get("posSize") or 0.0),
        "avgEntry": float(p.get("avg_entry") or p.get("avgEntry") or p.get("avgEntryPrice") or 0.0),
        "mark": float(p.get("mark") or p.get("price") or 0.0),
        "upnl": float(p.get("upnl") or p.get("unrealizedPnl") or 0.0),
        "fundingAccrued": float(p.get("funding_accrued") or p.get("fundingAccrued") or 0.0),
        "leverage": float(p.get("leverage") or 1.0),
        "riskCaps": p.get("riskCaps") or p.get("risk_caps") or None,
    }
