import React, { useState, useEffect, useRef } from 'react';
import { Database, AlertTriangle, MessageSquare, Send } from 'lucide-react';

const RightPane = ({ socket }) => {
  const [alerts, setAlerts] = useState([
    { id: 1, type: 'CRITICAL', title: 'AWAITING DATA', desc: 'The Oracle is listening for intelligence...' }
  ]);
  const [chatHistory, setChatHistory] = useState([
    { role: 'agent', text: "I am Ghost. Give me an objective, and I will execute it." }
  ]);
  const [chatInput, setChatInput] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (!socket) return;

    socket.on('chat_response', (data) => {
       if (data.response && (data.response.includes('[RISK] HIGH') || data.response.includes('[RISK] CRIT'))) {
          setAlerts(prev => [
            { 
               id: Date.now(), 
               type: data.response.includes('CRIT') ? 'CRITICAL' : 'HIGH',
               title: 'VULNERABILITY DETECTED', 
               desc: data.response.substring(0, 100) + '...'
            },
            ...prev
          ].slice(0, 3));
       }

       if (data.response) {
         // Sanitize the output to remove raw command blocks and internal tags
         let cleanText = data.response
            .replace(/```command[\s\S]*?```/g, '') // Remove command blocks
            .replace(/\[(?:FINDINGS|RISK|NEXT|CHAIN position)\][:\s]*.*?(\n|$)/g, '') // Remove tags
            .trim();
         
         // Extract only the very first sentence to keep output extremely minimal
         const sentenceMatch = cleanText.match(/^.*?[.!?](?:\s|$)/);
         if (sentenceMatch) {
            cleanText = sentenceMatch[0].trim();
         } else if (cleanText.length > 100) {
            cleanText = cleanText.substring(0, 100) + '...';
         }

         if (cleanText.length === 0) cleanText = "Executing directive...";

         // Drop meaningless post-execution analysis
         if (cleanText.includes("Post-Execution Analysis") && (cleanText.includes("None") || cleanText.length < 40)) {
            return;
         }

         setChatHistory(prev => [...prev, { role: 'agent', text: cleanText }]);
       }
    });

    return () => {
       socket.off('chat_response');
    };
  }, [socket]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    setChatHistory(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatInput('');

    try {
      await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, auto_execute: true })
      });
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'agent', text: `[SYSTEM ERROR] ${err.message}` }]);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
      
      {/* Top Section: The Oracle (Condensed) */}
      <div className="glass-panel" style={{ flex: '0 0 auto', maxHeight: '180px', overflowY: 'auto' }}>
        <div className="panel-header" style={{ color: 'var(--red-alert)' }}>
          <AlertTriangle size={16} /> The Oracle
        </div>
        <div className="panel-content" style={{ fontSize: '0.8rem', padding: '10px' }}>
          {alerts.map(alert => (
            <div key={alert.id} style={{ 
              borderLeft: `2px solid ${alert.type === 'CRITICAL' ? 'var(--red-alert)' : 'var(--gold-neural)'}`, 
              paddingLeft: '8px', 
              marginBottom: '10px' 
            }}>
              <div style={{ color: alert.type === 'CRITICAL' ? 'var(--red-alert)' : 'var(--gold-neural)', fontWeight: 'bold' }}>
                {alert.title}
              </div>
              <div style={{ color: 'var(--text-muted)' }}>{alert.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Section: Agentic Chatbot */}
      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="panel-header" style={{ color: 'var(--cyan-glow)' }}>
          <MessageSquare size={16} /> Cognitive Bridge (Chat)
        </div>
        
        {/* Chat Messages Area */}
        <div className="panel-content" style={{ flex: 1, overflowY: 'auto', padding: '15px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
          {chatHistory.map((msg, i) => (
            <div key={i} style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              background: msg.role === 'user' ? 'rgba(56, 189, 248, 0.15)' : 'rgba(0,0,0,0.4)',
              border: `1px solid ${msg.role === 'user' ? 'rgba(56, 189, 248, 0.4)' : 'var(--panel-border)'}`,
              padding: '10px 14px',
              borderRadius: '8px',
              maxWidth: '85%',
              fontSize: '0.9rem',
              color: msg.role === 'user' ? '#fff' : 'var(--text-muted)'
            }}>
              {msg.role === 'agent' && <div style={{ fontSize: '0.75rem', color: '#38bdf8', marginBottom: '4px', fontWeight: 'bold' }}>GHOST</div>}
              {msg.text}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Chat Input Field */}
        <div style={{ padding: '12px', borderTop: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.3)' }}>
          <form onSubmit={handleChatSubmit} style={{ display: 'flex', gap: '10px' }}>
            <input 
              type="text" 
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Direct the agent (e.g. 'Scan my network')" 
              style={{ 
                flex: 1, 
                padding: '10px', 
                background: 'rgba(0,0,0,0.5)', 
                border: '1px solid var(--panel-border)', 
                color: 'white', 
                borderRadius: '4px',
                outline: 'none'
              }}
            />
            <button type="submit" style={{
              background: 'rgba(56, 189, 248, 0.2)',
              border: '1px solid var(--cyan-glow)',
              color: 'var(--cyan-glow)',
              padding: '0 15px',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>

    </div>
  );
};

export default RightPane;
