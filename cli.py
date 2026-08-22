# sysmaint/cli.py

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

from .config import SysMaintConfig, load_config
from .logging_setup import setup_logging
from .modules import (
    backup as backup_module,
    disk as disk_module,
    drivers as drivers_module,
    integrity as integrity_module,
    malware as malware_module,
    memory as memory_module,
    report as report_module,
    restore as restore_module,
    services as services_module,
)
from .utils.escalate import ensure_elevated


def build_parser() -> argparse.ArgumentParser:
    """Create the argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="sysmaint",
        description="Cross-Platform System Maintenance Toolkit",
    )

    # Global options
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file (YAML or JSON)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        help="Log output to FILE",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Answer all prompts with 'yes'",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Disable online checks/scans",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # diagnose
    p_diag = subparsers.add_parser("diagnose", help="Run diagnostics (disk, memory, services, drivers)")
    p_diag.add_argument("--disk", action="store_true", help="Check disk")
    p_diag.add_argument("--memory", action="store_true", help="Check memory")
    p_diag.add_argument("--services", action="store_true", help="Check services")
    p_diag.add_argument("--drivers", action="store_true", help="Check drivers")
    p_diag.add_argument("--all", action="store_true", help="Run all diagnostics")
    p_diag.set_defaults(func=cmd_diagnose)

    # scan
    p_scan = subparsers.add_parser("scan", help="Perform malware and integrity scans")
    p_scan.add_argument("--clamav", action="store_true", help="Run ClamAV scan")
    p_scan.add_argument("--yara", action="store_true", help="Run YARA scan")
    p_scan.add_argument("--virustotal", action="store_true", help="Run VirusTotal scan")
    p_scan.add_argument("--integrity", action="store_true", help="Run system integrity check")
    p_scan.add_argument("--all", action="store_true", help="Run all scans")
    p_scan.set_defaults(func=cmd_scan)

    # repair
    p_repair = subparsers.add_parser("repair", help="Attempt repairs based on diagnostics")
    p_repair.add_argument("--disk", action="store_true", help="Repair disk/filesystem")
    p_repair.add_argument("--services", action="store_true", help="Repair services (start expected)")
    p_repair.add_argument("--files", action="store_true", help="Repair system files")
    p_repair.add_argument("--all", action="store_true", help="Run all repairs")
    p_repair.set_defaults(func=cmd_repair)

    # backup
    p_backup = subparsers.add_parser("backup", help="Create backups or snapshots")
    p_backup.add_argument("--snapshot", action="store_true", help="Create LVM/Btrfs snapshot")
    p_backup.add_argument("--restore-point", action="store_true", help="Create Windows restore point")
    p_backup.set_defaults(func=cmd_backup)

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore from a backup snapshot or restore point")
    p_restore.add_argument("--snapshot", metavar="NAME", help="Restore from snapshot NAME")
    p_restore.add_argument("--restore-point", metavar="NAME", help="Restore from restore point NAME")
    p_restore.set_defaults(func=cmd_restore)

    # service
    p_service = subparsers.add_parser("service", help="Start/stop/restart system services")
    p_service.add_argument("action", choices=["start", "stop", "restart", "status"])
    p_service.add_argument("service_name")
    p_service.set_defaults(func=cmd_service)

    # update-db
    p_update = subparsers.add_parser("update-db", help="Update ClamAV/YARA signature databases")
    p_update.set_defaults(func=cmd_update_db)

    return parser


def _merge_config(args: argparse.Namespace) -> SysMaintConfig:
    """Load config from file if provided, then apply CLI overrides."""
    if args.config:
        config = load_config(args.config)
    else:
        config = SysMaintConfig.from_dict({})

    if args.offline:
        config.system.offline_mode = True
    if args.yes:
        config.system.auto_yes = True
    if args.log:
        config.logging.file = args.log

    return config


def cmd_diagnose(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint diagnose`."""
    results: dict[str, Any] = {}
    run_all = args.all or not any([args.disk, args.memory, args.services, args.drivers])

    if run_all or args.disk:
        results["disk"] = disk_module.check_disk(repair=False)
    if run_all or args.memory:
        results["memory"] = memory_module.check_memory()
    if run_all or args.services:
        results["services"] = services_module.list_services()
    if run_all or args.drivers:
        results["drivers"] = drivers_module.check_drivers()

    return results


def cmd_scan(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint scan`."""
    results: dict[str, Any] = {}
    run_all = args.all or not any(
        [args.clamav, args.yara, args.virustotal, args.integrity]
    )

    if run_all or args.integrity:
        results["integrity"] = integrity_module.check_integrity(repair=False)

    if run_all or args.clamav or args.yara or args.virustotal:
        mal_cfg = config.malware
        if not run_all:
            # If specific flags were provided, restrict to selected engines
            mal_cfg = malware_module.MalwareConfig(
                use_clamav=args.clamav,
                use_yara=args.yara,
                yara_rules_path=config.malware.yara_rules_path,
                use_virustotal=args.virustotal,
                vt_api_key=config.malware.vt_api_key,
            )
        results["malware"] = malware_module.scan(
            mal_cfg, offline=config.system.offline_mode
        )

    return results


def cmd_repair(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint repair`."""
    results: dict[str, Any] = {}
    run_all = args.all or not any([args.disk, args.services, args.files])

    if args.dry_run:
        results["dry_run"] = True

    if run_all or args.disk:
        if not args.dry_run:
            results["disk"] = disk_module.check_disk(repair=True)
        else:
            results["disk"] = {"dry_run": "chkdsk /f or fsck -y"}

    if run_all or args.services:
        if not args.dry_run and config.services.enable:
            results["services"] = services_module.ensure_expected_services(
                config.services.expected_services
            )
        else:
            results["services"] = {"dry_run": "ensure expected services"}

    if run_all or args.files:
        if not args.dry_run:
            results["integrity"] = integrity_module.check_integrity(repair=True)
        else:
            results["integrity"] = {"dry_run": "DISM/SFC or dpkg --verify"}

    return results


def cmd_backup(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint backup`."""
    kind = "auto"
    if args.snapshot:
        kind = "snapshot"
    elif args.restore_point:
        kind = "restore-point"

    if args.dry_run:
        return {"dry_run": f"create backup of kind '{kind}'"}
    return backup_module.create_backup(config, kind)


def cmd_restore(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint restore`."""
    if args.dry_run:
        return {"dry_run": "restore requested"}

    if args.snapshot:
        return restore_module.restore_backup(config, args.snapshot, kind="snapshot")
    if args.restore_point:
        return restore_module.restore_backup(config, args.restore_point, kind="restore-point")
    return {"error": "No backup reference provided. Use --snapshot NAME or --restore-point NAME."}


def cmd_service(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint service`."""
    if args.dry_run:
        return {"dry_run": f"service {args.action} {args.service_name}"}

    if args.action == "status":
        return {
            "name": args.service_name,
            "status": services_module.service_status(args.service_name),
        }
    return services_module.control_service(args.service_name, args.action)


def cmd_update_db(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint update-db`."""
    if args.dry_run:
        return {"dry_run": "update malware database"}
    return malware_module.update_malware_database()


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Elevate privileges before anything else that requires it.
    # Help and argparse errors are already handled before this point.
    ensure_elevated()

    config = _merge_config(args)

    logger = setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        verbose=args.verbose,
    )

    logger.info("SysMaint starting (command=%s)", args.command)

    # Execute selected command
    results = args.func(args, config)

    report = report_module.build_report(results)
    output = report_module.format_report(report, json_output=args.json)
    print(output)

    # Determine exit code: 1 if any result contains an error
    exit_code = 0
    if _contains_error(results):
        exit_code = 1
    sys.exit(exit_code)


def _contains_error(data: Any) -> bool:
    """Recursively check if a result dict contains an 'error' key."""
    if isinstance(data, dict):
        if "error" in data:
            return True
        return any(_contains_error(value) for value in data.values())
    if isinstance(data, list):
        return any(_contains_error(item) for item in data)
    return False


if __name__ == "__main__":
    main()