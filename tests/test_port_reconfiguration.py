import unittest
from unittest.mock import patch

import app as dashboard


class PortReconfigurationTests(unittest.TestCase):

    def render_menu(self, reconfigure=False):
        path = "/port-config"
        if reconfigure:
            path += "?reconfigure=1"

        with dashboard.app.test_request_context(path):
            return dashboard.render_template(
                "port_config.html",
                model={},
                profile={"port_map": {}},
                enabled_ports=[],
                port_roles={},
                nodes={},
                all_ports_configured=False,
                version_info={"package": "test", "engine": "test"},
            )

    def test_initial_setup_shows_back(self):
        html = self.render_menu()
        self.assertIn(">Back</a>", html)
        self.assertNotIn('name="reconfigure"', html)

    def test_reconfiguration_hides_back_and_preserves_form_flag(self):
        html = self.render_menu(reconfigure=True)
        self.assertNotIn(">Back</a>", html)
        self.assertIn('name="reconfigure" value="1"', html)

    def test_initialisation_preserves_reconfiguration(self):
        for reconfigure in (False, True):
            with self.subTest(reconfigure=reconfigure):
                model = {
                    "hardware_profile_id": "ics_4x",
                    "hardware": {"family": "ics"},
                    "ports": {"enabled": ["1"]},
                    "port_roles": {"1": {"role": "simplex"}},
                    "nodes": {},
                }
                form = {"reconfigure": "1"} if reconfigure else {}

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "load_hardware_profile",
                    return_value={"port_map": {}},
                ), patch.object(
                    dashboard, "initialise_port_nodes",
                    return_value={"1": {"role": "simplex"}},
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        "/port-config", method="POST", data=form
                    ):
                        response = dashboard.port_config_page()

                self.assertEqual(
                    response.headers["Location"],
                    "/port-config?reconfigure=1"
                    if reconfigure else "/port-config",
                )
                save.assert_called_once_with(model)


    def test_port_roles_page_has_continue_button(self):
        with dashboard.app.test_request_context(
            "/port-roles"
        ):
            html = dashboard.render_template(
                "port_roles.html",
                model={
                    "hardware_profile_id": "ics_2x",
                },
                enabled_ports=["1", "2"],
                port_roles={},
                error=None,
                version_info={
                    "package": "test",
                    "engine": "test",
                },
            )

        self.assertIn(
            'type="submit"',
            html,
        )
        self.assertIn(
            "Save roles and continue",
            html,
        )
        self.assertIn(
            "GPIO: GPIO26, TX_1",
            html,
        )
        self.assertIn(
            "GPIO: GPIO23, TX_2",
            html,
        )
        self.assertNotIn(
            "GPIO: RX_1",
            html,
        )
        self.assertNotIn(
            "GPIO: RX_2",
            html,
        )

    def test_port_roles_save_uses_correct_workflow(self):
        for reconfigure in (False, True):
            with self.subTest(reconfigure=reconfigure):
                model = {
                    "hardware_profile_id": "ics_4x",
                    "ports": {"enabled": ["1"]},
                    "nodes": {"1": {"role": "simplex"}},
                }
                form = {"port_1_role": "repeater"}
                if reconfigure:
                    form["reconfigure"] = "1"

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        "/port-roles", method="POST", data=form
                    ):
                        response = dashboard.port_roles_page()

                self.assertEqual(
                    response.headers["Location"],
                    "/build" if reconfigure else "/port-config",
                )
                self.assertEqual(
                    model["nodes"]["1"]["role"], "repeater"
                )
                save.assert_called_once_with(model)


    def test_squelch_reconfiguration_saves_each_port_and_returns_to_list(self):
        model = {
            "hardware_profile_id": "ics_2x",
            "hardware": {"family": "ics"},
            "ports": {"enabled": ["1", "2"]},
            "nodes": {
                "1": {"gpio": {"cos_invert": False, "ptt_invert": False}},
                "2": {"gpio": {"cos_invert": False, "ptt_invert": False}},
            },
        }

        for port_id in ("1", "2"):
            other_port = "2" if port_id == "1" else "1"
            other_before = repr(model["nodes"][other_port])

            with self.subTest(port_id=port_id):
                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "parse_squelch_form",
                    return_value=({"method": "gpiod"}, []),
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        f"/port-squelch/{port_id}",
                        method="POST",
                        data={
                            "reconfigure": "1",
                            "sql_gpio_invert": "yes",
                            "ptt_gpio_invert": "yes",
                        },
                    ):
                        response = dashboard.port_squelch_detail_page(port_id)

                self.assertEqual(
                    response.headers["Location"],
                    "/port-squelch?reconfigure=1",
                )
                save.assert_called_once_with(model)
                self.assertTrue(model["nodes"][port_id]["gpio"]["cos_invert"])
                self.assertTrue(model["nodes"][port_id]["gpio"]["ptt_invert"])
                self.assertTrue(model["nodes"][port_id]["squelch_configured"])
                self.assertEqual(
                    repr(model["nodes"][other_port]), other_before
                )


    def test_squelch_completion_preserves_workflow(self):
        for configured in (False, True):
            for reconfigure in (False, True):
                with self.subTest(
                    configured=configured,
                    reconfigure=reconfigure,
                ):
                    model = {
                        "hardware_profile_id": "ics_4x",
                        "ports": {"enabled": ["1"]},
                        "nodes": {
                            "1": {"squelch_configured": configured}
                        },
                    }
                    path = "/port-squelch-complete"
                    if reconfigure:
                        path += "?reconfigure=1"

                    with patch.object(
                        dashboard, "load_node_model",
                        return_value=model,
                    ), patch.object(
                        dashboard, "save_node_model"
                    ) as save:
                        with dashboard.app.test_request_context(path):
                            response = (
                                dashboard.port_squelch_complete_page()
                            )

                    if configured:
                        expected = (
                            "/build"
                            if reconfigure else "/port-modules"
                        )
                        save.assert_called_once_with(model)
                        self.assertTrue(
                            model["build"]["port_squelch_configured"]
                        )
                    else:
                        expected = "/port-squelch"
                        if reconfigure:
                            expected += "?reconfigure=1"
                        save.assert_not_called()

                    self.assertEqual(
                        response.headers["Location"], expected
                    )


    def test_profile_review_confirmation_uses_correct_workflow(self):
        for reconfigure in (False, True):
            with self.subTest(reconfigure=reconfigure):
                model = {
                    "hardware_profile_id": "ics_4x",
                    "ports": {"enabled": ["1"]},
                    "nodes": {
                        "1": {
                            "role": "simplex",
                            "node_details_configured": True,
                        }
                    },
                }
                form = {"reconfigure": "1"} if reconfigure else {}

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "load_hardware_profile",
                    return_value={"port_map": {}},
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        "/port-profile-review",
                        method="POST",
                        data=form,
                    ):
                        response = dashboard.port_profile_review_page()

                self.assertEqual(
                    response.headers["Location"],
                    "/build" if reconfigure else "/port-squelch",
                )
                self.assertTrue(
                    model["build"]["profile_interface_confirmed"]
                )
                save.assert_called_once_with(model)


    def test_primary_port_save_precedes_shared_tones(self):
        for reconfigure in (False, True):
            with self.subTest(reconfigure=reconfigure):
                model = {
                    "hardware_profile_id": "ics_4x",
                    "ports": {"enabled": ["1", "2"]},
                    "nodes": {
                        "1": {"callsign": "G4NAB-1"},
                        "2": {"callsign": "G4NAB-2"},
                    },
                }
                form = {"primary_port_id": "2"}
                if reconfigure:
                    form["reconfigure"] = "1"

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        "/installation-identity",
                        method="POST",
                        data=form,
                    ):
                        response = dashboard.installation_identity_page()

                self.assertEqual(
                    model["installation"]["primary_port_id"], "2"
                )
                self.assertEqual(
                    response.headers["Location"],
                    "/build" if reconfigure else "/cw",
                )
                save.assert_called_once_with(model)


    def test_reconfigure_menu_opens_port_squelch_with_flag(self):
        model = {
            "hardware": {"family": "ics"},
            "hardware_profile_id": "ics_4x",
            "ports": {"enabled": ["1", "2"]},
            "nodes": {
                "1": {"role": "simplex"},
                "2": {"role": "repeater"},
            },
        }

        with patch.object(
            dashboard, "load_node_model", return_value=model
        ):
            with dashboard.app.test_request_context(
                "/reconfigure",
                method="POST",
                data={"target": "port_squelch"},
            ):
                dashboard.session["authorised"] = True
                response = dashboard.reconfigure_page()

        self.assertEqual(
            response.headers["Location"],
            "/port-squelch?reconfigure=1",
        )


    def test_port_cw_redirects_to_shared_cw(self):
        cases = (
            (
                "/port-cw",
                {},
                "/cw",
            ),
            (
                "/port-cw?reconfigure=1",
                {},
                "/cw?reconfigure=1",
            ),
            (
                "/port-cw",
                {"reconfigure": "1"},
                "/cw?reconfigure=1",
            ),
        )

        for path, form, expected_location in cases:
            with self.subTest(
                path=path,
                form=form,
            ):
                method = "POST" if form else "GET"

                with dashboard.app.test_request_context(
                    path,
                    method=method,
                    data=form,
                ):
                    response = dashboard.port_cw_page()

                self.assertEqual(
                    response.status_code,
                    302,
                )
                self.assertEqual(
                    response.headers["Location"],
                    expected_location,
                )


if __name__ == "__main__":
    unittest.main()
