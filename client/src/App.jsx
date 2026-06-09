import React, { useState } from 'react';
import LandingPage from './pages/Landing';
import Dashboard from './pages/Dashboard';
import { AuthProvider, useAuth } from './context/AuthContext';

const AppContent = () => {
  const { user } = useAuth();
  
  if (user) {
    return <Dashboard />;
  }
  
  return <LandingPage />;
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
