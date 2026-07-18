import unittest
import warnings
from datetime import datetime, timezone

from orbitarium.core import Orbitarium

STATE_FIELDS = ("x", "y", "z", "r", "vx", "vy", "vz", "lon", "lat")

# The feature-vector ordering contract, pinned in full: catalog depth-first
# body order x quantity order. Appending at the end is allowed in a minor
# version; any other change to this list is a breaking change.
FEATURE_BODY_ORDER = (
    "mercury", "venus",
    "earth", "luna",
    "mars", "phobos", "deimos",
    "jupiter", "metis", "adrastea", "amalthea", "thebe",
    "io", "europa", "ganymede", "callisto",
    "saturn", "pan", "daphnis", "atlas", "prometheus", "pandora",
    "janus", "epimetheus", "aegaeon", "mimas", "methone", "anthe",
    "pallene", "enceladus", "tethys", "telesto", "calypso",
    "dione", "helene", "polydeuces", "rhea", "titan", "hyperion",
    "iapetus", "phoebe",
    "uranus", "cordelia", "ophelia", "bianca", "cressida", "desdemona",
    "juliet", "portia", "rosalind", "cupid", "belinda", "perdita",
    "puck", "mab", "miranda", "ariel", "umbriel", "titania", "oberon",
    "neptune", "naiad", "thalassa", "despina", "galatea", "larissa",
    "hippocamp", "proteus", "triton", "nereid",
    "pluto", "charon", "styx", "nix", "kerberos", "hydra",
)
EXPECTED_FEATURE_NAMES = [
    f"{body}.{quantity}"
    for body in FEATURE_BODY_ORDER
    for quantity in STATE_FIELDS
]


class TestGetPositionsSchema(unittest.TestCase):
    def setUp(self):
        self.orbitarium = Orbitarium()
        self.tree = self.orbitarium.get_positions("2026-01-01T00:00:00Z")

    def test_tree_shape(self):
        self.assertIn("sol", self.tree)
        self.assertIn("earth", self.tree["sol"]["orbitals"])
        self.assertIn("luna", self.tree["sol"]["orbitals"]["earth"]["orbitals"])

    def test_sol_is_origin(self):
        for field in STATE_FIELDS:
            self.assertEqual(self.tree["sol"][field], 0.0)

    def test_migrated_body_has_full_state(self):
        earth = self.tree["sol"]["orbitals"]["earth"]
        for field in STATE_FIELDS:
            self.assertIn(field, earth)
            self.assertIsInstance(earth[field], float)
        self.assertGreater(earth["r"], 1.4e8)  # ~1 au in km
        self.assertLess(earth["r"], 1.6e8)
        self.assertTrue(0.0 <= earth["lon"] < 360.0)
        self.assertTrue(-90.0 <= earth["lat"] <= 90.0)



class TestFeatureVector(unittest.TestCase):
    def setUp(self):
        self.orbitarium = Orbitarium()

    def test_names_match_pinned_ordering_contract(self):
        self.assertEqual(self.orbitarium.feature_names(), EXPECTED_FEATURE_NAMES)

    def test_vector_and_names_have_equal_length(self):
        vector = self.orbitarium.get_feature_vector("2026-01-01T00:00:00Z")
        names = self.orbitarium.feature_names()
        self.assertEqual(len(vector), len(names))
        self.assertEqual(len(vector), 76 * len(STATE_FIELDS))

    def test_values_are_floats(self):
        vector = self.orbitarium.get_feature_vector("2026-01-01T00:00:00Z")
        for value in vector:
            self.assertIsInstance(value, float)

    def test_sun_and_constants_absent(self):
        for name in self.orbitarium.feature_names():
            body, quantity = name.split(".")
            self.assertNotEqual(body, "sol")
            self.assertIn(quantity, STATE_FIELDS)

    def test_deterministic(self):
        a = self.orbitarium.get_feature_vector("2026-01-01T00:00:00Z")
        b = self.orbitarium.get_feature_vector("2026-01-01T00:00:00Z")
        self.assertEqual(a, b)

    def test_names_stable_across_instances(self):
        self.assertEqual(
            self.orbitarium.feature_names(), Orbitarium().feature_names()
        )

    def test_consistent_with_get_positions(self):
        timestamp = "2026-01-01T00:00:00Z"
        vector = self.orbitarium.get_feature_vector(timestamp)
        tree = self.orbitarium.get_positions(timestamp)
        names = self.orbitarium.feature_names()

        def find(orbitals, target):
            for body, state in orbitals.items():
                if body == target:
                    return state
                found = find(state["orbitals"], target)
                if found is not None:
                    return found
            return None

        for name, value in zip(names, vector):
            body, quantity = name.split(".")
            state = find(tree["sol"]["orbitals"], body)
            self.assertIsNotNone(state, body)
            self.assertEqual(value, state[quantity], name)

    def test_names_returns_a_fresh_list(self):
        names = self.orbitarium.feature_names()
        names.append("tampered")
        self.assertNotEqual(names, self.orbitarium.feature_names())


class TestGetPositionsBehavior(unittest.TestCase):
    def setUp(self):
        self.orbitarium = Orbitarium()

    def test_deterministic(self):
        a = self.orbitarium.get_positions("2026-01-01T00:00:00Z")
        b = self.orbitarium.get_positions("2026-01-01T00:00:00Z")
        self.assertEqual(a, b)

    def test_string_and_datetime_inputs_agree(self):
        from_string = self.orbitarium.get_positions("2026-01-01T00:00:00Z")
        from_datetime = self.orbitarium.get_positions(
            datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(from_string, from_datetime)

    def test_rejects_invalid_type(self):
        with self.assertRaises(TypeError):
            self.orbitarium.get_positions(42)

    def test_max_range_deprecated_and_ignored(self):
        with self.assertWarns(DeprecationWarning):
            scaled = self.orbitarium.get_positions("2026-01-01T00:00:00Z", 1000)
        plain = self.orbitarium.get_positions("2026-01-01T00:00:00Z")
        self.assertEqual(scaled, plain)

    def test_no_deprecation_warning_without_max_range(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            self.orbitarium.get_positions("2026-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
