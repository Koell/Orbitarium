"""Keplerian two-body propagation: pure math, no dates, no I/O.

All functions work in radians, km, km/s. The output frame is the parent-
centered frame whose axes match the orientation the input angles are
referred to (ecliptic-J2000 for every table shipped with this package).
"""

import math

_KEPLER_TOL = 1e-12
_KEPLER_MAX_ITER = 100


def solve_kepler(mean_anomaly, eccentricity):
    """Solve E - e*sin(E) = M for the eccentric anomaly E (radians).

    Newton iteration; converges to _KEPLER_TOL for all elliptical
    eccentricities (0 <= e < 1).
    """
    if not 0.0 <= eccentricity < 1.0:
        raise ValueError(f"eccentricity must be in [0, 1), got {eccentricity}")
    mean_anomaly = math.remainder(mean_anomaly, math.tau)
    # Sign-matched pi is a safe start for high eccentricities where E=M
    # diverges (an unsigned pi start diverges for negative anomalies,
    # e.g. M=-2.88, e=0.95).
    eccentric_anomaly = (
        mean_anomaly
        if eccentricity < 0.8
        else math.copysign(math.pi, mean_anomaly)
    )
    for _ in range(_KEPLER_MAX_ITER):
        residual = (
            eccentric_anomaly
            - eccentricity * math.sin(eccentric_anomaly)
            - mean_anomaly
        )
        eccentric_anomaly -= residual / (
            1.0 - eccentricity * math.cos(eccentric_anomaly)
        )
        if abs(residual) < _KEPLER_TOL:
            return eccentric_anomaly
    raise ArithmeticError(
        f"Kepler solver did not converge (M={mean_anomaly}, e={eccentricity})"
    )


def elements_to_state(a, e, inclination, node, arg_periapsis, mean_anomaly, mu):
    """Convert osculating elements to a Cartesian state vector.

    Parameters: semi-major axis a (km), eccentricity e, inclination,
    longitude of ascending node, argument of periapsis, mean anomaly
    (all radians), and the parent's gravitational parameter mu (km^3/s^2).

    Returns ((x, y, z), (vx, vy, vz)) in km and km/s.
    """
    E = solve_kepler(mean_anomaly, e)
    cos_e, sin_e = math.cos(E), math.sin(E)
    b_over_a = math.sqrt(1.0 - e * e)

    # Perifocal coordinates (periapsis on +x axis).
    x_pf = a * (cos_e - e)
    y_pf = a * b_over_a * sin_e

    mean_motion = math.sqrt(mu / a**3)
    e_dot = mean_motion / (1.0 - e * cos_e)
    vx_pf = -a * sin_e * e_dot
    vy_pf = a * b_over_a * cos_e * e_dot

    cw, sw = math.cos(arg_periapsis), math.sin(arg_periapsis)
    co, so = math.cos(node), math.sin(node)
    ci, si = math.cos(inclination), math.sin(inclination)

    # Rotation Rz(-node) * Rx(-i) * Rz(-arg_periapsis), rows applied to (x_pf, y_pf).
    r11 = cw * co - sw * so * ci
    r12 = -sw * co - cw * so * ci
    r21 = cw * so + sw * co * ci
    r22 = -sw * so + cw * co * ci
    r31 = sw * si
    r32 = cw * si

    position = (
        r11 * x_pf + r12 * y_pf,
        r21 * x_pf + r22 * y_pf,
        r31 * x_pf + r32 * y_pf,
    )
    velocity = (
        r11 * vx_pf + r12 * vy_pf,
        r21 * vx_pf + r22 * vy_pf,
        r31 * vx_pf + r32 * vy_pf,
    )
    return position, velocity
