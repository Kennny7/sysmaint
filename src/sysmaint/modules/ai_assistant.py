# src/sysmaint/modules/ai_assistant.py

from __future__ import annotations

import json
import logging
import platform
import re
import shutil
from typing import Any, Optional

import httpx

from ..utils.common import run_command

logger = logging.getLogger("sysmaint.ai")

RECOMMENDED_MODEL = "qwen2.5-coder:7b"
FALLBACK_MODEL = "llama3.1:8b"
DEFAULT_ENDPOINT = "http://localhost:11434"

# Safety guardrails against catastrophic commands
_BLOCKED_PATTERNS = (
    r"\brm\s+-rf\s+/\s*$",
    r"\bmkfs\.",
    r"\bformat\s+[a-z]:",
    r"\bdel\s+/[fsq]+\s+[a-z]:\\\*",
    r":\(\)\{\s*:\|:&\s*\};:",
)


def is_command_safe(command: str) -> bool:
    """Reject obviously catastrophic command patterns."""
    lowered = command.strip().lower()
    if not lowered:
        return False
    return not any(re.search(pat, lowered) for pat in _BLOCKED_PATTERNS)


def build_setup_guide(
    ollama_installed: bool,
    docker_installed: bool,
    server_running: bool,
    model_ready: bool,
    model: str = RECOMMENDED_MODEL,
) -> list[str]:
    """Generate clear, beginner-friendly setup steps for missing AI components."""
    steps: list[str] = []
    system = platform.system().lower()

    if not ollama_installed and not server_running:
        if system == "windows":
            steps.append(
                "1. Install Ollama on Windows: winget install Ollama.Ollama "
                "(or download from https://ollama.com/download/windows)"
            )
        else:
            steps.append("1. Install Ollama on Linux: curl -fsSL https://ollama.com/install.sh | sh")

        if docker_installed:
            steps.append(
                "   (Alternative via Docker): docker run -d --name sysmaint-ollama "
                "-p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama"
            )
        else:
            steps.append(
                "   (Optional Docker option): Install Docker Desktop / Docker Engine, then run: "
                "docker run -d --name sysmaint-ollama -p 11434:11434 ollama/ollama"
            )

    if not server_running:
        steps.append("2. Start the Ollama service: ollama serve  (or launch the Ollama desktop app)")

    if not model_ready:
        steps.append(
            f"3. Download the OS Guard model (~4.7 GB): ollama pull {model} "
            f"(alternative: ollama pull {FALLBACK_MODEL})"
        )
        steps.append("4. Verify it works: ollama list  and  curl http://localhost:11434/api/tags")

    if not steps:
        steps.append(f"All set! Ollama is running and '{model}' is ready.")

    return steps


def check_ollama_environment(
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = RECOMMENDED_MODEL,
) -> dict[str, Any]:
    """Check whether Ollama, Docker, the local API server, and the target 7-8B model are ready."""
    ollama_bin = shutil.which("ollama")
    docker_bin = shutil.which("docker")
    server_running = False
    available_models: list[str] = []
    model_ready = False
    error_detail: Optional[str] = None

    try:
        resp = httpx.get(f"{endpoint.rstrip('/')}/api/tags", timeout=3.0)
        if resp.status_code == 200:
            server_running = True
            payload = resp.json()
            available_models = [m.get("name", "") for m in payload.get("models", []) if m.get("name")]
            model_base = model.split(":")[0]
            model_ready = any(
                m == model or m.startswith(f"{model_base}:") for m in available_models
            )
    except Exception as exc:
        error_detail = str(exc)

    setup_guide = build_setup_guide(
        ollama_installed=ollama_bin is not None,
        docker_installed=docker_bin is not None,
        server_running=server_running,
        model_ready=model_ready,
        model=model,
    )

    return {
        "ready": server_running and model_ready,
        "endpoint": endpoint,
        "recommended_model": model,
        "fallback_model": FALLBACK_MODEL,
        "ollama_cli_installed": ollama_bin is not None,
        "docker_cli_installed": docker_bin is not None,
        "server_running": server_running,
        "model_ready": model_ready,
        "available_models": available_models,
        "error": error_detail if not server_running else None,
        "setup_guide": setup_guide,
    }


def pull_model(model: str = RECOMMENDED_MODEL) -> dict[str, Any]:
    """Pull the recommended Ollama model using the local ollama CLI."""
    if not shutil.which("ollama"):
        return {
            "error": "Ollama CLI not found. Install Ollama first.",
            "setup_guide": build_setup_guide(False, shutil.which("docker") is not None, False, False, model),
        }
    res = run_command(["ollama", "pull", model], check=False)
    return {
        "model": model,
        "returncode": res.returncode,
        "success": res.returncode == 0,
        "output": res.stdout.strip() or res.stderr.strip(),
    }


def analyze_problem(
    problem_description: str,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = RECOMMENDED_MODEL,
    execute: bool = False,
    auto_confirm: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """
    Ask the local 7-8B Ollama OS Guard model to diagnose a user-described problem
    and recommend safe SysMaint or OS repair commands.
    """
    if not problem_description.strip():
        return {"error": "Please describe the system problem you want analyzed."}

    env = check_ollama_environment(endpoint=endpoint, model=model)
    if not env["ready"]:
        return {
            "error": "Local Ollama AI Guard is not ready yet.",
            "environment": env,
            "setup_guide": env["setup_guide"],
        }

    os_name = f"{platform.system()} {platform.release()}"
    system_prompt = (
        "You are SysMaint Sentinel, an expert Windows & Linux OS repair, security, and data recovery guard. "
        f"The host OS is {os_name}. "
        "Given a user problem description, respond ONLY with valid JSON containing:\n"
        '{\n'
        '  "diagnosis": "short plain-English explanation of likely cause",\n'
        '  "risk_level": "low|medium|high",\n'
        '  "sysmaint_action": "optional sysmaint subcommand like diagnose --all, repair --files, network flush-dns, scan --yara, or recovery trash",\n'
        '  "commands": [{"cmd": "exact shell command", "purpose": "what it does", "requires_admin": true}],\n'
        '  "warning": "safety advice before running"\n'
        '}\n'
        "Prefer read-only diagnostics first and safe built-in OS tools (DISM, SFC, chkdsk, netsh, fsck, journalctl)."
    )

    try:
        resp = httpx.post(
            f"{endpoint.rstrip('/')}/api/generate",
            json={
                "model": model,
                "system": system_prompt,
                "prompt": problem_description,
                "stream": False,
                "format": "json",
            },
            timeout=float(timeout),
        )
        resp.raise_for_status()
        raw_text = resp.json().get("response", "{}")
        plan = json.loads(raw_text)
    except Exception as exc:
        return {"error": f"AI inference failed: {exc}", "environment": env}

    commands = plan.get("commands", [])
    executed_results: list[dict[str, Any]] = []

    if execute and commands:
        if not auto_confirm:
            return {
                "model": model,
                "plan": plan,
                "executed": False,
                "note": "Pass --yes (or confirm in TUI/API) to execute the recommended commands.",
            }
        for item in commands:
            cmd_str = str(item.get("cmd", "")).strip()
            if not is_command_safe(cmd_str):
                executed_results.append({"cmd": cmd_str, "skipped": True, "reason": "Blocked by safety policy"})
                continue
            res = run_command(cmd_str, shell=True, check=False)
            executed_results.append(
                {
                    "cmd": cmd_str,
                    "returncode": res.returncode,
                    "output": (res.stdout or res.stderr)[:1500],
                }
            )

    return {
        "model": model,
        "os": os_name,
        "plan": plan,
        "executed": execute and auto_confirm,
        "execution_results": executed_results,
    }
