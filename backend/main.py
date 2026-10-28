import asyncio
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import bikes
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
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    types: list[ReportType] = Field(min_length=1)


class Report(ReportIn):
    id: int
    created_at: datetime


class Me(BaseModel):
    id: int
    name: str | None
    created_at: datetime
    devices: int


class NameIn(BaseModel):
    name: str | None = Field(default=None, max_length=40)


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class Link(BaseModel):
    code: str
    expires_at: datetime


TOKEN = re.compile(r"^[A-Za-z0-9-]{32,64}$")


def device(x_device: str | None = Header(default=None)) -> str:
    """The random token the app keeps in localStorage and sends in the X-Device header."""
    if not x_device or not TOKEN.match(x_device):
        raise HTTPException(400, "X-Device header missing or not a 32-64 char token")
    return x_device


def device_or_none(x_device: str | None = Header(default=None)) -> str | None:
    """Reads work without the header, they just don't know what is yours."""
    return device(x_device) if x_device else None


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    history.load()
    tasks = [asyncio.create_task(history.refresh_loop()), asyncio.create_task(bikes.get_rides())]
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="green-city reports", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def fetch_reports(con, since: datetime | None = None, user_id: int | None = None) -> list[dict]:
    where, args = [], []
    if since is not None:
        where.append("created_at >= ?")
        args.append(since.astimezone(timezone.utc).isoformat())
    if user_id is not None:
        where.append("user_id = ?")
        args.append(user_id)
    sql = "SELECT * FROM reports" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY created_at DESC"
    return [db.row_to_report(r) for r in con.execute(sql, args)]


@app.get("/me", response_model=Me)
def me(token: str = Depends(device)) -> dict:
    with db.connect() as con:
        return db.me(con, db.user_for(con, token))


@app.patch("/me", response_model=Me)
def set_name(body: NameIn, token: str = Depends(device)) -> dict:
    """The whole account in v00: a name, nothing else."""
    name = body.name.strip() if body.name else None
    with db.connect() as con:
        uid = db.user_for(con, token)
        con.execute("UPDATE users SET name = ? WHERE id = ?", (name or None, uid))
        return db.me(con, uid)


@app.post("/me/link", response_model=Link)
def link(token: str = Depends(device)) -> dict:
    """A 6-char code, valid 10 minutes, typed into another device to make it this user."""
    with db.connect() as con:
        return db.link_code(con, db.user_for(con, token))


@app.post("/me/claim", response_model=Me)
def claim(body: CodeIn, token: str = Depends(device)) -> dict:
    """This device becomes the user behind the code, its reports so far come along."""
    with db.connect() as con:
        uid = db.claim(con, token, body.code)
        if uid is None:
            raise HTTPException(400, "code unknown or expired")
        return db.me(con, uid)


@app.post("/reports", response_model=Report, status_code=201)
def create_report(rep: ReportIn, token: str = Depends(device)) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    types = json.dumps([t.value for t in rep.types])
    with db.connect() as con:
        cur = con.execute(
            "INSERT INTO reports (message, lat, lon, types, created_at, user_id) VALUES (?,?,?,?,?,?)",
            (rep.message, rep.lat, rep.lon, types, now, db.user_for(con, token)),
        )
        row = con.execute("SELECT * FROM reports WHERE id = ?", (cur.lastrowid,)).fetchone()
    return db.row_to_report(row)


@app.get("/reports", response_model=list[Report])
def list_reports(since: datetime | None = Query(default=None)) -> list[dict]:
    with db.connect() as con:
        return fetch_reports(con, since)


@app.get("/reports/mine", response_model=list[Report])
def my_reports(token: str = Depends(device)) -> list[dict]:
    with db.connect() as con:
        return fetch_reports(con, user_id=db.user_for(con, token))


@app.delete("/reports/{rid}", status_code=204)
def withdraw_report(rid: int, token: str = Depends(device)) -> None:
    """Only your own: anyone else's report looks like it is not there."""
    with db.connect() as con:
        gone = con.execute("DELETE FROM reports WHERE id = ? AND user_id = ?", (rid, db.user_of(con, token))).rowcount
    if not gone:
        raise HTTPException(404, "not your report")


@app.get("/clusters")
def list_clusters(
    days: int = Query(default=CLUSTER_WINDOW_DAYS, ge=1, le=365), token: str | None = Depends(device_or_none)
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with db.connect() as con:
        clusters = cluster(fetch_reports(con, since), me=db.user_of(con, token))
    for c in clusters:
        c["status"], c["reason"] = status.assess(c["lat"], c["lon"], dominant_type(c))
    return clusters


@app.get("/bikes")
async def list_bikes() -> dict:
    return await bikes.get_rides()


@app.get("/sensors")
async def list_sensors() -> list[dict]:
    return await sensors.get_sensors()
