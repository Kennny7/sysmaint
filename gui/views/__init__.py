# sysmaint/gui/views/__init__.py

from .backup import BackupView
from .cleaner import CleanerView
from .dashboard import DashboardView
from .diagnostics import DiagnosticsView
from .integrity import IntegrityView
from .malware import MalwareView
from .network import NetworkView
from .security import SecurityView
from .settings import SettingsView
from .startup import StartupView

__all__ = [
    "DashboardView",
    "CleanerView",
    "DiagnosticsView",
    "IntegrityView",
    "MalwareView",
    "StartupView",
    "NetworkView",
    "SecurityView",
    "BackupView",
    "SettingsView",
]
