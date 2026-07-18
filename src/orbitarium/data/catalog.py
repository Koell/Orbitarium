"""Catalog integrity validation.

``validate()`` checks the whole shipped catalog -- the body tree, the
physical-properties table, and both orbital-element tables -- against the
data contract and raises ``CatalogError`` listing every violation. The test
suite calls it, so a bad or incomplete catalog entry fails CI rather than
shipping.
"""

import math

from .celestial_data import CELESTIAL_DATA
from .elements import PLANET_ELEMENTS
from .physical import PHYSICAL
from .satellites import SATELLITE_ELEMENTS

# Bodies whose GM (and therefore derived mass) JPL does not publish;
# documented as None in orbitarium.data.physical.
BODIES_WITHOUT_GM = frozenset({
    "nereid", "styx",
    # Small moons with no JPL-published GM (see data.physical docstring).
    "daphnis", "methone", "pallene", "polydeuces", "anthe", "aegaeon",
    "puck", "cordelia", "ophelia", "bianca", "cressida", "desdemona",
    "juliet", "portia", "rosalind", "belinda", "perdita", "mab", "cupid",
    "hippocamp",
})

# Luna's state comes from the Meeus lunar series (orbitarium.lunar), not
# from the satellite element table.
_MOONS_WITHOUT_ELEMENTS = frozenset({"luna"})

_BODY_TYPES = frozenset({"star", "planet", "dwarf planet", "moon"})

_SATELLITE_NUMERIC_FIELDS = (
    "a_km", "e", "i_deg", "node_deg", "node_rate_deg_per_day",
    "arg_periapsis_deg", "arg_periapsis_rate_deg_per_day",
    "mean_anomaly_deg", "mean_motion_deg_per_day",
    "pole_ra_deg", "pole_dec_deg", "epoch_jd",
)

_PLANET_NUMERIC_FIELDS = (
    "a_au", "a_au_per_cy", "e", "e_per_cy", "i_deg", "i_deg_per_cy",
    "mean_longitude_deg", "mean_longitude_deg_per_cy",
    "longitude_periapsis_deg", "longitude_periapsis_deg_per_cy",
    "longitude_node_deg", "longitude_node_deg_per_cy",
)


class CatalogError(ValueError):
    """The shipped catalog violates its data contract."""


def _walk(node, parent=None):
    yield node, parent
    for child in node["orbitals"]:
        yield from _walk(child, node)


def _is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _check_tree(problems):
    names = []
    for node, parent in _walk(CELESTIAL_DATA["sol"]):
        name = node.get("name")
        if not isinstance(name, str) or not name or name != name.lower():
            problems.append(f"tree: bad body name {name!r}")
            continue
        names.append(name)
        if node.get("type") not in _BODY_TYPES:
            problems.append(f"{name}: unknown body type {node.get('type')!r}")
        if not isinstance(node.get("orbitals"), list):
            problems.append(f"{name}: 'orbitals' must be a list")
        if parent is None and name != "sol":
            problems.append(f"{name}: root body must be 'sol'")
    if len(names) != len(set(names)):
        duplicates = {n for n in names if names.count(n) > 1}
        problems.append(f"tree: duplicate body names {sorted(duplicates)}")
    return names


def _check_physical(problems, names):
    for name in names:
        entry = PHYSICAL.get(name)
        if entry is None:
            problems.append(f"{name}: missing physical entry")
            continue
        gm, mass = entry.get("gm_km3_s2"), entry.get("mass_kg")
        if name in BODIES_WITHOUT_GM:
            if gm is not None or mass is not None:
                problems.append(
                    f"{name}: GM documented as unpublished but has a value"
                )
        else:
            if not _is_number(gm) or gm <= 0.0:
                problems.append(f"{name}: GM must be a positive number")
            if not _is_number(mass) or mass <= 0.0:
                problems.append(f"{name}: mass must be a positive number")
        radius = entry.get("radius_km")
        # Lower bound accommodates Aegaeon (~0.33 km mean radius), the
        # smallest cataloged moon.
        if not _is_number(radius) or not 0.1 < radius < 7.0e5:
            problems.append(f"{name}: radius outside physical sanity range")
        source = entry.get("source")
        if not isinstance(source, str) or not source.strip():
            problems.append(f"{name}: physical entry lacks a source")
        retrieved = entry.get("retrieved")
        if not isinstance(retrieved, str) or not retrieved.strip():
            problems.append(f"{name}: physical entry lacks a retrieval date")


def _check_planet_elements(problems, planet_names):
    for name in planet_names:
        entry = PLANET_ELEMENTS.get(name)
        if entry is None:
            problems.append(f"{name}: missing heliocentric elements")
            continue
        for field in _PLANET_NUMERIC_FIELDS:
            if not _is_number(entry.get(field)):
                problems.append(f"{name}: element {field} must be a number")
        if not 0.0 <= entry.get("e", -1.0) < 1.0:
            problems.append(f"{name}: eccentricity outside [0, 1)")
        if not isinstance(entry.get("source"), str) or not entry["source"].strip():
            problems.append(f"{name}: elements lack a source")
        if not entry.get("epoch"):
            problems.append(f"{name}: elements lack a reference epoch")


def _check_satellite_elements(problems, moons):
    for name, parent_name in moons:
        if name in _MOONS_WITHOUT_ELEMENTS:
            continue
        entry = SATELLITE_ELEMENTS.get(name)
        if entry is None:
            problems.append(f"{name}: missing satellite elements")
            continue
        for field in _SATELLITE_NUMERIC_FIELDS:
            if not _is_number(entry.get(field)):
                problems.append(f"{name}: element {field} must be a number")
        if entry.get("parent") != parent_name:
            problems.append(
                f"{name}: element parent {entry.get('parent')!r} does not"
                f" match tree parent {parent_name!r}"
            )
        if not 0.0 < entry.get("a_km", 0.0) < 1.0e8:
            problems.append(f"{name}: semi-major axis outside sanity range")
        if not 0.0 <= entry.get("e", -1.0) < 1.0:
            problems.append(f"{name}: eccentricity outside [0, 1)")
        if not 0.0 <= entry.get("i_deg", -1.0) < 180.0:
            problems.append(f"{name}: inclination outside [0, 180)")
        if entry.get("mean_motion_deg_per_day", 0.0) <= 0.0:
            problems.append(
                f"{name}: mean motion must be positive (retrograde orbits"
                " use inclination > 90 deg, never negative periods)"
            )
        if not isinstance(entry.get("source"), str) or not entry["source"].strip():
            problems.append(f"{name}: elements lack a source")
        if not entry.get("ephemeris"):
            problems.append(f"{name}: elements lack an ephemeris ID")
        fit = entry.get("fit")
        if not isinstance(fit, dict) or not _is_number(fit.get("worst_deg")):
            problems.append(f"{name}: elements lack fit statistics")


def validate():
    """Validate the shipped catalog; raise CatalogError on any violation."""
    problems = []
    names = _check_tree(problems)
    _check_physical(problems, names)

    planet_names = []
    moons = []
    for node, parent in _walk(CELESTIAL_DATA["sol"]):
        if node["type"] in ("planet", "dwarf planet"):
            planet_names.append(node["name"])
        elif node["type"] == "moon":
            moons.append((node["name"], parent["name"]))
    _check_planet_elements(problems, planet_names)
    _check_satellite_elements(problems, moons)

    if problems:
        raise CatalogError(
            "catalog integrity violations:\n  " + "\n  ".join(problems)
        )
