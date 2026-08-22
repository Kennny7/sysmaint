# sysmaint/utils/linux.py

from __future__ import annotations

import logging
import shutil
from typing import Optional

from .common import run_command

logger = logging.getLogger("sysmaint.linux")


def detect_package_manager() -> Optional[str]:
    """Detect the system package manager and return its command name."""
    for pm in ("apt", "dnf", "yum", "zypper", "pacman"):
        if shutil.which(pm):
            return pm
    return None


def create_btrfs_snapshot(source: str, destination: str) -> bool:
    """Create a Btrfs snapshot if the filesystem supports it."""
    if shutil.which("btrfs"):
        result = run_command(["btrfs", "subvolume", "snapshot", source, destination])
        return result.returncode == 0
    return False