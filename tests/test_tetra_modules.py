import unittest
from unittest.mock import patch

import app as dashboard
from models.node_model import new_node_model
from renderers.svxlink_renderer import build_modules_line_for_node


class TetraModulesTests(unittest.TestCase):

    def test_single_tetra_modules_save_and_remove(self):
        model = new_node_model()
        model["ports"] = {"enabled": ["1"]}
        model["nodes"] = {
            "1": {
                "role": "tetra",
                "modules": {
                    "echolink": True,
                    "metar": True,
                },
            },
        }

        for enabled, expected in (
            (
                True,
                "MODULES=ModuleHelp,ModuleParrot,"
                "ModuleEchoLink,ModuleMetarInfo",
            ),
            (False, "MODULES=ModuleHelp,ModuleParrot"),
        ):
            with self.subTest(enabled=enabled):
                form = {"reconfigure": "1"}

                if enabled:
                    form.update({
                        "module_echolink": "yes",
                        "module_metar": "yes",
                    })

                with patch.object(
                    dashboard, "load_node_model", return_value=model
                ), patch.object(
                    dashboard, "save_node_model"
                ) as save:
                    with dashboard.app.test_request_context(
                        "/modules", method="POST", data=form
                    ):
                        response = dashboard.modules_page()

                save.assert_called_once_with(model)
                self.assertEqual(
                    build_modules_line_for_node(model["nodes"]["1"]),
                    expected,
                )
                self.assertEqual(
                    model["echolink"]["enabled"], enabled
                )
                self.assertEqual(
                    model["metar"]["enabled"], enabled
                )
                self.assertEqual(
                    response.headers["Location"],
                    "/echolink?return_to=build" if enabled else "/build",
                )

    def test_single_tetra_get_uses_standard_modules_page(self):
        model = new_node_model()
        model["ports"] = {"enabled": ["1"]}
        model["nodes"] = {"1": {"role": "tetra"}}

        with patch.object(
            dashboard, "load_node_model", return_value=model
        ), patch.object(
            dashboard,
            "render_template",
            return_value="modules page",
        ) as render:
            with dashboard.app.test_request_context("/modules"):
                response = dashboard.modules_page()

        self.assertEqual(response, "modules page")
        self.assertEqual(render.call_args.args[0], "modules.html")


if __name__ == "__main__":
    unittest.main()
