"""
GHOST v6.0 — Tool Output Parser (Enhancement #2)
Automatically extracts structured intelligence from command output.
Parses: nmap, masscan, arp-scan, netdiscover, nikto, enum4linux, gobuster, etc.
Populates session context and neural memory with discovered hosts, ports, OS, services.
"""

import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger("ghost.parsers")


class ToolOutputParser:
    """
    Extracts structured intelligence from raw tool output.
    Called after every command execution to auto-populate the target map.
    """

    @staticmethod
    def parse(command, stdout, stderr=""):
        """
        Route to the correct parser based on the tool name.
        Returns a dict of parsed intelligence or None if no parser matches.

        Result format:
        {
            "parser": "nmap",
            "hosts": [
                {
                    "ip": "192.168.1.1",
                    "hostname": "router.local",
                    "os": "Linux 4.15",
                    "ports": [22, 80, 443],
                    "services": [
                        {"port": 22, "protocol": "tcp", "service": "ssh", "version": "OpenSSH 8.2"},
                        {"port": 80, "protocol": "tcp", "service": "http", "version": "Apache 2.4.41"},
                    ],
                    "status": "up",
                }
            ],
            "raw_summary": "3 hosts up, 12 open ports",
        }
        """
        if not stdout:
            return None

        combined = stdout + "\n" + (stderr or "")
        tool = command.strip().split()[0].lower() if command else ""

        # Strip 'sudo' and 'wsl' prefixes
        cmd_parts = command.strip().split()
        for skip in ("sudo", "wsl", "-d", "kali-linux", "--", "bash", "-c", "-li"):
            if cmd_parts and cmd_parts[0].lower() == skip:
                cmd_parts.pop(0)
        tool = cmd_parts[0].lower() if cmd_parts else ""

        parsers = {
            "nmap": ToolOutputParser._parse_nmap,
            "masscan": ToolOutputParser._parse_masscan,
            "arp-scan": ToolOutputParser._parse_arp_scan,
            "netdiscover": ToolOutputParser._parse_netdiscover,
            "nikto": ToolOutputParser._parse_nikto,
            "enum4linux": ToolOutputParser._parse_enum4linux,
            "gobuster": ToolOutputParser._parse_gobuster,
            "adb": ToolOutputParser._parse_adb,
            "hydra": ToolOutputParser._parse_hydra,
            "searchsploit": ToolOutputParser._parse_searchsploit,
            "whatweb": ToolOutputParser._parse_whatweb,
        }

        parser_fn = parsers.get(tool)
        if parser_fn:
            try:
                result = parser_fn(combined, command)
                if result:
                    result["parser"] = tool
                    result["parsed_at"] = datetime.now(timezone.utc).isoformat()
                    logger.info(
                        f"[Parser:{tool}] Extracted {len(result.get('hosts', []))} hosts, "
                        f"{sum(len(h.get('ports', [])) for h in result.get('hosts', []))} ports"
                    )
                    return result
            except Exception as e:
                logger.warning(f"Parser error ({tool}): {e}")

        return None

    # ═══════════════════════════════════════════════════════════════
    #  Nmap Parser — the most critical one
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_nmap(output, command=""):
        """Parse nmap output (normal/grepable format)."""
        hosts = []
        current_host = None

        for line in output.split("\n"):
            line = line.strip()

            # Host detection: "Nmap scan report for 192.168.1.1" or "... hostname (ip)"
            host_match = re.match(
                r"Nmap scan report for\s+(?:(\S+)\s+\()?(\d+\.\d+\.\d+\.\d+)\)?",
                line
            )
            if not host_match:
                # Also match: "Nmap scan report for 192.168.1.1"
                host_match = re.match(
                    r"Nmap scan report for\s+(\d+\.\d+\.\d+\.\d+)",
                    line
                )
                if host_match:
                    ip = host_match.group(1)
                    hostname = ""
                else:
                    host_match = None

            if host_match and host_match.lastindex and host_match.lastindex >= 2:
                hostname = host_match.group(1) or ""
                ip = host_match.group(2)
            elif host_match:
                ip = host_match.group(1)
                hostname = ""

            if host_match:
                if current_host:
                    hosts.append(current_host)
                current_host = {
                    "ip": ip,
                    "hostname": hostname,
                    "os": "",
                    "ports": [],
                    "services": [],
                    "status": "up",
                }
                continue

            if not current_host:
                continue

            # Port line: "22/tcp   open  ssh     OpenSSH 8.2p1"
            port_match = re.match(
                r"(\d+)/(tcp|udp)\s+(open|filtered|closed)\s+(\S+)\s*(.*)",
                line
            )
            if port_match:
                port_num = int(port_match.group(1))
                protocol = port_match.group(2)
                state = port_match.group(3)
                service = port_match.group(4)
                version = port_match.group(5).strip()

                if state in ("open", "filtered"):
                    current_host["ports"].append(port_num)
                    current_host["services"].append({
                        "port": port_num,
                        "protocol": protocol,
                        "state": state,
                        "service": service,
                        "version": version,
                    })
                continue

            # OS detection: "OS details: Linux 4.15 - 5.6"
            os_match = re.match(r"OS details?:\s+(.+)", line)
            if os_match:
                current_host["os"] = os_match.group(1).strip()
                continue

            # Aggressive OS guess: "Running: Linux 4.X|5.X"
            running_match = re.match(r"Running:\s+(.+)", line)
            if running_match and not current_host["os"]:
                current_host["os"] = running_match.group(1).strip()
                continue

            # MAC address: "MAC Address: AA:BB:CC:DD:EE:FF (Vendor)"
            mac_match = re.match(r"MAC Address:\s+(\S+)\s*(?:\((.+)\))?", line)
            if mac_match:
                current_host["mac"] = mac_match.group(1)
                vendor = mac_match.group(2)
                if vendor:
                    current_host["vendor"] = vendor
                continue

        # Don't forget the last host
        if current_host:
            hosts.append(current_host)

        if not hosts:
            # Try grepable format: "Host: 192.168.1.1 ()  Ports: 22/open/tcp//ssh//..."
            for line in output.split("\n"):
                grep_match = re.match(r"Host:\s+(\S+)\s+\(([^)]*)\)\s+Ports:\s+(.*)", line)
                if grep_match:
                    ip = grep_match.group(1)
                    hostname = grep_match.group(2)
                    ports_str = grep_match.group(3)
                    host = {
                        "ip": ip,
                        "hostname": hostname,
                        "os": "",
                        "ports": [],
                        "services": [],
                        "status": "up",
                    }
                    for port_entry in ports_str.split(","):
                        parts = port_entry.strip().split("/")
                        if len(parts) >= 5 and parts[1] == "open":
                            port_num = int(parts[0])
                            host["ports"].append(port_num)
                            host["services"].append({
                                "port": port_num,
                                "protocol": parts[2],
                                "state": "open",
                                "service": parts[4],
                                "version": parts[6] if len(parts) > 6 else "",
                            })
                    hosts.append(host)

        if not hosts:
            return None

        total_ports = sum(len(h["ports"]) for h in hosts)
        return {
            "hosts": hosts,
            "raw_summary": f"{len(hosts)} host(s) discovered, {total_ports} open port(s)",
        }

    # ═══════════════════════════════════════════════════════════════
    #  Other Tool Parsers
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_masscan(output, command=""):
        """Parse masscan output."""
        hosts = {}
        for line in output.split("\n"):
            # "Discovered open port 80/tcp on 192.168.1.5"
            match = re.match(r"Discovered open port (\d+)/(tcp|udp) on (\S+)", line)
            if match:
                port = int(match.group(1))
                ip = match.group(3)
                if ip not in hosts:
                    hosts[ip] = {"ip": ip, "hostname": "", "os": "", "ports": [], "services": [], "status": "up"}
                if port not in hosts[ip]["ports"]:
                    hosts[ip]["ports"].append(port)
                    hosts[ip]["services"].append({
                        "port": port, "protocol": match.group(2),
                        "state": "open", "service": "", "version": ""
                    })

        if not hosts:
            return None
        host_list = list(hosts.values())
        return {
            "hosts": host_list,
            "raw_summary": f"{len(host_list)} host(s), {sum(len(h['ports']) for h in host_list)} port(s)",
        }

    @staticmethod
    def _parse_arp_scan(output, command=""):
        """Parse arp-scan output."""
        hosts = []
        for line in output.split("\n"):
            # "192.168.1.1\t00:aa:bb:cc:dd:ee\tTP-Link Technologies"
            match = re.match(r"(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+(.*)", line)
            if match:
                ip = match.group(1)
                mac = match.group(2)
                vendor = match.group(3).strip()
                # Validate MAC format
                if re.match(r"[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}", mac):
                    hosts.append({
                        "ip": ip, "hostname": "", "os": "", "ports": [],
                        "services": [], "status": "up", "mac": mac, "vendor": vendor,
                    })

        if not hosts:
            return None
        return {"hosts": hosts, "raw_summary": f"{len(hosts)} host(s) via ARP scan"}

    @staticmethod
    def _parse_netdiscover(output, command=""):
        """Parse netdiscover -P output."""
        hosts = []
        for line in output.split("\n"):
            # "192.168.1.1     00:aa:bb:cc:dd:ee      1      60  TP-Link"
            match = re.match(r"\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]{17})\s+\d+\s+\d+\s+(.*)", line)
            if match:
                hosts.append({
                    "ip": match.group(1), "hostname": "", "os": "", "ports": [],
                    "services": [], "status": "up", "mac": match.group(2),
                    "vendor": match.group(3).strip(),
                })

        if not hosts:
            return None
        return {"hosts": hosts, "raw_summary": f"{len(hosts)} host(s) via netdiscover"}

    @staticmethod
    def _parse_nikto(output, command=""):
        """Parse nikto output for web vulnerabilities."""
        findings = []
        target_ip = ""

        for line in output.split("\n"):
            # "+ Target IP: 192.168.1.5"
            ip_match = re.match(r"\+ Target IP:\s+(\S+)", line)
            if ip_match:
                target_ip = ip_match.group(1)

            # "+ OSVDB-xxxx: /path: description"
            vuln_match = re.match(r"\+ (OSVDB-\d+|[A-Z][\w-]+):\s+(.+)", line)
            if vuln_match:
                findings.append({
                    "id": vuln_match.group(1),
                    "detail": vuln_match.group(2).strip(),
                })

        if not findings:
            return None

        hosts = []
        if target_ip:
            hosts.append({
                "ip": target_ip, "hostname": "", "os": "", "ports": [80],
                "services": [], "status": "up",
                "vulnerabilities": findings,
            })

        return {
            "hosts": hosts,
            "findings": findings,
            "raw_summary": f"{len(findings)} finding(s) on {target_ip}",
        }

    @staticmethod
    def _parse_enum4linux(output, command=""):
        """Parse enum4linux output for SMB/AD intelligence."""
        intel = {"shares": [], "users": [], "groups": [], "os_info": ""}
        target_ip = ""

        for line in output.split("\n"):
            # Target
            ip_match = re.search(r"Target\s+\.+\s+(\S+)", line)
            if ip_match:
                target_ip = ip_match.group(1)

            # Shares: "//ip/share  Mapping: OK, Listing: OK"
            share_match = re.search(r"//\S+/(\S+)\s+Mapping:\s+(\w+)", line)
            if share_match:
                intel["shares"].append(share_match.group(1))

            # Users: "user:[username] rid:[0x...]"
            user_match = re.search(r"user:\[(\S+)\]\s+rid:", line)
            if user_match:
                intel["users"].append(user_match.group(1))

            # OS info
            os_match = re.search(r"OS=\[([^\]]+)\]", line)
            if os_match:
                intel["os_info"] = os_match.group(1)

        if not target_ip and not intel["users"] and not intel["shares"]:
            return None

        hosts = []
        if target_ip:
            hosts.append({
                "ip": target_ip, "hostname": "", "os": intel["os_info"],
                "ports": [445], "services": [], "status": "up",
                "smb_shares": intel["shares"], "smb_users": intel["users"],
            })

        return {
            "hosts": hosts,
            "smb_intel": intel,
            "raw_summary": f"{len(intel['users'])} user(s), {len(intel['shares'])} share(s) on {target_ip}",
        }

    @staticmethod
    def _parse_gobuster(output, command=""):
        """Parse gobuster dir output."""
        paths = []
        for line in output.split("\n"):
            # "/admin (Status: 200)"
            match = re.match(r"(/\S+)\s+\(Status:\s+(\d+)\)", line)
            if match:
                paths.append({
                    "path": match.group(1),
                    "status": int(match.group(2)),
                })

        if not paths:
            return None

        target_ip = ""
        ip_match = re.search(r"-u\s+https?://(\S+?)(?:[:/]|$)", command)
        if ip_match:
            target_ip = ip_match.group(1)

        return {
            "hosts": [{"ip": target_ip, "hostname": "", "os": "", "ports": [80],
                        "services": [], "status": "up", "web_paths": paths}] if target_ip else [],
            "web_paths": paths,
            "raw_summary": f"{len(paths)} path(s) discovered",
        }

    @staticmethod
    def _parse_adb(output, command=""):
        """Parse adb devices/shell output."""
        devices = []
        for line in output.split("\n"):
            # "192.168.1.5:5555    device"
            match = re.match(r"(\S+)\s+(device|unauthorized|offline)", line)
            if match and match.group(1) != "List":
                addr = match.group(1)
                ip = addr.split(":")[0] if ":" in addr else addr
                devices.append({
                    "ip": ip, "hostname": "", "os": "Android", "ports": [5555],
                    "services": [{"port": 5555, "protocol": "tcp", "state": "open",
                                  "service": "adb", "version": ""}],
                    "status": match.group(2),
                })

        if not devices:
            return None
        return {"hosts": devices, "raw_summary": f"{len(devices)} ADB device(s)"}

    @staticmethod
    def _parse_hydra(output, command=""):
        """Parse hydra output for cracked credentials."""
        creds = []
        for line in output.split("\n"):
            # "[22][ssh] host: 192.168.1.5   login: admin   password: secret123"
            match = re.search(
                r"\[(\d+)\]\[(\w+)\]\s+host:\s+(\S+)\s+login:\s+(\S+)\s+password:\s+(\S+)",
                line
            )
            if match:
                creds.append({
                    "port": int(match.group(1)),
                    "service": match.group(2),
                    "host": match.group(3),
                    "username": match.group(4),
                    "password": match.group(5),
                })

        if not creds:
            return None
        return {
            "hosts": [],
            "credentials": creds,
            "raw_summary": f"{len(creds)} credential(s) cracked",
        }

    @staticmethod
    def _parse_searchsploit(output, command=""):
        """Parse searchsploit output for exploit references."""
        exploits = []
        for line in output.split("\n"):
            # "Apache 2.4.49 - Path Traversal | exploits/multiple/remote/50383.py"
            match = re.match(r"\s*(.+?)\s+\|\s+(exploits/\S+)", line)
            if match:
                exploits.append({
                    "title": match.group(1).strip(),
                    "path": match.group(2).strip(),
                })

        if not exploits:
            return None
        return {
            "hosts": [],
            "exploits": exploits,
            "raw_summary": f"{len(exploits)} exploit(s) found",
        }

    @staticmethod
    def _parse_whatweb(output, command=""):
        """Parse whatweb output for web technology fingerprinting."""
        technologies = []
        target_ip = ""

        for line in output.split("\n"):
            # "http://192.168.1.5 [200 OK] Apache[2.4.41], PHP[7.4.3]"
            match = re.match(r"https?://(\S+)\s+\[(\d+ [^\]]+)\]\s+(.*)", line)
            if match:
                target_ip = match.group(1).split(":")[0].split("/")[0]
                techs = match.group(3)
                for tech in re.findall(r"(\w[\w.-]+)(?:\[([^\]]+)\])?", techs):
                    technologies.append({
                        "name": tech[0],
                        "version": tech[1] if tech[1] else "",
                    })

        if not technologies:
            return None

        return {
            "hosts": [{"ip": target_ip, "hostname": "", "os": "", "ports": [80],
                        "services": [], "status": "up",
                        "technologies": technologies}] if target_ip else [],
            "technologies": technologies,
            "raw_summary": f"{len(technologies)} technology/ies detected",
        }

