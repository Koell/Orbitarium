import math
import unittest

from orbitarium import lunar

# Meeus, "Astronomical Algorithms" 2nd ed., example 47.a:
# 1992 April 12.0 TD = JDE 2448724.5.
EXAMPLE_47A_T = (2448724.5 - 2451545.0) / 36525.0

DAYS_PER_CENTURY = 36525.0


def norm(v):
    return math.sqrt(sum(c * c for c in v))


class TestEclipticOfDate(unittest.TestCase):
    def test_meeus_example_47a(self):
        # Book values of the mean-equinox-of-date position before nutation:
        # lambda = 133.162655 deg, beta = -3.229126 deg, Delta = 368409.7 km.
        lambda_deg, beta_deg, delta_km = lunar.ecliptic_of_date(EXAMPLE_47A_T)
        self.assertAlmostEqual(lambda_deg, 133.162655, places=6)
        self.assertAlmostEqual(beta_deg, -3.229126, places=6)
        self.assertAlmostEqual(delta_km, 368409.7, places=1)

    def test_distance_and_latitude_bounds_over_metonic_cycle(self):
        # Scan one 19-year Metonic cycle around J2000 in ~7-day steps.
        step = 7.0 / DAYS_PER_CENTURY
        steps = int(19 * 365.25 / 7.0)
        for i in range(steps + 1):
            t = -0.095 + i * step
            lambda_deg, beta_deg, delta_km = lunar.ecliptic_of_date(t)
            self.assertTrue(0.0 <= lambda_deg < 360.0, f"t={t}")
            self.assertLessEqual(abs(beta_deg), 5.5, f"t={t}")
            self.assertTrue(356000.0 <= delta_km <= 407000.0, f"t={t}")


class TestGeocentricState(unittest.TestCase):
    def test_position_matches_spherical_coordinates_at_j2000(self):
        # At T = 0 the equinox of date IS J2000, so the Cartesian position
        # must reproduce the of-date spherical coordinates exactly.
        lambda_deg, beta_deg, delta_km = lunar.ecliptic_of_date(0.0)
        (x, y, z), _ = lunar.geocentric_state(0.0)
        self.assertAlmostEqual(norm((x, y, z)), delta_km, places=6)
        self.assertAlmostEqual(
            math.degrees(math.atan2(y, x)) % 360.0, lambda_deg, places=9
        )
        self.assertAlmostEqual(
            math.degrees(math.asin(z / delta_km)), beta_deg, places=9
        )

    def test_precession_moves_longitude_back_to_j2000(self):
        # One century from J2000 the equinox-of-date longitude leads the
        # J2000 longitude by the general precession, ~1.397 deg/century.
        t = 1.0
        lambda_date, _, _ = lunar.ecliptic_of_date(t)
        (x, y, _), _ = lunar.geocentric_state(t)
        lambda_j2000 = math.degrees(math.atan2(y, x)) % 360.0
        shift = (lambda_date - lambda_j2000) % 360.0
        self.assertAlmostEqual(shift, 5030.2077 / 3600.0, places=4)

    def test_velocity_magnitude_and_direction(self):
        # Mean orbital speed is ~1.022 km/s; it stays within ~0.95-1.1 km/s,
        # and the motion is prograde (angular momentum along +z).
        for t in (-0.9, -0.4, 0.0, 0.13, 0.5):
            pos, vel = lunar.geocentric_state(t)
            speed = norm(vel)
            self.assertTrue(0.9 < speed < 1.15, f"t={t}, speed={speed}")
            h_z = pos[0] * vel[1] - pos[1] * vel[0]
            self.assertGreater(h_z, 0.0, f"t={t}")

    def test_velocity_consistent_with_position_difference(self):
        # The 30 s central difference must agree with an independent
        # 60 s position difference to first order.
        t = 0.0421
        dt = 60.0 / (86400.0 * DAYS_PER_CENTURY)
        pos_before, _ = lunar.geocentric_state(t - dt)
        pos_after, _ = lunar.geocentric_state(t + dt)
        _, vel = lunar.geocentric_state(t)
        for v, p1, p0 in zip(vel, pos_after, pos_before):
            self.assertAlmostEqual(v, (p1 - p0) / 120.0, places=6)


if __name__ == "__main__":
    unittest.main()
