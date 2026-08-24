# sysmaint/modules/backup.py

from __future__ import annotations

import logging
import os
import platform
import time
from pathlib import Path
from typing import Any

from ..config import SysMaintConfig
from ..utils.common import format_bytes, run_command

logger = logging.getLogger("sysmaint.backup")


def create_backup(
    config: SysMaintConfig,
    kind: str = "auto",
    description: str = "SysMaint Automatic Backup",
) -> dict[str, Any]:
    """
    Create a system backup, Windows restore point, or Linux archive.

    Args:
        config: SysMaintConfig instance.
        kind: 'auto', 'restore-point', 'tar', or 'snapshot'.
        description: Description for the backup or restore point.

    Returns:
        Dictionary describing the backup outcome.
    """
    system = platform.system().lower()
    logger.info("Creating backup (kind=%s, system=%s)", kind, system)

    if system == "windows":
        from ..utils import windows
        if kind in ("restore-point", "auto"):
            try:
                windows.create_restore_point(description)
                return {
                    "type": "restore-point",
                    "created": True,
                    "description": description,
                    "message": "Windows System Restore Point created successfully.",
                }
            except Exception as exc:
                return {
                    "type": "restore-point",
                    "created": False,
                    "error": str(exc),
                }

        # Backup critical registry keys
        if kind == "registry":
            backup_dir = Path(config.repair.backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            reg_file = backup_dir / f"sysmaint-registry-{timestamp}.reg"
            res = run_command(["reg", "export", r"HKLM\SYSTEM", str(reg_file), "/y"], check=False)
            return {
                "type": "registry",
                "path": str(reg_file),
                "created": res.returncode == 0,
                "error": res.stderr if res.returncode != 0 else None,
            }

        return {"created": False, "error": f"Unsupported backup kind on Windows: {kind}"}

    if system == "linux":
        from ..utils import linux
        backup_dir = Path(config.repair.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        # Btrfs snapshot
        if kind == "snapshot":
            snap_path = f"/snapshots/sysmaint-snap-{timestamp}"
            if linux.create_btrfs_snapshot("/", snap_path):
                return {"type": "snapshot", "path": snap_path, "created": True}
            return {
                "type": "snapshot",
                "created": False,
                "error": "Btrfs snapshot failed or root is not a Btrfs subvolume",
            }

        # Tarball of /etc configuration
        tarball = backup_dir / f"sysmaint-config-{timestamp}.tar.gz"
        result = run_command(["tar", "-czf", str(tarball), "/etc"], check=False)
        if result.returncode == 0 and tarball.exists():
            size = tarball.stat().st_size
            return {
                "type": "tar",
                "path": str(tarball),
                "size_formatted": format_bytes(size),
                "created": True,
                "message": f"Archived /etc to {tarball.name}",
            }
        return {
            "type": "tar",
            "path": str(tarball),
            "created": False,
            "error": result.stderr,
        }

    return {"created": False, "error": f"Unsupported platform: {system}"}