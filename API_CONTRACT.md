# Production API Contract for swing-perp-16h Strategy

**Base URL**: `http://localhost:8000` (development) | `https://your-domain.com` (production)

**Strategy ID**: `swing-perp-16h` (canonical ID, website-only)

---

## Read-Only Endpoints (Frontend Consumption)

All endpoints return valid JSON and never crash. Empty states return empty arrays `[]` or `null` fields.

### 1. GET /v1/strategies/swing-perp-16h

Returns comprehensive strategy summary for header and at-a-glance display.

**Response Shape**:
```json
{
  "id": "swing-perp-16h",
  "name": "Swing Perp (16h)",
  "status": "Active | Waiting | Paused | Error",
  "lastEvaluated": "2025-11-05T15:36:56.005269+00:00",
  "latestSignal": {
    "label": "Observation | Accumulation | Aggressive Accumulation | Distribution | Aggressive Distribution",
    "score": 72,  // 0-100
    "market": "BTCUSDT",
    "price": 94250.50,
    "trend": {
      "sma20": "Up | Down",
      "sma50": "Up | Down",
      "rsi14": 58.7
    },
    "zones": {
      "deepAccum": 93500.00,
      "accum": 94000.00,
      "distrib": 95000.00,
      "safeDistrib": 95500.00
    }
  },
  "position": {
    "symbol": "BTCUSDT",
    "side": "LONG | FLAT | SHORT",
    "qty": 0.015,
    "avg_entry": 94100.00,
    "mark": 94250.00,
    "upnl": 2.25
  },
  "lastTrade": {
    "ts": "2025-11-05T12:33:00Z",
    "side": "OPEN_LONG | CLOSE_LONG | OPEN_SHORT | CLOSE_SHORT",
    "symbol": "BTCUSDT",
    "fill_px": 94200.00,
    "qty": 0.015,
    "order_id": "strat-open-1730812380000",
    "status": "filled | partial | canceled"
  }
}
```

**Notes**:
- `latestSignal` is `null` if no evaluations yet
- `lastTrade` is `null` if no trades executed yet
- `position.side` is `"FLAT"` when no position open
- All prices are rounded to 2 decimal places
- Score is clamped to 0-100 range

---

### 2. GET /v1/strategies/swing-perp-16h/logs?limit=50

Returns recent evaluation/decision events for the "Recent Logs" table.

**Query Parameters**:
- `limit` (optional, default 50): Max logs to return

**Response Shape**:
```json
[
  {
    "ts": "2025-11-05T15:48:33.818676+00:00",
    "level": "info",
    "event": "evaluation | signal_long | signal_short",
    "market": "BTC",
    "note": "score 72 • label Accumulation • 3/4 long filters",
    "score": 72,
    "label": "Accumulation",
    "price": 103708.60
  }
]
```

**Notes**:
- Returns empty array `[]` if no logs yet
- Logs are ordered newest first
- `note` field contains human-readable summary showing:
  - Score and label
  - Filter pass counts (e.g., "3/4 long filters")
  - Blockers if applicable (e.g., "blocked: no_fresh_WT_up")
- `event` values:
  - `evaluation`: Normal market assessment (no trade signal)
  - `signal_long`: Long entry signal generated
  - `signal_short`: Short entry signal generated

---

### 3. GET /v1/strategies/swing-perp-16h/trades?limit=20

Returns fills/executions (raw trades, not paired round-trips).

**Query Parameters**:
- `limit` (optional, default 20): Max trades to return

**Response Shape**:
```json
[
  {
    "ts": "2025-11-05T12:33:00+00:00",
    "order_id": "strat-open-1730812380000",
    "side": "OPEN_LONG | CLOSE_LONG | OPEN_SHORT | CLOSE_SHORT",
    "symbol": "BTCUSDT",
    "fill_px": 94200.00,
    "qty": 0.015,
    "status": "filled | partial | canceled"
  }
]
```

**Notes**:
- Returns empty array `[]` if no trades executed yet
- Trades ordered newest first
- Side labels use production terminology:
  - `OPEN_LONG`: Enter long position (buy)
  - `CLOSE_LONG`: Exit long position (sell)
  - `OPEN_SHORT`: Enter short position (sell)
  - `CLOSE_SHORT`: Exit short position (buy)
- Never uses `BUY/SELL` terminology

---

### 4. GET /v1/strategies/swing-perp-16h/roundtrips?limit=10

Returns paired entry/exit trades with PnL (computed round-trips).

**Query Parameters**:
- `limit` (optional, default 10): Max roundtrips to return

**Response Shape**:
```json
[
  {
    "entry_ts": "2025-11-05T10:15:00+00:00",
    "exit_ts": "2025-11-05T12:33:00+00:00",
    "side": "LONG | SHORT",
    "symbol": "BTCUSDT",
    "entry_px": 94100.00,
    "exit_px": 94850.00,
    "qty": 0.015,
    "pnl_quote": 11.25,  // PnL in quote currency (USDT)
    "hold_hours": 16.3
  }
]
```

**Notes**:
- Returns empty array `[]` if no completed round-trips yet
- Automatically pairs OPEN/CLOSE trades
- PnL calculation:
  - LONG: (exit_px - entry_px) × qty
  - SHORT: (entry_px - exit_px) × qty
- Ordered oldest to newest (most recent roundtrip last)

---

### 5. GET /v1/summary

Legacy homepage summary endpoint (still supported for backward compatibility).

**Response Shape**:
```json
{
  "updatedAt": 1730812416,  // Unix epoch seconds
  "regime": "Accumulation | Distribution | Observation",
  "status": "ok | degraded",
  "errors": 0,
  "mostRecentTrade": {
    // Same as lastTrade from /v1/strategies/swing-perp-16h
  }
}
```

**Notes**:
- `regime` derived from latest signal label
- `status` is `"degraded"` if strategy status is `"Error"`

---

## Write Endpoints (Bot-Only)

These endpoints are called automatically by the bot. Frontend should **not** call these.

### POST /v1/strategies/swing-perp-16h/logs

Bot posts evaluation logs after each cycle.

**Request Body**:
```json
{
  "event": "evaluation",
  "market": "BTCUSDT",
  "note": "score 71 • label Observation • 2/4 long filters",
  "score": 71,
  "label": "Observation",
  "price": 94250.50
}
```

**Response**: `{"ok": true}`

---

### POST /v1/strategies/swing-perp-16h/trades

Bot posts fills on trade executions.

**Request Body**:
```json
{
  "order_id": "strat-open-1730812380000",
  "side": "OPEN_LONG",
  "symbol": "BTCUSDT",
  "fill_px": 94200.00,
  "qty": 0.015,
  "status": "filled",
  "ts": "2025-11-05T12:33:00+00:00"
}
```

**Response**: `{"ok": true}`

---

## Data Guarantees

1. **Never crashes**: All endpoints return valid JSON with empty defaults if no data
2. **Score range**: Always 0-100 (clamped)
3. **Price precision**: 2 decimal places
4. **Terminology**: Only use OPEN_LONG/CLOSE_LONG/OPEN_SHORT/CLOSE_SHORT (never BUY/SELL)
5. **Timestamps**: ISO 8601 format with timezone (UTC)
6. **Labels**: One of 5 values:
   - Observation (neutral, waiting)
   - Accumulation (bullish setup forming)
   - Aggressive Accumulation (strong long signal)
   - Distribution (bearish setup forming)
   - Aggressive Distribution (strong short signal)

---

## Example Frontend Usage

### Strategy Card (Homepage)
```javascript
const response = await fetch('http://localhost:8000/v1/strategies/swing-perp-16h');
const strategy = await response.json();

// Display:
// - strategy.name: "Swing Perp (16h)"
// - strategy.status: "Active" (green badge)
// - strategy.latestSignal.label: "Accumulation"
// - strategy.latestSignal.score: 72
// - strategy.latestSignal.price: $94,250.50
// - strategy.position.side: "FLAT" or "LONG 0.015 @ $94,100"
```

### Recent Logs Table
```javascript
const response = await fetch('http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=20');
const logs = await response.json();

logs.forEach(log => {
  // Display row:
  // - log.ts: "2 min ago"
  // - log.event: "evaluation" (badge color: blue)
  // - log.note: "score 72 • label Accumulation • 3/4 long filters"
  // - log.score: 72 (color: green if >75, yellow if 50-75, red if <50)
});
```

### Trade History Table
```javascript
const response = await fetch('http://localhost:8000/v1/strategies/swing-perp-16h/roundtrips?limit=10');
const roundtrips = await response.json();

roundtrips.forEach(trip => {
  // Display row:
  // - trip.entry_ts: "Nov 5, 10:15 AM"
  // - trip.exit_ts: "Nov 5, 12:33 PM"
  // - trip.side: "LONG" (green) or "SHORT" (red)
  // - trip.entry_px: $94,100.00
  // - trip.exit_px: $94,850.00
  // - trip.pnl_quote: +$11.25 (green if positive, red if negative)
  // - trip.hold_hours: 16.3h
});
```

---

## Testing Endpoints

All endpoints are live and returning data:

```bash
# Strategy summary
curl http://localhost:8000/v1/strategies/swing-perp-16h

# Recent logs (last 5)
curl http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=5

# Trades
curl http://localhost:8000/v1/strategies/swing-perp-16h/trades?limit=10

# Roundtrips
curl http://localhost:8000/v1/strategies/swing-perp-16h/roundtrips?limit=5
```

**Current State** (as of deployment):
- ✅ Logs: Posting every 30 seconds with evaluation context
- ✅ Trades: Empty (no trades executed yet, waiting for signal alignment)
- ✅ Position: FLAT (no open position)
- ✅ Latest Signal: Distribution, score 60, price $103,589

---

## File Persistence

Backend uses simple file-based storage (no database required for these endpoints):

- `data/strategy_logs/swing-perp-16h.jsonl` - Append-only log entries
- `data/strategy_trades/swing-perp-16h.jsonl` - Append-only trade executions
- `data/strategy_state/swing-perp-16h.json` - Latest summary snapshot (overwritten)
- `data/strategy_roundtrips/swing-perp-16h.jsonl` - Computed roundtrips (optional)

All files are created automatically on first write.
