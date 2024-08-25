import unittest
from orbitalis.core import Orbitalis

class TestOrbitalis(unittest.TestCase):
    def test_positions(self):
        orbitalis = Orbitalis()
        timestamp = "2024-08-25T00:00:00Z"
        positions = orbitalis.get_positions(timestamp)
        self.assertIn("earth", positions["sol"]["orbitals"])
        self.assertIn("luna", positions["sol"]["orbitals"]["earth"]["orbitals"])

if __name__ == "__main__":
    unittest.main()
