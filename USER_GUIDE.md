<div align="center">

# SysMaint User Guide

**Version 3.0.0 (Sentinel Microservice) | Kennny7 Microservices**

A plain-English guide for both non-technical users and power users.

[Back to README](README.md)

</div>

---

## 1. What Is SysMaint?

SysMaint is a personal computer health, security, repair, and data recovery assistant for **Windows** and **Linux**. You can use it in four ways:

1. **Interactive Terminal UI (`sysmaint tui`)**: A keyboard-and-mouse terminal dashboard with tabs and buttons — no need to memorize commands.
2. **Command Line (`sysmaint ...`)**: Fast one-line commands for scanning, repairing, cleaning, or recovering files.
3. **Background Microservice (`sysmaint serve`)**: Runs as a local HTTP service (`http://127.0.0.1:8765`) so dashboards, scripts, or remote clients can talk to it.
4. **Optional Local AI Guard (`sysmaint ai`)**: Connects to a local **Ollama** 7B model (`qwen2.5-coder:7b`) on your own computer so you can describe a problem in plain English and get safe repair commands.

> [!NOTE]
> SysMaint works **100% offline** by default for diagnostics, YARA malware scanning, disk/file repair, and data recovery. You only need internet access if you choose to download updates, use VirusTotal, or pull the optional Ollama AI model for the first time.

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

---

## 5. Optional AI Guard Mode (Local Ollama 7B)

AI Mode is **100% optional**. It runs completely on your own machine using **Ollama** and the **`qwen2.5-coder:7b`** model (chosen specifically because it excels at OS diagnostics, PowerShell/Bash repair commands, and structured JSON output while fitting comfortably on consumer hardware).

### Step 1: Check If Ollama or Docker Is Already Working

Run SysMaint's built-in checker:
```bash
sysmaint ai status
```

Or check manually in your terminal:

<details>
<summary>Check Ollama directly (Windows & Linux)</summary>

```bash
# 1. Check if the Ollama CLI is installed
ollama --version

# 2. Check if the Ollama server is running and responding
curl http://localhost:11434/api/tags

# 3. Check which models are already downloaded
ollama list
```

If `curl` returns a JSON list of models (and shows `qwen2.5-coder:7b`), you are ready!

</details>

<details>
<summary>Check or run Ollama using Docker (if you prefer containers)</summary>

```bash
# 1. Check if Docker is installed and running
docker --version
docker ps

# 2. Start Ollama inside a Docker container (CPU)
docker run -d --name sysmaint-ollama -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama

# 3. (Optional) Start Ollama with NVIDIA GPU support
docker run -d --gpus=all --name sysmaint-ollama -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama

# 4. Pull the OS Guard model inside the container
docker exec -it sysmaint-ollama ollama pull qwen2.5-coder:7b

# 5. Verify the container API is responding
curl http://localhost:11434/api/tags
```

</details>

### Step 2: Install Ollama & Pull the Model (If Missing)

- **Windows:**
  ```powershell
  winget install Ollama.Ollama
  ollama pull qwen2.5-coder:7b
  ```
- **Linux:**
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ollama serve &
  ollama pull qwen2.5-coder:7b
  ```
- Or let SysMaint pull it for you once Ollama is installed:
  ```bash
  sysmaint ai pull
  ```

### Step 3: Ask the AI Guard About a Problem

```bash
# Get a diagnosis and recommended commands (safe, read-only preview)
sysmaint ai ask "My Wi-Fi connects but websites do not load after using a VPN"
```

If you review the recommended commands and want SysMaint to execute the safe ones automatically:
```bash
sysmaint ai ask "My Wi-Fi connects but websites do not load" --execute --yes
```

> [!IMPORTANT]
> SysMaint blocks catastrophic commands (such as `rm -rf /` or `format C:`) automatically, and never executes AI-suggested commands unless you explicitly pass both `--execute` and `--yes`.
