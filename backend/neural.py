"""
GHOST v6.0 — Neural Brain: Tactical Memory (Hippocampus)
ChromaDB-backed vector memory for cross-session intelligence accumulation.

Architecture:
    ┌─────────────────────────────────────────────────┐
    │              NEURAL BRAIN                       │
    │                                                 │
    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
    │  │Operations│  │Topology  │  │Attack Paths  │  │
    │  │(ChromaDB)│  │(ChromaDB)│  │(ChromaDB)    │  │
    │  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
    │       │             │               │           │
    │       └─────────────┼───────────────┘           │
    │                     │                           │
    │              ┌──────┴──────┐                    │
    │              │ Reflex Loop │                    │
    │              │  (< 50ms)   │                    │
    │              └──────┬──────┘                    │
    │                     │                           │
    │              ┌──────┴──────┐                    │
    │              │  Dopamine   │                    │
    │              │  (RL Loop)  │                    │
    │              └─────────────┘                    │
    └─────────────────────────────────────────────────┘

Tier 1: Tactical Memory — "Have I seen this before?"
Tier 3: Dopamine Loop  — success_weight reinforcement
"""

import os
import re
import json
import time
import logging
import hashlib
from datetime import datetime, timezone

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

logger = logging.getLogger("ghost.neural")


class TacticalMemory:
    """
    The Hippocampus — ChromaDB-backed persistent vector memory.

    Three collections:
        operations   — Every successful command execution + context
        topology     — Network topology snapshots (hosts, ports, OS)
        attack_paths — Proven attack chains with success_weight scores

    Reflex Loop:
        Before querying the LLM, the bot checks:
            "Have I hacked a target with these open ports / OS before?"
        If yes → execute the proven Reflex Command (Zero Latency).

    Dopamine Loop:
        reward(op_id)  → increment success_weight when shell is returned
        punish(op_id)  → decrement when bot gets blocked/banned
    """

    # Similarity threshold for reflex activation (0.0 - 1.0, higher = stricter)
    REFLEX_THRESHOLD = 0.85

    # Default success weight for new operations
    DEFAULT_WEIGHT = 0.5

    # Weight adjustment deltas
    REWARD_DELTA = 0.15
    PUNISH_DELTA = 0.20

    # Template placeholder for dynamic parameterization
    TARGET_PLACEHOLDER = "{{TARGET}}"

    # Regex patterns for IP addresses, subnets, URLs, and hostnames
    _IP_PATTERN = re.compile(
        r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:/\d{1,2})?\b'
    )
    _URL_PATTERN = re.compile(
        r'https?://[^\s/"\'>]+'
    )

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.neural_dir = os.path.join(base_dir, "memory", "neural")
        os.makedirs(self.neural_dir, exist_ok=True)

        self.available = CHROMADB_AVAILABLE
        self.client = None
        self.operations = None
        self.topology = None
        self.attack_paths = None

        if self.available:
            self._init_chromadb()
        else:
            logger.warning(
                "ChromaDB not installed. Neural Brain running in DEGRADED mode. "
                "Install with: pip install chromadb"
            )

    def _init_chromadb(self):
        """Initialize ChromaDB with persistent storage and local embedding model."""
        try:
            self.client = chromadb.PersistentClient(
                path=self.neural_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                ),
            )

            # Use local-only embedding model for Digital Sovereignty
            # all-MiniLM-L6-v2 runs entirely offline — no API calls
            self._embedding_fn = ONNXMiniLM_L6_V2()

            # ── Collection 1: Operations ─────────────────────────
            # Stores every successful command execution with context
            self.operations = self.client.get_or_create_collection(
                name="operations",
                embedding_function=self._embedding_fn,
                metadata={
                    "description": "Successful command executions with target context",
                    "hnsw:space": "cosine",
                },
            )

            # ── Collection 2: Topology ───────────────────────────
            # Stores network topology snapshots
            self.topology = self.client.get_or_create_collection(
                name="topology",
                embedding_function=self._embedding_fn,
                metadata={
                    "description": "Network topology: hosts, ports, OS, services",
                    "hnsw:space": "cosine",
                },
            )

            # ── Collection 3: Attack Paths ───────────────────────
            # Stores proven attack chains with RL weights
            self.attack_paths = self.client.get_or_create_collection(
                name="attack_paths",
                embedding_function=self._embedding_fn,
                metadata={
                    "description": "Proven attack chains with success_weight scores",
                    "hnsw:space": "cosine",
                },
            )

            ops_count = self.operations.count()
            topo_count = self.topology.count()
            paths_count = self.attack_paths.count()

            logger.info(
                f"Neural Brain ONLINE — Operations: {ops_count}, "
                f"Topology: {topo_count}, Attack Paths: {paths_count} "
                f"(Embedding: all-MiniLM-L6-v2 [LOCAL])"
            )

        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            self.available = False

    # ═══════════════════════════════════════════════════════════════
    #  REFLEX LOOP — Zero-Latency Command Recall
    # ═══════════════════════════════════════════════════════════════

    def recall_reflex(self, ports, os_type="", target_ip=None):
        """
        The Reflex Loop — query the hippocampus before hitting the LLM.

        Builds a fingerprint from ports + OS, searches for similar past
        operations, and returns the proven command if similarity > threshold.

        Args:
            ports: list of open port numbers (e.g., [22, 80, 443])
            os_type: detected OS string (e.g., "Linux", "Windows Server")
            target_ip: optional target IP for exact match boost

        Returns:
            dict with reflex command if found, None otherwise:
            {
                "reflex": True,
                "command": "nmap -sV -sC ...",
                "confidence": 0.92,
                "success_weight": 0.85,
                "source_op_id": "op_abc123",
                "reason": "Matched 92% similar target (ports: 22,80,443 / Linux)"
            }
        """
        if not self.available or not self.operations:
            return None

        # Build the query fingerprint
        fingerprint = self._build_fingerprint(ports, os_type)
        if not fingerprint:
            return None

        try:
            start_time = time.time()

            results = self.operations.query(
                query_texts=[fingerprint],
                n_results=5,
                include=["documents", "metadatas", "distances"],
            )

            elapsed_ms = (time.time() - start_time) * 1000

            if not results or not results["ids"][0]:
                return None

            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: 1 - (distance / 2)
            best_distance = results["distances"][0][0]
            similarity = 1 - (best_distance / 2)

            if similarity < self.REFLEX_THRESHOLD:
                logger.debug(
                    f"Reflex miss — best similarity {similarity:.2f} < threshold "
                    f"{self.REFLEX_THRESHOLD} ({elapsed_ms:.0f}ms)"
                )
                return None

            # Found a strong match — extract the reflex command
            best_id = results["ids"][0][0]
            best_meta = results["metadatas"][0][0]
            best_doc = results["documents"][0][0]

            weight = float(best_meta.get("success_weight", self.DEFAULT_WEIGHT))

            # Only fire reflex if weight is positive (not punished into oblivion)
            if weight <= 0.1:
                logger.info(
                    f"Reflex suppressed — operation {best_id} has low weight "
                    f"{weight:.2f} (punished)"
                )
                return None

            reflex = {
                "reflex": True,
                "command": self._deparameterize_command(
                    best_meta.get("command", ""), target_ip
                ),
                "command_template": best_meta.get("command", ""),
                "confidence": round(similarity, 3),
                "success_weight": round(weight, 3),
                "source_op_id": best_id,
                "original_target": best_meta.get("target_ip", "unknown"),
                "original_ports": best_meta.get("ports", ""),
                "original_os": best_meta.get("os_type", ""),
                "reason": (
                    f"Matched {similarity:.0%} similar target "
                    f"(ports: {best_meta.get('ports', '?')} / "
                    f"{best_meta.get('os_type', '?')}) "
                    f"— weight: {weight:.2f} — recalled in {elapsed_ms:.0f}ms"
                ),
            }

            logger.info(
                f"⚡ REFLEX FIRED — {reflex['command'][:60]} "
                f"(confidence: {similarity:.2f}, weight: {weight:.2f}, "
                f"{elapsed_ms:.0f}ms)"
            )

            return reflex

        except Exception as e:
            logger.error(f"Reflex recall error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    #  OPERATION RECORDING — Learn from every execution
    # ═══════════════════════════════════════════════════════════════

    def record_operation(self, command, target_ip, ports, os_type,
                         exit_code, stdout_snippet="", category="RECON"):
        """
        Record a successful operation into the hippocampus.

        Called after every successful command execution to build
        the reflex database for future zero-latency recall.

        Args:
            command: the full command string executed
            target_ip: target IP address
            ports: list of open ports on target
            os_type: detected OS string
            exit_code: command exit code (0 = success)
            stdout_snippet: first 500 chars of output (for context)
            category: command category (RECON, EXPLOIT, etc.)

        Returns:
            operation ID string
        """
        if not self.available or not self.operations:
            return None

        # Only record successful operations
        if exit_code != 0:
            return None

        # Build fingerprint and operation ID
        fingerprint = self._build_fingerprint(ports, os_type)

        # ── DYNAMIC PARAMETERIZATION ─────────────────────────
        # Store templatized command: "nmap 192.168.1.5" → "nmap {{TARGET}}"
        # This prevents Target Fixation — the same technique works
        # against ANY target with matching ports/OS, not just the original.
        templatized_cmd = self._templatize_command(command, target_ip)

        # Generate op_id from the TEMPLATE so that the same attack
        # technique against different IPs shares a single memory slot.
        op_id = self._generate_op_id(templatized_cmd, None)

        # Fallback: if no ports/OS, use the command itself as fingerprint
        if not fingerprint:
            fingerprint = f"Command: {templatized_cmd}"

        try:
            # Check if this exact operation already exists
            existing = self.operations.get(ids=[op_id])
            if existing and existing["ids"]:
                # Update execution count
                meta = existing["metadatas"][0]
                exec_count = int(meta.get("exec_count", 1)) + 1
                meta["exec_count"] = str(exec_count)
                meta["last_executed"] = datetime.now(timezone.utc).isoformat()

                self.operations.update(
                    ids=[op_id],
                    metadatas=[meta],
                )
                logger.debug(f"Operation {op_id} updated (exec #{exec_count})")
                return op_id

            # New operation — store TEMPLATIZED command
            ports_str = ",".join(str(p) for p in sorted(ports)) if ports else ""

            metadata = {
                "command": templatized_cmd,
                "target_ip": self.TARGET_PLACEHOLDER,
                "ports": ports_str,
                "os_type": os_type or "unknown",
                "category": category,
                "exit_code": str(exit_code),
                "success_weight": str(self.DEFAULT_WEIGHT),
                "exec_count": "1",
                "first_executed": datetime.now(timezone.utc).isoformat(),
                "last_executed": datetime.now(timezone.utc).isoformat(),
                "stdout_snippet": self._templatize_command(stdout_snippet[:500], target_ip),
            }

            # The document is the fingerprint (used for similarity search)
            # The metadata contains the templatized command template
            self.operations.add(
                ids=[op_id],
                documents=[fingerprint],
                metadatas=[metadata],
            )

            logger.info(f"📝 Operation recorded: {op_id} — {templatized_cmd[:60]}")
            return op_id

        except Exception as e:
            logger.error(f"Operation recording error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    #  TOPOLOGY PERSISTENCE — Remember network maps
    # ═══════════════════════════════════════════════════════════════

    def store_topology(self, subnet, hosts_data):
        """
        Store a network topology snapshot.

        Called after discovery/recon completes to persist the network
        map across sessions. Tomorrow the bot won't need to re-scan.

        Args:
            subnet: network subnet string (e.g., "192.168.1.0/24")
            hosts_data: dict of {ip: {hostname, os, ports[], risk_flags[]}}
        """
        if not self.available or not self.topology:
            return None

        stored_ids = []

        try:
            for ip, info in hosts_data.items():
                host_id = f"topo_{subnet.replace('/', '_')}_{ip.replace('.', '_')}"

                ports = info.get("ports", [])
                if ports and isinstance(ports[0], dict):
                    # Parse from nmap service scan format
                    port_numbers = [str(p.get("port", "")) for p in ports]
                    services = [f"{p.get('port')}/{p.get('service', '?')}" for p in ports]
                else:
                    port_numbers = [str(p) for p in ports]
                    services = port_numbers

                # Build a rich description for similarity search
                description = (
                    f"Host {ip} on {subnet} — "
                    f"OS: {info.get('os', 'unknown')} — "
                    f"Hostname: {info.get('hostname', 'unknown')} — "
                    f"Ports: {','.join(port_numbers)} — "
                    f"Services: {','.join(services)} — "
                    f"Risks: {','.join(info.get('risk_flags', []))}"
                )

                metadata = {
                    "subnet": subnet,
                    "ip": ip,
                    "hostname": info.get("hostname", "") or "",
                    "os": info.get("os", "") or "",
                    "ports": ",".join(port_numbers),
                    "services": ",".join(services),
                    "risk_flags": ",".join(info.get("risk_flags", [])),
                    "device_class": info.get("class", "unknown"),
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                }

                self.topology.upsert(
                    ids=[host_id],
                    documents=[description],
                    metadatas=[metadata],
                )
                stored_ids.append(host_id)

            logger.info(
                f"🗺️ Topology stored: {len(stored_ids)} hosts on {subnet}"
            )
            return stored_ids

        except Exception as e:
            logger.error(f"Topology storage error: {e}")
            return None

    def recall_topology(self, subnet=None):
        """
        Retrieve stored network topology.

        Args:
            subnet: optional filter by subnet. If None, returns all.

        Returns:
            dict of {ip: {hostname, os, ports, services, risk_flags, scanned_at}}
        """
        if not self.available or not self.topology:
            return {}

        try:
            if subnet:
                results = self.topology.get(
                    where={"subnet": subnet},
                    include=["metadatas"],
                )
            else:
                results = self.topology.get(
                    include=["metadatas"],
                )

            if not results or not results["ids"]:
                return {}

            topology_map = {}
            for meta in results["metadatas"]:
                ip = meta.get("ip", "unknown")
                topology_map[ip] = {
                    "hostname": meta.get("hostname", ""),
                    "os": meta.get("os", ""),
                    "ports": meta.get("ports", "").split(",") if meta.get("ports") else [],
                    "services": meta.get("services", "").split(",") if meta.get("services") else [],
                    "risk_flags": meta.get("risk_flags", "").split(",") if meta.get("risk_flags") else [],
                    "device_class": meta.get("device_class", "unknown"),
                    "subnet": meta.get("subnet", ""),
                    "scanned_at": meta.get("scanned_at", ""),
                }

            return topology_map

        except Exception as e:
            logger.error(f"Topology recall error: {e}")
            return {}

    # ═══════════════════════════════════════════════════════════════
    #  ATTACK PATH RECORDING — Proven chains
    # ═══════════════════════════════════════════════════════════════

    def record_attack_path(self, chain_name, target_profile, commands,
                           result="success", notes=""):
        """
        Record a proven attack path (multi-command chain).

        Args:
            chain_name: e.g., "NETWORK_DISCOVERY", "WEB_COMPROMISE"
            target_profile: dict with {ports, os_type, device_class}
            commands: list of command strings in execution order
            result: "success", "partial", "failed"
            notes: LLM analysis or human notes
        """
        if not self.available or not self.attack_paths:
            return None

        try:
            ports = target_profile.get("ports", [])
            os_type = target_profile.get("os_type", "unknown")
            device_class = target_profile.get("device_class", "unknown")

            # Build path fingerprint
            fingerprint = (
                f"Chain: {chain_name} — "
                f"Target: {os_type} / {device_class} — "
                f"Ports: {','.join(str(p) for p in sorted(ports))} — "
                f"Commands: {' → '.join(cmd[:40] for cmd in commands)}"
            )

            path_id = hashlib.md5(
                f"{chain_name}:{','.join(str(p) for p in sorted(ports))}:{os_type}".encode()
            ).hexdigest()[:16]
            path_id = f"path_{path_id}"

            weight = self.DEFAULT_WEIGHT
            if result == "success":
                weight = self.DEFAULT_WEIGHT + self.REWARD_DELTA
            elif result == "failed":
                weight = self.DEFAULT_WEIGHT - self.PUNISH_DELTA

            metadata = {
                "chain_name": chain_name,
                "ports": ",".join(str(p) for p in sorted(ports)),
                "os_type": os_type,
                "device_class": device_class,
                "commands": json.dumps(commands),
                "command_count": str(len(commands)),
                "result": result,
                "success_weight": str(weight),
                "notes": notes[:500],
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }

            self.attack_paths.upsert(
                ids=[path_id],
                documents=[fingerprint],
                metadatas=[metadata],
            )

            logger.info(
                f"🎯 Attack path recorded: {chain_name} → {result} "
                f"(weight: {weight:.2f})"
            )
            return path_id

        except Exception as e:
            logger.error(f"Attack path recording error: {e}")
            return None

    def recall_attack_path(self, ports, os_type="", device_class=""):
        """
        Find the best proven attack path for a target profile.

        Returns the highest-weighted attack path that matches.
        """
        if not self.available or not self.attack_paths:
            return None

        fingerprint = (
            f"Target: {os_type} / {device_class} — "
            f"Ports: {','.join(str(p) for p in sorted(ports))}"
        )

        try:
            results = self.attack_paths.query(
                query_texts=[fingerprint],
                n_results=3,
                include=["documents", "metadatas", "distances"],
            )

            if not results or not results["ids"][0]:
                return None

            # Find the best match with highest weight
            best = None
            best_score = -1

            for i, meta in enumerate(results["metadatas"][0]):
                distance = results["distances"][0][i]
                similarity = 1 - (distance / 2)

                if similarity < 0.70:
                    continue

                weight = float(meta.get("success_weight", 0))
                # Combined score: similarity * weight
                score = similarity * weight

                if score > best_score:
                    best_score = score
                    best = {
                        "chain_name": meta.get("chain_name", ""),
                        "commands": json.loads(meta.get("commands", "[]")),
                        "similarity": round(similarity, 3),
                        "success_weight": round(weight, 3),
                        "combined_score": round(score, 3),
                        "result": meta.get("result", ""),
                        "path_id": results["ids"][0][i],
                    }

            return best

        except Exception as e:
            logger.error(f"Attack path recall error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    #  DOPAMINE LOOP — Reinforcement Learning
    # ═══════════════════════════════════════════════════════════════

    def reward(self, op_id, delta=None):
        """
        Reward — shell returned successfully. Increment success_weight.

        Call this when: command produces a shell, data is exfiltrated,
        or chain completes successfully.
        """
        return self._adjust_weight(op_id, delta or self.REWARD_DELTA)

    def punish(self, op_id, delta=None):
        """
        Punish — bot got blocked/banned. Decrement success_weight.

        Call this when: command is blocked by IDS, connection refused,
        or chain fails due to detection.
        """
        return self._adjust_weight(op_id, -(delta or self.PUNISH_DELTA))

    def _adjust_weight(self, op_id, delta):
        """Adjust success_weight for an operation or attack path."""
        if not self.available:
            return False

        # Try operations collection first
        for collection in [self.operations, self.attack_paths]:
            if not collection:
                continue
            try:
                existing = collection.get(ids=[op_id])
                if existing and existing["ids"]:
                    meta = existing["metadatas"][0]
                    current = float(meta.get("success_weight", self.DEFAULT_WEIGHT))
                    new_weight = max(0.0, min(1.0, current + delta))
                    meta["success_weight"] = str(round(new_weight, 4))
                    meta["last_adjusted"] = datetime.now(timezone.utc).isoformat()

                    collection.update(ids=[op_id], metadatas=[meta])

                    action = "REWARD" if delta > 0 else "PUNISH"
                    logger.info(
                        f"🧠 {action}: {op_id} — "
                        f"{current:.2f} → {new_weight:.2f} (Δ{delta:+.2f})"
                    )
                    return True
            except Exception:
                continue

        return False

    # ═══════════════════════════════════════════════════════════════
    #  STATUS & DIAGNOSTICS
    # ═══════════════════════════════════════════════════════════════

    def get_status(self):
        """Get neural brain status and statistics."""
        status = {
            "available": self.available,
            "engine": "ChromaDB" if self.available else "DEGRADED (no chromadb)",
            "storage_path": self.neural_dir,
            "collections": {},
        }

        if self.available:
            try:
                status["collections"] = {
                    "operations": self.operations.count() if self.operations else 0,
                    "topology": self.topology.count() if self.topology else 0,
                    "attack_paths": self.attack_paths.count() if self.attack_paths else 0,
                }
                status["total_memories"] = sum(status["collections"].values())
            except Exception:
                status["collections"] = {"error": "Failed to query"}

        return status

    def get_top_reflexes(self, n=10):
        """Get the top N highest-weighted reflex operations."""
        if not self.available or not self.operations:
            return []

        try:
            all_ops = self.operations.get(
                include=["metadatas"],
            )

            if not all_ops or not all_ops["ids"]:
                return []

            # Sort by success_weight descending
            ops = []
            for i, op_id in enumerate(all_ops["ids"]):
                meta = all_ops["metadatas"][i]
                ops.append({
                    "op_id": op_id,
                    "command": meta.get("command", ""),
                    "target_ip": meta.get("target_ip", ""),
                    "ports": meta.get("ports", ""),
                    "os_type": meta.get("os_type", ""),
                    "success_weight": float(meta.get("success_weight", 0)),
                    "exec_count": int(meta.get("exec_count", 0)),
                    "category": meta.get("category", ""),
                })

            ops.sort(key=lambda x: x["success_weight"], reverse=True)
            return ops[:n]

        except Exception as e:
            logger.error(f"Top reflexes query error: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════
    #  INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════════

    def _build_fingerprint(self, ports, os_type=""):
        """
        Build a searchable text fingerprint from ports + OS.

        The fingerprint is what ChromaDB embeds and searches against.
        It's designed to cluster similar targets together.
        """
        if not ports and not os_type:
            return None

        port_str = ",".join(str(p) for p in sorted(ports)) if ports else "unknown"

        # Classify port groups for better semantic matching
        port_groups = []
        port_set = set(int(p) for p in ports) if ports else set()

        if port_set.intersection({80, 443, 8080, 8443}):
            port_groups.append("web-server")
        if port_set.intersection({22}):
            port_groups.append("ssh")
        if port_set.intersection({21}):
            port_groups.append("ftp")
        if port_set.intersection({445, 139}):
            port_groups.append("smb-windows")
        if port_set.intersection({3306, 5432, 1433, 27017, 6379, 9200}):
            port_groups.append("database")
        if port_set.intersection({88, 389, 636}):
            port_groups.append("active-directory")
        if port_set.intersection({5555}):
            port_groups.append("android-adb")
        if port_set.intersection({3389}):
            port_groups.append("rdp")
        if port_set.intersection({5900}):
            port_groups.append("vnc")
        if port_set.intersection({25, 110, 143, 993, 995}):
            port_groups.append("email")

        groups_str = " ".join(port_groups) if port_groups else "generic"

        fingerprint = (
            f"Target with ports [{port_str}] "
            f"running {os_type or 'unknown OS'} — "
            f"profile: {groups_str}"
        )

        return fingerprint

    def _generate_op_id(self, command, target_ip):
        """Generate a deterministic operation ID from templatized command."""
        # Uses the TEMPLATE so same technique against different IPs
        # shares one memory slot (prevents target fixation)
        normalized = command.strip().lower()
        key = f"{normalized}:{target_ip or 'any'}"
        return f"op_{hashlib.md5(key.encode()).hexdigest()[:16]}"

    def _templatize_command(self, command, target_ip):
        """
        Replace the active target IP/URL with {{TARGET}} placeholder.

        This prevents Target Fixation: "nmap 192.168.1.5" becomes
        "nmap {{TARGET}}", so the same proven technique can be recalled
        and applied to ANY new target with matching ports/OS.

        Also handles:
            - Subnets (192.168.1.0/24 → {{TARGET}})
            - URLs   (http://192.168.1.5/admin → http://{{TARGET}}/admin)
        """
        if not command:
            return command

        result = command

        # Replace the specific target IP first (most precise match)
        if target_ip:
            # Escape dots for regex, match with optional CIDR
            escaped_ip = re.escape(target_ip)
            result = re.sub(
                rf'\b{escaped_ip}(?:/\d{{1,2}})?\b',
                self.TARGET_PLACEHOLDER,
                result
            )

        return result

    def _deparameterize_command(self, template, target_ip):
        """
        Inject the current session's target IP into a {{TARGET}} template.

        Retrieval counterpart of _templatize_command().
        "nmap {{TARGET}}" + target_ip="10.0.0.5" → "nmap 10.0.0.5"
        """
        if not template:
            return template
        if not target_ip:
            return template  # Return template as-is if no target known

        return template.replace(self.TARGET_PLACEHOLDER, target_ip)
