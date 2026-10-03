import tempfile
import unittest
from pathlib import Path

from services.serial_discovery import discover_serial_devices


class SerialDiscoveryTests(unittest.TestCase):

    def test_prefers_persistent_path_without_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            device = root / "ttyUSB0"
            device.touch()

            by_id = root / "serial" / "by-id"
            by_id.mkdir(parents=True)
            persistent = by_id / "usb-FTDI-test"
            persistent.symlink_to(device)

            found = discover_serial_devices(root)

            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["device"], str(persistent))
            self.assertIn("ttyUSB0", found[0]["label"])

    def test_falls_back_to_usb_and_acm_devices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ttyUSB0").touch()
            (root / "ttyACM0").touch()
            (root / "ttyS0").touch()

            found = discover_serial_devices(root)

            self.assertEqual(
                {Path(item["device"]).name for item in found},
                {"ttyUSB0", "ttyACM0"},
            )

    def test_missing_devices_and_broken_links_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            by_id = root / "serial" / "by-id"
            by_id.mkdir(parents=True)
            (by_id / "disconnected").symlink_to(root / "ttyUSB9")

            self.assertEqual(discover_serial_devices(root), [])


if __name__ == "__main__":
    unittest.main()
