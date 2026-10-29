import asyncio
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

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
    trash = "trash"
    road = "road"
    other = "other"


class ReportIn(BaseModel):
    message: str | None = Field(default=None, max_length=500)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    types: list[ReportType] = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def blank_is_no_text(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None  # "   " would be an empty row on the card, counted as a text

    @field_validator("types")
    @classmethod
    def each_type_once(cls, v: list[ReportType]) -> list[ReportType]:
        return list(dict.fromkeys(v))


class Report(ReportIn):
    id: int
    created_at: datetime


class BubbleReport(Report):
    mine: bool = False  # from the caller's device


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


PING_SECONDS = 25  # keeps the event stream alive through proxies


class Events:
    """Who is listening on GET /events. A write publishes a kind, the app refetches on it."""

    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.subs: set[asyncio.Queue[str]] = set()

    def publish(self, kind: str) -> None:
        # the endpoints run in a worker thread, the queues belong to the loop
        if self.loop:
            self.loop.call_soon_threadsafe(lambda: [q.put_nowait(kind) for q in self.subs])

    async def stream(self):
        q: asyncio.Queue[str] = asyncio.Queue()
        self.subs.add(q)
        try:
            yield "retry: 3000\n\n"
            while True:
                try:
                    kind = await asyncio.wait_for(q.get(), PING_SECONDS)
                except TimeoutError:
                    yield "event: ping\ndata: \n\n"  # an event, not a comment: the app watches for it
                    continue
                yield f"event: {kind}\ndata: {datetime.now(timezone.utc).isoformat()}\n\n"
        finally:
            self.subs.discard(q)


events = Events()


@asynccontextmanager
async def lifespan(_: FastAPI):
    events.loop = asyncio.get_running_loop()
    db.init()
    history.load()
    tasks = [asyncio.create_task(history.refresh_loop()), asyncio.create_task(bikes.get_rides()),
             asyncio.create_task(sensors.get_sensors())]  # warm, so the first phone does not wait
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
        me = db.me(con, uid)
    events.publish("reports")  # the other device's reports are this user's now
    return me


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
    events.publish("reports")
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
    events.publish("reports")


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


@app.get("/clusters/{cid}/reports", response_model=list[BubbleReport])
def cluster_reports(
    cid: int, days: int = Query(default=CLUSTER_WINDOW_DAYS, ge=1, le=365), token: str | None = Depends(device_or_none)
) -> list[dict]:
    """The reports of one bubble: the caller's own first (`mine`), then the others, newest first; no author."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with db.connect() as con:
        reports = fetch_reports(con, since)
        me = db.user_of(con, token)
    for c in cluster(reports):
        if c["id"] == cid:
            ids = set(c["report_ids"])
            rows = [{**r, "mine": me is not None and r.get("user_id") == me} for r in reports if r["id"] in ids]
            return sorted(rows, key=lambda r: not r["mine"])
    raise HTTPException(404, "no such bubble")


@app.get("/events")
async def event_stream() -> StreamingResponse:
    """Server-sent events: `reports` whenever reports change, `ping` every 25 s. The app refetches on it."""
    return StreamingResponse(
        events.stream(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


@app.get("/bikes")
async def list_bikes() -> dict:
    return await bikes.get_rides()


@app.get("/sensors")
async def list_sensors() -> list[dict]:
    return await sensors.get_sensors()


@app.get("/sensors/{sid}/history")
def sensor_history(sid: str) -> dict:
    """per phenomenon: daily and 6-hour values since March, 15-minute ones of the last 7 days, [time, value] sorted"""
    s = history.series(sid)
    if s is None:
        raise HTTPException(404, "unknown sensor")
    return s
