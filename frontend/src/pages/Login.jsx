import React, { useState } from 'react';
import { login, register } from '../api';
import { useNavigate } from 'react-router-dom';

function Login({ setToken }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (isRegistering) {
        await register(username, password);
        // Auto login after register
        const res = await login(username, password);
        setToken(res.data.access_token);
        navigate('/dashboard');
      } else {
        const res = await login(username, password);
        setToken(res.data.access_token);
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred');
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
      <h2>{isRegistering ? 'Register' : 'Login'}</h2>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', width: '300px', gap: '10px' }}>
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">{isRegistering ? 'Register' : 'Login'}</button>
      </form>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button 
        onClick={() => setIsRegistering(!isRegistering)}
        style={{ marginTop: '10px', background: 'none', border: 'none', color: 'blue', cursor: 'pointer' }}
      >
        {isRegistering ? 'Already have an account? Login' : 'Need an account? Register'}
      </button>
    </div>
  );
}

export default Login;
