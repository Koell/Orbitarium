# Changelog

## 2.0.0

A deliberate clean break: Orbitarium goes from a toy phase approximation to a real, error-bounded ephemeris. If you consumed v1 output, read the migration notes below — the output schema changed for every body.

### Why v1 outputs were not physical

v1 returned a single `position` scalar (0–360°) per body, computed as uniform circular motion from an arbitrary epoch in the year **2492**, with every body assumed to be at 0° at that epoch. Only the periodicity was real; the absolute angles corresponded to nothing in the sky. Orbital periods were truncated to integer days, and the catalog stored masses and radii as unit-embedded strings (`"5.972 x 10^24 kg"`) that nothing could compute with.

v1 also had a known defect: the `max_range` scaling parameter was not propagated into the recursive moon calculation, so **moons were always scaled to 360 regardless of the caller's `max_range`**, silently producing inconsistently scaled outputs. v2 removes the mechanism rather than fixing it.

### What replaces it

- **Real states from JPL data.** Planets and Pluto: Standish J2000 mean elements + secular rates (valid 1800–2050) through a Kepler solver. Luna: the Meeus truncated lunar series. The other 66 moons: precessing-ellipse elements fit against JPL Horizons states over 1900–2050 (see `tools/fit_satellite_elements.py`; the published JPL mean-elements table is unusable for position computation, as documented in `orbitarium/data/satellites.py`). Resonant, trojan, and co-orbital moons carry explicit mean-longitude libration terms; Phobos a tidal mean-motion acceleration; Pluto's small moons a barycentric-wobble correction.
- **Accuracy is tested, not claimed.** Every body is checked against pinned JPL Horizons fixtures at up to five epochs spanning 1900–2050; the measured worst-case error per body is published in the README accuracy table. Planets: arcseconds–arcminutes. Luna: < 1′. Most moons: a degree or better. The co-orbital and chaotic Saturnian moons (Janus–Epimetheus horseshoe pair, Prometheus–Pandora–Atlas group, Helene, Anthe) are physically unpredictable by any mean-element model and carry documented worst cases of ~9–28°.
- **Full state vectors.** Each body now carries `x, y, z, r` (km), `vx, vy, vz` (km/s), `lon, lat` (degrees) — parent-centered, ecliptic-J2000 orientation.
- **ML feature vector.** New `get_feature_vector(date)` and `feature_names()`: a flat, stably-ordered vector of 684 features (76 orbiting bodies × 9 time-varying quantities) in raw physical units. The ordering is a public contract: minor versions may only append at the end. Planets are ordered by distance from the Sun, moons by mean distance from their parent (co-orbital companions follow the body whose orbit they share).
- **Numeric catalog.** All unit-embedded strings are gone. Physical constants (GM, mass, radius) are floats with cited JPL sources and retrieval dates in `orbitarium.data.physical.PHYSICAL`; `orbitarium.data.catalog.validate()` enforces the data contract in CI.
- **Retrograde orbits** are expressed via inclination > 90° (Triton); the v1 negative-period convention is gone.
- **Validity window.** Dates outside 1800–2050 still compute but emit a `UserWarning` about degraded accuracy.

### Migration guide (v1 → v2)

| v1 | v2 |
|----|----|
| `body["position"]` (0–360 phase angle) | **Removed.** Use `body["lon"]` for true ecliptic longitude, or `x/y/z` for geometry. There is no continuity between v1 phases and v2 angles — v1 values were fictional. |
| `get_positions(date, max_range=...)` | `max_range` is accepted but **deprecated**: it emits a `DeprecationWarning` and has no effect on output. It will be removed in a later major version. |
| Tree shape `{"sol": {"orbitals": {...}}}` | Unchanged — traversal code keeps working; each leaf just carries ten numeric fields instead of one. |
| Catalog strings (`"149.6 million km"`) | Floats in documented units: `orbitarium.data.physical.PHYSICAL[name]["radius_km"]` etc. |
| `from data.celestial_data import ...` (top-level `data` package) | Bundled data now lives under the package namespace: `from orbitarium.data.celestial_data import ...`. |
| Python ≥ 3.6 | Python ≥ **3.11**. |

### Notes for ML consumers (Dice_ml)

Feature pipelines should switch from tree flattening to `get_feature_vector` + `feature_names`. Input dimensionality grows from 37 (one angle per body + extras) to 684; models must be retrained from scratch — v1-trained checkpoints encode fictional positions and cannot be compared across the schema change. Normalization is explicitly the consumer's responsibility (compute statistics on your training split and persist them with the checkpoint).

## 1.0.1

Legacy line. Phase-angle approximation with the 2492 epoch; superseded by 2.0.0.
