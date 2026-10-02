import unittest

from renderers.svxlink_renderer import (
    render_port_rx_section,
    render_port_tx_section,
    render_tetra_logic,
)


class TetraRenderingTests(unittest.TestCase):

    def node(self):
        return {
            "role": "tetra",
            "audio": {
                "rx_audio": "alsa:plughw:CARD=Radio,DEV=0",
                "tx_audio": "alsa:plughw:CARD=Radio,DEV=0",
            },
            "interface": {"ptt_source": "serial"},
            "serial": {
                "ptt_port": "/dev/serial/by-id/usb-ptt",
                "ptt_pin": "RTS",
            },
            "tetra": {
                "pei_device": "/dev/serial0",
            },
        }

    def test_tetra_rx_ignores_conventional_squelch_selection(self):
        for method in ("hidraw", "serial", "gpiod", "ctcss"):
            with self.subTest(method=method):
                node = self.node()
                node["squelch"] = {"method": method}

                rendered = render_port_rx_section({}, "1", node)

                self.assertIn("SQL_DET=TETRA_SQL", rendered)
                self.assertNotIn("SQL_DET=GPIOD", rendered)
                self.assertNotIn("SQL_DET=SERIAL", rendered)
                self.assertNotIn("SQL_DET=HIDRAW", rendered)
                self.assertNotIn("SQL_DET=CTCSS", rendered)
                self.assertIn(
                    "AUDIO_DEV=alsa:plughw:CARD=Radio,DEV=0",
                    rendered,
                )

    def test_wired_ptt_is_separate_from_pei_device(self):
        rendered = render_port_tx_section({}, "1", self.node())

        self.assertIn("PTT_TYPE=SerialPin", rendered)
        self.assertIn(
            "PTT_PORT=/dev/serial/by-id/usb-ptt",
            rendered,
        )
        self.assertIn("PTT_PIN=RTS", rendered)
        self.assertNotIn("PTT_PORT=/dev/serial0", rendered)

    def test_conventional_serial_squelch_is_preserved(self):
        node = self.node()
        node["role"] = "simplex"
        node["squelch"] = {"method": "serial"}
        node["serial"].update({
            "sql_port": "/dev/ttyUSB1",
            "sql_pin": "CTS",
        })

        rendered = render_port_rx_section({}, "1", node)

        self.assertIn("SQL_DET=SERIAL", rendered)
        self.assertIn("SERIAL_PORT=/dev/ttyUSB1", rendered)
        self.assertNotIn("SQL_DET=TETRA_SQL", rendered)


    def tetra_logic_node(self):
        from models.node_model import new_tetra_configuration

        node = self.node()
        node["callsign"] = "G4NAB"
        node["modules"] = {"metar": True}
        tetra = new_tetra_configuration()
        tetra.update({
            "mode": "DMO-RPT",
            "pei_device": "/dev/serial0",
            "baud": 115200,
            "issi": 9999,
            "configured": True,
        })
        node["tetra"] = tetra
        return node

    def test_single_tetra_logic_has_connection_and_identity(self):
        from models.node_model import new_node_model

        rendered = render_tetra_logic(
            new_node_model(), "1", self.tetra_logic_node()
        )

        for line in (
            "[TetraLogic]",
            "TYPE=Tetra",
            "RX=Rx1",
            "TX=Tx1",
            "CALLSIGN=G4NAB",
            "PORT=/dev/serial0",
            "BAUD=115200",
            "ISSI=9999",
            "GSSI=1",
            "MCC=901",
            "MNC=16383",
            "TETRA_MODE=DMO-RPT",
            "PEI_INIT_FILE=/etc/svxlink/pei-init.json",
            "DTMF_CTRL_PTY=/dev/shm/port1_dtmf_ctrl",
            "END_CMD=ATH",
        ):
            self.assertIn(line, rendered.splitlines())

        self.assertNotIn("TYPE=Simplex", rendered)
        self.assertNotIn("PTT_PORT=", rendered)
        self.assertNotIn("INIT_PEI=", rendered)

    def test_tetra_logic_uses_per_node_modules(self):
        from models.node_model import new_node_model

        model = new_node_model()
        node = self.tetra_logic_node()

        rendered = render_tetra_logic(model, "1", node)
        self.assertIn(
            "MODULES=ModuleHelp,ModuleParrot,ModuleMetarInfo",
            rendered.splitlines(),
        )

        node["modules"]["metar"] = False
        rendered = render_tetra_logic(model, "1", node)
        self.assertIn(
            "MODULES=ModuleHelp,ModuleParrot",
            rendered.splitlines(),
        )


if __name__ == "__main__":
    unittest.main()
