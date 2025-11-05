import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

type LogEntry = {
  ts: string;
  event: string;
  details?: Record<string, any>;
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

export default function StrategyDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const apiBase = resolveApiBase();

  useEffect(() => {
    if (!id) return;

    const fetchLogs = async () => {
      try {
        const res = await fetch(`${apiBase}/v1/strategies/${id}/logs`);
        if (res.ok) {
          const data = await res.json();
          setLogs(data);
        }
        setLoading(false);
      } catch (e) {
        console.error('Logs fetch error:', e);
        setLoading(false);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 15000); // Poll every 15s
    return () => clearInterval(interval);
  }, [id, apiBase]);

  const formatTime = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleString();
    } catch {
      return isoString;
    }
  };

  if (loading) {
    return <div style={{ padding: 20 }}>Loading strategy logs...</div>;
  }

  return (
    <div style={{ padding: '0 20px', maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <button
          onClick={() => router.push('/')}
          style={{
            padding: '8px 16px',
            border: '1px solid #ddd',
            borderRadius: 6,
            background: '#f9f9f9',
            cursor: 'pointer',
            fontSize: 14,
            marginBottom: 12,
          }}
        >
          ← Back to Home
        </button>
        <h1 style={{ margin: 0, marginBottom: 8 }}>Strategy {id}</h1>
        <div style={{ fontSize: 14, color: '#666' }}>Execution logs (last 50 entries)</div>
      </div>

      {logs.length === 0 && (
        <div style={{ fontSize: 14, color: '#999', padding: 16, background: '#f9f9f9', borderRadius: 8 }}>
          No logs yet. Check back once the strategy runs.
        </div>
      )}

      {logs.length > 0 && (
        <div style={{ border: '1px solid #ddd', borderRadius: 8, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead style={{ background: '#f5f5f5' }}>
              <tr>
                <th style={{ textAlign: 'left', padding: 12, borderBottom: '1px solid #ddd' }}>Time</th>
                <th style={{ textAlign: 'left', padding: 12, borderBottom: '1px solid #ddd' }}>Event</th>
                <th style={{ textAlign: 'left', padding: 12, borderBottom: '1px solid #ddd' }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, idx) => (
                <tr key={idx} style={{ background: idx % 2 === 0 ? '#fff' : '#fafafa' }}>
                  <td style={{ padding: 12, borderBottom: '1px solid #eee', whiteSpace: 'nowrap' }}>
                    {formatTime(log.ts)}
                  </td>
                  <td style={{ padding: 12, borderBottom: '1px solid #eee', fontWeight: 600 }}>{log.event}</td>
                  <td style={{ padding: 12, borderBottom: '1px solid #eee', fontSize: 12, color: '#666' }}>
                    {log.details ? (
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer disclaimer */}
      <div
        style={{
          fontSize: 11,
          color: '#999',
          padding: '16px 0',
          borderTop: '1px solid #eee',
          textAlign: 'center',
          marginTop: 24,
        }}
      >
        <strong>Disclaimer:</strong> Informational only. Verify on-chain. Never DM-first. $MICO is independent and
        unaffiliated with Microsoft.
      </div>
    </div>
  );
}
