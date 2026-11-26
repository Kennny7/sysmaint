# sysmaint/modules/disk.py

from __future__ import annotations

import logging
import platform
import shutil
from typing import Any

import psutil

from ..utils.common import format_bytes, run_command
from ..utils.parsers import parse_fsck_output

logger = logging.getLogger("sysmaint.disk")


def get_disk_partitions() -> list[dict[str, Any]]:
    """
    Return all mounted partitions with storage metrics (total, used, free, percent).
    """
    partitions_info = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions_info.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "opts": part.opts,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
                "total_formatted": format_bytes(usage.total),
                "used_formatted": format_bytes(usage.used),
                "free_formatted": format_bytes(usage.free),
            })
        except (PermissionError, OSError):
            continue
    return partitions_info


def check_smart_health() -> list[dict[str, Any]]:
    """
    Check S.M.A.R.T. disk health status using smartctl or OS-specific tools.
    """
    system = platform.system().lower()
    drives: list[dict[str, Any]] = []

    # Check smartctl if installed
    if shutil.which("smartctl"):
        res = run_command(["smartctl", "--scan"], check=False)
        for line in res.stdout.splitlines():
            parts = line.split(None, 2)
            if parts and parts[0].startswith("/dev/"):
                dev_path = parts[0]
                health_res = run_command(["smartctl", "-H", dev_path], check=False)
                passed = "PASSED" in health_res.stdout or "OK" in health_res.stdout
                drives.append({
                    "device": dev_path,
                    "type": parts[1] if len(parts) > 1 else "Unknown",
                    "smart_status": "PASSED" if passed else "WARNING/FAILED",
                    "healthy": passed,
                })
        if drives:
            return drives

    if system == "windows":
        from ..utils.windows import run_powershell
        script = (
            "Get-PhysicalDisk -ErrorAction SilentlyContinue | "
            "Select-Object DeviceId, FriendlyName, MediaType, OperationalStatus, HealthStatus, Size | "
            "ConvertTo-Json"
        )
        data = run_powershell(script, as_json=True)
        if isinstance(data, list):
            for disk in data:
                if isinstance(disk, dict):
                    drives.append({
                        "device": f"Disk {disk.get('DeviceId', '')}",
                        "name": disk.get("FriendlyName", "Physical Disk"),
                        "media_type": disk.get("MediaType", "Unspecified"),
                        "smart_status": disk.get("HealthStatus", "Healthy"),
                        "operational_status": disk.get("OperationalStatus", "OK"),
                        "size_formatted": format_bytes(disk.get("Size", 0)),
                        "healthy": disk.get("HealthStatus") in ("Healthy", None),
                    })

    return drives


def check_disk(repair: bool = False, volume: str | None = None) -> dict[str, Any]:
    """
    Check disk/filesystem health and partition statistics.

    Args:
        repair: If True, attempt to repair filesystem errors.
        volume: Optional Windows volume letter (e.g., 'C:') or Linux mountpoint.

    Returns:
        Dictionary with partitions, tool results, and health status.
    """
    system = platform.system().lower()
    partitions = get_disk_partitions()
    smart_info = check_smart_health()

    logger.info("Running disk check (system=%s, repair=%s)", system, repair)

    if system == "windows":
        target_volume = volume or "C:"
        if not target_volume.endswith(":"):
            target_volume = f"{target_volume}:"

        cmd = ["chkdsk", target_volume]
        if repair:
            cmd.append("/f")
        else:
            cmd.append("/scan")

        result = run_command(cmd, check=False)
        return {
            "tool": "chkdsk",
            "volume": target_volume,
            "repair": repair,
            "returncode": result.returncode,
            "output": result.stdout,
            "stderr": result.stderr,
            "partitions": partitions,
            "smart_drives": smart_info,
            "healthy": result.returncode == 0,
        }

    if system == "linux":
        cmd = ["fsck"]
        if repair:
            cmd.append("-y")
        else:
            cmd.append("-N")
        cmd.append("-A")

        result = run_command(cmd, check=False)
        parsed = parse_fsck_output(result.stdout)
        return {
            "tool": "fsck",
            "repair": repair,
            "returncode": result.returncode,
            "output": result.stdout,
            "stderr": result.stderr,
            "parsed": parsed,
            "partitions": partitions,
            "smart_drives": smart_info,
            "healthy": result.returncode in (0, 1),
        }

    return {
        "partitions": partitions,
        "smart_drives": smart_info,
        "healthy": True,
    }