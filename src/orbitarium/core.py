from datetime import datetime, timezone
from data.celestial_data import CELESTIAL_DATA


class Orbitarium:
    def __init__(self):
        self.celestial_data = CELESTIAL_DATA
        self.epoch = datetime(2492, 6, 6, tzinfo=timezone.utc)

    def get_positions(self, date, max_range=360):
        if isinstance(date, str):
            if date.endswith("Z"):
                date = date.replace("Z", "+00:00")
            date = datetime.fromisoformat(date)
        elif not isinstance(date, datetime):
            raise TypeError("date must be a str or datetime object")

        elapsed_days = (date - self.epoch).total_seconds() / (24 * 3600)
        orbits = {"sol": {
            "position": 0.0,
            "orbitals": self.calculate_positions(self.celestial_data["sol"]["orbitals"], elapsed_days, max_range)}
        }
        return orbits

    def calculate_positions(self,orbitals, elapsed_days, max_range=360):
        positions = {}
        for orbital in orbitals:
            period = orbital["orbital_period"]
            position = (elapsed_days % period) / period * max_range
            child_positions = self.calculate_positions(orbital["orbitals"], elapsed_days)
            positions[orbital["name"]] = {
                "position": round(position, 2),
                "orbitals": child_positions
            }
        return positions
