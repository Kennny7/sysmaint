# src/sysmaint/tui/app.py

from __future__ import annotations

import platform
from typing import Any, Callable, Optional

import httpx
import psutil
from rich.table import Table
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    ProgressBar,
    Static,
    Tab,
    Tabs,
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
from ..utils.escalate import is_elevated, request_elevation
from .modals import ConfirmLongTaskModal, ElevationModal, TechnicalLogModal
from .themes import CUSTOM_THEMES, THEME_CYCLE


class SysMaintTUI(App):
    """User-friendly, btop-inspired Terminal Client UI for SysMaint."""

    TITLE = f"SysMaint v{__version__} ({__codename__})"
    SUB_TITLE = __brand__

    CSS = """
    Screen {
        background: $background;
        color: $text;
    }

    #workspace-pane {
        height: 1fr;
        padding: 0 1;
    }

    #nav-tabs {
        width: 100%;
        height: 3;
        background: $surface;
        border-bottom: solid $primary;
    }

    #nav-tabs Tab {
        width: 1fr;
        height: 3;
        padding: 1 1;
        content-align: center middle;
        text-style: bold;
        color: $text-muted;
    }

    #nav-tabs Tab.-active {
        color: $primary;
        background: $panel;
        text-style: bold;
    }

    .telemetry-grid {
        layout: grid;
        grid-size: 3;
        grid-gutter: 1;
        height: 5;
        margin: 1 0 0 0;
    }

    .metric-card {
        background: $panel;
        border: round $primary;
        padding: 0 1;
        height: 5;
    }

    #device-strip {
        background: $panel;
        border: round $secondary;
        padding: 0 2;
        height: 3;
        margin: 0;
        content-align: left middle;
    }

    #sysinfo-summary {
        height: 1;
    }

    #page-switcher {
        height: 1fr;
        margin-top: 1;
    }

    .tab-body {
        height: 1fr;
    }

    .card {
        background: $panel;
        border: round $secondary;
        padding: 1 2;
        margin: 0 0 1 0;
        height: auto;
    }

    .card-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 0;
    }

    .action-item {
        height: auto;
        margin: 1 0 0 0;
    }

    /* Radiant outline buttons on dark background (default for obsidian-gold & dark themes) */
    Button {
        background: $surface;
        color: $primary;
        border: round $primary;
        text-style: bold;
    }

    Button:hover, Button:focus {
        background: $panel;
        color: $accent;
        border: heavy $accent;
    }

    /* Solid dark-yellow / golden buttons for amber-slate theme */
    Screen.solid-gold-buttons Button {
        background: #a16207;
        color: #fefce8;
        border: round #eab308;
    }

    Screen.solid-gold-buttons Button:hover,
    Screen.solid-gold-buttons Button:focus {
        background: #ca8a04;
        color: #090b10;
        border: heavy #fde047;
    }

    .action-item Button {
        width: 1fr;
        margin-right: 1;
    }

    .action-desc {
        color: $text-muted;
        padding-left: 1;
        margin-top: 1;
    }

    .result-box {
        background: $surface;
        border: round $accent;
        padding: 1 2;
        margin: 0 0 1 0;
        height: 1fr;
        overflow-y: auto;
    }

    Footer {
        height: 3;
        border-top: solid $panel;
        padding: 0 2;
        content-align: left middle;
    }

    #activity-bar {
        height: auto;
        background: $surface;
        border-top: solid $primary;
        padding: 0 2;
        display: none;
    }

    #activity-bar.active {
        display: block;
    }

    #activity-top-row {
        height: auto;
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
        text-style: bold;
    }

    #activity-percent {
        width: 10;
        text-align: right;
        color: $accent;
        text-style: bold;
    }

    #activity-progress {
        width: 100%;
        height: auto;
        margin-top: 1;
        padding: 0 1;
        border: round $primary;
        background: $background;
        display: none;
    }

    #activity-progress.active {
        display: block;
    }

    ProgressBar {
        width: 100%;
    }

    ProgressBar > Bar {
        width: 1fr;
    }

    ProgressBar > Bar > .bar--bar {
        color: $primary;
        background: #334155;
    }

    ProgressBar > Bar > .bar--complete {
        color: $success;
        background: #334155;
    }

    ProgressBar > Bar > .bar--indeterminate {
        color: $accent;
        background: #334155;
    }

    #activity-live-line {
        color: $text-muted;
        margin-top: 0;
    }

    Input {
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_metrics", "Refresh"),
        Binding("l", "open_log", "View Technical Log"),
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
        self._log_entries: list[tuple[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="workspace-pane"):
            yield Tabs(
                Tab("Overview", id="tab-overview"),
                Tab("System Repair", id="tab-repair"),
                Tab("Security & Malware", id="tab-security"),
                Tab("Data Recovery", id="tab-recovery"),
                Tab("Background Service", id="tab-service"),
                id="nav-tabs",
            )

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

            with Vertical(id="device-strip"):
                yield Static("", id="sysinfo-summary")

            with ContentSwitcher(initial="tab-overview", id="page-switcher"):
                with Vertical(id="tab-overview", classes="tab-body"):
                    with Vertical(classes="card"):
                        yield Label("Quick Actions", classes="card-title")
                        with Horizontal(classes="action-item"):
                            yield Button("Quick Scan", id="btn-quick-scan")
                            yield Button("Refresh Stats", id="btn-refresh")
                            yield Button("View Technical Log (L)", id="btn-open-log")
                        yield Label(
                            "Note: Quick Scan safely checks storage, memory, and system health without changing files.",
                            classes="action-desc",
                        )
                    yield Static(
                        "Press Quick Scan to see a plain-English health summary.",
                        id="res-overview",
                        classes="result-box",
                    )

                with Vertical(id="tab-repair", classes="tab-body"):
                    with Vertical(classes="card"):
                        yield Label("Health Checks & Repair Tools", classes="card-title")
                        with Horizontal(classes="action-item"):
                            yield Button("Check System Files", id="btn-integrity")
                            yield Button("Fix System Files", id="btn-integrity-fix")
                            yield Button("Preview System Fixes", id="btn-repair-dry")
                            yield Button("Test & Fix Network", id="btn-net-check")
                        yield Label(
                            "Note: 'Check/Fix System Files' uses Windows DISM & SFC (or Linux package verify) and requires Administrator/root privileges.",
                            classes="action-desc",
                        )
                    yield Static(
                        "Select a check or repair above to inspect your system.",
                        id="res-repair",
                        classes="result-box",
                    )

                with Vertical(id="tab-security", classes="tab-body"):
                    with Vertical(classes="card"):
                        yield Label("Protection Audit & Threat Scanner", classes="card-title")
                        with Horizontal(classes="action-item"):
                            yield Button("Check System Protection", id="btn-sec-audit")
                            yield Button("Scan for Viruses & Malware", id="btn-malware-scan")
                        yield Label(
                            "Note: Scans Downloads, Temp, and Startup folders offline using built-in YARA rules and ClamAV (if installed).",
                            classes="action-desc",
                        )
                    yield Static(
                        "Run a protection check or malware scan to see results here.",
                        id="res-security",
                        classes="result-box",
                    )

                with Vertical(id="tab-recovery", classes="tab-body"):
                    with Vertical(classes="card"):
                        yield Label("Recover Deleted & Unsaved Files", classes="card-title")
                        with Horizontal(classes="action-item"):
                            yield Button("View Deleted Files", id="btn-trash-list")
                            yield Button("Find Unsaved Documents", id="btn-temp-rec")
                            yield Button("View Restore Snapshots", id="btn-shadows")
                        yield Label(
                            "Note: Inspects your Recycle Bin / Trash, Office & LibreOffice auto-recovery drafts, and OS restore snapshots.",
                            classes="action-desc",
                        )
                    yield Static(
                        "Choose a recovery option above to search for lost files.",
                        id="res-recovery",
                        classes="result-box",
                    )

                with Vertical(id="tab-service", classes="tab-body"):
                    with Vertical(classes="card"):
                        yield Label("Microservice Connection", classes="card-title")
                        yield Input(
                            value=self.server_url or "http://127.0.0.1:8765",
                            placeholder="http://127.0.0.1:8765",
                            id="input-server-url",
                        )
                        with Horizontal(classes="action-item"):
                            yield Button("Check Service Health", id="btn-svc-health")
                            yield Button("Fetch System Profile", id="btn-svc-sysinfo")
                        yield Label(
                            "Note: Start the background service anytime by running 'sysmaint serve' in a terminal.",
                            classes="action-desc",
                        )
                    yield Static(
                        "Check whether the local SysMaint microservice is running.",
                        id="res-service",
                        classes="result-box",
                    )

            with Vertical(id="activity-bar"):
                with Horizontal(id="activity-top-row"):
                    yield LoadingIndicator(id="activity-spinner")
                    yield Static("Ready.", id="activity-status")
                    yield Static("", id="activity-percent")
                yield ProgressBar(total=100, show_eta=False, id="activity-progress")
                yield Static("", id="activity-live-line")

            yield Footer()

    def on_mount(self) -> None:
        for theme_obj in CUSTOM_THEMES:
            self.register_theme(theme_obj)
        self._apply_theme("obsidian-gold")
        self.action_refresh_metrics()
        self.set_interval(5.0, self.action_refresh_metrics)

    def _apply_theme(self, theme_name: str) -> None:
        self.theme = theme_name
        if theme_name == "amber-slate":
            self.screen.add_class("solid-gold-buttons")
        else:
            self.screen.remove_class("solid-gold-buttons")

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab and event.tab.id:
            self.query_one("#page-switcher", ContentSwitcher).current = event.tab.id

    def action_open_log(self) -> None:
        self.push_screen(TechnicalLogModal(self._log_entries))

    def action_toggle_theme(self) -> None:
        try:
            idx = THEME_CYCLE.index(self.theme)
            next_theme = THEME_CYCLE[(idx + 1) % len(THEME_CYCLE)]
        except ValueError:
            next_theme = THEME_CYCLE[0]
        self._apply_theme(next_theme)
        self.notify(f"Theme switched to: {next_theme}", title="Theme")

    def _set_busy(self, busy: bool, message: str, live_line: str = "") -> None:
        self._busy = busy
        bar = self.query_one("#activity-bar", Vertical)
        spinner = self.query_one("#activity-spinner", LoadingIndicator)
        progress = self.query_one("#activity-progress", ProgressBar)
        status = self.query_one("#activity-status", Static)
        pct_lbl = self.query_one("#activity-percent", Static)
        live = self.query_one("#activity-live-line", Static)

        if busy:
            bar.add_class("active")
            spinner.add_class("active")
            progress.add_class("active")
            progress.update(total=None, progress=0)
            pct_lbl.update("Running...")
        else:
            bar.remove_class("active")
            spinner.remove_class("active")
            progress.remove_class("active")
            pct_lbl.update("")

        status.update(message)
        live.update(live_line)

    def _update_live_progress(self, line: str, percent: Optional[float]) -> None:
        progress = self.query_one("#activity-progress", ProgressBar)
        pct_lbl = self.query_one("#activity-percent", Static)
        live = self.query_one("#activity-live-line", Static)
        if percent is not None:
            progress.update(total=100, progress=percent)
            pct_lbl.update(f"{percent:.1f}%")
        live.update(f"Live output: {line[:110]}")

    def action_refresh_metrics(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        root = "C:\\" if platform.system().lower() == "windows" else "/"
        try:
            dsk = psutil.disk_usage(root).percent
        except OSError:
            dsk = 0.0

        priv = "Administrator / Root" if is_elevated() else "Standard User"
        engine = self.server_url or "Local Standalone"
        self.query_one("#bar-cpu", ProgressBar).update(progress=cpu)
        self.query_one("#bar-ram", ProgressBar).update(progress=ram)
        self.query_one("#bar-disk", ProgressBar).update(progress=dsk)
        self.query_one("#val-cpu", Static).update(f"{cpu:.1f}% used")
        self.query_one("#val-ram", Static).update(f"{ram:.1f}% used")
        self.query_one("#val-disk", Static).update(f"{dsk:.1f}% used")
        self.query_one("#sysinfo-summary", Static).update(
            f"Device: {platform.node()}   |   OS: {platform.system()} {platform.release()}   |   "
            f"Privileges: {priv}   |   Engine: {engine}"
        )

    def _finish_task(self, target_id: str, title: str, summary_renderable: Any, raw_data: Any) -> None:
        self.query_one(f"#{target_id}", Static).update(summary_renderable)
        self._log_entries.append((title, raw_data))
        self._set_busy(False, "", "")
        self.notify(f"Completed: {title} (press L for technical log)", title="Done")

    def _launch_guarded_task(
        self,
        *,
        title: str,
        status_msg: str,
        target_id: str,
        fn: Callable[[Callable[[str, Optional[float]], None]], tuple[Any, Any]],
        requires_admin: bool = False,
        long_estimate: Optional[str] = None,
        long_details: str = "",
    ) -> None:
        if self._busy:
            self.notify(
                "A background task is already running. Please wait for it to finish.",
                title="Task in Progress",
                severity="warning",
            )
            return

        def start_after_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            self._set_busy(True, status_msg, "Starting command...")
            self._worker_exec(target_id, title, fn)

        def check_long_or_run() -> None:
            if long_estimate:
                self.push_screen(
                    ConfirmLongTaskModal(title, long_estimate, long_details),
                    start_after_confirm,
                )
            else:
                start_after_confirm(True)

        if requires_admin and not is_elevated():
            def on_elev_choice(choice: str) -> None:
                if choice == "elevate":
                    ok = request_elevation(["tui"], exit_on_relaunch=True)
                    if not ok:
                        self.notify("Administrator elevation was cancelled.", severity="warning")
            self.push_screen(ElevationModal(title), on_elev_choice)
            return

        check_long_or_run()

    @work(thread=True)
    def _worker_exec(
        self,
        target_id: str,
        title: str,
        fn: Callable[[Callable[[str, Optional[float]], None]], tuple[Any, Any]],
    ) -> None:
        def report_progress(line: str, pct: Optional[float]) -> None:
            self.call_from_thread(self._update_live_progress, line, pct)

        try:
            summary, raw = fn(report_progress)
        except Exception as exc:
            summary = f"[red]Could not complete {title}:[/red] {exc}"
            raw = {"error": str(exc)}
        self.call_from_thread(self._finish_task, target_id, title, summary, raw)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-refresh":
            self.action_refresh_metrics()
            if not self._busy:
                self.notify("Live telemetry refreshed.", title="Refreshed")
        elif bid == "btn-open-log":
            self.action_open_log()
        elif bid == "btn-quick-scan":
            self._launch_guarded_task(
                title="Quick Scan",
                status_msg="Running Quick Scan (checking disk, memory, and system health)...",
                target_id="res-overview",
                fn=self._task_quick_scan,
            )
        elif bid == "btn-integrity":
            self._launch_guarded_task(
                title="Check System Files",
                status_msg="Checking core OS files (DISM & SFC)...",
                target_id="res-repair",
                fn=lambda cb: self._task_integrity(repair=False, cb=cb),
                requires_admin=True,
                long_estimate="5 to 25 minutes depending on disk speed",
                long_details="Runs Windows DISM /ScanHealth and SFC /verifyonly (or Linux package verification) to check OS files without modifying them.",
            )
        elif bid == "btn-integrity-fix":
            self._launch_guarded_task(
                title="Fix System Files",
                status_msg="Repairing corrupted OS files (DISM /RestoreHealth & SFC /scannow)...",
                target_id="res-repair",
                fn=lambda cb: self._task_integrity(repair=True, cb=cb),
                requires_admin=True,
                long_estimate="10 to 40 minutes depending on disk and network speed",
                long_details="Runs Windows DISM /RestoreHealth and sfc /scannow to repair corrupted operating system files.",
            )
        elif bid == "btn-repair-dry":
            self._launch_guarded_task(
                title="Preview System Fixes",
                status_msg="Preparing safe preview of system repairs...",
                target_id="res-repair",
                fn=self._task_repair_preview,
            )
        elif bid == "btn-net-check":
            self._launch_guarded_task(
                title="Test & Fix Network",
                status_msg="Testing connectivity and flushing DNS cache...",
                target_id="res-repair",
                fn=self._task_net_check,
            )
        elif bid == "btn-sec-audit":
            self._launch_guarded_task(
                title="Check System Protection",
                status_msg="Auditing firewall, antivirus, and protection status...",
                target_id="res-security",
                fn=self._task_sec_audit,
            )
        elif bid == "btn-malware-scan":
            self._launch_guarded_task(
                title="Scan for Viruses & Malware",
                status_msg="Scanning Downloads, Temp, and Startup folders for threats...",
                target_id="res-security",
                fn=self._task_malware_scan,
                long_estimate="2 to 15 minutes depending on Downloads/Temp folder size",
                long_details="Scans high-risk folders offline using YARA threat rules and ClamAV (if installed).",
            )
        elif bid == "btn-trash-list":
            self._launch_guarded_task(
                title="View Deleted Files",
                status_msg="Reading Recycle Bin / Trash contents...",
                target_id="res-recovery",
                fn=self._task_trash_list,
            )
        elif bid == "btn-temp-rec":
            self._launch_guarded_task(
                title="Find Unsaved Documents",
                status_msg="Searching for unsaved Office, LibreOffice, and temp documents...",
                target_id="res-recovery",
                fn=self._task_temp_rec,
            )
        elif bid == "btn-shadows":
            self._launch_guarded_task(
                title="View Restore Snapshots",
                status_msg="Checking available system restore snapshots...",
                target_id="res-recovery",
                fn=self._task_shadows,
                requires_admin=True,
            )
        elif bid == "btn-svc-health":
            url = self.query_one("#input-server-url", Input).value.strip().rstrip("/")
            self._launch_guarded_task(
                title="Check Service Health",
                status_msg=f"Connecting to {url}/health...",
                target_id="res-service",
                fn=lambda cb: self._task_svc_get(url, "/health", cb),
            )
        elif bid == "btn-svc-sysinfo":
            url = self.query_one("#input-server-url", Input).value.strip().rstrip("/")
            self._launch_guarded_task(
                title="Fetch System Profile",
                status_msg=f"Fetching system profile from {url}/v1/sysinfo...",
                target_id="res-service",
                fn=lambda cb: self._task_svc_get(url, "/v1/sysinfo", cb),
            )

    def _task_quick_scan(self, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        cb("Step 1/3: Checking memory usage...", 25.0)
        mem = memory.check_memory()
        cb("Step 2/3: Checking disk partitions...", 60.0)
        dsk = disk.check_disk(repair=False)
        cb("Step 3/3: Running smart health summary...", 90.0)
        if self.server_url:
            data = httpx.get(f"{self.server_url}/v1/smart-scan", timeout=30.0).json()
        else:
            data = optimizer.run_smart_scan(self.cfg)
        cb("Quick Scan complete.", 100.0)
        table = Table(title="Quick Scan Summary", expand=True)
        table.add_column("Area", style="cyan")
        table.add_column("Status", style="green")
        table.add_row("Memory Usage", f"{mem.get('percent_used', 'N/A')}% used")
        table.add_row("Disk Check", str(dsk.get("status", dsk.get("tool", "Checked"))))
        table.add_row("Overall Scan", "Completed safely (no files modified)")
        return table, {"smart_scan": data, "memory": mem, "disk": dsk}

    def _task_integrity(self, repair: bool, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        res = integrity.check_integrity(repair=repair, progress_cb=cb)
        status = res.get("status", "Checked")
        msg = f"[bold cyan]System File Status:[/bold cyan] {status}\nPress [bold]L[/bold] (View Technical Log) for full DISM/SFC output."
        return msg, res

    def _task_repair_preview(self, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        cb("Generating dry-run repair plan...", 50.0)
        net_preview = network.reset_network_stack(dry_run=True)
        res = {
            "dry_run": True,
            "disk": "chkdsk /scan (Windows) or fsck -n (Linux)",
            "system_files": "DISM /RestoreHealth + sfc /scannow",
            "network": net_preview,
        }
        cb("Preview ready.", 100.0)
        table = Table(title="Planned Repairs (Preview Only — Nothing Changed)", expand=True)
        table.add_column("Repair Step", style="yellow")
        table.add_column("Action")
        table.add_row("Disk Check", res["disk"])
        table.add_row("System Files", res["system_files"])
        table.add_row("Network Reset", ", ".join(net_preview.get("commands", ["NetworkManager restart"])))
        return table, res

    def _task_net_check(self, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        cb("Step 1/2: Pinging 1.1.1.1...", 40.0)
        ping_res = network.test_connectivity("1.1.1.1")
        cb("Step 2/2: Flushing DNS resolver cache...", 85.0)
        dns_res = network.flush_dns()
        cb("Network check complete.", 100.0)
        msg = (
            f"[bold cyan]Internet Ping (1.1.1.1):[/bold cyan] "
            f"{'Reachable' if ping_res.get('reachable', True) else 'Unreachable'}\n"
            f"[bold cyan]DNS Cache:[/bold cyan] {dns_res.get('message', 'Flushed')}"
        )
        return msg, {"ping": ping_res, "dns_flush": dns_res}

    def _task_sec_audit(self, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        cb("Inspecting firewall, antivirus, and privilege state...", 50.0)
        res = security.audit_security_posture()
        cb("Audit complete.", 100.0)
        table = Table(title="System Protection Status", expand=True)
        table.add_column("Check", style="cyan")
        table.add_column("Result")
        for key, val in res.items():
            table.add_row(str(key).replace("_", " ").title(), str(val))
        return table, res

    def _task_malware_scan(self, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        cb("Scanning Downloads, Temp, and Startup folders offline...", None)
        res = malware.scan(self.cfg.malware, offline=True, quick_scan=True)
        threats = res.get("threats_found", res.get("infected_count", 0))
        cb("Malware scan complete.", 100.0)
        msg = (
            f"[bold cyan]Scan Finished:[/bold cyan] {threats} potential threat(s) flagged.\n"
            "Press [bold]L[/bold] to inspect scanned paths and engine details."
        )
        return msg, res

    def _task_trash_list(self, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        cb("Listing Recycle Bin / Trash items...", 50.0)
        res = recovery.list_trash_items(limit=25)
        items = res.get("items", [])
        cb("Done.", 100.0)
        if not items:
            return "Your Recycle Bin / Trash is currently empty.", res
        table = Table(title=f"Deleted Files Found ({len(items)})", expand=True)
        table.add_column("Name", style="cyan")
        table.add_column("Size")
        table.add_column("Deleted Date")
        for item in items[:15]:
            table.add_row(item.get("name", ""), item.get("size_formatted", ""), item.get("deleted_date", ""))
        return table, res

    def _task_temp_rec(self, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        cb("Scanning Office, LibreOffice, and temp auto-recovery folders...", 50.0)
        res = recovery.scan_recoverable_temp_files(limit=25)
        files = res.get("files", [])
        cb("Done.", 100.0)
        if not files:
            return "No unsaved Office or temp draft files were found.", res
        table = Table(title=f"Recoverable Drafts Found ({len(files)})", expand=True)
        table.add_column("File", style="cyan")
        table.add_column("Size")
        table.add_column("Modified")
        for f in files[:15]:
            table.add_row(f.get("name", ""), f.get("size_formatted", ""), f.get("modified", ""))
        return table, res

    def _task_shadows(self, cb: Callable[[str, Optional[float]], None]) -> tuple[Any, Any]:
        cb("Querying system restore snapshots...", 50.0)
        res = recovery.list_shadow_copies()
        count = res.get("count", 0)
        note = res.get("note", "")
        cb("Done.", 100.0)
        msg = f"[bold cyan]Restore Snapshots Found:[/bold cyan] {count}\n{note}"
        return msg, res

    def _task_svc_get(
        self,
        base_url: str,
        path: str,
        cb: Callable[[str, Optional[float]], None],
    ) -> tuple[Any, Any]:
        cb(f"Requesting {base_url}{path}...", 50.0)
        try:
            resp = httpx.get(f"{base_url}{path}", timeout=5.0)
            data = resp.json()
            cb("Connected.", 100.0)
            return f"[green]Connected to {base_url}{path}[/green] (HTTP {resp.status_code}). Press L for JSON payload.", data
        except Exception as exc:
            err = {
                "error": f"Could not reach {base_url}{path}: {exc}",
                "hint": "Start the background service with: sysmaint serve",
            }
            cb("Service unreachable.", 100.0)
            return f"[yellow]Service is not running at {base_url}.[/yellow]\nStart it in a terminal with: [bold]sysmaint serve[/bold]", err


def launch_tui(config: Optional[SysMaintConfig] = None, server_url: Optional[str] = None) -> None:
    """Launch the SysMaint Terminal Client UI."""
    app = SysMaintTUI(config=config, server_url=server_url)
    app.run()
