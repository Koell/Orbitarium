import unittest
from orbitarium.core import Orbitarium

class TestOrbitarium(unittest.TestCase):
    def test_positions(self):
        orbitalis = Orbitarium()
        timestamp = "2024-08-25T00:00:00Z"
        positions = orbitalis.get_positions(timestamp)
        self.assertIn("earth", positions["sol"]["orbitals"])
        self.assertIn("luna", positions["sol"]["orbitals"]["earth"]["orbitals"])

if __name__ == "__main__":
    unittest.main()
