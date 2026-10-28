"""Daily statistics per sensor since March and hourly ones of the last days, from openSenseMap and UBA.
The daily ones are slow to fetch (1 min+ per call), so everything is cached on disk."""
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

log = logging.getLogger("history")
CACHE_PATH = Path(os.environ.get("GREENCITY_HISTORY_PATH", Path(__file__).parent / "history.json"))
OSEM = "https://api.opensensemap.org"
UBA = "https://luftdaten.umweltbundesamt.de/api/air-data/v3"
BBOX = "9.1,49.1,9.3,49.2"
NOISENODE = "6ae0d7aa4bc0370008dba0f7"
UBA_STATION = {"id": "DEBW015", "name": "Messstation Heilbronn (UBA)", "lat": 49.1655, "lon": 9.2248}
FROM = "2026-03-01T00:00:00Z"
MAX_AGE = timedelta(hours=24)
HOURLY_DAYS = 7
HOURLY_MAX_AGE = timedelta(minutes=50)  # the refresh loop is hourly
UTC_PLUS_1 = timezone(timedelta(hours=1))  # UBA times are CET all year

# phenomenon key -> (title regex, daily operation)
PHENOMENA = {
    "temp": (re.compile(r"^temperatur(e)?$", re.I), "max"),
    "pm25": (re.compile(r"^(finedust )?pm ?2[.,]?5$", re.I), "arithmeticMean"),
    "noise": (re.compile(r"^laeq|sound level|lärm|noise", re.I), "arithmeticMean"),
}


def last_ts(sensor: dict) -> float:
    """Unix time of the sensor's last measurement. The box list only carries the measurement's
    ObjectId, whose first 4 bytes are that time."""
    lm = sensor.get("lastMeasurement")
    if isinstance(lm, dict):
        return datetime.fromisoformat(lm["createdAt"].replace("Z", "+00:00")).timestamp()
    if isinstance(lm, str) and len(lm) == 24:
        return int(lm[:8], 16)
    return 0.0


def best_sensors(sensors: list[dict]) -> dict[str, dict]:
    """One sensor per phenomenon key: the one that reported last (the NoiseNode has a dead
    'Sound Level' channel next to the live 'LAeq_1min')."""
    best: dict[str, dict] = {}
    for s in sensors:
        key = phenomenon_key(s["title"])
        if key and (key not in best or last_ts(s) > last_ts(best[key])):
            best[key] = s
    return best

_cache: dict = {"boxes": {}, "uba": {}}


def phenomenon_key(title: str) -> str | None:
    return next((k for k, (rx, _) in PHENOMENA.items() if rx.match(title.strip())), None)


_loaded_mtime = 0.0


def load():
    """(Re)load the cache file if it changed on disk, e.g. written by `python history.py`."""
    global _cache, _loaded_mtime
    if CACHE_PATH.exists() and CACHE_PATH.stat().st_mtime != _loaded_mtime:
        _cache = json.loads(CACHE_PATH.read_text())
        _loaded_mtime = CACHE_PATH.stat().st_mtime
    return _cache


def save():
    global _loaded_mtime
    CACHE_PATH.write_text(json.dumps(_cache))
    _loaded_mtime = CACHE_PATH.stat().st_mtime


def get() -> dict:
    return load()


def _stale(entry: dict | None, field: str = "fetched", max_age: timedelta = MAX_AGE) -> bool:
    if not entry or field not in entry:
        return True
    return datetime.now(timezone.utc) - datetime.fromisoformat(entry[field]) > max_age


def _hourly_from() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=HOURLY_DAYS)


def _rows(values: dict | None) -> list[list]:
    return sorted([t, v] for t, v in (values or {}).items() if v is not None)


def series(sensor_id: str) -> dict[str, dict] | None:
    """Per phenomenon the daily values since March and the hourly ones of the last days, each as a
    sorted list of [time, value]. None for a sensor we do not know."""
    cache = get()
    if sensor_id == UBA_STATION["id"]:
        phenomena = cache["uba"]
    elif sensor_id in cache["boxes"]:
        phenomena = cache["boxes"][sensor_id].get("phenomena", {})
    else:
        return None
    return {key: {"daily": _rows(p.get("daily")), "hourly": _rows(p.get("hourly"))} for key, p in phenomena.items()}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def live_boxes(client: httpx.AsyncClient) -> list[dict]:
    """Outdoor boxes in Heilbronn that sent data in the last 24 h, plus the NoiseNode."""
    r = await client.get(f"{OSEM}/boxes", params={"bbox": BBOX, "format": "json"}, timeout=30)
    r.raise_for_status()
    out = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    for b in r.json():
        if b.get("exposure") != "outdoor":
            continue
        last = b.get("lastMeasurementAt")
        recent = last and datetime.fromisoformat(last.replace("Z", "+00:00")) > cutoff
        if recent or b["_id"] == NOISENODE:
            out.append(b)
    return out


async def _descriptive(client: httpx.AsyncClient, box_id: str, title: str, from_: str, window: str, op: str) -> dict:
    """time -> value for one sensor, one value per window"""
    r = await client.get(
        f"{OSEM}/statistics/descriptive",
        params={"boxId": box_id, "phenomenon": title, "from-date": from_, "to-date": _api_now(),
                "window": window, "operation": op, "format": "json"},
        timeout=300,
    )
    r.raise_for_status()
    rows = r.json()
    return {k: v for k, v in rows[0].items() if k != "sensorId"} if rows else {}


async def refresh_box(client: httpx.AsyncClient, box: dict):
    lon, lat = box["currentLocation"]["coordinates"][:2]
    entry = _cache["boxes"].setdefault(box["_id"], {})
    entry.update({"name": box["name"], "lat": lat, "lon": lon, "phenomena": entry.get("phenomena", {})})
    for key, s in best_sensors(box["sensors"]).items():
        cached = entry["phenomena"].get(key)
        if cached and cached.get("sensor_id") != s["_id"]:
            cached = None
        op = PHENOMENA[key][1]
        try:
            if _stale(cached):
                rows = await _descriptive(client, box["_id"], s["title"], FROM, "1d", op)
                cached = {"title": s["title"], "sensor_id": s["_id"], "fetched": _now(),
                          "daily": {k[:10]: v for k, v in rows.items()}, "hourly": {}}
                entry["phenomena"][key] = cached
                log.info("history %s %s: %d days", box["name"], key, len(rows))
            if _stale(cached, "hourly_fetched", HOURLY_MAX_AGE):
                rows = await _descriptive(client, box["_id"], s["title"], _hourly_from().strftime("%Y-%m-%dT%H:%M:%SZ"), "1h", op)
                cached.update({"hourly_fetched": _now(), "hourly": {k[:16] + "Z": v for k, v in rows.items()}})
        except Exception as e:  # noqa: BLE001
            log.warning("history %s %s: %s", box["name"], s["title"], e)
            continue
        save()


async def _uba_measures(client: httpx.AsyncClient, from_: str, scope: int) -> dict:
    """start time (CET, as UBA gives it) -> PM2.5; scope 1 is the daily mean, 2 the hourly"""
    r = await client.get(
        f"{UBA}/measures/json",
        params={"date_from": from_, "time_from": 1, "date_to": _api_now()[:10], "time_to": 24,
                "station": UBA_STATION["id"], "component": 9, "scope": scope},
        timeout=60,
    )
    r.raise_for_status()
    data = next(iter(r.json()["data"].values()), {})
    return {k: row[2] for k, row in data.items() if row[2] is not None}


def _uba_hour(cet: str) -> str:
    return datetime.fromisoformat(cet).replace(tzinfo=UTC_PLUS_1).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


async def refresh_uba(client: httpx.AsyncClient):
    entry = _cache["uba"].get("pm25")
    try:
        if _stale(entry):
            daily = await _uba_measures(client, FROM[:10], 1)
            entry = _cache["uba"]["pm25"] = {"fetched": _now(), "daily": {k[:10]: v for k, v in daily.items()}, "hourly": {}}
        if _stale(entry, "hourly_fetched", HOURLY_MAX_AGE):
            hourly = await _uba_measures(client, _hourly_from().strftime("%Y-%m-%d"), 2)
            entry.update({"hourly_fetched": _now(), "hourly": {_uba_hour(k): v for k, v in hourly.items()}})
    except Exception as e:  # noqa: BLE001
        log.warning("history uba: %s", e)
        return
    save()


async def refresh():
    async with httpx.AsyncClient() as client:
        await refresh_uba(client)
        for box in await live_boxes(client):
            await refresh_box(client, box)


async def refresh_loop():
    """Hourly. Starts late so a `python history.py` run in parallel is not duplicated."""
    while True:
        await asyncio.sleep(600)
        try:
            load()
            await refresh()
        except Exception as e:  # noqa: BLE001
            log.warning("history refresh: %s", e)
        await asyncio.sleep(3000)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    load()
    asyncio.run(refresh())
