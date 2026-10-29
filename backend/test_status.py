import unittest
from unittest import mock

import status


class UnitsTest(unittest.TestCase):
    def test_a_unit_stays_with_its_number(self):
        with mock.patch.object(status, "_assess", return_value=("confirmed", "NoiseNode (40 m): an 2 von 2 Tagen im Mittel über 55 dB(A).")):
            _, reason = status.assess(49.14, 9.22, "noise")
        self.assertEqual(reason, "NoiseNode (40 m): an 2 von 2 Tagen im Mittel über 55 dB(A).")

    def test_other_spaces_stay(self):
        with mock.patch.object(status, "_assess", return_value=("unconfirmed", "Messrad 3 kam Mo 08:10 vorbei: PM2,5 12,0 µg/m³, 1,2 km und 30 °C.")):
            _, reason = status.assess(49.14, 9.22, "air")
        self.assertEqual(reason, "Messrad 3 kam Mo 08:10 vorbei: PM2,5 12,0 µg/m³, 1,2 km und 30 °C.")

    def test_no_reason(self):
        self.assertEqual(status.assess(49.14, 9.22, "other"), (None, None))


class UnmeasuredTest(unittest.TestCase):
    """Müll and a broken road: no sensor measures them, so the status says so instead of pretending."""

    def test_trash(self):
        self.assertEqual(status.assess(49.14, 9.22, "trash"), ("no_data", "Kein Sensor misst Müll. Hier fehlt eine Messung."))

    def test_road(self):
        self.assertEqual(status.assess(49.14, 9.22, "road"), ("no_data", "Kein Sensor misst den Straßenzustand. Hier fehlt eine Messung."))


class ShadeTest(unittest.TestCase):
    """Kein Schatten is checked against the Baumkataster: the trees within 100 m."""

    def setUp(self):
        status._trees.cache_clear()
        self.addCleanup(status._trees.cache_clear)

    def assess(self, trees):
        rows = [[9.22 + dx / 73_000, 49.14 + dy / 111_000] for dx, dy in trees]  # metres east, north
        with mock.patch.object(status.Path, "read_text", return_value=status.json.dumps(rows)):
            return status.assess(49.14, 9.22, "no_shade")

    def test_few_trees_confirm(self):
        self.assertEqual(self.assess([(0, 0), (60, 0), (0, -90)]), ("confirmed", "Baumkataster: nur 3 Stadtbäume im Umkreis von 100 m."))

    def test_trees_further_away_dont_count(self):
        self.assertEqual(self.assess([(150, 0), (0, 120)]), ("confirmed", "Baumkataster: kein Stadtbaum im Umkreis von 100 m."))

    def test_one_tree(self):
        self.assertEqual(self.assess([(-95, 0)])[1], "Baumkataster: nur 1 Stadtbaum im Umkreis von 100 m.")

    def test_a_lined_street_does_not(self):
        street = [(x, y) for x in range(-90, 91, 10) for y in (-8, 8)]
        self.assertEqual(self.assess(street), ("unconfirmed", "Baumkataster: 38 Stadtbäume im Umkreis von 100 m."))

    def test_without_the_file_no_data(self):
        with mock.patch.object(status.Path, "read_text", side_effect=FileNotFoundError):
            self.assertEqual(status.assess(49.14, 9.22, "no_shade")[0], "no_data")


if __name__ == "__main__":
    unittest.main()
