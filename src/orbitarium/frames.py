"""Reference-frame rotations: pure math, no dates, no I/O.

JPL publishes satellite mean elements referred to each moon's local
Laplace plane, whose pole is given in ICRF equatorial coordinates
(R.A., Dec.), with angles measured from the ascending node of that
plane on the ICRF equator. These helpers rotate such vectors into the
ecliptic-J2000 frame used throughout this library.
"""

import math

# IAU76 obliquity of the ecliptic at J2000 (84381.448 arcsec), the same
# value JPL Horizons uses to define its ecliptic-J2000 output frame.
OBLIQUITY_J2000_DEG = 84381.448 / 3600.0
_COS_EPS = math.cos(math.radians(OBLIQUITY_J2000_DEG))
_SIN_EPS = math.sin(math.radians(OBLIQUITY_J2000_DEG))


def equatorial_to_ecliptic(vector):
    """Rotate an ICRF/J2000 equatorial vector into ecliptic-J2000."""
    x, y, z = vector
    return (
        x,
        _COS_EPS * y + _SIN_EPS * z,
        -_SIN_EPS * y + _COS_EPS * z,
    )


def rotation_from_pole(pole_ra_deg, pole_dec_deg):
    """Rotation matrix (rows) from a Laplace-plane frame to equatorial.

    The plane frame has +z along the given pole and +x at the ascending
    node of the plane on the ICRF equator (the JPL convention for
    satellite mean elements).
    """
    ra = math.radians(pole_ra_deg)
    dec = math.radians(pole_dec_deg)
    z_axis = (
        math.cos(dec) * math.cos(ra),
        math.cos(dec) * math.sin(ra),
        math.sin(dec),
    )
    # Ascending node of the plane on the equator: z_eq x z_plane.
    node = (-z_axis[1], z_axis[0], 0.0)
    node_norm = math.hypot(node[0], node[1])
    if node_norm < 1e-12:
        # Plane coincides with the equator; the node is undefined and any
        # equatorial direction serves as x.
        x_axis = (1.0, 0.0, 0.0)
    else:
        x_axis = (node[0] / node_norm, node[1] / node_norm, 0.0)
    y_axis = (
        z_axis[1] * x_axis[2] - z_axis[2] * x_axis[1],
        z_axis[2] * x_axis[0] - z_axis[0] * x_axis[2],
        z_axis[0] * x_axis[1] - z_axis[1] * x_axis[0],
    )
    # Columns are the frame axes; store as rows of the transpose applied
    # in plane_to_ecliptic below.
    return x_axis, y_axis, z_axis


def plane_to_ecliptic(pole_ra_deg, pole_dec_deg, vector):
    """Rotate a vector from a Laplace-plane frame into ecliptic-J2000."""
    x_axis, y_axis, z_axis = rotation_from_pole(pole_ra_deg, pole_dec_deg)
    equatorial = (
        x_axis[0] * vector[0] + y_axis[0] * vector[1] + z_axis[0] * vector[2],
        x_axis[1] * vector[0] + y_axis[1] * vector[1] + z_axis[1] * vector[2],
        x_axis[2] * vector[0] + y_axis[2] * vector[1] + z_axis[2] * vector[2],
    )
    return equatorial_to_ecliptic(equatorial)
