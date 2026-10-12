# services/ics_prepare_service.py

import subprocess
from pathlib import Path


ICS_HELPER = "/usr/local/sbin/svxlink_dashboard_ics_prepare"
OVERLAY_DIR = Path("/boot/firmware/overlays")
CONFIG_FILE = Path("/boot/firmware/config.txt")

VALID_ICS_PROFILES = {
    "ics_1x": {
        "name": "ICS 1x",
        "overlay": "ics_1x",
        "expected_i2c": ["0x20"],
        "max_ports": 1,
    },
    "ics_2x": {
        "name": "ICS 2x",
        "overlay": "ics_2x",
        "expected_i2c": ["0x20"],
        "max_ports": 2,
    },
    "ics_4x": {
        "name": "ICS 4x",
        "overlay": "ics_4x",
        "expected_i2c": ["0x26", "0x27"],
        "max_ports": 4,
    },
    "ics_8x": {
        "name": "ICS 8x",
        "overlay": "ics_8x",
        "expected_i2c": ["0x25", "0x26", "0x27"],
        "max_ports": 8,
    },
}


def _run_helper(*args):
    cmd = ["sudo", "-n", ICS_HELPER, *args]
    source = (
        Path(__file__).resolve().parent.parent
        / "install"
        / "svxlink_dashboard_ics_prepare"
    )

    try:
        if source.read_bytes() != Path(ICS_HELPER).read_bytes():
            return {
                "ok": False,
                "returncode": 1,
                "stdout": "",
                "stderr": (
                    "The installed ICS preparation helper is outdated. "
                    "Run the dashboard installer again to update it, "
                    "then return to ICS preparation."
                ),
                "command": " ".join(cmd),
            }
    except OSError as exc:
        return {
            "ok": False,
            "returncode": 1,
            "stdout": "",
            "stderr": f"Unable to verify the ICS preparation helper: {exc}",
            "command": " ".join(cmd),
        }

    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
    )

    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "command": " ".join(cmd),
    }


def helper_available():
    return Path(ICS_HELPER).exists()


def get_ics_profiles():
    return VALID_ICS_PROFILES


def get_profile(profile_id):
    return VALID_ICS_PROFILES.get(profile_id)


def overlay_file_exists(profile_id):
    profile = get_profile(profile_id)
    if not profile:
        return False

    overlay = profile["overlay"]
    return (OVERLAY_DIR / f"{overlay}.dtbo").exists()


def current_ics_overlay():
    """
    Returns the currently active dtoverlay=ics_* line value,
    or None if no ICS overlay is present.
    """
    if not CONFIG_FILE.exists():
        return None

    try:
        lines = CONFIG_FILE.read_text().splitlines()
    except Exception:
        return None

    active = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        if stripped.startswith("dtoverlay=ics"):
            active.append(stripped.split("=", 1)[1].strip())

    if not active:
        return None

    # If multiple lines exist, return them joined so the UI can warn.
    if len(active) > 1:
        return ", ".join(active)

    return active[0]


def check_i2c():
    return _run_helper("check-i2c")


def enable_i2c():
    return _run_helper("enable-i2c")


def check_overlay():
    return _run_helper("check-overlay")


def gpio_names():
    return _run_helper("gpio-names")


def set_overlay(profile_id):
    profile = get_profile(profile_id)

    if not profile:
        return {
            "ok": False,
            "returncode": 1,
            "stdout": "",
            "stderr": f"Unknown ICS profile: {profile_id}",
            "command": "",
        }

    return _run_helper("set-overlay", profile["overlay"])


def configure_audio_boot(profile_id):
    """
    Configure boot-time audio overlays required by selected ICS profile.
    """

    return _run_helper(
        "configure-audio-boot",
        profile_id,
    )


def configure_pcm1803(profile_id):
    profile = get_profile(profile_id)

    if not profile:
        return {
            "ok": False,
            "returncode": 1,
            "stdout": "",
            "stderr": f"Unknown ICS profile: {profile_id}",
            "command": "",
        }

    return _run_helper("configure-pcm1803", profile_id)


def build_ics_status(profile_id=None):
    """
    Creates a simple status dict for the preparation page.
    """
    selected_profile = get_profile(profile_id) if profile_id else None

    status = {
        "helper_available": helper_available(),
        "current_overlay": current_ics_overlay(),
        "profiles": VALID_ICS_PROFILES,
        "selected_profile_id": profile_id,
        "selected_profile": selected_profile,
        "selected_overlay_exists": False,
        "i2c": None,
        "overlay_check": None,
        "gpio_names": None,
    }

    if selected_profile:
        status["selected_overlay_exists"] = overlay_file_exists(profile_id)

    if status["helper_available"]:
        status["i2c"] = check_i2c()
        status["overlay_check"] = check_overlay()
        status["gpio_names"] = gpio_names()

    return status
