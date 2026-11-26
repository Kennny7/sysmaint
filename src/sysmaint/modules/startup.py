# sysmaint/modules/startup.py

from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger("sysmaint.startup")


def list_startup_items() -> list[dict[str, Any]]:
    """
    List all configured startup applications and autoruns across Windows or Linux.

    Returns:
        List of startup program records with name, command, location, and impact.
    """
    system = platform.system().lower()
    logger.info("Enumerating startup applications on %s", system)
    items: list[dict[str, Any]] = []

    if system == "windows":
        from ..utils import windows
        raw_items = windows.get_windows_startup_items()
        for it in raw_items:
            cmd = it.get("command", "")
            # Heuristic impact estimation
            impact = "Medium"
            cmd_lower = cmd.lower()
            if any(k in cmd_lower for k in ("update", "helper", "tray", "sync", "notify")):
                impact = "Low"
            elif any(k in cmd_lower for k in ("steam", "epic", "discord", "electron", "teams", "slack", "chrome")):
                impact = "High"

            it["impact"] = impact
            items.append(it)
        return items

    if system == "linux":
        from ..utils import linux
        raw_items = linux.get_linux_startup_items()
        for it in raw_items:
            it["impact"] = "Medium"
            it["is_system"] = "/etc" in it.get("location", "")
            items.append(it)
        return items

    return []


def toggle_startup_item(name: str, enable: bool) -> dict[str, Any]:
    """
    Enable or disable a startup item.

    Args:
        name: Name of the startup application.
        enable: Whether to enable or disable the item.

    Returns:
        Dictionary indicating status.
    """
    system = platform.system().lower()
    logger.info("Setting startup item '%s' enabled=%s", name, enable)

    if system == "windows":
        try:
            import winreg
            # Check HKCU Run key
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                if not enable:
                    try:
                        winreg.DeleteValue(key, name)
                        return {"success": True, "message": f"Removed '{name}' from HKCU Run key."}
                    except OSError:
                        pass
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if system == "linux":
        autostart_dir = Path.home() / ".config" / "autostart"
        for f in autostart_dir.glob("*.desktop"):
            if name.lower() in f.stem.lower():
                try:
                    content = f.read_text(encoding="utf-8")
                    if f"Hidden={not enable}" not in content:
                        new_content = content + f"\nHidden={'true' if not enable else 'false'}\n"
                        f.write_text(new_content, encoding="utf-8")
                        return {"success": True, "message": f"Updated {f.name}"}
                except Exception as exc:
                    return {"success": False, "error": str(exc)}

    return {"success": False, "message": "Startup item not found or modification requires elevated privileges."}
