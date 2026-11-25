# sysmaint/gui/views/startup.py

from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Callable, Optional

from ...config import SysMaintConfig
from ...modules.startup import list_startup_items, toggle_startup_item
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, ACCENT_ROSE, DARK_BG_CARD, DARK_BORDER
from ..components.cards import MetricCard, SectionHeader


class StartupView(ctk.CTkScrollableFrame):
    """Startup & Autorun Application Manager view."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="Startup Applications & Autoruns",
            subtitle="Manage programs that launch at login to reduce boot time and improve startup performance",
            btn_text="🔄 Refresh List",
            btn_cmd=self.refresh_startup_items,
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        # 2. Metric Cards
        self.count_card = MetricCard(
            self,
            title="Startup Programs",
            value="0",
            subtitle="Configured autoruns",
            icon="🚀",
            accent_color=ACCENT_CYAN,
        )
        self.count_card.grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=(0, 15))

        self.impact_card = MetricCard(
            self,
            title="High Impact Items",
            value="0",
            subtitle="Slows down boot",
            icon="⏱️",
            accent_color=ACCENT_ROSE,
        )
        self.impact_card.grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=(0, 15))

        # 3. Items List Container
        self.list_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.list_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.list_frame,
            text="📋 Configured Startup Applications",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self.items_container = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        self.items_container.pack(fill="x", padx=16, pady=(0, 12))

        self.refresh_startup_items()

    def refresh_startup_items(self):
        for w in self.items_container.winfo_children():
            w.destroy()

        items = list_startup_items()
        high_impact = len([i for i in items if i.get("impact") == "High"])

        self.count_card.update_values(str(len(items)), "Configured items")
        self.impact_card.update_values(str(high_impact), "High boot impact")

        if not items:
            lbl = ctk.CTkLabel(
                self.items_container,
                text="No startup applications detected.",
                font=ctk.CTkFont(size=12),
                text_color="#64748b",
            )
            lbl.pack(anchor="w", pady=6)
            return

        for item in items:
            row = ctk.CTkFrame(self.items_container, fg_color="#131d2e", corner_radius=8)
            row.pack(fill="x", pady=3)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", padx=10, pady=6, fill="x", expand=True)

            name = item.get("name", "Unknown Program")
            cmd = item.get("command", "")
            loc = item.get("location", "Registry")
            impact = item.get("impact", "Medium")

            top_line = ctk.CTkFrame(left, fg_color="transparent")
            top_line.pack(anchor="w")

            ctk.CTkLabel(top_line, text=name, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

            imp_color = ACCENT_ROSE if impact == "High" else (ACCENT_EMERALD if impact == "Low" else "#f59e0b")
            ctk.CTkLabel(top_line, text=f"• Impact: {impact}", font=ctk.CTkFont(size=11), text_color=imp_color).pack(side="left", padx=8)

            ctk.CTkLabel(left, text=f"Location: {loc} | Command: {cmd[:55]}", font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w")

            # Disable / Remove button
            btn_toggle = ctk.CTkButton(
                row,
                text="Disable",
                width=80,
                height=26,
                fg_color="#334155",
                hover_color="#475569",
                font=ctk.CTkFont(size=11),
                command=lambda n=name: self._toggle_item(n),
            )
            btn_toggle.pack(side="right", padx=10, pady=6)

    def _toggle_item(self, name: str):
        if self.log_callback:
            self.log_callback(f"Disabling startup item '{name}'...")
        res = toggle_startup_item(name, enable=False)
        if self.log_callback:
            self.log_callback(res.get("message", "Updated startup entry."))
        self.refresh_startup_items()
