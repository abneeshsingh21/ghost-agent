import React, { useEffect, useRef, useState } from 'react';
import { Terminal, Cpu } from 'lucide-react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

const CenterPane = ({ socket }) => {
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const [inputValue, setInputValue] = useState('');

  useEffect(() => {
    if (!terminalRef.current || xtermRef.current) return;

    const term = new XTerm({
      theme: {
        background: 'rgba(0,0,0,0)',
        foreground: '#f8fafc',
        cursor: '#38bdf8',
        selectionBackground: 'rgba(56, 189, 248, 0.3)',
      },
      fontFamily: 'Consolas, "Courier New", monospace',
      fontSize: 14,
      cursorBlink: true,
      scrollback: 10000,
      disableStdin: true, // We use the input box below for now
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    
    term.open(terminalRef.current);
    fitAddon.fit();
    xtermRef.current = term;

    term.writeln('\x1b[1;36mGHOST v6.0 \x1b[0m— Kali Linux Terminal Initialized');
    term.writeln('Awaiting autonomous commands or manual override...');
    term.write('\r\nroot@ghost:~# ');

    const resizeObserver = new ResizeObserver(() => {
      try { fitAddon.fit(); } catch (e) {}
    });
    resizeObserver.observe(terminalRef.current);

    return () => {
      resizeObserver.disconnect();
      term.dispose();
    };
  }, []);

  useEffect(() => {
    if (!socket || !xtermRef.current) return;

    const handleOutput = (data) => {
      if (data.data) {
        xtermRef.current.write(data.data);
      }
    };

    socket.on('command_output', handleOutput);

    return () => {
      socket.off('command_output', handleOutput);
    };
  }, [socket]);

  const handleInputSubmit = async (e) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      const rawCmd = inputValue.trim();
      setInputValue('');
      xtermRef.current.writeln(`\r\n> ${rawCmd}`);
      
      try {
        await fetch('http://localhost:5000/api/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: rawCmd, force: true })
        });
      } catch (err) {
        xtermRef.current.writeln(`\r\n\x1b[1;31m[ERROR]\x1b[0m Failed to connect to backend: ${err.message}`);
        xtermRef.current.write('\r\nroot@ghost:~# ');
      }
    }
  };

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Terminal size={16} /> Raw Execution Terminal
        </div>
        <div style={{ color: 'var(--red-alert)', display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem' }}>
          <Cpu size={14}/> SYSTEM ACTIVE
        </div>
      </div>
      
      <div className="panel-content" style={{ padding: 0, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div ref={terminalRef} style={{ flex: 1, padding: '10px', minHeight: '0', overflow: 'hidden' }}></div>
        
        {/* Input Field for Manual Commands */}
        <div style={{ padding: '12px', borderTop: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.3)' }}>
          <input 
            type="text" 
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleInputSubmit}
            placeholder="Manual override: Enter raw shell command..." 
            style={{ 
              width: '100%', 
              padding: '10px', 
              background: 'rgba(0,0,0,0.5)', 
              border: '1px solid var(--panel-border)', 
              color: 'white', 
              borderRadius: '4px',
              outline: 'none',
              fontFamily: 'monospace'
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default CenterPane;
