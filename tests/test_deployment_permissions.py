#!/usr/bin/env python3

import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from models.node_model import new_node_model
from services import node_info_service
from services.svxlink_service import write_text_file


class DeploymentPermissionTests(unittest.TestCase):

    def test_generated_text_file_uses_managed_mode(self):

        with tempfile.TemporaryDirectory() as directory:
            target = (
                Path(directory)
                / "svxlink.d"
                / "ModuleEchoLink.conf"
            )

            write_text_file(
                target,
                "NAME=EchoLink\n",
            )

            mode = target.stat().st_mode & 0o777

        self.assertEqual(mode, 0o664)

    def test_node_info_json_uses_managed_mode(self):

        model = new_node_model()

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "node_info.json"

            with patch.object(
                node_info_service,
                "NODE_INFO_FILE",
                target,
            ):
                written = (
                    node_info_service.write_node_info_json(
                        model
                    )
                )

            mode = target.stat().st_mode & 0o777

        self.assertEqual(written, target)
        self.assertEqual(mode, 0o664)

    def test_installer_enables_svxlink_for_boot(self):
        installer_text = Path(
            "install/install-dashboard.sh"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "\nsystemctl enable svxlink.service\n",
            installer_text,
        )
        self.assertNotIn(
            "\nsystemctl enable --now svxlink.service\n",
            installer_text,
        )


    def test_installer_prepares_account_before_dashboard_start(self):
        installer_text = Path(
            "install/install-dashboard.sh"
        ).read_text(encoding="utf-8")

        preparation_command = (
            '"$SERVICE_ACCOUNT_HELPER_DEST" no-gpio'
        )
        dashboard_restart = (
            "systemctl restart svxlink-dash\n"
        )

        self.assertIn(
            preparation_command,
            installer_text,
        )
        self.assertIn(
            dashboard_restart,
            installer_text,
        )
        self.assertLess(
            installer_text.index(preparation_command),
            installer_text.index(dashboard_restart),
        )

    def test_installer_replaces_recognised_dashboard_safely(self):
        installer_text = Path(
            "install/install-dashboard.sh"
        ).read_text(encoding="utf-8")

        self.assertNotIn(
            "\n    git pull\n",
            installer_text,
        )
        self.assertIn(
            (
                '*"/SvxLink-Dash-V3.git"|'
                '*"/SvxLink-Dash-V3")'
            ),
            installer_text,
        )
        self.assertIn(
            "SvxLink-Dash-V3.0.git",
            installer_text,
        )
        self.assertIn(
            "SvxLink-Dash-V3.1.git",
            installer_text,
        )
        self.assertIn(
            "SvxLink-Dash-V4.0.git",
            installer_text,
        )
        self.assertIn(
            "SvxLink-Dash-V4.1.git",
            installer_text,
        )
        self.assertIn(
            'BACKUP_ROOT="/var/backups/svxlink-dash"',
            installer_text,
        )
        self.assertIn(
            "Unrecognised existing dashboard installation",
            installer_text,
        )

    def test_installer_handles_obstructing_sudoers_path_safely(self):
        installer_text = Path(
            "install/install-dashboard.sh"
        ).read_text(encoding="utf-8")

        required_fragments = (
            'SUDOERS_FILE="/etc/sudoers.d/svxlink-dash"',
            'if [ -L "$SUDOERS_FILE" ]; then',
            'if [ -d "$SUDOERS_FILE" ]; then',
            'if ! rmdir "$SUDOERS_FILE"; then',
            "Its contents have been preserved for manual review.",
            'cat > "$SUDOERS_FILE" <<\'EOF\'',
            'chmod 0440 "$SUDOERS_FILE"',
            'visudo -c -f "$SUDOERS_FILE"',
        )

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, installer_text)


if __name__ == "__main__":
    unittest.main()
