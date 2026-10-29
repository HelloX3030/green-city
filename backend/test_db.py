import json
import tempfile
import unittest
from pathlib import Path

import db


class Db(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self.tmp.name) / "t.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_token_makes_one_user(self):
        db.init()
        with db.connect() as con:
            a = db.user_for(con, "a" * 32)
            self.assertEqual(db.user_for(con, "a" * 32), a)
            self.assertNotEqual(db.user_for(con, "b" * 32), a)
            self.assertEqual(db.user_of(con, "a" * 32), a)
            self.assertIsNone(db.user_of(con, "c" * 32))  # a look-up does not create
            self.assertIsNone(db.user_of(con, None))

    def test_two_requests_of_a_new_device_make_one_user(self):
        # the second request looked the token up before the first one created it
        db.init()
        with db.connect() as con:
            a = db.user_for(con, "a" * 32)
        lookup, calls = db.user_of, []
        db.user_of = lambda con, token: lookup(con, token) if calls.append(token) or len(calls) > 1 else None
        try:
            with db.connect() as con:
                b = db.user_for(con, "a" * 32)
        finally:
            db.user_of = lookup
        self.assertEqual(b, a)
        with db.connect() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM users").fetchone()[0], 1)

    def test_old_reports_get_a_user_from_their_author(self):
        with db.connect() as con:
            con.execute("CREATE TABLE reports (id INTEGER PRIMARY KEY, message TEXT, author TEXT, lat REAL, lon REAL, types TEXT, created_at TEXT)")
            for author in ("x" * 36, "x" * 36, "y" * 36):
                con.execute("INSERT INTO reports (author, lat, lon, types, created_at) VALUES (?, 49, 9, ?, '2026-10-28T09:44:00+00:00')", (author, json.dumps(["noise"])))
        db.init()
        with db.connect() as con:
            users = [r["user_id"] for r in con.execute("SELECT user_id FROM reports ORDER BY id")]
            self.assertEqual(users[0], users[1])
            self.assertNotEqual(users[0], users[2])
            self.assertEqual(db.user_for(con, "x" * 36), users[0])  # the old id still works as a token
            self.assertNotIn("author", db.row_to_report(con.execute("SELECT * FROM reports").fetchone()))


if __name__ == "__main__":
    unittest.main()
