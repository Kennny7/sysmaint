# sysmaint/gui/theme.py

from __future__ import annotations

import customtkinter as ctk

# Color Palette Definitions
DARK_BG_PRIMARY = "#0f172a"      # Slate 900
DARK_BG_SECONDARY = "#1e293b"    # Slate 800
DARK_BG_CARD = "#1e293b"         # Slate 800
DARK_BG_HOVER = "#334155"        # Slate 700
DARK_BORDER = "#334155"          # Slate 700

LIGHT_BG_PRIMARY = "#f8fafc"     # Slate 50
LIGHT_BG_SECONDARY = "#ffffff"   # White
LIGHT_BG_CARD = "#ffffff"        # White
LIGHT_BG_HOVER = "#f1f5f9"       # Slate 100
LIGHT_BORDER = "#e2e8f0"         # Slate 200

# Accent Colors
ACCENT_CYAN = "#38bdf8"          # Sky 400
ACCENT_BLUE = "#3b82f6"          # Blue 500
ACCENT_INDIGO = "#6366f1"        # Indigo 500
ACCENT_EMERALD = "#10b981"       # Emerald 500
ACCENT_AMBER = "#f59e0b"         # Amber 500
ACCENT_ROSE = "#ef4444"          # Rose 500

# Text Colors
TEXT_PRIMARY_DARK = "#f8fafc"
TEXT_SECONDARY_DARK = "#94a3b8"
TEXT_PRIMARY_LIGHT = "#0f172a"
TEXT_SECONDARY_LIGHT = "#64748b"


def init_theme(theme_mode: str = "dark", color_theme: str = "blue") -> None:
    """
    Initialize CustomTkinter visual appearance and defaults.
    """
    ctk.set_appearance_mode(theme_mode)
    ctk.set_default_color_theme(color_theme)


def get_health_color(score: int) -> str:
    """Return color hex code based on 0-100 health score."""
    if score >= 90:
        return ACCENT_EMERALD
    elif score >= 75:
        return ACCENT_CYAN
    elif score >= 50:
        return ACCENT_AMBER
    else:
        return ACCENT_ROSE
