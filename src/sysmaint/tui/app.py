# src/sysmaint/tui/app.py

from __future__ import annotations

import json
import platform
from typing import Any, Callable, Optional

import httpx
import psutil
from rich.json import JSON as RichJSON
from rich.panel import Panel
from rich.table import Table
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.theme import Theme
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    ProgressBar,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

from .. import __brand__, __codename__, __version__
from ..config import SysMaintConfig, load_config
from ..modules import (
    disk,
    integrity,
    malware,
    memory,
    network,
    optimizer,
    recovery,
    security,
)

CATPPUCCIN_MOCHA = Theme(
    name="catppuccin-mocha",
    primary="#89b4fa",
    secondary="#74c7ec",
    accent="#94e2d5",
    foreground="#cdd6f4",
    background="#1e1e2e",
    surface="#181825",
    panel="#313244",
    success="#a6e3a1",
    warning="#f9e2af",
    error="#f38ba8",
    dark=True,
)


class SysMaintTUI(App):
    """User-friendly, btop-inspired Terminal Client UI for SysMaint."""

    TITLE = f"SysMaint v{__version__} ({__codename__})"
    SUB_TITLE = __brand__

    CSS = """
    Screen {
        background: $background;
        color: $text;
    }

    #main-split {
        height: 1fr;
    }

    #workspace-pane {
        width: 1fr;
        height: 1fr;
        padding: 0 1;
    }

    #side-log-pane {
        width: 44;
        height: 1fr;
        border-left: solid $primary;
        background: $surface;
        padding: 1;
        display: none;
    }

    #side-log-pane.visible {
        display: block;
    }

    .side-log-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }

    #tech-log {
        height: 1fr;
        background: $background;
        border: round $panel;
        padding: 1;
    }

    #activity-bar {
        height: auto;
        background: $surface;
        border-top: solid $panel;
        padding: 0 2;
        align: left middle;
    }

    #activity-spinner {
        width: 4;
        height: 1;
        display: none;
    }

    #activity-spinner.active {
        display: block;
    }

    #activity-status {
        width: 1fr;
        padding: 0 1;
        color: $text;
    }

    #activity-progress {
        width: 24;
        display: none;
    }

    #activity-progress.active {
        display: block;
    }

    .telemetry-grid {
        layout: grid;
        grid-size: 3;
        grid-gutter: 1;
        height: auto;
        margin: 1 0;
    }

    .metric-card {
        background: $panel;
        border: round $primary;
        padding: 1 2;
        height: auto;
    }

    .card {
        background: $panel;
        border: round $secondary;
        padding: 1 2;
        margin: 1 0;
        height: auto;
    }

    .card-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }

    .action-item {
        height: auto;
        margin-bottom: 1;
    }

    .action-desc {
        color: $text-muted;
        padding-left: 1;
        margin-top: 0;
    }

    .result-box {
        background: $surface;
        border: round $accent;
        padding: 1 2;
        margin: 1 0;
        height: auto;
        min-height: 6;
    }

    Button {
        margin-right: 1;
    }

    Input {
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_metrics", "Refresh"),
        Binding("l", "toggle_log", "Toggle Log"),
        Binding("t", "toggle_theme", "Switch Theme"),
    ]

    def __init__(
        self,
        config: Optional[SysMaintConfig] = None,
        server_url: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.cfg = config or load_config()
        self.server_url = server_url.rstrip("/") if server_url else None
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-split"):
            with Vertical(id="workspace-pane"):
                with TabbedContent(initial="tab-overview"):
                    with TabPane("Overview", id="tab-overview"):
                        with VerticalScroll():
                            with Horizontal(classes="telemetry-grid"):
                                with Vertical(classes="metric-card"):
                                    yield Label("Processor (CPU)", classes="card-title")
                                    yield ProgressBar(total=100, show_eta=False, id="bar-cpu")
                                    yield Static("0.0%", id="val-cpu")
                                with Vertical(classes="metric-card"):
                                    yield Label("Memory (RAM)", classes="card-title")
                                    yield ProgressBar(total=100, show_eta=False, id="bar-ram")
                                    yield Static("0.0%", id="val-ram")
                                with Vertical(classes="metric-card"):
                                    yield Label("Main Storage", classes="card-title")
                                    yield ProgressBar(total=100, show_eta=False, id="bar-disk")
                                    yield Static("0.0%", id="val-disk")

                            with Vertical(classes="card"):
                                yield Label(
                                    f"Device Summary  |  Engine: {self.server_url or 'Local Standalone'}",
                                    classes="card-title",
                                )
                                yield Static("", id="sysinfo-summary")

                            with Vertical(classes="card"):
                                yield Label("Quick Actions", classes="card-title")
                                with Horizontal(classes="action-item"):
                                    yield Button("Quick Scan", id="btn-quick-scan", variant="success")
                                    yield Button("Refresh Stats", id="btn-refresh", variant="primary")
                                    yield Button("Show / Hide Details Log", id="btn-toggle-log", variant="default")
                                yield Label(
                                    "Note: Quick Scan safely checks storage, memory, and system health without changing files.",
                                    classes="action-desc",
                                )

                            yield Static("Press Quick Scan to see a plain-English health summary.", id="res-overview", classes="result-box")

                    with TabPane("System Repair", id="tab-repair"):
                        with VerticalScroll():
                            with Vertical(classes="card"):
                                yield Label("Health Checks & Repair Tools", classes="card-title")
                                with Horizontal(classes="action-item"):
                                    yield Button("Check System Files", id="btn-integrity", variant="primary")
                                    yield Button("Preview System Fixes", id="btn-repair-dry", variant="warning")
                                    yield Button("Test & Fix Network", id="btn-net-check", variant="default")
                                yield Label(
                                    "Note: 'Check System Files' uses Windows DISM/SFC or Linux package verification (read-only). "
                                    "'Preview System Fixes' shows planned repairs safely before making any changes.",
                                    classes="action-desc",
                                )
                            yield Static("Select a check or preview above to inspect your system.", id="res-repair", classes="result-box")

                    with TabPane("Security & Malware", id="tab-security"):
                        with VerticalScroll():
                            with Vertical(classes="card"):
                                yield Label("Protection Audit & Threat Scanner", classes="card-title")
                                with Horizontal(classes="action-item"):
                                    yield Button("Check System Protection", id="btn-sec-audit", variant="primary")
                                    yield Button("Scan for Viruses & Malware", id="btn-malware-scan", variant="success")
                                yield Label(
                                    "Note: Scans Downloads, Temp, and Startup folders offline using built-in YARA rules and ClamAV (if installed).",
                                    classes="action-desc",
                                )
                            yield Static("Run a protection check or malware scan to see results here.", id="res-security", classes="result-box")

                    with TabPane("Data Recovery", id="tab-recovery"):
                        with VerticalScroll():
                            with Vertical(classes="card"):
                                yield Label("Recover Deleted & Unsaved Files", classes="card-title")
                                with Horizontal(classes="action-item"):
                                    yield Button("View Deleted Files", id="btn-trash-list", variant="primary")
                                    yield Button("Find Unsaved Documents", id="btn-temp-rec", variant="success")
                                    yield Button("View Restore Snapshots", id="btn-shadows", variant="default")
                                yield Label(
                                    "Note: Inspects your Recycle Bin / Trash, Office & LibreOffice auto-recovery drafts, and OS restore snapshots.",
                                    classes="action-desc",
                                )
                            yield Static("Choose a recovery option above to search for lost files.", id="res-recovery", classes="result-box")

                    with TabPane("Background Service", id="tab-service"):
                        with VerticalScroll():
                            with Vertical(classes="card"):
                                yield Label("Microservice Connection", classes="card-title")
                                yield Input(
                                    value=self.server_url or "http://127.0.0.1:8765",
                                    placeholder="http://127.0.0.1:8765",
                                    id="input-server-url",
                                )
                                with Horizontal(classes="action-item"):
                                    yield Button("Check Service Health", id="btn-svc-health", variant="primary")
                                    yield Button("Fetch System Profile", id="btn-svc-sysinfo", variant="default")
                                yield Label(
                                    "Note: Start the background service anytime by running 'sysmaint serve' in a terminal.",
                                    classes="action-desc",
                                )
                            yield Static("Check whether the local SysMaint microservice is running.", id="res-service", classes="result-box")

            with Vertical(id="side-log-pane"):
                yield Label("Technical Activity Log (L)", classes="side-log-title")
                yield RichLog(id="tech-log", wrap=True, highlight=True)

        with Horizontal(id="activity-bar"):
            yield LoadingIndicator(id="activity-spinner")
            yield Static("Ready.", id="activity-status")
            yield ProgressBar(total=None, show_eta=False, show_percentage=False, id="activity-progress")

        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(CATPPUCCIN_MOCHA)
        self.theme = "tokyo-night"
        self.action_refresh_metrics()
        self.set_interval(5.0, self.action_refresh_metrics)

    def action_toggle_log(self) -> None:
        pane = self.query_one("#side-log-pane", Vertical)
        pane.toggle_class("visible")

    def action_toggle_theme(self) -> None:
        self.theme = "catppuccin-mocha" if self.theme == "tokyo-night" else "tokyo-night"

    def _set_busy(self, busy: bool, message: str) -> None:
        self._busy = busy
        spinner = self.query_one("#activity-spinner", LoadingIndicator)
        progress = self.query_one("#activity-progress", ProgressBar)
        status = self.query_one("#activity-status", Static)
        if busy:
            spinner.add_class("active")
            progress.add_class("active")
        else:
            spinner.remove_class("active")
            progress.remove_class("active")
        status.update(message)

    def action_refresh_metrics(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        root = "C:\\" if platform.system().lower() == "windows" else "/"
        try:
            dsk = psutil.disk_usage(root).percent
        except OSError:
            dsk = 0.0

        self.query_one("#bar-cpu", ProgressBar).update(progress=cpu)
        self.query_one("#bar-ram", ProgressBar).update(progress=ram)
        self.query_one("#bar-disk", ProgressBar).update(progress=dsk)
        self.query_one("#val-cpu", Static).update(f"{cpu:.1f}% used")
        self.query_one("#val-ram", Static).update(f"{ram:.1f}% used")
        self.query_one("#val-disk", Static).update(f"{dsk:.1f}% used")
        self.query_one("#sysinfo-summary", Static).update(
            f"Computer: {platform.node()}   |   OS: {platform.system()} {platform.release()}"
        )

    def _finish_task(self, target_id: str, title: str, summary_renderable: Any, raw_data: Any) -> None:
        self.query_one(f"#{target_id}", Static).update(summary_renderable)
        log = self.query_one("#tech-log", RichLog)
        log.write(Panel(RichJSON(json.dumps(raw_data, default=str)), title=title, border_style="cyan"))
        self._set_busy(False, f"Completed: {title}")

    def _run_background(
        self,
        status_msg: str,
        target_id: str,
        title: str,
        fn: Callable[[], tuple[Any, Any]],
    ) -> None:
        self._set_busy(True, status_msg)
        self._worker_exec(target_id, title, fn)

    @work(thread=True)
    def _worker_exec(
        self,
        target_id: str,
        title: str,
        fn: Callable[[], tuple[Any, Any]],
    ) -> None:
        try:
            summary, raw = fn()
        except Exception as exc:
            summary = f"[red]Could not complete {title}:[/red] {exc}"
            raw = {"error": str(exc)}
        self.call_from_thread(self._finish_task, target_id, title, summary, raw)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-refresh":
            self.action_refresh_metrics()
            self.query_one("#activity-status", Static).update("Live telemetry refreshed.")
        elif bid == "btn-toggle-log":
            self.action_toggle_log()
        elif bid == "btn-quick-scan":
            self._run_background(
                "Running Quick Scan (checking disk, memory, and system health)...",
                "res-overview",
                "Quick Scan",
                self._task_quick_scan,
            )
        elif bid == "btn-integrity":
            self._run_background(
                "Checking core OS files (DISM / SFC / package verification)...",
                "res-repair",
                "Check System Files",
                self._task_integrity,
            )
        elif bid == "btn-repair-dry":
            self._run_background(
                "Preparing safe preview of system repairs...",
                "res-repair",
                "Preview System Fixes",
                self._task_repair_preview,
            )
        elif bid == "btn-net-check":
            self._run_background(
                "Testing internet connectivity and flushing DNS cache...",
                "res-repair",
                "Network Check & DNS Flush",
                self._task_net_check,
            )
        elif bid == "btn-sec-audit":
            self._run_background(
                "Auditing firewall, antivirus, and protection status...",
                "res-security",
                "System Protection Check",
                self._task_sec_audit,
            )
        elif bid == "btn-malware-scan":
            self._run_background(
                "Scanning Downloads, Temp, and Startup folders for threats...",
                "res-security",
                "Malware & Virus Scan",
                self._task_malware_scan,
            )
        elif bid == "btn-trash-list":
            self._run_background(
                "Reading Recycle Bin / Trash contents...",
                "res-recovery",
                "Deleted Files",
                self._task_trash_list,
            )
        elif bid == "btn-temp-rec":
            self._run_background(
                "Searching for unsaved Office, LibreOffice, and temp documents...",
                "res-recovery",
                "Unsaved Documents",
                self._task_temp_rec,
            )
        elif bid == "btn-shadows":
            self._run_background(
                "Checking available system restore snapshots...",
                "res-recovery",
                "Restore Snapshots",
                self._task_shadows,
            )
        elif bid == "btn-svc-health":
            url = self.query_one("#input-server-url", Input).value.strip().rstrip("/")
            self._run_background(
                f"Connecting to {url}/health...",
                "res-service",
                "Service Health",
                lambda: self._task_svc_get(url, "/health"),
            )
        elif bid == "btn-svc-sysinfo":
            url = self.query_one("#input-server-url", Input).value.strip().rstrip("/")
            self._run_background(
                f"Fetching system profile from {url}/v1/sysinfo...",
                "res-service",
                "Service System Profile",
                lambda: self._task_svc_get(url, "/v1/sysinfo"),
            )

    def _task_quick_scan(self) -> tuple[Any, Any]:
        if self.server_url:
            data = httpx.get(f"{self.server_url}/v1/smart-scan", timeout=30.0).json()
        else:
            data = optimizer.run_smart_scan(self.cfg)
        mem = memory.check_memory()
        dsk = disk.check_disk(repair=False)
        table = Table(title="Quick Scan Summary", expand=True)
        table.add_column("Area", style="cyan")
        table.add_column("Status", style="green")
        table.add_row("Memory Usage", f"{mem.get('percent_used', 'N/A')}% used")
        table.add_row("Disk Check", str(dsk.get("status", dsk.get("tool", "Checked"))))
        table.add_row("Overall Scan", "Completed safely (no files modified)")
        return table, {"smart_scan": data, "memory": mem, "disk": dsk}

    def _task_integrity(self) -> tuple[Any, Any]:
        res = integrity.check_integrity(repair=False)
        status = res.get("status", "Checked")
        msg = f"[bold cyan]System File Status:[/bold cyan] {status}\nOpen the Technical Activity Log (press L) for full tool output."
        return msg, res

    def _task_repair_preview(self) -> tuple[Any, Any]:
        net_preview = network.reset_network_stack(dry_run=True)
        res = {
            "dry_run": True,
            "disk": "chkdsk /scan (Windows) or fsck -n (Linux)",
            "system_files": "DISM /RestoreHealth + sfc /scannow",
            "network": net_preview,
        }
        table = Table(title="Planned Repairs (Preview Only — Nothing Changed)", expand=True)
        table.add_column("Repair Step", style="yellow")
        table.add_column("Action")
        table.add_row("Disk Check", res["disk"])
        table.add_row("System Files", res["system_files"])
        table.add_row("Network Reset", ", ".join(net_preview.get("commands", ["NetworkManager restart"])))
        return table, res

    def _task_net_check(self) -> tuple[Any, Any]:
        ping_res = network.test_connectivity("1.1.1.1")
        dns_res = network.flush_dns()
        msg = (
            f"[bold cyan]Internet Ping (1.1.1.1):[/bold cyan] "
            f"{'Reachable' if ping_res.get('reachable', True) else 'Unreachable'}\n"
            f"[bold cyan]DNS Cache:[/bold cyan] {dns_res.get('message', 'Flushed')}"
        )
        return msg, {"ping": ping_res, "dns_flush": dns_res}

    def _task_sec_audit(self) -> tuple[Any, Any]:
        res = security.audit_security_posture()
        table = Table(title="System Protection Status", expand=True)
        table.add_column("Check", style="cyan")
        table.add_column("Result")
        for key, val in res.items():
            table.add_row(str(key).replace("_", " ").title(), str(val))
        return table, res

    def _task_malware_scan(self) -> tuple[Any, Any]:
        res = malware.scan(self.cfg.malware, offline=True, quick_scan=True)
        threats = res.get("threats_found", res.get("infected_count", 0))
        msg = (
            f"[bold cyan]Scan Finished:[/bold cyan] {threats} potential threat(s) flagged.\n"
            "Press [bold]L[/bold] to inspect scanned paths and engine details."
        )
        return msg, res

    def _task_trash_list(self) -> tuple[Any, Any]:
        res = recovery.list_trash_items(limit=25)
        items = res.get("items", [])
        if not items:
            return "Your Recycle Bin / Trash is currently empty.", res
        table = Table(title=f"Deleted Files Found ({len(items)})", expand=True)
        table.add_column("Name", style="cyan")
        table.add_column("Size")
        table.add_column("Deleted Date")
        for item in items[:15]:
            table.add_row(item.get("name", ""), item.get("size_formatted", ""), item.get("deleted_date", ""))
        return table, res

    def _task_temp_rec(self) -> tuple[Any, Any]:
        res = recovery.scan_recoverable_temp_files(limit=25)
        files = res.get("files", [])
        if not files:
            return "No unsaved Office or temp draft files were found.", res
        table = Table(title=f"Recoverable Drafts Found ({len(files)})", expand=True)
        table.add_column("File", style="cyan")
        table.add_column("Size")
        table.add_column("Modified")
        for f in files[:15]:
            table.add_row(f.get("name", ""), f.get("size_formatted", ""), f.get("modified", ""))
        return table, res

    def _task_shadows(self) -> tuple[Any, Any]:
        res = recovery.list_shadow_copies()
        count = res.get("count", 0)
        note = res.get("note", "")
        msg = f"[bold cyan]Restore Snapshots Found:[/bold cyan] {count}\n{note}"
        return msg, res

    def _task_svc_get(self, base_url: str, path: str) -> tuple[Any, Any]:
        try:
            resp = httpx.get(f"{base_url}{path}", timeout=5.0)
            data = resp.json()
            return f"[green]Connected to {base_url}{path}[/green] (HTTP {resp.status_code}). Press L for JSON payload.", data
        except Exception as exc:
            err = {
                "error": f"Could not reach {base_url}{path}: {exc}",
                "hint": "Start the background service with: sysmaint serve",
            }
            return f"[yellow]Service is not running at {base_url}.[/yellow]\nStart it in a terminal with: [bold]sysmaint serve[/bold]", err


def launch_tui(config: Optional[SysMaintConfig] = None, server_url: Optional[str] = None) -> None:
    """Launch the SysMaint Terminal Client UI."""
    app = SysMaintTUI(config=config, server_url=server_url)
    app.run()
