# sysmaint/gui/components/console.py

from __future__ import annotations

import customtkinter as ctk
import tkinter as tk
from typing import Optional


class ConsoleWidget(ctk.CTkFrame):
    """Embedded live terminal/log viewer with scrolling and controls."""

    def __init__(self, master, height: int = 200, **kwargs):
        super().__init__(master, corner_radius=10, fg_color="#090d16", border_width=1, border_color="#334155", **kwargs)

        # Header bar
        header = ctk.CTkFrame(self, height=30, fg_color="#1e293b", corner_radius=8)
        header.pack(fill="x", padx=2, pady=2)

        title = ctk.CTkLabel(
            header,
            text="💻 Execution Console",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8",
        )
        title.pack(side="left", padx=10)

        clear_btn = ctk.CTkButton(
            header,
            text="Clear",
            width=50,
            height=20,
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            hover_color="#334155",
            command=self.clear,
        )
        clear_btn.pack(side="right", padx=6)

        # Text Box
        self.text_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#090d16",
            text_color="#e2e8f0",
            wrap="word",
            height=height,
        )
        self.text_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.write_line("SysMaint Console Ready.\n")

    def write_line(self, text: str, tag: Optional[str] = None):
        """Append a line to the console and scroll to end."""
        self.text_box.configure(state="normal")
        self.text_box.insert("end", text + "\n")
        self.text_box.see("end")
        self.text_box.configure(state="disabled")

    def clear(self):
        """Clear all console text."""
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.configure(state="disabled")
