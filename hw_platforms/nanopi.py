#!/usr/bin/env python3

"""
NanoPi-Neo platform profile for SvxLink-Dash-V4.1.
"""

PROFILE = {
    "id": "nanopi_neo",
    "name": "NanoPi-Neo",
    "supported": True,

    "allowed_node_types": [
        "simplex",
        "repeater",
    ],

    "allowed_interface_modes": [
        "gpiod",
        "hidraw",
    ],

    "allowed_squelch_modes": [
        "gpiod",
        "ctcss",
        "gpiod_ctcss",
        "hidraw",
    ],

    "default_interface_mode": "gpiod",

    "gpio": {
        "sql": {
            "chip": "gpiochip0",
            "line": 203,
            "active": "high",
            "physical_pin": 7,
        },
        "ptt": {
            "chip": "gpiochip0",
            "line": 6,
            "physical_pin": 12,
        },
    },

    "audio": {
        "audio_dev": "alsa:plughw:0",
        "audio_channel": 0,
    },

    "notes": [
        "NanoPi-Neo uses fixed GPIOD SQL/PTT structure.",
        "HIDRAW and hybrid interface modes are not supported on this platform profile.",
    ],
}