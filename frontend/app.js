/**
 * GHOST v6.0 — Command Center Application
 * 3-Pane: Telemetry | xterm.js Terminal | Chat Controller
 * Features: PTY bridge, Strategic Brain thinking blocks, ANSI stripping, Kill Switch
 */

// ═══════════════════════════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════════════════════════
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

/** Strip ANSI escape codes for clean text in thinking blocks */
function stripAnsi(str) {
  return str
    .replace(/\x1B\[[0-9;]*[a-zA-Z]/g, '')
    .replace(/\x1B\][^\x07]*\x07/g, '')
    .replace(/\x1B[()][AB012]/g, '')
    .replace(/\x1B\[[\?]?[0-9;]*[hl]/g, '')
    .replace(/\x1B/g, '');
}

/** Format file size */
function fmtSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

// ═══════════════════════════════════════════════════════════════
//  State
// ═══════════════════════════════════════════════════════════════
const state = {
  mode: 'TEACHING',
  socket: null,
  connected: false,
  chatHistory: [],
  streaming: false,
  streamBubble: null,
  strategyRunning: false,
};

// ═══════════════════════════════════════════════════════════════
//  xterm.js Terminal (Center Pane)
// ═══════════════════════════════════════════════════════════════
let term, fitAddon;

function initTerminal() {
  term = new Terminal({
    cursorBlink: true,
    cursorStyle: 'bar',
    fontSize: 13,
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    theme: {
      background: '#0d1117',
      foreground: '#e2e8f0',
      cursor: '#00ff88',
      cursorAccent: '#0d1117',
      selectionBackground: 'rgba(0,255,136,0.2)',
      black: '#0d1117',
      red: '#ff3366',
      green: '#00ff88',
      yellow: '#ffaa00',
      blue: '#3b82f6',
      magenta: '#a855f7',
      cyan: '#00e5ff',
      white: '#e2e8f0',
      brightBlack: '#1c2333',
      brightRed: '#ff6b8a',
      brightGreen: '#44ffaa',
      brightYellow: '#ffc944',
      brightBlue: '#6ba3ff',
      brightMagenta: '#c084fc',
      brightCyan: '#44eeff',
      brightWhite: '#ffffff',
    },
    allowProposedApi: true,
    scrollback: 5000,
  });

  fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open($('#terminal'));

  // Delay fit to ensure container is sized
  requestAnimationFrame(() => {
    fitAddon.fit();
  });

  // Welcome message
  term.writeln('\x1b[1;32m ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗\x1b[0m');
  term.writeln('\x1b[1;32m██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝\x1b[0m');
  term.writeln('\x1b[1;32m██║  ███╗███████║██║   ██║███████╗   ██║   \x1b[0m');
  term.writeln('\x1b[1;32m██║   ██║██╔══██║██║   ██║╚════██║   ██║   \x1b[0m');
  term.writeln('\x1b[1;32m╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   \x1b[0m');
  term.writeln('\x1b[1;32m ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   \x1b[0m');
  term.writeln('');
  term.writeln('\x1b[36m  GHOST v6.0 — Interactive Kali Shell\x1b[0m');
  term.writeln('\x1b[90m  Connecting to PTY...\x1b[0m');
  term.writeln('');

  // Send keystrokes to backend PTY
  term.onData(data => {
    if (state.socket && state.connected) {
      state.socket.emit('pty_input', { data });
    }
  });

  // Handle resize — use ResizeObserver for accurate container tracking
  const termContainer = $('#terminal');
  const resizeObserver = new ResizeObserver(() => {
    try {
      fitAddon.fit();
      if (state.socket && state.connected) {
        state.socket.emit('pty_resize', { cols: term.cols, rows: term.rows });
      }
    } catch (e) {}
  });
  resizeObserver.observe(termContainer);

  // Also handle window resize as fallback
  window.addEventListener('resize', () => {
    try {
      fitAddon.fit();
      if (state.socket && state.connected) {
        state.socket.emit('pty_resize', { cols: term.cols, rows: term.rows });
      }
    } catch (e) {}
  });
}

// ═══════════════════════════════════════════════════════════════
//  Chat Renderer (Right Pane)
// ═══════════════════════════════════════════════════════════════
const chatBox = () => $('#chatMessages');

function addChatMsg(type, text) {
  const el = document.createElement('div');
  el.className = `msg msg-${type}`;
  el.textContent = text;
  chatBox().appendChild(el);
  chatBox().scrollTop = chatBox().scrollHeight;
  return el;
}

function addChatHTML(type, html) {
  const el = document.createElement('div');
  el.className = `msg msg-${type}`;
  el.innerHTML = html;
  chatBox().appendChild(el);
  chatBox().scrollTop = chatBox().scrollHeight;
  return el;
}

function addSystemMsg(text) { addChatMsg('system', text); }
function addErrorMsg(text) { addChatMsg('error', text); }

function addStreamingBubble() {
  const el = document.createElement('div');
  el.className = 'msg msg-ghost';
  el.innerHTML = '<div class="streaming-indicator"><div class="dot-loader"><span></span><span></span><span></span></div> Thinking...</div>';
  chatBox().appendChild(el);
  chatBox().scrollTop = chatBox().scrollHeight;
  state.streamBubble = el;
  return el;
}

function appendToStream(token) {
  if (!state.streamBubble) return;
  // Remove the streaming indicator if still present
  const indicator = state.streamBubble.querySelector('.streaming-indicator');
  if (indicator) indicator.remove();
  state.streamBubble.textContent += token;
  chatBox().scrollTop = chatBox().scrollHeight;
}

function finalizeStream() {
  if (state.streamBubble) {
    // If the bubble still shows 'Thinking...' (no tokens were streamed),
    // remove it entirely — the real response will be added separately.
    const indicator = state.streamBubble.querySelector('.streaming-indicator');
    if (indicator) {
      state.streamBubble.remove();
    }
    // Otherwise the bubble has real streamed content — keep it.
  }
  state.streamBubble = null;
  state.streaming = false;
}

/** Create a collapsible Thinking Block */
function addThinkingBlock(phase, title, content) {
  const details = document.createElement('details');
  details.className = 'thinking-block';
  details.open = true;

  const phaseClass = phase === 'PLAN' ? 'plan' : phase === 'EXECUTE' ? 'exec' : phase === 'FIX' ? 'fix' : 'report';

  details.innerHTML = `
    <summary>
      🧠 ${title}
      <span class="think-phase ${phaseClass}">${phase}</span>
    </summary>
    <div class="thinking-body">${stripAnsi(content)}</div>
  `;
  chatBox().appendChild(details);
  chatBox().scrollTop = chatBox().scrollHeight;
  return details;
}

/** Show command in chat with approval buttons */
function addCommandProposal(command, verdict) {
  const wrapper = document.createElement('div');
  wrapper.className = 'msg msg-ghost';
  wrapper.style.padding = '8px 12px';

  let verdictHtml = '';
  if (verdict) {
    if (verdict.verdict === 'HALT') {
      verdictHtml = `<div style="color:var(--red);font-size:10px;margin-top:4px;">🛑 HALT: ${verdict.reason}</div>`;
    } else if (verdict.verdict === 'PROPOSE') {
      verdictHtml = `<div style="color:var(--amber);font-size:10px;margin-top:4px;">⚠️ Requires approval: ${verdict.reason}</div>`;
    } else {
      verdictHtml = `<div style="color:var(--neon);font-size:10px;margin-top:4px;">✅ Allowed</div>`;
    }
  }

  wrapper.innerHTML = `
    <div class="cmd-block">$ ${stripAnsi(command)}</div>
    ${verdictHtml}
  `;

  // Add approval buttons if PROPOSE
  if (!verdict || verdict.verdict === 'PROPOSE') {
    const bar = document.createElement('div');
    bar.className = 'approval-bar';
    bar.innerHTML = `
      <button class="approve-btn">✓ EXECUTE</button>
      <button class="deny-btn">✕ DENY</button>
      <button class="wrong-btn">⊘ WRONG</button>
    `;
    bar.querySelector('.approve-btn').onclick = () => { bar.remove(); approveCmd(command); };
    bar.querySelector('.deny-btn').onclick = () => { bar.remove(); addSystemMsg('Command denied.'); };
    bar.querySelector('.wrong-btn').onclick = () => { bar.remove(); markWrong(command); };
    wrapper.appendChild(bar);
  }

  chatBox().appendChild(wrapper);
  chatBox().scrollTop = chatBox().scrollHeight;
}

// ═══════════════════════════════════════════════════════════════
//  WebSocket Connection
// ═══════════════════════════════════════════════════════════════
function initSocket() {
  const socket = io();
  state.socket = socket;

  socket.on('connect', () => {
    state.connected = true;
    setDot('wsDot', 'on');
    addSystemMsg('WebSocket connected.');
    // Request PTY spawn
    socket.emit('pty_spawn');
  });

  socket.on('disconnect', () => {
    state.connected = false;
    setDot('wsDot', 'off');
    setDot('ptyDot', 'off');
    addErrorMsg('WebSocket disconnected.');
  });

  // ── PTY Events ──────────────────────────────────────────
  socket.on('pty_output', data => {
    if (term && data.data) {
      term.write(data.data);
    }
  });

  socket.on('pty_ready', () => {
    setDot('ptyDot', 'on');
    term.writeln('\x1b[32m  ✓ PTY connected.\x1b[0m\r\n');
    // Send actual terminal dimensions to backend immediately
    try { fitAddon.fit(); } catch(e) {}
    socket.emit('pty_resize', { cols: term.cols, rows: term.rows });
  });

  socket.on('pty_error', data => {
    setDot('ptyDot', 'off');
    term.writeln(`\x1b[31m  ✗ PTY Error: ${data.error}\x1b[0m\r\n`);
  });

  // ── LLM Streaming ──────────────────────────────────────
  socket.on('llm_thinking', data => {
    if (data.status) {
      state.streaming = true;
      addStreamingBubble();
      // Safety: auto-remove after 30s if nothing clears it
      setTimeout(() => {
        if (state.streamBubble) {
          const indicator = state.streamBubble.querySelector('.streaming-indicator');
          if (indicator) {
            state.streamBubble.remove();
            state.streamBubble = null;
            state.streaming = false;
          }
        }
      }, 30000);
    } else {
      finalizeStream();
    }
  });

  socket.on('llm_token', data => {
    if (!data.token) return;
    if (data.token.includes('<think>') || data.token.includes('</think>')) return;
    if (state.streaming) appendToStream(data.token);
  });

  // ── Strategic Brain Events ─────────────────────────────
  socket.on('thinking_block', data => {
    addThinkingBlock(data.phase, data.title, data.content);
  });

  socket.on('strategy_started', () => {
    state.strategyRunning = true;
    $('#haltStrategyBtn').classList.add('pulsing');
  });

  socket.on('strategy_complete', data => {
    state.strategyRunning = false;
    $('#haltStrategyBtn').classList.remove('pulsing');
    if (data.summary) {
      addThinkingBlock('REPORT', 'Strategy Complete', data.summary);
    }
  });

  socket.on('strategy_halted', () => {
    state.strategyRunning = false;
    $('#haltStrategyBtn').classList.remove('pulsing');
    addSystemMsg('⏹ Strategy halted by operator.');
  });

  // ── Chat Response ──────────────────────────────────────
  socket.on('chat_response', data => {
    finalizeStream();
    if (data.response) {
      addChatMsg('ghost', stripAnsi(data.response));
    }
    if (data.commands && data.commands.length > 0) {
      data.commands.forEach((cmd, i) => {
        const command = cmd.full_command || cmd.raw || '';
        const verdict = data.verdicts ? data.verdicts[i] : null;
        addCommandProposal(command, verdict);
      });
    }
  });

  // ── Command Output (streamed to terminal) ──────────────
  socket.on('command_output', data => {
    if (term && data.data) {
      term.write(data.data);
    }
  });

  socket.on('command_complete', data => {
    if (data.result) {
      const r = data.result;
      const status = r.status === 'OK' ? `\x1b[32m✓ Done\x1b[0m` : `\x1b[31m✗ ${r.status}\x1b[0m`;
      if (term) term.writeln(`\r\n${status} (${r.duration}s, exit ${r.exit_code})\r\n`);
    }
  });

  // ── Ethics Events ──────────────────────────────────────
  socket.on('ethics_halt', data => addChatMsg('error', `🛑 HALT: ${stripAnsi(data.formatted || data.verdict?.reason || '')}`));
  socket.on('ethics_propose', data => addCommandProposal(data.command, data.verdict));

  // ── Mode Events ────────────────────────────────────────
  socket.on('mode_change', data => { state.mode = data.mode; updateModeUI(); addSystemMsg(`Mode → ${data.mode}`); });
  socket.on('system_message', data => addSystemMsg(stripAnsi(data.message)));

  // ── Engine Events ──────────────────────────────────────
  socket.on('discovery_started', () => addSystemMsg('🔍 Zero-Knowledge Discovery activated...'));
  socket.on('acquisition_started', data => addSystemMsg(`🎯 Acquisition: ${data.vectors?.length || 0} vectors loaded`));
  socket.on('osint_started', data => addSystemMsg(`🔍 OSINT: [${data.seed_type}] '${data.seed}'`));
  socket.on('mobile_started', data => addSystemMsg(`📱 Mobile: targeting ${data.target}`));
  socket.on('wireless_started', data => addSystemMsg(`📡 Wireless: ${data.type} mode`));

  // ── Feedback ───────────────────────────────────────────
  socket.on('feedback_processed', data => {
    if (data.acknowledged) addChatMsg('ghost', data.message);
    refreshDashboard();
  });

  // ── Privacy Watchtower ─────────────────────────────────
  socket.on('privacy_update', data => {
    if (data.mic !== undefined) setPrivacy('mic', data.mic);
    if (data.cam !== undefined) setPrivacy('cam', data.cam);
    if (data.gps !== undefined) setPrivacy('gps', data.gps);
    if (data.screen !== undefined) setPrivacy('screen', data.screen);
  });
}

// ═══════════════════════════════════════════════════════════════
//  Chat Input Handler
// ═══════════════════════════════════════════════════════════════
async function sendChat() {
  const input = $('#chatInput');
  const msg = input.value.trim();
  if (!msg) return;

  addChatMsg('user', msg);
  input.value = '';
  input.style.height = 'auto';

  // Local slash commands
  if (msg === '/clear') { chatBox().innerHTML = ''; return; }
  if (msg === '/help') { addChatMsg('ghost', 'Commands: /clear, /mode <MODE>, /status, /kill all, /help\n\nOr just describe what you want in natural language.'); return; }
  if (msg.startsWith('/mode ')) {
    const m = msg.split(' ')[1]?.toUpperCase();
    if (m) setMode(m);
    return;
  }

  // Send to backend Strategic Brain
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        auto_execute: state.mode === 'AUTONOMOUS',
        strategic: true,
      }),
    });
    const data = await res.json();

    finalizeStream();

    // The response will come via WebSocket events (thinking_block, chat_response)
    // But also handle the HTTP response for non-streaming data
    if (data.llm_response && !state.streaming) {
      // Remove any leftover Thinking... bubble before adding the real response
      const staleIndicators = chatBox().querySelectorAll('.streaming-indicator');
      staleIndicators.forEach(el => el.closest('.msg')?.remove());
      addChatMsg('ghost', stripAnsi(data.llm_response));
    }

    if (data.proposed_commands && data.proposed_commands.length > 0) {
      data.proposed_commands.forEach((cmd, i) => {
        const command = cmd.full_command || cmd.raw || '';
        const verdict = data.ethics_verdicts?.[i] || null;
        addCommandProposal(command, verdict);
      });
    }

    refreshDashboard();
  } catch (err) {
    addErrorMsg(`Connection error: ${err.message}`);
  }
}

async function approveCmd(command) {
  addSystemMsg(`Executing: ${command}`);
  try {
    const res = await fetch('/api/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    });
    const data = await res.json();
    if (data.result?.llm_analysis?.response) {
      addChatMsg('ghost', stripAnsi(data.result.llm_analysis.response));
    }
  } catch (err) {
    addErrorMsg(`Execution failed: ${err.message}`);
  }
}

async function markWrong(command) {
  addSystemMsg(`Marking WRONG: ${command}`);
  try {
    await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'WRONG', context: { command, pattern: command } }),
    });
    refreshDashboard();
  } catch (err) {
    addErrorMsg(`Feedback failed: ${err.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════
//  Mode Control
// ═══════════════════════════════════════════════════════════════
function setMode(mode) {
  fetch('/api/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  }).then(r => r.json()).then(d => {
    state.mode = d.mode;
    updateModeUI();
    addSystemMsg(`Mode → ${d.mode}`);
  }).catch(e => addErrorMsg(`Mode change failed: ${e.message}`));
}

function updateModeUI() {
  $$('.mode-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === state.mode);
  });
  $('#vMode').textContent = state.mode;
}

// ═══════════════════════════════════════════════════════════════
//  Dashboard Refresh
// ═══════════════════════════════════════════════════════════════
async function refreshDashboard() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    state.mode = data.mode;
    updateModeUI();

    // Vitals
    const m = data.memory;
    $('#vRules').textContent = m.absolute_rules_count;
    $('#vEthics').textContent = m.learned_ethics_count;
    $('#vTargets').textContent = m.target_profiles_count;
    $('#vCmds').textContent = m.session.commands_executed;
    $('#vShells').textContent = m.session.shells_count;
    $('#vCreds').textContent = m.session.credentials_count;
    $('#vSession').textContent = m.session.id;

    // LLM
    if (data.bridge.ollama_available) {
      setDot('llmDot', 'on');
      $('#llmLabel').textContent = data.bridge.model;
      $('#footerModel').textContent = data.bridge.model;
    } else {
      setDot('llmDot', 'off');
    }

    // Env
    if (data.environment) $('#footerEnv').textContent = data.environment.type;

  } catch {}
}

async function refreshRadar() {
  try {
    const res = await fetch('/api/memory/targets');
    const data = await res.json();
    const targets = data.targets || {};
    const keys = Object.keys(targets);
    $('#radarCount').textContent = keys.length;

    const list = $('#radarList');
    if (keys.length === 0) {
      list.innerHTML = '<div class="empty-state">No targets. Run a scan.</div>';
      return;
    }

    list.innerHTML = '';
    keys.forEach(ip => {
      const t = targets[ip];
      const risk = (t.risk_level || 'low').toLowerCase();
      const el = document.createElement('div');
      el.className = 'radar-item';
      el.innerHTML = `
        <div>
          <div class="radar-ip">${ip}</div>
          <div class="radar-os">${t.device_class || t.os || 'unknown'}</div>
        </div>
        <span class="radar-risk ${risk}">${risk.toUpperCase()}</span>
      `;
      el.onclick = () => {
        $('#chatInput').value = `Analyze target ${ip}`;
        sendChat();
      };
      list.appendChild(el);
    });
  } catch {}
}

async function refreshLoot() {
  try {
    const res = await fetch('/api/loot');
    const data = await res.json();
    const files = data.files || [];
    $('#lootCount').textContent = files.length;

    const list = $('#lootList');
    if (files.length === 0) {
      list.innerHTML = '<div class="empty-state">No loot collected.</div>';
      return;
    }

    list.innerHTML = '';
    files.forEach(f => {
      const el = document.createElement('div');
      el.className = 'loot-item';
      el.innerHTML = `
        <span class="loot-name" title="${f.name}">📄 ${f.name}</span>
        <span class="loot-size">${fmtSize(f.size)}</span>
        <a class="loot-dl" href="/api/loot/${encodeURIComponent(f.name)}" download title="Download">⬇</a>
      `;
      list.appendChild(el);
    });
  } catch {}
}

// ═══════════════════════════════════════════════════════════════
//  Privacy Watchtower
// ═══════════════════════════════════════════════════════════════
function setPrivacy(type, active) {
  const cell = $(`#priv-${type}`);
  if (!cell) return;
  const dot = cell.querySelector('.priv-dot');
  dot.className = `priv-dot ${active ? 'on' : 'off'}`;
  cell.classList.toggle('active', active);
}

// ═══════════════════════════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════════════════════════
function setDot(id, status) {
  const el = $(`#${id}`);
  if (el) el.className = `ind-dot ${status}`;
}

// ═══════════════════════════════════════════════════════════════
//  Event Listeners
// ═══════════════════════════════════════════════════════════════

// Chat send
$('#chatSendBtn').addEventListener('click', sendChat);

// Enter to send (Shift+Enter for newline)
$('#chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
});

// Auto-resize textarea
$('#chatInput').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 100) + 'px';
});

// Mode buttons
$$('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => setMode(btn.dataset.mode));
});

// Halt Strategy button
$('#haltStrategyBtn').addEventListener('click', () => {
  if (state.socket && state.connected) {
    state.socket.emit('halt_strategy');
    addSystemMsg('⏹ Sending halt signal...');
  }
});

// ═══════════════════════════════════════════════════════════════
//  Initialization
// ═══════════════════════════════════════════════════════════════
async function init() {
  // Init terminal
  initTerminal();

  // Init WebSocket
  initSocket();

  // Welcome message in chat
  addSystemMsg('GHOST v6.0 Command Center online.');
  addChatMsg('ghost', 'Ready. Tell me what you need — I\'ll plan it, execute it, and fix it if it breaks.\n\nTry: "scan the network" or "find all devices"');

  // Load dashboard data
  await refreshDashboard();
  await refreshRadar();
  await refreshLoot();

  // Auto-refresh
  setInterval(refreshDashboard, 10000);
  setInterval(refreshRadar, 15000);
  setInterval(refreshLoot, 20000);

  // Heartbeat
  setInterval(() => {
    if (state.socket && state.connected) {
      state.socket.emit('heartbeat', { timestamp: Date.now() });
    }
  }, 30000);

  // Focus chat input
  $('#chatInput').focus();
}

init();
