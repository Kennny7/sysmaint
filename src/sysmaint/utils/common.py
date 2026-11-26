# sysmaint/utils/common.py

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path

logger = logging.getLogger("sysmaint.utils")


def run_command(
    command: Iterable[str],
    *,
    check: bool = False,
    timeout: int | None = None,
    capture_output: bool = True,
    shell: bool = False,
    cwd: str | Path | None = None,
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
    if isinstance(command, str) and not shell or isinstance(command, str) and shell:
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
    except subprocess.TimeoutExpired:
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


_PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent)", re.IGNORECASE)


def extract_progress_percent(line: str) -> float | None:
    """Extract a real percentage (0-100) from command output lines (DISM, SFC, chkdsk)."""
    match = _PERCENT_RE.search(line)
    if not match:
        return None
    val = float(match.group(1))
    if 0.0 <= val <= 100.0:
        return val
    return None


def stream_command(
    command: Iterable[str],
    *,
    on_line: Callable[[str, float | None], None] | None = None,
    cwd: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Execute a command while streaming live output lines and parsed percentages.
    Handles both '\\n' and '\\r' updates used by tools like DISM and SFC.
    """
    cmd_list = [command] if isinstance(command, str) else list(command)
    captured: list[str] = []

    try:
        proc = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError:
        msg = f"Executable not found: {cmd_list[0] if cmd_list else ''}"
        if on_line:
            on_line(msg, None)
        return subprocess.CompletedProcess(args=cmd_list, returncode=127, stdout="", stderr=msg)
    except Exception as exc:
        if on_line:
            on_line(str(exc), None)
        return subprocess.CompletedProcess(args=cmd_list, returncode=-1, stdout="", stderr=str(exc))

    assert proc.stdout is not None
    buf = ""
    while True:
        ch = proc.stdout.read(1)
        if not ch:
            if buf.strip():
                line = buf.strip()
                captured.append(line)
                if on_line:
                    on_line(line, extract_progress_percent(line))
            break
        if ch in ("\r", "\n"):
            line = buf.strip()
            buf = ""
            if line:
                captured.append(line)
                if on_line:
                    on_line(line, extract_progress_percent(line))
        else:
            buf += ch

    rc = proc.wait()
    return subprocess.CompletedProcess(
        args=cmd_list,
        returncode=rc,
        stdout="\n".join(captured),
        stderr="",
    )


def format_bytes(num_bytes: float) -> str:
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


def compute_sha256(file_path: str | Path, chunk_size: int = 65536) -> str | None:
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


def safe_delete_file(file_path: str | Path) -> tuple[bool, int]:
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


def safe_delete_dir_contents(dir_path: str | Path) -> tuple[int, int]:
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