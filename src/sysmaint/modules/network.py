# sysmaint/modules/network.py

from __future__ import annotations

import logging
import platform
import socket
from typing import Any, List, Optional

import psutil

from ..utils.common import format_bytes, run_command
from ..utils.parsers import parse_ping_output

logger = logging.getLogger("sysmaint.network")


def get_network_interfaces() -> List[dict[str, Any]]:
    """
    Return all network adapters with IP addresses, MAC, status, and traffic stats.
    """
    interfaces = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    io_counters = psutil.net_io_counters(pernic=True)

    for iface_name, addr_list in addrs.items():
        stat = stats.get(iface_name)
        io = io_counters.get(iface_name)

        ipv4 = None
        ipv6 = None
        mac = None

        for addr in addr_list:
            if addr.family == socket.AF_INET:
                ipv4 = addr.address
            elif addr.family == socket.AF_INET6:
                ipv6 = addr.address
            elif getattr(psutil, "AF_LINK", None) and addr.family == psutil.AF_LINK:
                mac = addr.address

        is_up = stat.isup if stat else False
        speed = stat.speed if stat else 0

        # Skip virtual loopback if not active
        if iface_name.lower().startswith("loopback") and not is_up:
            continue

        interfaces.append({
            "name": iface_name,
            "ipv4": ipv4 or "N/A",
            "ipv6": ipv6 or "N/A",
            "mac": mac or "N/A",
            "is_up": is_up,
            "speed_mbps": speed,
            "bytes_sent_formatted": format_bytes(io.bytes_sent) if io else "0 B",
            "bytes_recv_formatted": format_bytes(io.bytes_recv) if io else "0 B",
        })

    return interfaces


def test_connectivity(target_host: str = "1.1.1.1") -> dict[str, Any]:
    """
    Test network latency and packet loss by pinging a host.
    """
    system = platform.system().lower()
    logger.info("Testing network latency to %s", target_host)

    count_flag = "-n" if system == "windows" else "-c"
    timeout_flag = "-w" if system == "windows" else "-W"
    timeout_val = "2000" if system == "windows" else "2"

    cmd = ["ping", count_flag, "3", timeout_flag, timeout_val, target_host]
    result = run_command(cmd, check=False)
    parsed = parse_ping_output(result.stdout)
    parsed["target"] = target_host
    return parsed


def flush_dns() -> dict[str, Any]:
    """
    Flush DNS resolver caches across Windows or Linux.
    """
    system = platform.system().lower()
    logger.info("Flushing DNS resolver cache on %s", system)

    if system == "windows":
        from ..utils.windows import flush_windows_dns
        success = flush_windows_dns()
        return {
            "success": success,
            "system": "windows",
            "message": "Flushed Windows DNS Resolver Cache successfully." if success else "Failed to flush DNS cache.",
        }

    if system == "linux":
        from ..utils.linux import flush_linux_dns
        success = flush_linux_dns()
        return {
            "success": success,
            "system": "linux",
            "message": "Flushed Linux DNS cache." if success else "Could not flush DNS (requires resolvectl/systemd-resolve).",
        }

    return {"success": False, "message": f"Unsupported platform: {system}"}


def get_listening_ports(limit: int = 50) -> List[dict[str, Any]]:
    """
    List active listening network sockets and their associated processes.
    """
    ports = []
    try:
        connections = psutil.net_connections(kind="inet")
        for conn in connections:
            if conn.status == psutil.CONN_LISTEN:
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
                proc_name = "System"
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        proc_name = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_name = f"PID {conn.pid}"

                ports.append({
                    "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                    "local_address": laddr,
                    "pid": conn.pid,
                    "process_name": proc_name,
                })
    except (psutil.AccessDenied, PermissionError):
        logger.debug("Access denied reading net_connections (run as admin for full port list)")

    return ports[:limit]


def reset_network_stack(dry_run: bool = False) -> dict[str, Any]:
    """Repair corrupted network stack (Winsock/TCP-IP reset on Windows, NetworkManager on Linux)."""
    system = platform.system().lower()
    if system == "windows":
        cmds = [
            ["ipconfig", "/flushdns"],
            ["netsh", "winsock", "reset"],
            ["netsh", "int", "ip", "reset"],
        ]
        if dry_run:
            return {"dry_run": True, "system": "windows", "commands": [" ".join(c) for c in cmds]}
        outputs = []
        for cmd in cmds:
            res = run_command(cmd, check=False)
            outputs.append({"command": " ".join(cmd), "returncode": res.returncode, "output": res.stdout.strip()})
        return {"system": "windows", "status": "reset_complete", "steps": outputs}

    if system == "linux":
        import shutil
        if shutil.which("systemctl"):
            cmd = ["systemctl", "restart", "NetworkManager"]
            if dry_run:
                return {"dry_run": True, "system": "linux", "commands": [" ".join(cmd)]}
            res = run_command(cmd, check=False)
            return {"system": "linux", "returncode": res.returncode, "output": res.stdout.strip()}
        return {"system": "linux", "error": "systemctl not available"}

    return {"error": f"Unsupported platform: {system}"}
