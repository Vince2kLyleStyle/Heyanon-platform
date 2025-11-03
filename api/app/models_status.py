from sqlalchemy import Column, String, Integer, DateTime, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import expression
from datetime import datetime

Base = declarative_base()


class StrategyStatus(Base):
    __tablename__ = 'strategy_status'
    strategy_id = Column(String, primary_key=True)
    last_seen_ts = Column(DateTime, nullable=False, server_default=func.now())
    last_trade_ts = Column(DateTime, nullable=True)
    open_position = Column(JSON, nullable=True)
    pnl_realized = Column(Integer, nullable=True)
    pnl_unrealized = Column(Integer, nullable=True)
