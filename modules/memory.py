# sysmaint/modules/memory.py

from __future__ import annotations

import logging
from typing import Any

import psutil

logger = logging.getLogger("sysmaint.memory")


def check_memory() -> dict[str, Any]:
    """
    Return current memory and swap usage statistics.

    Returns:
        Dictionary with total/available/used/free and swap values in bytes.
    """
    logger.info("Collecting memory statistics")
    virtual = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "total": virtual.total,
        "available": virtual.available,
        "used": virtual.used,
        "free": virtual.free,
        "percent": virtual.percent,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_free": swap.free,
        "swap_percent": swap.percent,
    }