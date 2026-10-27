"""Does the history of the nearest sensor back a cluster up? One line of reason, in German."""
from clustering import distance_m
from history import NOISENODE, UBA_STATION, get

NEAR_M = 800
UBA_NEAR_M = 3000
HOT_DAY_C = 30
HOT_DAYS_MIN = 5
PM25_WHO = 15
PM25_DAYS_MIN = 10
NOISE_DB = 55


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


def _days(daily: dict, pred) -> int:
    return sum(1 for v in daily.values() if v is not None and pred(v))


def assess(lat: float, lon: float, type_: str) -> tuple[str | None, str | None]:
    if type_ == "heat":
        box, d = _nearest(lat, lon, "temp")
        if not box or d > NEAR_M:
            return "no_data", f"Kein Temperatursensor im Umkreis von {NEAR_M} m."
        daily = box["phenomena"]["temp"]["daily"]
        n = _days(daily, lambda v: v >= HOT_DAY_C)
        where = f"{box['name']} ({_dist(d)})"
        if n >= HOT_DAYS_MIN:
            return "confirmed", f"{where}: {n} heiße Tage über {HOT_DAY_C} °C seit März."
        return "unconfirmed", f"{where}: nur {n} heiße Tage über {HOT_DAY_C} °C seit März."

    if type_ == "air":
        box, d = _nearest(lat, lon, "pm25")
        if box and d <= NEAR_M:
            daily, where = box["phenomena"]["pm25"]["daily"], f"{box['name']} ({_dist(d)})"
        else:
            d = distance_m(lat, lon, UBA_STATION["lat"], UBA_STATION["lon"])
            uba = get()["uba"].get("pm25")
            if not uba or d > UBA_NEAR_M:
                return "no_data", f"Kein Feinstaubsensor im Umkreis von {NEAR_M} m."
            daily, where = uba["daily"], f"{UBA_STATION['name']}, {_dist(d)}"
        n = _days(daily, lambda v: v > PM25_WHO)
        if n >= PM25_DAYS_MIN:
            return "confirmed", f"{where}: PM2,5 an {n} Tagen über dem WHO-Wert ({PM25_WHO} µg/m³) seit März."
        return "unconfirmed", f"{where}: PM2,5 nur an {n} Tagen über dem WHO-Wert ({PM25_WHO} µg/m³) seit März."

    if type_ == "noise":
        box, d = _nearest(lat, lon, "noise")
        if not box or d > NEAR_M:
            return "no_data", "Kein Lärmsensor in der Nähe. Hier fehlt eine Messung."
        daily = box["phenomena"]["noise"]["daily"]
        where = f"{box['name']} ({_dist(d)})"
        if not daily:
            return "no_data", f"{where} sendet noch keine Daten."
        n = _days(daily, lambda v: v >= NOISE_DB)
        if n:
            return "confirmed", f"{where}: an {n} von {len(daily)} Tagen im Mittel über {NOISE_DB} dB(A)."
        return "unconfirmed", f"{where}: an {len(daily)} Tagen im Mittel unter {NOISE_DB} dB(A)."

    if type_ == "no_shade":
        return "no_data", "Kein Sensor misst Schatten. Hier fehlt eine Messung."
    return None, None
