import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

type Trade = {
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

export default function StrategyDetail() {
  const router = useRouter();
  const { id } = router.query as { id?: string };
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [position, setPosition] = useState<any>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchData = async () => {
    if (!id) return;
    try {
      setError(null);
      setLoading(true);
      const [tRes, pRes] = await Promise.all([
        fetch(`${apiBase}/v1/strategies/${encodeURIComponent(id)}/trades`),
        fetch(`${apiBase}/v1/strategies/${encodeURIComponent(id)}/positions`),
      ]);
      if (!tRes.ok) throw new Error(`trades HTTP ${tRes.status}`);
      if (!pRes.ok) throw new Error(`positions HTTP ${pRes.status}`);
      const tJson = await tRes.json();
      const pJson = await pRes.json();
      // normalize trades response (support { items: [] } or array)
      const tItems = Array.isArray(tJson) ? tJson : tJson.items || [];
      setTrades(tItems as Trade[]);
      setPosition(pJson[0] || null);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || String(err));
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const iv = setInterval(() => { if (autoRefresh) fetchData(); }, 10000);
    return () => clearInterval(iv);
  }, [id]);

  const exportCsv = async () => {
    try {
      const res = await fetch(`${apiBase}/v1/strategies/${encodeURIComponent(id)}/trades.csv`);
      if (!res.ok) throw new Error(`csv HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${id}-trades.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e:any) {
      setError(e.message || String(e));
    }
  };

  return (
    <main style={{ padding: 20 }}>
      <h1>Strategy {id}</h1>
      {loading && <p>Loading…</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      <section>
        <h2>Open position</h2>
        {position ? (
          <div>
            <p>Side: {position.side}</p>
            <p>Size: {position.size}</p>
            <p>Avg entry: {position.avg_entry}</p>
            <p>Unrealized PnL: {position.unrealized_pnl} ({position.unrealized_pnl_pct ?? '—'}%)</p>
            <p>Last updated: {position.updated_at ?? position.ts ?? '—'}</p>
          </div>
        ) : (
          <p>No open position</p>
        )}
      </section>

      <section>
        <h2>Recent trades</h2>
        <div style={{ marginBottom: 8 }}>
          <button onClick={() => { exportCsv(); }}>Export CSV</button>
          <label style={{ marginLeft: 12 }}>
            <input type="checkbox" checked={autoRefresh} onChange={(e)=>setAutoRefresh(e.target.checked)} /> Auto-refresh
          </label>
        </div>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Pair</th>
              <th>Side</th>
              <th>Qty</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Fee</th>
              <th>PnL</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id}>
                <td>{t.ts}</td>
                <td>{t.pair}</td>
                <td>{t.side}</td>
                <td>{t.qty}</td>
                <td>{t.entry}</td>
                <td>{t.exit}</td>
                <td>{t.fee}</td>
                <td>{t.pnl}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
