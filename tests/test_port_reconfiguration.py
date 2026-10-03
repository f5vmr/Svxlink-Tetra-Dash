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
                    "/build" if reconfigure else "/courtesy",
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


if __name__ == "__main__":
    unittest.main()
