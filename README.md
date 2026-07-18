# Orbitarium

**Orbitarium** is a zero-dependency Python library that computes real, error-bounded positions and velocities for the Sun's planets and 67 of their moons at any timestamp. It propagates JPL orbital elements with a Kepler solver (plus the Meeus lunar series for Earth's Moon) and is tested against pinned JPL Horizons reference states — the measured worst-case error per body is published below.

Features
--------

- Full state vectors per body: Cartesian position **x, y, z** and distance **r** (km), velocity **vx, vy, vz** (km/s), and true ecliptic longitude/latitude (degrees).
- All state vectors are **parent-centric** (planets relative to the Sun, moons relative to their planet) in the **ecliptic-J2000** axis orientation.
- 76 bodies: all eight planets, Pluto, and 67 moons — every moon with a JPL mean-elements entry, from Ganymede down to sub-kilometre Aegaeon — nested in a tree that mirrors the Solar System's structure.
- A flat, stably-ordered **ML feature vector** (`get_feature_vector` / `feature_names`) for machine-learning pipelines.
- Zero runtime dependencies, pure Python ≥ 3.11. No network access, no kernel files.
- Accuracy demonstrated, not claimed: an offline test suite checks every body against pinned JPL Horizons states at five epochs spanning 1900–2050.

Installation
------------

```bash
pip install orbitarium
```

Quick start
-----------

```python
import orbitarium

instance = orbitarium.Orbitarium()
tree = instance.get_positions("2026-01-01T00:00:00Z")

earth = tree["sol"]["orbitals"]["earth"]
luna = earth["orbitals"]["luna"]
print(f"Earth is {earth['r']:.0f} km from the Sun, ecliptic longitude {earth['lon']:.1f} deg")
print(f"Luna is {luna['r']:.0f} km from Earth")
```

`get_positions` accepts an ISO-8601 string (trailing `Z` accepted) or a `datetime`; naive values are interpreted as UTC. It returns a nested dictionary — every body carries the same ten keys:

```python
{
  "sol": {
    "x": 0.0, "y": 0.0, "z": 0.0, "r": 0.0,          # the root sits at its own origin
    "vx": 0.0, "vy": 0.0, "vz": 0.0,
    "lon": 0.0, "lat": 0.0,
    "orbitals": {
      "mercury": {...},
      "venus": {...},
      "earth": {
        "x": -26071582.2, "y": 144774313.8, "z": -8544.2,   # km, heliocentric, ecliptic-J2000
        "r": 147103125.1,                                    # km
        "vx": -29.8, "vy": -5.4, "vz": 0.0,                  # km/s
        "lon": 100.2, "lat": -0.0,                           # degrees, true ecliptic long/lat
        "orbitals": {
          "luna": {
            "x": 144321.8, "y": 329397.9, "z": 31774.5,      # km, geocentric
            "r": 361028.2,
            "vx": -1.0, "vy": 0.4, "vz": 0.0,
            "lon": 66.3, "lat": 5.0,
            "orbitals": {}
          }
        }
      },
      ...
    }
  }
}
```

(Values above are the actual output for `2026-01-01T00:00:00Z`, rounded for display.)

The ML feature vector
---------------------

For machine-learning consumers there is a flat, stably-ordered interface — no tree flattening needed:

```python
import orbitarium

instance = orbitarium.Orbitarium()
names = instance.feature_names()
vector = instance.get_feature_vector("2026-01-01T00:00:00Z")

print(len(vector))        # 684  (76 orbiting bodies x 9 quantities)
print(names[0], vector[0])  # mercury.x -32195337.59...
```

- Names are dotted `body.quantity` pairs; bodies follow the catalog's depth-first order, and each body contributes `x, y, z, r, vx, vy, vz, lon, lat` in that order.
- Only time-varying quantities appear — no physical constants, and the Sun contributes nothing.
- Values are raw physical units (km, km/s, degrees); normalization is deliberately the consumer's job.
- **The ordering is a public contract from v2.0.0 on**: future minor versions may only append new features at the end; reordering or removal requires a major version.

Accuracy
--------

Measured worst-case deviation from JPL Horizons over five pinned epochs spanning 1900–2050 (angular separation of the position vector, relative distance error, relative velocity-vector error). The test suite enforces tolerances of roughly twice these values; regenerate the table with `python tools/measure_accuracy.py --markdown`.

| Body | Worst angle | Worst distance | Worst velocity | Epochs |
|------|------------:|---------------:|---------------:|-------:|
| mercury | 28″ | 0.002% | 0.01% | 5 |
| venus | 13″ | 0.002% | 0.01% | 5 |
| earth | 6″ | 0.003% | 0.05% | 5 |
| luna | 52″ | 0.002% | 0.02% | 5 |
| mars | 57″ | 0.015% | 0.02% | 5 |
| phobos | 2.57° | 1.036% | 3.06% | 5 |
| deimos | 0.39° | 0.010% | 0.70% | 5 |
| jupiter | 309″ | 0.070% | 0.16% | 5 |
| metis | 1.07° | 0.078% | 1.78% | 5 |
| adrastea | 1.02° | 0.062% | 1.73% | 5 |
| amalthea | 0.68° | 0.258% | 1.56% | 5 |
| thebe | 2.44° | 1.854% | 2.66% | 5 |
| io | 0.52° | 0.440% | 0.90% | 5 |
| europa | 0.83° | 0.948% | 1.37% | 5 |
| ganymede | 0.18° | 0.109% | 0.29% | 5 |
| callisto | 223″ | 0.014% | 0.12% | 5 |
| saturn | 0.15° | 0.132% | 0.38% | 5 |
| pan | 0.51° | 0.001% | 0.88% | 4 |
| daphnis | 0.52° | 0.001% | 0.91% | 1 |
| atlas | 9.43° | 0.270% | 16.23% | 4 |
| prometheus | 16.57° | 0.211% | 28.70% | 4 |
| pandora | 27.84° | 0.499% | 47.79% | 4 |
| janus | 8.95° | 0.580% | 15.10% | 4 |
| epimetheus | 25.28° | 2.398% | 43.33% | 4 |
| aegaeon | 3.35° | 0.072% | 5.84% | 4 |
| mimas | 4.31° | 1.310% | 5.13% | 5 |
| methone | 5.36° | 0.270% | 9.35% | 5 |
| anthe | 11.89° | 0.399% | 20.64% | 4 |
| pallene | 0.89° | 0.285% | 1.27% | 4 |
| enceladus | 0.63° | 0.014% | 1.11% | 5 |
| tethys | 0.19° | 0.014% | 0.32% | 5 |
| telesto | 2.60° | 0.020% | 4.54% | 5 |
| calypso | 2.61° | 0.072% | 4.58% | 5 |
| dione | 0.16° | 0.018% | 0.27% | 5 |
| helene | 9.49° | 1.367% | 16.56% | 5 |
| polydeuces | 0.53° | 0.076% | 0.89% | 5 |
| rhea | 353″ | 0.017% | 0.18% | 5 |
| titan | 206″ | 0.017% | 0.08% | 5 |
| hyperion | 2.24° | 3.247% | 4.11% | 5 |
| iapetus | 0.11° | 0.062% | 0.20% | 5 |
| phoebe | 2.34° | 1.896% | 2.77% | 5 |
| uranus | 79″ | 0.043% | 0.27% | 5 |
| cordelia | 0.91° | 0.038% | 1.54% | 5 |
| ophelia | 2.33° | 0.879% | 2.75% | 5 |
| bianca | 1.43° | 0.709% | 1.89% | 5 |
| cressida | 0.97° | 0.474% | 1.42% | 5 |
| desdemona | 1.24° | 0.668% | 1.67% | 5 |
| juliet | 0.88° | 0.592% | 1.30% | 5 |
| portia | 0.84° | 0.333% | 1.22% | 5 |
| rosalind | 0.67° | 0.264% | 1.10% | 5 |
| cupid | 1.17° | 0.481% | 1.43% | 5 |
| belinda | 0.49° | 0.198% | 0.84% | 5 |
| perdita | 0.74° | 0.329% | 1.10% | 5 |
| puck | 1.31° | 0.878% | 1.43% | 5 |
| mab | 0.80° | 0.499% | 1.03% | 5 |
| miranda | 0.69° | 0.046% | 1.20% | 5 |
| ariel | 0.24° | 0.120% | 0.41% | 5 |
| umbriel | 318″ | 0.104% | 0.13% | 5 |
| titania | 0.16° | 0.096% | 0.24% | 5 |
| oberon | 0.14° | 0.121% | 0.21% | 5 |
| neptune | 45″ | 0.022% | 0.30% | 5 |
| naiad | 1.25° | 0.016% | 2.13% | 5 |
| thalassa | 1.12° | 0.020% | 2.03% | 5 |
| despina | 0.88° | 0.027% | 1.53% | 5 |
| galatea | 0.69° | 0.017% | 1.20% | 5 |
| larissa | 0.77° | 0.083% | 1.06% | 5 |
| hippocamp | 0.36° | 0.014% | 0.87% | 5 |
| proteus | 0.58° | 0.045% | 0.78% | 5 |
| triton | 0.25° | 0.000% | 0.36% | 5 |
| nereid | 4.99° | 4.771% | 5.55% | 5 |
| pluto | 39″ | 0.023% | 0.59% | 5 |
| charon | 178″ | 0.000% | 0.09% | 5 |
| styx | 0.56° | 0.331% | 1.46% | 5 |
| nix | 0.29° | 0.337% | 0.90% | 5 |
| kerberos | 0.25° | 0.359% | 0.61% | 5 |
| hydra | 0.11° | 0.033% | 0.87% | 5 |

(Bodies whose satellite ephemeris does not reach back to 1900 are pinned at fewer epochs — Daphnis's only spans 1990–2018.)

In short: **planets are good to arcseconds–arcminutes, Luna to under an arcminute, and most moons to a degree or better.** The exceptions are physical, not numerical: the co-orbital and chaotic Saturnian moons — the Janus–Epimetheus horseshoe pair (which swap orbits every ~4 years; a two-harmonic libration can only approximate the sawtooth), the formally chaotic Prometheus–Pandora–Atlas group, the Dione trojan Helene, and the Mimas-resonant Anthe — carry worst-case errors of ~9–28°, and Mimas (~44° physical libration), Nereid (a 360-day, e = 0.75 orbit strongly perturbed by the Sun), Methone, and Phobos (Mars J2 short-period terms) sit in the 2–5° range. Every one of these is bounded by the test suite, so a regression past the documented worst case fails CI.

**Validity window: 1800–2050.** Timestamps outside it still compute but emit a `UserWarning` — the element fits degrade gradually beyond their fit spans.

How it works
------------

- **Planets and Pluto** — E. M. Standish's "Keplerian Elements for Approximate Positions of the Major Planets" (JPL): J2000 mean elements plus secular rates, valid 1800–2050, solved with Newton iteration on Kepler's equation and rotated into 3D ecliptic-J2000 states.
- **Luna** — the standard Meeus truncated lunar series (embedded periodic-term tables for longitude, latitude, and distance), accurate to well under an arcminute against Horizons; far beyond what mean elements can do for Earth's strongly perturbed Moon.
- **Moons** — precessing-ellipse mean elements **fit by least squares to JPL Horizons states over 1900–2050** (the committed, reproducible fit tool lives in `tools/fit_satellite_elements.py`). Reference-plane poles and ephemeris IDs come from JPL's Planetary Satellite Mean Elements page; the ellipses themselves are refit because the published table — as its own page warns — is not intended for ephemeris computation (its angles disagree with Horizons by up to ~157° at their own epoch for the Saturnian moons). Physically motivated extra terms are included where a plain ellipse cannot follow the real orbit: explicit mean-longitude libration terms for resonant, trojan, and co-orbital moons (Mimas–Tethys, Titan–Hyperion, the Janus–Epimetheus horseshoe pair, the Tethys and Dione trojans, the small Mimas-resonant moons — which additionally inherit Mimas's 71.8-yr resonance cycle as a second libration frequency — and the chaotic Prometheus–Pandora pair), Phobos's tidal mean-motion acceleration, and barycentric-wobble corrections for Pluto's small moons.
- **Retrograde orbits** (Triton) are represented physically, via inclination > 90°; there are no negative periods.
- **Timescale** — inputs are UTC, used directly where Terrestrial Time is formally required. The ~69 s difference contributes at most ~0.9° for the fastest body (Phobos) and is negligible for everything else; the accuracy table above already **includes** this simplification, since the reference fixtures are pinned at exact TDB instants.
- **Physical constants** — masses, mean radii, and GM values for every body are available as proper floats with cited JPL sources in `orbitarium.data.physical.PHYSICAL`; catalog integrity (required fields, numeric types, sanity ranges, citations) is enforced by `orbitarium.data.catalog.validate()` in CI.

The reference fixtures (five epochs per body, generated once from the JPL Horizons API by `tools/generate_horizons_fixtures.py`) are committed to the repository, so the full test suite runs offline.

Migrating from v1
-----------------

v1 positions were **not physical** — a single 0–360° phase angle computed from an arbitrary epoch in the year 2492. v2 is a clean break: real states, ten numeric fields per body, and the legacy `position` field is gone. `get_positions` keeps its nested tree shape, and `max_range` is still accepted but deprecated (it emits a `DeprecationWarning` and has no effect). See [CHANGELOG.md](CHANGELOG.md) for the full list of changes and migration notes.

Contributing
------------

Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request on the [GitHub repository](https://github.com/koell/orbitarium).

License
-------

Orbitarium is licensed under the GNU General Public License v3.0. See the [LICENSE](https://github.com/koell/orbitarium/blob/main/LICENSE) file for more details.
