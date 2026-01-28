import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));

  const setTokenAndStorage = (newToken) => {
    if (newToken) {
        localStorage.setItem('token', newToken);
    } else {
        localStorage.removeItem('token');
    }
    setToken(newToken);
  };

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/login" element={<Login setToken={setTokenAndStorage} />} />
          <Route 
            path="/dashboard" 
            element={token ? <Dashboard setToken={setTokenAndStorage} /> : <Navigate to="/login" />} 
          />
          <Route path="*" element={<Navigate to={token ? "/dashboard" : "/login"} />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
