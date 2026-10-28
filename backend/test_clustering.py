"""uv run python -m unittest"""
import unittest
from datetime import datetime, timedelta, timezone

from clustering import cluster, weight


def rep(id_, days_ago, lat=49.15, lon=9.22, user=1):
    at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {"id": id_, "lat": lat, "lon": lon, "types": ["noise"], "created_at": at.isoformat(), "user_id": user}


class Clustering(unittest.TestCase):
    def test_recent_counts_the_last_week(self):
        (c,) = cluster([rep(1, 10), rep(2, 8), rep(3, 1), rep(4, 0)])
        self.assertEqual((c["count"], c["recent"]), (4, 2))
        self.assertEqual(c["id"], 1)  # the oldest anchors

    def test_one_voice_per_person_and_day(self):
        (c,) = cluster([rep(1, 0, user=7), rep(2, 0, user=7), rep(3, 0, user=7)])
        self.assertEqual((c["count"], c["people"]), (3, 1))
        self.assertAlmostEqual(c["weight"], 1.0, places=1)  # three taps, one voice
        (c,) = cluster([rep(1, 1, user=7), rep(2, 0, user=7), rep(3, 0, user=8)])
        self.assertEqual(c["people"], 2)
        self.assertAlmostEqual(c["weight"], 2.9, places=1)  # yesterday counts again, 0.9 + 1 + 1

    def test_dominant_type_is_by_people_not_by_tap(self):
        # user 7 taps heat twice, then noise; user 8 says heat: heat is what most people name
        reps = [rep(1, 0.02, user=7), rep(2, 0.01, user=7), rep(3, 0, user=7), rep(4, 0.03, user=8)]
        reps[0]["types"] = reps[1]["types"] = reps[3]["types"] = ["heat"]
        reps[2]["types"] = ["noise"]
        c = cluster(reps)[0]
        self.assertEqual(c["dominant"], "heat")
        self.assertEqual(c["types"], {"heat": 2, "noise": 1})  # people per type, dominant first
        self.assertEqual(c["count"], 4)
        self.assertAlmostEqual(c["weight"], 2.0, places=1)  # two voices, whatever the types

    def test_a_person_naming_two_types_is_one_voice_for_each(self):
        reps = [rep(1, 0, user=7), rep(2, 0, user=8), rep(3, 0, user=8)]
        reps[0]["types"] = ["heat", "noise"]
        reps[1]["types"] = ["air"]
        reps[2]["types"] = ["noise"]  # user 8's later tap, noise now leads with 2 people
        c = cluster(reps)[0]
        self.assertEqual(c["dominant"], "noise")
        self.assertEqual(c["types"], {"noise": 2, "heat": 1, "air": 1})

    def test_mine_counts_the_callers_reports(self):
        reports = [rep(1, 1, user=7), rep(2, 1, user=8), rep(3, 0, user=7)]
        self.assertEqual(cluster(reports, me=7)[0]["mine"], 2)
        self.assertEqual(cluster(reports, me=9)[0]["mine"], 0)
        self.assertEqual(cluster(reports)[0]["mine"], 0)  # no header, nothing is yours

    def test_far_report_opens_a_new_bubble(self):
        a, b = cluster([rep(1, 1), rep(2, 0, lon=9.22 + 0.0021)])  # ~150 m east
        self.assertEqual((a["count"], b["count"]), (1, 1))

    def test_nearest_anchor_wins(self):
        # 3 is 88 m from anchor 1 and 66 m from anchor 2
        out = cluster([rep(1, 2), rep(2, 1, lon=9.22 + 0.0021), rep(3, 0, lon=9.22 + 0.0012)])
        self.assertEqual([c["report_ids"] for c in sorted(out, key=lambda c: c["id"])], [[1], [2, 3]])


if __name__ == "__main__":
    unittest.main()
