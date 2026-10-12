#!/usr/bin/env python3

"""
Raspberry Pi platform profile for SvxLink-Dash-V4.1.
"""

PROFILE = {
    "id": "raspberry_pi",
    "name": "Raspberry Pi",
    "supported": True,

    "allowed_node_types": [
        "simplex",
        "repeater",
    ],

    "allowed_interface_modes": [
        "gpiod",
        "hidraw",
        "hybrid",
    ],

    "allowed_squelch_modes": [
        "gpiod",
        "ctcss",
        "gpiod_ctcss",
        "hidraw",
    ],

    "default_interface_mode": "gpiod",

    "gpio": {
        "sql": None,
        "ptt": None,
    },

    "audio": {
        "audio_dev": "alsa:plughw:0",
        "audio_channel": 0,
    },

    "notes": [
        "Raspberry Pi may use GPIOD, HIDRAW, or hybrid control.",
        "GPIOD pin definitions must be supplied by the Raspberry Pi configuration path.",
        "HIDRAW mode assumes a TOADS card or suitably modified CM108/CM119 device.",
        "Hybrid mode assumes HIDRAW PTT and GPIOD SQL.",
    ],
}