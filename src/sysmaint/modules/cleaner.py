# sysmaint/modules/cleaner.py

from __future__ import annotations

import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.common import format_bytes, safe_delete_dir_contents, safe_delete_file

logger = logging.getLogger("sysmaint.cleaner")


def get_junk_targets() -> Dict[str, List[Path]]:
    """
    Locate junk file target paths grouped by category based on current OS.
    """
    system = platform.system().lower()
    targets: Dict[str, List[Path]] = {
        "user_temp": [],
        "system_temp": [],
        "browser_cache": [],
        "system_logs": [],
        "package_cache": [],
        "thumbnails": [],
    }

    user_home = Path.home()

    if system == "windows":
        # 1. User Temp
        user_temp = os.environ.get("TEMP") or os.environ.get("TMP")
        if user_temp and Path(user_temp).is_dir():
            targets["user_temp"].append(Path(user_temp))

        # 2. System Temp & Prefetch
        sys_temp = Path(r"C:\Windows\Temp")
        if sys_temp.is_dir():
            targets["system_temp"].append(sys_temp)
        prefetch = Path(r"C:\Windows\Prefetch")
        if prefetch.is_dir():
            targets["system_temp"].append(prefetch)

        # 3. Browser Caches (Chrome, Edge, Brave, Firefox)
        local_app_data = os.environ.get("LOCALAPPDATA")
        app_data = os.environ.get("APPDATA")

        if local_app_data:
            lad = Path(local_app_data)
            # Chrome Cache
            chrome_cache = lad / r"Google\Chrome\User Data\Default\Cache"
            if chrome_cache.is_dir():
                targets["browser_cache"].append(chrome_cache)
            # Edge Cache
            edge_cache = lad / r"Microsoft\Edge\User Data\Default\Cache"
            if edge_cache.is_dir():
                targets["browser_cache"].append(edge_cache)
            # Brave Cache
            brave_cache = lad / r"BraveSoftware\Brave-Browser\User Data\Default\Cache"
            if brave_cache.is_dir():
                targets["browser_cache"].append(brave_cache)
            # Crash Dumps
            crash_dumps = lad / "CrashDumps"
            if crash_dumps.is_dir():
                targets["system_logs"].append(crash_dumps)
            # Windows Explorer Thumbnails
            thumb_cache = lad / r"Microsoft\Windows\Explorer"
            if thumb_cache.is_dir():
                targets["thumbnails"].append(thumb_cache)

        if app_data:
            mozilla = Path(app_data) / r"Mozilla\Firefox\Profiles"
            if mozilla.is_dir():
                for p in mozilla.iterdir():
                    if (p / "cache2").is_dir():
                        targets["browser_cache"].append(p / "cache2")

        # 4. Windows Update Download Cache
        soft_dist = Path(r"C:\Windows\SoftwareDistribution\Download")
        if soft_dist.is_dir():
            targets["package_cache"].append(soft_dist)

    elif system == "linux":
        # 1. User Temp
        targets["user_temp"].append(Path("/tmp"))
        targets["user_temp"].append(Path("/var/tmp"))

        # 2. User Cache
        user_cache = user_home / ".cache"
        if user_cache.is_dir():
            targets["user_temp"].append(user_cache)
            # Browser caches inside .cache
            for b in ("google-chrome", "chromium", "mozilla/firefox", "BraveSoftware"):
                b_path = user_cache / b
                if b_path.is_dir():
                    targets["browser_cache"].append(b_path)
            # Thumbnails
            thumbs = user_cache / "thumbnails"
            if thumbs.is_dir():
                targets["thumbnails"].append(thumbs)

        # 3. System Logs
        var_log = Path("/var/log")
        if var_log.is_dir():
            targets["system_logs"].append(var_log)

    return targets


def calculate_dir_size(dir_path: Path) -> tuple[int, int]:
    """
    Calculate total bytes and file count inside a directory safely without following symlinks outside.
    """
    if not dir_path.is_dir():
        return 0, 0

    total_size = 0
    file_count = 0
    try:
        for entry in dir_path.rglob("*"):
            try:
                if entry.is_file():
                    total_size += entry.stat().st_size
                    file_count += 1
            except (PermissionError, OSError):
                continue
    except (PermissionError, OSError):
        pass

    return total_size, file_count


def scan_junk(categories: Optional[List[str]] = None) -> dict[str, Any]:
    """
    Scan system for junk, temporary files, and caches without deleting anything.

    Args:
        categories: Optional subset of categories to scan.

    Returns:
        Itemized summary of reclaimable storage space.
    """
    logger.info("Scanning for junk and temporary files")
    all_targets = get_junk_targets()
    selected_cats = categories or list(all_targets.keys())

    breakdown: Dict[str, dict[str, Any]] = {}
    total_bytes = 0
    total_files = 0

    for cat, paths in all_targets.items():
        if cat not in selected_cats:
            continue

        cat_bytes = 0
        cat_files = 0
        found_paths = []

        for p in paths:
            if p.exists():
                b_size, f_count = calculate_dir_size(p)
                cat_bytes += b_size
                cat_files += f_count
                found_paths.append(str(p))

        breakdown[cat] = {
            "bytes": cat_bytes,
            "bytes_formatted": format_bytes(cat_bytes),
            "files_count": cat_files,
            "paths": found_paths,
        }
        total_bytes += cat_bytes
        total_files += cat_files

    return {
        "total_bytes": total_bytes,
        "total_bytes_formatted": format_bytes(total_bytes),
        "total_files": total_files,
        "categories": breakdown,
    }


def clean_junk(
    categories: Optional[List[str]] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Safely clean junk files and caches from selected categories.

    Args:
        categories: Categories to clean. Defaults to all safe categories.
        dry_run: If True, only simulates the cleanup.

    Returns:
        Dictionary with cleaned bytes, deleted file count, and category results.
    """
    logger.info("Starting junk cleaning (dry_run=%s)", dry_run)
    if dry_run:
        scan_res = scan_junk(categories)
        return {
            "dry_run": True,
            "freed_bytes": scan_res["total_bytes"],
            "freed_bytes_formatted": scan_res["total_bytes_formatted"],
            "deleted_files": scan_res["total_files"],
            "categories": scan_res["categories"],
            "message": f"Dry-run: Would free {scan_res['total_bytes_formatted']} across {scan_res['total_files']} files.",
        }

    all_targets = get_junk_targets()
    selected_cats = categories or list(all_targets.keys())

    total_freed = 0
    total_deleted = 0
    results: Dict[str, dict[str, Any]] = {}

    for cat in selected_cats:
        paths = all_targets.get(cat, [])
        cat_freed = 0
        cat_deleted = 0

        for p in paths:
            if p.is_dir():
                f_count, b_freed = safe_delete_dir_contents(p)
                cat_deleted += f_count
                cat_freed += b_freed

        results[cat] = {
            "freed_bytes": cat_freed,
            "freed_bytes_formatted": format_bytes(cat_freed),
            "deleted_files": cat_deleted,
        }
        total_freed += cat_freed
        total_deleted += cat_deleted

    # Run Linux package clean if applicable
    if platform.system().lower() == "linux" and "package_cache" in selected_cats:
        from ..utils.linux import clean_package_cache
        clean_package_cache(dry_run=False)

    return {
        "dry_run": False,
        "freed_bytes": total_freed,
        "freed_bytes_formatted": format_bytes(total_freed),
        "deleted_files": total_deleted,
        "categories": results,
        "message": f"Cleaned {format_bytes(total_freed)} of junk files ({total_deleted} files removed).",
    }
