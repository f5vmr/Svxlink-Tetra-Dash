#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch

import app as dashboard
from pathlib import Path
from models.node_model import new_node_model


class WorkflowRoutingTests(unittest.TestCase):

    def multiport_model(self):
        model = new_node_model()
        model["hardware"] = {
            "family": "usb_multi_interface",
        }
        model["hardware_profile_id"] = "dual_usb"
        model["ports"] = {
            "enabled": ["1", "2"],
        }
        model["nodes"] = {
            "1": {
                "role": "simplex",
                "callsign": "G4NAB-1",
            },
            "2": {
                "role": "repeater",
                "callsign": "G4NAB-2",
            },
        }
        model["modules_multi"] = {
            "echolink_port": None,
            "metar_ports": [],
        }
        model["metar"].update({
            "region": "ukwide",
            "startdefault": None,
            "airports": [],
        })
        return model

    def test_online_control_single_save_and_navigation(self):
        for role, destination in (
            ("simplex", "/modules"),
            ("repeater", "/repeater"),
        ):
            for reconfigure in (False, True):
                with self.subTest(role=role, reconfigure=reconfigure):
                    model = new_node_model()
                    model["node"]["type"] = role
                    data = {
                        "single_enabled": "1",
                        "single_command": "012345",
                    }
                    if reconfigure:
                        data["reconfigure"] = "1"

                    with patch.object(
                        dashboard, "load_node_model", return_value=model
                    ), patch.object(
                        dashboard, "save_node_model"
                    ) as save:
                        with dashboard.app.test_request_context(
                            "/online-control", method="POST", data=data
                        ):
                            response = dashboard.online_control_page()

                    save.assert_called_once_with(model)
                    self.assertEqual(
                        model["online_control"],
                        {"enabled": True, "command": "012345"},
                    )
                    self.assertEqual(
                        response.headers["Location"],
                        "/build" if reconfigure else destination,
                    )

    def test_online_control_ports_save_independently(self):
        model = self.multiport_model()
        model["nodes"]["2"]["online_control"] = {
            "enabled": True,
            "command": "654321",
        }

        with patch.object(
            dashboard, "load_node_model", return_value=model
        ), patch.object(
            dashboard, "save_node_model"
        ) as save:
            with dashboard.app.test_request_context(
                "/online-control",
                method="POST",
                data={
                    "port_1_enabled": "1",
                    "port_1_command": "012345",
                    "port_2_command": "654321",
                },
            ):
                response = dashboard.online_control_page()

        save.assert_called_once_with(model)
        self.assertEqual(
            model["nodes"]["1"]["online_control"],
            {"enabled": True, "command": "012345"},
        )
        self.assertEqual(
            model["nodes"]["2"]["online_control"],
            {"enabled": False, "command": "654321"},
        )
        self.assertEqual(
            response.headers["Location"], "/port-repeater"
        )

    def test_online_control_invalid_port_does_not_partially_save(self):
        model = self.multiport_model()

        with patch.object(
            dashboard, "load_node_model", return_value=model
        ), patch.object(
            dashboard, "save_node_model"
        ) as save, patch.object(
            dashboard, "get_version_info", return_value={}
        ), patch.object(
            dashboard, "render_template", return_value="invalid"
        ) as render:
            with dashboard.app.test_request_context(
                "/online-control",
                method="POST",
                data={
                    "port_1_enabled": "1",
                    "port_1_command": "012345",
                    "port_2_enabled": "1",
                    "port_2_command": "12345#",
                },
            ):
                response = dashboard.online_control_page()

        self.assertEqual(response, "invalid")
        save.assert_not_called()
        for node in model["nodes"].values():
            self.assertNotIn("online_control", node)

        values = render.call_args.kwargs
        self.assertIn("Port 2", values["error"])
        self.assertEqual(
            values["controls"][1]["command"], "12345#"
        )

    def test_online_control_get_renders_saved_settings(self):
        model = new_node_model()
        model["online_control"] = {
            "enabled": True,
            "command": "012345",
        }

        with patch.object(
            dashboard, "load_node_model", return_value=model
        ), patch.object(
            dashboard, "get_version_info",
            return_value={"package": "test", "engine": "test"},
        ):
            with dashboard.app.test_request_context(
                "/online-control?reconfigure=1"
            ):
                html = dashboard.online_control_page()

        self.assertIn('value="012345"', html)
        self.assertIn('name="single_enabled"', html)
        self.assertIn('name="reconfigure" value="1"', html)

    def test_online_control_requires_authorisation(self):
        with patch.object(
            dashboard, "dashboard_auth_exists", return_value=True
        ), patch.object(
            dashboard, "load_node_model"
        ) as load:
            with dashboard.app.test_client() as client:
                for method in ("get", "post"):
                    with self.subTest(method=method):
                        response = getattr(client, method)(
                            "/online-control"
                        )
                        self.assertEqual(response.status_code, 302)
                        self.assertIn(
                            "/authorise?",
                            response.headers["Location"],
                        )

        load.assert_not_called()

    def test_dual_usb_nodes_use_discovered_device_mapping(self):
        model = self.multiport_model()
        model["hardware_preparation"] = {
            "status": "reviewed",
            "dual_usb": {
                "ready": True,
                "ports": [
                    {
                        "port": "1",
                        "audio_index": 2,
                        "audio_dev": (
                            "alsa:plughw:CARD=Set,DEV=0"
                        ),
                        "hidraw_device": "/dev/hidraw0",
                    },
                    {
                        "port": "2",
                        "audio_index": 3,
                        "audio_dev": (
                            "alsa:plughw:CARD=Device,DEV=0"
                        ),
                        "hidraw_device": "/dev/hidraw1",
                    },
                ],
                "errors": [],
            },
        }

        profile = {
            "port_map": {
                "1": {
                    "rx_audio": "alsa:plughw:0",
                    "tx_audio": "alsa:plughw:0",
                    "hidraw_device": "/dev/hidraw0",
                },
                "2": {
                    "rx_audio": "alsa:plughw:1",
                    "tx_audio": "alsa:plughw:1",
                    "hidraw_device": "/dev/hidraw1",
                },
            },
        }

        nodes = dashboard.initialise_port_nodes(
            model,
            profile,
        )

        self.assertEqual(
            nodes["1"]["audio"]["rx_audio"],
            "alsa:plughw:CARD=Set,DEV=0",
        )
        self.assertEqual(
            nodes["1"]["audio"]["tx_audio"],
            "alsa:plughw:CARD=Set,DEV=0",
        )
        self.assertEqual(
            nodes["1"]["hidraw"]["device"],
            "/dev/hidraw0",
        )
        self.assertEqual(
            nodes["2"]["audio"]["rx_audio"],
            "alsa:plughw:CARD=Device,DEV=0",
        )
        self.assertEqual(
            nodes["2"]["audio"]["tx_audio"],
            "alsa:plughw:CARD=Device,DEV=0",
        )
        self.assertEqual(
            nodes["2"]["hidraw"]["device"],
            "/dev/hidraw1",
        )

    def test_nanopi_platform_routes_to_preparation(
        self,
    ):
        model = new_node_model()
        model["platform"] = {
            "id": "nanopi_neo",
            "name": "NanoPi-Neo",
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,

        ), patch.object(
            dashboard,
            "save_node_model",
        ), patch.object(
            dashboard,
            "prepare_service_account",
        ) as prepare_account:
            with dashboard.app.test_request_context(
                "/platform",
                method="POST",
            ):
                response = dashboard.platform_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/nanopi-prepare",
        )
        prepare_account.assert_not_called()

    def test_verified_nanopi_routes_to_hardware(
        self,
    ):
        model = new_node_model()
        model["platform"] = {
            "id": "nanopi_neo",
            "name": "NanoPi-Neo",
        }
        model["nanopi_prepare"] = {
            "verified": True,
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ):
            with dashboard.app.test_request_context(
                "/platform",
                method="POST",
            ):
                response = dashboard.platform_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/hardware",
        )

    def test_raspberry_pi_prepares_gpio_account(
        self,
    ):
        model = new_node_model()
        model["platform"] = {
            "id": "raspberry_pi",
            "name": "Raspberry Pi",
            "supported": True,
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ), patch.object(
            dashboard,
            "prepare_service_account",
            return_value={
                "ok": True,
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            },
        ) as prepare_account:
            with dashboard.app.test_request_context(
                "/platform",
                method="POST",
            ):
                response = dashboard.platform_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/hardware",
        )
        prepare_account.assert_called_once_with(
            require_gpio=True
        )

    def test_linux_server_prepares_non_gpio_account(
        self,
    ):
        model = new_node_model()
        model["platform"] = {
            "id": "linux_server",
            "name": "Debian Server",
            "supported": True,
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ), patch.object(
            dashboard,
            "prepare_service_account",
            return_value={
                "ok": True,
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            },
        ) as prepare_account:
            with dashboard.app.test_request_context(
                "/platform",
                method="POST",
            ):
                response = dashboard.platform_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/hardware",
        )
        prepare_account.assert_called_once_with(
            require_gpio=False
        )

    def test_ready_nanopi_continues_to_hardware(
        self,
    ):
        model = new_node_model()
        model["platform"] = {
            "id": "nanopi_neo",
            "name": "NanoPi-Neo",
        }
        model["build"] = {
            "resume_after_reboot": (
                "/nanopi-prepare"
            ),
        }
        model["nanopi_prepare"] = {
            "reboot_required": True,
            "verified": False,
        }
        status = {
            "helper_available": True,
            "boot_check": {
                "ok": True,
                "stdout": "READY=yes",
                "stderr": "",
            },
            "boot_configured": True,
            "i2c_available": True,
            "analog_codec_available": True,
            "ready": True,
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ), patch.object(
            dashboard,
            "build_nanopi_status",
            return_value=status,
        ), patch.object(
            dashboard,
            "prepare_service_account",
            return_value={
                "ok": True,
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            },
        ) as prepare_account:
            with dashboard.app.test_request_context(
                "/nanopi-prepare",
                method="POST",
                data={
                    "action": "continue",
                },
            ):
                response = (
                    dashboard.nanopi_prepare_page()
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/hardware",
        )
        self.assertTrue(
            model["nanopi_prepare"]["verified"]
        )
        self.assertFalse(
            model["nanopi_prepare"][
                "reboot_required"
            ]
        )
        self.assertNotIn(
            "resume_after_reboot",
            model["build"],
        )
        prepare_account.assert_called_once_with(
            require_gpio=True
        )

    def test_detect_platform_uses_common_profile(
        self,
    ):
        expected = {
            "id": "linux_server",
            "name": "Debian Server",
            "supported": True,
        }

        with patch.object(
            dashboard.hw_platforms,
            "get_platform_profile",
            return_value=expected,
        ) as get_profile:
            platform = dashboard.detect_platform()

        self.assertEqual(platform, expected)
        get_profile.assert_called_once_with()

    def test_nanopi_reboot_preserves_resume_route(
        self,
    ):
        model = new_node_model()
        model["platform"] = {
            "id": "nanopi_neo",
            "name": "NanoPi-Neo",
        }
        status = {
            "helper_available": True,
            "boot_check": {
                "ok": True,
                "stdout": "READY=yes",
                "stderr": "",
            },
            "boot_configured": True,
            "i2c_available": False,
            "analog_codec_available": False,
            "ready": False,
        }
        reboot_result = Mock(
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ), patch.object(
            dashboard,
            "build_nanopi_status",
            return_value=status,
        ), patch.object(
            dashboard,
            "schedule_reboot",
            return_value=reboot_result,
        ) as reboot_mock:
            with dashboard.app.test_request_context(
                "/nanopi-prepare",
                method="POST",
                data={
                    "action": "reboot",
                },
            ):
                response = (
                    dashboard.nanopi_prepare_page()
                )

        reboot_mock.assert_called_once_with(8)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/rebooting?return_to=nanopi",
        )
        self.assertEqual(
            model["build"]["resume_after_reboot"],
            "/nanopi-prepare",
        )
        self.assertTrue(
            model["nanopi_prepare"][
                "reboot_required"
            ]
        )

    def test_modules_reconfiguration_routes_to_port_modules(self):
        for profile, ports in (
            ("ics_1x", ["1"]),
            ("dual_usb", ["1", "2"]),
        ):
            with self.subTest(profile=profile):
                model = self.multiport_model()
                model["hardware_profile_id"] = profile
                model["ports"]["enabled"] = ports

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        "/modules?reconfigure=1"
                    ):
                        response = dashboard.modules_page()

                self.assertEqual(
                    response.headers["Location"],
                    "/port-modules?reconfigure=1",
                )
                save.assert_not_called()

    def test_port_modules_remove_restore_and_move_optional_modules(self):
        model = self.multiport_model()
        model["metar"]["startdefault"] = "KMCO"
        model["echolink"]["callsign"] = "G4NAB-R"

        for echolink_port, metar_ports in (
            ("1", ["1"]),
            ("none", []),
            ("2", ["2"]),
        ):
            with self.subTest(
                echolink_port=echolink_port,
                metar_ports=metar_ports,
            ):
                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        "/port-modules",
                        method="POST",
                        data={
                            "reconfigure": "1",
                            "echolink_port": echolink_port,
                            "metar_ports": metar_ports,
                        },
                    ):
                        response = dashboard.port_modules_page()

                self.assertEqual(response.headers["Location"], "/build")
                save.assert_called_once_with(model)

                self.assertEqual(
                    model["echolink"]["enabled"],
                    echolink_port != "none",
                )
                self.assertEqual(
                    model["metar"]["enabled"],
                    bool(metar_ports),
                )
                self.assertEqual(
                    model["echolink"]["callsign"], "G4NAB-R"
                )
                self.assertEqual(
                    model["metar"]["startdefault"], "KMCO"
                )

                enabled = model["modules"]["enabled"]
                self.assertEqual(
                    "ModuleEchoLink" in enabled,
                    echolink_port != "none",
                )
                self.assertEqual(
                    "ModuleMetarInfo" in enabled,
                    bool(metar_ports),
                )

                for port_id in ("1", "2"):
                    self.assertEqual(
                        model["nodes"][port_id]["modules"],
                        {
                            "echolink": port_id == echolink_port,
                            "metar": port_id in metar_ports,
                        },
                    )

    def post_port_modules(self, model, reconfigure=False):
        form = {
            "echolink_port": "none",
            "metar_ports": "1",
        }

        if reconfigure:
            form["reconfigure"] = "1"

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ):
            with dashboard.app.test_request_context(
                "/port-modules",
                method="POST",
                data=form,
            ):
                return dashboard.port_modules_page()

    def test_initial_port_modules_sets_explicit_metar_return(self):
        model = self.multiport_model()

        response = self.post_port_modules(model)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/metar-default?return_to=port_ident",
        )
        self.assertNotIn(
            "return_after_metar",
            model.get("build", {}),
        )
        self.assertNotIn(
            "return_after_modules",
            model.get("build", {}),
        )

    def test_reconfigured_port_modules_returns_metar_to_build(self):
        model = self.multiport_model()

        response = self.post_port_modules(
            model,
            reconfigure=True,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/metar-default?return_to=build",
        )

    def test_metar_default_preserves_explicit_return(self):
        model = self.multiport_model()
        airport = next(
            iter(dashboard.METAR_REGIONS["ukwide"])
        )

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ):
            with dashboard.app.test_request_context(
                "/metar-default",
                method="POST",
                data={
                    "startdefault": airport,
                    "return_to": "build",
                },
            ):
                response = dashboard.metar_default_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/metar-airports?return_to=build",
        )

    def test_metar_airports_returns_to_port_ident(self):
        model = self.multiport_model()
        airport = next(
            iter(dashboard.METAR_REGIONS["ukwide"])
        )
        model["metar"]["startdefault"] = airport

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ):
            with dashboard.app.test_request_context(
                "/metar-airports",
                method="POST",
                data={
                    "return_to": "port_ident",
                },
            ):
                response = dashboard.metar_airports_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/port-ident",
        )

    def test_metar_airports_returns_to_build(self):
        model = self.multiport_model()
        airport = next(
            iter(dashboard.METAR_REGIONS["ukwide"])
        )
        model["metar"]["startdefault"] = airport

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ):
            with dashboard.app.test_request_context(
                "/metar-airports",
                method="POST",
                data={
                    "return_to": "build",
                },
            ):
                response = dashboard.metar_airports_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/build",
        )

    def test_reflector_completion_routes_to_node_information(self):
        for model in (
            new_node_model(),
            self.multiport_model(),
        ):
            with self.subTest(
                multiport=dashboard.is_multiport_build(model),
            ):
                with dashboard.app.test_request_context():
                    self.assertEqual(
                        dashboard.next_after_reflector(model),
                        "/node-info",
                    )

    def test_authentication_setup_continues_to_start(self):
        model = new_node_model()

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "generate_password_hash",
            return_value="test-password-hash",
        ):
            with dashboard.app.test_request_context(
                "/setup-auth",
                method="POST",
                data={
                    "username": "operator",
                    "password": "private-test-password",
                },
            ):
                response = dashboard.setup_auth_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/start",
        )
        self.assertEqual(
            model["dashboard_auth"]["username"],
            "operator",
        )
        self.assertEqual(
            model["dashboard_auth"]["password_hash"],
            "test-password-hash",
        )
        save_mock.assert_called_once_with(model)

    def test_node_information_uses_correct_next_step(self):
        cases = (
            (
                new_node_model(),
                "/review",
            ),
            (
                self.multiport_model(),
                "/topology",
            ),
        )

        for model, expected_location in cases:
            with self.subTest(
                expected_location=expected_location,
            ):
                with patch.object(
                    dashboard,
                    "load_node_model",
                    return_value=model,
                ), patch.object(
                    dashboard,
                    "save_node_model",
                ) as save_mock, patch.object(
                    dashboard,
                    "update_node_information_from_form",
                    return_value=model["node_info"],
                ), patch.object(
                    dashboard,
                    "update_location_information_from_form",
                    return_value=model["location_info"],
                ), patch.object(
                    dashboard,
                    "validate_node_information",
                    return_value=[],
                ):
                    with dashboard.app.test_request_context(
                        "/node-info",
                        method="POST",
                        data={},
                    ):
                        response = dashboard.node_info_page()

                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response.headers["Location"],
                    expected_location,
                )
                save_mock.assert_called_once_with(model)

    def test_multiport_final_validation_uses_correct_destination(self):
        cases = (
            (
                False,
                False,
                "/review",
            ),
            (
                True,
                False,
                "/review",
            ),
            (
                True,
                True,
                "/build",
            ),
        )

        for authenticated, reconfigure, expected_location in cases:
            with self.subTest(
                authenticated=authenticated,
                reconfigure=reconfigure,
            ):
                model = self.multiport_model()
                model.setdefault("build", {}).update({
                    "topology_configured": True,
                    "tones_configured": True,
                })

                for node in model["nodes"].values():
                    node.update({
                        "node_details_configured": True,
                        "squelch_configured": True,
                        "ident_configured": True,
                        "repeater_configured": True,
                    })

                if authenticated:
                    model["dashboard_auth"] = {
                        "username": "operator",
                        "password_hash": "test-password-hash",
                    }

                form = {}

                if reconfigure:
                    form["reconfigure"] = "1"

                with patch.object(
                    dashboard,
                    "load_node_model",
                    return_value=model,
                ), patch.object(
                    dashboard,
                    "save_node_model",
                ) as save_mock, patch.object(
                    dashboard,
                    "validate_topology",
                    return_value=[],
                ):
                    with dashboard.app.test_request_context(
                        "/port-final-review",
                        method="POST",
                        data=form,
                    ):
                        response = (
                            dashboard.port_final_review_page()
                        )

                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response.headers["Location"],
                    expected_location,
                )
                self.assertTrue(
                    model["build"][
                        "port_final_review_confirmed"
                    ]
                )
                save_mock.assert_called_once_with(model)

    def test_echolink_form_omits_managed_location_prefix(self):
        model = new_node_model()
        model["echolink"].update({
            "enabled": True,
            "callsign": "G4NAB-R",
            "password": "test-password",
            "sysopname": "Chris",
            "location": "[Svx] London",
        })

        captured = {}

        def capture_template(
            template_name,
            **context,
        ):
            captured["template_name"] = template_name
            captured["context"] = context
            return "rendered"

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "render_template",
            side_effect=capture_template,
        ):
            with dashboard.app.test_request_context(
                "/echolink",
                method="GET",
            ):
                response = dashboard.echolink_page()

        self.assertEqual(response, "rendered")
        self.assertEqual(
            captured["template_name"],
            "echolink.html",
        )
        self.assertEqual(
            captured["context"]["location_text"],
            "London",
        )

    def test_reconfigured_modules_use_explicit_build_return(self):
        cases = (
            (
                {
                    "reconfigure": "1",
                },
                "/build",
            ),
            (
                {
                    "reconfigure": "1",
                    "module_echolink": "yes",
                },
                "/echolink?return_to=build",
            ),
            (
                {
                    "reconfigure": "1",
                    "module_metar": "yes",
                },
                "/metar-default?return_to=build",
            ),
        )

        for form, expected_location in cases:
            with self.subTest(
                expected_location=expected_location,
            ):
                model = new_node_model()

                with patch.object(
                    dashboard,
                    "load_node_model",
                    return_value=model,
                ), patch.object(
                    dashboard,
                    "save_node_model",
                ) as save_mock:
                    with dashboard.app.test_request_context(
                        "/modules",
                        method="POST",
                        data=form,
                    ):
                        response = dashboard.modules_page()

                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response.headers["Location"],
                    expected_location,
                )
                save_mock.assert_called_once_with(model)

    def test_reconfigured_echolink_preserves_build_return(self):
        cases = (
            (
                False,
                "/build",
            ),
            (
                True,
                "/metar-default?return_to=build",
            ),
        )

        for metar_enabled, expected_location in cases:
            with self.subTest(
                metar_enabled=metar_enabled,
            ):
                model = new_node_model()
                model["metar"]["enabled"] = metar_enabled

                with patch.object(
                    dashboard,
                    "load_node_model",
                    return_value=model,
                ), patch.object(
                    dashboard,
                    "save_node_model",
                ) as save_mock:
                    with dashboard.app.test_request_context(
                        "/echolink",
                        method="POST",
                        data={
                            "return_to": "build",
                            "echolink_callsign": "G4NAB-R",
                            "echolink_password": "test-password",
                            "echolink_sysopname": "Chris",
                            "echolink_location": "London",
                        },
                    ):
                        response = dashboard.echolink_page()

                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response.headers["Location"],
                    expected_location,
                )
                self.assertEqual(
                    model["echolink"]["location"],
                    "[Svx] London",
                )
                save_mock.assert_called_once_with(model)

    def test_reconfigured_node_information_returns_to_build(self):
        model = new_node_model()

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "update_node_information_from_form",
            return_value=model["node_info"],
        ), patch.object(
            dashboard,
            "update_location_information_from_form",
            return_value=model["location_info"],
        ), patch.object(
            dashboard,
            "validate_node_information",
            return_value=[],
        ), patch.object(
            dashboard,
            "build_svxlink_configuration",
        ) as build_mock:
            with dashboard.app.test_request_context(
                "/edit/node-info",
                method="POST",
                data={
                    "reconfigure": "1",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.node_info_edit_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/build",
        )
        save_mock.assert_called_once_with(model)
        build_mock.assert_not_called()

    def test_reconfiguration_menu_includes_shared_targets(self):
        for model in (
            new_node_model(),
            self.multiport_model(),
        ):
            captured = {}

            def capture_template(
                template_name,
                **context,
            ):
                captured["template_name"] = template_name
                captured["context"] = context
                return "rendered"

            with patch.object(
                dashboard,
                "load_node_model",
                return_value=model,
            ), patch.object(
                dashboard,
                "render_template",
                side_effect=capture_template,
            ):
                with dashboard.app.test_request_context(
                    "/reconfigure",
                    method="GET",
                ):
                    response = dashboard.reconfigure_page()

            self.assertEqual(response, "rendered")
            self.assertEqual(
                captured["template_name"],
                "reconfigure.html",
            )

            target_ids = {
                target["id"]
                for target in captured["context"][
                    "reconfigure_targets"
                ]
            }

            self.assertTrue({
                "modules",
                "reflector",
                "node_info",
                "tones",
                "build",
                "full_reset",
            }.issubset(target_ids))

    def test_reflector_selection_template_matches_current_route(self):
        template_text = Path(
            "templates/reflector.html"
        ).read_text(
            encoding="utf-8"
        )

        dashboard.app.jinja_env.parse(template_text)

        self.assertIn(
            'name="reflector_route"',
            template_text,
        )
        self.assertIn(
            'value="none"',
            template_text,
        )
        self.assertIn(
            'value="federation"',
            template_text,
        )
        self.assertIn(
            'value="v2"',
            template_text,
        )
        self.assertIn(
            'value="v3"',
            template_text,
        )
        self.assertIn(
            "SvxLink Dashboard password",
            template_text,
        )
        self.assertNotIn(
            'name="connect"',
            template_text,
        )

    def test_courtesy_page_accepts_selected_cw_letter(self):
        model = new_node_model()
        model["node"]["type"] = "simplex"

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock:
            with dashboard.app.test_request_context(
                "/courtesy",
                method="POST",
                data={
                    "courtesy_mode": "R",
                },
            ):
                response = dashboard.courtesy_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/online-control",
        )
        self.assertEqual(
            model["tones"]["courtesy_mode"],
            "R",
        )
        self.assertEqual(
            model["tones"]["idle_mode"],
            "silence",
        )
        self.assertEqual(
            model["tones"]["closedown_mode"],
            "none",
        )
        save_mock.assert_called_once_with(model)

    def test_courtesy_template_offers_supported_cw_letters(self):
        template_text = Path(
            "templates/courtesy.html"
        ).read_text(
            encoding="utf-8"
        )

        for letter in (
            "A",
            "D",
            "E",
            "I",
            "K",
            "M",
            "N",
            "R",
            "S",
            "T",
            "U",
            "X",
        ):
            with self.subTest(letter=letter):
                self.assertIn(
                    f'value="{letter}"',
                    template_text,
                )

        self.assertIn(
            "E, I, K and R are common choices",
            template_text,
        )
        self.assertNotIn(
            'value="beep"',
            template_text,
        )
        self.assertNotIn(
            'name="tone_frequency"',
            template_text,
        )
        self.assertNotIn(
            "Courtesy beep frequency",
            template_text,
        )

    def test_review_templates_show_cw_courtesy_without_beep(self):
        for template_name in (
            "review.html",
            "port_final_review.html",
        ):
            with self.subTest(template=template_name):
                template_text = (
                    Path("templates") / template_name
                ).read_text(encoding="utf-8")

                self.assertNotIn(
                    "Beep frequency",
                    template_text,
                )
                self.assertNotIn(
                    "courtesy_frequency",
                    template_text,
                )
                self.assertIn(
                    "CW",
                    template_text,
                )

    def test_courtesy_repeater_controls_follow_port_roles(self):
        cases = (
            (
                {
                    "hardware_profile_id": "ics_2x",
                    "ports": {
                        "enabled": ["1", "2"],
                    },
                    "nodes": {
                        "1": {
                            "role": "simplex",
                        },
                        "2": {
                            "role": "simplex",
                        },
                    },
                },
                False,
            ),
            (
                {
                    "hardware_profile_id": "ics_2x",
                    "ports": {
                        "enabled": ["1", "2"],
                    },
                    "nodes": {
                        "1": {
                            "role": "simplex",
                        },
                        "2": {
                            "role": "repeater",
                        },
                    },
                },
                True,
            ),
        )

        for model, controls_expected in cases:
            with self.subTest(
                controls_expected=controls_expected,
            ):
                model["tones"] = {
                    "courtesy_mode": "none",
                    "courtesy_frequency": 800,
                    "idle_mode": "silence",
                    "closedown_mode": "none",
                }

                with patch.object(
                    dashboard,
                    "load_node_model",
                    return_value=model,
                ):
                    with dashboard.app.test_request_context(
                        "/courtesy",
                    ):
                        html = dashboard.courtesy_page()

                if controls_expected:
                    self.assertIn(
                        'name="idle_mode"',
                        html,
                    )
                    self.assertIn(
                        'name="closedown_mode"',
                        html,
                    )
                else:
                    self.assertNotIn(
                        'name="idle_mode"',
                        html,
                    )
                    self.assertNotIn(
                        'name="closedown_mode"',
                        html,
                    )

    def test_reconfiguration_back_links_return_to_menu(self):
        template_names = (
            "environment.html",
            "timezone.html",
            "node.html",
            "interface.html",
            "squelch.html",
            "ident.html",
            "cw.html",
            "courtesy.html",
            "repeater.html",
            "modules.html",
            "reflector.html",
            "topology.html",
            "port_final_review.html",
        )

        for template_name in template_names:
            with self.subTest(
                template_name=template_name,
            ):
                template_text = (
                    Path("templates") / template_name
                ).read_text(
                    encoding="utf-8"
                )

                self.assertIn(
                    "reconfigure_page",
                    template_text,
                )

    def test_invalid_model_cannot_start_build(self):
        model = new_node_model()
        validation = {
            "validation_errors": [
                "Callsign is required.",
            ],
            "platform_errors": [],
        }
        captured = {}

        def capture_template(
            template_name,
            **context,
        ):
            captured["template_name"] = template_name
            captured["context"] = context
            return "rendered"

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "validate_build",
            return_value=validation,
        ) as validate_mock, patch.object(
            dashboard,
            "build_svxlink_configuration",
        ) as build_mock, patch.object(
            dashboard,
            "render_template",
            side_effect=capture_template,
        ):
            with dashboard.app.test_request_context(
                "/build",
                method="POST",
                data={},
            ):
                response = dashboard.build_page()

        self.assertEqual(response, "rendered")
        self.assertEqual(
            captured["template_name"],
            "build.html",
        )
        self.assertFalse(
            captured["context"]["build_allowed"],
        )
        self.assertEqual(
            captured["context"]["validation_errors"],
            validation["validation_errors"],
        )
        validate_mock.assert_called_once_with(model)
        build_mock.assert_not_called()

    def test_valid_model_may_start_build(self):
        model = new_node_model()
        validation = {
            "validation_errors": [],
            "platform_errors": [],
        }
        build_result = {
            "success": True,
            "service_status": "active",
        }
        captured = {}

        def capture_template(
            template_name,
            **context,
        ):
            captured["template_name"] = template_name
            captured["context"] = context
            return "rendered"

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "validate_build",
            return_value=validation,
        ), patch.object(
            dashboard,
            "build_svxlink_configuration",
            return_value=build_result,
        ) as build_mock, patch.object(
            dashboard,
            "render_template",
            side_effect=capture_template,
        ):
            with dashboard.app.test_request_context(
                "/build",
                method="POST",
                data={},
            ):
                response = dashboard.build_page()

        self.assertEqual(response, "rendered")
        self.assertEqual(
            captured["template_name"],
            "done.html",
        )
        build_mock.assert_called_once_with(
            model,
            restart=True,
        )

    def test_invalid_review_cannot_continue_to_build(self):
        model = new_node_model()
        model["dashboard_auth"] = {
            "username": "operator",
            "password_hash": "test-password-hash",
        }
        validation = {
            "validation_errors": [
                "Callsign is required.",
            ],
            "platform_errors": [],
        }
        captured = {}

        def capture_template(
            template_name,
            **context,
        ):
            captured["template_name"] = template_name
            captured["context"] = context
            return "rendered"

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "validate_build",
            return_value=validation,
        ), patch.object(
            dashboard,
            "render_template",
            side_effect=capture_template,
        ):
            with dashboard.app.test_request_context(
                "/review",
                method="POST",
                data={},
            ):
                response = dashboard.review_page()

        self.assertEqual(response, "rendered")
        self.assertEqual(
            captured["template_name"],
            "review.html",
        )
        self.assertFalse(
            captured["context"]["review_allowed"],
        )
        self.assertEqual(
            captured["context"]["validation_errors"],
            validation["validation_errors"],
        )

    def test_valid_review_continues_to_build(self):
        model = new_node_model()
        model["dashboard_auth"] = {
            "username": "operator",
            "password_hash": "test-password-hash",
        }
        validation = {
            "validation_errors": [],
            "platform_errors": [],
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "validate_build",
            return_value=validation,
        ) as validate_mock:
            with dashboard.app.test_request_context(
                "/review",
                method="POST",
                data={},
            ):
                response = dashboard.review_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/build",
        )
        validate_mock.assert_called_once_with(model)

    def test_ready_dual_usb_preparation_is_saved(self):
        model = new_node_model()
        model["hardware_profile_id"] = "dual_usb"

        profile = {
            "profile_id": "dual_usb",
            "family": "usb_multi_interface",
            "type": "multi_interface",
        }

        inspection = {
            "ready": True,
            "ports": [
                {
                    "port": "1",
                    "audio_index": 2,
                    "audio_dev": (
                        "alsa:plughw:CARD=Set,DEV=0"
                    ),
                    "audio_name": "Set",
                    "audio_description": (
                        "C-Media USB Headphone Set"
                    ),
                    "hidraw_device": "/dev/hidraw0",
                    "hidraw_exists": True,
                    "hidraw_accessible": True,
                    "hidraw_is_cmedia": True,
                },
                {
                    "port": "2",
                    "audio_index": 3,
                    "audio_dev": (
                        "alsa:plughw:CARD=Device,DEV=0"
                    ),
                    "audio_name": "Device",
                    "audio_description": (
                        "C-Media USB Audio Device"
                    ),
                    "hidraw_device": "/dev/hidraw1",
                    "hidraw_exists": True,
                    "hidraw_accessible": True,
                    "hidraw_is_cmedia": True,
                },
            ],
            "errors": [],
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "load_hardware_profile",
            return_value=profile,
        ), patch.object(
            dashboard,
            "inspect_dual_usb_hardware",
            return_value=inspection,
            create=True,
        ) as inspect_mock, patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock:
            with dashboard.app.test_request_context(
                "/hardware-prepare/reviewed",
                method="POST",
            ):
                response = (
                    dashboard.hardware_prepare_reviewed_page()
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/hardware-ports",
        )
        inspect_mock.assert_called_once_with()
        save_mock.assert_called_once_with(model)
        self.assertEqual(
            model["hardware_preparation"]["status"],
            "reviewed",
        )
        self.assertEqual(
            model["hardware_preparation"]["dual_usb"],
            inspection,
        )

    def test_incomplete_dual_usb_preparation_is_blocked(
        self,
    ):
        model = new_node_model()
        model["hardware_profile_id"] = "dual_usb"

        profile = {
            "profile_id": "dual_usb",
            "family": "usb_multi_interface",
            "type": "multi_interface",
        }

        inspection = {
            "ready": False,
            "ports": [],
            "errors": [
                (
                    "Exactly two duplex USB audio devices "
                    "are required; 1 was detected."
                ),
            ],
        }

        captured = {}

        def capture_template(
            template_name,
            **context,
        ):
            captured["template_name"] = template_name
            captured["context"] = context
            return "rendered"

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "load_hardware_profile",
            return_value=profile,
        ), patch.object(
            dashboard,
            "inspect_dual_usb_hardware",
            return_value=inspection,
            create=True,
        ) as inspect_mock, patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "render_template",
            side_effect=capture_template,
        ):
            with dashboard.app.test_request_context(
                "/hardware-prepare/reviewed",
                method="POST",
            ):
                response = (
                    dashboard.hardware_prepare_reviewed_page()
                )

        self.assertEqual(response, "rendered")
        self.assertEqual(
            captured["template_name"],
            "hardware_prepare.html",
        )
        self.assertEqual(
            captured["context"]["dual_usb_status"],
            inspection,
        )
        self.assertIn(
            "Exactly two duplex USB audio devices",
            captured["context"]["error"],
        )
        inspect_mock.assert_called_once_with()
        save_mock.assert_not_called()

    def test_review_template_contains_final_validation_summary(self):
        template_text = Path(
            "templates/review.html"
        ).read_text(
            encoding="utf-8"
        )

        dashboard.app.jinja_env.parse(template_text)

        required_labels = (
            "Primary-port completion",
            "Reflector-route completion",
            "ReflectorLogic callsign",
            "Runtime-managed talkgroups",
            "Installation-wide tones",
            "Reflector node-map publication",
            "SvxLink LocationInfo / APRS publication",
            "Publication information",
            "Reflector link ports",
            "Independent ports",
            "Local link",
            "Resolve Configuration Issues",
            "Repair Node Information",
        )

        for label in required_labels:
            with self.subTest(label=label):
                self.assertIn(label, template_text)


if __name__ == "__main__":
    unittest.main()
