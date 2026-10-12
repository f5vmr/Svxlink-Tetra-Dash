#!/usr/bin/env python3

"""
Runtime monitoring helpers for SvxLink-Dash-V4.1.

Read-only status collection only.
No control functions belong here.
"""

from pathlib import Path
import subprocess
import time
import re 
from services.svxlink_service import svxlink_status
from services.log_service import (
    get_svxlink_log_path,
    read_recent_svxlink_log_lines,
)

UPTIME_FILE = Path("/proc/uptime")


def get_system_uptime():
    """
    Return human-readable system uptime.
    """

    try:
        uptime_seconds = float(
            UPTIME_FILE.read_text().split()[0]
        )

    except Exception:
        return "unknown"

    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    parts.append(f"{minutes}m")

    return " ".join(parts)


def get_connected_reflector(model=None):
    """
    Determine reflector connection state from recent SvxLink log lines.

    The latest relevant ReflectorLogic event wins.
    """

    reflector_name = "Connected"

    if model:
        candidate = (
            model.get("reflector", {})
            .get("name")
        )

        if candidate and str(candidate).strip().lower() != "none":
            reflector_name = str(candidate).strip()

    lines = read_recent_svxlink_log_lines(800)

    if not lines:
        return "unknown"

    connected_terms = (
        "authentication ok",
        "connected to",
        "connection established",
        "reflector connected",
    )

    disconnected_terms = (
        "disconnected",
        "connection failed",
        "connection lost",
        "server closed connection",
        "authentication failed",
    )

    for line in reversed(lines[-800:]):

        lower = line.lower()

        if "reflectorlogic" not in lower:
            continue

        if any(term in lower for term in disconnected_terms):
            return "not connected"

        if any(term in lower for term in connected_terms):
            return reflector_name

    return "not connected"


def get_radio_state(selected_port="1"):
        """
        Determine current radio state from recent SvxLink log lines.
    
        TX state is detected from either Tx1 messages.
        RX/input state is detected from Rx1 squelch messages.
        """

        if svxlink_status() != "active":
            return {
                "label": "Stopped",
                "input": "Unknown",
                "class": "radio-standby",
                "tx": False,
                "rx": False,
            }
        tx_active = False
        rx_open = False
        selected_port = str(selected_port or "1")
        rx_name = f"rx{selected_port}:"
        tx_name = f"tx{selected_port}:"

        lines = read_recent_svxlink_log_lines(300)
        # Ignore radio activity from an earlier SvxLink run.
        for index in range(len(lines) - 1, -1, -1):
            lower = lines[index].lower()
            if any(marker in lower for marker in (
                "notice: initialization done. starting main application",
                "notice: sigterm received. shutting down application",
                "notice: exiting",
            )):
                lines = lines[index + 1:]
                break

        if not lines:
            return {
                "label": "Listening",
                "input": "Unknown",
                "class": "radio-standby",
                "tx": False,
                "rx": False,
            }
        for line in reversed(lines[-300:]):
            lower = line.lower()
            if tx_name not in lower:
                continue
            if "turning the transmitter off" in lower:
                tx_active = False
                break
            if "turning the transmitter on" in lower:
                tx_active = True
                break

        for line in reversed(lines[-300:]):
            lower = line.lower()

            if f"{rx_name} the squelch is closed" in lower:
                rx_open = False
                break

            if f"{rx_name} the squelch is open" in lower:
                rx_open = True
                break       
            
        if tx_active:
            label = "Transmitting"
            css_class = "radio-tx"
        elif rx_open:
            label = "Receiving"
            css_class = "radio-rx"
        else:
            label = "Listening"
            css_class = "radio-standby"

        return {
            "label": label,
            "input": "Open" if rx_open else "Closed",
            "class": css_class,
            "tx": tx_active,
            "rx": rx_open,
    }


def get_echolink_state():
    """
    Determine the current EchoLink connection state from SvxLink's
    most recent EchoLink QSO state transition.
    """

    idle_state = {
        "active": False,
        "label": "Idle",
        "station": "",
        "class": "status-good",
    }

    lines = read_recent_svxlink_log_lines(1000)

    if not lines:
        return idle_state

    qso_pattern = re.compile(
        r"([A-Za-z0-9-]+):\s+"
        r"EchoLink QSO state changed to "
        r"(CONNECTED|DISCONNECTED)\b"
    )

    # The latest QSO state transition is authoritative.
    for line in reversed(lines[-1000:]):
        match = qso_pattern.search(line)

        if not match:
            continue

        station = match.group(1).upper()
        state = match.group(2)

        if state == "CONNECTED":
            return {
                "active": True,
                "label": "Connected",
                "station": station,
                "class": "status-warn",
            }

        return idle_state

    return idle_state


def get_active_talkgroup():
    """
    Determine the currently selected SvxReflector talkgroup
    from recent SvxLink log lines.

    Examples:
        ReflectorLogic: Selecting TG #0   -> Standby
        ReflectorLogic: Selecting TG #505 -> 505
    """

    lines = read_recent_svxlink_log_lines(1000)

    if not lines:
        return "Unknown"

    tg_pattern = re.compile(
        r"ReflectorLogic:\s+Selecting TG #(\d+)"
    )

    for line in reversed(lines[-1000:]):
        match = tg_pattern.search(line)

        if not match:
            continue

        talkgroup = match.group(1)

        if talkgroup == "0":
            return "Standby"

        return talkgroup

    return "Standby"


def get_status_callsign(model, selected_port="1"):
    """
    Return the callsign for the selected dashboard port.
    """

    selected_port = str(selected_port or "1")

    port_node = (
        model.get("nodes", {})
        .get(selected_port, {})
    )

    return (
        port_node.get("callsign")
        or model.get("node", {}).get("callsign")
        or model.get("ident", {}).get("callsign")
        or "unknown"
    )


def get_runtime_status(model, selected_port="1"):
    """
    Collect dashboard runtime information.
    """

    selected_port = str(selected_port or "1")

    return {
        "callsign": get_status_callsign(
            model,
            selected_port=selected_port,
        ),

        "node_type": model.get("nodes", {})
        .get(selected_port, {})
        .get(
            "role",
            model.get("node", {}).get(
                "type",
                "unknown"
            )
        ),

        "service_status": svxlink_status(),

        "uptime": get_system_uptime(),

        "reflector": get_connected_reflector(model),

        "active_talkgroup": get_active_talkgroup(),

        "modules": model.get("nodes", {})
        .get(selected_port, {})
        .get("modules", model.get("modules", {}))
        .get(
            "enabled",
            []
        ),

        "recent_log": get_recent_log_lines(),
        "selected_port": selected_port,
        "radio_state": get_radio_state(selected_port=selected_port),
        "echolink_state": get_echolink_state(),
    }


def get_recent_log_lines(limit=40):
    """
    Return recent SvxLink log lines for dashboard display.
    """

    log_file = get_svxlink_log_path()

    if not log_file.exists():
        return ["Log file not found: /var/log/svxlink.log"]

    try:
        lines = log_file.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()

    except Exception as exc:
        return [f"Unable to read log file: {exc}"]

    return lines[-limit:]    
