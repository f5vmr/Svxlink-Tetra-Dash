#!/usr/bin/env python3

"""
DTMF control helper for SvxLink-Dash-V4.1.

Writes DTMF command strings to the SvxLink control PTY selected
for the current node type.
"""

from pathlib import Path
import json
import re

APP_ROOT = Path(__file__).resolve().parent.parent
NODE_MODEL = APP_ROOT / "config" / "node_model.json"


def get_dtmf_control_path(selected_port=None):
    """
    Return the DTMF control PTY for the selected radio logic.

    Multi-port configurations use the port-numbered PTY generated
    for the selected PortNLogic section. Single-port configurations
    retain their simplex or repeater PTY naming.
    """

    try:
        model = json.loads(
            NODE_MODEL.read_text(encoding="utf-8")
        )
    except Exception:
        model = {}

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})
    selected_port = str(selected_port or "")

    if (
        isinstance(nodes, dict)
        and selected_port in enabled_ports
        and selected_port in nodes
    ):
        return Path(
            f"/dev/shm/port{selected_port}_dtmf_ctrl"
        )

    for port_id in enabled_ports:
        if isinstance(nodes, dict) and port_id in nodes:
            return Path(
                f"/dev/shm/port{port_id}_dtmf_ctrl"
            )

    node_type = model.get("node", {}).get("type")

    if node_type == "repeater":
        return Path("/dev/shm/repeater_dtmf_ctrl")

    return Path("/dev/shm/simplex_dtmf_ctrl")


def normalise_dtmf(command):
    """
    Normalise keyboard-entered DTMF characters.
    """

    return command.strip().upper()


def validate_dtmf(command):
    """
    Allow the complete sixteen-key DTMF alphabet.
    """

    command = normalise_dtmf(command)

    return bool(
        re.fullmatch(
            r"[0-9A-D*#]+",
            command,
        )
    )


def send_dtmf(command, selected_port=None):
    """
    Send a DTMF command to the selected SvxLink logic PTY.
    """

    command = normalise_dtmf(command)

    if not validate_dtmf(command):
        raise ValueError("Invalid DTMF command.")

    dtmf_path = get_dtmf_control_path(
        selected_port=selected_port,
    )

    if not dtmf_path.exists():
        raise FileNotFoundError(
            f"DTMF control path not found: {dtmf_path}"
        )

    with dtmf_path.open("w", encoding="utf-8") as handle:
        handle.write(command)

    return command
