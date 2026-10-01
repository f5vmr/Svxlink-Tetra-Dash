#!/usr/bin/env python3

import json
import subprocess
import time
from pathlib import Path

import gpiod


MODEL_FILE = Path("/opt/dashboard/config/node_model.json")
LINE_NAME = "PCM_PDWN"
REQUIRED_PROFILES = {"ics_4x", "ics_8x"}


def selected_profile_requires_pcm1803():
    try:
        model = json.loads(MODEL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False

    hardware = model.get("hardware", {})

    profile_id = (
        model.get("hardware_profile_id")
        or hardware.get("profile_id")
        or hardware.get("id")
        or hardware.get("profile")
    )

    return profile_id in REQUIRED_PROFILES


def find_gpio_line_by_name(line_name):
    result = subprocess.run(
        ["gpioinfo"],
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "gpioinfo failed: "
            + (result.stderr.strip() or result.stdout.strip())
        )

    current_chip = None

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()

        if line.startswith("gpiochip"):
            current_chip = line.split()[0].rstrip(":")
            continue

        if not current_chip:
            continue

        if f'"{line_name}"' not in line:
            continue

        # Example:
        # line  11: "PCM_PDWN" unused input active-high
        before_colon = line.split(":", 1)[0]
        parts = before_colon.split()

        if len(parts) < 2:
            continue

        return current_chip, int(parts[1])

    raise RuntimeError(f"Could not find GPIO line named {line_name}")


def main():
    if not selected_profile_requires_pcm1803():
        print("PCM1803 enable not required for selected hardware profile.")
        return

    chip_name, line_offset = find_gpio_line_by_name(LINE_NAME)
    chip_path = str(Path("/dev") / chip_name)

    if hasattr(gpiod, "request_lines"):
        from gpiod.line import Direction, Value

        with gpiod.request_lines(
            chip_path,
            consumer="PCM1803-enable",
            config={
                line_offset: gpiod.LineSettings(
                    direction=Direction.OUTPUT,
                    active_low=False,
                    output_value=Value.ACTIVE,
                )
            },
        ) as request:
            print(
                f"PCM1803 enabled on {chip_name} "
                f"line {line_offset} ({LINE_NAME})",
                flush=True,
            )

            while True:
                request.set_value(line_offset, Value.ACTIVE)
                time.sleep(3600)
    else:
        chip = gpiod.Chip(chip_path)
        line = chip.get_line(line_offset)

        line.request(
            consumer="PCM1803-enable",
            type=gpiod.LINE_REQ_DIR_OUT,
            default_vals=[1],
        )

        try:
            print(
                f"PCM1803 enabled on {chip_name} "
                f"line {line_offset} ({LINE_NAME})",
                flush=True,
            )

            while True:
                line.set_value(1)
                time.sleep(3600)
        finally:
            line.release()
            chip.close()


if __name__ == "__main__":
    main()
