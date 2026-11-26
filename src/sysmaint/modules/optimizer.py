# sysmaint/modules/optimizer.py

from __future__ import annotations

import logging
from typing import Any

from ..config import SysMaintConfig
from .backup import create_backup
from .cleaner import clean_junk, scan_junk
from .disk import get_disk_partitions
from .memory import check_memory, optimize_memory
from .network import flush_dns
from .security import audit_security_posture
from .services import ensure_expected_services, list_services

logger = logging.getLogger("sysmaint.optimizer")


def run_smart_scan(config: SysMaintConfig) -> dict[str, Any]:
    """
    Perform a unified, non-destructive Smart Health Scan across all system areas.

    Returns:
        Comprehensive health report with a 0-100 System Health Score and actionable findings.
    """
    logger.info("Starting 1-Click Smart System Health Scan")
    findings: list[dict[str, Any]] = []
    score = 100

    # 1. Disk Space & Partitions
    partitions = get_disk_partitions()
    for part in partitions:
        if part.get("percent", 0) > 90.0:
            findings.append({
                "category": "Disk",
                "severity": "High",
                "title": f"Drive {part.get('device')} is nearly full ({part.get('percent')}%)",
                "fixable": True,
                "action": "clean_junk",
            })
            score -= 15
        elif part.get("percent", 0) > 80.0:
            findings.append({
                "category": "Disk",
                "severity": "Medium",
                "title": f"Drive {part.get('device')} has low storage space ({part.get('percent')}%)",
                "fixable": True,
                "action": "clean_junk",
            })
            score -= 5

    # 2. Memory Pressure
    mem_info = check_memory()
    if mem_info.get("percent", 0) > 85.0:
        findings.append({
            "category": "Memory",
            "severity": "Medium",
            "title": f"High RAM usage ({mem_info.get('percent')}%) - cache trimming recommended",
            "fixable": True,
            "action": "optimize_memory",
        })
        score -= 10

    # 3. Junk Files & Temporary Data
    junk_info = scan_junk()
    if junk_info.get("total_bytes", 0) > 500 * 1024 * 1024:  # > 500 MB
        findings.append({
            "category": "Cleaner",
            "severity": "Medium",
            "title": f"Found {junk_info.get('total_bytes_formatted')} of junk files ({junk_info.get('total_files')} files)",
            "fixable": True,
            "action": "clean_junk",
            "data": junk_info,
        })
        score -= 10
    elif junk_info.get("total_bytes", 0) > 50 * 1024 * 1024:  # > 50 MB
        findings.append({
            "category": "Cleaner",
            "severity": "Low",
            "title": f"Found {junk_info.get('total_bytes_formatted')} of temporary cache files",
            "fixable": True,
            "action": "clean_junk",
            "data": junk_info,
        })
        score -= 5

    # 4. Services
    services = list_services()
    failed_services = [s for s in services if not s.get("healthy", True)]
    if failed_services:
        findings.append({
            "category": "Services",
            "severity": "High",
            "title": f"Found {len(failed_services)} failed or stopped service(s)",
            "fixable": True,
            "action": "restart_services",
            "details": [s.get("name") for s in failed_services[:5]],
        })
        score -= 15

    # 5. Security Posture
    sec_info = audit_security_posture()
    for issue in sec_info.get("issues", []):
        findings.append({
            "category": "Security",
            "severity": "High" if "Disabled" in issue or "OFF" in issue else "Medium",
            "title": issue,
            "fixable": False,
        })
        score -= 10

    # Final Score Normalization
    final_score = max(0, min(100, score))
    if final_score >= 90:
        health_grade = "Excellent"
    elif final_score >= 75:
        health_grade = "Good"
    elif final_score >= 50:
        health_grade = "Fair"
    else:
        health_grade = "Critical"

    return {
        "health_score": final_score,
        "health_grade": health_grade,
        "total_issues": len(findings),
        "fixable_issues": len([f for f in findings if f.get("fixable")]),
        "findings": findings,
        "memory_summary": {
            "used_formatted": mem_info.get("used_formatted"),
            "total_formatted": mem_info.get("total_formatted"),
            "percent": mem_info.get("percent"),
        },
        "junk_summary": {
            "reclaimable_bytes": junk_info.get("total_bytes"),
            "reclaimable_formatted": junk_info.get("total_bytes_formatted"),
            "file_count": junk_info.get("total_files"),
        },
    }


def run_auto_fix(
    config: SysMaintConfig,
    create_restore: bool = True,
) -> dict[str, Any]:
    """
    Execute 1-Click Auto-Fix for all detected fixable issues.

    Args:
        config: SysMaintConfig instance.
        create_restore: Whether to create a backup / restore point before fixing.

    Returns:
        Summary of executed repair operations and updated health state.
    """
    logger.info("Executing 1-Click Auto-Fix")
    results: dict[str, Any] = {}

    # 1. Automatic Restore Point Creation
    if create_restore and config.repair.auto_create_restore_point:
        try:
            results["backup"] = create_backup(config, kind="auto", description="SysMaint Pre-Optimization Point")
        except Exception as exc:
            results["backup"] = {"created": False, "error": str(exc)}

    # 2. Clean Junk Files
    results["cleaner"] = clean_junk(dry_run=False)

    # 3. Optimize Memory
    results["memory"] = optimize_memory()

    # 4. Flush DNS Cache
    results["network"] = flush_dns()

    # 5. Ensure Expected Services
    if config.services.enable and config.services.expected_services:
        results["services"] = ensure_expected_services(config.services.expected_services)

    # Re-evaluate health score
    new_scan = run_smart_scan(config)
    results["new_health_score"] = new_scan["health_score"]
    results["new_health_grade"] = new_scan["health_grade"]
    results["remaining_issues"] = new_scan["total_issues"]

    return results
