import unittest
from copy import deepcopy

from models.node_model import new_node_model
from services.topology_validation import (
    PORT_CONFIGURATION_STEPS,
    get_incomplete_topology_ports,
    validate_topology,
    validate_topology_membership,
)


class TopologyMembershipTests(unittest.TestCase):
    def setUp(self):
        self.model = new_node_model()
        self.model["ports"] = {"enabled": ["1", "2", "3", "4"]}
        self.model["installation"]["primary_port_id"] = "1"
        self.model["reflector"]["enabled"] = True
        self.topology = self.model["topology"]
        self.topology["reflector_link"]["ports"] = ["1"]
        self.topology["local_links"] = [{"name": "Local", "ports": ["2", "3"]}]
        self.topology["independent_ports"] = ["4"]

    def errors(self):
        return "\n".join(validate_topology_membership(self.model))

    def test_valid_mixed_topology_is_not_mutated(self):
        before = deepcopy(self.model)
        self.assertEqual(validate_topology_membership(self.model), [])
        self.assertEqual(self.model, before)

    def test_conflict_and_missing_assignment(self):
        self.topology["independent_ports"] = ["2"]
        self.assertIn("Port 2 has conflicting assignments", self.errors())
        self.assertIn("Port 4 needs", self.errors())

    def test_duplicate_does_not_satisfy_local_link_minimum(self):
        self.topology["local_links"][0]["ports"] = ["2", "2", "9"]
        errors = self.errors()
        self.assertIn("Port 2 appears more than once", errors)
        self.assertIn("Port 9", errors)
        self.assertIn("at least two distinct enabled ports", errors)

    def test_primary_must_join_reflector(self):
        self.topology["reflector_link"]["ports"] = []
        self.assertIn("Primary port 1 must join", self.errors())

    def test_disabled_reflector_requires_empty_membership(self):
        self.model["reflector"]["enabled"] = False
        self.assertIn("reflector operation is disabled", self.errors())
        self.topology["reflector_link"]["ports"] = []
        self.topology["independent_ports"].append("1")
        self.assertEqual(validate_topology_membership(self.model), [])

    def test_duplicate_names(self):
        self.topology["local_links"].append({"name": "Local", "ports": []})
        self.assertIn("name Local is used more than once", self.errors())

    def test_local_names_reject_delimiters_and_whitespace(self):
        for name in ("Local,Other", "Local]", "Local\nOther", " Local", "Local Link", "1Local"):
            with self.subTest(name=name):
                self.topology["local_links"][0]["name"] = name
                self.assertIn("Use a letter", self.errors())

    def test_local_names_cannot_collide_with_managed_sections(self):
        for name in ("GLOBAL", "Rx1", "Tx4", "Port2Logic", "SimplexLogic",
                     "ReflectorLogic", "LocationInfo", "Macros", "ModuleHelp", "LinkToReflector"):
            with self.subTest(name=name):
                self.topology["local_links"][0]["name"] = name
                self.assertIn("reserved", self.errors())
        self.topology["reflector_link"]["name"] = "CustomReflector"
        self.topology["local_links"][0]["name"] = "CustomReflector"
        self.assertIn("reserved", self.errors())

    def test_guided_local_names_are_accepted(self):
        for name in ("Local", "LocalLink_1", "Link-to-2"):
            with self.subTest(name=name):
                self.topology["local_links"][0]["name"] = name
                self.assertEqual(validate_topology_membership(self.model), [])

    def test_malformed_membership_reports_error(self):
        self.topology["local_links"][0]["ports"] = [[], None, 2]
        self.assertIn("invalid port ID", self.errors())
        self.topology["independent_ports"] = None
        self.assertIn("must contain a port list", self.errors())

    def test_single_explicit_port(self):
        self.model["ports"]["enabled"] = ["1"]
        self.topology["local_links"] = []
        self.topology["independent_ports"] = []
        self.assertEqual(validate_topology_membership(self.model), [])

    def test_single_explicit_port_is_automatic_primary(self):
        self.model["ports"]["enabled"] = ["1"]
        self.model["installation"]["primary_port_id"] = None
        self.topology["local_links"] = []
        self.topology["independent_ports"] = []

        before = deepcopy(self.model)

        self.assertEqual(
            validate_topology_membership(self.model),
            [],
        )
        self.assertEqual(self.model, before)

    def test_ordinary_single_membership_without_changing_model(self):
        for role in ("simplex", "repeater"):
            for reflector in (False, True):
                with self.subTest(role=role, reflector=reflector):
                    model = new_node_model()
                    model["node"].update(type=role, callsign="TEST")
                    model["reflector"]["enabled"] = reflector
                    topology = model["topology"]
                    if reflector:
                        topology["reflector_link"]["ports"] = ["1"]
                    else:
                        topology["independent_ports"] = ["1"]
                    before = deepcopy(model)
                    self.assertEqual(validate_topology_membership(model), [])
                    self.assertEqual(model, before)
                    topology["independent_ports"] = ["2"]
                    self.assertIn("Port 2", "\n".join(validate_topology_membership(model)))

    def test_ics_does_not_acquire_implicit_single_port(self):
        model = new_node_model()
        model["node"]["type"] = "simplex"
        model["hardware_profile_id"] = "ics_1x"
        model["topology"]["independent_ports"] = ["1"]
        self.assertTrue(validate_topology_membership(model))

    def test_missing_explicit_ports(self):
        del self.model["ports"]
        self.assertIn("explicit non-empty enabled-port list", self.errors())


class TopologyCompletionTests(unittest.TestCase):
    def setUp(self):
        self.model = new_node_model()
        self.model["ports"] = {"enabled": ["1"]}
        self.model["topology"]["independent_ports"] = ["1"]
        self.node = {
            "role": "simplex",
            "callsign": "TEST",
            "squelch": {
                "method": "gpiod",
                "combine_components": [],
                "manual_detector": None,
                "ctcss_freq": None,
                "ctcss_tx": False,
            },
        }
        self.node.update({
            flag: True
            for flag, _, _, _ in PORT_CONFIGURATION_STEPS
        })
        self.model["nodes"] = {"1": self.node}

    def test_complete_port_and_no_mutation(self):
        before = deepcopy(self.model)
        self.assertEqual(validate_topology(self.model), [])
        self.assertEqual(self.model, before)

    def test_missing_squelch_has_direct_destination(self):
        self.node["squelch_configured"] = False
        issues = get_incomplete_topology_ports(self.model)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["endpoint"], "port_squelch_detail_page")
        self.assertEqual(issues[0]["values"], {"port_id": "1"})
        self.assertIn("Port 1: complete squelch", validate_topology(self.model)[0])

    def test_invalid_completed_squelch_has_direct_destination(self):
        self.node["squelch"] = {
            "method": "gpiod",
            "advanced_example": "combine",
            "combine_components": ["vox"],
            "manual_detector": None,
            "ctcss_freq": None,
            "ctcss_tx": False,
        }

        issues = get_incomplete_topology_ports(
            self.model
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(
            issues[0]["missing"],
            "squelch_configuration",
        )
        self.assertEqual(
            issues[0]["endpoint"],
            "port_squelch_detail_page",
        )
        self.assertEqual(
            issues[0]["values"],
            {"port_id": "1"},
        )
        self.assertIn(
            "COMBINE requires at least two",
            issues[0]["message"],
        )

    def test_shared_page_destination_has_no_port_parameter(self):
        self.node["ident_configured"] = False
        issue = get_incomplete_topology_ports(self.model)[0]
        self.assertEqual(issue["endpoint"], "port_ident_page")
        self.assertEqual(issue["values"], {})

    def test_missing_node_routes_to_initialisation(self):
        self.model["nodes"] = {}
        issues = get_incomplete_topology_ports(self.model)
        self.assertEqual(len(issues), 4)
        self.assertTrue(all(issue["endpoint"] == "port_config_page" for issue in issues))

    def test_completed_flags_do_not_hide_missing_identity(self):
        for field, value in (("callsign", " "), ("role", "invalid")):
            with self.subTest(field=field):
                original = self.node[field]
                self.node[field] = value
                self.assertEqual(get_incomplete_topology_ports(self.model)[0]["missing"],
                                 "node_details_configured")
                self.node[field] = original

    def test_disabled_unfinished_port_is_ignored(self):
        self.model["nodes"]["2"] = {}
        self.assertEqual(get_incomplete_topology_ports(self.model), [])

    def test_ordinary_single_uses_top_level_validation(self):
        model = new_node_model()
        model["node"].update(type="simplex", callsign="TEST")
        model["squelch"]["method"] = "hidraw"
        model["topology"]["independent_ports"] = ["1"]
        self.assertEqual(validate_topology(model), [])
        for explicit_ports in (False, True):
            with self.subTest(explicit_ports=explicit_ports):
                if explicit_ports:
                    model["ports"] = {"enabled": ["1"]}
                model["node"]["callsign"] = ""
                issues = get_incomplete_topology_ports(model)
                self.assertTrue(any("Callsign is required" in issue["message"] for issue in issues))
                self.assertTrue(all(issue["endpoint"] == "review_page" for issue in issues))

    def test_ics_one_still_requires_per_port_flags(self):
        self.model["hardware_profile_id"] = "ics_1x"
        self.model["node"].update(type="simplex", callsign="TEST")
        self.node["squelch_configured"] = False
        issue = get_incomplete_topology_ports(self.model)[0]
        self.assertEqual(issue["missing"], "squelch_configured")
        self.assertEqual(issue["endpoint"], "port_squelch_detail_page")


if __name__ == "__main__":
    unittest.main()
