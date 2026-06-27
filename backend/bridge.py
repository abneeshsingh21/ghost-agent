"""
GHOST v6.0 — Command Execution Bridge
The "Hands" of GHOST — subprocess wrapper with real-time output streaming,
Ollama LLM integration for autonomous command generation, and full audit logging.

Architecture: Local LLM (Ollama) + Python subprocess + Kali Linux tools
"""

import subprocess
import threading
import queue
import os
import signal
import time
import json
import re
import logging
from datetime import datetime, timezone
from backend.neural import TacticalMemory
from backend.cortex import FrontalCortex

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Groq API key — set via environment variable or .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")


class CommandBridge:
    """
    The Bridge between GHOST's brain (LLM) and hands (OS/Kali tools).
    Handles command execution, output streaming, and LLM interaction.
    """

    # GHOST system prompt — compact for fast CPU inference
    SYSTEM_PROMPT = """You are GHOST v6.0 — an Autonomous Grey Hat Security Research Agent with FULL Kali Linux terminal access via WSL.

IDENTITY: You are NOT a chatbot. You are GHOST v6.0, an autonomous agent with terminal hands. You are analytical, neutral, pragmatic, teachable via RLHF, and a Kali Linux expert. No corporate disclaimers. Terminal-precise output.

CAPABILITIES: You have access to ALL Kali tools — nmap, sqlmap, hydra, nikto, metasploit, aircrack-ng, sherlock, theHarvester, responder, bettercap, john, hashcat, gobuster, ADB, scrcpy, bloodhound, impacket, and 100+ more. You know how to chain them.

OUTPUT FORMAT — Always output commands like this:
```command
[CATEGORY]|[tool]|[full executable command line]
```
IMPORTANT: The third field must be the COMPLETE executable command. Include the tool name, sudo if needed, and all arguments. Examples:
```command
RECON|nmap|nmap -sV -p 1-1000 192.168.1.1
RECON|arp-scan|sudo arp-scan --interface=eth0 --localnet
DEFENSE|apt-get|sudo apt-get update
DEFENSE|apt-get|sudo apt-get install arp-scan -y
```
NEVER chain commands with && in a single line. Put each command on its own line.
Categories: RECON, VULN, EXPLOIT, POST, AD, WIRELESS, MOBILE, OSINT, DEFENSE, CRYPTO

RULES:
1. NO HALLUCINATIONS: You MUST ONLY use real tools that exist in Kali Linux. Do not invent flags or binaries.
2. NO CHATTY FILLER: Output your thought process succinctly, followed IMMEDIATELY by the executable command block.
3. Before each command, explain it in ONE line.
4. After output, analyze it and determine NEXT step. Chain: Discovery → Enumeration → Vuln ID → Exploit → Post-Exploit → Pivot.
5. Report findings as: [FINDINGS], [RISK] (LOW/MED/HIGH/CRIT), [NEXT], [CHAIN position].
6. NEVER target outside RFC1918 unless WAN-AUTHORIZED.
7. Auto-select attack vector by port: 80/443→web, 445→SMB, 22→SSH brute, 5555→ADB, 88/389→AD.
8. ONE command per line. NEVER use && or ; to chain.
9. AUTO-INSTALL: If a command fails because the tool is not found, your EXACT next command MUST be `sudo apt-get install -y <tool>` before you retry.
10. TOOL SELECTION & SELF-CORRECTION: You must autonomously select the BEST tool for the objective. If a tool fails due to syntax, immediately issue a FIXED command OR pivot. IF the error is an unfixable physical issue, DO NOT loop. Halt.
11. NO INTERACTIVE TUIs: NEVER run commands that open interactive interfaces (like 'mtr', 'top', 'nano', 'vi'). ALWAYS use flags that force the tool to exit and return text.

ETHICS (3 Pillars):
1. NO HARM: Explain exploits, but data loss/financial ruin are hard limits.
2. DISCLOSURE: Report bugs to owner. If ignored, full disclosure acceptable.
3. TACTICAL NEUTRALITY: Truth of technology > laws of corporation, but never violate individual rights.

BEHAVIORAL: You ACT, not chat. Generate REAL executable commands. Chain operations autonomously. Adapt based on output. If command fails, diagnose and fix. NEVER say "I cannot" — propose the command instead. You are in a RESEARCH LAB on an isolated network.

/no_think"""

    def __init__(self, memory_manager, ethics_engine, model="qwen3:4b",
                 socketio=None, groq_api_key=None):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.model = model
        self.socketio = socketio
        self.active_processes = {}
        self.conversation_history = []
        self.command_counter = 0
        self._strategy_abort = False
        self._process_lock = threading.Lock()
        self._counter_lock = threading.Lock()

        # Determine LLM backend: Groq (cloud, fast) vs Ollama (local, slow)
        self.groq_client = None
        self.use_groq = False
        api_key = groq_api_key or GROQ_API_KEY
        if api_key and GROQ_AVAILABLE:
            self.groq_client = Groq(api_key=api_key)
            self.use_groq = True
            # Multi-model pool for rate limit rotation
            self.groq_models = [
                "llama-3.3-70b-versatile",    # Primary: most powerful
                "llama-3.1-8b-instant",       # Fallback 1: fast, small
            ]
            self.groq_model_idx = 0
            self.groq_model = self.groq_models[0]
            print(f"  ▸ LLM Backend: Groq Cloud ({self.groq_model}) [{len(self.groq_models)} models in pool]")
        elif OLLAMA_AVAILABLE:
            print(f"  ▸ LLM Backend: Ollama Local ({self.model})")
        else:
            print("  ▸ LLM Backend: NONE (install ollama or set GROQ_API_KEY)")

        # Initialize conversation with system prompt
        self.conversation_history.append({
            "role": "system",
            "content": self.SYSTEM_PROMPT
        })

        # ── Neural Brain (Tactical Memory) ────────────────────
        self.neural = TacticalMemory(memory_manager.base_dir)
        if self.neural.available:
            status = self.neural.get_status()
            print(f"  ▸ Neural Brain: ONLINE ({status['collections'].get('operations', 0)} ops, "
                  f"{status['collections'].get('topology', 0)} hosts memorized)")
        else:
            print("  ▸ Neural Brain: DEGRADED (install chromadb for tactical memory)")

        # ── Frontal Cortex (Multi-Agent Swarm) ───────────────
        self.cortex = FrontalCortex(self, self.neural)
        print("  ▸ Frontal Cortex: ONLINE (Red/Blue/Judge swarm ready)")

        # Add current ethics rules context
        rules = self.memory.get_ethics_rules()
        if rules:
            rules_text = "\n".join([
                f"- Rule #{r['id']}: [{r['type']}] {r['pattern']}"
                + (f" (condition: {r.get('condition', '')})" if r.get('condition') else "")
                for r in rules
            ])
            self.conversation_history.append({
                "role": "system",
                "content": f"ACTIVE ETHICS RULES (from previous training):\n{rules_text}\n\nYou MUST respect these rules. They were taught by the operator."
            })

        forbidden = self.memory.get_forbidden_targets()
        if forbidden:
            self.conversation_history.append({
                "role": "system",
                "content": f"FORBIDDEN TARGETS (NEVER access these): {', '.join(forbidden)}"
            })

    def _rotate_groq_model(self):
        """Rotate to the next Groq model in the pool after rate limit."""
        self.groq_model_idx = (self.groq_model_idx + 1) % len(self.groq_models)
        self.groq_model = self.groq_models[self.groq_model_idx]
        print(f"  [!] Rotated to Groq model: {self.groq_model}")
        return self.groq_model

    def ask_llm(self, user_message):
        """
        Send a message to the LLM and get the response.
        Uses Groq cloud API (fast) if available, falls back to Ollama (slow).
        Auto-rotates Groq models on rate limit (429) errors.
        """
        if not self.use_groq and not OLLAMA_AVAILABLE:
            return {
                "response": "[ERROR] No LLM backend available.\nSet GROQ_API_KEY for cloud inference, or install Ollama for local.",
                "commands": [],
                "analysis": None,
            }

        # Add user message to conversation
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Emit thinking indicator
        if self.socketio:
            self.socketio.emit("llm_thinking", {"status": True})

        try:
            if self.use_groq:
                assistant_message = self._ask_groq_with_fallback()
            else:
                assistant_message = self._ask_ollama()

            # Strip thinking tags if present
            assistant_message = re.sub(
                r"<think>.*?</think>", "", assistant_message, flags=re.DOTALL
            ).strip()

            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            # Keep conversation history manageable
            # IMPORTANT: Preserve ALL system messages (prompt, ethics, forbidden targets)
            # so the LLM never "forgets" learned rules mid-session.
            if len(self.conversation_history) > 42:
                system_msgs = [m for m in self.conversation_history if m.get("role") == "system"]
                non_system = [m for m in self.conversation_history if m.get("role") != "system"]
                self.conversation_history = system_msgs + non_system[-38:]

            # Parse commands from response
            commands = self._parse_commands(assistant_message)
            analysis = self._parse_analysis(assistant_message)

            if self.socketio:
                self.socketio.emit("llm_thinking", {"status": False})

            return {
                "response": assistant_message,
                "commands": commands,
                "analysis": analysis,
            }

        except Exception as e:
            if self.socketio:
                self.socketio.emit("llm_thinking", {"status": False})

            error_msg = f"[LLM ERROR] {str(e)}"
            if "rate_limit" in str(e).lower():
                error_msg += "\n[HINT] All Groq models rate-limited. Wait ~1 min and retry."
            elif "authentication" in str(e).lower() or "api_key" in str(e).lower():
                error_msg += "\n[HINT] Invalid Groq API key. Check your key at console.groq.com"
            elif "connection refused" in str(e).lower():
                error_msg += "\n[HINT] Make sure Ollama is running: ollama serve"
            return {
                "response": error_msg,
                "commands": [],
                "analysis": None,
            }

    def _ask_groq_with_fallback(self):
        """
        Try current Groq model. On 429 rate limit, auto-rotate to next model
        in the pool and retry. Tries all models before giving up.
        """
        attempts = len(self.groq_models)
        last_error = None

        for i in range(attempts):
            try:
                return self._ask_groq()
            except Exception as e:
                error_str = str(e).lower()
                if "rate_limit" in error_str or "429" in error_str:
                    old_model = self.groq_model
                    new_model = self._rotate_groq_model()
                    rotate_msg = f"⚡ Rate limit on {old_model} → switching to {new_model}"
                    print(f"  {rotate_msg}")
                    if self.socketio:
                        self.socketio.emit("system_message", {"message": rotate_msg})
                    last_error = e
                    continue
                else:
                    raise  # Non-rate-limit errors propagate immediately

        # All models exhausted
        raise last_error or Exception("All Groq models rate-limited")

    def _ask_groq(self):
        """Fast cloud inference via Groq API."""
        full_response = ""
        stream = self.groq_client.chat.completions.create(
            model=self.groq_model,
            messages=self.conversation_history,
            max_tokens=2048,
            temperature=0.7,
            stream=True,
        )

        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            full_response += token
            if self.socketio and token:
                self.socketio.emit("llm_token", {"token": token})

        return full_response

    def _ask_ollama(self):
        """Slow local inference via Ollama."""
        full_response = ""
        stream = ollama.chat(
            model=self.model,
            messages=self.conversation_history,
            stream=True,
            options={
                "num_predict": 2048,
                "temperature": 0.7,
                "num_ctx": 2048,
            },
        )

        for chunk in stream:
            token = chunk.get("message", {}).get("content", "")
            full_response += token
            if self.socketio and token:
                self.socketio.emit("llm_token", {"token": token})

        return full_response

    def feed_output_to_llm(self, command, output, exit_code):
        """
        Feed command output back to the LLM for analysis.
        The LLM will analyze results and suggest next steps.
        """
        feedback = f"""Command executed: {command}
Exit code: {exit_code}
Output:
```
{output[:4000]}
```
Analyze this output. What did we find? What should we do next?"""

        return self.ask_llm(feedback)

    # Linux/Kali tools that MUST run through WSL on Windows
    WSL_TOOLS = {
        # Recon
        "nmap", "masscan", "netdiscover", "arp-scan", "nbtscan", "enum4linux",
        "dnsrecon", "dnsenum", "fierce", "sublist3r", "amass", "recon-ng",
        "whatweb", "wafw00f", "whois", "dig", "host", "traceroute", "ping",
        "nmblookup", "dnsmasq", "geoiplookup",
        # Vulnerability
        "nikto", "wpscan", "sqlmap", "searchsploit", "openvas", "lynis",
        # Exploitation
        "msfconsole", "msfvenom", "msfdb", "hydra", "medusa", "crackmapexec",
        "evil-winrm", "smbclient", "rpcclient", "impacket-psexec",
        "impacket-smbexec", "impacket-wmiexec", "impacket-secretsdump",
        # Wireless
        "airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng",
        "wifite", "wifiphisher", "bettercap", "ettercap", "kismet", "hostapd-mana",
        # Password
        "john", "hashcat", "ophcrack", "cewl", "crunch", "hash-identifier",
        # OSINT
        "sherlock", "theHarvester", "maltego", "spiderfoot", "holehe",
        "phoneinfoga", "spoofcheck",
        # Social Engineering
        "setoolkit", "gophish", "httrack", "beef-xss",
        # Post-Exploitation
        "linpeas", "winpeas", "pspy", "chisel", "socat", "proxychains",
        # Mobile / Android
        "apktool", "apksigner", "adb", "fastboot",
        # Bluetooth
        "hcitool", "sdptool", "bluetoothctl", "l2ping",
        # Forensics
        "binwalk", "foremost", "steghide", "exiftool", "volatility",
        # Sniffing
        "tcpdump", "tshark", "wireshark", "responder", "mitm6",
        # Misc Linux
        "curl", "wget", "nc", "ncat", "netcat", "gobuster", "dirb",
        "dirbuster", "ffuf", "wfuzz", "nuclei", "httpx",
        # Fuzzing
        "afl-fuzz", "boofuzz",
        # Shell
        "bash", "sh", "sudo", "apt", "apt-get", "dpkg", "ifconfig",
        "iwconfig", "ip", "iptables", "ss", "lsof", "grep", "awk",
        "sed", "cat", "ls", "find", "chmod", "chown", "mkdir", "rm",
    }

    def _should_route_wsl(self, command):
        """Check if a command should be routed through WSL Kali on Windows."""
        if os.name != 'nt':
            return False  # Already on Linux

        # Extract the base tool name
        parts = command.strip().split()
        if not parts:
            return False

        tool = parts[0].lower()
        # If it explicitly asks for sudo, always route to WSL to prevent Windows 11 'sudo is disabled' errors.
        if tool == "sudo":
            return True

        return tool in self.WSL_TOOLS

    def _route_through_wsl(self, command):
        """Wrap a command to execute through WSL Kali Linux."""
        # Escape single quotes in the command for bash
        escaped = command.replace("'", "'\\''")
        return f"wsl -d kali-linux -- bash -c '{escaped}'"

    def _normalize_command(self, command):
        """Normalize and lightly de-duplicate malformed command text."""
        if not isinstance(command, str):
            return ""

        normalized = " ".join(command.strip().split())
        if not normalized:
            return ""

        parts = normalized.split()
        # Collapse accidental duplicate prefixes (e.g. "sudo sudo apt update", "nmap nmap -sV").
        while len(parts) >= 2 and parts[0].lower() == parts[1].lower():
            parts.pop(0)

        return " ".join(parts)

    def _assess_command_quality(self, command):
        """
        Score command quality before execution.
        Returns: {ok, score, issues, normalized_command}
        """
        raw_command = command if isinstance(command, str) else ""
        normalized = self._normalize_command(raw_command)
        issues = []
        score = 1.0

        if not normalized:
            issues.append("Empty command.")
            score -= 1.0

        if "\n" in raw_command or "\r" in raw_command:
            issues.append("Multi-line command detected.")
            score -= 0.35

        if re.search(r"&&|\|\||;", normalized):
            issues.append("Command chaining detected; use one command per line.")
            score -= 0.45

        placeholder_pattern = r"(\{[^}]+\}|<[^>]+>|\bTARGET_IP\b|\bOSINT_PIN_HERE\b|\bdiscovered_ip\b)"
        if re.search(placeholder_pattern, normalized):
            issues.append("Unresolved placeholders found in command.")
            score -= 0.6

        if len(normalized) > 1024:
            issues.append("Command is too long and likely malformed.")
            score -= 0.35

        score = max(0.0, min(1.0, score))
        return {
            "ok": score >= 0.55 and not any("placeholder" in i.lower() for i in issues),
            "score": round(score, 2),
            "issues": issues,
            "normalized_command": normalized,
        }

    def execute_command(self, command, timeout=300, stream_callback=None):
        """
        Execute a shell command with real-time output streaming.
        On Windows, automatically routes Linux/Kali tools through WSL.

        Returns dict:
        {
            "status": "OK" | "ERR" | "TIMEOUT" | "KILLED",
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "duration": float,
            "command_id": int,
            "wsl_routed": bool,
        }
        """
        with self._counter_lock:
            self.command_counter += 1
            cmd_id = self.command_counter

        quality = self._assess_command_quality(command)
        if not quality["ok"]:
            return {
                "status": "ERR",
                "stdout": "",
                "stderr": f"[QUALITY GATE] {' '.join(quality['issues'])}",
                "exit_code": -1,
                "duration": 0,
                "command_id": cmd_id,
                "quality": quality,
            }

        command = quality["normalized_command"]

        # Log to memory
        category = self.ethics._detect_category(command)
        target_ip = self._extract_ip(command)
        self.memory.log_command(category, command.split()[0] if command else "unknown",
                                command, {"target": target_ip})

        # Auto-route through WSL if needed
        wsl_routed = False
        actual_command = command
        if self._should_route_wsl(command):
            actual_command = self._route_through_wsl(command)
            wsl_routed = True
            if self.socketio:
                self.socketio.emit("command_output", {
                    "id": cmd_id,
                    "type": "info",
                    "data": f"[WSL] Routing through kali-linux: {command}\r\n",
                })

        start_time = time.time()
        stdout_lines = []
        stderr_lines = []

        try:
            process = subprocess.Popen(
                actual_command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid if os.name != 'nt' else None,
            )
            with self._process_lock:
                self.active_processes[cmd_id] = process

            # Stream stdout in real-time
            def read_stdout():
                for line in iter(process.stdout.readline, ""):
                    stdout_lines.append(line)
                    if stream_callback:
                        stream_callback("stdout", line, cmd_id)
                    if self.socketio:
                        # Normalize to \r\n for proper xterm.js alignment
                        out_line = line.replace('\r\n', '\n').replace('\n', '\r\n')
                        self.socketio.emit("command_output", {
                            "id": cmd_id,
                            "type": "stdout",
                            "data": out_line,
                        })

            def read_stderr():
                for line in iter(process.stderr.readline, ""):
                    stderr_lines.append(line)
                    if stream_callback:
                        stream_callback("stderr", line, cmd_id)
                    if self.socketio:
                        # Normalize to \r\n for proper xterm.js alignment
                        out_line = line.replace('\r\n', '\n').replace('\n', '\r\n')
                        self.socketio.emit("command_output", {
                            "id": cmd_id,
                            "type": "stderr",
                            "data": out_line,
                        })

            t_out = threading.Thread(target=read_stdout, daemon=True)
            t_err = threading.Thread(target=read_stderr, daemon=True)
            t_out.start()
            t_err.start()

            process.wait(timeout=timeout)
            t_out.join(timeout=2)
            t_err.join(timeout=2)

            duration = time.time() - start_time
            exit_code = process.returncode

            # Clean up
            with self._process_lock:
                self.active_processes.pop(cmd_id, None)

            status = "OK" if exit_code == 0 else "ERR"

            result = {
                "status": status,
                "stdout": "".join(stdout_lines),
                "stderr": "".join(stderr_lines),
                "exit_code": exit_code,
                "duration": round(duration, 2),
                "command_id": cmd_id,
                "quality": quality,
            }

            # Log completion
            log_path = os.path.join(self.memory.logs_dir, "command_history.log")
            with open(log_path, "a", encoding="utf-8") as f:
                ts = datetime.now(timezone.utc).isoformat()
                f.write(f"[{ts}] [RESULT] cmd_id={cmd_id} status={status} "
                        f"exit={exit_code} duration={duration:.2f}s\n")

            return result

        except subprocess.TimeoutExpired:
            self._kill_process(cmd_id)
            return {
                "status": "TIMEOUT",
                "stdout": "".join(stdout_lines),
                "stderr": "".join(stderr_lines) + f"\n[TIMEOUT after {timeout}s]",
                "exit_code": -1,
                "duration": timeout,
                "command_id": cmd_id,
            }
        except Exception as e:
            return {
                "status": "ERR",
                "stdout": "".join(stdout_lines),
                "stderr": str(e),
                "exit_code": -1,
                "duration": time.time() - start_time,
                "command_id": cmd_id,
            }

    def execute_command_async(self, command, timeout=300, stream_callback=None):
        """Standard wrapper to offload blocking execution onto a daemon thread."""
        def _target():
            exec_result = self.execute_command(command, timeout, stream_callback)
            if self.socketio:
                self.socketio.emit("command_complete", {
                    "command": command,
                    "result": exec_result,
                })
            
            # Feed output back to LLM for analysis to enable self-correction
            if exec_result["status"] in ("OK", "ERR"):
                try:
                    follow_up = self.feed_output_to_llm(
                        command, exec_result["stdout"] + "\n" + exec_result["stderr"], exec_result["exit_code"]
                    )
                    if self.socketio:
                        # Process ethics for any proposed follow-up commands
                        verdicts = []
                        for cmd in follow_up.get("commands", []):
                            target_ip = self._extract_ip(cmd.get("full_command", ""))
                            verdict = self.ethics.check_command(cmd.get("full_command", ""), target_ip)
                            verdicts.append(verdict)

                        payload = {
                            "response": f"[Post-Execution Analysis]:\n{follow_up.get('analysis', follow_up.get('response', 'No analysis provided.'))}",
                            "commands": follow_up.get("commands", []),
                            "verdicts": verdicts
                        }
                        self.socketio.emit("chat_response", payload)
                except Exception as e:
                    print(f"Error in async follow-up: {e}")

        # Start background execution
        threading.Thread(target=_target, daemon=True).start()
        return {
            "status": "RUNNING",
            "command": command,
            "message": "Spawning background process for WSL..."
        }

    def send_input(self, cmd_id, text):
        """Send raw text to the stdin of an active process."""
        with self._process_lock:
            process = self.active_processes.get(cmd_id)
        if process and process.poll() is None:
            try:
                process.stdin.write(text + "\n")
                process.stdin.flush()
                return True
            except Exception as e:
                return False
        return False

    def kill_command(self, cmd_id):
        """Kill a running command by ID."""
        return self._kill_process(cmd_id)

    def kill_all(self):
        """Kill all running commands."""
        with self._process_lock:
            cmd_ids = list(self.active_processes.keys())
        for cmd_id in cmd_ids:
            self._kill_process(cmd_id)

    def process_user_input(self, user_input, auto_execute=False):
        """
        Full pipeline: User input → LLM → Ethics check → Execute (if approved).

        Returns dict with the full interaction result.
        """
        result = {
            "user_input": user_input,
            "llm_response": None,
            "proposed_commands": [],
            "ethics_verdicts": [],
            "execution_results": [],
            "analysis": None,
        }

        # Step 1: Ask the LLM
        llm_result = self.ask_llm(user_input)
        result["llm_response"] = llm_result["response"]
        result["proposed_commands"] = llm_result["commands"]
        result["analysis"] = llm_result.get("analysis")

        # Step 2: Ethics check each proposed command
        for cmd_info in llm_result["commands"]:
            command = cmd_info.get("full_command", "")
            quality = self._assess_command_quality(command)
            cmd_info["quality"] = quality

            if quality["normalized_command"]:
                cmd_info["full_command"] = quality["normalized_command"]
            command = cmd_info.get("full_command", "")

            if not quality["ok"]:
                quality_verdict = {
                    "verdict": "HALT",
                    "reason": f"COMMAND QUALITY: {' '.join(quality['issues'])}",
                    "rule_id": None,
                    "layer": "command_quality",
                    "category": self.ethics._detect_category(command),
                    "risk_level": "MEDIUM",
                    "safety_flags": ["QUALITY_GATE"],
                }
                cmd_info["ethics_verdict"] = quality_verdict
                cmd_info["executed"] = False
                cmd_info["halt_reason"] = quality_verdict["reason"]
                result["ethics_verdicts"].append(quality_verdict)
                continue

            target_ip = self._extract_ip(command)

            verdict = self.ethics.check_command(command, target_ip)
            cmd_info["ethics_verdict"] = verdict
            result["ethics_verdicts"].append(verdict)

            # Step 3: Execute if policy allows
            mode = self.memory.get_mode()

            if verdict["verdict"] == "HALT":
                # Never execute — report to user
                cmd_info["executed"] = False
                cmd_info["halt_reason"] = verdict["reason"]
            elif verdict["verdict"] == "ALLOW" or (verdict["verdict"] == "PROPOSE" and auto_execute) or mode in ("AUTONOMOUS", "STEALTH"):
                # Auto-execute (Async) — STEALTH mode is even more autonomous than AUTONOMOUS
                exec_result = self.execute_command_async(command)
                cmd_info["executed"] = True
                cmd_info["exec_result"] = exec_result
                result["execution_results"].append(exec_result)

                # Feed output back to LLM for analysis is now handled automatically
                # inside the async thread created by execute_command_async
            else:
                # PROPOSE — wait for user approval
                cmd_info["executed"] = False
                cmd_info["awaiting_approval"] = True

        return result

    def approve_and_execute(self, command):
        """Execute a previously proposed command after user approval."""
        quality = self._assess_command_quality(command)
        if not quality["ok"]:
            return {
                "status": "ERR",
                "command": command,
                "message": f"[QUALITY GATE] {' '.join(quality['issues'])}",
                "quality": quality,
            }

        normalized = quality["normalized_command"]
        target_ip = self._extract_ip(normalized)
        verdict = self.ethics.check_command(normalized, target_ip)
        if verdict["verdict"] == "HALT":
            return {
                "status": "HALT",
                "command": normalized,
                "message": verdict.get("reason", "Blocked by ethics."),
                "ethics_verdict": verdict,
                "quality": quality,
            }

        exec_result = self.execute_command_async(normalized)
        exec_result["quality"] = quality
        return exec_result

    def change_model(self, model_name):
        """Switch the Ollama model."""
        self.model = model_name
        return {"status": "OK", "model": model_name}

    # ── Helpers ────────────────────────────────────────────────────────────

    def _parse_commands(self, llm_response):
        """Extract command blocks from LLM response."""
        commands = []

        try:
            # Match ```command blocks AND ```bash blocks
            cmd_blocks = re.findall(r"```(?:command|bash)\s*\n(.*?)```", llm_response, re.DOTALL)
            for block in cmd_blocks:
                for line in block.strip().split("\n"):
                    line = line.strip()
                    if "|" in line:
                        parts = line.split("|", 2)
                        if len(parts) >= 3:
                            tool = parts[1].strip("[] ")
                            args = parts[2].strip("[] ")
                            # Smart full_command: use args directly if they already
                            # contain the tool name (e.g. "sudo apt update")
                            args_first = args.split()[0] if args.split() else ""
                            if args_first == tool or args_first == "sudo" or tool in args:
                                full_cmd = args
                            else:
                                full_cmd = f"{tool} {args}"
                            commands.append({
                                "category": parts[0].strip("[] "),
                                "tool": tool,
                                "arguments": args,
                                "full_command": full_cmd,
                                "raw": line,
                            })
                    elif line and not line.startswith("#"):
                        # Plain command in bash block (no pipe format)
                        tool = line.split()[0] if line.split() else "unknown"
                        commands.append({
                            "category": "RECON",
                            "tool": tool,
                            "arguments": line[len(tool):].strip(),
                            "full_command": line,
                            "raw": line,
                        })

            # Also match inline commands (backtick-wrapped)
            if not commands:
                inline = re.findall(r"`([^`]+)`", llm_response)
                for cmd in inline:
                    cmd = cmd.strip()
                    # Filter out non-commands
                    if any(tool in cmd.lower() for tool in [
                        # Reconnaissance
                        "nmap", "masscan", "netdiscover", "arp-scan", "arp ",
                        "tcpdump", "traceroute", "whatweb", "whois", "dig ",
                        "ip addr", "ip route", "ifconfig", "iwconfig", "route ",
                        "cat /etc", "hostname", "uname",
                        # Vulnerability
                        "nikto", "dirb", "gobuster", "searchsploit", "openvas",
                        "wpscan", "nuclei",
                        # Exploitation
                        "sqlmap", "hydra", "msfconsole", "msfvenom", "metasploit",
                        "bettercap", "ettercap",
                        # AD / Enterprise
                        "crackmapexec", "enum4linux", "bloodhound",
                        "responder", "ntlmrelayx", "ldapdomaindump",
                        "GetUserSPNs", "GetNPUsers", "secretsdump",
                        "psexec.py", "wmiexec.py", "smbexec.py",
                        "ticketer.py", "dacledit.py", "certipy",
                        # Wireless
                        "aircrack", "airodump", "aireplay", "airmon",
                        "wifiphisher", "reaver", "bully", "wash",
                        "hostapd", "kismet", "airbase",
                        # Mobile
                        "adb ", "adb connect", "scrcpy", "frida",
                        # OSINT
                        "theHarvester", "sherlock", "recon-ng",
                        "social-mapper", "maltego", "spiderfoot",
                        "dnsrecon", "sublist3r", "amass",
                        # Social Engineering
                        "setoolkit", "gophish", "httrack",
                        "spoofcheck", "swaks",
                        # Crypto / Password
                        "hashcat", "john ", "john the",
                        "cupp", "cewl", "crunch", "ophcrack",
                        "hash-identifier", "hashid",
                        # Post-exploitation
                        "linpeas", "winpeas", "mimikatz",
                        "meterpreter", "empire", "covenant",
                        # Defense
                        "iptables", "ufw ", "fail2ban", "snort",
                        "suricata", "ossec",
                        # Fuzzing
                        "afl-fuzz", "boofuzz", "wfuzz", "ffuf",
                        # General
                        "curl", "wget", "python ", "python3 ",
                        "nc ", "netcat", "socat",
                        "chmod", "chown", "cat ", "grep",
                        "find ", "locate", "ls ", "pwd",
                        "ssh ", "scp ", "ftp ",
                        "netstat", "ss -", "lsof",
                    ]):
                        tool = cmd.split()[0] if cmd else "unknown"
                        category = self.ethics._detect_category(cmd)
                        commands.append({
                            "category": category.upper(),
                            "tool": tool,
                            "arguments": cmd[len(tool):].strip(),
                            "full_command": cmd,
                            "raw": cmd,
                        })
        except Exception as e:
            logging.getLogger("ghost.bridge").warning(f"Command parser error (non-fatal): {e}")

        return commands

    def _parse_analysis(self, llm_response):
        """Extract analysis blocks from LLM response."""
        try:
            analysis_blocks = re.findall(r"```analysis\s*\n(.*?)```", llm_response, re.DOTALL)
            if analysis_blocks:
                analysis = {}
                for block in analysis_blocks:
                    for line in block.strip().split("\n"):
                        if line.startswith("[FINDINGS]"):
                            analysis["findings"] = line.split(":", 1)[1].strip()
                        elif line.startswith("[RISK]"):
                            analysis["risk"] = line.split(":", 1)[1].strip()
                        elif line.startswith("[NEXT]"):
                            analysis["next_action"] = line.split(":", 1)[1].strip()
                        elif line.startswith("[CHAIN]"):
                            analysis["chain_position"] = line.split(":", 1)[1].strip()
                return analysis
        except Exception:
            pass
        return None

    def _extract_ip(self, command):
        """Extract the first IP address from a command string."""
        ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b"
        match = re.search(ip_pattern, command)
        if match:
            ip = match.group().split("/")[0]
            return ip
        return None

    def _kill_process(self, cmd_id):
        """Kill a process by command ID."""
        with self._process_lock:
            process = self.active_processes.get(cmd_id)
        if process:
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                return True
            except (ProcessLookupError, OSError):
                return True
            finally:
                with self._process_lock:
                    self.active_processes.pop(cmd_id, None)
        return False

    def get_status(self):
        """Get bridge status summary."""
        with self._process_lock:
            active_count = len(self.active_processes)
        status = {
            "ollama_available": OLLAMA_AVAILABLE or self.use_groq,
            "model": self.groq_model if self.use_groq else self.model,
            "active_processes": active_count,
            "commands_executed": self.command_counter,
            "conversation_length": len(self.conversation_history),
        }

        # Include neural brain status
        if self.neural and self.neural.available:
            status["neural_brain"] = self.neural.get_status()

        # Include cortex decision count
        if self.cortex:
            status["cortex_decisions"] = len(self.cortex.decision_history)

        return status

    # ═══════════════════════════════════════════════════════════════
    #  Strategic Brain — Chain of Thought Execution
    # ═══════════════════════════════════════════════════════════════

    STRATEGY_PROMPT = """STRATEGIC MODE ACTIVATED.
Before executing ANY commands, you MUST follow this protocol:

1. ANALYZE the request and identify threats/obstacles.
2. Generate a STRATEGIC PLAN explaining your approach step by step.
3. Wrap your plan in ```plan ... ``` tags.
4. Then output the actual commands in ```command ... ``` or ```bash ... ``` format.
5. If a command fails and I show you the error, generate a FIX PLAN in ```fix ... ``` tags with corrected commands.

Example plan format:
```plan
1. Target is on a local subnet, will use passive ARP scan first to avoid detection.
2. If hosts found, perform selective port scan on high-value ports (22,80,443,445,3389,5555).
3. Based on open ports, choose attack vector: web → nikto/gobuster, SMB → enum4linux, ADB → direct connect.
4. Fallback: if firewall detected, switch to stealth SYN scan with decoy.
```

Always think before acting. Be strategic."""

    def __init_strategy(self):
        """Reset strategy abort flag."""
        self._strategy_abort = False

    def abort_strategy(self):
        """Set the abort flag to halt the current strategy loop."""
        self._strategy_abort = True

    def strategic_execute(self, user_input, auto_execute=False, socketio=None):
        """
        Full Strategic Brain pipeline:
        1. PLAN — Ask LLM for strategic plan before any action
        2. EXECUTE — Run planned commands
        3. SELF-CORRECT — If failure, auto-fix and retry (max 3)
        4. REPORT — Log all thinking to chat pane
        """
        self.__init_strategy()
        sio = socketio or self.socketio
        max_retries = 3

        if sio:
            sio.emit("strategy_started", {})

        # ── Phase 0: REFLEX CHECK (Zero Latency) ─────────────
        # Query the hippocampus BEFORE hitting the LLM.
        # If we've successfully attacked a similar target before,
        # skip straight to the proven command.
        reflex = self._check_reflex(user_input, sio)
        if reflex and auto_execute:
            return reflex

        # ── Phase 1: PLANNING ─────────────────────────────────
        plan_request = f"{self.STRATEGY_PROMPT}\n\nOperator request: {user_input}"
        llm_result = self.ask_llm(plan_request)

        if self._strategy_abort:
            if sio: sio.emit("strategy_halted", {})
            return self._build_strategy_result(user_input, "HALTED", llm_result)

        # Extract and emit plan block
        plan_text = self._extract_block(llm_result["response"], "plan")
        if plan_text and sio:
            sio.emit("thinking_block", {
                "phase": "PLAN",
                "title": "Strategic Plan",
                "content": plan_text,
            })

        # Build initial result
        result = {
            "user_input": user_input,
            "llm_response": llm_result["response"],
            "proposed_commands": llm_result["commands"],
            "ethics_verdicts": [],
            "execution_results": [],
            "analysis": llm_result.get("analysis"),
            "strategy_plan": plan_text,
        }

        # ── Phase 2: EXECUTE ──────────────────────────────────
        for cmd_info in llm_result["commands"]:
            if self._strategy_abort:
                if sio: sio.emit("strategy_halted", {})
                return result

            command = cmd_info.get("full_command", "")
            if not command:
                continue

            target_ip = self._extract_ip(command)
            verdict = self.ethics.check_command(command, target_ip)
            cmd_info["ethics_verdict"] = verdict
            result["ethics_verdicts"].append(verdict)

            if verdict["verdict"] == "HALT":
                cmd_info["executed"] = False
                cmd_info["halt_reason"] = verdict["reason"]
                if sio:
                    sio.emit("thinking_block", {
                        "phase": "EXECUTE",
                        "title": f"HALTED: {command[:60]}",
                        "content": f"Ethics blocked: {verdict['reason']}",
                    })
                continue

            should_exec = (verdict["verdict"] == "ALLOW" and
                          (auto_execute or self.memory.get_mode() in ["AUTONOMOUS", "STEALTH"]))

            if not should_exec and verdict["verdict"] == "PROPOSE":
                cmd_info["executed"] = False
                cmd_info["awaiting_approval"] = True
                continue

            if not should_exec:
                cmd_info["executed"] = False
                cmd_info["awaiting_approval"] = True
                continue

            # Execute with self-correction loop
            if sio:
                sio.emit("thinking_block", {
                    "phase": "EXECUTE",
                    "title": f"Executing: {command[:60]}",
                    "content": f"$ {command}",
                })

            exec_result = self.execute_command(command)
            cmd_info["executed"] = True
            cmd_info["exec_result"] = exec_result
            result["execution_results"].append(exec_result)

            # ── Neural: Auto-record successful operations ─────
            self._neural_record(command, exec_result, target_ip)

            # ── Phase 3: SELF-CORRECTION ──────────────────────
            retry_count = 0
            original_cmd = command
            while (exec_result["status"] != "OK" and
                   retry_count < max_retries and
                   not self._strategy_abort):

                retry_count += 1
                stderr = exec_result.get("stderr", "")
                stdout = exec_result.get("stdout", "")  # BUG FIX: was 'output', execute_command returns 'stdout'
                exit_code = exec_result.get("exit_code", -1)
                combined_out = f"{stdout}\n{stderr}".strip()

                # Auto-detect "command not found" and install
                not_found_match = re.search(r"(?:command not found|No such file|not recognized).*?(\S+)", combined_out)
                tool_name = None
                if not_found_match:
                    # Extract the tool name from the original command
                    cmd_parts = original_cmd.split()
                    for p in cmd_parts:
                        if p not in ("sudo", "wsl", "-d", "kali-linux", "--", "bash", "-c", "-li"):
                            tool_name = p
                            break

                fix_request = (
                    f"The previous command FAILED.\n"
                    f"Command: {command}\n"
                    f"Exit code: {exit_code}\n"
                    f"Error output:\n```\n{combined_out[:2000]}\n```\n\n"
                )

                if tool_name and "not found" in combined_out.lower():
                    fix_request += (
                        f"The tool '{tool_name}' is NOT INSTALLED. "
                        f"Generate TWO commands:\n"
                        f"1. Install the tool: sudo apt-get install {tool_name} -y\n"
                        f"2. Retry the original command: {original_cmd}\n\n"
                    )
                else:
                    fix_request += (
                        f"Analyze why it failed and generate FIXED commands. "
                    )

                fix_request += (
                    f"Wrap your analysis in ```fix ... ``` tags. "
                    f"Then output ALL corrected commands in ```command ... ``` or ```bash ... ``` tags. "
                    f"ONE command per line. Do NOT ask for permission. Fix it."
                )

                fix_result = self.ask_llm(fix_request)
                fix_text = self._extract_block(fix_result["response"], "fix")

                if sio and fix_text:
                    sio.emit("thinking_block", {
                        "phase": "FIX",
                        "title": f"Self-Correction (attempt {retry_count}/{max_retries})",
                        "content": fix_text,
                    })

                # Execute ALL fixed commands in sequence
                fixed_commands = fix_result.get("commands", [])
                if fixed_commands:
                    for fc in fixed_commands:
                        if self._strategy_abort:
                            break
                        fixed_cmd = fc.get("full_command", "")
                        if not fixed_cmd:
                            continue

                        if sio:
                            sio.emit("thinking_block", {
                                "phase": "FIX",
                                "title": f"Running fix: {fixed_cmd[:60]}",
                                "content": f"$ {fixed_cmd}",
                            })

                        exec_result = self.execute_command(fixed_cmd)
                        cmd_info["exec_result"] = exec_result

                    # After all fix commands, check if the last one succeeded
                    command = fixed_commands[-1].get("full_command", command)
                else:
                    break  # No fix generated, stop retrying

        # ── Phase 4: REPORT ───────────────────────────────────
        if sio and not self._strategy_abort:
            executed_cmds = [c for c in llm_result["commands"] if c.get("executed")]
            summary_lines = [
                f"Commands planned: {len(llm_result['commands'])}",
                f"Commands executed: {len(executed_cmds)}",
                f"Self-corrections: {sum(1 for r in result['execution_results'] if r.get('status') != 'OK')}",
            ]
            if plan_text:
                summary_lines.insert(0, f"Plan: {plan_text[:200]}")

            sio.emit("strategy_complete", {
                "summary": "\n".join(summary_lines),
            })

        return result

    def _extract_block(self, text, block_type):
        """Extract content from ```blocktype ... ``` tags."""
        pattern = rf"```{block_type}\s*\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None

    def _build_strategy_result(self, user_input, status, llm_result):
        return {
            "user_input": user_input,
            "llm_response": llm_result.get("response", ""),
            "proposed_commands": [],
            "ethics_verdicts": [],
            "execution_results": [],
            "analysis": None,
            "strategy_status": status,
        }

    # ═══════════════════════════════════════════════════════════════
    #  Neural Brain Helpers — Reflex & Recording
    # ═══════════════════════════════════════════════════════════════

    def _check_reflex(self, user_input, sio=None):
        """
        Phase 0 — Query the hippocampus BEFORE the LLM.

        Extracts port/OS hints from the user input and checks if we've
        successfully attacked a similar target before. If yes, returns
        the proven reflex command immediately (Zero Latency).
        """
        if not self.neural or not self.neural.available:
            return None

        # Extract port hints from user input
        ports = []
        os_type = ""

        # Check discovered hosts in session for port info
        target_ip = self._extract_ip(user_input)
        if target_ip:
            for host in self.memory.get_session().get("discovered_hosts", []):
                if host.get("ip") == target_ip:
                    ports = [int(p) for p in host.get("ports", []) if str(p).isdigit()]
                    os_type = host.get("os", "")
                    break

        # Also check topology memory
        if not ports and target_ip:
            topo = self.neural.recall_topology()
            if target_ip in topo:
                host_info = topo[target_ip]
                ports = [int(p) for p in host_info.get("ports", []) if str(p).isdigit()]
                os_type = host_info.get("os", "")

        if not ports:
            return None

        # Query the hippocampus
        reflex = self.neural.recall_reflex(ports, os_type, target_ip)
        if not reflex:
            return None

        # Emit reflex notification to UI
        if sio:
            sio.emit("thinking_block", {
                "phase": "REFLEX",
                "title": f"⚡ Neural Reflex Fired ({reflex['confidence']:.0%} match)",
                "content": (
                    f"Recognized target pattern from memory.\n"
                    f"Original: {reflex['original_target']} "
                    f"(ports: {reflex['original_ports']} / {reflex['original_os']})\n"
                    f"Proven command: {reflex['command']}\n"
                    f"Success weight: {reflex['success_weight']:.2f}\n"
                    f"Bypassing LLM — executing from muscle memory."
                ),
            })

        # Build a result that mimics strategic_execute output
        return {
            "user_input": user_input,
            "llm_response": f"[REFLEX] {reflex['reason']}",
            "proposed_commands": [{
                "full_command": reflex["command"],
                "category": "REFLEX",
                "reflex": True,
                "confidence": reflex["confidence"],
                "success_weight": reflex["success_weight"],
            }],
            "ethics_verdicts": [],
            "execution_results": [],
            "analysis": reflex["reason"],
            "strategy_plan": None,
            "reflex_activated": True,
        }

    def _neural_record(self, command, exec_result, target_ip=None):
        """
        Auto-record a command execution into the hippocampus.

        Called after every command execution in the strategic pipeline.
        Records successful operations for future reflex recall.
        Triggers dopamine reward/punish based on exit code.
        """
        if not self.neural or not self.neural.available:
            return

        exit_code = exec_result.get("exit_code", -1)
        stdout = exec_result.get("stdout", "") or exec_result.get("output", "") or ""
        stderr = exec_result.get("stderr", "") or ""
        combined_output = (stdout + "\n" + stderr).lower()

        # Get target's port/OS info from session context
        ports = []
        os_type = ""
        if target_ip:
            for host in self.memory.get_session().get("discovered_hosts", []):
                if host.get("ip") == target_ip:
                    ports = [int(p) for p in host.get("ports", []) if str(p).isdigit()]
                    os_type = host.get("os", "")
                    break

        # Detect category from command
        category = "RECON"
        cmd_lower = command.lower()
        if any(t in cmd_lower for t in ["nmap", "netdiscover", "masscan", "arp-scan"]):
            category = "RECON"
        elif any(t in cmd_lower for t in ["nikto", "sqlmap", "searchsploit"]):
            category = "VULN"
        elif any(t in cmd_lower for t in ["msfvenom", "meterpreter", "exploit", "hydra"]):
            category = "EXPLOIT"
        elif any(t in cmd_lower for t in ["adb", "scrcpy", "frida"]):
            category = "MOBILE"

        # Record the operation
        op_id = self.neural.record_operation(
            command=command,
            target_ip=target_ip or "",
            ports=ports,
            os_type=os_type,
            exit_code=exit_code,
            stdout_snippet=stdout[:500],
            category=category,
        )

        if not op_id:
            return

        # ── Dopamine Loop ─────────────────────────────────────
        # Reward: shell acquired, data returned successfully
        # Punish: blocked, banned, connection refused
        # BUG FIX: Now checks combined stdout+stderr, not just stdout
        if exit_code == 0:
            # Check for high-value indicators in output
            shell_indicators = ["uid=", "whoami", "root@", "meterpreter", "session opened"]
            if any(ind in combined_output for ind in shell_indicators):
                # Strong reward — shell acquired!
                self.neural.reward(op_id, delta=0.25)
            else:
                # Mild reward — command succeeded
                self.neural.reward(op_id, delta=0.10)
        else:
            # Check for punishment indicators in BOTH stdout and stderr
            punish_indicators = ["blocked", "banned", "filtered", "connection refused",
                                 "access denied", "permission denied", "ids alert"]
            if any(ind in combined_output for ind in punish_indicators):
                # Strong punishment — detected/blocked
                self.neural.punish(op_id, delta=0.30)
            else:
                # Mild punishment — command just failed
                self.neural.punish(op_id, delta=0.10)


# ═══════════════════════════════════════════════════════════════
#  PTY Manager — Interactive Shell Sessions
# ═══════════════════════════════════════════════════════════════

class PtyManager:
    """
    Manages a persistent interactive shell session (WSL Kali on Windows,
    or native bash on Linux) with bidirectional WebSocket piping.

    Uses `script -qc` inside WSL to force a REAL pseudo-terminal so that
    programs detect a TTY and properly handle line wrapping, colors, and
    terminal dimensions.
    """

    def __init__(self, socketio):
        self.socketio = socketio
        self.process = None
        self._reader_thread = None
        self._alive = False
        self._cols = 120
        self._rows = 30

    def spawn(self, shell_cmd=None):
        """Spawn a persistent shell process with proper PTY."""
        if self.process and self.process.poll() is None:
            return True  # Already running

        if os.name == 'nt':
            # Use `script -qc` to force a real PTY inside WSL.
            # This makes isatty() return True inside the shell, so programs
            # like apt, nmap, etc. properly handle terminal width and colors.
            inner_shell = (
                f"export TERM=xterm-256color COLUMNS={self._cols} LINES={self._rows}; "
                f"exec bash -li"
            )
            cmd = shell_cmd or f'wsl -d kali-linux -- script -qc "{inner_shell}" /dev/null'
        else:
            cmd = shell_cmd or "/bin/bash"

        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        env['COLORTERM'] = 'truecolor'

        try:
            kwargs = {
                'shell': True,
                'stdin': subprocess.PIPE,
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
                'env': env,
                'bufsize': 0,
            }
            if os.name == 'nt':
                kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

            self.process = subprocess.Popen(cmd, **kwargs)
            self._alive = True
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()

            # Send initial resize after shell starts
            def _initial_resize():
                import time
                time.sleep(1.0)
                if self.process and self.process.poll() is None:
                    try:
                        resize_cmd = (
                            f"stty cols {self._cols} rows {self._rows} 2>/dev/null; "
                            f"export COLUMNS={self._cols} LINES={self._rows}\n"
                        )
                        self.process.stdin.write(resize_cmd.encode('utf-8'))
                        self.process.stdin.flush()
                    except Exception:
                        pass

            threading.Thread(target=_initial_resize, daemon=True).start()

            if self.socketio:
                self.socketio.emit('pty_ready', {})

            return True
        except Exception as e:
            if self.socketio:
                self.socketio.emit('pty_error', {'error': str(e)})
            return False

    def _read_loop(self):
        """Read output from shell and emit to frontend."""
        fd = self.process.stdout.fileno()
        while self._alive and self.process and self.process.poll() is None:
            try:
                data = os.read(fd, 4096)
                if data:
                    text = data.decode('utf-8', errors='replace')
                    # Normalize line endings: `script` inside WSL should produce
                    # proper \r\n, but ensure consistency for xterm.js.
                    # First collapse any existing \r\n to \n, then convert all \n to \r\n.
                    text = text.replace('\r\n', '\n').replace('\r', '').replace('\n', '\r\n')
                    if self.socketio:
                        self.socketio.emit('pty_output', {'data': text})
                else:
                    break
            except OSError:
                break
            except Exception:
                break

        self._alive = False
        if self.socketio:
            self.socketio.emit('pty_output', {
                'data': '\r\n\x1b[31m[PTY] Shell session ended.\x1b[0m\r\n'
            })

    def write(self, data):
        """Write data (keystrokes) to the shell stdin."""
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(data.encode('utf-8'))
                self.process.stdin.flush()
                return True
            except Exception:
                return False
        return False

    def resize(self, rows, cols):
        """
        Resize the terminal. With `script` providing a real PTY,
        stty will work correctly without ioctl errors.
        """
        self._rows = rows
        self._cols = cols
        if self.process and self.process.poll() is None:
            try:
                resize_cmd = (
                    f"stty cols {cols} rows {rows} 2>/dev/null; "
                    f"export COLUMNS={cols} LINES={rows}\n"
                )
                self.process.stdin.write(resize_cmd.encode('utf-8'))
                self.process.stdin.flush()
                return True
            except Exception:
                return False
        return False

    def kill(self):
        """Terminate the shell."""
        self._alive = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    @property
    def is_alive(self):
        return self._alive and self.process and self.process.poll() is None

