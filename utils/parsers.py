# sysmaint/utils/parsers.py

from __future__ import annotations

import re
from typing import List


def parse_clamscan_output(output: str) -> List[dict]:
    """
    Parse clamscan output and return a list of infected file records.

    Expected line format: `/path/to/file: MalwareName FOUND`
    """
    threats = []
    for line in output.splitlines():
        if "FOUND" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                file_path = parts[0].strip()
                malware = parts[1].split(" FOUND")[0].strip()
                threats.append({"file": file_path, "malware": malware, "engine": "clamav"})
    return threats


def parse_sfc_log(log_text: str) -> List[str]:
    """
    Extract repaired file references from SFC CBS log snippets.
    Looks for lines containing '[SR]'.
    """
    repaired_files = []
    for line in log_text.splitlines():
        if "[SR]" in line:
            repaired_files.append(line.strip())
    return repaired_files


def parse_fsck_output(output: str) -> dict:
    """Extract basic summary from fsck output."""
    clean = "clean" in output.lower()
    errors = re.findall(r"error", output, re.IGNORECASE)
    return {"clean": clean, "error_count": len(errors), "raw": output}