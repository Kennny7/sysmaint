# src/sysmaint/service/server.py

from __future__ import annotations

import platform
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from .. import __brand__, __codename__, __version__
from ..config import SysMaintConfig, load_config
from ..modules import (
    ai_assistant,
    disk,
    drivers,
    integrity,
    malware,
    memory,
    network,
    optimizer,
    recovery,
    security,
    services,
    sysinfo,
)

_START_TIME = time.time()


class DiagnoseRequest(BaseModel):
    disk: bool = True
    memory: bool = True
    services: bool = False
    drivers: bool = False


class ScanRequest(BaseModel):
    yara: bool = True
    clamav: bool = False
    integrity: bool = True
    offline: bool = True
    target: Optional[str] = None


class RepairRequest(BaseModel):
    disk: bool = False
    files: bool = False
    services: bool = False
    network: bool = False
    offline_source: Optional[str] = None
    dry_run: bool = True


class TrashRestoreRequest(BaseModel):
    name: str
    destination: Optional[str] = None
    dry_run: bool = False


class CarveRequest(BaseModel):
    source_path: str
    output_dir: str
    file_types: Optional[list[str]] = None
    max_files: int = Field(default=50, ge=1, le=500)
    dry_run: bool = True


class AIAssistRequest(BaseModel):
    problem: str
    model: str = ai_assistant.RECOMMENDED_MODEL
    endpoint: str = ai_assistant.DEFAULT_ENDPOINT
    execute: bool = False
    auto_confirm: bool = False


def create_app(config: Optional[SysMaintConfig] = None) -> FastAPI:
    """Create the SysMaint Sentinel FastAPI microservice."""
    cfg = config or load_config()
    app = FastAPI(
        title="SysMaint Sentinel Microservice",
        description=(
            f"Cross-Platform System Maintenance, Security, Data Recovery & AI Guard API "
            f"by {__brand__}."
        ),
        version=__version__,
    )

    @app.middleware("http")
    async def add_brand_header(request: Request, call_next: Any):
        response = await call_next(request)
        response.headers["X-Powered-By"] = __brand__
        response.headers["X-Service-Version"] = __version__
        return response

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "sysmaint",
            "codename": __codename__,
            "version": __version__,
            "brand": __brand__,
            "platform": platform.system(),
            "uptime_seconds": round(time.time() - _START_TIME, 2),
        }

    @app.get("/v1/sysinfo")
    def get_sysinfo() -> dict[str, Any]:
        return {"sysinfo": sysinfo.get_system_specs()}

    @app.get("/v1/smart-scan")
    def get_smart_scan() -> dict[str, Any]:
        return {"smart_scan": optimizer.run_smart_scan(cfg)}

    @app.get("/v1/security")
    def get_security() -> dict[str, Any]:
        return {"security": security.audit_security_posture()}

    @app.post("/v1/diagnose")
    def run_diagnose(req: DiagnoseRequest) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if req.disk:
            out["disk"] = disk.check_disk(repair=False)
        if req.memory:
            out["memory"] = memory.check_memory()
        if req.services:
            out["services"] = services.list_services()
        if req.drivers:
            out["drivers"] = drivers.check_drivers()
        return out

    @app.post("/v1/scan")
    def run_scan(req: ScanRequest) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if req.integrity:
            out["integrity"] = integrity.check_integrity(repair=False)
        if req.yara or req.clamav:
            mal_cfg = malware.MalwareConfig(
                use_clamav=req.clamav,
                use_yara=req.yara,
                yara_rules_path=cfg.malware.yara_rules_path,
                use_virustotal=False,
                vt_api_key="",
            )
            out["malware"] = malware.scan(
                mal_cfg,
                target=Path(req.target) if req.target else None,
                offline=req.offline,
                quick_scan=req.target is None,
            )
        return out

    @app.post("/v1/repair")
    def run_repair(req: RepairRequest) -> dict[str, Any]:
        out: dict[str, Any] = {"dry_run": req.dry_run}
        if req.disk:
            out["disk"] = (
                {"dry_run": "chkdsk /f or fsck -y"}
                if req.dry_run
                else disk.check_disk(repair=True)
            )
        if req.files:
            out["integrity"] = (
                {"dry_run": "DISM /RestoreHealth and SFC /scannow"}
                if req.dry_run
                else integrity.check_integrity(repair=True, offline_source=req.offline_source)
            )
        if req.services:
            out["services"] = (
                {"dry_run": "ensure expected services"}
                if req.dry_run
                else services.ensure_expected_services(cfg.services.expected_services)
            )
        if req.network:
            out["network"] = network.reset_network_stack(dry_run=req.dry_run)
        return out

    @app.get("/v1/recovery/trash")
    def api_list_trash(limit: int = 50) -> dict[str, Any]:
        return recovery.list_trash_items(limit=limit)

    @app.post("/v1/recovery/trash/restore")
    def api_restore_trash(req: TrashRestoreRequest) -> dict[str, Any]:
        return recovery.restore_trash_item(
            name=req.name,
            destination=Path(req.destination) if req.destination else None,
            dry_run=req.dry_run,
        )

    @app.get("/v1/recovery/shadows")
    def api_list_shadows() -> dict[str, Any]:
        return recovery.list_shadow_copies()

    @app.get("/v1/recovery/temp")
    def api_scan_temp(limit: int = 50) -> dict[str, Any]:
        return recovery.scan_recoverable_temp_files(limit=limit)

    @app.post("/v1/recovery/carve")
    def api_carve(req: CarveRequest) -> dict[str, Any]:
        return recovery.carve_recoverable_files(
            source_path=Path(req.source_path),
            output_dir=Path(req.output_dir),
            file_types=req.file_types,
            max_files=req.max_files,
            dry_run=req.dry_run,
        )

    @app.get("/v1/ai/status")
    def api_ai_status(
        endpoint: str = ai_assistant.DEFAULT_ENDPOINT,
        model: str = ai_assistant.RECOMMENDED_MODEL,
    ) -> dict[str, Any]:
        return ai_assistant.check_ollama_environment(endpoint=endpoint, model=model)

    @app.post("/v1/ai/assist")
    def api_ai_assist(req: AIAssistRequest) -> dict[str, Any]:
        return ai_assistant.analyze_problem(
            problem_description=req.problem,
            endpoint=req.endpoint,
            model=req.model,
            execute=req.execute,
            auto_confirm=req.auto_confirm,
        )

    return app


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Launch the SysMaint microservice with Uvicorn."""
    import uvicorn

    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")
