# sysmaint/utils/escalate.py

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import sys

logger = logging.getLogger("sysmaint.escalate")


def ensure_elevated() -> None:
    """
    Re-launch the current script with elevated privileges if needed.

    Windows: Uses ShellExecuteW with the 'runas' verb (UAC prompt).
    Linux/macOS: Uses sudo if not already root.
    """
    if os.name == "nt":
        try:
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except AttributeError:
            is_admin = False

        if not is_admin:
            logger.info("Not running as administrator. Requesting elevation...")
            params = subprocess.list2cmdline(sys.argv[1:])
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 1
            )
            # ShellExecuteW returns a value greater than 32 on success
            if ret <= 32:
                logger.error("UAC elevation failed (code %d).", ret)
                raise RuntimeError("UAC elevation failed")
            sys.exit(0)
    else:
        if os.geteuid() != 0:
            logger.info("Not running as root. Restarting with sudo...")
            try:
                subprocess.check_call(["sudo", sys.executable] + sys.argv)
                sys.exit(0)
            except subprocess.CalledProcessError as exc:
                logger.error("Sudo elevation failed. Please run as root.")
                raise SystemExit(1) from exc
            