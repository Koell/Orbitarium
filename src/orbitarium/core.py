from datetime import datetime, timezone
from data.celestial_data import CELESTIAL_DATA


class Orbitarium:
    def __init__(self):
        self.celestial_data = CELESTIAL_DATA
        self.epoch = datetime(2492, 6, 6, tzinfo=timezone.utc)

    def get_positions(self, timestamp):
        timestamp_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elapsed_days = (timestamp_dt - self.epoch).total_seconds() / (24 * 3600)
        orbits = {"sol": {
            "position": 0.0,
            "orbitals": self.calculate_positions(self.celestial_data["sol"]["orbitals"], elapsed_days)}
        }
        return orbits

    def calculate_positions(self,orbitals, elapsed_days):
        positions = {}
        for orbital in orbitals:
            period = orbital["orbital_period"]
            position = (elapsed_days % period) / period * 360
            child_positions = self.calculate_positions(orbital["orbitals"], elapsed_days)
            positions[orbital["name"]] = {
                "position": round(position, 2),
                "orbitals": child_positions
            }
        return positions
