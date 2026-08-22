# sysmaint/config.py

from __future__ import annotations

import json
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: Optional[Path] = None


@dataclass
class DiagnosticsConfig:
    disk: bool = True
    memory: bool = True
    services: bool = True
    drivers: bool = False


@dataclass
class MalwareConfig:
    use_clamav: bool = True
    use_yara: bool = True
    yara_rules_path: Optional[Path] = None
    use_virustotal: bool = False
    vt_api_key: str = ""


@dataclass
class RepairConfig:
    auto_create_restore_point: bool = True
    backup_dir: str = "/var/log/sysmaint/backups"
    lvm_vg: str = "vg0"


@dataclass
class ServicesConfig:
    enable: bool = True
    expected_services: list[str] = field(default_factory=list)


@dataclass
class SystemConfig:
    offline_mode: bool = False
    auto_yes: bool = False


@dataclass
class SysMaintConfig:
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    malware: MalwareConfig = field(default_factory=MalwareConfig)
    repair: RepairConfig = field(default_factory=RepairConfig)
    services: ServicesConfig = field(default_factory=ServicesConfig)
    system: SystemConfig = field(default_factory=SystemConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SysMaintConfig":
        """Create a config instance from a dict, applying defaults."""
        if not data:
            return cls()

        log_data = data.get("logging", {})
        diag_data = data.get("diagnostics", {})
        mal_data = data.get("malware", {})
        repair_data = data.get("repair", {})
        serv_data = data.get("services", {})
        sys_data = data.get("system", {})

        return cls(
            logging=LoggingConfig(
                level=str(log_data.get("level", "INFO")).upper(),
                file=Path(log_data["file"]) if log_data.get("file") else None,
            ),
            diagnostics=DiagnosticsConfig(
                disk=bool(diag_data.get("disk", True)),
                memory=bool(diag_data.get("memory", True)),
                services=bool(diag_data.get("services", True)),
                drivers=bool(diag_data.get("drivers", False)),
            ),
            malware=MalwareConfig(
                use_clamav=bool(mal_data.get("use_clamav", True)),
                use_yara=bool(mal_data.get("use_yara", True)),
                yara_rules_path=(
                    Path(mal_data["yara_rules_path"])
                    if mal_data.get("yara_rules_path")
                    else None
                ),
                use_virustotal=bool(mal_data.get("use_virustotal", False)),
                vt_api_key=str(mal_data.get("vt_api_key", "")),
            ),
            repair=RepairConfig(
                auto_create_restore_point=bool(
                    repair_data.get("auto_create_restore_point", True)
                ),
                backup_dir=str(repair_data.get("backup_dir", "/var/log/sysmaint/backups")),
                lvm_vg=str(repair_data.get("lvm_vg", "vg0")),
            ),
            services=ServicesConfig(
                enable=bool(serv_data.get("enable", True)),
                expected_services=[
                    str(s) for s in serv_data.get("expected_services", [])
                ],
            ),
            system=SystemConfig(
                offline_mode=bool(sys_data.get("offline_mode", False)),
                auto_yes=bool(sys_data.get("auto_yes", False)),
            ),
        )


def load_config(path: str | Path) -> SysMaintConfig:
    """Load configuration from YAML or JSON file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    text = config_path.read_text(encoding="utf-8")
    suffix = config_path.suffix.lower()

    data: Dict[str, Any] = {}
    if suffix in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML is required to read YAML config files")
        data = yaml.safe_load(text) or {}
    elif suffix == ".json":
        data = json.loads(text)
    else:
        # Try YAML first, fallback to JSON
        if yaml is not None:
            try:
                data = yaml.safe_load(text) or {}
            except Exception:
                data = json.loads(text)
        else:
            data = json.loads(text)

    return SysMaintConfig.from_dict(data)