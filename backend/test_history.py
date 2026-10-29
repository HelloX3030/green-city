import unittest

import history


class FoldTest(unittest.TestCase):
    """The daily values come from the 6-hour series, the UBA 6-hour series from its hourly values."""

    def test_days_max_or_mean(self):
        coarse = {"2026-03-01T00:00Z": 2.0, "2026-03-01T06:00Z": 5.0, "2026-03-01T12:00Z": 9.0, "2026-03-02T00:00Z": 4.0}
        self.assertEqual(history.fold_days(coarse, "max"), {"2026-03-01": 9.0, "2026-03-02": 4.0})
        self.assertEqual(history.fold_days(coarse, "arithmeticMean"), {"2026-03-01": 5.3, "2026-03-02": 4.0})

    def test_windows_from_hours(self):
        hourly = {"2026-03-01T05:00Z": 2, "2026-03-01T06:00Z": 4, "2026-03-01T11:00Z": 6, "2026-03-01T12:00Z": 1}
        self.assertEqual(history.fold_windows(hourly), {"2026-03-01T00:00Z": 2.0, "2026-03-01T06:00Z": 5.0, "2026-03-01T12:00Z": 1.0})

    def test_clean_rounds_cuts_and_drops_gaps(self):
        rows = {"2026-10-27T23:45:00.000Z": 64.51818, "2026-10-28T00:00:00.000Z": None}
        self.assertEqual(history._clean(rows, 16), {"2026-10-27T23:45Z": 64.5})
        self.assertEqual(history._clean({"2026-03-01T00:00:00.000Z": 3.25}, 10), {"2026-03-01": 3.2})


if __name__ == "__main__":
    unittest.main()


class SeedTest(unittest.TestCase):
    """Synthetic demo values under phenomena.<key>.seed are merged under the real ones: a real value always
    wins, the seed ends at the first real timestamp, so a refresh of the real series never erases or
    doubles it."""

    P = {"fine": {"2026-10-27T23:30Z": 65.1, "2026-10-28T00:00Z": None, "2026-10-28T00:15Z": 66.0},
         "coarse": {"2026-10-27T18:00Z": 66.1},
         "daily": {"2026-10-27": 66.1},
         "seed": {"until": "2026-10-27T23:30Z",
                  "fine": {"2026-10-27T23:15Z": 58.0, "2026-10-27T23:30Z": 99.0, "2026-10-28T00:00Z": 99.0},
                  "coarse": {"2026-10-27T12:00Z": 64.0, "2026-10-27T18:00Z": 99.0},
                  "daily": {"2026-10-26": 63.5, "2026-10-27": 99.0}}}

    def test_real_wins_and_the_seed_ends_at_the_first_real_value(self):
        self.assertEqual(history.values(self.P, "fine"), {"2026-10-27T23:15Z": 58.0, "2026-10-27T23:30Z": 65.1, "2026-10-28T00:15Z": 66.0})
        self.assertEqual(history.values(self.P, "coarse"), {"2026-10-27T12:00Z": 64.0, "2026-10-27T18:00Z": 66.1})
        self.assertEqual(history.values(self.P, "daily"), {"2026-10-26": 63.5, "2026-10-27": 66.1})

    def test_the_old_hourly_series_stands_in_for_a_missing_fine_one(self):
        self.assertEqual(history.values({"hourly": {"2026-10-28T10:00Z": 3}}, "fine"), {"2026-10-28T10:00Z": 3})
        self.assertEqual(history.values({"hourly": {"a": 1}, "fine": {"b": 2}}, "fine"), {"b": 2})
        self.assertEqual(history.values({"hourly": {"a": 1}}, "coarse"), {})

    def test_without_a_seed(self):
        self.assertEqual(history.values({"fine": {"a": 1, "b": None}}, "fine"), {"a": 1})
        self.assertEqual(history.values({}, "coarse"), {})
