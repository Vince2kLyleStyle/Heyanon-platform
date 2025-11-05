"""
Async market signal engine for Heyanon Platform.

Fetches CoinGecko market data, computes indicators (SMA20/50, RSI14, ATR proxy, vol_spike),
calculates ATR-based zones, assigns safe action labels (no BUY/SELL wording), and maintains
a global state that updates every 60 seconds.

Safe labels: Observation | Accumulation | Aggressive Accumulation | Distribution | Aggressive Distribution
"""

import asyncio
import random
import statistics
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import pandas as pd
import httpx

VS_CURRENCY = "usd"
RETRY_DELAY = 10
POLL_SECONDS = 60

# Coins with CoinGecko IDs and risk tiers for zone multipliers
COINS = {
    "BTC": {"id": "bitcoin", "risk": "low"},
    "ETH": {"id": "ethereum", "risk": "low"},
    "SOL": {"id": "solana", "risk": "medium"},
    "AVAX": {"id": "avalanche-2", "risk": "medium"},
    "LINK": {"id": "chainlink", "risk": "medium"},
    "PYTH": {"id": "pyth-network", "risk": "high"},
}

# ATR-based zone multipliers (k1, k2) for risk tiers
RISK_MULTIPLIERS = {
    "low": (1.0, 1.8),
    "medium": (1.3, 2.2),
    "high": (1.6, 2.8),
}

# Global state: last_updated (ISO), signals (dict per symbol), errors (last 10)
state: Dict[str, Any] = {
    "last_updated": None,
    "regime": "Neutral",  # Neutral | Risk-ON | Risk-OFF (future: compute from BTC/SOL)
    "signals": {},
    "errors": [],
}


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute SMA20, SMA50, ATR14 proxy, RSI14, vol_spike."""
    if len(df) < 50:
        return df
    
    # SMA
    df["SMA20"] = df["close"].rolling(20).mean()
    df["SMA50"] = df["close"].rolling(50).mean()
    
    # ATR proxy: use simple range from high/low if available, else stddev of close
    # Since CoinGecko market_chart only has close, use rolling stddev as ATR proxy
    df["ATR14"] = df["close"].rolling(14).std()
    
    # RSI14
    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    down = down.replace(0, 1e-9)  # prevent div by zero
    roll_up = up.rolling(14).mean()
    roll_down = down.rolling(14).mean().replace(0, 1e-9)
    rs = roll_up / roll_down
    df["RSI14"] = 100 - (100 / (1 + rs))
    
    # Volume spike: volume > 2x 20-period SMA
    vma20 = df["volume"].rolling(20).mean()
    df["vol_spike"] = df["volume"] > 2 * vma20
    
    return df


def compute_zones(df: pd.DataFrame, risk: str) -> Optional[Dict[str, float]]:
    """
    Calculate ATR-based zones:
    - deepAccum = SMA20 - k2*ATR
    - accum = SMA20 - k1*ATR
    - distrib = SMA20 + k1*ATR
    - safeDistrib = SMA20 + k2*ATR
    """
    if len(df) < 50 or df["SMA20"].isna().iloc[-1] or df["ATR14"].isna().iloc[-1]:
        return None
    
    sma20 = float(df["SMA20"].iloc[-1])
    atr14 = float(df["ATR14"].iloc[-1])
    k1, k2 = RISK_MULTIPLIERS[risk]
    
    return {
        "deepAccum": max(0.0, sma20 - k2 * atr14),
        "accum": max(0.0, sma20 - k1 * atr14),
        "distrib": sma20 + k1 * atr14,
        "safeDistrib": sma20 + k2 * atr14,
        "current": float(df["close"].iloc[-1]),
        "sma20": sma20,
        "sma50": float(df["SMA50"].iloc[-1]) if not df["SMA50"].isna().iloc[-1] else sma20,
        "atr14": atr14,
    }


def label_from_zones(zones: Dict[str, float], regime: str) -> str:
    """
    Assign safe label based on price vs zones:
    - Aggressive Accumulation: price <= deepAccum
    - Accumulation: price <= accum
    - Aggressive Distribution: price >= safeDistrib
    - Distribution: price >= distrib
    - Observation: else
    """
    price = zones["current"]
    if price <= zones["deepAccum"]:
        return "Aggressive Accumulation"
    elif price <= zones["accum"]:
        return "Accumulation"
    elif price >= zones["safeDistrib"]:
        return "Aggressive Distribution"
    elif price >= zones["distrib"]:
        return "Distribution"
    else:
        return "Observation"


def compute_score(zones: Dict[str, float], df: pd.DataFrame, regime: str) -> int:
    """
    Compute confidence score (0-100):
    - regime alignment: 30 pts (neutral=15, risk-on with accum=30, etc.)
    - trend alignment: 30 pts (SMA20 > SMA50 + price near zones)
    - liquidity/vol: 20 pts (vol_spike + ATR relative to price)
    - RSI mean-reversion quality: 10 pts
    - vol pattern: 10 pts (consistent vol or spike)
    """
    score = 0
    
    # Regime (simplified: neutral=15, else 30 if aligned)
    # Future: compute regime from BTC/SOL; for now, always neutral
    score += 15
    
    # Trend alignment: SMA20 > SMA50 and price near zones
    if zones["sma20"] > zones["sma50"]:
        score += 15
    if abs(zones["current"] - zones["sma20"]) / zones["sma20"] < 0.05:
        score += 15
    
    # Liquidity/vol
    if not df["vol_spike"].isna().iloc[-1] and df["vol_spike"].iloc[-1]:
        score += 10
    if zones["atr14"] / zones["current"] > 0.02:  # ATR > 2% of price
        score += 10
    
    # RSI mean-reversion quality
    if not df["RSI14"].isna().iloc[-1]:
        rsi = float(df["RSI14"].iloc[-1])
        if rsi < 30 or rsi > 70:
            score += 10
    
    # Vol pattern: if recent volume > avg
    recent_vol = df["volume"].iloc[-5:].mean()
    avg_vol = df["volume"].mean()
    if recent_vol > avg_vol:
        score += 10
    
    return min(100, score)


async def fetch_market_data(
    client: httpx.AsyncClient, coin_id: str, days: int = 60, retries: int = 2
) -> Optional[pd.DataFrame]:
    """Fetch CoinGecko market_chart for a coin and return DataFrame with close, volume, timestamp."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": VS_CURRENCY, "days": days}
    
    for attempt in range(retries + 1):
        try:
            r = await client.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            
            if "prices" not in data or "total_volumes" not in data:
                return None
            
            df = pd.DataFrame(data["prices"], columns=["timestamp", "close"])
            df["volume"] = [v[1] for v in data["total_volumes"]]
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            return df
        
        except Exception as e:
            if attempt < retries:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            else:
                error_msg = f"{coin_id}: {str(e)}"
                state["errors"] = (state["errors"] + [error_msg])[-10:]
                return None


async def refresh_signals():
    """Fetch market data for all coins, compute indicators, zones, labels, and scores."""
    async with httpx.AsyncClient() as client:
        results = {}
        
        for symbol, info in COINS.items():
            df = await fetch_market_data(client, info["id"])
            if df is None or len(df) < 50:
                continue
            
            df = calculate_indicators(df)
            zones = compute_zones(df, info["risk"])
            if not zones:
                continue
            
            label = label_from_zones(zones, state["regime"])
            score = compute_score(zones, df, state["regime"])
            
            rsi = float(df["RSI14"].iloc[-1]) if not df["RSI14"].isna().iloc[-1] else None
            vol_spike = bool(df["vol_spike"].iloc[-1]) if not df["vol_spike"].isna().iloc[-1] else False
            
            results[symbol] = {
                "symbol": symbol,
                "label": label,
                "score": score,
                "price": zones["current"],
                "sma20": zones["sma20"],
                "sma50": zones["sma50"],
                "atr14": zones["atr14"],
                "rsi14": rsi,
                "vol_spike": vol_spike,
                "zones": {
                    "deepAccum": zones["deepAccum"],
                    "accum": zones["accum"],
                    "distrib": zones["distrib"],
                    "safeDistrib": zones["safeDistrib"],
                },
            }
            
            # Rate-limit friendly: small random delay between requests
            await asyncio.sleep(0.25 * random.uniform(0.8, 1.2))
        
        state["signals"] = results
        state["last_updated"] = datetime.now(timezone.utc).isoformat()


async def loop_runner():
    """Background task that refreshes signals every POLL_SECONDS."""
    while True:
        try:
            await refresh_signals()
        except Exception as e:
            error_msg = f"loop: {str(e)}"
            state["errors"] = (state["errors"] + [error_msg])[-10:]
        
        await asyncio.sleep(POLL_SECONDS)
