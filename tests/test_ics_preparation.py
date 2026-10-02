#!/usr/bin/env python3

import unittest
from unittest.mock import mock_open, patch
from html.parser import HTMLParser

import app as dashboard
from services.ics_prepare_service import VALID_ICS_PROFILES


class PreparationControls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.apply_disabled = None
        self.continue_available = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if (
            tag == "button"
            and attrs.get("name") == "action"
            and attrs.get("value") == "set_overlay"
        ):
            self.apply_disabled = "disabled" in attrs

        if (
            tag == "a"
            and attrs.get("href") == self.ports_url
        ):
            self.continue_available = True


class IcsPreparationTests(unittest.TestCase):
    def render_controls(
        self, helper=True, overlay=False,
        verified=False, reboot=False,
    ):
        with dashboard.app.test_request_context("/ics_prepare"):
            html = dashboard.render_template(
                "ics_prepare.html",
                model={
                    "ics_prepare": {
                        "verified": verified,
                        "reboot_required": reboot,
                    },
                },
                profiles=VALID_ICS_PROFILES,
                selected_profile="ics_4x",
                status={
                    "helper_available": helper,
                    "selected_overlay_exists": overlay,
                    "selected_profile": VALID_ICS_PROFILES["ics_4x"],
                    "current_overlay": None,
                    "i2c": {"ok": True, "stdout": "", "stderr": ""},
                    "overlay_check": None,
                    "gpio_names": {
                        "ok": True, "stdout": "", "stderr": "",
                    },
                },
                message=None,
                error=None,
                version_info={"package": "test", "engine": "test"},
            )
            controls = PreparationControls()
            controls.ports_url = dashboard.url_for("hardware_ports_page")
            controls.feed(html)
            return controls

    def test_apply_can_create_missing_overlay(self):
        controls = self.render_controls(overlay=False)
        self.assertIs(controls.apply_disabled, False)

    def test_apply_requires_installed_helper(self):
        controls = self.render_controls(helper=False, overlay=True)
        self.assertIs(controls.apply_disabled, True)

    def test_continue_requires_complete_verification_and_reboot(self):
        for verified, reboot, expected in (
            (False, False, False),
            (False, True, False),
            (True, True, False),
            (True, False, True),
        ):
            with self.subTest(verified=verified, reboot=reboot):
                controls = self.render_controls(
                    verified=verified, reboot=reboot,
                )
                self.assertEqual(
                    controls.continue_available, expected,
                )


    def test_apply_requires_reboot_before_gpio_verification(self):
        model = {"hardware_profile_id": "ics_4x"}
        success = {
            "ok": True,
            "stdout": "Completed",
            "stderr": "",
        }
        status = {
            "selected_overlay_exists": True,
            "current_overlay": "ics_4x",
            "i2c": {"ok": True},
            "gpio_names": {"ok": True},
        }

        with patch.object(
            dashboard, "load_node_model", return_value=model,
        ), patch.object(
            dashboard, "save_node_model",
        ), patch(
            "builtins.open", mock_open(read_data="boot-before-reboot"),
        ), patch.object(
            dashboard, "set_overlay", return_value=success,
        ) as overlay_mock, patch.object(
            dashboard, "configure_audio_boot", return_value=success,
        ) as audio_mock, patch.object(
            dashboard, "build_ics_status", return_value=status,
        ), patch.object(
            dashboard, "update_model_gpiod_discovery",
        ) as discovery_mock, patch.object(
            dashboard, "configure_pcm1803",
        ) as pcm_mock, patch.object(
            dashboard, "render_template", return_value="rendered",
        ), patch.object(
            dashboard, "get_version_info", return_value={},
        ):
            with dashboard.app.test_request_context(
                "/ics_prepare",
                method="POST",
                data={
                    "action": "set_overlay",
                    "profile": "ics_4x",
                },
            ):
                dashboard.ics_prepare_page()

        overlay_mock.assert_called_once_with("ics_4x")
        audio_mock.assert_called_once_with("ics_4x")
        discovery_mock.assert_not_called()
        pcm_mock.assert_not_called()

        preparation = model["ics_prepare"]
        self.assertTrue(preparation["reboot_required"])
        self.assertFalse(preparation["verified"])
        self.assertTrue(preparation["audio_boot_configured"])
        self.assertEqual(
            preparation["overlay_install_boot_id"],
            "boot-before-reboot",
        )
        self.assertEqual(
            model["build"]["resume_after_reboot"],
            "/ics_prepare",
        )


    def test_post_reboot_verification_requires_gpio_and_pcm_success(self):
        for missing_lines, pcm_ok, expected in (
            ([], True, True),
            (["PCM_PDWN"], True, False),
            ([], False, False),
        ):
            with self.subTest(
                missing_lines=missing_lines, pcm_ok=pcm_ok,
            ):
                model = {
                    "hardware_profile_id": "ics_4x",
                    "build": {"resume_after_reboot": "/ics_prepare"},
                    "ics_prepare": {
                        "overlay_applied": "ics_4x",
                        "overlay_install_boot_id": "previous-boot",
                        "audio_boot_configured": True,
                        "reboot_required": True,
                        "verified": False,
                    },
                }
                status = {
                    "selected_overlay_exists": True,
                    "current_overlay": "ics_4x",
                    "i2c": {"ok": True},
                    "gpio_names": {"ok": True},
                }

                def discover(current_model):
                    current_model["gpiod"] = {
                        "missing_lines": missing_lines,
                    }
                    return current_model

                with patch.object(
                    dashboard, "load_node_model", return_value=model,
                ), patch.object(
                    dashboard, "save_node_model",
                ), patch(
                    "builtins.open",
                    mock_open(read_data="new-boot"),
                ), patch.object(
                    dashboard, "build_ics_status", return_value=status,
                ), patch.object(
                    dashboard,
                    "update_model_gpiod_discovery",
                    side_effect=discover,
                ) as discovery_mock, patch.object(
                    dashboard,
                    "configure_pcm1803",
                    return_value={
                        "ok": pcm_ok,
                        "stdout": "",
                        "stderr": "" if pcm_ok else "PCM1803 failed",
                    },
                ) as pcm_mock, patch.object(
                    dashboard,
                    "render_template",
                    side_effect=lambda template, **context: context,
                ), patch.object(
                    dashboard, "get_version_info", return_value={},
                ):
                    with dashboard.app.test_request_context(
                        "/ics_prepare",
                    ):
                        response = dashboard.ics_prepare_page()

                discovery_mock.assert_called_once_with(model)

                if missing_lines:
                    pcm_mock.assert_not_called()
                else:
                    pcm_mock.assert_called_once_with("ics_4x")

                self.assertEqual(
                    model["ics_prepare"]["verified"], expected,
                )
                self.assertEqual(
                    model["ics_prepare"]["reboot_required"],
                    not expected,
                )
                self.assertEqual(
                    "resume_after_reboot" in model["build"],
                    not expected,
                )
                if expected:
                    self.assertIsNone(response["error"])
                else:
                    self.assertTrue(response["error"])


if __name__ == "__main__":
    unittest.main()
