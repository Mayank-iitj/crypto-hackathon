import React, { useEffect, useMemo, useRef, useState } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_V1 = `${API_BASE}/api/v1`;

const tabs = [
  'Overview',
  'Discovery',
  'Assets',
  'Public Inventory',
  'Scans',
  'Crypto Assessment',
  'CBOM',
  'Certificates',
  'Compliance',
  'OAuth',
];

const guidedTourSteps = [
  {
    tab: 'Overview',
    title: 'Platform Snapshot',
    talkingPoints: [
      'Open with the KPI cards to frame total exposure and risk posture.',
      'Call out that this dashboard uses live APIs and can switch to seeded demo instantly.',
    ],
  },
  {
    tab: 'Discovery',
    title: 'Internet-Facing Discovery',
    talkingPoints: [
      'Show domain and CIDR discovery for external attack surface visibility.',
      'Explain subdomain enrichment and CT intelligence usage for broad coverage.',
    ],
  },
  {
    tab: 'Assets',
    title: 'Asset Registry',
    talkingPoints: [
      'Demonstrate secure asset onboarding and inventory governance.',
      'Highlight quick lifecycle actions like create, refresh, and delete.',
    ],
  },
  {
    tab: 'Public Inventory',
    title: 'PQC Visibility',
    talkingPoints: [
      'Review TLS controls, readiness posture, and quantum-safe label eligibility.',
      'Use this table to discuss risk prioritization and modernization backlog.',
    ],
  },
  {
    tab: 'Scans',
    title: 'Scan Orchestration',
    talkingPoints: [
      'Run full or scoped scans and track status in one workflow.',
      'Show this as the operational entry point for continuous validation.',
    ],
  },
  {
    tab: 'Crypto Assessment',
    title: 'Crypto Analysis',
    talkingPoints: [
      'Assess target cryptography and readiness level in real time.',
      'Discuss how results support remediation and migration planning.',
    ],
  },
  {
    tab: 'CBOM',
    title: 'CBOM Generation',
    talkingPoints: [
      'Generate machine-readable crypto inventories for audit and governance.',
      'Position this output as evidence for control frameworks and stakeholders.',
    ],
  },
  {
    tab: 'Certificates',
    title: 'Certificate Workbench',
    talkingPoints: [
      'Issue and verify quantum-safe certificates with traceable identifiers.',
      'Emphasize policy gating and confidence in certificate eligibility.',
    ],
  },
  {
    tab: 'Compliance',
    title: 'Framework Reporting',
    talkingPoints: [
      'Map controls against NIST and organizational frameworks.',
      'Use this output for executive reporting and remediation planning.',
    ],
  },
  {
    tab: 'OAuth',
    title: 'Identity Federation',
    talkingPoints: [
      'Close with SSO/OAuth provider integration for enterprise readiness.',
      'Tie this to secure access governance for platform operators.',
    ],
  },
];

function createDemoDataset() {
  const now = new Date().toISOString();

  const assets = [
    {
      id: 9001,
      hostname: 'bank-demo.example',
      port: 443,
      pqc_readiness: 'pqc_ready',
      asset_type: 'web_server',
      risk_score: 31.2,
    },
    {
      id: 9002,
      hostname: 'api.bank-demo.example',
      port: 8443,
      pqc_readiness: 'transitional',
      asset_type: 'api_endpoint',
      risk_score: 44.8,
    },
    {
      id: 9003,
      hostname: 'vpn.bank-demo.example',
      port: 443,
      pqc_readiness: 'vulnerable',
      asset_type: 'vpn_server',
      risk_score: 68.1,
    },
  ];

  const inventoryAssets = [
    {
      id: 'asset-9001',
      hostname: 'bank-demo.example',
      port: 443,
      asset_type: 'web_server',
      pqc_readiness: 'pqc_ready',
      quantum_safe_label: 'PQC Ready',
      crypto_controls: {
        tls_version: 'TLSv1.3',
        preferred_cipher: 'TLS_AES_256_GCM_SHA384',
      },
    },
    {
      id: 'asset-9002',
      hostname: 'api.bank-demo.example',
      port: 8443,
      asset_type: 'api_endpoint',
      pqc_readiness: 'transitional',
      quantum_safe_label: null,
      crypto_controls: {
        tls_version: 'TLSv1.2',
        preferred_cipher: 'ECDHE-RSA-AES256-GCM-SHA384',
      },
    },
    {
      id: 'asset-9003',
      hostname: 'vpn.bank-demo.example',
      port: 443,
      asset_type: 'vpn_server',
      pqc_readiness: 'vulnerable',
      quantum_safe_label: null,
      crypto_controls: {
        tls_version: 'TLSv1.2',
        preferred_cipher: 'ECDHE-RSA-AES128-GCM-SHA256',
      },
    },
  ];

  return {
    health: {
      status: 'healthy',
      service: 'Q-Shield',
      environment: 'production-demo',
      generated_at: now,
    },
    assets,
    discoveryResult: {
      status: 'success',
      discovered_assets: 3,
      persisted_assets: 3,
      discovery_summary: {
        domains: ['bank-demo.example'],
        ip_ranges: [],
        include_subdomains: true,
      },
      generated_at: now,
    },
    publicInventory: {
      counts: {
        total_public_assets: 3,
        pqc_ready_assets: 1,
        vulnerable_assets: 1,
      },
      inventory: {
        all_public_assets: inventoryAssets,
      },
      generated_at: now,
    },
    scanResult: {
      scan_id: 'demo-scan-2026-001',
      status: 'started',
      accepted_targets: ['bank-demo.example:443', 'api.bank-demo.example:8443'],
      started_at: now,
    },
    scanStatus: {
      scan_id: 'demo-scan-2026-001',
      status: 'completed',
      progress: 100,
      findings: {
        low: 2,
        medium: 2,
        high: 1,
        critical: 0,
      },
      completed_at: now,
    },
    cryptoResult: {
      target: 'bank-demo.example:443',
      readiness_level: 'pqc_ready',
      pqc_kem_detected: 'ML-KEM-768',
      pqc_signature_detected: 'ML-DSA-65',
      uses_tls_1_3: true,
      recommendation: 'Proceed with phased certificate transition and monitor dependent APIs.',
    },
    cbomResult: {
      cbom_id: 'cbom-demo-2026-01',
      format: 'json',
      entries: 3,
      generated_at: now,
      download_url: '/api/v1/cbom/demo-artifact',
    },
    issuedCert: {
      certificate_id: 'QSC-DEMO-0001',
      asset: 'bank-demo.example:443',
      label: 'PQC Ready',
      issued_at: now,
      valid_days: 365,
    },
    certificateLookup: {
      certificate_id: 'QSC-DEMO-0001',
      status: 'valid',
      owner: 'bank-demo.example',
      readiness_level: 'pqc_ready',
      issued_at: now,
      expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    },
    complianceResult: {
      overall_status: 'partially_compliant',
      score: 82,
      frameworks: {
        nist_sp_800_208: 'compliant',
        nist_sp_800_52: 'partially_compliant',
        iso_27001: 'compliant',
        rbi_csf: 'partially_compliant',
      },
      recommendations: [
        'Upgrade API endpoint cipher profile to TLS 1.3 baseline.',
        'Schedule certificate renewal for vulnerable VPN node.',
      ],
    },
    providers: {
      providers: [
        { name: 'google', enabled: true },
        { name: 'github', enabled: true },
        { name: 'microsoft', enabled: true },
      ],
    },
    forms: {
      assetForm: { hostname: 'bank-demo.example', port: 443 },
      discoveryForm: {
        domains: 'bank-demo.example',
        ip_ranges: '',
        include_subdomains: true,
        ports: '443,8443,9443,500,1194',
      },
      scanForm: { targets: 'bank-demo.example:443, api.bank-demo.example:8443', scan_type: 'full' },
      cryptoForm: { hostname: 'bank-demo.example', port: 443 },
      cbomForm: { assets: 'bank-demo.example,api.bank-demo.example,vpn.bank-demo.example', format: 'json' },
      certForm: { hostname: 'bank-demo.example', port: 443 },
      complianceForm: {
        assets: 'bank-demo.example,api.bank-demo.example,vpn.bank-demo.example',
        frameworks: 'nist_sp_800_208,nist_sp_800_52,iso_27001,rbi_csf',
      },
      certificateId: 'QSC-DEMO-0001',
    },
  };
}

function buildUrl(path, query = {}) {
  const url = new URL(path, API_BASE);
  Object.entries(query).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.filter(Boolean).forEach((entry) => url.searchParams.append(key, entry));
      return;
    }
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

async function request(path, options = {}, query = {}) {
  const res = await fetch(buildUrl(path, query), {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });

  if (res.status === 204) {
    return null;
  }

  const text = await res.text();
  let parsed;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = { raw: text };
  }

  if (!res.ok) {
    const detail = parsed?.detail || `Request failed with status ${res.status}`;
    throw new Error(detail);
  }

  return parsed;
}

function parseCsv(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function App() {
  const [activeTab, setActiveTab] = useState('Overview');
  const [demoMode, setDemoMode] = useState(false);
  const [guidedMode, setGuidedMode] = useState(false);
  const [guidedStep, setGuidedStep] = useState(0);
  const [guidedAutoPlay, setGuidedAutoPlay] = useState(false);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState({ type: 'info', message: 'Ready' });
  const [health, setHealth] = useState(null);

  const [assets, setAssets] = useState([]);
  const [assetForm, setAssetForm] = useState({ hostname: '', port: 443 });
  const [discoveryForm, setDiscoveryForm] = useState({
    domains: '',
    ip_ranges: '',
    include_subdomains: true,
    ports: '443,8443,9443,500,1194,1701,1723,4500',
  });
  const [discoveryResult, setDiscoveryResult] = useState(null);
  const [publicInventory, setPublicInventory] = useState(null);

  const [scanForm, setScanForm] = useState({ targets: '', scan_type: 'full' });
  const [scanResult, setScanResult] = useState(null);
  const [scanStatus, setScanStatus] = useState(null);

  const [cryptoForm, setCryptoForm] = useState({ hostname: '', port: 443 });
  const [cryptoResult, setCryptoResult] = useState(null);

  const [cbomForm, setCbomForm] = useState({ assets: '', format: 'json' });
  const [cbomResult, setCbomResult] = useState(null);

  const [certForm, setCertForm] = useState({ hostname: '', port: 443 });
  const [issuedCert, setIssuedCert] = useState(null);
  const [certificateId, setCertificateId] = useState('');
  const [certificateLookup, setCertificateLookup] = useState(null);

  const [complianceForm, setComplianceForm] = useState({
    assets: '',
    frameworks: 'nist_sp_800_208,nist_sp_800_52,iso_27001,rbi_csf',
  });
  const [complianceResult, setComplianceResult] = useState(null);

  const [providers, setProviders] = useState(null);
  const sessionIdRef = useRef(`sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`);

  const kpis = useMemo(() => {
    const riskKnown = assets.filter((a) => typeof a.risk_score === 'number');
    const riskAvg =
      riskKnown.length > 0
        ? (riskKnown.reduce((sum, item) => sum + item.risk_score, 0) / riskKnown.length).toFixed(2)
        : 'N/A';
    return {
      totalAssets: assets.length,
      pqcReady: assets.filter((a) => String(a.pqc_readiness || '').includes('pqc')).length,
      vulnerable: assets.filter((a) => String(a.pqc_readiness || '').includes('vulnerable')).length,
      apis: assets.filter((a) => String(a.asset_type || '').includes('api')).length,
      vpns: assets.filter((a) => String(a.asset_type || '').includes('vpn')).length,
      avgRisk: riskAvg,
    };
  }, [assets]);

  const withBusy = async (label, work) => {
    void recordSessionActivity('operation', label, 'started', { tab: activeTab });
    setBusy(true);
    try {
      const result = await work();
      setFlash({ type: 'success', message: label });
      void recordSessionActivity('operation', label, 'success', { tab: activeTab });
      return result;
    } catch (error) {
      setFlash({ type: 'error', message: error.message });
      void recordSessionActivity('operation', label, 'failed', { tab: activeTab, error: error.message });
      throw error;
    } finally {
      setBusy(false);
    }
  };

  const recordSessionActivity = async (eventType, action, outcome = 'success', details = {}) => {
    try {
      await fetch(buildUrl('/api/v1/reports/session/activity'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          event_type: eventType,
          action,
          resource: 'frontend',
          outcome,
          actor: 'web-user',
          details: {
            tab: activeTab,
            ...details,
          },
        }),
      });
    } catch {
      // Session analytics should never block core product workflows.
    }
  };

  const selectTab = (tab) => {
    setActiveTab(tab);
    void recordSessionActivity('navigation', `tab:${tab}`, 'success');
  };

  const loadHealth = async () => {
    const response = await request('/health');
    setHealth(response);
  };

  const loadAssets = async () => {
    const response = await request('/api/v1/assets', {}, { skip: 0, limit: 100 });
    setAssets(response?.assets || []);
  };

  const loadPublicInventory = async () => {
    const response = await request('/api/v1/inventory/public-facing', {}, { skip: 0, limit: 200 });
    setPublicInventory(response);
  };

  const loadProviders = async () => {
    const response = await request('/api/v1/auth/providers');
    setProviders(response);
  };

  useEffect(() => {
    const bootstrap = async () => {
      setBusy(true);
      try {
        await Promise.all([loadHealth(), loadAssets(), loadProviders(), loadPublicInventory()]);
        setFlash({ type: 'success', message: 'Loaded platform state' });
      } catch (error) {
        setFlash({ type: 'error', message: error.message });
      } finally {
        setBusy(false);
      }

      try {
        await fetch(buildUrl('/api/v1/reports/session/activity'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: sessionIdRef.current,
            event_type: 'session',
            action: 'session_started',
            resource: 'frontend',
            outcome: 'success',
            actor: 'web-user',
            details: {
              session_id: sessionIdRef.current,
              user_agent: navigator.userAgent,
            },
          }),
        });
      } catch {
        // Non-blocking analytics hook.
      }
    };
    bootstrap();
  }, []);

  useEffect(() => {
    if (!guidedMode || !guidedAutoPlay) {
      return undefined;
    }

    const timer = setInterval(() => {
      setGuidedStep((current) => {
        const next = (current + 1) % guidedTourSteps.length;
        setActiveTab(guidedTourSteps[next].tab);
        return next;
      });
    }, 8000);

    return () => clearInterval(timer);
  }, [guidedMode, guidedAutoPlay]);

  const runDiscovery = async (event) => {
    event.preventDefault();
    const domains = parseCsv(discoveryForm.domains);
    const ipRanges = parseCsv(discoveryForm.ip_ranges);
    const ports = parseCsv(discoveryForm.ports).map((value) => Number(value)).filter((value) => Number.isInteger(value));

    await withBusy('Public-facing discovery complete', async () => {
      const response = await request(
        '/api/v1/discovery/public-facing',
        { method: 'POST' },
        {
          domains,
          ip_ranges: ipRanges,
          include_subdomains: discoveryForm.include_subdomains,
          ports,
        },
      );
      setDiscoveryResult(response);
      await Promise.all([loadAssets(), loadPublicInventory()]);
    });
  };

  const createAsset = async (event) => {
    event.preventDefault();
    await withBusy('Asset created', async () => {
      await request('/api/v1/assets', { method: 'POST' }, assetForm);
      await loadAssets();
      setAssetForm({ hostname: '', port: 443 });
    });
  };

  const deleteAsset = async (assetId) => {
    await withBusy('Asset deleted', async () => {
      await request(`/api/v1/assets/${assetId}`, { method: 'DELETE' });
      await loadAssets();
    });
  };

  const launchScan = async (event) => {
    event.preventDefault();
    const targets = parseCsv(scanForm.targets);
    await withBusy('Scan started', async () => {
      const response = await request('/api/v1/scans', { method: 'POST' }, { targets, scan_type: scanForm.scan_type });
      setScanResult(response);
      setScanStatus(null);
    });
  };

  const checkScanStatus = async () => {
    if (!scanResult?.scan_id) {
      setFlash({ type: 'error', message: 'Start a scan first' });
      return;
    }
    await withBusy('Scan status refreshed', async () => {
      const response = await request(`/api/v1/scans/${scanResult.scan_id}`);
      setScanStatus(response);
    });
  };

  const runCryptoAssessment = async (event) => {
    event.preventDefault();
    await withBusy('Cryptographic assessment completed', async () => {
      const response = await request('/api/v1/assess/crypto', { method: 'POST' }, cryptoForm);
      setCryptoResult(response);
    });
  };

  const generateCbom = async (event) => {
    event.preventDefault();
    const assetsInput = parseCsv(cbomForm.assets);
    await withBusy('CBOM generated', async () => {
      const response = await request('/api/v1/cbom/generate', { method: 'POST' }, { assets: assetsInput, format: cbomForm.format });
      setCbomResult(response);
    });
  };

  const issueCertificate = async (event) => {
    event.preventDefault();
    await withBusy('Certificate issued', async () => {
      const response = await request('/api/v1/certificates/issue', { method: 'POST' }, certForm);
      setIssuedCert(response);
      setCertificateId(response?.certificate_id || '');
    });
  };

  const lookupCertificate = async () => {
    if (!certificateId) {
      setFlash({ type: 'error', message: 'Certificate ID is required' });
      return;
    }
    await withBusy('Certificate loaded', async () => {
      const response = await request(`/api/v1/certificates/${certificateId}`);
      setCertificateLookup(response);
    });
  };

  const runCompliance = async (event) => {
    event.preventDefault();
    const assetsInput = parseCsv(complianceForm.assets);
    const frameworksInput = parseCsv(complianceForm.frameworks);
    await withBusy('Compliance check completed', async () => {
      const response = await request('/api/v1/compliance/check', { method: 'POST' }, { assets: assetsInput, frameworks: frameworksInput });
      setComplianceResult(response);
    });
  };

  const loadDemoData = () => {
    const demo = createDemoDataset();

    setDemoMode(true);
    setHealth(demo.health);
    setAssets(demo.assets);
    setDiscoveryResult(demo.discoveryResult);
    setPublicInventory(demo.publicInventory);
    setScanResult(demo.scanResult);
    setScanStatus(demo.scanStatus);
    setCryptoResult(demo.cryptoResult);
    setCbomResult(demo.cbomResult);
    setIssuedCert(demo.issuedCert);
    setCertificateLookup(demo.certificateLookup);
    setComplianceResult(demo.complianceResult);
    setProviders(demo.providers);

    setAssetForm(demo.forms.assetForm);
    setDiscoveryForm(demo.forms.discoveryForm);
    setScanForm(demo.forms.scanForm);
    setCryptoForm(demo.forms.cryptoForm);
    setCbomForm(demo.forms.cbomForm);
    setCertForm(demo.forms.certForm);
    setComplianceForm(demo.forms.complianceForm);
    setCertificateId(demo.forms.certificateId);

    setFlash({ type: 'success', message: 'Demo dataset loaded for all features (frontend-only).' });
  };

  const clearDemoData = async () => {
    setDemoMode(false);
    setGuidedMode(false);
    setGuidedAutoPlay(false);
    setGuidedStep(0);
    setDiscoveryResult(null);
    setScanResult(null);
    setScanStatus(null);
    setCryptoResult(null);
    setCbomResult(null);
    setIssuedCert(null);
    setCertificateLookup(null);
    setComplianceResult(null);

    await withBusy('Demo mode disabled and live data restored', async () => {
      await Promise.all([loadHealth(), loadAssets(), loadProviders(), loadPublicInventory()]);
    });
  };

  const downloadSessionReport = async () => {
    await withBusy('Session PDF report downloaded', async () => {
      const response = await fetch(buildUrl(`/api/v1/reports/session/${sessionIdRef.current}/pdf`));
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Failed to download session report');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `qshield-session-${sessionIdRef.current}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);

      void recordSessionActivity('report', 'session_pdf_downloaded', 'success', {
        session_id: sessionIdRef.current,
      });
    });
  };

  const goToGuidedStep = (stepIndex) => {
    const normalized = (stepIndex + guidedTourSteps.length) % guidedTourSteps.length;
    setGuidedStep(normalized);
    setActiveTab(guidedTourSteps[normalized].tab);
  };

  const startGuidedDemo = () => {
    if (!demoMode) {
      loadDemoData();
    }
    setGuidedMode(true);
    setGuidedAutoPlay(false);
    goToGuidedStep(0);
    setFlash({ type: 'info', message: 'Guided demo started. Use Next or Autoplay to present.' });
  };

  const stopGuidedDemo = () => {
    setGuidedMode(false);
    setGuidedAutoPlay(false);
    setGuidedStep(0);
    setFlash({ type: 'info', message: 'Guided demo stopped.' });
  };

  const currentStep = guidedTourSteps[guidedStep];

  return (
    <div className="shell">
      <div className="background-layer" />
      <div className="grain-layer" />
      <header className="hero">
        <div className="hero-brand">
          <span className="eyebrow">Quantum Security Operations</span>
          <h1>Q-Shield Command Deck</h1>
          <p>Live cryptographic operations, real API execution, zero mock workflows.</p>
        </div>
        <div className="hero-kpis">
          <article>
            <span>Assets</span>
            <strong>{kpis.totalAssets}</strong>
          </article>
          <article>
            <span>PQC Ready</span>
            <strong>{kpis.pqcReady}</strong>
          </article>
          <article>
            <span>Avg Risk</span>
            <strong>{kpis.avgRisk}</strong>
          </article>
        </div>
        <div className="hero-actions">
          <button type="button" onClick={loadDemoData}>Load Demo Data</button>
          <button type="button" onClick={startGuidedDemo}>Start Guided Demo</button>
          <button type="button" onClick={downloadSessionReport}>Download Session PDF</button>
          <button type="button" className="secondary" onClick={clearDemoData}>Clear Demo</button>
        </div>
        <div className={`badge ${health?.status === 'healthy' ? 'ok' : 'down'}`}>
          {demoMode ? 'Demo Mode Active' : health?.status === 'healthy' ? 'API Healthy' : 'API Unreachable'}
        </div>
      </header>

      <div className="tab-scroll">
        <nav className="tab-bar" aria-label="Primary navigation">
          {tabs.map((tab) => (
            <button
              type="button"
              key={tab}
              className={activeTab === tab ? 'tab active' : 'tab'}
              onClick={() => selectTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      <div className={`flash ${flash.type}`} aria-live="polite">{busy ? 'Working...' : flash.message}</div>

      {guidedMode && (
        <section className="tour-strip" aria-live="polite">
          <div className="tour-copy">
            <p className="tour-kicker">Guided Demo</p>
            <h3>{currentStep.title}</h3>
            <p>
              Step {guidedStep + 1} of {guidedTourSteps.length} : {currentStep.tab}
            </p>
            <ul>
              {currentStep.talkingPoints.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </div>
          <div className="tour-controls">
            <button type="button" onClick={() => goToGuidedStep(guidedStep - 1)}>Previous</button>
            <button type="button" onClick={() => goToGuidedStep(guidedStep + 1)}>Next</button>
            <button
              type="button"
              className="secondary"
              onClick={() => setGuidedAutoPlay((value) => !value)}
            >
              {guidedAutoPlay ? 'Pause Autoplay' : 'Start Autoplay'}
            </button>
            <button type="button" className="danger" onClick={stopGuidedDemo}>End Guided Demo</button>
          </div>
        </section>
      )}

      <main className="panel-grid">
        {activeTab === 'Overview' && (
          <section className="panel wide">
            <h2>Platform Overview</h2>
            <div className="kpi-grid">
              <article>
                <h3>Total Assets</h3>
                <p>{kpis.totalAssets}</p>
              </article>
              <article>
                <h3>PQC Ready Assets</h3>
                <p>{kpis.pqcReady}</p>
              </article>
              <article>
                <h3>Vulnerable Assets</h3>
                <p>{kpis.vulnerable}</p>
              </article>
              <article>
                <h3>API Endpoints</h3>
                <p>{kpis.apis}</p>
              </article>
              <article>
                <h3>TLS-based VPN</h3>
                <p>{kpis.vpns}</p>
              </article>
              <article>
                <h3>Average Risk</h3>
                <p>{kpis.avgRisk}</p>
              </article>
            </div>
            <div className="endpoint-row">
              <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">Swagger</a>
              <a href={`${API_BASE}/redoc`} target="_blank" rel="noreferrer">ReDoc</a>
              <a href={`${API_BASE}/health`} target="_blank" rel="noreferrer">Health</a>
              <a href="http://localhost:3001" target="_blank" rel="noreferrer">Grafana</a>
              <a href="http://localhost:5601" target="_blank" rel="noreferrer">Kibana</a>
            </div>
          </section>
        )}

        {activeTab === 'Discovery' && (
          <section className="panel wide">
            <h2>Discover Internet-Facing Assets</h2>
            <form onSubmit={runDiscovery} className="form-stack">
              <label>
                Domains (comma separated)
                <input
                  value={discoveryForm.domains}
                  onChange={(e) => setDiscoveryForm({ ...discoveryForm, domains: e.target.value })}
                  placeholder="example.com, bank.example.com"
                />
              </label>
              <label>
                IP Ranges (CIDR, comma separated)
                <input
                  value={discoveryForm.ip_ranges}
                  onChange={(e) => setDiscoveryForm({ ...discoveryForm, ip_ranges: e.target.value })}
                  placeholder="203.0.113.0/28"
                />
              </label>
              <label>
                Ports
                <input
                  value={discoveryForm.ports}
                  onChange={(e) => setDiscoveryForm({ ...discoveryForm, ports: e.target.value })}
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={discoveryForm.include_subdomains}
                  onChange={(e) => setDiscoveryForm({ ...discoveryForm, include_subdomains: e.target.checked })}
                />
                Include common subdomains and CT intelligence
              </label>
              <button type="submit">Run Discovery</button>
            </form>
            {discoveryResult && <pre>{JSON.stringify(discoveryResult, null, 2)}</pre>}
          </section>
        )}

        {activeTab === 'Assets' && (
          <>
            <section className="panel">
              <h2>Register Asset</h2>
              <form onSubmit={createAsset} className="form-stack">
                <label>
                  Hostname
                  <input
                    required
                    value={assetForm.hostname}
                    onChange={(e) => setAssetForm({ ...assetForm, hostname: e.target.value })}
                    placeholder="example.com"
                  />
                </label>
                <label>
                  Port
                  <input
                    type="number"
                    min="1"
                    max="65535"
                    value={assetForm.port}
                    onChange={(e) => setAssetForm({ ...assetForm, port: Number(e.target.value) })}
                  />
                </label>
                <button type="submit">Create Asset</button>
              </form>
            </section>

            <section className="panel wide">
              <div className="panel-heading">
                <h2>Asset Inventory</h2>
                <button type="button" onClick={() => withBusy('Assets refreshed', loadAssets)}>Refresh</button>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Hostname</th>
                    <th>Port</th>
                    <th>PQC</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {assets.length === 0 && (
                    <tr>
                      <td colSpan="5">No assets yet.</td>
                    </tr>
                  )}
                  {assets.map((asset) => (
                    <tr key={asset.id}>
                      <td className="mono">{asset.id}</td>
                      <td>{asset.hostname}</td>
                      <td>{asset.port}</td>
                      <td>{asset.pqc_readiness}</td>
                      <td>
                        <button type="button" className="danger" onClick={() => deleteAsset(asset.id)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}

        {activeTab === 'Public Inventory' && (
          <section className="panel wide">
            <div className="panel-heading">
              <h2>Public-Facing Crypto Inventory</h2>
              <button type="button" onClick={() => withBusy('Public inventory refreshed', loadPublicInventory)}>Refresh</button>
            </div>
            {!publicInventory && <p>No inventory yet. Run discovery and scans first.</p>}
            {publicInventory && (
              <>
                <pre>{JSON.stringify(publicInventory.counts, null, 2)}</pre>
                <table>
                  <thead>
                    <tr>
                      <th>Host</th>
                      <th>Type</th>
                      <th>TLS</th>
                      <th>Preferred Cipher</th>
                      <th>Readiness</th>
                      <th>Label</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(publicInventory.inventory?.all_public_assets || []).map((asset) => (
                      <tr key={asset.id}>
                        <td>{asset.hostname}:{asset.port}</td>
                        <td>{asset.asset_type}</td>
                        <td>{asset.crypto_controls?.tls_version || 'n/a'}</td>
                        <td>{asset.crypto_controls?.preferred_cipher || 'n/a'}</td>
                        <td>{asset.pqc_readiness || 'unknown'}</td>
                        <td>{asset.quantum_safe_label || 'Not Eligible'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <pre>{JSON.stringify(publicInventory.inventory?.all_public_assets || [], null, 2)}</pre>
              </>
            )}
          </section>
        )}

        {activeTab === 'Scans' && (
          <section className="panel wide">
            <h2>Launch Scan</h2>
            <form onSubmit={launchScan} className="form-stack">
              <label>
                Targets (comma separated host:port)
                <textarea
                  rows="3"
                  value={scanForm.targets}
                  onChange={(e) => setScanForm({ ...scanForm, targets: e.target.value })}
                  placeholder="example.com:443, api.example.com:8443"
                  required
                />
              </label>
              <label>
                Scan Type
                <select
                  value={scanForm.scan_type}
                  onChange={(e) => setScanForm({ ...scanForm, scan_type: e.target.value })}
                >
                  <option value="full">full</option>
                  <option value="tls">tls</option>
                  <option value="pqc">pqc</option>
                  <option value="compliance">compliance</option>
                </select>
              </label>
              <div className="button-row">
                <button type="submit">Start Scan</button>
                <button type="button" onClick={checkScanStatus}>Check Status</button>
              </div>
            </form>
            {scanResult && <pre>{JSON.stringify(scanResult, null, 2)}</pre>}
            {scanStatus && <pre>{JSON.stringify(scanStatus, null, 2)}</pre>}
          </section>
        )}

        {activeTab === 'Crypto Assessment' && (
          <section className="panel wide">
            <h2>Real TLS and PQC Assessment</h2>
            <form onSubmit={runCryptoAssessment} className="inline-form">
              <input
                placeholder="hostname"
                value={cryptoForm.hostname}
                onChange={(e) => setCryptoForm({ ...cryptoForm, hostname: e.target.value })}
                required
              />
              <input
                type="number"
                min="1"
                max="65535"
                value={cryptoForm.port}
                onChange={(e) => setCryptoForm({ ...cryptoForm, port: Number(e.target.value) })}
              />
              <button type="submit">Assess</button>
            </form>
            {cryptoResult && <pre>{JSON.stringify(cryptoResult, null, 2)}</pre>}
          </section>
        )}

        {activeTab === 'CBOM' && (
          <section className="panel wide">
            <h2>Generate CBOM</h2>
            <form onSubmit={generateCbom} className="form-stack">
              <label>
                Assets (hostnames, comma separated)
                <input
                  value={cbomForm.assets}
                  onChange={(e) => setCbomForm({ ...cbomForm, assets: e.target.value })}
                  placeholder="example.com, api.example.com"
                  required
                />
              </label>
              <label>
                Format
                <select value={cbomForm.format} onChange={(e) => setCbomForm({ ...cbomForm, format: e.target.value })}>
                  <option value="json">json</option>
                  <option value="pdf">pdf</option>
                  <option value="csv">csv</option>
                  <option value="jws">jws</option>
                </select>
              </label>
              <button type="submit">Generate</button>
            </form>
            {cbomResult && <pre>{JSON.stringify(cbomResult, null, 2)}</pre>}
          </section>
        )}

        {activeTab === 'Certificates' && (
          <section className="panel wide">
            <h2>Quantum-Safe Certificates</h2>
            <form onSubmit={issueCertificate} className="inline-form">
              <input
                placeholder="hostname"
                value={certForm.hostname}
                onChange={(e) => setCertForm({ ...certForm, hostname: e.target.value })}
                required
              />
              <input
                type="number"
                min="1"
                max="65535"
                value={certForm.port}
                onChange={(e) => setCertForm({ ...certForm, port: Number(e.target.value) })}
              />
              <button type="submit">Issue</button>
            </form>
            {issuedCert && <pre>{JSON.stringify(issuedCert, null, 2)}</pre>}

            <div className="lookup-row">
              <input
                placeholder="certificate_id"
                value={certificateId}
                onChange={(e) => setCertificateId(e.target.value)}
              />
              <button type="button" onClick={lookupCertificate}>Lookup</button>
            </div>
            {certificateLookup && <pre>{JSON.stringify(certificateLookup, null, 2)}</pre>}
          </section>
        )}

        {activeTab === 'Compliance' && (
          <section className="panel wide">
            <h2>Compliance Check</h2>
            <form onSubmit={runCompliance} className="form-stack">
              <label>
                Assets (comma separated)
                <input
                  value={complianceForm.assets}
                  onChange={(e) => setComplianceForm({ ...complianceForm, assets: e.target.value })}
                  placeholder="example.com, api.example.com"
                  required
                />
              </label>
              <label>
                Frameworks (comma separated)
                <input
                  value={complianceForm.frameworks}
                  onChange={(e) => setComplianceForm({ ...complianceForm, frameworks: e.target.value })}
                />
              </label>
              <button type="submit">Run Compliance</button>
            </form>
            {complianceResult && <pre>{JSON.stringify(complianceResult, null, 2)}</pre>}
          </section>
        )}

        {activeTab === 'OAuth' && (
          <section className="panel wide">
            <div className="panel-heading">
              <h2>OAuth Providers</h2>
              <button type="button" onClick={() => withBusy('OAuth providers refreshed', loadProviders)}>
                Refresh
              </button>
            </div>
            <pre>{JSON.stringify(providers, null, 2)}</pre>
            <div className="endpoint-row">
              <a href={`${API_V1}/auth/google/login`} target="_blank" rel="noreferrer">Google Login URL</a>
              <a href={`${API_V1}/auth/github/login`} target="_blank" rel="noreferrer">GitHub Login URL</a>
              <a href={`${API_V1}/auth/microsoft/login`} target="_blank" rel="noreferrer">Microsoft Login URL</a>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
