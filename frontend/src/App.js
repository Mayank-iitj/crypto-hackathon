import React, { useEffect, useState } from 'react';
import './App.css';

function App() {
  const [apiStatus, setApiStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAPI = async () => {
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        console.log('Attempting to connect to API:', apiUrl);
        
        const response = await fetch(`${apiUrl}/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          mode: 'cors',
          credentials: 'include',
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('API Response:', data);
        setApiStatus(data);
      } catch (error) {
        console.error('API Error:', error);
        setApiStatus({ error: `Failed to connect to API: ${error.message}` });
      } finally {
        setLoading(false);
      }
    };

    checkAPI();
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="container">
          <h1>🛡️ Q-Shield</h1>
          <p>Cryptographic Intelligence Platform for Post-Quantum Readiness</p>
        </div>
      </header>

      <main className="app-main">
        <div className="container">
          <section className="status-section">
            <h2>API Status</h2>
            {loading ? (
              <div className="loading">Checking API status...</div>
            ) : apiStatus && apiStatus.status === 'healthy' ? (
              <div className="status-healthy">
                <h3>✅ Connected</h3>
                <div className="status-details">
                  <p><strong>Service:</strong> {apiStatus.service}</p>
                  <p><strong>Version:</strong> {apiStatus.version}</p>
                  <p><strong>Environment:</strong> {apiStatus.environment}</p>
                </div>
              </div>
            ) : (
              <div className="status-error">
                <h3>❌ Connection Failed</h3>
                <p>{apiStatus?.error || 'Unable to reach API'}</p>
              </div>
            )}
          </section>

          <section className="features-section">
            <h2>Key Features</h2>
            <div className="features-grid">
              <div className="feature-card">
                <h3>🔍 Asset Discovery</h3>
                <p>Automatic discovery of internet-facing banking assets</p>
              </div>
              <div className="feature-card">
                <h3>🔐 Crypto Scanner</h3>
                <p>Real TLS handshakes and cryptographic configuration analysis</p>
              </div>
              <div className="feature-card">
                <h3>🧬 PQC Validation</h3>
                <p>Post-Quantum Cryptography readiness assessment</p>
              </div>
              <div className="feature-card">
                <h3>📜 CBOM Generator</h3>
                <p>Machine-readable Cryptographic Bill of Materials</p>
              </div>
              <div className="feature-card">
                <h3>🏷️ Certificates</h3>
                <p>Digitally verifiable Quantum-Safe Certificates</p>
              </div>
              <div className="feature-card">
                <h3>📊 Dashboard</h3>
                <p>Real-time asset inventory and risk visualization</p>
              </div>
            </div>
          </section>

          <section className="getting-started">
            <h2>Getting Started</h2>
            <div className="links">
              <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="btn btn-primary">
                📚 API Documentation (Swagger)
              </a>
              <a href="http://localhost:8000/redoc" target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
                📖 API Docs (ReDoc)
              </a>
              <a href="http://localhost:8000/health" target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
                💚 Health Check
              </a>
            </div>
          </section>
        </div>
      </main>

      <footer className="app-footer">
        <div className="container">
          <p>&copy; 2026 Q-Shield. Building quantum-safe banking infrastructure.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
