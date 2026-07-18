import math
import unittest

from orbitarium import kepler

MU = 1.32712440041e11  # km^3/s^2
AU_KM = 149_597_870.7


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(v):
    return math.sqrt(sum(c * c for c in v))


class TestSolveKepler(unittest.TestCase):
    def test_residual_over_grid(self):
        # e=0.95 at negative anomalies is a regression case: the solver's
        # old unsigned-pi start diverged there (M=-165 deg, e=0.95).
        for e in (0.0, 0.0167, 0.2, 0.6, 0.9, 0.95, 0.99):
            for m_deg in range(-180, 181, 15):
                m = math.radians(m_deg)
                E = kepler.solve_kepler(m, e)
                residual = E - e * math.sin(E) - math.remainder(m, math.tau)
                self.assertLess(abs(residual), 1e-10, f"e={e}, M={m_deg}")

    def test_circular_orbit_identity(self):
        for m_deg in (0, 45, 123, 300):
            m = math.remainder(math.radians(m_deg), math.tau)
            self.assertAlmostEqual(kepler.solve_kepler(m, 0.0), m, places=12)

    def test_rejects_non_elliptical(self):
        with self.assertRaises(ValueError):
            kepler.solve_kepler(1.0, 1.0)
        with self.assertRaises(ValueError):
            kepler.solve_kepler(1.0, -0.1)


class TestElementsToState(unittest.TestCase):
    def test_circular_orbit_geometry(self):
        a = AU_KM
        pos, vel = kepler.elements_to_state(a, 0.0, 0.0, 0.0, 0.0, math.radians(90), MU)
        self.assertAlmostEqual(norm(pos) / a, 1.0, places=12)
        self.assertAlmostEqual(norm(vel) / math.sqrt(MU / a), 1.0, places=12)
        radial_speed = sum(p * v for p, v in zip(pos, vel)) / norm(pos)
        self.assertLess(abs(radial_speed), 1e-9)

    def test_vis_viva(self):
        a, e = 1.5 * AU_KM, 0.3
        for m_deg in (0, 30, 90, 180, 270):
            pos, vel = kepler.elements_to_state(
                a, e, math.radians(10), math.radians(40), math.radians(70),
                math.radians(m_deg), MU,
            )
            r, v2 = norm(pos), sum(c * c for c in vel)
            expected = MU * (2.0 / r - 1.0 / a)
            self.assertAlmostEqual(v2 / expected, 1.0, places=10, msg=f"M={m_deg}")

    def test_angular_momentum_conserved(self):
        a, e = 5.2 * AU_KM, 0.048
        expected_h = math.sqrt(MU * a * (1.0 - e * e))
        for m_deg in (0, 60, 180, 300):
            pos, vel = kepler.elements_to_state(
                a, e, math.radians(1.3), math.radians(100), math.radians(275),
                math.radians(m_deg), MU,
            )
            self.assertAlmostEqual(norm(cross(pos, vel)) / expected_h, 1.0, places=10)

    def test_periapsis_and_apoapsis_distances(self):
        a, e = 2.0 * AU_KM, 0.5
        peri, _ = kepler.elements_to_state(a, e, 0.1, 0.2, 0.3, 0.0, MU)
        apo, _ = kepler.elements_to_state(a, e, 0.1, 0.2, 0.3, math.pi, MU)
        self.assertAlmostEqual(norm(peri) / (a * (1 - e)), 1.0, places=12)
        self.assertAlmostEqual(norm(apo) / (a * (1 + e)), 1.0, places=12)

    def test_period_recovery(self):
        a, e = AU_KM, 0.0167
        args = (math.radians(5), math.radians(30), math.radians(102), MU)
        p1, v1 = kepler.elements_to_state(a, e, *args[:3], math.radians(77), MU)
        p2, v2 = kepler.elements_to_state(a, e, *args[:3], math.radians(77) + math.tau, MU)
        for c1, c2 in zip(p1 + v1, p2 + v2):
            self.assertAlmostEqual(c1, c2, places=6)

    def test_retrograde_inclination_flips_orbit_normal(self):
        a = AU_KM
        pos, vel = kepler.elements_to_state(a, 0.1, math.radians(157), 0.5, 1.0, 2.0, MU)
        h = cross(pos, vel)
        self.assertLess(h[2], 0.0, "i > 90 deg must give retrograde (h_z < 0)")


if __name__ == "__main__":
    unittest.main()
