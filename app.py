#!/usr/bin/env python3

from platform import node
from pyexpat import model

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pathlib import Path
import shutil
import datetime
import json
import urllib.error
import urllib.request
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
                                                                                       
from services.sound_discovery import (
    discover_sound_cards,
    discover_default_audio_dev,
    apply_safe_baseline,
    set_slider_control,
)
from services.ident_audio_service import save_ident_upload
from services.svxlink_config_discovery import (
    DEFAULT_SVXLINK_CONFIG,
    discover_audio_sections,
)

from services.sound_calibration import (
    get_svxlink_service_state,
    stop_svxlink_for_calibration,
    restart_svxlink_after_calibration,
    start_devcal_session,
    stop_devcal_session,
    get_devcal_output,
    devcal_is_running,
    get_devcal_mode,
    get_devcal_tx_state,
    toggle_devcal_tx,
)

from services.hardware_profile_service import (
    list_hardware_profiles,
    load_hardware_profile,
)
from services.dual_usb_service import (
    inspect_dual_usb_hardware,
)
from services.model_store import (
    load_node_model,
    save_node_model,
    CTCSS_TONES,
    normalise_ctcss_tone,
)
from services.squelch_configuration import (
    parse_squelch_form,
)
from services.build_svxlink import (
    build_svxlink_configuration,
    validate_build,
)

from models.node_model import (
    ctcss_talkgroup_selection_available,
    get_installation_tones,
    validate_ctcss_talkgroup_configuration,
)
## Wifi
from services.wifi_service import (
    wifi_scan,
    connection_list,
    wifi_status,
    wifi_on,
    connect_wifi,
    switch_wifi,
    delete_wifi,
    hotspot_status,
    start_hotspot,
    stop_hotspot,
)

from services.talkgroup_service import load_talkgroups, save_talkgroups
from services.macro_service import (
    classify_macro_command,
    build_macro_command,
)
from services.dtmf_service import send_dtmf
from services.status_service import get_runtime_status
from services.activity_service import get_reflector_activity
from services.hardware_service import get_system_info
from services.ics_prepare_service import (
    build_ics_status,
    configure_pcm1803,
    configure_audio_boot,
    get_ics_profiles,
    set_overlay,
    enable_i2c,
)
from services.nanopi_prepare_service import (
    build_nanopi_status,
    configure_boot,
)
from services.service_account_prepare_service import (
    prepare_service_account,
)
from services.log_service import get_svxlink_log_path
from services.metar_validation import (
    MetarVerificationUnavailable,
    find_unavailable_metar_airports,
    is_valid_icao_format,
)
from services.gpio_service import (
    flatten_gpio_lines,
    prepare_gpio_lines,
    update_model_gpiod_discovery,
)
from services.node_info_service import (
    get_primary_port_id,
)
from services.node_info_validation import (
    validate_node_information,
)
from services.topology_ports import (
    get_topology_memberships,
    get_topology_ports,
)
from services.topology_validation import (
    get_incomplete_topology_ports,
    validate_local_link_name,
    validate_topology,
)
from services.transmitter_configuration import (
    parse_tx_delay,
)
from renderers.svxlink_renderer import (
    get_primary_callsign,
)
from services.version_service import get_version_info

import subprocess
import hw_platforms
from services.system_service import (
    restart_services,
    reboot_device,
    shutdown_device,
    schedule_reboot,
)
from data.metar_airports import METAR_REGIONS
from data.timezones import TIMEZONES


# =========================================================
# Core paths
# =========================================================

APP_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_ROOT / "templates"
STATIC_DIR = APP_ROOT / "static"

CONFIG_DIR = APP_ROOT / "config"
MODEL_FILE = CONFIG_DIR / "node_model.json"
MODEL_BACKUP_DIR = CONFIG_DIR / "backups"
# =========================================================
# Supported CTCSS frequencies
# =========================================================
CTCSS_FREQUENCIES = [
    ("", "None / disabled"),
    ("67.0", "67.0 Hz"),
    ("69.3", "69.3 Hz"),
    ("71.9", "71.9 Hz"),
    ("74.4", "74.4 Hz"),
    ("77.0", "77.0 Hz"),
    ("79.7", "79.7 Hz"),
    ("82.5", "82.5 Hz"),
    ("85.4", "85.4 Hz"),
    ("88.5", "88.5 Hz"),
    ("91.5", "91.5 Hz"),
    ("94.8", "94.8 Hz"),
    ("97.4", "97.4 Hz"),
    ("100.0", "100.0 Hz"),
    ("103.5", "103.5 Hz"),
    ("107.2", "107.2 Hz"),
    ("110.9", "110.9 Hz"),
    ("114.8", "114.8 Hz"),
    ("118.8", "118.8 Hz"),
    ("123.0", "123.0 Hz"),
    ("127.3", "127.3 Hz"),
    ("131.8", "131.8 Hz"),
    ("136.5", "136.5 Hz"),
    ("141.3", "141.3 Hz"),
    ("146.2", "146.2 Hz"),
    ("151.4", "151.4 Hz"),
    ("156.7", "156.7 Hz"),
    ("159.8", "159.8 Hz"),
    ("162.2", "162.2 Hz"),
    ("165.5", "165.5 Hz"),
    ("167.9", "167.9 Hz"),
    ("171.3", "171.3 Hz"),
    ("173.8", "173.8 Hz"),
    ("177.3", "177.3 Hz"),
    ("179.9", "179.9 Hz"),
    ("183.5", "183.5 Hz"),
    ("186.2", "186.2 Hz"),
    ("189.9", "189.9 Hz"),
    ("192.8", "192.8 Hz"),
    ("196.6", "196.6 Hz"),
    ("199.5", "199.5 Hz"),
    ("203.5", "203.5 Hz"),
    ("206.5", "206.5 Hz"),
    ("210.7", "210.7 Hz"),
    ("218.1", "218.1 Hz"),
    ("225.7", "225.7 Hz"),
    ("229.1", "229.1 Hz"),
    ("233.6", "233.6 Hz"),
    ("241.8", "241.8 Hz"),
    ("250.3", "250.3 Hz"),
    ("254.1", "254.1 Hz"),
]
# =========================================================
# Macro Limit
# =========================================================
MACRO_LIMIT = 16
# =========================================================
# SvxLink paths
# =========================================================

SVXLINK_CONF = Path("/etc/svxlink/svxlink.conf")

EVENT_FILES = ['Logic.tcl', 'RepeaterLogicType.tcl', 'CW.tcl']
# =========================================================
# Flask app
# =========================================================

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)
app.permanent_session_lifetime = timedelta(hours=8)
app.secret_key = "change-this-dashboard-secret"

app.permanent_session_lifetime = datetime.timedelta(minutes=15)

# =========================================================
# Authorisation and protection
# =========================================================


def dashboard_auth_exists():
    """
    Return True only when dashboard credentials exist and are parseable.
    Fail closed if the model cannot be read safely.
    """

    try:
        model = load_node_model()
        auth = model.get("dashboard_auth", {})

        username = auth.get("username", "").strip()
        password_hash = auth.get("password_hash", "").strip()

        return bool(username and password_hash)

    except Exception:
        return False


@app.before_request
def require_dashboard_auth():
    """
    Protect all dashboard configuration/control routes.

    Public:
      - static assets
      - /status
      - /api/status
      - /authorise
      - /logout
      - /setup-auth only when no credentials exist yet

    Everything else requires session["authorised"].
    """

    public_paths = {
        "/status",
        "/api/status",
        "/stream/live.mp3",
        "/wifi",
    }

    auth_paths = {
        "/authorise",
        "/logout",
    }

    setup_auth_path = "/setup-auth"

    if request.endpoint == "static":
        return None

    path = request.path.rstrip("/") or "/"

    if path in public_paths:
        return None

    auth_exists = dashboard_auth_exists()

    if not auth_exists:
        if path == setup_auth_path:
            return None

        session.pop("authorised", None)
        return redirect(url_for("setup_auth_page"))

    if path in auth_paths:
        return None

    if path == setup_auth_path:
        if session.get("authorised"):
            return None

        return redirect(url_for("authorise_page", next=request.path))

    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    return None
# ========================================================
# Context processors
# ========================================================


@app.context_processor
def inject_versions():
    return {
        "version_info": get_version_info()
    }


# =========================================================
# Platform detection
# =========================================================

def detect_platform():
    """
    Return the centrally detected platform profile.
    """
    return hw_platforms.get_platform_profile()

# =========================================================
# Hardware Profiles
# =========================================================


@app.route("/hardware-profiles")
def hardware_profiles():
    profiles = list_hardware_profiles()
    return render_template("hardware_profiles.html", profiles=profiles)


# =========================================================
# GPIOD Support
# =========================================================
# services/platform_service.py

def detect_gpiod_support():
    """
    Return True if this system exposes Linux GPIO character devices.
    """

    return any(Path("/dev").glob("gpiochip*"))


def platform_supports_gpiod(model):
    """
    Decide whether GPIOD options should be shown.

    Explicit platform setting wins.
    Runtime detection is fallback.
    """

    platform = model.get("platform", {})

    if "supports_gpiod" in platform:
        return bool(platform["supports_gpiod"])

    return detect_gpiod_support()
# =========================================================
# Node model defaults
# =========================================================


def default_node_model():
    """
    This is the authoritative in-memory model.
    svxlink.conf should eventually be generated from this.
    """

    return {
        "platform": detect_platform(),
        "node_type": None,          # simplex | repeater
        "callsign": None,
        "language": "en_US",

        "reflector": {
            "enabled": False,
            "name": None,
            "host": None,
            "port": None,
            "auth_key": None,
        },

        "ident": {
            "short": {
                "mode": None,
                "interval": 15,
            },
            "long": {
                "mode": None,       # none | cw | voice | both
                "interval": 60,
            },
        },

        "courtesy": {
            "mode": "none",         # none | beep | morse_t | morse_k
        },

        "squelch": {
            "method": None,         # gpiod | ctcss
            "ctcss_freq": None,
            "ctcss_tx": False,
        },

        "modules": [
            "ModuleHelp",
            "ModuleParrot",
        ],
    }


# =========================================================
# Model persistence
# =========================================================

def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# SvxLink service wrapper
# =========================================================

def svxlink_status():
    result = subprocess.run(
        ["systemctl", "is-active", "svxlink.service"],
        text=True,
        capture_output=True
    )

    return result.stdout.strip()

# =========================================================
# Wizard routes
# =========================================================


@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("start"))


@app.route("/start", methods=["GET", "POST"])
def start():
    model = load_node_model()
    resume_after_reboot = model.get("build", {}).get("resume_after_reboot")
    if resume_after_reboot:
        return redirect(resume_after_reboot)
    
    if "build" not in model:
        model["build"] = {
            "intent": "single_channel",
        }

    if request.method == "POST":
        build_intent = request.form.get("build_intent", "single_channel").strip()

        if build_intent not in ("single_channel", "multichannel"):
            build_intent = "single_channel"

        model["build"]["intent"] = build_intent
        save_node_model(model)

        return redirect(url_for("platform_page"))

    return render_template("start.html", model=model)


@app.route("/platform", methods=["GET", "POST"])
def platform_page():
    model = load_node_model()
    error = None

    if request.method == "POST":
        # Platform is normally detected, not user-selected.
        save_node_model(model)
        platform_id = (
            model.get("platform", {}).get("id")
        )
        nanopi_verified = (
            model.get("nanopi_prepare", {})
            .get("verified", False)
        )

        if (
            platform_id == "nanopi_neo"
            and not nanopi_verified
        ):
            return redirect(
                url_for("nanopi_prepare_page")
            )

        if platform_id == "raspberry_pi":
            result = prepare_service_account(
                require_gpio=True
            )
        elif platform_id == "linux_server":
            result = prepare_service_account(
                require_gpio=False
            )
        else:
            result = None

        if result is not None and not result["ok"]:
            error = (
                result["stderr"]
                or result["stdout"]
                or (
                    "Failed to prepare the SvxLink "
                    "service account."
                )
            )
        else:
            return redirect(url_for("hardware_page"))

    return render_template(
        "platform.html",
        model=model,
        error=error,
    )


@app.route(
    "/nanopi-prepare",
    methods=["GET", "POST"],
)
def nanopi_prepare_page():
    model = load_node_model()
    platform_id = (
        model.get("platform", {}).get("id")
    )

    if platform_id != "nanopi_neo":
        return redirect(url_for("platform_page"))

    message = None
    error = None
    status = build_nanopi_status()

    if status["ready"]:
        model.setdefault(
            "nanopi_prepare",
            {},
        )
        model["nanopi_prepare"][
            "reboot_required"
        ] = False
        save_node_model(model)

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "configure":
            result = configure_boot()
            if result["ok"]:
                model.setdefault("build", {})
                model["build"][
                    "resume_after_reboot"
                ] = "/nanopi-prepare"
                model.setdefault(
                    "nanopi_prepare",
                    {},
                )
                model["nanopi_prepare"][
                    "configuration_requested"
                ] = True
                model["nanopi_prepare"][
                    "reboot_required"
                ] = True
                model["nanopi_prepare"][
                    "verified"
                ] = False
                save_node_model(model)
                message = (
                    result["stdout"]
                    or (
                        "NanoPi boot preparation "
                        "completed. Reboot required."
                    )
                )
            else:
                error = (
                    result["stderr"]
                    or result["stdout"]
                    or (
                        "Failed to configure NanoPi "
                        "boot overlays."
                    )
                )

        elif action == "reboot":
            model.setdefault("build", {})
            model["build"][
                "resume_after_reboot"
            ] = "/nanopi-prepare"
            model.setdefault(
                "nanopi_prepare",
                {},
            )
            model["nanopi_prepare"][
                "reboot_required"
            ] = True
            model["nanopi_prepare"][
                "verified"
            ] = False
            save_node_model(model)

            result = schedule_reboot(8)
            if result.returncode != 0:
                error = (
                    result.stderr
                    or result.stdout
                    or "Failed to schedule reboot."
                )
            else:
                return redirect(
                    url_for(
                        "rebooting_page",
                        return_to="nanopi",
                    )
                )

        elif action == "continue":
            status = build_nanopi_status()

            if not status["ready"]:
                error = (
                    "NanoPi preparation is not yet "
                    "complete. Confirm the overlays, "
                    "reboot, and refresh the checks."
                )
            else:
                account_result = (
                    prepare_service_account(
                        require_gpio=True
                    )
                )

                if not account_result["ok"]:
                    error = (
                        account_result["stderr"]
                        or account_result["stdout"]
                        or (
                            "Failed to prepare the "
                            "SvxLink service account."
                        )
                    )
                else:
                    model.setdefault(
                        "nanopi_prepare",
                        {},
                    )
                    model["nanopi_prepare"][
                        "reboot_required"
                    ] = False
                    model["nanopi_prepare"][
                        "verified"
                    ] = True

                    if "build" in model:
                        model["build"].pop(
                            "resume_after_reboot",
                            None,
                        )

                    save_node_model(model)

                    return redirect(
                        url_for("hardware_page")
                    )

        else:
            error = "Unknown action."

        status = build_nanopi_status()

    return render_template(
        "nanopi_prepare.html",
        model=model,
        status=status,
        message=message,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/hardware", methods=["GET", "POST"])
def hardware_page():
    model = load_node_model()

    build_intent = (
        model.get("build", {})
        .get("intent", "single_channel")
    )

    all_profiles = list_hardware_profiles()

    if build_intent == "multichannel":
        profiles = [
            profile for profile in all_profiles
            if profile.get("type") in ("port_based", "multi_interface")
        ]
    else:
        profiles = [
            profile for profile in all_profiles
            if profile.get("type") == "generic"
        ]

    if request.method == "POST":
        hardware_profile_id = request.form.get("hardware_profile_id", "").strip()

        allowed_profile_ids = {
            profile["profile_id"]
            for profile in profiles
        }

        if hardware_profile_id not in allowed_profile_ids:
            return render_template(
                "hardware.html",
                model=model,
                profiles=profiles,
                build_intent=build_intent,
                error="Please select a valid hardware profile for this build type.",
            )

        model["hardware_profile_id"] = hardware_profile_id

        profile = load_hardware_profile(hardware_profile_id)

        model["hardware"] = {
            "profile_id": hardware_profile_id,
            "profile_name": profile.get("name"),
            "type": profile.get("type"),
            "family": profile.get("family"),
            "ports": profile.get("ports", 1),
        }

        model["hardware_preparation"] = {
            "required": bool(profile.get("preparation", {}).get("required")),
            "requires_reboot": bool(profile.get("preparation", {}).get("requires_reboot")),
            "service": profile.get("preparation", {}).get("service"),
            "status": "pending" if profile.get("preparation", {}).get("required") else "not_required",
            "resume_after_reboot": profile.get("preparation", {}).get("resume_after_reboot"),
        }
        if hardware_profile_id == "generic_single":
            model.setdefault("audio", {})

            current_audio_dev = (
            model["audio"].get("audio_dev", "").strip()
        )

            # Upgrade the old numeric default while preserving any
            # explicit custom or previously discovered device.
            if current_audio_dev in ("", "alsa:plughw:0"):
                detected_audio_dev = discover_default_audio_dev()

                if detected_audio_dev:
                    model["audio"]["audio_dev"] = detected_audio_dev

        save_node_model(model)

        if profile.get("preparation", {}).get("required"):
            return redirect(url_for("hardware_prepare_page"))

        return redirect(url_for("hardware_ports_page"))

    return render_template(
        "hardware.html",
        model=model,
        profiles=profiles,
        build_intent=build_intent,
        error=None,
    )


@app.route("/hardware-prepare")
def hardware_prepare_page():
    model = load_node_model()

    hardware_profile_id = model.get("hardware_profile_id")

    if not hardware_profile_id:
        return redirect(url_for("hardware_page"))

    try:
        profile = load_hardware_profile(hardware_profile_id)
    except FileNotFoundError:
        return redirect(url_for("hardware_page"))

    dual_usb_status = None

    if hardware_profile_id == "dual_usb":
        dual_usb_status = (
            inspect_dual_usb_hardware()
        )

    return render_template(
        "hardware_prepare.html",
        model=model,
        profile=profile,
        dual_usb_status=dual_usb_status,
    )


@app.route("/hardware-prepare/reviewed", methods=["POST"])
def hardware_prepare_reviewed_page():
    model = load_node_model()

    hardware_profile_id = model.get("hardware_profile_id")

    if not hardware_profile_id:
        return redirect(url_for("hardware_page"))

    try:
        profile = load_hardware_profile(hardware_profile_id)
    except FileNotFoundError:
        return redirect(url_for("hardware_page"))

    dual_usb_status = None

    if hardware_profile_id == "dual_usb":
        dual_usb_status = (
            inspect_dual_usb_hardware()
        )

        if not dual_usb_status["ready"]:
            return render_template(
                "hardware_prepare.html",
                model=model,
                profile=profile,
                dual_usb_status=dual_usb_status,
                error=" ".join(
                    dual_usb_status["errors"]
                ),
            )

    requires_physical_confirmation = (
        profile.get("family") == "ics"
        or profile.get("type") == "port_based"
    )

    if requires_physical_confirmation:
        confirmed = request.form.get("confirm_hardware") == "yes"

        if not confirmed:
            return render_template(
                "hardware_prepare.html",
                model=model,
                profile=profile,
                error="Please confirm that the selected ICS board is physically installed.",
            )

    if "hardware_preparation" not in model:
        model["hardware_preparation"] = {}

    model["hardware_preparation"]["status"] = "reviewed"
    model["hardware_preparation"]["physical_profile_confirmed"] = (
        requires_physical_confirmation
    )

    if dual_usb_status is not None:
        model["hardware_preparation"]["dual_usb"] = (
            dual_usb_status
        )

    save_node_model(model)

    if profile.get("family") == "ics":
        return redirect(url_for("ics_prepare_page"))

    return redirect(url_for("hardware_ports_page"))


@app.route("/hardware-ports", methods=["GET", "POST"])
def hardware_ports_page():
    model = load_node_model()

    hardware_profile_id = model.get("hardware_profile_id")

    if not hardware_profile_id:
        return redirect(url_for("hardware_page"))

    try:
        profile = load_hardware_profile(hardware_profile_id)
    except FileNotFoundError:
        return redirect(url_for("hardware_page"))
    if profile.get("family") == "ics":
        ics_prepare = model.get("ics_prepare", {})
        if not ics_prepare.get("verified"):
            return redirect(url_for("ics_prepare_page"))
    port_count = int(profile.get("ports", 1))
    available_ports = [str(port) for port in range(1, port_count + 1)]

    if request.method == "POST":
        selected_ports = request.form.getlist("enabled_ports")

        enabled_ports = []
        for port in selected_ports:
            try:
                port_number = int(port)
            except ValueError:
                continue

            if str(port_number) in available_ports:
                enabled_ports.append(str(port_number))

        enabled_ports = sorted(set(enabled_ports), key=int)

        if not enabled_ports:
            return render_template(
                "hardware_ports.html",
                model=model,
                profile=profile,
                available_ports=available_ports,
                enabled_ports=model.get("ports", {}).get("enabled", available_ports),
                error="Select at least one port.",
                version_info=get_version_info(),
            )

        model["ports"] = {
            "available": available_ports,
            "enabled": enabled_ports,
        }

        if profile.get("family") == "ics":
            try:
                model = update_model_gpiod_discovery(model)
            except Exception as exc:
                return render_template(
                    "hardware_ports.html",
                    model=model,
                    profile=profile,
                    available_ports=available_ports,
                    enabled_ports=enabled_ports,
                    error=f"GPIOD discovery failed after port selection: {exc}",
                    version_info=get_version_info(),
                )

        save_node_model(model)

#        if len(enabled_ports) > 1:
#            return redirect(url_for("port_roles_page"))

        return redirect(url_for("hardware_review_page"))

    enabled_ports = (
        model.get("ports", {})
        .get("enabled", available_ports)
    )

    return render_template(
        "hardware_ports.html",
        model=model,
        profile=profile,
        available_ports=available_ports,
        enabled_ports=enabled_ports,
        error=None,
    )


@app.route("/hardware-review", methods=["GET", "POST"])
def hardware_review_page():
    model = load_node_model()

    hardware_profile_id = model.get("hardware_profile_id")

    if not hardware_profile_id:
        return redirect(url_for("hardware_page"))

    try:
        profile = load_hardware_profile(hardware_profile_id)
    except FileNotFoundError:
        return redirect(url_for("hardware_page"))

    ports = model.get("ports", {})
    available_ports = ports.get("available", [])
    enabled_ports = ports.get("enabled", [])
    if not available_ports or not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    if request.method == "POST":
        return redirect(url_for("environment_page"))

    return render_template(
        "hardware_review.html",
        model=model,
        profile=profile,
        available_ports=available_ports,
        enabled_ports=enabled_ports,
        error=None,
        version_info=get_version_info
    )


@app.route("/ics_prepare", methods=["GET", "POST"])
def ics_prepare_page():
    model = load_node_model()
    message = None
    error = None
    try:
        with open("/proc/sys/kernel/random/boot_id", encoding="ascii") as stream:
            current_boot_id = stream.read().strip()
    except OSError:
        current_boot_id = None

    selected_profile = (
        model.get("hardware_profile_id")
        or model.get("hardware", {}).get("profile")
        or "ics_4x"
    )

    if request.method == "POST":
        action = request.form.get("action", "")
        selected_profile = request.form.get("profile", selected_profile)

        model["hardware_profile_id"] = selected_profile
        save_node_model(model)

        if action == "enable_i2c":
            result = enable_i2c()

            if result["ok"]:
                model.setdefault("build", {})
                model["build"]["resume_after_reboot"] = "/ics_prepare"

                model.setdefault("ics_prepare", {})
                model["ics_prepare"]["i2c_enable_requested"] = True
                model["ics_prepare"]["reboot_required"] = False

                save_node_model(model)

                message = (
                    result["stdout"]
                    or "I²C enable request completed. Reboot required before continuing."
                )
            else:
                error = result["stderr"] or result["stdout"] or "Failed to enable I²C."
        elif action == "set_overlay":
            result = set_overlay(selected_profile)

            if result["ok"]:
                audio_result = configure_audio_boot(selected_profile)

                model.setdefault("build", {})
                model["build"]["resume_after_reboot"] = "/ics_prepare"

                model.setdefault("ics_prepare", {})
                model["ics_prepare"]["overlay_applied"] = selected_profile
                model["ics_prepare"]["overlay_install_boot_id"] = current_boot_id
                model["ics_prepare"]["reboot_required"] = True
                model["ics_prepare"]["verified"] = False
                model["ics_prepare"]["audio_boot_configured"] = audio_result["ok"]
                save_node_model(model)

                if audio_result["ok"]:
                    message = (
                        result["stdout"]
                        or f"Overlay set for {selected_profile}. Reboot required before continuing."
                    )
                    if audio_result["stdout"]:
                        message += "\n" + audio_result["stdout"]
                else:
                    error = (
                        audio_result["stderr"]
                        or audio_result["stdout"]
                        or "Failed to configure ICS audio boot overlays."
                    )
            else:
                error = (
                    result["stderr"]
                    or result["stdout"]
                    or "Failed to set ICS overlay."
                )
        elif action == "reboot":
            model.setdefault("build", {})
            model["build"]["resume_after_reboot"] = "/ics_prepare"
        
            model.setdefault("ics_prepare", {})
            model["ics_prepare"]["reboot_required"] = True
        
            save_node_model(model)
        
            result = schedule_reboot(8)
        
            if result.returncode != 0:
                error = result.stderr or result.stdout or "Failed to schedule reboot."
            else:
                return redirect(url_for("rebooting_page"))
        else:
            error = "Unknown action."

    preparation = model.get("ics_prepare", {})
    overlay_reboot_pending = (
        "overlay_install_boot_id" in preparation
        and (
            not current_boot_id
            or current_boot_id == preparation["overlay_install_boot_id"]
        )
    )
    status = build_ics_status(selected_profile)
    model.setdefault("ics_prepare", {})
    model["ics_prepare"]["verified"] = False

    if (
        not overlay_reboot_pending
        and preparation.get("audio_boot_configured", False)
        and status.get("selected_overlay_exists")
        and status.get("current_overlay") == selected_profile
        and status.get("i2c")
        and status["i2c"].get("ok")
        and status.get("gpio_names")
        and status["gpio_names"].get("ok")
    ):

        try:
            model = update_model_gpiod_discovery(model)

            missing_lines = (
                model.get("gpiod", {})
                .get("missing_lines", [])
            )

            if missing_lines:
                error = (
                    "GPIOD discovery completed, but these required lines "
                    "were not found: "
                    + ", ".join(missing_lines)
                )
            else:
                pcm1803_result = configure_pcm1803(selected_profile)

                if not pcm1803_result["ok"]:
                    error = (
                        pcm1803_result["stderr"]
                        or pcm1803_result["stdout"]
                        or "Failed to configure PCM1803 service."
                    )
                elif selected_profile in ("ics_4x", "ics_8x"):
                    message = (
                        message
                        or "ICS GPIO lines discovered and PCM1803 service enabled."
                    )
                else:
                    message = (
                        message
                        or "ICS GPIO lines discovered. PCM1803 service disabled for this profile."
                    )

        except Exception as exc:
            error = f"GPIOD discovery failed: {exc}"

        if not error:
            model["ics_prepare"]["verified"] = True
            model["ics_prepare"]["reboot_required"] = False

            if "build" in model:
                model["build"].pop("resume_after_reboot", None)

    save_node_model(model)
    return render_template(
        "ics_prepare.html",
        model=model,
        profiles=get_ics_profiles(),
        selected_profile=selected_profile,
        status=status,
        message=message,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/rebooting")
def rebooting_page():
    return_to = request.args.get(
        "return_to",
        "ics",
    )

    if return_to == "nanopi":
        device_name = "NanoPi Neo"
        preparation_name = "NanoPi Preparation"
        preparation_endpoint = (
            "nanopi_prepare_page"
        )
    else:
        device_name = "Raspberry Pi"
        preparation_name = "ICS Preparation"
        preparation_endpoint = "ics_prepare_page"

    return render_template(
        "rebooting.html",
        device_name=device_name,
        preparation_name=preparation_name,
        preparation_endpoint=preparation_endpoint,
        version_info=get_version_info(),
    )      


@app.route("/environment", methods=["GET", "POST"])
def environment_page():
    model = load_node_model()
    error = None

    if "environment" not in model:
        model["environment"] = {}

    if request.method == "POST":

        environment = request.form.get("environment", "").strip()

        if not environment:
            error = "Please select an operating environment."

        else:

            if environment == "north_america":
                language = "en_US"
                metar_region = "north_america"

            elif environment == "australia_nz":
                language = "en_AU"
                metar_region = "australia"

            else:
                environment = "british_isles"
                language = "en_GB"
                metar_region = "ukwide"

            model["environment"] = {
                "region": environment,
            }

            model["language"] = {
                "default": language,
            }
            model.setdefault("metar", {})
            model["metar"]["region"] = metar_region

            save_node_model(model)
            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(url_for("timezone_page"))

    return render_template(
        "environment.html",
        model=model,
        error=error,
    )


@app.route("/timezone", methods=["GET", "POST"])
def timezone_page():
    model = load_node_model()
    error = None

    if "timezone" not in model:
        model["timezone"] = {}

    environment = (
        model.get("environment", {})
        .get("region", "british_isles")
    )

    timezones = TIMEZONES.get(environment, {})

    if request.method == "POST":

        timezone = request.form.get("timezone", "").strip()

        if not timezone:
            error = "Please select a time zone."

        elif timezone not in timezones:
            error = "Invalid time zone selection."

        else:
            model["timezone"] = {
                "name": timezone,
            }

            save_node_model(model)

            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(next_after_timezone(model))

    return render_template(
        "timezone.html",
        model=model,
        timezones=timezones,
        error=error,
    )
    

def is_multiport_build(model):
    enabled_ports = model.get("ports", {}).get("enabled", [])
    hardware = model.get("hardware", {})
    profile_id = (
        model.get("hardware_profile_id")
        or hardware.get("profile")
        or hardware.get("profile_id")
        or ""
    )

    return (
        profile_id in ("ics_1x","ics_2x", "ics_4x", "ics_8x")
        or len(enabled_ports) > 1
    )


def next_after_timezone(model):
    if is_multiport_build(model):
        return url_for("port_roles_page")

    return url_for("node_page")


def next_after_reflector(model):
    return url_for("node_info_page")


def redirect_after_port_configuration(
    default_endpoint,
):
    """
    Return a completed port-configuration form to its caller.

    Topology repair takes priority over ordinary wizard progression.
    Existing reconfiguration behaviour remains unchanged otherwise.
    """

    if request.form.get("return_to") == "topology":
        route_arguments = {}

        if request.form.get("reconfigure") == "1":
            route_arguments["reconfigure"] = "1"

        return redirect(
            url_for(
                "topology_page",
                **route_arguments,
            )
        )

    if request.form.get("reconfigure") == "1":
        return redirect(url_for("build_page"))

    return redirect(url_for(default_endpoint))


def initialise_port_nodes(model, profile):
    ports = model.get("ports", {})
    enabled_ports = ports.get("enabled", [])
    port_roles = model.get("port_roles", {})
    port_map = profile.get("port_map", {})

    dual_usb_preparation = (
        model.get("hardware_preparation", {})
        .get("dual_usb", {})
    )

    discovered_usb_ports = {}

    if dual_usb_preparation.get("ready"):
        discovered_usb_ports = {
            str(port.get("port")): port
            for port in dual_usb_preparation.get("ports", [])
            if (
                isinstance(port, dict)
                and port.get("port") is not None
                and port.get("audio_dev")
            )
        }

    existing_nodes = model.get("nodes", {})
    nodes = {}

    for port in enabled_ports:
        port_id = str(port)

        role_entry = port_roles.get(port_id, {})

        if isinstance(role_entry, dict):
            role = role_entry.get("role", "simplex")
        else:
            role = role_entry or "simplex"

        if role not in ("simplex", "repeater"):
            role = "simplex"

        mapping = dict(
            port_map.get(port_id, {})
        )
        discovered_usb = discovered_usb_ports.get(
            port_id
        )

        if discovered_usb:
            audio_dev = discovered_usb["audio_dev"]

            mapping["rx_audio"] = audio_dev
            mapping["tx_audio"] = audio_dev
            mapping["hidraw_device"] = (
                discovered_usb.get("hidraw_device")
                or mapping.get("hidraw_device")
            )

        node = existing_nodes.get(port_id, {}).copy()

        node.setdefault("port", port)
        node["role"] = role
        node.setdefault("enabled", True)
        node.setdefault("name", f"Port {port} {role.title()}")
        node.setdefault("callsign", None)
        node.setdefault(
            "language",
            model.get("language", {}).get("default", "en_GB")
        )
        node.setdefault("configured", False)
        node.setdefault("tx_delay", 500)
        node.setdefault("ctcss_to_tg", {})
        node["ctcss_to_tg"].setdefault(
            "enabled",
            False,
        )
        node["ctcss_to_tg"].setdefault(
            "delay_ms",
            0,
        )
        node["ctcss_to_tg"].setdefault(
            "mappings",
            [],
        )
        node.setdefault("audio", {})

        if discovered_usb:
            node["audio"]["rx_audio"] = mapping.get(
                "rx_audio"
            )
            node["audio"]["tx_audio"] = mapping.get(
                "tx_audio"
            )
        else:
            node["audio"].setdefault(
                "rx_audio",
                mapping.get("rx_audio"),
            )
            node["audio"].setdefault(
                "tx_audio",
                mapping.get("tx_audio"),
            )

        node.setdefault("gpio", {})
        node["gpio"].setdefault("ptt", mapping.get("ptt"))
        node["gpio"].setdefault("cos", mapping.get("cos"))
        node["gpio"].setdefault("enable", mapping.get("enable"))
        node["gpio"].setdefault("control", mapping.get("control"))
        node.setdefault("hidraw", {})

        try:
            hidraw_index = int(port_id) - 1
        except ValueError:
            hidraw_index = 0
        
        if discovered_usb:
            node["hidraw"]["device"] = mapping.get(
                "hidraw_device",
                f"/dev/hidraw{hidraw_index}",
            )
        else:
            node["hidraw"].setdefault(
                "device",
                mapping.get(
                    "hidraw_device",
                    f"/dev/hidraw{hidraw_index}",
                ),
            )
        
        node["hidraw"].setdefault(
            "sql_pin",
            mapping.get("hidraw_sql_pin", "VOL_DN")
        )
        
        node["hidraw"].setdefault(
            "ptt_pin",
            mapping.get("hidraw_ptt_pin", "GPIO3")
        )
        
        node["hidraw"].setdefault("sql_invert", False)
        node["hidraw"].setdefault("ptt_invert", False)
        nodes[port_id] = node

    return nodes


@app.route("/port-roles", methods=["GET", "POST"])
def port_roles_page():
    model = load_node_model()

    ports = model.get("ports", {})
    enabled_ports = ports.get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("node_page"))

    if not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    existing_roles = model.get("port_roles", {})

    if request.method == "POST":
        port_roles = {}

        for port in enabled_ports:
            role = request.form.get(f"port_{port}_role", "").strip()

            if role not in ("simplex", "repeater"):
                return render_template(
                    "port_roles.html",
                    model=model,
                    enabled_ports=enabled_ports,
                    port_roles=existing_roles,
                    error=f"Please select a valid role for Port {port}.",
                    version_info=get_version_info(),
                )

            port_roles[str(port)] = {
                "role": role,
            }

        model["port_roles"] = port_roles

        nodes = model.get("nodes", {})

        for port in enabled_ports:
            port_id = str(port)
            node = nodes.get(port_id, {})

            node["role"] = port_roles[port_id]["role"]
            nodes[port_id] = node

        model["nodes"] = nodes
        save_node_model(model)

        return redirect(url_for("port_config_page"))

    return render_template(
        "port_roles.html",
        model=model,
        enabled_ports=enabled_ports,
        port_roles=existing_roles,
        error=None,
        version_info=get_version_info(),
    )


@app.route("/port-config", methods=["GET", "POST"])
def port_config_page():
    model = load_node_model()

    hardware_profile_id = model.get("hardware_profile_id")
    ports = model.get("ports", {})
    enabled_ports = ports.get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("node_page"))

    if not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    if not model.get("port_roles"):
        return redirect(url_for("port_roles_page"))

    try:
        profile = load_hardware_profile(hardware_profile_id)
    except FileNotFoundError:
        return redirect(url_for("hardware_page"))
    profile.setdefault("port_map", {})

    if request.method == "POST":
        first_port = str(enabled_ports[0])

        model["nodes"] = initialise_port_nodes(model, profile)

        model.setdefault("build", {})
        model["build"]["multi_node"] = True
        model["build"]["active_port"] = first_port

        save_node_model(model)

        return redirect(url_for("port_config_page"))

    nodes = model.get("nodes", {})

    nodes_need_initialising = any(
        str(port) not in nodes
        or not nodes.get(str(port), {}).get("role")
        or "audio" not in nodes.get(str(port), {})
        or "gpio" not in nodes.get(str(port), {})
        for port in enabled_ports
    )

    if nodes_need_initialising:
        model["nodes"] = initialise_port_nodes(model, profile)
        save_node_model(model)
        nodes = model.get("nodes", {})

    all_ports_configured = bool(enabled_ports) and all(
        nodes.get(str(port), {}).get("node_details_configured")
        for port in enabled_ports
    )

    return render_template(
        "port_config.html",
        model=model,
        profile=profile,
        enabled_ports=enabled_ports,
        port_roles=model.get("port_roles", {}),
        nodes=nodes,
        all_ports_configured=all_ports_configured,
        version_info=get_version_info(),
    )


@app.route("/port-node/<port_id>", methods=["GET", "POST"])
def port_node_page(port_id):
    model = load_node_model()

    nodes = model.get("nodes", {})
    node = nodes.get(port_id)

    if not node:
        return redirect(url_for("port_config_page"))

    node.setdefault("audio", {})
    node["audio"].setdefault("rx_audio", f"rx{port_id}")
    node["audio"].setdefault("tx_audio", f"tx{port_id}")
    node["audio"].setdefault("deemphasis", False)
    node["audio"].setdefault("preemphasis", False)
    node.setdefault("tx_delay", 500)
    node.setdefault("gpio", {})
    node["gpio"].setdefault("ptt", f"TX_{port_id}")
    node["gpio"].setdefault("cos", f"RX_{port_id}")
    node["gpio"].setdefault("enable", f"EN_{port_id}")
    node["gpio"].setdefault("control", f"CT_{port_id}")

    role_entry = model.get("port_roles", {}).get(port_id, {})

    if isinstance(role_entry, dict):
        role = role_entry.get("role", "simplex")
    else:
        role = role_entry or "simplex"

    node["role"] = node.get("role") or role

    nodes[port_id] = node
    model["nodes"] = nodes
    save_node_model(model)
    
    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    if port_id not in enabled_ports:
        return redirect(url_for("port_config_page"))

    error = None

    if request.method == "POST":
        callsign = request.form.get(
            "callsign",
            "",
        ).strip().upper()

        name = request.form.get(
            "name",
            "",
        ).strip()

        name = name.capitalize() if name else ""

        tx_delay, tx_delay_errors = parse_tx_delay(
            request.form.get("tx_delay"),
            f"Port {port_id} TX delay",
        )

        if not callsign:
            error = (
                "Please enter a callsign for this port."
            )
        elif tx_delay_errors:
            error = " ".join(tx_delay_errors)
        else:
            node["callsign"] = callsign
            node["tx_delay"] = tx_delay
            node["name"] = name or node.get("name") or f"Port {port_id} {node.get('role', '').title()}"
            node["audio"]["deemphasis"] = (
                request.form.get("deemphasis") == "1"
            )
            node["audio"]["preemphasis"] = (
                request.form.get("preemphasis") == "1"
            )
            node["node_details_configured"] = True
            node["configured"] = True

            nodes[port_id] = node
            model["nodes"] = nodes

            model.setdefault("build", {})
            model["build"]["active_port"] = port_id

            save_node_model(model)

            return redirect_after_port_configuration(
                "port_config_page"
            )

    return render_template(
        "port_node.html",
        model=model,
        port_id=port_id,
        node=node,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/port-profile-review", methods=["GET", "POST"])
def port_profile_review_page():
    model = load_node_model()

    hardware = model.get("hardware", {})
    hardware_profile_id = model.get("hardware_profile_id")
    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("interface_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    all_ports_configured = bool(enabled_ports) and all(
        nodes.get(str(port), {}).get("node_details_configured")
        for port in enabled_ports
    )

    if not all_ports_configured:
        return redirect(url_for("port_config_page"))

    try:
        profile = load_hardware_profile(hardware_profile_id)
    except FileNotFoundError:
        return redirect(url_for("hardware_page"))

    if request.method == "POST":
        model.setdefault("build", {})
        model["build"]["profile_interface_confirmed"] = True

        save_node_model(model)

        return redirect(url_for("port_squelch_page"))

    return render_template(
        "port_profile_review.html",
        model=model,
        profile=profile,
        nodes=nodes,
        enabled_ports=enabled_ports,
        version_info=get_version_info(),
    )


@app.route("/port-squelch", methods=["GET"])
def port_squelch_page():
    model = load_node_model()

    hardware = model.get("hardware", {})
    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("squelch_page"))
    if not nodes:
        return redirect(url_for("port_config_page"))

    all_ports_configured = bool(enabled_ports) and all(
        nodes.get(str(port), {}).get("squelch_configured")
        for port in enabled_ports
    )

    return render_template(
        "port_squelch.html",
        model=model,
        nodes=nodes,
        enabled_ports=enabled_ports,
        all_ports_configured=all_ports_configured,
        version_info=get_version_info(),
    )


@app.route("/port-squelch-complete", methods=["GET"])
def port_squelch_complete_page():
    model = load_node_model()

    hardware = model.get("hardware", {})
    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("squelch_page"))

    all_ports_configured = bool(enabled_ports) and all(
        nodes.get(str(port), {}).get("squelch_configured")
        for port in enabled_ports
    )

    if not all_ports_configured:
        return redirect(url_for("port_squelch_page"))

    model.setdefault("build", {})
    model["build"]["port_squelch_configured"] = True

    save_node_model(model)

    return redirect(url_for("port_modules_page"))


@app.route("/port-squelch/<port_id>", methods=["GET", "POST"])
def port_squelch_detail_page(port_id):
    model = load_node_model()
    hardware = model.get("hardware", {})
    nodes = model.get("nodes", {})
    node = nodes.get(port_id)

    if not is_multiport_build(model):
        return redirect(
            url_for("squelch_page")
        )

    if not node:
        return redirect(
            url_for("port_squelch_page")
        )

    enabled_ports = [
        str(port)
        for port in model.get(
            "ports",
            {},
        ).get(
            "enabled",
            [],
        )
    ]

    if port_id not in enabled_ports:
        return redirect(
            url_for("port_squelch_page")
        )

    error = None

    if hardware.get("family") == "ics":
        allowed_methods = {
            "gpiod",
            "ctcss",
        }
    else:
        allowed_methods = {
            "hidraw",
            "gpiod",
            "serial",
            "ctcss",
        }

    if request.method == "POST":
        valid_ctcss_values = {
            value
            for value, _label in CTCSS_FREQUENCIES
        }

        squelch, squelch_errors = (
            parse_squelch_form(
                request.form,
                allowed_methods,
                valid_ctcss_values,
                f"Port {port_id} squelch",
            )
        )

        if hardware.get("family") == "ics":
            ptt_source = "gpiod"
        elif squelch.get("method") == "ctcss":
            ptt_source = str(
                request.form.get("ptt_source")
                or ""
            ).strip().lower()

            if ptt_source not in {
                "hidraw",
                "gpiod",
                "serial",
            }:
                squelch_errors.append(
                    f"Port {port_id} requires a valid "
                    "PTT source when CTCSS is used for "
                    "squelch."
                )
        else:
            ptt_source = squelch.get("method")

        if squelch_errors:
            error = " ".join(squelch_errors)

        else:
            node.setdefault("gpio", {})
            node.setdefault("hidraw", {})
            node.setdefault("serial", {})
            node.setdefault("interface", {})
            node["interface"]["ptt_source"] = (
                ptt_source
            )
            node["gpio"]["cos_invert"] = (
                request.form.get(
                    "sql_gpio_invert"
                ) == "yes"
            )

            node["gpio"]["ptt_invert"] = (
                request.form.get(
                    "ptt_gpio_invert"
                ) == "yes"
            )

            node["hidraw"]["sql_invert"] = (
                request.form.get(
                    "hidraw_sql_invert"
                ) == "yes"
            )

            node["hidraw"]["ptt_invert"] = (
                request.form.get(
                    "hidraw_ptt_invert"
                ) == "yes"
            )

            node["serial"]["sql_invert"] = (
                request.form.get(
                    "serial_sql_invert"
                ) == "yes"
            )

            node["squelch"] = squelch
            node["squelch_configured"] = True

            nodes[port_id] = node
            model["nodes"] = nodes

            model.setdefault("build", {})
            model["build"]["active_port"] = (
                port_id
            )

            save_node_model(model)

            return (
                redirect_after_port_configuration(
                    "port_squelch_page"
                )
            )

    return render_template(
        "port_squelch_detail.html",
        model=model,
        hardware=hardware,
        port_id=port_id,
        node=node,
        squelch=node.get("squelch", {}),
        ctcss_frequencies=CTCSS_FREQUENCIES,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/port-modules", methods=["GET", "POST"])
def port_modules_page():
    model = load_node_model()

    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("modules_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    enabled_port_ids = [str(port) for port in enabled_ports]
    modules_multi = model.get("modules_multi", {})

    if request.method == "POST":
        echolink_port = request.form.get("echolink_port", "none").strip()

        if echolink_port == "none":
            echolink_port = None
        elif echolink_port not in enabled_port_ids:
            echolink_port = None

        metar_ports = request.form.getlist("metar_ports")
        metar_ports = [
            port_id
            for port_id in metar_ports
            if port_id in enabled_port_ids
        ]

        for port_id in enabled_port_ids:
            node = nodes.get(port_id, {})
            node["modules"] = {
                "echolink": port_id == echolink_port,
                "metar": port_id in metar_ports,
            }
            nodes[port_id] = node

        model["nodes"] = nodes
        model["modules_multi"] = {
            "echolink_port": echolink_port,
            "metar_ports": metar_ports,
        }
        model.setdefault("echolink", {})
        model["echolink"]["enabled"] = echolink_port is not None

        model.setdefault("metar", {})
        model["metar"]["enabled"] = bool(metar_ports)

        model.setdefault("build", {})
        model["build"]["port_modules_configured"] = True

        model.setdefault("modules", {})
        global_enabled = set(model["modules"].get("enabled", []))

        if echolink_port:
            global_enabled.add("ModuleEchoLink")
        else:
            global_enabled.discard("ModuleEchoLink")

        if metar_ports:
            global_enabled.add("ModuleMetarInfo")
        else:
            global_enabled.discard("ModuleMetarInfo")

        model["modules"]["enabled"] = sorted(global_enabled)

        if (
            metar_ports
            and not model.get(
                "metar",
                {},
            ).get("startdefault")
        ):
            return_to = (
                "build"
                if request.form.get("reconfigure") == "1"
                else "port_ident"
            )
            save_node_model(model)
            return redirect(
                url_for(
                    "metar_default_page",
                    return_to=return_to,
                )
            )

        save_node_model(model)

        if request.form.get("reconfigure") == "1":
            return redirect(url_for("build_page"))

        return redirect(url_for("port_ident_page"))

    return render_template(
        "port_modules.html",
        model=model,
        nodes=nodes,
        enabled_ports=enabled_ports,
        modules_multi=modules_multi,
        version_info=get_version_info(),
    )


@app.route("/port-ident", methods=["GET", "POST"])
def port_ident_page():
    model = load_node_model()
    error = None

    hardware = model.get("hardware", {})
    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("ident_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    enabled_port_ids = [
        str(port)
        for port in enabled_ports
    ]

    if request.method == "POST":
        try:
            for port_id in enabled_port_ids:
                node = nodes.get(port_id, {})

                existing_ident = node.get("ident", {})
                existing_short = existing_ident.get("short", {})
                existing_long = existing_ident.get("long", {})

                short_interval = request.form.get(
                    f"port_{port_id}_short_ident_interval",
                    "15"
                ).strip()

                long_interval = request.form.get(
                    f"port_{port_id}_long_ident_interval",
                    "60"
                ).strip()

                try:
                    short_interval_value = int(short_interval)
                except ValueError:
                    short_interval_value = 15

                try:
                    long_interval_value = int(long_interval)
                except ValueError:
                    long_interval_value = 60

                short_upload = request.files.get(
                    f"port_{port_id}_short_announce_file"
                )

                long_upload = request.files.get(
                    f"port_{port_id}_long_announce_file"
                )

                short_announce_file = save_ident_upload(
                    short_upload,
                    f"port{port_id}_short_ident",
                )

                long_announce_file = save_ident_upload(
                    long_upload,
                    f"port{port_id}_long_ident",
                )

                if not short_announce_file:
                    short_announce_file = existing_short.get(
                        "announce_file",
                        ""
                    )

                if not long_announce_file:
                    long_announce_file = existing_long.get(
                        "announce_file",
                        ""
                    )

                node["ident"] = {
                    "short": {
                        "interval": short_interval_value,
                        "voice_enable": request.form.get(
                            f"port_{port_id}_short_voice_enable"
                        ) == "1",
                        "cw_enable": request.form.get(
                            f"port_{port_id}_short_cw_enable"
                        ) == "1",
                        "announce_enable": request.form.get(
                            f"port_{port_id}_short_announce_enable"
                        ) == "1",
                        "announce_file": short_announce_file,
                    },
                    "long": {
                        "interval": long_interval_value,
                        "voice_enable": request.form.get(
                            f"port_{port_id}_long_voice_enable"
                        ) == "1",
                        "cw_enable": request.form.get(
                            f"port_{port_id}_long_cw_enable"
                        ) == "1",
                        "announce_enable": request.form.get(
                            f"port_{port_id}_long_announce_enable"
                        ) == "1",
                        "announce_file": long_announce_file,
                    },
                }

                node["ident_configured"] = True
                nodes[port_id] = node

            model["nodes"] = nodes

            model.setdefault("build", {})
            model["build"]["port_ident_configured"] = True

            save_node_model(model)

            return redirect_after_port_configuration(
                "port_cw_page"
            )

        except Exception as exc:
            error = f"Announcement file upload failed: {exc}"

    return render_template(
        "port_ident.html",
        model=model,
        nodes=nodes,
        enabled_ports=enabled_ports,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/port-cw", methods=["GET", "POST"])
def port_cw_page():
    model = load_node_model()

    hardware = model.get("hardware", {})
    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("cw_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    enabled_port_ids = [
        str(port)
        for port in enabled_ports
    ]

    if request.method == "POST":
        for port_id in enabled_port_ids:
            node = nodes.get(port_id, {})

            amp = request.form.get(f"port_{port_id}_cw_amp", "-10").strip()
            pitch = request.form.get(f"port_{port_id}_cw_pitch", "650").strip()
            cpm = request.form.get(f"port_{port_id}_cw_cpm", "95").strip()

            try:
                amp_value = int(amp)
            except ValueError:
                amp_value = -10

            try:
                pitch_value = int(pitch)
            except ValueError:
                pitch_value = 650

            try:
                cpm_value = int(cpm)
            except ValueError:
                cpm_value = 95

            node["cw"] = {
                "amp": amp_value,
                "pitch": pitch_value,
                "cpm": cpm_value,
            }

            node["cw_configured"] = True
            nodes[port_id] = node

        model["nodes"] = nodes

        model.setdefault("build", {})
        model["build"]["port_cw_configured"] = True

        save_node_model(model)

        return redirect_after_port_configuration(
            "courtesy_page"
        )

    return render_template(
        "port_cw.html",
        model=model,
        nodes=nodes,
        enabled_ports=enabled_ports,
        version_info=get_version_info(),
    )


@app.route("/port-courtesy", methods=["GET", "POST"])
def port_courtesy_page():
    """
    Compatibility redirect for older multi-port workflow links.
    """

    reconfigure = (
        request.args.get("reconfigure") == "1"
        or request.form.get("reconfigure") == "1"
    )

    if reconfigure:
        return redirect(
            url_for(
                "courtesy_page",
                reconfigure="1",
            )
        )

    return redirect(url_for("courtesy_page"))


@app.route("/port-repeater", methods=["GET", "POST"])
def port_repeater_page():
    model = load_node_model()

    hardware = model.get("hardware", {})
    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("repeater_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    enabled_port_ids = [
        str(port)
        for port in enabled_ports
    ]

    repeater_port_ids = [
        port_id
        for port_id in enabled_port_ids
        if nodes.get(port_id, {}).get("role") == "repeater"
    ]

    error = None

    if request.method == "POST":
        validated_repeater_values = {}

        for port_id in repeater_port_ids:
            idle_timeout = request.form.get(
                f"port_{port_id}_idle_timeout",
                "10",
            ).strip()
            sql_timeout = request.form.get(
                f"port_{port_id}_sql_timeout",
                "180",
            ).strip()

            try:
                idle_timeout_value = int(
                    idle_timeout
                )
                sql_timeout_value = int(
                    sql_timeout
                )
            except ValueError:
                error = (
                    f"Port {port_id}: timeout values "
                    "must be numeric."
                )
                break

            if not 0 <= idle_timeout_value <= 10:
                error = (
                    f"Port {port_id}: idle timeout must "
                    "be between 0 and 10 seconds."
                )
                break

            if not 120 <= sql_timeout_value <= 300:
                error = (
                    f"Port {port_id}: SQL timeout must "
                    "be between 120 and 300 seconds."
                )
                break

            validated_repeater_values[port_id] = {
                "idle_timeout": idle_timeout_value,
                "sql_timeout": sql_timeout_value,
            }

        if error is None:
            for port_id, values in (
                validated_repeater_values.items()
            ):
                node = nodes.get(port_id, {})
                repeater = node.setdefault(
                    "repeater",
                    {},
                )
                repeater.update(values)
                repeater.pop("open_on_sql", None)
                repeater.pop("open_sql_flank", None)
                node["repeater_configured"] = True
                nodes[port_id] = node

            for port_id in enabled_port_ids:
                node = nodes.get(port_id, {})

                if node.get("role") != "repeater":
                    node["repeater_configured"] = True
                    nodes[port_id] = node

            model["nodes"] = nodes
            model.setdefault("build", {})
            model["build"][
                "port_repeater_configured"
            ] = True

            save_node_model(model)

            return redirect_after_port_configuration(
                "installation_identity_page"
            )

    return render_template(
        "port_repeater.html",
        model=model,
        nodes=nodes,
        enabled_ports=enabled_ports,
        repeater_port_ids=repeater_port_ids,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/installation-identity", methods=["GET", "POST"])
def installation_identity_page():
    model = load_node_model()

    if not is_multiport_build(model):
        return redirect(url_for("reflector_page"))

    nodes = model.get("nodes", {})

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    if not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    installation = model.setdefault("installation", {})
    primary_port_id = str(
        installation.get("primary_port_id") or ""
    )

    error = None

    if request.method == "POST":
        selected_port_id = str(
            request.form.get("primary_port_id") or ""
        ).strip()

        if selected_port_id not in enabled_ports:
            error = "Please select an enabled primary port."

        elif not nodes.get(selected_port_id, {}).get("callsign"):
            error = (
                f"Port {selected_port_id} must have a callsign "
                "before it can become the primary port."
            )

        else:
            installation["primary_port_id"] = selected_port_id
            model["installation"] = installation

            save_node_model(model)

            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(url_for("reflector_page"))

    return render_template(
        "installation_identity.html",
        model=model,
        nodes=nodes,
        enabled_ports=enabled_ports,
        primary_port_id=primary_port_id,
        error=error,
        version_info=get_version_info(),
    )


@app.route(
    "/topology/independent",
    methods=["GET", "POST"],
)
def topology_independent_page():
    """
    Assign currently unlinked ports to independent operation.
    """

    model = load_node_model()

    if not is_multiport_build(model):
        return redirect(url_for("review_page"))

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})

    if not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    topology = model.setdefault("topology", {})

    linked_ports = set()

    reflector_link = topology.get(
        "reflector_link",
        {},
    )

    if isinstance(reflector_link, dict):
        reflector_ports = reflector_link.get(
            "ports",
            [],
        )

        if isinstance(reflector_ports, list):
            linked_ports.update(
                str(port_id)
                for port_id in reflector_ports
            )

    local_links = topology.get("local_links", [])

    if isinstance(local_links, list):
        for link in local_links:
            if not isinstance(link, dict):
                continue

            link_ports = link.get("ports", [])

            if not isinstance(link_ports, list):
                continue

            linked_ports.update(
                str(port_id)
                for port_id in link_ports
            )

    available_ports = [
        port_id
        for port_id in enabled_ports
        if port_id not in linked_ports
    ]

    saved_independent_ports = topology.get(
        "independent_ports",
        [],
    )

    if not isinstance(saved_independent_ports, list):
        saved_independent_ports = []

    selected_ports = [
        port_id
        for port_id in available_ports
        if port_id in {
            str(saved_port_id)
            for saved_port_id in saved_independent_ports
        }
    ]

    primary_port_id = str(
        model.get("installation", {}).get(
            "primary_port_id"
        )
        or ""
    )

    if not primary_port_id and len(enabled_ports) == 1:
        primary_port_id = enabled_ports[0]

    error = None

    if request.method == "POST":
        requested_ports = [
            str(port_id)
            for port_id in request.form.getlist(
                "independent_ports"
            )
        ]

        invalid_ports = [
            port_id
            for port_id in requested_ports
            if port_id not in available_ports
        ]

        if invalid_ports:
            error = (
                "The independent-port selection contains a port "
                "that is unavailable or assigned to a link."
            )

        else:
            selected_ports = [
                port_id
                for port_id in available_ports
                if port_id in requested_ports
            ]

            topology["independent_ports"] = selected_ports
            model["topology"] = topology

            save_node_model(model)

            route_arguments = {}

            if request.form.get("reconfigure") == "1":
                route_arguments["reconfigure"] = "1"

            return redirect(
                url_for(
                    "topology_page",
                    **route_arguments,
                )
            )

    return render_template(
        "topology_independent.html",
        model=model,
        available_ports=available_ports,
        nodes=nodes,
        selected_ports=selected_ports,
        primary_port_id=primary_port_id,
        error=error,
        version_info=get_version_info(),
    )


@app.route(
    "/topology/local-link/<int:link_index>",
    methods=["GET", "POST"],
)
def topology_local_link_edit_page(link_index):
    """
    Edit or remove one existing operator-named local link.
    """

    model = load_node_model()

    if not is_multiport_build(model):
        return redirect(url_for("review_page"))

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})

    if not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    topology = model.get("topology", {})
    local_links = topology.get("local_links", [])

    if (
        not isinstance(local_links, list)
        or link_index < 0
        or link_index >= len(local_links)
        or not isinstance(local_links[link_index], dict)
    ):
        return redirect(url_for("topology_page"))

    link = local_links[link_index]

    reflector_link = topology.get(
        "reflector_link",
        {},
    )

    if not isinstance(reflector_link, dict):
        reflector_link = {}

    reflector_name = str(
        reflector_link.get("name")
        or "LinkToReflector"
    )

    reflector_ports = reflector_link.get("ports", [])

    if not isinstance(reflector_ports, list):
        reflector_ports = []

    unavailable_ports = {
        str(port_id)
        for port_id in reflector_ports
    }

    for other_index, other_link in enumerate(local_links):
        if other_index == link_index:
            continue

        if not isinstance(other_link, dict):
            continue

        other_ports = other_link.get("ports", [])

        if not isinstance(other_ports, list):
            continue

        unavailable_ports.update(
            str(port_id)
            for port_id in other_ports
        )

    available_ports = [
        port_id
        for port_id in enabled_ports
        if port_id not in unavailable_ports
    ]

    saved_link_ports = link.get("ports", [])

    if not isinstance(saved_link_ports, list):
        saved_link_ports = []

    selected_ports = [
        port_id
        for port_id in available_ports
        if port_id in {
            str(saved_port_id)
            for saved_port_id in saved_link_ports
        }
    ]

    saved_independent_ports = topology.get(
        "independent_ports",
        [],
    )

    if not isinstance(saved_independent_ports, list):
        saved_independent_ports = []

    independent_port_ids = {
        str(port_id)
        for port_id in saved_independent_ports
    }

    original_name = str(
        link.get("name")
        or ""
    )

    available_assignments = {}

    for port_id in available_ports:
        if port_id in selected_ports:
            available_assignments[port_id] = (
                original_name or "Current local link"
            )

        elif port_id in independent_port_ids:
            available_assignments[port_id] = (
                "Independent operation"
            )

        else:
            available_assignments[port_id] = "Unassigned"

    entered_name = original_name
    error = None

    if request.method == "POST":
        action = str(
            request.form.get("action")
            or "save"
        ).strip().lower()

        if action == "delete":
            local_links.pop(link_index)
            topology["local_links"] = local_links
            model["topology"] = topology

            save_node_model(model)

            route_arguments = {}

            if request.form.get("reconfigure") == "1":
                route_arguments["reconfigure"] = "1"

            return redirect(
                url_for(
                    "topology_page",
                    **route_arguments,
                )
            )

        entered_name = str(
            request.form.get("local_link_name")
            or ""
        ).strip()

        requested_ports = [
            str(port_id)
            for port_id in request.form.getlist(
                "local_link_ports"
            )
        ]

        selected_ports = [
            port_id
            for port_id in available_ports
            if port_id in requested_ports
        ]

        invalid_ports = [
            port_id
            for port_id in requested_ports
            if port_id not in available_ports
        ]

        other_names = {
            str(other_link.get("name"))
            for other_index, other_link in enumerate(
                local_links
            )
            if (
                other_index != link_index
                and isinstance(other_link, dict)
                and other_link.get("name")
            )
        }

        name_error = validate_local_link_name(
            entered_name,
            reflector_name,
        )

        if action != "save":
            error = "Invalid local-link action."

        elif name_error:
            error = name_error

        elif entered_name in other_names:
            error = (
                f"Local-link name {entered_name} is already in use."
            )

        elif invalid_ports:
            error = (
                "The local-link selection contains a port that "
                "is unavailable or assigned to another link."
            )

        elif len(selected_ports) < 2:
            error = (
                "A local link must contain at least two "
                "available ports."
            )

        else:
            link["name"] = entered_name
            link["ports"] = selected_ports
            link.setdefault("default_active", True)
            link.setdefault("timeout", 300)

            local_links[link_index] = link
            topology["local_links"] = local_links

            topology["independent_ports"] = [
                port_id
                for port_id in enabled_ports
                if (
                    port_id in independent_port_ids
                    and port_id not in selected_ports
                )
            ]

            model["topology"] = topology

            save_node_model(model)

            route_arguments = {}

            if request.form.get("reconfigure") == "1":
                route_arguments["reconfigure"] = "1"

            return redirect(
                url_for(
                    "topology_page",
                    **route_arguments,
                )
            )

    return render_template(
        "topology_local_link_edit.html",
        model=model,
        link_index=link_index,
        available_ports=available_ports,
        nodes=nodes,
        available_assignments=available_assignments,
        entered_name=entered_name,
        selected_ports=selected_ports,
        error=error,
        version_info=get_version_info(),
    )


@app.route(
    "/topology/local-link/add",
    methods=["GET", "POST"],
)
def topology_local_link_add_page():
    """
    Create an operator-named local link from currently available ports.
    """

    model = load_node_model()

    if not is_multiport_build(model):
        return redirect(url_for("review_page"))

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})

    if not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    topology = model.setdefault("topology", {})

    reflector_link = topology.setdefault(
        "reflector_link",
        {},
    )

    reflector_name = str(
        reflector_link.get("name")
        or "LinkToReflector"
    )

    reflector_ports = reflector_link.get("ports", [])

    if not isinstance(reflector_ports, list):
        reflector_ports = []

    reflector_port_ids = {
        str(port_id)
        for port_id in reflector_ports
    }

    local_links = topology.setdefault(
        "local_links",
        [],
    )

    error = None

    if not isinstance(local_links, list):
        local_links = []
        error = (
            "The saved local-link configuration is invalid and "
            "must be repaired before another link can be added."
        )

    locally_assigned_ports = set()

    for link in local_links:
        if not isinstance(link, dict):
            continue

        link_ports = link.get("ports", [])

        if not isinstance(link_ports, list):
            continue

        locally_assigned_ports.update(
            str(port_id)
            for port_id in link_ports
        )

    available_ports = [
        port_id
        for port_id in enabled_ports
        if (
            port_id not in reflector_port_ids
            and port_id not in locally_assigned_ports
        )
    ]

    independent_ports = topology.get(
        "independent_ports",
        [],
    )

    if not isinstance(independent_ports, list):
        independent_ports = []

    independent_port_ids = {
        str(port_id)
        for port_id in independent_ports
    }

    available_assignments = {
        port_id: (
            "Independent operation"
            if port_id in independent_port_ids
            else "Unassigned"
        )
        for port_id in available_ports
    }

    entered_name = ""
    selected_ports = []

    if request.method == "POST":
        entered_name = str(
            request.form.get("local_link_name")
            or ""
        ).strip()

        requested_ports = [
            str(port_id)
            for port_id in request.form.getlist(
                "local_link_ports"
            )
        ]

        selected_ports = [
            port_id
            for port_id in available_ports
            if port_id in requested_ports
        ]

        submitted_invalid_ports = [
            port_id
            for port_id in requested_ports
            if port_id not in available_ports
        ]

        existing_names = {
            str(link.get("name"))
            for link in local_links
            if (
                isinstance(link, dict)
                and link.get("name")
            )
        }

        name_error = validate_local_link_name(
            entered_name,
            reflector_name,
        )

        if error:
            pass

        elif name_error:
            error = name_error

        elif entered_name in existing_names:
            error = (
                f"Local-link name {entered_name} is already in use."
            )

        elif submitted_invalid_ports:
            error = (
                "The local-link selection contains a port that "
                "is unavailable or already assigned to another link."
            )

        elif len(selected_ports) < 2:
            error = (
                "Select at least two available ports for the "
                "new local link."
            )

        else:
            local_links.append({
                "name": entered_name,
                "ports": selected_ports,
                "default_active": True,
                "timeout": 300,
            })

            topology["local_links"] = local_links

            topology["independent_ports"] = [
                port_id
                for port_id in enabled_ports
                if (
                    port_id in independent_port_ids
                    and port_id not in selected_ports
                )
            ]

            model["topology"] = topology
            save_node_model(model)

            route_arguments = {}

            if request.form.get("reconfigure") == "1":
                route_arguments["reconfigure"] = "1"

            return redirect(
                url_for(
                    "topology_page",
                    **route_arguments,
                )
            )

    return render_template(
        "topology_local_link.html",
        model=model,
        available_ports=available_ports,
        nodes=nodes,
        available_assignments=available_assignments,
        entered_name=entered_name,
        selected_ports=selected_ports,
        error=error,
        version_info=get_version_info(),
    )


@app.route(
    "/topology/reflector",
    methods=["GET", "POST"],
)
def topology_reflector_page():
    """
    Select which enabled ports participate in LinkToReflector.

    The primary port is compulsory. Selecting a port for the
    reflector removes it from local-link and independent assignments.
    """

    model = load_node_model()

    if not is_multiport_build(model):
        return redirect(url_for("reflector_page"))

    reflector = model.get("reflector", {})

    if not reflector.get("enabled"):
        return redirect(url_for("reflector_page"))

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})

    if not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    primary_port_id = str(
        model.get("installation", {}).get(
            "primary_port_id"
        )
        or ""
    )

    if not primary_port_id and len(enabled_ports) == 1:
        primary_port_id = enabled_ports[0]

    if primary_port_id not in enabled_ports:
        return redirect(
            url_for("installation_identity_page")
        )

    topology = model.setdefault("topology", {})

    reflector_link = topology.setdefault(
        "reflector_link",
        {},
    )

    current_reflector_ports = [
        str(port)
        for port in reflector_link.get("ports", [])
        if str(port) in enabled_ports
    ]

    error = None

    if request.method == "POST":
        requested_ports = [
            str(port)
            for port in request.form.getlist(
                "reflector_ports"
            )
        ]

        invalid_ports = [
            port_id
            for port_id in requested_ports
            if port_id not in enabled_ports
        ]

        if invalid_ports:
            error = (
                "The reflector selection contains a disabled "
                "or unknown port."
            )

        elif primary_port_id not in requested_ports:
            error = (
                f"Primary port {primary_port_id} must remain "
                "connected to LinkToReflector."
            )

        else:
            selected_ports = [
                port_id
                for port_id in enabled_ports
                if port_id in requested_ports
            ]

            reflector_link["name"] = "LinkToReflector"
            reflector_link["ports"] = selected_ports
            reflector_link.setdefault(
                "default_active",
                True,
            )
            reflector_link.setdefault(
                "timeout",
                300,
            )

            topology["reflector_link"] = reflector_link

            local_links = topology.get(
                "local_links",
                [],
            )

            if isinstance(local_links, list):
                for link in local_links:
                    if not isinstance(link, dict):
                        continue

                    link_ports = link.get("ports")

                    if not isinstance(link_ports, list):
                        continue

                    link["ports"] = [
                        str(port_id)
                        for port_id in link_ports
                        if (
                            str(port_id) in enabled_ports
                            and str(port_id)
                            not in selected_ports
                        )
                    ]

            independent_ports = topology.get(
                "independent_ports",
                [],
            )

            if isinstance(independent_ports, list):
                topology["independent_ports"] = [
                    str(port_id)
                    for port_id in independent_ports
                    if (
                        str(port_id) in enabled_ports
                        and str(port_id)
                        not in selected_ports
                    )
                ]

            model["topology"] = topology
            save_node_model(model)

            route_arguments = {}

            if request.form.get("reconfigure") == "1":
                route_arguments["reconfigure"] = "1"

            return redirect(
                url_for(
                    "topology_page",
                    **route_arguments,
                )
            )

    return render_template(
        "topology_reflector.html",
        model=model,
        enabled_ports=enabled_ports,
        nodes=nodes,
        primary_port_id=primary_port_id,
        current_reflector_ports=current_reflector_ports,
        error=error,
        version_info=get_version_info(),
    )


@app.route(
    "/topology",
    methods=["GET", "POST"],
)
def topology_page():
    """
    Display the current installation topology without modifying it.
    """

    model = load_node_model()

    if not is_multiport_build(model):
        return redirect(url_for("review_page"))

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})

    if not enabled_ports:
        return redirect(url_for("hardware_ports_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    topology = model.get("topology", {})

    if not isinstance(topology, dict):
        topology = {}

    reflector = model.get("reflector", {})
    reflector_enabled = bool(reflector.get("enabled"))

    reflector_route = str(
        reflector.get("route")
        or "none"
    ).strip().lower()

    reflector_route_labels = {
        "none": "Disabled",
        "federation": "Federation",
        "v2": "Independent Protocol 2",
        "v3": "Protocol 3 with X.509 certificates",
    }

    reflector_route_label = (
        reflector_route_labels.get(
            reflector_route,
            "Unknown reflector route",
        )
    )

    primary_port_id = str(
        model.get("installation", {}).get(
            "primary_port_id"
        )
        or ""
    )

    if not primary_port_id and len(enabled_ports) == 1:
        primary_port_id = enabled_ports[0]

    logic_names = get_topology_ports(model)

    assignments = get_topology_memberships(model)

    incomplete_issues = get_incomplete_topology_ports(
        model
    )

    issues_by_port = {
        port_id: []
        for port_id in enabled_ports
    }

    for saved_issue in incomplete_issues:
        issue = dict(saved_issue)
        port_id = str(issue.get("port_id") or "")

        endpoint = issue.get("endpoint")
        endpoint_values = issue.get("values", {})

        if not isinstance(endpoint_values, dict):
            endpoint_values = {}

        route_arguments = dict(endpoint_values)
        route_arguments["return_to"] = "topology"

        if request.args.get("reconfigure") == "1":
            route_arguments["reconfigure"] = "1"

        if endpoint:
            issue["configure_url"] = url_for(
                endpoint,
                **route_arguments,
            )
        else:
            issue["configure_url"] = None

        if port_id in issues_by_port:
            issues_by_port[port_id].append(issue)

    port_rows = []

    for port_id in enabled_ports:
        node = nodes.get(port_id, {})

        port_issues = issues_by_port[port_id]

        port_rows.append({
            "port_id": port_id,
            "callsign": node.get("callsign"),
            "role": node.get("role"),
            "logic_name": logic_names.get(
                port_id,
                f"Port{port_id}Logic",
            ),
            "is_primary": port_id == primary_port_id,
            "assignments": assignments[port_id],
            "configuration_complete": not port_issues,
            "configuration_issues": port_issues,
        })

    topology_errors = validate_topology(model)

    if request.method == "POST":
        if not topology_errors:
            model.setdefault("build", {})
            model["build"]["topology_configured"] = True

            save_node_model(model)

            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(
                url_for("port_final_review_page")
            )
    return render_template(
        "topology.html",
        model=model,
        topology=topology,
        reflector_enabled=reflector_enabled,
        reflector_route_label=reflector_route_label,
        primary_port_id=primary_port_id,
        primary_callsign=get_primary_callsign(model),
        port_rows=port_rows,
        topology_errors=topology_errors,
        version_info=get_version_info(),
    )


@app.route("/port-final-review", methods=["GET", "POST"])
def port_final_review_page():
    model = load_node_model()
    reconfigure = (
        request.values.get("reconfigure") == "1"
    )
    hardware = model.get("hardware", {})
    nodes = model.get("nodes", {})
    enabled_ports = model.get("ports", {}).get("enabled", [])

    if not is_multiport_build(model):
        return redirect(url_for("status_page"))

    if not nodes:
        return redirect(url_for("port_config_page"))

    topology_errors = validate_topology(model)
    topology_configured = bool(
        model.get("build", {}).get(
            "topology_configured"
        )
    )

    if topology_errors or not topology_configured:
        return redirect(url_for("topology_page"))

    enabled_port_ids = [
        str(port)
        for port in enabled_ports
    ]

    required_flags = [
        "node_details_configured",
        "squelch_configured",
        "ident_configured",
        "cw_configured",
        "repeater_configured",
    ]

    incomplete = []

    for port_id in enabled_port_ids:
        node = nodes.get(port_id, {})

        for flag in required_flags:
            if not node.get(flag):
                incomplete.append({
                    "port_id": port_id,
                    "node": node,
                    "missing": flag,
                })
    if not model.get("build", {}).get("tones_configured"):
        incomplete.append({
            "port_id": None,
            "node": {},
            "missing": "tones_configured",
        })
    if request.method == "POST":
        if incomplete:
            return redirect(url_for("port_final_review_page"))

        model.setdefault("build", {})
        model["build"]["port_final_review_confirmed"] = True
        save_node_model(model)
        if reconfigure:
            return redirect(url_for("build_page"))

        return redirect(url_for("review_page"))

    return render_template(
        "port_final_review.html",
        model=model,
        nodes=nodes,
        enabled_ports=enabled_ports,
        incomplete=incomplete,
        reconfigure=reconfigure,
        version_info=get_version_info(),
    )
#def render_port_rx_section(model, port_id, node):
#    """
#    Render one Rx section for an ICS port.
#    """
#
#    audio = node.get("audio", {})
#    squelch = node.get("squelch", {})
#    gpio = node.get("gpio", {})
#
#    rx_name = f"Rx{port_id}"
#    audio_dev = audio.get("rx_audio", f"alsa:rx{port_id}")
#
#    method = squelch.get("method", "gpiod")
#    ctcss_mode = squelch.get("ctcss_mode", "radio")
#    ctcss_freq = squelch.get("ctcss_freq")
#
#    lines = [
#        f"[{rx_name}]",
#        "TYPE=Local",
#        f"AUDIO_DEV={audio_dev}",
#        "AUDIO_CHANNEL=0",
#        "SQL_DET=GPIOD" if method == "gpiod" else "SQL_DET=CTCSS",
#        f"SQL_HANGTIME={model.get('sql_hangtime', 20)}",
#        f"SQL_TAIL_ELIM={model.get('sql_tail_elim', 270)}",
#    ]
#
#    if method == "gpiod":
#        sql_gpio = gpio.get("cos", f"RX_{port_id}")
#
#        if gpio.get("cos_invert"):
#            sql_gpio = f"!{sql_gpio}"
#
#        lines.extend([
#            f"SQL_GPIO={sql_gpio}",
#        ])        
#    if method == "ctcss" and ctcss_mode in ("rx", "rx_tx") and ctcss_freq:
#        lines.extend([
#            f"CTCSS_FQ={ctcss_freq}",
#            "CTCSS_SNR_OFFSET=0",
#            "CTCSS_OPEN_THRESH=15",
#            "CTCSS_CLOSE_THRESH=9",
#        ])
#
#    return "\n".join(lines)
#
#
#def render_port_tx_section(model, port_id, node):
#    """
#    Render one Tx section for an ICS port.
#    """
#
#    audio = node.get("audio", {})
#    gpio = node.get("gpio", {})
#    squelch = node.get("squelch", {})
#
#    tx_name = f"Tx{port_id}"
#    audio_dev = audio.get("tx_audio", f"alsa:tx{port_id}")
#
#    ctcss_mode = squelch.get("ctcss_mode", "radio")
#    ctcss_freq = squelch.get("ctcss_freq")
#
#    ptt_gpio = gpio.get("ptt", f"TX_{port_id}")
#
#    if gpio.get("ptt_invert"):
#        ptt_gpio = f"!{ptt_gpio}"
#
#    lines = [
#        f"[{tx_name}]",
#        "TYPE=Local",
#        f"AUDIO_DEV={audio_dev}",
#        "AUDIO_CHANNEL=0",
#        "PTT_TYPE=GPIOD",
#        f"PTT_GPIO={ptt_gpio}",
#    ]
#
#    if ctcss_mode == "rx_tx" and ctcss_freq:
#        lines.extend([
#            f"CTCSS_FQ={ctcss_freq}",
#            "CTCSS_LEVEL=9",
#        ])
#
#    return "\n".join(lines)


# def render_multiport_rx_tx_sections(model):
#     """
#     Render all Rx and Tx sections for enabled ICS ports.
#     """
# 
#     nodes = model.get("nodes", {})
#     enabled_ports = model.get("ports", {}).get("enabled", [])
# 
#     rx_sections = []
#     tx_sections = []
# 
#     for port in enabled_ports:
#         port_id = str(port)
#         node = nodes.get(port_id, {})
# 
#         if not node:
#             continue
# 
#         rx_sections.append(
#             render_port_rx_section(model, port_id, node)
#         )
# 
#         tx_sections.append(
#             render_port_tx_section(model, port_id, node)
#         )
# 
#     return {
#         "rx_sections": "\n\n".join(rx_sections),
#         "tx_sections": "\n\n".join(tx_sections),
#     }

@app.route("/node", methods=["GET", "POST"])
def node_page():
    model = load_node_model()
    error = None

    model.setdefault("audio", {})
    model["audio"].setdefault("deemphasis", False)
    model["audio"].setdefault("preemphasis", False)

    if request.method == "POST":
        node_type = request.form.get("node_type")
        callsign = request.form.get(
            "callsign",
            "",
        ).strip().upper()

        tx_delay, tx_delay_errors = parse_tx_delay(
            request.form.get("tx_delay"),
        )

        if node_type not in ("simplex", "repeater"):
            error = "Please select Simplex or Repeater."
        elif not callsign:
            error = "Please enter a callsign."
        elif tx_delay_errors:
            error = " ".join(tx_delay_errors)
        else:
            model["node"]["type"] = node_type
            model["node"]["callsign"] = callsign
            model["tx_delay"] = tx_delay

            model["audio"]["deemphasis"] = (
                request.form.get("deemphasis") == "1"
            )
            model["audio"]["preemphasis"] = (
                request.form.get("preemphasis") == "1"
            )

            save_node_model(model)
            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))
            return redirect(url_for("interface_page"))

    return render_template("node.html", model=model, error=error)


@app.route("/interface", methods=["GET", "POST"])
def interface_page():
    model = load_node_model()
    error = None

    platform_id = model.get("platform", {}).get("id", "unknown")
    supports_gpiod = platform_id in ("raspberry_pi", "nanopi_neo")

    gpio_data = prepare_gpio_lines(platform_id)

    gpio_lines = flatten_gpio_lines(
        data=gpio_data,
        chip_filter="gpiochip0",
    )

    if request.method == "POST":
        interface_mode = request.form.get("interface_mode")

        if interface_mode not in ("hidraw", "gpiod", "hybrid", "serial"):
            interface_mode = "hidraw"

        model.setdefault("interface", {})
        model.setdefault("serial", {})
        model.setdefault("gpio", {})
        model["gpio"].setdefault("sql", {})
        model["gpio"].setdefault("ptt", {})

        model["interface"]["mode"] = interface_mode

        if interface_mode == "hidraw":
            model["interface"]["sql_source"] = "hidraw"
            model["interface"]["ptt_source"] = "hidraw"

        elif interface_mode == "hybrid":
            model["interface"]["sql_source"] = "gpiod"
            model["interface"]["ptt_source"] = "hidraw"

        elif interface_mode == "serial":
            model["interface"]["sql_source"] = "serial"
            model["interface"]["ptt_source"] = "serial"

        else:
            model["interface"]["sql_source"] = "gpiod"
            model["interface"]["ptt_source"] = "gpiod"

        uses_sql_gpiod = (
            model["interface"]["sql_source"] == "gpiod"
        )

        uses_ptt_gpiod = (
            model["interface"]["ptt_source"] == "gpiod"
        )

        if interface_mode == "serial":
            model["serial"]["sql_port"] = request.form.get(
                "serial_sql_port",
                "/dev/ttyS0",
            ).strip()

            model["serial"]["sql_pin"] = request.form.get(
                "serial_sql_pin",
                "CTS",
            ).strip().upper()

            model["serial"]["ptt_port"] = request.form.get(
                "serial_ptt_port",
                "/dev/ttyS0",
            ).strip()

            model["serial"]["ptt_pin"] = request.form.get(
                "serial_ptt_pin",
                "RTS",
            ).strip().upper()

        sql_line = (
            request.form.get("sql_gpio_line")
            if uses_sql_gpiod
            else None
        )

        ptt_line = (
            request.form.get("ptt_gpio_line")
            if uses_ptt_gpiod
            else None
        )

        if (
            uses_sql_gpiod
            and uses_ptt_gpiod
            and sql_line
            and ptt_line
            and sql_line == ptt_line
        ):
            error = "SQL and PTT cannot use the same GPIO line."

            return render_template(
                "interface.html",
                model=model,
                error=error,
                gpio_lines=gpio_lines,
                supports_gpiod=supports_gpiod,
            )

        if uses_sql_gpiod and sql_line:
            model["gpio"]["sql"]["chip"] = "gpiochip0"
            model["gpio"]["sql"]["line"] = int(sql_line)

        if uses_ptt_gpiod and ptt_line:
            model["gpio"]["ptt"]["chip"] = "gpiochip0"
            model["gpio"]["ptt"]["line"] = int(ptt_line)

        save_node_model(model)
        if request.form.get("reconfigure") == "1":
            return redirect(url_for("build_page"))
        return redirect(url_for("squelch_page"))

    return render_template(
        "interface.html",
        model=model,
        error=error,
        gpio_lines=gpio_lines,
        supports_gpiod=supports_gpiod,
    )


@app.route("/reconfigure/reset", methods=["GET", "POST"])
def reconfigure_reset_page():
    if request.method == "POST":
        confirmation = request.form.get("confirmation", "").strip()

        if confirmation != "RESET":
            return render_template(
                "reconfigure_reset.html",
                error="Type RESET to confirm the full reset.",
            )

        MODEL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        if MODEL_FILE.exists():
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = MODEL_BACKUP_DIR / f"node_model.json.bak-{timestamp}"
            shutil.copy2(MODEL_FILE, backup_path)
            MODEL_FILE.unlink()

        return redirect(url_for("start"))

    return render_template(
        "reconfigure_reset.html",
        error=None,
    )
    

@app.route("/squelch", methods=["GET", "POST"])
def squelch_page():
    model = load_node_model()
    error = None

    model.setdefault("squelch", {})

    platform_id = model.get(
        "platform",
        {},
    ).get(
        "id",
        "unknown",
    )

    supports_gpiod = platform_id in (
        "raspberry_pi",
        "nanopi_neo",
    )

    allowed_methods = {
        "hidraw",
        "serial",
        "ctcss",
    }

    if supports_gpiod:
        allowed_methods.add("gpiod")

    if request.method == "POST":
        valid_ctcss_values = {
            value
            for value, _label in CTCSS_FREQUENCIES
        }

        squelch, squelch_errors = (
            parse_squelch_form(
                request.form,
                allowed_methods,
                valid_ctcss_values,
            )
        )

        if squelch_errors:
            error = " ".join(squelch_errors)

        else:
            model["squelch"] = squelch

            model.setdefault("serial", {})
            model.setdefault("hidraw", {})
            model.setdefault("gpio", {})
            model["gpio"].setdefault("sql", {})

            model["serial"]["sql_port"] = str(
                request.form.get(
                    "serial_sql_port",
                )
                or "/dev/ttyS0"
            ).strip()

            model["serial"]["sql_pin"] = str(
                request.form.get(
                    "serial_sql_pin",
                )
                or "CTS"
            ).strip().upper()

            model["serial"]["sql_set_pins"] = str(
                request.form.get(
                    "serial_sql_set_pins",
                )
                or "DTR!RTS"
            ).strip().upper()

            model["hidraw"]["sql_invert"] = (
                request.form.get(
                    "hidraw_sql_invert"
                ) == "yes"
            )

            model["hidraw"]["ptt_invert"] = (
                request.form.get(
                    "hidraw_ptt_invert"
                ) == "yes"
            )

            model["gpio"]["sql"]["invert"] = (
                request.form.get(
                    "sql_gpio_invert"
                ) == "yes"
            )

            save_node_model(model)

            if (
                request.form.get("reconfigure")
                == "1"
            ):
                return redirect(
                    url_for("build_page")
                )

            return redirect(
                url_for("ident_page")
            )

    return render_template(
        "squelch.html",
        model=model,
        supports_gpiod=supports_gpiod,
        error=error,
        ctcss_frequencies=CTCSS_FREQUENCIES,
        version_info=get_version_info(),
    )


@app.route("/ident", methods=["GET", "POST"])
def ident_page():
    model = load_node_model()
    error = None

    model.setdefault("ident", {})
    model["ident"].setdefault("short", {})
    model["ident"].setdefault("long", {})

    short_ident = model["ident"]["short"]
    long_ident = model["ident"]["long"]

    if request.method == "POST":
        try:
            short_ident["mode"] = request.form.get("short_ident_mode")
            short_ident["interval"] = int(
                request.form.get("short_ident_interval", "15")
            )

            long_ident["mode"] = request.form.get("long_ident_mode")
            long_ident["interval"] = int(
                request.form.get("long_ident_interval", "60")
            )

            short_ident["announce_enable"] = (
                request.form.get("short_announce_enable") == "1"
            )

            long_ident["announce_enable"] = (
                request.form.get("long_announce_enable") == "1"
            )

            short_upload = request.files.get("short_announce_file")
            long_upload = request.files.get("long_announce_file")

            short_file = save_ident_upload(
                short_upload,
                "single_short_ident",
            )

            long_file = save_ident_upload(
                long_upload,
                "single_long_ident",
            )

            if short_file:
                short_ident["announce_file"] = short_file
            else:
                short_ident["announce_file"] = short_ident.get(
                    "announce_file",
                    "",
                )

            if long_file:
                long_ident["announce_file"] = long_file
            else:
                long_ident["announce_file"] = long_ident.get(
                    "announce_file",
                    "",
                )

            save_node_model(model)
            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))
            return redirect(url_for("cw_page"))

        except ValueError:
            error = "Identification intervals must be numeric."

        except Exception as exc:
            error = f"Announcement file upload failed: {exc}"

    return render_template(
        "ident.html",
        model=model,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/cw", methods=["GET", "POST"])
def cw_page():
    model = load_node_model()
    error = None

    if "cw" not in model:
        model["cw"] = {
            "amp": -10,
            "pitch": 650,
            "cpm": 95,
        }

    if request.method == "POST":
        try:
            cw_amp = int(request.form.get("cw_amp", "-10"))
            cw_pitch = int(request.form.get("cw_pitch", "650"))
            cw_cpm = int(request.form.get("cw_cpm", "95"))
        except ValueError:
            error = "CW settings must be numeric."
        else:
            if cw_amp > -10 or cw_amp < -30:
                error = "CW amplitude must be between -10 and -30 dB."
            elif cw_pitch < 400 or cw_pitch > 1000:
                error = "CW pitch must be between 400 and 1000 Hz."
            elif cw_cpm < 60 or cw_cpm > 160:
                error = "CW speed must be between 60 and 160 CPM."
            else:
                model["cw"] = {
                    "amp": cw_amp,
                    "pitch": cw_pitch,
                    "cpm": cw_cpm,
                }

                save_node_model(model)
                if request.form.get("reconfigure") == "1":
                    return redirect(url_for("build_page"))
                return redirect(url_for("courtesy_page"))

    return render_template(
        "cw.html",
        model=model,
        error=error,
    )
    

@app.route("/courtesy", methods=["GET", "POST"])
def courtesy_page():
    model = load_node_model()
    error = None

    multiport = is_multiport_build(model)

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})

    has_repeater = (
        model.get("node", {}).get("type") == "repeater"
        or any(
            nodes.get(port_id, {}).get("role") == "repeater"
            for port_id in enabled_ports
        )
    )

    tones = get_installation_tones(model)

    if request.method == "POST":
        courtesy_mode = request.form.get(
            "courtesy_mode",
            "",
        ).strip()

        idle_mode = request.form.get(
            "idle_mode",
            "",
        ).strip()

        closedown_mode = request.form.get(
            "closedown_mode",
            "",
        ).strip()

        if courtesy_mode not in (
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
        ):
            error = "Please select a valid courtesy tone."

        elif idle_mode not in (
            "chime",
            "pip",
            "silence",
        ):
            error = "Please select a valid idle tone."

        elif closedown_mode not in (
            "none",
            "biboop",
            "va",
        ):
            error = "Please select a valid closedown tone."

        else:
            model["tones"] = {
                "courtesy_mode": courtesy_mode,
                "courtesy_frequency": tones.get(
                    "courtesy_frequency",
                    800,
                ),
                "idle_mode": idle_mode,
                "closedown_mode": closedown_mode,
            }

            model.setdefault("build", {})
            model["build"]["tones_configured"] = True

            save_node_model(model)

            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(url_for("online_control_page"))

    return render_template(
        "courtesy.html",
        model=model,
        tones=tones,
        has_repeater=has_repeater,
        is_multiport=multiport,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/online-control", methods=["GET", "POST"])
def online_control_page():
    model = load_node_model()
    multiport = is_multiport_build(model)
    reconfigure = request.values.get("reconfigure") == "1"
    error = None

    controls = []

    if multiport:
        nodes = model.get("nodes", {})
        enabled_ports = [
            str(port)
            for port in model.get("ports", {}).get("enabled", [])
        ]

        if not enabled_ports:
            return redirect(url_for("hardware_ports_page"))

        if any(port_id not in nodes for port_id in enabled_ports):
            return redirect(url_for("port_config_page"))

        for port_id in enabled_ports:
            node = nodes[port_id]
            configuration = node.get("online_control", {})
            controls.append({
                "key": f"port_{port_id}",
                "label": f"Port {port_id} — {node.get('callsign', '')}",
                "target": node,
                "enabled": configuration.get("enabled", False),
                "command": configuration.get("command", ""),
            })
    else:
        configuration = model.get("online_control", {})
        controls.append({
            "key": "single",
            "label": model.get("node", {}).get("callsign") or "Radio logic",
            "target": model,
            "enabled": configuration.get("enabled", False),
            "command": configuration.get("command", ""),
        })

    if request.method == "POST":
        for control in controls:
            key = control["key"]
            control["enabled"] = (
                request.form.get(f"{key}_enabled") == "1"
            )
            control["command"] = request.form.get(
                f"{key}_command", ""
            ).strip()

            command = control["command"]

            if control["enabled"] and (
                len(command) != 6
                or any(character not in "0123456789" for character in command)
            ):
                if error is None:
                    error = (
                        f"{control['label']}: enter exactly six digits "
                        "for the private command."
                    )

        if error is None:
            for control in controls:
                control["target"]["online_control"] = {
                    "enabled": control["enabled"],
                    "command": control["command"],
                }

            save_node_model(model)

            if reconfigure:
                return redirect(url_for("build_page"))

            if multiport:
                return redirect(url_for("port_repeater_page"))

            if model.get("node", {}).get("type") == "repeater":
                return redirect(url_for("repeater_page"))

            return redirect(url_for("modules_page"))

    return render_template(
        "online_control.html",
        controls=controls,
        reconfigure=reconfigure,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/repeater", methods=["GET", "POST"])
def repeater_page():
    model = load_node_model()
    error = None

    if "repeater" not in model:
        model["repeater"] = {
            "idle_timeout": 10,
            "sql_timeout": 180,
            "idle_tone": "chime",
            "down_tone": "biboop",
        }

    if request.method == "POST":
        try:
            idle_timeout = int(request.form.get("idle_timeout", "10"))
            sql_timeout = int(request.form.get("sql_timeout", "180"))
        except ValueError:
            error = "Timeout values must be numeric."
        else:

            if idle_timeout < 0 or idle_timeout > 10:
                error = (
                    "Idle timeout must be between 0 and "
                    "10 seconds."
                )

            elif sql_timeout < 120 or sql_timeout > 300:
                error = "SQL timeout must be between 120 and 300 seconds."

            else:
                repeater = model.setdefault("repeater", {})
                repeater["idle_timeout"] = idle_timeout
                repeater["sql_timeout"] = sql_timeout
                model["repeater"] = repeater

                save_node_model(model)
                if request.form.get("reconfigure") == "1":
                    return redirect(url_for("build_page"))
                return redirect(url_for("modules_page"))

    return render_template(
        "repeater.html",
        model=model,
        error=error,
    )
    

@app.route("/modules", methods=["GET", "POST"])
def modules_page():

    model = load_node_model()

    reconfigure = (
        request.values.get("reconfigure") == "1"
    )
    if is_multiport_build(model):
        route_arguments = {}

        if reconfigure:
            route_arguments["reconfigure"] = "1"

        return redirect(
            url_for(
                "port_modules_page",
                **route_arguments,
            )
        )


    if request.method == "POST":

        modules = [
            "ModuleHelp",
            "ModuleParrot",
        ]

        echolink_enabled = (
            request.form.get("module_echolink") == "yes"
        )

        metar_enabled = (
            request.form.get("module_metar") == "yes"
        )

        if echolink_enabled:
            modules.append("ModuleEchoLink")

        if metar_enabled:
            modules.append("ModuleMetarInfo")

        model["modules"]["enabled"] = modules
        model["echolink"]["enabled"] = echolink_enabled
        model["metar"]["enabled"] = metar_enabled

        save_node_model(model)

        if echolink_enabled:
            route_arguments = {}

            if reconfigure:
                route_arguments["return_to"] = "build"

            return redirect(
                url_for(
                    "echolink_page",
                    **route_arguments,
                )
            )

        if metar_enabled:
            route_arguments = {}

            if reconfigure:
                route_arguments["return_to"] = "build"

            return redirect(
                url_for(
                    "metar_default_page",
                    **route_arguments,
                )
            )

        if reconfigure:
            return redirect(url_for("build_page"))

        return redirect(url_for("reflector_page"))

    return render_template(
        "modules.html",
        model=model,
        reconfigure=reconfigure,
    )


@app.route("/echolink", methods=["GET", "POST"])
def echolink_page():

    model = load_node_model()
    error = None

    return_to = str(
        request.values.get("return_to") or ""
    ).strip()

    if return_to not in {
        "",
        "build",
    }:
        return_to = ""

    location_text = str(
        model.get(
            "echolink",
            {},
        ).get("location") or ""
    ).strip()

    if location_text.lower().startswith("[svx]"):
        location_text = location_text[5:].lstrip()

    if request.method == "POST":

        callsign = request.form.get(
            "echolink_callsign",
            "",
        ).strip().upper()

        password = request.form.get(
            "echolink_password",
            "",
        ).strip()

        sysopname = request.form.get(
            "echolink_sysopname",
            "",
        ).strip()

        location_text = request.form.get(
            "echolink_location",
            "",
        ).strip()

        location = f"[Svx] {location_text}"

        if not callsign.endswith(("-L", "-R")):
            error = "EchoLink callsign must end in -L or -R."

        elif not password:
            error = "EchoLink password is required."

        elif not sysopname:
            error = "EchoLink sysop name is required."

        elif not location_text:
            error = "EchoLink location is required."

        elif len(location_text) > 12:
            error = (
                "EchoLink location must be 12 characters or "
                "fewer after [Svx]."
            )

        else:
            model["echolink"] = {
                "enabled": True,
                "callsign": callsign,
                "password": password,
                "sysopname": sysopname,
                "location": location,
            }

            save_node_model(model)

            if model["metar"]["enabled"]:
                route_arguments = {}

                if return_to:
                    route_arguments["return_to"] = return_to

                return redirect(
                    url_for(
                        "metar_default_page",
                        **route_arguments,
                    )
                )

            if return_to == "build":
                return redirect(url_for("build_page"))

            return redirect(url_for("reflector_page"))

    return render_template(
        "echolink.html",
        model=model,
        location_text=location_text,
        return_to=return_to,
        error=error,
    )


@app.route("/metar-default", methods=["GET", "POST"])
def metar_default_page():
    model = load_node_model()
    error = None
    return_to = str(
        request.values.get("return_to") or ""
    ).strip()

    if return_to not in {
        "",
        "build",
        "port_ident",
    }:
        return_to = ""
    if "metar" not in model:
        model["metar"] = {}

    region = model["metar"].get("region") or "ukwide"

    if region not in METAR_REGIONS:
        region = "ukwide"
        model["metar"]["region"] = region
        save_node_model(model)

    airports = METAR_REGIONS[region]

    if request.method == "POST":
        startdefault = request.form.get("startdefault", "").strip().upper()

        if not startdefault:
            error = "Please select a default airport."
        elif startdefault not in airports:
            error = "Selected airport is not valid for this region."
        else:
            model["metar"]["startdefault"] = startdefault
            save_node_model(model)
            route_arguments = {}

            if return_to:
                route_arguments["return_to"] = return_to

            return redirect(
                url_for(
                    "metar_airports_page",
                    **route_arguments,
                )
            )

    return render_template(
        "metar_default.html",
        model=model,
        airports=airports,
        return_to=return_to,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/metar-airports", methods=["GET", "POST"])
def metar_airports_page():
    model = load_node_model()
    error = None
    return_to = str(
        request.values.get("return_to") or ""
    ).strip()

    if return_to not in {
        "",
        "build",
        "port_ident",
    }:
        return_to = ""
    region = model["metar"].get("region", "ukwide")
    airports = METAR_REGIONS.get(region, {})

    startdefault = model["metar"].get("startdefault", "")

    if request.method == "POST":
        selected_airports = request.form.getlist("airports")

        if len(selected_airports) > 6:
            error = "Please select no more than 6 additional airports."
        else:
            model["metar"]["airports"] = selected_airports
            save_node_model(model)

            if return_to == "build":
                return redirect(url_for("build_page"))

            if return_to == "port_ident":
                return redirect(
                    url_for("port_ident_page")
                )

            return redirect(url_for("reflector_page"))
    return render_template(
        "metar_airports.html",
        model=model,
        airports=airports,
        startdefault=startdefault,
        error=error,
        return_to=return_to,
        version_info=get_version_info(),
    )


FEDERATION_REFLECTORS = {
    "north_america": {
        "name": "North America",
        "host": "north.america.svxlink.net",
        "port": 35300,
        "url": "https://north.america.svxlink.net",
        "suggested_monitor_tgs": [310],
    },
    "ukwide": {
        "name": "UKWide",
        "host": "uk.wide.svxlink.uk",
        "port": 35300,
        "url": "https://ukwide.svxlink.net",
        "suggested_monitor_tgs": [235],
    },
    "australia_nz": {
        "name": "Australia / New Zealand",
        "host": "australia.svxlink.net",
        "port": 35300,
        "url": "https://au.svxlink.net",
        "suggested_monitor_tgs": [505],
    },
    "yorkshire": {
        "name": "YorkshireNet Reflector",
        "host": "yorkshire.svxlink.uk",
        "port": 5310,
        "url": "https://svxlink.qsos.uk/",
        "suggested_monitor_tgs": [23450],
    },
}


@app.route("/reflector", methods=["GET", "POST"])
def reflector_page():
    model = load_node_model()
    error = None

    reflector = model.setdefault("reflector", {})
    multiport = is_multiport_build(model)

    valid_routes = {
        "none",
        "federation",
        "v2",
        "v3",
    }

    selected_route = str(
        reflector.get("route") or "none"
    ).strip().lower()

    if selected_route not in valid_routes:
        selected_route = "none"

    if request.method == "POST":
        requested_route = str(
            request.form.get("reflector_route") or ""
        ).strip().lower()

        if requested_route not in valid_routes:
            error = "Please select a valid reflector access route."

        elif requested_route == "none":
            reflector["enabled"] = False
            reflector["route"] = "none"
            model["reflector"] = reflector

            save_node_model(model)

            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(next_after_reflector(model))

        else:
            previous_route = str(
                reflector.get("route") or "none"
            ).strip().lower()

            reflector["route"] = requested_route

            if previous_route != requested_route:
                reflector["enabled"] = False

            model["reflector"] = reflector
            save_node_model(model)

            route_endpoints = {
                "federation": "reflector_federation_page",
                "v2": "reflector_v2_page",
                "v3": "reflector_v3_page",
            }

            route_arguments = {}

            if request.form.get("reconfigure") == "1":
                route_arguments["reconfigure"] = "1"

            return redirect(
                url_for(
                    route_endpoints[requested_route],
                    **route_arguments,
                )
            )

    primary_port_id = None

    if multiport:
        primary_port_id = str(
            model.get("installation", {}).get(
                "primary_port_id"
            )
            or ""
        )

    return render_template(
        "reflector.html",
        model=model,
        selected_route=selected_route,
        primary_callsign=get_primary_callsign(model),
        primary_port_id=primary_port_id,
        is_multiport=multiport,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/reflector/federation", methods=["GET", "POST"])
def reflector_federation_page():
    model = load_node_model()
    error = None

    reflector = model.setdefault("reflector", {})
    federation = reflector.setdefault("federation", {})

    selected_network_id = str(
        federation.get("network_id") or ""
    ).strip()

    if request.method == "POST":
        selected_network_id = str(
            request.form.get("network_id") or ""
        ).strip()

        auth_key = str(
            request.form.get("auth_key") or ""
        ).strip()

        if selected_network_id not in FEDERATION_REFLECTORS:
            error = "Please select a Federation Family reflector."

        elif len(auth_key) != 16:
            error = (
                "The Federation subscription password must be "
                "exactly 16 characters."
            )

        else:
            selected = FEDERATION_REFLECTORS[
                selected_network_id
            ]

            federation.update({
                "network_id": selected_network_id,
                "name": selected["name"],
                "host": selected["host"],
                "port": selected["port"],
                "auth_key": auth_key,
            })

            reflector["enabled"] = True
            reflector["route"] = "federation"
            reflector["federation"] = federation

            model["reflector"] = reflector
            save_node_model(model)

            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(next_after_reflector(model))

    return render_template(
        "reflector_federation.html",
        model=model,
        reflectors=FEDERATION_REFLECTORS,
        federation=federation,
        selected_network_id=selected_network_id,
        primary_callsign=get_primary_callsign(model),
        error=error,
        version_info=get_version_info(),
    )


@app.route("/reflector/v2", methods=["GET", "POST"])
def reflector_v2_page():
    model = load_node_model()
    error = None

    reflector = model.setdefault("reflector", {})
    v2 = reflector.setdefault("v2", {})

    if request.method == "POST":
        name = str(
            request.form.get("name") or ""
        ).strip()

        host = str(
            request.form.get("host") or ""
        ).strip()

        port_text = str(
            request.form.get("port") or ""
        ).strip()

        auth_key = str(
            request.form.get("auth_key") or ""
        ).strip()

        try:
            port = int(port_text)
        except ValueError:
            port = None

        if not name:
            error = "Please enter a name for the reflector."

        elif not host:
            error = (
                "Please enter the reflector hostname or IP address."
            )

        elif port is None or port < 1 or port > 65535:
            error = (
                "Reflector port must be a number between 1 and 65535."
            )

        elif not auth_key:
            error = (
                "Please enter the authentication password supplied "
                "by the reflector administrator."
            )

        else:
            v2.update({
                "name": name,
                "host": host,
                "port": port,
                "auth_key": auth_key,
            })

            reflector["enabled"] = True
            reflector["route"] = "v2"
            reflector["v2"] = v2

            model["reflector"] = reflector
            save_node_model(model)

            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(next_after_reflector(model))

    return render_template(
        "reflector_v2.html",
        model=model,
        v2=v2,
        primary_callsign=get_primary_callsign(model),
        error=error,
        version_info=get_version_info(),
    )


@app.route("/reflector/v3", methods=["GET", "POST"])
def reflector_v3_page():
    model = load_node_model()
    error = None

    reflector = model.setdefault("reflector", {})
    v3 = reflector.setdefault("v3", {})
    subject = v3.setdefault("subject", {})

    if request.method == "POST":
        name = str(
            request.form.get("name") or ""
        ).strip()

        host = str(
            request.form.get("host") or ""
        ).strip()

        port_text = str(
            request.form.get("port") or ""
        ).strip()

        given_name = str(
            request.form.get("given_name") or ""
        ).strip()

        surname = str(
            request.form.get("surname") or ""
        ).strip()

        organizational_unit = str(
            request.form.get("organizational_unit") or ""
        ).strip()

        organization = str(
            request.form.get("organization") or ""
        ).strip()

        locality = str(
            request.form.get("locality") or ""
        ).strip()

        state_or_province = str(
            request.form.get("state_or_province") or ""
        ).strip()

        country = str(
            request.form.get("country") or ""
        ).strip().upper()

        email = str(
            request.form.get("email") or ""
        ).strip()

        try:
            port = int(port_text)
        except ValueError:
            port = None

        if not name:
            error = "Please enter a name for the reflector."

        elif not host:
            error = (
                "Please enter the reflector hostname or IP address."
            )

        elif port is None or port < 1 or port > 65535:
            error = (
                "Reflector port must be a number between 1 and 65535."
            )

        elif not given_name:
            error = "Please enter the certificate given name."

        elif not surname:
            error = "Please enter the certificate surname."

        elif not organizational_unit:
            error = (
                "Please enter the certificate organizational unit."
            )

        elif not organization:
            error = "Please enter the certificate organization."

        elif not locality:
            error = "Please enter the certificate locality."

        elif not state_or_province:
            error = (
                "Please enter the certificate state or province."
            )

        elif len(country) != 2 or not country.isalpha():
            error = (
                "Certificate country must be a two-letter code."
            )

        elif (
            not email
            or "@" not in email
            or email.startswith("@")
            or email.endswith("@")
        ):
            error = "Please enter a valid certificate email address."

        else:
            subject.update({
                "given_name": given_name,
                "surname": surname,
                "organizational_unit": (
                    organizational_unit
                ),
                "organization": organization,
                "locality": locality,
                "state_or_province": (
                    state_or_province
                ),
                "country": country,
                "email": email,
            })

            v3.update({
                "name": name,
                "host": host,
                "port": port,
                "subject": subject,
            })

            reflector["enabled"] = True
            reflector["route"] = "v3"
            reflector["v3"] = v3

            model["reflector"] = reflector
            save_node_model(model)

            if request.form.get("reconfigure") == "1":
                return redirect(url_for("build_page"))

            return redirect(next_after_reflector(model))

    return render_template(
        "reflector_v3.html",
        model=model,
        v3=v3,
        subject=subject,
        primary_callsign=get_primary_callsign(model),
        error=error,
        version_info=get_version_info(),
    )
## Wifi


@app.route("/wifi", methods=["GET", "POST"])
def wifi_page():
    screen = []
    ssid = ""
    password = ""

    if request.method == "POST":
        ssid = request.form.get("ssid", "").strip()
        password = request.form.get("password", "").strip()

        if "btnScan" in request.form:
            screen = wifi_scan()

        elif "btnConnList" in request.form:
            screen = connection_list()

        elif "btnWifiStatus" in request.form:
            screen = wifi_status()

        elif "btnWifiOn" in request.form:
            screen = wifi_on()

        elif "btnAdd" in request.form:
            screen = connect_wifi(ssid, password)

        elif "btnSwitch" in request.form:
            screen = switch_wifi(ssid)

        elif "btnDelete" in request.form:
            screen = delete_wifi(ssid)

        elif "btnHotspotStatus" in request.form:
            screen = hotspot_status()

        elif "btnStartHotspot" in request.form:
            screen = start_hotspot()

        elif "btnStopHotspot" in request.form:
            screen = stop_hotspot()

    return render_template(
        "wifi.html",
        screen=screen,
        ssid=ssid,
        password=password,
    )
## End Wifi


def get_aprs_server_suggestion(model):
    """
    Return the documented initial APRS server suggestion where applicable.
    """
    environment = (
        model.get("environment", {}).get("region")
        or "british_isles"
    )

    if environment == "british_isles":
        return "euro.aprs2.net:14580"

    return ""


@app.route("/node-info", methods=["GET", "POST"])
def node_info_page():

    model = load_node_model()

    if "node_info" not in model:
        model["node_info"] = {}

    node_info = model["node_info"]

    location_info = model.setdefault(
        "location_info",
        {},
    )

    echolink_enabled = bool(
        model.get("echolink", {}).get("enabled")
    )

    aprs_server_suggestion = get_aprs_server_suggestion(
        model
    )
    primary_port_id = get_primary_port_id(model)

    errors = []

    if request.method == "POST":

        node_info = update_node_information_from_form(
            model,
            request.form,
        )
        location_info = (
            update_location_information_from_form(
                model,
                request.form,
            )
        )

        validation_errors = validate_node_information(
            node_info,
            location_info,
        )

        if validation_errors:
            errors = validation_errors
        else:
            save_node_model(model)

            if is_multiport_build(model):
                return redirect(url_for("topology_page"))

            return redirect(url_for("review_page"))

    return render_template(
        "node_info.html",
        node_info=node_info,
        location_info=location_info,
        echolink_enabled=echolink_enabled,
        aprs_server_suggestion=aprs_server_suggestion,
        primary_port_id=primary_port_id,
        errors=errors,
    )


def update_node_information_from_form(model, form):
    """
    Update the shared node-information model from either the setup
    form or the protected runtime editing form.
    """

    node_info = model.setdefault("node_info", {})
    node_info["enabled"] = (
        form.get("node_info_enabled") == "yes"
    )
    node_info["nodeLocation"] = str(
        form.get("node_location") or ""
    ).strip()

    node_info["qth_name"] = str(
        form.get("qth_name") or ""
    ).strip()

    node_info["sysop"] = str(
        form.get("sysop") or ""
    ).strip().upper()

    node_info["lat"] = str(
        form.get("lat") or ""
    ).strip()

    node_info["long"] = str(
        form.get("long") or ""
    ).strip()

    node_info["locator"] = str(
        form.get("locator") or ""
    ).strip().upper()

    node_info["lat_dms"] = str(
        form.get("lat_dms") or ""
    ).strip().upper()

    node_info["long_dms"] = str(
        form.get("long_dms") or ""
    ).strip().upper()

    node_info["rx_freq"] = str(
        form.get("rx_freq") or ""
    ).strip()

    node_info["tx_freq"] = str(
        form.get("tx_freq") or ""
    ).strip()

    node_info["tx_power"] = str(
        form.get("tx_power") or ""
    ).strip()

    node_info["antenna"] = str(
        form.get("antenna") or ""
    ).strip()

    node_info["antenna_height"] = str(
        form.get("antenna_height") or ""
    ).strip()

    node_info["antenna_direction"] = str(
        form.get("antenna_direction") or ""
    ).strip()

    # Dashboard-generated node information is always public.
    node_info["hidden"] = False

    model["node_info"] = node_info

    return node_info


def update_location_information_from_form(model, form):
    """
    Update installation-wide LocationInfo settings from either the
    setup form or the protected runtime editing form.

    Validation is performed separately.
    """

    location_info = model.setdefault(
        "location_info",
        {},
    )

    location_info["enabled"] = (
        form.get("location_info_enabled") == "yes"
    )

    location_info["aprs_server_list"] = str(
        form.get("aprs_server_list") or ""
    ).strip()

    echolink_enabled = bool(
        model.get("echolink", {}).get("enabled")
    )

    location_info["publish_echolink_status"] = (
        echolink_enabled
        and form.get("publish_echolink_status") == "yes"
    )

    location_info["status_server_list"] = str(
        form.get("status_server_list")
        or "aprs.echolink.org:5199"
    ).strip()

    offset_selection = str(
        form.get("tx_offset_khz") or "0"
    ).strip()

    if offset_selection == "custom":
        offset_value = str(
            form.get("custom_tx_offset_khz") or ""
        ).strip()
    else:
        offset_value = offset_selection

    try:
        numeric_offset = float(offset_value)

        if numeric_offset.is_integer():
            location_info["tx_offset_khz"] = int(
                numeric_offset
            )
        else:
            location_info["tx_offset_khz"] = offset_value

    except (TypeError, ValueError):
        location_info["tx_offset_khz"] = offset_value

    location_info["narrow"] = True

    location_info["antenna_gain"] = str(
        form.get("antenna_gain") or ""
    ).strip()

    antenna_height_unit = str(
        form.get("antenna_height_unit") or "m"
    ).strip().lower()

    if antenna_height_unit not in ("m", "feet"):
        antenna_height_unit = "m"

    location_info["antenna_height_unit"] = (
        antenna_height_unit
    )

    beacon_interval = str(
        form.get("beacon_interval") or "10"
    ).strip()

    try:
        numeric_beacon_interval = float(
            beacon_interval
        )

        if numeric_beacon_interval.is_integer():
            location_info["beacon_interval"] = int(
                numeric_beacon_interval
            )
        else:
            location_info["beacon_interval"] = (
                beacon_interval
            )

    except (TypeError, ValueError):
        location_info["beacon_interval"] = (
            beacon_interval
        )

    location_info["comment"] = str(
        form.get("location_comment") or ""
    ).strip()

    model["location_info"] = location_info

    return location_info


@app.route("/edit/node-info", methods=["GET", "POST"])
def node_info_edit_page():
    saved = request.args.get("saved") == "1"
    reconfigure = (
        request.values.get("reconfigure") == "1"
    )
    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    model = load_node_model()

    if "node_info" not in model:
        model["node_info"] = {}

    node_info = model["node_info"]

    location_info = model.setdefault(
        "location_info",
        {},
    )

    echolink_enabled = bool(
        model.get("echolink", {}).get("enabled")
    )

    aprs_server_suggestion = get_aprs_server_suggestion(
        model
    )

    primary_port_id = get_primary_port_id(model)

    errors = []

    if request.method == "POST":

        node_info = update_node_information_from_form(
            model,
            request.form,
        )

        location_info = (
            update_location_information_from_form(
                model,
                request.form,
            )
        )

        validation_errors = validate_node_information(
            node_info,
            location_info,
        )

        if validation_errors:
            errors = validation_errors
        else:
            save_node_model(model)

            if reconfigure:
                return redirect(url_for("build_page"))

            result = build_svxlink_configuration(
                model,
                restart=True,
            )

            if not result.get("success"):
                errors = [
                    "Node information was saved, but the SvxLink "
                    "configuration rebuild or restart failed."
                ]
            else:
                return redirect(
                    url_for(
                        "node_info_edit_page",
                        saved="1",
                    )
                )

    return render_template(
        "node_info_edit.html",
        node_info=node_info,
        location_info=location_info,
        echolink_enabled=echolink_enabled,
        aprs_server_suggestion=aprs_server_suggestion,
        errors=errors,
        reconfigure=reconfigure,
        saved=saved,
        primary_port_id=primary_port_id,
    )


@app.route("/review", methods=["GET", "POST"])
def review_page():

    model = load_node_model()

    if not model.get(
        "dashboard_auth",
        {},
    ).get("password_hash"):
        return redirect(url_for("setup_auth_page"))

    validation = validate_build(model)

    validation_errors = validation.get(
        "validation_errors",
        [],
    )

    platform_errors = validation.get(
        "platform_errors",
        [],
    )

    review_allowed = not (
        validation_errors
        or platform_errors
    )

    if request.method == "POST" and review_allowed:
        return redirect(url_for("build_page"))

    reflector = model.get("reflector", {})
    reflector_operational = reflector.get(
        "operational",
        {},
    )
    topology = model.get("topology", {})
    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    is_multi_port = is_multiport_build(model)

    return render_template(
        "review.html",
        model=model,
        validation_errors=validation_errors,
        platform_errors=platform_errors,
        review_allowed=review_allowed,
        is_multi_port=is_multi_port,
        enabled_ports=enabled_ports,
        nodes=model.get("nodes", {}),
        primary_port_id=get_primary_port_id(model),
        primary_callsign=get_primary_callsign(model),
        reflector=reflector,
        reflector_operational=reflector_operational,
        topology=topology,
        tones=get_installation_tones(model),
        location_info=model.get("location_info", {}),
        node_information_errors=validate_node_information(
            model.get("node_info", {}),
            model.get("location_info", {}),
        ),
        version_info=get_version_info(),
    )


@app.route("/build", methods=["GET", "POST"])
def build_page():

    model = load_node_model()
    result = None

    hardware = model.get("hardware", {})

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    if not enabled_ports:
        enabled_ports = ["1"]

    is_multi_port = (
        hardware.get("family") == "ics"
        or len(enabled_ports) > 1
    )

    validation = validate_build(model)
    validation_errors = validation.get(
        "validation_errors",
        [],
    )
    platform_errors = validation.get(
        "platform_errors",
        [],
    )

    build_allowed = not (
        validation_errors
        or platform_errors
    )

    if request.method == "POST":

        if not build_allowed:
            return render_template(
                "build.html",
                model=model,
                build_result=None,
                is_multi_port=is_multi_port,
                validation_errors=validation_errors,
                platform_errors=platform_errors,
                build_allowed=False,
                version_info=get_version_info(),
            )

        result = build_svxlink_configuration(
            model,
            restart=True,
        )

        return render_template(
            "done.html",
            model=model,
            svxlink_status=result.get("service_status"),
            build_result=result,
            error=(
                None
                if result.get("success")
                else "Build or launch failed."
            ),
            is_multi_port=is_multi_port,
            version_info=get_version_info(),
        )

    return render_template(
        "build.html",
        model=model,
        build_result=result,
        is_multi_port=is_multi_port,
        validation_errors=validation_errors,
        platform_errors=platform_errors,
        build_allowed=build_allowed,
        version_info=get_version_info(),
    )


@app.route("/setup-auth", methods=["GET", "POST"])
def setup_auth_page():

    model = load_node_model()

    auth = model.get(
        "dashboard_auth",
        {},
    )

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        ).strip()

        if not username or not password:
            error = "Username and password are required."

        else:
            model["dashboard_auth"] = {
                "username": username,
                "password_hash": generate_password_hash(password),
            }

            save_node_model(model)
            session.permanent = True
            session["authorised"] = True

            return redirect(url_for("start"))

    return render_template(
        "setup_auth.html",
        auth=auth,
        error=error,
        version_info=get_version_info(),
    )


@app.route("/done", methods=["GET"])
def done():
    model = load_node_model()

    return render_template(
        "done.html",
        model=model,
        svxlink_status=svxlink_status(),
    )


@app.route("/launch", methods=["POST"])
def launch():
    model = load_node_model()

    result = build_svxlink_configuration(
        model,
        restart=True,
    )

    return render_template(
        "done.html",
        model=model,
        svxlink_status=result.get("service_status"),
        build_result=result,
        error=None if result.get("success") else "Build or launch failed.",
    )


STREAMER_HEALTH_URL = "http://127.0.0.1:8766/health"


def streamer_is_available():
    try:
        with urllib.request.urlopen(
            STREAMER_HEALTH_URL,
            timeout=0.25,
        ) as response:
            if response.status != 200:
                return False

            data = json.load(response)

        return data.get("status") == "ok"

    except (
        OSError,
        ValueError,
        urllib.error.URLError,
    ):
        return False


STREAMER_AUDIO_URL = "http://127.0.0.1:8766/stream.mp3"


@app.route("/stream/live.mp3", methods=["GET"])
def live_stream():
    try:
        upstream = urllib.request.urlopen(
            STREAMER_AUDIO_URL,
        )
    except (OSError, urllib.error.URLError):
        return Response(
            "Live stream unavailable\n",
            status=503,
            mimetype="text/plain",
        )

    def generate():
        try:
            while True:
                chunk = upstream.read(4096)

                if not chunk:
                    break

                yield chunk
        finally:
            upstream.close()

    return Response(
        generate(),
        mimetype="audio/mpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/status", methods=["GET"])
def status_page():
    model = load_node_model()

    system_info = get_system_info()

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    if not enabled_ports:
        enabled_ports = ["1"]
    streamer_available = (
        len(enabled_ports) == 1
        and streamer_is_available()
    )

    selected_port = request.args.get("port", enabled_ports[0])

    if selected_port not in enabled_ports:
        selected_port = enabled_ports[0]

    status = get_runtime_status(
        model,
        selected_port=selected_port,
    )

    monitor_tgs = (
        model.get("reflector", {})
        .get("operational", {})
        .get("monitor_tgs", [])
    )

    activity = get_reflector_activity()

    environment = model.get(
        "environment",
        {}
    ).get(
        "region",
        "british_isles"
    )

    talkgroups = load_talkgroups(environment)

    selected_node = model.get("nodes", {}).get(str(selected_port), {})

    port_modules = []

    if selected_node:
        selected_node_modules = selected_node.get("modules", {})

        if selected_node_modules.get("echolink"):
            port_modules.append("EchoLink")

        if selected_node_modules.get("metar"):
            port_modules.append("MetarInfo")

    else:
        enabled_modules = model.get("modules", {}).get("enabled", [])

        module_display_names = {
            "ModuleHelp": "Help",
            "ModuleParrot": "Parrot",
            "ModuleEchoLink": "EchoLink",
            "ModuleMetarInfo": "MetarInfo",
        }

        port_modules = [
            module_display_names.get(module, module.replace("Module", ""))
            for module in enabled_modules
        ]

    primary_port_id = get_primary_port_id(model)
    primary_callsign = get_primary_callsign(model)

    try:
        topology_memberships = get_topology_memberships(
            model
        )
    except ValueError:
        topology_memberships = {}

    selected_topology_memberships = (
        topology_memberships.get(
            str(selected_port),
            [],
        )
    )

    return render_template(
        "status.html",
        model=model,
        status=status,
        activity=activity,
        port_modules=port_modules,
        talkgroups=talkgroups,
        monitor_tgs=monitor_tgs,
        active_talkgroup=status.get("active_talkgroup"),
        system_info=system_info,
        enabled_ports=enabled_ports,
        selected_port=selected_port,
        primary_port_id=primary_port_id,
        primary_callsign=primary_callsign,
        selected_topology_memberships=(
            selected_topology_memberships
        ),
        port_count=len(enabled_ports),
        streamer_available=streamer_available,
        version_info=get_version_info(),
    )


@app.route("/sound-levels", methods=["GET", "POST"])
def sound_levels_page():
    result = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        try:
            if action == "baseline":
                card_index = int(request.form.get("card_index", "").strip())
                result = apply_safe_baseline(card_index)

            elif action == "set_slider":
                card_index = int(request.form.get("card_index", "").strip())
                numid = int(request.form.get("numid", "").strip())
                raw_value = int(request.form.get("raw_value", "").strip())

                result = set_slider_control(card_index, numid, raw_value)

            else:
                error = "Unknown sound-level action."

        except ValueError as exc:
            error = str(exc)

        except Exception as exc:
            error = f"Failed to update sound levels: {exc}"

    cards = discover_sound_cards()

    return render_template(
        "sound_levels.html",
        cards=cards,
        result=result,
        error=error,
    )


@app.route("/sound-calibration", methods=["GET", "POST"])
def sound_calibration_page():
    error = None
    result = None
    config_file = DEFAULT_SVXLINK_CONFIG
    devcal_values = {
        "mode": "txcal",
        "section": "",
        "modfqs": "1000",
        "caldev": "2405",
        "maxdev": "5000",
        "headroom": "6",
        "audiodev": "",
        "flat": False,
        "wide": False,
    }
    if request.method == "POST":
        action = request.form.get("action", "").strip()
        devcal_values["mode"] = request.form.get("mode", devcal_values["mode"]).strip()
        devcal_values["section"] = request.form.get("section", devcal_values["section"]).strip()
        devcal_values["modfqs"] = request.form.get("modfqs", devcal_values["modfqs"]).strip()
        devcal_values["caldev"] = request.form.get("caldev", devcal_values["caldev"]).strip()
        devcal_values["maxdev"] = request.form.get("maxdev", devcal_values["maxdev"]).strip()
        devcal_values["headroom"] = request.form.get("headroom", devcal_values["headroom"]).strip()
        devcal_values["audiodev"] = request.form.get("audiodev", devcal_values["audiodev"]).strip()
        devcal_values["flat"] = request.form.get("flat") == "on"
        devcal_values["wide"] = request.form.get("wide") == "on"
        try:
            if action == "stop_svxlink":
                result = stop_svxlink_for_calibration()

            elif action == "restart_svxlink":
                result = restart_svxlink_after_calibration()

            elif action == "start_devcal":
                config_file = request.form.get(
                    "config_file",
                    DEFAULT_SVXLINK_CONFIG
                ).strip()

                section = request.form.get("section", "").strip()
                mode = request.form.get("mode", "").strip()
                modfqs = request.form.get("modfqs", "1000.0").strip()
                caldev = request.form.get("caldev", "2404.8").strip()
                maxdev = request.form.get("maxdev", "5000").strip()
                headroom = request.form.get("headroom", "6").strip()
                audiodev = request.form.get("audiodev", "").strip()
                flat = request.form.get("flat") == "on"
                wide = request.form.get("wide") == "on"

                result = start_devcal_session(
                    config_file=config_file,
                    section=devcal_values["section"],
                    mode=devcal_values["mode"],
                    modfqs=devcal_values["modfqs"],
                    caldev=devcal_values["caldev"],
                    maxdev=devcal_values["maxdev"],
                    headroom=devcal_values["headroom"],
                    audiodev=devcal_values["audiodev"],
                    flat=devcal_values["flat"],
                    wide=devcal_values["wide"],
                )

            elif action == "toggle_devcal_tx":
                result = toggle_devcal_tx()

            elif action == "stop_devcal":
                result = stop_devcal_session()

            else:
                error = "Unknown calibration action."

        except Exception as exc:
            error = f"Calibration service action failed: {exc}"

    try:
        audio_sections = discover_audio_sections(config_file)
    except Exception as exc:
        audio_sections = {
            "config_file": config_file,
            "rx_sections": [],
            "tx_sections": [],
        }

        if not error:
            error = f"Could not read SvxLink audio sections: {exc}"

    svxlink_state = get_svxlink_service_state()

    return render_template(
        "sound_calibration.html",
        audio_sections=audio_sections,
        svxlink_state=svxlink_state,
        error=error,
        result=result,
        devcal_running=devcal_is_running(),
        devcal_mode=get_devcal_mode(),
        devcal_tx_state=get_devcal_tx_state(),
        devcal_output=get_devcal_output(),
        devcal_values=devcal_values,
    )


@app.route("/authorise", methods=["GET", "POST"])
def authorise_page():
    error = None
    next_page = request.args.get("next", "")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        next_page = request.form.get("next", "").strip()

        auth = load_node_model().get(
            "dashboard_auth",
            {}
        )

        stored_user = auth.get("username", "")
        stored_hash = auth.get("password_hash", "")

        if (
            username == stored_user
            and stored_hash
            and check_password_hash(stored_hash, password)
        ):
            session.clear()
            session.permanent = True
            session["authorised"] = True

            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)

            return redirect(url_for("status_page"))

        error = "Incorrect username or password."

    return render_template(
        "authorise.html",
        error=error,
        next_page=next_page,
    )


@app.route("/api/status", methods=["GET"])
def api_status_page():
    model = load_node_model()

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    if not enabled_ports:
        enabled_ports = ["1"]

    selected_port = request.args.get(
        "port",
        enabled_ports[0]
    )

    if selected_port not in enabled_ports:
        selected_port = enabled_ports[0]

    status = get_runtime_status(
        model,
        selected_port=selected_port,
    )

    activity = get_reflector_activity()
    system_info = get_system_info()

    return jsonify({
        "status": status,
        "activity": activity,
        "system_info": system_info,
        "enabled_ports": enabled_ports,
        "selected_port": selected_port,
        "port_count": len(enabled_ports),
    })


@app.route("/talkgroups", methods=["GET", "POST"])
def talkgroups_page():
    saved = request.args.get("saved")
    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))    
    model = load_node_model()
        
    environment = model.get(
        "environment",
        {}
    ).get(
        "region",
        "british_isles"
    )

    talkgroups = load_talkgroups(environment)
    error = None
    if request.method == "POST":

        updated = []
        submitted = []

        allowed_colours = {
            "tg-yellow",
            "tg-green",
            "tg-blue",
            "tg-red",
            "tg-orange",
            "tg-purple",
            "tg-gold",
        }

        for index in range(len(talkgroups)):
            tg_id = request.form.get(
                f"id_{index}",
                "",
            ).strip()

            label = request.form.get(
                f"label_{index}",
                "",
            ).strip()

            colour = request.form.get(
                f"colour_{index}",
                "tg-yellow",
            ).strip()

            command = (
                f"91{tg_id}#"
                if tg_id
                else ""
            )

            row = {
                "id": tg_id,
                "label": label,
                "colour": colour,
                "command": command,
            }

            submitted.append(row)

            if not tg_id and not label:
                continue

            if not tg_id or not label:
                if error is None:
                    error = (
                        f"Talkgroup row {index + 1} is "
                        "incomplete. Enter both a talkgroup "
                        "and label, or clear the row."
                    )
                continue

            if not tg_id.isdigit():
                if error is None:
                    error = (
                        f"Talkgroup row {index + 1} must use "
                        "digits only."
                    )
                continue

            if colour not in allowed_colours:
                if error is None:
                    error = (
                        f"Talkgroup row {index + 1} has an "
                        "invalid colour."
                    )
                continue

            updated.append(row)

        if error:
            talkgroups = submitted

        else:
            save_talkgroups(
                environment,
                updated,
            )

            return redirect(
                url_for(
                    "talkgroups_page",
                    saved="1",
                )
            )

    return render_template(
        "talkgroups.html",
        model=model,
        talkgroups=talkgroups,
        saved=saved,
        error=error,
    )


@app.route("/macros", methods=["GET", "POST"])
def macros_page():
    saved = request.args.get("saved")

    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    model = load_node_model()

    macros = model.get("macros", {})
    error = None

    enabled_module_sections = set(
        model.get("modules", {}).get("enabled", [])
    )
    available_macro_modules = [
        module_name
        for section_name, module_name in (
            ("ModuleEchoLink", "EchoLink"),
            ("ModuleMetarInfo", "MetarInfo"),
        )
        if section_name in enabled_module_sections
    ]

    if len(macros) > MACRO_LIMIT:
        error = (
            f"This configuration contains more than {MACRO_LIMIT} macros. "
            "Reduce the list before editing it in the dashboard."
        )

    if request.method == "POST" and len(macros) <= MACRO_LIMIT:
        updated = {}
        seen = set()

        for index in range(MACRO_LIMIT):
            remove = request.form.get(f"remove_{index}") == "yes"

            if remove:
                continue

            number = request.form.get(f"number_{index}", "").strip()
            macro_type = request.form.get(
                f"type_{index}",
                "custom",
            ).strip()

            talkgroup = request.form.get(
                f"talkgroup_{index}",
                "",
            ).strip()

            module = request.form.get(
                f"module_{index}",
                "",
            ).strip()

            module_command = request.form.get(
                f"module_command_{index}",
                "",
            ).strip()

            custom_command = request.form.get(
                f"command_{index}",
                "",
            ).strip()

            row_has_content = any([
                number,
                talkgroup,
                module,
                module_command,
                custom_command,
            ])

            if not row_has_content:
                continue

            if not number:
                error = "Each configured macro requires a macro number."
                break

            if number in seen:
                error = f"Macro {number} is defined more than once."
                break

            try:
                command = build_macro_command(
                    macro_type,
                    talkgroup=talkgroup,
                    module=module,
                    module_command=module_command,
                    custom_command=custom_command,
                )
            except ValueError as exc:
                error = f"Macro {number}: {exc}"
                break

            seen.add(number)
            updated[number] = command

        if error is None:
            model["macros"] = updated
            save_node_model(model)

            result = build_svxlink_configuration(
                model,
                restart=True,
            )

            if not result.get("success"):
                error = "Macros saved, but SvxLink rebuild/restart failed."
            else:
                return redirect(url_for("macros_page", saved="1"))

        macros = updated

    macro_rows = []

    for number, command in macros.items():
        macro = classify_macro_command(command)

        macro_rows.append({
            "number": number,
            "command": (
                command
                if macro.get("type", "custom") == "custom"
                else ""
            ),
            "type": macro.get("type", "custom"),
            "talkgroup": macro.get("talkgroup", ""),
            "module": macro.get("module", ""),
            "module_command": macro.get("module_command", ""),
        })

    while len(macro_rows) < MACRO_LIMIT:
        macro_rows.append({
            "number": "",
            "command": "",
            "type": "custom",
            "talkgroup": "",
            "module": "",
            "module_command": "",
        })

    return render_template(
        "macros.html",
        model=model,
        macro_rows=macro_rows,
        macro_limit=MACRO_LIMIT,
        available_macro_modules=available_macro_modules,
        saved=saved,
        error=error,
    )


@app.route(
    "/ctcss-talkgroups",
    methods=["GET", "POST"],
)
def ctcss_talkgroups_page():

    if not session.get("authorised"):
        return redirect(
            url_for(
                "authorise_page",
                next=request.path,
            )
        )

    model = load_node_model()
    multiport = is_multiport_build(model)
    eligible_ports = []
    selected_port = None
    logic_label = ""
    target = None
    squelch = {}
    errors = []
    saved = request.args.get("saved") == "1"

    empty_configuration = {
        "enabled": False,
        "delay_ms": 0,
        "mappings": [],
    }

    configuration = empty_configuration.copy()

    if multiport:
        nodes = model.get("nodes", {})
        enabled_ports = [
            str(port)
            for port in model.get(
                "ports",
                {},
            ).get("enabled", [])
        ]

        for port_id in enabled_ports:
            node = nodes.get(port_id, {})

            if ctcss_talkgroup_selection_available(
                node.get("squelch", {})
            ):
                eligible_ports.append({
                    "id": port_id,
                    "label": (
                        node.get("name")
                        or f"Port {port_id}"
                    ),
                })

        requested_port = str(
            request.args.get("port") or ""
        ).strip()

        eligible_ids = [
            port["id"]
            for port in eligible_ports
        ]

        if requested_port in eligible_ids:
            selected_port = requested_port
        elif eligible_ids:
            selected_port = eligible_ids[0]

        if selected_port is not None:
            target = nodes.get(selected_port, {})
            squelch = target.get("squelch", {})
            configuration = target.get(
                "ctcss_to_tg",
                empty_configuration,
            )
            logic_label = (
                target.get("name")
                or f"Port {selected_port}"
            )

    else:
        squelch = model.get("squelch", {})

        if ctcss_talkgroup_selection_available(
            squelch
        ):
            target = model
            configuration = model.get(
                "ctcss_to_tg",
                empty_configuration,
            )
            logic_label = (
                model.get("node", {}).get("type")
                or "single-port"
            ).title()

    if not isinstance(configuration, dict):
        configuration = empty_configuration.copy()

    mappings = configuration.get(
        "mappings",
        [],
    )

    if not isinstance(mappings, list):
        mappings = []

    if request.method == "POST":
        if target is None:
            errors.append(
                "No eligible radio logic is available for "
                "local RF CTCSS TalkGroup selection."
            )
        else:
            enabled = (
                request.form.get("enabled") == "yes"
            )

            delay_text = str(
                request.form.get("delay_ms") or ""
            ).strip()

            try:
                delay_ms = int(delay_text)
            except ValueError:
                delay_ms = delay_text

            submitted_mappings = []
            mapping_indices = sorted({
                int(field_name[5:])
                for field_name in request.form
                if (
                    field_name.startswith("tone_")
                    and field_name[5:].isdigit()
                )
            })

            for index in mapping_indices:
                tone_text = str(
                    request.form.get(
                        f"tone_{index}"
                    ) or ""
                ).strip()

                talkgroup_text = str(
                    request.form.get(
                        f"talkgroup_{index}"
                    ) or ""
                ).strip()

                if not tone_text and not talkgroup_text:
                    continue

                tone = normalise_ctcss_tone(
                    tone_text
                )

                if not tone:
                    errors.append(
                        f"Row {index + 1}: select a valid "
                        "CTCSS tone."
                    )
                    tone = tone_text

                if (
                    talkgroup_text.isdigit()
                    and int(talkgroup_text) > 0
                ):
                    talkgroup = str(
                        int(talkgroup_text)
                    )
                else:
                    talkgroup = talkgroup_text

                submitted_mappings.append({
                    "tone": tone,
                    "talkgroup": talkgroup,
                })

            configuration = {
                "enabled": enabled,
                "delay_ms": delay_ms,
                "mappings": submitted_mappings,
            }
            mappings = submitted_mappings

            errors.extend(
                validate_ctcss_talkgroup_configuration(
                    configuration,
                    squelch,
                    label=(
                        f"{logic_label} CTCSS TalkGroup "
                        "selection"
                    ),
                )
            )

            if not errors:
                target["ctcss_to_tg"] = configuration

                if multiport:
                    nodes[selected_port] = target
                    model["nodes"] = nodes
                else:
                    model["ctcss_to_tg"] = (
                        configuration
                    )

                save_node_model(model)

                result = build_svxlink_configuration(
                    model,
                    restart=True,
                )

                if result.get("success"):
                    redirect_arguments = {
                        "saved": "1",
                    }

                    if selected_port is not None:
                        redirect_arguments["port"] = (
                            selected_port
                        )

                    return redirect(
                        url_for(
                            "ctcss_talkgroups_page",
                            **redirect_arguments,
                        )
                    )

                errors.append(
                    "The mappings were saved, but the "
                    "SvxLink rebuild or restart failed."
                )

    return render_template(
        "ctcss_talkgroups.html",
        model=model,
        multiport=multiport,
        eligible_ports=eligible_ports,
        selected_port=selected_port,
        logic_label=logic_label,
        configuration=configuration,
        mappings=mappings,
        ctcss_tones=CTCSS_TONES,
        errors=errors,
        saved=saved,
    )


def normalise_monitor_talkgroup(value):
    """
    Validate and normalize one Monitoring TalkGroup entry.

    A valid entry is a positive integer followed by zero, one,
    or two priority plus signs.
    """

    value = str(value or "").strip()

    if not value:
        return ""

    priority_length = (
        len(value)
        - len(value.rstrip("+"))
    )

    if priority_length > 2:
        raise ValueError(
            "Monitoring TalkGroup priority may use "
            "only + or ++."
        )

    talkgroup_number = value[
        :len(value) - priority_length
        if priority_length
        else len(value)
    ]

    if (
        not talkgroup_number.isdigit()
        or int(talkgroup_number) <= 0
    ):
        raise ValueError(
            "A Monitoring TalkGroup must be a "
            "positive number, optionally followed "
            "by + or ++."
        )

    priority = "+" * priority_length

    return (
        str(int(talkgroup_number))
        + priority
    )


@app.route("/monitor-tgs", methods=["GET", "POST"])
def monitor_tgs_page():
    saved = request.args.get("saved")

    if not session.get("authorised"):
        return redirect(
            url_for(
                "authorise_page",
                next=request.path,
            )
        )

    model = load_node_model()
    reflector = model.setdefault(
        "reflector",
        {},
    )
    operational = reflector.setdefault(
        "operational",
        {},
    )

    operational.setdefault("default_tg", 0)
    operational.setdefault("monitor_tgs", [])
    operational.setdefault(
        "tg_select_timeout",
        60,
    )

    existing = reflector.get(
        "monitor_tg_defs",
        [],
    )
    selected = operational.get(
        "monitor_tgs",
        [],
    )

    error = None
    monitor_rows = []

    if request.method == "POST":
        updated_defs = []
        updated_selected = []
        submitted_rows = []
        seen_talkgroups = set()
        errors = []

        default_tg_text = str(
            request.form.get(
                "default_tg",
                operational.get(
                    "default_tg",
                    0,
                ),
            )
        ).strip()

        timeout_text = str(
            request.form.get(
                "tg_select_timeout",
                operational.get(
                    "tg_select_timeout",
                    60,
                ),
            )
        ).strip()

        if (
            not default_tg_text.isdigit()
            or int(default_tg_text) < 0
        ):
            errors.append(
                "Default TalkGroup must be 0 or "
                "a positive number."
            )
            default_tg = operational.get(
                "default_tg",
                0,
            )
        else:
            default_tg = int(default_tg_text)

        if (
            not timeout_text.isdigit()
            or int(timeout_text) <= 0
        ):
            errors.append(
                "TalkGroup selection timeout must "
                "be a positive number of seconds."
            )
            tg_select_timeout = operational.get(
                "tg_select_timeout",
                60,
            )
        else:
            tg_select_timeout = int(
                timeout_text
            )

        for index in range(6):
            raw_tg_id = request.form.get(
                f"id_{index}",
                "",
            ).strip()

            label = request.form.get(
                f"label_{index}",
                "",
            ).strip()

            enabled = (
                request.form.get(
                    f"enabled_{index}"
                )
                == "yes"
            )

            try:
                tg_id = (
                    normalise_monitor_talkgroup(
                        raw_tg_id
                    )
                )
            except ValueError as exc:
                tg_id = raw_tg_id
                errors.append(
                    f"Row {index + 1}: {exc}"
                )

            submitted_rows.append({
                "id": tg_id,
                "label": label,
                "enabled": enabled,
            })

            if not tg_id:
                if enabled:
                    errors.append(
                        f"Row {index + 1}: select "
                        "requires a TalkGroup number."
                    )

                if label:
                    updated_defs.append({
                        "id": "",
                        "label": label,
                    })

                continue

            base_talkgroup = tg_id.rstrip("+")

            if base_talkgroup in seen_talkgroups:
                errors.append(
                    f"TalkGroup {base_talkgroup} "
                    "is entered more than once."
                )
            else:
                seen_talkgroups.add(
                    base_talkgroup
                )

            updated_defs.append({
                "id": tg_id,
                "label": label,
            })

            if enabled:
                updated_selected.append(tg_id)

        if len(updated_selected) > 6:
            errors.append(
                "Please select no more than six "
                "Monitoring TalkGroups."
            )

        if errors:
            error = " ".join(errors)
            monitor_rows = submitted_rows

        else:
            reflector["monitor_tg_defs"] = (
                updated_defs
            )

            operational["default_tg"] = (
                default_tg
            )
            operational["monitor_tgs"] = (
                updated_selected
            )
            operational[
                "tg_select_timeout"
            ] = tg_select_timeout

            reflector["operational"] = (
                operational
            )
            model["reflector"] = reflector

            save_node_model(model)

            result = build_svxlink_configuration(
                model,
                restart=True,
            )

            if not result.get("success"):
                error = (
                    "Monitoring TalkGroups saved, "
                    "but the SvxLink rebuild or "
                    "restart failed."
                )
                existing = updated_defs
                selected = updated_selected
            else:
                return redirect(
                    url_for(
                        "monitor_tgs_page",
                        saved="1",
                    )
                )

    if not monitor_rows:
        for index in range(6):
            row = (
                existing[index]
                if index < len(existing)
                else {}
            )

            tg_id = str(
                row.get("id") or ""
            ).strip()

            label = str(
                row.get("label") or ""
            ).strip()

            monitor_rows.append({
                "id": tg_id,
                "label": label,
                "enabled": tg_id in selected,
            })

    return render_template(
        "monitor_tgs.html",
        model=model,
        operational=operational,
        monitor_rows=monitor_rows,
        saved=saved,
        error=error,
    )


@app.route("/edit/echolink", methods=["GET", "POST"])
def echolink_edit_page():
    saved = request.args.get("saved")
    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    model = load_node_model()

    if "echolink" not in model:
        model["echolink"] = {}

    echolink = model["echolink"]

    error = None

    if request.method == "POST":

        enabled = (
            request.form.get("enabled") == "yes"
        )

        callsign = request.form.get(
            "callsign",
            "",
        ).strip().upper()

        password = request.form.get(
            "password",
            "",
        ).strip()

        sysopname = request.form.get(
            "sysopname",
            "",
        ).strip()

        location_text = request.form.get(
            "location",
            "",
        ).strip()

        if location_text.lower().startswith("[svx]"):
            location_text = location_text[5:].lstrip()

        location = (
            f"[Svx] {location_text}"
            if location_text
            else ""
        )

        submitted_echolink = {
            "enabled": enabled,
            "callsign": callsign,
            "password": password,
            "sysopname": sysopname,
            "location": location,
        }

        if enabled:
            if not callsign.endswith(("-L", "-R")):
                error = (
                    "EchoLink callsign must end in -L or -R."
                )
            elif not password:
                error = "EchoLink password is required."
            elif not sysopname:
                error = "EchoLink sysop name is required."
            elif not location_text:
                error = "EchoLink location is required."
            elif len(location_text) > 12:
                error = (
                    "EchoLink location must be 12 characters "
                    "or fewer after [Svx]."
                )

        if error:
            echolink = submitted_echolink
        else:
            model["echolink"] = submitted_echolink
            echolink = submitted_echolink

            save_node_model(model)

            result = build_svxlink_configuration(
                model,
                restart=True,
            )

            if not result.get("success"):
                error = (
                    "EchoLink settings were saved, but the "
                    "SvxLink rebuild or restart failed."
                )

            else:
                return redirect(
                    url_for(
                        "echolink_edit_page",
                        saved="1",
                    )
                )

    return render_template(
                "echolink_edit.html",
                echolink=echolink,
                error=error,
                saved=saved
    )


@app.route("/edit/metar", methods=["GET", "POST"])
def metar_edit_page():
    saved = request.args.get("saved")
    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    model = load_node_model()

    if "metar" not in model:
        model["metar"] = {}

    metar = model["metar"]

    error = None

    if request.method == "POST":

        enabled = (
            request.form.get("enabled") == "yes"
        )

        startdefault = request.form.get(
            "startdefault",
            "",
        ).strip().upper()

        airports = [
            value.strip().upper()
            for value in request.form.get(
                "airports",
                "",
            ).split(",")
            if value.strip()
        ]

        submitted_metar = dict(metar)
        submitted_metar.update({
            "enabled": enabled,
            "startdefault": startdefault,
            "airports": airports,
        })

        if enabled:
            if not startdefault:
                error = "Default airport ICAO is required."

            elif not is_valid_icao_format(startdefault):
                error = (
                    "Default airport ICAO must contain exactly "
                    "four letters."
                )

            elif len(airports) > 6:
                error = (
                    "Please enter no more than 6 additional "
                    "airports."
                )

            else:
                invalid_airports = [
                    airport
                    for airport in airports
                    if not is_valid_icao_format(airport)
                ]

                if invalid_airports:
                    error = (
                        "Additional airport ICAO codes must each "
                        "contain exactly four letters."
                    )

            if not error:
                try:
                    unavailable_airports = (
                        find_unavailable_metar_airports(
                            [startdefault] + airports
                        )
                    )

                except MetarVerificationUnavailable:
                    error = (
                        "METAR airport verification is temporarily "
                        "unavailable. No settings were changed."
                    )

                else:
                    if unavailable_airports:
                        error = (
                            "No METAR weather source is available "
                            "for: "
                            + ", ".join(unavailable_airports)
                            + "."
                        )

        if error:
            metar = submitted_metar

        else:
            model["metar"] = submitted_metar
            metar = submitted_metar

            if "modules" not in model:
                model["modules"] = {
                    "enabled": [],
                }

            if "enabled" not in model["modules"]:
                model["modules"]["enabled"] = []

            if enabled:
                if (
                    "ModuleMetarInfo"
                    not in model["modules"]["enabled"]
                ):
                    model["modules"]["enabled"].append(
                        "ModuleMetarInfo"
                    )

            elif (
                "ModuleMetarInfo"
                in model["modules"]["enabled"]
            ):
                model["modules"]["enabled"].remove(
                    "ModuleMetarInfo"
                )

            save_node_model(model)

            result = build_svxlink_configuration(
                model,
                restart=True,
            )

            if (
                result["validation_errors"]
                or result["platform_errors"]
                or result["deployment_errors"]
            ):
                error = "; ".join(
                    result["validation_errors"]
                    + result["platform_errors"]
                    + result["deployment_errors"]
                )

                return render_template(
                    "metar_edit.html",
                    metar=metar,
                    error=error,
                    saved=False,
                )

            return redirect(
                url_for(
                    "metar_edit_page",
                    saved="1",
                )
        )

    return render_template(
        "metar_edit.html",
        metar=metar,
        error=error,
        saved=saved
    )


@app.route("/log", methods=["GET"])
def log_page():

    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    log_file = get_svxlink_log_path()

    log_lines = []

    try:
        if log_file.exists():

            lines = log_file.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()

            log_lines = lines[-250:]

    except Exception as exc:

        log_lines = [
            f"Failed to read log: {exc}"
        ]

    return render_template(
        "log.html",
        log_lines=log_lines,
    )


@app.route("/log-data", methods=["GET"])
def log_data():

    if not session.get("authorised"):
        return ""

    log_file = get_svxlink_log_path()

    try:

        if log_file.exists():

            lines = log_file.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()

            return "\n".join(lines[-250:])

    except Exception as exc:

        return f"Failed to read log: {exc}"

    return ""


@app.route("/maintenance")
def maintenance_page():

    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    return render_template(
        "maintenance.html"
    )


@app.route("/reconfigure", methods=["GET", "POST"])
def reconfigure_page():
    model = load_node_model()

    hardware = model.get("hardware", {})
    nodes = model.get("nodes", {})

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    if not enabled_ports:
        enabled_ports = ["1"]

    is_multi_port = (
        hardware.get("family") == "ics"
        or len(enabled_ports) > 1
    )

    reconfigure_targets = [
        {
            "id": "environment",
            "label": "Environment / Region",
            "route": "environment_page",
            "description": "Change the region/environment settings. The hardware platform is preserved.",
        },
        {
            "id": "timezone",
            "label": "Timezone",
            "route": "timezone_page",
            "description": "Change the configured timezone.",
        },
        {
            "id": "modules",
            "label": "Optional Modules",
            "route": "modules_page",
            "description": (
                "Change EchoLink and METAR module selections "
                "and their associated settings."
            ),
        },
        {
            "id": "reflector",
            "label": "Reflector Connection",
            "route": "reflector_page",
            "description": (
                "Change the reflector access route and "
                "connection settings."
            ),
        },
        {
            "id": "node_info",
            "label": "Node Information / LocationInfo",
            "route": "node_info_edit_page",
            "description": (
                "Change published node details and optional "
                "SvxLink LocationInfo settings."
            ),
        },
    ]

    if is_multi_port:
        reconfigure_targets.extend([
            {
                "id": "hardware_ports",
                "label": "Enabled Hardware Ports",
                "route": "hardware_ports_page",
                "description": "Change which hardware ports are enabled for this build.",
            },
            {
                "id": "port_roles",
                "label": "Port Roles",
                "route": "port_roles_page",
                "description": "Change whether each enabled port is simplex or repeater.",
            },
            {
                "id": "port_config",
                "label": "Port Configuration Menu",
                "route": "port_config_page",
                "description": "Return to the multi-port configuration menu.",
            },
            {
                "id": "installation_identity",
                "label": "Primary Installation Port",
                "route": "installation_identity_page",
                "description": (
                    "Select the primary port and callsign used to "
                    "identify the complete installation."
                ),
            },
            {
                "id": "topology",
                "label": "Port Link Topology",
                "route": "topology_page",
                "description": (
                    "Change reflector membership, local links "
                    "and independent port assignments."
                ),
            },
            {
                "id": "port_final_review",
                "label": "Multi-port Final Review",
                "route": "port_final_review_page",
                "description": "Review the current multi-port model before rebuilding.",
            },
        ])

    else:
        reconfigure_targets.extend([
            {
                "id": "node",
                "label": "Node Details",
                "route": "node_page",
                "description": "Change callsign, node type, location, and related node identity settings.",
            },
            {
                "id": "interface",
                "label": "Radio Interface",
                "route": "interface_page",
                "description": "Change radio interface settings.",
            },
            {
                "id": "squelch",
                "label": "Squelch / COS",
                "route": "squelch_page",
                "description": "Change squelch, COS, or CTCSS settings.",
            },
            {
                "id": "ident",
                "label": "Ident",
                "route": "ident_page",
                "description": "Change ident settings.",
            },
            {
                "id": "cw",
                "label": "CW Settings",
                "route": "cw_page",
                "description": "Change CW pitch, speed, and level settings.",
            },
        ])

        if model.get("node", {}).get("type") == "repeater":
            reconfigure_targets.append({
                "id": "repeater",
                "label": "Repeater Settings",
                "route": "repeater_page",
                "description": "Change repeater timing and behaviour settings.",
            })

        reconfigure_targets.append({
            "id": "review",
            "label": "Review Configuration",
            "route": "review_page",
            "description": "Review the current model before rebuilding.",
        })
    reconfigure_targets.append({
        "id": "online_control",
        "label": "Emergency DTMF Control",
        "route": "online_control_page",
        "description": (
            "Enable or disable private DTMF online/offline "
            "commands for each radio logic."
        ),
    })
    reconfigure_targets.append({
        "id": "tones",
        "label": "Installation Tones",
        "route": "courtesy_page",
        "description": (
            "Change the shared courtesy, idle and closedown "
            "tone settings."
        ),
    })
    reconfigure_targets.extend([
        {
            "id": "build",
            "label": "Build Configuration",
            "route": "build_page",
            "description": "Regenerate the active SvxLink configuration.",
        },
        {
            "id": "full_reset",
            "label": "Full Reset and Start Again",
            "route": "reconfigure_reset_page",
            "description": "Archive the current node model and restart the setup wizard.",
        },
    ])

    if request.method == "POST":
        target_id = request.form.get("target", "").strip()

        for target in reconfigure_targets:
            if target["id"] == target_id:
                route_args = dict(target.get("route_args", {}))

                if target["id"] not in ("build", "full_reset"):
                    route_args["reconfigure"] = "1"

                return redirect(
                    url_for(
                        target["route"],
                        **route_args,
                    )
                )

        return render_template(
            "reconfigure.html",
            reconfigure_targets=reconfigure_targets,
            is_multi_port=is_multi_port,
            enabled_ports=enabled_ports,
            error="Please select a valid reconfiguration option.",
            version_info=get_version_info(),
        )

    return render_template(
        "reconfigure.html",
        reconfigure_targets=reconfigure_targets,
        is_multi_port=is_multi_port,
        enabled_ports=enabled_ports,
        error=None,
        version_info=get_version_info(),
    )


@app.route("/maintenance/restart", methods=["POST"])
def restart_services_page():

    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    restart_services()

    return render_template(
        "message.html",
        title="Restart Requested",
        message="SvxLink services are restarting."
    )


@app.route("/maintenance/reboot", methods=["POST"])
def reboot_device_page():

    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    reboot_device()

    return render_template(
        "message.html",
        title="Reboot Requested",
        message="The device is rebooting."
    )


@app.route("/maintenance/shutdown", methods=["POST"])
def shutdown_device_page():

    if not session.get("authorised"):
        return redirect(url_for("authorise_page", next=request.path))

    shutdown_device()

    return render_template(
        "message.html",
        title="Shutdown Requested",
        message="The device is shutting down."
    )


@app.route("/logout", methods=["GET"])
def logout_page():
    session.pop("authorised", None)
    return redirect(url_for("status_page"))


@app.route("/dtmf", methods=["POST"])
def dtmf_page():
    command = request.form.get("command", "").strip()
    selected_port = str(
        request.values.get("selected_port") or ""
    ).strip()

    model = load_node_model()

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    if selected_port not in enabled_ports:
        selected_port = (
            enabled_ports[0]
            if enabled_ports
            else ""
        )

    try:
        send_dtmf(
            command,
            selected_port=selected_port,
        )

    except Exception as exc:
        print(f"DTMF send failed: {exc}")

    route_arguments = {}

    if selected_port:
        route_arguments["port"] = selected_port

    return redirect(
        url_for(
            "status_page",
            **route_arguments,
        )
    )
    

if __name__ == "__main__":
    ensure_dirs()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
