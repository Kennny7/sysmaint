# Changelog

All notable changes to **SysMaint** by **Kennny7 Microservices** are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [3.0.0] - Sentinel Microservice (2026-11-25)

### Added
- **Microservice Architecture (`sysmaint serve` / `sysmaint-serve`)**: FastAPI + Uvicorn HTTP microservice with OpenAPI docs at `/docs`, `/health`, `/v1/sysinfo`, `/v1/smart-scan`, `/v1/diagnose`, `/v1/scan`, `/v1/repair`, `/v1/recovery/*`, and `/v1/ai/*`, plus `X-Powered-By: Kennny7 Microservices` service headers.
- **Interactive Terminal Client UI (`sysmaint tui` / `sysmaint-tui`)**: Textual + Rich dark-slate/cyan TUI with live CPU, RAM, and Disk telemetry, 5 tabbed workspaces, and optional remote microservice client mode (`--server`).
- **Data Recovery Engine (`sysmaint recovery`)**: Recycle Bin / FreeDesktop Trash inspection and restoration, Windows Volume Shadow Copy (`vssadmin`) & Linux snapshot listing, Office/LibreOffice/temp auto-recovery draft scanning, and safe read-only file signature carving (`pdf`, `png`, `jpg`, `zip`, `sqlite`).
- **Network Stack & Offline Integrity Repair**: Added `network reset` (`netsh winsock reset` / `netsh int ip reset` / `NetworkManager` restart) and `--offline-source` WIM/ESD support for DISM.
- **Modern `uv` Packaging**: Migrated to `src/sysmaint/` layout with `hatchling`, `uv` dependency groups, and `pytest` suite covering recovery, disk, and microservice endpoints.

## [2.0.0] - Legacy Toolkit
- Cross-platform CLI and CustomTkinter GUI for diagnostics, malware scanning (ClamAV, YARA, VirusTotal), system integrity (`DISM`/`SFC`/`dpkg`/`rpm`), junk cleaning, backup/restore, and scheduling.
