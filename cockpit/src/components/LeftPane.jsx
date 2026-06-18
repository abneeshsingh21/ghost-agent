import React, { useState } from 'react';
import { Radar, MonitorPlay, Wifi } from 'lucide-react';

const LeftPane = () => {
  const [activeTab, setActiveTab] = useState('radar'); // 'radar' or 'mirror'

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <Radar size={16} /> Tactical Radar
      </div>
      
      <div style={{ display: 'flex', borderBottom: '1px solid var(--panel-border)', padding: '8px' }}>
        <button 
          onClick={() => setActiveTab('radar')}
          style={{ flex: 1, padding: '5px', background: activeTab === 'radar' ? 'rgba(56, 189, 248, 0.2)' : 'transparent', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', borderRadius: '4px' }}
        >
          <Wifi size={14} style={{ marginRight: '5px' }}/> Topology
        </button>
        <button 
          onClick={() => setActiveTab('mirror')}
          style={{ flex: 1, padding: '5px', background: activeTab === 'mirror' ? 'rgba(56, 189, 248, 0.2)' : 'transparent', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', borderRadius: '4px' }}
        >
          <MonitorPlay size={14} style={{ marginRight: '5px' }}/> Mirroring
        </button>
      </div>

      <div className="panel-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {activeTab === 'radar' ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            <p>Force-Directed Graph will render here.</p>
            <p style={{ fontSize: '0.8rem', marginTop: '10px' }}>Waiting for network data...</p>
          </div>
        ) : (
          <div style={{ width: '100%', height: '100%', background: '#000', border: '1px solid #333', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div id="vnc-screen" style={{ color: 'var(--cyan-glow)' }}>
              [ VNC / Scrcpy Stream Offline ]
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LeftPane;
