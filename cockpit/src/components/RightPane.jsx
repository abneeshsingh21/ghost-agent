import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, MessageSquare, Send } from 'lucide-react';
import NeuralDashboard from './NeuralDashboard';
import CortexViewer from './CortexViewer';
import ChainProgress from './ChainProgress';

/**
 * RightPane — Full intelligence column.
 * Stacks: Neural Brain → Cortex Viewer → Chain Progress → Oracle → Chat
 */
const RightPane = ({ socket }) => {
  const [alerts, setAlerts] = useState([
    { id: 1, type: 'INFO', title: 'GHOST ONLINE', desc: 'Maximum capability. Learned restraint. Documented accountability.' }
  ]);
  const [chatHistory, setChatHistory] = useState([
    { role: 'agent', text: 'I am GHOST. Give me an objective, and I will execute it.', time: new Date().toLocaleTimeString() }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [strategicMode, setStrategicMode] = useState(true);
  const [isThinking, setIsThinking] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (!socket) return;

    socket.on('llm_thinking', (data) => {
      setIsThinking(data.status === true);
    });

    socket.on('chat_response', (data) => {
      setIsThinking(false);

      // Oracle alerts from high-risk responses
      if (data.response && (data.response.includes('[RISK] HIGH') || data.response.includes('[RISK] CRIT'))) {
        setAlerts(prev => [{
          id: Date.now(),
          type: data.response.includes('CRIT') ? 'CRITICAL' : 'HIGH',
          title: 'VULNERABILITY DETECTED',
          desc: data.response.substring(0, 120) + '...',
        }, ...prev].slice(0, 3));
      }

      // Chain suggestion alert
      if (data.chain_suggestion) {
        setAlerts(prev => [{
          id: Date.now() + 1,
          type: 'INFO',
          title: `🎯 Chain: ${data.chain_suggestion.chain_name}`,
          desc: data.chain_suggestion.reason,
        }, ...prev].slice(0, 3));
      }

      if (data.response) {
        let cleanText = data.response
          .replace(/```command[\s\S]*?```/g, '')
          .replace(/\[(?:FINDINGS|RISK|NEXT|CHAIN position)\][:\s]*.*?(\n|$)/g, '')
          .trim();

        const sentenceMatch = cleanText.match(/^.*?[.!?](?:\s|$)/);
        if (sentenceMatch) {
          cleanText = sentenceMatch[0].trim();
        } else if (cleanText.length > 150) {
          cleanText = cleanText.substring(0, 150) + '...';
        }

        if (cleanText.length === 0) cleanText = 'Executing directive...';
        if (cleanText.includes('Post-Execution Analysis') && cleanText.length < 40) return;

        setChatHistory(prev => [...prev, {
          role: 'agent', text: cleanText,
          time: new Date().toLocaleTimeString(),
        }]);
      }
    });

    socket.on('intelligence_update', (data) => {
      setAlerts(prev => [{
        id: Date.now(),
        type: 'INTEL',
        title: `📡 ${data.parser?.toUpperCase()} Intelligence`,
        desc: data.summary,
      }, ...prev].slice(0, 3));
    });

    socket.on('c2_session_callback', (data) => {
      setAlerts(prev => [{
        id: Date.now(),
        type: 'CRITICAL',
        title: '🎯 NEW SESSION',
        desc: `Meterpreter session ${data.session_id} — ${data.info?.tunnel_peer || 'callback received'}`,
      }, ...prev].slice(0, 3));
    });

    socket.on('strategy_started', () => {
      setIsThinking(true);
      setChatHistory(prev => [...prev, {
        role: 'system', text: '⚡ Strategic Brain engaged...',
        time: new Date().toLocaleTimeString(),
      }]);
    });

    return () => {
      socket.off('llm_thinking');
      socket.off('chat_response');
      socket.off('intelligence_update');
      socket.off('c2_session_callback');
      socket.off('strategy_started');
    };
  }, [socket]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    setChatHistory(prev => [...prev, {
      role: 'user', text: userMsg,
      time: new Date().toLocaleTimeString(),
    }]);
    setChatInput('');
    setIsThinking(true);

    try {
      await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          auto_execute: true,
          strategic: strategicMode,
        }),
      });
    } catch (err) {
      setIsThinking(false);
      setChatHistory(prev => [...prev, {
        role: 'agent', text: `[SYSTEM ERROR] ${err.message}`,
        time: new Date().toLocaleTimeString(),
      }]);
    }
  };

  const alertColor = (type) => {
    if (type === 'CRITICAL') return '#f43f5e';
    if (type === 'HIGH') return '#fbbf24';
    if (type === 'INTEL') return '#34d399';
    return '#38bdf8';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%', overflow: 'hidden' }}>

      {/* Neural Brain Dashboard */}
      <NeuralDashboard socket={socket} />

      {/* Cortex Swarm Viewer */}
      <CortexViewer socket={socket} />

      {/* Chain Progress */}
      <ChainProgress socket={socket} />

      {/* Oracle — Alerts Feed */}
      <div className="glass-panel" style={{ flex: '0 0 auto', maxHeight: '160px' }}>
        <div className="panel-header" style={{ color: 'var(--red-alert)' }}>
          <AlertTriangle size={16} /> The Oracle
        </div>
        <div className="panel-content" style={{ padding: '10px', overflowY: 'auto' }}>
          {alerts.map(alert => (
            <div key={alert.id} style={{
              borderLeft: `2px solid ${alertColor(alert.type)}`,
              paddingLeft: '8px', marginBottom: '8px',
            }}>
              <div style={{ color: alertColor(alert.type), fontWeight: 'bold', fontSize: '0.78rem' }}>
                {alert.title}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginTop: '2px' }}>
                {alert.desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cognitive Bridge — Chat */}
      <div className="glass-panel" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div className="panel-header" style={{ color: 'var(--cyan-glow)' }}>
          <MessageSquare size={16} /> Cognitive Bridge

          {/* Strategic mode toggle */}
          <label style={{
            marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px',
            cursor: 'pointer', fontSize: '0.72rem', fontWeight: 'normal',
            color: strategicMode ? '#38bdf8' : 'var(--text-muted)',
          }}>
            <div
              onClick={() => setStrategicMode(s => !s)}
              style={{
                width: '28px', height: '14px', borderRadius: '7px',
                background: strategicMode ? '#38bdf8' : '#334155',
                position: 'relative', cursor: 'pointer',
                transition: 'background 0.2s',
              }}
            >
              <div style={{
                position: 'absolute', top: '2px',
                left: strategicMode ? '16px' : '2px',
                width: '10px', height: '10px', borderRadius: '50%',
                background: '#fff', transition: 'left 0.2s',
              }} />
            </div>
            STRATEGIC
          </label>
        </div>

        {/* Chat messages */}
        <div className="panel-content" style={{
          flex: 1, overflowY: 'auto', padding: '12px',
          display: 'flex', flexDirection: 'column', gap: '10px',
        }}>
          {chatHistory.map((msg, i) => (
            <div key={i} style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '88%',
            }}>
              {msg.role === 'system' ? (
                <div style={{
                  fontSize: '0.72rem', color: '#38bdf8', textAlign: 'center',
                  alignSelf: 'center', opacity: 0.7, fontStyle: 'italic',
                }}>
                  {msg.text}
                </div>
              ) : (
                <div style={{
                  background: msg.role === 'user'
                    ? 'rgba(56,189,248,0.15)'
                    : 'rgba(0,0,0,0.45)',
                  border: `1px solid ${msg.role === 'user' ? 'rgba(56,189,248,0.4)' : 'var(--panel-border)'}`,
                  padding: '8px 12px', borderRadius: '8px',
                  fontSize: '0.85rem',
                  color: msg.role === 'user' ? '#fff' : 'var(--text-muted)',
                }}>
                  {msg.role === 'agent' && (
                    <div style={{ fontSize: '0.68rem', color: '#38bdf8', marginBottom: '3px', fontWeight: 'bold', letterSpacing: '0.5px' }}>
                      GHOST · {msg.time}
                    </div>
                  )}
                  {msg.text}
                </div>
              )}
            </div>
          ))}

          {/* Thinking indicator */}
          {isThinking && (
            <div style={{
              alignSelf: 'flex-start',
              background: 'rgba(0,0,0,0.4)', border: '1px solid var(--panel-border)',
              padding: '8px 14px', borderRadius: '8px',
              display: 'flex', alignItems: 'center', gap: '8px',
            }}>
              <div style={{ display: 'flex', gap: '4px' }}>
                {[0, 1, 2].map(i => (
                  <div key={i} style={{
                    width: '6px', height: '6px', borderRadius: '50%',
                    background: '#38bdf8',
                    animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                  }} />
                ))}
              </div>
              <span style={{ fontSize: '0.78rem', color: '#38bdf8' }}>
                {strategicMode ? 'Strategic Brain deliberating...' : 'Processing...'}
              </span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div style={{ padding: '10px', borderTop: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.3)' }}>
          <form onSubmit={handleChatSubmit} style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder={strategicMode ? 'Strategic directive (e.g. scan the network)...' : 'Direct command...'}
              disabled={isThinking}
              style={{
                flex: 1, padding: '9px 12px',
                background: 'rgba(0,0,0,0.5)',
                border: `1px solid ${isThinking ? '#1e293b' : 'var(--panel-border)'}`,
                color: 'white', borderRadius: '6px', outline: 'none',
                fontSize: '0.85rem',
                transition: 'border-color 0.2s',
              }}
            />
            <button
              type="submit"
              disabled={isThinking || !chatInput.trim()}
              style={{
                background: isThinking ? 'rgba(0,0,0,0.3)' : 'rgba(56,189,248,0.2)',
                border: `1px solid ${isThinking ? '#1e293b' : '#38bdf8'}`,
                color: isThinking ? '#334155' : '#38bdf8',
                padding: '0 14px', borderRadius: '6px',
                cursor: isThinking ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.2s',
              }}
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default RightPane;
