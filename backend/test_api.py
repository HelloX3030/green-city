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

    def test_name_is_the_account(self):
        self.assertIsNone(self.c.get("/me", headers=A).json()["name"])
        self.assertEqual(self.c.patch("/me", json={"name": " Kim "}, headers=A).json()["name"], "Kim")
        self.assertEqual(self.c.get("/me", headers=A).json()["name"], "Kim")
        self.assertIsNone(self.c.patch("/me", json={"name": ""}, headers=A).json()["name"])

    def test_link_joins_the_devices_and_their_reports(self):
        self.c.post("/reports", json=REPORT, headers=A)
        self.c.post("/reports", json={**REPORT, "message": "from b"}, headers=B)
        code = self.c.post("/me/link", headers=A).json()["code"]
        self.assertEqual(len(code), 6)
        self.assertEqual(self.c.post("/me/claim", json={"code": code.lower()}, headers=B).json()["id"], self.c.get("/me", headers=A).json()["id"])
        self.assertEqual(self.c.get("/me", headers=A).json()["devices"], 2)
        self.assertEqual(len(self.c.get("/reports/mine", headers=A).json()), 2)  # b's report came along
        self.assertEqual(len(self.c.get("/reports/mine", headers=B).json()), 2)
        self.assertEqual(self.c.get("/clusters", headers=B).json()[0]["mine"], 2)
        self.assertEqual(self.c.post("/me/claim", json={"code": code}, headers=B).status_code, 400)  # spent
        self.assertEqual(self.c.post("/me/claim", json={"code": "ZZZZZZ"}, headers=B).status_code, 400)

    def test_expired_code_is_refused(self):
        code = self.c.post("/me/link", headers=A).json()["code"]
        with db.connect() as con:
            con.execute("UPDATE links SET expires_at = '2000-01-01T00:00:00+00:00'")
        self.assertEqual(self.c.post("/me/claim", json={"code": code}, headers=B).status_code, 400)

    def test_withdraw_only_your_own(self):
        rid = self.c.post("/reports", json=REPORT, headers=A).json()["id"]
        self.assertEqual(self.c.delete(f"/reports/{rid}", headers=B).status_code, 404)
        self.assertEqual(self.c.delete(f"/reports/{rid}").status_code, 400)
        self.assertEqual(self.c.delete(f"/reports/{rid}", headers=A).status_code, 204)
        self.assertEqual(self.c.delete(f"/reports/{rid}", headers=A).status_code, 404)
        self.assertEqual(self.c.get("/reports/mine", headers=A).json(), [])


if __name__ == "__main__":
    unittest.main()
