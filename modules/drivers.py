# sysmaint/modules/drivers.py

from __future__ import annotations

import logging
import platform
import shutil
from typing import Any, List

from ..utils.common import run_command
from ..utils.parsers import parse_driverquery_output

logger = logging.getLogger("sysmaint.drivers")


def check_drivers() -> dict[str, Any]:
    """
    List installed drivers / kernel modules and detect hardware device issues.

    Returns:
        Dictionary with driver list, device errors, and overall driver health status.
    """
    system = platform.system().lower()
    logger.info("Enumerating drivers and hardware devices for %s", system)

    drivers: List[dict[str, Any]] = []
    faulty_devices: List[dict[str, Any]] = []

    if system == "windows":
        from ..utils.windows import get_pnp_device_errors

        # Check driver query
        res = run_command(["driverquery", "/v", "/fo", "csv"], check=False)
        if res.returncode == 0:
            drivers = parse_driverquery_output(res.stdout)
        else:
            # Fallback to non-csv
            res_txt = run_command(["driverquery"], check=False)
            drivers = parse_driverquery_output(res_txt.stdout)

        # Detect faulty devices
        try:
            faulty_devices = get_pnp_device_errors()
        except Exception as exc:
            logger.debug("Failed to query PnP devices: %s", exc)

        return {
            "tool": "driverquery / PnP",
            "drivers_count": len(drivers),
            "drivers": drivers[:100],  # cap at 100 for telemetry
            "faulty_devices": faulty_devices,
            "healthy": len(faulty_devices) == 0,
            "status": "Healthy" if not faulty_devices else f"Found {len(faulty_devices)} problematic device(s)",
        }

    if system == "linux":
        res = run_command(["lsmod"], check=False)
        if res.returncode == 0:
            for line in res.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    drivers.append({
                        "name": parts[0],
                        "size": parts[1],
                        "used_by_count": parts[2],
                        "used_by": parts[3] if len(parts) > 3 else "",
                    })

        # Check PCI devices
        if shutil.which("lspci"):
            pci_res = run_command(["lspci"], check=False)
            pci_devices = [line.strip() for line in pci_res.stdout.splitlines() if line.strip()]
        else:
            pci_devices = []

        return {
            "tool": "lsmod",
            "modules_count": len(drivers),
            "drivers": drivers[:100],
            "pci_devices": pci_devices[:50],
            "faulty_devices": [],
            "healthy": True,
            "status": "Healthy",
        }

    return {
        "error": f"Unsupported platform: {system}",
        "healthy": True,
    }