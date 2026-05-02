import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Play, 
  RefreshCw, 
  FolderOpen, 
  Terminal, 
  Upload, 
  Activity, 
  CheckCircle2, 
  AlertCircle,
  FileSpreadsheet,
  ExternalLink,
  Cpu,
  Lock,
  Unlock
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [inputPath, setInputPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [totalRecords, setTotalRecords] = useState(0);
  const [pendingRecords, setPendingRecords] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const [status, setStatus] = useState({
    is_running: false,
    progress: 0,
    total: 0,
    logs: [],
    error: null
  });

  const logsEndRef = useRef(null);
  const terminalRef = useRef(null);

  useEffect(() => {
    // Status polling
    const statusInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/status`);
        const data = res.data;
        setStatus(data);
        
        if (data.input_file) setInputPath(data.input_file);
        if (data.output_file) setOutputPath(data.output_file);
        if (data.total) setTotalRecords(data.total);
        if (data.pending) setPendingRecords(data.pending);
        
      } catch (err) {
        console.error("Status check failed", err);
      }
    }, 3000); // 3s interval to reduce console log noise

    // Heartbeat logic for auto-shutdown
    const ping = async () => {
      try {
        await axios.post(`${API_BASE}/heartbeat`);
      } catch (e) {
        console.error("Heartbeat failed", e);
      }
    };
    
    ping(); // Initial ping
    const heartbeatInterval = setInterval(ping, 5000); // Ping every 5s

    // Explicit disconnect on tab close/refresh
    const handleUnload = () => {
      navigator.sendBeacon(`${API_BASE}/disconnect`);
    };
    window.addEventListener('beforeunload', handleUnload);

    return () => {
      clearInterval(statusInterval);
      clearInterval(heartbeatInterval);
      window.removeEventListener('beforeunload', handleUnload);
    };
  }, []);

  const handleInputBrowse = async () => {
    try {
      const res = await axios.get(`${API_BASE}/select-input-path`);
      if (res.data.path) {
        const fileExt = res.data.path.split('.').pop().toLowerCase();
        if (fileExt !== 'xlsx' && fileExt !== 'xls') {
          alert("INVALID FILE TYPE: Please select a valid Excel file (.xlsx or .xls)");
          return;
        }
        setInputPath(res.data.path);
        setTotalRecords(res.data.total);
        setPendingRecords(res.data.pending);
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.message) {
        alert("UPLOAD ERROR: " + err.response.data.message);
      } else {
        console.error("Browse Input Error:", err);
      }
    }
  };

  const handleBrowse = async () => {
    try {
      const inputFilename = inputPath.split(/[/\\]/).pop();
      const res = await axios.get(`${API_BASE}/select-output-path?input_filename=${encodeURIComponent(inputFilename)}`);
      if (res.data.path) setOutputPath(res.data.path);
    } catch (err) {
      console.error("Browse Error:", err);
    }
  };

  const startScraping = async () => {
    try {
      await axios.post(`${API_BASE}/start?input_file=${encodeURIComponent(inputPath)}&output_path=${encodeURIComponent(outputPath)}&total=${totalRecords}&pending=${pendingRecords}`);
    } catch (err) {
      console.error("Start Error:", err);
    }
  };

  const stopScraping = async () => {
    try {
      await axios.post(`${API_BASE}/stop`);
    } catch (err) {
      console.error("Stop Error:", err);
    }
  };

  const handleOpenFile = async () => {
    try {
      await axios.get(`${API_BASE}/open-file?path=${encodeURIComponent(outputPath)}`);
    } catch (err) {
      console.error("Open File Error:", err);
      alert("Error opening file: " + (err.response?.data?.message || err.message));
    }
  };

  const handleOpenFolder = async () => {
    try {
      await axios.get(`${API_BASE}/open-folder?path=${encodeURIComponent(outputPath)}`);
    } catch (err) {
      console.error("Open Folder Error:", err);
      alert("Error opening folder: " + (err.response?.data?.message || err.message));
    }
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="logo-container">
          <h1>Companies Data Extractor</h1>
        </div>
        <div className={`status-badge ${status.is_running ? 'status-running animate-pulse' : 'status-idle'}`} 
             style={{ 
               padding: '0.5rem 1rem', 
               borderRadius: '99px', 
               fontSize: '0.8rem', 
               fontWeight: '600',
               display: 'flex',
               alignItems: 'center',
               gap: '0.5rem',
               background: status.is_running ? 'rgba(59, 130, 246, 0.1)' : 'rgba(156, 163, 175, 0.1)',
               color: status.is_running ? '#3b82f6' : '#9ca3af',
               border: `1px solid ${status.is_running ? 'rgba(59, 130, 246, 0.2)' : 'rgba(156, 163, 175, 0.2)'}`
             }}>
          <Activity size={16} />
          {status.is_running ? "Engine Active" : "System Idle"}
        </div>
      </header>

      <main className="dashboard-main">
        {/* Sidebar */}
        <aside className="sidebar" style={{ 
          gap: '1rem', 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column',
          justifyContent: 'flex-start'
        }}>
          {/* Input File Section */}
          <section className="glass-panel animate-in" style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '1.25rem', 
            padding: '1.5rem',
            background: 'linear-gradient(180deg, var(--panel-bg) 0%, rgba(17, 24, 39, 0.9) 100%)',
            border: '1px solid var(--glass-border)'
          }}>
            <div className="panel-title">
              <div style={{ padding: '0.4rem', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.1)', display: 'flex' }}>
                <Upload size={20} color="var(--accent-blue)" />
              </div>
              Input Configuration
            </div>
            
            <div className="input-group">
              <label className="label-text" style={{ fontSize: '0.75rem', opacity: 0.8 }}>SOURCE WORKBOOK (.XLSX)</label>
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button className="btn-base" 
                        style={{ padding: '0.6rem 1rem', background: 'var(--panel-hover)', border: '1px solid var(--border-bright)', color: 'white', flexShrink: 0, borderRadius: '10px' }}
                        onClick={handleInputBrowse}
                        disabled={status.is_running}>
                  <FolderOpen size={18} />
                  Browse
                </button>
                <div className="file-display" style={{ flex: 1, minWidth: 0, background: 'rgba(0,0,0,0.4)', borderRadius: '10px' }}>
                  <span className="file-name" style={{ fontWeight: '500' }}>{inputPath ? inputPath.split(/[/\\]/).pop() : "No file selected..."}</span>
                </div>
              </div>
            </div>

            <div className="stats-compact-container" style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
              <div className="stat-box-adaptive total-records" style={{ flex: 1, padding: '1rem', background: 'rgba(59, 130, 246, 0.05)', border: '1px solid rgba(59, 130, 246, 0.1)' }}>
                <div className="stat-label-adaptive" style={{ fontSize: '0.65rem' }}>TOTAL</div>
                <div className="stat-value-adaptive" style={{ fontSize: '1.5rem' }}>{totalRecords || "0"}</div>
              </div>
              
              <div className="stat-box-adaptive pending-records" style={{ flex: 1, padding: '1rem', background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.1)' }}>
                <div className="stat-label-adaptive" style={{ fontSize: '0.65rem' }}>PENDING</div>
                <div className="stat-value-adaptive" style={{ color: 'var(--warning-orange)', fontSize: '1.5rem' }}>{pendingRecords || "0"}</div>
              </div>
            </div>
          </section>

          {/* Output File Section */}
          <section className="glass-panel animate-in" style={{ padding: '1.5rem', animationDelay: '0.1s', background: 'linear-gradient(180deg, var(--panel-bg) 0%, rgba(17, 24, 39, 0.9) 100%)' }}>
            <div className="panel-title">
              <div style={{ padding: '0.4rem', borderRadius: '8px', background: 'rgba(139, 92, 246, 0.1)', display: 'flex' }}>
                <FileSpreadsheet size={20} color="var(--accent-purple)" />
              </div>
              Output Destination
            </div>
            
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label className="label-text" style={{ fontSize: '0.75rem', opacity: 0.8 }}>EXPORT PATH</label>
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button className="btn-base" 
                        style={{ padding: '0.6rem 1rem', background: 'var(--panel-hover)', border: '1px solid var(--border-bright)', color: 'white', borderRadius: '10px' }}
                        onClick={handleBrowse}
                        disabled={status.is_running || !inputPath}>
                  <ExternalLink size={18} />
                  Path
                </button>
                <div className="file-display" style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '10px' }}>
                  <span className="file-name">{outputPath ? outputPath.split(/[/\\]/).pop() : "Not set..."}</span>
                  {outputPath && (
                    <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '0.5rem' }}>
                      <button onClick={handleOpenFile} disabled={status.is_running} style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer' }}>
                        <FileSpreadsheet size={16} />
                      </button>
                      <button onClick={handleOpenFolder} disabled={status.is_running} style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer' }}>
                        <FolderOpen size={16} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>

          <div style={{ flex: 1 }}></div>

          <button className={`btn-primary animate-in ${status.is_running ? 'running' : ''}`}
                  style={{ 
                    padding: '1.5rem', 
                    borderRadius: '16px', 
                    fontSize: '1.25rem', 
                    fontWeight: '800',
                    letterSpacing: '0.02em',
                    textTransform: 'uppercase',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.4rem',
                    height: 'auto',
                    border: '1px solid rgba(255,255,255,0.1)',
                    boxShadow: status.is_running ? '0 0 40px rgba(239, 68, 68, 0.2)' : '0 0 40px rgba(59, 130, 246, 0.2)'
                  }}
                  onClick={status.is_running ? stopScraping : startScraping}
                  disabled={!inputPath || !outputPath}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {status.is_running ? <Square size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" />}
              {status.is_running ? "Stop Engine" : "Launch Engine"}
            </div>
            <span style={{ fontSize: '0.7rem', opacity: 0.7, fontWeight: '500' }}>
              {status.is_running ? "TERMINATE ALL PROCESSES" : "START HIGH-VOLUME EXTRACTION"}
            </span>
          </button>
        </aside>

        {/* Main Content Area */}
        <section className="content-area">
          {/* Progress Header Panel */}
          <div className="glass-panel animate-in" style={{ animationDelay: '0.2s' }}>
            <div className="progress-container">
              <div className="progress-header">
                <span style={{ fontWeight: '600', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>EXTRACTION PROGRESS</span>
                <span style={{ fontWeight: '700', color: 'var(--accent-blue)' }}>
                  {status.progress} / {pendingRecords} ({pendingRecords > 0 ? ((status.progress / pendingRecords) * 100).toFixed(1) : "0.0"}%)
                </span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${pendingRecords > 0 ? (status.progress / pendingRecords) * 100 : 0}%` }}></div>
              </div>
            </div>

            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Records Processed</div>
                <div className="stat-value" style={{ color: 'var(--accent-blue)' }}>{status.progress}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Current State</div>
                <div className="stat-value" style={{ color: status.is_running ? 'var(--success-green)' : 'var(--text-dim)', fontSize: '1rem', textTransform: 'uppercase' }}>
                  {status.is_running ? "Running" : "Idle"}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Success Rate</div>
                <div className="stat-value" style={{ color: 'var(--success-green)' }}>
                  {pendingRecords > 0 ? ((status.progress / pendingRecords) * 100).toFixed(1) : "0.0"}%
                </div>
              </div>
            </div>
          </div>

          {/* System Log Panel */}
          <section className="glass-panel animate-in" style={{ flex: 1, display: 'flex', flexDirection: 'column', animationDelay: '0.3s' }}>
            <div className="panel-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Terminal size={20} color="var(--accent-blue)" />
                System Log
              </div>
            </div>
            <div className="terminal-wrapper" ref={terminalRef}>
              {status.logs.map((log, i) => (
                  <div key={i} style={{ 
                    marginBottom: '0.25rem',
                    color: log.includes('[OK]') ? 'var(--success-green)' : 
                           log.includes('[V]') ? 'var(--success-green)' : 
                           log.includes('[Save]') ? 'var(--success-green)' : 
                           log.includes('[KillSwitch]') ? 'var(--success-green)' : 
                           log.includes('[Go]') ? 'var(--accent-blue)' : 
                           log.includes('[Wait]') ? 'var(--warning-orange)' : 
                           log.includes('[X]') ? 'var(--danger-red)' : 'var(--text-main)'
                  }}>
                    <span style={{ color: 'var(--text-dim)', marginRight: '0.5rem' }}>&gt;</span>
                    {log}
                  </div>
                ))
              }
              {status.error && (
                <div style={{ color: 'var(--danger-red)', fontWeight: 'bold', marginTop: '1rem', padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                  CRITICAL ERROR: {status.error}
                </div>
              )}
              <div ref={logsEndRef} />
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;
