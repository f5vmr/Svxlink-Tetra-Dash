#!/usr/bin/env python3

"""
SvxLink-Dash-V4.0 node model.

This file defines the authoritative configuration model used by:
- Flask setup pages
- validation logic
- svxlink.conf renderers
- future dashboard editing
"""

from copy import deepcopy


SUPPORTED_NODE_TYPES = {"simplex", "repeater"}

SUPPORTED_IDENT_MODES = {
    "none",
    "cw",
    "voice",
    "both",
}

SUPPORTED_ROGER_MODES = {
    "none",
    "A",
    "D",
    "E",
    "I",
    "K",
    "M",
    "N",
    "R",
    "S",
    "T",
    "U",
    "X",
}
SUPPORTED_IDLE_TONES = {
    "chime",
    "pip",
    "silence",
}

SUPPORTED_DOWN_TONES = {
    "biboop",
    "va",
    "none",
}

STANDARD_SQUELCH_METHODS = (
    "hidraw",
    "gpiod",
    "serial",
    "ctcss",
)

ADVANCED_SQUELCH_METHODS = (
    "vox",
    "siglev",
    "combine",
)

MANUAL_SQUELCH_DETECTORS = (
    "evdev",
    "pty",
    "rtl_sdr",
)

SUPPORTED_SQUELCH_METHODS = (
    *STANDARD_SQUELCH_METHODS,
)

SUPPORTED_INTERFACE_MODES = {
    "hidraw",
    "gpiod",
    "hybrid",
    "serial",
}
NANOPI_NEO_GPIO_DEFAULTS = {
    "sql": {
        "chip": "gpiochip0",
        "line": 203,
        "active": "high",
    },
    "ptt": {
        "chip": "gpiochip0",
        "line": 6,
    },
}
DEFAULT_MODEL = {
    "schema_version": 2,

    "build": {
        "intent": "single_channel",
    },

    "installation": {
        "primary_port_id": None,
    },

    "platform": {
        "id": None,
        "name": None,
        "supported": False,
    },

    "node": {
        "type": None,
        "callsign": None,
        "language": "en_US",
    },
    "interface": {
        "mode": "hidraw",
        "sql_source": "hidraw",
        "ptt_source": "hidraw",
    },
    "reflector": {
        "enabled": False,
        "route": "none",

        # Legacy Protocol 2 fields retained during migration.
        "name": None,
        "host": None,
        "port": None,
        "auth_key": None,

        "operational": {
            "default_tg": 0,
            "monitor_tgs": [],
            "tg_select_timeout": 60,
        },

        "federation": {
            "network_id": None,
            "name": None,
            "host": None,
            "port": None,
            "auth_key": None,
        },

        "v2": {
            "name": None,
            "host": None,
            "port": None,
            "auth_key": None,
        },

        "v3": {
            "name": None,
            "host": None,
            "port": None,
            "subject": {
                "given_name": None,
                "surname": None,
                "organizational_unit": None,
                "organization": None,
                "locality": None,
                "state_or_province": None,
                "country": None,
                "email": None,
            },
        },
    },

    "topology": {
        "reflector_link": {
            "name": "LinkToReflector",
            "ports": [],
            "default_active": True,
            "timeout": 300,
        },
        "local_links": [],
        "independent_ports": [],
    },
        "node_info": {
            "enabled": False,
            "nodeLocation": "",
            "hidden": False,
            "qth_name": "",
            "sysop": "",
            "lat": "",
            "long": "",
            "locator": "",
            "lat_dms": "",
            "long_dms": "",
            "rx_freq": "",
            "tx_freq": "",
            "tx_power": "",
            "antenna": "",
            "antenna_height": "",
            "antenna_direction": "omni",
        },

        "location_info": {
            "enabled": False,
            "aprs_server_list": "",
            "publish_echolink_status": False,
            "status_server_list": "aprs.echolink.org:5199",
            "narrow": True,
            "tx_offset_khz": 0,
            "antenna_gain": "",
            "antenna_height_unit": "m",
            "beacon_interval": 10,
            "comment": "",
        },
        "ident": {
            "short": {
            "mode": "cw",
            "interval": 15,
        },
        "long": {
            "mode": "voice",
            "interval": 60,
        },
    },
    "gpio": {
        "sql": {
            "chip": "gpiochip0",
            "line": 23,
            "active": "high",
        },
        "ptt": {
            "chip": "gpiochip0",
            "line": 24,
        },
    },
    "hidraw": {
        "device": "/dev/hidraw0",
        "sql_pin": "VOL_DN",
        "ptt_pin": "GPIO3",
    },
    "serial": {
        "sql_port": "/dev/ttyS0",
        "sql_pin": "CTS",
        "sql_set_pins": "DTR!RTS",
        "ptt_port": "/dev/ttyS0",
        "ptt_pin": "DTRRTS",
    },
    "cw": {
        "amp": -10,
        "pitch": 650,
        "cpm": 95,
    },
    "audio": {
        "audio_dev": "alsa:plughw:0",
        "audio_channel": 0,
    },
    "time_format": "24",
    "fx_gain_normal": 0,
    "fx_gain_low": -12,
    "sql_hangtime": 200,
    "sql_tail_elim": 270,
    "tx_delay": 500,
    "tg_timeout": 60,
    "tx_ctcss_mode": "ALWAYS",

    "tones": {
        "courtesy_mode": "none",
        "courtesy_frequency": 800,
        "idle_mode": "chime",
        "closedown_mode": "biboop",
    },
    "courtesy": {
        "mode": "none",
    },
    "repeater": {
    "idle_tone": "chime",
    "down_tone": "biboop",
    "idle_timeout": 10,
    "sql_timeout": 180,
    },
    "squelch": {
        "method": "hidraw",
        "advanced_example": None,
        "combine_components": [],
        "manual_detector": None,
        "ctcss_freq": None,
        "ctcss_tx": False,
    },
    "ctcss_to_tg": {
        "enabled": False,
        "delay_ms": 0,
        "mappings": [],
    },
    "echolink": {
        "enabled": False,
        "callsign": None,
        "password": None,
        "sysopname": None,
        "location": None,
    },
        "metar": {
            "enabled": False,
            "region": None,
            "startdefault": None,
            "airports": [],
            "custom_startdefault": None,
    },  
        "modules": {
            "enabled": [
            "ModuleHelp",
            "ModuleParrot",
        ],
    },
}


def new_tetra_configuration():
    """
    Return independent TETRA settings for one radio port.

    Connection, baud, mode and ISSI require explicit configuration.
    """
    return {
        "radio_model": "MTM5400",
        "mode": None,
        "pei_device": None,
        "baud": None,
        "issi": None,
        "gssi": 1,
        "mcc": 901,
        "mnc": 16383,
        "pei_init_file": "/etc/svxlink/pei-init.json",
        "user_info_file": "/etc/svxlink/tetra_users.json",
        "end_cmd": "ATH",
        "configured": False,
    }


def new_node_model(platform=None):
    """
    Return a fresh node model.

    platform may be a dict from the platform detection layer.
    """

    model = deepcopy(DEFAULT_MODEL)

    if platform is not None:
        platform_id = platform.get("id")

        model["platform"] = {
            "id": platform_id,
            "name": platform.get("name"),
            "supported": bool(platform.get("supported")),
        }

        if platform_id == "nanopi_neo":
            model["gpio"] = deepcopy(NANOPI_NEO_GPIO_DEFAULTS)

    return model


def is_ics_multiport_model(model):
    hardware = model.get("hardware", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    return (
        hardware.get("family") == "ics"
        and len(enabled_ports)
    )


def has_tetra_port(model):
    """
    Return whether an enabled port has the TETRA role.
    """
    nodes = model.get("nodes", {})
    roles = model.get("port_roles", {})

    for port in model.get("ports", {}).get("enabled", []):
        port_id = str(port)
        role_entry = roles.get(port_id, {})
        selected_role = (
            role_entry.get("role")
            if isinstance(role_entry, dict)
            else role_entry
        )

        role = selected_role or nodes.get(port_id, {}).get("role")

        if role == "tetra":
            return True

    return False


def is_multiport_model(model):
    enabled_ports = model.get("ports", {}).get("enabled", [])

    return (
        is_ics_multiport_model(model)
        or len(enabled_ports) > 1
        or has_tetra_port(model)
    )


def squelch_uses_ctcss(squelch):
    """
    Return True when CTCSS is the active SQL detector or is
    selected for a commented Advanced COMBINE example.
    """

    if not isinstance(squelch, dict):
        return False

    if squelch.get("method") == "ctcss":
        return True

    if squelch.get("advanced_example") != "combine":
        return False

    components = squelch.get(
        "combine_components",
        [],
    )

    return (
        isinstance(components, list)
        and "ctcss" in components
    )


def ctcss_talkgroup_selection_available(
    squelch,
):
    """
    Return whether CTCSS_TO_TG may be offered for this receiver.
    """

    return not squelch_uses_ctcss(squelch)


def validate_squelch_configuration(
    squelch,
    label="Squelch",
):
    """
    Validate one guided squelch configuration.

    The active method must always be a Standard detector.
    Advanced and specialist selections only describe commented
    manual configuration examples.
    """

    errors = []

    if not isinstance(squelch, dict):
        return [
            f"{label} configuration must be an object."
        ]

    method = squelch.get("method")

    if method not in SUPPORTED_SQUELCH_METHODS:
        errors.append(
            f"{label} active detector must be HIDRAW, GPIOD, "
            "SERIAL or CTCSS."
        )

    advanced_example = squelch.get(
        "advanced_example"
    )

    if (
        advanced_example is not None
        and advanced_example
        not in ADVANCED_SQUELCH_METHODS
    ):
        errors.append(
            f"{label} Advanced example must be VOX, SIGLEV "
            "or COMBINE."
        )

    manual_detector = squelch.get(
        "manual_detector"
    )

    if (
        manual_detector is not None
        and manual_detector
        not in MANUAL_SQUELCH_DETECTORS
    ):
        errors.append(
            f"{label} specialist example must be EVDEV, PTY "
            "or RTL-SDR."
        )

    if advanced_example and manual_detector:
        errors.append(
            f"{label} cannot select both an Advanced and a "
            "Super-advanced example."
        )

    components = squelch.get(
        "combine_components",
        [],
    )

    if advanced_example == "combine":
        if not isinstance(components, list):
            errors.append(
                f"{label} COMBINE components must be a list."
            )
        else:
            allowed_components = {
                "vox",
                "siglev",
                "ctcss",
            }

            invalid_components = [
                component
                for component in components
                if component not in allowed_components
            ]

            if invalid_components:
                errors.append(
                    f"{label} COMBINE contains an unsupported "
                    "detector component."
                )

            if len(components) < 2:
                errors.append(
                    f"{label} COMBINE requires at least two "
                    "detector components."
                )

            if len(components) > 3:
                errors.append(
                    f"{label} COMBINE permits no more than "
                    "three detector components."
                )

            if len(set(components)) != len(
                components
            ):
                errors.append(
                    f"{label} COMBINE cannot contain the same "
                    "detector component more than once."
                )

    elif components:
        errors.append(
            f"{label} cannot retain COMBINE components when "
            "the Advanced example is not COMBINE."
        )

    if squelch_uses_ctcss(squelch):
        ctcss_freq = str(
            squelch.get("ctcss_freq") or ""
        ).strip()

        if not ctcss_freq:
            errors.append(
                f"{label} CTCSS frequency is required when "
                "CTCSS participates in SQL detection."
            )

    if (
        squelch.get("ctcss_tx")
        and squelch.get("method") != "ctcss"
    ):
        errors.append(
            f"{label} may use TX CTCSS only when CTCSS "
            "is the active SQL detector."
        )
    return errors


def validate_ctcss_talkgroup_configuration(
    configuration,
    squelch,
    label="CTCSS TalkGroup selection",
):
    """
    Validate one logic core's local RF CTCSS-to-TalkGroup mapping.
    """

    if configuration is None:
        return []

    if not isinstance(configuration, dict):
        return [
            f"{label} configuration must be an object."
        ]

    errors = []

    enabled = configuration.get("enabled", False)

    if not isinstance(enabled, bool):
        errors.append(
            f"{label} enabled state must be true or false."
        )

    delay_ms = configuration.get("delay_ms", 0)

    if (
        not isinstance(delay_ms, int)
        or isinstance(delay_ms, bool)
        or delay_ms < 0
    ):
        errors.append(
            f"{label} delay must be a whole number of "
            "milliseconds, zero or greater."
        )

    mappings = configuration.get("mappings", [])

    if not isinstance(mappings, list):
        errors.append(
            f"{label} mappings must be a list."
        )
        return errors

    if enabled and not mappings:
        errors.append(
            f"{label} requires at least one tone mapping "
            "when enabled."
        )

    if (
        enabled
        and not ctcss_talkgroup_selection_available(
            squelch
        )
    ):
        errors.append(
            f"{label} is unavailable because CTCSS is "
            "already used for squelch detection."
        )

    seen_tones = set()

    for index, mapping in enumerate(mappings):
        row_label = f"{label} row {index + 1}"

        if not isinstance(mapping, dict):
            errors.append(
                f"{row_label} must be an object."
            )
            continue

        tone_text = str(
            mapping.get("tone") or ""
        ).strip()

        try:
            tone = float(tone_text)
        except (TypeError, ValueError):
            tone = None

        if tone is None or tone <= 0:
            errors.append(
                f"{row_label} must contain a positive "
                "CTCSS frequency."
            )
        else:
            normalised_tone = format(tone, "g")

            if normalised_tone in seen_tones:
                errors.append(
                    f"{label} tone {normalised_tone} Hz "
                    "is entered more than once."
                )
            else:
                seen_tones.add(normalised_tone)

        talkgroup_text = str(
            mapping.get("talkgroup") or ""
        ).strip()

        if (
            not talkgroup_text.isdigit()
            or int(talkgroup_text) <= 0
        ):
            errors.append(
                f"{row_label} must contain a positive "
                "whole-number TalkGroup."
            )

    return errors


def validate_tetra_configuration(configuration, label="TETRA"):
    """
    Validate the connection and identity settings for one TETRA port.
    """
    errors = []

    if not isinstance(configuration, dict):
        return [f"{label} settings are required."]

    if configuration.get("mode") not in {
        "TMO",
        "DMO-RPT",
        "DMO-MS",
        "GATEWAY",
    }:
        errors.append(f"{label} operating mode is required.")

    device = configuration.get("pei_device")
    if (
        not isinstance(device, str)
        or not device.startswith("/dev/")
        or device == "/dev/"
        or any(character.isspace() for character in device)
    ):
        errors.append(
            f"{label} PEI device must be a path under /dev/."
        )

    for field, description in (
        ("baud", "baud rate"),
        ("issi", "ISSI"),
        ("gssi", "GSSI"),
        ("mcc", "MCC"),
        ("mnc", "MNC"),
    ):
        value = configuration.get(field)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            errors.append(
                f"{label} {description} must be a positive integer."
            )

    return errors


def validate_tetra_interface(node, label="TETRA"):
    """
    Require saved audio and independent wired PTT settings.
    """
    errors = []
    audio = node.get("audio", {})
    interface = node.get("interface", {})

    if interface.get("configured") is not True:
        errors.append(f"{label} audio and PTT must be configured.")

    for field, description in (
        ("rx_audio", "receive audio"),
        ("tx_audio", "transmit audio"),
    ):
        value = audio.get(field)
        if (
            not isinstance(value, str)
            or not value.startswith("alsa:")
            or value == "alsa:"
            or any(character.isspace() for character in value)
        ):
            errors.append(
                f"{label} {description} must be an ALSA device."
            )

    source = interface.get("ptt_source")

    if source == "serial":
        serial = node.get("serial", {})
        device = serial.get("ptt_port")

        if (
            not isinstance(device, str)
            or not device.startswith("/dev/")
            or device == "/dev/"
            or any(character.isspace() for character in device)
        ):
            errors.append(f"{label} PTT serial device is required.")

        if serial.get("ptt_pin") not in {
            "RTS", "!RTS", "DTR", "!DTR",
            "DTRRTS", "DTR!RTS", "!DTRRTS", "!DTR!RTS",
        }:
            errors.append(f"{label} serial PTT pin is invalid.")

        if device and device == node.get(
            "tetra", {}
        ).get("pei_device"):
            errors.append(
                f"{label} PEI and serial PTT must use separate devices."
            )

    elif source == "hidraw":
        hidraw = node.get("hidraw", {})
        device = hidraw.get("device")

        if (
            not isinstance(device, str)
            or not device.startswith("/dev/")
            or device == "/dev/"
            or any(character.isspace() for character in device)
        ):
            errors.append(f"{label} HID PTT device is required.")

        if hidraw.get("ptt_pin") not in {
            "GPIO1", "GPIO2", "GPIO3", "GPIO4",
        }:
            errors.append(f"{label} HID PTT pin is invalid.")

    else:
        errors.append(f"{label} wired PTT must be Serial or Hidraw.")

    return errors


def port_node_details_complete(node):
    """
    Require identity details and valid TETRA settings where applicable.
    """
    if not node.get("node_details_configured"):
        return False

    if node.get("role") != "tetra":
        return True

    tetra = node.get("tetra", {})

    return (
        isinstance(tetra, dict)
        and tetra.get("configured") is True
        and not validate_tetra_configuration(tetra)
        and not validate_tetra_interface(node)
    )


def validate_model(model):
    """
    Validate high-level model consistency.

    Returns:
        list[str]: validation error messages.
    """

    errors = []
    
    multiport = is_multiport_model(model)

    node_type = model.get("node", {}).get("type")
    callsign = model.get("node", {}).get("callsign")

    if multiport:
        nodes = model.get("nodes", {})
        enabled_ports = model.get("ports", {}).get("enabled", [])

        if not enabled_ports:
            errors.append("At least one port must be enabled.")

        if not nodes:
            errors.append("Port configuration is required.")

        for port in enabled_ports:
            port_id = str(port)
            node = nodes.get(port_id, {})

            if node.get("role") not in ("simplex", "repeater", "tetra"):
                errors.append(
                    f"Port {port_id} type must be simplex, repeater, or TETRA."
                )
            if node.get("role") == "tetra":
                errors.extend(
                    validate_tetra_configuration(
                        node.get("tetra"),
                        label=f"Port {port_id} TETRA",
                    )
                )
                errors.extend(
                    validate_tetra_interface(
                        node,
                        label=f"Port {port_id} TETRA",
                    )
                )
            if not node.get("callsign"):
                errors.append(
                    f"Port {port_id} callsign is required."
                )
            errors.extend(
                validate_ctcss_talkgroup_configuration(
                    node.get("ctcss_to_tg"),
                    node.get("squelch", {}),
                    label=(
                        f"Port {port_id} CTCSS TalkGroup "
                        "selection"
                    ),
                )
            )
    else:
        if node_type not in SUPPORTED_NODE_TYPES:
            errors.append("Node type must be simplex or repeater.")

        if not callsign:
            errors.append("Callsign is required.")

    short_ident = model.get("ident", {}).get("short", {})
    long_ident = model.get("ident", {}).get("long", {})

    if short_ident.get("mode") not in SUPPORTED_IDENT_MODES:
        errors.append("Short ident mode is invalid.")

    if long_ident.get("mode") not in SUPPORTED_IDENT_MODES:
        errors.append("Long ident mode is invalid.")

    for ident_name, ident_data in (
        ("Short", short_ident),
        ("Long", long_ident),
    ):
        interval = ident_data.get("interval")

        if not isinstance(interval, int):
            errors.append(f"{ident_name} ident interval must be a number.")
        elif interval < 1:
            errors.append(f"{ident_name} ident interval must be at least 1 minute.")

    tones = get_installation_tones(model)

    courtesy_mode = tones["courtesy_mode"]
    courtesy_frequency = tones["courtesy_frequency"]
    idle_mode = tones["idle_mode"]
    closedown_mode = tones["closedown_mode"]

    if courtesy_mode not in SUPPORTED_ROGER_MODES:
        errors.append("Courtesy tone mode is invalid.")

    if (
        not isinstance(courtesy_frequency, int)
        or isinstance(courtesy_frequency, bool)
        or courtesy_frequency < 300
        or courtesy_frequency > 3000
    ):
        errors.append(
            "Courtesy beep frequency must be between 300 and 3000 Hz."
        )

    if idle_mode not in SUPPORTED_IDLE_TONES:
        errors.append("Idle tone mode is invalid.")

    if closedown_mode not in SUPPORTED_DOWN_TONES:
        errors.append("Close-down tone mode is invalid.")
    
    if not multiport:
        interface_mode = model.get(
            "interface",
            {},
        ).get("mode")

        if interface_mode not in SUPPORTED_INTERFACE_MODES:
            errors.append("Interface mode is invalid.")

        errors.extend(
            validate_squelch_configuration(
                model.get("squelch", {}),
            )
        )

        errors.extend(
            validate_ctcss_talkgroup_configuration(
                model.get("ctcss_to_tg"),
                model.get("squelch", {}),
            )
        )

    reflector = model.get("reflector", {})

    reflector_route = str(
        reflector.get("route") or "none"
    ).strip().lower()

    if (
        not reflector.get("enabled")
        and reflector_route not in {
            "",
            "none",
        }
    ):
        errors.append(
            "Complete the selected reflector route or choose "
            "No reflector connection."
        )

    if reflector.get("enabled"):
        route = str(
            reflector.get("route") or ""
        ).strip().lower()

        if route == "federation":
            federation = reflector.get("federation", {})

            network_id = str(
                federation.get("network_id") or ""
            ).strip()

            name = (
                federation.get("name")
                or reflector.get("name")
            )

            host = (
                federation.get("host")
                or reflector.get("host")
            )

            port = (
                federation.get("port")
                or reflector.get("port")
            )

            auth_key = str(
                federation.get("auth_key")
                or reflector.get("auth_key")
                or ""
            )

            if not network_id:
                errors.append(
                    "Federation Family reflector selection is required."
                )

            if len(auth_key) != 16:
                errors.append(
                    "Federation subscription password must be "
                    "exactly 16 characters."
                )

            if not name:
                errors.append(
                    "Federation Family reflector name is required."
                )

            if not host:
                errors.append(
                    "Federation Family reflector host is required."
                )

            if not port:
                errors.append(
                    "Federation Family reflector port is required."
                )

        elif route == "v2":
            v2 = reflector.get("v2", {})

            name = v2.get("name") or reflector.get("name")
            host = v2.get("host") or reflector.get("host")
            port = v2.get("port") or reflector.get("port")
            auth_key = (
                v2.get("auth_key")
                or reflector.get("auth_key")
            )
            if not name:
                errors.append(
                    "Protocol 2 reflector name is required."
                )

            if not host:
                errors.append("Protocol 2 reflector host is required.")

            if not port:
                errors.append("Protocol 2 reflector port is required.")

            if not auth_key:
                errors.append(
                    "Protocol 2 reflector authentication password "
                    "is required."
                )

        elif route == "v3":
            v3 = reflector.get("v3", {})
            subject = v3.get("subject", {})

            name = v3.get("name") or reflector.get("name")
            host = v3.get("host") or reflector.get("host")
            port = v3.get("port") or reflector.get("port")

            if not name:
                errors.append(
                    "Protocol 3 reflector name is required."
                )

            if not host:
                errors.append("Protocol 3 reflector host is required.")

            if not port:
                errors.append("Protocol 3 reflector port is required.")

            required_subject_fields = {
                "given_name": "given name",
                "surname": "surname",
                "organizational_unit": "organizational unit",
                "organization": "organization",
                "locality": "locality",
                "state_or_province": "state or province",
                "country": "country",
                "email": "email address",
            }

            for field_name, field_label in required_subject_fields.items():
                if not str(subject.get(field_name) or "").strip():
                    errors.append(
                        f"Protocol 3 certificate {field_label} "
                        "is required."
                    )

            country = str(
                subject.get("country") or ""
            ).strip()

            if country and (
                len(country) != 2
                or not country.isalpha()
            ):
                errors.append(
                    "Protocol 3 certificate country must be "
                    "a two-letter code."
                )

            email = str(
                subject.get("email") or ""
            ).strip()

            if email and (
                "@" not in email
                or email.startswith("@")
                or email.endswith("@")
            ):
                errors.append(
                    "Protocol 3 certificate email address is invalid."
                )

        else:
            errors.append(
                "Enabled reflector must use Federation Family, "
                "Protocol 2 or Protocol 3."
            )

    echolink = model.get("echolink", {})

    if echolink.get("enabled"):
        echolink_callsign = echolink.get("callsign")

        if not echolink_callsign:
            errors.append("EchoLink callsign is required.")
        elif not (
            echolink_callsign.endswith("-L")
            or echolink_callsign.endswith("-R")
        ):
            errors.append("EchoLink callsign must end in -L or -R.")

        if not echolink.get("password"):
            errors.append("EchoLink password is required.")

        if not echolink.get("sysopname"):
            errors.append("EchoLink sysop name is required.")

        location = echolink.get("location")

        if not location:
            errors.append("EchoLink location is required.")
        elif not location.startswith("[Svx] "):
            errors.append("EchoLink location must start with [Svx].")
        elif len(location.replace("[Svx] ", "", 1)) > 12:
            errors.append("EchoLink location text must be 12 characters or fewer.")
    
    return errors


def set_node_identity(model, node_type, callsign):
    """
    Set basic node identity.
    """

    model["node"]["type"] = node_type
    model["node"]["callsign"] = callsign.strip().upper()
    return model


def set_ident(model, short_mode, short_interval, long_mode, long_interval):
    """
    Set short and long identification behaviour.
    """

    model["ident"]["short"]["mode"] = short_mode
    model["ident"]["short"]["interval"] = int(short_interval)

    model["ident"]["long"]["mode"] = long_mode
    model["ident"]["long"]["interval"] = int(long_interval)

    return model


def get_installation_tones(model):
    """
    Return normalised installation-wide tone settings.

    Legacy single-port values are used only when the version 2 tone
    structure is absent.
    """

    tones = model.get("tones")

    if isinstance(tones, dict):
        return {
            "courtesy_mode": tones.get("courtesy_mode", "none"),
            "courtesy_frequency": tones.get(
                "courtesy_frequency",
                800,
            ),
            "idle_mode": tones.get("idle_mode", "chime"),
            "closedown_mode": tones.get(
                "closedown_mode",
                "biboop",
            ),
        }

    courtesy = model.get("courtesy", {})
    repeater = model.get("repeater", {})

    idle_mode = repeater.get("idle_tone", "chime")

    if idle_mode == "none":
        idle_mode = "silence"

    return {
        "courtesy_mode": courtesy.get("mode", "none"),
        "courtesy_frequency": courtesy.get("frequency", 800),
        "idle_mode": idle_mode,
        "closedown_mode": repeater.get(
            "down_tone",
            "biboop",
        ),
    }


def set_roger(model, roger_mode):
    """
    Set the installation-wide courtesy tone mode.
    """

    model.setdefault("tones", {})
    model["tones"]["courtesy_mode"] = roger_mode

    return model


def set_interface_mode(model, mode):
    """
    Set physical SQL/PTT control interface.

    gpiod:
        SQL = GPIOD
        PTT = GPIOD

    hidraw:
        SQL = HIDRAW
        PTT = HIDRAW

    hybrid:
        SQL = GPIOD
        PTT = HIDRAW
    """

    if mode == "gpiod":
        model["interface"] = {
            "mode": "gpiod",
            "sql_source": "gpiod",
            "ptt_source": "gpiod",
        }

    elif mode == "hidraw":
        model["interface"] = {
            "mode": "hidraw",
            "sql_source": "hidraw",
            "ptt_source": "hidraw",
        }

    elif mode == "hybrid":
        model["interface"] = {
            "mode": "hybrid",
            "sql_source": "gpiod",
            "ptt_source": "hidraw",
        }

    else:
        raise ValueError(f"Unsupported interface mode: {mode}")

    return model


def set_squelch(model, method, ctcss_freq=None, ctcss_tx=False):
    """
    Set squelch configuration.
    """

    model["squelch"]["method"] = method
    model["squelch"]["ctcss_freq"] = ctcss_freq
    model["squelch"]["ctcss_tx"] = bool(ctcss_tx)

    return model


def enable_reflector(model, name, host, port, auth_key):
    """
    Enable reflector configuration.
    """

    model["reflector"] = {
        "enabled": True,
        "name": name,
        "host": host,
        "port": int(port),
        "auth_key": auth_key,
    }

    return model


def disable_reflector(model):
    """
    Disable reflector configuration.
    """

    model["reflector"] = {
        "enabled": False,
        "name": None,
        "host": None,
        "port": None,
        "auth_key": None,
    }

    return model
    

def set_echolink(
    model,
    enabled,
    callsign=None,
    password=None,
    sysopname=None,
    location=None,
):
    """
    Set EchoLink module configuration.

    EchoLink LOCATION is built as:
        [Svx] Fq, Location

    The final LOCATION field must not exceed 17 characters.
    """

    if not enabled:
        model["echolink"] = {
            "enabled": False,
            "callsign": None,
            "password": None,
            "sysopname": None,           
            "location": None,
        }
        return model

    callsign = callsign.strip().upper()
    password = password.strip()
    sysopname = sysopname.strip()
    location_text = location.strip()

    location = f"[Svx] {location_text}"

    model["echolink"] = {
        "enabled": True,
        "callsign": callsign,
        "password": password,
        "sysopname": sysopname,
        "location": location,
    }

    return model


def enable_module(model, module_name):
    """
    Enable a SvxLink module by name.
    """

    modules = model["modules"]["enabled"]

    if module_name not in modules:
        modules.append(module_name)

    return model


def disable_module(model, module_name):
    """
    Disable a SvxLink module by name.
    """

    modules = model["modules"]["enabled"]

    if module_name in modules:
        modules.remove(module_name)

    return model