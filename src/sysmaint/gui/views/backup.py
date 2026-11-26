# sysmaint/gui/views/backup.py

from __future__ import annotations

import threading
from collections.abc import Callable

import customtkinter as ctk

from ...config import SysMaintConfig
from ...modules.backup import create_backup
from ...modules.restore import launch_system_recovery, list_available_backups
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, DARK_BG_CARD, DARK_BORDER
from ..components.cards import MetricCard, SectionHeader


class BackupView(ctk.CTkScrollableFrame):
    """System Restore Points, Snapshots, and Recovery view."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Callable | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="System Restore Points & Backups",
            subtitle="Create Windows System Restore Points, Linux configuration snapshots, and access recovery wizards",
            btn_text="🔄 Refresh Points",
            btn_cmd=self.refresh_backups,
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        # 2. Metric Cards
        self.points_card = MetricCard(
            self,
            title="Available Restore Points",
            value="0",
            subtitle="System recovery points",
            icon="💾",
            accent_color=ACCENT_CYAN,
        )
        self.points_card.grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=(0, 15))

        self.status_card = MetricCard(
            self,
            title="Backup Protection",
            value="Enabled",
            subtitle="Auto restore point on repair",
            icon="🛡️",
            accent_color=ACCENT_EMERALD,
        )
        self.status_card.grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=(0, 15))

        # 3. Create Restore Point Action Card
        self.create_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.create_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.create_frame,
            text="✨ Create New System Restore Point",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        bar = ctk.CTkFrame(self.create_frame, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(0, 16))

        self.entry_desc = ctk.CTkEntry(bar, width=280, placeholder_text="Enter description (e.g. SysMaint Manual Point)")
        self.entry_desc.insert(0, "SysMaint Manual Backup Point")
        self.entry_desc.pack(side="left", padx=(0, 10))

        self.btn_create = ctk.CTkButton(
            bar,
            text="➕ Create Restore Point",
            command=self.trigger_create,
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            width=170,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_create.pack(side="left", padx=(0, 10))

        self.btn_ui = ctk.CTkButton(
            bar,
            text="🛠️ System Recovery UI",
            command=self.trigger_recovery_ui,
            fg_color="#334155",
            hover_color="#475569",
            width=160,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_ui.pack(side="left")

        # 4. Existing Restore Points List
        self.list_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.list_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.list_frame,
            text="📋 Existing Restore Points & Backup Archives",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self.points_container = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        self.points_container.pack(fill="x", padx=16, pady=(0, 12))

        self.refresh_backups()

    def trigger_create(self):
        desc = self.entry_desc.get().strip() or "SysMaint Restore Point"
        if self.log_callback:
            self.log_callback(f"Creating restore point '{desc}'...")
        self.btn_create.configure(state="disabled")

        def _worker():
            res = create_backup(self.config, kind="auto", description=desc)
            self.after(0, lambda: self._apply_create(res))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_create(self, res: dict):
        self.btn_create.configure(state="normal")
        if res.get("created"):
            if self.log_callback:
                self.log_callback(res.get("message", "Restore point created successfully."))
        else:
            if self.log_callback:
                self.log_callback(f"Failed to create restore point: {res.get('error')}")
        self.refresh_backups()

    def trigger_recovery_ui(self):
        if self.log_callback:
            self.log_callback("Launching native system recovery wizard...")
        launch_system_recovery()

    def refresh_backups(self):
        for w in self.points_container.winfo_children():
            w.destroy()

        backups = list_available_backups(self.config)
        self.points_card.update_values(str(len(backups)), "Discovered points")

        if not backups:
            lbl = ctk.CTkLabel(
                self.points_container,
                text="No restore points detected.",
                font=ctk.CTkFont(size=12),
                text_color="#64748b",
            )
            lbl.pack(anchor="w", pady=6)
            return

        for pt in backups:
            row = ctk.CTkFrame(self.points_container, fg_color="#131d2e", corner_radius=8)
            row.pack(fill="x", pady=3)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", padx=10, pady=6)

            ctk.CTkLabel(left, text=pt.get("name", "Restore Point"), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(left, text=f"Type: {pt.get('type')}  |  Date: {pt.get('date', 'N/A')}", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")
