# sysmaint/utils/common.py

from __future__ import annotations

import logging
import subprocess
from typing import Iterable, Optional

logger = logging.getLogger("sysmaint.utils")


def run_command(
    command: Iterable[str],
    *,
    check: bool = False,
    timeout: Optional[int] = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command safely and log its execution.

    Args:
        command: Iterable of command and arguments.
        check: If True, raise CalledProcessError on non-zero return code.
        timeout: Optional timeout in seconds.
        capture_output: If True, capture stdout and stderr.

    Returns:
        CompletedProcess with stdout/stderr strings.
    """
    cmd_list = list(command)
    logger.debug("Executing: %s", " ".join(cmd_list))
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("Command failed: %s\n%s", " ".join(cmd_list), exc.stderr)
        raise
    if result.returncode != 0:
        logger.debug(
            "Command returned %d: %s\nstderr: %s",
            result.returncode,
            " ".join(cmd_list),
            result.stderr,
        )
    return result