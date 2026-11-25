# sysmaint/gui/views/cleaner.py

from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Callable, Dict, Optional

from ...config import SysMaintConfig
from ...modules.cleaner import clean_junk, scan_junk
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, DARK_BG_CARD, DARK_BORDER
from ..components.cards import MetricCard, SectionHeader


class CleanerView(ctk.CTkScrollableFrame):
    """System Junk & Temporary File Cleaner view."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="System Cleaner & Junk Optimizer",
            subtitle="Safely discover and reclaim disk space from temporary files, caches, and system dumps",
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        # 2. Metric Summary Cards
        self.space_card = MetricCard(
            self,
            title="Reclaimable Space",
            value="0 B",
            subtitle="Ready to scan",
            icon="🧹",
            accent_color=ACCENT_EMERALD,
        )
        self.space_card.grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=(0, 15))

        self.files_card = MetricCard(
            self,
            title="Junk Files Found",
            value="0 Files",
            subtitle="Across all cache directories",
            icon="📁",
            accent_color=ACCENT_CYAN,
        )
        self.files_card.grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=(0, 15))

        # 3. Category Checkboxes & Controls Frame
        self.controls_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.controls_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))
        self.controls_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.controls_frame,
            text="⚙️ Select Cleaning Categories",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 10))

        self.cat_vars: Dict[str, ctk.BooleanVar] = {
            "user_temp": ctk.BooleanVar(value=True),
            "system_temp": ctk.BooleanVar(value=True),
            "browser_cache": ctk.BooleanVar(value=True),
            "system_logs": ctk.BooleanVar(value=True),
            "package_cache": ctk.BooleanVar(value=True),
            "thumbnails": ctk.BooleanVar(value=True),
        }

        cb_labels = [
            ("user_temp", "User Temp Files & AppData Cache"),
            ("system_temp", "Windows / System Temp & Prefetch"),
            ("browser_cache", "Web Browser Caches (Chrome, Edge, Firefox, Brave)"),
            ("system_logs", "Crash Dumps & Application Log Files"),
            ("package_cache", "Update Download & Package Manager Caches"),
            ("thumbnails", "File Explorer Thumbnail Cache"),
        ]

        for i, (key, label) in enumerate(cb_labels):
            row = 1 + (i // 2)
            col = i % 2
            cb = ctk.CTkCheckBox(
                self.controls_frame,
                text=label,
                variable=self.cat_vars[key],
                font=ctk.CTkFont(size=12),
            )
            cb.grid(row=row, column=col, sticky="w", padx=16, pady=6)

        # Buttons
        btn_bar = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        btn_bar.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(15, 16))

        self.btn_scan = ctk.CTkButton(
            btn_bar,
            text="🔍 Analyze Space",
            command=self.trigger_scan,
            width=140,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_scan.pack(side="left", padx=(0, 10))

        self.btn_clean = ctk.CTkButton(
            btn_bar,
            text="✨ Clean Selected Junk",
            command=self.trigger_clean,
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            width=160,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_clean.pack(side="left")

        # 4. Itemized Results Container
        self.results_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.results_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        self.lbl_res_header = ctk.CTkLabel(
            self.results_frame,
            text="📊 Itemized Breakdown",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.lbl_res_header.pack(anchor="w", padx=16, pady=(12, 6))

        self.breakdown_container = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        self.breakdown_container.pack(fill="x", padx=16, pady=(0, 12))

        self.lbl_status = ctk.CTkLabel(
            self.breakdown_container,
            text="Click 'Analyze Space' to calculate how much disk space can be safely reclaimed.",
            font=ctk.CTkFont(size=12),
            text_color="#64748b",
        )
        self.lbl_status.pack(anchor="w", pady=4)

    def _get_selected_categories(self):
        return [k for k, v in self.cat_vars.items() if v.get()]

    def trigger_scan(self):
        """Scan selected junk categories in background."""
        cats = self._get_selected_categories()
        if self.log_callback:
            self.log_callback(f"Scanning for junk files across categories: {', '.join(cats)}...")
        self.btn_scan.configure(state="disabled")

        def _worker():
            res = scan_junk(categories=cats)
            self.after(0, lambda: self._apply_scan(res))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_scan(self, res: dict):
        self.btn_scan.configure(state="normal")
        total_formatted = res.get("total_bytes_formatted", "0 B")
        total_files = f"{res.get('total_files', 0)} Files"

        self.space_card.update_values(total_formatted, "Ready to clean")
        self.files_card.update_values(total_files, "Scanned locations")

        for widget in self.breakdown_container.winfo_children():
            widget.destroy()

        breakdown = res.get("categories", {})
        for cat_name, cat_data in breakdown.items():
            row = ctk.CTkFrame(self.breakdown_container, fg_color="#131d2e", corner_radius=6)
            row.pack(fill="x", pady=2)

            name_lbl = ctk.CTkLabel(
                row,
                text=cat_name.replace("_", " ").title(),
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            name_lbl.pack(side="left", padx=10, pady=6)

            size_lbl = ctk.CTkLabel(
                row,
                text=f"{cat_data.get('bytes_formatted', '0 B')} ({cat_data.get('files_count', 0)} files)",
                font=ctk.CTkFont(size=12),
                text_color=ACCENT_CYAN,
            )
            size_lbl.pack(side="right", padx=10, pady=6)

        if self.log_callback:
            self.log_callback(f"Junk analysis completed: {total_formatted} in {total_files} can be freed.")

    def trigger_clean(self):
        """Clean selected junk files in background."""
        cats = self._get_selected_categories()
        if self.log_callback:
            self.log_callback(f"Cleaning junk files across {len(cats)} categories...")
        self.btn_clean.configure(state="disabled")

        def _worker():
            res = clean_junk(categories=cats, dry_run=False)
            self.after(0, lambda: self._apply_clean(res))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_clean(self, res: dict):
        self.btn_clean.configure(state="normal")
        freed = res.get("freed_bytes_formatted", "0 B")
        deleted = f"{res.get('deleted_files', 0)} Files"

        self.space_card.update_values("0 B", f"Cleaned {freed}")
        self.files_card.update_values("0 Files", f"Removed {deleted}")

        for widget in self.breakdown_container.winfo_children():
            widget.destroy()

        lbl_success = ctk.CTkLabel(
            self.breakdown_container,
            text=f"✅ Successfully cleaned {freed}! Freed space across {deleted} files.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ACCENT_EMERALD,
        )
        lbl_success.pack(anchor="w", pady=6)

        if self.log_callback:
            self.log_callback(f"Cleanup finished: {res.get('message', '')}")
