==========================
Usage
==========================

Using Orbitarium is simple. Here's a quick start:

.. code-block:: python

    from orbitarium import Orbitarium

    instance = Orbitarium()
    timestamp = "2026-01-01T00:00:00Z"
    tree = instance.get_positions(timestamp)

    earth = tree["sol"]["orbitals"]["earth"]
    luna = earth["orbitals"]["luna"]
    print(earth["r"], earth["lon"])   # 147103125.08... 100.24...
    print(luna["r"])                  # 361028.19...

``get_positions`` accepts an ISO-8601 string (trailing ``Z`` accepted) or
a ``datetime``; naive values are interpreted as UTC. The result is a
nested dictionary in which every body carries the same ten keys --
``x, y, z, r`` (km), ``vx, vy, vz`` (km/s), ``lon, lat`` (degrees), and
``orbitals`` with its children. States are parent-centered (planets
heliocentric, moons planetocentric) in the ecliptic-J2000 orientation:

.. code-block:: json

    {
      "sol": {
        "x": 0.0, "y": 0.0, "z": 0.0, "r": 0.0,
        "vx": 0.0, "vy": 0.0, "vz": 0.0,
        "lon": 0.0, "lat": 0.0,
        "orbitals": {
          "earth": {
            "x": -26071582.2, "y": 144774313.8, "z": -8544.2,
            "r": 147103125.1,
            "vx": -29.8, "vy": -5.4, "vz": 0.0,
            "lon": 100.2, "lat": -0.0,
            "orbitals": {
              "luna": {
                "x": 144321.8, "y": 329397.9, "z": 31774.5,
                "r": 361028.2,
                "vx": -1.0, "vy": 0.4, "vz": 0.0,
                "lon": 66.3, "lat": 5.0,
                "orbitals": {}
              }
            }
          }
        }
      }
    }

(Excerpt of the actual output for ``2026-01-01T00:00:00Z``, rounded for
display; the other planets appear alongside ``earth`` in the same shape.)

For machine-learning pipelines there is a flat, stably-ordered feature
vector -- see the README's "The ML feature vector" section:

.. code-block:: python

    names = instance.feature_names()          # ["mercury.x", ..., "hydra.lat"]
    vector = instance.get_feature_vector(timestamp)
    assert len(names) == len(vector) == 684   # 76 orbiting bodies x 9

Timestamps outside 1800--2050 still compute but emit a ``UserWarning``,
because the underlying orbital-element fits degrade beyond that window.
