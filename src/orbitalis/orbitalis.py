from datetime import datetime, timezone
from data.celestial_data import CELESTIAL_DATA


class Orbitalis:
    def __init__(self):
        self.celestial_data = CELESTIAL_DATA

    def get_positions(self, timestamp):
        timestamp_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        epoch = datetime(2492, 6, 6, tzinfo=timezone.utc)
        elapsed_days = (timestamp_dt - epoch).total_seconds() / (24 * 3600)
        return self.calculate_positions("sol", self.celestial_data["sol"]["orbitals"], elapsed_days)

    def calculate_positions(self, name, orbitals, elapsed_days):
        positions = {}
        for orbital in orbitals:
            period = orbital["orbital_period"]
            position = (elapsed_days % period) / period * 360
            child_positions = self.calculate_positions(orbital["name"], orbital["orbitals"], elapsed_days)
            positions[orbital["name"]] = {
                "position": round(position, 2),
                "orbitals": child_positions
            }
        return positions
