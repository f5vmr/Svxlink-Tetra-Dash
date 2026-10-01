#!/usr/bin/env python3

import unittest

from unittest.mock import patch

import app as dashboard


class ProtectedEditingTests(unittest.TestCase):

    def test_invalid_echolink_edit_does_not_save_or_restart(self):

        model = {
            "echolink": {
                "enabled": True,
                "callsign": "G4NAB-L",
                "password": "existing-password",
                "sysopname": "Chris",
                "location": "[Svx] Existing",
            },
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "build_svxlink_configuration",
        ) as build_mock, patch.object(
            dashboard,
            "render_template",
            side_effect=lambda template, **context: context,
        ):
            with dashboard.app.test_request_context(
                "/edit/echolink",
                method="POST",
                data={
                    "enabled": "yes",
                    "callsign": "G4NAB",
                    "password": "new-password",
                    "sysopname": "Chris",
                    "location": "[Svx] Newcastle",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.echolink_edit_page()
        self.assertIsInstance(response, dict)
        self.assertEqual(
            response["error"],
            "EchoLink callsign must end in -L or -R.",
        )
        self.assertEqual(
            model["echolink"]["callsign"],
            "G4NAB-L",
        )
        save_mock.assert_not_called()
        build_mock.assert_not_called()

    def test_valid_echolink_edit_saves_and_restarts(self):

        model = {
            "echolink": {
                "enabled": True,
                "callsign": "G4NAB-L",
                "password": "existing-password",
                "sysopname": "Chris",
                "location": "[Svx] Existing",
            },
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "build_svxlink_configuration",
            return_value={"success": True},
        ) as build_mock:
            with dashboard.app.test_request_context(
                "/edit/echolink",
                method="POST",
                data={
                    "enabled": "yes",
                    "callsign": "G4NAB-R",
                    "password": "new-password",
                    "sysopname": "Chris",
                    "location": "[Svx] Newcastle",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.echolink_edit_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/edit/echolink?saved=1",
        )
        self.assertEqual(
            model["echolink"]["location"],
            "[Svx] Newcastle",
        )
        save_mock.assert_called_once_with(model)
        build_mock.assert_called_once_with(
            model,
            restart=True,
        )

    def test_echolink_menu_removes_and_restores_module(self):
        model = {
            "echolink": {
                "enabled": True,
                "callsign": "G4NAB-R",
                "password": "existing-password",
                "sysopname": "Chris",
                "location": "[Svx] Newcastle",
            },
            "modules": {
                "enabled": [
                    "ModuleHelp",
                    "ModuleParrot",
                    "ModuleEchoLink",
                    "ModuleMetarInfo",
                ],
            },
        }

        for enabled in (False, True, False):
            with self.subTest(enabled=enabled):
                def check_rebuild(saved_model, restart):
                    self.assertTrue(restart)
                    self.assertEqual(
                        saved_model["echolink"]["enabled"],
                        enabled,
                    )
                    names = saved_model["modules"]["enabled"]
                    self.assertEqual(
                        names.count("ModuleEchoLink"),
                        1 if enabled else 0,
                    )
                    for required in (
                        "ModuleHelp",
                        "ModuleParrot",
                        "ModuleMetarInfo",
                    ):
                        self.assertEqual(names.count(required), 1)
                    return {"success": True}

                with patch.object(
                    dashboard,
                    "load_node_model",
                    return_value=model,
                ), patch.object(
                    dashboard,
                    "save_node_model",
                ) as save_mock, patch.object(
                    dashboard,
                    "build_svxlink_configuration",
                    side_effect=check_rebuild,
                ) as build_mock:
                    with dashboard.app.test_request_context(
                        "/edit/echolink",
                        method="POST",
                        data={
                            "enabled": "yes" if enabled else "no",
                            "callsign": "G4NAB-R",
                            "password": "existing-password",
                            "sysopname": "Chris",
                            "location": "Newcastle",
                        },
                    ):
                        dashboard.session["authorised"] = True
                        response = dashboard.echolink_edit_page()

                self.assertEqual(
                    response.headers["Location"],
                    "/edit/echolink?saved=1",
                )
                save_mock.assert_called_once_with(model)
                build_mock.assert_called_once_with(
                    model,
                    restart=True,
                )

    def test_invalid_metar_format_does_not_save_or_build(self):

        model = {
            "metar": {
                "enabled": True,
                "startdefault": "EGNT",
                "airports": ["EGNV"],
            },
            "modules": {
                "enabled": ["ModuleMetarInfo"],
            },
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "build_svxlink_configuration",
        ) as build_mock, patch.object(
            dashboard,
            "find_unavailable_metar_airports",
        ) as source_mock, patch.object(
            dashboard,
            "render_template",
            side_effect=lambda template, **context: context,
        ):
            with dashboard.app.test_request_context(
                "/edit/metar",
                method="POST",
                data={
                    "enabled": "yes",
                    "startdefault": "EG1T",
                    "airports": "EGNV",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.metar_edit_page()

        self.assertIsInstance(response, dict)
        self.assertEqual(
            response["error"],
            "Default airport ICAO must contain exactly four letters.",
        )
        self.assertEqual(
            model["metar"]["startdefault"],
            "EGNT",
        )
        source_mock.assert_not_called()
        save_mock.assert_not_called()
        build_mock.assert_not_called()

    def test_unavailable_metar_station_does_not_save_or_build(self):

        model = {
            "metar": {
                "enabled": True,
                "startdefault": "EGNT",
                "airports": ["EGNV"],
            },
            "modules": {
                "enabled": ["ModuleMetarInfo"],
            },
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "build_svxlink_configuration",
        ) as build_mock, patch.object(
            dashboard,
            "find_unavailable_metar_airports",
            return_value=["ZZZZ"],
        ) as source_mock, patch.object(
            dashboard,
            "render_template",
            side_effect=lambda template, **context: context,
        ):
            with dashboard.app.test_request_context(
                "/edit/metar",
                method="POST",
                data={
                    "enabled": "yes",
                    "startdefault": "EGNT",
                    "airports": "EGNV, ZZZZ",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.metar_edit_page()

        self.assertIsInstance(response, dict)
        self.assertEqual(
            response["error"],
            "No METAR weather source is available for: ZZZZ.",
        )
        self.assertEqual(
            model["metar"]["airports"],
            ["EGNV"],
        )
        source_mock.assert_called_once_with(
            ["EGNT", "EGNV", "ZZZZ"]
        )
        save_mock.assert_not_called()
        build_mock.assert_not_called()

    def test_metar_source_failure_preserves_configuration(self):

        model = {
            "metar": {
                "enabled": True,
                "startdefault": "EGNT",
                "airports": ["EGNV"],
            },
            "modules": {
                "enabled": ["ModuleMetarInfo"],
            },
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "build_svxlink_configuration",
        ) as build_mock, patch.object(
            dashboard,
            "find_unavailable_metar_airports",
            side_effect=dashboard.MetarVerificationUnavailable(),
        ), patch.object(
            dashboard,
            "render_template",
            side_effect=lambda template, **context: context,
        ):
            with dashboard.app.test_request_context(
                "/edit/metar",
                method="POST",
                data={
                    "enabled": "yes",
                    "startdefault": "EGNT",
                    "airports": "EGNV",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.metar_edit_page()

        self.assertIsInstance(response, dict)
        self.assertEqual(
            response["error"],
            (
                "METAR airport verification is temporarily "
                "unavailable. No settings were changed."
            ),
        )
        self.assertEqual(
            model["metar"]["startdefault"],
            "EGNT",
        )
        save_mock.assert_not_called()
        build_mock.assert_not_called()

    def test_valid_metar_edit_saves_and_builds(self):

        model = {
            "metar": {
                "enabled": True,
                "region": "ukwide",
                "startdefault": "EGNT",
                "airports": ["EGNV"],
            },
            "modules": {
                "enabled": ["ModuleMetarInfo"],
            },
        }

        build_result = {
            "validation_errors": [],
            "platform_errors": [],
            "deployment_errors": [],
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "build_svxlink_configuration",
            return_value=build_result,
        ) as build_mock, patch.object(
            dashboard,
            "find_unavailable_metar_airports",
            return_value=[],
        ) as source_mock:
            with dashboard.app.test_request_context(
                "/edit/metar",
                method="POST",
                data={
                    "enabled": "yes",
                    "startdefault": "EGNT",
                    "airports": "EGNV, EGCC",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.metar_edit_page()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/edit/metar?saved=1",
        )
        self.assertEqual(
            model["metar"]["airports"],
            ["EGNV", "EGCC"],
        )
        self.assertEqual(
            model["metar"]["region"],
            "ukwide",
        )
        source_mock.assert_called_once_with(
            ["EGNT", "EGNV", "EGCC"]
        )
        save_mock.assert_called_once_with(model)
        build_mock.assert_called_once_with(
            model,
            restart=True,
        )

    def test_partial_talkgroup_row_does_not_save(self):

        model = {
            "environment": {
                "region": "british_isles",
            },
        }

        existing = [
            {
                "id": "235",
                "label": "UK Wide",
                "colour": "tg-green",
                "command": "91235#",
            },
        ]

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "load_talkgroups",
            return_value=existing,
        ), patch.object(
            dashboard,
            "save_talkgroups",
        ) as save_mock, patch.object(
            dashboard,
            "render_template",
            side_effect=lambda template, **context: context,
        ):
            with dashboard.app.test_request_context(
                "/talkgroups",
                method="POST",
                data={
                    "id_0": "235",
                    "label_0": "",
                    "colour_0": "tg-green",
                    "command_0": "91235#",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.talkgroups_page()

        self.assertIsInstance(response, dict)
        self.assertEqual(
            response["error"],
            (
                "Talkgroup row 1 is incomplete. Enter both a "
                "talkgroup and label, or clear the row."
            ),
        )
        save_mock.assert_not_called()

    def test_valid_talkgroup_row_derives_command(self):

        model = {
            "environment": {
                "region": "british_isles",
            },
        }

        existing = [
            {
                "id": "235",
                "label": "UK Wide",
                "colour": "tg-green",
                "command": "91235#",
            },
        ]

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "load_talkgroups",
            return_value=existing,
        ), patch.object(
            dashboard,
            "save_talkgroups",
        ) as save_mock:
            with dashboard.app.test_request_context(
                "/talkgroups",
                method="POST",
                data={
                    "id_0": "2350",
                    "label_0": "UK Calling",
                    "colour_0": "tg-blue",
                    "command_0": "malicious-value",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.talkgroups_page()

        self.assertEqual(response.status_code, 302)
        save_mock.assert_called_once_with(
            "british_isles",
            [
                {
                    "id": "2350",
                    "label": "UK Calling",
                    "colour": "tg-blue",
                    "command": "912350#",
                },
            ],
        )

    def test_invalid_macro_edit_does_not_save_or_build(self):

        model = {
            "macros": {
                "1": "91235#",
            },
        }

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "save_node_model",
        ) as save_mock, patch.object(
            dashboard,
            "build_svxlink_configuration",
        ) as build_mock, patch.object(
            dashboard,
            "render_template",
            side_effect=lambda template, **context: context,
        ):
            with dashboard.app.test_request_context(
                "/macros",
                method="POST",
                data={
                    "number_0": "1",
                    "type_0": "custom",
                    "command_0": "91235#",
                    "number_1": "1",
                    "type_1": "custom",
                    "command_1": "91505#",
                },
            ):
                dashboard.session["authorised"] = True
                response = dashboard.macros_page()

        self.assertIsInstance(response, dict)
        self.assertEqual(
            response["error"],
            "Macro 1 is defined more than once.",
        )
        self.assertEqual(
            model["macros"],
            {
                "1": "91235#",
            },
        )
        save_mock.assert_not_called()
        build_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
