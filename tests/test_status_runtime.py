#!/usr/bin/env python3

import unittest
from unittest.mock import patch

import app as dashboard
from services import status_service


class RuntimeStatusTests(unittest.TestCase):

    def multiport_model(self):
        return {
            "installation": {
                "primary_port_id": "1",
            },
            "ports": {
                "enabled": ["1", "2"],
            },
            "nodes": {
                "1": {
                    "role": "simplex",
                    "callsign": "G4NAB-1",
                    "modules": {
                        "echolink": True,
                        "metar": False,
                    },
                },
                "2": {
                    "role": "repeater",
                    "callsign": "G4NAB-2",
                    "modules": {
                        "echolink": False,
                        "metar": True,
                    },
                },
            },
            "reflector": {
                "operational": {
                    "monitor_tgs": ["235", "2350"],
                },
            },
            "topology": {
                "reflector_link": {
                    "name": "LinkToReflector",
                    "ports": ["1"],
                },
                "local_links": [],
                "independent_ports": ["2"],
            },
            "environment": {
                "region": "british_isles",
            },
        }

    def test_runtime_status_uses_selected_port_radio_identity(self):
        model = self.multiport_model()

        with patch.object(
            status_service,
            "svxlink_status",
            return_value="active",
        ), patch.object(
            status_service,
            "get_system_uptime",
            return_value="1h",
        ), patch.object(
            status_service,
            "get_connected_reflector",
            return_value="Connected",
        ) as reflector_mock, patch.object(
            status_service,
            "get_active_talkgroup",
            return_value="235",
        ) as talkgroup_mock, patch.object(
            status_service,
            "get_recent_log_lines",
            return_value=[],
        ), patch.object(
            status_service,
            "get_radio_state",
            return_value={
                "label": "Receiving",
                "input": "Open",
                "class": "radio-rx",
                "tx": False,
                "rx": True,
            },
        ) as radio_mock, patch.object(
            status_service,
            "get_echolink_state",
            return_value={
                "active": False,
                "label": "Idle",
                "station": "",
                "class": "status-good",
            },
        ):
            status = status_service.get_runtime_status(
                model,
                selected_port="2",
            )

        self.assertEqual(status["callsign"], "G4NAB-2")
        self.assertEqual(status["node_type"], "repeater")
        self.assertEqual(status["selected_port"], "2")

        radio_mock.assert_called_once_with(
            selected_port="2"
        )
        reflector_mock.assert_called_once_with(model)
        talkgroup_mock.assert_called_once_with()

    def test_status_route_attributes_modules_and_topology_to_port(self):
        model = self.multiport_model()
        captured = {}

        def capture_template(template_name, **context):
            captured["template_name"] = template_name
            captured["context"] = context
            return context

        with patch.object(
            dashboard,
            "load_node_model",
            return_value=model,
        ), patch.object(
            dashboard,
            "get_system_info",
            return_value={},
        ), patch.object(
            dashboard,
            "get_runtime_status",
            return_value={
                "active_talkgroup": "235",
            },
        ), patch.object(
            dashboard,
            "get_reflector_activity",
            return_value=[],
        ), patch.object(
            dashboard,
            "load_talkgroups",
            return_value=[],
        ), patch.object(
            dashboard,
            "get_version_info",
            return_value={},
        ), patch.object(
            dashboard,
            "render_template",
            side_effect=capture_template,
        ):
            with dashboard.app.test_request_context(
                "/status?port=2"
            ):
                dashboard.status_page()

        context = captured["context"]

        self.assertEqual(
            captured["template_name"],
            "status.html",
        )
        self.assertEqual(context["selected_port"], "2")
        self.assertEqual(context["port_modules"], ["MetarInfo"])
        self.assertEqual(context["primary_port_id"], "1")
        self.assertEqual(context["primary_callsign"], "G4NAB-1")
        self.assertEqual(
            context["selected_topology_memberships"],
            ["Independent operation"],
        )

    def test_radio_state_uses_rotation_aware_log_reader(self):

        lines = [
            "Rx2: The squelch is open",
            "Unrelated event after log rotation",
        ]

        with patch.object(
            status_service,
            "svxlink_status",
            return_value="active",
        ), patch.object(
            status_service,
            "read_recent_svxlink_log_lines",
            return_value=lines,
        ) as log_mock:
            state = status_service.get_radio_state(
                selected_port="2"
            )

        self.assertEqual(state["label"], "Receiving")
        self.assertEqual(state["input"], "Open")
        self.assertTrue(state["rx"])
        self.assertFalse(state["tx"])
        log_mock.assert_called_once_with(300)

    def test_radio_state_does_not_reuse_events_before_restart(self):
        boundary = (
            "NOTICE: Initialization done. Starting main application."
        )

        for port in ("1", "2"):
            for fresh_events, expected_rx, expected_tx in (
                ([], False, False),
                ([f"Rx{port}: The squelch is OPEN"], True, False),
                ([f"Tx{port}: Turning the transmitter ON"], False, True),
                ([f"Rx{port}: The squelch is CLOSED"], False, False),
            ):
                with self.subTest(port=port, events=fresh_events):
                    lines = [
                        f"Rx{port}: The squelch is OPEN",
                        f"Tx{port}: Turning the transmitter ON",
                        "NOTICE: SIGTERM received. Shutting down application...",
                        "NOTICE: Exiting",
                        boundary,
                    ] + fresh_events

                    with patch.object(
                        status_service,
                        "svxlink_status",
                        return_value="active",
                    ), patch.object(
                        status_service,
                        "read_recent_svxlink_log_lines",
                        return_value=lines,
                    ):
                        state = status_service.get_radio_state(port)

                    self.assertEqual(state["rx"], expected_rx)
                    self.assertEqual(state["tx"], expected_tx)
                    self.assertEqual(
                        state["label"],
                        "Transmitting" if expected_tx else
                        "Receiving" if expected_rx else "Listening",
                    )
                    if not fresh_events:
                        self.assertEqual(state["input"], "Unknown")

    def test_stopped_service_ignores_stale_radio_events(self):
        for service_state in ("inactive", "failed", "unknown"):
            for port in ("1", "2"):
                with self.subTest(service_state=service_state, port=port):
                    with patch.object(
                        status_service,
                        "svxlink_status",
                        return_value=service_state,
                    ), patch.object(
                        status_service,
                        "read_recent_svxlink_log_lines",
                        return_value=[
                            f"Rx{port}: The squelch is open",
                            f"Tx{port}: Turning the transmitter on",
                        ],
                    ) as log_mock:
                        state = status_service.get_radio_state(
                            selected_port=port
                        )

                    self.assertEqual(state["label"], "Stopped")
                    self.assertEqual(state["input"], "Unknown")
                    self.assertEqual(state["class"], "radio-standby")
                    self.assertFalse(state["rx"])
                    self.assertFalse(state["tx"])
                    log_mock.assert_not_called()

    def test_talkgroup_state_uses_rotation_aware_log_reader(self):

        lines = [
            "ReflectorLogic: Selecting TG #235",
            "Unrelated event after log rotation",
        ]

        with patch.object(
            status_service,
            "read_recent_svxlink_log_lines",
            return_value=lines,
        ) as log_mock:
            talkgroup = status_service.get_active_talkgroup()

        self.assertEqual(talkgroup, "235")
        log_mock.assert_called_once_with(1000)


if __name__ == "__main__":
    unittest.main()
