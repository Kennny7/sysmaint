# sysmaint/modules/drivers.py

from __future__ import annotations

import logging
import platform
from typing import Any

from ..utils.common import run_command

logger = logging.getLogger("sysmaint.drivers")


def check_drivers() -> dict[str, Any]:
    """
    List installed drivers / kernel modules.

    Returns:
        Dictionary with tool name, return code, and raw output.
    """
    system = platform.system().lower()
    logger.info("Enumerating drivers/modules")

    if system == "windows":
        result = run_command(["driverquery", "/v"], check=False)
        return {
            "tool": "driverquery",
            "returncode": result.returncode,
            "output": result.stdout,
            "stderr": result.stderr,
        }

    if system == "linux":
        result = run_command(["lsmod"], check=False)
        return {
            "tool": "lsmod",
            "returncode": result.returncode,
            "output": result.stdout,
            "stderr": result.stderr,
        }

    return {"error": f"Unsupported platform: {system}"}