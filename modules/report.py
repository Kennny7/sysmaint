# sysmaint/modules/report.py

from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


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
        "os_release": platform.release(),
        "hostname": platform.node(),
        "results": results,
    }


def format_report(report: dict[str, Any], json_output: bool = False) -> str:
    """
    Format a report as JSON or structured human-readable text.

    Args:
        report: Report dictionary from build_report().
        json_output: If True, return pretty-printed JSON.

    Returns:
        Formatted report string.
    """
    if json_output:
        return json.dumps(report, indent=2, default=str)

    lines = [
        "=" * 60,
        "  SysMaint - System Maintenance Report",
        "=" * 60,
        f"  Timestamp : {report.get('timestamp', 'unknown')}",
        f"  Host      : {report.get('hostname', 'unknown')}",
        f"  OS        : {report.get('os', 'unknown')} {report.get('os_release', '')}",
        "-" * 60,
        "  RESULTS SUMMARY:",
        "-" * 60,
    ]

    results = report.get("results", {})
    if not results:
        lines.append("    (No operations executed)")

    for section, data in results.items():
        if isinstance(data, dict):
            if "error" in data:
                lines.append(f"  [!] {section.upper()}: ERROR - {data['error']}")
            elif "message" in data:
                lines.append(f"  [*] {section.upper()}: {data['message']}")
            else:
                lines.append(f"  [*] {section.upper()}:")
                for k, v in data.items():
                    if k not in ("output", "stderr", "raw", "data"):
                        lines.append(f"      - {k}: {v}")
        else:
            lines.append(f"  [*] {section.upper()}: {data}")

    lines.append("=" * 60)
    return "\n".join(lines)


def generate_html_report(
    report: dict[str, Any],
    output_path: Optional[str | Path] = None,
) -> str:
    """
    Generate a modern, responsive standalone HTML health report dashboard.

    Args:
        report: Report dictionary.
        output_path: Optional file path to save HTML to.

    Returns:
        HTML string.
    """
    timestamp = report.get("timestamp", datetime.now(timezone.utc).isoformat())
    host = report.get("hostname", platform.node())
    os_name = f"{report.get('os', platform.system())} {report.get('os_release', '')}"
    results = report.get("results", {})

    # Extract health score if present
    health_score = 100
    health_grade = "Good"
    if "smart_scan" in results and isinstance(results["smart_scan"], dict):
        health_score = results["smart_scan"].get("health_score", 100)
        health_grade = results["smart_scan"].get("health_grade", "Good")
    elif "optimizer" in results and isinstance(results["optimizer"], dict):
        health_score = results["optimizer"].get("new_health_score", 100)
        health_grade = results["optimizer"].get("new_health_grade", "Good")

    score_color = "#10b981" if health_score >= 85 else ("#3b82f6" if health_score >= 70 else ("#f59e0b" if health_score >= 50 else "#ef4444"))

    # Render section cards
    sections_html = []
    for sec_name, data in results.items():
        content_items = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k in ("output", "stderr", "raw", "data") or isinstance(v, (dict, list)):
                    continue
                content_items.append(f"<div class='metric-row'><span class='metric-key'>{k.replace('_', ' ').capitalize()}</span><span class='metric-val'>{v}</span></div>")
        else:
            content_items.append(f"<div class='metric-row'><span>{data}</span></div>")

        items_str = "".join(content_items) or "<div class='metric-row'><span>Completed successfully</span></div>"
        sections_html.append(f"""
        <div class="card">
            <div class="card-header">
                <h3>{sec_name.replace('_', ' ').upper()}</h3>
            </div>
            <div class="card-body">
                {items_str}
            </div>
        </div>
        """)

    sections_str = "".join(sections_html)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SysMaint Health Report - {host}</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #38bdf8;
            --accent-gradient: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            --border: #334155;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background-color: var(--bg-primary); color: var(--text-primary); padding: 2rem; line-height: 1.6; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; padding-bottom: 2rem; border-bottom: 1px solid var(--border); margin-bottom: 2rem; }}
        .header h1 {{ font-size: 2rem; background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header .meta {{ color: var(--text-secondary); font-size: 0.9rem; text-align: right; }}
        .hero {{ display: grid; grid-template-columns: 260px 1fr; gap: 1.5rem; margin-bottom: 2rem; }}
        .score-card {{ background: var(--bg-secondary); border-radius: 16px; border: 1px solid var(--border); padding: 2rem; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
        .score-circle {{ width: 130px; height: 130px; border-radius: 50%; border: 8px solid {score_color}; display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 1rem; box-shadow: 0 0 20px {score_color}33; }}
        .score-number {{ font-size: 2.5rem; font-weight: 800; color: {score_color}; }}
        .score-grade {{ font-size: 1rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; }}
        .system-card {{ background: var(--bg-secondary); border-radius: 16px; border: 1px solid var(--border); padding: 1.5rem; }}
        .system-card h2 {{ font-size: 1.25rem; margin-bottom: 1rem; color: var(--accent); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; }}
        .card {{ background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); overflow: hidden; }}
        .card-header {{ background: rgba(255,255,255,0.03); padding: 1rem 1.25rem; border-bottom: 1px solid var(--border); }}
        .card-header h3 {{ font-size: 1rem; letter-spacing: 0.5px; color: var(--accent); }}
        .card-body {{ padding: 1.25rem; }}
        .metric-row {{ display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }}
        .metric-row:last-child {{ border-bottom: none; }}
        .metric-key {{ color: var(--text-secondary); }}
        .metric-val {{ font-weight: 600; }}
        .footer {{ text-align: center; margin-top: 3rem; color: var(--text-secondary); font-size: 0.85rem; padding-top: 1.5rem; border-top: 1px solid var(--border); }}
        @media print {{
            body {{ background: #fff; color: #000; padding: 1rem; }}
            .card, .score-card, .system-card {{ border: 1px solid #ccc; background: #fff; color: #000; box-shadow: none; }}
            .header h1 {{ color: #000; -webkit-text-fill-color: #000; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>SysMaint System Health Report</h1>
                <p style="color: var(--text-secondary); margin-top: 0.25rem;">Automated Diagnostic & Maintenance Telemetry</p>
            </div>
            <div class="meta">
                <div><strong>Host:</strong> {host}</div>
                <div><strong>OS:</strong> {os_name}</div>
                <div><strong>Date:</strong> {timestamp[:19].replace('T', ' ')} UTC</div>
            </div>
        </div>

        <div class="hero">
            <div class="score-card">
                <div class="score-circle">
                    <div class="score-number">{health_score}</div>
                </div>
                <div class="score-grade">{health_grade} Condition</div>
            </div>
            <div class="system-card">
                <h2>System Overview</h2>
                <div class="metric-row"><span class="metric-key">Host Node</span><span class="metric-val">{host}</span></div>
                <div class="metric-row"><span class="metric-key">Operating System</span><span class="metric-val">{os_name}</span></div>
                <div class="metric-row"><span class="metric-key">Report Generated</span><span class="metric-val">{timestamp}</span></div>
                <div class="metric-row"><span class="metric-key">Status</span><span class="metric-val" style="color: {score_color}; font-weight: bold;">Verified</span></div>
            </div>
        </div>

        <div class="grid">
            {sections_str}
        </div>

        <div class="footer">
            <p>Generated by <strong>SysMaint Toolkit</strong> • Cross-Platform System Maintenance Suite</p>
        </div>
    </div>
</body>
</html>
"""
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

    return html