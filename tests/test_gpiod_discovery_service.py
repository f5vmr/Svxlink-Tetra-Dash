#!/usr/bin/env python3

import unittest

from unittest.mock import patch

from services import gpio_service


class GpiodDiscoveryServiceTests(unittest.TestCase):

    def test_ics_1x_discovers_tx_and_uses_native_rx(self):
        model = {
            "hardware_profile_id": "ics_1x",
            "ports": {
                "enabled": ["1"],
            },
            "nodes": {
                "1": {
                    "gpio": {},
                },
            },
        }

        discovered = {
            "TX_1": {
                "chip": "gpiochip4",
                "line": "TX_1",
                "offset": 10,
            },
        }

        with patch.object(
            gpio_service,
            "discover_named_gpio_lines",
            return_value=(discovered, []),
        ) as discovery_mock:
            result = (
                gpio_service
                .update_model_gpiod_discovery(model)
            )

        discovery_mock.assert_called_once_with(
            ["TX_1"],
            refresh=True,
        )

        self.assertEqual(
            result["gpiod"]["missing_lines"],
            [],
        )

        gpio = result["nodes"]["1"]["gpio"]

        self.assertEqual(gpio["cos_chip"], "gpiochip0")
        self.assertEqual(gpio["cos_line"], 26)
        self.assertEqual(gpio["ptt_chip"], "gpiochip4")
        self.assertEqual(gpio["ptt_line"], "TX_1")

    def test_ics_2x_discovers_tx_and_uses_native_rx(self):
        model = {
            "hardware_profile_id": "ics_2x",
            "ports": {
                "enabled": ["1", "2"],
            },
            "nodes": {
                "1": {
                    "gpio": {},
                },
                "2": {
                    "gpio": {},
                },
            },
        }

        discovered = {
            "TX_1": {
                "chip": "gpiochip4",
                "line": "TX_1",
                "offset": 10,
            },
            "TX_2": {
                "chip": "gpiochip4",
                "line": "TX_2",
                "offset": 11,
            },
        }

        with patch.object(
            gpio_service,
            "discover_named_gpio_lines",
            return_value=(discovered, []),
        ) as discovery_mock:
            result = (
                gpio_service
                .update_model_gpiod_discovery(model)
            )

        discovery_mock.assert_called_once_with(
            [
                "TX_1",
                "TX_2",
            ],
            refresh=True,
        )

        discovery_mock.assert_called_once_with(
            [
                "TX_1",
                "TX_2",
            ],
            refresh=True,
        )

        self.assertEqual(
            result["gpiod"]["missing_lines"],
            [],
        )

        port_1_gpio = result["nodes"]["1"]["gpio"]
        port_2_gpio = result["nodes"]["2"]["gpio"]

        self.assertEqual(
            port_1_gpio["cos_chip"],
            "gpiochip0",
        )
        self.assertEqual(port_1_gpio["cos_line"], 26)
        self.assertEqual(
            port_1_gpio["ptt_chip"],
            "gpiochip4",
        )
        self.assertEqual(
            port_1_gpio["ptt_line"],
            "TX_1",
        )

        self.assertEqual(
            port_2_gpio["cos_chip"],
            "gpiochip0",
        )
        self.assertEqual(port_2_gpio["cos_line"], 23)
        self.assertEqual(
            port_2_gpio["ptt_chip"],
            "gpiochip4",
        )
        self.assertEqual(
            port_2_gpio["ptt_line"],
            "TX_2",
        )

    def test_ics_4x_still_discovers_named_rx_and_tx(self):
        model = {
            "hardware_profile_id": "ics_4x",
            "ports": {
                "enabled": ["1", "2"],
            },
        }

        self.assertEqual(
            gpio_service.required_ics_gpio_lines(model),
            [
                "RX_1",
                "TX_1",
                "RX_2",
                "TX_2",
                "PCM_PDWN",
            ],
        )


if __name__ == "__main__":
    unittest.main()
