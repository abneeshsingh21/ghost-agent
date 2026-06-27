import React, { useState, useEffect } from 'react';
import { Radar, MonitorPlay, Wifi } from 'lucide-react';
import TargetMap from './TargetMap';

/**
 * LeftPane — Tactical Radar with live TargetMap replacing placeholder.
 */
const LeftPane = ({ socket }) => {
  const [activeTab, setActiveTab] = useState('radar');

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <Radar size={16} /> Tactical Radar
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid var(--panel-border)', padding: '8px', gap: '4px' }}>
        <button
          onClick={() => setActiveTab('radar')}
          style={{
            flex: 1, padding: '5px 8px',
            background: activeTab === 'radar' ? 'rgba(56,189,248,0.2)' : 'transparent',
            border: `1px solid ${activeTab === 'radar' ? 'rgba(56,189,248,0.4)' : 'transparent'}`,
            color: activeTab === 'radar' ? '#38bdf8' : 'var(--text-muted)',
            cursor: 'pointer', borderRadius: '6px', fontSize: '0.8rem',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px',
            transition: 'all 0.2s ease',
          }}
        >
          <Wifi size={13} /> Target Map
        </button>
        <button
          onClick={() => setActiveTab('mirror')}
          style={{
            flex: 1, padding: '5px 8px',
            background: activeTab === 'mirror' ? 'rgba(56,189,248,0.2)' : 'transparent',
            border: `1px solid ${activeTab === 'mirror' ? 'rgba(56,189,248,0.4)' : 'transparent'}`,
            color: activeTab === 'mirror' ? '#38bdf8' : 'var(--text-muted)',
            cursor: 'pointer', borderRadius: '6px', fontSize: '0.8rem',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px',
            transition: 'all 0.2s ease',
          }}
        >
          <MonitorPlay size={13} /> Mirroring
        </button>
      </div>

      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'radar' ? (
          /* Live TargetMap replaces the placeholder */
          <TargetMap socket={socket} />
        ) : (
          <div style={{
            flex: 1, background: '#000',
            border: '1px solid #1e293b', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: '10px',
          }}>
            <MonitorPlay size={32} style={{ color: 'var(--cyan-glow)', opacity: 0.3 }} />
            <div id="vnc-screen" style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              VNC / Scrcpy Stream Offline
            </div>
            <div style={{ fontSize: '0.72rem', color: '#334155' }}>
              Start a screen-share session from the command bridge
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LeftPane;
