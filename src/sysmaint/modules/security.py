# sysmaint/modules/security.py

from __future__ import annotations

import logging
import platform
import shutil
from typing import Any

from ..utils.escalate import is_elevated

logger = logging.getLogger("sysmaint.security")


def audit_security_posture() -> dict[str, Any]:
    """
    Perform a security posture audit (Antivirus, Firewall, UAC/Sudo elevation).

    Returns:
        Dictionary with security scores, status flags, and actionable recommendations.
    """
    system = platform.system().lower()
    logger.info("Auditing security posture for %s", system)

    issues: list[str] = []
    score = 100

    elevated = is_elevated()
    if not elevated:
        issues.append("Toolkit is running in unprivileged user mode. Some deep security audits require Admin/root.")

    if system == "windows":
        from ..utils.windows import get_windows_security_status
        sec = get_windows_security_status()

        if not sec.get("realtime_protection", True):
            issues.append("Windows Defender Real-time Protection appears to be disabled!")
            score -= 30

        if not sec.get("firewall_enabled", True):
            issues.append("One or more Windows Firewall profiles are turned OFF.")
            score -= 25

        return {
            "system": "windows",
            "score": max(0, score),
            "elevated": elevated,
            "antivirus": sec.get("antivirus", "Windows Defender"),
            "realtime_protection": sec.get("realtime_protection", True),
            "firewall_active": sec.get("firewall_enabled", True),
            "firewall_profiles": sec.get("firewall_profiles", []),
            "issues": issues,
            "healthy": len(issues) == 0,
        }

    if system == "linux":
        from ..utils.linux import get_linux_security_status
        sec = get_linux_security_status()

        if not sec.get("firewall_active", False):
            issues.append(f"Linux Firewall ({sec.get('firewall', 'iptables/ufw')}) is inactive or unconfigured.")
            score -= 25

        has_clamav = bool(shutil.which("clamscan"))
        if not has_clamav:
            issues.append("ClamAV antivirus engine is not installed.")
            score -= 10

        return {
            "system": "linux",
            "score": max(0, score),
            "elevated": elevated,
            "firewall": sec.get("firewall", "Unknown"),
            "firewall_active": sec.get("firewall_active", False),
            "mac_system": sec.get("mac_system", "None"),
            "mac_enforcing": sec.get("mac_enforcing", False),
            "clamav_installed": has_clamav,
            "issues": issues,
            "healthy": len(issues) == 0,
        }

    return {
        "system": system,
        "score": 80,
        "elevated": elevated,
        "issues": issues,
        "healthy": True,
    }
