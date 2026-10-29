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


if __name__ == "__main__":
    unittest.main()
