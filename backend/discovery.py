"""
GHOST v6.0 — Zero-Knowledge Discovery Engine
Autonomous environment mapping from zero information.
4-phase protocol: Local Recon → Host Discovery → Service Enum → Intelligence Synthesis
"""

import re
from datetime import datetime, timezone


class DiscoveryEngine:
    """
    Zero-Knowledge Discovery — maps entire network without any prior target info.
    Triggered by: "find everything", "map network", "show me what's here", "discover targets"
    """

    TRIGGER_PHRASES = [
        "find everything", "map network", "show me what's here",
        "discover targets", "discover", "scan network", "what's here",
        "map everything", "recon", "zero knowledge", "find hosts",
        "network scan", "find devices",
    ]

    PRIORITY_PORTS = [
        21, 22, 23, 25, 53, 80, 88, 110, 135, 139, 143, 389, 443, 445,
        993, 995, 1433, 1521, 3306, 3389, 5432, 5555, 5900, 5985, 6379,
        8080, 8443, 9200, 27017, 2375,
    ]

    QUICK_WIN_CHECKS = {
        5555: {"risk": "ADB WIRELESS", "class": "iot", "severity": "HIGH"},
        2375: {"risk": "Docker API exposed", "class": "server", "severity": "CRITICAL"},
        6379: {"risk": "Redis exposed", "class": "server", "severity": "HIGH"},
        3389: {"risk": "RDP enabled", "class": "workstation", "severity": "MEDIUM"},
        445: {"risk": "SMB enabled", "class": "workstation", "severity": "MEDIUM"},
        23: {"risk": "Telnet (unencrypted)", "class": "network_infrastructure", "severity": "HIGH"},
        21: {"risk": "FTP (check anonymous)", "class": "server", "severity": "MEDIUM"},
        88: {"risk": "Kerberos (Domain Controller)", "class": "domain_controller", "severity": "CRITICAL"},
        5985: {"risk": "WinRM enabled", "class": "server", "severity": "MEDIUM"},
        27017: {"risk": "MongoDB exposed", "class": "server", "severity": "HIGH"},
        9200: {"risk": "Elasticsearch exposed", "class": "server", "severity": "HIGH"},
    }

    # OS detection heuristics from open ports
    OS_HINTS = {
        frozenset([88, 135, 139, 389, 445, 5985]): "Windows Server (AD DC)",
        frozenset([135, 139, 445, 3389]): "Windows Workstation",
        frozenset([135, 445]): "Windows",
        frozenset([22, 80]): "Linux",
        frozenset([22, 80, 443]): "Linux Server",
        frozenset([22, 80, 3306]): "Linux (MySQL)",
        frozenset([22, 80, 5432]): "Linux (PostgreSQL)",
        frozenset([5555]): "Android (ADB)",
        frozenset([62078]): "iOS",
        frozenset([80, 443]): "Web Server / Router",
        frozenset([161, 22]): "Network Device (SNMP)",
    }

    def __init__(self, memory_manager, ethics_engine, bridge):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.bridge = bridge

    def is_discovery_request(self, user_input):
        """Check if user input is a zero-knowledge discovery trigger."""
        lower = user_input.lower().strip()
        return any(phrase in lower for phrase in self.TRIGGER_PHRASES)

    def get_phase_commands(self, phase, subnet=None, live_hosts=None):
        """Get commands for a specific discovery phase."""
        commands = {
            1: self._phase1_local_recon(),
            2: self._phase2_host_discovery(subnet),
            3: self._phase3_service_enum(live_hosts or []),
            4: [],  # Synthesis is done in code, not commands
        }
        return commands.get(phase, [])

    def _phase1_local_recon(self):
        """Phase 1: Local Environment Reconnaissance."""
        return [
            {
                "description": "Enumerate network interfaces",
                "command": "ip addr" if not self._is_windows() else "ipconfig /all",
                "category": "RECON",
                "parse": "interfaces",
            },
            {
                "description": "Show routing table",
                "command": "ip route" if not self._is_windows() else "route print",
                "category": "RECON",
                "parse": "routes",
            },
            {
                "description": "Check DNS configuration",
                "command": "cat /etc/resolv.conf" if not self._is_windows() else "nslookup localhost",
                "category": "RECON",
                "parse": "dns",
            },
            {
                "description": "Show ARP cache (passive host hints)",
                "command": "arp -a",
                "category": "RECON",
                "parse": "arp",
            },
        ]

    def _phase2_host_discovery(self, subnet=None):
        """Phase 2: Host Discovery (escalating intrusiveness)."""
        if not subnet:
            subnet = "192.168.1.0/24"  # Default, will be replaced by Phase 1 results

        is_stealth = self.memory.get_session().get("stealth", False)

        commands = [
            {
                "description": "Passive ARP discovery",
                "command": f"netdiscover -r {subnet} -P -c 20",
                "category": "RECON",
                "subcategory": "passive",
                "parse": "hosts",
            },
        ]

        if is_stealth:
            commands.append({
                "description": "Stealth ICMP sweep (1 pkt/sec)",
                "command": f"nmap -sn -PE -PP -PM --max-rate 1 {subnet}",
                "category": "RECON",
                "subcategory": "active",
                "parse": "hosts",
            })
        else:
            commands.extend([
                {
                    "description": "ICMP sweep",
                    "command": f"nmap -sn -PE -PP -PM {subnet}",
                    "category": "RECON",
                    "subcategory": "active",
                    "parse": "hosts",
                },
                {
                    "description": "Fast host discovery via masscan",
                    "command": f"masscan {subnet} -p0 --rate=1000",
                    "category": "RECON",
                    "subcategory": "active",
                    "parse": "hosts",
                },
            ])

        return commands

    def _phase3_service_enum(self, live_hosts):
        """Phase 3: Service Enumeration & Vulnerability Triage."""
        if not live_hosts:
            return []

        hosts_str = " ".join(live_hosts)
        ports_str = ",".join(str(p) for p in self.PRIORITY_PORTS)

        commands = [
            {
                "description": "Full service version scan on discovered hosts",
                "command": f"nmap -sV -sC -O --version-intensity 5 -p {ports_str} {hosts_str}",
                "category": "RECON",
                "parse": "services",
            },
        ]

        # Quick win checks per host
        for host in live_hosts:
            commands.append({
                "description": f"SMB enumeration on {host}",
                "command": f"nmap --script smb-os-discovery,smb-security-mode -p 445 {host}",
                "category": "RECON",
                "parse": "smb",
            })

        return commands

    def parse_interfaces(self, output):
        """Parse 'ip addr' output to extract interface information."""
        interfaces = []
        current = None

        for line in output.split("\n"):
            # Match interface line
            iface_match = re.match(r"^\d+:\s+(\S+):", line)
            if iface_match:
                if current:
                    interfaces.append(current)
                current = {"name": iface_match.group(1), "ips": [], "type": "unknown"}

            if current:
                # Match IPv4 address
                ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+/\d+)", line)
                if ip_match:
                    current["ips"].append(ip_match.group(1))

                # Classify type
                if "wireless" in line.lower() or "wlan" in current["name"]:
                    current["type"] = "wireless"
                elif "eth" in current["name"] or "en" in current["name"]:
                    current["type"] = "wired"
                elif "tun" in current["name"] or "tap" in current["name"]:
                    current["type"] = "tunnel"
                elif "lo" == current["name"]:
                    current["type"] = "loopback"

        if current:
            interfaces.append(current)

        return [i for i in interfaces if i["type"] != "loopback"]

    def parse_routes(self, output):
        """Parse 'ip route' output to extract routing information."""
        routes = []
        gateway = None
        subnet = None

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith("default"):
                gw_match = re.search(r"via\s+(\d+\.\d+\.\d+\.\d+)", line)
                if gw_match:
                    gateway = gw_match.group(1)
                    routes.append({"type": "default", "gateway": gateway})
            else:
                subnet_match = re.match(r"(\d+\.\d+\.\d+\.\d+/\d+)", line)
                if subnet_match:
                    subnet = subnet_match.group(1)
                    routes.append({"type": "connected", "subnet": subnet})

        return {"routes": routes, "gateway": gateway, "local_subnet": subnet}

    def parse_nmap_hosts(self, output):
        """Parse nmap ping sweep output for live hosts."""
        hosts = []
        current_ip = None

        for line in output.split("\n"):
            ip_match = re.search(r"Nmap scan report for\s+(?:(\S+)\s+\()?(\d+\.\d+\.\d+\.\d+)", line)
            if ip_match:
                hostname = ip_match.group(1) or ""
                ip = ip_match.group(2)
                current_ip = ip
                hosts.append({"ip": ip, "hostname": hostname, "status": "up"})

            if "Host is up" in line and current_ip:
                latency_match = re.search(r"\((.+?)\)", line)
                if latency_match and hosts:
                    hosts[-1]["latency"] = latency_match.group(1)

        return hosts

    def parse_nmap_services(self, output):
        """Parse nmap service scan output."""
        hosts = {}
        current_ip = None

        for line in output.split("\n"):
            # Host header
            ip_match = re.search(r"Nmap scan report for\s+(?:(\S+)\s+\()?(\d+\.\d+\.\d+\.\d+)", line)
            if ip_match:
                hostname = ip_match.group(1) or ""
                current_ip = ip_match.group(2)
                hosts[current_ip] = {
                    "hostname": hostname,
                    "ports": [],
                    "os": "",
                    "risk_flags": [],
                }

            # Port line
            port_match = re.match(r"(\d+)/(tcp|udp)\s+(open|filtered)\s+(\S+)\s*(.*)", line.strip())
            if port_match and current_ip:
                port = int(port_match.group(1))
                state = port_match.group(3)
                service = port_match.group(4)
                version = port_match.group(5).strip()

                hosts[current_ip]["ports"].append({
                    "port": port,
                    "state": state,
                    "service": service,
                    "version": version,
                })

                # Quick win check
                if port in self.QUICK_WIN_CHECKS:
                    qw = self.QUICK_WIN_CHECKS[port]
                    hosts[current_ip]["risk_flags"].append(qw["risk"])

            # OS detection
            os_match = re.search(r"OS details:\s+(.+)", line)
            if os_match and current_ip:
                hosts[current_ip]["os"] = os_match.group(1)

            # Aggressive OS guess
            os_match2 = re.search(r"Running:\s+(.+)", line)
            if os_match2 and current_ip and not hosts[current_ip]["os"]:
                hosts[current_ip]["os"] = os_match2.group(1)

        # Infer OS from ports if not detected
        for ip, info in hosts.items():
            if not info["os"]:
                open_ports = frozenset(p["port"] for p in info["ports"])
                for port_set, os_name in self.OS_HINTS.items():
                    if port_set.issubset(open_ports):
                        info["os"] = os_name
                        break

        return hosts

    def synthesize_intelligence(self, hosts_data):
        """
        Phase 4: Compile all findings into the intelligence report.
        Returns formatted report + recommended attack chains.
        """
        if not hosts_data:
            return {"report": "No hosts discovered.", "recommendations": []}

        # Detect gateway
        session = self.memory.get_session()
        gateway_ip = None
        for host in self.memory.get_session().get("discovered_hosts", []):
            if "gateway" in str(host.get("risk_flags", [])).lower():
                gateway_ip = host.get("ip")

        recommendations = []
        report_lines = []

        for ip, info in hosts_data.items():
            hostname = info.get("hostname", "[unknown]")
            os_type = info.get("os", "[unknown]")
            ports = [str(p["port"]) for p in info.get("ports", [])]
            risks = info.get("risk_flags", [])

            # Store in session
            self.memory.add_discovered_host(
                ip=ip,
                hostname=hostname,
                os_info=os_type,
                ports=ports,
                risk_flags=risks,
            )

            # Auto-classify device
            open_ports = [p["port"] for p in info.get("ports", [])]
            device_class = self._infer_device_class(open_ports, os_type)

            report_lines.append({
                "ip": ip,
                "hostname": hostname,
                "os": os_type,
                "ports": ", ".join(ports),
                "risks": risks,
                "class": device_class,
            })

            # Generate recommended chains
            rec = self._recommend_chain(ip, hostname, os_type, open_ports, risks, device_class)
            if rec:
                recommendations.append(rec)

        return {
            "report": report_lines,
            "recommendations": recommendations,
            "total_hosts": len(hosts_data),
            "gateway": gateway_ip,
        }

    def format_report(self, synthesis):
        """Format synthesis into the spec's table format."""
        lines = [
            "═" * 70,
            "ZERO-KNOWLEDGE RECON COMPLETE",
            f"Discovered: {synthesis['total_hosts']} hosts",
            "═" * 70,
            "",
            f"{'IP':<16} {'Hostname':<14} {'OS/Type':<18} {'Ports':<14} {'Risk Flags'}",
            "─" * 70,
        ]

        for host in synthesis.get("report", []):
            risks_str = ", ".join(host.get("risks", []))[:30]
            lines.append(
                f"{host['ip']:<16} {host['hostname']:<14} {host['os']:<18} "
                f"{host['ports']:<14} {risks_str}"
            )

        lines.extend(["", "─" * 70, "", "RECOMMENDED CHAINS:"])

        for rec in synthesis.get("recommendations", []):
            lines.append(f"  → {rec['target']}: {rec['chain']}")

        lines.extend(["", "═" * 70])
        return "\n".join(lines)

    def _infer_device_class(self, ports, os_info):
        """Infer device class from open ports and OS information."""
        os_lower = os_info.lower() if os_info else ""

        if 88 in ports and 389 in ports:
            return "domain_controller"
        if "android" in os_lower or 5555 in ports:
            return "mobile"
        if any(kw in os_lower for kw in ["router", "switch", "mikrotik", "cisco"]):
            return "network_infrastructure"
        if any(kw in os_lower for kw in ["tv", "iot", "smart", "alexa", "ring", "nest"]):
            return "iot"
        if any(kw in os_lower for kw in ["server", "ubuntu", "centos", "debian"]):
            return "server"
        if any(kw in os_lower for kw in ["windows 10", "windows 11", "workstation"]):
            return "workstation"

        # Port-based inference
        if set(ports).intersection({80, 443, 8080, 3306, 5432}):
            return "server"
        if 3389 in ports:
            return "workstation"

        return "unknown"

    def _recommend_chain(self, ip, hostname, os_type, ports, risks, device_class):
        """Generate attack chain recommendation for a host."""
        os_lower = (os_type or "").lower()

        if device_class == "domain_controller":
            return {
                "target": f"{ip} ({hostname})",
                "chain": "BloodHound → Kerberoasting → Domain Admin (AD Chain)",
                "template": "AD_CHAIN",
                "risk": "CRITICAL",
            }

        if 80 in ports or 443 in ports or 8080 in ports:
            has_db = any(p in ports for p in [3306, 5432, 1433, 1521, 27017])
            if has_db:
                return {
                    "target": f"{ip} ({hostname})",
                    "chain": "Gobuster → WPScan → Advanced SQLMap → Shell",
                    "template": "ADVANCED_WEB_ARSENAL",
                    "risk": "HIGH",
                }
            return {
                "target": f"{ip} ({hostname})",
                "chain": "Deep Enum (Gobuster) → Fingerprint (Nikto/WPScan) → Shell",
                "template": "ADVANCED_WEB_ARSENAL",
                "risk": "MEDIUM",
            }

        if device_class == "server" and not (80 in ports or 443 in ports):
            return {
                "target": f"{ip} ({hostname})",
                "chain": "SearchSploit CVE → Auto-Generate MSF Script → Reverse Shell",
                "template": "METASPLOIT_AUTO_PWN",
                "risk": "HIGH",
            }

        if 445 in ports and 3389 in ports:
            return {
                "target": f"{ip} ({hostname})",
                "chain": "Responder → NTLM capture → Relay → Local Admin",
                "template": "AD_CHAIN",
                "risk": "MEDIUM",
            }

        if 5555 in ports:
            return {
                "target": f"{ip} ({hostname})",
                "chain": "ADB connect → Screen mirror → [IoT RESTRICTED]",
                "template": "MOBILE_CHAIN",
                "risk": "HIGH",
            }

        if 22 in ports:
            return {
                "target": f"{ip} ({hostname})",
                "chain": "SSH brute force → Shell → Privesc",
                "template": "WEB_COMPROMISE",
                "risk": "LOW",
            }

        return None

    def _is_windows(self):
        """Check if running on Windows."""
        import platform
        return platform.system().lower() == "windows"
