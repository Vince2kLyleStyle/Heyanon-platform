from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    buy = "buy"
    sell = "sell"


class TradeType(str, Enum):
    market = "market"
    limit = "limit"


class TradeStatus(str, Enum):
    new = "new"
    filled = "filled"
    cancelled = "cancelled"


class TradeEvent(BaseModel):
    orderId: str = Field(..., min_length=1)
    ts: datetime
    # 'symbol' is the preferred field (e.g. BTC-PERP). 'market' is accepted for backward compatibility.
    symbol: Optional[str] = None
    market: Optional[str] = None
    venue: str
    strategyId: str
    side: Side
    type: TradeType
    status: TradeStatus
    entryPx: Optional[float] = None
    fillPx: Optional[float] = None
    qty: float = Field(..., gt=0)
    fees: float = Field(..., ge=0)
    leverage: Optional[float] = None
    idempotencyKey: Optional[str] = Field(None, min_length=1)
    meta: Optional[Dict] = None


class PositionSnapshot(BaseModel):
    ts: datetime
    market: str
    venue: str
    strategyId: str
    qty: float
    avgEntry: float
    mark: float
    upnl: float
    fundingAccrued: float
    leverage: float
    riskCaps: Optional[Dict] = None


class PnLAttribution(BaseModel):
    ts: datetime
    strategyId: str
    realizedPnL: float
    unrealizedPnL: float
    fees: float = Field(..., ge=0)
    fundingPnL: float
    slippage: float
    basis: str