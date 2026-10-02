import unittest
from unittest.mock import patch

import app as dashboard
from models.node_model import new_node_model


class TetraEntryTests(unittest.TestCase):

    def post(self, model, extra=None):
        form = {
            "node_type": "tetra",
            "callsign": "g4nab",
            "tx_delay": "500",
        }
        form.update(extra or {})

        with patch.object(
            dashboard, "load_node_model", return_value=model
        ), patch.object(
            dashboard, "save_node_model"
        ) as save, patch.object(
            dashboard,
            "render_template",
            side_effect=lambda template, **context: context,
        ):
            with dashboard.app.test_request_context(
                "/node", method="POST", data=form
            ):
                response = dashboard.node_page()

        return response, save

    def test_single_tetra_entry_creates_one_radio(self):
        model = new_node_model()
        model["ports"] = {"enabled": ["1"]}

        response, save = self.post(model)

        self.assertEqual(response.headers["Location"], "/port-tetra/1")
        save.assert_called_once_with(model)
        self.assertEqual(model["ports"]["enabled"], ["1"])
        self.assertEqual(set(model["nodes"]), {"1"})
        node = model["nodes"]["1"]
        self.assertEqual(node["role"], "tetra")
        self.assertEqual(node["callsign"], "G4NAB")
        self.assertTrue(node["node_details_configured"])
        self.assertFalse(node["tetra"]["configured"])

    def test_reconfiguration_preserves_saved_tetra_settings(self):
        model = new_node_model()
        model["ports"] = {"enabled": ["1"]}
        model["nodes"] = {
            "1": {
                "role": "tetra",
                "tetra": {
                    "pei_device": "/dev/serial0",
                    "issi": 9999,
                },
            },
        }

        response, save = self.post(model, {"reconfigure": "1"})

        self.assertEqual(
            response.headers["Location"],
            "/port-tetra/1?reconfigure=1",
        )
        self.assertEqual(
            model["nodes"]["1"]["tetra"]["pei_device"],
            "/dev/serial0",
        )
        self.assertEqual(model["nodes"]["1"]["tetra"]["issi"], 9999)
        save.assert_called_once()

    def test_multiple_ports_cannot_enter_single_tetra_setup(self):
        model = new_node_model()
        model["ports"] = {"enabled": ["1", "2"]}

        response, save = self.post(model)

        self.assertIn("one enabled radio port", response["error"])
        save.assert_not_called()

    def test_conventional_entry_keeps_existing_destination(self):
        for role in ("simplex", "repeater"):
            with self.subTest(role=role):
                model = new_node_model()
                response, save = self.post(
                    model, {"node_type": role}
                )

                self.assertEqual(
                    response.headers["Location"], "/interface"
                )
                save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
