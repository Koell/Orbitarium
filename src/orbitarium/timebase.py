"""Timestamp parsing and time-scale conversion.

Timestamps are interpreted as UTC and used directly where Terrestrial Time
(TT) is formally required. The difference (~69 s in the 2020s) contributes
an error far below the library's stated accuracy (see README accuracy
notes), so no leap-second handling is performed.
"""

import warnings
from datetime import datetime, timezone

J2000_JD = 2451545.0
J2000_EPOCH = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)

# Validity window of the JPL mean-element tables (years, inclusive).
VALID_YEAR_MIN = 1800
VALID_YEAR_MAX = 2050

SECONDS_PER_DAY = 86400.0
DAYS_PER_CENTURY = 36525.0


def parse_timestamp(value):
    """Return an aware UTC datetime from an ISO-8601 string or datetime.

    Naive datetimes and ISO strings without an offset are interpreted as UTC.
    """
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise TypeError("date must be a str or datetime object")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def julian_date(moment):
    """Julian date of an aware datetime (UTC treated as TT)."""
    return J2000_JD + (moment - J2000_EPOCH).total_seconds() / SECONDS_PER_DAY


def julian_centuries(moment):
    """Julian centuries since J2000.0.

    Emits a UserWarning outside the 1800-2050 element validity window;
    the result is still returned (accuracy degrades gradually).
    """
    if not VALID_YEAR_MIN <= moment.year <= VALID_YEAR_MAX:
        warnings.warn(
            f"{moment.isoformat()} is outside the {VALID_YEAR_MIN}-{VALID_YEAR_MAX} "
            "validity window of the orbital element tables; accuracy is degraded",
            UserWarning,
            stacklevel=2,
        )
    return (julian_date(moment) - J2000_JD) / DAYS_PER_CENTURY
