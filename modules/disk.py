# sysmaint/modules/disk.py

from __future__ import annotations

import logging
import platform
from typing import Any

from ..utils.common import run_command

logger = logging.getLogger("sysmaint.disk")


def check_disk(repair: bool = False, volume: str = "C:") -> dict[str, Any]:
    """
    Check disk/filesystem health.

    Args:
        repair: If True, attempt to repair filesystem errors.
        volume: Windows volume letter or mount point (ignored on Linux).

    Returns:
        Dictionary with tool, return code, and raw output.
    """
    system = platform.system().lower()
    logger.info("Running disk check (repair=%s)", repair)

    if system == "windows":
        cmd = ["chkdsk", volume]
        if repair:
            cmd.append("/f")
        else:
            cmd.append("/scan")
        result = run_command(cmd, check=False)
        return {
            "tool": "chkdsk",
            "volume": volume,
            "repair": repair,
            "returncode": result.returncode,
            "output": result.stdout,
            "stderr": result.stderr,
        }

    if system == "linux":
        # Use fsck with -A to check all filesystems from /etc/fstab.
        # -N is read-only, -y is automatic repair.
        cmd = ["fsck"]
        if repair:
            cmd.append("-y")
        else:
            cmd.append("-N")
        cmd.append("-A")
        result = run_command(cmd, check=False)
        return {
            "tool": "fsck",
            "repair": repair,
            "returncode": result.returncode,
            "output": result.stdout,
            "stderr": result.stderr,
        }

    return {"error": f"Unsupported platform: {system}"}