"""Geocentric lunar position from the Meeus truncated lunar theory.

Implements Jean Meeus, "Astronomical Algorithms", 2nd ed., chapter 47
("Position of the Moon"): the abridged ELP2000-82 solution with the full
60-term periodic series for longitude/distance (table 47.A) and latitude
(table 47.B). Stated accuracy of the truncation is about 10 arcsec in
longitude and 4 arcsec in latitude.

Coefficient tables and fundamental-argument polynomials were transcribed
from two independent open-source copies of the Meeus tables and found
digit-identical (all 60 + 60 terms, retrieved 2026-07-18):
  * pymeeus (architest/pymeeus, pymeeus/Moon.py)
  * soniakeys/meeus v3 (moonposition/moonposition.go)
The only divergence is the T^2 coefficient of the Sun's mean anomaly
(-0.0001536 vs -0.0001535 deg); the book value -0.0001536 is used.

Meeus refers coordinates to the mean ecliptic and equinox OF DATE. This
library's frame is ecliptic-J2000, so the longitude is precessed from the
equinox of date back to J2000 using the accumulated general precession in
longitude p_A = 5029.0966"*T + 1.11113"*T^2 - 0.000006"*T^3 (Meeus ch. 21).
The latitude is left unchanged: the ecliptic-plane rotation it ignores is
about 47" per century, well below this module's accuracy target.

Like kepler.py this module is pure math: the single time input is Julian
centuries of TT since J2000.0 (as produced by timebase.julian_centuries;
the project-wide UTC-as-TT approximation applies).
"""

import math

_SECONDS_PER_DAY = 86400.0
_DAYS_PER_CENTURY = 36525.0
# Half-step for the symmetric velocity difference: 30 s in Julian centuries.
_VELOCITY_HALF_STEP = 30.0 / (_SECONDS_PER_DAY * _DAYS_PER_CENTURY)

# Mean Earth-Moon distance constant of the theory, km (Meeus eq. 47 text).
_MEAN_DISTANCE_KM = 385000.56

# Table 47.A: arguments are multiples of (D, M, M', F); coefficients are
# the sine coefficient of Sigma_l (1e-6 deg) and the cosine coefficient of
# Sigma_r (1e-3 km).
_TABLE_47A = (
    (0, 0, 1, 0, 6288774, -20905355),
    (2, 0, -1, 0, 1274027, -3699111),
    (2, 0, 0, 0, 658314, -2955968),
    (0, 0, 2, 0, 213618, -569925),
    (0, 1, 0, 0, -185116, 48888),
    (0, 0, 0, 2, -114332, -3149),
    (2, 0, -2, 0, 58793, 246158),
    (2, -1, -1, 0, 57066, -152138),
    (2, 0, 1, 0, 53322, -170733),
    (2, -1, 0, 0, 45758, -204586),
    (0, 1, -1, 0, -40923, -129620),
    (1, 0, 0, 0, -34720, 108743),
    (0, 1, 1, 0, -30383, 104755),
    (2, 0, 0, -2, 15327, 10321),
    (0, 0, 1, 2, -12528, 0),
    (0, 0, 1, -2, 10980, 79661),
    (4, 0, -1, 0, 10675, -34782),
    (0, 0, 3, 0, 10034, -23210),
    (4, 0, -2, 0, 8548, -21636),
    (2, 1, -1, 0, -7888, 24208),
    (2, 1, 0, 0, -6766, 30824),
    (1, 0, -1, 0, -5163, -8379),
    (1, 1, 0, 0, 4987, -16675),
    (2, -1, 1, 0, 4036, -12831),
    (2, 0, 2, 0, 3994, -10445),
    (4, 0, 0, 0, 3861, -11650),
    (2, 0, -3, 0, 3665, 14403),
    (0, 1, -2, 0, -2689, -7003),
    (2, 0, -1, 2, -2602, 0),
    (2, -1, -2, 0, 2390, 10056),
    (1, 0, 1, 0, -2348, 6322),
    (2, -2, 0, 0, 2236, -9884),
    (0, 1, 2, 0, -2120, 5751),
    (0, 2, 0, 0, -2069, 0),
    (2, -2, -1, 0, 2048, -4950),
    (2, 0, 1, -2, -1773, 4130),
    (2, 0, 0, 2, -1595, 0),
    (4, -1, -1, 0, 1215, -3958),
    (0, 0, 2, 2, -1110, 0),
    (3, 0, -1, 0, -892, 3258),
    (2, 1, 1, 0, -810, 2616),
    (4, -1, -2, 0, 759, -1897),
    (0, 2, -1, 0, -713, -2117),
    (2, 2, -1, 0, -700, 2354),
    (2, 1, -2, 0, 691, 0),
    (2, -1, 0, -2, 596, 0),
    (4, 0, 1, 0, 549, -1423),
    (0, 0, 4, 0, 537, -1117),
    (4, -1, 0, 0, 520, -1571),
    (1, 0, -2, 0, -487, -1739),
    (2, 1, 0, -2, -399, 0),
    (0, 0, 2, -2, -381, -4421),
    (1, 1, 1, 0, 351, 0),
    (3, 0, -2, 0, -340, 0),
    (4, 0, -3, 0, 330, 0),
    (2, -1, 2, 0, 327, 0),
    (0, 2, 1, 0, -323, 1165),
    (1, 1, -1, 0, 299, 0),
    (2, 0, 3, 0, 294, 0),
    (2, 0, -1, -2, 0, 8752),
)

# Table 47.B: arguments are multiples of (D, M, M', F); coefficient is the
# sine coefficient of Sigma_b (1e-6 deg).
_TABLE_47B = (
    (0, 0, 0, 1, 5128122),
    (0, 0, 1, 1, 280602),
    (0, 0, 1, -1, 277693),
    (2, 0, 0, -1, 173237),
    (2, 0, -1, 1, 55413),
    (2, 0, -1, -1, 46271),
    (2, 0, 0, 1, 32573),
    (0, 0, 2, 1, 17198),
    (2, 0, 1, -1, 9266),
    (0, 0, 2, -1, 8822),
    (2, -1, 0, -1, 8216),
    (2, 0, -2, -1, 4324),
    (2, 0, 1, 1, 4200),
    (2, 1, 0, -1, -3359),
    (2, -1, -1, 1, 2463),
    (2, -1, 0, 1, 2211),
    (2, -1, -1, -1, 2065),
    (0, 1, -1, -1, -1870),
    (4, 0, -1, -1, 1828),
    (0, 1, 0, 1, -1794),
    (0, 0, 0, 3, -1749),
    (0, 1, -1, 1, -1565),
    (1, 0, 0, 1, -1491),
    (0, 1, 1, 1, -1475),
    (0, 1, 1, -1, -1410),
    (0, 1, 0, -1, -1344),
    (1, 0, 0, -1, -1335),
    (0, 0, 3, 1, 1107),
    (4, 0, 0, -1, 1021),
    (4, 0, -1, 1, 833),
    (0, 0, 1, -3, 777),
    (4, 0, -2, 1, 671),
    (2, 0, 0, -3, 607),
    (2, 0, 2, -1, 596),
    (2, -1, 1, -1, 491),
    (2, 0, -2, 1, -451),
    (0, 0, 3, -1, 439),
    (2, 0, 2, 1, 422),
    (2, 0, -3, -1, 421),
    (2, 1, -1, 1, -366),
    (2, 1, 0, 1, -351),
    (4, 0, 0, 1, 331),
    (2, -1, 1, 1, 315),
    (2, -2, 0, -1, 302),
    (0, 0, 1, 3, -283),
    (2, 1, 1, -1, -229),
    (1, 1, 0, -1, 223),
    (1, 1, 0, 1, 223),
    (0, 1, -2, -1, -220),
    (2, 1, -1, -1, -220),
    (1, 0, 1, 1, -185),
    (2, -1, -2, -1, 181),
    (0, 1, 2, 1, -177),
    (4, 0, -2, -1, 176),
    (4, -1, -1, -1, 166),
    (1, 0, 1, -1, -164),
    (4, 0, 1, -1, 132),
    (1, 0, -1, -1, -119),
    (4, -1, 0, -1, 115),
    (2, -2, 0, 1, 107),
)


def _polynomial(t, coefficients):
    """Evaluate sum(c_k * t**k) by Horner's scheme."""
    result = 0.0
    for coefficient in reversed(coefficients):
        result = result * t + coefficient
    return result


def _fundamental_arguments(t):
    """Meeus eq. 47.1-47.5 plus A1-A3 and E, for T centuries TT since J2000.

    Returns (l_prime, d, m, m_prime, f, a1, a2, a3, e) with all angles in
    degrees (not normalized; only their trig functions are used) and e the
    dimensionless eccentricity factor.
    """
    l_prime = _polynomial(t, (
        218.3164477, 481267.88123421, -0.0015786, 1.0 / 538841, -1.0 / 65194000,
    ))
    d = _polynomial(t, (
        297.8501921, 445267.1114034, -0.0018819, 1.0 / 545868, -1.0 / 113065000,
    ))
    m = _polynomial(t, (357.5291092, 35999.0502909, -0.0001536, 1.0 / 24490000))
    m_prime = _polynomial(t, (
        134.9633964, 477198.8675055, 0.0087414, 1.0 / 69699, -1.0 / 14712000,
    ))
    f = _polynomial(t, (
        93.2720950, 483202.0175233, -0.0036539, -1.0 / 3526000, 1.0 / 863310000,
    ))
    a1 = 119.75 + 131.849 * t
    a2 = 53.09 + 479264.290 * t
    a3 = 313.45 + 481266.484 * t
    e = 1.0 - 0.002516 * t - 0.0000074 * t * t
    return l_prime, d, m, m_prime, f, a1, a2, a3, e


def ecliptic_of_date(julian_centuries_tt):
    """Geocentric ecliptic coordinates of the Moon, mean equinox of date.

    Returns (lambda_deg, beta_deg, delta_km): longitude in [0, 360) and
    latitude in degrees, distance between the centers of the Earth and the
    Moon in km. Nutation is not applied (Meeus ch. 47 before eq. for
    apparent longitude).
    """
    t = julian_centuries_tt
    l_prime, d, m, m_prime, f, a1, a2, a3, e = _fundamental_arguments(t)
    e2 = e * e

    d_rad = math.radians(d)
    m_rad = math.radians(m)
    m_prime_rad = math.radians(m_prime)
    f_rad = math.radians(f)

    # Additive terms: Venus (A1), Jupiter (A2) and flattening (F) effects.
    sigma_l = (
        3958.0 * math.sin(math.radians(a1))
        + 1962.0 * math.sin(math.radians(l_prime - f))
        + 318.0 * math.sin(math.radians(a2))
    )
    sigma_r = 0.0
    sigma_b = (
        -2235.0 * math.sin(math.radians(l_prime))
        + 382.0 * math.sin(math.radians(a3))
        + 175.0 * math.sin(math.radians(a1 - f))
        + 175.0 * math.sin(math.radians(a1 + f))
        + 127.0 * math.sin(math.radians(l_prime - m_prime))
        - 115.0 * math.sin(math.radians(l_prime + m_prime))
    )

    for mult_d, mult_m, mult_m_prime, mult_f, coeff_l, coeff_r in _TABLE_47A:
        argument = (
            mult_d * d_rad
            + mult_m * m_rad
            + mult_m_prime * m_prime_rad
            + mult_f * f_rad
        )
        # Terms with the Sun's mean anomaly decay with orbital eccentricity.
        scale = e if abs(mult_m) == 1 else e2 if abs(mult_m) == 2 else 1.0
        sigma_l += coeff_l * scale * math.sin(argument)
        sigma_r += coeff_r * scale * math.cos(argument)

    for mult_d, mult_m, mult_m_prime, mult_f, coeff_b in _TABLE_47B:
        argument = (
            mult_d * d_rad
            + mult_m * m_rad
            + mult_m_prime * m_prime_rad
            + mult_f * f_rad
        )
        scale = e if abs(mult_m) == 1 else e2 if abs(mult_m) == 2 else 1.0
        sigma_b += coeff_b * scale * math.sin(argument)

    lambda_deg = (l_prime + sigma_l * 1e-6) % 360.0
    beta_deg = sigma_b * 1e-6
    delta_km = _MEAN_DISTANCE_KM + sigma_r * 1e-3
    return lambda_deg, beta_deg, delta_km


def _precession_in_longitude_deg(t):
    """Accumulated general precession in longitude from J2000 to date, deg.

    p_A polynomial from Meeus ch. 21 (linear rate 5029.0966"/century).
    """
    return _polynomial(t, (0.0, 5029.0966, 1.11113, -0.000006)) / 3600.0


def _position_j2000(t):
    """Geocentric position vector (km) in the ecliptic-J2000 frame."""
    lambda_date, beta_deg, delta_km = ecliptic_of_date(t)
    # Rotate the equinox of date back to J2000; the ~47"/century tilt
    # between the two ecliptic planes is neglected (see module docstring).
    lambda_rad = math.radians(lambda_date - _precession_in_longitude_deg(t))
    beta_rad = math.radians(beta_deg)
    cos_beta = math.cos(beta_rad)
    return (
        delta_km * cos_beta * math.cos(lambda_rad),
        delta_km * cos_beta * math.sin(lambda_rad),
        delta_km * math.sin(beta_rad),
    )


def geocentric_state(julian_centuries_tt):
    """Geocentric state vector of the Moon, ecliptic-J2000 frame.

    Returns ((x, y, z), (vx, vy, vz)) in km and km/s. The velocity is a
    symmetric finite difference of the position over +/- 30 seconds.
    """
    t = julian_centuries_tt
    position = _position_j2000(t)
    before = _position_j2000(t - _VELOCITY_HALF_STEP)
    after = _position_j2000(t + _VELOCITY_HALF_STEP)
    velocity = tuple((a - b) / 60.0 for a, b in zip(after, before))
    return position, velocity
