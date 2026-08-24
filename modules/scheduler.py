# sysmaint/modules/scheduler.py

from __future__ import annotations

import logging
import platform
import sys
from typing import Any, Optional

from ..utils.common import run_command

logger = logging.getLogger("sysmaint.scheduler")

TASK_NAME = "SysMaintAutomatedMaintenance"


def get_schedule_status() -> dict[str, Any]:
    """
    Check if SysMaint automated maintenance is currently scheduled.
    """
    system = platform.system().lower()
    logger.info("Checking maintenance schedule status for %s", system)

    if system == "windows":
        res = run_command(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"], check=False)
        is_installed = res.returncode == 0 and "TaskName:" in res.stdout
        return {
            "system": "windows",
            "installed": is_installed,
            "task_name": TASK_NAME,
            "details": res.stdout.strip() if is_installed else "Task not scheduled",
        }

    if system == "linux":
        res = run_command(["crontab", "-l"], check=False)
        is_installed = "sysmaint" in res.stdout
        return {
            "system": "linux",
            "installed": is_installed,
            "details": [line for line in res.stdout.splitlines() if "sysmaint" in line] if is_installed else [],
        }

    return {"system": system, "installed": False}


def install_schedule(
    interval: str = "WEEKLY",
    time_str: str = "02:00",
    command_flag: str = "smart-scan",
) -> dict[str, Any]:
    """
    Install an automated background maintenance task.

    Args:
        interval: 'DAILY', 'WEEKLY', or 'MONTHLY'.
        time_str: Time in HH:MM (24-hour) format.
        command_flag: Subcommand to run, e.g. 'smart-scan' or 'clean'.

    Returns:
        Dictionary indicating status.
    """
    system = platform.system().lower()
    py_exec = sys.executable
    maint_cmd = f'"{py_exec}" -m sysmaint {command_flag} --yes'

    logger.info("Installing maintenance schedule (%s at %s)", interval, time_str)

    if system == "windows":
        # schtasks /Create /SC WEEKLY /TN SysMaintAutomatedMaintenance /TR "python -m sysmaint smart-scan --yes" /ST 02:00 /F /RL HIGHEST
        cmd = [
            "schtasks",
            "/Create",
            "/SC",
            interval.upper(),
            "/TN",
            TASK_NAME,
            "/TR",
            maint_cmd,
            "/ST",
            time_str,
            "/F",
            "/RL",
            "HIGHEST",
        ]
        res = run_command(cmd, check=False)
        return {
            "success": res.returncode == 0,
            "system": "windows",
            "message": "Scheduled task created successfully in Windows Task Scheduler." if res.returncode == 0 else f"Failed to create task: {res.stderr.strip()}",
        }

    if system == "linux":
        # Determine cron schedule
        hh, mm = time_str.split(":") if ":" in time_str else ("02", "00")
        if interval.upper() == "DAILY":
            cron_expr = f"{mm} {hh} * * *"
        elif interval.upper() == "MONTHLY":
            cron_expr = f"{mm} {hh} 1 * *"
        else:  # WEEKLY
            cron_expr = f"{mm} {hh} * * 0"

        cron_line = f"{cron_expr} {maint_cmd} > /var/log/sysmaint-cron.log 2>&1 # sysmaint"

        existing = run_command(["crontab", "-l"], check=False).stdout
        filtered = [l for l in existing.splitlines() if "sysmaint" not in l]
        filtered.append(cron_line)
        new_cron = "\n".join(filtered) + "\n"

        proc = run_command(["crontab", "-"], check=False)
        return {
            "success": True,
            "system": "linux",
            "message": f"Installed cron schedule: '{cron_expr}'",
        }

    return {"success": False, "message": f"Unsupported platform: {system}"}


def remove_schedule() -> dict[str, Any]:
    """
    Remove any configured automated maintenance schedules.
    """
    system = platform.system().lower()
    logger.info("Removing maintenance schedule")

    if system == "windows":
        res = run_command(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], check=False)
        return {
            "success": res.returncode == 0,
            "message": "Removed Windows scheduled task." if res.returncode == 0 else "No scheduled task found to remove.",
        }

    if system == "linux":
        existing = run_command(["crontab", "-l"], check=False).stdout
        filtered = [l for l in existing.splitlines() if "sysmaint" not in l]
        new_cron = "\n".join(filtered) + "\n"
        run_command(["crontab", "-"], check=False)
        return {"success": True, "message": "Removed sysmaint cron jobs."}

    return {"success": False, "message": f"Unsupported platform: {system}"}
