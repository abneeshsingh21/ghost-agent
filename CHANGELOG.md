# Changelog

All notable changes to GHOST are documented in this file.

---

## [6.0.0] — 2026-06-18

### Added
- React/Vite **Cockpit** dashboard (3-pane Command Center with xterm.js live terminal)
- Privacy Watchtower widget (MIC / CAM / GPS / SCREEN sensors)
- Network Radar & Loot Box live telemetry panels
- System Vitals real-time stats panel

### Changed
- Frontend upgraded to v6.0 branding
- WebSocket protocol stabilized for high-frequency PTY streaming

---

## [5.0.0] — 2026-04-21 — *"Digital Sovereign"*

### Added
- **Universal Pivot Engine:**
  - `build_escapology_plan()` — Kernel UAF/Type Confusion pivot mapping
  - `build_imds_siphon_plan()` — IMDSv2 AWS/Azure/GCP credential exfiltration
  - `WEB_LOGIC_PIVOT` chain — SSRF discovery → internal SQLi execution
- **Ultimate Offensive Arsenal (`arsenal.py`):**
  - `ArsenalEngine.synthesize_zeroday()` — LLM-driven AFL fuzzing pipeline
  - `/arsenal` slash command wired to server routing
- **Tactical Resiliency (`resiliency.py`):**
  - `MemoryLoader` — `memfd_create` reflective payload injection (zero disk I/O)
  - `PeerToPeerMesh` — Decentralized swarm C2 with peer hop routing
  - `apply_metamorphic_shift()` — Entropy-keyed payload mutation
  - `build_ultrasonic_tunnel_plan()` — 19kHz numpy/scipy air-gap bridge
- **Autonomous Looting (`osint.py`):**
  - `SemanticLootClassifier` — Dual-score file prioritizer (extension + name matching)
- **Strategic Governance (`governance.py`):**
  - `select_optimal_mvd_path()` — Weighted forensic visibility scoring
  - `enforce_shadow_protocol()` — Volatile-only execution mandate
- **Ethics (`ethics.py`):**
  - `rlhf_gut_instinct()` — Intercepts brute-force tactics, proposes surgical alternatives
- **Anti-Forensic Timestomping (`chains.py`):**
  - `SanitizationEngine.timestomp_purge()` — MACE timestamp restoration on log wipe

### Fixed
- `SemanticLootClassifier` missing from `osint.py` after silent edit failure
- `PeerToPeerMesh` mutable default argument `known_peers=[]` → `None` pattern
- All version strings updated from v3.0 → v5.0
- `/help` text missing v5.0 advanced slash commands
- Unclosed bracket in `build_memory_telemetry_plan()` causing `SyntaxError`

---

## [4.0.0] — 2026-04 — *"Kernel Tier"*

### Added
- `DiagnosticEngine` with 4 diagnostic plan builders:
  - Memory Corruption (UAF), Zero-Click (mDNS), Persistence Audit, Memory Telemetry
- `/api/diagnose` REST endpoint
- `/diagnose` slash command
- `GovernanceLayer` with `evaluate_mvd()` tiered authorization
- `ResiliencyEngine` with:
  - SDR air-gap detection (HackRF auto-detect via `hackrf_info`)
  - Self-healing DNS/ICMP C2 tunneling (`dnscat2`, `icmptunnel`)
  - Quantum-stealth traffic shaping via `tc qdisc/netem`
- Groq Cloud LLM integration (`llama-3.3-70b-versatile`) replacing Ollama-only

---

## [3.0.0] — 2026-04 — *"Full Arsenal"*

### Added
- Flask/SocketIO server with 3-pane web dashboard
- `ChainEngine` with multi-phase Operation Graph execution
- `OSINTEngine` — username, email, domain, IP profiling
- `MobileEngine` — Android/ADB exploitation workflow
- `WirelessEngine` — aircrack-ng WiFi attack automation
- `DiscoveryEngine` — nmap/netdiscover wrapper
- `TargetAcquisitionEngine` — autonomous target selection
- `EthicsEngine` — 4-layer arbitration with WRONG/CONDITIONAL/OVERRIDE feedback
- `MemoryManager` — JSON-backed 4-layer persistent memory
- Dead Man's Switch watchdog for automatic sanitization on telemetry loss
- `--shadow` flag for STEALTH mode autonomous operation
