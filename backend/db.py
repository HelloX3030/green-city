import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("GREENCITY_DB_PATH", Path(__file__).parent / "reports.db"))

# a user is a row, a device token is one way to prove you are that user (an account is a later one).
# reports.author is the old client-chosen id, kept only for the migration in init()
SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message    TEXT,
    author     TEXT,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    types      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    user_id    INTEGER REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS reports_created_at ON reports (created_at);
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users (id),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS links (
    code       TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users (id),
    expires_at TEXT NOT NULL
);
"""

CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I
LINK_MINUTES = 10


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    with connect() as con:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(reports)")}
        if cols and "user_id" not in cols:
            con.execute("ALTER TABLE reports ADD COLUMN user_id INTEGER REFERENCES users (id)")
        con.executescript(SCHEMA)
        # reports from before the users table: their author id becomes the device token
        for row in con.execute("SELECT DISTINCT author FROM reports WHERE user_id IS NULL AND author IS NOT NULL"):
            uid = user_for(con, row["author"])
            con.execute("UPDATE reports SET user_id = ? WHERE author = ? AND user_id IS NULL", (uid, row["author"]))


def user_for(con: sqlite3.Connection, token: str) -> int:
    """The user behind a device token, created on first contact."""
    uid = user_of(con, token)
    if uid is not None:
        return uid
    now = datetime.now(timezone.utc).isoformat()
    uid = con.execute("INSERT INTO users (created_at) VALUES (?)", (now,)).lastrowid
    con.execute("INSERT INTO devices (token, user_id, created_at) VALUES (?,?,?)", (token, uid, now))
    return uid


def user_of(con: sqlite3.Connection, token: str | None) -> int | None:
    """The user behind a device token, None for an unknown or missing one."""
    row = token and con.execute("SELECT user_id FROM devices WHERE token = ?", (token,)).fetchone()
    return row["user_id"] if row else None


def me(con: sqlite3.Connection, uid: int) -> dict:
    row = dict(con.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone())
    row["devices"] = con.execute("SELECT count(*) FROM devices WHERE user_id = ?", (uid,)).fetchone()[0]
    return row


def link_code(con: sqlite3.Connection, uid: int) -> dict:
    """A short code another device can claim within LINK_MINUTES to become this user."""
    now = datetime.now(timezone.utc)
    con.execute("DELETE FROM links WHERE expires_at < ?", (now.isoformat(),))
    code = "".join(secrets.choice(CODE_CHARS) for _ in range(6))
    expires = (now + timedelta(minutes=LINK_MINUTES)).isoformat()
    con.execute("INSERT INTO links (code, user_id, expires_at) VALUES (?,?,?)", (code, uid, expires))
    return {"code": code, "expires_at": expires}


def claim(con: sqlite3.Connection, token: str, code: str) -> int | None:
    """The device behind token joins the user behind code, taking its reports along.
    None when the code is unknown or expired, the code is spent either way."""
    now = datetime.now(timezone.utc).isoformat()
    row = con.execute("SELECT user_id FROM links WHERE code = ? AND expires_at >= ?", (code.upper(), now)).fetchone()
    con.execute("DELETE FROM links WHERE code = ?", (code.upper(),))
    if not row:
        return None
    new, old = row["user_id"], user_for(con, token)
    if new != old:
        con.execute("UPDATE reports SET user_id = ? WHERE user_id = ?", (new, old))
        con.execute("UPDATE devices SET user_id = ? WHERE user_id = ?", (new, old))
        con.execute("DELETE FROM users WHERE id = ?", (old,))
    return new


def row_to_report(row: sqlite3.Row) -> dict:
    """user_id stays for clustering, the Report model drops it from responses."""
    d = dict(row)
    d["types"] = json.loads(d["types"])
    d.pop("author", None)
    return d
