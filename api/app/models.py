from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from .db import Base
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc)


class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False)  # "perp" | "spot"
    status = Column(String, default="live")  # "live" | "paper" | "paused"
    risk_profile = Column(JSON, nullable=True)
    markets = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), default=now)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String, ForeignKey("strategies.id"), index=True)
    order_id = Column(String, index=True)
    ts = Column(DateTime(timezone=True), index=True)
    market = Column(String)
    # normalized symbol (e.g. BTC-PERP). kept separate for indexing/filtering.
    symbol = Column(String, index=True)
    venue = Column(String)
    side = Column(String)
    type = Column(String)
    status = Column(String)
    entry_px = Column(Float)
    fill_px = Column(Float)
    qty = Column(Float)
    fees = Column(Float)
    leverage = Column(Float, nullable=True)
    idempotency_key = Column(String, index=True)
    meta = Column(JSON)

    strategy = relationship("Strategy")

    __table_args__ = (
        Index("idx_trades_dedupe", "order_id", "idempotency_key", unique=True),
    )


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String, ForeignKey("strategies.id"), index=True)
    ts = Column(DateTime(timezone=True), index=True)
    market = Column(String)
    # normalized symbol copied from market for faster queries
    symbol = Column(String, index=True)
    venue = Column(String)
    qty = Column(Float)
    avg_entry = Column(Float)
    mark = Column(Float)
    upnl = Column(Float)
    funding_accrued = Column(Float)
    leverage = Column(Float)
    snapshot = Column(JSON, nullable=True)

    strategy = relationship("Strategy")

    __table_args__ = (
        Index("idx_positions_strategy_ts", "strategy_id", "ts"),
    )


class PnL(Base):
    __tablename__ = "pnl"
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String, ForeignKey("strategies.id"), index=True)
    ts = Column(DateTime(timezone=True), index=True)
    realized_pnl = Column(Float)
    unrealized_pnl = Column(Float)
    fees = Column(Float)
    funding_pnl = Column(Float)
    slippage = Column(Float)
    basis = Column(String)

    strategy = relationship("Strategy")

    __table_args__ = (
        Index("idx_pnl_strategy_ts", "strategy_id", "ts"),
    )


class Subscriber(Base):
    __tablename__ = "copy_subscribers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String, ForeignKey("strategies.id"), index=True)
    risk_multiplier = Column(Float, default=1.0)
    max_leverage = Column(Float, default=1.0)
    enabled = Column(Integer, default=1)  # 1 true, 0 false
    notes = Column(String, nullable=True)
    max_notional_usd = Column(Float, nullable=True)

    strategy = relationship("Strategy")


class Execution(Base):
    __tablename__ = "copy_executions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String, ForeignKey("strategies.id"), index=True)
    subscriber_id = Column(Integer, ForeignKey("copy_subscribers.id"), index=True)
    signal_trade_id = Column(Integer, nullable=True, index=True)
    side = Column(String)
    qty = Column(Float)
    price = Column(Float, nullable=True)
    ts = Column(DateTime(timezone=True), default=now)
    status = Column(String, default="pending")
    error = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    notional_usd = Column(Float, nullable=True)
    copied_qty = Column(Float, nullable=True)

    strategy = relationship("Strategy")
    subscriber = relationship("Subscriber")
