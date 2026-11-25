# sysmaint/logging_setup.py

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.logging import RichHandler
except ImportError:
    RichHandler = None


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path | str] = None,
    verbose: bool = False,
) -> logging.Logger:
    """
    Configure root logging for SysMaint.

    Args:
        level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        log_file: Optional path to append log entries to.
        verbose: If True, force DEBUG level.

    Returns:
        Configured logger instance for 'sysmaint'.
    """
    log_level = logging.DEBUG if verbose else getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = []

    # Console handler (prefer RichHandler if rich is installed)
    if RichHandler is not None:
        console_handler = RichHandler(
            level=log_level,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
        )
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        console_handler.setFormatter(logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S"))

    handlers.append(console_handler)

    # File handler
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_fmt = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        file_handler.setFormatter(logging.Formatter(file_fmt, "%Y-%m-%d %H:%M:%S"))
        handlers.append(file_handler)

    logging.basicConfig(level=log_level, handlers=handlers, force=True)
    return logging.getLogger("sysmaint")