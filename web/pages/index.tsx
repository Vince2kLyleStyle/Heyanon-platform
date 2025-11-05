import Signals from '../components/Signals';

export default function Home() {
  return (
    <main style={{ padding: 20 }}>
      <h1>Mico's World</h1>
      <p style={{ marginBottom: 24 }}>
        <a href="/strategies">View strategies</a>
      </p>
      
      <Signals />
    </main>
  );
}
