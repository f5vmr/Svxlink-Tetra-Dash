import unittest

from models.node_model import (
    new_node_model,
    new_tetra_configuration,
    validate_model,
    validate_tetra_configuration,
    validate_tetra_interface,
    port_node_details_complete,
)


class TetraValidationTests(unittest.TestCase):

    def valid_configuration(self):
        configuration = new_tetra_configuration()
        configuration.update({
            "mode": "DMO-RPT",
            "pei_device": "/dev/serial0",
            "baud": 115200,
            "issi": 9999,
        })
        return configuration

    def tetra_errors(self, configuration):
        model = new_node_model()
        model["hardware_profile_id"] = "generic_single"
        model["ports"] = {"enabled": ["1"]}
        model["nodes"] = {
            "1": {
                "role": "tetra",
                "callsign": "G4NAB",
                "tetra": configuration,
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
        }
        return [
            error
            for error in validate_model(model)
            if "Port 1" in error
        ]

    def test_defaults_require_connection_and_identity(self):
        errors = validate_tetra_configuration(
            new_tetra_configuration()
        )
        self.assertEqual(len(errors), 4)

    def test_valid_settings_accept_stable_device_paths(self):
        for device in (
            "/dev/serial0",
            "/dev/serial/by-id/usb-radio",
        ):
            with self.subTest(device=device):
                configuration = self.valid_configuration()
                configuration["pei_device"] = device
                self.assertEqual(
                    validate_tetra_configuration(configuration),
                    [],
                )

    def test_invalid_numeric_settings_are_rejected(self):
        for field in ("baud", "issi", "gssi", "mcc", "mnc"):
            for value in (None, True, 0, -1, "123", 1.5):
                with self.subTest(field=field, value=value):
                    configuration = self.valid_configuration()
                    configuration[field] = value
                    self.assertTrue(
                        validate_tetra_configuration(configuration)
                    )

    def test_invalid_mode_and_device_are_rejected(self):
        for field, value in (
            ("mode", "repeater"),
            ("pei_device", "ttyUSB0"),
            ("pei_device", "/dev/"),
            ("pei_device", "/dev/ttyUSB0\n"),
        ):
            with self.subTest(field=field, value=value):
                configuration = self.valid_configuration()
                configuration[field] = value
                self.assertTrue(
                    validate_tetra_configuration(configuration)
                )

    def test_model_accepts_configured_tetra_role(self):
        self.assertEqual(
            self.tetra_errors(self.valid_configuration()),
            [],
        )

    def test_model_rejects_incomplete_tetra_settings(self):
        errors = self.tetra_errors(new_tetra_configuration())
        self.assertEqual(len(errors), 4)
        self.assertTrue(
            all("Port 1 TETRA" in error for error in errors)
        )


    def test_tetra_identity_alone_is_incomplete(self):
        node = {
            "role": "tetra",
            "node_details_configured": True,
            "tetra": self.valid_configuration(),
        }
        self.assertFalse(port_node_details_complete(node))

    def test_tetra_completion_requires_valid_settings(self):
        configuration = self.valid_configuration()
        configuration["configured"] = True
        node = {
            "role": "tetra",
            "node_details_configured": True,
            "tetra": configuration,
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
        }

        self.assertTrue(port_node_details_complete(node))

        configuration["pei_device"] = None
        self.assertFalse(port_node_details_complete(node))

        configuration["pei_device"] = "/dev/serial0"
        node["node_details_configured"] = False
        self.assertFalse(port_node_details_complete(node))

    def test_conventional_completion_is_preserved(self):
        for role in ("simplex", "repeater"):
            with self.subTest(role=role):
                node = {
                    "role": role,
                    "node_details_configured": True,
                }
                self.assertTrue(port_node_details_complete(node))

                node["node_details_configured"] = False
                self.assertFalse(port_node_details_complete(node))


    def test_interface_cannot_be_bypassed_or_share_pei(self):
        node = {
            "tetra": {"pei_device": "/dev/serial0"},
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
        }

        self.assertEqual(validate_tetra_interface(node), [])

        node["interface"]["configured"] = False
        self.assertTrue(validate_tetra_interface(node))

        node["interface"]["configured"] = True
        node["serial"]["ptt_port"] = "/dev/serial0"
        self.assertTrue(validate_tetra_interface(node))


if __name__ == "__main__":
    unittest.main()
