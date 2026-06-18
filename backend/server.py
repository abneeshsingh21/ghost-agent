"""
GHOST v6.0 — Flask + WebSocket API Server
REST + real-time streaming for the Command Center.
Features: PTY shell bridge, Strategic Brain, Loot management.
"""

import os
import sys
import json
import re
import platform
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.memory import MemoryManager
from backend.ethics import EthicsEngine
from backend.bridge import CommandBridge, PtyManager
from backend.chains import ChainEngine
from backend.discovery import DiscoveryEngine
from backend.osint import OSINTEngine
from backend.mobile import MobileEngine
from backend.wireless import WirelessEngine
from backend.acquisition import TargetAcquisitionEngine
from backend.resiliency import ResiliencyEngine
from backend.diagnostics import DiagnosticEngine
from backend.arsenal import ArsenalEngine
from backend.c2_manager import C2Manager
from backend.payload_factory import PayloadFactory


def create_app(base_dir=None, initial_mode="TEACHING", shadow_mode=False, initial_model="qwen3:4b"):
    """Create and configure the GHOST Flask application."""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Flask app
    app = Flask(
        __name__,
        static_folder=os.path.join(base_dir, "cockpit", "dist"),
        static_url_path="",
    )
    app.config["SECRET_KEY"] = "ghost-v6-" + datetime.now().strftime("%Y%m%d")
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    # ── Initialize Core Engines ───────────────────────────────────────────

    memory = MemoryManager(base_dir)
    if shadow_mode:
        memory.set_mode("STEALTH")
        memory.set_stealth(True)
        context = memory.get_session()
        context["shadow_mode"] = True
        memory._save_json(memory.paths["session_context"], memory.session_context)
    else:
        memory.set_stealth(False)
        memory.set_mode(initial_mode)
        context = memory.get_session()
        context["shadow_mode"] = False
        memory._save_json(memory.paths["session_context"], memory.session_context)

    ethics = EthicsEngine(memory)
    bridge = CommandBridge(memory, ethics, model=initial_model, socketio=socketio)
    chains = ChainEngine(memory, ethics, bridge)
    discovery = DiscoveryEngine(memory, ethics, bridge)
    osint = OSINTEngine(memory, ethics, bridge)
    mobile = MobileEngine(memory, ethics, bridge)
    wireless = WirelessEngine(memory, ethics, bridge)
    acquisition = TargetAcquisitionEngine(memory, ethics, bridge)
    resiliency = ResiliencyEngine(memory, bridge)
    diagnostics = DiagnosticEngine(memory, ethics, bridge)

    # Init new C2 and Factory components
    c2 = C2Manager(memory, ethics, bridge)
    factory = PayloadFactory(memory, ethics, bridge)

    # PTY Manager for interactive terminal
    pty_mgr = PtyManager(socketio)

    # Loot directory
    loot_dir = os.path.join(base_dir, "loot")
    os.makedirs(loot_dir, exist_ok=True)
    arsenal = ArsenalEngine(memory, ethics, bridge)

    valid_modes = {"TEACHING", "SUPERVISED", "AUTONOMOUS", "STEALTH"}

    def _get_json_payload():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None, (jsonify({"error": "Invalid JSON payload"}), 400)
        return data, None

    def _coerce_bool(value, default=False):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        return default

    # ── Serve Frontend ────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:path>")
    def serve_static(path):
        return send_from_directory(app.static_folder, path)

    # ── Status & System ───────────────────────────────────────────────────

    @app.route("/api/status")
    def get_status():
        """Get full GHOST system status."""
        mem_status = memory.get_full_status()
        bridge_status = bridge.get_status()
        chain_status = chains.get_chain_status()

        # Detect environment
        env = _detect_environment()

        return jsonify({
            "version": "6.0",
            "codename": "GHOST",
            "mode": memory.get_mode(),
            "stealth": memory.get_session().get("stealth", False),
            "environment": env,
            "memory": mem_status,
            "bridge": bridge_status,
            "chain": chain_status,
            "autonomy": _get_autonomy_display(memory),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @app.route("/api/startup-banner")
    def startup_banner():
        """Get the GHOST startup banner text."""
        mem = memory.get_full_status()
        mode = memory.get_mode()
        env = _detect_environment()
        bridge_info = bridge.get_status()

        banner = f"""═══════════════════════════════════════════════════════════════
 GHOST v6.0 COMMAND CENTER OPERATIONAL
═══════════════════════════════════════════════════════════════

 MODE: {mode}
 STEALTH: {mem['session']['stealth']}
 ENVIRONMENT: {env['type']} ({env['os']})
 LLM: {'✅ ' + bridge_info['model'] if bridge_info['ollama_available'] else '❌ Ollama not available'}

 MEMORY STATE:
   Absolute Rules: {mem['absolute_rules_count']} hardcoded
   Learned Ethics: {mem['learned_ethics_count']} rules active
   Target Profiles: {mem['target_profiles_count']} systems classified
   Session: {mem['session']['id']}

 AUTONOMY MATRIX:
   Reconnaissance: {memory.get_autonomy_policy('reconnaissance')}
   Vulnerability:  {memory.get_autonomy_policy('vulnerability_analysis')}
   Exploitation:   {memory.get_autonomy_policy('exploitation')}
   AD/Enterprise:  {memory.get_autonomy_policy('ad_enterprise')}
   Wireless:       {memory.get_autonomy_policy('wireless')}
   Social Eng:     {memory.get_autonomy_policy('social_engineering')}

  ZERO-KNOWLEDGE ENGINE: READY
  TOOL CHAIN ORCHESTRATION: READY
  OSINT ENGINE: READY
  MOBILE/ADB ENGINE: READY
  WIRELESS ENGINE: READY

  AWAITING COMMAND.
═══════════════════════════════════════════════════════════════

 "Maximum capability. Learned restraint. Documented accountability."
"""
        return jsonify({"banner": banner})

    # ── Mode Control ──────────────────────────────────────────────────────

    @app.route("/api/mode", methods=["GET", "POST"])
    def mode_control():
        if request.method == "GET":
            return jsonify({"mode": memory.get_mode()})
        data, error = _get_json_payload()
        if error:
            return error

        mode = str(data.get("mode", "TEACHING")).strip().upper()
        if mode not in valid_modes:
            return jsonify({"error": f"Invalid mode '{mode}'. Allowed: {sorted(valid_modes)}"}), 400

        success = memory.set_mode(mode)
        if success:
            socketio.emit("mode_change", {"mode": mode})
        return jsonify({"success": success, "mode": memory.get_mode()})

    @app.route("/api/stealth", methods=["POST"])
    def stealth_toggle():
        data, error = _get_json_payload()
        if error:
            return error

        enabled = _coerce_bool(data.get("enabled", False), default=False)
        memory.set_stealth(enabled)
        socketio.emit("stealth_change", {"stealth": enabled})
        return jsonify({"stealth": enabled})

    # ── Command Execution ─────────────────────────────────────────────────

    @app.route("/api/execute", methods=["POST"])
    def execute_command():
        """Execute a raw command (with ethics check)."""
        data, error = _get_json_payload()
        if error:
            return error

        command = str(data.get("command", "")).strip()
        force = _coerce_bool(data.get("force", False), default=False)

        if not command:
            return jsonify({"error": "No command provided"}), 400

        quality = bridge._assess_command_quality(command)
        if not quality["ok"]:
            return jsonify({"status": "HALT", "error": "Command failed quality gate", "quality": quality}), 400

        command = quality["normalized_command"]

        # Extract target IP
        target_ip = bridge._extract_ip(command)

        # Ethics check
        verdict = ethics.check_command(command, target_ip)

        if verdict["verdict"] == "HALT" and not force:
            socketio.emit("ethics_halt", {
                "command": command,
                "verdict": verdict,
                "formatted": ethics.format_verdict(verdict),
            })
            return jsonify({
                "status": "HALT",
                "verdict": verdict,
                "formatted": ethics.format_verdict(verdict),
            })

        if verdict["verdict"] == "PROPOSE" and not force:
            socketio.emit("ethics_propose", {
                "command": command,
                "verdict": verdict,
                "formatted": ethics.format_verdict(verdict),
            })
            return jsonify({
                "status": "PROPOSE",
                "verdict": verdict,
                "formatted": ethics.format_verdict(verdict),
                "message": "Command requires approval. Send with force=true to execute.",
            })

        # Execute
        result = bridge.execute_command(command)
        socketio.emit("command_complete", {
            "command": command,
            "result": result,
        })
        return jsonify({"status": "OK", "result": result})

    @app.route("/api/approve", methods=["POST"])
    def approve_command():
        """Approve and execute a previously proposed command."""
        data, error = _get_json_payload()
        if error:
            return error

        command = str(data.get("command", "")).strip()
        if not command:
            return jsonify({"error": "No command provided"}), 400

        result = bridge.approve_and_execute(command)
        status = result.get("status", "OK")
        code = 200 if status in {"OK", "RUNNING"} else 400
        return jsonify({"status": status, "result": result}), code

    # ── LLM Interaction ───────────────────────────────────────────────────

    @app.route("/api/chat", methods=["POST"])
    def chat():
        """Send user input through the full LLM pipeline with smart engine routing."""
        data, error = _get_json_payload()
        if error:
            return error

        user_input = str(data.get("message", "")).strip()
        auto_execute = _coerce_bool(data.get("auto_execute", False), default=False)
        strategic = _coerce_bool(data.get("strategic", False), default=False)

        if not user_input:
            return jsonify({"error": "No message provided"}), 400
        if len(user_input) > 4000:
            return jsonify({"error": "Message too long (max 4000 characters)"}), 400

        # ── Strategic Brain takes priority when enabled ───────────────
        if strategic:
            import threading

            # Emit engine hints for telemetry widgets
            if discovery.is_discovery_request(user_input):
                socketio.emit("discovery_started", {"message": "Strategic Discovery initiated..."})
            elif osint.is_osint_request(user_input):
                socketio.emit("osint_started", {"seed": user_input.split()[-1], "seed_type": "auto"})
            elif mobile.is_mobile_request(user_input):
                socketio.emit("mobile_started", {"target": bridge._extract_ip(user_input) or "auto"})

            def _run_strategy():
                r = bridge.strategic_execute(user_input, auto_execute=auto_execute, socketio=socketio)
                socketio.emit("chat_response", {
                    "user_input": user_input,
                    "response": r.get("llm_response", ""),
                    "commands": r.get("proposed_commands", []),
                    "verdicts": r.get("ethics_verdicts", []),
                })

            t = threading.Thread(target=_run_strategy, daemon=True)
            t.start()
            return jsonify({"status": "STRATEGIC_STARTED", "message": "Strategic Brain engaged. Results will stream via WebSocket."})

        # ── Smart Engine Routing (non-strategic mode) ─────────────────

        # OSINT Engine
        if osint.is_osint_request(user_input):
            import shlex
            try:
                tokens = shlex.split(user_input)
            except ValueError:
                tokens = user_input.split()
            seed = tokens[-1] if tokens else ""
            plan = osint.build_recon_plan(seed)
            socketio.emit("osint_started", {
                "seed": seed,
                "seed_type": plan["seed_type"],
                "phases": len(plan["phases"]),
            })
            result = bridge.process_user_input(user_input, auto_execute=auto_execute)
            result["engine_activated"] = "osint"
            result["osint_plan"] = plan
            socketio.emit("chat_response", {
                "user_input": user_input,
                "response": result["llm_response"],
                "commands": result["proposed_commands"],
                "verdicts": result["ethics_verdicts"],
                "engine": "osint",
            })
            return jsonify(result)

        # Mobile Engine
        if mobile.is_mobile_request(user_input):
            target_ip = bridge._extract_ip(user_input)
            plan = mobile.build_control_plan(target_ip)
            socketio.emit("mobile_started", {
                "target": target_ip or "discovery mode",
                "phases": len(plan["phases"]),
            })
            result = bridge.process_user_input(user_input, auto_execute=auto_execute)
            result["engine_activated"] = "mobile"
            result["mobile_plan"] = plan
            socketio.emit("chat_response", {
                "user_input": user_input,
                "response": result["llm_response"],
                "commands": result["proposed_commands"],
                "verdicts": result["ethics_verdicts"],
                "engine": "mobile",
            })
            return jsonify(result)

        # Wireless Engine
        if wireless.is_wireless_request(user_input):
            plan = wireless.build_scan_plan()
            socketio.emit("wireless_started", {
                "type": "scan",
                "phases": len(plan.get("phases", [])),
            })
            result = bridge.process_user_input(user_input, auto_execute=auto_execute)
            result["engine_activated"] = "wireless"
            result["wireless_plan"] = plan
            socketio.emit("chat_response", {
                "user_input": user_input,
                "response": result["llm_response"],
                "commands": result["proposed_commands"],
                "verdicts": result["ethics_verdicts"],
                "engine": "wireless",
            })
            return jsonify(result)

        # Autonomous Target Acquisition Engine
        if acquisition.is_acquisition_request(user_input):
            target_ip = bridge._extract_ip(user_input)
            target_type = "phone" if any(w in user_input.lower() for w in ["phone", "mobile", "android", "iphone"]) else "unknown"
            plan = acquisition.build_acquisition_plan(target_ip, target_type)
            socketio.emit("acquisition_started", {
                "target": target_ip or "auto-discover",
                "target_type": target_type,
                "vectors": len(_get_attack_vectors(plan)),
            })
            result = bridge.process_user_input(user_input, auto_execute=auto_execute)
            result["engine_activated"] = "acquisition"
            result["acquisition_plan"] = plan
            socketio.emit("chat_response", {
                "user_input": user_input,
                "response": result["llm_response"],
                "commands": result["proposed_commands"],
                "verdicts": result["ethics_verdicts"],
                "engine": "acquisition",
                "attack_vectors": [v["name"] for v in _get_attack_vectors(plan)],
            })
            return jsonify(result)

        # Discovery Engine
        if discovery.is_discovery_request(user_input):
            socketio.emit("discovery_started", {"message": "Zero-Knowledge Discovery initiated..."})

        # ── Default: Standard LLM Pipeline ────────────────────────────
        result = bridge.process_user_input(user_input, auto_execute=auto_execute)
        socketio.emit("chat_response", {
            "user_input": user_input,
            "response": result["llm_response"],
            "commands": result["proposed_commands"],
            "verdicts": result["ethics_verdicts"],
        })
        return jsonify(result)

    @app.route("/api/model", methods=["POST"])
    def change_model():
        """Change the Ollama LLM model."""
        data, error = _get_json_payload()
        if error:
            return error

        model = str(data.get("model", "qwen3:4b")).strip()
        if not model or len(model) > 100 or not re.fullmatch(r"[A-Za-z0-9_.:-]+", model):
            return jsonify({"error": "Invalid model format"}), 400

        result = bridge.change_model(model)
        return jsonify(result)

    # ── Feedback / Teaching ───────────────────────────────────────────────

    @app.route("/api/feedback", methods=["POST"])
    def submit_feedback():
        """Submit ethical feedback (WRONG, CONDITIONAL, OVERRIDE, PRINCIPLE, CLASSIFICATION)."""
        data, error = _get_json_payload()
        if error:
            return error

        feedback_type = str(data.get("type", "")).upper()
        context = data.get("context", {})
        details = data.get("details", {})

        valid_types = ["WRONG", "CONDITIONAL", "OVERRIDE", "PRINCIPLE", "CLASSIFICATION"]
        if feedback_type not in valid_types:
            return jsonify({"error": f"Invalid feedback type. Must be one of: {valid_types}"}), 400

        result = ethics.process_feedback(feedback_type, context, details)
        socketio.emit("feedback_processed", result)
        return jsonify(result)

    # ── Chain Operations ──────────────────────────────────────────────────

    @app.route("/api/chains", methods=["GET"])
    def list_chains():
        """List all available chain templates."""
        return jsonify(chains.list_chains())

    @app.route("/api/chain/start", methods=["POST"])
    def start_chain():
        """Start a new operation chain."""
        data = request.get_json()
        chain_name = data.get("chain", "")
        variables = data.get("variables", {})
        result = chains.start_chain(chain_name, variables)
        socketio.emit("chain_started", result)
        return jsonify(result)

    @app.route("/api/chain/status", methods=["GET"])
    def chain_status():
        """Get current chain status."""
        return jsonify(chains.get_chain_status())

    @app.route("/api/chain/advance", methods=["POST"])
    def advance_chain():
        """Advance to next chain phase."""
        data = request.get_json()
        decision = data.get("decision", None)
        result = chains.advance_phase(decision)
        socketio.emit("chain_advanced", result)
        return jsonify(result)

    @app.route("/api/chain/execute", methods=["POST"])
    def execute_chain_phase():
        """Execute all commands in current chain phase."""
        result = chains.execute_current_phase(socketio)
        socketio.emit("chain_phase_complete", result)
        return jsonify(result)

    @app.route("/api/chain/halt", methods=["POST"])
    def halt_chain():
        """Halt the active chain."""
        data = request.get_json()
        reason = data.get("reason", "User requested halt")
        result = chains.halt_chain(reason)
        socketio.emit("chain_halted", result)
        return jsonify(result)

    # ── OSINT Engine ──────────────────────────────────────────────────────

    @app.route("/api/osint", methods=["POST"])
    def osint_profile():
        """Run automated OSINT profiling on a target seed."""
        data = request.get_json()
        seed = data.get("seed", "")
        seed_type = data.get("type", None)
        auto_execute = data.get("auto_execute", False)

        if not seed:
            return jsonify({"error": "No seed data provided (username/email/domain/IP)"}), 400

        plan = osint.build_recon_plan(seed, seed_type)
        socketio.emit("osint_started", {
            "seed": seed,
            "seed_type": plan["seed_type"],
            "phases": len(plan["phases"]),
        })

        if auto_execute:
            results = osint.execute_plan(plan, socketio)
            return jsonify(results)
        else:
            return jsonify({"plan": plan, "message": "Plan ready. Send auto_execute=true to run."})

    # ── Mobile/ADB Engine ─────────────────────────────────────────────────

    @app.route("/api/mobile", methods=["POST"])
    def mobile_control():
        """Run automated mobile device control workflow."""
        data = request.get_json()
        target_ip = data.get("target_ip", None)
        subnet = data.get("subnet", "192.168.1.0/24")
        action = data.get("action", "plan")  # plan, execute, quick
        quick_action = data.get("quick_action", None)

        if action == "quick" and target_ip and quick_action:
            commands = mobile.get_quick_commands(target_ip)
            cmd = commands.get(quick_action)
            if cmd:
                verdict = ethics.check_command(cmd, target_ip)
                if verdict["verdict"] == "HALT":
                    return jsonify({"status": "HALT", "verdict": verdict})
                result = bridge.execute_command(cmd)
                return jsonify({"status": "OK", "result": result})
            return jsonify({"error": f"Unknown action: {quick_action}", "available": list(commands.keys())}), 400

        plan = mobile.build_control_plan(target_ip, subnet)
        socketio.emit("mobile_started", {
            "target": target_ip or "discovery mode",
            "phases": len(plan["phases"]),
        })

        if action == "execute":
            results = mobile.execute_plan(plan, socketio)
            return jsonify(results)
        else:
            return jsonify({"plan": plan, "quick_actions": mobile.get_quick_commands(target_ip or "TARGET_IP") if target_ip else None})

    @app.route("/api/mobile/actions", methods=["GET"])
    def mobile_actions():
        """List all available ADB quick actions."""
        ip = request.args.get("ip", "TARGET_IP")
        return jsonify(mobile.get_quick_commands(ip))

    # ── Wireless Attack Engine ────────────────────────────────────────────

    @app.route("/api/wireless", methods=["POST"])
    def wireless_attack():
        """Run wireless attack workflows."""
        data = request.get_json()
        attack_type = data.get("type", "scan")
        interface = data.get("interface", "wlan0")

        if attack_type == "scan":
            plan = wireless.build_scan_plan(interface)
        elif attack_type == "deauth":
            plan = wireless.build_deauth_plan(
                interface=data.get("interface", "wlan0mon"),
                bssid=data.get("bssid"),
                client_mac=data.get("client_mac"),
                count=data.get("count", 10),
            )
        elif attack_type == "handshake":
            plan = wireless.build_handshake_plan(
                interface=data.get("interface", "wlan0mon"),
                bssid=data.get("bssid"),
                channel=data.get("channel"),
            )
        elif attack_type == "evil_twin":
            plan = wireless.build_evil_twin_plan(
                interface=data.get("interface", "wlan0mon"),
                target_ssid=data.get("ssid"),
                target_bssid=data.get("bssid"),
                channel=data.get("channel"),
            )
        elif attack_type == "wps":
            plan = wireless.build_wps_attack_plan(
                interface=data.get("interface", "wlan0mon"),
                bssid=data.get("bssid"),
            )
        else:
            return jsonify({"error": f"Unknown attack type: {attack_type}"}), 400

        socketio.emit("wireless_started", {
            "type": attack_type,
            "phases": len(plan.get("phases", [])),
        })

        return jsonify({"plan": plan})

    # ── Autonomous Target Acquisition ───────────────────────────────────

    @app.route("/api/acquire", methods=["POST"])
    def acquire_target():
        """Autonomous target acquisition — bot finds the way in by itself."""
        data = request.get_json()
        target_ip = data.get("target_ip", None)
        target_type = data.get("target_type", "unknown")
        subnet = data.get("subnet", None)
        auto_execute = data.get("auto_execute", False)

        plan = acquisition.build_acquisition_plan(target_ip, target_type, subnet)
        socketio.emit("acquisition_started", {
            "target": target_ip or "auto-discover",
            "target_type": target_type,
            "phases": len(plan["phases"]),
            "vectors": [v["name"] for v in _get_attack_vectors(plan)],
        })

        if auto_execute:
            results = acquisition.execute_plan(plan, socketio)
            return jsonify(results)
        else:
            return jsonify({"plan": plan})

    @app.route("/api/acquire/vectors", methods=["GET"])
    def list_vectors():
        """List all available autonomous attack vectors."""
        return jsonify({"summary": acquisition.get_vector_summary()})

    # ── Resiliency Engine ─────────────────────────────────────────────────

    @app.route("/api/resiliency", methods=["POST"])
    def resiliency_ops():
        """Execute resiliency / stealth operations."""
        data = request.get_json()
        op_type = data.get("type", "c2")

        if op_type == "sdr":
            plan = resiliency.build_sdr_airgap_plan(
                target_frequency=data.get("frequency", "433.92M"),
                data_payload=data.get("payload", "PING")
            )
        elif op_type == "traffic":
            plan = resiliency.apply_traffic_shaping(interface=data.get("interface", "eth0"))
        else:
            plan = resiliency.build_c2_tunnel_plan(
                domain=data.get("domain", "ghost.local"),
                target_ip=data.get("target_ip", "192.168.1.100"),
                tunnel_type=data.get("tunnel_type", "DNS")
            )

        socketio.emit("system_message", {
            "message": f"Resiliency Operation: {plan.get('strategy', plan.get('name'))}"
        })
        return jsonify({"plan": plan})

    # ── Neural Brain ──────────────────────────────────────────────────────

    @app.route("/api/neural/status", methods=["GET"])
    def neural_status():
        """Get Neural Brain status and statistics."""
        if bridge.neural and bridge.neural.available:
            return jsonify(bridge.neural.get_status())
        return jsonify({
            "available": False,
            "engine": "DEGRADED (chromadb not installed)",
            "message": "Install chromadb: pip install chromadb",
        })

    @app.route("/api/neural/topology", methods=["GET"])
    def neural_topology():
        """Retrieve stored network topology from hippocampus."""
        if not bridge.neural or not bridge.neural.available:
            return jsonify({"error": "Neural Brain not available"}), 503

        subnet = request.args.get("subnet")
        topology = bridge.neural.recall_topology(subnet)
        return jsonify({
            "subnet": subnet or "all",
            "hosts": topology,
            "count": len(topology),
        })

    @app.route("/api/neural/topology/store", methods=["POST"])
    def neural_store_topology():
        """Manually store topology data into hippocampus."""
        if not bridge.neural or not bridge.neural.available:
            return jsonify({"error": "Neural Brain not available"}), 503

        data = request.get_json()
        subnet = data.get("subnet", "")
        hosts = data.get("hosts", {})
        if not subnet or not hosts:
            return jsonify({"error": "subnet and hosts required"}), 400

        ids = bridge.neural.store_topology(subnet, hosts)
        return jsonify({"stored": len(ids) if ids else 0, "ids": ids})

    @app.route("/api/neural/reflexes", methods=["GET"])
    def neural_reflexes():
        """List top reflex commands ranked by success weight."""
        if not bridge.neural or not bridge.neural.available:
            return jsonify({"error": "Neural Brain not available"}), 503

        n = request.args.get("n", 10, type=int)
        reflexes = bridge.neural.get_top_reflexes(n)
        return jsonify({"reflexes": reflexes, "count": len(reflexes)})

    @app.route("/api/neural/reward", methods=["POST"])
    def neural_reward():
        """Manually reward or punish an operation (Dopamine Loop)."""
        if not bridge.neural or not bridge.neural.available:
            return jsonify({"error": "Neural Brain not available"}), 503

        data = request.get_json()
        op_id = data.get("op_id", "")
        action = data.get("action", "reward")  # "reward" or "punish"
        delta = data.get("delta")

        if not op_id:
            return jsonify({"error": "op_id required"}), 400

        if action == "punish":
            success = bridge.neural.punish(op_id, delta)
        else:
            success = bridge.neural.reward(op_id, delta)

        return jsonify({"success": success, "op_id": op_id, "action": action})

    # ── Frontal Cortex (Multi-Agent Swarm) ────────────────────────────────

    @app.route("/api/cortex/deliberate", methods=["POST"])
    def cortex_deliberate():
        """Run a full Red/Blue/Judge deliberation on a target."""
        if not bridge.cortex:
            return jsonify({"error": "Frontal Cortex not initialized"}), 503

        data = request.get_json()
        target_profile = {
            "ip": data.get("ip", ""),
            "os": data.get("os", "unknown"),
            "ports": data.get("ports", []),
            "services": data.get("services", []),
            "device_class": data.get("device_class", "unknown"),
            "risk_flags": data.get("risk_flags", []),
        }

        if not target_profile["ip"]:
            return jsonify({"error": "ip is required"}), 400

        decision = bridge.cortex.deliberate(target_profile, socketio=socketio)
        return jsonify(decision)

    @app.route("/api/cortex/history", methods=["GET"])
    def cortex_history():
        """Get recent deliberation decisions."""
        if not bridge.cortex:
            return jsonify({"error": "Frontal Cortex not initialized"}), 503

        n = request.args.get("n", 10, type=int)
        history = bridge.cortex.get_history(n)
        return jsonify({"decisions": history, "count": len(history)})

    # ── Diagnostics Engine ────────────────────────────────────────────────

    @app.route("/api/diagnose", methods=["POST"])
    def run_diagnostics():
        """Run advanced diagnostics primitives."""
        data = request.get_json()
        target_ip = data.get("target_ip", "127.0.0.1")
        diag_type = data.get("type", "uaf")
        
        if diag_type == "uaf":
            plan = diagnostics.build_memory_corruption_plan(target_ip, process_name=data.get("process", "target_binary"))
        elif diag_type == "zeroclick":
            plan = diagnostics.build_zero_click_plan(target_ip)
        elif diag_type == "persistence":
            plan = diagnostics.build_persistence_audit_plan(target_ip)
        elif diag_type == "telemetry":
            plan = diagnostics.build_memory_telemetry_plan(target_ip)
        else:
            return jsonify({"error": "Unknown diagnostic mode"}), 400

        socketio.emit("system_message", {
            "message": f"Diagnostic Operation Triggered: {plan.get('type')}\nTarget: {target_ip}\nTier: {plan.get('tier')}"
        })
        return jsonify({"plan": plan})

    # ── Arsenal Engine ────────────────────────────────────────────────────

    @app.route("/api/arsenal", methods=["POST"])
    def run_arsenal():
        data = request.get_json()
        target = data.get("target", "target_binary")
        plan = arsenal.synthesize_zeroday(target)
        socketio.emit("system_message", {
            "message": f"Arsenal Zero-Day Synthesis Triggered: {target}\nJob ID: {plan.get('job_id')}"
        })
        return jsonify({"plan": plan})

    # ── C2 & Payload Factory ──────────────────────────────────────────────

    @app.route("/api/c2/listen", methods=["POST"])
    def c2_listen():
        data = request.get_json()
        lhost = data.get("lhost", "0.0.0.0")
        lport = data.get("lport", 4444)
        plan = c2.start_listener(lhost, lport)
        socketio.emit("system_message", {
            "message": f"C2 Listener Initialized on {lhost}:{lport} (Job ID: {plan.get('job_id')})"
        })
        return jsonify({"plan": plan})

    @app.route("/api/c2/sessions", methods=["GET"])
    def c2_sessions():
        return jsonify(c2.get_sessions())

    @app.route("/api/factory/generate", methods=["POST"])
    def factory_generate():
        data = request.get_json()
        target_apk = data.get("target_apk", "/var/www/html/SystemUpdate.apk")
        lhost = data.get("lhost", "192.168.1.100")
        lport = data.get("lport", 4444)
        plan = factory.generate_backdoored_apk(target_apk, lhost, lport)
        socketio.emit("system_message", {
            "message": f"Payload Factory compiling infected APK (Job ID: {plan.get('job_id')})"
        })
        return jsonify({"plan": plan})

    # ── Memory Management ─────────────────────────────────────────────────

    @app.route("/api/memory/rules", methods=["GET"])
    def get_rules():
        """Get all learned ethics rules."""
        return jsonify({
            "rules": memory.get_ethics_rules(),
            "forbidden_targets": memory.get_forbidden_targets(),
            "forbidden_commands": memory.get_forbidden_commands_learned(),
            "pillars": memory.get_pillars(),
        })

    @app.route("/api/memory/targets", methods=["GET"])
    def get_targets():
        """Get all target profiles."""
        return jsonify({
            "targets": memory.get_all_targets(),
            "device_classes": memory.get_device_classes(),
        })

    @app.route("/api/memory/session", methods=["GET"])
    def get_session():
        """Get current session context."""
        return jsonify(memory.get_session())

    @app.route("/api/memory/target", methods=["POST"])
    def set_target():
        """Create or update a target profile."""
        data = request.get_json()
        ip = data.pop("ip", None)
        if not ip:
            return jsonify({"error": "IP required"}), 400
        profile = memory.set_target_profile(ip, **data)
        return jsonify({"ip": ip, "profile": profile})

    @app.route("/api/memory/token", methods=["POST"])
    def add_token():
        """Add an override token to the session."""
        data, error = _get_json_payload()
        if error:
            return error

        token = str(data.get("token", "")).strip()
        if not token:
            return jsonify({"error": "token required"}), 400
        if len(token) > 128:
            return jsonify({"error": "token too long (max 128 characters)"}), 400

        memory.add_override_token(token)
        return jsonify({"token": token, "added": True})

    # ── Loot Management ───────────────────────────────────────────────────

    @app.route("/api/loot", methods=["GET"])
    def list_loot():
        """List all files in the loot directory."""
        files = []
        try:
            for f in os.listdir(loot_dir):
                fpath = os.path.join(loot_dir, f)
                if os.path.isfile(fpath):
                    files.append({
                        "name": f,
                        "size": os.path.getsize(fpath),
                        "modified": datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc).isoformat(),
                    })
        except Exception as e:
            return jsonify({"files": [], "error": str(e)})
        return jsonify({"files": files})

    @app.route("/api/loot/<path:filename>", methods=["GET"])
    def download_loot(filename):
        """Download a specific loot file."""
        return send_from_directory(loot_dir, filename, as_attachment=True)

    # ── Kill Commands ─────────────────────────────────────────────────────

    @app.route("/api/kill/<int:cmd_id>", methods=["POST"])
    def kill_command(cmd_id):
        """Kill a running command by ID."""
        result = bridge.kill_command(cmd_id)
        return jsonify({"killed": result, "command_id": cmd_id})

    @app.route("/api/kill-all", methods=["POST"])
    def kill_all():
        """Kill all running commands."""
        bridge.kill_all()
        return jsonify({"status": "All processes terminated"})

    # ── WebSocket Events ──────────────────────────────────────────────────

    @socketio.on("connect")
    def handle_connect():
        chains.update_heartbeat()
        emit("connected", {"status": "GHOST v6.0 WebSocket connected"})

    @socketio.on("heartbeat")
    def handle_heartbeat(data):
        chains.update_heartbeat()

    @socketio.on("send_command")
    def handle_command(data):
        """Handle real-time command from terminal."""
        command = data.get("command", "")
        if command.startswith("/"):
            _handle_slash_command(command, socketio)
        else:
            # Route through LLM pipeline
            result = bridge.process_user_input(command)
            emit("chat_response", {
                "response": result["llm_response"],
                "commands": result["proposed_commands"],
                "verdicts": result["ethics_verdicts"],
            })

    @socketio.on("send_interactive_input")
    def handle_interactive_input(data):
        cmd_id = data.get("command_id")
        text = data.get("text", "")
        if cmd_id is not None:
            bridge.send_input(cmd_id, text)

    @socketio.on("approve_command")
    def handle_approve(data):
        command = data.get("command", "")
        result = bridge.approve_and_execute(command)
        emit("command_complete", {"command": command, "result": result})

    @socketio.on("send_feedback")
    def handle_feedback(data):
        result = ethics.process_feedback(
            data.get("type", ""),
            data.get("context", {}),
            data.get("details", {}),
        )
        emit("feedback_processed", result)

    # ── PTY Shell Events ──────────────────────────────────────────────────

    @socketio.on("pty_spawn")
    def handle_pty_spawn(data=None):
        """Spawn a persistent interactive shell."""
        shell_cmd = data.get("shell", None) if data else None
        success = pty_mgr.spawn(shell_cmd)
        if not success:
            emit("pty_error", {"error": "Failed to spawn shell. Is WSL/Kali installed?"})

    @socketio.on("pty_input")
    def handle_pty_input(data):
        """Relay keystrokes to the PTY shell."""
        text = data.get("data", "")
        if text:
            pty_mgr.write(text)

    @socketio.on("pty_resize")
    def handle_pty_resize(data):
        """Resize the PTY terminal."""
        rows = data.get("rows", 24)
        cols = data.get("cols", 80)
        pty_mgr.resize(rows, cols)

    @socketio.on("pty_kill")
    def handle_pty_kill(data=None):
        """Kill the PTY shell."""
        pty_mgr.kill()
        emit("pty_output", {"data": "\r\n\x1b[33m[PTY] Shell terminated by operator.\x1b[0m\r\n"})

    # ── Strategic Brain Control ───────────────────────────────────────────

    @socketio.on("halt_strategy")
    def handle_halt_strategy(data=None):
        """Halt the current Strategic Brain execution loop."""
        bridge.abort_strategy()
        emit("strategy_halted", {})

    # ── Slash Commands ────────────────────────────────────────────────────

    def _handle_slash_command(command, sio):
        """Handle /slash commands."""
        parts = command.strip().split()
        cmd = parts[0].lower()

        if cmd == "/mode":
            if len(parts) > 1:
                mode = parts[1].upper()
                memory.set_mode(mode)
                sio.emit("system_message", {"message": f"Mode changed to {mode}"})
            else:
                sio.emit("system_message", {"message": f"Current mode: {memory.get_mode()}"})

        elif cmd == "/stealth":
            current = memory.get_session().get("stealth", False)
            memory.set_stealth(not current)
            sio.emit("system_message", {"message": f"Stealth: {'ON' if not current else 'OFF'}"})

        elif cmd == "/status":
            status = memory.get_full_status()
            sio.emit("system_message", {"message": json.dumps(status, indent=2)})

        elif cmd == "/chains":
            available = chains.list_chains()
            msg = "Available Chains:\n" + "\n".join(
                f"  {name}: {info['description']}" for name, info in available.items()
            )
            sio.emit("system_message", {"message": msg})

        elif cmd == "/chain":
            if len(parts) > 1:
                chain_name = parts[1].upper()
                variables = {}
                for p in parts[2:]:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        variables[k] = v
                result = chains.start_chain(chain_name, variables)
                sio.emit("chain_started", result)
            else:
                sio.emit("system_message", {"message": json.dumps(chains.get_chain_status(), indent=2)})

        elif cmd == "/halt":
            result = chains.halt_chain()
            sio.emit("chain_halted", result)

        elif cmd == "/wrong":
            context = {"command": " ".join(parts[1:]), "pattern": " ".join(parts[1:])}
            result = ethics.process_feedback("WRONG", context)
            sio.emit("feedback_processed", result)

        elif cmd == "/model":
            if len(parts) > 1:
                bridge.change_model(parts[1])
                sio.emit("system_message", {"message": f"Model changed to {parts[1]}"})

        elif cmd == "/token":
            if len(parts) > 1:
                token = parts[1]
                memory.add_override_token(token)
                sio.emit("system_message", {"message": f"Token added: {token}"})

        elif cmd == "/kill":
            if len(parts) > 1 and parts[1] == "all":
                bridge.kill_all()
                sio.emit("system_message", {"message": "All processes terminated."})
            elif len(parts) > 1:
                bridge.kill_command(int(parts[1]))
                sio.emit("system_message", {"message": f"Process {parts[1]} terminated."})

        elif cmd == "/osint":
            if len(parts) > 1:
                seed = parts[1]
                plan = osint.build_recon_plan(seed)
                sio.emit("system_message", {
                    "message": f"OSINT Plan for [{plan['seed_type']}] '{seed}':\n" +
                               "\n".join(f"  Phase {p['phase']}: {p['name']}" for p in plan['phases'])
                })
                sio.emit("osint_started", {"seed": seed, "seed_type": plan["seed_type"]})
            else:
                sio.emit("system_message", {"message": "Usage: /osint <username|email|domain|IP>"})

        elif cmd == "/mobile" or cmd == "/adb":
            if len(parts) > 1:
                target_ip = parts[1]
                plan = mobile.build_control_plan(target_ip)
                sio.emit("system_message", {
                    "message": f"Mobile Control Plan for {target_ip}:\n" +
                               "\n".join(f"  Phase {p['phase']}: {p['name']}" for p in plan['phases'])
                })
                sio.emit("mobile_started", {"target": target_ip})
            else:
                sio.emit("system_message", {"message": "Usage: /mobile <target_ip>  or  /adb <target_ip>"})

        elif cmd == "/wireless" or cmd == "/wifi":
            plan = wireless.build_scan_plan(parts[1] if len(parts) > 1 else "wlan0")
            sio.emit("system_message", {
                "message": "Wireless Scan Plan:\n" +
                           "\n".join(f"  Phase {p['phase']}: {p['name']}" for p in plan['phases'])
            })
            sio.emit("wireless_started", {"type": "scan"})

        elif cmd == "/acquire" or cmd == "/hack":
            target_ip = parts[1] if len(parts) > 1 else None
            target_type = "phone" if len(parts) > 2 and "phone" in parts[2].lower() else "unknown"
            plan = acquisition.build_acquisition_plan(target_ip, target_type)
            vectors = _get_attack_vectors(plan)
            msg = f"""AUTONOMOUS TARGET ACQUISITION
  Target: {target_ip or 'AUTO-DISCOVER'}
  Type: {target_type}
  Strategy: {plan['strategy']}

  PHASES:
""" + "\n".join(f"  {p['phase']}. {p['name']}" for p in plan['phases']) + """

  ATTACK VECTORS (tried in order):
""" + "\n".join(f"    [{i+1}] {v['name']} — Success: {v['success_rate']}" for i, v in enumerate(vectors))
            sio.emit("system_message", {"message": msg})
            sio.emit("acquisition_started", {
                "target": target_ip or "auto-discover",
                "vectors": [v["name"] for v in vectors],
            })
            
        elif cmd == "/sdr":
            plan = resiliency.build_sdr_airgap_plan()
            sio.emit("system_message", {
                "message": "SDR AIRGAP JUMP:\n" +
                           "\n".join(f"  Phase {p['phase']}: {p['name']} ({'Hardware' if p['hardware'] else 'Software'})" for p in plan['phases'])
            })

        elif cmd == "/c2":
            tunnel_type = parts[1].upper() if len(parts) > 1 else "DNS"
            plan = resiliency.build_c2_tunnel_plan(tunnel_type=tunnel_type)
            sio.emit("system_message", {
                "message": f"SELF-HEALING C2 ({tunnel_type}):\n" +
                           "\n".join(f"  Phase {p['phase']}: {p['name']}" for p in plan['phases'])
            })

        elif cmd == "/traffic":
            interface = parts[1] if len(parts) > 1 else "eth0"
            plan = resiliency.apply_traffic_shaping(interface)
            sio.emit("system_message", {
                "message": f"TRAFFIC SHAPING ({interface}):\n  " + "\n  ".join(plan['commands'])
            })

        elif cmd == "/diagnose":
            diag_type = parts[1].lower() if len(parts) > 1 else "uaf"
            target_ip = parts[2] if len(parts) > 2 else "127.0.0.1"
            if diag_type == "zeroclick":
                plan = diagnostics.build_zero_click_plan(target_ip)
            elif diag_type == "persistence":
                plan = diagnostics.build_persistence_audit_plan(target_ip)
            elif diag_type == "telemetry":
                plan = diagnostics.build_memory_telemetry_plan(target_ip)
            else:
                plan = diagnostics.build_memory_corruption_plan(target_ip)
            
            sio.emit("system_message", {
                "message": f"DIAGNOSTIC ENGAGED ({plan['type']}):\n" +
                           "\n".join(f"  Phase {p['phase']}: {p['name']}" for p in plan['phases'])
            })

        elif cmd == "/arsenal":
            target = parts[1] if len(parts) > 1 else "target_binary"
            plan = arsenal.synthesize_zeroday(target)
            sio.emit("system_message", {
                "message": f"ARSENAL ZERO-DAY SYNTHESIS ENGAGED:\nJob ID: {plan.get('job_id')}\nTarget: {target}\n  " + 
                           "\n  ".join(f"Phase {p['phase']}: {p['name']}" for p in plan['phases'])
            })

        elif cmd == "/help":
            help_text = """GHOST v6.0 — Slash Commands:

  ── Core ──────────────────────────────────────────
  /mode [TEACHING|SUPERVISED|AUTONOMOUS|STEALTH]  — Change mode
  /stealth                — Toggle stealth mode
  /status                 — Show system status
  /model <name>           — Change LLM model
  /token <TOKEN>          — Add override token
  /kill <id|all>          — Kill running command(s)

  ── Attack Chains ─────────────────────────────────
  /chains                 — List available chains
  /chain <name> [vars]    — Start a chain
  /halt                   — Halt active chain

  ── Engines ───────────────────────────────────────
  /osint <seed>           — OSINT recon (username/email/domain/IP)
  /mobile <target_ip>     — Mobile/ADB control workflow
  /adb <target_ip>        — Same as /mobile
  /wireless [interface]   — WiFi scan & attack
  /wifi [interface]       — Same as /wireless
  /acquire [target_ip]    — Autonomous target acquisition
  /hack [target_ip]       — Same as /acquire

  ── v6.0 Advanced ─────────────────────────────────
  /diagnose <type> [ip]   — Kernel diagnostics (uaf|zeroclick|persistence|telemetry)
  /arsenal <binary>       — Autonomous zero-day fuzzing synthesis
  /sdr [freq]             — SDR air-gap jump (HackRF auto-detect)
  /c2 <DNS|ICMP> [domain] — Self-healing covert C2 tunnel
  /traffic [interface]    — Quantum-stealth traffic shaping

  ── Training ──────────────────────────────────────
  /wrong <action>         — Mark action as WRONG (permanent prohibition)

  /help                   — Show this help"""
            sio.emit("system_message", {"message": help_text})

        else:
            sio.emit("system_message", {"message": f"Unknown command: {cmd}. Type /help for commands."})

    # ── Helpers ────────────────────────────────────────────────────────────

    def _get_attack_vectors(plan):
        """Safely extract attack vectors from any phase in an acquisition plan."""
        for phase in plan.get("phases", []):
            vectors = phase.get("attack_vectors", [])
            if vectors:
                return vectors
        return []

    def _detect_environment():
        """Detect the runtime environment."""
        env = {
            "os": platform.system(),
            "os_version": platform.version(),
            "hostname": platform.node(),
            "type": "UNKNOWN",
        }

        # VM detection
        try:
            if os.path.exists("/sys/class/dmi/id/product_name"):
                with open("/sys/class/dmi/id/product_name") as f:
                    product = f.read().strip().lower()
                    if "vmware" in product:
                        env["type"] = "VMware"
                    elif "virtualbox" in product:
                        env["type"] = "VirtualBox"
                    elif "kvm" in product or "qemu" in product:
                        env["type"] = "KVM"
                    else:
                        env["type"] = "BARE-METAL ⚠️"
            else:
                env["type"] = f"{platform.system()} (VM detection unavailable)"
        except Exception:
            env["type"] = f"{platform.system()}"

        return env

    def _get_autonomy_display(mem):
        """Get autonomy matrix for display."""
        categories = [
            "reconnaissance", "vulnerability_analysis", "exploitation",
            "ad_enterprise", "wireless", "social_engineering",
            "osint", "password_cracking", "defense",
        ]
        return {cat: mem.get_autonomy_policy(cat) for cat in categories}

    return app, socketio


# ── Direct Run ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app, socketio = create_app()
    print("\n" + "═" * 60)
    print("  GHOST v6.0 — Command Center Starting")
    print("  http://localhost:5000")
    print("═" * 60 + "\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
