import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from models.node_model import (
    new_node_model,
    new_tetra_configuration,
)
from renderers.svxlink_renderer import (
    get_primary_logic_name,
    render_multiport_link_to_reflector,
    render_multiport_logic_sections,
)
from services import build_svxlink as builder
from services.topology_ports import get_topology_ports


class TetraBuildTests(unittest.TestCase):

    def model(self):
        model = new_node_model()
        model["hardware_profile_id"] = "generic_single"
        model["hardware"] = {"family": "usb"}
        model["ports"] = {"enabled": ["1"]}
        model["node"].update({
            "type": "tetra",
            "callsign": "G4NAB",
        })

        tetra = new_tetra_configuration()
        tetra.update({
            "mode": "DMO-RPT",
            "pei_device": "/dev/serial0",
            "baud": 115200,
            "issi": 9999,
            "configured": True,
        })

        model["nodes"] = {
            "1": {
                "role": "tetra",
                "callsign": "G4NAB",
                "tetra": tetra,
                "modules": {},
                "audio": {
                    "rx_audio": "alsa:plughw:CARD=Radio,DEV=0",
                    "tx_audio": "alsa:plughw:CARD=Radio,DEV=0",
                },
                "interface": {"ptt_source": "serial"},
                "serial": {
                    "ptt_port": "/dev/serial/by-id/usb-ptt",
                    "ptt_pin": "RTS",
                },
            },
        }
        model["reflector"]["enabled"] = False
        model["topology"] = {
            "reflector_link": {
                "ports": ["1"],
                "default_active": True,
                "timeout": 300,
            },
            "local_links": [],
        }
        return model

    def test_single_tetra_names_agree(self):
        model = self.model()

        self.assertEqual(
            get_topology_ports(model),
            {"1": "TetraLogic"},
        )
        self.assertEqual(
            get_primary_logic_name(model),
            "TetraLogic",
        )

        sections = render_multiport_logic_sections(model)
        self.assertEqual(sections["logics"], "TetraLogic")
        self.assertEqual(sections["sections"], "")

    def test_reflector_link_uses_tetra_name(self):
        model = self.model()
        model["reflector"]["enabled"] = True

        rendered = render_multiport_link_to_reflector(model)

        self.assertIn(
            "CONNECT_LOGICS=TetraLogic:9,ReflectorLogic",
            rendered,
        )
        self.assertIn(
            "ACTIVATE_ON_ACTIVITY=TetraLogic",
            rendered,
        )
        self.assertNotIn("Port1Logic", rendered)

    def test_render_outputs_separate_logic_file(self):
        rendered = builder.render_all(self.model())
        main = rendered["svxlink.conf"]
        tetra = rendered["TetraLogic.conf"]

        self.assertIn("LOGICS=TetraLogic", main)
        self.assertIn("CFG_DIR=svxlink.d", main)
        self.assertIn("[Rx1]", main)
        self.assertIn("[Tx1]", main)
        self.assertIn("SQL_DET=TETRA_SQL", main)
        self.assertNotIn("[TetraLogic]", main)
        self.assertNotIn("[Port1Logic]", main)
        self.assertIn("[TetraLogic]", tetra)
        self.assertIn("TYPE=Tetra", tetra)

    def test_deployment_writes_tetra_into_config_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "svxlink.conf"
            modules = root / "svxlink.d"

            with patch.object(
                builder, "SVXLINK_CONF", config
            ), patch.object(
                builder, "MODULE_DIR", modules
            ):
                deployed = builder.deploy_rendered_files({
                    "svxlink.conf": "[GLOBAL]\nLOGICS=TetraLogic\n",
                    "TetraLogic.conf": "[TetraLogic]\nTYPE=Tetra\n",
                })

            target = modules / "TetraLogic.conf"
            self.assertEqual(
                target.read_text(),
                "[TetraLogic]\nTYPE=Tetra\n",
            )
            self.assertIn(str(target), deployed)
            self.assertTrue(config.exists())


if __name__ == "__main__":
    unittest.main()
