# src/sysmaint/tui/app.py

from __future__ import annotations

import json
import platform
from typing import Any, Optional

import httpx
import psutil
from rich.json import JSON as RichJSON
from rich.panel import Panel
from rich.table import Table
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
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
    sysinfo,
)


class SysMaintTUI(App):
    """Attractive Terminal Client UI for SysMaint Sentinel Microservice."""

    TITLE = f"SysMaint v{__version__} ({__codename__})"
    SUB_TITLE = __brand__

    CSS = """
    Screen {
        background: #0b1120;
        color: #e2e8f0;
    }
    Header {
        background: #0f172a;
        color: #38bdf8;
        border-bottom: solid #1e293b;
    }
    Footer {
        background: #0f172a;
        color: #94a3b8;
    }
    .card {
        background: #111827;
        border: round #1e293b;
        padding: 1 2;
        margin: 1 0;
        height: auto;
    }
    .card-title {
        color: #38bdf8;
        text-style: bold;
        margin-bottom: 1;
    }
    .action-row {
        height: auto;
        margin: 1 0;
    }
    Button {
        margin-right: 1;
    }
    RichLog {
        background: #020617;
        border: round #1e293b;
        min-height: 14;
        height: 1fr;
        padding: 1;
    }
    Input {
        margin: 1 0;
    }
    .metric-label {
        color: #94a3b8;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_metrics", "Refresh"),
        Binding("s", "smart_scan", "Smart Scan"),
    ]

    def __init__(
        self,
        config: Optional[SysMaintConfig] = None,
        server_url: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.cfg = config or load_config()
        self.server_url = server_url.rstrip("/") if server_url else None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="tab-dashboard"):
            with TabPane("Dashboard", id="tab-dashboard"):
                with VerticalScroll():
                    with Vertical(classes="card"):
                        yield Label(
                            f"System Telemetry & Sentinel Overview  |  Mode: "
                            f"{self.server_url or 'Direct Local Engine'}",
                            classes="card-title",
                        )
                        yield Label("CPU Usage", classes="metric-label")
                        yield ProgressBar(total=100, show_eta=False, id="bar-cpu")
                        yield Label("Memory Usage", classes="metric-label")
                        yield ProgressBar(total=100, show_eta=False, id="bar-ram")
                        yield Label("Root Disk Usage", classes="metric-label")
                        yield ProgressBar(total=100, show_eta=False, id="bar-disk")
                        yield Static("", id="sysinfo-summary")
                    with Horizontal(classes="action-row"):
                        yield Button("Refresh Telemetry", id="btn-refresh", variant="primary")
                        yield Button("1-Click Smart Scan", id="btn-smart-scan", variant="success")
                    yield RichLog(id="log-dashboard", wrap=True, highlight=True)

            with TabPane("Diagnostics & Repair", id="tab-repair"):
                with VerticalScroll():
                    with Vertical(classes="card"):
                        yield Label("System Integrity, Disk & Network Repair", classes="card-title")
                        with Horizontal(classes="action-row"):
                            yield Button("Run Full Diagnostics", id="btn-diag", variant="primary")
                            yield Button("Integrity Check (DISM/SFC)", id="btn-integrity", variant="default")
                            yield Button("Dry-Run Repair", id="btn-repair-dry", variant="warning")
                            yield Button("Network Stack Reset (Dry)", id="btn-net-reset", variant="default")
                    yield RichLog(id="log-repair", wrap=True, highlight=True)

            with TabPane("Malware & Security", id="tab-security"):
                with VerticalScroll():
                    with Vertical(classes="card"):
                        yield Label("Security Posture & Offline Malware Guard", classes="card-title")
                        with Horizontal(classes="action-row"):
                            yield Button("Security Posture Audit", id="btn-sec-audit", variant="primary")
                            yield Button("Quick YARA Malware Scan", id="btn-yara-scan", variant="success")
                    yield RichLog(id="log-security", wrap=True, highlight=True)

            with TabPane("Data Recovery", id="tab-recovery"):
                with VerticalScroll():
                    with Vertical(classes="card"):
                        yield Label("Deleted Files, Shadow Copies & Temp Drafts", classes="card-title")
                        with Horizontal(classes="action-row"):
                            yield Button("List Recycle Bin / Trash", id="btn-trash-list", variant="primary")
                            yield Button("List Shadow Copies / Snapshots", id="btn-shadows", variant="default")
                            yield Button("Scan Temp Auto-Recovery", id="btn-temp-rec", variant="success")
                    yield RichLog(id="log-recovery", wrap=True, highlight=True)

            with TabPane("Microservice", id="tab-service"):
                with VerticalScroll():
                    with Vertical(classes="card"):
                        yield Label("Microservice Client & Health Probe", classes="card-title")
                        yield Input(
                            value=self.server_url or "http://127.0.0.1:8765",
                            placeholder="http://127.0.0.1:8765",
                            id="input-server-url",
                        )
                        with Horizontal(classes="action-row"):
                            yield Button("Ping /health", id="btn-svc-health", variant="primary")
                            yield Button("Fetch /v1/sysinfo", id="btn-svc-sysinfo", variant="default")
                    yield RichLog(id="log-service", wrap=True, highlight=True)

        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh_metrics()
        self.set_interval(5.0, self.action_refresh_metrics)

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
        self.query_one("#sysinfo-summary", Static).update(
            f"[cyan]Host:[/cyan] {platform.node()}  |  "
            f"[cyan]OS:[/cyan] {platform.system()} {platform.release()}  |  "
            f"[cyan]CPU:[/cyan] {cpu:.1f}%  |  [cyan]RAM:[/cyan] {ram:.1f}%  |  [cyan]Disk:[/cyan] {dsk:.1f}%"
        )

    def action_smart_scan(self) -> None:
        self._run_smart_scan()

    def _write_result(self, log_id: str, title: str, data: Any) -> None:
        log = self.query_one(f"#{log_id}", RichLog)
        log.write(Panel(RichJSON(json.dumps(data, default=str)), title=title, border_style="cyan"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-refresh":
            self.action_refresh_metrics()
        elif bid == "btn-smart-scan":
            self._run_smart_scan()
        elif bid == "btn-diag":
            self._run_diagnostics()
        elif bid == "btn-integrity":
            self._run_integrity()
        elif bid == "btn-repair-dry":
            self._run_repair_dry()
        elif bid == "btn-net-reset":
            self._run_net_reset()
        elif bid == "btn-sec-audit":
            self._run_sec_audit()
        elif bid == "btn-yara-scan":
            self._run_yara_scan()
        elif bid == "btn-trash-list":
            self._run_trash_list()
        elif bid == "btn-shadows":
            self._run_shadows()
        elif bid == "btn-temp-rec":
            self._run_temp_rec()
        elif bid == "btn-svc-health":
            url = self.query_one("#input-server-url", Input).value.strip().rstrip("/")
            self._run_svc_get(url, "/health")
        elif bid == "btn-svc-sysinfo":
            url = self.query_one("#input-server-url", Input).value.strip().rstrip("/")
            self._run_svc_get(url, "/v1/sysinfo")

    @work(thread=True)
    def _run_smart_scan(self) -> None:
        if self.server_url:
            res = httpx.get(f"{self.server_url}/v1/smart-scan", timeout=30.0).json()
        else:
            res = optimizer.run_smart_scan(self.cfg)
        self.call_from_thread(self._write_result, "log-dashboard", "Smart Scan", res)

    @work(thread=True)
    def _run_diagnostics(self) -> None:
        res = {
            "disk": disk.check_disk(repair=False),
            "memory": memory.check_memory(),
        }
        self.call_from_thread(self._write_result, "log-repair", "Diagnostics", res)

    @work(thread=True)
    def _run_integrity(self) -> None:
        res = integrity.check_integrity(repair=False)
        self.call_from_thread(self._write_result, "log-repair", "Integrity Check", res)

    @work(thread=True)
    def _run_repair_dry(self) -> None:
        res = {
            "dry_run": True,
            "disk": "chkdsk /scan or fsck -n",
            "integrity": "DISM /RestoreHealth + sfc /scannow",
            "network": network.reset_network_stack(dry_run=True),
        }
        self.call_from_thread(self._write_result, "log-repair", "Dry-Run Repair Plan", res)

    @work(thread=True)
    def _run_net_reset(self) -> None:
        res = network.reset_network_stack(dry_run=True)
        self.call_from_thread(self._write_result, "log-repair", "Network Reset (Dry-Run)", res)

    @work(thread=True)
    def _run_sec_audit(self) -> None:
        res = security.audit_security_posture()
        self.call_from_thread(self._write_result, "log-security", "Security Audit", res)

    @work(thread=True)
    def _run_yara_scan(self) -> None:
        res = malware.scan(self.cfg.malware, offline=True, quick_scan=True)
        self.call_from_thread(self._write_result, "log-security", "Quick Malware Scan", res)

    @work(thread=True)
    def _run_trash_list(self) -> None:
        res = recovery.list_trash_items(limit=30)
        self.call_from_thread(self._write_result, "log-recovery", "Recycle Bin / Trash", res)

    @work(thread=True)
    def _run_shadows(self) -> None:
        res = recovery.list_shadow_copies()
        self.call_from_thread(self._write_result, "log-recovery", "Shadow Copies / Snapshots", res)

    @work(thread=True)
    def _run_temp_rec(self) -> None:
        res = recovery.scan_recoverable_temp_files(limit=30)
        self.call_from_thread(self._write_result, "log-recovery", "Temp Auto-Recovery Files", res)

    @work(thread=True)
    def _run_svc_get(self, base_url: str, path: str) -> None:
        try:
            resp = httpx.get(f"{base_url}{path}", timeout=5.0)
            data: Any = resp.json()
        except Exception as exc:
            data = {
                "error": f"Could not reach microservice at {base_url}{path}: {exc}",
                "hint": "Start the microservice first with: sysmaint serve",
            }
        self.call_from_thread(self._write_result, "log-service", f"GET {path}", data)


def launch_tui(config: Optional[SysMaintConfig] = None, server_url: Optional[str] = None) -> None:
    """Launch the SysMaint Terminal Client UI."""
    app = SysMaintTUI(config=config, server_url=server_url)
    app.run()
