#!/usr/bin/env python3

"""
Primary SvxLink configuration renderer for SvxLink-Dash-V4.0.
"""
from models.node_model import (
    get_installation_tones,
    is_multiport_model,
)
from renderers.template_engine import render_config_template
from services.hardware_service import get_architecture_label
import platform
from services.topology_ports import (
    get_topology_logic_name,
)


# =========================================================
# System information
# =========================================================


def get_library_path():
    architecture = get_architecture_label().strip().lower()
    machine = platform.machine().lower()

    if architecture in (
        "armhf",
        "arm64",
        "amd64",
        "i386",
    ):
        machine = architecture

    if machine in ("armv7l", "armhf"):
        return (
            "/usr/lib/arm-linux-gnueabihf/"
            "svxlink"
        )

    if machine in ("aarch64", "arm64"):
        return (
            "/usr/lib/aarch64-linux-gnu/"
            "svxlink"
        )

    if machine in ("x86_64", "amd64"):
        return (
            "/usr/lib/x86_64-linux-gnu/"
            "svxlink"
        )

    if machine in (
        "i386",
        "i486",
        "i586",
        "i686",
        "x86",
    ):
        return (
            "/usr/lib/i386-linux-gnu/"
            "svxlink"
        )

    return "/usr/lib/svxlink"

# =========================================================
# Module rendering
# =========================================================


def build_modules(model):
    """
    Render MODULES= line content.
    """

    enabled = model.get("modules", {}).get("enabled", [])

    return ",".join(enabled)


def build_modules_line(model):
    """
    Render the complete MODULES line for a single-node logic section.
    """

    enabled = model.get("modules", {}).get("enabled", [])

    if not enabled:
        return "#MODULES="

    return "MODULES=" + ",".join(enabled)


def build_modules_line_for_node(node):
    """
    Render the complete MODULES line for one multi-port node.
    """

    modules = node.get("modules", {})

    enabled = ["ModuleHelp","ModuleParrot",]

    if modules.get("echolink"):
        enabled.append("ModuleEchoLink")

    if modules.get("metar"):
        enabled.append("ModuleMetarInfo")

    if not enabled:
        return "#MODULES="

    return "MODULES=" + ",".join(enabled)
# =========================================================
# Language rendering
# =========================================================


def get_default_language(model):
    """
    Return selected default language.

    Set by /environment page.
    British Isles use en_GB.
    Australia/NZ use en_AU.
    North America uses en_US.
    """

    return (
        model.get("language", {}).get("default")
        or model.get("node", {}).get("language")
        or "en_GB"
    )
# =========================================================
# Module-specific renderers
# =========================================================


def render_echolink_module(model):
    """
    Render ModuleEchoLink section if enabled.
    """

    echolink = model.get("echolink", {})

    if not echolink.get("enabled"):
        return ""

    return render_config_template(
        "module_echolink.template",
        {
            "ECHOLINK_CALLSIGN": echolink.get("callsign", ""),
            "ECHOLINK_PASSWORD": echolink.get("password", ""),
            "ECHOLINK_SYSOPNAME": echolink.get("sysopname", ""),
            "ECHOLINK_LOCATION": echolink.get("location", ""),
            "DEFAULT_LANG": get_default_language(model),
        }
    )

# =========================================================
# METAR rendering
# =========================================================


def render_metar_module(model):
    """
    Render ModuleMetarInfo section if enabled.

    STARTDEFAULT must always contain a valid ICAO.
    AIRPORTS includes STARTDEFAULT first, followed by up to six extras.
    """

    metar = model.get("metar", {})

    if not metar.get("enabled"):
        return ""

    startdefault = metar.get("startdefault", "").strip().upper()
    extras = metar.get("airports", [])

    airports = []

    if startdefault:
        airports.append(startdefault)

    for airport in extras:
        airport = airport.strip().upper()
        if airport and airport not in airports:
            airports.append(airport)

    return render_config_template(
        "module_metar.template",
        {
            "METAR_STARTDEFAULT": startdefault,
            "METAR_AIRPORTS": ",".join(airports),
        }
    )
# =========================================================
# Ident rendering
# =========================================================


def ident_enabled(mode, ident_type):
    """
    Determine voice/cw enable flags.

    mode:
        none
        cw
        voice
        both

    ident_type:
        voice
        cw
    """

    if mode == "both":
        return 1

    if mode == ident_type:
        return 1

    return 0


# =========================================================
# Online control block
# =========================================================

def render_online_control(configuration=None):
    """
    Render optional emergency DTMF online/offline control.
    Retain the manual reference when disabled.
    """
    configuration = configuration or {}

    if configuration.get("enabled", False):
        command = configuration.get("command", "")

        if (
            not isinstance(command, str)
            or len(command) != 6
            or any(character not in "0123456789" for character in command)
        ):
            raise ValueError(
                "Emergency DTMF command must contain exactly six digits."
            )

        return "\n".join([
            "# Emergency DTMF logic control.",
            "# Append 0# to the private command to take this logic offline.",
            "# Append 1# to the private command to return this logic online.",
            "# Prefix the command with * if a module is active.",
            "# DTMF muting prevents the digits being retransmitted.",
            f"ONLINE_CMD={command}",
            "ONLINE=1",
        ])

    return "\n".join([
        "# Emergency DTMF logic control.",
        "# Replace XXXXXX with a private six-digit command.",
        "# Enter XXXXXX0# to take this logic offline.",
        "# Enter XXXXXX1# to return this logic online.",
        "# Prefix the command with * if a module is active.",
        "# DTMF muting prevents the digits being retransmitted.",
        "#ONLINE_CMD=XXXXXX",
        "#ONLINE=1",
    ])

# =========================================================
# CTCSS helpers
# =========================================================

def render_report_ctcss(model):
    """
    Render REPORT_CTCSS line if required.
    """

    squelch = model.get("squelch", {})

    if squelch.get("method") != ("ctcss"):
        return ""

    freq = squelch.get("ctcss_freq")

    if not freq:
        return ""

    return f"REPORT_CTCSS={freq}"


def render_tx_ctcss_logic(model):
    """
    Render the optional TX CTCSS logic setting.
    TX CTCSS is available only with active CTCSS SQL.
    """

    squelch = model.get("squelch", {})

    if (
        squelch.get("method") == "ctcss"
        and squelch.get("ctcss_freq")
        and squelch.get("ctcss_tx")
    ):
        return "TX_CTCSS=ALWAYS"

    return "#TX_CTCSS=ALWAYS"


def render_open_on_ctcss_line(squelch):
    """
    Enable CTCSS opening only when CTCSS is the active SQL
    detector with a configured frequency.
    """
    if (
        squelch.get("method") == "ctcss"
        and squelch.get("ctcss_freq")
    ):
        return "OPEN_ON_CTCSS=200"

    return "#OPEN_ON_CTCSS=200"


def render_open_on_sql_line(squelch):
    """
    Enable ordinary SQL opening for physical state detectors.
    CTCSS provides its own opening condition.
    """
    if squelch.get("method") in {
        "hidraw",
        "gpiod",
        "serial",
    }:
        return "OPEN_ON_SQL=200"

    return "#OPEN_ON_SQL=200"

# =========================================================
# RX rendering
# =========================================================


def render_rx_sql_block(model):
    """
    Render the selected active Standard SQL detector.
    """

    method = model.get(
        "squelch",
        {},
    ).get(
        "method",
        "gpiod",
    )

    detector_lines = {
        "hidraw": "SQL_DET=HIDRAW",
        "gpiod": "SQL_DET=GPIOD",
        "serial": "SQL_DET=SERIAL",
        "ctcss": "SQL_DET=CTCSS",
    }

    return detector_lines.get(
        method,
        "SQL_DET=GPIOD",
    )


def render_rx_ctcss_block(model):
    """
    Render the active single-port CTCSS SQL settings.

    Advanced decoder tuning remains commented for manual use.
    """

    squelch = model.get("squelch", {})

    if squelch.get("method") != "ctcss":
        return ""

    freq = squelch.get("ctcss_freq")

    if not freq:
        return ""

    return "\n".join([
        "CTCSS_MODE=3",
        f"CTCSS_FQ={freq}",
        "#CTCSS_SNR_OFFSET=0",
        "#CTCSS_SNR_OFFSETS=88.5:-1.0,136.5:-0.5",
        "#CTCSS_OPEN_THRESH=15",
        "#CTCSS_CLOSE_THRESH=9",
        "#CTCSS_BPF_LOW=60",
        "#CTCSS_BPF_HIGH=270",
        "#CTCSS_EMIT_TONE_DETECTED=0",
    ])


def render_rx_gpiod_block(model):
    """
    Render RX GPIOD block.

    Active-high COS uses PULLDOWN.
    Active-low COS uses PULLUP.

    Do not render RX GPIOD when CTCSS is selected.
    PTT GPIOD is rendered separately.
    """

    squelch_method = model.get(
        "squelch",
        {},
    ).get(
        "method",
    )

    if squelch_method != "gpiod":
        return ""

    gpio = model.get("gpio", {}).get("sql", {})

    chip = gpio.get("chip", "gpiochip0")
    line = str(gpio.get("line", 203))
    inverted = bool(gpio.get("invert", False))

    if inverted:
        line = f"!{line}"
        bias = "PULLUP"
    else:
        bias = "PULLDOWN"

    return "\n".join([
        f"SQL_GPIOD_CHIP={chip}",
        f"SQL_GPIOD_LINE={line}",
        f"SQL_GPIOD_BIAS={bias}",
    ])


def render_rx_hidraw_block(model):
    """
    Render RX HIDRAW block.
    """

    if (
        model.get("squelch", {}).get("method")
        != "hidraw"
    ):
        return ""

    hid = model.get("hidraw", {})

    device = hid.get("device", "/dev/hidraw0")
    pin = hid.get("sql_pin", "VOL_DN")
    if hid.get("sql_invert"):
        pin = f"!{pin}"

    return "\n".join([
        f"HID_DEVICE={device}",
        f"HID_SQL_PIN={pin}",
    ])


def render_commented_squelch_example(
    squelch,
    rx_name,
):
    """
    Render the selected Advanced or specialist SQL example.

    Every generated line is commented. The operator must configure,
    verify and activate the example manually.
    """

    if not isinstance(squelch, dict):
        return ""

    advanced_example = squelch.get(
        "advanced_example"
    )

    manual_detector = squelch.get(
        "manual_detector"
    )

    if advanced_example == "vox":
        return "\n".join([
            "# Advanced VOX SQL example - manual configuration required",
            "#SQL_DET=VOX",
            "#VOX_FILTER_DEPTH=20",
            "#VOX_THRESH=1000",
        ])

    if advanced_example == "siglev":
        return "\n".join([
            "# Advanced SIGLEV SQL example - manual configuration required",
            "#SQL_DET=SIGLEV",
            "#SIGLEV_DET=NOISE",
            "#SIGLEV_SLOPE=1",
            "#SIGLEV_OFFSET=0",
            "#SIGLEV_BOGUS_THRESH=120",
            "#TONE_SIGLEV_MAP=100,84,60,50,37,32,28,23,19,8",
            "#SQL_SIGLEV_OPEN_THRESH=30",
            "#SQL_SIGLEV_CLOSE_THRESH=10",
        ])

    if advanced_example == "combine":
        components = squelch.get(
            "combine_components",
            [],
        )

        component_names = [
            str(component).strip().upper()
            for component in components
            if str(component).strip()
        ]

        expression = "&".join(
            f"({rx_name}:{component})"
            for component in component_names
        )

        lines = [
            "# Advanced COMBINE SQL example - manual configuration required",
            "#SQL_DET=COMBINE",
            f"#SQL_COMBINE={expression}",
        ]

        if "VOX" in component_names:
            lines.extend([
                "",
                f"#[{rx_name}:VOX]",
                "#SQL_DET=VOX",
                "#VOX_FILTER_DEPTH=20",
                "#VOX_THRESH=1000",
            ])

        if "SIGLEV" in component_names:
            lines.extend([
                "",
                f"#[{rx_name}:SIGLEV]",
                "#SQL_DET=SIGLEV",
                "#SIGLEV_DET=NOISE",
                "#SIGLEV_SLOPE=1",
                "#SIGLEV_OFFSET=0",
                "#SIGLEV_BOGUS_THRESH=120",
                "#TONE_SIGLEV_MAP=100,84,60,50,37,32,28,23,19,8",
                "#SQL_SIGLEV_OPEN_THRESH=30",
                "#SQL_SIGLEV_CLOSE_THRESH=10",
            ])

        if "CTCSS" in component_names:
            frequency = str(
                squelch.get("ctcss_freq") or ""
            ).strip()

            lines.extend([
                "",
                f"#[{rx_name}:CTCSS]",
                "#SQL_DET=CTCSS",
                "#CTCSS_MODE=3",
                f"#CTCSS_FQ={frequency}",
                "#CTCSS_SNR_OFFSET=0",
                "#CTCSS_SNR_OFFSETS=88.5:-1.0,136.5:-0.5",
                "#CTCSS_OPEN_THRESH=15",
                "#CTCSS_CLOSE_THRESH=9",
                "#CTCSS_BPF_LOW=60",
                "#CTCSS_BPF_HIGH=270",
                "#CTCSS_EMIT_TONE_DETECTED=0",
            ])

        return "\n".join(lines)

    if manual_detector == "evdev":
        return "\n".join([
            "# Specialist EVDEV SQL example - manual configuration required",
            "#SQL_DET=EVDEV",
            "#EVDEV_DEVNAME=/dev/input/by-id/usb-SYNIC_SYNIC_Wireless_Audio-event-if03",
            "#EVDEV_OPEN=1,163,1",
            "#EVDEV_CLOSE=1,163,0",
        ])

    if manual_detector == "pty":
        return "\n".join([
            "# Specialist PTY SQL example - manual configuration required",
            "#SQL_DET=PTY",
            f"#PTY_PATH=/tmp/{rx_name.lower()}_sql",
        ])

    if manual_detector == "rtl_sdr":
        wb_rx_name = f"WbRx{rx_name[2:]}"

        return "\n".join([
            "# Specialist RTL-SDR receiver example - manual configuration required",
            f"#WBRX={wb_rx_name}",
            "",
            f"#[{wb_rx_name}]",
            "#TYPE=RtlUsb",
            "#DEV_MATCH=0",
            "#HOST=localhost",
            "#PORT=1234",
            "#CENTER_FQ=435075000",
            "#FQ_CORR=0",
            "#GAIN=0",
            "#PEAK_METER=1",
            "#SAMPLE_RATE=960000",
        ])

    return ""


def render_receiver_common_options(rx_name):
    """
    Render common active DTMF defaults and retained manual
    receiver facilities.
    """

    compressor_name = f"{rx_name}_Compressor"

    return "\n".join([
        "DTMF_DEC_TYPE=INTERNAL",
        "DTMF_MUTING=1",
        "1750_MUTING=1",
        "#DTMF_HANGTIME=40",
        "#DTMF_SERIAL=/dev/ttyS0",
        f"#DTMF_PTY=/tmp/{rx_name.lower()}_dtmf",
        "#DTMF_MAX_FWD_TWIST=8",
        "#DTMF_MAX_REV_TWIST=4",
        "#SEL5_DEC_TYPE=INTERNAL",
        "#SEL5_TYPE=ZVEI1",
        "#FQ=433475000",
        "#MODULATION=FM",
        "#OB_AFSK_ENABLE=0",
        "#OB_AFSK_VOICE_GAIN=6",
        "#IB_AFSK_ENABLE=0",
        f"#LADSPA_PLUGINS=hpf:1000,@{compressor_name}",
        "",
        f"#[{compressor_name}]",
        "#LABEL=tap_dynamics_m",
        "#Attack=4",
        "#Release=500",
        "#Offset Gain=15",
        "#Makeup Gain=15",
        "#Function=13",
    ])


def render_rx_combine_sections(model):
    """
    Render COMBINE detector subsections.
    """

    squelch = model.get("squelch", {})

    if squelch.get("method") == "gpiod_ctcss":
        return "\n\n".join([
            render_rx_ctcss_combine_block(model),
            render_rx_gpiod_combine_block(model),
        ])

    if squelch.get("method") == "serial_ctcss":
        return "\n\n".join([
            render_rx_ctcss_combine_block(model),
            render_rx_serial_combine_block(model),
        ])
    return ""


def render_rx_ctcss_combine_block(model):
    squelch = model.get("squelch", {})
    freq = squelch.get("ctcss_freq")

    if not freq:
        return ""

    return "\n".join([
        "[Rx1:CTCSS]",
        "SQL_DET=CTCSS",
        "CTCSS_MODE=4",
        f"CTCSS_FQ={freq}",
        "#CTCSS_SNR_OFFSET=0",
        "#CTCSS_SNR_OFFSETS=88.5:-1.0,136.5:-0.5",
        "#CTCSS_OPEN_THRESH=15",
        "#CTCSS_CLOSE_THRESH=9",
        "#CTCSS_BPF_LOW=60",
        "#CTCSS_BPF_HIGH=270",
        "#CTCSS_EMIT_TONE_DETECTED=0",
    ])


def render_rx_gpiod_combine_block(model):
    gpio = model.get("gpio", {}).get("sql", {})

    chip = gpio.get("chip", "gpiochip0")
    line = gpio.get("line", 203)

    return "\n".join([
        "[Rx1:GPIOD]",
        "SQL_DET=GPIOD",
        f"SQL_GPIOD_CHIP={chip}",
        f"SQL_GPIOD_LINE={line}",
    ])


def render_rx_serial_block(model):
    """
    Render RX SERIAL squelch block.
    """

    if model.get("squelch", {}).get("method") != "serial":
        return ""

    serial = model.get("serial", {})

    return "\n".join([
        "SERIAL_PORT=" + serial.get("sql_port", "/dev/ttyS0"),
        "SERIAL_PIN=" + serial.get("sql_pin", "CTS"),
        "SERIAL_SET_PINS=" + serial.get("sql_set_pins", "DTR!RTS"),
    ])


def render_rx_serial_combine_block(model):
    """
    Render RX SERIAL subsection for COMBINE squelch.
    """

    serial = model.get("serial", {})

    return "\n".join([
        "[Rx1:SERIAL]",
        "SQL_DET=SERIAL",
        "SERIAL_PORT=" + serial.get("sql_port", "/dev/ttyS0"),
        "SERIAL_PIN=" + serial.get("sql_pin", "CTS"),
        "SERIAL_SET_PINS=" + serial.get("sql_set_pins", "DTR!RTS"),
    ])
# =========================================================
# TX rendering
# =========================================================


def render_tx_ptt_block(model):
    """
    Render TX PTT block.
    """

    interface = model.get("interface", {})
    ptt_source = interface.get("ptt_source")

    if ptt_source == "hidraw":

        hid = model.get("hidraw", {})

        device = hid.get("device", "/dev/hidraw0")
        pin = str(hid.get("ptt_pin", "GPIO3")).lstrip("!")
        
        if hid.get("ptt_invert"):
            pin = f"!{pin}"

        return "\n".join([
            "PTT_TYPE=Hidraw",
            f"HID_DEVICE={device}",
            f"HID_PTT_PIN={pin}",
        ])

    gpio = model.get("gpio", {}).get("ptt", {})

    chip = gpio.get("chip", "gpiochip0")
    line = gpio.get("line", 6)

    if ptt_source == "serial":

        serial = model.get("serial", {})

        return "\n".join([
            "PTT_TYPE=SerialPin",
            "PTT_PORT=" + serial.get("ptt_port", "/dev/ttyS0"),
            "PTT_PIN=" + serial.get("ptt_pin", "DTRRTS"),
        ])
    return "\n".join([
        "PTT_TYPE=GPIOD",
        f"PTT_GPIOD_CHIP={chip}",
        f"PTT_GPIOD_LINE={line}",
    ])


def render_tx_ctcss_block(model):
    """
    Render TX-side CTCSS using the active RX CTCSS
    frequency and the upstream default level.
    """

    squelch = model.get("squelch", {})

    if (
        squelch.get("method") != "ctcss"
        or not squelch.get("ctcss_tx")
    ):
        return ""

    freq = squelch.get("ctcss_freq")

    if not freq:
        return ""

    return "\n".join([
        f"CTCSS_FQ={freq}",
        "CTCSS_LEVEL=-24",
    ])


# =========================================================
# Macros
# =========================================================

def render_macros(model):
    """
    Render macros section.
    """

    macros = model.get("macros", {})

    if not macros:
        return "[Macros]"

    macro_lines = "\n".join(
        f"{number}={command}"
        for number, command in macros.items()
    )

    return render_config_template(
        "macros.template",
        {
            "MACRO_LINES": macro_lines,
        }
    )


def render_ctcss_to_tg(configuration, example_delay=0):
    """
    Render local RF CTCSS-to-TalkGroup selection for one logic.
    """

    example_lines = (
        "#CTCSS_TO_TG=77.0:999,123.0:9990,146.2:9992\n"
        f"#CTCSS_TO_TG_DELAY={example_delay}"
    )

    if not isinstance(configuration, dict):
        return example_lines

    if not configuration.get("enabled"):
        return example_lines

    mappings = configuration.get("mappings", [])

    if not isinstance(mappings, list) or not mappings:
        return example_lines

    mapping_values = []

    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue

        tone = str(mapping.get("tone") or "").strip()
        talkgroup = str(
            mapping.get("talkgroup") or ""
        ).strip()

        if tone and talkgroup:
            mapping_values.append(
                f"{tone}:{talkgroup}"
            )

    if not mapping_values:
        return example_lines

    delay_ms = configuration.get("delay_ms", 0)

    return (
        f"CTCSS_TO_TG={','.join(mapping_values)}\n"
        f"CTCSS_TO_TG_DELAY={delay_ms}"
    )


# =========================================================
# Logic rendering
# =========================================================

def render_active_logic(model):
    """
    Render SimplexLogic or RepeaterLogic.
    """

    node_type = model.get("node", {}).get("type")
    logic_name = (
    "RepeaterLogic"
    if node_type == "repeater"
    else "SimplexLogic"
    )
    short_ident = model.get("ident", {}).get("short", {})
    long_ident = model.get("ident", {}).get("long", {})
    tones = get_installation_tones(model)
    repeater = model.get("repeater", {})
    values = {
        "LOGIC_NAME": logic_name,
        "RX_NAME": "Rx1",
        "TX_NAME": "Tx1",
        "MODULES_LINE": build_modules_line(model),
        "CALLSIGN": model["node"]["callsign"],

        "SHORT_IDENT_INTERVAL": short_ident.get("interval", 15),
        "SHORT_VOICE_ID_ENABLE": ident_enabled(
            short_ident.get("mode"),
            "voice"
        ),
        "SHORT_CW_ID_ENABLE": ident_enabled(
            short_ident.get("mode"),
            "cw"
        ),
        "SHORT_ANNOUNCE_ENABLE": 1 if short_ident.get("announce_enable", False) else 0,
        "SHORT_ANNOUNCE_FILE": short_ident.get("announce_file", ""),

        "LONG_IDENT_INTERVAL": long_ident.get("interval", 60),
        "LONG_VOICE_ID_ENABLE": ident_enabled(
            long_ident.get("mode"),
            "voice"
        ),
        "LONG_CW_ID_ENABLE": ident_enabled(
            long_ident.get("mode"),
            "cw"
        ),
        "LONG_ANNOUNCE_ENABLE": 1 if long_ident.get("announce_enable", False) else 0,
        "LONG_ANNOUNCE_FILE": long_ident.get("announce_file", ""),
        "TIME_FORMAT": model.get("time_format", "24"),

        "CW_AMP": model.get("cw", {}).get("amp", -10),
        "CW_PITCH": model.get("cw", {}).get("pitch", 650),
        "CW_CPM": model.get("cw", {}).get("cpm", 95),

        "DEFAULT_LANG": get_default_language(model),
        "RGR_SOUND_DELAY": (
            200
            if tones["courtesy_mode"] != "none"
            else 0
        ),
        "RGR_SOUND_ALWAYS": (
            1 if tones["courtesy_mode"] != "none" else 0
        ),
        "REPORT_CTCSS_LINE": render_report_ctcss(model),
        "TX_CTCSS_LINE": render_tx_ctcss_logic(model),

        "FX_GAIN_NORMAL": model.get("fx_gain_normal", 0),
        "FX_GAIN_LOW": model.get("fx_gain_low", -12),

        "ONLINE_CONTROL_BLOCK": render_online_control(
            model.get("online_control", {})
        ),
        "DTMF_CTRL_PTY": get_dtmf_ctrl_pty(model),
        "CTCSS_TO_TG_BLOCK": render_ctcss_to_tg(
            model.get("ctcss_to_tg", {}),
            example_delay=(
                0 if node_type == "repeater" else 1000
            ),
        ),
        "IDLE_TIMEOUT": repeater.get(
            "idle_timeout",
            10,
        ),
        "OPEN_ON_CTCSS_LINE": render_open_on_ctcss_line(
            model.get("squelch", {})
        ),
        "OPEN_ON_SQL_LINE": render_open_on_sql_line(
            model.get("squelch", {})
        ),
        "REPEATER_SQL_TIMEOUT": repeater.get(
            "sql_timeout",
            180,
        ),
    }
    if node_type == "repeater":
        return render_config_template(
            "repeater_logic.template",
            values
        )

    return render_config_template(
        "simplex_logic.template",
        values
    )
# =========================================================
# ICS port logic rendering
# =========================================================


def render_port_logic(model, port_id, node):
    """
    Render one SimplexLogic or RepeaterLogic section for an ICS port.
    """

    role = node.get("role", "simplex")
    logic_name = f"Port{port_id}Logic"

    ident = node.get("ident", {})
    short_ident = ident.get("short", {})
    long_ident = ident.get("long", {})

    cw = node.get("cw", {})
    tones = get_installation_tones(model)
    repeater = node.get("repeater", {})

    values = {
        "LOGIC_NAME": logic_name,
        "RX_NAME": f"Rx{port_id}",
        "TX_NAME": f"Tx{port_id}",

        "MODULES_LINE": build_modules_line_for_node(node),
        "CALLSIGN": node.get("callsign", model.get("node", {}).get("callsign", "")),

        "SHORT_IDENT_INTERVAL": short_ident.get("interval", 15),
        "SHORT_VOICE_ID_ENABLE": 1 if short_ident.get("voice_enable", False) else 0,
        "SHORT_CW_ID_ENABLE": 1 if short_ident.get("cw_enable", True) else 0,
        "SHORT_ANNOUNCE_ENABLE": 1 if short_ident.get("announce_enable", False) else 0,
        "SHORT_ANNOUNCE_FILE": short_ident.get("announce_file", ""),

        "LONG_IDENT_INTERVAL": long_ident.get("interval", 60),
        "LONG_VOICE_ID_ENABLE": 1 if long_ident.get("voice_enable", True) else 0,
        "LONG_CW_ID_ENABLE": 1 if long_ident.get("cw_enable", False) else 0,
        "LONG_ANNOUNCE_ENABLE": 1 if long_ident.get("announce_enable", False) else 0,
        "LONG_ANNOUNCE_FILE": long_ident.get("announce_file", ""),

        "TIME_FORMAT": model.get("time_format", "24"),

        "CW_AMP": cw.get("amp", -10),
        "CW_PITCH": cw.get("pitch", 650),
        "CW_CPM": cw.get("cpm", 95),

        "DEFAULT_LANG": get_default_language(model),
        "RGR_SOUND_DELAY": (
            200
            if tones["courtesy_mode"] != "none"
            else 0
        ),
        "RGR_SOUND_ALWAYS": (
            1 if tones["courtesy_mode"] != "none" else 0
        ),

        "REPORT_CTCSS_LINE": render_port_report_ctcss(node),
        "TX_CTCSS_LINE": render_port_tx_ctcss_logic(node),

        "FX_GAIN_NORMAL": model.get("fx_gain_normal", 0),
        "FX_GAIN_LOW": model.get("fx_gain_low", -12),

        "ONLINE_CONTROL_BLOCK": render_online_control(
            node.get("online_control", {})
        ),
        "DTMF_CTRL_PTY": f"/dev/shm/port{port_id}_dtmf_ctrl",
        "CTCSS_TO_TG_BLOCK": render_ctcss_to_tg(
            node.get("ctcss_to_tg", {}),
            example_delay=(
                0 if role == "repeater" else 1000
            ),
        ),
        "IDLE_TIMEOUT": repeater.get("idle_timeout", 10),
        "OPEN_ON_CTCSS_LINE": render_open_on_ctcss_line(
            node.get("squelch", {})
        ),
        "OPEN_ON_SQL_LINE": render_open_on_sql_line(
            node.get("squelch", {})
        ),
        "REPEATER_SQL_TIMEOUT": repeater.get("sql_timeout", 180),
    }

    if role == "repeater":
        return render_config_template(
            "repeater_logic.template",
            values
        )

    return render_config_template(
        "simplex_logic.template",
        values
    )


def build_modules_for_node(node):
    """
    Build the MODULES line for one multi-port node.
    """

    modules = node.get("modules", {})

    enabled = []

    if modules.get("echolink"):
        enabled.append("ModuleEchoLink")

    if modules.get("metar"):
        enabled.append("ModuleMetarInfo")

    return ",".join(enabled)


def render_port_report_ctcss(node):
    """
    Render REPORT_CTCSS for one port.
    """

    squelch = node.get("squelch", {})

    if squelch.get("ctcss_mode") in ("rx", "rx_tx"):
        return "REPORT_CTCSS=1"

    return "#REPORT_CTCSS=1"


def render_port_tx_ctcss_logic(node):
    """
    Render optional TX CTCSS for one multi-port node.
    """

    squelch = node.get("squelch", {})

    if (
        squelch.get("method") == "ctcss"
        and squelch.get("ctcss_freq")
        and squelch.get("ctcss_tx")
    ):
        return "TX_CTCSS=ALWAYS"

    return "#TX_CTCSS=ALWAYS"


def resolve_gpiod_line(model, node, label):
    """
    Resolve a stable GPIO line name to chip/line details.

    Prefer per-node data created during ICS GPIOD discovery.
    Fall back to the top-level discovered line map.
    Finally fall back to the stable line name itself.
    """

    gpio = node.get("gpio", {})

    if label.startswith("RX_"):
        chip = gpio.get("cos_chip", "")
        line = (
            gpio.get("cos_line")
            or gpio.get("cos")
            or label
        )
        offset = gpio.get("cos_offset")

    elif label.startswith("TX_"):
        chip = gpio.get("ptt_chip", "")
        line = (
            gpio.get("ptt_line")
            or gpio.get("ptt")
            or label
        )
        offset = gpio.get("ptt_offset")

    else:
        chip = ""
        line = label
        offset = None

    if chip:
        return {
            "chip": chip,
            "line": line,
            "offset": offset,
        }

    resolved = (
        model.get("gpiod", {})
        .get("resolved_lines", {})
        .get(label, {})
    )

    return {
        "chip": resolved.get("chip", ""),
        "line": resolved.get("line", line),
        "offset": resolved.get("offset", offset),
    }


def render_multiport_logic_sections(model):
    """
    Render all radio logic sections for an explicit multi-port model.
    """

    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    logic_names = []
    logic_sections = []

    for port in enabled_ports:
        port_id = str(port)
        node = nodes.get(port_id, {})

        if not node:
            continue

        logic_name = f"Port{port_id}Logic"

        logic_names.append(logic_name)
        logic_sections.append(
            render_port_logic(model, port_id, node)
        )

    return {
        "logics": ",".join(logic_names),
        "sections": "\n\n".join(logic_sections),
    }


def render_port_rx_section(model, port_id, node):
    """
    Render one Rx section for a multi-port node.
    """

    audio = node.get("audio", {})
    squelch = node.get("squelch", {})

    rx_name = f"Rx{port_id}"
    rx_label = f"RX_{port_id}"

    audio_dev = audio.get("rx_audio", f"alsa:rx{port_id}")

    method = squelch.get("method", "gpiod")
    ctcss_freq = squelch.get("ctcss_freq")

    lines = [
        f"[{rx_name}]",
        "TYPE=Local",
        "#RX_ID=?",
        f"AUDIO_DEV={audio_dev}",
        "AUDIO_CHANNEL=0",
        "#AUDIO_DEV_KEEP_OPEN=0",
        "#LIMITER_THRESH=-6",
        f"DEEMPHASIS={1 if audio.get('deemphasis', False) else 0}",
    ]

    if method == "hidraw":
        hidraw = node.get("hidraw", {})

        try:
            hidraw_index = int(port_id) - 1
        except ValueError:
            hidraw_index = 0

        device = hidraw.get("device", f"/dev/hidraw{hidraw_index}")
        pin = hidraw.get("sql_pin", "VOL_DN")

        if hidraw.get("sql_invert"):
            pin = f"!{pin}"

        lines.extend([
            "SQL_DET=HIDRAW",
            f"HID_DEVICE={device}",
            f"HID_SQL_PIN={pin}",
        ])
    elif method == "serial":
        serial = node.get("serial", {})

        lines.extend([
            "SQL_DET=SERIAL",
            "SERIAL_PORT=" + serial.get("sql_port", "/dev/ttyS0"),
            "SERIAL_PIN=" + serial.get("sql_pin", "CTS"),
            "SERIAL_SET_PINS=" + serial.get("sql_set_pins", "DTR!RTS"),
        ])

    elif method == "ctcss":
        lines.append("SQL_DET=CTCSS")

    else:
        resolved = resolve_gpiod_line(
            model,
            node,
            rx_label,
        )

        sql_line = resolved.get("line", rx_label)

        if node.get("gpio", {}).get("cos_invert"):
            # External COS is active-low.
            sql_line = f"!{sql_line}"
            sql_bias = "PULLUP"
        else:
            # External COS is active-high.
            sql_bias = "PULLDOWN"

        lines.extend([
            "SQL_DET=GPIOD",
            f"SQL_GPIOD_CHIP={resolved.get('chip', '')}",
            f"SQL_GPIOD_LINE={sql_line}",
            f"SQL_GPIOD_BIAS={sql_bias}",
        ])

    lines.extend([
        "SQL_START_DELAY=0",
        "SQL_DELAY=0",
        "SQL_HANGTIME=200",
        "#SQL_EXTENDED_HANGTIME=1000",
        "#SQL_EXTENDED_HANGTIME_THRESH=15",
        "#SQL_TIMEOUT=0",
        f"SQL_TAIL_ELIM={model.get('sql_tail_elim', 270)}",
        "#GPIO_PATH=/sys/class/gpio",
        "#GPIO_SQL_PIN=gpio30",
        "#PREAMP=6",
    ])

    if method == "ctcss" and ctcss_freq:
        lines.extend([
            "CTCSS_MODE=3",
            f"CTCSS_FQ={ctcss_freq}",
            "#CTCSS_SNR_OFFSET=0",
            "#CTCSS_SNR_OFFSETS=88.5:-1.0,136.5:-0.5",
            "#CTCSS_OPEN_THRESH=15",
            "#CTCSS_CLOSE_THRESH=9",
            "#CTCSS_BPF_LOW=60",
            "#CTCSS_BPF_HIGH=270",
            "#CTCSS_EMIT_TONE_DETECTED=0",
        ])

    lines.extend([
        "",
        render_receiver_common_options(
            rx_name
        ),
    ])

    manual_example = (
        render_commented_squelch_example(
            squelch,
            rx_name,
        )
    )

    if manual_example:
        lines.extend([
            "",
            manual_example,
        ])

    return "\n".join(lines)


def render_transmitter_common_options(tx_name):
    """
    Render retained manual transmitter facilities.
    """

    compressor_name = f"{tx_name}_Compressor"

    return "\n".join([
        "#DTMF_TONE_LENGTH=100",
        "#DTMF_TONE_SPACING=50",
        "#DTMF_DIGIT_PWR=-15",
        "#MASTER_GAIN=0.0",
        "#OB_AFSK_ENABLE=0",
        "#OB_AFSK_VOICE_GAIN=-6",
        "#OB_AFSK_LEVEL=-12",
        "#OB_AFSK_TX_DELAY=100",
        "#IB_AFSK_ENABLE=0",
        "#IB_AFSK_LEVEL=-6",
        "#IB_AFSK_TX_DELAY=100",
        f"#LADSPA_PLUGINS=hpf:1000,@{compressor_name}",
        "",
        f"#[{compressor_name}]",
        "#LABEL=tap_dynamics_m",
        "#Attack=4",
        "#Release=500",
        "#Offset Gain=15",
        "#Makeup Gain=15",
        "#Function=13",
    ])


def render_port_tx_section(model, port_id, node):
    """
    Render one Tx section for a multi-port node.
    """

    audio = node.get("audio", {})
    squelch = node.get("squelch", {})

    tx_name = f"Tx{port_id}"
    tx_label = f"TX_{port_id}"

    audio_dev = audio.get("tx_audio", f"alsa:tx{port_id}")

    method = squelch.get("method", "gpiod")

    if (
        model.get("hardware", {}).get("family")
        == "ics"
    ):
        ptt_source = "gpiod"
    else:
        ptt_source = (
            node.get(
                "interface",
                {},
            ).get(
                "ptt_source"
            )
        )

        if ptt_source not in {
            "hidraw",
            "gpiod",
            "serial",
        }:
            # Migration fallback for models saved before
            # per-port PTT selection was introduced.
            if method in {
                "hidraw",
                "gpiod",
                "serial",
            }:
                ptt_source = method
            else:
                ptt_source = "gpiod"

    ctcss_freq = squelch.get("ctcss_freq")

    lines = [
        f"[{tx_name}]",
        "TYPE=Local",
        "#TX_ID=T",
        f"AUDIO_DEV={audio_dev}",
        "AUDIO_CHANNEL=0",
        "#AUDIO_DEV_KEEP_OPEN=0",
        "#LIMITER_THRESH=-6",
    ]

    if ptt_source == "hidraw":
        hidraw = node.get("hidraw", {})

        try:
            hidraw_index = int(port_id) - 1
        except ValueError:
            hidraw_index = 0

        device = hidraw.get("device", f"/dev/hidraw{hidraw_index}")
        pin = hidraw.get("ptt_pin", "GPIO3")

        if hidraw.get("ptt_invert"):
            pin = f"!{pin}"

        lines.extend([
            "PTT_TYPE=Hidraw",
            f"HID_DEVICE={device}",
            f"HID_PTT_PIN={pin}",
        ])

    elif ptt_source == "serial":
        serial = node.get("serial", {})

        lines.extend([
            "PTT_TYPE=SerialPin",
            "PTT_PORT="
            + serial.get(
                "ptt_port",
                "/dev/ttyS0",
            ),
            "PTT_PIN="
            + serial.get(
                "ptt_pin",
                "DTRRTS",
            ),
        ])

    else:
        resolved = resolve_gpiod_line(
            model,
            node,
            tx_label,
        )

        ptt_line = resolved.get("line", tx_label)

        if not node.get("gpio", {}).get("ptt_invert"):
            ptt_line = f"!{ptt_line}"

        lines.extend([
            "PTT_TYPE=GPIOD",
            f"PTT_GPIOD_CHIP={resolved.get('chip', '')}",
            f"PTT_GPIOD_LINE={ptt_line}",
        ])

    lines.extend([
        "#SERIAL_SET_PINS=DTR!RTS",
        "#GPIO_PATH=/sys/class/gpio",
        "#PTT_HANGTIME=1000",
        "#TIMEOUT=0",
        f"TX_DELAY={node.get('tx_delay', 500)}",
    ])

    if (
        method == "ctcss"
        and squelch.get("ctcss_tx")
        and ctcss_freq
    ):
        lines.extend([
            f"CTCSS_FQ={ctcss_freq}",
            "CTCSS_LEVEL=-24",
        ])

    lines.extend([
        (
            "PREEMPHASIS=1"
            if audio.get("preemphasis", False)
            else "PREEMPHASIS=0"
        ),
        "",
        render_transmitter_common_options(
            tx_name
        ),
    ])

    return "\n".join(lines)


def render_multiport_rx_tx_sections(model):
    """
    Render all Rx and Tx sections for an explicit multi-port model.
    """

    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    rx_sections = []
    tx_sections = []

    for port in enabled_ports:
        port_id = str(port)
        node = nodes.get(port_id, {})

        if not node:
            continue

        rx_sections.append(
            render_port_rx_section(model, port_id, node)
        )

        tx_sections.append(
            render_port_tx_section(model, port_id, node)
        )

    return {
        "rx_sections": "\n\n".join(rx_sections),
        "tx_sections": "\n\n".join(tx_sections),
    }

# =========================================================
# DTMF Sender Renderer
# =========================================================


def get_dtmf_ctrl_pty(model):
    node_type = model.get("node", {}).get("type")

    if node_type == "repeater":
        return "/dev/shm/repeater_dtmf_ctrl"

    return "/dev/shm/simplex_dtmf_ctrl"
# =========================================================
# Reflector rendering
# =========================================================


def get_primary_callsign(model):
    """
    Return the callsign representing the installation as a whole.

    Multi-port installations use the explicitly selected primary port.
    Older models fall back to the first enabled port with a callsign.
    Single-port installations use the configured node callsign.
    """

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})

    primary_port_id = str(
        model.get("installation", {}).get("primary_port_id") or ""
    )

    if primary_port_id in enabled_ports:
        primary_callsign = (
            nodes.get(primary_port_id, {}).get("callsign")
        )

        if primary_callsign:
            return str(primary_callsign).strip().upper()

    for port_id in enabled_ports:
        callsign = nodes.get(port_id, {}).get("callsign")

        if callsign:
            return str(callsign).strip().upper()

    callsign = (
        model.get("node", {}).get("callsign")
        or model.get("ident", {}).get("callsign")
        or "NOCALL"
    )

    return str(callsign).strip().upper()


def get_primary_port_id(model):
    """
    Return the explicitly selected primary port for a multi-port build.

    Older models fall back to the first enabled port. A single-port
    installation does not require a port identifier here.
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

    if enabled_ports:
        return enabled_ports[0]

    return None


def get_primary_logic_name(model):
    """
    Return the logic section representing the installation.

    Multi-port logic sections currently use PortNLogic names.
    """

    primary_port_id = get_primary_port_id(model)

    if primary_port_id is not None:
        return f"Port{primary_port_id}Logic"

    if model.get("node", {}).get("type") == "repeater":
        return "RepeaterLogic"

    return "SimplexLogic"


def get_location_info_callsign(model):
    """
    Return the APRS identity for LocationInfo.

    EchoLink -R and -L callsigns become ER- and EL- object names.
    Without EchoLink, use the primary installation callsign.
    """

    echolink = model.get("echolink", {})

    if echolink.get("enabled"):
        echolink_callsign = str(
            echolink.get("callsign") or ""
        ).strip().upper()

        if echolink_callsign.endswith("-R"):
            return f"ER-{echolink_callsign[:-2]}"

        if echolink_callsign.endswith("-L"):
            return f"EL-{echolink_callsign[:-2]}"

    return get_primary_callsign(model)


def render_location_info(model):
    """
    Render the optional installation-wide LocationInfo section.

    LocationInfo represents the selected primary port in a multi-port
    installation, or the only radio logic in a single-port installation.
    """

    location_info = model.get("location_info", {})

    if not location_info.get("enabled"):
        return ""

    node_info = model.get("node_info", {})
    primary_port_id = get_primary_port_id(model)
    primary_node = {}

    if primary_port_id is not None:
        primary_node = model.get("nodes", {}).get(primary_port_id, {})

    primary_role = (
        primary_node.get("role")
        or model.get("node", {}).get("type")
        or "simplex"
    )

    tx_frequency = str(
        node_info.get("tx_freq")
        or primary_node.get("tx_freq")
        or ""
    ).strip()

    tx_offset_raw = location_info.get("tx_offset_khz", 0)

    try:
        tx_offset = int(tx_offset_raw)
    except (TypeError, ValueError):
        try:
            tx_offset = int(float(str(tx_offset_raw).strip()))
        except (TypeError, ValueError):
            tx_offset = 0

    if tx_offset == 0:
        tx_offset_value = "0"
    else:
        tx_offset_value = f"{tx_offset:+d}"

    tx_power = str(node_info.get("tx_power") or "0").strip()

    for suffix in (
        "Watts",
        "Watt",
        "watts",
        "watt",
        "W",
        "w",
    ):
        if tx_power.endswith(suffix):
            tx_power = tx_power[:-len(suffix)].strip()
            break

    if tx_power in ("", "None"):
        tx_power = "0"

    antenna_direction = str(
        node_info.get("antenna_direction") or "omni"
    ).strip().lower()

    if not antenna_direction or antenna_direction == "omni":
        antenna_direction = "-1"

    antenna_height = str(node_info.get("antenna_height") or "0").strip()
    if not antenna_height:
        antenna_height = "0"

    antenna_height_unit = str(
        location_info.get("antenna_height_unit") or "m"
    ).strip().lower()

    if antenna_height_unit not in ("m", "feet"):
        antenna_height_unit = "m"

    antenna_height_value = f"{antenna_height}{antenna_height_unit}"

    symbol = "/r" if primary_role == "repeater" else "/n"

    echolink_enabled = bool(model.get("echolink", {}).get("enabled"))
    publish_echolink_status = bool(
        location_info.get("publish_echolink_status")
    )
    status_server = str(
        location_info.get("status_server_list") or ""
    ).strip()

    if publish_echolink_status and echolink_enabled and status_server:
        status_server_line = f"STATUS_SERVER_LIST={status_server}"
    else:
        status_server_line = (
            f"#STATUS_SERVER_LIST={status_server}"
            if status_server
            else "#STATUS_SERVER_LIST="
        )

    aprs_server = str(location_info.get("aprs_server_list") or "").strip()
    aprs_server_line = (
        f"APRS_SERVER_LIST={aprs_server}"
        if aprs_server
        else "#APRS_SERVER_LIST="
    )

    comment = str(location_info.get("comment") or "").strip()
    comment_line = (
        f"COMMENT={comment}"
        if comment
        else "#COMMENT=SvxLink Node"
    )

    return render_config_template(
        "location_info.template",
        {
            "STATUS_SERVER_LINE": status_server_line,
            "APRS_SERVER_LINE": aprs_server_line,
            "LON_POSITION": str(node_info.get("long_dms") or "").strip(),
            "LAT_POSITION": str(node_info.get("lat_dms") or "").strip(),
            "CALLSIGN": get_location_info_callsign(model),
            "FREQUENCY": tx_frequency or "0",
            "TX_OFFSET": tx_offset_value,
            "TX_POWER": tx_power or "0",
            "ANTENNA_GAIN": str(location_info.get("antenna_gain") or "0").strip(),
            "ANTENNA_HEIGHT": antenna_height_value,
            "ANTENNA_DIR": antenna_direction,
            "BEACON_INTERVAL": location_info.get("beacon_interval", 10),
            "SYMBOL": symbol,
            "TONE": "0",
            "PRIMARY_LOGIC": get_primary_logic_name(model),
            "COMMENT_LINE": comment_line,
        },
    )


def render_reflector_logic(model):
    """
    Render the route-specific ReflectorLogic section.

    Route-specific settings are authoritative. Legacy flat fields
    remain available only as migration fallback.
    """

    reflector = model.get("reflector", {})

    if not reflector.get("enabled"):
        return ""

    route = str(
        reflector.get("route") or ""
    ).strip().lower()

    if route not in (
        "federation",
        "v2",
        "v3",
    ):
        # Legacy enabled reflectors without an explicit route used
        # Protocol 2 authentication.
        route = "v2"

    route_settings = reflector.get(route, {})

    if not isinstance(route_settings, dict):
        route_settings = {}

    def connection_value(key, default=""):
        value = route_settings.get(key)

        if value not in (
            None,
            "",
        ):
            return value

        value = reflector.get(key)

        if value not in (
            None,
            "",
        ):
            return value

        return default

    operational = reflector.get(
        "operational",
        {},
    )

    if not isinstance(operational, dict):
        operational = {}

    def operational_value(key, default):
        if key in operational:
            return operational[key]

        if key in reflector:
            return reflector[key]

        if key in route_settings:
            return route_settings[key]

        return default

    monitor_tgs = operational_value(
        "monitor_tgs",
        [],
    )

    if isinstance(monitor_tgs, list):
        monitor_tgs = ",".join(
            str(talkgroup).strip()
            for talkgroup in monitor_tgs
            if str(talkgroup).strip()
        )
    elif monitor_tgs is None:
        monitor_tgs = ""
    else:
        monitor_tgs = str(
            monitor_tgs
        ).strip()

    tg_select_timeout = operational.get(
        "tg_select_timeout",
        model.get("tg_timeout", 60),
    )

    values = {
        "REFLECTOR_HOST": connection_value(
            "host"
        ),
        "REFLECTOR_PORT": connection_value(
            "port"
        ),
        "CALLSIGN": get_primary_callsign(
            model
        ),
        "DEFAULT_TG": operational_value(
            "default_tg",
            0,
        ),
        "MONITOR_TGS": monitor_tgs,
        "TG_SELECT_TIMEOUT": (
            tg_select_timeout
        ),
        "TG_SELECT_INHIBIT_TIMEOUT": 60,
        "DEFAULT_LANG": get_default_language(
            model
        ),
    }

    if route == "v3":
        subject = route_settings.get(
            "subject",
            {},
        )

        if not isinstance(subject, dict):
            subject = {}

        values.update({
            "CERT_GIVEN_NAME": subject.get(
                "given_name",
                "",
            ),
            "CERT_SURNAME": subject.get(
                "surname",
                "",
            ),
            "CERT_ORGANIZATIONAL_UNIT": subject.get(
                "organizational_unit",
                "",
            ),
            "CERT_ORGANIZATION": subject.get(
                "organization",
                "",
            ),
            "CERT_LOCALITY": subject.get(
                "locality",
                "",
            ),
            "CERT_STATE_OR_PROVINCE": subject.get(
                "state_or_province",
                "",
            ),
            "CERT_COUNTRY": subject.get(
                "country",
                "",
            ),
            "CERT_EMAIL": subject.get(
                "email",
                "",
            ),
        })

        template_name = (
            "reflector_logic_v3.template"
        )

    else:
        values["REFLECTOR_AUTH_KEY"] = (
            connection_value("auth_key")
        )

        template_name = (
            "reflector_logic.template"
        )

    return render_config_template(
        template_name,
        values,
    )


def render_link_to_reflector(model):
    """
    Render LinkToReflector section if reflector is enabled.
    """

    if not model.get("reflector", {}).get("enabled"):
        return ""

    node_type = model.get("node", {}).get("type")

    active_logic_name = (
        "RepeaterLogic"
        if node_type == "repeater"
        else "SimplexLogic"
    )

    values = {
        "CONNECT_LOGICS": (
            f"{active_logic_name}:9,"
            "ReflectorLogic"
        ),
        "DEFAULT_ACTIVE": 1,
        "TIMEOUT": 300,
        "ACTIVATE_ON_ACTIVITY": active_logic_name,
    }

    return render_config_template(
        "link_to_reflector.template",
        values
    )


def render_multiport_link_to_reflector(
    model,
    active_logics=None,
):
    """
    Render the single installation-wide LinkToReflector section.

    Only ports explicitly assigned to the reflector link are
    connected. ReflectorLogic is added exactly once.
    """

    if not model.get("reflector", {}).get("enabled"):
        return ""

    topology = model.get("topology", {})
    reflector_link = topology.get(
        "reflector_link",
        {},
    )

    reflector_ports = reflector_link.get(
        "ports",
        [],
    )

    connect_logics = []

    for port_id in reflector_ports:
        logic_name = get_topology_logic_name(
            model,
            port_id,
        )

        if logic_name:
            connect_logics.append(
                f"{logic_name}:9"
            )

    connect_logics.append("ReflectorLogic")

    primary_logic = get_primary_logic_name(model)

    default_active = (
        1
        if reflector_link.get(
            "default_active",
            True,
        )
        else 0
    )

    timeout = reflector_link.get(
        "timeout",
        300,
    )

    values = {
        "CONNECT_LOGICS": ",".join(
            connect_logics
        ),
        "DEFAULT_ACTIVE": default_active,
        "TIMEOUT": timeout,
        "ACTIVATE_ON_ACTIVITY": primary_logic,
    }

    return render_config_template(
        "link_to_reflector.template",
        values,
    )


def render_local_links(model):
    """
    Render every operator-defined local radio link.

    Each member receives command prefix 9, providing 90# to
    deactivate and 91# to activate the link.
    """

    topology = model.get("topology", {})
    local_links = topology.get("local_links", [])

    if not isinstance(local_links, list):
        return ""

    rendered_links = []

    for local_link in local_links:
        if not isinstance(local_link, dict):
            continue

        link_name = str(
            local_link.get("name") or ""
        ).strip()

        if not link_name:
            continue

        member_ports = local_link.get("ports", [])

        if not isinstance(member_ports, list):
            continue

        connect_logics = []

        for port_id in member_ports:
            logic_name = get_topology_logic_name(
                model,
                port_id,
            )

            if logic_name:
                connect_logics.append(
                    f"{logic_name}:9"
                )

        if not connect_logics:
            continue

        default_active = (
            1
            if local_link.get(
                "default_active",
                True,
            )
            else 0
        )

        timeout = local_link.get("timeout", 300)

        rendered_links.append(
            render_config_template(
                "local_link.template",
                {
                    "LINK_NAME": link_name,
                    "CONNECT_LOGICS": ",".join(
                        connect_logics
                    ),
                    "DEFAULT_ACTIVE": default_active,
                    "TIMEOUT": timeout,
                },
            )
        )

    return "\n\n".join(rendered_links)


def render_topology_links_line(model):
    """
    Render the GLOBAL LINKS setting from the saved topology.
    """

    topology = model.get("topology", {})
    link_names = []

    reflector = model.get("reflector", {})
    reflector_link = topology.get(
        "reflector_link",
        {},
    )

    if (
        reflector.get("enabled")
        and isinstance(reflector_link, dict)
        and reflector_link.get("ports")
    ):
        link_names.append("LinkToReflector")

    local_links = topology.get("local_links", [])

    if isinstance(local_links, list):
        for local_link in local_links:
            if not isinstance(local_link, dict):
                continue

            link_name = str(
                local_link.get("name") or ""
            ).strip()

            if link_name:
                link_names.append(link_name)

    if not link_names:
        return "#LINKS="

    return "LINKS=" + ",".join(link_names)


def render_multiport_svxlink_config(model):
    """
    Render final svxlink.conf text for ICS multi-port builds.
    """

    logic_result = render_multiport_logic_sections(model)
    audio_result = render_multiport_rx_tx_sections(model)

    reflector_enabled = bool(
        model.get("reflector", {}).get("enabled")
    )

    active_logics = [
        logic.strip()
        for logic in logic_result["logics"].split(",")
        if logic.strip()
    ]

    global_logics = list(active_logics)

    if reflector_enabled and "ReflectorLogic" not in global_logics:
        global_logics.append("ReflectorLogic")

    links_line = render_topology_links_line(
        model
    )

    location_info_enabled = bool(
        model.get("location_info", {}).get("enabled")
    )

    location_info_line = (
        "LOCATION_INFO=LocationInfo"
        if location_info_enabled
        else "#LOCATION_INFO=LocationInfo"
    )
    values = {
        "LOGIC_CORE_PATH": get_library_path(),
        "LOGICS": ",".join(global_logics),
        "LINKS_LINE": links_line,
        "LOCATION_INFO_LINE": location_info_line,
        "LOCATION_INFO_SECTION": render_location_info(model),

        "ACTIVE_LOGIC_SECTION": logic_result["sections"],

        "REFLECTOR_LOGIC_SECTION": (
            render_reflector_logic(model)
            if reflector_enabled
            else ""
        ),

        "LINK_TO_REFLECTOR_SECTION": (
            render_multiport_link_to_reflector(model, active_logics)
            if reflector_enabled
            else ""
        ),

        "LOCAL_LINK_SECTIONS": render_local_links(
            model
        ),

        "RX_SECTIONS": audio_result["rx_sections"],
        "TX_SECTIONS": audio_result["tx_sections"],

        "MACROS_SECTION": render_macros(model),

        "SPECIALIST_REFERENCE_SECTIONS": (
            render_specialist_reference_sections()
        ),
    }

    return normalise_config_spacing(
        render_config_template(
            "svxlink_multiport.conf.template",
            values,
        )
    )


def render_specialist_reference_sections():
    """
    Render the shared commented manual-reference sections.
    """

    return render_config_template(
        "specialist_reference.template",
        {},
    )


# =========================================================
# Final configuration renderer
# =========================================================

def normalise_config_spacing(rendered_text):
    """
    Give the completed configuration consistent upstream-style spacing.

    Trailing whitespace is removed, consecutive blank lines are reduced
    to one, and the file is terminated by exactly one newline.
    """

    output_lines = []
    previous_blank = False

    for source_line in str(rendered_text).splitlines():
        line = source_line.rstrip()
        blank = not line

        if blank and previous_blank:
            continue

        output_lines.append(line)
        previous_blank = blank

    while output_lines and not output_lines[0]:
        output_lines.pop(0)

    while output_lines and not output_lines[-1]:
        output_lines.pop()

    return "\n".join(output_lines) + "\n"


def render_svxlink_config(model):
    """
    Render final svxlink.conf text.
    """
    if is_multiport_model(model):
        return render_multiport_svxlink_config(
            model
        )

    node_type = model.get("node", {}).get("type")

    logic_name = (
        "RepeaterLogic"
        if node_type == "repeater"
        else "SimplexLogic"
    )
    logics = logic_name

    if model.get("reflector", {}).get("enabled"):
        logics = f"{logic_name},ReflectorLogic"
        
    reflector_enabled = model.get("reflector", {}).get("enabled")

    links_line = (
        "LINKS=LinkToReflector"
        if reflector_enabled
        else "#LINKS=LinkToReflector"
    )
    location_info_enabled = bool(
        model.get("location_info", {}).get("enabled")
    )

    location_info_line = (
        "LOCATION_INFO=LocationInfo"
        if location_info_enabled
        else "#LOCATION_INFO=LocationInfo"
    )
    values = {
        "LOGIC_CORE_PATH": get_library_path(),
        "LOGICS": logics,
        "LINKS_LINE": links_line,
        "LOCATION_INFO_LINE": location_info_line,
        "LOCATION_INFO_SECTION": render_location_info(model),

        "ACTIVE_LOGIC_SECTION": render_active_logic(model),

        "REFLECTOR_LOGIC_SECTION": render_reflector_logic(model),

        "LINK_TO_REFLECTOR_SECTION": render_link_to_reflector(model),
        "AUDIO_DEV": (
            model.get("audio", {}).get("audio_dev")
            or "alsa:plughw:0"
        ),
        "AUDIO_CHANNEL": model.get(
            "audio",
            {},
        ).get(
            "audio_channel",
            0,
        ),

        "DEEMPHASIS": 1 if model.get("audio", {}).get("deemphasis", False) else 0,
        "PREEMPHASIS": 1 if model.get("audio", {}).get("preemphasis", False) else 0,
        "TX_DELAY": model.get(
            "tx_delay",
            500,
        ),
        "RX_SQL_BLOCK": render_rx_sql_block(model),
        "RX_CTCSS_BLOCK": render_rx_ctcss_block(model),
        "RX_GPIOD_BLOCK": render_rx_gpiod_block(model),
        "RX_HIDRAW_BLOCK": render_rx_hidraw_block(model),
        "RX_SERIAL_BLOCK": render_rx_serial_block(model),
        "RX_MANUAL_SQL_EXAMPLE": (
            render_commented_squelch_example(
                model.get("squelch", {}),
                "Rx1",
            )
        ),

        "TX_PTT_BLOCK": render_tx_ptt_block(model),
        "TX_CTCSS_BLOCK": render_tx_ctcss_block(model),
        "TX_COMMON_OPTIONS": (
            render_transmitter_common_options(
                "Tx1"
            )
        ),
        "SQL_TAIL_ELIM": model.get(
            "sql_tail_elim",
            270,
        ),
        "RX_COMMON_OPTIONS": (
            render_receiver_common_options(
                "Rx1"
            )
        ),

        "MACROS_SECTION": render_macros(model),

        "SPECIALIST_REFERENCE_SECTIONS": (
            render_specialist_reference_sections()
        ),
    }

    return normalise_config_spacing(
        render_config_template(
            "svxlink.conf.template",
            values,
        )
    )