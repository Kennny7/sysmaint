# sysmaint/modules/report.py

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from typing import Any


def build_report(results: dict[str, Any]) -> dict[str, Any]:
    """
    Build a structured report dictionary.

    Args:
        results: Dictionary of results produced by the executed command.

    Returns:
        Report dictionary with timestamp, OS, and results.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "os": platform.system(),
        "results": results,
    }


def format_report(report: dict[str, Any], json_output: bool = False) -> str:
    """
    Format a report as JSON or human-readable text.

    Args:
        report: Report dictionary from build_report().
        json_output: If True, return pretty-printed JSON.

    Returns:
        Formatted report string.
    """
    if json_output:
        return json.dumps(report, indent=2, default=str)

    lines = [
        "SysMaint Report",
        f"  Timestamp : {report.get('timestamp', 'unknown')}",
        f"  OS        : {report.get('os', 'unknown')}",
        "  Results   :",
    ]
    results = report.get("results", {})
    if not results:
        lines.append("    (none)")
    for section, data in results.items():
        if isinstance(data, dict):
            if "error" in data:
                lines.append(f"    {section}: ERROR - {data['error']}")
            else:
                lines.append(f"    {section}: {data}")
        else:
            lines.append(f"    {section}: {data}")
    return "\n".join(lines)