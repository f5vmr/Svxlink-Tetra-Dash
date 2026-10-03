from pathlib import Path


def discover_serial_devices(dev_root="/dev"):
    """List USB serial devices, preferring persistent by-id paths."""
    root = Path(dev_root)
    devices = []
    seen = set()

    candidates = sorted((root / "serial" / "by-id").glob("*"))
    candidates += sorted(root.glob("ttyUSB*"))
    candidates += sorted(root.glob("ttyACM*"))

    for path in candidates:
        try:
            if not path.exists():
                continue
            resolved = path.resolve(strict=True)
        except OSError:
            continue

        if resolved in seen:
            continue

        seen.add(resolved)
        devices.append({
            "device": str(path),
            "label": f"{path.name} — {resolved.name}",
        })

    return devices
