"""Live values of the Heilbronn sensors: openSenseMap boxes (incl. the team's NoiseNode) and the UBA air station."""
import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

import history
from history import NOISENODE, OSEM, UBA, UBA_STATION, live_boxes, phenomenon_key

log = logging.getLogger("sensors")
TTL = 60
BOXLIST_TTL = 600

# sensor title -> (key, label) for the values we show
LABELS = [
    ("temp", "Temperatur"), ("humidity", "Luftfeuchte"), ("pm25", "PM2,5"), ("pm10", "PM10"),
    ("noise", "Lärm Ø 1 min"), ("lmax", "Spitze 1 min"), ("events", "Laute Ereignisse"),
    ("uv", "UV-Index"), ("wind", "Wind"),
]
TITLE_KEYS = {
    "humidity": ("rel. luftfeuchte", "relative luftfeuchte", "luftfeuchtigkeit", "humid", "rel. humidity"),
    "pm10": ("pm10", "finedust pm10"),
    "lmax": ("lmax_1min", "lmax"),
    "events": ("eventcount_1min",),
    "uv": ("uv-index", "uv index"),
    "wind": ("windgeschwindigkeit", "windspeed", "wind"),
}
UNITS = {"count": "/min"}
UBA_COMPONENTS = {1: ("pm10", "PM10", "µg/m³"), 5: ("no2", "NO₂", "µg/m³"), 9: ("pm25", "PM2,5", "µg/m³")}
HISTORY_UNITS = {"temp": "°C", "pm25": "µg/m³", "noise": "dB(A)"}

_state = {"boxes": [], "boxes_at": 0.0, "sensors": [], "at": 0.0}
_lock = asyncio.Lock()
_task: asyncio.Task | None = None


def _previous(sid: str) -> dict | None:
    return next((s for s in _state["sensors"] if s["id"] == sid), None)


def history_values(phenomena: dict) -> list[dict]:
    """The last hourly value per phenomenon from history.json, for when the live API is down."""
    out = []
    for key, p in phenomena.items():
        hourly = {t: v for t, v in (p.get("hourly") or {}).items() if v is not None}
        if key in HISTORY_UNITS and hourly:
            t = max(hourly)
            label = "Lärm Ø 1 h" if key == "noise" else dict(LABELS)[key]
            time_ = datetime.fromisoformat(t.replace("Z", "+00:00")).isoformat()
            out.append({"key": key, "label": label, "value": float(hourly[t]), "unit": HISTORY_UNITS[key], "time": time_})
    return out


def _fallback(out: dict, phenomena: dict) -> dict:
    """Keep the last good values of this sensor, else the last hour from history.json."""
    prev = _previous(out["id"])
    out["values"] = prev["values"] if prev and prev["values"] else history_values(phenomena)
    out["values"].sort(key=lambda v: [k for k, _ in LABELS].index(v["key"]))
    out["last"] = max((v["time"] for v in out["values"]), default=None)
    return out


def history_boxes() -> list[dict]:
    """The boxes of history.json in the shape of the box list, so the pins stay when it cannot be fetched."""
    return [{"_id": bid, "name": b["name"], "currentLocation": {"coordinates": [b["lon"], b["lat"]]},
             "sensors": [{"title": p["title"]} for p in b.get("phenomena", {}).values()]}
            for bid, b in history.get()["boxes"].items()]


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
        return _fallback(out, history.get()["boxes"].get(box["_id"], {}).get("phenomena", {}))
    best: dict[str, dict] = {}  # per key the sensor that reported last
    for s in sensors:
        key = value_key(s["title"])
        lm = s.get("lastMeasurement")
        if key and isinstance(lm, dict) and (key not in best or lm["createdAt"] > best[key]["lastMeasurement"]["createdAt"]):
            best[key] = s
    for key, s in best.items():
        lm = s["lastMeasurement"]
        unit = s.get("unit", "")
        out["values"].append({"key": key, "label": dict(LABELS)[key], "value": float(lm["value"]),
                              "unit": UNITS.get(unit, unit), "time": lm["createdAt"]})
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
    if not out["values"]:  # down, or nothing yet today (UTC) in the small hours
        return _fallback(out, history.get()["uba"])
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
                if not _state["boxes"]:
                    _state["boxes"] = history_boxes()  # retried on the next refresh, boxes_at stays
        results = await asyncio.gather(*(fetch_box(client, b) for b in _state["boxes"]), fetch_uba(client))
    _state["sensors"] = list(results)
    _state["at"] = time.time()


async def _locked_refresh():
    async with _lock:
        if time.time() - _state["at"] > TTL:
            await _refresh()


async def get_sensors() -> list[dict]:
    """Waits for the upstream APIs only on the very first call, after that a stale answer comes at
    once and the refresh runs in the background, so a slow openSenseMap never holds up the map."""
    global _task
    if time.time() - _state["at"] > TTL:
        if not _state["sensors"]:
            await _locked_refresh()
        elif not _task or _task.done():
            _task = asyncio.create_task(_locked_refresh())
    return _state["sensors"]
