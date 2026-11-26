# sysmaint/utils/escalate.py

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import sys

logger = logging.getLogger("sysmaint.escalate")


def is_elevated() -> bool:
    """
    Check if the current process is running with elevated privileges (Admin/root).

    Returns:
        True if running as Administrator on Windows or root on Linux/macOS.
    """
    if os.name == "nt":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return False
    else:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False


def request_elevation(
    args: list[str] | None = None,
    exit_on_relaunch: bool = True,
) -> bool:
    """
    Request elevated privileges by re-launching the process.

    Windows: Triggers a UAC prompt using ShellExecuteW with the 'runas' verb.
    Linux/macOS: Spawns sudo / pkexec.

    Args:
        args: Optional custom command-line arguments. Defaults to current sys.argv[1:].
        exit_on_relaunch: Whether to exit current non-elevated process upon successful launch.

    Returns:
        True if already elevated or if elevation process was launched.
    """
    if is_elevated():
        return True

    cmd_args = sys.argv[1:] if args is None else args

    if os.name == "nt":
        logger.info("Requesting administrative elevation via Windows UAC...")
        params = subprocess.list2cmdline(cmd_args)
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1,  # SW_SHOWNORMAL
        )
        if ret > 32:
            logger.info("Elevated process spawned successfully.")
            if exit_on_relaunch:
                sys.exit(0)
            return True
        else:
            logger.warning("UAC elevation was cancelled or failed (code %d).", ret)
            return False
    else:
        logger.info("Requesting root elevation via sudo...")
        try:
            sudo_cmd = ["sudo", sys.executable] + sys.argv
            result = subprocess.run(sudo_cmd, check=False)
            if exit_on_relaunch:
                sys.exit(result.returncode)
            return result.returncode == 0
        except Exception as exc:
            logger.error("Failed to execute sudo: %s", exc)
            return False


def ensure_elevated() -> None:
    """
    Ensure the process is running as root or administrator.
    If not, re-launches with elevated privileges.
    """
    if not is_elevated():
        request_elevation(exit_on_relaunch=True)