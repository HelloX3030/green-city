import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("GREENCITY_DB_PATH", Path(__file__).parent / "reports.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message    TEXT,
    author     TEXT,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    types      TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS reports_created_at ON reports (created_at);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    with connect() as con:
        con.executescript(SCHEMA)


def row_to_report(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["types"] = json.loads(d["types"])
    return d
