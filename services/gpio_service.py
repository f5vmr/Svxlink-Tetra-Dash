#!/usr/bin/env python3

"""
GPIO line helper for SvxLink-Dash-V4.1.
"""

import json
import subprocess
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
GPIO_LINES_FILE = APP_ROOT / "config" / "gpio_lines.json"


def build_raspberry_pi_gpio_lines():
    """
    Build the selectable Raspberry Pi GPIO list used by the setup wizard.
    """

    lines = []

    for line in range(2, 28):
        lines.append({
            "chip": "gpiochip0",
            "line": line,
            "label": f"GPIO{line}",
            "consumer": "",
            "direction": "",
            "active": "",
            "available": True,
        })

    return {
        "platform": "raspberry_pi",
        "gpiochips": [
            {
                "chip": "gpiochip0",
                "label": "Raspberry Pi GPIO",
                "lines": lines,
            }
        ],
    }


def load_gpio_lines():
    """
    Load scanned GPIO line map.
    """

    if not GPIO_LINES_FILE.exists():
        return {
            "gpiochips": []
        }

    try:
        return json.loads(
            GPIO_LINES_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {
            "gpiochips": []
        }


def flatten_gpio_lines(data=None, available_only=False, chip_filter=None):
    """
    Return GPIO lines as a simple list for templates.
    """

    if data is None:
        data = load_gpio_lines()

    rows = []

    for chip in data.get("gpiochips", []):
        chip_name = chip.get("chip", "")

        if chip_filter and chip_name != chip_filter:
            continue

        for line in chip.get("lines", []):
            available = line.get("available", True)

            if available_only and not available:
                continue

            line_number = line.get("line")
            label = line.get("label") or f"GPIO{line_number}"

            rows.append({
                "chip": line.get("chip", chip_name),
                "line": line_number,
                "label": label,
                "consumer": line.get("consumer", ""),
                "direction": line.get("direction", ""),
                "active": line.get("active", ""),
                "available": available,
            })

    return rows


def scan_gpio_lines():
    """
    Scan current GPIO chips and lines using gpioinfo.

    Returns data suitable for saving to GPIO_LINES_FILE.
    """

    result = subprocess.run(
        ["gpioinfo"],
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "gpioinfo failed: "
            + (result.stderr.strip() or result.stdout.strip())
        )

    gpiochips = []
    current_chip = None

    for raw_line in result.stdout.splitlines():
        line = raw_line.rstrip()

        if line.startswith("gpiochip"):
            chip_name = line.split()[0].rstrip(":")

            current_chip = {
                "chip": chip_name,
                "lines": [],
            }

            gpiochips.append(current_chip)
            continue

        if current_chip is None:
            continue

        stripped = line.strip()

        if not stripped.startswith("line "):
            continue

        try:
            before_colon, after_colon = stripped.split(":", 1)
        except ValueError:
            continue

        parts = before_colon.split()

        if len(parts) < 2:
            continue

        try:
            line_number = int(parts[1])
        except ValueError:
            continue

        quoted = []
        remainder = after_colon

        while '"' in remainder:
            before, quote, rest = remainder.partition('"')
            value, quote, remainder = rest.partition('"')
            quoted.append(value)

        label = quoted[0] if len(quoted) >= 1 else ""
        consumer = quoted[1] if len(quoted) >= 2 else ""

        available = "unused" in after_colon

        direction = ""
        if " input " in f" {after_colon} ":
            direction = "input"
        elif " output " in f" {after_colon} ":
            direction = "output"

        active = ""
        if "active-high" in after_colon:
            active = "active-high"
        elif "active-low" in after_colon:
            active = "active-low"

        current_chip["lines"].append({
            "chip": current_chip["chip"],
            "line": line_number,
            "label": label,
            "consumer": consumer,
            "direction": direction,
            "active": active,
            "available": available,
        })

    return {
        "gpiochips": gpiochips
    }


def save_gpio_lines(data):
    """
    Save scanned GPIO line map.
    """

    GPIO_LINES_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    GPIO_LINES_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def prepare_gpio_lines(platform_id, force=False):
    """
    Prepare the GPIO map required by the selected platform.

    Raspberry Pi:
        Uses the fixed selectable GPIO2-GPIO27 map.

    NanoPi-Neo:
        Uses its fixed image configuration and does not need selectable lines.
    """

    if platform_id == "raspberry_pi":
        existing = load_gpio_lines()

        if (
            not force
            and existing.get("platform") == "raspberry_pi"
            and existing.get("gpiochips")
        ):
            return existing

        data = build_raspberry_pi_gpio_lines()
        save_gpio_lines(data)
        return data

    if platform_id == "nanopi_neo":
        data = {
            "platform": "nanopi_neo",
            "gpiochips": [],
        }

        save_gpio_lines(data)
        return data

    data = {
        "platform": platform_id or "unknown",
        "gpiochips": [],
    }

    save_gpio_lines(data)
    return data


def refresh_gpio_lines():
    """
    Scan and save the current GPIO line map.
    """

    data = scan_gpio_lines()
    save_gpio_lines(data)
    return data


def find_gpio_line(label, data=None):
    """
    Find one GPIO line by stable gpio-line-name.

    Returns:
        {
            "chip": "gpiochip3",
            "line": "RX_1",
            "offset": 6,
            "consumer": "...",
            "available": true/false,
        }

    or None if not found.
    """

    if data is None:
        data = load_gpio_lines()

    for chip in data.get("gpiochips", []):
        chip_name = chip.get("chip", "")

        for line in chip.get("lines", []):
            if line.get("label") == label:
                return {
                    "chip": line.get("chip", chip_name),
                    "line": label,
                    "offset": line.get("line"),
                    "consumer": line.get("consumer", ""),
                    "direction": line.get("direction", ""),
                    "active": line.get("active", ""),
                    "available": line.get("available", True),
                }

    return None


def discover_named_gpio_lines(labels, refresh=True):
    """
    Discover multiple stable GPIO line names.

    By default this refreshes gpio_lines.json first.
    """

    data = refresh_gpio_lines() if refresh else load_gpio_lines()

    resolved = {}
    missing = []

    for label in labels:
        found = find_gpio_line(label, data)

        if found:
            resolved[label] = found
        else:
            missing.append(label)

    return resolved, missing


NATIVE_ICS_RX_LINES = {
    "ics_1x": {
        "1": {
            "chip": "gpiochip0",
            "line": 26,
        },
    },
    "ics_2x": {
        "1": {
            "chip": "gpiochip0",
            "line": 26,
        },
        "2": {
            "chip": "gpiochip0",
            "line": 23,
        },
    },
}


def required_ics_gpio_lines(model):
    """
    Return the GPIO line names required by the selected ICS profile.
    """

    hardware = model.get("hardware", {})

    profile_id = (
        model.get("hardware_profile_id")
        or hardware.get("profile_id")
        or hardware.get("id")
    )

    enabled_ports = model.get("ports", {}).get("enabled", [])

    labels = []

    for port in enabled_ports:
        port_id = str(port)

        if profile_id not in NATIVE_ICS_RX_LINES:
            labels.append(f"RX_{port_id}")

        labels.append(f"TX_{port_id}")

    if profile_id in ("ics_4x", "ics_8x"):
        labels.append("PCM_PDWN")

    return labels


def update_model_gpiod_discovery(model):
    """
    Refresh GPIO discovery and store resolved GPIOD data in node_model.
    """

    hardware = model.get("hardware", {})

    profile_id = (
        model.get("hardware_profile_id")
        or hardware.get("profile_id")
        or hardware.get("id")
    )

    native_rx_lines = NATIVE_ICS_RX_LINES.get(
        profile_id,
        {},
    )

    labels = required_ics_gpio_lines(model)

    resolved, missing = discover_named_gpio_lines(
        labels,
        refresh=True,
    )

    model.setdefault("gpiod", {})
    model["gpiod"]["resolved_lines"] = resolved
    model["gpiod"]["missing_lines"] = missing

    nodes = model.get("nodes", {})

    for port in model.get("ports", {}).get("enabled", []):
        port_id = str(port)
        node = nodes.get(port_id, {})

        rx_label = f"RX_{port_id}"
        tx_label = f"TX_{port_id}"

        rx = (
            native_rx_lines.get(port_id)
            or resolved.get(rx_label, {})
        )
        tx = resolved.get(tx_label, {})

        node.setdefault("gpio", {})

        node["gpio"]["cos_chip"] = rx.get("chip", "")
        node["gpio"]["cos_line"] = rx.get("line", rx_label)

        if "offset" in rx:
            node["gpio"]["cos_offset"] = rx["offset"]
        else:
            node["gpio"].pop("cos_offset", None)

        node["gpio"]["ptt_chip"] = tx.get("chip", "")
        node["gpio"]["ptt_line"] = tx.get("line", tx_label)
        node["gpio"]["ptt_offset"] = tx.get("offset")

        nodes[port_id] = node

    model["nodes"] = nodes

    return model