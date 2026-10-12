#!/usr/bin/env python3

import unittest

from renderers.svxlink_renderer import (
    render_port_rx_section,
    render_rx_ctcss_block,
    render_rx_gpiod_block,
    render_rx_hidraw_block,
    render_rx_sql_block,
    render_commented_squelch_example,
    render_receiver_common_options,
    
)


EXPECTED_CTCSS_BLOCK = "\n".join([
    "CTCSS_MODE=3",
    "CTCSS_FQ=88.5",
    "#CTCSS_SNR_OFFSET=0",
    "#CTCSS_SNR_OFFSETS=88.5:-1.0,136.5:-0.5",
    "#CTCSS_OPEN_THRESH=15",
    "#CTCSS_CLOSE_THRESH=9",
    "#CTCSS_BPF_LOW=60",
    "#CTCSS_BPF_HIGH=270",
    "#CTCSS_EMIT_TONE_DETECTED=0",
])


class ReceiverCtcssRenderingTests(unittest.TestCase):

    def test_single_port_ctcss_uses_mode_three(self):
        model = {
            "squelch": {
                "method": "ctcss",
                "ctcss_freq": "88.5",
            },
        }

        self.assertEqual(
            render_rx_ctcss_block(model),
            EXPECTED_CTCSS_BLOCK,
        )

    def test_single_port_non_ctcss_has_no_active_block(self):
        model = {
            "squelch": {
                "method": "gpiod",
                "ctcss_freq": None,
            },
        }

        self.assertEqual(
            render_rx_ctcss_block(model),
            "",
        )

    def test_multiport_ctcss_does_not_require_legacy_mode(self):
        model = {
            "sql_tail_elim": 270,
        }
        node = {
            "audio": {
                "rx_audio": "alsa:rx1",
                "deemphasis": False,
            },
            "squelch": {
                "method": "ctcss",
                "ctcss_freq": "88.5",
            },
        }

        rendered = render_port_rx_section(
            model,
            "1",
            node,
        )

        self.assertIn(
            EXPECTED_CTCSS_BLOCK,
            rendered,
        )
        self.assertNotIn(
            "CTCSS_MODE=4",
            rendered,
        )


class ReceiverStandardSqlRenderingTests(
    unittest.TestCase
):

    def test_multiport_native_gpio_cos_is_rendered(self):
        model = {
            "sql_tail_elim": 270,
        }
        node = {
            "audio": {
                "rx_audio": "alsa:rx1",
                "deemphasis": False,
            },
            "squelch": {
                "method": "gpiod",
                "ctcss_freq": None,
            },
            "gpio": {
                "cos_chip": "gpiochip0",
                "cos_line": 26,
                "cos_invert": False,
            },
        }

        rendered = render_port_rx_section(
            model,
            "1",
            node,
        )

        self.assertIn(
            "SQL_GPIOD_CHIP=gpiochip0",
            rendered,
        )
        self.assertIn(
            "SQL_GPIOD_LINE=26",
            rendered,
        )

    def test_selected_standard_detector_is_rendered(self):
        expected = {
            "hidraw": "SQL_DET=HIDRAW",
            "gpiod": "SQL_DET=GPIOD",
            "serial": "SQL_DET=SERIAL",
            "ctcss": "SQL_DET=CTCSS",
        }

        for method, line in expected.items():
            with self.subTest(method=method):
                model = {
                    "interface": {
                        "mode": "hidraw",
                        "sql_source": "hidraw",
                    },
                    "squelch": {
                        "method": method,
                    },
                }

                self.assertEqual(
                    render_rx_sql_block(model),
                    line,
                )

    def test_gpiod_block_follows_squelch_selection(self):
        model = {
            "interface": {
                "mode": "hidraw",
                "sql_source": "hidraw",
            },
            "squelch": {
                "method": "gpiod",
            },
            "gpio": {
                "sql": {
                    "chip": "gpiochip0",
                    "line": 23,
                    "invert": False,
                },
            },
        }

        rendered = render_rx_gpiod_block(model)

        self.assertIn(
            "SQL_GPIOD_CHIP=gpiochip0",
            rendered,
        )
        self.assertIn(
            "SQL_GPIOD_LINE=23",
            rendered,
        )

        model["squelch"]["method"] = "serial"

        self.assertEqual(
            render_rx_gpiod_block(model),
            "",
        )

    def test_hidraw_block_follows_squelch_selection(self):
        model = {
            "interface": {
                "mode": "gpiod",
                "sql_source": "gpiod",
            },
            "squelch": {
                "method": "hidraw",
            },
            "hidraw": {
                "device": "/dev/hidraw0",
                "sql_pin": "VOL_DN",
                "sql_invert": False,
            },
        }

        rendered = render_rx_hidraw_block(model)

        self.assertIn(
            "HID_DEVICE=/dev/hidraw0",
            rendered,
        )
        self.assertIn(
            "HID_SQL_PIN=VOL_DN",
            rendered,
        )

        model["squelch"]["method"] = "ctcss"

        self.assertEqual(
            render_rx_hidraw_block(model),
            "",
        )


class ReceiverCommentedSqlExampleTests(
    unittest.TestCase
):

    def test_no_selection_renders_nothing(self):
        self.assertEqual(
            render_commented_squelch_example(
                {},
                "Rx1",
            ),
            "",
        )

    def test_vox_example_is_fully_commented(self):
        rendered = render_commented_squelch_example(
            {
                "advanced_example": "vox",
            },
            "Rx1",
        )

        self.assertIn(
            "#SQL_DET=VOX",
            rendered,
        )
        self.assertIn(
            "#VOX_FILTER_DEPTH=20",
            rendered,
        )
        self.assertNotIn(
            "\nSQL_DET=VOX",
            rendered,
        )

    def test_siglev_example_uses_noise(self):
        rendered = render_commented_squelch_example(
            {
                "advanced_example": "siglev",
            },
            "Rx1",
        )

        self.assertIn(
            "#SIGLEV_DET=NOISE",
            rendered,
        )
        self.assertIn(
            "#SQL_SIGLEV_OPEN_THRESH=30",
            rendered,
        )
        self.assertNotIn(
            "\nSIGLEV_DET=",
            rendered,
        )

    def test_combine_example_uses_selected_components(self):
        rendered = render_commented_squelch_example(
            {
                "advanced_example": "combine",
                "combine_components": [
                    "vox",
                    "ctcss",
                ],
                "ctcss_freq": "88.5",
            },
            "Rx2",
        )

        self.assertIn(
            "#SQL_COMBINE=(Rx2:VOX)&(Rx2:CTCSS)",
            rendered,
        )
        self.assertIn(
            "#[Rx2:VOX]",
            rendered,
        )
        self.assertIn(
            "#[Rx2:CTCSS]",
            rendered,
        )
        self.assertIn(
            "#CTCSS_MODE=3",
            rendered,
        )
        self.assertIn(
            "#CTCSS_FQ=88.5",
            rendered,
        )
        self.assertNotIn(
            "\nSQL_DET=COMBINE",
            rendered,
        )

    def test_evdev_and_pty_examples_are_commented(self):
        examples = {
            "evdev": "#SQL_DET=EVDEV",
            "pty": "#PTY_PATH=/tmp/rx3_sql",
        }

        for detector, expected in examples.items():
            with self.subTest(detector=detector):
                rendered = (
                    render_commented_squelch_example(
                        {
                            "manual_detector": detector,
                        },
                        "Rx3",
                    )
                )

                self.assertIn(
                    expected,
                    rendered,
                )

    def test_rtl_sdr_uses_port_specific_wbrx(self):
        rendered = render_commented_squelch_example(
            {
                "manual_detector": "rtl_sdr",
            },
            "Rx4",
        )

        self.assertIn(
            "#WBRX=WbRx4",
            rendered,
        )
        self.assertIn(
            "#[WbRx4]",
            rendered,
        )
        self.assertIn(
            "#TYPE=RtlUsb",
            rendered,
        )
        self.assertNotIn(
            "\n[WbRx4]",
            rendered,
        )

    def test_multiport_receiver_includes_selected_example(self):
        model = {
            "sql_tail_elim": 270,
        }
        node = {
            "audio": {
                "rx_audio": "alsa:rx2",
                "deemphasis": False,
            },
            "gpio": {
                "cos_invert": False,
            },
            "squelch": {
                "method": "gpiod",
                "advanced_example": "vox",
                "combine_components": [],
                "manual_detector": None,
                "ctcss_freq": None,
                "ctcss_tx": False,
            },
        }

        rendered = render_port_rx_section(
            model,
            "2",
            node,
        )

        self.assertIn(
            "SQL_DET=GPIOD",
            rendered,
        )
        self.assertIn(
            "#SQL_DET=VOX",
            rendered,
        )
        self.assertIn(
            "#VOX_FILTER_DEPTH=20",
            rendered,
        )
        self.assertNotIn(
            "\nSQL_DET=VOX",
            rendered,
        )
        self.assertIn(
            "DTMF_DEC_TYPE=INTERNAL",
            rendered,
        )
        self.assertIn(
            "DTMF_MUTING=1",
            rendered,
        )
        self.assertIn(
            "1750_MUTING=1",
            rendered,
        )
        self.assertIn(
            "#[Rx2_Compressor]",
            rendered,
        )


class ReceiverCommonOptionsTests(
    unittest.TestCase
):

    def test_active_dtmf_defaults(self):
        rendered = (
            render_receiver_common_options(
                "Rx1"
            )
        )

        self.assertIn(
            "DTMF_DEC_TYPE=INTERNAL",
            rendered,
        )
        self.assertIn(
            "DTMF_MUTING=1",
            rendered,
        )
        self.assertIn(
            "1750_MUTING=1",
            rendered,
        )

        self.assertNotIn(
            "#DTMF_DEC_TYPE=INTERNAL",
            rendered,
        )
        self.assertNotIn(
            "#DTMF_MUTING=1",
            rendered,
        )
        self.assertNotIn(
            "#1750_MUTING=1",
            rendered,
        )

    def test_manual_options_are_port_specific(self):
        rendered = (
            render_receiver_common_options(
                "Rx3"
            )
        )

        self.assertIn(
            "#DTMF_PTY=/tmp/rx3_dtmf",
            rendered,
        )
        self.assertIn(
            "#LADSPA_PLUGINS=hpf:1000,@Rx3_Compressor",
            rendered,
        )
        self.assertIn(
            "#[Rx3_Compressor]",
            rendered,
        )

        for expected in (
            "#DTMF_HANGTIME=40",
            "#DTMF_SERIAL=/dev/ttyS0",
            "#DTMF_MAX_FWD_TWIST=8",
            "#DTMF_MAX_REV_TWIST=4",
            "#SEL5_DEC_TYPE=INTERNAL",
            "#SEL5_TYPE=ZVEI1",
            "#FQ=433475000",
            "#MODULATION=FM",
            "#OB_AFSK_ENABLE=0",
            "#IB_AFSK_ENABLE=0",
        ):
            self.assertIn(
                expected,
                rendered,
            )


if __name__ == "__main__":
    unittest.main()
