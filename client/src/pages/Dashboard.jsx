import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export default function Dashboard() {
  const { user, logout } = useAuth();
  
  // State
  const [history, setHistory] = useState([]);
  const [file, setFile] = useState(null);
  const [documentText, setDocumentText] = useState('');
  const [step, setStep] = useState('upload'); // upload -> verify -> results
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (user) {
      fetchHistory();
    } else {
      setHistory([]);
    }
  }, [user]);

  const fetchHistory = async () => {
    try {
      const res = await api.reports.getAll();
      setHistory(res.reports || []);
    } catch (err) {
      console.error("Failed to load history", err);
    }
  };

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    
    setFile(selectedFile);
    setIsLoading(true);
    setError('');
    
    try {
      // 1. Upload and parse to get raw text for verification
      const res = await api.analysis.parse(selectedFile);
      setDocumentText(res.text);
      setStep('verify');
    } catch (err) {
      setError(err.message || 'Failed to parse document.');
      setFile(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyze = async (runAllAgents = false) => {
    setIsLoading(true);
    setError('');
    
    try {
      // We pass the already extracted text to the backend
      const data = await api.analysis.analyzeText(documentText, question, runAllAgents);
      setReport(data);
      setStep('results');
      fetchHistory(); // Refresh history
    } catch (err) {
      setError(err.message || 'An error occurred during analysis.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const loadReport = async (reportId, contractName) => {
    setIsLoading(true);
    setError('');
    try {
      const res = await api.reports.get(reportId);
      if (res.ok && res.report && res.report.analysis_json) {
        setReport(res.report.analysis_json);
        setDocumentText(`[Document Text is not stored for historical reports. This is the analysis for: ${contractName}]`);
        setQuestion(res.report.analysis_json.question || '');
        setStep('results');
      }
    } catch (err) {
      setError(err.message || 'Failed to load report.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetWorkspace = () => {
    setFile(null);
    setDocumentText('');
    setReport(null);
    setQuestion('');
    setError('');
    setStep('upload');
  };

  const getHighlightedHtml = () => {
    if (!documentText) return '';
    
    // Escape HTML to prevent XSS from document content
    let html = documentText
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    if (report && report.analysis) {
      const evidenceList = report.analysis.key_evidence || [];
      // If intent was fact_summary, evidence might be in analysis.key_evidence with different format
      const evidenceStrings = evidenceList.map(e => typeof e === 'string' ? e : e.text).filter(Boolean);
      
      evidenceStrings.forEach(text => {
        if (text.length > 5) {
          const escapedEvidence = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
            
          const regexStr = escapedEvidence
            .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            .replace(/\\\s+/g, '\\s+')
            .replace(/\s+/g, '\\s+');
            
          try {
            const regex = new RegExp(`(${regexStr})`, 'gi');
            html = html.replace(regex, `<mark class="highlight">$1</mark>`);
          } catch (e) {
            html = html.split(escapedEvidence).join(`<mark class="highlight">${escapedEvidence}</mark>`);
          }
        }
      });
    }
    return html;
  };

  return (
    <div className="dashboard-layout">
      {/* LEFT SIDEBAR - HISTORY */}
      <div className="sidebar">
        <div style={{ marginBottom: '2rem' }}>
          <h2 className="nav-brand" style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>🤖 ClauseAI</h2>
          <button className="btn-primary" style={{ width: '100%' }} onClick={resetWorkspace}>
            + New Analysis
          </button>
        </div>

        <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem', textTransform: 'uppercase' }}>
          Analysis History
        </h3>
        
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {history.length === 0 ? (
            <p style={{ fontSize: '0.85rem' }}>No past reports.</p>
          ) : (
            history.map(item => (
              <div key={item.id} className="sidebar-item" onClick={() => loadReport(item.id, item.contract_name)}>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.25rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {item.contract_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {new Date(item.created_at).toLocaleDateString()}
                </div>
              </div>
            ))
          )}
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>{user?.email || 'Guest'}</div>
          <button className="btn-secondary" style={{ width: '100%', padding: '0.5rem' }} onClick={logout}>Sign Out</button>
        </div>
      </div>

      {/* MAIN WORKSPACE - SPLIT PANE */}
      <div className="main-content">
        {step === 'upload' && (
          <div className="flex-center" style={{ height: '100%', padding: '2rem' }}>
            <div className="glass-card" style={{ textAlign: 'center', padding: '4rem', maxWidth: '600px', width: '100%' }}>
              <h2>Start New Analysis</h2>
              <p style={{ margin: '1rem 0 2rem 0' }}>Upload your PDF or DOCX file. We'll extract the text for you to verify before sending it to our agents.</p>
              
              <input 
                type="file" 
                onChange={handleFileChange}
                style={{ display: 'none' }}
                id="file-upload"
              />
              <label htmlFor="file-upload" className="btn-primary" style={{ display: 'inline-block', cursor: 'pointer', opacity: isLoading ? 0.7 : 1 }}>
                {isLoading ? 'Extracting Text...' : 'Browse Files'}
              </label>
              
              {error && <div style={{ color: '#ef4444', marginTop: '1rem' }}>{error}</div>}
            </div>
          </div>
        )}

        {step !== 'upload' && (
          <div className="split-pane">
            
            {/* LEFT PANE: DOCUMENT VIEWER */}
            <div className="pane-left">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 style={{ color: 'var(--primary)' }}>Document Viewer</h3>
                <span className="badge">{file?.name}</span>
              </div>
              
              <div 
                className="document-text glass-card" 
                style={{ padding: '2rem', background: 'rgba(0,0,0,0.4)', border: 'none' }}
                dangerouslySetInnerHTML={{ __html: getHighlightedHtml() }}
              />
            </div>

            {/* RIGHT PANE: ANALYSIS WORKSPACE */}
            <div className="pane-right">
              {step === 'verify' && (
                <div>
                  <h2 style={{ marginBottom: '1rem' }}>Verify & Analyze</h2>
                  <p style={{ marginBottom: '2rem' }}>
                    We've extracted the text from your document (shown on the left). 
                    If it looks correct, you can ask a specific question or run a comprehensive multi-agent analysis.
                  </p>

                  <div className="glass-card">
                    <div className="input-group">
                      <label>Ask a specific question (Required)</label>
                      <input 
                        className="input-field" 
                        type="text" 
                        placeholder="e.g. What are the termination conditions?" 
                        value={question}
                        onChange={e => setQuestion(e.target.value)}
                      />
                    </div>

                    {error && <div style={{ color: '#ef4444', marginBottom: '1rem' }}>{error}</div>}

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <button className="btn-primary" onClick={() => handleAnalyze(false)} disabled={isLoading || !question.trim()}>
                        {isLoading ? 'Analyzing...' : 'Analyze Specific Question'}
                      </button>
                      <button className="btn-secondary" onClick={() => handleAnalyze(true)} disabled={isLoading || !question.trim()}>
                        {isLoading ? 'Analyzing...' : 'Analyze using ALL Four Agents'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {step === 'results' && report && (
                <div className="report-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2>Analysis Results</h2>
                    <button className="btn-secondary" onClick={handlePrint}>📥 Download Report</button>
                  </div>

                  <div style={{ width: '100%', display: 'flex', gap: '0.5rem', marginBottom: '2rem' }}>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="Ask another question about this document..."
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={(e) => { if(e.key === 'Enter') handleAnalyze(false); }}
                      style={{ flex: 1 }}
                    />
                    <button 
                      className="btn-secondary" 
                      onClick={() => handleAnalyze(false)}
                      disabled={isLoading || !question.trim()}
                    >
                      Ask
                    </button>
                  </div>

                  <div className="glass-card" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
                    {/* Always show the Answer section if a question was asked and QA data exists */}
                    {question && report.qa && (
                      <div style={{ marginBottom: report.intent === 'fact_summary' || report.intent === 'qa' ? '0' : '2rem' }}>
                        <h3 style={{ color: 'var(--primary)', marginBottom: '1rem' }}>Answer</h3>
                        {report.qa?.sections?.length > 0 ? (
                          report.qa.sections.map((sec, i) => (
                            <div key={i} style={{ marginBottom: '1.5rem' }}>
                              <h4 style={{ color: '#eab308', marginBottom: '0.5rem' }}>{sec.heading}</h4>
                              <ul style={{ paddingLeft: '1.5rem' }}>
                                {sec.bullets.map((b, j) => <li key={j} style={{ marginBottom: '0.5rem' }}>{b}</li>)}
                              </ul>
                            </div>
                          ))
                        ) : (
                          <p style={{ color: 'var(--text-muted)' }}>No direct clauses could be found answering your question. This might happen if the document doesn't contain the specific terms, or if there was a typo in the question.</p>
                        )}
                      </div>
                    )}

                    {/* Render Executive Summary / Agent Findings if applicable */}
                    {report.intent !== 'fact_summary' && report.intent !== 'qa' && (
                      <>
                        {report.intent === 'executive_review' && (
                          <>
                            <h3 style={{ color: '#eab308', marginBottom: '1rem' }}>Executive Summary</h3>
                        {report.analysis?.executive_summary_points?.length > 0 ? (
                          <ul style={{ paddingLeft: '1.5rem', marginBottom: '2rem' }}>
                            {report.analysis.executive_summary_points.map((pt, i) => (
                              <li key={i} style={{ marginBottom: '0.5rem' }}>{pt}</li>
                            ))}
                          </ul>
                        ) : (
                          <p>No summary generated.</p>
                            )}
                          </>
                        )}
                        
                        <h3 style={{ color: '#eab308', marginTop: report.intent === 'executive_review' ? '2rem' : '0', marginBottom: '1rem' }}>Agent Findings</h3>
                        {['legal', 'compliance', 'finance', 'operations'].map(agent => {
                          const data = report.agent_analysis?.[agent] || report.analysis?.[agent];
                          if (!data || data.skipped || !data.findings || data.findings.length === 0) return null;
                          
                          const riskColor = data.risk_level === 'high' ? '#ef4444' : data.risk_level === 'medium' ? '#eab308' : '#10b981';
                          
                          return (
                            <div key={agent} style={{ padding: '1.5rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', marginBottom: '1rem', borderLeft: `4px solid ${riskColor}` }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                <h4 style={{ color: 'white', margin: 0, textTransform: 'capitalize' }}>🤖 {agent} Agent</h4>
                                <span className="badge" style={{ background: `rgba(${riskColor === '#ef4444' ? '239,68,68' : riskColor === '#eab308' ? '234,179,8' : '16,185,129'}, 0.1)`, color: riskColor, borderColor: `rgba(${riskColor === '#ef4444' ? '239,68,68' : riskColor === '#eab308' ? '234,179,8' : '16,185,129'}, 0.2)` }}>
                                  Risk: {(data.risk_level || 'unknown').toUpperCase()}
                                </span>
                              </div>
                              <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
                                {data.findings.map((f, i) => (
                                  <li key={i} style={{ marginBottom: '0.5rem' }}>{f}</li>
                                ))}
                              </ul>
                            </div>
                          );
                        })}
                      </>
                    )}

                    {/* Add button to re-analyze with all agents */}
                    <div style={{ marginTop: '3rem', paddingTop: '2rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'center' }}>
                      <button 
                        className="btn-primary" 
                        onClick={() => handleAnalyze(true)}
                        disabled={isLoading}
                        style={{ padding: '1rem 2rem', fontSize: '1.1rem', boxShadow: '0 0 20px rgba(16, 185, 129, 0.4)' }}
                      >
                        {isLoading ? '⏳ Analyzing...' : '🚀 Analyze Document using ALL Models'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
