# src/sysmaint/modules/recovery.py

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..utils.common import format_bytes, run_command

logger = logging.getLogger("sysmaint.recovery")

# Magic byte signatures for safe read-only file carving
FILE_SIGNATURES: dict[str, dict[str, Any]] = {
    "pdf": {
        "header": b"%PDF-",
        "footer": b"%%EOF",
        "ext": ".pdf",
        "max_size": 25 * 1024 * 1024,
    },
    "png": {
        "header": b"\x89PNG\r\n\x1a\n",
        "footer": b"IEND\xaeB`\x82",
        "ext": ".png",
        "max_size": 15 * 1024 * 1024,
    },
    "jpg": {
        "header": b"\xff\xd8\xff",
        "footer": b"\xff\xd9",
        "ext": ".jpg",
        "max_size": 15 * 1024 * 1024,
    },
    "zip": {
        "header": b"PK\x03\x04",
        "footer": None,
        "ext": ".zip",
        "max_size": 25 * 1024 * 1024,
    },
    "sqlite": {
        "header": b"SQLite format 3\x00",
        "footer": None,
        "ext": ".sqlite",
        "max_size": 25 * 1024 * 1024,
    },
}


def list_trash_items(limit: int = 50) -> dict[str, Any]:
    """List recently deleted items in the OS Recycle Bin (Windows) or Trash (Linux)."""
    system = platform.system().lower()
    items: list[dict[str, Any]] = []

    if system == "windows":
        from ..utils.windows import run_powershell

        script = (
            "$shell = New-Object -ComObject Shell.Application; "
            "$bin = $shell.NameSpace(10); "
            f"$bin.Items() | Select-Object -First {int(limit)} | ForEach-Object {{ "
            "[PSCustomObject]@{ "
            "Name = $_.Name; "
            "OriginalPath = $bin.GetDetailsOf($_, 1); "
            "DeletedDate = $bin.GetDetailsOf($_, 2); "
            "Size = $_.Size; "
            "Path = $_.Path "
            "} } | ConvertTo-Json"
        )
        data = run_powershell(script, as_json=True)
        if isinstance(data, dict):
            data = [data]
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    size = int(entry.get("Size") or 0)
                    items.append(
                        {
                            "name": entry.get("Name", ""),
                            "original_path": entry.get("OriginalPath", ""),
                            "deleted_date": entry.get("DeletedDate", ""),
                            "size": size,
                            "size_formatted": format_bytes(size),
                            "trash_path": entry.get("Path", ""),
                        }
                    )
        return {"platform": "windows", "count": len(items), "items": items}

    # Linux FreeDesktop Trash (~/.local/share/Trash)
    trash_root = Path.home() / ".local" / "share" / "Trash"
    info_dir = trash_root / "info"
    files_dir = trash_root / "files"

    if info_dir.is_dir():
        for info_file in sorted(info_dir.glob("*.trashinfo"))[:limit]:
            try:
                content = info_file.read_text(encoding="utf-8", errors="replace")
                orig_match = re.search(r"^Path=(.+)$", content, re.MULTILINE)
                date_match = re.search(r"^DeletionDate=(.+)$", content, re.MULTILINE)
                item_name = info_file.stem
                file_path = files_dir / item_name
                size = file_path.stat().st_size if file_path.is_file() else 0
                items.append(
                    {
                        "name": item_name,
                        "original_path": orig_match.group(1).strip() if orig_match else "",
                        "deleted_date": date_match.group(1).strip() if date_match else "",
                        "size": size,
                        "size_formatted": format_bytes(size),
                        "trash_path": str(file_path),
                    }
                )
            except OSError as exc:
                logger.debug("Skipping trash info %s: %s", info_file, exc)

    return {"platform": system, "count": len(items), "items": items}


def restore_trash_item(
    name: str,
    destination: Optional[Path] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Restore a deleted file or folder from Recycle Bin / Trash to its original or custom path."""
    if not name:
        return {"error": "Item name is required for trash recovery."}

    trash_listing = list_trash_items(limit=200)
    matches = [
        item
        for item in trash_listing.get("items", [])
        if item.get("name", "").lower() == name.lower()
        or Path(item.get("original_path", "")).name.lower() == name.lower()
    ]

    if not matches:
        return {"error": f"No item matching '{name}' found in Recycle Bin / Trash."}

    target = matches[0]
    src = Path(target["trash_path"])
    if not src.exists():
        return {"error": f"Trash backing file does not exist: {src}"}

    if destination:
        dest_path = Path(destination) / target["name"] if Path(destination).is_dir() else Path(destination)
    else:
        orig_dir = target.get("original_path") or str(Path.home() / "Recovered")
        dest_path = Path(orig_dir) / target["name"]

    if dry_run:
        return {
            "dry_run": True,
            "action": "restore_trash_item",
            "source": str(src),
            "destination": str(dest_path),
        }

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest_path, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dest_path)

    return {
        "status": "restored",
        "name": target["name"],
        "restored_to": str(dest_path),
    }


def list_shadow_copies() -> dict[str, Any]:
    """List Volume Shadow Copies (Windows) or filesystem snapshots (Linux)."""
    system = platform.system().lower()
    if system == "windows":
        res = run_command(["vssadmin", "list", "shadows"], check=False)
        shadows: list[dict[str, str]] = []
        current: dict[str, str] = {}
        for line in res.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("Contents of shadow copy set ID:"):
                if current:
                    shadows.append(current)
                    current = {}
                current["set_id"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Shadow Copy ID:"):
                current["shadow_id"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Original Volume:"):
                current["volume"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Shadow Copy Volume:"):
                current["shadow_volume"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Creation Time:") or stripped.startswith("creation time:"):
                current["created_at"] = stripped.split(":", 1)[1].strip()
        if current:
            shadows.append(current)

        return {
            "platform": "windows",
            "count": len(shadows),
            "shadows": shadows,
            "raw_returncode": res.returncode,
            "note": (
                "Administrator privileges are required to query VSS."
                if res.returncode != 0 and not shadows
                else "Use mklink /d C:\\ShadowMount <shadow_volume>\\ to browse a shadow copy."
            ),
        }

    # Linux: check timeshift or btrfs
    if shutil.which("timeshift"):
        res = run_command(["timeshift", "--list"], check=False)
        return {"platform": "linux", "tool": "timeshift", "output": res.stdout[:3000]}
    if shutil.which("btrfs"):
        res = run_command(["btrfs", "subvolume", "list", "/"], check=False)
        return {"platform": "linux", "tool": "btrfs", "output": res.stdout[:3000]}

    return {"platform": system, "count": 0, "shadows": [], "note": "No snapshot tool detected."}


def scan_recoverable_temp_files(limit: int = 50) -> dict[str, Any]:
    """Scan common application auto-recovery and temp backup locations for unsaved drafts."""
    candidates: list[Path] = []
    home = Path.home()

    if platform.system().lower() == "windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        candidates.extend(
            [
                appdata / "Microsoft" / "Word",
                appdata / "Microsoft" / "Excel",
                appdata / "Microsoft" / "PowerPoint",
                local / "Microsoft" / "Office" / "UnsavedFiles",
                local / "Temp",
            ]
        )
    else:
        candidates.extend(
            [
                home / ".config" / "libreoffice" / "4" / "user" / "backup",
                Path("/tmp"),
            ]
        )

    recovery_exts = {".asd", ".wbk", ".tmp", ".bak", ".autosave", ".swp"}
    found: list[dict[str, Any]] = []

    for folder in candidates:
        if not folder.is_dir():
            continue
        try:
            for entry in folder.iterdir():
                if len(found) >= limit:
                    break
                if entry.is_file() and (
                    entry.suffix.lower() in recovery_exts or entry.name.startswith("~$")
                ):
                    stat = entry.stat()
                    found.append(
                        {
                            "name": entry.name,
                            "path": str(entry),
                            "size": stat.st_size,
                            "size_formatted": format_bytes(stat.st_size),
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(
                                timespec="seconds"
                            ),
                        }
                    )
        except OSError:
            continue

    return {"count": len(found), "files": found}


def carve_recoverable_files(
    source_path: Path,
    output_dir: Path,
    file_types: Optional[list[str]] = None,
    max_files: int = 50,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Safely scan a binary disk image or raw file for known file signatures and carve them
    into a separate output directory (read-only on source).
    """
    src = Path(source_path)
    out = Path(output_dir)

    if not src.exists() or not src.is_file():
        return {"error": f"Source must be an existing file or raw disk image: {src}"}

    if out.resolve() == src.parent.resolve() and src.suffix.lower() in {".img", ".dd", ".raw"}:
        return {
            "error": "Safety block: output_dir must be in a separate directory from the disk image."
        }

    selected_types = [t.lower() for t in (file_types or list(FILE_SIGNATURES.keys()))]
    active_sigs = {k: v for k, v in FILE_SIGNATURES.items() if k in selected_types}
    if not active_sigs:
        return {"error": f"No valid file types selected. Choose from: {list(FILE_SIGNATURES)}"}

    data = src.read_bytes()
    carved: list[dict[str, Any]] = []

    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)

    for sig_name, spec in active_sigs.items():
        header: bytes = spec["header"]
        footer: Optional[bytes] = spec["footer"]
        ext: str = spec["ext"]
        max_size: int = spec["max_size"]

        pos = 0
        while len(carved) < max_files:
            start = data.find(header, pos)
            if start == -1:
                break

            if footer:
                end_idx = data.find(footer, start + len(header), start + max_size)
                end = (end_idx + len(footer)) if end_idx != -1 else min(len(data), start + max_size)
            else:
                end = min(len(data), start + min(max_size, 1024 * 1024))

            chunk = data[start:end]
            out_name = f"carved_{sig_name}_{len(carved) + 1:04d}{ext}"
            out_file = out / out_name

            if not dry_run:
                out_file.write_bytes(chunk)

            carved.append(
                {
                    "type": sig_name,
                    "offset": start,
                    "size": len(chunk),
                    "size_formatted": format_bytes(len(chunk)),
                    "output_file": str(out_file),
                }
            )
            pos = end if end > start else start + len(header)

    return {
        "source": str(src),
        "output_dir": str(out),
        "dry_run": dry_run,
        "carved_count": len(carved),
        "files": carved,
    }
