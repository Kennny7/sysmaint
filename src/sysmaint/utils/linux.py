# sysmaint/utils/linux.py

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from .common import run_command

logger = logging.getLogger("sysmaint.linux")


def detect_package_manager() -> str | None:
    """Detect the system package manager and return its command name."""
    for pm in ("apt-get", "apt", "dnf", "yum", "zypper", "pacman", "apk"):
        if shutil.which(pm):
            return pm
    return None


def clean_package_cache(dry_run: bool = False) -> dict[str, Any]:
    """
    Clean package manager download caches (e.g. apt clean, dnf clean all).
    """
    pm = detect_package_manager()
    if not pm:
        return {"status": "skipped", "message": "No supported package manager detected"}

    cmd_map = {
        "apt": ["apt-get", "clean"],
        "apt-get": ["apt-get", "clean"],
        "dnf": ["dnf", "clean", "all"],
        "yum": ["yum", "clean", "all"],
        "zypper": ["zypper", "clean", "--all"],
        "pacman": ["pacman", "-Sc", "--noconfirm"],
        "apk": ["apk", "cache", "clean"],
    }

    cmd = cmd_map.get(pm)
    if not cmd:
        return {"status": "unsupported", "package_manager": pm}

    if dry_run:
        return {"status": "dry_run", "command": " ".join(cmd)}

    result = run_command(cmd, check=False)
    return {
        "status": "success" if result.returncode == 0 else "error",
        "package_manager": pm,
        "returncode": result.returncode,
        "output": result.stdout,
    }


def get_failed_systemd_units() -> list[dict[str, str]]:
    """
    Return list of failed systemd units and services.
    """
    if not shutil.which("systemctl"):
        return []

    result = run_command(
        ["systemctl", "--failed", "--no-legend", "--no-pager"],
        check=False,
    )
    failed = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) >= 4:
            failed.append({
                "unit": parts[0],
                "load": parts[1],
                "active": parts[2],
                "sub": parts[3],
                "description": parts[4] if len(parts) > 4 else "",
            })
    return failed


def get_system_journal_errors(max_lines: int = 50) -> list[str]:
    """
    Retrieve recent priority 3 (Error) and above systemd journal entries.
    """
    if not shutil.which("journalctl"):
        return []

    result = run_command(
        ["journalctl", "-p", "3", "-xb", "--no-pager", "-n", str(max_lines)],
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def vacuum_systemd_journal(retention: str = "7d") -> bool:
    """
    Vacuum old journal logs to free disk space.
    """
    if not shutil.which("journalctl"):
        return False
    result = run_command(["journalctl", f"--vacuum-time={retention}"], check=False)
    return result.returncode == 0


def flush_linux_dns() -> bool:
    """
    Flush Linux DNS resolver cache using resolvectl, systemd-resolve, or nscd.
    """
    if shutil.which("resolvectl"):
        res = run_command(["resolvectl", "flush-caches"], check=False)
        return res.returncode == 0
    elif shutil.which("systemd-resolve"):
        res = run_command(["systemd-resolve", "--flush-caches"], check=False)
        return res.returncode == 0
    elif shutil.which("nscd"):
        res = run_command(["nscd", "-i", "hosts"], check=False)
        return res.returncode == 0
    return False


def get_linux_security_status() -> dict[str, Any]:
    """
    Check Linux firewall, SELinux/AppArmor, and basic security configuration.
    """
    status: dict[str, Any] = {
        "firewall": "Unknown",
        "firewall_active": False,
        "mac_system": "None",
        "mac_enforcing": False,
    }

    # Firewall check
    if shutil.which("ufw"):
        res = run_command(["ufw", "status"], check=False)
        status["firewall"] = "UFW"
        status["firewall_active"] = "Status: active" in res.stdout
    elif shutil.which("firewall-cmd"):
        res = run_command(["firewall-cmd", "--state"], check=False)
        status["firewall"] = "firewalld"
        status["firewall_active"] = "running" in res.stdout
    elif shutil.which("iptables"):
        res = run_command(["iptables", "-L", "-n"], check=False)
        status["firewall"] = "iptables"
        status["firewall_active"] = res.returncode == 0 and len(res.stdout.splitlines()) > 5

    # Mandatory Access Control check (AppArmor / SELinux)
    if shutil.which("aa-status"):
        res = run_command(["aa-status", "--enabled"], check=False)
        status["mac_system"] = "AppArmor"
        status["mac_enforcing"] = res.returncode == 0
    elif shutil.which("getenforce"):
        res = run_command(["getenforce"], check=False)
        status["mac_system"] = "SELinux"
        status["mac_enforcing"] = res.stdout.strip().lower() == "enforcing"

    return status


def get_linux_startup_items() -> list[dict[str, Any]]:
    """
    Scan Linux XDG autostart directories and user systemd units for startup apps.
    """
    items = []
    autostart_dirs = [
        Path.home() / ".config" / "autostart",
        Path("/etc/xdg/autostart"),
    ]

    for d in autostart_dirs:
        if d.is_dir():
            for f in d.glob("*.desktop"):
                try:
                    name = f.stem
                    exec_cmd = ""
                    hidden = False
                    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if line.startswith("Name="):
                            name = line.split("=", 1)[1].strip()
                        elif line.startswith("Exec="):
                            exec_cmd = line.split("=", 1)[1].strip()
                        elif line.startswith("Hidden="):
                            hidden = line.split("=", 1)[1].strip().lower() == "true"
                    if not hidden and exec_cmd:
                        items.append({
                            "name": name,
                            "command": exec_cmd,
                            "location": str(d),
                            "file": str(f),
                            "enabled": True,
                        })
                except Exception:
                    pass

    return items


def create_btrfs_snapshot(source: str, destination: str) -> bool:
    """Create a Btrfs snapshot if the filesystem supports it."""
    if shutil.which("btrfs"):
        result = run_command(["btrfs", "subvolume", "snapshot", source, destination], check=False)
        return result.returncode == 0
    return False


def get_linux_temp_paths() -> dict[str, Path]:
    """Return standard Linux junk, log, and cache directories."""
    paths = {
        "System Temp": Path("/tmp"),
        "Variable Temp": Path("/var/tmp"),
    }
    user_cache = Path.home() / ".cache"
    if user_cache.is_dir():
        paths["User Cache"] = user_cache

    user_trash = Path.home() / ".local" / "share" / "Trash"
    if user_trash.is_dir():
        paths["User Trash"] = user_trash

    var_log = Path("/var/log")
    if var_log.is_dir():
        paths["System Logs"] = var_log

    return paths


def drop_linux_page_caches() -> bool:
    """
    Sync and drop page caches / dentries on Linux (requires root).
    """
    try:
        run_command(["sync"], check=False)
        drop_path = Path("/proc/sys/vm/drop_caches")
        if drop_path.exists():
            with open(drop_path, "w") as f:
                f.write("3\n")
            return True
    except (PermissionError, OSError):
        pass
    return False