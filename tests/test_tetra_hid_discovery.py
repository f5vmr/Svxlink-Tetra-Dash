import tempfile
import unittest
from pathlib import Path

from services.dual_usb_service import discover_cmedia_hidraw_devices


class TetraHidDiscoveryTests(unittest.TestCase):

    def test_lists_cmedia_and_excludes_other_vendors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dev = root / "dev"
            sys_hid = root / "sys"
            dev.mkdir()

            for name, vendor in (
                ("hidraw0", "00000D8C"),
                ("hidraw1", "00001234"),
            ):
                (dev / name).touch()
                identity = sys_hid / name / "device"
                identity.mkdir(parents=True)
                (identity / "uevent").write_text(
                    f"HID_ID=0003:{vendor}:0000013A\n",
                    encoding="utf-8",
                )

            found = discover_cmedia_hidraw_devices(dev, sys_hid)

            self.assertEqual(len(found), 1)
            self.assertEqual(
                found[0]["device"], str(dev / "hidraw0")
            )

    def test_missing_identity_is_not_offered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "hidraw0").touch()

            self.assertEqual(
                discover_cmedia_hidraw_devices(
                    root, root / "missing-sys"
                ),
                [],
            )

    def test_no_connected_devices_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                discover_cmedia_hidraw_devices(directory),
                [],
            )


if __name__ == "__main__":
    unittest.main()
