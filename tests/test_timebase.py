import unittest
import warnings
from datetime import datetime, timezone, timedelta

from orbitarium import timebase


class TestParseTimestamp(unittest.TestCase):
    def test_iso_string_with_z_suffix(self):
        parsed = timebase.parse_timestamp("2026-01-01T00:00:00Z")
        self.assertEqual(parsed, datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_iso_string_with_offset_normalized_to_utc(self):
        parsed = timebase.parse_timestamp("2026-01-01T02:00:00+02:00")
        self.assertEqual(parsed, datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_naive_string_treated_as_utc(self):
        parsed = timebase.parse_timestamp("2026-01-01T00:00:00")
        self.assertEqual(parsed, datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_naive_datetime_treated_as_utc(self):
        parsed = timebase.parse_timestamp(datetime(2026, 1, 1))
        self.assertEqual(parsed, datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_aware_datetime_converted_to_utc(self):
        aware = datetime(2026, 1, 1, 2, tzinfo=timezone(timedelta(hours=2)))
        parsed = timebase.parse_timestamp(aware)
        self.assertEqual(parsed, datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_rejects_other_types(self):
        with self.assertRaises(TypeError):
            timebase.parse_timestamp(1234567890)


class TestJulianConversion(unittest.TestCase):
    def test_j2000_epoch(self):
        j2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
        self.assertEqual(timebase.julian_date(j2000), 2451545.0)
        self.assertEqual(timebase.julian_centuries(j2000), 0.0)

    def test_known_julian_date(self):
        moment = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(timebase.julian_date(moment), 2461041.5)

    def test_century_scale(self):
        moment = datetime(2100, 1, 1, 12, tzinfo=timezone.utc)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            centuries = timebase.julian_centuries(moment)
        self.assertAlmostEqual(centuries, 1.0, places=3)


class TestValidityWindow(unittest.TestCase):
    def test_warns_outside_window(self):
        for year in (1750, 2100):
            with self.assertWarns(UserWarning):
                timebase.julian_centuries(datetime(year, 6, 1, tzinfo=timezone.utc))

    def test_silent_inside_window(self):
        for year in (1800, 1950, 2026, 2050):
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                timebase.julian_centuries(datetime(year, 6, 1, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
