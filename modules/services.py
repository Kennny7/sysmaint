# sysmaint/modules/services.py

from __future__ import annotations

import logging
import platform
from typing import Any, Iterable, Optional

import psutil

from ..utils.common import run_command

logger = logging.getLogger("sysmaint.services")


def list_services() -> list[dict[str, Any]]:
    """
    List all services on the current system.

    Returns:
        A list of dictionaries with service name and status.
    """
    system = platform.system().lower()
    logger.info("Listing services")

    if system == "windows":
        services = []
        for svc in psutil.win_service_iter():
            services.append(
                {
                    "name": svc.name(),
                    "display_name": svc.display_name(),
                    "status": svc.status(),
                }
            )
        return services

    if system == "linux":
        # systemd is assumed; fallback to service command is possible
        result = run_command(
            ["systemctl", "list-units", "--type=service", "--no-pager", "--no-legend"],
            check=False,
        )
        services = []
        for line in result.stdout.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 5:
                unit_name = parts[0].replace(".service", "")
                status = parts[3]  # ACTIVE column
                description = parts[4]
                services.append(
                    {
                        "name": unit_name,
                        "status": status,
                        "description": description,
                    }
                )
        return services

    return []


def service_status(name: str) -> str:
    """Return the current status of a single service."""
    system = platform.system().lower()
    logger.info("Checking service status: %s", name)

    if system == "windows":
        for svc in psutil.win_service_iter():
            if svc.name().lower() == name.lower():
                return svc.status()
        return "not_found"

    if system == "linux":
        result = run_command(["systemctl", "is-active", name], check=False)
        return result.stdout.strip() if result.stdout else "inactive"

    return "unsupported"


def control_service(name: str, action: str) -> dict[str, Any]:
    """
    Start, stop, or restart a system service.

    Args:
        name: Service name.
        action: One of 'start', 'stop', 'restart'.

    Returns:
        Dictionary with command result details.
    """
    system = platform.system().lower()
    logger.info("Service action '%s' on '%s'", action, name)

    if system == "windows":
        cmd = ["sc", action, name]
    elif system == "linux":
        cmd = ["systemctl", action, name]
    else:
        return {"error": f"Unsupported platform: {system}"}

    result = run_command(cmd, check=False)
    return {
        "name": name,
        "action": action,
        "returncode": result.returncode,
        "output": result.stdout,
        "stderr": result.stderr,
    }


def ensure_expected_services(expected_services: Iterable[str]) -> dict[str, Any]:
    """
    Ensure that a list of expected services is running.

    If a service is inactive, attempt to start it.

    Returns:
        Dictionary with lists of started, already_running, and failed services.
    """
    result = {"started": [], "already_running": [], "failed": []}
    logger.info("Ensuring expected services are running")

    for svc_name in expected_services:
        status = service_status(svc_name)
        if status in ("active", "running"):
            result["already_running"].append(svc_name)
        elif status in ("inactive", "failed", "stopped"):
            control_result = control_service(svc_name, "start")
            if control_result.get("returncode") == 0:
                result["started"].append(svc_name)
            else:
                result["failed"].append(svc_name)
        else:
            result["failed"].append(svc_name)

    return result