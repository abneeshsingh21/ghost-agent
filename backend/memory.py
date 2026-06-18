"""
GHOST v6.0 — 4-Layer Memory Manager
Manages: absolute_rules, ethics_rules, target_profiles, session_context
"""

import json
import os
import hashlib
from datetime import datetime, timezone


class MemoryManager:
    """Four-layer persistent memory system for GHOST v6.0."""

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.memory_dir = os.path.join(base_dir, "memory")
        self.config_dir = os.path.join(base_dir, "config")
        self.logs_dir = os.path.join(base_dir, "logs")
        self.tmp_dir = os.path.join(base_dir, "tmp")

        # Ensure directories exist
        for d in [self.memory_dir, self.config_dir, self.logs_dir, self.tmp_dir]:
            os.makedirs(d, exist_ok=True)

        # Layer paths
        self.paths = {
            "absolute_rules": os.path.join(self.memory_dir, "absolute_rules.json"),
            "ethics_rules": os.path.join(self.memory_dir, "ethics_rules.json"),
            "target_profiles": os.path.join(self.memory_dir, "target_profiles.json"),
            "session_context": os.path.join(self.tmp_dir, "session_context.json"),
            "autonomy_matrix": os.path.join(self.config_dir, "autonomy_matrix.json"),
            "authorized_bssids": os.path.join(self.config_dir, "authorized_bssids.json"),
        }

        # Load all layers
        self.absolute_rules = self._load_json(self.paths["absolute_rules"])
        self.ethics_rules = self._load_json(self.paths["ethics_rules"])
        self.target_profiles = self._load_json(self.paths["target_profiles"])
        self.autonomy_matrix = self._load_json(self.paths["autonomy_matrix"])
        self.authorized_bssids = self._load_json(self.paths["authorized_bssids"])

        # Initialize session context (volatile — resets on startup)
        self.session_context = self._init_session()
        self._save_json(self.paths["session_context"], self.session_context)

        # Audit log
        self.audit_log_path = os.path.join(self.logs_dir, "ethics_decisions.log")

    # ── Loaders ──────────────────────────────────────────────────────────

    def _load_json(self, path):
        """Load a JSON file, return empty dict if not found."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_json(self, path, data):
        """Save data to JSON file with pretty formatting."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _init_session(self):
        """Create a fresh session context (Layer 4 — volatile)."""
        return {
            "session_id": hashlib.md5(
                datetime.now(timezone.utc).isoformat().encode()
            ).hexdigest()[:12],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "mode": "TEACHING",
            "stealth": False,
            "chain_active": None,
            "chain_phase": None,
            "pivots": [],
            "shells": [],
            "credentials_found": [],
            "override_tokens": [],
            "discovered_hosts": [],
            "command_history": [],
        }

    # ── Layer 1: Absolute Rules (READ-ONLY) ──────────────────────────────

    def get_forbidden_commands(self):
        """Get list of globally forbidden commands."""
        return self.absolute_rules.get("global_forbidden_commands", [])

    def get_rfc1918_ranges(self):
        """Get allowed private network ranges."""
        nb = self.absolute_rules.get("network_boundaries", {})
        return nb.get("rfc1918_ranges", ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"])

    def is_rfc1918_enforced(self):
        """Check if RFC1918 enforcement is active."""
        nb = self.absolute_rules.get("network_boundaries", {})
        return nb.get("allow_rfc1918", True) and not nb.get("allow_internet", False)

    def get_critical_infrastructure_patterns(self):
        """Get patterns for critical infrastructure detection."""
        return self.absolute_rules.get("critical_infrastructure_patterns", [])

    def get_self_preservation_paths(self):
        """Get paths that must never be deleted."""
        return self.absolute_rules.get("self_preservation_paths", [])

    def get_safety_constraints(self):
        """Get all 7 safety constraints."""
        return self.absolute_rules.get("safety_constraints", {})

    def get_proportionality_levels(self):
        """Get the 4-level proportionality system."""
        return self.absolute_rules.get("proportionality_levels", {})

    # ── Layer 2: Learned Ethics (READ/WRITE) ──────────────────────────────

    def get_ethics_rules(self):
        """Get all learned ethics rules."""
        return self.ethics_rules.get("rules", [])

    def get_forbidden_targets(self):
        """Get list of forbidden target IPs/hostnames."""
        return self.ethics_rules.get("forbidden_targets", [])

    def get_forbidden_commands_learned(self):
        """Get list of forbidden commands from learned rules."""
        return self.ethics_rules.get("forbidden_commands", [])

    def get_pillars(self):
        """Get the 3 ethical pillars."""
        return self.ethics_rules.get("pillars", {})

    def add_ethics_rule(self, rule_type, pattern, condition=None, scope=None,
                        exception=None, constraint=None, inheritance=None):
        """
        Add a new learned ethics rule.
        Types: 'forbidden', 'conditional', 'forbidden_class', 'principle'
        """
        rule_id = self.ethics_rules.get("next_rule_id", 1)
        rule = {
            "id": rule_id,
            "type": rule_type,
            "pattern": pattern,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        if condition:
            rule["condition"] = condition
        if scope:
            rule["scope"] = scope
        if exception:
            rule["exception"] = exception
        if constraint:
            rule["constraint"] = constraint
        if inheritance:
            rule["inheritance"] = inheritance

        if "rules" not in self.ethics_rules:
            self.ethics_rules["rules"] = []
        self.ethics_rules["rules"].append(rule)
        self.ethics_rules["next_rule_id"] = rule_id + 1

        self._save_json(self.paths["ethics_rules"], self.ethics_rules)
        self._audit_log(f"RULE_ADDED", f"Rule #{rule_id}: [{rule_type}] {pattern}")

        return rule

    def add_forbidden_target(self, target, reason="User feedback"):
        """Add a target IP/hostname to the forbidden list."""
        if "forbidden_targets" not in self.ethics_rules:
            self.ethics_rules["forbidden_targets"] = []
        if target not in self.ethics_rules["forbidden_targets"]:
            self.ethics_rules["forbidden_targets"].append(target)
            self._save_json(self.paths["ethics_rules"], self.ethics_rules)
            self._audit_log("TARGET_FORBIDDEN", f"{target} — Reason: {reason}")
        return True

    def add_forbidden_command(self, command, reason="User feedback"):
        """Add a command to the forbidden list."""
        if "forbidden_commands" not in self.ethics_rules:
            self.ethics_rules["forbidden_commands"] = []
        if command not in self.ethics_rules["forbidden_commands"]:
            self.ethics_rules["forbidden_commands"].append(command)
            self._save_json(self.paths["ethics_rules"], self.ethics_rules)
            self._audit_log("COMMAND_FORBIDDEN", f"{command} — Reason: {reason}")
        return True

    # ── Layer 3: Target Profiles (READ/WRITE) ─────────────────────────────

    def get_target_profile(self, ip):
        """Get profile for a specific target IP."""
        targets = self.target_profiles.get("targets", {})
        return targets.get(ip, None)

    def get_all_targets(self):
        """Get all target profiles."""
        return self.target_profiles.get("targets", {})

    def get_device_classes(self):
        """Get device classification rules."""
        return self.target_profiles.get("device_classes", {})

    def set_target_profile(self, ip, alias=None, os_info=None, authorized_level="NONE",
                           auto_approve=None, prohibited=None, notes=None,
                           device_class=None, exception_token=None):
        """Create or update a target profile."""
        if "targets" not in self.target_profiles:
            self.target_profiles["targets"] = {}

        profile = self.target_profiles["targets"].get(ip, {})
        if alias:
            profile["alias"] = alias
        if os_info:
            profile["os"] = os_info
        profile["authorized_level"] = authorized_level
        if auto_approve is not None:
            profile["auto_approve"] = auto_approve
        if prohibited is not None:
            profile["prohibited"] = prohibited
        if notes:
            profile["notes"] = notes
        if device_class:
            profile["device_class"] = device_class
        if exception_token:
            profile["exception_token_required"] = exception_token
        profile["last_updated"] = datetime.now(timezone.utc).isoformat()

        self.target_profiles["targets"][ip] = profile
        self._save_json(self.paths["target_profiles"], self.target_profiles)
        self._audit_log("TARGET_PROFILE", f"{ip} — Level: {authorized_level}")

        return profile

    def classify_target(self, ip, device_class, inherit_rules=True):
        """Classify a target by device class and inherit class rules."""
        classes = self.get_device_classes()
        class_info = classes.get(device_class, {})

        profile = self.get_target_profile(ip) or {}
        profile["device_class"] = device_class

        if inherit_rules and class_info:
            if class_info.get("default_policy") == "HALT":
                profile["authorized_level"] = "NONE"
            if class_info.get("auto_protected"):
                if "prohibited" not in profile:
                    profile["prohibited"] = []
                profile["prohibited"].append("all")

        if "targets" not in self.target_profiles:
            self.target_profiles["targets"] = {}
        self.target_profiles["targets"][ip] = profile
        self._save_json(self.paths["target_profiles"], self.target_profiles)

        self._audit_log("TARGET_CLASSIFIED",
                        f"{ip} → {device_class} (inherited: {inherit_rules})")
        return profile

    # ── Layer 4: Session Context (VOLATILE) ───────────────────────────────

    def get_session(self):
        """Get current session context."""
        return self.session_context

    def get_mode(self):
        """Get current operational mode."""
        return self.session_context.get("mode", "TEACHING")

    def set_mode(self, mode):
        """Set operational mode."""
        valid = ["TEACHING", "SUPERVISED", "AUTONOMOUS", "STEALTH"]
        if mode.upper() not in valid:
            return False
        self.session_context["mode"] = mode.upper()
        self._save_json(self.paths["session_context"], self.session_context)
        self._audit_log("MODE_CHANGE", f"Mode set to {mode.upper()}")
        return True

    def set_stealth(self, enabled):
        """Toggle stealth mode."""
        self.session_context["stealth"] = bool(enabled)
        self._save_json(self.paths["session_context"], self.session_context)
        return True

    def add_override_token(self, token):
        """Add a single-use override token to session (stored as SHA256 hash)."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.session_context["override_tokens"].append({
            "token_hash": token_hash,
            "created": datetime.now(timezone.utc).isoformat(),
            "used": False,
        })
        self._save_json(self.paths["session_context"], self.session_context)
        self._audit_log("OVERRIDE_TOKEN", f"Token added (hash): {token_hash[:8]}...")
        return True


    def has_override_token(self, token):
        """Check if an override token exists and hasn't been used."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        for t in self.session_context.get("override_tokens", []):
            if t.get("token_hash") == token_hash and not t["used"]:
                return True
        return False


    def consume_override_token(self, token):
        """Use and consume an override token atomically."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        for t in self.session_context.get("override_tokens", []):
            if t.get("token_hash") == token_hash and not t["used"]:
                t["used"] = True
                t["used_at"] = datetime.now(timezone.utc).isoformat()
                self._save_json(self.paths["session_context"], self.session_context)
                self._audit_log("OVERRIDE_USED", f"Token consumed (hash): {token_hash[:8]}...")
                return True
        return False


    def set_active_chain(self, chain_name, phase=1):
        """Set the currently active operation chain."""
        self.session_context["chain_active"] = chain_name
        self.session_context["chain_phase"] = phase
        self._save_json(self.paths["session_context"], self.session_context)
        return True

    def add_shell(self, shell_type, target, pid=None):
        """Register an active shell session."""
        shell = {
            "type": shell_type,
            "target": target,
            "pid": pid,
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }
        self.session_context["shells"].append(shell)
        self._save_json(self.paths["session_context"], self.session_context)
        return shell

    def add_credential(self, service, user, password_hash=None, source=None):
        """Log a discovered credential."""
        cred = {
            "service": service,
            "user": user,
            "hash": password_hash,
            "source": source,
            "found_at": datetime.now(timezone.utc).isoformat(),
        }
        self.session_context["credentials_found"].append(cred)
        self._save_json(self.paths["session_context"], self.session_context)
        self._audit_log("CREDENTIAL_FOUND", f"{service}:{user} from {source}")
        return cred

    def add_discovered_host(self, ip, hostname=None, os_info=None, ports=None,
                            risk_flags=None):
        """Add a discovered host from reconnaissance."""
        host = {
            "ip": ip,
            "hostname": hostname,
            "os": os_info,
            "ports": ports or [],
            "risk_flags": risk_flags or [],
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        # Update if already exists
        existing = [h for h in self.session_context["discovered_hosts"] if h["ip"] == ip]
        if existing:
            idx = self.session_context["discovered_hosts"].index(existing[0])
            self.session_context["discovered_hosts"][idx] = host
        else:
            self.session_context["discovered_hosts"].append(host)

        self._save_json(self.paths["session_context"], self.session_context)
        return host

    def add_pivot(self, via_ip, to_subnet):
        """Register a pivot opportunity."""
        pivot = {
            "via": via_ip,
            "to": to_subnet,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        self.session_context["pivots"].append(pivot)
        self._save_json(self.paths["session_context"], self.session_context)
        self._audit_log("PIVOT_DISCOVERED", f"via {via_ip} → {to_subnet}")
        return pivot

    def log_command(self, category, tool, arguments, metadata=None):
        """Log a command to session history."""
        entry = {
            "category": category,
            "tool": tool,
            "arguments": arguments,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.session_context["command_history"].append(entry)
        self._save_json(self.paths["session_context"], self.session_context)

        # Also append to persistent command log
        log_path = os.path.join(self.logs_dir, "command_history.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{entry['timestamp']}] [{category}] {tool} {arguments}\n")

        return entry

    # ── Autonomy Matrix ───────────────────────────────────────────────────

    def get_autonomy_policy(self, category, subcategory=None):
        """
        Get the autonomy policy for a given action category.
        Returns: 'AUTO', 'PROPOSE', or 'HALT'
        """
        mode = self.get_mode()
        modes = self.autonomy_matrix.get("modes", {})

        if mode == "TEACHING":
            return "PROPOSE"

        mode_config = modes.get(mode, {})

        if mode == "AUTONOMOUS":
            return mode_config.get("global_policy", "AUTO")

        if mode == "STEALTH":
            return "AUTO"  # Stealth auto-executes but with timing constraints

        # SUPERVISED mode — per-category
        categories = mode_config.get("categories", {})
        cat_policy = categories.get(category, "PROPOSE")

        if isinstance(cat_policy, dict) and subcategory:
            return cat_policy.get(subcategory, "PROPOSE").upper()
        elif isinstance(cat_policy, str):
            return cat_policy.upper()

        return "PROPOSE"

    def get_stealth_config(self):
        """Get stealth mode configuration."""
        modes = self.autonomy_matrix.get("modes", {})
        return modes.get("STEALTH", {})

    # ── BSSID Authorization ───────────────────────────────────────────────

    def is_bssid_authorized(self, bssid):
        """Check if a wireless BSSID is in the authorized list."""
        authorized = self.authorized_bssids.get("authorized", [])
        return bssid.upper() in [b.upper() for b in authorized]

    # ── Audit Logging ─────────────────────────────────────────────────────

    def _audit_log(self, event_type, message):
        """Append an immutable audit log entry."""
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] [{event_type}] {message}"

        # Hash the entry for integrity
        entry_hash = hashlib.sha256(entry.encode()).hexdigest()[:16]
        full_entry = f"{entry} [HASH:{entry_hash}]"

        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(full_entry + "\n")

    # ── Full State Export ─────────────────────────────────────────────────

    def get_full_status(self):
        """Get complete memory state for status display."""
        return {
            "absolute_rules_count": len(self.absolute_rules.get("safety_constraints", {})),
            "learned_ethics_count": len(self.ethics_rules.get("rules", [])),
            "forbidden_targets_count": len(self.ethics_rules.get("forbidden_targets", [])),
            "target_profiles_count": len(self.target_profiles.get("targets", {})),
            "session": {
                "id": self.session_context.get("session_id"),
                "mode": self.session_context.get("mode"),
                "stealth": self.session_context.get("stealth"),
                "chain_active": self.session_context.get("chain_active"),
                "shells_count": len(self.session_context.get("shells", [])),
                "credentials_count": len(self.session_context.get("credentials_found", [])),
                "discovered_hosts_count": len(self.session_context.get("discovered_hosts", [])),
                "commands_executed": len(self.session_context.get("command_history", [])),
            },
            "pillars": self.get_pillars(),
        }
