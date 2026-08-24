# sysmaint/gui/views/integrity.py

from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Callable, Optional

from ...config import SysMaintConfig
from ...modules.integrity import check_integrity
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, ACCENT_ROSE, DARK_BG_CARD, DARK_BORDER
from ..components.cards import MetricCard, SectionHeader


class IntegrityView(ctk.CTkScrollableFrame):
    """System File Integrity, DISM, and SFC repair view."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="System Integrity & Component Repair",
            subtitle="Verify and repair corrupted Windows system files (DISM & SFC) or Linux package files",
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        # 2. Metric Cards
        self.dism_card = MetricCard(
            self,
            title="Component Store (DISM)",
            value="Ready",
            subtitle="Deep Windows image check",
            icon="🛡️",
            accent_color=ACCENT_CYAN,
        )
        self.dism_card.grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=(0, 15))

        self.sfc_card = MetricCard(
            self,
            title="System File Checker (SFC)",
            value="Ready",
            subtitle="System file verification",
            icon="🔍",
            accent_color=ACCENT_EMERALD,
        )
        self.sfc_card.grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=(0, 15))

        # 3. Actions Frame
        self.actions_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.actions_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.actions_frame,
            text="⚡ Automated Repair Operations",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            self.actions_frame,
            text="Run non-destructive integrity verification or perform a full online system file repair.",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        btn_bar = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 16))

        self.btn_verify = ctk.CTkButton(
            btn_bar,
            text="🔍 Verify Only (Read-Only)",
            command=lambda: self.run_check(repair=False),
            width=180,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_verify.pack(side="left", padx=(0, 10))

        self.btn_repair = ctk.CTkButton(
            btn_bar,
            text="✨ Scan & Repair Corruptions",
            command=lambda: self.run_check(repair=True),
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            width=210,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_repair.pack(side="left")

        # 4. Status Details Frame
        self.details_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.details_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        self.lbl_det_title = ctk.CTkLabel(
            self.details_frame,
            text="📋 Integrity Scan Output",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.lbl_det_title.pack(anchor="w", padx=16, pady=(12, 6))

        self.txt_output = ctk.CTkTextbox(
            self.details_frame,
            height=160,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#090d16",
        )
        self.txt_output.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.txt_output.insert("end", "Click 'Verify Only' or 'Scan & Repair' to execute system integrity operations.\n")
        self.txt_output.configure(state="disabled")

    def run_check(self, repair: bool = False):
        mode_str = "Scan & Repair" if repair else "Verification"
        if self.log_callback:
            self.log_callback(f"Starting system integrity {mode_str}...")

        self.btn_verify.configure(state="disabled")
        self.btn_repair.configure(state="disabled")

        def _worker():
            res = check_integrity(repair=repair)
            self.after(0, lambda: self._apply_results(res, repair))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_results(self, res: dict, repair: bool):
        self.btn_verify.configure(state="normal")
        self.btn_repair.configure(state="normal")

        dism = res.get("dism", {})
        sfc = res.get("sfc", {})

        dism_status = dism.get("parsed", {}).get("status", "Completed")
        sfc_status = sfc.get("parsed", {}).get("status", "Completed")

        self.dism_card.update_values(dism_status, "DISM Image Status")
        self.sfc_card.update_values(sfc_status, "SFC Verification Status")

        self.txt_output.configure(state="normal")
        self.txt_output.delete("1.0", "end")
        self.txt_output.insert("end", f"=== Integrity Check Results ({'Repair' if repair else 'Read-Only'}) ===\n\n")

        if dism.get("output"):
            self.txt_output.insert("end", f"[DISM Output]\n{dism.get('output')}\n\n")
        if sfc.get("output"):
            self.txt_output.insert("end", f"[SFC Output]\n{sfc.get('output')}\n\n")

        self.txt_output.configure(state="disabled")

        if self.log_callback:
            self.log_callback(f"Integrity check finished: DISM={dism_status}, SFC={sfc_status}")
