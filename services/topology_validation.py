"""Read-only topology membership and per-port workflow validation.

Generated section names and workflow integration remain to be completed.
"""

import re

from models.node_model import (
    validate_model,
    validate_squelch_configuration,
    validate_tetra_configuration,
    validate_tetra_interface,
)
from services.topology_ports import get_topology_ports


PORT_CONFIGURATION_STEPS = (
    ("node_details_configured", "node details", "port_node_page", True),
    ("squelch_configured", "squelch", "port_squelch_detail_page", True),
    ("ident_configured", "identification", "port_ident_page", False),
    ("cw_configured", "CW settings", "port_cw_page", False),
    ("repeater_configured", "repeater settings", "port_repeater_page", False),
)


def validate_local_link_name(name, reflector_name="LinkToReflector"):
    """Apply the guided dashboard naming subset and reserve managed sections."""
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name):
        return "Use a letter followed by letters, digits, underscores or hyphens for a local-link name."
    reserved = {"GLOBAL", "SimplexLogic", "RepeaterLogic", "ReflectorLogic",
                "LinkToReflector", "LocationInfo", "Macros"}
    if (name in reserved or name == reflector_name or name.startswith("Module")
            or re.fullmatch(r"(?:Rx|Tx)[0-9]+|Port[0-9]+Logic", name)):
        return "Local-link name {} is reserved for another configuration section.".format(name)
    return None


def get_incomplete_topology_ports(model):
    """Describe unfinished enabled ports with Flask endpoint/argument metadata.

    Match the existing per-port final review flags, including the repeater
    stage's explicit completion flag for simplex ports. These flags indicate
    workflow completion, not full validation of every radio parameter.
    """
    try:
        resolved = get_topology_ports(model)
    except ValueError:
        resolved = {}
    if len(resolved) == 1 and next(iter(resolved.values())) in ("SimplexLogic", "RepeaterLogic"):
        port_id = next(iter(resolved))
        # Ordinary radios use top-level configuration, not nodes/ICS flags.
        # Reuse the current model checks; this does not prove hardware readiness.
        return [{
            "port_id": port_id,
            "missing": "model_validation",
            "message": "Port {} configuration: {}".format(port_id, message),
            "endpoint": "review_page",
            "values": {},
        } for message in validate_model(model)]

    ports = model.get("ports", {})
    enabled = ports.get("enabled", []) if isinstance(ports, dict) else []
    nodes = model.get("nodes", {})
    if not isinstance(enabled, list):
        return []
    if not isinstance(nodes, dict):
        nodes = {}
    incomplete = []
    seen = set()
    for port_id in enabled:
        if not isinstance(port_id, str) or not port_id or port_id in seen:
            continue
        seen.add(port_id)
        node = nodes.get(port_id, {})
        if not isinstance(node, dict):
            node = {}

        if node.get("role") == "tetra":
            callsign = node.get("callsign")
            if (
                not node.get("node_details_configured")
                or not isinstance(callsign, str)
                or not callsign.strip()
            ):
                incomplete.append({
                    "port_id": port_id,
                    "missing": "node_details_configured",
                    "message": f"Port {port_id}: complete TETRA identity.",
                    "endpoint": "node_page" if enabled == ["1"] else "port_node_page",
                    "values": {} if enabled == ["1"] else {"port_id": port_id},
                })

            tetra = node.get("tetra", {})
            tetra_errors = validate_tetra_configuration(
                tetra,
                label=f"Port {port_id} TETRA",
            )
            if (
                not isinstance(tetra, dict)
                or tetra.get("configured") is not True
            ):
                tetra_errors.append(
                    f"Port {port_id}: save the TETRA connection settings."
                )

            for message in tetra_errors:
                incomplete.append({
                    "port_id": port_id,
                    "missing": "tetra_configuration",
                    "message": message,
                    "endpoint": "port_tetra_page",
                    "values": {"port_id": port_id},
                })

            for message in validate_tetra_interface(
                node,
                label=f"Port {port_id} TETRA",
            ):
                incomplete.append({
                    "port_id": port_id,
                    "missing": "tetra_interface",
                    "message": message,
                    "endpoint": "tetra_interface_page",
                    "values": {"port_id": port_id},
                })

            continue

        for flag, label, endpoint, per_port in PORT_CONFIGURATION_STEPS:
            complete = bool(node.get(flag))
            if flag == "node_details_configured":
                callsign = node.get("callsign")
                complete = (
                    complete
                    and node.get("role") in (
                        "simplex",
                        "repeater",
                    )
                    and isinstance(callsign, str)
                    and bool(callsign.strip())
                )

            elif (
                flag == "squelch_configured"
                and complete
            ):
                squelch_errors = (
                    validate_squelch_configuration(
                        node.get("squelch", {}),
                        f"Port {port_id} squelch",
                    )
                )

                for message in squelch_errors:
                    incomplete.append({
                        "port_id": port_id,
                        "missing": "squelch_configuration",
                        "message": message,
                        "endpoint": (
                            "port_squelch_detail_page"
                        ),
                        "values": {
                            "port_id": port_id,
                        },
                    })

                continue

            if not complete:
                incomplete.append({
                    "port_id": port_id,
                    "missing": flag,
                    "message": "Port {}: complete {} before using topology.".format(port_id, label),
                    "endpoint": endpoint if node else "port_config_page",
                    "values": {"port_id": port_id} if per_port and node else {},
                })
    return incomplete


def validate_topology(model):
    """Combine membership and port-completion errors for future UI integration."""
    return validate_topology_membership(model) + [
        issue["message"] for issue in get_incomplete_topology_ports(model)
    ]


def validate_topology_membership(model):
    """Return actionable membership errors without modifying the model."""
    errors = []
    ports = model.get("ports", {})
    enabled = ports.get("enabled") if isinstance(ports, dict) else None
    implicit_single = False
    if "ports" not in model:
        try:
            enabled = list(get_topology_ports(model))
            implicit_single = True
        except ValueError:
            pass
    if not isinstance(enabled, list) or not enabled:
        return ["Topology requires an explicit non-empty enabled-port list."]
    if any(not isinstance(port, str) or not port for port in enabled):
        return ["Enabled topology port IDs must be non-empty strings."]
    if len(set(enabled)) != len(enabled):
        errors.append("The enabled-port list contains duplicate port IDs.")

    topology = model.get("topology")
    if not isinstance(topology, dict):
        return errors + ["Topology configuration is required."]
    memberships = {port: [] for port in enabled}

    def check_members(members, label):
        if not isinstance(members, list):
            errors.append("{} must contain a port list.".format(label))
            return set()
        seen = set()
        valid = set()
        for port in members:
            if not isinstance(port, str) or not port:
                errors.append("{} contains an invalid port ID.".format(label))
                continue
            if port in seen:
                errors.append("Port {} appears more than once in {}.".format(port, label))
                continue
            seen.add(port)
            if port not in memberships:
                errors.append("Port {} in {} is disabled or removed.".format(port, label))
                continue
            memberships[port].append(label)
            valid.add(port)
        return valid

    reflector = model.get("reflector", {})
    reflector_enabled = isinstance(reflector, dict) and bool(reflector.get("enabled"))
    reflector_link = topology.get("reflector_link")
    reflector_members = set()
    if not isinstance(reflector_link, dict):
        errors.append("Reflector link configuration is required.")
    else:
        reflector_members = check_members(reflector_link.get("ports"), "reflector link")
        if not reflector_enabled and reflector_link.get("ports"):
            errors.append("Remove reflector link memberships while reflector operation is disabled.")

    if reflector_enabled:
        installation = model.get("installation", {})
        primary = installation.get("primary_port_id") if isinstance(installation, dict) else None
        if primary is None and len(memberships) == 1:
            primary = next(iter(memberships))
        if not isinstance(primary, str) or primary not in memberships:
            errors.append("Select an enabled primary port for the reflector link.")
        elif primary not in reflector_members:
            errors.append("Primary port {} must join the reflector link.".format(primary))

    local_links = topology.get("local_links")
    if not isinstance(local_links, list):
        errors.append("Local links must be a list.")
    else:
        names = set()
        for index, link in enumerate(local_links, 1):
            label = "local link {}".format(index)
            if not isinstance(link, dict):
                errors.append("{} must be a link object.".format(label))
                continue
            name = link.get("name")
            if not isinstance(name, str) or not name.strip():
                errors.append("{} needs a name.".format(label))
            else:
                label += " ({})".format(name)
                reflector_name = (reflector_link.get("name")
                                  if isinstance(reflector_link, dict) else "LinkToReflector")
                name_error = validate_local_link_name(name, reflector_name)
                if name_error:
                    errors.append("{}: {}".format(label, name_error))
                if name in names:
                    errors.append("Local-link name {} is used more than once.".format(name))
                names.add(name)
            members = check_members(link.get("ports"), label)
            if len(members) < 2:
                errors.append("{} needs at least two distinct enabled ports.".format(label))

    check_members(topology.get("independent_ports"), "independent operation")
    for port, assignments in memberships.items():
        if not assignments:
            errors.append("Port {} needs a reflector, local-link or independent assignment.".format(port))
        elif len(assignments) > 1:
            errors.append("Port {} has conflicting assignments: {}.".format(port, ", ".join(assignments)))
    return errors
