# sysmaint/config.py

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
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
    backup_dir: str = str(Path.home() / ".sysmaint" / "backups")
    lvm_vg: str = "vg0"


@dataclass
class ServicesConfig:
    enable: bool = True
    expected_services: list[str] = field(default_factory=list)


@dataclass
class CleanerConfig:
    clean_user_temp: bool = True
    clean_system_temp: bool = True
    clean_browser_cache: bool = True
    clean_system_logs: bool = True
    clean_package_cache: bool = True
    clean_thumbnails: bool = True


@dataclass
class NetworkConfig:
    ping_target: str = "1.1.1.1"
    flush_dns_on_optimize: bool = True


@dataclass
class UIConfig:
    theme: str = "dark"  # 'dark', 'light', 'system'
    accent_color: str = "blue"  # 'blue', 'green', 'dark-blue'
    auto_refresh_interval: int = 5


@dataclass
class SystemConfig:
    offline_mode: bool = False
    auto_yes: bool = False


@dataclass
class AIConfig:
    enabled: bool = False
    provider: str = "ollama"
    model: str = "qwen2.5-coder:7b"
    endpoint: str = "http://localhost:11434"
    timeout_seconds: int = 60


@dataclass
class SysMaintConfig:
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    malware: MalwareConfig = field(default_factory=MalwareConfig)
    repair: RepairConfig = field(default_factory=RepairConfig)
    services: ServicesConfig = field(default_factory=ServicesConfig)
    cleaner: CleanerConfig = field(default_factory=CleanerConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    ai: AIConfig = field(default_factory=AIConfig)

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
        clean_data = data.get("cleaner", {})
        net_data = data.get("network", {})
        ui_data = data.get("ui", {})
        sys_data = data.get("system", {})
        ai_data = data.get("ai", {})

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
                backup_dir=str(repair_data.get("backup_dir", str(Path.home() / ".sysmaint" / "backups"))),
                lvm_vg=str(repair_data.get("lvm_vg", "vg0")),
            ),
            services=ServicesConfig(
                enable=bool(serv_data.get("enable", True)),
                expected_services=[
                    str(s) for s in serv_data.get("expected_services", [])
                ],
            ),
            cleaner=CleanerConfig(
                clean_user_temp=bool(clean_data.get("clean_user_temp", True)),
                clean_system_temp=bool(clean_data.get("clean_system_temp", True)),
                clean_browser_cache=bool(clean_data.get("clean_browser_cache", True)),
                clean_system_logs=bool(clean_data.get("clean_system_logs", True)),
                clean_package_cache=bool(clean_data.get("clean_package_cache", True)),
                clean_thumbnails=bool(clean_data.get("clean_thumbnails", True)),
            ),
            network=NetworkConfig(
                ping_target=str(net_data.get("ping_target", "1.1.1.1")),
                flush_dns_on_optimize=bool(net_data.get("flush_dns_on_optimize", True)),
            ),
            ui=UIConfig(
                theme=str(ui_data.get("theme", "dark")),
                accent_color=str(ui_data.get("accent_color", "blue")),
                auto_refresh_interval=int(ui_data.get("auto_refresh_interval", 5)),
            ),
            system=SystemConfig(
                offline_mode=bool(sys_data.get("offline_mode", False)),
                auto_yes=bool(sys_data.get("auto_yes", False)),
            ),
            ai=AIConfig(
                enabled=bool(ai_data.get("enabled", False)),
                provider=str(ai_data.get("provider", "ollama")),
                model=str(ai_data.get("model", "qwen2.5-coder:7b")),
                endpoint=str(ai_data.get("endpoint", "http://localhost:11434")),
                timeout_seconds=int(ai_data.get("timeout_seconds", 60)),
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary representation."""
        data = asdict(self)
        # Convert Path objects to strings
        if self.logging.file:
            data["logging"]["file"] = str(self.logging.file)
        if self.malware.yara_rules_path:
            data["malware"]["yara_rules_path"] = str(self.malware.yara_rules_path)
        return data


def get_default_config_path() -> Path:
    """Return standard user config path."""
    if os.name == "nt":
        app_data = os.environ.get("APPDATA")
        base = Path(app_data) / "SysMaint" if app_data else Path.home() / ".sysmaint"
    else:
        base = Path.home() / ".config" / "sysmaint"
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.yaml"


def save_config(config: SysMaintConfig, path: Optional[str | Path] = None) -> Path:
    """Save configuration to YAML or JSON."""
    target_path = Path(path) if path else get_default_config_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    data = config.to_dict()
    if yaml is not None:
        target_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    else:
        target_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return target_path


def load_config(path: Optional[str | Path] = None) -> SysMaintConfig:
    """Load configuration from YAML or JSON file or default user location."""
    config_path = Path(path) if path else get_default_config_path()
    if not config_path.exists():
        return SysMaintConfig()

    text = config_path.read_text(encoding="utf-8")
    suffix = config_path.suffix.lower()

    data: Dict[str, Any] = {}
    if suffix in (".yaml", ".yml"):
        if yaml is not None:
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        if yaml is not None:
            try:
                data = yaml.safe_load(text) or {}
            except Exception:
                data = json.loads(text)
        else:
            data = json.loads(text)

    return SysMaintConfig.from_dict(data)