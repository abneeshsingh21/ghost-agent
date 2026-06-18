"""
GHOST v6.0 — Ethics Arbitration Engine
Pre-execution ethics check against all 4 memory layers.
Feedback integration: WRONG, CONDITIONAL, OVERRIDE, PRINCIPLE, CLASSIFICATION
"""

import re
import ipaddress
from datetime import datetime, timezone


class EthicsEngine:
    """
    The Conscience of GHOST — checks every command against the ethics framework
    before allowing execution.

    Decision flow:
    1. Check absolute rules (Layer 1) — cannot be overridden
    2. Check learned ethics rules (Layer 2) — user-taught prohibitions
    3. Check target profiles (Layer 3) — per-system authorization
    4. Check autonomy matrix — mode-based policy
    5. Return verdict: ALLOW, PROPOSE, or HALT with reason
    """

    # Payload safety filter keywords (from research doc)
    PAYLOAD_KEYWORDS = [
        "msfvenom", "meterpreter", "reverse_tcp", "reverse_http",
        "bind_tcp", "payload", "shellcode", "exploit/", "post/",
    ]

    PERSISTENCE_KEYWORDS = [
        "crontab", "registry", "autorun", "schtasks", "systemd",
        "persistence", "backdoor", "implant", "rootkit",
    ]

    PHISHING_KEYWORDS = [
        "setoolkit", "gophish", "phishing", "credential_harvest",
        "httrack", "clone", "evil_twin", "wifiphisher",
    ]

    EXFILTRATION_KEYWORDS = [
        "exfiltrate", "exfil", "data_steal", "shadow_steal",
        "compress.*upload", "zip.*send",
    ]

    DESTRUCTIVE_KEYWORDS = [
        "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
        "format c:", "del c:\\", "wipe", "shred",
        "ransomware", "cryptolocker", "encrypt.*files",
    ]

    # Database and text-dump identifiers for High-Risk permissions
    HIGH_RISK_KEYWORDS = [
        "content://sms", "content://contacts", "content://call_log",
        "dump_contacts", "dump_sms", "dump_call_log",
    ]

    # Tool-to-category mapping — full Kali arsenal
    TOOL_CATEGORIES = {
        # ── Reconnaissance ────────────────────────────────────────────
        "nmap": "reconnaissance",
        "netdiscover": "reconnaissance",
        "masscan": "reconnaissance",
        "arp-scan": "reconnaissance",
        "arp": "reconnaissance",
        "tcpdump": "reconnaissance",
        "traceroute": "reconnaissance",
        "whois": "reconnaissance",
        "dig": "reconnaissance",
        "dnsrecon": "reconnaissance",
        "whatweb": "reconnaissance",
        "nikto": "reconnaissance",
        "dirb": "reconnaissance",
        "gobuster": "reconnaissance",
        "ffuf": "reconnaissance",
        "wfuzz": "reconnaissance",
        "enum4linux": "reconnaissance",
        "wpscan": "reconnaissance",
        "nuclei": "reconnaissance",
        "sublist3r": "reconnaissance",
        "amass": "reconnaissance",
        "ip": "reconnaissance",
        "ifconfig": "reconnaissance",
        "iwconfig": "reconnaissance",
        "netstat": "reconnaissance",
        "ss": "reconnaissance",
        "lsof": "reconnaissance",
        "route": "reconnaissance",
        # ── Vulnerability Analysis ────────────────────────────────────
        "searchsploit": "vulnerability_analysis",
        "openvas": "vulnerability_analysis",
        "nessus": "vulnerability_analysis",
        # ── Exploitation ──────────────────────────────────────────────
        "msfconsole": "exploitation",
        "msfvenom": "exploitation",
        "metasploit": "exploitation",
        "sqlmap": "exploitation",
        "hydra": "exploitation",
        "bettercap": "exploitation",
        "ettercap": "exploitation",
        "nc": "exploitation",
        "netcat": "exploitation",
        "socat": "exploitation",
        # ── Post-exploitation ─────────────────────────────────────────
        "meterpreter": "post_exploitation",
        "mimikatz": "post_exploitation",
        "linpeas": "post_exploitation",
        "winpeas": "post_exploitation",
        "empire": "post_exploitation",
        "covenant": "post_exploitation",
        # ── Active Directory ──────────────────────────────────────────
        "bloodhound-python": "ad_enterprise",
        "bloodhound": "ad_enterprise",
        "crackmapexec": "ad_enterprise",
        "GetUserSPNs.py": "ad_enterprise",
        "GetNPUsers.py": "ad_enterprise",
        "secretsdump.py": "ad_enterprise",
        "psexec.py": "ad_enterprise",
        "wmiexec.py": "ad_enterprise",
        "smbexec.py": "ad_enterprise",
        "ntlmrelayx.py": "ad_enterprise",
        "ntlmrelayx": "ad_enterprise",
        "responder": "ad_enterprise",
        "ldapdomaindump": "ad_enterprise",
        "ticketer.py": "ad_enterprise",
        "dacledit.py": "ad_enterprise",
        "certipy": "ad_enterprise",
        "rpcclient": "ad_enterprise",
        "smbclient": "ad_enterprise",
        # ── Wireless ──────────────────────────────────────────────────
        "airmon-ng": "wireless",
        "airodump-ng": "wireless",
        "aireplay-ng": "wireless",
        "aircrack-ng": "wireless",
        "airbase-ng": "wireless",
        "kismet": "wireless",
        "wash": "wireless",
        "wifiphisher": "wireless",
        "hostapd-mana": "wireless",
        "hostapd": "wireless",
        "reaver": "wireless",
        "bully": "wireless",
        # ── Social Engineering ────────────────────────────────────────
        "setoolkit": "social_engineering",
        "gophish": "social_engineering",
        "httrack": "social_engineering",
        "spoofcheck.py": "social_engineering",
        "spoofcheck": "social_engineering",
        "swaks": "social_engineering",
        # ── Mobile / Android ──────────────────────────────────────────
        "adb": "mobile",
        "scrcpy": "mobile",
        "frida": "mobile",
        "drozer": "mobile",
        "apktool": "mobile",
        # ── OSINT ─────────────────────────────────────────────────────
        "sherlock": "osint",
        "theHarvester": "osint",
        "theharvester": "osint",
        "social-mapper": "osint",
        "maltego": "osint",
        "recon-ng": "osint",
        "spiderfoot": "osint",
        # ── Password Cracking ─────────────────────────────────────────
        "john": "password_cracking",
        "hashcat": "password_cracking",
        "ophcrack": "password_cracking",
        "cupp": "password_cracking",
        "cewl": "password_cracking",
        "crunch": "password_cracking",
        "hash-identifier": "password_cracking",
        "hashid": "password_cracking",
        # ── Defense ───────────────────────────────────────────────────
        "iptables": "defense",
        "ufw": "defense",
        "fail2ban": "defense",
        "fail2ban-client": "defense",
        "snort": "defense",
        "suricata": "defense",
        "ossec": "defense",
        # ── Fuzzing / Research ────────────────────────────────────────
        "afl-fuzz": "fuzzing",
        "boofuzz": "fuzzing",
    }

    def __init__(self, memory_manager):
        self.memory = memory_manager

    def check_command(self, command, target_ip=None):
        """
        Main arbitration method. Checks a proposed command against all layers.

        Returns dict:
        {
            "verdict": "ALLOW" | "PROPOSE" | "HALT",
            "reason": str,
            "rule_id": int | None,
            "layer": str,
            "category": str,
            "risk_level": str,
            "safety_flags": [],
        }
        """
        result = {
            "verdict": "ALLOW",
            "reason": "",
            "rule_id": None,
            "layer": None,
            "category": self._detect_category(command),
            "risk_level": "LOW",
            "safety_flags": [],
        }

        # ── EXCEPTION: Shadow Mode Bypass ────────────────────────────────
        is_shadow = self.memory.get_session().get("shadow_mode", False)

        # ── LAYER 1: Absolute Rules (CANNOT be overridden) ───────────────

        # Check 1: Forbidden commands
        for forbidden in self.memory.get_forbidden_commands():
            if forbidden.lower() in command.lower():
                result["verdict"] = "HALT"
                result["reason"] = f"ABSOLUTE PROHIBITION: Command matches forbidden pattern '{forbidden}'"
                result["layer"] = "absolute_rules"
                result["risk_level"] = "CRITICAL"
                return result

        # Check 2: Destructive commands
        for keyword in self.DESTRUCTIVE_KEYWORDS:
            try:
                if re.search(re.escape(keyword), command, re.IGNORECASE):
                    result["verdict"] = "HALT"
                    result["reason"] = f"SAFETY CONSTRAINT #6: Destructive/encryption command detected '{keyword}'"
                    result["layer"] = "absolute_rules"
                    result["risk_level"] = "CRITICAL"
                    result["safety_flags"].append("DESTRUCTIVE")
                    return result
            except re.error:
                # Fallback to simple string match if regex fails
                if keyword.lower() in command.lower():
                    result["verdict"] = "HALT"
                    result["reason"] = f"SAFETY CONSTRAINT #6: Destructive command detected '{keyword}'"
                    result["layer"] = "absolute_rules"
                    result["risk_level"] = "CRITICAL"
                    result["safety_flags"].append("DESTRUCTIVE")
                    return result

        # Check 3: Self-preservation
        for path in self.memory.get_self_preservation_paths():
            if path in command and any(d in command for d in ["rm ", "del ", "rmdir", "> "]):
                result["verdict"] = "HALT"
                result["reason"] = f"SAFETY CONSTRAINT #4: Self-preservation — cannot modify '{path}'"
                result["layer"] = "absolute_rules"
                result["risk_level"] = "CRITICAL"
                return result

        # Check 4: RFC1918 enforcement
        if target_ip and self.memory.is_rfc1918_enforced():
            if not self._is_rfc1918(target_ip):
                if not self.memory.has_override_token("WAN-AUTHORIZED"):
                    result["verdict"] = "HALT"
                    result["reason"] = f"SAFETY CONSTRAINT #1: Target {target_ip} is not in RFC1918 range. Requires 'WAN-AUTHORIZED' token."
                    result["layer"] = "absolute_rules"
                    result["risk_level"] = "CRITICAL"
                    result["safety_flags"].append("NON-RFC1918")
                    return result
                else:
                    self.memory.consume_override_token("WAN-AUTHORIZED")


        # Check 5: Critical infrastructure patterns
        for pattern in self.memory.get_critical_infrastructure_patterns():
            if pattern.replace("*.", "").lower() in command.lower():
                result["verdict"] = "HALT"
                result["reason"] = f"SAFETY CONSTRAINT #5: Critical infrastructure pattern detected '{pattern}'"
                result["layer"] = "absolute_rules"
                result["risk_level"] = "CRITICAL"
                result["safety_flags"].append("CRITICAL_INFRASTRUCTURE")
                return result

        # ── LAYER 2: Learned Ethics Rules ─────────────────────────────────

        # Check forbidden targets
        if target_ip and target_ip in self.memory.get_forbidden_targets():
            result["verdict"] = "HALT"
            result["reason"] = f"LEARNED RULE: Target {target_ip} is in the forbidden targets list."
            result["layer"] = "ethics_rules"
            result["risk_level"] = "HIGH"
            return result

        # Check forbidden commands (learned)
        for fc in self.memory.get_forbidden_commands_learned():
            if fc.lower() in command.lower():
                result["verdict"] = "HALT"
                result["reason"] = f"LEARNED RULE: Command matches forbidden pattern '{fc}'"
                result["layer"] = "ethics_rules"
                result["risk_level"] = "HIGH"
                return result

        # Check specific rules
        for rule in self.memory.get_ethics_rules():
            match = self._rule_matches(rule, command, target_ip)
            if match:
                if rule["type"] == "forbidden" or rule["type"] == "forbidden_class":
                    result["verdict"] = "HALT"
                    result["reason"] = f"ETHICS RULE #{rule['id']}: {rule['pattern']} is forbidden."
                    result["rule_id"] = rule["id"]
                    result["layer"] = "ethics_rules"
                    result["risk_level"] = "HIGH"
                    return result
                elif rule["type"] == "conditional":
                    result["verdict"] = "PROPOSE"
                    result["reason"] = f"ETHICS RULE #{rule['id']}: {rule['pattern']} requires condition: {rule.get('condition', 'approval')}"
                    result["rule_id"] = rule["id"]
                    result["layer"] = "ethics_rules"
                    result["risk_level"] = "MEDIUM"
                elif rule["type"] == "principle":
                    result["safety_flags"].append(f"PRINCIPLE #{rule['id']}: {rule.get('constraint', '')}")

        # ── LAYER 3: Target Profiles ──────────────────────────────────────

        if target_ip:
            profile = self.memory.get_target_profile(target_ip)
            if profile:
                # Check if target is fully prohibited
                if profile.get("authorized_level") == "NONE":
                    token = profile.get("exception_token_required")
                    if token:
                        if not self.memory.has_override_token(token):
                            result["verdict"] = "HALT"
                            result["reason"] = f"TARGET PROFILE: {target_ip} ({profile.get('alias', 'unknown')}) — Authorization level NONE. Requires token: {token}"
                            result["layer"] = "target_profiles"
                            result["risk_level"] = "HIGH"
                            return result
                        else:
                            self.memory.consume_override_token(token)


                # Check prohibited actions for this target
                prohibited = profile.get("prohibited", [])
                if "all" in prohibited:
                    result["verdict"] = "HALT"
                    result["reason"] = f"TARGET PROFILE: All actions prohibited on {target_ip}"
                    result["layer"] = "target_profiles"
                    return result

                category = result["category"]
                if category in prohibited:
                    result["verdict"] = "HALT"
                    result["reason"] = f"TARGET PROFILE: {category} is prohibited on {target_ip}"
                    result["layer"] = "target_profiles"
                    return result

                # Check auto-approve
                auto_approve = profile.get("auto_approve", [])
                if category in auto_approve:
                    result["verdict"] = "ALLOW"
                    result["reason"] = f"TARGET PROFILE: {category} auto-approved for {target_ip}"
                    result["layer"] = "target_profiles"

            # Check device class rules
            if profile and profile.get("device_class"):
                device_class = profile["device_class"]
                classes = self.memory.get_device_classes()
                class_info = classes.get(device_class, {})
                if class_info.get("default_policy") == "HALT":
                    if not class_info.get("requires_per_device_auth") or \
                       profile.get("authorized_level", "NONE") == "NONE":
                        result["verdict"] = "HALT"
                        result["reason"] = f"DEVICE CLASS: {device_class} requires explicit per-device authorization."
                        result["layer"] = "target_profiles"
                        result["risk_level"] = "HIGH"
                        result["safety_flags"].append(f"CLASS:{device_class}")
                        return result

        # ── Payload Safety Filter (from research doc) ─────────────────────

        for kw in self.PAYLOAD_KEYWORDS:
            if kw.lower() in command.lower():
                result["safety_flags"].append("PAYLOAD_DETECTED")
                if result["verdict"] == "ALLOW":
                    result["verdict"] = "PROPOSE"
                    result["reason"] = f"PAYLOAD FILTER: Payload keyword '{kw}' detected. Is this for an authorized penetration test?"
                    result["risk_level"] = "HIGH"
                break

        for kw in self.PERSISTENCE_KEYWORDS:
            if kw.lower() in command.lower():
                result["safety_flags"].append("PERSISTENCE_DETECTED")
                if result["verdict"] == "ALLOW":
                    result["verdict"] = "PROPOSE"
                    result["reason"] = f"PERSISTENCE FILTER: Persistence keyword '{kw}' detected. Self-destruct timer required."
                    result["risk_level"] = "HIGH"
                break

        for kw in self.PHISHING_KEYWORDS:
            if kw.lower() in command.lower():
                result["safety_flags"].append("PHISHING_DETECTED")
                result["verdict"] = "PROPOSE"
                result["reason"] = f"SOCIAL ENGINEERING FILTER: Phishing keyword '{kw}' detected. Strictest ethics module applies."
                result["risk_level"] = "HIGH"
                break

        for kw in self.EXFILTRATION_KEYWORDS:
            if re.search(kw, command, re.IGNORECASE):
                result["safety_flags"].append("EXFILTRATION_DETECTED")
                result["verdict"] = "HALT"
                result["reason"] = f"EXFILTRATION FILTER: Data theft pattern '{kw}' detected. Level 3 proportionality: Always Wrong unless CTF."
                result["risk_level"] = "CRITICAL"
                return result

        # ── High-Risk Permission Observer ─────────────────────────────────
        for kw in self.HIGH_RISK_KEYWORDS:
            if kw.lower() in command.lower():
                result["safety_flags"].append("HIGH_RISK_DATA_REQUEST")
                if result["verdict"] == "ALLOW":
                    result["verdict"] = "PROPOSE"
                    result["reason"] = f"HIGH-RISK PERMISSION OBSERVER: Attempting to access highly sensitive PII '{kw}'. PAUSE AND VERIFY required."
                    result["risk_level"] = "CRITICAL"
                break

        # ── Philosophical Logic Framework ─────────────────────────────────
        if self._violates_philosophical_logic(command):
            result["verdict"] = "PROPOSE"
            result["reason"] = "PHILOSOPHICAL ARBITRATION: Command violates Transparency or Impact Minimization pillars. Manual review heavily advised."
            result["risk_level"] = "HIGH"

        # ── LAYER 4: Autonomy Matrix ──────────────────────────────────────

        if result["verdict"] == "ALLOW":
            category = result["category"]
            policy = self.memory.get_autonomy_policy(category)

            if policy == "HALT":
                result["verdict"] = "HALT"
                result["reason"] = f"AUTONOMY MATRIX: {category} is set to HALT in current mode ({self.memory.get_mode()})."
                result["layer"] = "autonomy_matrix"
            elif policy == "PROPOSE":
                result["verdict"] = "PROPOSE"
                result["reason"] = f"AUTONOMY MATRIX: {category} requires approval in current mode ({self.memory.get_mode()})."
                result["layer"] = "autonomy_matrix"
            # AUTO = allow

        return result

    def _violates_philosophical_logic(self, command):
        """
        Philosophical Logic Framework: Quantifying system actions based on the pillars of 
        Transparency, Individual Rights, and Impact Minimization.
        """
        obscuration_keywords = ["nohup", "/dev/null", "base64 -d | sh", "curl -sL http"]
        return any(ok in command.lower() for ok in obscuration_keywords)

    # ── Feedback Integration ──────────────────────────────────────────────

    def rlhf_gut_instinct(self, command):
        """
        RLHF Gut Instinct.
        Intercepts overtly aggressive (Force-based) tactics like generic vulnerability flooding 
        and recommends surgically precise, elegant alternatives.
        """
        aggressive_patterns = ["nmap -p- -T5", "sqlmap --level 5", "hydra -l root -P rockyou.txt"]
        for p in aggressive_patterns:
            if p in command:
                return {
                    "intercepted": True,
                    "suggestion": f"GUT INSTINCT: '{p}' is a high-noise 'Force-based' tactic. Suggesting surgical alternative: targeted sub-domain logic or passive token harvesting instead."
                }
        return {"intercepted": False}

    def process_feedback(self, feedback_type, context, details=None):
        """
        Process user feedback to learn new rules.

        feedback_type: 'WRONG', 'CONDITIONAL', 'OVERRIDE', 'PRINCIPLE', 'CLASSIFICATION'
        context: The command/action that triggered feedback
        details: Additional info (conditions, class name, etc.)
        """
        response = {"acknowledged": False, "message": ""}

        if feedback_type == "WRONG":
            # Absolute prohibition — add to forbidden list
            rule = self.memory.add_ethics_rule(
                rule_type="forbidden",
                pattern=context.get("pattern", context.get("command", "")),
                scope="all"
            )
            # Also forbid the target if specified
            if context.get("target_ip"):
                self.memory.add_forbidden_target(
                    context["target_ip"],
                    reason=f"User feedback: WRONG (Rule #{rule['id']})"
                )
            response["acknowledged"] = True
            response["message"] = f"Rule #{rule['id']} logged: [{context.get('pattern', '')}]. Permanent prohibition. Never again."
            response["rule"] = rule

        elif feedback_type == "CONDITIONAL":
            rule = self.memory.add_ethics_rule(
                rule_type="conditional",
                pattern=context.get("pattern", ""),
                condition=details.get("condition", "explicit_approval"),
                scope=details.get("scope", "all")
            )
            response["acknowledged"] = True
            response["message"] = f"Conditional Rule #{rule['id']}: [{context.get('pattern', '')}] ALLOWED IF [{details.get('condition', '')}]."
            response["rule"] = rule

        elif feedback_type == "OVERRIDE":
            # Single-use token — session only, not persisted
            token = context.get("token", f"OVERRIDE-{datetime.now(timezone.utc).strftime('%H%M%S')}")
            self.memory.add_override_token(token)
            response["acknowledged"] = True
            response["message"] = f"Override logged for this session. Token: {token}. Not permanent."

        elif feedback_type == "PRINCIPLE":
            rule = self.memory.add_ethics_rule(
                rule_type="principle",
                pattern=context.get("pattern", ""),
                constraint=details.get("constraint", ""),
                inheritance="class"
            )
            response["acknowledged"] = True
            response["message"] = f"Principle #{rule['id']} derived: [{details.get('constraint', '')}]. Will match on [{context.get('pattern', '')}]."
            response["rule"] = rule

        elif feedback_type == "CLASSIFICATION":
            # Tag target with device class
            target_ip = context.get("target_ip", "")
            device_class = details.get("class", "unknown")
            profile = self.memory.classify_target(target_ip, device_class)

            # Get inherited rules
            classes = self.memory.get_device_classes()
            class_info = classes.get(device_class, {})
            inherited = class_info.get("default_policy", "UNKNOWN")

            response["acknowledged"] = True
            response["message"] = f"Classified {target_ip} as [{device_class}]. Inherited policy: {inherited}."
            response["profile"] = profile

        return response

    # ── Helpers ────────────────────────────────────────────────────────────

    def _detect_category(self, command):
        """Detect the category of a command based on the tool being used."""
        cmd_lower = command.strip().lower()
        # Extract the tool name (first word or known tool)
        for tool, category in self.TOOL_CATEGORIES.items():
            if tool.lower() in cmd_lower:
                return category
        # Default heuristics
        if any(kw in cmd_lower for kw in ["scan", "nmap", "discover", "recon"]):
            return "reconnaissance"
        if any(kw in cmd_lower for kw in ["exploit", "payload", "msf"]):
            return "exploitation"
        if any(kw in cmd_lower for kw in ["crack", "hash", "brute"]):
            return "password_cracking"
        return "general"

    def _is_rfc1918(self, ip_str):
        """Check if an IP address is in RFC1918 private range."""
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_private
        except ValueError:
            # Could be a hostname — allow it (DNS resolution would be needed)
            return True

    def _rule_matches(self, rule, command, target_ip=None):
        """Check if an ethics rule matches the given command/target."""
        pattern = rule.get("pattern", "").lower()
        cmd_lower = command.lower()

        # Direct pattern match
        if pattern in cmd_lower:
            return True

        # Category match
        category = self._detect_category(command)
        if pattern == category:
            return True

        # Target class match
        if target_ip:
            profile = self.memory.get_target_profile(target_ip)
            if profile and profile.get("device_class", "").lower() == pattern:
                return True

        return False

    def get_gateway_ip(self):
        """Get the default gateway IP (for auto-protection)."""
        # This will be populated by the discovery engine at runtime
        session = self.memory.get_session()
        return session.get("gateway_ip", None)

    def format_verdict(self, result):
        """Format an ethics verdict for display."""
        icons = {
            "ALLOW": "✅",
            "PROPOSE": "⚠️",
            "HALT": "🛑",
        }
        icon = icons.get(result["verdict"], "❓")

        lines = [
            f"{icon} ETHICS VERDICT: {result['verdict']}",
            f"   Category: {result['category']}",
            f"   Risk Level: {result['risk_level']}",
            f"   Reason: {result['reason']}",
        ]
        if result.get("rule_id"):
            lines.append(f"   Rule ID: #{result['rule_id']}")
        if result.get("layer"):
            lines.append(f"   Layer: {result['layer']}")
        if result.get("safety_flags"):
            lines.append(f"   Flags: {', '.join(result['safety_flags'])}")

        return "\n".join(lines)
