import React, { useState, useEffect } from 'react';
import { Brain, Zap, TrendingUp, TrendingDown } from 'lucide-react';

/**
 * NeuralDashboard — Displays the Neural Brain's state:
 * Reflex history, dopamine weights, operation stats.
 * Listens to 'intelligence_update' and 'strategy_complete' events.
 */
const NeuralDashboard = ({ socket }) => {
  const [stats, setStats] = useState({ operations: 0, topology: 0, reflexes: 0 });
  const [recentOps, setRecentOps] = useState([]);
  const [reflexFired, setReflexFired] = useState(null);

  useEffect(() => {
    if (!socket) return;

    // Fetch initial neural stats
    fetch('http://localhost:5000/api/status')
      .then(r => r.json())
      .then(data => {
        if (data.memory?.neural) {
          setStats(data.memory.neural);
        }
      })
      .catch(() => {});

    socket.on('thinking_block', (data) => {
      if (data.phase === 'REFLEX') {
        setReflexFired({
          title: data.title,
          content: data.content,
          time: new Date().toLocaleTimeString(),
        });
        setTimeout(() => setReflexFired(null), 8000);
      }
    });

    socket.on('intelligence_update', (data) => {
      setRecentOps(prev => [{
        parser: data.parser,
        summary: data.summary,
        hosts: data.hosts_count,
        time: new Date().toLocaleTimeString(),
      }, ...prev].slice(0, 8));

      setStats(prev => ({
        ...prev,
        topology: prev.topology + (data.hosts_count || 0),
      }));
    });

    return () => {
      socket.off('thinking_block');
      socket.off('intelligence_update');
    };
  }, [socket]);

  return (
    <div className="glass-panel" style={{ flex: '0 0 auto', maxHeight: '260px' }}>
      <div className="panel-header" style={{ color: 'var(--gold-neural)' }}>
        <Brain size={16} /> Neural Brain
      </div>
      <div className="panel-content" style={{ padding: '10px', fontSize: '0.82rem' }}>

        {/* Stats Row */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
          {[
            { label: 'Operations', value: stats.operations || 0, color: 'var(--cyan-glow)' },
            { label: 'Topology', value: stats.topology || 0, color: '#34d399' },
            { label: 'Reflexes', value: stats.reflexes || 0, color: 'var(--gold-neural)' },
          ].map(s => (
            <div key={s.label} style={{
              flex: 1, textAlign: 'center', padding: '6px',
              background: 'rgba(0,0,0,0.3)', borderRadius: '6px',
              border: `1px solid ${s.color}22`,
            }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: s.color }}>{s.value}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Reflex Flash */}
        {reflexFired && (
          <div style={{
            background: 'rgba(251, 191, 36, 0.1)',
            border: '1px solid rgba(251, 191, 36, 0.3)',
            borderRadius: '6px', padding: '8px', marginBottom: '8px',
            animation: 'pulse 1s ease-in-out',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--gold-neural)', fontWeight: 'bold', fontSize: '0.78rem' }}>
              <Zap size={14} /> {reflexFired.title}
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginTop: '4px', whiteSpace: 'pre-line' }}>
              {reflexFired.content}
            </div>
          </div>
        )}

        {/* Recent Intelligence */}
        {recentOps.length > 0 && (
          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Recent Intelligence
            </div>
            {recentOps.map((op, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)',
              }}>
                <span style={{ color: '#34d399' }}>
                  <TrendingUp size={12} style={{ marginRight: '4px' }} />
                  {op.parser}: {op.summary}
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{op.time}</span>
              </div>
            ))}
          </div>
        )}

        {recentOps.length === 0 && !reflexFired && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '10px', fontSize: '0.78rem' }}>
            Neural Brain standing by. Execute commands to accumulate intelligence.
          </div>
        )}
      </div>
    </div>
  );
};

export default NeuralDashboard;
