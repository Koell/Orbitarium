"""Generate pinned JPL Horizons reference fixtures for the accuracy suite.

Queries the Horizons API (https://ssd.jpl.nasa.gov/api/horizons.api) for
geometric state vectors (ecliptic-J2000, km, km/s) and writes one JSON file
per body under tests/fixtures/horizons/. CI never runs this script; it
consumes the committed fixtures offline. Re-run only to regenerate.

Usage: python tools/generate_horizons_fixtures.py [body ...]
"""

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "horizons"
API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

J2000_JD = 2451545.0
J2000_EPOCH = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
# TT - UTC since 2017 (37 leap seconds + 32.184 s); Horizons TLIST is TDB≈TT.
TT_MINUS_UTC_DAYS = 69.184 / 86400.0

# body -> (Horizons COMMAND, Horizons CENTER); planet body centers,
# heliocentric (Sun body center); moons parent-body-centered.
BODIES = {
    "mercury": ("199", "500@10"),
    "venus": ("299", "500@10"),
    "earth": ("399", "500@10"),
    "mars": ("499", "500@10"),
    "jupiter": ("599", "500@10"),
    "saturn": ("699", "500@10"),
    "uranus": ("799", "500@10"),
    "neptune": ("899", "500@10"),
    "pluto": ("999", "500@10"),
    # moons
    "luna": ("301", "500@399"),
    "phobos": ("401", "500@499"),
    "deimos": ("402", "500@499"),
    "metis": ("516", "500@599"),
    "adrastea": ("515", "500@599"),
    "amalthea": ("505", "500@599"),
    "thebe": ("514", "500@599"),
    "io": ("501", "500@599"),
    "europa": ("502", "500@599"),
    "ganymede": ("503", "500@599"),
    "callisto": ("504", "500@599"),
    "pan": ("618", "500@699"),
    "daphnis": ("635", "500@699"),
    "atlas": ("615", "500@699"),
    "prometheus": ("616", "500@699"),
    "pandora": ("617", "500@699"),
    "janus": ("610", "500@699"),
    "epimetheus": ("611", "500@699"),
    "aegaeon": ("653", "500@699"),
    "mimas": ("601", "500@699"),
    "methone": ("632", "500@699"),
    "anthe": ("649", "500@699"),
    "pallene": ("633", "500@699"),
    "enceladus": ("602", "500@699"),
    "tethys": ("603", "500@699"),
    "telesto": ("613", "500@699"),
    "calypso": ("614", "500@699"),
    "dione": ("604", "500@699"),
    "helene": ("612", "500@699"),
    "polydeuces": ("634", "500@699"),
    "rhea": ("605", "500@699"),
    "titan": ("606", "500@699"),
    "hyperion": ("607", "500@699"),
    "iapetus": ("608", "500@699"),
    "phoebe": ("609", "500@699"),
    "cordelia": ("706", "500@799"),
    "ophelia": ("707", "500@799"),
    "bianca": ("708", "500@799"),
    "cressida": ("709", "500@799"),
    "desdemona": ("710", "500@799"),
    "juliet": ("711", "500@799"),
    "portia": ("712", "500@799"),
    "rosalind": ("713", "500@799"),
    "cupid": ("727", "500@799"),
    "belinda": ("714", "500@799"),
    "perdita": ("725", "500@799"),
    "puck": ("715", "500@799"),
    "mab": ("726", "500@799"),
    "miranda": ("705", "500@799"),
    "ariel": ("701", "500@799"),
    "umbriel": ("702", "500@799"),
    "titania": ("703", "500@799"),
    "oberon": ("704", "500@799"),
    "naiad": ("803", "500@899"),
    "thalassa": ("804", "500@899"),
    "despina": ("805", "500@899"),
    "galatea": ("806", "500@899"),
    "larissa": ("807", "500@899"),
    "hippocamp": ("814", "500@899"),
    "proteus": ("808", "500@899"),
    "triton": ("801", "500@899"),
    "nereid": ("802", "500@899"),
    "charon": ("901", "500@999"),
    "nix": ("902", "500@999"),
    "hydra": ("903", "500@999"),
    "kerberos": ("904", "500@999"),
    "styx": ("905", "500@999"),
}

# UTC epochs; spread across the 1800-2050 validity window.
EPOCHS_UTC = [
    "1900-06-15T00:00:00+00:00",
    "1950-01-01T00:00:00+00:00",
    "2000-01-01T12:00:00+00:00",
    "2026-01-01T00:00:00+00:00",
    "2049-12-31T00:00:00+00:00",
]


def julian_date_utc(iso_utc):
    moment = datetime.fromisoformat(iso_utc)
    return J2000_JD + (moment - J2000_EPOCH).total_seconds() / 86400.0


def fetch_state(command, center, jd_tdb):
    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": f"'{center}'",
        "REF_PLANE": "'ECLIPTIC'",
        "REF_SYSTEM": "'J2000'",
        "VEC_TABLE": "'2'",
        "OUT_UNITS": "'KM-S'",
        "CSV_FORMAT": "'YES'",
        "TLIST": f"'{jd_tdb:.9f}'",
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode())
    text = payload["result"]
    block = text.split("$$SOE")[1].split("$$EOE")[0].strip()
    fields = [f.strip() for f in block.split(",")]
    # JDTDB, calendar date, X, Y, Z, VX, VY, VZ, (trailing empty)
    return {
        "x_km": float(fields[2]),
        "y_km": float(fields[3]),
        "z_km": float(fields[4]),
        "vx_km_s": float(fields[5]),
        "vy_km_s": float(fields[6]),
        "vz_km_s": float(fields[7]),
    }


def generate(body):
    command, center = BODIES[body]
    records = []
    for iso_utc in EPOCHS_UTC:
        jd_tdb = julian_date_utc(iso_utc) + TT_MINUS_UTC_DAYS
        try:
            state = fetch_state(command, center, jd_tdb)
        except (IndexError, KeyError, ValueError) as error:
            # Epoch outside the span of this body's satellite ephemeris.
            print(f"  {body} @ {iso_utc}: unavailable ({type(error).__name__}), skipped")
            continue
        records.append({"utc": iso_utc, "jd_tdb": jd_tdb, **state})
        print(f"  {body} @ {iso_utc}: r=({state['x_km']:.0f}, {state['y_km']:.0f}, {state['z_km']:.0f}) km")
    if not records:
        print(f"  {body}: no states available, fixture not written")
        return
    fixture = {
        "body": body,
        "horizons_command": command,
        "horizons_center": center,
        "frame": "ecliptic-J2000, parent-centered",
        "units": {"position": "km", "velocity": "km/s"},
        "source": "JPL Horizons API (DE441), geometric states, TLIST in TDB",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "states": records,
    }
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR / f"{body}.json"
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    targets = sys.argv[1:] or list(BODIES)
    for name in targets:
        generate(name)
