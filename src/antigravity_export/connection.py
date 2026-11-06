"""
Language Server discovery, port resolution, and connection status detection.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from typing import Any, Optional

import requests
import urllib3

from antigravity_export.config import AntigravityConfig
from antigravity_export.models import ConnectionStatus

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LanguageServerManager:
    """Manages discovery and connection health checks for Antigravity Language Server."""

    def __init__(self, config: Optional[AntigravityConfig] = None):
        self.config = config or AntigravityConfig()

    def discover_processes(self) -> list[dict[str, Any]]:
        """Find all running language_server instances across operating systems."""
        system = platform.system()
        if system == "Windows":
            return self._discover_windows()
        elif system == "Darwin":
            return self._discover_macos()
        else:
            return self._discover_linux()

    def _discover_windows(self) -> list[dict[str, Any]]:
        """Discover language_server processes on Windows via PowerShell CIM."""
        processes = []
        try:
            ps_cmd = (
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.Name -like 'language_server*' -or $_.CommandLine -like '*language_server*' } | "
                "Select-Object ProcessId, CommandLine, ExecutablePath | "
                "ConvertTo-Json -Compress"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=12,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return processes

            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]

            for item in data:
                cmd = item.get("CommandLine") or ""
                pid = item.get("ProcessId")
                exe = item.get("ExecutablePath") or ""
                if not cmd and not exe:
                    continue

                csrf = self._extract_flag(cmd, r"--csrf_token\s+([^\s]+)")
                ide_name = self._extract_flag(cmd, r"--override_ide_name\s+([^\s]+)") or "antigravity"
                ide_ver = self._extract_flag(cmd, r"--override_ide_version\s+([^\s]+)")

                processes.append({
                    "pid": pid,
                    "csrf_token": csrf,
                    "cmd": cmd,
                    "executable_path": exe,
                    "ide_name": ide_name,
                    "ide_version": ide_ver,
                })
        except Exception:
            pass
        return processes

    def _discover_macos(self) -> list[dict[str, Any]]:
        """Discover language_server processes on macOS."""
        processes = []
        try:
            res = subprocess.run(["pgrep", "-f", "language_server"], capture_output=True, text=True)
            for line in res.stdout.strip().splitlines():
                pid_str = line.strip()
                if not pid_str.isdigit():
                    continue
                pid = int(pid_str)
                ps = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
                cmd = ps.stdout.strip()
                csrf = self._extract_flag(cmd, r"--csrf_token\s+([^\s]+)")
                ide_name = self._extract_flag(cmd, r"--override_ide_name\s+([^\s]+)") or "antigravity"
                ide_ver = self._extract_flag(cmd, r"--override_ide_version\s+([^\s]+)")
                processes.append({
                    "pid": pid,
                    "csrf_token": csrf,
                    "cmd": cmd,
                    "executable_path": "",
                    "ide_name": ide_name,
                    "ide_version": ide_ver,
                })
        except Exception:
            pass
        return processes

    def _discover_linux(self) -> list[dict[str, Any]]:
        """Discover language_server processes on Linux."""
        processes = []
        try:
            res = subprocess.run(["pgrep", "-f", "language_server"], capture_output=True, text=True)
            for line in res.stdout.strip().splitlines():
                pid_str = line.strip()
                if not pid_str.isdigit():
                    continue
                pid = int(pid_str)
                cmd_path = f"/proc/{pid}/cmdline"
                if os.path.exists(cmd_path):
                    with open(cmd_path, "rb") as f:
                        cmd = f.read().decode("utf-8", errors="ignore").replace("\x00", " ")
                    csrf = self._extract_flag(cmd, r"--csrf_token\s+([^\s]+)")
                    ide_name = self._extract_flag(cmd, r"--override_ide_name\s+([^\s]+)") or "antigravity"
                    ide_ver = self._extract_flag(cmd, r"--override_ide_version\s+([^\s]+)")
                    processes.append({
                        "pid": pid,
                        "csrf_token": csrf,
                        "cmd": cmd,
                        "executable_path": "",
                        "ide_name": ide_name,
                        "ide_version": ide_ver,
                    })
        except Exception:
            pass
        return processes

    @staticmethod
    def _extract_flag(cmd: str, pattern: str) -> Optional[str]:
        m = re.search(pattern, cmd)
        return m.group(1) if m else None

    def find_ports_for_pid(self, pid: int) -> list[int]:
        """Find local TCP ports on which the process is actively listening."""
        ports: list[int] = []
        system = platform.system()

        if system == "Windows":
            try:
                res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=8)
                pid_suffix = str(pid)
                for line in res.stdout.splitlines():
                    if "LISTENING" in line and line.rstrip().endswith(pid_suffix):
                        m = re.search(r"127\.0\.0\.1:(\d+)", line)
                        if m:
                            port = int(m.group(1))
                            if port not in ports:
                                ports.append(port)
            except Exception:
                pass
        else:
            try:
                res = subprocess.run(
                    ["lsof", "-p", str(pid), "-iTCP", "-sTCP:LISTEN", "-P", "-n"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                for line in res.stdout.splitlines():
                    m = re.search(r":(\d+)\s+\(LISTEN\)", line)
                    if m:
                        port = int(m.group(1))
                        if port not in ports:
                            ports.append(port)
            except Exception:
                pass

        return ports

    def test_endpoint(self, port: int, csrf_token: str, timeout: float = 3.0) -> bool:
        """Ping the gRPC-Web Connect endpoint with GetAllCascadeTrajectories."""
        url = f"https://localhost:{port}/{self.config.BASE_SERVICE_PATH}/GetAllCascadeTrajectories"
        headers = {
            "Content-Type": "application/json",
            "Connect-Protocol-Version": self.config.CONNECT_PROTOCOL_VERSION,
            self.config.CSRF_HEADER_NAME: csrf_token,
        }
        try:
            resp = requests.post(url, headers=headers, json={}, verify=False, timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def find_all_endpoints(
        self,
        manual_port: Optional[int] = None,
        manual_token: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Find and verify all valid running (port, csrf, pid) endpoints."""
        if manual_port and manual_token:
            if self.test_endpoint(manual_port, manual_token):
                return [{"port": manual_port, "csrf_token": manual_token, "pid": 0}]
            return []

        endpoints = []
        processes = self.discover_processes()
        for proc in processes:
            pid = proc.get("pid")
            csrf = proc.get("csrf_token") or ""
            if not pid or not csrf:
                continue

            ports = self.find_ports_for_pid(pid)
            for port in ports:
                if self.test_endpoint(port, csrf, timeout=2.5):
                    endpoints.append({
                        "port": port,
                        "csrf_token": csrf,
                        "pid": pid,
                        "ide_name": proc.get("ide_name"),
                        "ide_version": proc.get("ide_version"),
                        "executable_path": proc.get("executable_path"),
                    })
                    break  # One verified port per instance is sufficient
        return endpoints

    def get_status(
        self,
        manual_port: Optional[int] = None,
        manual_token: Optional[str] = None,
    ) -> ConnectionStatus:
        """Generate a complete diagnostic status of the Antigravity Language Server."""
        status = ConnectionStatus()
        procs = self.discover_processes()

        if procs:
            status.is_running = True
            primary = procs[0]
            status.process_id = primary.get("pid")
            status.executable_path = primary.get("executable_path")
            status.csrf_token = primary.get("csrf_token")
            status.ide_name = primary.get("ide_name")
            status.ide_version = primary.get("ide_version")

        endpoints = self.find_all_endpoints(manual_port, manual_token)
        status.endpoints = endpoints

        if endpoints:
            status.is_reachable = True
            status.port = endpoints[0]["port"]
            status.csrf_token = endpoints[0]["csrf_token"]
        elif status.is_running:
            status.error_message = (
                "Language Server process is running, but no HTTP/gRPC listening port could be verified."
            )
        else:
            status.error_message = "No running Antigravity Language Server process found."

        # Scan crash count
        if self.config.crashes_dir.is_dir():
            status.crashes_detected = len(list(self.config.crashes_dir.glob("crash_*.log")))

        # Check total stored conversations from SQLite
        if self.config.summaries_db.is_file():
            try:
                import sqlite3
                with sqlite3.connect(str(self.config.summaries_db)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM conversation_summaries")
                    row = cursor.fetchone()
                    if row:
                        status.total_stored_conversations = row[0]
            except Exception:
                pass

        return status
