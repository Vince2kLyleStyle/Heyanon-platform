# Home Screen Features

## Overview
Comprehensive home screen rebuild showing real-time trading system status, strategies, and execution logs.

## Backend Endpoints (`api/app/routes_summary.py`)

### GET /v1/summary
Returns system overview:
- `updatedAt`: Last signals refresh timestamp
- `regime`: Current market regime (Accumulation/Distribution/Neutral)
- `status`: System health (ok/degraded)
- `errors`: Count of errors in signals
- `mostRecentTrade`: Most recent trade object or null

### GET /v1/strategies
Returns array of strategies with:
- `id`, `name`, `description`, `category`, `status`
- `markets`: List of markets the strategy trades
- `lastEvaluated`: Last heartbeat timestamp
- `latestSignal`: Most recent signal (label, score, market, ts) or null

### GET /v1/strategies/{id}/logs
Returns last 50 log entries for a strategy:
- `ts`: ISO timestamp
- `event`: Event name (e.g., "strategy_tick", "regime_change")
- `details`: Optional JSON object with event details

### Testing Endpoints
- POST /v1/trades: Add demo trade
- POST /v1/strategies/{id}/logs: Add demo log entry

## Frontend Pages

### Home (`web/pages/index.tsx`)
**Hero Section:**
- Title "Mico's World"
- Updated timestamp
- Current regime
- Status badge (degraded vs ok)

**How to Read:**
- Static educational content explaining score, zones, ATR
- Footer disclaimer

**Most Recent Trade:**
- Strategy name and market
- Action (OBSERVED_LONG/SHORT)
- Price and timestamp
- "View logs" button linking to strategy detail

**Strategies Grid:**
- Strategy cards showing:
  - Name and status badge
  - Markets list
  - Last evaluated timestamp
  - Latest signal or "No signal yet" empty state
  - "View logs" button

**Graceful Empty States:**
- No recent trade: Card doesn't render
- No strategies: Shows "Strategies loading…"
- No signal: Shows "No signal yet — waiting for first evaluation"

### Strategy Detail (`web/pages/strategies/[id].tsx`)
**Features:**
- Back to Home button
- Strategy ID in header
- Last 50 logs in table format
- Columns: Time, Event, Details (JSON)
- Auto-refresh every 15s
- Empty state: "No logs yet. Check back once the strategy runs."
- Footer disclaimer

## Data Persistence
- **Trades:** `api/data/trades.json` (last 100 trades)
- **Logs:** `api/data/strategy_logs/{strategy_id}.jsonl` (append-only)

## Design Principles
- No BUY/SELL language (observational only: OBSERVED_LONG/SHORT)
- Footer disclaimer on every page
- Graceful handling of null/empty data
- Auto-refresh with polling intervals
- Clean, minimal styling with cards and badges
- Responsive grid layout for strategies

## Testing Demo Data
```powershell
# Add a demo trade
$body = @{ 
  strategyId = "scalp-perp-15m"
  name = "Scalp Perp (15m)"
  market = "BTCUSDT"
  action = "OBSERVED_LONG"
  price = 94250.50 
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/v1/trades" -Method POST -Body $body -ContentType "application/json"

# Add demo logs
$body = @{ 
  event = "strategy_tick"
  details = @{ market = "BTCUSDT"; signal = "ACCUMULATION"; score = 67 } 
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/v1/strategies/scalp-perp-15m/logs" -Method POST -Body $body -ContentType "application/json"
```

## Deployment
Changes auto-deploy to Render when pushed to GitHub `main` branch.

Production URL: https://heyanon-platform.onrender.com

## Next Steps
- Add authentication/authorization
- Implement real strategy execution logging
- Add filtering/sorting to logs table
- Export logs as CSV
- Add trade history pagination
- Real-time WebSocket updates instead of polling
