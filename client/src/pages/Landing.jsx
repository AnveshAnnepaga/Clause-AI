import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function LandingPage() {
  const [showModal, setShowModal] = useState(false);
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [step, setStep] = useState(1); // 1 = form, 2 = otp
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [timer, setTimer] = useState(300);

  const { login } = useAuth();

  const handleOpenAuth = (mode) => {
    setIsLoginMode(mode === 'login');
    setShowModal(true);
    setStep(1);
    setError('');
    setSuccess('');
    setTimer(300);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      if (isLoginMode) {
        await login(email, password);
      } else {
        if (!isLoginMode) {
          await api.auth.register({ email, password, name: `${firstName} ${lastName}`.trim() });
          // Automatically log them in immediately after successful registration
          await login(email, password);
        }
      }
    } catch (err) {
      setError(err.message || 'An error occurred');
    }
  };

  useEffect(() => {
    let interval;
    if (!isLoginMode && step === 2 && timer > 0) {
      interval = setInterval(() => {
        setTimer((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isLoginMode, step, timer]);

  const handleResendOtp = async () => {
    try {
      setError('');
      setSuccess('');
      await api.auth.resendOtp(email);
      setTimer(300);
      setSuccess('A new OTP has been sent to your email.');
    } catch (err) {
      setError(err.message || 'Failed to resend OTP');
    }
  };

  return (
    <div className="container">
      <nav className="navbar">
        <div className="nav-brand">🤖 ClauseAI</div>
        <div className="nav-links">
          <button className="btn-secondary" onClick={() => handleOpenAuth('login')}>Login</button>
          <button className="btn-primary" onClick={() => handleOpenAuth('register')}>Register</button>
        </div>
      </nav>

      <div style={{ textAlign: 'center', padding: '4rem 0' }}>
        <h1>Contract Intelligence, <span style={{ color: 'var(--primary)' }}>Automated</span>.</h1>
        <p style={{ fontSize: '1.25rem', maxWidth: '700px', margin: '0 auto 3rem auto' }}>
          Upload any contract and let our multi-agent AI engine analyze risks instantly. 
          Our specialized agents cross-check every single clause to protect your interests.
        </p>

        <div className="grid-3" style={{ marginBottom: '4rem' }}>
          <div className="glass-card">
            <h3 style={{fontSize: '2rem', marginBottom:'10px'}}>⚖️</h3>
            <h4 style={{color: 'white', marginBottom:'10px'}}>Legal Agent</h4>
            <p style={{fontSize: '0.9rem'}}>Checks for indemnification, governing law, and liability limits.</p>
          </div>
          <div className="glass-card">
            <h3 style={{fontSize: '2rem', marginBottom:'10px'}}>📋</h3>
            <h4 style={{color: 'white', marginBottom:'10px'}}>Compliance Agent</h4>
            <p style={{fontSize: '0.9rem'}}>Ensures GDPR, CCPA, and regulatory alignment across clauses.</p>
          </div>
          <div className="glass-card">
            <h3 style={{fontSize: '2rem', marginBottom:'10px'}}>💰</h3>
            <h4 style={{color: 'white', marginBottom:'10px'}}>Finance Agent</h4>
            <p style={{fontSize: '0.9rem'}}>Validates payment terms, late fees, and financial obligations.</p>
          </div>
        </div>

        <button className="btn-primary" onClick={() => handleOpenAuth('register')} style={{ padding: '1rem 3rem', fontSize: '1.1rem' }}>
          🚀 Start Analyzing Now
        </button>
      </div>

      {showModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: '400px', position: 'relative' }}>
            <button 
              onClick={() => setShowModal(false)}
              style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'none', border: 'none', color: 'white', fontSize: '1.5rem', cursor: 'pointer' }}
            >
              ×
            </button>
            <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>
              {isLoginMode ? 'Welcome Back' : 'Create Account'}
            </h2>
            
            {error && <div style={{ color: '#ef4444', marginBottom: '1rem', textAlign: 'center', background: 'rgba(239, 68, 68, 0.1)', padding: '0.5rem', borderRadius: '8px' }}>{error}</div>}
            {success && <div style={{ color: '#10b981', marginBottom: '1rem', textAlign: 'center', background: 'rgba(16, 185, 129, 0.1)', padding: '0.5rem', borderRadius: '8px' }}>{success}</div>}

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {!isLoginMode && (
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <div className="input-group">
                    <label>First Name</label>
                    <input className="input-field" type="text" value={firstName} onChange={e => setFirstName(e.target.value)} required />
                  </div>
                  <div className="input-group">
                    <label>Last Name</label>
                    <input className="input-field" type="text" value={lastName} onChange={e => setLastName(e.target.value)} required />
                  </div>
                </div>
              )}
              
              <>
                  <div className="input-group" style={{ marginBottom: 0 }}>
                    <label>Email Address</label>
                    <input className="input-field" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
                  </div>
                  <div className="input-group" style={{ marginBottom: 0 }}>
                    <label>Password</label>
                    <input className="input-field" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
                  </div>
              </>



              <button type="submit" className="btn-primary" style={{ marginTop: '1rem' }}>
                {isLoginMode ? 'Sign In' : 'Create Account'}
              </button>
            </form>

            <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.9rem' }}>
              {isLoginMode ? "Don't have an account? " : "Already have an account? "}
              <span 
                style={{ color: 'var(--primary)', cursor: 'pointer' }}
                onClick={() => { setIsLoginMode(!isLoginMode); setStep(1); setError(''); setSuccess(''); setTimer(300); }}
              >
                {isLoginMode ? 'Sign up' : 'Log in'}
              </span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
