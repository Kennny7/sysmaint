# src/sysmaint/tui/themes.py

from __future__ import annotations

from textual.theme import Theme

OBSIDIAN_GOLD = Theme(
    name="obsidian-gold",
    primary="#facc15",      # Radiant gold/yellow outlines
    secondary="#f59e0b",    # Warm amber
    accent="#fde047",       # Bright highlight yellow
    foreground="#f8fafc",
    background="#090b10",   # Deep obsidian dark
    surface="#111520",
    panel="#171c2b",
    success="#4ade80",
    warning="#fbbf24",
    error="#f87171",
    dark=True,
)

AMBER_SLATE = Theme(
    name="amber-slate",
    primary="#ca8a04",      # Dark golden yellow
    secondary="#eab308",
    accent="#fde047",
    foreground="#f3f4f6",
    background="#18191f",   # Dark grey/charcoal
    surface="#1f2128",
    panel="#272a34",
    success="#4ade80",
    warning="#facc15",
    error="#fb7185",
    dark=True,
)

EMERALD_NOIR = Theme(
    name="emerald-noir",
    primary="#34d399",      # Radiant emerald
    secondary="#10b981",
    accent="#6ee7b7",
    foreground="#ecfdf5",
    background="#070b09",
    surface="#0e1612",
    panel="#14201a",
    success="#34d399",
    warning="#fbbf24",
    error="#fb7185",
    dark=True,
)

CYBER_COBALT = Theme(
    name="cyber-cobalt",
    primary="#22d3ee",      # Electric cyan
    secondary="#38bdf8",
    accent="#67e8f9",
    foreground="#f0f9ff",
    background="#080d1a",
    surface="#0f172a",
    panel="#16223d",
    success="#4ade80",
    warning="#facc15",
    error="#f87171",
    dark=True,
)

CATPPUCCIN_MOCHA = Theme(
    name="catppuccin-mocha",
    primary="#89b4fa",
    secondary="#74c7ec",
    accent="#94e2d5",
    foreground="#cdd6f4",
    background="#1e1e2e",
    surface="#181825",
    panel="#313244",
    success="#a6e3a1",
    warning="#f9e2af",
    error="#f38ba8",
    dark=True,
)

CUSTOM_THEMES = [
    OBSIDIAN_GOLD,
    AMBER_SLATE,
    EMERALD_NOIR,
    CYBER_COBALT,
    CATPPUCCIN_MOCHA,
]

THEME_CYCLE = [
    "obsidian-gold",
    "amber-slate",
    "emerald-noir",
    "cyber-cobalt",
    "catppuccin-mocha",
    "tokyo-night",
]
