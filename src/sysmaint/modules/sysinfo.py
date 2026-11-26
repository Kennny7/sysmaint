# sysmaint/modules/sysinfo.py

from __future__ import annotations

import datetime
import logging
import platform
import time
from typing import Any

import psutil

from ..utils.common import format_bytes

logger = logging.getLogger("sysmaint.sysinfo")


def get_cpu_info() -> dict[str, Any]:
    """
    Get detailed processor metrics and model.
    """
    cpu_freq = psutil.cpu_freq()
    model = platform.processor() or "Generic CPU"

    # On Windows, try querying wmic / registry for friendly CPU brand string
    if platform.system().lower() == "windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            brand, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if brand:
                model = str(brand).strip()
        except Exception:
            pass

    return {
        "model": model,
        "physical_cores": psutil.cpu_count(logical=False) or 1,
        "logical_cores": psutil.cpu_count(logical=True) or 1,
        "current_frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
        "max_frequency_mhz": round(cpu_freq.max, 1) if cpu_freq and cpu_freq.max else None,
        "usage_percent": psutil.cpu_percent(interval=0.1),
    }


def get_battery_info() -> dict[str, Any] | None:
    """
    Get battery level and charging status if system has a battery.
    """
    if hasattr(psutil, "sensors_battery"):
        bat = psutil.sensors_battery()
        if bat:
            return {
                "percent": bat.percent,
                "power_plugged": bat.power_plugged,
                "secs_left": bat.secsleft if bat.secsleft > 0 else None,
            }
    return None


def get_system_specs() -> dict[str, Any]:
    """
    Collect complete system hardware specifications and OS information.
    """
    logger.info("Collecting system hardware and OS specs")
    boot_time_ts = psutil.boot_time()
    boot_dt = datetime.datetime.fromtimestamp(boot_time_ts)
    uptime_secs = int(time.time() - boot_time_ts)

    uptime_hours = uptime_secs // 3600
    uptime_mins = (uptime_secs % 3600) // 60

    v_mem = psutil.virtual_memory()

    # Calculate total disk capacity across physical partitions
    total_disk_bytes = 0
    used_disk_bytes = 0
    for part in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(part.mountpoint)
            total_disk_bytes += u.total
            used_disk_bytes += u.used
        except (PermissionError, OSError):
            continue

    return {
        "os_name": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "boot_time": boot_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_formatted": f"{uptime_hours}h {uptime_mins}m",
        "uptime_seconds": uptime_secs,
        "cpu": get_cpu_info(),
        "memory": {
            "total_bytes": v_mem.total,
            "total_formatted": format_bytes(v_mem.total),
            "available_formatted": format_bytes(v_mem.available),
            "usage_percent": v_mem.percent,
        },
        "storage": {
            "total_bytes": total_disk_bytes,
            "total_formatted": format_bytes(total_disk_bytes),
            "used_formatted": format_bytes(used_disk_bytes),
        },
        "battery": get_battery_info(),
        "python_version": platform.python_version(),
    }
