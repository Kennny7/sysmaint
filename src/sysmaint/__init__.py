"""SysMaint - Cross-Platform System Maintenance, Security & Recovery Microservice."""

__version__ = "3.0.0"
__codename__ = "Sentinel Microservice"
__brand__ = "Kennny7 Microservices"
__author__ = "Kennny7"

from .config import SysMaintConfig, load_config, save_config

__all__ = [
    "SysMaintConfig",
    "load_config",
    "save_config",
    "__version__",
    "__codename__",
    "__brand__",
]
