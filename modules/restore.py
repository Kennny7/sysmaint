# sysmaint/modules/restore.py

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Any, List

from ..config import SysMaintConfig
from ..utils.common import format_bytes, run_command

logger = logging.getLogger("sysmaint.restore")


def list_available_backups(config: SysMaintConfig) -> List[dict[str, Any]]:
    """
    List all available System Restore points or backup archives.
    """
    system = platform.system().lower()
    backups: List[dict[str, Any]] = []

    if system == "windows":
        from ..utils import windows
        try:
            points = windows.list_restore_points()
            for pt in points:
                backups.append({
                    "id": str(pt.get("sequence_number")),
                    "name": pt.get("description", "Restore Point"),
                    "type": "Windows System Restore Point",
                    "date": pt.get("time"),
                    "can_restore": True,
                })
        except Exception as exc:
            logger.debug("Failed to list Windows restore points: %s", exc)

    # Also list local file backups
    backup_dir = Path(config.repair.backup_dir)
    if backup_dir.is_dir():
        for f in backup_dir.glob("sysmaint-*"):
            if f.is_file():
                size = f.stat().st_size
                mtime = f.stat().st_mtime
                backups.append({
                    "id": f.name,
                    "name": f.name,
                    "type": "Archive / Backup File",
                    "path": str(f.resolve()),
                    "size_formatted": format_bytes(size),
                    "can_restore": True,
                })

    return backups


def launch_system_recovery() -> dict[str, Any]:
    """
    Launch native OS recovery / System Restore wizard.
    """
    system = platform.system().lower()
    if system == "windows":
        # Launch Windows System Restore UI (rstrui.exe)
        run_command(["rstrui.exe"], check=False)
        return {
            "success": True,
            "message": "Launched Windows System Restore UI (rstrui.exe)",
        }
    return {
        "success": False,
        "message": f"Interactive recovery UI not supported on {system}",
    }


def restore_backup(
    config: SysMaintConfig,
    backup_ref: str,
    kind: str = "auto",
) -> dict[str, Any]:
    """
    Restore system from a specified backup reference.

    Args:
        config: SysMaintConfig instance.
        backup_ref: Backup file name or restore point identifier.
        kind: 'auto', 'restore-point', 'tar', or 'snapshot'.

    Returns:
        Dictionary with restoration result and details.
    """
    system = platform.system().lower()
    logger.info("Restore requested: kind=%s, ref=%s", kind, backup_ref)

    if system == "windows" and (kind == "restore-point" or backup_ref.isdigit()):
        return {
            "restored": False,
            "requires_reboot": True,
            "message": (
                f"To restore Windows Restore Point #{backup_ref}, please use Windows Recovery (rstrui.exe) "
                "or Advanced Startup Options to ensure system state integrity."
            ),
            "reference": backup_ref,
        }

    # Tarball restore on Linux
    if system == "linux" and backup_ref.endswith(".tar.gz"):
        backup_file = Path(config.repair.backup_dir) / backup_ref
        if not backup_file.exists():
            backup_file = Path(backup_ref)

        if backup_file.exists():
            res = run_command(["tar", "-xzf", str(backup_file), "-C", "/"], check=False)
            return {
                "restored": res.returncode == 0,
                "file": str(backup_file),
                "error": res.stderr if res.returncode != 0 else None,
                "message": "Extracted backup archive to root filesystem." if res.returncode == 0 else "Extraction failed.",
            }

    return {
        "restored": False,
        "message": "Automated restore requires specific reference and user confirmation.",
        "reference": backup_ref,
    }