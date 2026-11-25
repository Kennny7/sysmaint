# sysmaint/modules/services.py

from __future__ import annotations

import logging
import platform
import shutil
from typing import Any, Iterable, List

import psutil

from ..utils.common import run_command

logger = logging.getLogger("sysmaint.services")


def list_services() -> List[dict[str, Any]]:
    """
    List all installed services across Windows or Linux safely.

    Returns:
        A list of dictionaries with service name, display name, status, and description.
    """
    system = platform.system().lower()
    logger.info("Enumerating services on %s", system)
    services: List[dict[str, Any]] = []

    if system == "windows":
        for svc in psutil.win_service_iter():
            try:
                name = svc.name()
                display_name = svc.display_name()
                status = svc.status()
                start_type = svc.start_type()
                services.append({
                    "name": name,
                    "display_name": display_name,
                    "status": status,
                    "start_type": start_type,
                    "healthy": status != "stopped" or start_type != "automatic",
                })
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                continue
        return sorted(services, key=lambda x: x["name"].lower())

    if system == "linux":
        if shutil.which("systemctl"):
            result = run_command(
                ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"],
                check=False,
            )
            for line in result.stdout.splitlines():
                parts = line.strip().split(None, 4)
                if len(parts) >= 4:
                    unit_name = parts[0].replace(".service", "")
                    active_state = parts[2]
                    sub_state = parts[3]
                    desc = parts[4] if len(parts) > 4 else ""
                    is_failed = active_state == "failed"
                    services.append({
                        "name": unit_name,
                        "display_name": desc or unit_name,
                        "status": active_state,
                        "sub_status": sub_state,
                        "healthy": not is_failed,
                    })
        return sorted(services, key=lambda x: x["name"].lower())

    return []


def service_status(name: str) -> str:
    """
    Return the current status of a single service ('running', 'stopped', 'failed', 'not_found').
    """
    system = platform.system().lower()
    logger.info("Checking service status: %s", name)

    if system == "windows":
        try:
            svc = psutil.win_service_get(name)
            return svc.status()
        except (psutil.NoSuchProcess, Exception):
            return "not_found"

    if system == "linux":
        if shutil.which("systemctl"):
            res = run_command(["systemctl", "is-active", name], check=False)
            status = res.stdout.strip()
            if status in ("active", "running"):
                return "running"
            elif status == "failed":
                return "failed"
            elif status in ("inactive", "dead"):
                return "stopped"
        return "unknown"

    return "unsupported"


def control_service(name: str, action: str) -> dict[str, Any]:
    """
    Start, stop, or restart a system service.

    Args:
        name: Service identifier name.
        action: One of 'start', 'stop', 'restart', 'enable', 'disable'.

    Returns:
        Dictionary with execution result.
    """
    system = platform.system().lower()
    logger.info("Performing service action '%s' on '%s'", action, name)

    if system == "windows":
        if action in ("start", "stop", "restart"):
            # Use PowerShell Start-Service / Stop-Service / Restart-Service for synchronous reliability
            ps_map = {
                "start": f"Start-Service -Name '{name}'",
                "stop": f"Stop-Service -Name '{name}' -Force",
                "restart": f"Restart-Service -Name '{name}' -Force",
            }
            script = ps_map.get(action, f"sc {action} '{name}'")
            cmd = ["powershell", "-NoProfile", "-Command", script]
        elif action in ("enable", "disable"):
            startup_type = "Automatic" if action == "enable" else "Disabled"
            cmd = ["powershell", "-NoProfile", "-Command", f"Set-Service -Name '{name}' -StartupType {startup_type}"]
        else:
            return {"error": f"Invalid action: {action}"}

    elif system == "linux":
        if action in ("start", "stop", "restart", "enable", "disable"):
            cmd = ["systemctl", action, name]
        else:
            return {"error": f"Invalid action: {action}"}
    else:
        return {"error": f"Unsupported platform: {system}"}

    result = run_command(cmd, check=False)
    return {
        "name": name,
        "action": action,
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "output": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def ensure_expected_services(expected_services: Iterable[str]) -> dict[str, Any]:
    """
    Ensure that a list of critical services is active, starting any that are stopped.
    """
    result: dict[str, list[str]] = {"started": [], "already_running": [], "failed": []}
    logger.info("Verifying expected services are running")

    for svc_name in expected_services:
        status = service_status(svc_name)
        if status in ("active", "running"):
            result["already_running"].append(svc_name)
        elif status in ("inactive", "failed", "stopped"):
            res = control_service(svc_name, "start")
            if res.get("success"):
                result["started"].append(svc_name)
            else:
                result["failed"].append(svc_name)
        else:
            result["failed"].append(svc_name)

    return result