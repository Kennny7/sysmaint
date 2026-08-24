"""SysMaint - Professional Cross-Platform System Maintenance Suite."""

__version__ = "2.0.0"
__author__ = "SysMaint Team"

from .config import SysMaintConfig, load_config, save_config

__all__ = ["SysMaintConfig", "load_config", "save_config", "__version__"]