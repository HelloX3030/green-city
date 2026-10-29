import asyncio
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import db
import history
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
        history.CACHE_PATH = Path(self.tmp.name) / "none.json"  # the cache is whatever a test puts in
        history._cache = {"boxes": {}, "uba": {}}

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

    def test_a_bubbles_reports_mine_first_then_newest_without_author(self):
        self.c.post("/reports", json={**REPORT, "message": "first"}, headers=A)
        self.c.post("/reports", json={**REPORT, "types": ["heat"]}, headers=B)
        self.c.post("/reports", json={**REPORT, "lon": 9.24, "message": "elsewhere"}, headers=B)
        (near, far) = sorted(self.c.get("/clusters").json(), key=lambda c: c["id"])
        rows = self.c.get(f"/clusters/{near['id']}/reports").json()
        self.assertEqual([(r["message"], r["mine"]) for r in rows], [(None, False), ("first", False)])
        self.assertNotIn("user_id", rows[0])
        rows = self.c.get(f"/clusters/{near['id']}/reports", headers=A).json()
        self.assertEqual([(r["message"], r["mine"]) for r in rows], [("first", True), (None, False)])
        self.assertEqual(self.c.get(f"/clusters/{far['id']}/reports").json()[0]["message"], "elsewhere")
        self.assertEqual(self.c.get("/clusters/999/reports").status_code, 404)

    def test_blank_text_is_no_text_and_each_type_counts_once(self):
        r = self.c.post("/reports", json={**REPORT, "message": "   ", "types": ["noise", "noise"]}, headers=A).json()
        self.assertEqual((r["message"], r["types"]), (None, ["noise"]))
        r = self.c.post("/reports", json={**REPORT, "message": "  Baustelle \n"}, headers=A).json()
        self.assertEqual(r["message"], "Baustelle")

    def test_events_stream_says_when_reports_change(self):
        async def run():
            ev = main.Events()
            ev.loop = asyncio.get_running_loop()
            gen = ev.stream()
            first = await gen.__anext__()
            await asyncio.to_thread(ev.publish, "reports")  # as the endpoints do, from a worker thread
            line = await asyncio.wait_for(gen.__anext__(), 2)
            await gen.aclose()
            return first, line, ev.subs

        first, line, subs = asyncio.run(run())
        self.assertTrue(first.startswith("retry:"))
        self.assertTrue(line.startswith("event: reports\ndata: "))
        self.assertEqual(subs, set())  # gone after the close
        main.events.publish("reports")  # no loop in the tests: a no-op, not an error

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

    def test_sensor_history_sorted_without_gaps_404_for_unknown(self):
        history._cache = {
            "boxes": {"box1": {"name": "x", "lat": 49.1, "lon": 9.2, "phenomena": {
                "temp": {"daily": {"2026-03-02": 7.5, "2026-03-01": 3, "2026-03-03": None},
                         "hourly": {"2026-10-28T10:00Z": 12.0, "2026-10-28T09:00Z": 11.0}},
                "pm25": {"daily": {}},
            }}},
            "uba": {"pm25": {"daily": {"2026-03-01": 6}, "hourly": {"2026-10-27T23:00Z": 9}}},
        }
        h = self.c.get("/sensors/box1/history").json()
        self.assertEqual(h["temp"]["daily"], [["2026-03-01", 3], ["2026-03-02", 7.5]])
        self.assertEqual(h["temp"]["hourly"], [["2026-10-28T09:00Z", 11.0], ["2026-10-28T10:00Z", 12.0]])
        self.assertEqual(h["pm25"], {"daily": [], "hourly": []})
        self.assertEqual(self.c.get("/sensors/DEBW015/history").json(), {"pm25": {"daily": [["2026-03-01", 6]], "hourly": [["2026-10-27T23:00Z", 9]]}})
        self.assertEqual(self.c.get("/sensors/nope/history").status_code, 404)
        self.assertEqual(history._uba_hour("2026-10-28 00:00:00"), "2026-10-27T23:00Z")
