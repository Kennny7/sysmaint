# sysmaint/modules/memory.py

from __future__ import annotations

import logging
import platform
from typing import Any

import psutil

from ..utils.common import format_bytes

logger = logging.getLogger("sysmaint.memory")


def get_top_processes(limit: int = 10) -> list[dict[str, Any]]:
    """
    Return top processes ordered by RAM memory consumption.
    """
    procs = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent", "memory_info", "username"]):
        try:
            info = proc.info
            rss = info["memory_info"].rss if info.get("memory_info") else 0
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "Unknown",
                "memory_percent": round(info.get("memory_percent") or 0.0, 1),
                "cpu_percent": round(info.get("cpu_percent") or 0.0, 1),
                "rss": rss,
                "rss_formatted": format_bytes(rss),
                "user": info.get("username") or "N/A",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    procs.sort(key=lambda x: x["rss"], reverse=True)
    return procs[:limit]


def optimize_memory() -> dict[str, Any]:
    """
    Attempt to free unused memory by trimming process working sets (Windows) or dropping page caches (Linux).
    """
    system = platform.system().lower()
    logger.info("Executing memory optimization for %s", system)

    if system == "windows":
        from ..utils.windows import trim_process_working_sets
        count = trim_process_working_sets()
        return {
            "success": True,
            "system": "windows",
            "message": f"Trimmed working set memory on {count} active processes.",
            "processes_trimmed": count,
        }

    if system == "linux":
        from ..utils.linux import drop_linux_page_caches
        success = drop_linux_page_caches()
        return {
            "success": success,
            "system": "linux",
            "message": "Dropped filesystem page caches and slab objects." if success else "Requires root to drop caches.",
        }

    return {"success": False, "message": f"Optimization not supported on {system}"}


def check_memory() -> dict[str, Any]:
    """
    Collect comprehensive memory, swap, and top process statistics.

    Returns:
        Dictionary with total/available/used/free, swap metrics, and top processes.
    """
    logger.info("Collecting system memory statistics")
    virtual = psutil.virtual_memory()
    swap = psutil.swap_memory()
    top_processes = get_top_processes(limit=10)

    # Health status based on memory pressure
    is_critical = virtual.percent >= 90.0
    is_warning = virtual.percent >= 80.0

    return {
        "total": virtual.total,
        "available": virtual.available,
        "used": virtual.used,
        "free": virtual.free,
        "percent": virtual.percent,
        "total_formatted": format_bytes(virtual.total),
        "available_formatted": format_bytes(virtual.available),
        "used_formatted": format_bytes(virtual.used),
        "free_formatted": format_bytes(virtual.free),
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_free": swap.free,
        "swap_percent": swap.percent,
        "swap_total_formatted": format_bytes(swap.total),
        "swap_used_formatted": format_bytes(swap.used),
        "swap_free_formatted": format_bytes(swap.free),
        "status": "Critical" if is_critical else ("Warning" if is_warning else "Healthy"),
        "top_processes": top_processes,
    }