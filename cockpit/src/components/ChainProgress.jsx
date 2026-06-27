import React, { useState, useEffect } from 'react';
import { Link, CheckCircle, Clock, Play, XCircle, ChevronRight } from 'lucide-react';

/**
 * ChainProgress — Shows the currently active operation chain's
 * phase-by-phase progress in real time.
 * Listens to chain_started, chain_auto_selected, and strategy_complete events.
 */
const ChainProgress = ({ socket }) => {
  const [activeChain, setActiveChain] = useState(null);
  const [suggestion, setSuggestion] = useState(null);
  const [chains, setChains] = useState({});

  useEffect(() => {
    // Load available chains
    fetch('http://localhost:5000/api/chains')
      .then(r => r.json())
      .then(data => setChains(data))
      .catch(() => {});

    // Load active chain from status
    fetch('http://localhost:5000/api/chain/status')
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ACTIVE') setActiveChain(data);
      })
      .catch(() => {});

    if (!socket) return;

    socket.on('chain_started', (data) => {
      setActiveChain(data);
      setSuggestion(null);
    });

    socket.on('chain_advanced', (data) => {
      setActiveChain(prev => prev ? { ...prev, current_phase: data.phase } : data);
    });

    socket.on('chain_auto_selected', (data) => {
      setSuggestion(data);
    });

    socket.on('strategy_complete', () => {
      // If no explicit chain, clear
    });

    return () => {
      socket.off('chain_started');
      socket.off('chain_advanced');
      socket.off('chain_auto_selected');
      socket.off('strategy_complete');
    };
  }, [socket]);

  const startSuggestedChain = async () => {
    if (!suggestion) return;
    try {
      await fetch('http://localhost:5000/api/chain/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chain: suggestion.chain, variables: {} }),
      });
    } catch (e) {}
  };

  const phaseStatus = (phaseId, currentPhase) => {
    if (phaseId < currentPhase) return 'done';
    if (phaseId === currentPhase) return 'active';
    return 'pending';
  };

  const phaseColor = (status) => {
    if (status === 'done') return '#34d399';
    if (status === 'active') return '#38bdf8';
    return '#334155';
  };

  return (
    <div className="glass-panel" style={{ flex: '0 0 auto', maxHeight: '240px' }}>
      <div className="panel-header" style={{ color: '#38bdf8' }}>
        <Link size={16} /> Chain Progress
        {activeChain && (
          <span style={{
            marginLeft: 'auto', fontSize: '0.68rem', fontWeight: 'normal',
            background: 'rgba(56,189,248,0.15)', padding: '2px 8px',
            borderRadius: '20px', border: '1px solid rgba(56,189,248,0.3)',
          }}>
            {activeChain.template || activeChain.name}
          </span>
        )}
      </div>
      <div className="panel-content" style={{ padding: '10px', overflowY: 'auto' }}>

        {/* Chain auto-selection suggestion */}
        {suggestion && !activeChain && (
          <div style={{
            background: 'rgba(56,189,248,0.08)',
            border: '1px solid rgba(56,189,248,0.25)',
            borderRadius: '8px', padding: '10px', marginBottom: '10px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ color: '#38bdf8', fontWeight: '600', fontSize: '0.82rem' }}>
                  🎯 Suggested Chain
                </div>
                <div style={{ color: '#f8fafc', fontSize: '0.88rem', margin: '2px 0' }}>
                  {suggestion.display_name}
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                  {suggestion.reason} · {Math.round(suggestion.confidence * 100)}% confidence
                </div>
              </div>
              <button
                onClick={startSuggestedChain}
                style={{
                  background: 'rgba(56,189,248,0.2)', border: '1px solid #38bdf8',
                  color: '#38bdf8', padding: '6px 12px', borderRadius: '6px',
                  cursor: 'pointer', fontSize: '0.8rem', display: 'flex',
                  alignItems: 'center', gap: '4px', flexShrink: 0,
                }}
              >
                <Play size={12} /> Start
              </button>
            </div>
          </div>
        )}

        {/* Active chain progress */}
        {activeChain && activeChain.total_phases ? (
          <div>
            {/* Progress bar */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px',
              }}>
                <span>Phase {activeChain.current_phase} / {activeChain.total_phases}</span>
                <span>{Math.round((activeChain.current_phase / activeChain.total_phases) * 100)}%</span>
              </div>
              <div style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '4px', height: '4px', overflow: 'hidden' }}>
                <div style={{
                  width: `${(activeChain.current_phase / activeChain.total_phases) * 100}%`,
                  height: '100%', background: '#38bdf8',
                  transition: 'width 0.5s ease',
                  boxShadow: '0 0 8px #38bdf8',
                }} />
              </div>
            </div>

            {/* Phase steps */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {Array.from({ length: activeChain.total_phases }, (_, i) => i + 1).map(phaseId => {
                const status = phaseStatus(phaseId, activeChain.current_phase);
                const color = phaseColor(status);
                return (
                  <div key={phaseId} style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    opacity: status === 'pending' ? 0.4 : 1,
                  }}>
                    <div style={{
                      width: '20px', height: '20px', borderRadius: '50%',
                      background: color + (status === 'active' ? '' : '22'),
                      border: `1px solid ${color}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      {status === 'done' && <CheckCircle size={12} color={color} />}
                      {status === 'active' && <Play size={10} color={color} />}
                      {status === 'pending' && <Clock size={10} color={color} />}
                    </div>
                    <span style={{
                      fontSize: '0.78rem',
                      color: status === 'active' ? '#f8fafc' : 'var(--text-muted)',
                      fontWeight: status === 'active' ? '600' : 'normal',
                    }}>
                      Phase {phaseId}
                      {status === 'active' && (
                        <span style={{
                          marginLeft: '6px', fontSize: '0.65rem',
                          color: '#38bdf8', animation: 'pulse 1.5s infinite',
                        }}>
                          ● EXECUTING
                        </span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          !suggestion && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '0.78rem' }}>
              <ChevronRight size={24} style={{ opacity: 0.2, marginBottom: '6px' }} />
              <div>No chain active. Use strategic mode to auto-select a chain.</div>
            </div>
          )
        )}
      </div>
    </div>
  );
};

export default ChainProgress;
