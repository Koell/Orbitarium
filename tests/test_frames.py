import math
import unittest

from orbitarium import frames

# Ecliptic north pole in ICRF equatorial coordinates.
ECLIPTIC_POLE_RA = 270.0
ECLIPTIC_POLE_DEC = 90.0 - frames.OBLIQUITY_J2000_DEG


def norm(v):
    return math.sqrt(sum(c * c for c in v))


class TestEquatorialToEcliptic(unittest.TestCase):
    def test_x_axis_invariant(self):
        self.assertEqual(frames.equatorial_to_ecliptic((1.0, 0.0, 0.0)), (1.0, 0.0, 0.0))

    def test_celestial_pole_maps_to_obliquity(self):
        x, y, z = frames.equatorial_to_ecliptic((0.0, 0.0, 1.0))
        self.assertAlmostEqual(x, 0.0, places=12)
        self.assertAlmostEqual(y, math.sin(math.radians(frames.OBLIQUITY_J2000_DEG)), places=12)
        self.assertAlmostEqual(z, math.cos(math.radians(frames.OBLIQUITY_J2000_DEG)), places=12)

    def test_preserves_norm(self):
        v = (3.0, -4.0, 12.0)
        self.assertAlmostEqual(norm(frames.equatorial_to_ecliptic(v)), norm(v), places=12)


class TestPlaneToEcliptic(unittest.TestCase):
    def test_ecliptic_pole_gives_identity(self):
        # A "Laplace plane" that IS the ecliptic: the composite rotation
        # must be the identity (x lands on the equinox).
        for v in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.3, -0.4, 0.5)):
            out = frames.plane_to_ecliptic(ECLIPTIC_POLE_RA, ECLIPTIC_POLE_DEC, v)
            for got, expected in zip(out, v):
                self.assertAlmostEqual(got, expected, places=9)

    def test_celestial_pole_equals_plain_equatorial_rotation(self):
        # A plane that IS the equator: plane frame == equatorial frame.
        v = (0.2, 0.7, -0.5)
        out = frames.plane_to_ecliptic(0.0, 90.0, v)
        expected = frames.equatorial_to_ecliptic(v)
        for got, want in zip(out, expected):
            self.assertAlmostEqual(got, want, places=12)

    def test_rotation_is_orthonormal(self):
        axes = frames.rotation_from_pole(123.4, -56.7)
        for i, a in enumerate(axes):
            self.assertAlmostEqual(norm(a), 1.0, places=12)
            for b in axes[i + 1:]:
                dot = sum(x * y for x, y in zip(a, b))
                self.assertAlmostEqual(dot, 0.0, places=12)

    def test_pole_z_maps_to_pole_direction(self):
        ra, dec = 40.0, 75.0
        out = frames.plane_to_ecliptic(ra, dec, (0.0, 0.0, 1.0))
        expected_eq = (
            math.cos(math.radians(dec)) * math.cos(math.radians(ra)),
            math.cos(math.radians(dec)) * math.sin(math.radians(ra)),
            math.sin(math.radians(dec)),
        )
        expected = frames.equatorial_to_ecliptic(expected_eq)
        for got, want in zip(out, expected):
            self.assertAlmostEqual(got, want, places=12)


if __name__ == "__main__":
    unittest.main()
