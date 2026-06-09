const API_URL = import.meta.env.PROD ? '' : '/api';

export const api = {
  async fetch(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    const headers = {
      ...options.headers,
    };
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Generate/retrieve guest device id
    let deviceId = localStorage.getItem('device_id');
    if (!deviceId) {
      deviceId = crypto.randomUUID();
      localStorage.setItem('device_id', deviceId);
    }
    headers['X-Device-Id'] = deviceId;

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      let errorMsg = 'API Request Failed';
      if (error.detail) {
        if (typeof error.detail === 'string') {
          errorMsg = error.detail;
        } else if (Array.isArray(error.detail)) {
          errorMsg = error.detail.map(e => e.msg).join(', ');
        } else {
          errorMsg = JSON.stringify(error.detail);
        }
      }
      throw new Error(errorMsg);
    }

    return response.json();
  },

  auth: {
    login: (email, password) => 
      api.fetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      }),
      
    register: (data) => 
      api.fetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data)
      }),
      
    verifyOtp: (email, otp) => 
      api.fetch('/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ email, otp })
      }),
      
    resendOtp: (email) => 
      api.fetch('/auth/resend-otp', {
        method: 'POST',
        body: JSON.stringify({ email })
      }),
      
    getMe: () => api.fetch('/auth/me'),
  },
  
  reports: {
    getAnalytics: () => api.fetch('/analytics'),
    getAll: () => api.fetch('/reports'),
    get: (id) => api.fetch(`/reports/${id}`),
  },

  analysis: {
    parse: (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.fetch('/parse_file', {
        method: 'POST',
        body: formData
      });
    },

    analyzeText: (text, question, run_all_agents = false) => {
      return api.fetch('/analyze_text', {
        method: 'POST',
        body: JSON.stringify({
          contract_text: text,
          question: question,
          run_all_agents: run_all_agents,
          intent_override: run_all_agents ? 'executive_review' : 'risk_analysis'
        })
      });
    },

    upload: (file, question, run_all_agents = false) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('question', question);
      formData.append('run_all_agents', run_all_agents);
      formData.append('intent_override', run_all_agents ? 'executive_review' : 'risk_analysis');
      
      return api.fetch('/analyze', {
        method: 'POST',
        body: formData
      });
    }
  }
};
