#!/usr/bin/env python3

"""
Node model persistence for SvxLink Dashboard V4.1.
"""

import json
from pathlib import Path
from copy import deepcopy
from models.node_model import DEFAULT_MODEL, new_node_model
from hw_platforms import get_platform_profile
from services.svxlink_config_discovery import discover_macros


APP_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = APP_ROOT / "config"
MODEL_FILE = CONFIG_DIR / "node_model.json"
FEDERATION_HOST_IDS = {
    "north.america.svxlink.net": "north_america",
    "uk.wide.svxlink.uk": "ukwide",
    "australia.svxlink.net": "australia_nz",
    "yorkshire.svxlink.uk": "yorkshire",
}
CTCSS_TONES = [
    ("", "None / disabled"),
    ("67.0", "67.0 Hz"),
    ("69.3", "69.3 Hz"),
    ("71.9", "71.9 Hz"),
    ("74.4", "74.4 Hz"),
    ("77.0", "77.0 Hz"),
    ("79.7", "79.7 Hz"),
    ("82.5", "82.5 Hz"),
    ("85.4", "85.4 Hz"),
    ("88.5", "88.5 Hz"),
    ("91.5", "91.5 Hz"),
    ("94.8", "94.8 Hz"),
    ("97.4", "97.4 Hz"),
    ("100.0", "100.0 Hz"),
    ("103.5", "103.5 Hz"),
    ("107.2", "107.2 Hz"),
    ("110.9", "110.9 Hz"),
    ("114.8", "114.8 Hz"),
    ("118.8", "118.8 Hz"),
    ("123.0", "123.0 Hz"),
    ("127.3", "127.3 Hz"),
    ("131.8", "131.8 Hz"),
    ("136.5", "136.5 Hz"),
    ("141.3", "141.3 Hz"),
    ("146.2", "146.2 Hz"),
    ("151.4", "151.4 Hz"),
    ("156.7", "156.7 Hz"),
    ("159.8", "159.8 Hz"),
    ("162.2", "162.2 Hz"),
    ("165.5", "165.5 Hz"),
    ("167.9", "167.9 Hz"),
    ("171.3", "171.3 Hz"),
    ("173.8", "173.8 Hz"),
    ("177.3", "177.3 Hz"),
    ("179.9", "179.9 Hz"),
    ("183.5", "183.5 Hz"),
    ("186.2", "186.2 Hz"),
    ("189.9", "189.9 Hz"),
    ("192.8", "192.8 Hz"),
    ("196.6", "196.6 Hz"),
    ("199.5", "199.5 Hz"),
    ("203.5", "203.5 Hz"),
    ("206.5", "206.5 Hz"),
    ("210.7", "210.7 Hz"),
    ("218.1", "218.1 Hz"),
    ("225.7", "225.7 Hz"),
    ("229.1", "229.1 Hz"),
    ("233.6", "233.6 Hz"),
    ("241.8", "241.8 Hz"),
    ("250.3", "250.3 Hz"),
    ("254.1", "254.1 Hz"),
]


def normalise_ctcss_tone(value):
    value = str(value or "").strip()

    valid_values = {
        tone_value
        for tone_value, _label in CTCSS_TONES
    }

    if value in valid_values:
        return value

    return ""


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def create_default_model():
    platform = get_platform_profile()
    return new_node_model(platform=platform)


def merge_missing_defaults(model, defaults=None):
    """
    Add missing default values without replacing saved configuration.

    Returns True when the model was changed.
    """

    if defaults is None:
        defaults = DEFAULT_MODEL

    changed = False

    for key, default_value in defaults.items():
        if key not in model:
            model[key] = deepcopy(default_value)
            changed = True
            continue

        saved_value = model[key]

        if isinstance(saved_value, dict) and isinstance(default_value, dict):
            if merge_missing_defaults(saved_value, default_value):
                changed = True

    return changed


def normalise_port_ids(model):
    """Convert integer radio-port references to strings without changing membership.

    Leave malformed values for validation; this is not topology cleanup.
    JSON object keys (including nodes and port_roles) are already strings.
    """
    changed = False

    def normalise_field(container, key):
        nonlocal changed
        if not isinstance(container, dict):
            return
        value = container.get(key)
        if isinstance(value, list):
            normalised = [str(item) if type(item) is int else item for item in value]
        elif type(value) is int:
            normalised = str(value)
        else:
            return
        if normalised != value:
            container[key] = normalised
            changed = True

    ports = model.get("ports", {})
    normalise_field(ports, "available")
    normalise_field(ports, "enabled")
    normalise_field(model.get("installation", {}), "primary_port_id")

    topology = model.get("topology", {})
    if isinstance(topology, dict):
        normalise_field(topology.get("reflector_link", {}), "ports")
        normalise_field(topology, "independent_ports")
        local_links = topology.get("local_links", [])
        if isinstance(local_links, list):
            for link in local_links:
                normalise_field(link, "ports")

    return changed


def clean_stale_topology_ports(model):
    """Remove disabled port references when an explicit enabled list exists.

    Retain link definitions, ordering, duplicates and malformed values for
    topology validation. Missing port selection is not an empty selection.
    """
    ports = model.get("ports", {})
    if not isinstance(ports, dict) or not isinstance(ports.get("enabled"), list):
        return False
    enabled = [str(port) for port in ports["enabled"]
               if isinstance(port, str) or type(port) is int]
    topology = model.get("topology", {})
    if not isinstance(topology, dict):
        return False
    changed = False

    def clean_members(container, key):
        nonlocal changed
        if not isinstance(container, dict):
            return
        members = container.get(key)
        if not isinstance(members, list):
            return
        retained = [port for port in members
                    if not (isinstance(port, str) or type(port) is int)
                    or str(port) in enabled]
        if retained != members:
            container[key] = retained
            changed = True

    clean_members(topology.get("reflector_link", {}), "ports")
    clean_members(topology, "independent_ports")
    local_links = topology.get("local_links", [])
    if isinstance(local_links, list):
        for link in local_links:
            clean_members(link, "ports")
    return changed


def migrate_reflector_operational(model):
    """
    Consolidate historical reflector talkgroup settings into the
    installation-wide operational block.

    Existing operational values take precedence. Legacy flat values
    are preferred over old route-specific copies because the runtime
    dashboard historically updated the flat fields.
    """

    reflector = model.get("reflector")

    if not isinstance(reflector, dict):
        return False

    before = deepcopy(
        reflector.get("operational")
    )

    operational = reflector.get("operational")

    if not isinstance(operational, dict):
        operational = {}

    route = str(
        reflector.get("route") or ""
    ).strip().lower()

    route_settings = reflector.get(route, {})

    if not isinstance(route_settings, dict):
        route_settings = {}

    if "default_tg" not in operational:
        if "default_tg" in reflector:
            operational["default_tg"] = deepcopy(
                reflector["default_tg"]
            )
        elif "default_tg" in route_settings:
            operational["default_tg"] = deepcopy(
                route_settings["default_tg"]
            )
        else:
            operational["default_tg"] = 0

    if "monitor_tgs" not in operational:
        if "monitor_tgs" in reflector:
            monitor_tgs = deepcopy(
                reflector["monitor_tgs"]
            )
        elif "monitor_tgs" in route_settings:
            monitor_tgs = deepcopy(
                route_settings["monitor_tgs"]
            )
        else:
            monitor_tgs = []

        operational["monitor_tgs"] = monitor_tgs

    monitor_tgs = operational.get(
        "monitor_tgs"
    )

    if isinstance(monitor_tgs, list):
        operational["monitor_tgs"] = [
            str(talkgroup).strip()
            for talkgroup in monitor_tgs
            if str(talkgroup).strip()
        ]

    elif isinstance(monitor_tgs, str):
        operational["monitor_tgs"] = [
            talkgroup.strip()
            for talkgroup in monitor_tgs.split(",")
            if talkgroup.strip()
        ]

    if "tg_select_timeout" not in operational:
        if "tg_select_timeout" in reflector:
            operational["tg_select_timeout"] = deepcopy(
                reflector["tg_select_timeout"]
            )
        elif "tg_timeout" in model:
            operational["tg_select_timeout"] = deepcopy(
                model["tg_timeout"]
            )
        else:
            operational["tg_select_timeout"] = 60

    reflector["operational"] = operational

    return before != operational


def migrate_node_info_publication(model):
    """
    Preserve the historical combined publication choice.

    Models saved before node_info and LocationInfo were separated used
    location_info.enabled to control both generated outputs.
    """
    node_info = model.get("node_info")

    if node_info is None:
        node_info = {}
        model["node_info"] = node_info
    elif not isinstance(node_info, dict):
        return False

    if "enabled" in node_info:
        return False

    location_info = model.get("location_info", {})
    node_info["enabled"] = bool(
        isinstance(location_info, dict)
        and location_info.get("enabled")
    )
    return True


def migrate_node_model(model):
    """
    Migrate an existing saved model to the current schema.

    Existing values are retained. Legacy fields remain available until
    all renderers and configuration pages have moved to schema version 2.
    """

    try:
        schema_version = int(model.get("schema_version", 1))
    except (TypeError, ValueError):
        schema_version = 1

    node_info_changed = migrate_node_info_publication(
        model
    )

    operational_changed = (
        migrate_reflector_operational(model)
    )

    if schema_version >= 2:
        changed = (
            operational_changed
            or node_info_changed
        )
        changed = (
            merge_missing_defaults(model)
            or changed
        )
        changed = (
            normalise_port_ids(model)
            or changed
        )
        changed = (
            clean_stale_topology_ports(model)
            or changed
        )
        return changed

    saved_model = deepcopy(model)
    legacy_reflector = deepcopy(model.get("reflector", {}))
    legacy_courtesy = deepcopy(model.get("courtesy", {}))
    legacy_repeater = deepcopy(model.get("repeater", {}))

    enabled_ports = [
        str(port)
        for port in model.get("ports", {}).get("enabled", [])
    ]

    nodes = model.get("nodes", {})
    hardware = model.get("hardware", {})

    is_multiport = (
        hardware.get("family") == "ics"
        or len(enabled_ports) > 1
    )

    port_courtesy = {}

    if is_multiport and enabled_ports:
        first_node = nodes.get(enabled_ports[0], {})
        port_courtesy = deepcopy(first_node.get("courtesy", {}))

    merge_missing_defaults(model)

    if is_multiport and enabled_ports:
        model["installation"]["primary_port_id"] = enabled_ports[0]

    courtesy_source = port_courtesy or legacy_courtesy

    courtesy_mode = courtesy_source.get(
        "mode",
        model["tones"]["courtesy_mode"],
    )

    courtesy_frequency = courtesy_source.get(
        "frequency",
        legacy_courtesy.get(
            "frequency",
            model["tones"]["courtesy_frequency"],
        ),
    )

    idle_mode = courtesy_source.get(
        "idle_tone",
        legacy_repeater.get(
            "idle_tone",
            model["tones"]["idle_mode"],
        ),
    )

    closedown_mode = courtesy_source.get(
        "down_tone",
        legacy_repeater.get(
            "down_tone",
            model["tones"]["closedown_mode"],
        ),
    )

    if idle_mode == "none":
        idle_mode = "silence"

    model["tones"] = {
        "courtesy_mode": courtesy_mode,
        "courtesy_frequency": courtesy_frequency,
        "idle_mode": idle_mode,
        "closedown_mode": closedown_mode,
    }

    model.setdefault("build", {})
    model["build"]["tones_configured"] = True

    reflector_enabled = bool(
        legacy_reflector.get("enabled")
    )

    model["reflector"]["enabled"] = reflector_enabled

    if reflector_enabled:
        legacy_host = str(
            legacy_reflector.get("host") or ""
        ).strip()

        federation_id = FEDERATION_HOST_IDS.get(legacy_host)

        if federation_id:
            model["reflector"]["route"] = "federation"
            model["reflector"]["federation"]["network_id"] = federation_id
            model["reflector"]["federation"]["auth_key"] = (
                legacy_reflector.get("auth_key")
            )
        else:
            model["reflector"]["route"] = "v2"
            model["reflector"]["v2"].update({
                "name": legacy_reflector.get("name"),
                "host": legacy_reflector.get("host"),
                "port": legacy_reflector.get("port"),
                "auth_key": legacy_reflector.get("auth_key"),
                "default_tg": legacy_reflector.get("default_tg", 0),
                "monitor_tgs": legacy_reflector.get("monitor_tgs", []),
            })
    else:
        model["reflector"]["route"] = "none"

    if is_multiport and enabled_ports and "topology" not in saved_model:
        if reflector_enabled:
            model["topology"]["reflector_link"]["ports"] = list(
                enabled_ports
            )
            model["topology"]["independent_ports"] = []
        else:
            model["topology"]["reflector_link"]["ports"] = []
            model["topology"]["independent_ports"] = list(
                enabled_ports
            )

    # Treat migration-derived values as defaults for partially migrated models.
    # Explicit saved values (including False, zero, empty lists and extensions)
    # win over values inferred from legacy fields.
    merge_missing_defaults(saved_model, model)
    model.update(saved_model)
    model["schema_version"] = 2
    normalise_port_ids(model)
    clean_stale_topology_ports(model)

    return True


def save_node_model(model):
    normalise_port_ids(model)
    clean_stale_topology_ports(model)
    ensure_config_dir()

    MODEL_FILE.write_text(
        json.dumps(model, indent=4),
        encoding="utf-8",
    )


def load_node_model():
    ensure_config_dir()

    if not MODEL_FILE.exists() or MODEL_FILE.stat().st_size == 0:
        model = create_default_model()
        save_node_model(model)
        return model

    try:
        model = json.loads(
            MODEL_FILE.read_text(encoding="utf-8")
        )

        model_changed = migrate_node_model(model)

        if "macros" not in model:
            try:
                model["macros"] = discover_macros()
            except FileNotFoundError:
                model["macros"] = {}

            model_changed = True

        if model_changed:
            save_node_model(model)

        return model

    except json.JSONDecodeError:
        corrupt_file = MODEL_FILE.with_suffix(".json.corrupt")
        MODEL_FILE.rename(corrupt_file)

        model = create_default_model()
        save_node_model(model)
        return model


def reset_node_model():
    model = create_default_model()
    save_node_model(model)
    return model
