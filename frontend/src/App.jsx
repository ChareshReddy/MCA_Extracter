import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Play, 
  FolderOpen, 
  Terminal,
  Upload, 
  Activity, 
  FileSpreadsheet,
  ExternalLink,
  Cpu,
  Square,
  CheckCircle2,
  Clock
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [inputPath, setInputPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [totalRecords, setTotalRecords] = useState(0);
  const [pendingRecords, setPendingRecords] = useState(0);
  const [status, setStatus] = useState({
    is_running: false,
    progress: 0,
    total: 0,
    logs: [],
    error: null
  });

  const logsEndRef = useRef(null);

  useEffect(() => {
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
    }, 1500);

    const ping = () => axios.post(`${API_BASE}/heartbeat`).catch(() => {});
    ping();
    const heartbeatInterval = setInterval(ping, 5000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(heartbeatInterval);
    };
  }, []);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [status.logs]);

  const handleInputBrowse = async () => {
    try {
      const res = await axios.get(`${API_BASE}/select-input-path`);
      if (res.data.path) {
        setInputPath(res.data.path);
        setTotalRecords(res.data.total);
        setPendingRecords(res.data.pending);
      }
    } catch (err) {
      if (err.response?.data?.message) alert(err.response.data.message);
    }
  };

  const handleBrowse = async () => {
    try {
      const res = await axios.get(`${API_BASE}/select-output-path`);
      if (res.data.path) setOutputPath(res.data.path);
    } catch (err) {
      console.error(err);
    }
  };

  const startScraping = async () => {
    try {
      await axios.get(`${API_BASE}/start`);
    } catch (err) {
      console.error(err);
    }
  };

  const stopScraping = async () => {
    try {
      await axios.get(`${API_BASE}/stop`);
    } catch (err) {
      console.error(err);
    }
  };

  const handleOpenFile = () => axios.get(`${API_BASE}/open-file?path=${encodeURIComponent(outputPath)}`).catch(console.error);
  const handleOpenFolder = () => axios.get(`${API_BASE}/open-folder?path=${encodeURIComponent(outputPath)}`).catch(console.error);

  return (
    <div className="app-container">
      <div className="dashboard-layout">
        {/* Sidebar */}
        <aside className="sidebar-panel">
          <div className="brand-section">
            <div className="brand-logo">
              <Activity size={24} color="var(--accent-blue)" />
            </div>
            <h1 className="brand-name">Companies Data Extracter</h1>
          </div>

          <section className="glass-panel animate-in" style={{ padding: '1.25rem' }}>
            <div className="panel-title">
              <div className="icon-wrapper blue">
                <Upload size={18} />
              </div>
              Input File
            </div>
            
            <div className="input-group">
              <label className="label-text">SELECT INPUT EXCEL (CIN LIST)</label>
              <div className="flex-row">
                <button className="btn-base" onClick={handleInputBrowse} disabled={status.is_running}>
                  <FolderOpen size={16} />
                  Choose File
                </button>
                <div className="file-display">
                  <span className="file-name">{inputPath ? inputPath.split(/[/\\]/).pop() : "No file..."}</span>
                </div>
              </div>
            </div>

            <div className="kpi-stack">
              <div className="kpi-card-vertical blue">
                <div className="kpi-icon-row">
                  <CheckCircle2 size={16} />
                  <span className="kpi-label">TOTAL RECORDS</span>
                </div>
                <span className="kpi-value">{totalRecords}</span>
              </div>
              <div className="kpi-card-vertical orange">
                <div className="kpi-icon-row">
                  <Clock size={16} />
                  <span className="kpi-label">RECORDS PENDING</span>
                </div>
                <span className="kpi-value">{pendingRecords}</span>
              </div>
            </div>
          </section>

          <section className="glass-panel animate-in" style={{ padding: '1.25rem', animationDelay: '0.1s' }}>
            <div className="panel-title">
              <div className="icon-wrapper purple">
                <FileSpreadsheet size={18} />
              </div>
              Output File
            </div>
            
            <div className="input-group">
              <label className="label-text">EXPORT DESTINATION PATH</label>
              <div className="flex-row">
                <button className="btn-base" onClick={handleBrowse} disabled={status.is_running || !inputPath}>
                  <ExternalLink size={16} />
                  Save Path
                </button>
                <div className="file-display">
                  <span className="file-name">{outputPath ? outputPath.split(/[/\\]/).pop() : "No location..."}</span>
                  {outputPath && (
                    <div className="file-actions">
                      <button onClick={handleOpenFile} disabled={status.is_running}><FileSpreadsheet size={14} /></button>
                      <button onClick={handleOpenFolder} disabled={status.is_running}><FolderOpen size={14} /></button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>

          <div style={{ flex: 1 }}></div>

          <button className={`btn-primary ${status.is_running ? 'running-red' : ''}`}
                  onClick={status.is_running ? stopScraping : startScraping}
                  disabled={!inputPath || !outputPath}>
            {status.is_running ? <Activity size={20} className="pulse-slow" /> : <Play size={20} fill="currentColor" />}
            {status.is_running ? "Stop Extraction" : "Start Extraction"}
          </button>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          <header className="content-header">
            <div className="header-info">
              <h2 className="page-title">Dashboard Overview</h2>
              <p className="page-subtitle">Real-time monitoring and control</p>
            </div>
            <div className={`status-badge ${status.is_running ? 'active' : 'idle'}`}>
              <div className="status-dot"></div>
              {status.is_running ? "Engine Active" : "System Idle"}
            </div>
          </header>

          <section className="glass-panel animate-in" style={{ padding: '1.5rem', animationDelay: '0.2s' }}>
            <div className="progress-header">
              <span className="label-text">EXTRACTION PROGRESS</span>
              <span className="progress-stats">
                {status.progress} / {status.total} ({((status.progress / (status.total || 1)) * 100).toFixed(1)}%)
              </span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ 
                width: `${(status.progress / (status.total || 1)) * 100}%`,
                boxShadow: status.is_running ? '0 0 15px rgba(59, 130, 246, 0.4)' : 'none'
              }}></div>
            </div>

            <div className="kpi-row">
              <div className="mini-kpi">
                <span className="mini-label">RECORDS PROCESSED</span>
                <span className="mini-value">{status.progress}</span>
              </div>
              <div className="mini-kpi">
                <span className="mini-label">CURRENT STATE</span>
                <span className={`mini-value ${status.is_running ? 'text-blue' : ''}`}>{status.is_running ? 'RUNNING' : 'IDLE'}</span>
              </div>
              <div className="mini-kpi">
                <span className="mini-label">SUCCESS RATE</span>
                <span className="mini-value text-green">{status.total > 0 ? ((status.progress / status.total) * 100).toFixed(1) : "0.0"}%</span>
              </div>
            </div>
          </section>

          <section className="glass-panel animate-in" style={{ padding: '1.5rem', marginTop: '1.5rem', animationDelay: '0.3s', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div className="panel-title">
              <div className="icon-wrapper gray">
                <Terminal size={18} />
              </div>
              System Log
            </div>
            <div className="log-window">
              {status.logs.length === 0 ? (
                <div className="log-idle">
                  <Cpu size={48} opacity={0.2} />
                  <p>Waiting for extraction to start...</p>
                </div>
              ) : (
                status.logs.map((log, i) => (
                  <div key={i} className="log-line">
                    <span className="log-prompt">&gt;</span>
                    <span className={`log-text ${
                      log.includes('[OK]') || log.includes('[V]') ? 'success' :
                      log.includes('[X]') || log.includes('[!]') || log.includes('[Fail]') ? 'error' :
                      log.includes('[Go]') ? 'info' :
                      log.includes('[Wait]') ? 'warning' : ''
                    }`}>{log}</span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
