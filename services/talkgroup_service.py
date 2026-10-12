#!/usr/bin/env python3

"""
Talkgroup configuration helpers for SvxLink-Dash-V4.1.
"""

from pathlib import Path
import json

from data.talkgroups import TALKGROUPS


APP_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = APP_ROOT / "config"

TALKGROUP_FILE = CONFIG_DIR / "talkgroups.json"
MAX_TALKGROUP_BUTTONS = 18


def ensure_config_dir():
    """
    Ensure config directory exists.
    """

    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def load_talkgroups(environment):
    """
    Load talkgroups from local JSON override if present.

    Falls back to built-in defaults.
    """

    ensure_config_dir()

    if TALKGROUP_FILE.exists():

        try:
            data = json.loads(
                TALKGROUP_FILE.read_text(
                    encoding="utf-8"
                )
            )

            return pad_talkgroups(
                data.get(
                    environment,
                    TALKGROUPS.get(environment, [])
                )
            )

        except Exception:
            pass

    return pad_talkgroups(
        TALKGROUPS.get(environment, [])
    )


def save_talkgroups(environment, talkgroups):
    """
    Save talkgroups to local JSON config.
    """

    ensure_config_dir()

    data = {}

    if TALKGROUP_FILE.exists():

        try:
            data = json.loads(
                TALKGROUP_FILE.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            data = {}

    data[environment] = talkgroups

    TALKGROUP_FILE.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )

    return TALKGROUP_FILE


def pad_talkgroups(talkgroups):
    """
    Ensure the dashboard always has 18 editable button slots.
    """

    padded = list(talkgroups[:MAX_TALKGROUP_BUTTONS])

    while len(padded) < MAX_TALKGROUP_BUTTONS:
        padded.append({
            "id": "",
            "label": "",
            "colour": "tg-yellow",
            "command": "",
        })

    return padded