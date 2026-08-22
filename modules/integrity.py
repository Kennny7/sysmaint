# sysmaint/modules/integrity.py

from __future__ import annotations

import logging
import platform
import shutil
from typing import Any

from ..utils.common import run_command

logger = logging.getLogger("sysmaint.integrity")


def check_integrity(repair: bool = False) -> dict[str, Any]:
    """
    Verify system file integrity.

    Windows: DISM + SFC (repair mode if requested).
    Linux: dpkg/rpm verification and journalctl verify.

    Args:
        repair: If True, run repair commands; otherwise run read-only checks.

    Returns:
        Dictionary keyed by tool with return code, output, and stderr.
    """
    system = platform.system().lower()
    logger.info("Running integrity check (repair=%s)", repair)

    if system == "windows":
        results = {}
        if repair:
            dism_cmd = [
                "Dism.exe",
                "/Online",
                "/Cleanup-Image",
                "/RestoreHealth",
            ]
            sfc_cmd = ["sfc", "/scannow"]
        else:
            dism_cmd = ["Dism.exe", "/Online", "/Cleanup-Image", "/CheckHealth"]
            sfc_cmd = ["sfc", "/verifyonly"]

        dism_result = run_command(dism_cmd, check=False)
        sfc_result = run_command(sfc_cmd, check=False)

        results["dism"] = {
            "returncode": dism_result.returncode,
            "output": dism_result.stdout,
            "stderr": dism_result.stderr,
        }
        results["sfc"] = {
            "returncode": sfc_result.returncode,
            "output": sfc_result.stdout,
            "stderr": sfc_result.stderr,
        }
        return results

    if system == "linux":
        results = {}
        # Detect package manager and run verification
        pm = None
        for candidate in ("dpkg", "rpm"):
            if shutil.which(candidate):
                pm = candidate
                break

        if pm == "dpkg":
            result = run_command(["dpkg", "--verify"], check=False)
            results["dpkg"] = {
                "returncode": result.returncode,
                "output": result.stdout,
                "stderr": result.stderr,
            }
        elif pm == "rpm":
            result = run_command(["rpm", "-Va"], check=False)
            results["rpm"] = {
                "returncode": result.returncode,
                "output": result.stdout,
                "stderr": result.stderr,
            }
        else:
            results["package_manager"] = {"error": "No supported package manager found"}

        # Verify systemd journal if available
        if shutil.which("journalctl"):
            journal_result = run_command(["journalctl", "--verify"], check=False)
            results["journalctl"] = {
                "returncode": journal_result.returncode,
                "output": journal_result.stdout,
                "stderr": journal_result.stderr,
            }

        return results

    return {"error": f"Unsupported platform: {system}"}