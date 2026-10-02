import unittest
from copy import deepcopy
from unittest.mock import patch

import app as dashboard


class TetraInterfaceTests(unittest.TestCase):

    def model(self):
        return {
            "ports": {"enabled": ["1"]},
            "nodes": {
                "1": {
                    "role": "tetra",
                    "tetra": {"pei_device": "/dev/serial0"},
                    "audio": {"deemphasis": False},
                },
            },
        }

    def form(self):
        return {
            "rx_audio": "alsa:plughw:CARD=Radio,DEV=0",
            "tx_audio": "alsa:plughw:CARD=Radio,DEV=0",
            "ptt_source": "serial",
            "ptt_port": "/dev/serial/by-id/usb-ptt",
            "ptt_pin": "RTS",
        }

    def post(self, model, form):
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
                "/tetra-interface/1", method="POST", data=form
            ):
                response = dashboard.tetra_interface_page("1")

        return response, save

    def test_serial_ptt_saves_separately_from_pei(self):
        model = self.model()
        response, save = self.post(model, self.form())

        self.assertEqual(response.headers["Location"], "/modules")
        save.assert_called_once_with(model)
        node = model["nodes"]["1"]
        self.assertTrue(node["interface"]["configured"])
        self.assertEqual(node["serial"]["ptt_pin"], "RTS")
        self.assertEqual(
            node["serial"]["ptt_port"],
            "/dev/serial/by-id/usb-ptt",
        )
        self.assertEqual(node["tetra"]["pei_device"], "/dev/serial0")
        self.assertFalse(node["audio"]["deemphasis"])

    def test_hid_ptt_saves_device_pin_and_polarity(self):
        model = self.model()
        form = self.form()
        form.update({
            "ptt_source": "hidraw",
            "hid_device": "/dev/hidraw0",
            "hid_ptt_pin": "GPIO3",
            "hid_ptt_invert": "1",
        })

        response, save = self.post(model, form)

        self.assertEqual(response.status_code, 302)
        save.assert_called_once_with(model)
        self.assertEqual(
            model["nodes"]["1"]["hidraw"],
            {
                "device": "/dev/hidraw0",
                "ptt_pin": "GPIO3",
                "ptt_invert": True,
            },
        )

    def test_invalid_settings_do_not_change_model(self):
        for field, value in (
            ("rx_audio", ""),
            ("tx_audio", "hw:0"),
            ("ptt_source", "unknown"),
            ("ptt_port", "/dev/serial0"),
            ("ptt_pin", "invalid"),
        ):
            with self.subTest(field=field, value=value):
                model = self.model()
                original = deepcopy(model)
                form = self.form()
                form[field] = value

                response, save = self.post(model, form)

                self.assertTrue(response["errors"])
                self.assertEqual(model, original)
                save.assert_not_called()

    def test_get_renders_actual_template(self):
        model = self.model()

        with patch.object(
            dashboard, "load_node_model", return_value=model
        ):
            with dashboard.app.test_request_context("/tetra-interface/1"):
                response = dashboard.tetra_interface_page("1")

        self.assertIn("TETRA Audio and PTT", response)
        self.assertIn('name="rx_audio"', response)
        self.assertIn('name="ptt_port"', response)


if __name__ == "__main__":
    unittest.main()
