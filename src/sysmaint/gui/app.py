# sysmaint/gui/app.py

from __future__ import annotations

import customtkinter as ctk

from ..config import SysMaintConfig, load_config
from ..utils.escalate import is_elevated, request_elevation
from .components.console import ConsoleWidget
from .theme import DARK_BG_PRIMARY, DARK_BG_SECONDARY, init_theme
from .views.backup import BackupView
from .views.cleaner import CleanerView
from .views.dashboard import DashboardView
from .views.diagnostics import DiagnosticsView
from .views.integrity import IntegrityView
from .views.malware import MalwareView
from .views.network import NetworkView
from .views.security import SecurityView
from .views.settings import SettingsView
from .views.startup import StartupView


class SysMaintApp(ctk.CTk):
    """Main SysMaint Graphical User Interface Application."""

    def __init__(self, config: SysMaintConfig | None = None):
        super().__init__()
        self.config = config or load_config()

        init_theme(
            theme_mode=self.config.ui.theme,
            color_theme=self.config.ui.accent_color,
        )

        self.title("SysMaint - Professional Cross-Platform System Maintenance Suite")
        self.geometry("1180x760")
        self.minsize(980, 640)

        # Configure Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Left Sidebar Navigation
        self.sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0,
            fg_color=DARK_BG_SECONDARY,
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(11, weight=1)

        # App Logo & Branding
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=16, pady=(18, 14), sticky="w")

        lbl_logo = ctk.CTkLabel(
            brand_frame,
            text="⚡ SysMaint",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8",
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            brand_frame,
            text="System Maintenance Suite",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        lbl_sub.pack(anchor="w")

        # Nav Buttons List
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("cleaner", "🧹  Junk Cleaner"),
            ("diagnostics", "🩺  Diagnostics"),
            ("integrity", "🛡️  File Integrity"),
            ("malware", "🦠  Malware Scan"),
            ("startup", "🚀  Startup Apps"),
            ("network", "🌐  Network Tools"),
            ("security", "🔒  Security Audit"),
            ("backup", "💾  Backups & Points"),
            ("settings", "⚙️  Settings"),
        ]

        for idx, (view_id, label) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=36,
                corner_radius=8,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="transparent",
                text_color="#cbd5e1",
                hover_color="#334155",
                command=lambda v=view_id: self.show_view(v),
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=12, pady=2)
            self.nav_buttons[view_id] = btn

        # Bottom Elevation Status
        elevated = is_elevated()
        elev_frame = ctk.CTkFrame(self.sidebar, fg_color="#131d2e", corner_radius=8)
        elev_frame.grid(row=12, column=0, sticky="ew", padx=12, pady=16)

        elev_txt = "🛡️ Administrator Active" if elevated else "⚠️ Run as Administrator"
        elev_col = "#10b981" if elevated else "#f59e0b"
        self.btn_elev = ctk.CTkButton(
            elev_frame,
            text=elev_txt,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=elev_col,
            fg_color="transparent",
            hover_color="#1e293b",
            height=28,
            command=self._handle_elevation if not elevated else None,
        )
        self.btn_elev.pack(fill="x", padx=4, pady=4)

        # 2. Main Content & Console Area
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=DARK_BG_PRIMARY)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Bottom Console
        self.console = ConsoleWidget(self.main_container, height=130)
        self.console.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))

        # View Dictionary
        self.views: dict[str, ctk.CTkFrame] = {
            "dashboard": DashboardView(self.main_container, self.config, log_callback=self.log),
            "cleaner": CleanerView(self.main_container, self.config, log_callback=self.log),
            "diagnostics": DiagnosticsView(self.main_container, self.config, log_callback=self.log),
            "integrity": IntegrityView(self.main_container, self.config, log_callback=self.log),
            "malware": MalwareView(self.main_container, self.config, log_callback=self.log),
            "startup": StartupView(self.main_container, self.config, log_callback=self.log),
            "network": NetworkView(self.main_container, self.config, log_callback=self.log),
            "security": SecurityView(self.main_container, self.config, log_callback=self.log),
            "backup": BackupView(self.main_container, self.config, log_callback=self.log),
            "settings": SettingsView(self.main_container, self.config, log_callback=self.log),
        }

        self.current_view_id: str | None = None
        self.show_view("dashboard")
        self.log("SysMaint GUI started successfully. Ready for operations.")

    def log(self, message: str):
        """Append log message to bottom console safely across threads."""
        self.after(0, lambda: self.console.write_line(f"[*] {message}"))

    def show_view(self, view_id: str):
        """Display the selected view and update sidebar button highlights."""
        if view_id == self.current_view_id:
            return

        # Hide current view
        if self.current_view_id and self.current_view_id in self.views:
            self.views[self.current_view_id].grid_forget()
            if self.current_view_id in self.nav_buttons:
                self.nav_buttons[self.current_view_id].configure(
                    fg_color="transparent",
                    text_color="#cbd5e1",
                )

        # Show new view
        if view_id in self.views:
            self.views[view_id].grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
            if view_id in self.nav_buttons:
                self.nav_buttons[view_id].configure(
                    fg_color="#38bdf8",
                    text_color="#0f172a",
                )
            self.current_view_id = view_id

    def _handle_elevation(self):
        """Request UAC elevation on Windows or sudo on Linux."""
        self.log("Requesting administrative elevation...")
        request_elevation(exit_on_relaunch=True)


def launch_gui(config: SysMaintConfig | None = None):
    """Launcher helper function for GUI."""
    app = SysMaintApp(config=config)
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
