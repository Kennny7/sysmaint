# sysmaint/gui/components/cards.py

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..theme import (
    ACCENT_CYAN,
    ACCENT_EMERALD,
    DARK_BG_CARD,
    DARK_BORDER,
    get_health_color,
)


class MetricCard(ctk.CTkFrame):
    """A styled card displaying a key system metric with title and value."""

    def __init__(
        self,
        master,
        title: str,
        value: str,
        subtitle: str = "",
        icon: str = "📊",
        accent_color: str = ACCENT_CYAN,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=12,
            border_width=1,
            border_color=DARK_BORDER,
            fg_color=DARK_BG_CARD,
            **kwargs,
        )

        self.grid_columnconfigure(0, weight=1)

        # Header with icon and title
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(12, 4))

        icon_label = ctk.CTkLabel(
            header_frame,
            text=icon,
            font=ctk.CTkFont(size=20),
        )
        icon_label.pack(side="left", padx=(0, 8))

        title_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#94a3b8",
        )
        title_label.pack(side="left")

        # Primary Value
        self.val_label = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=accent_color,
        )
        self.val_label.pack(anchor="w", padx=16, pady=(2, 2))

        # Subtitle
        self.sub_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self.sub_label.pack(anchor="w", padx=16, pady=(0, 12))

    def update_values(self, value: str, subtitle: str | None = None):
        self.val_label.configure(text=value)
        if subtitle is not None:
            self.sub_label.configure(text=subtitle)


class HealthScoreCard(ctk.CTkFrame):
    """Large hero card displaying overall System Health Score and quick action."""

    def __init__(
        self,
        master,
        score: int = 100,
        grade: str = "Excellent",
        on_scan: Callable | None = None,
        on_fix: Callable | None = None,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=16,
            border_width=1,
            border_color=DARK_BORDER,
            fg_color=DARK_BG_CARD,
            **kwargs,
        )

        self.grid_columnconfigure(1, weight=1)

        # Left: Big Score Badge
        self.score_frame = ctk.CTkFrame(
            self,
            width=110,
            height=110,
            corner_radius=55,
            border_width=3,
            border_color=get_health_color(score),
            fg_color="#0f172a",
        )
        self.score_frame.grid(row=0, column=0, rowspan=2, padx=20, pady=20)
        self.score_frame.pack_propagate(False)

        self.score_label = ctk.CTkLabel(
            self.score_frame,
            text=str(score),
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=get_health_color(score),
        )
        self.score_label.pack(expand=True)

        # Middle: Text Information
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=(20, 10))

        self.title_label = ctk.CTkLabel(
            info_frame,
            text=f"System Health: {grade}",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.pack(anchor="w")

        self.desc_label = ctk.CTkLabel(
            info_frame,
            text="All core components and diagnostics are operating smoothly.",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        )
        self.desc_label.pack(anchor="w", pady=(4, 0))

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            self,
            orientation="horizontal",
            height=8,
            corner_radius=4,
            progress_color=get_health_color(score),
        )
        self.progress.set(score / 100.0)
        self.progress.grid(row=1, column=1, sticky="ew", padx=(0, 20), pady=(0, 20))

        # Right: Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=2, padx=20, pady=20)

        if on_scan:
            self.scan_btn = ctk.CTkButton(
                btn_frame,
                text="🔍 Smart Scan",
                command=on_scan,
                width=130,
                height=36,
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            self.scan_btn.pack(pady=(0, 8))

        if on_fix:
            self.fix_btn = ctk.CTkButton(
                btn_frame,
                text="⚡ Auto-Fix All",
                command=on_fix,
                fg_color=ACCENT_EMERALD,
                hover_color="#059669",
                width=130,
                height=36,
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            self.fix_btn.pack()

    def update_score(self, score: int, grade: str, desc: str = ""):
        self.score_label.configure(text=str(score), text_color=get_health_color(score))
        self.score_frame.configure(border_color=get_health_color(score))
        self.title_label.configure(text=f"System Health: {grade}")
        if desc:
            self.desc_label.configure(text=desc)
        self.progress.set(score / 100.0)
        self.progress.configure(progress_color=get_health_color(score))


class SectionHeader(ctk.CTkFrame):
    """Header for content views with title, subtitle, and optional right-hand button."""

    def __init__(
        self,
        master,
        title: str,
        subtitle: str = "",
        btn_text: str | None = None,
        btn_cmd: Callable | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)

        t_label = ctk.CTkLabel(
            text_frame,
            text=title,
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        t_label.pack(anchor="w")

        if subtitle:
            s_label = ctk.CTkLabel(
                text_frame,
                text=subtitle,
                font=ctk.CTkFont(size=12),
                text_color="#94a3b8",
            )
            s_label.pack(anchor="w", pady=(2, 0))

        if btn_text and btn_cmd:
            btn = ctk.CTkButton(
                self,
                text=btn_text,
                command=btn_cmd,
                height=32,
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            btn.pack(side="right", padx=(10, 0))
