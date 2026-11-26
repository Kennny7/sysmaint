# sysmaint/gui/components/dialogs.py

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk


def show_confirmation_dialog(
    master,
    title: str,
    message: str,
    on_confirm: Callable,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
) -> ctk.CTkToplevel:
    """Show a modern confirmation modal dialog."""
    dialog = ctk.CTkToplevel(master)
    dialog.title(title)
    dialog.geometry("420x200")
    dialog.resizable(False, False)
    dialog.transient(master)
    dialog.grab_set()

    # Center window
    dialog.update_idletasks()
    x = master.winfo_x() + (master.winfo_width() // 2) - 210
    y = master.winfo_y() + (master.winfo_height() // 2) - 100
    dialog.geometry(f"+{x}+{y}")

    lbl_title = ctk.CTkLabel(
        dialog,
        text=title,
        font=ctk.CTkFont(size=16, weight="bold"),
    )
    lbl_title.pack(padx=20, pady=(20, 8), anchor="w")

    lbl_msg = ctk.CTkLabel(
        dialog,
        text=message,
        font=ctk.CTkFont(size=12),
        text_color="#94a3b8",
        wraplength=380,
        justify="left",
    )
    lbl_msg.pack(padx=20, pady=(0, 20), anchor="w")

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=(0, 20), side="bottom")

    def handle_confirm():
        dialog.destroy()
        on_confirm()

    def handle_cancel():
        dialog.destroy()

    btn_confirm = ctk.CTkButton(
        btn_frame,
        text=confirm_text,
        command=handle_confirm,
        fg_color="#ef4444",
        hover_color="#dc2626",
        width=100,
    )
    btn_confirm.pack(side="right", padx=(8, 0))

    btn_cancel = ctk.CTkButton(
        btn_frame,
        text=cancel_text,
        command=handle_cancel,
        fg_color="#334155",
        hover_color="#475569",
        width=100,
    )
    btn_cancel.pack(side="right")

    return dialog
