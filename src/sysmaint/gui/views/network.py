# sysmaint/gui/views/network.py

from __future__ import annotations

import threading
from collections.abc import Callable

import customtkinter as ctk

from ...config import SysMaintConfig
from ...modules.network import (
    flush_dns,
    get_network_interfaces,
    test_connectivity,
)
from ...theme import ACCENT_CYAN, ACCENT_EMERALD, DARK_BG_CARD, DARK_BORDER
from ..components.cards import MetricCard, SectionHeader


class NetworkView(ctk.CTkScrollableFrame):
    """Network Diagnostics, DNS Cache Flush, and Port Viewer."""

    def __init__(self, master, config: SysMaintConfig, log_callback: Callable | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config = config
        self.log_callback = log_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Header
        self.header = SectionHeader(
            self,
            title="Network Diagnostics & DNS Tools",
            subtitle="Analyze network adapter performance, test latency, flush DNS resolver caches, and inspect listening sockets",
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        # 2. Latency & Ping Card
        self.ping_card = MetricCard(
            self,
            title="Internet Latency",
            value="-- ms",
            subtitle="Ready to test ping",
            icon="🌐",
            accent_color=ACCENT_CYAN,
        )
        self.ping_card.grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=(0, 15))

        # 3. DNS Flush Action Card
        self.dns_card = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.dns_card.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(0, 15))

        ctk.CTkLabel(
            self.dns_card,
            text="⚡ DNS Resolver Cache",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            self.dns_card,
            text="Flush DNS entries to fix website resolution or stale IP records.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=16, pady=(0, 10))

        self.btn_dns = ctk.CTkButton(
            self.dns_card,
            text="🧹 Flush DNS Cache",
            command=self.trigger_flush_dns,
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            width=160,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_dns.pack(anchor="w", padx=16, pady=(0, 12))

        # 4. Latency Test Controls Frame
        self.test_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.test_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.test_frame,
            text="🔍 Network Latency & Connectivity Test",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        test_bar = ctk.CTkFrame(self.test_frame, fg_color="transparent")
        test_bar.pack(fill="x", padx=16, pady=(0, 14))

        self.entry_host = ctk.CTkEntry(test_bar, width=200, placeholder_text="1.1.1.1 or google.com")
        self.entry_host.insert(0, "1.1.1.1")
        self.entry_host.pack(side="left", padx=(0, 10))

        self.btn_ping = ctk.CTkButton(
            test_bar,
            text="📡 Test Ping",
            command=self.run_ping_test,
            width=120,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_ping.pack(side="left")

        # 5. Network Adapters List
        self.adapters_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=DARK_BORDER, fg_color=DARK_BG_CARD)
        self.adapters_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            self.adapters_frame,
            text="🔌 Active Network Interfaces",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self.adapters_container = ctk.CTkFrame(self.adapters_frame, fg_color="transparent")
        self.adapters_container.pack(fill="x", padx=16, pady=(0, 12))

        self.refresh_adapters()

    def run_ping_test(self):
        target = self.entry_host.get().strip() or "1.1.1.1"
        if self.log_callback:
            self.log_callback(f"Pinging {target}...")
        self.btn_ping.configure(state="disabled")

        def _worker():
            res = test_connectivity(target)
            self.after(0, lambda: self._apply_ping(res))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_ping(self, res: dict):
        self.btn_ping.configure(state="normal")
        lat = res.get("avg_latency_ms")
        loss = res.get("packet_loss_percent", 0)

        if lat is not None:
            self.ping_card.update_values(f"{lat} ms", f"Packet loss: {loss}%")
        else:
            self.ping_card.update_values("Unreachable", f"Packet loss: {loss}%")

        if self.log_callback:
            self.log_callback(f"Ping result for {res.get('target')}: {lat} ms average, {loss}% loss.")

    def trigger_flush_dns(self):
        if self.log_callback:
            self.log_callback("Flushing DNS resolver cache...")
        res = flush_dns()
        if self.log_callback:
            self.log_callback(res.get("message", "Flushed DNS cache."))

    def refresh_adapters(self):
        for w in self.adapters_container.winfo_children():
            w.destroy()

        ifaces = get_network_interfaces()
        for iface in ifaces:
            row = ctk.CTkFrame(self.adapters_container, fg_color="#131d2e", corner_radius=8)
            row.pack(fill="x", pady=3)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", padx=10, pady=6)

            status_txt = "🟢 Connected" if iface.get("is_up") else "⚪ Disconnected"
            ctk.CTkLabel(left, text=f"{iface.get('name')}  ({status_txt})", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(left, text=f"IPv4: {iface.get('ipv4')}  |  MAC: {iface.get('mac')}", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w")

            right = ctk.CTkFrame(row, fg_color="transparent")
            right.pack(side="right", padx=10, pady=6)
            ctk.CTkLabel(right, text=f"Sent: {iface.get('bytes_sent_formatted')}  |  Recv: {iface.get('bytes_recv_formatted')}", font=ctk.CTkFont(size=11), text_color=ACCENT_CYAN).pack(anchor="e")
