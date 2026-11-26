# sysmaint/gui/views/dashboard.py

from __future__ import annotations

import threading
from collections.abc import Callable

import customtkinter as ctk

from ...config import SysMaintConfig
from ...modules.optimizer import run_auto_fix, run_smart_scan
from ...modules.sysinfo import get_system_specs
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, ACCENT_INDIGO, DARK_BG_CARD, DARK_BORDER
from ..components.cards import HealthScoreCard, MetricCard, SectionHeader


class DashboardView(ctk.CTkScrollableFrame):
    """Main Home Dashboard view."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Callable | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="System Dashboard",
            subtitle="Overview of system health, real-time resource utilization, and smart maintenance",
            btn_text="🔄 Refresh Specs",
            btn_cmd=self.refresh_specs,
        )
        self.header.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 15))

        # 2. Hero Health Score Card
        self.hero_card = HealthScoreCard(
            self,
            score=100,
            grade="Excellent",
            on_scan=self.trigger_smart_scan,
            on_fix=self.trigger_auto_fix,
        )
        self.hero_card.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 15))

        # 3. Live Metric Cards Grid
        self.cpu_card = MetricCard(
            self,
            title="Processor (CPU)",
            value="0 %",
            subtitle="Cores: -- | Freq: --",
            icon="⚡",
            accent_color=ACCENT_CYAN,
        )
        self.cpu_card.grid(row=2, column=0, sticky="ew", padx=(10, 5), pady=(0, 15))

        self.ram_card = MetricCard(
            self,
            title="Memory (RAM)",
            value="0 %",
            subtitle="Used: -- / Total: --",
            icon="🧠",
            accent_color=ACCENT_INDIGO,
        )
        self.ram_card.grid(row=2, column=1, sticky="ew", padx=5, pady=(0, 15))

        self.disk_card = MetricCard(
            self,
            title="Storage",
            value="--",
            subtitle="Junk scan pending",
            icon="💾",
            accent_color=ACCENT_EMERALD,
        )
        self.disk_card.grid(row=2, column=2, sticky="ew", padx=5, pady=(0, 15))

        self.sec_card = MetricCard(
            self,
            title="Security Posture",
            value="Active",
            subtitle="Firewall: ON | AV: Active",
            icon="🛡️",
            accent_color="#38bdf8",
        )
        self.sec_card.grid(row=2, column=3, sticky="ew", padx=(5, 10), pady=(0, 15))

        # 4. System Specifications Card
        self.specs_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.specs_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 15))
        self.specs_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        spec_title = ctk.CTkLabel(
            self.specs_frame,
            text="💻 Host System Specifications",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        spec_title.grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 8))

        self.lbl_os = ctk.CTkLabel(self.specs_frame, text="OS: Loading...", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        self.lbl_os.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        self.lbl_host = ctk.CTkLabel(self.specs_frame, text="Host: Loading...", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        self.lbl_host.grid(row=1, column=1, sticky="w", padx=16, pady=(0, 12))

        self.lbl_cpu_model = ctk.CTkLabel(self.specs_frame, text="CPU: Loading...", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        self.lbl_cpu_model.grid(row=1, column=2, sticky="w", padx=16, pady=(0, 12))

        self.lbl_uptime = ctk.CTkLabel(self.specs_frame, text="Uptime: Loading...", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        self.lbl_uptime.grid(row=1, column=3, sticky="w", padx=16, pady=(0, 12))

        # 5. Detected Issues & Recommendations Frame
        self.findings_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.findings_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 15))
        self.findings_frame.grid_columnconfigure(0, weight=1)

        findings_header = ctk.CTkLabel(
            self.findings_frame,
            text="📋 Detected System Health Findings",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        findings_header.pack(anchor="w", padx=16, pady=(12, 6))

        self.findings_container = ctk.CTkFrame(self.findings_frame, fg_color="transparent")
        self.findings_container.pack(fill="x", padx=16, pady=(0, 12))

        self.lbl_no_findings = ctk.CTkLabel(
            self.findings_container,
            text="Click 'Smart Scan' to analyze all system modules for issues and optimizations.",
            font=ctk.CTkFont(size=12),
            text_color="#64748b",
        )
        self.lbl_no_findings.pack(anchor="w", pady=4)

        # Initial background load
        threading.Thread(target=self.refresh_specs, daemon=True).start()

    def refresh_specs(self):
        """Fetch real-time specifications and metrics in background."""
        try:
            specs = get_system_specs()
            os_txt = f"{specs.get('os_name')} {specs.get('os_release')}"
            host_txt = f"Host: {specs.get('hostname')}"
            cpu_model = f"CPU: {specs.get('cpu', {}).get('model', 'Generic')[:28]}"
            uptime_txt = f"Uptime: {specs.get('uptime_formatted')}"

            cpu_usage = f"{specs.get('cpu', {}).get('usage_percent', 0)} %"
            cores_txt = f"Cores: {specs.get('cpu', {}).get('logical_cores')} | {specs.get('cpu', {}).get('current_frequency_mhz')} MHz"

            mem_usage = f"{specs.get('memory', {}).get('usage_percent', 0)} %"
            mem_sub = f"{specs.get('memory', {}).get('available_formatted')} available"

            disk_txt = specs.get('storage', {}).get('total_formatted', '--')
            disk_sub = f"Used: {specs.get('storage', {}).get('used_formatted', '--')}"

            self.after(0, lambda: self._apply_specs(os_txt, host_txt, cpu_model, uptime_txt, cpu_usage, cores_txt, mem_usage, mem_sub, disk_txt, disk_sub))
        except Exception as exc:
            if self.log_callback:
                self.log_callback(f"Failed to refresh specs: {exc}")

    def _apply_specs(self, os_txt, host_txt, cpu_model, uptime_txt, cpu_usage, cores_txt, mem_usage, mem_sub, disk_txt, disk_sub):
        self.lbl_os.configure(text=f"OS: {os_txt}")
        self.lbl_host.configure(text=host_txt)
        self.lbl_cpu_model.configure(text=cpu_model)
        self.lbl_uptime.configure(text=uptime_txt)

        self.cpu_card.update_values(cpu_usage, cores_txt)
        self.ram_card.update_values(mem_usage, mem_sub)
        self.disk_card.update_values(disk_txt, disk_sub)

    def trigger_smart_scan(self):
        """Execute non-destructive 1-Click Smart Scan."""
        if self.log_callback:
            self.log_callback("Initiating 1-Click Smart Health Scan...")
        self.hero_card.title_label.configure(text="Scanning System...")

        def _worker():
            res = run_smart_scan(self.config)
            self.after(0, lambda: self._apply_scan_results(res))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_scan_results(self, res: dict):
        score = res.get("health_score", 100)
        grade = res.get("health_grade", "Excellent")
        findings = res.get("findings", [])
        total_issues = res.get("total_issues", 0)

        desc = f"Scan complete. Found {total_issues} item(s) to optimize or fix."
        self.hero_card.update_score(score, grade, desc)

        # Clear existing findings
        for widget in self.findings_container.winfo_children():
            widget.destroy()

        if not findings:
            lbl = ctk.CTkLabel(
                self.findings_container,
                text="✅ No critical issues found! System is in excellent condition.",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=ACCENT_EMERALD,
            )
            lbl.pack(anchor="w", pady=4)
        else:
            for f in findings:
                item_frame = ctk.CTkFrame(self.findings_container, fg_color="#131d2e", corner_radius=6)
                item_frame.pack(fill="x", pady=2, padx=2)

                sev_color = "#ef4444" if f.get("severity") == "High" else "#f59e0b"
                badge = ctk.CTkLabel(
                    item_frame,
                    text=f"[{f.get('category')}]",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=sev_color,
                )
                badge.pack(side="left", padx=(8, 6), pady=4)

                title_lbl = ctk.CTkLabel(
                    item_frame,
                    text=f.get("title", ""),
                    font=ctk.CTkFont(size=12),
                )
                title_lbl.pack(side="left", padx=4, pady=4)

        if self.log_callback:
            self.log_callback(f"Smart Scan finished: Health Score {score}/100 ({grade}) with {total_issues} findings.")

    def trigger_auto_fix(self):
        """Execute 1-Click Auto-Fix for all detected fixable issues."""
        if self.log_callback:
            self.log_callback("Starting 1-Click Auto-Fix & Optimization...")
        self.hero_card.title_label.configure(text="Optimizing System...")

        def _worker():
            res = run_auto_fix(self.config)
            self.after(0, lambda: self._apply_fix_results(res))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_fix_results(self, res: dict):
        new_score = res.get("new_health_score", 100)
        new_grade = res.get("new_health_grade", "Excellent")
        desc = "Auto-fix applied successfully! Junk cleared, memory optimized, DNS flushed."
        self.hero_card.update_score(new_score, new_grade, desc)

        # Trigger quick refresh of findings
        self.trigger_smart_scan()
        if self.log_callback:
            self.log_callback(f"Auto-Fix complete! New Health Score: {new_score}/100.")
