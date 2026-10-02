import unittest

from models.node_model import new_tetra_configuration
from services.topology_validation import get_incomplete_topology_ports
from unittest.mock import patch

import app as dashboard
from models.node_model import new_node_model
from services.topology_validation import validate_topology_membership


class TetraTopologyTests(unittest.TestCase):

    def model(self):
        tetra = new_tetra_configuration()
        tetra.update({
            "mode": "DMO-RPT",
            "pei_device": "/dev/serial0",
            "baud": 115200,
            "issi": 9999,
            "configured": True,
        })
        return {
            "hardware_profile_id": "generic_single",
            "ports": {"enabled": ["1"]},
            "nodes": {
                "1": {
                    "role": "tetra",
                    "callsign": "G4NAB",
                    "node_details_configured": True,
                    "tetra": tetra,
                    "audio": {
                        "rx_audio": "alsa:plughw:CARD=Radio,DEV=0",
                        "tx_audio": "alsa:plughw:CARD=Radio,DEV=0",
                    },
                    "interface": {
                        "configured": True,
                        "ptt_source": "serial",
                    },
                    "serial": {
                        "ptt_port": "/dev/serial/by-id/usb-ptt",
                        "ptt_pin": "RTS",
                    },
                },
            },
        }

    def test_tetra_does_not_require_conventional_workflow_flags(self):
        self.assertEqual(
            get_incomplete_topology_ports(self.model()),
            [],
        )

    def test_missing_tetra_settings_have_correct_repair_pages(self):
        model = self.model()
        node = model["nodes"]["1"]
        node["tetra"]["configured"] = False
        node["interface"]["configured"] = False

        issues = get_incomplete_topology_ports(model)

        self.assertEqual(
            {issue["endpoint"] for issue in issues},
            {"port_tetra_page", "tetra_interface_page"},
        )
        self.assertTrue(
            all(issue["values"] == {"port_id": "1"} for issue in issues)
        )


    def test_single_tetra_node_information_assigns_and_reviews(self):
        for reflector_enabled in (False, True):
            with self.subTest(reflector_enabled=reflector_enabled):
                model = new_node_model()
                model.update(self.model())
                model["reflector"]["enabled"] = reflector_enabled

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save, patch.object(
                    dashboard,
                    "validate_node_information",
                    return_value=[],
                ):
                    with dashboard.app.test_request_context(
                        "/node-info", method="POST", data={}
                    ):
                        response = dashboard.node_info_page()

                self.assertEqual(
                    response.headers["Location"], "/review"
                )
                save.assert_called_once_with(model)
                self.assertTrue(
                    model["build"]["topology_configured"]
                )
                self.assertEqual(
                    model["topology"]["reflector_link"]["ports"],
                    ["1"] if reflector_enabled else [],
                )
                self.assertEqual(
                    model["topology"]["independent_ports"],
                    [] if reflector_enabled else ["1"],
                )
                self.assertEqual(
                    validate_topology_membership(model), []
                )


if __name__ == "__main__":
    unittest.main()
