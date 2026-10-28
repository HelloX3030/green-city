import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import db
import main

A = {"x-device": "a" * 32}
B = {"x-device": "b" * 32}
REPORT = {"lat": 49.15, "lon": 9.22, "types": ["noise"]}


class Api(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self.tmp.name) / "t.db"
        db.init()
        self.c = TestClient(main.app)  # no lifespan: no sensor history, no bike fetch

    def tearDown(self):
        self.tmp.cleanup()

    def test_mine_per_cluster_and_my_reports(self):
        self.c.post("/reports", json=REPORT, headers=A)
        self.c.post("/reports", json=REPORT, headers=A)
        self.c.post("/reports", json={**REPORT, "message": "b"}, headers=B)
        (c,) = self.c.get("/clusters", headers=A).json()
        self.assertEqual((c["count"], c["mine"]), (3, 2))
        self.assertEqual(self.c.get("/clusters", headers=B).json()[0]["mine"], 1)
        self.assertEqual(self.c.get("/clusters").json()[0]["mine"], 0)
        self.assertEqual(self.c.get("/clusters", headers={"x-device": "c" * 32}).json()[0]["mine"], 0)
        mine = self.c.get("/reports/mine", headers=B).json()
        self.assertEqual([r["message"] for r in mine], ["b"])
        self.assertNotIn("user_id", mine[0])
        self.assertNotIn("user_id", self.c.get("/reports").json()[0])
        self.assertEqual(self.c.get("/reports/mine").status_code, 400)
        self.assertEqual(self.c.get("/clusters", headers={"x-device": "short"}).status_code, 400)

    def test_withdraw_only_your_own(self):
        rid = self.c.post("/reports", json=REPORT, headers=A).json()["id"]
        self.assertEqual(self.c.delete(f"/reports/{rid}", headers=B).status_code, 404)
        self.assertEqual(self.c.delete(f"/reports/{rid}").status_code, 400)
        self.assertEqual(self.c.delete(f"/reports/{rid}", headers=A).status_code, 204)
        self.assertEqual(self.c.delete(f"/reports/{rid}", headers=A).status_code, 404)
        self.assertEqual(self.c.get("/reports/mine", headers=A).json(), [])


if __name__ == "__main__":
    unittest.main()
