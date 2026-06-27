import React, { useState, useEffect } from 'react';
import { GitBranch, Shield, Sword, Scale, CheckCircle, XCircle } from 'lucide-react';

/**
 * CortexViewer — Shows the Red/Blue/Judge swarm debate live.
 * Listens to 'thinking_block' events with phase === 'SWARM'.
 */
const CortexViewer = ({ socket }) => {
  const [decisions, setDecisions] = useState([]);
  const [active, setActive] = useState(null); // current in-progress deliberation

  useEffect(() => {
    if (!socket) return;

    socket.on('thinking_block', (data) => {
      if (data.phase !== 'SWARM' && data.phase !== 'CORTEX') return;

      const entry = {
        phase: data.phase,
        title: data.title,
        content: data.content,
        time: new Date().toLocaleTimeString(),
        id: Date.now(),
      };

      // Detect JUDGE (final decision) → move to history
      if (data.title?.includes('Judge') || data.title?.includes('⚖️')) {
        setDecisions(prev => [entry, ...prev].slice(0, 5));
        setActive(null);
      } else {
        setActive(entry);
      }
    });

    socket.on('chat_response', (data) => {
      if (data.cortex_decision) {
        const d = data.cortex_decision;
        setDecisions(prev => [{
          phase: 'JUDGE',
          title: `⚖️ ${d.chosen_agent} wins — Score ${d.composite_score}`,
          content: `Command: ${d.final_command}\n${d.rationale}`,
          time: new Date().toLocaleTimeString(),
          id: Date.now(),
          chosen: d.chosen_agent,
        }, ...prev].slice(0, 5));
        setActive(null);
      }
    });

    return () => {
      socket.off('thinking_block');
      socket.off('chat_response');
    };
  }, [socket]);

  const agentColor = (title = '') => {
    if (title.includes('Red') || title.includes('🔴')) return '#f43f5e';
    if (title.includes('Blue') || title.includes('🔵')) return '#38bdf8';
    if (title.includes('Judge') || title.includes('⚖️')) return '#fbbf24';
    return 'var(--text-muted)';
  };

  const agentIcon = (title = '') => {
    if (title.includes('Red') || title.includes('🔴')) return <Sword size={13} />;
    if (title.includes('Blue') || title.includes('🔵')) return <Shield size={13} />;
    if (title.includes('Judge') || title.includes('⚖️')) return <Scale size={13} />;
    return <GitBranch size={13} />;
  };

  return (
    <div className="glass-panel" style={{ flex: '0 0 auto', maxHeight: '220px' }}>
      <div className="panel-header" style={{ color: '#a78bfa' }}>
        <GitBranch size={16} /> Frontal Cortex — Swarm Debate
      </div>
      <div className="panel-content" style={{ padding: '10px', fontSize: '0.8rem', overflowY: 'auto' }}>

        {/* Active deliberation */}
        {active && (
          <div style={{
            background: `${agentColor(active.title)}11`,
            border: `1px solid ${agentColor(active.title)}44`,
            borderRadius: '6px', padding: '8px', marginBottom: '8px',
            display: 'flex', flexDirection: 'column', gap: '4px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: agentColor(active.title), fontWeight: 'bold' }}>
              {agentIcon(active.title)}
              {active.title}
              <span style={{
                marginLeft: 'auto', fontSize: '0.65rem',
                background: `${agentColor(active.title)}22`, padding: '1px 6px', borderRadius: '20px',
              }}>LIVE</span>
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', whiteSpace: 'pre-line', maxHeight: '60px', overflowY: 'auto' }}>
              {active.content}
            </div>
          </div>
        )}

        {/* Historical decisions */}
        {decisions.map(d => (
          <div key={d.id} style={{
            display: 'flex', alignItems: 'flex-start', gap: '8px',
            padding: '5px 0', borderBottom: '1px solid rgba(255,255,255,0.05)',
          }}>
            <span style={{ color: agentColor(d.title), marginTop: '2px' }}>{agentIcon(d.title)}</span>
            <div style={{ flex: 1 }}>
              <div style={{ color: agentColor(d.title), fontWeight: '600', fontSize: '0.77rem' }}>{d.title}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginTop: '2px', 
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '280px' }}>
                {d.content}
              </div>
            </div>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', whiteSpace: 'nowrap' }}>{d.time}</span>
          </div>
        ))}

        {decisions.length === 0 && !active && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '0.78rem' }}>
            Swarm standing by. Run strategic mode to activate Red/Blue/Judge debate.
          </div>
        )}
      </div>
    </div>
  );
};

export default CortexViewer;
