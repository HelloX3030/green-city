"""Live values of the Heilbronn sensors: openSenseMap boxes (incl. the team's NoiseNode) and the UBA air station."""
import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from history import NOISENODE, OSEM, UBA, UBA_STATION, live_boxes, phenomenon_key

log = logging.getLogger("sensors")
TTL = 60
BOXLIST_TTL = 600

# sensor title -> (key, label) for the values we show
LABELS = [
    ("temp", "Temperatur"), ("humidity", "Luftfeuchte"), ("pm25", "PM2,5"), ("pm10", "PM10"),
    ("noise", "Lärm"), ("uv", "UV-Index"), ("wind", "Wind"),
]
TITLE_KEYS = {
    "humidity": ("rel. luftfeuchte", "relative luftfeuchte", "luftfeuchtigkeit", "humid", "rel. humidity"),
    "pm10": ("pm10", "finedust pm10"),
    "uv": ("uv-index", "uv index"),
    "wind": ("windgeschwindigkeit", "windspeed", "wind"),
}
UBA_COMPONENTS = {1: ("pm10", "PM10", "µg/m³"), 5: ("no2", "NO₂", "µg/m³"), 9: ("pm25", "PM2,5", "µg/m³")}

_state = {"boxes": [], "boxes_at": 0.0, "sensors": [], "at": 0.0}
_lock = asyncio.Lock()


def value_key(title: str) -> str | None:
    k = phenomenon_key(title)
    if k:
        return k
    t = title.strip().lower()
    return next((key for key, names in TITLE_KEYS.items() if t in names), None)


def box_kind(box: dict) -> str:
    if box["_id"] == NOISENODE or any(phenomenon_key(s["title"]) == "noise" for s in box["sensors"]):
        return "noise"
    return "env"


async def fetch_box(client: httpx.AsyncClient, box: dict) -> dict:
    lon, lat = box["currentLocation"]["coordinates"][:2]
    out = {"id": box["_id"], "name": box["name"], "lat": lat, "lon": lon, "source": "opensensemap",
           "kind": box_kind(box), "team": box["_id"] == NOISENODE, "values": [], "last": None}
    try:
        r = await client.get(f"{OSEM}/boxes/{box['_id']}", timeout=20)
        r.raise_for_status()
        sensors = r.json()["sensors"]
    except Exception as e:  # noqa: BLE001
        log.warning("box %s: %s", box["name"], e)
        return out
    seen = set()
    for s in sensors:
        key = value_key(s["title"])
        lm = s.get("lastMeasurement")
        if not key or key in seen or not isinstance(lm, dict):
            continue
        seen.add(key)
        label = dict(LABELS).get(key, s["title"])
        out["values"].append({"key": key, "label": label, "value": float(lm["value"]), "unit": s.get("unit", ""),
                              "time": lm["createdAt"]})
    out["values"].sort(key=lambda v: [k for k, _ in LABELS].index(v["key"]))
    out["last"] = max((v["time"] for v in out["values"]), default=None)
    return out


async def fetch_uba(client: httpx.AsyncClient) -> dict:
    out = {**UBA_STATION, "source": "uba", "kind": "air", "team": False, "values": [], "last": None}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for comp, (key, label, unit) in UBA_COMPONENTS.items():
        try:
            r = await client.get(f"{UBA}/measures/json", params={
                "date_from": today, "time_from": 1, "date_to": today, "time_to": 24,
                "station": UBA_STATION["id"], "component": comp, "scope": 2}, timeout=20)
            r.raise_for_status()
            data = next(iter(r.json()["data"].values()), {})
            rows = [(k, v) for k, v in data.items() if v[2] is not None]
            if not rows:
                continue
            start, row = max(rows)
            out["values"].append({"key": key, "label": label, "value": row[2], "unit": unit,
                                  "time": row[3].replace(" ", "T") + "+01:00"})
        except Exception as e:  # noqa: BLE001
            log.warning("uba %s: %s", key, e)
    out["last"] = max((v["time"] for v in out["values"]), default=None)
    return out


async def _refresh():
    async with httpx.AsyncClient() as client:
        if time.time() - _state["boxes_at"] > BOXLIST_TTL:
            try:
                _state["boxes"] = await live_boxes(client)
                _state["boxes_at"] = time.time()
            except Exception as e:  # noqa: BLE001
                log.warning("box list: %s", e)
        results = await asyncio.gather(*(fetch_box(client, b) for b in _state["boxes"]), fetch_uba(client))
    _state["sensors"] = list(results)
    _state["at"] = time.time()


async def get_sensors() -> list[dict]:
    if time.time() - _state["at"] > TTL:
        if _lock.locked() and _state["sensors"]:
            return _state["sensors"]  # refresh in progress, serve stale
        async with _lock:
            if time.time() - _state["at"] > TTL:
                await _refresh()
    return _state["sensors"]
