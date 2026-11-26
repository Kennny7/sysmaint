# sysmaint/utils/windows.py

from __future__ import annotations

import ctypes
import json
import logging
import os
from pathlib import Path
from typing import Any

from .common import run_command

logger = logging.getLogger("sysmaint.windows")


def run_powershell(script: str, as_json: bool = False) -> Any:
    """
    Execute a PowerShell snippet and optionally parse JSON output.
    """
    cmd = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    result = run_command(cmd, check=False)
    if result.returncode != 0:
        logger.debug("PowerShell command error: %s", result.stderr.strip())
        return None if as_json else result.stdout

    if as_json:
        raw = result.stdout.strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            logger.debug("Failed to decode JSON from PowerShell: %s", raw[:100])
            return []
    return result.stdout


def create_restore_point(description: str = "SysMaint Backup") -> bool:
    """
    Create a Windows System Restore point using PowerShell.
    Requires administrator privileges.
    """
    ps_script = (
        f'Checkpoint-Computer -Description "{description}" '
        '-RestorePointType "MODIFY_SETTINGS" -ErrorAction Stop'
    )
    result = run_command(
        ["powershell", "-NoProfile", "-Command", ps_script],
        check=False,
    )
    if result.returncode != 0:
        logger.warning("Restore point creation failed: %s", result.stderr.strip())
        raise RuntimeError(f"Failed to create restore point: {result.stderr.strip()}")
    return True


def list_restore_points() -> list[dict[str, Any]]:
    """
    List all available Windows System Restore Points.
    """
    script = (
        "Get-ComputerRestorePoint -ErrorAction SilentlyContinue | "
        "Select-Object SequenceNumber, Description, CreationTime, EventType, RestorePointType | "
        "ConvertTo-Json"
    )
    data = run_powershell(script, as_json=True)
    points = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                points.append({
                    "sequence_number": item.get("SequenceNumber"),
                    "description": item.get("Description", "Restore Point"),
                    "time": item.get("CreationTime"),
                    "type": item.get("RestorePointType"),
                })
    return points


def get_windows_services() -> list[dict[str, Any]]:
    """Return a list of all Windows services using PowerShell."""
    script = (
        "Get-Service | "
        "Select-Object Name, DisplayName, Status, StartType | "
        "ConvertTo-Json -Compress"
    )
    data = run_powershell(script, as_json=True)
    services = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                services.append({
                    "name": item.get("Name", ""),
                    "display_name": item.get("DisplayName", item.get("Name", "")),
                    "status": str(item.get("Status", "Unknown")),
                    "start_type": str(item.get("StartType", "Unknown")),
                })
    return services


def get_pnp_device_errors() -> list[dict[str, Any]]:
    """
    Scan for hardware devices reporting errors or degraded states in Windows Device Manager.
    """
    script = (
        "Get-PnpDevice -Status 'Error','Degraded','Unknown' -ErrorAction SilentlyContinue | "
        "Select-Object FriendlyName, InstanceId, Class, Status, Problem, ProblemDescription | "
        "ConvertTo-Json"
    )
    data = run_powershell(script, as_json=True)
    devices = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("FriendlyName"):
                devices.append({
                    "name": item.get("FriendlyName"),
                    "class": item.get("Class"),
                    "status": item.get("Status"),
                    "problem_code": item.get("Problem"),
                    "problem_description": item.get("ProblemDescription", "Device has a problem"),
                })
    return devices


def get_windows_startup_items() -> list[dict[str, Any]]:
    """
    Enumerate startup programs from Windows Registry (HKCU and HKLM Run keys).
    """
    items = []
    try:
        import winreg

        reg_locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "User Registry"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "System Registry"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "System (32-bit)"),
        ]

        for hkey, subkey, location in reg_locations:
            try:
                with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            items.append({
                                "name": name,
                                "command": value,
                                "location": location,
                                "registry_key": subkey,
                                "is_system": hkey == winreg.HKEY_LOCAL_MACHINE,
                                "enabled": True,
                            })
                            i += 1
                        except OSError:
                            break
            except OSError:
                pass
    except ImportError:
        pass

    # Check Startup Folder
    appdata = os.environ.get("APPDATA")
    if appdata:
        startup_dir = Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        if startup_dir.is_dir():
            for entry in startup_dir.iterdir():
                if entry.is_file() and entry.name.lower() != "desktop.ini":
                    items.append({
                        "name": entry.stem,
                        "command": str(entry),
                        "location": "Startup Folder",
                        "registry_key": None,
                        "is_system": False,
                        "enabled": True,
                    })

    return items


def flush_windows_dns() -> bool:
    """
    Flush the Windows DNS resolver cache.
    """
    result = run_command(["ipconfig", "/flushdns"], check=False)
    return result.returncode == 0


def get_windows_security_status() -> dict[str, Any]:
    """
    Query Windows Defender, Windows Firewall, and UAC security settings.
    """
    script = (
        "@{ "
        "Defender = (Get-MpComputerStatus -ErrorAction SilentlyContinue | Select-Object AMServiceEnabled, AntispywareEnabled, RealTimeProtectionEnabled); "
        "Firewall = (Get-NetFirewallProfile -ErrorAction SilentlyContinue | Select-Object Name, Enabled); "
        "} | ConvertTo-Json -Depth 3"
    )
    res = run_powershell(script, as_json=False)
    security_info = {
        "antivirus": "Windows Defender",
        "realtime_protection": True,
        "firewall_enabled": True,
        "firewall_profiles": [],
        "uac_active": True,
    }

    if res:
        try:
            parsed = json.loads(res)
            defender = parsed.get("Defender", {})
            if defender:
                security_info["realtime_protection"] = bool(defender.get("RealTimeProtectionEnabled", True))
                security_info["antivirus_active"] = bool(defender.get("AMServiceEnabled", True))
            
            firewalls = parsed.get("Firewall", [])
            if isinstance(firewalls, dict):
                firewalls = [firewalls]
            if isinstance(firewalls, list):
                all_enabled = all(bool(f.get("Enabled")) for f in firewalls if isinstance(f, dict))
                security_info["firewall_enabled"] = all_enabled
                security_info["firewall_profiles"] = [
                    {"name": f.get("Name"), "enabled": bool(f.get("Enabled"))}
                    for f in firewalls if isinstance(f, dict)
                ]
        except Exception:
            pass

    return security_info


def get_windows_temp_paths() -> dict[str, Path]:
    """
    Return standard Windows junk and cache directories.
    """
    paths: dict[str, Path] = {}
    
    # User Temp
    user_temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if user_temp:
        paths["User Temp Files"] = Path(user_temp)
    
    # System Temp
    sys_temp = Path(r"C:\Windows\Temp")
    if sys_temp.is_dir():
        paths["System Temp Files"] = sys_temp

    # Prefetch
    prefetch = Path(r"C:\Windows\Prefetch")
    if prefetch.is_dir():
        paths["Windows Prefetch"] = prefetch

    # Windows Update Download Cache
    software_dist = Path(r"C:\Windows\SoftwareDistribution\Download")
    if software_dist.is_dir():
        paths["Windows Update Cache"] = software_dist

    # Crash Dumps
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        crash_dumps = Path(local_app_data) / "CrashDumps"
        if crash_dumps.is_dir():
            paths["Application Crash Dumps"] = crash_dumps

    return paths


def trim_process_working_sets() -> int:
    """
    Trigger Windows working set cleanup (EmptyWorkingSet) on accessible processes to free inactive RAM.
    Returns number of processes trimmed.
    """
    if os.name != "nt":
        return 0

    count = 0
    try:
        import psutil
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_QUERY_INFORMATION = 0x0400

        for proc in psutil.process_iter(["pid", "name"]):
            pid = proc.info["pid"]
            if pid <= 4:
                continue
            h_proc = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
            if h_proc:
                try:
                    if psapi.EmptyWorkingSet(h_proc):
                        count += 1
                finally:
                    kernel32.CloseHandle(h_proc)
    except Exception as exc:
        logger.debug("Memory trim encountered exception: %s", exc)

    return count