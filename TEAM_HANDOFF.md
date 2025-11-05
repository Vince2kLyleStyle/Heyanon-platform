# Team Handoff Message for Frontend Developer

---

**Subject:** Backend for swing-perp-16h is LIVE ✅

---

## Quick Summary

The production backend for the **swing-perp-16h** strategy is now fully operational and ready for frontend integration. All endpoints are tested, documented, and returning live data.

---

## API Endpoints (Use These)

**Base URL (Development):** `http://localhost:8000`  
**Base URL (Production):** *[Your production API URL here]*

### 1. Strategy Summary (Header + At-a-Glance)
```
GET /v1/strategies/swing-perp-16h
```
**Returns:** Complete strategy state including:
- `latestSignal` (label, score, market, price, trend, zones)
- `position` (symbol, side, qty, avg_entry, mark, upnl)
- `lastTrade` (ts, side, symbol, fill_px, qty)
- `lastEvaluated` timestamp
- `status` (Active/Waiting/Paused/Error)

### 2. Recent Logs (Evaluation Events)
```
GET /v1/strategies/swing-perp-16h/logs?limit=50
```
**Returns:** Recent evaluation/decision events with:
- `ts`, `event`, `market`, `note`, `score`, `label`, `price`
- Rich context like: `"score 60 • label Distribution • 0/4 long (blocked: no_fresh_WT_up,MFI1h<=50)"`

### 3. Trade Fills
```
GET /v1/strategies/swing-perp-16h/trades?limit=20
```
**Returns:** Individual trade executions (not paired):
- `ts`, `order_id`, `side`, `symbol`, `fill_px`, `qty`, `status`

### 4. Roundtrips (Entry/Exit Pairs with PnL)
```
GET /v1/strategies/swing-perp-16h/roundtrips?limit=10
```
**Returns:** Paired entry/exit trades:
- `entry_ts`, `exit_ts`, `side`, `symbol`, `entry_px`, `exit_px`, `qty`, `pnl_quote`, `hold_hours`

### 5. Strategy KPIs (Optional)
```
GET /v1/strategies/swing-perp-16h/kpis?window=7d
```
**Returns:** Aggregated metrics:
- `alertsIssued`, `avgScore`, `riskSuppressedCount`, `medianTimeBetweenEvalsMin`

### 6. Build Info (Optional)
```
GET /v1/version
```
**Returns:** `{sha, built_at, strategy_id, version}` for footer display

---

## Data Guarantees

✅ **Never crashes** - All endpoints return valid JSON with graceful empty defaults  
✅ **Score range:** Always 0-100 (clamped)  
✅ **Price precision:** 2 decimal places  
✅ **Terminology:** Only `OPEN_LONG`, `CLOSE_LONG`, `OPEN_SHORT`, `CLOSE_SHORT` (never BUY/SELL)  
✅ **Timestamps:** ISO 8601 format with timezone (UTC)  
✅ **Labels:** One of 5 values:
- `Observation` (neutral, waiting)
- `Accumulation` (bullish setup forming)
- `Aggressive Accumulation` (strong long signal)
- `Distribution` (bearish setup forming)
- `Aggressive Distribution` (strong short signal)

---

## Documentation

📘 **[API_CONTRACT.md](./API_CONTRACT.md)** - Complete endpoint specs with request/response shapes, data guarantees, frontend examples, testing commands

📦 **[FRONTEND_COMPONENT_SPECS.md](./FRONTEND_COMPONENT_SPECS.md)** - Ready-to-implement component specs (<1hr):
- `StrategyCard` with props and styling
- `RecentLogs` table with polling
- `TradeHistory` roundtrips table (optional)
- Helper functions (`timeAgo`, `statusBadge`, `formatK`)

🔧 **[RUNBOOK.md](./RUNBOOK.md)** - Troubleshooting guide for when things go wrong (UI degraded, logs stop, no trades, stale data)

---

## Quick Start (Copy/Paste)

### Test Endpoints (Local)
```powershell
# Strategy summary
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h" | ConvertTo-Json -Depth 5

# Recent logs (last 5)
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=5" | ConvertTo-Json -Depth 5

# Trades
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h/trades?limit=5" | ConvertTo-Json

# Roundtrips
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h/roundtrips?limit=3" | ConvertTo-Json

# KPIs (7 days)
Invoke-RestMethod "http://localhost:8000/v1/strategies/swing-perp-16h/kpis?window=7d" | ConvertTo-Json
```

### Fetch in React/Next.js
```javascript
// Strategy summary (poll every 30s)
const fetchStrategy = async () => {
  const res = await fetch('http://localhost:8000/v1/strategies/swing-perp-16h');
  const data = await res.json();
  setStrategy(data);
};

useEffect(() => {
  fetchStrategy();
  const interval = setInterval(fetchStrategy, 30000);
  return () => clearInterval(interval);
}, []);

// Recent logs
const fetchLogs = async () => {
  const res = await fetch('http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=20');
  const data = await res.json();
  setLogs(data);
};
```

---

## Current Status (as of deployment)

✅ **Bot posting evaluations:** Every 30s with rich context  
✅ **Logs endpoint:** Returning live data (11KB file, growing)  
✅ **Trades endpoint:** Empty `[]` (no trades yet, waiting for 4/4 filter alignment)  
✅ **Position:** FLAT (no open position)  
✅ **Latest Signal:** Distribution, score 60, price $103,706  
✅ **Strategy Status:** Active  

**Note on Trades:** The strategy is evaluating correctly but showing `"0/4 long (blocked: no_fresh_WT_up,MFI1h<=50)"`. This is **expected behavior** - trades will appear once market conditions align with all 4 filters. Monitor the logs endpoint to see when alignment occurs.

---

## Public Labels (Website-Only)

**Safe, observational language:**
- ✅ "Accumulation" / "Distribution" / "Observation"
- ✅ "Aggressive Accumulation" / "Aggressive Distribution"
- ❌ Never use "BUY" / "SELL" / "LONG" / "SHORT" in public-facing UI

**Trade terminology for logs:**
- Use `OPEN_LONG` / `CLOSE_LONG` when displaying raw trade data
- Translate for non-technical users: "Entry" / "Exit"

---

## CORS Configuration

**Allowed Origins:** Configured via `API_ORIGINS` env var in docker-compose.yml

**Current:** `http://localhost:3000` (development)

**Production:** Update to your frontend domain:
```yaml
environment:
  - API_ORIGINS=https://your-frontend-domain.com,https://www.your-frontend-domain.com
```

---

## Disclaimer Block (Always Visible)

```
How to Read:
- Score: 0–100 range. Higher means stronger alignment of trend (SMA20/50), volatility (ATR), RSI, and volume.
- Zones: Prices relative to SMA20 ± k·ATR define Accumulation/Distribution bands; k varies by asset risk.

Disclaimer: Informational only. Verify on-chain. Never DM-first. $MICO is independent and unaffiliated with Microsoft.
```

---

## Next Steps

1. ✅ Review **[FRONTEND_COMPONENT_SPECS.md](./FRONTEND_COMPONENT_SPECS.md)** for implementation guide
2. ✅ Test all endpoints using the Quick Start commands above
3. ✅ Implement `StrategyCard` and `RecentLogs` components (~45 min)
4. ✅ Add polling (30s interval) for live updates
5. ✅ Add disclaimer block on all pages
6. ✅ Deploy to production and update `NEXT_PUBLIC_API_URL` env var

---

## Support

**Questions?**
- Check **[API_CONTRACT.md](./API_CONTRACT.md)** for endpoint details
- Check **[RUNBOOK.md](./RUNBOOK.md)** for troubleshooting
- View live code: https://github.com/Vince2kLyleStyle/Heyanon-platform

**Issues?**
- API not responding: See RUNBOOK.md Section 1
- Logs not updating: See RUNBOOK.md Section 2
- No trades visible: See RUNBOOK.md Section 3 (expected if filters blocked)

---

**Happy coding! The backend is stable, tested, and ready for frontend integration. 🚀**

---

_Last updated: 2025-11-05 by @GitHub-Copilot_
