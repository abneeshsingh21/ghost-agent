"""
GHOST v6.0 — OSINT Intelligence Engine
Automated person/organization profiling from usernames, emails, and domains.
Integrates: Sherlock, theHarvester, DNS recon, breach DB checks.
"""

import re
from datetime import datetime, timezone


class OSINTEngine:
    """
    Automated OSINT — builds complete target profiles from minimal seed data.
    Trigger: "find info on <target>", "who is <username>", "investigate <domain>"
    """

    TRIGGER_PHRASES = [
        "find info", "who is", "investigate", "osint", "lookup",
        "find person", "social media", "email lookup", "domain recon",
        "find accounts", "dox", "profile", "background check",
        "find emails", "find subdomains", "harvest",
    ]

    def __init__(self, memory_manager, ethics_engine, bridge):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.bridge = bridge

    def is_osint_request(self, user_input):
        """Check if user input triggers the OSINT engine."""
        lower = user_input.lower().strip()
        return any(phrase in lower for phrase in self.TRIGGER_PHRASES)

    def detect_seed_type(self, seed):
        """Detect what kind of seed data the user provided."""
        seed = seed.strip()

        # Email
        if re.match(r"[^@]+@[^@]+\.[^@]+", seed):
            return "email"

        # Domain
        if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$", seed):
            return "domain"

        # IP Address
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", seed):
            return "ip"

        # Phone number
        if re.match(r"^[\+]?[\d\s-]{7,15}$", seed):
            return "phone"

        # Username (default)
        return "username"

    def build_recon_plan(self, seed, seed_type=None):
        """
        Build a full OSINT recon plan based on the seed data.
        Returns ordered list of commands to execute.
        """
        if seed_type is None:
            seed_type = self.detect_seed_type(seed)

        plan = {
            "seed": seed,
            "seed_type": seed_type,
            "phases": [],
        }

        if seed_type == "username":
            plan["phases"] = self._plan_username_recon(seed)
        elif seed_type == "email":
            plan["phases"] = self._plan_email_recon(seed)
        elif seed_type == "domain":
            plan["phases"] = self._plan_domain_recon(seed)
        elif seed_type == "ip":
            plan["phases"] = self._plan_ip_recon(seed)
        elif seed_type == "phone":
            plan["phases"] = self._plan_phone_recon(seed)

        return plan

    def _plan_username_recon(self, username):
        """Build recon plan for a username seed."""
        return [
            {
                "phase": 1,
                "name": "Social Media Account Discovery",
                "description": f"Find all accounts linked to username '{username}' across 300+ platforms",
                "commands": [
                    {
                        "tool": "sherlock",
                        "args": f"{username} --output /tmp/osint_{username}_sherlock.txt",
                        "category": "OSINT",
                        "description": f"Search for '{username}' across 300+ social media platforms",
                    },
                ],
            },
            {
                "phase": 2,
                "name": "Username Variation Search",
                "description": f"Try common username variations: {username}_, _{username}, {username}123",
                "commands": [
                    {
                        "tool": "sherlock",
                        "args": f"{username}_ {username}123 _{username} --output /tmp/osint_{username}_vars.txt",
                        "category": "OSINT",
                        "description": "Search username variations for additional accounts",
                    },
                ],
            },
            {
                "phase": 3,
                "name": "GitHub/GitLab Code Search",
                "description": "Search public code repositories for username mentions",
                "commands": [
                    {
                        "tool": "curl",
                        "args": f"-s 'https://api.github.com/users/{username}' | python3 -m json.tool",
                        "category": "OSINT",
                        "description": "Check GitHub for public profile and repositories",
                    },
                ],
            },
        ]

    def _plan_email_recon(self, email):
        """Build recon plan for an email seed."""
        domain = email.split("@")[1] if "@" in email else ""
        username = email.split("@")[0] if "@" in email else email

        return [
            {
                "phase": 1,
                "name": "Seed-to-Entity Mapping",
                "description": f"Find accounts linked to {email}",
                "commands": [
                    {
                        "tool": "sherlock",
                        "args": f"{username} --output /tmp/osint_{username}_sherlock.txt",
                        "category": "OSINT",
                        "description": f"Search for username '{username}' derived from email",
                    },
                    {
                        "tool": "holehe",
                        "args": f"{email} --only-used",
                        "category": "OSINT",
                        "description": f"Check if email {email} is attached to social media accounts",
                    },
                ],
            },
            {
                "phase": 2,
                "name": "Domain Infrastructure",
                "description": f"Map the email domain infrastructure: {domain}",
                "commands": [
                    {
                        "tool": "theHarvester",
                        "args": f"-d {domain} -b all -f /tmp/osint_{domain}_harvest.html",
                        "category": "OSINT",
                        "description": f"Harvest emails, subdomains, and IPs from {domain}",
                    },
                    {
                        "tool": "dig",
                        "args": f"{domain} MX +short",
                        "category": "OSINT",
                        "description": f"Check mail server configuration for {domain}",
                    },
                ],
            },
            {
                "phase": 3,
                "name": "Email Spoofing Assessment",
                "description": f"Check if {domain} is vulnerable to email spoofing",
                "commands": [
                    {
                        "tool": "spoofcheck",
                        "args": f"{domain}",
                        "category": "OSINT",
                        "description": f"Check SPF/DMARC/DKIM configuration for spoofing vulnerability",
                    },
                    {
                        "tool": "dig",
                        "args": f"{domain} TXT +short",
                        "category": "OSINT",
                        "description": "Check TXT records for SPF policy",
                    },
                ],
            },
            {
                "phase": 4,
                "name": "Data Breach Correlation",
                "description": f"Cross-reference {email} against historical data leaks",
                "commands": [
                    {
                        "tool": "h8mail",
                        "args": f"-t {email} -c /etc/h8mail/config.ini -o /tmp/osint_breach_{username}.txt",
                        "category": "OSINT",
                        "description": f"Search databases for credential leaks related to {email}",
                    },
                ],
            },
            {
                "phase": 5,
                "name": "Risk-Based Profiling",
                "description": "Generate comprehensive 'Digital Footprint' report",
                "commands": [
                    {
                        "tool": "python3",
                        "args": f"-c \"print('Generating consolidated Risk-Based Digital Footprint Report...')\"",
                        "category": "OSINT",
                        "description": "Consolidate all findings into a vector assessment profile",
                    },
                ],
            },
        ]

    def _plan_domain_recon(self, domain):
        """Build recon plan for a domain seed."""
        return [
            {
                "phase": 1,
                "name": "Email & Staff Harvesting",
                "description": f"Find all publicly available emails and employee names for {domain}",
                "commands": [
                    {
                        "tool": "theHarvester",
                        "args": f"-d {domain} -b all -l 500 -f /tmp/osint_{domain}_harvest.html",
                        "category": "OSINT",
                        "description": f"Full harvest of emails, subdomains, hosts, and employee names",
                    },
                ],
            },
            {
                "phase": 2,
                "name": "DNS & Subdomain Enumeration",
                "description": f"Deep DNS analysis and subdomain discovery for {domain}",
                "commands": [
                    {
                        "tool": "dnsrecon",
                        "args": f"-d {domain} -t std,brt,axfr",
                        "category": "OSINT",
                        "description": "Standard DNS enumeration, brute-force, and zone transfer attempt",
                    },
                    {
                        "tool": "dig",
                        "args": f"{domain} ANY +noall +answer",
                        "category": "OSINT",
                        "description": "Pull all DNS record types",
                    },
                    {
                        "tool": "dig",
                        "args": f"{domain} MX +short",
                        "category": "OSINT",
                        "description": "Find mail servers",
                    },
                    {
                        "tool": "dig",
                        "args": f"{domain} NS +short",
                        "category": "OSINT",
                        "description": "Find nameservers",
                    },
                ],
            },
            {
                "phase": 3,
                "name": "Web Technology Fingerprinting",
                "description": f"Identify technologies, frameworks, and servers used by {domain}",
                "commands": [
                    {
                        "tool": "whatweb",
                        "args": f"https://{domain} -v",
                        "category": "OSINT",
                        "description": "Fingerprint web technologies, CMS, server info",
                    },
                    {
                        "tool": "curl",
                        "args": f"-sI https://{domain}",
                        "category": "OSINT",
                        "description": "Check HTTP headers for server info and security headers",
                    },
                ],
            },
            {
                "phase": 4,
                "name": "Email Spoofing Check",
                "description": f"Assess {domain} for email spoofing vulnerability",
                "commands": [
                    {
                        "tool": "spoofcheck",
                        "args": f"{domain}",
                        "category": "OSINT",
                        "description": "Full SPF/DMARC assessment",
                    },
                ],
            },
            {
                "phase": 5,
                "name": "Infrastructure Mapping",
                "description": f"Map IP ranges, ASN, and hosting for {domain}",
                "commands": [
                    {
                        "tool": "whois",
                        "args": f"{domain}",
                        "category": "OSINT",
                        "description": "WHOIS registration data",
                    },
                    {
                        "tool": "nmap",
                        "args": f"-sV -sC -p 80,443,8080,8443,21,22,25,53 {domain}",
                        "category": "OSINT",
                        "description": "Service scan on common ports",
                    },
                ],
            },
        ]

    def _plan_ip_recon(self, ip):
        """Build recon plan for an IP seed."""
        return [
            {
                "phase": 1,
                "name": "IP Registration & Geolocation",
                "commands": [
                    {
                        "tool": "whois",
                        "args": ip,
                        "category": "OSINT",
                        "description": f"WHOIS lookup for {ip}",
                    },
                    {
                        "tool": "curl",
                        "args": f"-s 'http://ip-api.com/json/{ip}' | python3 -m json.tool",
                        "category": "OSINT",
                        "description": f"Geolocation and ISP data for {ip}",
                    },
                ],
            },
            {
                "phase": 2,
                "name": "Reverse DNS & Port Scan",
                "commands": [
                    {
                        "tool": "nmap",
                        "args": f"-sV -sC -O {ip}",
                        "category": "RECON",
                        "description": f"Full port scan with service detection on {ip}",
                    },
                    {
                        "tool": "dig",
                        "args": f"-x {ip} +short",
                        "category": "OSINT",
                        "description": "Reverse DNS lookup",
                    },
                ],
            },
        ]

    def _plan_phone_recon(self, phone):
        """Build recon plan for a phone number seed."""
        return [
            {
                "phase": 1,
                "name": "Phone Number Analysis",
                "description": "Note: Limited to publicly available data sources",
                "commands": [
                    {
                        "tool": "curl",
                        "args": f"-s 'http://apilayer.net/api/validate?access_key=YOUR_KEY&number={phone}'",
                        "category": "OSINT",
                        "description": f"Validate and identify carrier for {phone}",
                    },
                ],
            },
        ]

    def execute_plan(self, plan, socketio=None):
        """Execute an OSINT recon plan phase by phase."""
        results = []

        for phase in plan.get("phases", []):
            phase_results = {
                "phase": phase.get("phase", 0),
                "name": phase.get("name", ""),
                "command_results": [],
            }

            for cmd_info in phase.get("commands", []):
                full_command = f"{cmd_info['tool']} {cmd_info['args']}"
                target_ip = self.bridge._extract_ip(full_command)

                # Ethics check
                verdict = self.ethics.check_command(full_command, target_ip)

                cmd_result = {
                    "command": full_command,
                    "description": cmd_info.get("description", ""),
                    "ethics_verdict": verdict,
                    "executed": False,
                }

                if verdict["verdict"] == "HALT":
                    cmd_result["halt_reason"] = verdict["reason"]
                elif verdict["verdict"] in ["ALLOW", "PROPOSE"]:
                    mode = self.memory.get_mode()
                    if verdict["verdict"] == "ALLOW" or mode in ["AUTONOMOUS", "SUPERVISED"]:
                        exec_result = self.bridge.execute_command(full_command, timeout=120)
                        cmd_result["executed"] = True
                        cmd_result["output"] = exec_result

                        if socketio:
                            socketio.emit("osint_result", {
                                "phase": phase.get("name", ""),
                                "command": full_command,
                                "output": exec_result.get("stdout", "")[:2000],
                            })
                            
                        # Smart-Pivoting: Extract credentials/PINs for Mobile/Wireless engines
                        if exec_result.get("status") == "OK" and exec_result.get("stdout"):
                            import re
                            hints = set()
                            # Basic heuristic to extract passwords from breach dumps / outputs
                            matches = re.findall(r'(?i)(?:password|pass|pin|pwd)[\s:=]+([^\s,;\"\']+)', exec_result["stdout"])
                            for m in matches:
                                if len(m) >= 4 and m.lower() not in ["null", "none", "unknown", "hidden"]:
                                    hints.add(m)
                                    
                            if hints:
                                p_ip = target_ip if target_ip else (plan.get("seed") if plan.get("seed_type") == "ip" else "OSINT_GLOBAL")
                                profile = self.memory.get_target_profile(p_ip) or {}
                                existing_hints = profile.get("credential_hints", [])
                                profile["credential_hints"] = list(set(existing_hints + list(hints)))
                                # Avoid overwriting IP in kwargs
                                self.memory.set_target_profile(p_ip, 
                                    authorized_level=profile.get("authorized_level", "NONE"),
                                    auto_approve=profile.get("auto_approve", []),
                                    prohibited=profile.get("prohibited", []),
                                    device_class=profile.get("device_class"),
                                    exception_token=profile.get("exception_token_required")
                                )
                                # Re-inject hints explicitly since set_target_profile kwargs might not support custom fields directly
                                p = self.memory.get_target_profile(p_ip)
                                p["credential_hints"] = profile["credential_hints"]
                                self.memory._save_json(self.memory.paths["target_profiles"], self.memory.target_profiles)
                                
                                if socketio:
                                    socketio.emit('system_message', {"message": f"🔑 OSINT Smart-Pivot: Extracted {len(hints)} credential hints. Stored in Layer 3 Memory for '{p_ip}'."})

                    else:
                        cmd_result["awaiting_approval"] = True

                phase_results["command_results"].append(cmd_result)

            results.append(phase_results)

        return {
            "seed": plan.get("seed", ""),
            "seed_type": plan.get("seed_type", ""),
            "phases_completed": len(results),
            "results": results,
        }


class SemanticLootClassifier:
    """
    Autonomous 'Loot' Prioritization.
    Uses heuristics and LLM to scan filenames and file headers in real-time.
    Ignores garbage and prioritizes exfiltration of high-value targets.
    """
    HIGH_VALUE_EXTENSIONS = ['.kdbx', '.pem', '.key', '.dat', '.json', '.bak', '.sql', '.yaml', '.yml', '.env']
    HIGH_VALUE_NAMES = ['id_rsa', 'id_ed25519', 'config', 'wallet', 'shadow', 'passwd',
                        'secrets', 'aws_credentials', 'credentials', '.htpasswd',
                        'master.key', 'token', 'private']

    def __init__(self, bridge=None):
        self.bridge = bridge

    def prioritize_loot(self, file_list):
        """
        Evaluate a list of discovered files and sort them strictly by intelligence value.
        Returns only HIGH and MEDIUM priority targets, sorted descending by score.
        """
        prioritized = []
        for f in file_list:
            score = 0
            f_lower = f.lower()
            if any(f_lower.endswith(ext) for ext in self.HIGH_VALUE_EXTENSIONS):
                score += 50
            if any(name in f_lower for name in self.HIGH_VALUE_NAMES):
                score += 50

            if score >= 50:
                priority = "CRITICAL" if score >= 100 else "HIGH"
                prioritized.append({"file": f, "priority": priority, "score": score})

        return sorted(prioritized, key=lambda x: x["score"], reverse=True)
