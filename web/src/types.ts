export type Strategy = {
  id: string;
  name?: string;
  lastHeartbeat?: string | null;
  lastTradeAt?: string | null;
  pnl_realized?: number | null;
  open_position?: {
    side?: string;
    size?: number;
    avg_entry?: number;
    unrealized_pnl?: number;
    unrealized_pnl_pct?: number;
    updated_at?: string;
  } | null;
};

export type Trade = {
  id: string;
  ts: string;
  pair: string;
  side: string;
  qty: number;
  entry?: number;
  exit?: number;
  fee?: number;
  pnl?: number;
};
