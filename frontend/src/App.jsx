import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Activity, Download, Upload, Play, Settings, Terminal, RefreshCw } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || ''; // Relative path if empty or use env var

function App() {
  const [file, setFile] = useState(null);
  const [uploadedPath, setUploadedPath] = useState('');
  
  const [status, setStatus] = useState({
    is_running: false,
    logs: [],
    progress: 0,
    total: 0,
    output_file: null,
    error: null
  });

  const logsEndRef = useRef(null);

  // Poll status
  useEffect(() => {
    let interval;
    if (status.is_running) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/status`);
          setStatus(res.data);
        } catch (e) {
          console.error("Failed to fetch status", e);
        }
      }, 2000);
    } else {
      // Fetch once when not running just to get latest state on load
      axios.get(`${API_BASE}/status`).then(res => setStatus(res.data)).catch(console.error);
    }
    return () => clearInterval(interval);
  }, [status.is_running]);

  // Auto-scroll disabled per user request to prevent screen movement
  /*
  useEffect(() => {
    const terminal = logsEndRef.current?.parentNode;
    if (terminal) {
      const isNearBottom = terminal.scrollHeight - terminal.scrollTop - terminal.clientHeight < 100;
      if (isNearBottom) {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }
    }
  }, [status.logs]);
  */

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    setFile(selectedFile);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await axios.post(`${API_BASE}/upload`, formData);
      setUploadedPath(res.data.path);
    } catch (err) {
      console.error("Upload failed", err);
      alert("Failed to upload file");
    }
  };

  const startScraping = async () => {
    if (!uploadedPath) {
      alert("Please upload an input file first.");
      return;
    }
    try {
      await axios.post(`${API_BASE}/start?input_file=${uploadedPath}`);
      setStatus(prev => ({ ...prev, is_running: true, logs: ["Starting scraper engine..."] }));
    } catch (err) {
      console.error(err);
      alert("Failed to start scraping.");
    }
  };

  const stopScraping = async () => {
    try {
      await axios.post(`${API_BASE}/stop`);
    } catch (err) {
      console.error(err);
      alert("Failed to stop scraping.");
    }
  };

  const downloadResults = () => {
    window.open(`${API_BASE}/download`, '_blank');
  };

  return (
    <div style={{ padding: '3rem', display: 'flex', flexDirection: 'column', gap: '3rem', flex: 1 }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '1600px', margin: '0 auto', width: '95%' }}>
        <div>
          <h1 style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>Pankaj Vikram IT Group</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>High-Volume Data Extraction Engine</p>
        </div>
        <div className={`status-badge ${status.is_running ? 'status-running animate-pulse' : 'status-idle'}`}>
          <Activity size={14} />
          {status.is_running ? 'Engine Active' : 'System Idle'}
        </div>
      </header>

      <main className="dashboard-container" style={{ padding: 0 }}>
        {/* Left Column: Config */}
        <div className="left-column">
          <section className="panel">
            <div className="panel-header">
              <Upload size={20} color="var(--accent-primary)" />
              Data Source
            </div>
            <div className="form-group">
              <label>Input Excel File (CIN List)</label>
              <input type="file" accept=".xlsx, .xls" onChange={handleFileUpload} disabled={status.is_running} />
              {file && <p style={{ fontSize: '0.8rem', color: 'var(--success)' }}>✓ {file.name} uploaded</p>}
            </div>
          </section>

          <div style={{ display: 'flex', gap: '1rem' }}>
            {!status.is_running ? (
              <button 
                className="btn btn-primary" 
                style={{ flex: 1 }} 
                onClick={startScraping}
                disabled={!uploadedPath}
              >
                <Play size={18} />
                Initialize Engine
              </button>
            ) : (
              <button 
                className="btn btn-danger" 
                style={{ flex: 1 }} 
                onClick={stopScraping}
              >
                <RefreshCw size={18} className="animate-pulse" />
                Stop Engine
              </button>
            )}
            <button 
              className="btn btn-success"
              onClick={downloadResults}
              disabled={!status.output_file}
              title={!status.output_file ? "Wait for first results to export" : "Download current results"}
            >
              <Download size={18} />
              Export
            </button>
          </div>
        </div>

        {/* Right Column: Logs */}
        <div style={{ height: '100%', overflow: 'hidden' }}>
          <section className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div className="panel-header">
              <Terminal size={20} color="var(--accent-primary)" />
              System Telemetry
            </div>
            <div className="terminal">
              {status.logs.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)' }}>Waiting for system initialization...</p>
              ) : (
                status.logs.map((log, i) => (
                  <p key={i} style={{ 
                    color: log.includes('[X]') ? '#ef4444' : 
                           log.includes('[OK]') ? '#10b981' : 
                           log.includes('[V]') ? '#3b82f6' : 
                           log.includes('[Wait]') ? '#f59e0b' : '#34d399'
                  }}>
                    {log}
                  </p>
                ))
              )}
              {status.error && <p style={{ color: '#ef4444', fontWeight: 'bold' }}>CRITICAL ERROR: {status.error}</p>}
              <div ref={logsEndRef} />
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
