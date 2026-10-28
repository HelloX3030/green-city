"""uv run python -m unittest"""
import unittest
from datetime import datetime, timedelta, timezone

from clustering import cluster


def rep(id_, days_ago, lat=49.15, lon=9.22):
    at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {"id": id_, "lat": lat, "lon": lon, "types": ["noise"], "created_at": at.isoformat()}


class Clustering(unittest.TestCase):
    def test_recent_counts_the_last_week(self):
        (c,) = cluster([rep(1, 10), rep(2, 8), rep(3, 1), rep(4, 0)])
        self.assertEqual((c["count"], c["recent"]), (4, 2))
        self.assertEqual(c["id"], 1)  # the oldest anchors

    def test_far_report_opens_a_new_bubble(self):
        a, b = cluster([rep(1, 1), rep(2, 0, lon=9.22 + 0.0021)])  # ~150 m east
        self.assertEqual((a["count"], b["count"]), (1, 1))

    def test_nearest_anchor_wins(self):
        # 3 is 88 m from anchor 1 and 66 m from anchor 2
        out = cluster([rep(1, 2), rep(2, 1, lon=9.22 + 0.0021), rep(3, 0, lon=9.22 + 0.0012)])
        self.assertEqual([c["report_ids"] for c in sorted(out, key=lambda c: c["id"])], [[1], [2, 3]])


if __name__ == "__main__":
    unittest.main()
