==========================
Usage
==========================

Using Orbitalis is simple. Here's a quick start:

.. code-block:: python

    from orbitalis import Orbitalis

    orbitalis = Orbitalis()
    timestamp = "2024-08-25T00:00:00Z"
    positions = orbitalis.get_positions(timestamp)

    print(positions)

The result is a JSON dictionary with the positions of the planets and their moons:

.. code-block:: json

    {
      "sol": {
        "orbitals": {
            "earth": {
                "position": 123.45,
                "orbitals": {
                    "luna": {
                        "position": 67.89
                    }
                }
            },
            "mars": {
                "position": 234.56
            }
        }
      }
    }
