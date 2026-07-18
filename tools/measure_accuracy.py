"""Report measured worst-case errors per body against the pinned fixtures.

Runs fully offline against the committed Horizons fixtures and prints the
worst angular separation, relative distance error, and relative velocity
error per body over all pinned epochs -- the numbers behind the README
accuracy table and the tolerances in tests/test_accuracy.py.

Usage: python tools/measure_accuracy.py [--markdown]
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from orbitarium.core import Orbitarium, _FEATURE_BODIES  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "horizons"

# Report in the catalog's depth-first body order (the feature-vector order).
BODY_ORDER = {name: index for index, name in enumerate(_FEATURE_BODIES)}


def norm(v):
    return math.sqrt(sum(c * c for c in v))


def angular_separation_deg(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    cos_angle = max(-1.0, min(1.0, dot / (norm(a) * norm(b))))
    return math.degrees(math.acos(cos_angle))


def find_body(tree, name):
    for body_name, state in tree.items():
        if body_name == name:
            return state
        found = find_body(state.get("orbitals", {}), name)
        if found is not None:
            return found
    return None


def measure():
    orbitarium = Orbitarium()
    rows = []
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        body = fixture["body"]
        worst_angle = worst_dist = worst_vel = 0.0
        for record in fixture["states"]:
            state = find_body(orbitarium.get_positions(record["utc"]), body)
            computed_pos = (state["x"], state["y"], state["z"])
            computed_vel = (state["vx"], state["vy"], state["vz"])
            reference_pos = (record["x_km"], record["y_km"], record["z_km"])
            reference_vel = (
                record["vx_km_s"], record["vy_km_s"], record["vz_km_s"],
            )
            worst_angle = max(
                worst_angle, angular_separation_deg(computed_pos, reference_pos)
            )
            worst_dist = max(
                worst_dist,
                abs(norm(computed_pos) - norm(reference_pos)) / norm(reference_pos),
            )
            worst_vel = max(
                worst_vel,
                norm(tuple(c - r for c, r in zip(computed_vel, reference_vel)))
                / norm(reference_vel),
            )
        rows.append((body, worst_angle, worst_dist, worst_vel, len(fixture["states"])))
    rows.sort(key=lambda row: BODY_ORDER.get(row[0], len(BODY_ORDER)))
    return rows


def main():
    markdown = "--markdown" in sys.argv[1:]
    rows = measure()
    if markdown:
        print("| Body | Worst angle | Worst distance | Worst velocity | Epochs |")
        print("|------|------------:|---------------:|---------------:|-------:|")
        for body, angle, dist, vel, n in rows:
            angle_text = (
                f"{angle * 3600:.0f}″" if angle < 0.1 else f"{angle:.2f}°"
            )
            print(
                f"| {body} | {angle_text} | {dist * 100:.3f}% |"
                f" {vel * 100:.2f}% | {n} |"
            )
    else:
        print(f"{'body':<10} {'ang_deg':>10} {'dist_rel':>10} {'vel_rel':>10} {'epochs':>7}")
        for body, angle, dist, vel, n in rows:
            print(f"{body:<10} {angle:>10.4f} {dist:>10.5f} {vel:>10.5f} {n:>7}")


if __name__ == "__main__":
    main()
