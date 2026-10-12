#!/usr/bin/env python3

"""
System maintenance helpers for SvxLink-Dash-V4.1.
"""

import subprocess


def restart_services():
    """
    Restart SvxLink and dashboard services.
    """

    subprocess.Popen(
        [
            "sudo",
            "/usr/bin/systemd-run",
            "--on-active=2",
            "/usr/bin/systemctl",
            "restart",
            "svxlink",
            "svxlink-dash",
        ]
    )


def reboot_device():
    """
    Reboot the device.
    """

    subprocess.Popen(
        [
            "sudo",
            "/usr/sbin/shutdown",
            "-r",
            "now",
        ]
    )


def schedule_reboot(delay_seconds=3):
    return subprocess.run(
        [
            "sudo",
            "-n",
            "/usr/bin/systemd-run",
            f"--on-active={delay_seconds}",
            "--unit=svxlink-dash-reboot",
            "/usr/sbin/shutdown",
            "-r",
            "now",
        ],
        text=True,
        capture_output=True,
    )


def shutdown_device():
    """
    Shut down the device.
    """

    subprocess.Popen(
        [
            "sudo",
            "/usr/sbin/shutdown",
            "-h",
            "now",
        ]
    )