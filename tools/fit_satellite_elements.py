"""Fit precessing-ellipse mean elements to JPL Horizons satellite states.

Why this tool exists
--------------------
JPL's "Planetary Satellite Mean Elements" page (https://ssd.jpl.nasa.gov/
sats/elem/) warns that its tables are "not intended for ephemeris
computation", and measurement confirms it: interpreted per the page's own
legend, the published angles disagree with JPL Horizons at their stated
epoch by up to ~157 deg in mean longitude for the Saturnian satellites
(e.g. Titan's published M = 11.7 deg vs an actual mean anomaly of ~163 deg
at 2000-01-01.5 TDB) and by tens of degrees for Pluto's small moons, while
the periods of the Martian and small Plutonian moons carry too few digits
to hold orbital phase over more than a few years. No reading of the table
(epoch shifts, angle conventions, column permutations, precession signs)
resolves those inconsistencies -- see the analysis notes in
src/orbitarium/data/satellites.py.

This tool therefore builds the same kind of data product JPL describes --
"elements of a precessing ellipse which has been fit in a least squares
sense to the numerically integrated orbit" -- directly against JPL Horizons
(the numerically integrated orbits themselves), so that the fitted elements
reproduce Horizons by construction. Reference planes (Laplace-plane poles,
planet equator poles) are taken from the JPL page; only the ellipse and its
precession rates are fit.

The fit model per moon (9 parameters, all angles in the moon's reference
plane): a, e, i, node0, node_rate, argp0, argp_rate, M0, M_rate. Positions
are propagated with orbitarium's own Kepler solver, so the fit is exactly
the model the library evaluates at runtime.

Fitting runs in widening stages (~3 months -> ~20 years -> full 1900-2050
span) so the mean motion locks in without mod-360 ambiguity.

Usage:  python tools/fit_satellite_elements.py [moon ...]
        python tools/fit_satellite_elements.py --emit-module
Writes: tools/fitted_elements.json  (fitted values + fit statistics), and
with --emit-module renders src/orbitarium/data/satellites.py from it.
CI never runs this script; it is kept for reproducibility.
"""

import datetime
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from orbitarium import frames, kepler  # noqa: E402

API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
OUT_PATH = Path(__file__).resolve().parent / "fitted_elements.json"

J2000_JD = 2451545.0
SECONDS_PER_DAY = 86400.0

# Ecliptic north pole in ICRF equatorial coordinates (for ecliptic-referred
# reference planes the reference plane IS the output frame).
ECLIPTIC_POLE = (270.0, 90.0 - frames.OBLIQUITY_J2000_DEG)

# Reference-plane poles (ICRF RA/Dec, deg), from the JPL mean-elements page.
# Uranus and Pluto satellites are referred to the planet's equatorial plane;
# the pole that makes the published near-zero inclinations prograde is the
# right-hand-rule spin pole. For Uranus that is the ANTI-pole of the IAU
# (pck00011) direction -- the JPL page itself lists the outer-Uranian
# Laplace pole as (77.3, +15.2) with tilt 180 deg, confirming the flip.
POLES = {
    "phobos": (317.7, 52.9), "deimos": (316.6, 53.5),
    "io": (268.1, 64.5), "europa": (268.1, 64.5), "ganymede": (268.2, 64.6),
    "callisto": (268.7, 64.8), "amalthea": (268.1, 64.5),
    "thebe": (268.1, 64.5), "adrastea": (268.1, 64.5), "metis": (268.1, 64.5),
    "mimas": (40.6, 83.5), "enceladus": (40.6, 83.5), "rhea": (40.6, 83.5),
    "titan": (36.4, 84.0), "iapetus": (288.7, 78.9),
    "tethys": (40.6, 83.5), "dione": (40.6, 83.5),
    "hyperion": (40.2, 83.6), "phoebe": (276.0, 67.5),
    "janus": (40.6, 83.5), "epimetheus": (40.6, 83.5),
    "helene": (40.6, 83.5), "telesto": (40.6, 83.5), "calypso": (40.6, 83.5),
    "atlas": (40.6, 83.5), "prometheus": (40.6, 83.5), "pandora": (40.6, 83.5),
    "pan": (40.6, 83.5), "daphnis": (40.6, 83.5), "methone": (40.6, 83.5),
    "pallene": (40.6, 83.5), "polydeuces": (40.6, 83.5),
    "anthe": (40.6, 83.5), "aegaeon": (40.6, 83.5),
    "ariel": (77.311, 15.175), "umbriel": (77.311, 15.175),
    "titania": (77.311, 15.175), "oberon": (77.311, 15.175),
    "miranda": (77.311, 15.175), "puck": (77.311, 15.175),
    # URA184 inner belt: the page lists their Laplace pole directly as
    # (77.3, +15.2) with tilt 180 deg to the (IAU) equator.
    "cordelia": (77.3, 15.2), "ophelia": (77.3, 15.2), "bianca": (77.3, 15.2),
    "cressida": (77.3, 15.2), "desdemona": (77.3, 15.2),
    "juliet": (77.3, 15.2), "portia": (77.3, 15.2), "rosalind": (77.3, 15.2),
    "belinda": (77.3, 15.2), "perdita": (77.3, 15.2), "mab": (77.3, 15.2),
    "cupid": (77.3, 15.2),
    "triton": (299.8, 43.1), "proteus": (299.8, 42.6),
    "naiad": (299.7, 42.7), "thalassa": (299.7, 42.7),
    "despina": (299.7, 42.7), "galatea": (299.8, 43.1),
    "larissa": (299.8, 43.1), "hippocamp": (299.8, 43.0),
    "nereid": ECLIPTIC_POLE,
    "charon": (132.993, -6.163), "styx": (132.993, -6.163),
    "nix": (132.993, -6.163), "kerberos": (132.993, -6.163),
    "hydra": (132.993, -6.163),
}

# moon -> (Horizons COMMAND, CENTER)
BODIES = {
    "phobos": ("401", "500@499"), "deimos": ("402", "500@499"),
    "io": ("501", "500@599"), "europa": ("502", "500@599"),
    "ganymede": ("503", "500@599"), "callisto": ("504", "500@599"),
    "amalthea": ("505", "500@599"), "thebe": ("514", "500@599"),
    "adrastea": ("515", "500@599"), "metis": ("516", "500@599"),
    "mimas": ("601", "500@699"), "enceladus": ("602", "500@699"),
    "rhea": ("605", "500@699"), "titan": ("606", "500@699"),
    "iapetus": ("608", "500@699"),
    "tethys": ("603", "500@699"), "dione": ("604", "500@699"),
    "hyperion": ("607", "500@699"), "phoebe": ("609", "500@699"),
    "janus": ("610", "500@699"), "epimetheus": ("611", "500@699"),
    "helene": ("612", "500@699"), "telesto": ("613", "500@699"),
    "calypso": ("614", "500@699"), "atlas": ("615", "500@699"),
    "prometheus": ("616", "500@699"), "pandora": ("617", "500@699"),
    "pan": ("618", "500@699"), "daphnis": ("635", "500@699"),
    "methone": ("632", "500@699"), "pallene": ("633", "500@699"),
    "polydeuces": ("634", "500@699"), "anthe": ("649", "500@699"),
    "aegaeon": ("653", "500@699"),
    "ariel": ("701", "500@799"), "umbriel": ("702", "500@799"),
    "titania": ("703", "500@799"), "oberon": ("704", "500@799"),
    "miranda": ("705", "500@799"), "puck": ("715", "500@799"),
    "cordelia": ("706", "500@799"), "ophelia": ("707", "500@799"),
    "bianca": ("708", "500@799"), "cressida": ("709", "500@799"),
    "desdemona": ("710", "500@799"), "juliet": ("711", "500@799"),
    "portia": ("712", "500@799"), "rosalind": ("713", "500@799"),
    "belinda": ("714", "500@799"), "perdita": ("725", "500@799"),
    "mab": ("726", "500@799"), "cupid": ("727", "500@799"),
    "triton": ("801", "500@899"), "nereid": ("802", "500@899"),
    "proteus": ("808", "500@899"),
    "naiad": ("803", "500@899"), "thalassa": ("804", "500@899"),
    "despina": ("805", "500@899"), "galatea": ("806", "500@899"),
    "larissa": ("807", "500@899"), "hippocamp": ("814", "500@899"),
    # Charon is fit plutocentrically. Pluto's SMALL moons orbit the
    # Pluto-Charon barycenter, around which Pluto itself wobbles by
    # ~2100 km; a plutocentric precessing ellipse cannot represent that,
    # so they are fit around the system barycenter (500@9) and the runtime
    # converts to plutocentric with the analytic wobble correction
    # (see data.satellites and core._moon_state).
    "charon": ("901", "500@999"), "styx": ("905", "500@9"),
    "nix": ("902", "500@9"), "kerberos": ("904", "500@9"),
    "hydra": ("903", "500@9"),
}

# Published precession periods (P_apsis_yr, P_node_yr) from the JPL
# mean-elements page, used ONLY to initialize the precession rates (their
# magnitudes are reliable even where the page's angles are not). Signs at
# initialization follow oblateness-driven physics: node regresses, periapsis
# longitude advances (both flipped for retrograde orbits); the fit refines
# magnitude and sign freely from stage 3 on. None/0 -> no published period.
PUBLISHED_PRECESSION_YR = {
    "phobos": (1.1, 2.3), "deimos": (0.0, 56.2),
    "io": (1.333, 0.0), "europa": (1.394, 30.202),
    "ganymede": (68.301, 137.812), "callisto": (277.921, 577.264),
    "amalthea": (0.196, 0.393),
    "thebe": (0.398, 0.797), "adrastea": (0.0, 0.0), "metis": (0.0, 0.0),
    "mimas": (0.493, 0.986), "enceladus": (2.916, 0.0),
    "rhea": (33.939, 35.775), "titan": (346.680, 687.370),
    "iapetus": (1662.900, 3130.302),
    "tethys": (0.005, 4.982), "dione": (11.698, 0.0),
    "hyperion": (20.843, 257.625), "phoebe": (468.321, 741.483),
    "janus": (0.240, 0.482), "epimetheus": (0.240, 0.482),
    "helene": (5.825, 11.707), "telesto": (0.005, 4.982),
    "calypso": (0.005, 4.983), "atlas": (0.342, 0.0),
    "prometheus": (0.357, 0.0), "pandora": (0.379, 0.0),
    "pan": (0.0, 0.0), "daphnis": (0.0, 0.0), "methone": (0.003, 0.0),
    "pallene": (0.790, 1.582), "polydeuces": (5.810, 11.692),
    "anthe": (1.190, 0.0), "aegaeon": (0.0, 0.0),
    "ariel": (28.901, 0.0), "umbriel": (64.126, 129.745),
    "titania": (579.928, 1644.649), "oberon": (158.604, 192.798),
    "miranda": (8.939, 17.787), "puck": (2.226, 4.454),
    "cordelia": (0.0, 0.6), "ophelia": (0.4, 0.8), "bianca": (0.5, 1.1),
    "cressida": (0.6, 1.2), "desdemona": (0.6, 1.3), "juliet": (0.7, 1.4),
    "portia": (0.8, 1.6), "rosalind": (0.9, 1.9), "belinda": (1.2, 2.4),
    "perdita": (1.3, 2.6), "mab": (3.1, 6.1), "cupid": (1.2, 2.3),
    "triton": (0.0, 340.379), "nereid": (7990.433, 9426.334),
    "proteus": (0.0, 0.0),
    "naiad": (0.0, 0.575), "thalassa": (0.0, 0.654), "despina": (0.0, 0.0),
    "galatea": (0.0, 0.0), "larissa": (1.257, 2.514),
    "hippocamp": (8.726, 661.762),
    "charon": (None, None), "styx": (None, None), "nix": (None, None),
    "kerberos": (None, 9.0), "hydra": (None, 14.0),
}

DAYS_PER_YEAR = 365.25

# Resonance/co-orbital libration in mean longitude, too large for a
# precessing ellipse to absorb: moon -> initial libration period (yr).
# The sine/cosine amplitudes start at zero and are fit linearly; the
# period is refined in the final stage.
#   mimas/tethys      Mimas-Tethys 4:2 resonance (~72 yr; ~44 deg on Mimas)
#   hyperion          Titan-Hyperion 4:3 resonance (~1.75 yr)
#   janus/epimetheus  horseshoe co-orbital swap (~8 yr cycle)
#   telesto/calypso   Tethys L4/L5 trojans (tadpole libration)
#   helene/polydeuces Dione L4/L5 trojans (Polydeuces librates ~26 deg)
#   methone/anthe/aegaeon  resonant with Mimas: they librate on their own
#     resonant period AND inherit Mimas's 71.8-yr resonance cycle (their
#     residual spectra peak at ~72 yr with 20-56 deg amplitude), so they
#     carry a second, independent libration term (below)
#   pallene           near 19:16 with Mimas (~1.3 yr; small amplitude)
#   prometheus/pandora chaotic mutual interaction (~6.2 yr)
LIBRATION_PERIOD_INIT_YR = {
    "mimas": 71.8, "tethys": 71.8,
    "hyperion": 1.75,
    "janus": 8.0, "epimetheus": 8.0,
    "telesto": 1.9, "calypso": 1.9,
    "helene": 2.2, "polydeuces": 2.2,
    "methone": 1.2, "anthe": 2.0, "pallene": 1.3, "aegaeon": 1.3,
    "prometheus": 6.2, "pandora": 6.2,
}

# Second libration term (see model_position): the small Mimas-resonant
# moons additionally ride Mimas's 71.8-yr Mimas-Tethys resonance cycle.
LIBRATION2_PERIOD_INIT_YR = {
    "methone": 71.8, "anthe": 71.8, "aegaeon": 71.8,
}

# Moons with a fitted secular mean-motion acceleration (quadratic mean-
# longitude term). Phobos's tidal deceleration accelerates its mean
# longitude by ~1e-3 deg/yr^2 -- degrees over a century, the dominant
# residual of a pure precessing ellipse.
ACCELERATED = frozenset({"phobos"})

# Inert placeholder period for moons without a libration term.
_NO_LIBRATION_PERIOD_DAYS = 1.0e6

# Fit arcs. Widening spans lock the mean motion in without mod-360
# ambiguity (each stage refines the mean motion enough that the next,
# longer stage stays within half an orbit of phase drift); the final arc
# covers the tested 1900-2050 window. The dense arcs (start, stop, step)
# sit around J2000, which every satellite ephemeris covers. The wide arcs
# (start, stop, samples) may exceed a late-discovered moon's ephemeris
# (e.g. Daphnis only spans 1990-06-15 to 2018-01-17): fetch_arc_available
# clips them to the coverage bounds Horizons reports and re-spaces the
# step over what remains.
DENSE_ARCS = [
    ("2000-01-01", "2000-01-08", "1h"),
    ("2000-01-08", "2000-04-01", "12h"),
]
# Librating moons additionally bridge the 90-day-to-20-year jump with
# ~1.5- and ~5-year arcs, with the libration amplitudes free: a 90-day
# arc cannot separate a libration (periods 1.2-8 yr) from the mean
# motion, so its fitted mean motion absorbs the libration slope (up to
# ~0.25 deg/day for Helene), which wraps the phase many times over over
# a 20-year arc and strands the fit in a false minimum.
BRIDGE_ARCS = [
    ("2000-04-01", "2001-07-01", "3d"),
    ("2001-07-01", "2005-01-01", "7d"),
]
WIDE_ARCS = [
    ("1990-01-01", "2010-01-01", 365),
    ("1900-01-01", "2050-01-01", 400),
]
# Librating moons get one more intermediate span on the wide side, for
# the same reason as the bridge arcs: the leftover mean-motion bias after
# the 20-year stage (~0.01 deg/day) still wraps the phase at the far end
# of a 150-year arc, and wrapped residuals hide the true minimum from
# the gradient.
LIBRATION_WIDE_ARCS = [
    ("1990-01-01", "2010-01-01", 365),
    ("1970-01-01", "2030-01-01", 250),
    ("1900-01-01", "2050-01-01", 400),
]

# Co-orbital seeding: Janus and Epimetheus swap orbits every ~4 yr; their
# mean-longitude librations are anti-phased with amplitudes in inverse
# proportion to their GMs (momentum conservation), and they share one
# time-averaged orbit. Epimetheus's libration (~110 deg peak, sawtooth)
# is too large to find from a cold start, so it is seeded from Janus's
# fitted solution: moon -> (sibling, amplitude ratio = -GM_sib/GM_moon,
# from sats/phys_par: 0.12662 / 0.03514).
CO_ORBITAL_SEED = {"epimetheus": ("janus", -0.12662 / 0.03514)}


def fetch_arc(command, center, start, stop, step):
    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": f"'{center}'",
        "REF_PLANE": "'ECLIPTIC'",
        "REF_SYSTEM": "'J2000'",
        "VEC_TABLE": "'2'",
        "OUT_UNITS": "'KM-S'",
        "CSV_FORMAT": "'YES'",
        "START_TIME": f"'TDB {start}'",
        "STOP_TIME": f"'{stop}'",
        "STEP_SIZE": f"'{step}'",
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = json.loads(response.read().decode())
    text = payload["result"]
    if "$$SOE" not in text:
        raise RuntimeError(f"Horizons returned no data: {text[:300]}")
    samples = []
    for line in text.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines():
        fields = [f.strip() for f in line.split(",")]
        jd = float(fields[0])
        pos = (float(fields[2]), float(fields[3]), float(fields[4]))
        vel = (float(fields[5]), float(fields[6]), float(fields[7]))
        samples.append((jd - J2000_JD, pos, vel))
    return samples


_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _coverage_bound(message, side):
    """Extract an ephemeris coverage bound from a Horizons error message.

    Horizons rejects out-of-span requests with e.g.
    'No ephemeris for target "Daphnis" prior to A.D. 1990-JUN-15 ...' /
    '... after A.D. 2018-JAN-17 ...'; returns that bound as a date, or
    None if the message reports no bound for the requested side.
    """
    match = re.search(
        rf"{side} A\.D\. (\d{{4}})-([A-Z]{{3}})-(\d{{2}})", message
    )
    if not match:
        return None
    year, month, day = match.groups()
    return datetime.date(int(year), _MONTHS[month], int(day))


def fetch_arc_available(command, center, start, stop, samples):
    """Fetch an arc, clipping the span to the ephemeris coverage bounds.

    Requests `samples` points across [start, stop]; when Horizons reports
    the target's ephemeris starts later / ends earlier, the span is
    clipped (one day inside the reported bound) and re-requested with the
    step re-spaced to keep the sample count.
    """
    lo = datetime.date.fromisoformat(start)
    hi = datetime.date.fromisoformat(stop)
    for _ in range(5):
        step_days = max(1, (hi - lo).days // samples)
        try:
            return (
                fetch_arc(command, center, lo.isoformat(), hi.isoformat(),
                          f"{step_days}d"),
                lo.isoformat(), hi.isoformat(),
            )
        except RuntimeError as error:
            message = str(error)
            starts = _coverage_bound(message, "prior to")
            ends = _coverage_bound(message, "after")
            if starts is None and ends is None:
                raise
            one_day = datetime.timedelta(days=1)
            if starts is not None and starts + one_day > lo:
                lo = starts + one_day
            if ends is not None and ends - one_day < hi:
                hi = ends - one_day
            if lo >= hi:
                raise
    raise RuntimeError(
        f"could not converge on ephemeris coverage for {command}"
    )


def ecliptic_to_plane(pole_ra, pole_dec, vector):
    """Inverse of frames.plane_to_ecliptic."""
    x, y, z = vector
    eps = math.radians(frames.OBLIQUITY_J2000_DEG)
    ce, se = math.cos(eps), math.sin(eps)
    equatorial = (x, ce * y - se * z, se * y + ce * z)
    axes = frames.rotation_from_pole(pole_ra, pole_dec)
    return tuple(
        sum(a * c for a, c in zip(axis, equatorial)) for axis in axes
    )


def rv_to_elements(position, velocity, mu):
    """Osculating elements (a, e, i, node, argp, M) from an r/v pair."""
    r_vec, v_vec = position, velocity
    r = math.sqrt(sum(c * c for c in r_vec))
    v2 = sum(c * c for c in v_vec)
    h_vec = (
        r_vec[1] * v_vec[2] - r_vec[2] * v_vec[1],
        r_vec[2] * v_vec[0] - r_vec[0] * v_vec[2],
        r_vec[0] * v_vec[1] - r_vec[1] * v_vec[0],
    )
    h = math.sqrt(sum(c * c for c in h_vec))
    inclination = math.acos(max(-1.0, min(1.0, h_vec[2] / h)))
    node_vec = (-h_vec[1], h_vec[0], 0.0)
    n_norm = math.hypot(node_vec[0], node_vec[1])
    node = math.atan2(node_vec[1], node_vec[0]) if n_norm > 1e-12 else 0.0

    rv_dot = sum(a * b for a, b in zip(r_vec, v_vec))
    e_vec = tuple(
        (v2 / mu - 1.0 / r) * rc - (rv_dot / mu) * vc
        for rc, vc in zip(r_vec, v_vec)
    )
    e = math.sqrt(sum(c * c for c in e_vec))
    a = 1.0 / (2.0 / r - v2 / mu)

    if n_norm > 1e-12 and e > 1e-9:
        cos_w = sum(a_ * b_ for a_, b_ in zip(node_vec, e_vec)) / (n_norm * e)
        argp = math.acos(max(-1.0, min(1.0, cos_w)))
        if e_vec[2] < 0:
            argp = -argp
    else:
        argp = math.atan2(e_vec[1], e_vec[0]) if e > 1e-9 else 0.0

    if e > 1e-9:
        cos_nu = sum(a_ * b_ for a_, b_ in zip(e_vec, r_vec)) / (e * r)
        nu = math.acos(max(-1.0, min(1.0, cos_nu)))
        if rv_dot < 0:
            nu = -nu
        E = math.atan2(math.sqrt(1 - e * e) * math.sin(nu), e + math.cos(nu))
        M = E - e * math.sin(E)
    else:
        # circular: use argument of latitude as the anomaly
        M = math.atan2(r_vec[1] * math.cos(node) - r_vec[0] * math.sin(node),
                       (r_vec[0] * math.cos(node) + r_vec[1] * math.sin(node)))
        M -= argp
    return a, e, inclination, node % math.tau, argp % math.tau, M % math.tau


def model_position(params, t_days):
    """Reference-plane position at t (days since J2000) for fit params.

    params (18): a, e, i, node0, node_rate, argp0, argp_rate, M0, M_rate,
    libration sin/cos amp (fundamental), libration period (days),
    mean-motion acceleration (deg/day^2), libration sin/cos amp at the
    second harmonic (sawtooth-like horseshoe/resonance librations need
    it), and a second, independent libration term (sin/cos amp, period)
    for moons whose longitude carries two unrelated cycles (the small
    Mimas-resonant moons librate on their own resonant period AND inherit
    Mimas's 71.8-yr resonance cycle). The extra terms are frozen at zero
    amplitude for moons that do not need them.
    """
    (a, e, i_deg, node0, node_rate, argp0, argp_rate, m0, m_rate,
     sin_amp, cos_amp, period_days, m_accel, sin2_amp, cos2_amp,
     sin_b_amp, cos_b_amp, period_b_days) = params
    e = min(abs(e), 0.95)  # keep trial steps inside the solver's domain
    phase = math.tau * t_days / period_days
    phase_b = math.tau * t_days / period_b_days
    libration = (
        sin_amp * math.sin(phase) + cos_amp * math.cos(phase)
        + sin2_amp * math.sin(2.0 * phase) + cos2_amp * math.cos(2.0 * phase)
        + sin_b_amp * math.sin(phase_b) + cos_b_amp * math.cos(phase_b)
    )
    node = math.radians(node0 + node_rate * t_days)
    argp = math.radians(argp0 + argp_rate * t_days)
    mean_anomaly = math.radians(
        m0 + m_rate * t_days + libration + 0.5 * m_accel * t_days * t_days
    )
    n_rad_s = math.radians(m_rate) / SECONDS_PER_DAY
    mu = n_rad_s * n_rad_s * a**3
    position, _ = kepler.elements_to_state(
        a, e, math.radians(i_deg), node, argp, mean_anomaly, mu
    )
    return position


def residuals(params, samples, scale):
    """Position residuals normalized by a FIXED length scale.

    The scale must not be the fitted semi-major axis: dividing by params[0]
    would let the optimizer shrink the loss by inflating the orbit.

    Trial steps that leave the solver's eccentricity domain are rejected
    outright (huge residuals) rather than clamped: a clamp zeroes the
    gradient, so once a step lands past it the eccentricity can never
    recover and the whole fit silently diverges (Tethys did exactly that,
    converging to e = 0.95, rms = 95 deg). Libration amplitudes beyond
    180 deg are rejected for the same reason: a libration is < 180 deg by
    definition, and runaway amplitudes (Epimetheus reached 565 deg) let
    the mean motion alias onto a false minimum.
    """
    if not abs(params[1]) < 0.95:
        return [1e9] * (3 * len(samples))
    if any(abs(params[k]) > 180.0 for k in (9, 10, 13, 14, 15, 16)):
        return [1e9] * (3 * len(samples))
    out = []
    for t_days, pos in samples:
        model = model_position(params, t_days)
        out.extend((m - p) / scale for m, p in zip(model, pos))
    return out


def solve_normal_equations(jacobian, errors, damping):
    n = len(jacobian[0])
    ata = [[0.0] * n for _ in range(n)]
    atb = [0.0] * n
    for row, err in zip(jacobian, errors):
        for i in range(n):
            if row[i] == 0.0:
                continue
            atb[i] -= row[i] * err
            for j in range(n):
                ata[i][j] += row[i] * row[j]
    for i in range(n):
        ata[i][i] *= 1.0 + damping
        ata[i][i] += 1e-30
    # Gaussian elimination with partial pivoting
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(ata[r][col]))
        ata[col], ata[pivot] = ata[pivot], ata[col]
        atb[col], atb[pivot] = atb[pivot], atb[col]
        if abs(ata[col][col]) < 1e-30:
            continue
        for row in range(col + 1, n):
            factor = ata[row][col] / ata[col][col]
            atb[row] -= factor * atb[col]
            for j in range(col, n):
                ata[row][j] -= factor * ata[col][j]
    delta = [0.0] * n
    for row in range(n - 1, -1, -1):
        if abs(ata[row][row]) < 1e-30:
            continue
        acc = atb[row] - sum(ata[row][j] * delta[j] for j in range(row + 1, n))
        delta[row] = acc / ata[row][row]
    return delta


def levenberg_marquardt(params, samples, free, scale, iterations=60):
    """Minimize position residuals; `free` masks which params move."""
    base_steps = (1e-3, 1e-9, 1e-7, 1e-7, 1e-12, 1e-7, 1e-12, 1e-7, 1e-12,
                  1e-6, 1e-6, 1e-2, 1e-15, 1e-6, 1e-6, 1e-6, 1e-6, 1e-1)
    steps = [
        max(abs(p) * 1e-7, s) for p, s in zip(params, base_steps)
    ]
    damping = 1e-3
    best = residuals(params, samples, scale)
    best_cost = sum(e * e for e in best)
    for _ in range(iterations):
        jacobian = []
        base = residuals(params, samples, scale)
        columns = []
        for k in range(len(params)):
            if not free[k]:
                columns.append(None)
                continue
            bumped = list(params)
            bumped[k] += steps[k]
            column = [
                (r1 - r0) / steps[k]
                for r1, r0 in zip(residuals(bumped, samples, scale), base)
            ]
            columns.append(column)
        active = [k for k in range(len(params)) if free[k]]
        for row_idx in range(len(base)):
            jacobian.append([columns[k][row_idx] for k in active])
        delta = solve_normal_equations(jacobian, base, damping)
        trial = list(params)
        for slot, k in enumerate(active):
            trial[k] += delta[slot]
        trial_res = residuals(trial, samples, scale)
        trial_cost = sum(e * e for e in trial_res)
        if trial_cost < best_cost:
            params = trial
            improvement = (best_cost - trial_cost) / max(best_cost, 1e-30)
            best_cost = trial_cost
            damping = max(damping / 3.0, 1e-9)
            if improvement < 1e-10:
                break
        else:
            damping *= 10.0
            if damping > 1e6:
                break
    return params, best_cost


def fit_stage_multistart(params, samples, free, scale, prev_span_days):
    """Fit one stage from a lattice of mean-motion starts, keep the best.

    Extending a fit from a span T to a longer arc leaves a lattice of
    false minima: any mean motion differing by a multiple of 360/T deg/day
    fits the previous span equally well but wraps the new arc. Gradient
    descent alone can also WANDER onto that lattice mid-stage (Methone's
    mean motion drifted 26 lattice steps and settled at rms 45 deg), so
    each candidate is refined briefly and only the lowest-cost basin gets
    the full refinement.
    """
    lattice = 360.0 / prev_span_days
    best_params, best_cost = None, math.inf
    for k in range(-3, 4):
        trial = list(params)
        trial[8] += k * lattice
        trial, cost = levenberg_marquardt(
            trial, samples, free, scale, iterations=15
        )
        if cost < best_cost:
            best_params, best_cost = trial, cost
    return levenberg_marquardt(best_params, samples, free, scale)


def fit_stats(params, samples):
    worst_deg = 0.0
    sum_sq = 0.0
    worst_dist = 0.0
    for t_days, pos in samples:
        model = model_position(params, t_days)
        dot = sum(m * p for m, p in zip(model, pos))
        nm = math.sqrt(sum(m * m for m in model))
        np_ = math.sqrt(sum(p * p for p in pos))
        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot / (nm * np_)))))
        worst_deg = max(worst_deg, angle)
        worst_dist = max(worst_dist, abs(nm - np_) / np_)
        sum_sq += angle * angle
    rms = math.sqrt(sum_sq / len(samples))
    return {"rms_deg": rms, "worst_deg": worst_deg, "worst_dist_rel": worst_dist}


def fit_moon(name):
    command, center = BODIES[name]
    pole = POLES[name]
    has_libration = name in LIBRATION_PERIOD_INIT_YR
    print(f"{name}: fetching arcs...")
    arcs = [fetch_arc(command, center, *arc) for arc in DENSE_ARCS]
    if has_libration:
        arcs += [fetch_arc(command, center, *arc) for arc in BRIDGE_ARCS]
    wide_arcs = LIBRATION_WIDE_ARCS if has_libration else WIDE_ARCS
    for start, stop, samples in wide_arcs:
        arc, got_start, got_stop = fetch_arc_available(
            command, center, start, stop, samples
        )
        if (got_start, got_stop) != (start, stop):
            print(f"{name}: ephemeris coverage is limited; arc"
                  f" {start}..{stop} clipped to {got_start}..{got_stop}")
        arcs.append(arc)
    plane_arcs = [
        [(t, ecliptic_to_plane(pole[0], pole[1], pos)) for t, pos, _ in arc]
        for arc in arcs
    ]

    # Initialize from the first dense-arc state (Horizons velocity rotated
    # into the reference plane; the frame rotation is linear).
    t0, pos0, vel0 = arcs[0][0]
    p0 = ecliptic_to_plane(pole[0], pole[1], pos0)
    v0 = ecliptic_to_plane(pole[0], pole[1], vel0)
    r = math.sqrt(sum(c * c for c in p0))
    v2 = sum(c * c for c in v0)
    mu0 = r * v2  # exact for a circular orbit; refined by the fit
    a0, e0, i0, node0, argp0, m0 = rv_to_elements(p0, v0, mu0)
    m_rate0 = math.degrees(math.sqrt(mu0 / a0**3)) * SECONDS_PER_DAY
    libration_period_yr = LIBRATION_PERIOD_INIT_YR.get(name)
    p_apsis_yr, p_node_yr = PUBLISHED_PRECESSION_YR[name]
    retrograde = math.degrees(i0) > 90.0
    node_rate0 = 0.0
    if p_node_yr:
        node_rate0 = 360.0 / (p_node_yr * DAYS_PER_YEAR)
        node_rate0 = node_rate0 if retrograde else -node_rate0
    periapsis_rate0 = 0.0
    if p_apsis_yr:
        periapsis_rate0 = 360.0 / (p_apsis_yr * DAYS_PER_YEAR)
        periapsis_rate0 = -periapsis_rate0 if retrograde else periapsis_rate0
    # Published periods short enough to imply rates beyond any real
    # oblateness-driven precession (the largest FITTED rate is ~6 deg/day,
    # Janus) are page artifacts for near-circular resonant moons -- e.g.
    # Tethys's listed 0.005 yr apsidal period would be 197 deg/day, and
    # starting there sends the fit into a false minimum. Start those at
    # zero; the rate is refined freely from stage 3 anyway.
    if abs(node_rate0) > 10.0:
        node_rate0 = 0.0
    if abs(periapsis_rate0) > 10.0:
        periapsis_rate0 = 0.0
    argp_rate0 = periapsis_rate0 - node_rate0
    params = [
        a0, max(e0, 1e-6), math.degrees(i0),
        math.degrees(node0), node_rate0,
        math.degrees(argp0), argp_rate0,
        math.degrees(m0) - m_rate0 * t0, m_rate0,
    ]
    accelerated = name in ACCELERATED
    libration2_period_yr = LIBRATION2_PERIOD_INIT_YR.get(name)
    has_libration2 = bool(libration2_period_yr)
    params += [
        0.0, 0.0,
        libration_period_yr * DAYS_PER_YEAR
        if has_libration else _NO_LIBRATION_PERIOD_DAYS,
        0.0,
        0.0, 0.0,
        0.0, 0.0,
        libration2_period_yr * DAYS_PER_YEAR
        if has_libration2 else _NO_LIBRATION_PERIOD_DAYS,
    ]
    seeded = False
    if name in CO_ORBITAL_SEED:
        sibling, ratio = CO_ORBITAL_SEED[name]
        fitted = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        if sibling in fitted:
            sib = fitted[sibling]
            params[0] = sib["a_km"]
            params[8] = sib["mean_motion_deg_per_day"]
            params[9] = ratio * sib["libration_sin_deg"]
            params[10] = ratio * sib["libration_cos_deg"]
            params[11] = sib["libration_period_days"]
            params[13] = ratio * sib.get("libration_sin2_deg", 0.0)
            params[14] = ratio * sib.get("libration_cos2_deg", 0.0)
            seeded = True
            print(f"{name}: seeded from {sibling}'s co-orbital solution")
        else:
            print(f"{name}: WARNING: seed sibling {sibling} not fitted yet")

    def mask(*, rates, extras=False, libration_period=False, extras2=False):
        return [
            True, True, True, True, rates, True, rates, True, True,
            extras and has_libration, extras and has_libration,
            libration_period and has_libration,
            extras and accelerated,
            extras and has_libration, extras and has_libration,
            extras2 and has_libration2, extras2 and has_libration2,
            libration_period and has_libration2,
        ]

    # Dense stages first (rates frozen); librating moons then work through
    # the bridge arcs before the span widens, and every wide stage starts
    # from a lattice of mean-motion candidates (see fit_stage_multistart).
    # Libration amplitudes only open up once the fitted span covers at
    # least a quarter of the libration period: on shorter arcs the
    # libration is degenerate with the mean motion and the amplitudes
    # absorb arbitrary phase slope (Methone with its 71.8-yr period freed
    # on a 1.5-yr bridge arc diverged to rms 65 deg). Co-orbitally seeded
    # moons keep the seeded libration frozen until the final stage: their
    # libration is too large to refit from scratch mid-widening, and the
    # sibling's scaled solution already matches it (Epimetheus refit from
    # a free cold start diverged to rms 43 deg; frozen-seed converges
    # to ~9).
    def _span_covers(samples, period_days):
        span = max(t for t, _ in samples) - min(t for t, _ in samples)
        return span >= period_days / 4.0

    def stage_extras(samples):
        if not has_libration or seeded:
            return False
        return _span_covers(samples, params[11])

    def stage_extras2(samples):
        if not has_libration2 or seeded:
            return False
        return _span_covers(samples, params[17])

    acc = list(plane_arcs[0])
    stages = [(acc, mask(rates=False), False)]
    acc = acc + plane_arcs[1]
    stages.append((acc, mask(rates=False), False))
    for bridge_index in range(len(BRIDGE_ARCS)) if has_libration else ():
        acc = acc + plane_arcs[2 + bridge_index]
        stages.append((acc, mask(rates=True, extras=stage_extras(acc),
                                 extras2=stage_extras2(acc)), False))
    for wide_index in range(len(wide_arcs)):
        final = wide_index == len(wide_arcs) - 1
        acc = acc + plane_arcs[len(arcs) - len(wide_arcs) + wide_index]
        stages.append((
            acc,
            mask(rates=True,
                 extras=stage_extras(acc) or final,
                 libration_period=final,
                 extras2=stage_extras2(acc) or final),
            has_libration,
        ))
    scale = a0
    prev_span = 1.0
    for stage_index, (samples, free, multistart) in enumerate(stages):
        if multistart:
            params, _ = fit_stage_multistart(
                params, samples, free, scale, prev_span
            )
        else:
            params, _ = levenberg_marquardt(params, samples, free, scale)
        prev_span = max(t for t, _ in samples) - min(t for t, _ in samples)
        stage_stats = fit_stats(params, samples)
        print(f"{name}:   stage {stage_index + 1}/{len(stages)}"
              f" ({prev_span / DAYS_PER_YEAR:.1f} yr,"
              f" {len(samples)} samples):"
              f" rms={stage_stats['rms_deg']:.3f} deg,"
              f" worst={stage_stats['worst_deg']:.3f} deg")

    # Canonicalize the sign-degenerate parameterization: a negative
    # semi-major axis is the same ellipse point-reflected in-plane, i.e.
    # positive a with the periapsis rotated half a turn.
    if params[0] < 0.0:
        params[0] = -params[0]
        params[5] += 180.0

    full = sum(plane_arcs, [])
    stats = fit_stats(params, full)
    stats["n_samples"] = len(full)
    print(
        f"{name}: rms={stats['rms_deg']:.3f} deg, worst={stats['worst_deg']:.3f} deg,"
        f" worst dist={stats['worst_dist_rel'] * 100:.3f}%"
    )
    a, e, i_deg, node0, node_rate, argp0, argp_rate, m0, m_rate = params[:9]
    result = {
        "a_km": a,
        "e": abs(e),
        "i_deg": i_deg % 360.0,
        "node_deg": node0 % 360.0,
        "node_rate_deg_per_day": node_rate,
        "arg_periapsis_deg": argp0 % 360.0,
        "arg_periapsis_rate_deg_per_day": argp_rate,
        "mean_anomaly_deg": m0 % 360.0,
        "mean_motion_deg_per_day": m_rate,
        "pole_ra_deg": pole[0],
        "pole_dec_deg": pole[1],
        "fit": stats,
    }
    if has_libration:
        result["libration_sin_deg"] = params[9]
        result["libration_cos_deg"] = params[10]
        result["libration_period_days"] = params[11]
        result["libration_sin2_deg"] = params[13]
        result["libration_cos2_deg"] = params[14]
    if has_libration2:
        result["libration2_sin_deg"] = params[15]
        result["libration2_cos_deg"] = params[16]
        result["libration2_period_days"] = params[17]
    if accelerated:
        result["mean_motion_rate_deg_per_day2"] = params[12]
    return result


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "src" / "orbitarium" / "data" / "satellites.py"
)

PARENTS = {
    "phobos": "mars", "deimos": "mars",
    "io": "jupiter", "europa": "jupiter", "ganymede": "jupiter",
    "callisto": "jupiter", "amalthea": "jupiter",
    "thebe": "jupiter", "adrastea": "jupiter", "metis": "jupiter",
    "titan": "saturn", "enceladus": "saturn", "mimas": "saturn",
    "iapetus": "saturn", "rhea": "saturn",
    "tethys": "saturn", "dione": "saturn", "hyperion": "saturn",
    "phoebe": "saturn", "janus": "saturn", "epimetheus": "saturn",
    "helene": "saturn", "telesto": "saturn", "calypso": "saturn",
    "atlas": "saturn", "prometheus": "saturn", "pandora": "saturn",
    "pan": "saturn", "daphnis": "saturn", "methone": "saturn",
    "pallene": "saturn", "polydeuces": "saturn", "anthe": "saturn",
    "aegaeon": "saturn",
    "titania": "uranus", "oberon": "uranus", "umbriel": "uranus",
    "ariel": "uranus", "miranda": "uranus", "puck": "uranus",
    "cordelia": "uranus", "ophelia": "uranus", "bianca": "uranus",
    "cressida": "uranus", "desdemona": "uranus", "juliet": "uranus",
    "portia": "uranus", "rosalind": "uranus", "belinda": "uranus",
    "perdita": "uranus", "mab": "uranus", "cupid": "uranus",
    "triton": "neptune", "nereid": "neptune", "proteus": "neptune",
    "naiad": "neptune", "thalassa": "neptune", "despina": "neptune",
    "galatea": "neptune", "larissa": "neptune", "hippocamp": "neptune",
    "charon": "pluto", "styx": "pluto", "nix": "pluto",
    "kerberos": "pluto", "hydra": "pluto",
}

REF_PLANES = {
    "mars": "Laplace", "jupiter": "Laplace", "saturn": "Laplace",
    "uranus": "equatorial", "neptune": "Laplace", "pluto": "equatorial",
}
REF_PLANE_OVERRIDES = {
    "nereid": "ecliptic",
    # URA184 inner belt: referred to local Laplace planes (pole listed
    # explicitly on the page), unlike the URA182 equatorial main table.
    **{name: "Laplace" for name in (
        "cordelia", "ophelia", "bianca", "cressida", "desdemona", "juliet",
        "portia", "rosalind", "belinda", "perdita", "mab", "cupid",
    )},
}

EPHEMERIDES = {
    "mars": "MAR099", "jupiter": "JUP365", "saturn": "SAT441",
    "uranus": "URA182", "neptune": "NEP097", "pluto": "PLU060",
}
EPHEMERIS_OVERRIDES = {
    "nereid": "NEP105",
    **{name: "SAT415" for name in (
        "janus", "epimetheus", "atlas", "prometheus", "pandora", "pan",
        "daphnis", "pallene", "anthe", "aegaeon",
    )},
    **{name: "URA184" for name in (
        "cordelia", "ophelia", "bianca", "cressida", "desdemona", "juliet",
        "portia", "rosalind", "belinda", "perdita", "mab", "cupid",
    )},
}

# Pluto's small moons are fit around the Pluto-Charon barycenter; the
# runtime converts to plutocentric by adding f * Charon's plutocentric
# state, with f = GM_charon / (GM_pluto + GM_charon) from DE440
# (gm_de440.tpc: BODY999_GM = 869.6138177608748, BODY901_GM = 106.1).
BARYCENTRIC_MOONS = ("styx", "nix", "kerberos", "hydra")
GM_PLUTO = 869.6138177608748
GM_CHARON = 106.1

MODULE_HEADER = '''"""Precessing-ellipse mean elements for 66 planetary satellites.

GENERATED by tools/fit_satellite_elements.py -- do not edit values by hand.

Each entry is a least-squares fit of a precessing ellipse to JPL Horizons
geometric states (parent-centered, ecliptic-J2000 in, converted to the
moon's reference plane) sampled over 1900-2050, evaluated with this
package's own Kepler solver. "Mean elements, in this context, are simply
the elements of a precessing ellipse which has been fit in a least squares
sense to the numerically integrated orbit" (JPL SSD) -- here the fit is
made directly against Horizons so that it reproduces those integrated
orbits by construction; per-moon fit statistics are stored under "fit".

Why not the published mean-elements table: JPL's "Planetary Satellite Mean
Elements" page (https://ssd.jpl.nasa.gov/sats/elem/, retrieved 2026-07-18)
states its parameters "are not intended for ephemeris computation", and
indeed its angles, interpreted per the page's own legend, disagree with
Horizons at their stated epoch by up to ~157 deg of mean longitude for the
Saturnian satellites (e.g. Titan: published M = 11.7 deg vs an actual mean
anomaly of ~163 deg at 2000-01-01.5 TDB) and tens of degrees for Pluto's
small moons, while the published periods of the Martian and small
Plutonian moons carry too few significant digits to hold orbital phase
over decades. No consistent reading (epoch shifts, angle conventions,
column permutations, precession signs) reconciles them, so the ellipses
are refit here from Horizons itself.

What IS taken from the published page: the reference-plane poles (each
moon's Laplace-plane pole, or the parent's equatorial pole for Uranus and
Pluto) and the underlying ephemeris IDs. Note the Uranus satellite pole
used here, (77.311, +15.175) ICRF, is the right-hand-rule spin pole -- the
anti-pole of the IAU/pck00011 direction -- which the JPL page itself
confirms by listing the outer-Uranian Laplace pole as (77.3, +15.2) with a
180-deg tilt to the planet's equator. With it, every prograde Uranian moon
has inclination near zero, and angles follow the page's convention
("measured from the node of the reference plane on the ICRF equator").

Conventions:
* Angles are in the moon's reference plane; the node is measured from the
  ascending node of that plane on the ICRF equator.
* All rates are per day; node/periapsis rates are SIGNED (negative =
  regression). Retrograde orbits carry inclination > 90 deg (Triton);
  no negative periods appear anywhere.
* mean_motion_deg_per_day is the rate of the mean anomaly; the parent's
  effective GM used for velocities follows from it and a_km.
* Resonant, trojan, and co-orbital moons carry an explicit mean-longitude
  libration term (fundamental plus second harmonic, for sawtooth-like
  horseshoe librations) applied to the mean anomaly:
  M += s1*sin(2*pi*t/P) + c1*cos(2*pi*t/P)
     + s2*sin(4*pi*t/P) + c2*cos(4*pi*t/P).
  (Mimas & Tethys: 4:2 resonance; Hyperion: 4:3 with Titan; Janus &
  Epimetheus: horseshoe swap; Telesto/Calypso and Helene/Polydeuces:
  trojan tadpole libration; Methone/Anthe/Pallene/Aegaeon: resonances
  with Mimas; Prometheus/Pandora: mutual chaotic interaction.)
* Methone, Anthe, and Aegaeon carry a SECOND, independent libration term
  (keys libration2_*, same sin/cos form, no harmonic): they librate on
  their own resonant period and additionally inherit Mimas's 71.8-yr
  Mimas-Tethys resonance cycle, with amplitudes of tens of degrees.
* Phobos carries a fitted secular mean-motion acceleration (tidal orbital
  decay), applied as M += 0.5 * rate * t^2.
* Pluto's small moons (Styx, Nix, Kerberos, Hydra) orbit the Pluto-Charon
  BARYCENTER, around which Pluto itself wobbles by ~2100 km; their
  ellipses are therefore fit barycentrically and carry a
  "barycenter_correction" pointing at Charon: the plutocentric state is
  the barycentric state plus factor * Charon's plutocentric state, with
  factor = GM_charon / (GM_pluto + GM_charon) (DE440 values).
* Epoch of all element sets: J2000.0 (JD 2451545.0 TDB).

Luna is intentionally absent: its geocentric state comes from the Meeus
truncated lunar series (orbitarium.lunar), far more accurate for Earth's
strongly perturbed moon than any precessing ellipse.
"""

J2000_JD = 2451545.0

_FIT_SOURCE = (
    "Precessing-ellipse fit to JPL Horizons geometric states (1900-2050), "
    "tools/fit_satellite_elements.py; reference plane pole and ephemeris "
    "ID from JPL SSD Planetary Satellite Mean Elements "
    "(https://ssd.jpl.nasa.gov/sats/elem/, retrieved 2026-07-18)"
)

SATELLITE_ELEMENTS = {
'''


def emit_module():
    results = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    lines = [MODULE_HEADER]
    for name in PARENTS:
        entry = results[name]
        parent = PARENTS[name]
        fit = entry["fit"]
        lines.append(f'    "{name}": {{\n')
        lines.append(f'        "parent": "{parent}",\n')
        for key in (
            "a_km", "e", "i_deg", "node_deg", "node_rate_deg_per_day",
            "arg_periapsis_deg", "arg_periapsis_rate_deg_per_day",
            "mean_anomaly_deg", "mean_motion_deg_per_day",
        ):
            lines.append(f'        "{key}": {entry[key]!r},\n')
        if "libration_sin_deg" in entry:
            for key in (
                "libration_sin_deg", "libration_cos_deg",
                "libration_period_days",
                "libration_sin2_deg", "libration_cos2_deg",
            ):
                lines.append(f'        "{key}": {entry.get(key, 0.0)!r},\n')
        if "libration2_sin_deg" in entry:
            for key in (
                "libration2_sin_deg", "libration2_cos_deg",
                "libration2_period_days",
            ):
                lines.append(f'        "{key}": {entry[key]!r},\n')
        if "mean_motion_rate_deg_per_day2" in entry:
            lines.append(
                '        "mean_motion_rate_deg_per_day2": '
                f'{entry["mean_motion_rate_deg_per_day2"]!r},\n'
            )
        lines.append(f'        "pole_ra_deg": {entry["pole_ra_deg"]!r},\n')
        lines.append(f'        "pole_dec_deg": {entry["pole_dec_deg"]!r},\n')
        ref_plane = REF_PLANE_OVERRIDES.get(name, REF_PLANES[parent])
        ephemeris = EPHEMERIS_OVERRIDES.get(name, EPHEMERIDES[parent])
        if name in BARYCENTRIC_MOONS:
            factor = GM_CHARON / (GM_PLUTO + GM_CHARON)
            lines.append(
                '        "barycenter_correction": '
                f'{{"sibling": "charon", "factor": {factor!r}}},\n'
            )
        lines.append(f'        "ref_plane": "{ref_plane}",\n')
        lines.append('        "epoch_jd": J2000_JD,\n')
        lines.append(f'        "ephemeris": "{ephemeris}",\n')
        lines.append('        "source": _FIT_SOURCE,\n')
        lines.append(
            '        "fit": {'
            f'"rms_deg": {fit["rms_deg"]:.4f}, '
            f'"worst_deg": {fit["worst_deg"]:.4f}, '
            f'"worst_dist_rel": {fit["worst_dist_rel"]:.6f}, '
            f'"n_samples": {fit["n_samples"]}}},\n'
        )
        lines.append("    },\n")
    lines.append("}\n")
    MODULE_PATH.write_text("".join(lines), encoding="utf-8")
    print(f"wrote {MODULE_PATH}")


def main():
    if sys.argv[1:] == ["--emit-module"]:
        emit_module()
        return
    targets = sys.argv[1:] or list(BODIES)
    results = {}
    if OUT_PATH.exists():
        results = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    for name in targets:
        results[name] = fit_moon(name)
        OUT_PATH.write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8"
        )
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
