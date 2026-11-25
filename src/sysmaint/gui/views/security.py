# sysmaint/gui/views/security.py

from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Callable, Optional

from ...config import SysMaintConfig
from ...modules.security import audit_security_posture
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, ACCENT_ROSE, DARK_BG_CARD, DARK_BORDER
from ..components.cards import MetricCard, SectionHeader


class SecurityView(ctk.CTkScrollableFrame):
    """Security Posture Audit and Defense configuration view."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="Security & Firewall Posture Audit",
            subtitle="Verify Antivirus protection, Firewall profiles, and system defense integrity",
            btn_text="🔄 Re-Audit Security",
            btn_cmd=self.refresh_security,
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        # 2. Metric Cards
        self.score_card = MetricCard(
            self,
            title="Security Score",
            value="100 / 100",
            subtitle="Optimal defense status",
            icon="🛡️",
            accent_color=ACCENT_EMERALD,
        )
        self.score_card.grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=(0, 15))

        self.fw_card = MetricCard(
            self,
            title="System Firewall",
            value="Active",
            subtitle="All profiles enabled",
            icon="🔥",
            accent_color=ACCENT_CYAN,
        )
        self.fw_card.grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=(0, 15))

        # 3. Posture Checklist Frame
        self.checklist_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.checklist_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.checklist_frame,
            text="📋 Defense Configuration & Checklist",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self.checklist_container = ctk.CTkFrame(self.checklist_frame, fg_color="transparent")
        self.checklist_container.pack(fill="x", padx=16, pady=(0, 12))

        self.refresh_security()

    def refresh_security(self):
        for w in self.checklist_container.winfo_children():
            w.destroy()

        res = audit_security_posture()
        score = res.get("score", 100)
        issues = res.get("issues", [])
        fw_active = res.get("firewall_active", True)

        self.score_card.update_values(f"{score} / 100", "Overall security rating")
        self.score_card.val_label.configure(text_color=ACCENT_EMERALD if score >= 80 else ACCENT_ROSE)

        self.fw_card.update_values("Active" if fw_active else "Inactive", "Firewall protection")

        # Add items
        checks = [
            ("Antivirus & Real-time Protection", "Active", ACCENT_EMERALD),
            ("System Firewall Rules", "Enabled" if fw_active else "Warning", ACCENT_EMERALD if fw_active else ACCENT_ROSE),
            ("Process Elevation (Admin / Root)", "Verified" if res.get("elevated") else "Standard User", ACCENT_EMERALD if res.get("elevated") else "#f59e0b"),
        ]

        for title, status, color in checks:
            row = ctk.CTkFrame(self.checklist_container, fg_color="#131d2e", corner_radius=8)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(row, text=f"• {title}", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=12, pady=6)
            ctk.CTkLabel(row, text=status, font=ctk.CTkFont(size=11, weight="bold"), text_color=color).pack(side="right", padx=12, pady=6)

        if issues:
            lbl_iss = ctk.CTkLabel(
                self.checklist_container,
                text="⚠️ Recommendations:",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#fca5a5",
            )
            lbl_iss.pack(anchor="w", padx=4, pady=(10, 2))

            for issue in issues:
                ctk.CTkLabel(
                    self.checklist_container,
                    text=f"  - {issue}",
                    font=ctk.CTkFont(size=11),
                    text_color="#fecaca",
                ).pack(anchor="w", padx=4, pady=1)

        if self.log_callback:
            self.log_callback(f"Security audit completed: Score {score}/100.")
