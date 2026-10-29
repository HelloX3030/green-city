"""Does the history of the nearest sensor back a cluster up? One line of reason, in German."""
import json
import re
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

import bikes
from clustering import distance_m
from history import NOISENODE, UBA_STATION, get

NEAR_M = 800
UBA_NEAR_M = 3000
HOT_DAY_C = 30
HOT_DAYS_MIN = 5
PM25_WHO = 15
PM25_DAYS_MIN = 10
NOISE_DB = 55
BIKE_NEAR_M = 150
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
TZ = ZoneInfo("Europe/Berlin")
TREES_PATH = Path(__file__).parent / "trees.json"  # [lon, lat] of the Baumkataster, the app's Stadtbäume layer
TREE_NEAR_M = 100  # the bubble's radius
FEW_TREES = 10  # fewer within 100 m: no shade confirmed (a lined street has 30+)
CELL = 0.001  # grid of ~110 m (lat) × ~70 m (lon) cells for the lookup


@cache
def _trees() -> dict[tuple[int, int], list[tuple[float, float]]] | None:
    try:
        rows = json.loads(TREES_PATH.read_text())
    except (OSError, ValueError):
        return None
    grid: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for lon, lat in rows:
        grid.setdefault((int(lat // CELL), int(lon // CELL)), []).append((lat, lon))
    return grid


def _trees_near(lat: float, lon: float) -> int | None:
    grid = _trees()
    if grid is None:
        return None
    i, j = int(lat // CELL), int(lon // CELL)
    return sum(
        1
        for di in range(-1, 2)
        for dj in range(-2, 3)
        for t in grid.get((i + di, j + dj), ())
        if distance_m(lat, lon, *t) <= TREE_NEAR_M
    )


def _nearest(lat: float, lon: float, key: str) -> tuple[dict | None, float]:
    best, best_d = None, float("inf")
    for box_id, b in get()["boxes"].items():
        if key not in b.get("phenomena", {}):
            continue
        d = distance_m(lat, lon, b["lat"], b["lon"])
        if d < best_d:
            best, best_d = {**b, "id": box_id}, d
    return best, best_d


def _dist(m: float) -> str:
    return f"{m / 1000:.1f} km".replace(".", ",") if m >= 1000 else f"{round(m / 10) * 10} m"


def _num(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


def _days(daily: dict, pred) -> int:
    return sum(1 for v in daily.values() if v is not None and pred(v))


def assess(lat: float, lon: float, type_: str) -> tuple[str | None, str | None]:
    status, reason = _assess(lat, lon, type_)
    # a unit never wraps away from its number on the phone ("55" / "dB(A).")
    return status, reason and re.sub(r"(\d) (?=m\b|km\b|°C|dB\(A\)|µg/m³)", "\\1\u00a0", reason)


def _assess(lat: float, lon: float, type_: str) -> tuple[str | None, str | None]:
    if type_ == "heat":
        box, d = _nearest(lat, lon, "temp")
        if not box or d > NEAR_M:
            return "no_data", f"Kein Temperatursensor im Umkreis von {NEAR_M} m. Hier fehlt ein Sensor."
        daily = box["phenomena"]["temp"]["daily"]
        n = _days(daily, lambda v: v >= HOT_DAY_C)
        where = f"{box['name']} ({_dist(d)})"
        if n >= HOT_DAYS_MIN:
            return "confirmed", f"{where}: an {n} Tagen über {HOT_DAY_C} °C gemessen seit März."
        return "unconfirmed", f"{where}: nur an {n} Tagen über {HOT_DAY_C} °C gemessen seit März."

    if type_ == "air":
        ride = bikes.nearest_pass(lat, lon, BIKE_NEAR_M)
        bike = ""
        if ride:
            when = f"{WEEKDAYS[ride['time'].weekday()]} {ride['time'].astimezone(TZ).strftime('%H:%M')}"
            bike = f" Messrad {ride['box']} kam {when} vorbei: PM2,5 {_num(ride['pm25'])} µg/m³."
        box, d = _nearest(lat, lon, "pm25")
        if box and d <= NEAR_M:
            daily, where = box["phenomena"]["pm25"]["daily"], f"{box['name']} ({_dist(d)})"
        else:
            d = distance_m(lat, lon, UBA_STATION["lat"], UBA_STATION["lon"])
            uba = get()["uba"].get("pm25")
            if not uba or d > UBA_NEAR_M:
                if ride:
                    return "unconfirmed", f"Kein fester Feinstaubsensor im Umkreis von {NEAR_M} m.{bike}"
                return "no_data", f"Kein Feinstaubsensor im Umkreis von {NEAR_M} m. Hier fehlt ein Sensor."
            daily, where = uba["daily"], f"{UBA_STATION['name']}, {_dist(d)}"
        n = _days(daily, lambda v: v > PM25_WHO)
        if n >= PM25_DAYS_MIN:
            return "confirmed", f"{where}: PM2,5 an {n} Tagen über dem WHO-Wert ({PM25_WHO} µg/m³) seit März.{bike}"
        return "unconfirmed", f"{where}: PM2,5 nur an {n} Tagen über dem WHO-Wert ({PM25_WHO} µg/m³) seit März.{bike}"

    if type_ == "noise":
        box, d = _nearest(lat, lon, "noise")
        if not box or d > NEAR_M:
            return "no_data", f"Kein Lärmsensor im Umkreis von {NEAR_M} m. Hier fehlt ein Sensor."
        daily = box["phenomena"]["noise"]["daily"]
        where = f"{box['name']} ({_dist(d)})"
        if not daily:
            return "no_data", f"{where} sendet noch keine Daten."
        n = _days(daily, lambda v: v >= NOISE_DB)
        if n:
            return "confirmed", f"{where}: an {n} von {len(daily)} Tagen im Mittel über {NOISE_DB} dB(A)."
        return "unconfirmed", f"{where}: an {len(daily)} Tagen im Mittel unter {NOISE_DB} dB(A)."

    if type_ == "no_shade":
        n = _trees_near(lat, lon)
        if n is None:
            return "no_data", "Kein Sensor misst Schatten. Hier fehlt eine Messung."
        few = n < FEW_TREES
        trees = "kein Stadtbaum" if n == 0 else "nur 1 Stadtbaum" if n == 1 else f"{'nur ' if few else ''}{n} Stadtbäume"
        return "confirmed" if few else "unconfirmed", f"Baumkataster: {trees} im Umkreis von {TREE_NEAR_M} m."
    return None, None
