# sysmaint/gui/views/diagnostics.py

from __future__ import annotations

import threading
import customtkinter as ctk
from typing import Callable, Optional

import psutil

from ...config import SysMaintConfig
from ...modules.disk import check_disk, get_disk_partitions
from ...modules.drivers import check_drivers
from ...modules.memory import check_memory, optimize_memory
from ...modules.services import control_service, list_services
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, ACCENT_ROSE, DARK_BG_CARD, DARK_BORDER
from ..components.cards import MetricCard, SectionHeader


class DiagnosticsView(ctk.CTkFrame):
    """System Hardware & OS Diagnostics view with tabbed sub-panels."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="System Diagnostics & Hardware",
            subtitle="Real-time monitoring and management for Disks, Memory, Drivers, and Services",
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=(0, 10))

        # 2. Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.tab_disk = self.tabview.add("💾 Disks & Storage")
        self.tab_mem = self.tabview.add("🧠 Memory & Processes")
        self.tab_drv = self.tabview.add("⚙️ Drivers & Devices")
        self.tab_svc = self.tabview.add("🛠️ Services")

        self._build_disk_tab()
        self._build_mem_tab()
        self._build_driver_tab()
        self._build_services_tab()

    # ---------------- Disks Tab ----------------
    def _build_disk_tab(self):
        tab = self.tab_disk
        tab.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(bar, text="Physical Disks & Mounted Partitions", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(bar, text="🔍 Check Filesystem Health", command=self._run_disk_check, width=170, height=30).pack(side="right")

        self.disk_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.disk_scroll.pack(fill="both", expand=True, padx=10, pady=6)
        self._refresh_disk_tab()

    def _refresh_disk_tab(self):
        for w in self.disk_scroll.winfo_children():
            w.destroy()

        parts = get_disk_partitions()
        for p in parts:
            card = ctk.CTkFrame(self.disk_scroll, corner_radius=10, fg_color=DARK_BG_CARD, border_width=1, border_color=DARK_BORDER)
            card.pack(fill="x", pady=4)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(8, 4))

            ctk.CTkLabel(top, text=f"Drive {p.get('device')} ({p.get('mountpoint')})", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
            ctk.CTkLabel(top, text=f"{p.get('used_formatted')} / {p.get('total_formatted')} ({p.get('percent')}%)", font=ctk.CTkFont(size=12), text_color=ACCENT_CYAN).pack(side="right")

            prog = ctk.CTkProgressBar(card, height=8, corner_radius=4)
            prog.set((p.get("percent", 0)) / 100.0)
            if p.get("percent", 0) > 85:
                prog.configure(progress_color=ACCENT_ROSE)
            prog.pack(fill="x", padx=12, pady=(0, 10))

    def _run_disk_check(self):
        if self.log_callback:
            self.log_callback("Running filesystem integrity scan (chkdsk/fsck)...")
        threading.Thread(target=lambda: check_disk(repair=False), daemon=True).start()

    # ---------------- Memory Tab ----------------
    def _build_mem_tab(self):
        tab = self.tab_mem
        tab.grid_columnconfigure((0, 1), weight=1)

        btn_bar = ctk.CTkFrame(tab, fg_color="transparent")
        btn_bar.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(btn_bar, text="RAM Usage & Top Processes", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(
            btn_bar,
            text="⚡ Trim Inactive Working Sets",
            command=self._trim_memory,
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            height=30,
        ).pack(side="right")

        self.proc_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.proc_scroll.pack(fill="both", expand=True, padx=10, pady=6)
        self._refresh_mem_tab()

    def _refresh_mem_tab(self):
        for w in self.proc_scroll.winfo_children():
            w.destroy()

        mem = check_memory()
        procs = mem.get("top_processes", [])

        # Header row
        hdr = ctk.CTkFrame(self.proc_scroll, fg_color="#131d2e", corner_radius=6)
        hdr.pack(fill="x", pady=2)
        ctk.CTkLabel(hdr, text="Process Name", font=ctk.CTkFont(size=11, weight="bold"), width=180, anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(hdr, text="PID", font=ctk.CTkFont(size=11, weight="bold"), width=70).pack(side="left")
        ctk.CTkLabel(hdr, text="RAM (MB)", font=ctk.CTkFont(size=11, weight="bold"), width=90).pack(side="left")
        ctk.CTkLabel(hdr, text="CPU %", font=ctk.CTkFont(size=11, weight="bold"), width=60).pack(side="left")

        for p in procs:
            row = ctk.CTkFrame(self.proc_scroll, fg_color=DARK_BG_CARD, corner_radius=6)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=p.get("name")[:24], font=ctk.CTkFont(size=11), width=180, anchor="w").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(row, text=str(p.get("pid")), font=ctk.CTkFont(size=11), width=70).pack(side="left", pady=4)
            ctk.CTkLabel(row, text=p.get("rss_formatted"), font=ctk.CTkFont(size=11), width=90, text_color=ACCENT_CYAN).pack(side="left", pady=4)
            ctk.CTkLabel(row, text=f"{p.get('cpu_percent')}%", font=ctk.CTkFont(size=11), width=60).pack(side="left", pady=4)

    def _trim_memory(self):
        if self.log_callback:
            self.log_callback("Trimming process working sets / freeing cache...")
        res = optimize_memory()
        if self.log_callback:
            self.log_callback(res.get("message", "Memory optimized."))
        self._refresh_mem_tab()

    # ---------------- Drivers Tab ----------------
    def _build_driver_tab(self):
        tab = self.tab_drv
        tab.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(bar, text="Installed Drivers & Hardware Devices", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(bar, text="🔄 Refresh Drivers", command=self._refresh_drivers, width=130, height=30).pack(side="right")

        self.drv_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.drv_scroll.pack(fill="both", expand=True, padx=10, pady=6)
        self._refresh_drivers()

    def _refresh_drivers(self):
        for w in self.drv_scroll.winfo_children():
            w.destroy()

        res = check_drivers()
        faulty = res.get("faulty_devices", [])

        if faulty:
            alert = ctk.CTkFrame(self.drv_scroll, fg_color="#450a0a", border_width=1, border_color="#ef4444", corner_radius=8)
            alert.pack(fill="x", pady=(0, 8))
            ctk.CTkLabel(alert, text=f"⚠️ {len(faulty)} Problematic Hardware Device(s) Detected!", font=ctk.CTkFont(size=12, weight="bold"), text_color="#fca5a5").pack(anchor="w", padx=10, pady=(6, 2))
            for dev in faulty:
                ctk.CTkLabel(alert, text=f"• {dev.get('name')}: {dev.get('problem_description')}", font=ctk.CTkFont(size=11), text_color="#fecaca").pack(anchor="w", padx=16, pady=1)

        drivers = res.get("drivers", [])
        for d in drivers[:30]:
            row = ctk.CTkFrame(self.drv_scroll, fg_color=DARK_BG_CARD, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=d.get("name", ""), font=ctk.CTkFont(size=11, weight="bold"), width=160, anchor="w").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(row, text=d.get("display_name", "")[:35], font=ctk.CTkFont(size=11), width=220, anchor="w").pack(side="left", pady=4)
            ctk.CTkLabel(row, text=d.get("state", "Running"), font=ctk.CTkFont(size=11), width=80, text_color=ACCENT_EMERALD).pack(side="right", padx=8, pady=4)

    # ---------------- Services Tab ----------------
    def _build_services_tab(self):
        tab = self.tab_svc
        tab.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(bar, text="System Services Manager", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(bar, text="🔄 Reload Services", command=self._refresh_services, width=130, height=30).pack(side="right")

        self.svc_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.svc_scroll.pack(fill="both", expand=True, padx=10, pady=6)
        self._refresh_services()

    def _refresh_services(self):
        for w in self.svc_scroll.winfo_children():
            w.destroy()

        services = list_services()
        for svc in services[:40]:
            row = ctk.CTkFrame(self.svc_scroll, fg_color=DARK_BG_CARD, corner_radius=6)
            row.pack(fill="x", pady=2)

            name = svc.get("name", "")
            status = svc.get("status", "")
            is_running = status.lower() in ("running", "active")

            ctk.CTkLabel(row, text=name[:24], font=ctk.CTkFont(size=11, weight="bold"), width=160, anchor="w").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(row, text=svc.get("display_name", name)[:30], font=ctk.CTkFont(size=11), width=200, anchor="w").pack(side="left", pady=4)

            status_lbl = ctk.CTkLabel(
                row,
                text=status.upper(),
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=ACCENT_EMERALD if is_running else "#94a3b8",
                width=80,
            )
            status_lbl.pack(side="left", padx=6, pady=4)

            # Action button
            action = "stop" if is_running else "start"
            btn = ctk.CTkButton(
                row,
                text="Stop" if is_running else "Start",
                width=60,
                height=24,
                font=ctk.CTkFont(size=10),
                fg_color="#ef4444" if is_running else ACCENT_EMERALD,
                hover_color="#dc2626" if is_running else "#059669",
                command=lambda s=name, a=action: self._toggle_service(s, a),
            )
            btn.pack(side="right", padx=8, pady=4)

    def _toggle_service(self, name: str, action: str):
        if self.log_callback:
            self.log_callback(f"Executing '{action}' on service '{name}'...")
        res = control_service(name, action)
        if self.log_callback:
            self.log_callback(f"Service {name} {action} result: {res.get('success')}")
        self._refresh_services()
