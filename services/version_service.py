#!/usr/bin/env python3

"""
Version helpers for SvxLink-Dash.
"""

import subprocess


DASHBOARD_VERSION = "4.1"
DASHBOARD_NAME_PREFIX = "SvxLink-Dash-V"


def get_dashboard_version():
    return DASHBOARD_VERSION


def get_dashboard_name():
    return f"{DASHBOARD_NAME_PREFIX}{DASHBOARD_VERSION}"


def get_dashboard_title():
    return get_dashboard_name()


def get_svxlink_package_version():
    try:
        result = subprocess.run(
            [
                "/usr/bin/dpkg-query",
                "-W",
                "-f=${Version}",
                "svxlink",
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        return result.stdout.strip() or "unknown"

    except Exception:
        return "unknown"


def get_svxlink_engine_version():
    try:
        result = subprocess.run(
            [
                "/usr/bin/svxlink",
                "--version",
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        first_line = result.stdout.strip().splitlines()[0]
        return first_line.replace("SvxLink", "").strip()

    except Exception:
        return "unknown"


def get_version_info():
    return {
        "dashboard_name": get_dashboard_name(),
        "dashboard": get_dashboard_version(),
        "dashboard_title": get_dashboard_title(),
        "package": get_svxlink_package_version(),
        "engine": get_svxlink_engine_version(),
    }