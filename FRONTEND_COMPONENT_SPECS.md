# Frontend Component Specs for swing-perp-16h

**Goal:** Implement in <1 hour. Clean, minimal, production-ready UI.

---

## 1. Strategy Summary Card

**Location:** Homepage (above existing content)

**Data Source:** `GET /v1/strategies/swing-perp-16h`

**Props:**
```typescript
interface StrategyCardProps {
  id: string;              // "swing-perp-16h"
  name: string;            // "Swing Perp (16h)"
  status: "Active" | "Waiting" | "Paused" | "Error";
  lastEvaluated: string;   // ISO timestamp
  latestSignal: {
    label: "Observation" | "Accumulation" | "Aggressive Accumulation" | "Distribution" | "Aggressive Distribution";
    score: number;         // 0-100
    market: string;        // "BTC"
    price: number;         // 103589.11
    trend: {
      sma20: "Up" | "Down";
      sma50: "Up" | "Down";
      rsi14: number;       // 58.7
    };
    zones: {
      deepAccum: number;
      accum: number;
      distrib: number;
      safeDistrib: number;
    };
  };
  position: {
    symbol: string;        // "BTCUSDT"
    side: "LONG" | "FLAT" | "SHORT";
    qty: number;
    avg_entry: number;
    mark: number;
    upnl: number;
  };
  lastTrade: {
    ts: string;
    side: "OPEN_LONG" | "CLOSE_LONG" | "OPEN_SHORT" | "CLOSE_SHORT";
    symbol: string;
    fill_px: number;
    qty: number;
  } | null;
}
```

**UI Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Swing Perp (16h) • Active • Last evaluated 2m ago  │
├─────────────────────────────────────────────────────┤
│ [Label • Score/100] | [Market • Price]             │
│ Distribution • 60   | BTC • $103,589.11            │
├─────────────────────────────────────────────────────┤
│ Trend: SMA20 ↑ / SMA50 ↑ • RSI 58.7                │
│ Zones: Deep $91K | Accum $91.5K | Dist $94.5K      │
├─────────────────────────────────────────────────────┤
│ Position: FLAT (no open position)                   │
│ Last Trade: None                                     │
└─────────────────────────────────────────────────────┘
```

**Styling:**
- Status badge: Green (Active), Yellow (Waiting), Red (Error/Paused)
- Label badge:
  - `Aggressive Accumulation`: Dark green
  - `Accumulation`: Light green
  - `Observation`: Gray
  - `Distribution`: Light red
  - `Aggressive Distribution`: Dark red
- Score: Green (>75), Yellow (50-75), Red (<50)
- Position side: Green (LONG), Gray (FLAT), Red (SHORT)

**Implementation:**
```tsx
export function StrategyCard({ strategy }: { strategy: StrategyCardProps }) {
  const labelColor = {
    "Aggressive Accumulation": "bg-green-700",
    "Accumulation": "bg-green-500",
    "Observation": "bg-gray-500",
    "Distribution": "bg-red-500",
    "Aggressive Distribution": "bg-red-700"
  }[strategy.latestSignal?.label || "Observation"];
  
  const scoreColor = strategy.latestSignal?.score > 75 ? "text-green-600" :
                     strategy.latestSignal?.score > 50 ? "text-yellow-600" : "text-red-600";
  
  return (
    <div className="border rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-bold">{strategy.name}</h2>
        <span className={`px-2 py-1 rounded text-xs ${statusBadge(strategy.status)}`}>
          {strategy.status}
        </span>
        <span className="text-sm text-gray-600">
          Last evaluated {timeAgo(strategy.lastEvaluated)}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <span className={`px-3 py-1 rounded ${labelColor} text-white`}>
            {strategy.latestSignal?.label}
          </span>
          <span className={`ml-2 text-2xl font-bold ${scoreColor}`}>
            {strategy.latestSignal?.score}
          </span>
        </div>
        <div>
          <div className="text-sm text-gray-600">{strategy.latestSignal?.market}</div>
          <div className="text-xl font-bold">
            ${strategy.latestSignal?.price.toLocaleString()}
          </div>
        </div>
      </div>
      
      <div className="text-sm mb-2">
        <strong>Trend:</strong> SMA20 {strategy.latestSignal?.trend.sma20} / 
        SMA50 {strategy.latestSignal?.trend.sma50} • RSI {strategy.latestSignal?.trend.rsi14}
      </div>
      
      <div className="text-sm mb-2">
        <strong>Zones:</strong> Deep ${formatK(strategy.latestSignal?.zones.deepAccum)} | 
        Accum ${formatK(strategy.latestSignal?.zones.accum)} | 
        Dist ${formatK(strategy.latestSignal?.zones.distrib)}
      </div>
      
      <div className="text-sm">
        <strong>Position:</strong> {strategy.position.side}
        {strategy.position.side !== "FLAT" && 
          ` ${strategy.position.qty} @ $${strategy.position.avg_entry}`
        }
      </div>
      
      {strategy.lastTrade && (
        <div className="text-sm text-gray-600">
          Last Trade: {strategy.lastTrade.side} {strategy.lastTrade.qty} @ ${strategy.lastTrade.fill_px}
        </div>
      )}
    </div>
  );
}
```

---

## 2. Recent Logs Table

**Location:** Below Strategy Card or on separate `/strategies/swing-perp-16h` page

**Data Source:** `GET /v1/strategies/swing-perp-16h/logs?limit=20`

**Props:**
```typescript
interface LogEntry {
  ts: string;              // ISO timestamp
  level: "info" | "warn" | "error";
  event: "evaluation" | "signal_long" | "signal_short";
  market: string;          // "BTC"
  note: string;            // "score 60 • label Distribution • 0/4 long (blocked: ...)"
  score?: number;          // 0-100
  label?: string;          // "Distribution"
  price?: number;          // 103589.11
}
```

**UI Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│ Recent Logs (Last 20)                                        │
├───────────┬────────────┬────────┬──────────────────────────────┤
│ Time      │ Event      │ Market │ Note                        │
├───────────┼────────────┼────────┼──────────────────────────────┤
│ 2m ago    │ evaluation │ BTC    │ score 60 • label Distrib... │
│ 2m ago    │ evaluation │ BTC    │ score 60 • label Distrib... │
│ 3m ago    │ evaluation │ BTC    │ score 60 • label Distrib... │
└───────────┴────────────┴────────┴──────────────────────────────┘
```

**Styling:**
- Event badges:
  - `evaluation`: Blue
  - `signal_long`: Green
  - `signal_short`: Red
- Score in note: Same color rules as Strategy Card (>75 green, 50-75 yellow, <50 red)
- Auto-refresh every 30s (poll or WebSocket future enhancement)

**Implementation:**
```tsx
export function RecentLogs({ logs }: { logs: LogEntry[] }) {
  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-bold mb-3">Recent Logs</h3>
      <table className="w-full text-sm">
        <thead className="border-b">
          <tr>
            <th className="text-left py-2">Time</th>
            <th className="text-left py-2">Event</th>
            <th className="text-left py-2">Market</th>
            <th className="text-left py-2">Note</th>
          </tr>
        </thead>
        <tbody>
          {logs.length === 0 ? (
            <tr>
              <td colSpan={4} className="text-center py-4 text-gray-500">
                No logs yet — strategy is waiting for first evaluation
              </td>
            </tr>
          ) : (
            logs.map((log, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="py-2 text-gray-600">{timeAgo(log.ts)}</td>
                <td className="py-2">
                  <span className={`px-2 py-1 rounded text-xs ${eventBadge(log.event)}`}>
                    {log.event}
                  </span>
                </td>
                <td className="py-2">{log.market}</td>
                <td className="py-2 font-mono text-xs">{log.note}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Helper Functions

```typescript
function timeAgo(isoTimestamp: string): string {
  const seconds = (Date.now() - new Date(isoTimestamp).getTime()) / 1000;
  if (seconds < 60) return `${Math.floor(seconds)}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function statusBadge(status: string): string {
  return {
    Active: "bg-green-100 text-green-800",
    Waiting: "bg-yellow-100 text-yellow-800",
    Paused: "bg-gray-100 text-gray-800",
    Error: "bg-red-100 text-red-800"
  }[status] || "bg-gray-100 text-gray-800";
}

function eventBadge(event: string): string {
  return {
    evaluation: "bg-blue-100 text-blue-800",
    signal_long: "bg-green-100 text-green-800",
    signal_short: "bg-red-100 text-red-800"
  }[event] || "bg-gray-100 text-gray-800";
}

function formatK(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toFixed(0);
}
```

---

## 3. Optional: Trade History Table (Roundtrips)

**Data Source:** `GET /v1/strategies/swing-perp-16h/roundtrips?limit=10`

**Props:**
```typescript
interface Roundtrip {
  entry_ts: string;
  exit_ts: string;
  side: "LONG" | "SHORT";
  symbol: string;
  entry_px: number;
  exit_px: number;
  qty: number;
  pnl_quote: number;
  hold_hours: number;
}
```

**UI Layout:**
```
┌───────────────────────────────────────────────────────────────┐
│ Trade History (Last 10 Roundtrips)                           │
├──────────┬──────────┬──────┬─────────┬─────────┬──────┬──────┤
│ Entry    │ Exit     │ Side │ Entry   │ Exit    │ PnL  │ Hold │
├──────────┼──────────┼──────┼─────────┼─────────┼──────┼──────┤
│ Nov 5 AM │ Nov 5 PM │ LONG │ $94,100 │ $94,850 │ +$11 │ 16h  │
└──────────┴──────────┴──────┴─────────┴─────────┴──────┴──────┘
```

**Styling:**
- Side: Green (LONG), Red (SHORT)
- PnL: Green (positive), Red (negative)

---

## API Polling Strategy

```typescript
// Fetch strategy summary every 30s
useEffect(() => {
  const fetchStrategy = async () => {
    const res = await fetch('http://localhost:8000/v1/strategies/swing-perp-16h');
    const data = await res.json();
    setStrategy(data);
  };
  
  fetchStrategy();
  const interval = setInterval(fetchStrategy, 30000);
  return () => clearInterval(interval);
}, []);

// Fetch logs every 30s (separate state to avoid flicker)
useEffect(() => {
  const fetchLogs = async () => {
    const res = await fetch('http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=20');
    const data = await res.json();
    setLogs(data);
  };
  
  fetchLogs();
  const interval = setInterval(fetchLogs, 30000);
  return () => clearInterval(interval);
}, []);
```

---

## Disclaimer Block (Always Visible)

```tsx
<div className="bg-gray-50 border rounded-lg p-4 mt-4">
  <h4 className="font-bold mb-2">How to Read</h4>
  <p className="text-sm mb-2">
    <strong>Score:</strong> 0–100 range. Higher means stronger alignment of trend (SMA20/50), 
    volatility (ATR), RSI, and volume. Not financial advice.
  </p>
  <p className="text-sm mb-2">
    <strong>Zones:</strong> Prices relative to SMA20 ± k·ATR define Accumulation/Distribution 
    bands; k varies by asset risk.
  </p>
  <p className="text-sm text-gray-600">
    <strong>Disclaimer:</strong> Informational only. Verify on-chain. Never DM-first. $MICO is 
    independent and unaffiliated with Microsoft.
  </p>
</div>
```

---

## Summary

**Components to build:**
1. `StrategyCard` (10 min) - Shows header, at-a-glance signal, position, last trade
2. `RecentLogs` (15 min) - Table with polling
3. `TradeHistory` (15 min, optional) - Roundtrips table
4. `Disclaimer` (5 min) - Always visible block

**Total time:** ~45 minutes for core functionality

**Testing:**
```bash
# Test endpoints
curl http://localhost:8000/v1/strategies/swing-perp-16h
curl http://localhost:8000/v1/strategies/swing-perp-16h/logs?limit=5
curl http://localhost:8000/v1/strategies/swing-perp-16h/roundtrips?limit=3
```

**Production URL:** Replace `http://localhost:8000` with production API URL in env vars.
