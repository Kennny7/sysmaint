# sysmaint/modules/backup.py

from __future__ import annotations

import logging
import platform
import time
from pathlib import Path
from typing import Any

from ..config import SysMaintConfig
from ..utils.common import run_command
from ..utils import windows

logger = logging.getLogger("sysmaint.backup")


def create_backup(config: SysMaintConfig, kind: str = "auto") -> dict[str, Any]:
    """
    Create a system backup or restore point.

    Args:
        config: SysMaintConfig instance.
        kind: 'auto', 'restore-point', or 'snapshot'.

    Returns:
        Dictionary describing the backup result.
    """
    system = platform.system().lower()
    logger.info("Creating backup (kind=%s)", kind)

    if system == "windows":
        if kind in ("restore-point", "auto"):
            try:
                windows.create_restore_point("SysMaint Backup")
                return {"type": "restore-point", "created": True}
            except Exception as exc:
                return {"type": "restore-point", "created": False, "error": str(exc)}
        return {"created": False, "error": f"Unsupported backup kind on Windows: {kind}"}

    if system == "linux":
        backup_dir = Path(config.repair.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        # Try LVM snapshot if requested and possible
        if kind == "snapshot":
            # This is a simplified placeholder; real LVM/Btrfs snapshot requires volume info.
            return {"type": "snapshot", "created": False, "error": "LVM/Btrfs snapshot not implemented"}

        # Fallback: create a compressed tarball of /etc (config files)
        tarball = backup_dir / f"sysmaint-config-{timestamp}.tar.gz"
        result = run_command(["tar", "-czf", str(tarball), "/etc"], check=False)
        if result.returncode == 0:
            return {"type": "tar", "path": str(tarball), "created": True}
        return {
            "type": "tar",
            "path": str(tarball),
            "created": False,
            "error": result.stderr,
        }

    return {"created": False, "error": f"Unsupported platform: {system}"}