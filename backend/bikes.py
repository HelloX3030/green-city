"""Rides of the senseBox:bike boxes tagged "heilbronn" in the last 7 days, as GeoJSON lines
with the mean PM2.5 per ride. Pulled from openSenseMap every 10 min. Points outside the
city bbox are dropped, so a ride out of town ends at the edge the map can reach."""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from clustering import distance_m
from history import OSEM

log = logging.getLogger("bikes")
DAYS = 7
TTL = 600
GAP = timedelta(minutes=10)  # longer pause = new ride
MIN_POINTS = 20
MAX_POINTS = 300  # per ride in the GeoJSON
BBOX = (9.04, 49.09, 9.31, 49.21)  # city limit bbox, same as the map bounds

_state = {"rides": [], "at": 0.0}
_lock = asyncio.Lock()


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _in_city(loc: list) -> bool:
    return BBOX[0] < loc[0] < BBOX[2] and BBOX[1] < loc[1] < BBOX[3]


def split_rides(box: dict, rows: list[dict]) -> list[dict]:
    rows = sorted((r for r in rows if r.get("location") and _in_city(r["location"])), key=lambda r: r["createdAt"])
    rides, cur = [], []
    for r in rows:
        t = datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))
        if cur and t - cur[-1][0] > GAP:
            rides.append(cur)
            cur = []
        cur.append((t, r["location"][0], r["location"][1], float(r["value"])))
    if cur:
        rides.append(cur)
    out = []
    for i, pts in enumerate(rides):
        if len(pts) < MIN_POINTS:
            continue
        vals = [v for _, _, _, v in pts]
        km = sum(distance_m(a[2], a[1], b[2], b[1]) for a, b in zip(pts, pts[1:])) / 1000
        step = max(1, len(pts) // MAX_POINTS)
        out.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[round(lon, 5), round(lat, 5)] for _, lon, lat, _ in pts[::step]],
                },
                "properties": {
                    "id": f"{box['_id']}-{i}",
                    "box": box["name"],
                    "start": _iso(pts[0][0]),
                    "end": _iso(pts[-1][0]),
                    "km": round(km, 1),
                    "pm25": round(sum(vals) / len(vals), 1),
                    "pm25_max": round(max(vals), 1),
                    "points": len(pts),
                },
                "_pts": pts,
            }
        )
    return out


async def fetch_rides(client: httpx.AsyncClient) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    boxes = (await client.get(f"{OSEM}/boxes", params={"grouptag": "heilbronn", "format": "json"})).json()
    rides = []
    for b in boxes:
        if b.get("exposure") != "mobile" or (b.get("lastMeasurementAt") or "") < _iso(since):
            continue
        sensor = next((s for s in b["sensors"] if s["title"] == "Finedust PM2.5"), None)
        if not sensor:
            continue
        r = await client.get(
            f"{OSEM}/boxes/{b['_id']}/data/{sensor['_id']}",
            params={"from-date": _iso(since), "to-date": _iso(datetime.now(timezone.utc)), "format": "json"},
        )
        r.raise_for_status()
        rides += split_rides(b, r.json())
    rides.sort(key=lambda f: f["properties"]["start"], reverse=True)
    return rides


async def _refresh():
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            _state["rides"] = await fetch_rides(client)
        log.info("bikes: %d rides", len(_state["rides"]))
    except Exception as e:  # keep the old rides
        log.warning("bikes refresh failed: %s", e)
    _state["at"] = time.time()


async def get_rides() -> dict:
    if time.time() - _state["at"] > TTL and not _lock.locked():
        async with _lock:
            await _refresh()
    return {
        "type": "FeatureCollection",
        "features": [{k: v for k, v in f.items() if k != "_pts"} for f in _state["rides"]],
    }


def nearest_pass(lat: float, lon: float, radius_m: float) -> dict | None:
    """Latest ride point within radius_m, with its PM2.5 value, or None."""
    best = None
    for f in _state["rides"]:
        for t, plon, plat, v in f["_pts"]:
            if distance_m(lat, lon, plat, plon) <= radius_m and (best is None or t > best["time"]):
                best = {"time": t, "pm25": v, "box": f["properties"]["box"]}
    return best
