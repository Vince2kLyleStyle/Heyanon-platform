import React from 'react';

type State = {
  hasError: boolean;
  error?: Error;
};

export default class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('UI Error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, textAlign: 'center' }}>
          <h2 style={{ color: '#f44336' }}>Status: Degraded</h2>
          <p>The application encountered an error. Retrying in a moment...</p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 16px',
              border: '1px solid #ddd',
              borderRadius: 6,
              background: '#f9f9f9',
              cursor: 'pointer',
            }}
          >
            Refresh Now
          </button>
          {this.state.error && (
            <pre style={{ marginTop: 16, fontSize: 12, color: '#999', textAlign: 'left', maxWidth: 600, margin: '16px auto' }}>
              {this.state.error.message}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
