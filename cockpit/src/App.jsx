import React, { useState, useEffect } from 'react'
import { io } from 'socket.io-client'
import LeftPane from './components/LeftPane'
import CenterPane from './components/CenterPane'
import RightPane from './components/RightPane'
import { AlertCircle } from 'lucide-react'

// Initialize Socket.IO connection to the Python backend
const socket = io('http://localhost:5000');

function App() {
  const [toast, setToast] = useState(null);

  useEffect(() => {
    // Listen for system messages and achievements from backend
    socket.on('system_message', (data) => {
      setToast({
        title: "⚡ System Message",
        message: data.message
      });
      setTimeout(() => setToast(null), 5000);
    });

    socket.on('ethics_halt', (data) => {
      setToast({
        title: "⚠️ Ethics Override",
        message: data.formatted || "Command execution halted."
      });
      setTimeout(() => setToast(null), 5000);
    });

    return () => {
      socket.off('system_message');
      socket.off('ethics_halt');
    }
  }, []);

  return (
    <>
      <div className="cockpit-layout">
        <LeftPane socket={socket} />
        <CenterPane socket={socket} />
        <RightPane socket={socket} />
      </div>

      {/* Heads-up Overlay (Toast) */}
      {toast && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          background: 'rgba(16, 22, 35, 0.9)',
          border: '1px solid var(--gold-neural)',
          padding: '16px',
          borderRadius: '8px',
          boxShadow: '0 0 20px rgba(251, 191, 36, 0.2)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          zIndex: 1000,
          color: 'var(--gold-neural)',
          animation: 'slideIn 0.3s ease-out'
        }}>
          <AlertCircle size={24} />
          <div>
            <div style={{ fontWeight: 'bold', fontSize: '0.95rem' }}>{toast.title}</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{toast.message}</div>
          </div>
        </div>
      )}
    </>
  )
}

export default App
