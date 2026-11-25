<div align="center">

# SysMaint User Guide

**Version 3.0.0 (Sentinel Microservice) | Kennny7 Microservices**

A plain-English guide for both non-technical users and power users.

[Back to README](README.md)

</div>

---

## 1. What Is SysMaint?

SysMaint is a personal computer health, security, repair, and data recovery assistant for **Windows** and **Linux**. You can use it in three ways:

1. **Interactive Terminal UI (`sysmaint tui`)**: A keyboard-and-mouse terminal dashboard with tabs and buttons — no need to memorize commands.
2. **Command Line (`sysmaint ...`)**: Fast one-line commands for scanning, repairing, cleaning, or recovering files.
3. **Background Microservice (`sysmaint serve`)**: Runs as a local HTTP service (`http://127.0.0.1:8765`) so dashboards, scripts, or remote clients can talk to it.

> [!NOTE]
> SysMaint works **100% offline** by default for diagnostics, YARA malware scanning, disk/file repair, and data recovery. You only need internet access if you choose to download signature updates or use VirusTotal.

---

## 2. Easy Installation

### Option A: Using `uv` (Recommended, Fastest)

1. Install `uv` if you do not have it yet:
   - **Windows (PowerShell):**
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   - **Linux / macOS:**
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
2. Clone and sync SysMaint:
   ```bash
   git clone https://github.com/Kennny7/sysmaint.git
   cd sysmaint
   uv sync
   ```
3. Launch the interactive Terminal UI:
   ```bash
   uv run sysmaint tui
   ```

### Option B: Standard `pip`

```bash
git clone https://github.com/Kennny7/sysmaint.git
cd sysmaint
pip install .
sysmaint tui
```

---

## 3. Everyday Use Cases (Copy-Paste Examples)

### Case 1: "My PC feels slow — check everything safely"
Run a read-only smart health scan (does not change any files):
```bash
sysmaint smart-scan
```

### Case 2: "Windows files or updates seem corrupted"
Check system file integrity first (read-only):
```bash
sysmaint scan --integrity
```
Repair corrupted Windows system files (`DISM /RestoreHealth` + `sfc /scannow`) or Linux packages (run as Administrator / `sudo`):
```bash
sysmaint repair --files
```
If you are **offline** with a Windows installation ISO/WIM mounted at `D:\sources\install.wim`:
```bash
sysmaint repair --files --offline-source D:\sources\install.wim
```

### Case 3: "My internet / DNS is broken or acting weird"
Test connectivity and flush DNS:
```bash
sysmaint network ping --target 1.1.1.1
sysmaint network flush-dns
```
Full network stack reset (Winsock + TCP/IP reset on Windows, NetworkManager restart on Linux). Preview first with `--dry-run`:
```bash
sysmaint network reset --dry-run
sysmaint network reset
```

### Case 4: "I think I downloaded malware"
Run an offline local YARA + ClamAV scan on Downloads, Temp, and Startup folders:
```bash
sysmaint scan --yara --clamav --offline
```
Scan a specific suspicious folder:
```bash
sysmaint scan --yara --target "C:\Users\YourName\Downloads"
```

### Case 5: "I accidentally deleted a file or lost an unsaved document"
List items currently in your Recycle Bin (Windows) or Trash (Linux):
```bash
sysmaint recovery trash
```
Restore a specific deleted file to a safe folder:
```bash
sysmaint recovery restore --name "report.pdf" --dest "C:\Recovered"
```
Scan for unsaved Word/Excel/LibreOffice/temp recovery drafts:
```bash
sysmaint recovery temp
```
List Windows Volume Shadow Copies (or Linux snapshots):
```bash
sysmaint recovery shadows
```
Carve lost files (`pdf`, `png`, `jpg`, `zip`, `sqlite`) from a disk image into a **separate** folder:
```bash
sysmaint recovery carve --source "D:\images\usb.img" --dest "E:\carved_output" --types pdf png jpg
```

> [!WARNING]
> Always set `--dest` to a **different drive or folder** than `--source` when carving files so you never overwrite unallocated data.

---

## 4. Using the Microservice & Terminal Client UI

Start the local microservice in one terminal:
```bash
sysmaint serve --host 127.0.0.1 --port 8765
```
Verify the microservice is healthy:
```bash
curl http://127.0.0.1:8765/health
```
Open the interactive API documentation in your browser at:
`http://127.0.0.1:8765/docs`

Connect the Terminal Client UI to the running microservice:
```bash
sysmaint tui --server http://127.0.0.1:8765
```
