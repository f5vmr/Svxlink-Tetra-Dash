#!/usr/bin/env python3

"""
node_info.json renderer for SvxLink-Dash-V4.1.
"""

import json
from pathlib import Path


NODE_INFO_FILE = Path("/etc/svxlink/node_info.json")


def get_primary_port_id(model):
    """
    Return the selected enabled primary port for a multi-port model.
    """
    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    primary_port_id = str(
        model.get("installation", {}).get("primary_port_id") or ""
    )

    if primary_port_id in enabled_ports:
        return primary_port_id

    if len(enabled_ports) == 1:
        return enabled_ports[0]

    return None


def build_node_info_json(model):
    if not model.get("node_info", {}).get("enabled"):
        return {}

    info = model.get("node_info", {})
    primary_port_id = get_primary_port_id(model)

    if primary_port_id is None:
        rx_name = "Rx1"
        tx_name = "Tx1"
        squelch = model.get("squelch", {})
    else:
        rx_name = f"Rx{primary_port_id}"
        tx_name = f"Tx{primary_port_id}"
        squelch = (
            model.get("nodes", {})
            .get(primary_port_id, {})
            .get("squelch", {})
        )

    sql_type = (
        "CTCSS"
        if squelch.get("method") == "ctcss"
        else "COR"
    )

    return {
        "nodeLocation": info.get("nodeLocation", ""),
        "hidden": False,
        "sysop": info.get("sysop", ""),
        "qth": [
            {
                "name": info.get("qth_name", ""),
                "pos": {
                    "lat": info.get("lat", ""),
                    "long": info.get("long", ""),
                    "loc": info.get("locator", ""),
                },
                "rx": {
                    "K": {
                        "name": rx_name,
                        "freq": float(
                            info.get("rx_freq") or 0
                        ),
                        "sqlType": sql_type,
                        "ant": {
                            "comment": info.get(
                                "antenna",
                                "",
                            ),
                            "height": info.get(
                                "antenna_height",
                                "",
                            ),
                            "dir": info.get(
                                "antenna_direction",
                                "Omni",
                            ),
                        },
                    }
                },
                "tx": {
                    "K": {
                        "name": tx_name,
                        "freq": float(
                            info.get("tx_freq") or 0
                        ),
                        "pwr": info.get("tx_power", ""),
                        "ant": {
                            "comment": info.get(
                                "antenna",
                                "",
                            ),
                            "height": info.get(
                                "antenna_height",
                                "",
                            ),
                            "dir": info.get(
                                "antenna_direction",
                                "Omni",
                            ),
                            "gain": "",
                            "Antenna_type": "omni",
                        },
                    }
                },
            }
        ],
    }


def write_node_info_json(model):
    data = build_node_info_json(model)

    NODE_INFO_FILE.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )

    NODE_INFO_FILE.chmod(0o664)

    return NODE_INFO_FILE