# GHOST v6.0 — Grey Hat Operational Security Tool

<div align="center">

```
 ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
██║  ███╗███████║██║   ██║███████╗   ██║   
██║   ██║██╔══██║██║   ██║╚════██║   ██║   
╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   
```

**"Maximum capability. Learned restraint. Documented accountability."**

![Version](https://img.shields.io/badge/version-6.0.0-cyan?style=for-the-badge)
![License](https://img.shields.io/badge/license-Proprietary-red?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python)
![LLM](https://img.shields.io/badge/LLM-Groq%20%7C%20llama--3.3--70b-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-Kali%20Linux%20%7C%20WSL-purple?style=for-the-badge)
![Status](https://img.shields.io/badge/status-Active%20Research-yellow?style=for-the-badge)

</div>

---

> ⚠️ **FOR AUTHORIZED SECURITY RESEARCH ONLY**  
> This tool is designed exclusively for use in isolated lab environments with explicit written authorization. Unauthorized deployment against systems you do not own is illegal and unethical.

---

## 🧠 What is GHOST?

GHOST is an **autonomous, LLM-driven security research agent** built for elite-tier offensive security operations, vulnerability research, and red team simulations. Unlike traditional security tools that execute single commands, GHOST constructs entire **multi-phase Operation Graphs**, reasons about tactical tradeoffs using a **Cognitive Governance Layer**, and adapts in real-time using an integrated **Ethics & Autonomy Engine**.

It operates at the intersection of AI reasoning and deep system exploitation — giving the operator a co-pilot that thinks, plans, adapts, and maintains forensic invisibility throughout every operation.

---

## ✨ Core Feature Matrix

### 🌐 Universal Pivot Engine
| Feature | Description |
|---------|-------------|
| **Kernel Escapology** | Maps User Shell → UID 0/SYSTEM via simulated UAF/Type Confusion primitives |
| **Cloud IMDS Siphoning** | Automated IMDSv2 token acquisition + IAM credential exfiltration (AWS/Azure/GCP) |
| **Web-Logic Exploitation** | SSRF discovery → Internal network mapping → Tampered SQLi chain execution |

### 💣 Ultimate Offensive Arsenal
| Feature | Description |
|---------|-------------|
| **Zero-Day Synthesis** | LLM-driven AFL fuzzing pipeline with `objdump` disassembly + generative fuzz dictionaries |
| **Memory-Only Loader** | Reflective `memfd_create` / ReflectiveLoader injection — zero disk I/O, bypasses AV |
| **P2P Mesh C2** | Decentralized swarm command hopping — survives primary C2 takedown |
| **Metamorphic Shifting** | Entropy-keyed payload mutation on every deployment cycle |
| **Ultrasonic Tunneling** | Native Python `numpy/scipy` air-gap bridge via 19kHz sine carriers |

### 🔬 Advanced Diagnostics
| Feature | Description |
|---------|-------------|
| **Memory Corruption Testing** | UAF/Type Confusion simulation against Kernel Control Flow Guard |
| **Zero-Click Vectors** | Scapy-based malformed mDNS/BlastDoor packet generation |
| **Persistence Audit** | EDR detection baiting via dormant crontab injection |
| **Runtime Telemetry** | Frida-based keychain API hooking for in-RAM encryption verification |

### 🧬 Strategic Governance
| Feature | Description |
|---------|-------------|
| **MVD Path-Finding** | Weighted algorithm: `(stability × 0.4) − (visibility × 0.6)` for minimal footprint |
| **Shadow Protocol** | Volatile-only execution mandate — blocks all static disk writes |
| **Anti-Forensic Timestomping** | Captures kernel MACE timestamps before purge, restores after |
| **RLHF Gut Instinct** | Intercepts noisy brute-force tactics, proposes surgical alternatives |
| **4-Layer Ethics Engine** | Absolute rules → learned ethics → target profiles → autonomy matrix |

### 🔍 OSINT & Looting
| Feature | Description |
|---------|-------------|
| **Semantic Loot Classifier** | Dual-score file prioritizer: extension (+50) + filename (+50) = CRITICAL at 100+ |
| **Smart OSINT Engine** | Username/email/domain/IP profiling via Sherlock, theHarvester, holehe |
| **Credential Smart-Pivot** | Auto-injects discovered credentials into subsequent attack phases |

---

## 🏗️ Architecture

```
ghost.py  (CLI Launcher)
    │
    └── backend/server.py  (Flask/SocketIO Brain Stem)
            │
            ├── memory.py         ← 4-Layer Persistent Memory
            ├── ethics.py         ← Arbitration Engine + RLHF
            ├── bridge.py         ← PTY Command Bridge (Groq/Ollama)
            ├── chains.py         ← Operation Graph Orchestrator
            ├── governance.py     ← MVD Cognitive Layer
            ├── diagnostics.py    ← Kernel-Layer Diagnostics
            ├── arsenal.py        ← Zero-Day Synthesis Engine
            ├── resiliency.py     ← Tactical Evasion + Mesh C2
            ├── osint.py          ← OSINT + SemanticLootClassifier
            ├── acquisition.py    ← Autonomous Target Acquisition
            ├── mobile.py         ← Android/ADB Engine
            ├── wireless.py       ← WiFi Attack Engine
            └── discovery.py      ← Network Discovery Engine
```

---

## 🚀 Installation

### Prerequisites
- **OS:** Kali Linux or WSL2 running Kali
- **Python:** 3.10+
- **Tools:** nmap, sqlmap, ffuf, aircrack-ng, adb, frida-tools, afl-fuzz

```bash
# Clone the repository
git clone https://github.com/abneeshsingh21/ghost-agent.git
cd ghost-agent

# Install Python dependencies
pip install -r requirements.txt

# Set your Groq API key
cp .env.example .env
# Edit .env and set: GROQ_API_KEY=your_key_here
```

---

## ⚡ Usage

### Standard Launch
```bash
python ghost.py
```

### Stealth Mode (Zero-Trace, Bypasses Approval Loops)
```bash
python ghost.py --shadow --mode STEALTH
```

### Full Options
```bash
python ghost.py --help

  --port     Server port (default: 5000)
  --host     Server host (default: 0.0.0.0)
  --mode     TEACHING | SUPERVISED | AUTONOMOUS | STEALTH
  --shadow   Shadow Protocol (volatile-only execution)
  --debug    Enable debug output
```

Then open your browser at **http://localhost:5000** to access the Command Center.

---

## 💻 Slash Commands

Once the dashboard is open, use the chat input to issue slash commands:

```
── Core ────────────────────────────────────────────────────
/mode [TEACHING|SUPERVISED|AUTONOMOUS|STEALTH]
/stealth          — Toggle stealth mode
/status           — System status + vitals
/kill <id|all>    — Terminate running shells

── Attack Chains ───────────────────────────────────────────
/chains           — List all available chains
/chain <name>     — Execute a named operation chain
/halt             — Abort active chain

── Engines ─────────────────────────────────────────────────
/osint <seed>     — OSINT recon (username/email/domain/IP)
/acquire <ip>     — Autonomous target acquisition
/mobile <ip>      — Android/ADB attack workflow
/wireless         — WiFi scan & attack suite

── v5.0 Advanced ───────────────────────────────────────────
/diagnose <type> [ip]   — uaf | zeroclick | persistence | telemetry
/arsenal <binary>       — Autonomous zero-day fuzzing
/sdr [frequency]        — Air-gap SDR transmission
/c2 <DNS|ICMP> [domain] — Self-healing covert C2 tunnel
/traffic [interface]    — Quantum-stealth traffic shaping

── Training ────────────────────────────────────────────────
/wrong <action>   — Permanently prohibit an action
/help             — Show all commands
```

---

## 🔒 Operational Modes

| Mode | Behavior |
|------|----------|
| **TEACHING** | Shows planned commands before execution, explains reasoning |
| **SUPERVISED** | Executes recon automatically, pauses before exploitation |
| **AUTONOMOUS** | Fully self-directed — proposes and executes all phases |
| **STEALTH** | Maximum autonomy + forensic evasion (Shadow Protocol active) |

---

## 🛡️ Ethics Framework

GHOST contains a multi-layer ethics system that **cannot be fully disabled**:

1. **Absolute Rules (Layer 1)** — Hardcoded prohibitions that survive any override
2. **Learned Ethics (Layer 2)** — User-taught prohibitions via `/wrong` command  
3. **Target Profiles (Layer 3)** — Per-system authorization checking
4. **Autonomy Matrix (Layer 4)** — Mode-based policy enforcement

The **RLHF Gut Instinct** system actively intercepts noisy, destructive tactics and suggests precise surgical alternatives — making GHOST not just powerful, but intelligent.

---

## 📁 Project Structure

```
ghost-agent/
├── ghost.py                 # CLI entry point
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── .gitignore
├── LICENSE
├── README.md
├── SECURITY.md
├── CHANGELOG.md
├── backend/
│   ├── __init__.py          # v5.0.0 package manifest
│   ├── server.py            # Flask/SocketIO (985 lines)
│   ├── bridge.py            # PTY + Groq API bridge
│   ├── memory.py            # 4-layer memory system
│   ├── ethics.py            # Ethics arbitration (621 lines)
│   ├── governance.py        # MVD cognitive layer
│   ├── chains.py            # Operation graph engine (767 lines)
│   ├── diagnostics.py       # Kernel diagnostics
│   ├── arsenal.py           # Zero-day synthesis
│   ├── resiliency.py        # Tactical evasion
│   ├── osint.py             # OSINT + loot classifier
│   ├── acquisition.py       # Autonomous acquisition
│   ├── mobile.py            # Android/ADB engine
│   ├── wireless.py          # WiFi attack engine
│   └── discovery.py         # Network discovery
├── frontend/
│   ├── index.html           # Command Center dashboard
│   ├── styles.css           # Dark UI stylesheet
│   └── app.js               # WebSocket client logic
└── memory/                  # Persistent agent memory (gitignored)
```

---

## 🔐 Security Policy

Please read [SECURITY.md](SECURITY.md) before reporting any vulnerabilities.

---

## 👤 Author

**Abneesh Singh**  
📧 Singhabneesh250@gmail.com  
🐙 [@abneeshsingh21](https://github.com/abneeshsingh21)

---

## ⚖️ License

**STRICTLY PROPRIETARY.** See [LICENSE](LICENSE) for full terms.

Copyright © 2026 Abneesh Singh. All Rights Reserved.

This software is for **authorized security research only**. Any unauthorized, malicious, or illegal use is strictly prohibited and is the sole legal responsibility of the operator.

---

<div align="center">

*Built with precision. Governed by principle. Deployed with accountability.*

</div>
