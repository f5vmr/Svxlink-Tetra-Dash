#!/usr/bin/env python3

import unittest
import app as dashboard
from models.node_model import (
    is_multiport_model,
    new_tetra_configuration,
)


class TetraModelTests(unittest.TestCase):
    def test_connection_and_identity_require_configuration(self):
        tetra = new_tetra_configuration()

        for field in ("mode", "pei_device", "baud", "issi"):
            self.assertIsNone(tetra[field])

        self.assertFalse(tetra["configured"])
        self.assertEqual(tetra["radio_model"], "MTM5400")
        self.assertEqual(tetra["gssi"], 1)
        self.assertEqual(tetra["mcc"], 901)
        self.assertEqual(tetra["mnc"], 16383)

    def test_ports_have_independent_tetra_settings(self):
        first = new_tetra_configuration()
        second = new_tetra_configuration()

        first["issi"] = 23401
        first["pei_device"] = "/dev/serial0"

        self.assertIsNone(second["issi"])
        self.assertIsNone(second["pei_device"])


    def test_port_initialization_preserves_tetra_settings(self):
        model = {
            "ports": {"enabled": ["1", "2"]},
            "port_roles": {
                "1": {"role": "tetra"},
                "2": {"role": "repeater"},
            },
            "nodes": {
                "1": {
                    "tetra": {
                        "issi": 23401,
                        "pei_device": "/dev/serial0",
                        "baud": 9600,
                        "mode": "DMO-RPT",
                    },
                },
            },
        }

        nodes = dashboard.initialise_port_nodes(
            model, {"port_map": {}},
        )

        self.assertEqual(nodes["1"]["role"], "tetra")
        self.assertEqual(nodes["2"]["role"], "repeater")
        self.assertNotIn("tetra", nodes["2"])

        tetra = nodes["1"]["tetra"]
        self.assertEqual(tetra["issi"], 23401)
        self.assertEqual(tetra["pei_device"], "/dev/serial0")
        self.assertEqual(tetra["baud"], 9600)
        self.assertEqual(tetra["mode"], "DMO-RPT")
        self.assertEqual(tetra["end_cmd"], "ATH")
        self.assertFalse(tetra["configured"])


    def test_single_tetra_port_uses_port_workflow(self):
        for role_source in ("port_roles", "nodes"):
            with self.subTest(role_source=role_source):
                model = {
                    "hardware_profile_id": "generic_single",
                    "hardware": {"family": "usb"},
                    "ports": {"enabled": ["1"]},
                    role_source: {"1": {"role": "tetra"}},
                }

                self.assertTrue(is_multiport_model(model))
                self.assertTrue(dashboard.is_multiport_build(model))

        for role in ("simplex", "repeater"):
            with self.subTest(role=role):
                model = {
                    "hardware_profile_id": "generic_single",
                    "ports": {"enabled": ["1"]},
                    "nodes": {
                        "1": {"role": role},
                        "2": {"role": "tetra"},
                    },
                }

                self.assertFalse(is_multiport_model(model))
                self.assertFalse(dashboard.is_multiport_build(model))


if __name__ == "__main__":
    unittest.main()
