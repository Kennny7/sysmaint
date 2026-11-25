# sysmaint/utils/common.py

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Union

logger = logging.getLogger("sysmaint.utils")


def run_command(
    command: Iterable[str],
    *,
    check: bool = False,
    timeout: Optional[int] = None,
    capture_output: bool = True,
    shell: bool = False,
    cwd: Optional[Union[str, Path]] = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run a system command safely with structured logging and error handling.

    Args:
        command: Iterable of command and arguments, or string if shell=True.
        check: If True, raise CalledProcessError on non-zero return code.
        timeout: Optional timeout in seconds.
        capture_output: If True, capture stdout and stderr as text.
        shell: Whether to execute command through the shell.
        cwd: Working directory.

    Returns:
        subprocess.CompletedProcess with text stdout/stderr.
    """
    if isinstance(command, str) and not shell:
        cmd_list = [command]
    elif isinstance(command, str) and shell:
        cmd_list = [command]
    else:
        cmd_list = list(command)

    display_cmd = cmd_list[0] if shell and isinstance(command, str) else " ".join(cmd_list)
    logger.debug("Executing command: %s", display_cmd)

    try:
        result = subprocess.run(
            cmd_list if not shell else display_cmd,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout,
            shell=shell,
            cwd=cwd,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Command timed out after %ds: %s", timeout, display_cmd)
        return subprocess.CompletedProcess(
            args=cmd_list,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
        )
    except subprocess.CalledProcessError as exc:
        logger.error("Command failed (rc=%d): %s\n%s", exc.returncode, display_cmd, exc.stderr)
        raise
    except FileNotFoundError:
        logger.warning("Command executable not found: %s", cmd_list[0] if cmd_list else "")
        return subprocess.CompletedProcess(
            args=cmd_list,
            returncode=127,
            stdout="",
            stderr=f"Executable not found: {cmd_list[0] if cmd_list else ''}",
        )
    except Exception as exc:
        logger.error("Unexpected error executing %s: %s", display_cmd, exc)
        return subprocess.CompletedProcess(
            args=cmd_list,
            returncode=-1,
            stdout="",
            stderr=str(exc),
        )

    if result.returncode != 0:
        logger.debug(
            "Command returned %d: %s\nstderr: %s",
            result.returncode,
            display_cmd,
            result.stderr.strip() if result.stderr else "",
        )
    return result


def format_bytes(num_bytes: Union[int, float]) -> str:
    """
    Convert a byte count into a human-readable string (e.g., '14.2 GB', '512 KB').
    """
    if num_bytes < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(num_bytes) < 1024.0:
            if unit in ("B", "KB"):
                return f"{num_bytes:.0f} {unit}"
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} EB"


def compute_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> Optional[str]:
    """
    Compute SHA-256 hash of a file safely in chunks.

    Returns:
        Hex-encoded SHA-256 string or None if unreadable.
    """
    path = Path(file_path)
    if not path.is_file():
        return None

    sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (PermissionError, OSError) as exc:
        logger.warning("Could not compute hash for %s: %s", file_path, exc)
        return None


def safe_delete_file(file_path: Union[str, Path]) -> tuple[bool, int]:
    """
    Safely delete a file, returning (success, bytes_freed).
    """
    path = Path(file_path)
    try:
        if path.is_file() or path.is_symlink():
            size = path.stat().st_size
            path.unlink(missing_ok=True)
            return True, size
    except (PermissionError, OSError) as exc:
        logger.debug("Failed to delete file %s: %s", file_path, exc)
    return False, 0


def safe_delete_dir_contents(dir_path: Union[str, Path]) -> tuple[int, int]:
    """
    Safely delete all files and subdirectories inside a folder without deleting the folder itself.

    Returns:
        tuple of (files_deleted_count, bytes_freed)
    """
    path = Path(dir_path)
    if not path.is_dir():
        return 0, 0

    files_deleted = 0
    bytes_freed = 0

    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            fp = Path(root) / f
            success, size = safe_delete_file(fp)
            if success:
                files_deleted += 1
                bytes_freed += size
        for d in dirs:
            dp = Path(root) / d
            try:
                dp.rmdir()
            except OSError:
                pass

    return files_deleted, bytes_freed