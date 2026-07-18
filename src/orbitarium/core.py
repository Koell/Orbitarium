import math
import warnings

from . import frames, kepler, lunar, timebase
from .data.celestial_data import CELESTIAL_DATA
from .data.elements import AU_KM, GM_SUN_KM3_S2, PLANET_ELEMENTS
from .data.satellites import SATELLITE_ELEMENTS

# State of a body at the origin of its own frame (the tree root).
_ORIGIN_STATE = {
    "x": 0.0, "y": 0.0, "z": 0.0, "r": 0.0,
    "vx": 0.0, "vy": 0.0, "vz": 0.0,
    "lon": 0.0, "lat": 0.0,
}

# Per-body quantities in the feature vector, in order. Time-varying state
# only: physical constants (mass, radius, GM) are catalog-only and never
# appear in the vector.
_FEATURE_QUANTITIES = ("x", "y", "z", "r", "vx", "vy", "vz", "lon", "lat")


def _depth_first_names(orbitals):
    for body in orbitals:
        yield body["name"]
        yield from _depth_first_names(body["orbitals"])


# Feature ordering is a public contract (see Orbitarium.feature_names):
# catalog depth-first body order x _FEATURE_QUANTITIES per body. The sun
# contributes no features (it sits at the origin of its own frame).
_FEATURE_BODIES = tuple(_depth_first_names(CELESTIAL_DATA["sol"]["orbitals"]))
_FEATURE_NAMES = tuple(
    f"{body}.{quantity}"
    for body in _FEATURE_BODIES
    for quantity in _FEATURE_QUANTITIES
)


class Orbitarium:
    def __init__(self):
        self.celestial_data = CELESTIAL_DATA

    def get_positions(self, date, max_range=None):
        """Return the state tree for all bodies at the given timestamp.

        Every body carries x, y, z, r (km), vx, vy, vz (km/s) and
        lon, lat (degrees) in the parent-centered ecliptic-J2000 frame.
        """
        if max_range is not None:
            warnings.warn(
                "max_range is deprecated and ignored; positions are physical"
                " angles in degrees",
                DeprecationWarning,
                stacklevel=2,
            )
        moment = timebase.parse_timestamp(date)
        centuries = timebase.julian_centuries(moment)
        children = self._calculate_children(
            self.celestial_data["sol"]["orbitals"], centuries
        )
        return {"sol": {**_ORIGIN_STATE, "orbitals": children}}

    def feature_names(self):
        """Return the name of every feature, in vector order.

        Names are dotted ``body.quantity`` pairs (e.g. ``mercury.x``,
        ``luna.lat``). Bodies follow the catalog's depth-first order;
        each body contributes x, y, z, r (km), vx, vy, vz (km/s) and
        lon, lat (degrees), in that order. The sun contributes nothing
        (it sits at the origin of its own frame), and physical constants
        (mass, radius, GM) never appear.

        The ordering is part of the public API contract from v2.0.0:
        a future minor version may only APPEND new features at the end;
        reordering or removing entries requires a major version.
        """
        return list(_FEATURE_NAMES)

    def get_feature_vector(self, date):
        """Return the flat ML feature vector for the given timestamp.

        A list of floats matching :meth:`feature_names` element for
        element (same length, same order), carrying the same values as
        the :meth:`get_positions` tree for the same timestamp. Values are
        raw physical units (km, km/s, degrees); normalization is
        explicitly the consumer's responsibility. Output is deterministic
        for a given timestamp.
        """
        tree = self.get_positions(date)
        states = {}

        def collect(orbitals):
            for name, state in orbitals.items():
                states[name] = state
                collect(state["orbitals"])

        collect(tree["sol"]["orbitals"])
        return [
            states[body][quantity]
            for body in _FEATURE_BODIES
            for quantity in _FEATURE_QUANTITIES
        ]

    def _calculate_children(self, orbitals, centuries):
        states = {}
        for body in orbitals:
            name = body["name"]
            if name == "luna":
                state = _state_fields(*lunar.geocentric_state(centuries))
            elif name in PLANET_ELEMENTS:
                state = _planet_state(PLANET_ELEMENTS[name], centuries)
            else:
                state = _moon_state(SATELLITE_ELEMENTS[name], centuries)
            state["orbitals"] = self._calculate_children(
                body["orbitals"], centuries
            )
            states[name] = state
        return states


def _state_fields(position, velocity):
    x, y, z = position
    r = math.sqrt(x * x + y * y + z * z)
    return {
        "x": x, "y": y, "z": z, "r": r,
        "vx": velocity[0], "vy": velocity[1], "vz": velocity[2],
        "lon": math.degrees(math.atan2(y, x)) % 360.0,
        "lat": math.degrees(math.asin(z / r)),
    }


def _planet_state(elements, centuries):
    a = (elements["a_au"] + elements["a_au_per_cy"] * centuries) * AU_KM
    e = elements["e"] + elements["e_per_cy"] * centuries
    inclination = elements["i_deg"] + elements["i_deg_per_cy"] * centuries
    mean_longitude = (
        elements["mean_longitude_deg"]
        + elements["mean_longitude_deg_per_cy"] * centuries
    )
    longitude_periapsis = (
        elements["longitude_periapsis_deg"]
        + elements["longitude_periapsis_deg_per_cy"] * centuries
    )
    node = (
        elements["longitude_node_deg"]
        + elements["longitude_node_deg_per_cy"] * centuries
    )

    state = kepler.elements_to_state(
        a,
        e,
        math.radians(inclination),
        math.radians(node),
        math.radians(longitude_periapsis - node),
        math.radians(mean_longitude - longitude_periapsis),
        GM_SUN_KM3_S2,
    )
    return _state_fields(*state)


def _moon_state(elements, centuries):
    """Propagate a precessing-ellipse satellite fit (see data.satellites).

    The ellipse is solved in the moon's reference-plane frame (Laplace
    plane or parent equator) with signed nodal/apsidal precession rates,
    then rotated into the parent-centered ecliptic-J2000 frame. Precession
    contributions to velocity (< 0.1% here) are neglected. Mimas carries
    an additional mean-longitude libration term (Mimas-Tethys resonance).
    """
    days = (
        centuries * timebase.DAYS_PER_CENTURY
        + (timebase.J2000_JD - elements["epoch_jd"])
    )

    mean_anomaly = (
        elements["mean_anomaly_deg"]
        + elements["mean_motion_deg_per_day"] * days
    )
    if "mean_motion_rate_deg_per_day2" in elements:
        # Secular acceleration (tidal decay; Phobos), quadratic in time.
        mean_anomaly += (
            0.5 * elements["mean_motion_rate_deg_per_day2"] * days * days
        )
    if "libration_period_days" in elements:
        phase = math.tau * days / elements["libration_period_days"]
        mean_anomaly += (
            elements["libration_sin_deg"] * math.sin(phase)
            + elements["libration_cos_deg"] * math.cos(phase)
            + elements["libration_sin2_deg"] * math.sin(2.0 * phase)
            + elements["libration_cos2_deg"] * math.cos(2.0 * phase)
        )
    if "libration2_period_days" in elements:
        # Second, independent libration (the small Mimas-resonant moons
        # also ride Mimas's 71.8-yr resonance cycle; see data.satellites).
        phase = math.tau * days / elements["libration2_period_days"]
        mean_anomaly += (
            elements["libration2_sin_deg"] * math.sin(phase)
            + elements["libration2_cos_deg"] * math.cos(phase)
        )
    node = elements["node_deg"] + elements["node_rate_deg_per_day"] * days
    arg_periapsis = (
        elements["arg_periapsis_deg"]
        + elements["arg_periapsis_rate_deg_per_day"] * days
    )

    a = elements["a_km"]
    mean_motion = (
        math.radians(elements["mean_motion_deg_per_day"])
        / timebase.SECONDS_PER_DAY
    )
    mu = mean_motion * mean_motion * a**3

    position, velocity = kepler.elements_to_state(
        a,
        elements["e"],
        math.radians(elements["i_deg"]),
        math.radians(node),
        math.radians(arg_periapsis),
        math.radians(mean_anomaly),
        mu,
    )
    pole_ra, pole_dec = elements["pole_ra_deg"], elements["pole_dec_deg"]
    position = frames.plane_to_ecliptic(pole_ra, pole_dec, position)
    velocity = frames.plane_to_ecliptic(pole_ra, pole_dec, velocity)

    correction = elements.get("barycenter_correction")
    if correction:
        # The ellipse describes barycentric motion; shift to parent-centric
        # by adding the parent's wobble, factor * sibling's state.
        sibling = _moon_state(
            SATELLITE_ELEMENTS[correction["sibling"]], centuries
        )
        factor = correction["factor"]
        position = tuple(
            c + factor * s
            for c, s in zip(position, (sibling["x"], sibling["y"], sibling["z"]))
        )
        velocity = tuple(
            c + factor * s
            for c, s in zip(velocity, (sibling["vx"], sibling["vy"], sibling["vz"]))
        )
    return _state_fields(position, velocity)
