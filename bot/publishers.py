# Allow running bot as a script (python bot.py) without package context
try:
    from .serializers import build_trade_event, build_position_event  # type: ignore
except Exception:
    from serializers import build_trade_event, build_position_event
import uuid


def trade_idempotency_key(ev: dict) -> str:
    # prefer orderId as the canonical id for trades
    return f"trade:{ev.get('strategyId','')}:{ev.get('orderId','') or str(uuid.uuid4())}"


def position_idempotency_key(ev: dict) -> str:
    return f"position:{ev.get('strategyId','')}:{ev.get('positionId','') or str(uuid.uuid4())}:{ev.get('ts','') }"


def publish_trade(client, e: dict, session=None):
    ev = build_trade_event(e)
    idem = trade_idempotency_key(ev)
    return client.trade(ev, idempotency_key=idem)


def publish_position(client, p: dict, session=None):
    ev = build_position_event(p)
    idem = position_idempotency_key(ev)
    return client.position(ev, idempotency_key=idem)
