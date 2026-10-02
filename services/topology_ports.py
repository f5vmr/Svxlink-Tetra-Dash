"""Resolve topology radio identities without changing saved model structure."""


from models.node_model import has_tetra_port


def get_port_logic_name(port_id, node):
    """Return the logic name for a radio stored in the per-port model."""
    if node.get("role") == "tetra":
        return (
            "TetraLogic"
            if str(port_id) == "1"
            else f"TetraLogic{port_id}"
        )

    return f"Port{port_id}Logic"


def get_topology_ports(model):
    """Return port ID -> logic name for established renderer configurations.

    An ordinary single radio uses virtual ID '1' when no hardware-port list
    exists. This does not create nodes, choose memberships or change rendering.
    Raise ValueError for ambiguous or unfinished configurations.
    """
    hardware = model.get("hardware", {})
    profile_id = (model.get("hardware_profile_id") or hardware.get("profile_id")
                  or hardware.get("id") or hardware.get("profile") or "")
    is_ics = hardware.get("family") == "ics" or str(profile_id).startswith("ics_")
    ports = model.get("ports", {})
    enabled = ports.get("enabled") if isinstance(ports, dict) else None
    if enabled is None and not is_ics and "ports" not in model:
        enabled = ["1"]
    if not isinstance(enabled, list) or not enabled:
        raise ValueError("Select at least one enabled radio port.")
    if any(not isinstance(port, str) or not port for port in enabled):
        raise ValueError("Radio-port IDs must be non-empty strings.")
    if len(set(enabled)) != len(enabled):
        raise ValueError("Enabled radio-port IDs must be unique.")
    if is_ics or len(enabled) > 1 or has_tetra_port(model):
        nodes = model.get("nodes", {})
        return {
            port: get_port_logic_name(
                port,
                nodes.get(port, {}),
            )
            for port in enabled
        }

    role = model.get("node", {}).get("type")
    if role not in ("simplex", "repeater"):
        raise ValueError("Select the single radio's simplex or repeater role.")
    return {enabled[0]: "RepeaterLogic" if role == "repeater" else "SimplexLogic"}


def get_topology_logic_name(model, port_id):
    """Resolve an enabled port; never silently substitute another port."""
    ports = get_topology_ports(model)
    if not isinstance(port_id, str) or port_id not in ports:
        raise ValueError("Port {!r} is not an enabled topology port.".format(port_id))
    return ports[port_id]


def get_topology_memberships(model):
    """
    Return every saved topology assignment for each enabled port.

    Multiple entries are retained so conflicting assignments remain
    visible to the topology page and validator.
    """

    topology_ports = get_topology_ports(model)

    memberships = {
        port_id: []
        for port_id in topology_ports
    }

    topology = model.get("topology", {})

    if not isinstance(topology, dict):
        return memberships

    def add_members(members, label):
        if not isinstance(members, list):
            return

        for member in members:
            port_id = str(member)

            if port_id in memberships:
                memberships[port_id].append(label)

    reflector_link = topology.get(
        "reflector_link",
        {},
    )

    if isinstance(reflector_link, dict):
        reflector_name = str(
            reflector_link.get("name")
            or "LinkToReflector"
        )

        add_members(
            reflector_link.get("ports"),
            reflector_name,
        )

    local_links = topology.get("local_links", [])

    if isinstance(local_links, list):
        for link in local_links:
            if not isinstance(link, dict):
                continue

            link_name = str(
                link.get("name")
                or "Unnamed local link"
            )

            add_members(
                link.get("ports"),
                link_name,
            )

    add_members(
        topology.get("independent_ports"),
        "Independent operation",
    )

    return memberships