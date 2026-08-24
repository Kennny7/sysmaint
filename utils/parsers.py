# sysmaint/utils/parsers.py

from __future__ import annotations

import re
from typing import Any, List, Optional


def parse_clamscan_output(output: str) -> List[dict[str, Any]]:
    """
    Parse clamscan output and return a list of infected file records.

    Expected line format: `/path/to/file: MalwareName FOUND`
    """
    threats = []
    for line in output.splitlines():
        line = line.strip()
        if "FOUND" in line and not line.startswith("Known viruses"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                file_path = parts[0].strip()
                malware_part = parts[1].replace("FOUND", "").strip()
                threats.append({
                    "file": file_path,
                    "malware": malware_part,
                    "engine": "clamav",
                })
    return threats


def parse_sfc_output(output: str) -> dict[str, Any]:
    """
    Parse SFC console output on Windows.
    """
    out_lower = output.lower()
    corruptions_found = "found corrupt files" in out_lower or "resource protection found corrupt" in out_lower
    repaired = "successfully repaired" in out_lower
    clean = "did not find any integrity violations" in out_lower
    reboot_required = "reboot" in out_lower or "restart" in out_lower

    status = "Clean"
    if clean:
        status = "Clean"
    elif corruptions_found and repaired:
        status = "Repaired"
    elif corruptions_found and not repaired:
        status = "Corrupted (Unrepaired)"
    elif "could not perform" in out_lower:
        status = "Error"

    return {
        "status": status,
        "clean": clean,
        "corruptions_found": corruptions_found,
        "repaired": repaired,
        "reboot_required": reboot_required,
        "raw": output.strip(),
    }


def parse_dism_output(output: str) -> dict[str, Any]:
    """
    Parse Windows DISM check/scan/restore health output.
    """
    out_lower = output.lower()
    healthy = "no component store corruption detected" in out_lower
    repairable = "the component store is repairable" in out_lower
    repaired = "the restore operation completed successfully" in out_lower
    corrupted = "component store has been corrupted" in out_lower or repairable

    status = "Healthy"
    if healthy:
        status = "Healthy"
    elif repaired:
        status = "Repaired Successfully"
    elif repairable:
        status = "Corruption Detected (Repairable)"
    elif corrupted:
        status = "Corrupted"

    return {
        "status": status,
        "healthy": healthy,
        "corrupted": corrupted,
        "repaired": repaired,
        "raw": output.strip(),
    }


def parse_sfc_log(log_text: str) -> List[str]:
    """
    Extract repaired file references from SFC CBS log snippets.
    Looks for lines containing '[SR]'.
    """
    repaired_files = []
    for line in log_text.splitlines():
        if "[SR]" in line and "Repairing corrupted file" in line:
            repaired_files.append(line.strip())
    return repaired_files


def parse_fsck_output(output: str) -> dict[str, Any]:
    """Extract basic summary from fsck output."""
    clean = "clean" in output.lower()
    errors = re.findall(r"error|corrupt|inconsistent", output, re.IGNORECASE)
    return {
        "clean": clean,
        "error_count": len(errors),
        "errors_found": len(errors) > 0,
        "raw": output.strip(),
    }


def parse_driverquery_output(output: str) -> List[dict[str, str]]:
    """
    Parse Windows driverquery /v CSV or tabular output.
    """
    drivers = []
    lines = output.splitlines()
    for line in lines:
        if line.startswith('"') and '","' in line:
            # CSV format
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 4 and parts[0] != "Module Name":
                drivers.append({
                    "name": parts[0],
                    "display_name": parts[1] if len(parts) > 1 else parts[0],
                    "driver_type": parts[2] if len(parts) > 2 else "",
                    "state": parts[4] if len(parts) > 4 else "Running",
                    "status": parts[5] if len(parts) > 5 else "OK",
                })
        elif len(line.split()) >= 3 and not line.startswith("==") and not line.startswith("Module"):
            parts = line.split(None, 3)
            drivers.append({
                "name": parts[0],
                "display_name": parts[1],
                "driver_type": parts[2],
                "state": parts[3] if len(parts) > 3 else "Running",
                "status": "OK",
            })
    return drivers


def parse_ping_output(output: str) -> dict[str, Any]:
    """
    Parse ping command output across Windows and Linux.
    """
    avg_match = re.search(r"Average = (\d+)ms|avg = [\d\.]+/([\d\.]+)/", output)
    loss_match = re.search(r"(\d+)% loss", output)
    
    latency = None
    if avg_match:
        val = avg_match.group(1) or avg_match.group(2)
        if val:
            try:
                latency = float(val)
            except ValueError:
                pass

    packet_loss = 100
    if loss_match:
        try:
            packet_loss = int(loss_match.group(1))
        except ValueError:
            pass

    return {
        "reachable": packet_loss < 100,
        "packet_loss_percent": packet_loss,
        "avg_latency_ms": latency,
    }