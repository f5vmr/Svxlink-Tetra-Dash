import unittest

from models.node_model import new_node_model
from renderers.svxlink_renderer import render_reflector_logic


class TetraReflectorTests(unittest.TestCase):

    def model(self, route):
        model = new_node_model()
        model["hardware_profile_id"] = "generic_single"
        model["ports"] = {"enabled": ["1"]}
        model["installation"] = {"primary_port_id": "1"}
        model["nodes"] = {
            "1": {
                "role": "tetra",
                "callsign": "G4NAB",
            },
        }

        model["reflector"].update({
            "enabled": True,
            "route": route,
            route: {
                "host": "reflector.example.test",
                "port": 5300,
                "auth_key": "test-password-123",
                "subject": {
                    "given_name": "Chris",
                    "surname": "Jackson",
                    "country": "GB",
                    "email": "test@example.test",
                },
            },
        })
        return model

    def test_password_routes_use_reflector_v2(self):
        for route in ("v2", "federation"):
            with self.subTest(route=route):
                rendered = render_reflector_logic(self.model(route))
                active = [
                    line.strip()
                    for line in rendered.splitlines()
                    if line.strip()
                    and not line.strip().startswith("#")
                ]

                self.assertIn("TYPE=ReflectorV2", active)
                self.assertIn('AUTH_KEY="test-password-123"', active)
                self.assertFalse(
                    any(line.startswith("CERT_") for line in active)
                )

    def test_v3_uses_certificate_logic(self):
        rendered = render_reflector_logic(self.model("v3"))
        active = [
            line.strip()
            for line in rendered.splitlines()
            if line.strip()
            and not line.strip().startswith("#")
        ]

        self.assertIn("TYPE=Reflector", active)
        self.assertIn("CERT_SUBJ_givenName=Chris", active)
        self.assertIn("CERT_SUBJ_surname=Jackson", active)
        self.assertIn("CERT_SUBJ_countryName=GB", active)
        self.assertIn("CERT_DOWNLOAD_CA_BUNDLE=1", active)
        self.assertFalse(
            any(line.startswith("AUTH_KEY=") for line in active)
        )

    def test_disabled_reflector_renders_nothing(self):
        model = self.model("v3")
        model["reflector"]["enabled"] = False
        self.assertEqual(render_reflector_logic(model), "")


if __name__ == "__main__":
    unittest.main()
