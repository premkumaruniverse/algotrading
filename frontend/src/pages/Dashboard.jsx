import React, { useState, useEffect } from 'react';
import { getMe, updateCredentials, generateToken, toggleTrading, getTrades } from '../api';

function Dashboard({ setToken }) {
  const [user, setUser] = useState(null);
  const [trades, setTrades] = useState([]);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [numLots, setNumLots] = useState(1);
  const [requestToken, setRequestToken] = useState('');
  const [message, setMessage] = useState('');

  // Initial Fetch for Configuration
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const userRes = await getMe();
        setUser(userRes.data);
        setApiKey(userRes.data.api_key || '');
        setApiSecret(userRes.data.api_secret || '');
        setNumLots(userRes.data.num_lots || 1);
      } catch (err) {
        console.error(err);
        if (err.response?.status === 401) {
          setToken(null);
        }
      }
    };
    fetchConfig();
  }, [setToken]);

  // Polling for Trades and Status (Does NOT overwrite config inputs)
  const fetchData = async () => {
    try {
      // Refresh user to get latest trading status and token status, but NOT overwrite keys if user is editing
      // Actually, we should probably separate "User Config" from "User Status"
      const userRes = await getMe();
      // Only update status fields
      setUser(prev => ({ ...prev, ...userRes.data })); 
      // Do NOT setApiKey/setApiSecret here to avoid overwriting user input while typing

      const tradesRes = await getTrades();
      setTrades(tradesRes.data);
    } catch (err) {
      console.error(err);
      if (err.response?.status === 401) {
        setToken(null);
      }
    }
  };

  useEffect(() => {
    fetchData(); // Initial load of trades
    const interval = setInterval(fetchData, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  const handleUpdateCredentials = async () => {
    try {
      await updateCredentials(apiKey, apiSecret, numLots);
      setMessage('Credentials updated successfully');
      fetchData();
    } catch (err) {
      setMessage('Error updating credentials');
    }
  };

  const handleGenerateToken = async () => {
    try {
      await generateToken(requestToken);
      setMessage('Token generated successfully');
      fetchData();
    } catch (err) {
      setMessage('Error generating token: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleToggleTrading = async () => {
    try {
      await toggleTrading(!user.is_trading_active);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const calculateTotalPnL = () => {
    return trades.reduce((acc, trade) => acc + (trade.pnl || 0), 0);
  };

  if (!user) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>Loading...</div>;

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
        <h1 style={{ margin: 0 }}>Algo Trading Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span>{user.username} </span>
          <button onClick={() => setToken(null)} style={{ padding: '8px 16px' }}>Logout</button>
        </div>
      </header>

      <div className="grid-cols-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Configuration</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '5px' }}>API Key</label>
              <input type="text" value={apiKey} onChange={(e) => setApiKey(e.target.value)} style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '5px' }}>API Secret</label>
              <input type="password" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '5px' }}>Lots</label>
              <input type="number" value={numLots} onChange={(e) => setNumLots(parseInt(e.target.value))} style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>
            <button onClick={handleUpdateCredentials} style={{ width: '100%', marginTop: '10px' }}>Save Config</button>
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Daily Login (Kite Connect)</h3>
          <div style={{ marginBottom: '15px' }}>
            <p style={{ margin: '5px 0' }}>Access Token: {user.access_token ? <span style={{ color: 'green', fontWeight: 'bold' }}>Active</span> : <span style={{ color: 'red', fontWeight: 'bold' }}>Inactive</span>}</p>
            <p style={{ margin: '5px 0', fontSize: '0.9em', color: '#888' }}>Last Updated: {user.request_token_updated_at ? new Date(user.request_token_updated_at).toLocaleString() : 'Never'}</p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '5px' }}>Request Token</label>
              <input type="text" value={requestToken} onChange={(e) => setRequestToken(e.target.value)} placeholder="Paste request token here" style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>
            <button onClick={handleGenerateToken} style={{ width: '100%', marginTop: '10px' }}>Generate Access Token</button>
          </div>
        </div>
      </div>

      <div style={{ marginTop: '30px', textAlign: 'center' }}>
        <h2 style={{ marginBottom: '15px' }}>Status: <span style={{ color: user.is_trading_active ? '#44ff44' : '#ff4444' }}>{user.is_trading_active ? 'RUNNING' : 'STOPPED'}</span></h2>
        <button 
            onClick={handleToggleTrading}
            style={{ 
                padding: '12px 30px', 
                fontSize: '18px', 
                backgroundColor: user.is_trading_active ? '#ff4444' : '#44ff44',
                color: user.is_trading_active ? 'white' : '#1a1a1a',
                border: 'none',
                fontWeight: 'bold',
                width: '100%',
                maxWidth: '300px'
            }}
        >
            {user.is_trading_active ? 'STOP TRADING' : 'START TRADING'}
        </button>
      </div>

      {message && <div style={{ marginTop: '15px', color: '#646cff', textAlign: 'center', padding: '10px', backgroundColor: 'rgba(100, 108, 255, 0.1)', borderRadius: '5px' }}>{message}</div>}

      <div style={{ marginTop: '30px' }}>
        <h3>Stats</h3>
        <div className="stats-container" style={{ display: 'flex', gap: '20px' }}>
            <div className="card stats-card" style={{ flex: 1, textAlign: 'center' }}>
                <h4 style={{ margin: '0 0 10px 0', color: '#888' }}>Total PnL</h4>
                <p style={{ fontSize: '28px', margin: 0, fontWeight: 'bold', color: calculateTotalPnL() >= 0 ? '#44ff44' : '#ff4444' }}>
                    ₹{calculateTotalPnL().toFixed(2)}
                </p>
            </div>
            <div className="card stats-card" style={{ flex: 1, textAlign: 'center' }}>
                <h4 style={{ margin: '0 0 10px 0', color: '#888' }}>Total Trades</h4>
                <p style={{ fontSize: '28px', margin: 0, fontWeight: 'bold' }}>{trades.length}</p>
            </div>
        </div>
      </div>

      <div style={{ marginTop: '30px' }}>
        <h3>Trade History</h3>
        <div className="card table-container" style={{ padding: '0' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '600px' }}>
            <thead>
                <tr style={{ textAlign: 'left', backgroundColor: 'rgba(255,255,255,0.05)' }}>
                <th>Time</th>
                <th>Symbol</th>
                <th>Type</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>Qty</th>
                <th>PnL</th>
                <th>Status</th>
                <th>Reason</th>
                </tr>
            </thead>
            <tbody>
                {trades.length === 0 ? (
                    <tr><td colSpan="9" style={{ textAlign: 'center', padding: '20px' }}>No trades yet</td></tr>
                ) : (
                    trades.map((trade) => (
                    <tr key={trade.id}>
                        <td>{new Date(trade.entry_time).toLocaleString()}</td>
                        <td>{trade.symbol}</td>
                        <td>
                            <span style={{ 
                                padding: '2px 6px', 
                                borderRadius: '4px', 
                                backgroundColor: trade.symbol.includes('CE') ? 'rgba(68, 255, 68, 0.2)' : 'rgba(255, 68, 68, 0.2)',
                                color: trade.symbol.includes('CE') ? '#44ff44' : '#ff4444',
                                fontSize: '0.8em'
                            }}>
                                {trade.symbol.includes('CE') ? 'CE' : 'PE'}
                            </span>
                        </td>
                        <td>{trade.entry_price}</td>
                        <td>{trade.exit_price || '-'}</td>
                        <td>{trade.quantity}</td>
                        <td style={{ color: (trade.pnl || 0) >= 0 ? '#44ff44' : '#ff4444', fontWeight: 'bold' }}>{trade.pnl ? trade.pnl.toFixed(2) : '-'}</td>
                        <td>{trade.status}</td>
                        <td>{trade.reason}</td>
                    </tr>
                    ))
                )}
            </tbody>
            </table>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
