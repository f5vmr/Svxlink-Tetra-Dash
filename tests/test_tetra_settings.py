import unittest
from copy import deepcopy
from unittest.mock import patch

import app as dashboard
from models.node_model import new_tetra_configuration


class TetraSettingsTests(unittest.TestCase):

    def model(self):
        return {
            "ports": {"enabled": ["1"]},
            "nodes": {
                "1": {
                    "role": "tetra",
                    "tetra": new_tetra_configuration(),
                },
            },
        }

    def form(self):
        return {
            "mode": "DMO-RPT",
            "pei_device": "/dev/serial0",
            "baud": "115200",
            "issi": "9999",
            "gssi": "1",
            "mcc": "901",
            "mnc": "16383",
        }

    def test_valid_settings_save_and_preserve_return_paths(self):
        for extras, destination in (
            ({}, "/tetra-interface/1"),
            (
                {"reconfigure": "1"},
                "/tetra-interface/1?reconfigure=1",
            ),
            (
                {"return_to": "topology", "reconfigure": "1"},
                "/tetra-interface/1?reconfigure=1&return_to=topology",
            ),
        ):
            with self.subTest(extras=extras):
                model = self.model()
                model["nodes"]["1"]["tetra"]["end_cmd"] = "ATH"
                form = self.form()
                form.update(extras)

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        "/port-tetra/1", method="POST", data=form
                    ):
                        response = dashboard.port_tetra_page("1")

                self.assertEqual(
                    response.headers["Location"], destination
                )
                save.assert_called_once_with(model)
                tetra = model["nodes"]["1"]["tetra"]
                self.assertTrue(tetra["configured"])
                self.assertEqual(tetra["baud"], 115200)
                self.assertEqual(tetra["issi"], 9999)
                self.assertEqual(tetra["end_cmd"], "ATH")

    def test_invalid_settings_do_not_change_saved_model(self):
        model = self.model()
        original = deepcopy(model)
        form = self.form()
        form["baud"] = "invalid"

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
                "/port-tetra/1", method="POST", data=form
            ):
                response = dashboard.port_tetra_page("1")

        self.assertTrue(response["errors"])
        self.assertEqual(model, original)
        save.assert_not_called()

    def test_unavailable_or_conventional_port_cannot_be_edited(self):
        for port_id, role in (
            ("2", "tetra"),
            ("1", "repeater"),
        ):
            with self.subTest(port_id=port_id, role=role):
                model = self.model()
                model["nodes"]["1"]["role"] = role

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        f"/port-tetra/{port_id}",
                        method="POST",
                        data=self.form(),
                    ):
                        response = dashboard.port_tetra_page(port_id)

                self.assertEqual(
                    response.headers["Location"], "/port-config"
                )
                save.assert_not_called()

    def test_get_renders_settings_form(self):
        model = self.model()

        with patch.object(
            dashboard, "load_node_model", return_value=model
        ), patch.object(
            dashboard, "save_node_model"
        ) as save:
            with dashboard.app.test_request_context("/port-tetra/1"):
                response = dashboard.port_tetra_page("1")

        self.assertIn("PEI serial device", response)
        self.assertIn('name="issi"', response)
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
