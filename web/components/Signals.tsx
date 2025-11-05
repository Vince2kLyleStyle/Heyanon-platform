import React, { useEffect, useState } from 'react';

type Signal = {
  symbol: string;
  label: string;
  score: number;
  price: number;
  sma20: number;
  sma50: number;
  atr14: number;
  rsi14?: number;
  vol_spike?: boolean;
  zones: {
    deepAccum: number;
    accum: number;
    distrib: number;
    safeDistrib: number;
  };
};

type SignalsPayload = {
  last_updated?: string;
  regime?: string;
  signals?: Record<string, Signal>;
  errors?: string[];
};

function resolveApiBase(): string {
  const envVal = process.env.NEXT_PUBLIC_API_URL as string | undefined;
  if (envVal && envVal.trim().length > 0) return envVal;
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host && host !== 'localhost' && host !== '127.0.0.1') {
      return 'https://heyanon-platform.onrender.com';
    }
  }
  return 'http://localhost:8000';
}

export default function Signals() {
  const [data, setData] = useState<SignalsPayload>({});
  const [loading, setLoading] = useState(true);
  const apiBase = resolveApiBase();

  useEffect(() => {
    const fetcher = async () => {
      try {
        const res = await fetch(`${apiBase}/v1/signals`);
        if (res.ok) {
          const json = await res.json();
          setData(json);
          setLoading(false);
        }
      } catch (e) {
        console.error('Signals fetch error:', e);
      }
    };

    fetcher();
    const interval = setInterval(fetcher, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [apiBase]);

  const signals = data.signals || {};
  const signalList = Object.values(signals);

  const getLabelColor = (label: string) => {
    if (label.includes('Aggressive Accumulation')) return '#4caf50';
    if (label.includes('Accumulation')) return '#8bc34a';
    if (label.includes('Aggressive Distribution')) return '#f44336';
    if (label.includes('Distribution')) return '#ff9800';
    return '#9e9e9e';
  };

  if (loading) {
    return <div style={{ padding: 20 }}>Loading signals...</div>;
  }

  return (
    <div style={{ padding: '0 20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Market Signals</h2>
        <div style={{ fontSize: 12, color: '#666' }}>
          <div>Updated: {data.last_updated ? new Date(data.last_updated).toLocaleTimeString() : '—'}</div>
          <div>Regime: {data.regime || 'Neutral'}</div>
          {data.errors && data.errors.length > 0 && (
            <div style={{ color: '#f44336' }}>Errors: {data.errors.length}</div>
          )}
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 16,
          marginBottom: 20,
        }}
      >
        {signalList.length === 0 && <p>No signals available yet. Wait ~60s for initial data.</p>}
        {signalList.map((s) => (
          <div
            key={s.symbol}
            style={{
              border: '1px solid #ddd',
              borderRadius: 8,
              padding: 16,
              backgroundColor: '#fafafa',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <strong style={{ fontSize: 18 }}>{s.symbol}</strong>
                {s.vol_spike && <span style={{ fontSize: 16 }}>🚀</span>}
              </div>
              <div
                style={{
                  fontSize: 12,
                  padding: '4px 8px',
                  borderRadius: 6,
                  backgroundColor: getLabelColor(s.label),
                  color: '#fff',
                  fontWeight: 600,
                }}
              >
                {s.score}
              </div>
            </div>

            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: getLabelColor(s.label),
                marginBottom: 12,
              }}
            >
              {s.label}
            </div>

            <div style={{ fontSize: 13, marginBottom: 4 }}>
              <strong>Price:</strong> ${s.price.toFixed(4)}
            </div>
            <div style={{ fontSize: 13, marginBottom: 4 }}>
              <strong>SMA20 / SMA50:</strong> ${s.sma20.toFixed(4)} / ${s.sma50.toFixed(4)}
            </div>
            <div style={{ fontSize: 13, marginBottom: 4 }}>
              <strong>RSI14:</strong> {s.rsi14 !== undefined ? s.rsi14.toFixed(1) : '—'}
            </div>
            <div style={{ fontSize: 13, marginBottom: 4 }}>
              <strong>ATR14:</strong> ${s.atr14.toFixed(4)}
            </div>

            <div style={{ fontSize: 12, color: '#666', marginTop: 12, paddingTop: 8, borderTop: '1px solid #ddd' }}>
              <div style={{ marginBottom: 2 }}>
                <strong>Deep Accum:</strong> ${s.zones.deepAccum.toFixed(4)}
              </div>
              <div style={{ marginBottom: 2 }}>
                <strong>Accum:</strong> ${s.zones.accum.toFixed(4)}
              </div>
              <div style={{ marginBottom: 2 }}>
                <strong>Distrib:</strong> ${s.zones.distrib.toFixed(4)}
              </div>
              <div>
                <strong>Safe Distrib:</strong> ${s.zones.safeDistrib.toFixed(4)}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ fontSize: 11, color: '#999', padding: '16px 0', borderTop: '1px solid #eee' }}>
        <strong>Disclaimer:</strong> Informational only. Verify on-chain. Never DM-first. $MICO is independent and
        unaffiliated with Microsoft.
      </div>
    </div>
  );
}
