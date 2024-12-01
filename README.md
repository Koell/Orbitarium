# Orbitarium

**Orbitarium** is a Python library designed to approximate the position of planets and their moons relative to the object they orbit, using a given timestamp. The library provides a JSON dictionary with the positional data of the Solar System’s bodies, including nested orbital objects like moons. This is useful for astronomy enthusiasts, game developers, and educators who want a quick way to calculate and visualize celestial positions without needing a deep understanding of astrophysics.

Features
--------

- Calculates the position of all major planets in the Solar System relative to the Sun.
- Includes positional data for moons relative to their parent planets (e.g., the Moon relative to Earth).
- Outputs positions in degrees, ranging from 0° to 360°.
- Accepts any valid timestamp to get celestial positions at a specific moment.
- Provides results in a structured JSON format for easy integration into other applications or visualizations.

Installation
------------

Install via pip:

```bash
    pip install orbitarium
```

Here's a simple example of how to use Orbitarium:

```python
import orbitarium

instance = orbitarium.Orbitarium()
timestamp = "2024-08-25T00:00:00Z"
positions = instance.get_positions(timestamp)

print(positions)
```

Example Output
--------------

```json
{
  "sol": {
    "position": 0.0,
    "orbitals": [
      {
        "earth": {
          "position": 123.45,
          "orbitals": [
            {
              "luna": {
                "position": 67.89
              }
            }
          ]
        }
      },
      {
        "mars": {
          "position": 234.56
        }
      }
      // Additional planets and their moons here...
    ]
  }
}
```

JSON Structure Explanation
---------------------------

- **sol**: The root object representing the Sun, with its direct orbitals being the planets.
- **orbitals**: A list of celestial objects that orbit the parent object.
  - Each object (like Earth) contains:
    - **position**: The position in degrees (0-360°) relative to the parent object.
    - **orbitals**: (Optional) A nested list of objects that orbit this object (like moons).

How It Works
------------

Orbitarium uses simplified orbital mechanics, leveraging known orbital periods and elliptical characteristics to approximate positions. While it’s not intended for highly precise scientific calculations, it provides accurate enough results for educational and recreational use cases.

Contributing
------------

Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request on the [GitHub repository](https://github.com/koell/orbitarium).

License
-------

Orbitarium is licensed under the GNU General Public License v3.0. See the [LICENSE](https://github.com/koell/orbitarium/blob/main/LICENSE) file for more details.

For more information and detailed documentation, visit the [GitHub repository](https://github.com/koell/orbitarium).
