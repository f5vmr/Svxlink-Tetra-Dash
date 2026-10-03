#!/usr/bin/env python3

"""
Inspect the two-device USB audio and HIDRAW installation.
"""

import os

from pathlib import Path

from services.sound_discovery import discover_sound_cards


CMEDIA_VENDOR_ID = "00000D8C"

EXPECTED_HIDRAW_DEVICES = (
    Path("/dev/hidraw0"),
    Path("/dev/hidraw1"),
)

SYS_CLASS_HIDRAW = Path("/sys/class/hidraw")


def is_duplex_usb_card(card):
    """Return True for a duplex USB audio device."""

    description = (
        f"{card.get('name', '')} "
        f"{card.get('description', '')}"
    ).lower()

    return (
        bool(card.get("has_playback"))
        and bool(card.get("has_capture"))
        and "usb" in description
    )


def read_hidraw_uevent(
    device,
    sys_class_hidraw=SYS_CLASS_HIDRAW,
):
    """Read the kernel identity record for one HIDRAW device."""

    device = Path(device)
    uevent_path = (
        Path(sys_class_hidraw)
        / device.name
        / "device"
        / "uevent"
    )

    try:
        return uevent_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


def is_cmedia_hidraw(
    device,
    sys_class_hidraw=SYS_CLASS_HIDRAW,
):
    """Return True when a HIDRAW device belongs to C-Media."""

    uevent = read_hidraw_uevent(
        device,
        sys_class_hidraw=sys_class_hidraw,
    )

    for line in uevent.splitlines():
        if not line.startswith("HID_ID="):
            continue

        components = line.partition("=")[2].split(":")

        if len(components) != 3:
            return False

        return components[1].upper() == CMEDIA_VENDOR_ID

    return False


def discover_cmedia_hidraw_devices(
    dev_root="/dev",
    sys_class_hidraw=SYS_CLASS_HIDRAW,
):
    """List connected C-Media HID devices for manual selection."""
    return [
        {
            "device": str(device),
            "label": f"C-Media PTT — {device.name}",
        }
        for device in sorted(Path(dev_root).glob("hidraw*"))
        if device.exists()
        and is_cmedia_hidraw(
            device,
            sys_class_hidraw=sys_class_hidraw,
        )
    ]


def inspect_dual_usb_hardware(
    cards=None,
    hidraw_devices=EXPECTED_HIDRAW_DEVICES,
    sys_class_hidraw=SYS_CLASS_HIDRAW,
    access_check=os.access,
):
    """
    Inspect and assign two USB audio and HIDRAW interfaces.

    Duplex USB audio devices are ordered by their current ALSA card
    indices. Their named ALSA devices are retained so unrelated host
    sound hardware does not affect the final SvxLink configuration.
    """

    if cards is None:
        cards = discover_sound_cards()

    usb_cards = sorted(
        (
            card
            for card in cards
            if is_duplex_usb_card(card)
        ),
        key=lambda card: int(
            card.get("index", -1)
        ),
    )

    errors = []
    ports = []

    if len(usb_cards) != 2:
        errors.append(
            "Exactly two duplex USB audio devices are required; "
            f"{len(usb_cards)} were detected."
        )

    hidraw_devices = [
        Path(device)
        for device in hidraw_devices
    ]

    for port_number in (1, 2):
        card_position = port_number - 1

        card = (
            usb_cards[card_position]
            if len(usb_cards) > card_position
            else None
        )

        hidraw_device = (
            hidraw_devices[card_position]
            if len(hidraw_devices) > card_position
            else Path(
                f"/dev/hidraw{card_position}"
            )
        )

        audio_index = (
            int(card.get("index", -1))
            if card
            else None
        )

        audio_dev = (
            card.get("audio_dev", "")
            if card
            else ""
        )

        if card and not audio_dev:
            audio_dev = (
                f"alsa:plughw:{audio_index}"
            )

        hidraw_exists = hidraw_device.exists()
        hidraw_accessible = (
            hidraw_exists
            and access_check(
                hidraw_device,
                os.R_OK | os.W_OK,
            )
        )
        hidraw_is_cmedia = (
            hidraw_exists
            and is_cmedia_hidraw(
                hidraw_device,
                sys_class_hidraw=sys_class_hidraw,
            )
        )

        if card is None:
            errors.append(
                f"Port {port_number} requires a duplex "
                "USB audio device."
            )

        if not hidraw_exists:
            errors.append(
                f"Port {port_number} HID device was not found: "
                f"{hidraw_device}"
            )
        elif not hidraw_is_cmedia:
            errors.append(
                f"Port {port_number} HID device is not a "
                f"C-Media interface: {hidraw_device}"
            )
        elif not hidraw_accessible:
            errors.append(
                f"Port {port_number} HID device is not readable "
                f"and writable: {hidraw_device}"
            )

        ports.append({
            "port": str(port_number),
            "audio_index": audio_index,
            "audio_dev": audio_dev,
            "audio_name": (
                card.get("name", "")
                if card
                else ""
            ),
            "audio_description": (
                card.get("description", "")
                if card
                else ""
            ),
            "hidraw_device": str(hidraw_device),
            "hidraw_exists": hidraw_exists,
            "hidraw_accessible": hidraw_accessible,
            "hidraw_is_cmedia": hidraw_is_cmedia,
        })

    return {
        "ready": not errors,
        "ports": ports,
        "errors": errors,
    }
