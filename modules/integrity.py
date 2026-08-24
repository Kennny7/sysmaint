# sysmaint/modules/integrity.py

from __future__ import annotations

import logging
import platform
import shutil
from typing import Any

from ..utils.common import run_command
from ..utils.parsers import parse_dism_output, parse_sfc_output

logger = logging.getLogger("sysmaint.integrity")


def check_integrity(repair: bool = False) -> dict[str, Any]:
    """
    Verify system file and package integrity.

    Windows: DISM (CheckHealth/ScanHealth or RestoreHealth) + SFC (verifyonly or scannow).
    Linux: dpkg/rpm/pacman verification and systemd journal verification.

    Args:
        repair: If True, run repair commands; otherwise run read-only checks.

    Returns:
        Dictionary keyed by tool with parsed status, output, and health summary.
    """
    system = platform.system().lower()
    logger.info("Running system integrity check (system=%s, repair=%s)", system, repair)

    if system == "windows":
        results: dict[str, Any] = {}

        # 1. DISM
        if repair:
            dism_cmd = ["Dism.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"]
        else:
            dism_cmd = ["Dism.exe", "/Online", "/Cleanup-Image", "/ScanHealth"]

        dism_result = run_command(dism_cmd, check=False)
        parsed_dism = parse_dism_output(dism_result.stdout)
        results["dism"] = {
            "returncode": dism_result.returncode,
            "parsed": parsed_dism,
            "output": dism_result.stdout,
            "stderr": dism_result.stderr,
        }

        # 2. SFC
        if repair:
            sfc_cmd = ["sfc", "/scannow"]
        else:
            sfc_cmd = ["sfc", "/verifyonly"]

        sfc_result = run_command(sfc_cmd, check=False)
        parsed_sfc = parse_sfc_output(sfc_result.stdout)
        results["sfc"] = {
            "returncode": sfc_result.returncode,
            "parsed": parsed_sfc,
            "output": sfc_result.stdout,
            "stderr": sfc_result.stderr,
        }

        overall_healthy = (
            dism_result.returncode == 0
            and sfc_result.returncode in (0, 1)
            and not parsed_sfc.get("corruptions_found", False)
        )
        if repair and parsed_sfc.get("repaired", False):
            overall_healthy = True

        results["healthy"] = overall_healthy
        results["status"] = "Clean" if overall_healthy else "Corruption Detected"
        return results

    if system == "linux":
        results = {}
        pm = None
        for candidate in ("dpkg", "rpm", "pacman"):
            if shutil.which(candidate):
                pm = candidate
                break

        if pm == "dpkg":
            result = run_command(["dpkg", "--verify"], check=False)
            results["package_manager"] = {
                "tool": "dpkg",
                "returncode": result.returncode,
                "corrupted_files_count": len(result.stdout.splitlines()),
                "output": result.stdout[:2000],
                "healthy": result.returncode == 0,
            }
        elif pm == "rpm":
            result = run_command(["rpm", "-Va"], check=False)
            results["package_manager"] = {
                "tool": "rpm",
                "returncode": result.returncode,
                "corrupted_files_count": len(result.stdout.splitlines()),
                "output": result.stdout[:2000],
                "healthy": result.returncode == 0,
            }
        elif pm == "pacman":
            result = run_command(["pacman", "-Qk"], check=False)
            results["package_manager"] = {
                "tool": "pacman",
                "returncode": result.returncode,
                "output": result.stdout[:2000],
                "healthy": result.returncode == 0,
            }

        # Verify systemd journal if available
        if shutil.which("journalctl"):
            journal_result = run_command(["journalctl", "--verify"], check=False)
            results["journalctl"] = {
                "returncode": journal_result.returncode,
                "healthy": journal_result.returncode == 0,
                "output": journal_result.stdout,
            }

        overall_healthy = all(
            v.get("healthy", True) for v in results.values() if isinstance(v, dict)
        )
        results["healthy"] = overall_healthy
        results["status"] = "Clean" if overall_healthy else "Integrity Issues Found"
        return results

    return {
        "error": f"Unsupported platform: {system}",
        "healthy": True,
        "status": "Unknown",
    }