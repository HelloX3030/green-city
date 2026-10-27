import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
import history
import sensors
import status
from clustering import cluster, dominant_type

CLUSTER_WINDOW_DAYS = 14


class ReportType(str, Enum):
    noise = "noise"
    heat = "heat"
    air = "air"
    no_shade = "no_shade"
    other = "other"


class ReportIn(BaseModel):
    message: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=64)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    types: list[ReportType] = Field(min_length=1)


class Report(ReportIn):
    id: int
    created_at: datetime


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    history.load()
    task = asyncio.create_task(history.refresh_loop())
    yield
    task.cancel()


app = FastAPI(title="green-city reports", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def fetch_reports(since: datetime | None) -> list[dict]:
    sql = "SELECT * FROM reports"
    args: tuple = ()
    if since is not None:
        sql += " WHERE created_at >= ?"
        args = (since.astimezone(timezone.utc).isoformat(),)
    sql += " ORDER BY created_at DESC"
    with db.connect() as con:
        return [db.row_to_report(r) for r in con.execute(sql, args)]


@app.post("/reports", response_model=Report, status_code=201)
def create_report(rep: ReportIn) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    types = json.dumps([t.value for t in rep.types])
    with db.connect() as con:
        cur = con.execute(
            "INSERT INTO reports (message, author, lat, lon, types, created_at) VALUES (?,?,?,?,?,?)",
            (rep.message, rep.author, rep.lat, rep.lon, types, now),
        )
        row = con.execute("SELECT * FROM reports WHERE id = ?", (cur.lastrowid,)).fetchone()
    return db.row_to_report(row)


@app.get("/reports", response_model=list[Report])
def list_reports(since: datetime | None = Query(default=None)) -> list[dict]:
    return fetch_reports(since)


@app.get("/clusters")
def list_clusters(days: int = Query(default=CLUSTER_WINDOW_DAYS, ge=1, le=365)) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    clusters = cluster(fetch_reports(since))
    for c in clusters:
        c["status"], c["reason"] = status.assess(c["lat"], c["lon"], dominant_type(c))
    return clusters


@app.get("/sensors")
async def list_sensors() -> list[dict]:
    return await sensors.get_sensors()
