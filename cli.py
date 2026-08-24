# sysmaint/cli.py

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
except ImportError:
    console = None

from .config import SysMaintConfig, load_config
from .logging_setup import setup_logging
from .modules import (
    backup as backup_module,
    cleaner as cleaner_module,
    disk as disk_module,
    drivers as drivers_module,
    integrity as integrity_module,
    malware as malware_module,
    memory as memory_module,
    network as network_module,
    optimizer as optimizer_module,
    report as report_module,
    restore as restore_module,
    scheduler as scheduler_module,
    security as security_module,
    services as services_module,
    startup as startup_module,
    sysinfo as sysinfo_module,
)
from .utils.escalate import is_elevated, request_elevation


def build_parser() -> argparse.ArgumentParser:
    """Create the argparse parser with all SysMaint subcommands."""
    parser = argparse.ArgumentParser(
        prog="sysmaint",
        description="SysMaint - Professional Cross-Platform System Maintenance Toolkit",
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
        help="Verbose debug output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--html",
        type=Path,
        help="Export comprehensive HTML report to FILE",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--elevate",
        action="store_true",
        help="Request administrator / root privileges before executing",
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

    # gui
    p_gui = subparsers.add_parser("gui", help="Launch modern graphical user interface")
    p_gui.set_defaults(func=cmd_gui)

    # smart-scan
    p_smart = subparsers.add_parser("smart-scan", help="Run 1-Click Smart System Health Scan")
    p_smart.set_defaults(func=cmd_smart_scan)

    # optimize
    p_opt = subparsers.add_parser("optimize", help="Run 1-Click Auto-Fix & System Optimization")
    p_opt.set_defaults(func=cmd_optimize)

    # clean
    p_clean = subparsers.add_parser("clean", help="Clean junk, temporary files, and browser caches")
    p_clean.add_argument("--temp", action="store_true", help="Clean temporary files")
    p_clean.add_argument("--browser", action="store_true", help="Clean browser caches")
    p_clean.add_argument("--logs", action="store_true", help="Clean system logs and crash dumps")
    p_clean.add_argument("--package", action="store_true", help="Clean package manager caches")
    p_clean.add_argument("--thumbnails", action="store_true", help="Clean thumbnail caches")
    p_clean.add_argument("--all", action="store_true", help="Clean all junk categories")
    p_clean.set_defaults(func=cmd_clean)

    # info
    p_info = subparsers.add_parser("info", help="Display hardware specs and operating system details")
    p_info.set_defaults(func=cmd_info)

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
    p_scan.add_argument("--target", type=Path, help="Specific file or folder to scan")
    p_scan.add_argument("--all", action="store_true", help="Run all scans")
    p_scan.set_defaults(func=cmd_scan)

    # repair
    p_repair = subparsers.add_parser("repair", help="Attempt repairs based on diagnostics")
    p_repair.add_argument("--disk", action="store_true", help="Repair disk/filesystem")
    p_repair.add_argument("--services", action="store_true", help="Repair services (start expected)")
    p_repair.add_argument("--files", action="store_true", help="Repair system files")
    p_repair.add_argument("--all", action="store_true", help="Run all repairs")
    p_repair.set_defaults(func=cmd_repair)

    # startup
    p_startup = subparsers.add_parser("startup", help="Manage startup applications and autoruns")
    p_startup.add_argument("action", nargs="?", default="list", choices=["list", "enable", "disable"])
    p_startup.add_argument("name", nargs="?", help="Startup application name")
    p_startup.set_defaults(func=cmd_startup)

    # network
    p_net = subparsers.add_parser("network", help="Network diagnostics, ping, and DNS flush")
    p_net.add_argument("action", nargs="?", default="status", choices=["status", "ping", "flush-dns", "ports"])
    p_net.add_argument("--target", default="1.1.1.1", help="Target host to ping")
    p_net.set_defaults(func=cmd_network)

    # security
    p_sec = subparsers.add_parser("security", help="Audit security posture (Antivirus, Firewall, Elevation)")
    p_sec.set_defaults(func=cmd_security)

    # backup
    p_backup = subparsers.add_parser("backup", help="Create backups or restore points")
    p_backup.add_argument("--snapshot", action="store_true", help="Create LVM/Btrfs snapshot")
    p_backup.add_argument("--restore-point", action="store_true", help="Create Windows restore point")
    p_backup.add_argument("--registry", action="store_true", help="Create Windows registry backup")
    p_backup.set_defaults(func=cmd_backup)

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore from a backup snapshot or restore point")
    p_restore.add_argument("--list", action="store_true", help="List available backups and restore points")
    p_restore.add_argument("--ui", action="store_true", help="Launch native system recovery UI")
    p_restore.add_argument("--snapshot", metavar="NAME", help="Restore from snapshot NAME")
    p_restore.add_argument("--restore-point", metavar="NAME", help="Restore from restore point NAME")
    p_restore.set_defaults(func=cmd_restore)

    # service
    p_service = subparsers.add_parser("service", help="Manage system services")
    p_service.add_argument("action", choices=["start", "stop", "restart", "status", "list"])
    p_service.add_argument("service_name", nargs="?", help="Service identifier name")
    p_service.set_defaults(func=cmd_service)

    # schedule
    p_sched = subparsers.add_parser("schedule", help="Manage recurring automated maintenance tasks")
    p_sched.add_argument("action", choices=["status", "install", "remove"])
    p_sched.add_argument("--interval", default="WEEKLY", choices=["DAILY", "WEEKLY", "MONTHLY"])
    p_sched.add_argument("--time", default="02:00", help="Time to execute (HH:MM)")
    p_sched.set_defaults(func=cmd_schedule)

    # update-db
    p_update = subparsers.add_parser("update-db", help="Update ClamAV signature database")
    p_update.set_defaults(func=cmd_update_db)

    # report
    p_report = subparsers.add_parser("report", help="Generate full system health report")
    p_report.set_defaults(func=cmd_report)

    return parser


def _merge_config(args: argparse.Namespace) -> SysMaintConfig:
    """Load config from file if provided, then apply CLI overrides."""
    if getattr(args, "config", None):
        config = load_config(args.config)
    else:
        config = load_config()

    if getattr(args, "offline", False):
        config.system.offline_mode = True
    if getattr(args, "yes", False):
        config.system.auto_yes = True
    if getattr(args, "log", None):
        config.logging.file = args.log

    return config


# ---------------- Command Handlers ----------------


def cmd_gui(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Launch the modern graphical user interface."""
    from .gui.app import SysMaintApp
    app = SysMaintApp(config=config)
    app.mainloop()
    return {"status": "GUI Closed"}


def cmd_smart_scan(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Run 1-Click Smart System Health Scan."""
    return {"smart_scan": optimizer_module.run_smart_scan(config)}


def cmd_optimize(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Run 1-Click Auto-Fix & System Optimization."""
    return {"optimizer": optimizer_module.run_auto_fix(config, create_restore=not args.dry_run)}


def cmd_clean(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint clean`."""
    cats = []
    if args.all or not any([args.temp, args.browser, args.logs, args.package, args.thumbnails]):
        cats = None
    else:
        if args.temp:
            cats.extend(["user_temp", "system_temp"])
        if args.browser:
            cats.append("browser_cache")
        if args.logs:
            cats.append("system_logs")
        if args.package:
            cats.append("package_cache")
        if args.thumbnails:
            cats.append("thumbnails")

    return {"cleaner": cleaner_module.clean_junk(categories=cats, dry_run=args.dry_run)}


def cmd_info(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Display hardware specs and operating system details."""
    return {"sysinfo": sysinfo_module.get_system_specs()}


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
    run_all = args.all or not any([args.clamav, args.yara, args.virustotal, args.integrity])

    if run_all or args.integrity:
        results["integrity"] = integrity_module.check_integrity(repair=False)

    if run_all or args.clamav or args.yara or args.virustotal:
        mal_cfg = config.malware
        if not run_all:
            mal_cfg = malware_module.MalwareConfig(
                use_clamav=args.clamav,
                use_yara=args.yara,
                yara_rules_path=config.malware.yara_rules_path,
                use_virustotal=args.virustotal,
                vt_api_key=config.malware.vt_api_key,
            )
        results["malware"] = malware_module.scan(
            mal_cfg,
            target=args.target,
            offline=config.system.offline_mode,
            quick_scan=args.target is None,
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
            results["integrity"] = {"dry_run": "DISM /RestoreHealth and SFC /scannow"}

    return results


def cmd_startup(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint startup`."""
    if args.action == "list":
        return {"startup_items": startup_module.list_startup_items()}
    elif args.action in ("enable", "disable"):
        if not args.name:
            return {"error": f"Please specify the startup item name to {args.action}"}
        return startup_module.toggle_startup_item(args.name, enable=(args.action == "enable"))
    return {"startup_items": startup_module.list_startup_items()}


def cmd_network(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint network`."""
    if args.action == "status":
        return {"interfaces": network_module.get_network_interfaces()}
    elif args.action == "ping":
        return {"ping": network_module.test_connectivity(args.target)}
    elif args.action == "flush-dns":
        return {"dns_flush": network_module.flush_dns()}
    elif args.action == "ports":
        return {"ports": network_module.get_listening_ports()}
    return {"interfaces": network_module.get_network_interfaces()}


def cmd_security(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint security`."""
    return {"security": security_module.audit_security_posture()}


def cmd_backup(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint backup`."""
    kind = "auto"
    if args.snapshot:
        kind = "snapshot"
    elif args.restore_point:
        kind = "restore-point"
    elif args.registry:
        kind = "registry"

    if args.dry_run:
        return {"dry_run": f"create backup of kind '{kind}'"}
    return backup_module.create_backup(config, kind)


def cmd_restore(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint restore`."""
    if args.list:
        return {"backups": restore_module.list_available_backups(config)}
    if args.ui:
        return restore_module.launch_system_recovery()
    if args.snapshot:
        return restore_module.restore_backup(config, args.snapshot, kind="snapshot")
    if args.restore_point:
        return restore_module.restore_backup(config, args.restore_point, kind="restore-point")
    return {"error": "Use --list to view backups or specify --snapshot / --restore-point"}


def cmd_service(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint service`."""
    if args.action == "list":
        return {"services": services_module.list_services()}
    if not args.service_name:
        return {"error": f"Please specify service_name for action '{args.action}'"}
    if args.action == "status":
        return {
            "name": args.service_name,
            "status": services_module.service_status(args.service_name),
        }
    return services_module.control_service(args.service_name, args.action)


def cmd_schedule(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint schedule`."""
    if args.action == "status":
        return {"schedule": scheduler_module.get_schedule_status()}
    elif args.action == "install":
        return scheduler_module.install_schedule(interval=args.interval, time_str=args.time)
    elif args.action == "remove":
        return scheduler_module.remove_schedule()
    return {"schedule": scheduler_module.get_schedule_status()}


def cmd_update_db(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint update-db`."""
    if args.dry_run:
        return {"dry_run": "update malware database"}
    return malware_module.update_malware_database()


def cmd_report(args: argparse.Namespace, config: SysMaintConfig) -> dict[str, Any]:
    """Handler for `sysmaint report`."""
    # Run full diagnostics, cleaner preview, and security audit
    results: dict[str, Any] = {
        "sysinfo": sysinfo_module.get_system_specs(),
        "smart_scan": optimizer_module.run_smart_scan(config),
        "security": security_module.audit_security_posture(),
        "disk": disk_module.check_disk(repair=False),
        "memory": memory_module.check_memory(),
    }
    return results


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point for SysMaint CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # If no subcommand provided, default to GUI if interactive or show help
    if not getattr(args, "command", None):
        if len(sys.argv) == 1:
            try:
                cmd_gui(args, load_config())
                return
            except Exception:
                parser.print_help()
                return
        parser.print_help()
        return

    # Elevate if explicitly requested
    if getattr(args, "elevate", False) and not is_elevated():
        request_elevation()

    config = _merge_config(args)

    logger = setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        verbose=args.verbose,
    )

    logger.info("SysMaint starting (command=%s)", args.command)

    # Execute selected command
    results = args.func(args, config)

    # HTML Export if requested
    if getattr(args, "html", None):
        rep = report_module.build_report(results)
        report_module.generate_html_report(rep, output_path=args.html)
        if not args.json:
            print(f"Exported HTML report to: {args.html}")

    # Standard Output
    report = report_module.build_report(results)
    if args.json:
        output = report_module.format_report(report, json_output=True)
        print(output)
    else:
        output = report_module.format_report(report, json_output=False)
        print(output)

    # Determine exit code
    exit_code = 1 if _contains_error(results) else 0
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