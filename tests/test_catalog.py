import copy
import unittest
from unittest import mock

from orbitarium.data import catalog
from orbitarium.data.catalog import BODIES_WITHOUT_GM, CatalogError
from orbitarium.data.celestial_data import CELESTIAL_DATA
from orbitarium.data.physical import G_KM3_KG_S2, PHYSICAL
from orbitarium.data.satellites import SATELLITE_ELEMENTS

PLANETS = (
    "mercury", "venus", "earth", "mars", "jupiter",
    "saturn", "uranus", "neptune", "pluto",
)


def catalog_body_names():
    """All body names in the CELESTIAL_DATA tree, plus the root 'sol'."""
    names = ["sol"]

    def walk(node):
        for child in node.get("orbitals", []):
            names.append(child["name"])
            walk(child)

    walk(CELESTIAL_DATA["sol"])
    return names


class TestCatalogCoverage(unittest.TestCase):
    def test_every_catalog_body_has_physical_entry(self):
        for name in catalog_body_names():
            self.assertIn(name, PHYSICAL)

    def test_catalog_names_are_lowercase(self):
        for name in catalog_body_names():
            self.assertEqual(name, name.lower())


class TestPhysicalValues(unittest.TestCase):
    def test_gm_values_are_positive_floats_or_documented_none(self):
        for name, entry in PHYSICAL.items():
            gm = entry["gm_km3_s2"]
            if name in BODIES_WITHOUT_GM:
                self.assertIsNone(gm, name)
            else:
                self.assertIsInstance(gm, float, name)
                self.assertGreater(gm, 0.0, name)

    def test_radius_values_are_positive_floats(self):
        for name, entry in PHYSICAL.items():
            radius = entry["radius_km"]
            self.assertIsInstance(radius, float, name)
            self.assertGreater(radius, 0.0, name)

    def test_every_entry_has_nonempty_source(self):
        for name, entry in PHYSICAL.items():
            self.assertIsInstance(entry["source"], str, name)
            self.assertTrue(entry["source"].strip(), name)


class TestCatalogValidation(unittest.TestCase):
    """The integrity-validation entry point enforces the data contract."""

    def test_shipped_catalog_validates(self):
        catalog.validate()  # must not raise

    def _assert_invalid(self, patched_name, broken, message_part):
        with mock.patch.object(catalog, patched_name, broken):
            with self.assertRaisesRegex(CatalogError, message_part):
                catalog.validate()

    def test_missing_physical_entry_fails(self):
        broken = {k: v for k, v in PHYSICAL.items() if k != "titan"}
        self._assert_invalid("PHYSICAL", broken, "titan: missing physical")

    def test_unit_embedded_string_fails(self):
        broken = copy.deepcopy(PHYSICAL)
        broken["earth"]["radius_km"] = "6,371 km"
        self._assert_invalid("PHYSICAL", broken, "earth: radius")

    def test_negative_gm_fails(self):
        broken = copy.deepcopy(PHYSICAL)
        broken["mars"]["gm_km3_s2"] = -1.0
        self._assert_invalid("PHYSICAL", broken, "mars: GM")

    def test_empty_source_fails(self):
        broken = copy.deepcopy(PHYSICAL)
        broken["venus"]["source"] = "  "
        self._assert_invalid("PHYSICAL", broken, "venus: .*source")

    def test_missing_satellite_field_fails(self):
        broken = copy.deepcopy(SATELLITE_ELEMENTS)
        del broken["triton"]["mean_motion_deg_per_day"]
        self._assert_invalid(
            "SATELLITE_ELEMENTS", broken, "triton: element mean_motion"
        )

    def test_negative_period_convention_fails(self):
        # Retrograde orbits must use inclination > 90 deg, never negative
        # mean motions / periods.
        broken = copy.deepcopy(SATELLITE_ELEMENTS)
        broken["triton"]["mean_motion_deg_per_day"] *= -1.0
        self._assert_invalid(
            "SATELLITE_ELEMENTS", broken, "triton: mean motion"
        )


class TestRetrogradeConvention(unittest.TestCase):
    def test_triton_is_retrograde_via_inclination(self):
        self.assertGreater(SATELLITE_ELEMENTS["triton"]["i_deg"], 90.0)

    def test_no_negative_rates_of_mean_motion(self):
        for name, entry in SATELLITE_ELEMENTS.items():
            self.assertGreater(entry["mean_motion_deg_per_day"], 0.0, name)


class TestSanityRanges(unittest.TestCase):
    def test_sol_gm(self):
        gm = PHYSICAL["sol"]["gm_km3_s2"]
        self.assertAlmostEqual(gm / 1.32712440e11, 1.0, places=6)

    def test_planet_gm_range(self):
        # Lower bound accommodates Pluto's planet-only (excluding Charon)
        # DE440 GM of ~869.6 km^3/s^2; upper bound is just above Jupiter's.
        for name in PLANETS:
            gm = PHYSICAL[name]["gm_km3_s2"]
            self.assertGreater(gm, 8e2, name)
            self.assertLess(gm, 1.3e8, name)

    def test_radius_range(self):
        # Lower bound accommodates Aegaeon (~0.33 km mean radius).
        for name, entry in PHYSICAL.items():
            self.assertGreater(entry["radius_km"], 0.1, name)
            self.assertLess(entry["radius_km"], 700000.0, name)

    def test_mass_derived_consistently_from_gm(self):
        # mass_kg must equal GM / G for every body: the mass/GM ratio is a
        # single constant (1/G) across all bodies to ~1e-6 relative.
        expected_ratio = 1.0 / G_KM3_KG_S2
        for name, entry in PHYSICAL.items():
            gm, mass = entry["gm_km3_s2"], entry["mass_kg"]
            if gm is None:
                self.assertIsNone(mass, name)
                continue
            self.assertIsInstance(mass, float, name)
            ratio = mass / gm
            self.assertAlmostEqual(
                ratio / expected_ratio, 1.0, places=6, msg=name
            )


if __name__ == "__main__":
    unittest.main()
