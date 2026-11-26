# sysmaint/gui/views/settings.py

from __future__ import annotations

import threading
from collections.abc import Callable
from tkinter import filedialog

import customtkinter as ctk

from ...config import SysMaintConfig, save_config
from ...modules.optimizer import run_smart_scan
from ...modules.report import build_report, generate_html_report
from ...modules.scheduler import get_schedule_status, install_schedule, remove_schedule
from ...modules.security import audit_security_posture
from ...modules.sysinfo import get_system_specs
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, DARK_BG_CARD, DARK_BORDER
from ..components.cards import SectionHeader


class SettingsView(ctk.CTkScrollableFrame):
    """Application Configuration, Automated Scheduler, and Report Export view."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Callable | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="Settings & Automation",
            subtitle="Configure theme appearance, automated maintenance intervals, and export health reports",
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=(0, 15))

        # 2. Automated Maintenance Scheduler Frame
        self.sched_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.sched_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.sched_frame,
            text="⏰ Automated Recurring Maintenance",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            self.sched_frame,
            text="Schedule automatic background health scans and optimizations using OS Task Scheduler / Cron.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        sched_bar = ctk.CTkFrame(self.sched_frame, fg_color="transparent")
        sched_bar.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(sched_bar, text="Interval:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
        self.opt_interval = ctk.CTkOptionMenu(sched_bar, values=["DAILY", "WEEKLY", "MONTHLY"], width=110)
        self.opt_interval.set("WEEKLY")
        self.opt_interval.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(sched_bar, text="Time:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
        self.entry_time = ctk.CTkEntry(sched_bar, width=80, placeholder_text="02:00")
        self.entry_time.insert(0, "02:00")
        self.entry_time.pack(side="left", padx=(0, 12))

        self.btn_sched_install = ctk.CTkButton(
            sched_bar,
            text="Enable Schedule",
            command=self.install_maint_schedule,
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            width=130,
            height=30,
        )
        self.btn_sched_install.pack(side="left", padx=(0, 8))

        self.btn_sched_remove = ctk.CTkButton(
            sched_bar,
            text="Disable",
            command=self.remove_maint_schedule,
            fg_color="#ef4444",
            hover_color="#dc2626",
            width=90,
            height=30,
        )
        self.btn_sched_remove.pack(side="left")

        self.lbl_sched_status = ctk.CTkLabel(
            self.sched_frame,
            text="Status: Checking...",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        self.lbl_sched_status.pack(anchor="w", padx=16, pady=(0, 12))

        # 3. HTML Report Export Frame
        self.rep_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.rep_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.rep_frame,
            text="📄 Export System Health Report (HTML / PDF)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            self.rep_frame,
            text="Generate a modern, responsive HTML report dashboard summarizing all diagnostics and telemetry.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        self.btn_export = ctk.CTkButton(
            self.rep_frame,
            text="📥 Export HTML Health Report...",
            command=self.export_report,
            fg_color=ACCENT_CYAN,
            hover_color="#0284c7",
            text_color="#0f172a",
            width=220,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_export.pack(anchor="w", padx=16, pady=(0, 16))

        # 4. Appearance & Preferences Frame
        self.pref_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.pref_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.pref_frame,
            text="🎨 Appearance & Themes",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        theme_bar = ctk.CTkFrame(self.pref_frame, fg_color="transparent")
        theme_bar.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkLabel(theme_bar, text="Theme Mode:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self.opt_theme = ctk.CTkOptionMenu(
            theme_bar,
            values=["Dark", "Light", "System"],
            command=self.change_theme,
            width=120,
        )
        self.opt_theme.set("Dark")
        self.opt_theme.pack(side="left")

        self.refresh_schedule_status()

    def change_theme(self, choice: str):
        ctk.set_appearance_mode(choice.lower())
        self.config.ui.theme = choice.lower()
        save_config(self.config)

    def refresh_schedule_status(self):
        st = get_schedule_status()
        if st.get("installed"):
            self.lbl_sched_status.configure(
                text="Status: 🟢 Active (Automated background maintenance is enabled)",
                text_color=ACCENT_EMERALD,
            )
        else:
            self.lbl_sched_status.configure(
                text="Status: ⚪ Inactive (No recurring maintenance task scheduled)",
                text_color="#94a3b8",
            )

    def install_maint_schedule(self):
        inv = self.opt_interval.get()
        tm = self.entry_time.get().strip() or "02:00"
        if self.log_callback:
            self.log_callback(f"Installing maintenance schedule: {inv} at {tm}...")
        res = install_schedule(interval=inv, time_str=tm)
        if self.log_callback:
            self.log_callback(res.get("message", "Updated schedule."))
        self.refresh_schedule_status()

    def remove_maint_schedule(self):
        if self.log_callback:
            self.log_callback("Removing maintenance schedule...")
        res = remove_schedule()
        if self.log_callback:
            self.log_callback(res.get("message", "Removed schedule."))
        self.refresh_schedule_status()

    def export_report(self):
        f_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML Document", "*.html")],
            title="Save System Health Report",
        )
        if f_path:
            if self.log_callback:
                self.log_callback(f"Compiling full telemetry and exporting to {f_path}...")

            def _worker():
                results = {
                    "sysinfo": get_system_specs(),
                    "smart_scan": run_smart_scan(self.config),
                    "security": audit_security_posture(),
                }
                rep = build_report(results)
                generate_html_report(rep, output_path=f_path)
                if self.log_callback:
                    self.log_callback(f"HTML report successfully exported to {f_path}!")

            threading.Thread(target=_worker, daemon=True).start()
