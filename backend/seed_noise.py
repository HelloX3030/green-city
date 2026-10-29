"""Demo data for the NoiseNode: a believable week and a half of street noise before its first real
value, so the chart on a slide does not show two days. Deterministic, idempotent, written under
phenomena.noise.seed in history.json; history.values() merges it under the real values (a real value
always wins, the seed ends at the first real one). Remove with `uv run python seed_noise.py --remove`."""
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import history
from history import NOISENODE

TZ = ZoneInfo("Europe/Berlin")
SEED_FROM = datetime(2026, 10, 17, tzinfo=timezone.utc)  # a whole UTC day, as the daily values count them
STEP = timedelta(minutes=15)  # the fine series
# LAeq per local hour of a weekday at a street in town, dB(A): night 54-57, morning rush 70-74,
# day 67-70, evening 63-66, the upper ends of a street's usual ranges (the real NoiseNode reads
# high); linear in between
WEEKDAY = [(0, 57), (1, 56), (2, 55), (3, 54), (4, 55), (5, 58), (6, 65), (7, 72), (7.75, 74), (8.5, 72), (9.5, 69),
           (12, 68), (14, 67), (16, 68), (17.5, 70), (19, 67), (20.5, 65), (22, 63), (23, 60), (24, 57)]
# Saturday: a late, weak rush; Sunday: quiet morning, quiet day
SATURDAY = [(0, 60), (2, 56), (4, 54), (6, 55), (8, 60), (10, 66), (12, 68), (15, 67), (18, 66), (20, 64), (22, 63), (24, 61)]
SUNDAY = [(0, 60), (2, 56), (4, 53), (7, 54), (9, 57), (11, 62), (13, 64), (16, 65), (18, 64), (20, 62), (22, 59), (24, 57)]
POSER_HOURS = (22, 26)  # Friday and Saturday 22:00 to 02:00: a few loud runs of 74-80 dB
POSERS_PER_NIGHT = (5, 9)


def curve(points: list[tuple[float, float]], h: float) -> float:
    for (h0, v0), (h1, v1) in zip(points, points[1:]):
        if h0 <= h <= h1:
            return v0 + (v1 - v0) * (h - h0) / (h1 - h0)
    return points[-1][1]


def fine_series(until: datetime) -> dict[str, float]:
    """15-minute LAeq means from SEED_FROM up to (not including) `until`"""
    rng = random.Random(20261017)
    out: dict[str, float] = {}
    posers: set[datetime] = set()
    day_offset: dict[str, float] = {}
    t = SEED_FROM
    # the loud runs of each Friday and Saturday night, picked per night, from the local midnight on
    night = SEED_FROM.astimezone(TZ).replace(hour=0, minute=0)
    while night < until:
        if night.weekday() in (4, 5):
            slots = [night + timedelta(hours=POSER_HOURS[0], minutes=15 * i) for i in range((POSER_HOURS[1] - POSER_HOURS[0]) * 4)]
            posers.update(rng.sample(slots, rng.randint(*POSERS_PER_NIGHT)))
        night += timedelta(days=1)
    posers = {p.astimezone(timezone.utc) for p in posers}
    while t < until:
        local = t.astimezone(TZ)
        day = local.strftime("%Y-%m-%d")
        if day not in day_offset:
            day_offset[day] = rng.uniform(-1.2, 1.2)  # one day a little busier than the next
        h = local.hour + local.minute / 60
        shape = SATURDAY if local.weekday() == 5 else SUNDAY if local.weekday() == 6 else WEEKDAY
        v = curve(shape, h) + day_offset[day] + rng.gauss(0, 1.1)
        if t in posers:
            v = rng.uniform(74, 80)
        out[t.strftime("%Y-%m-%dT%H:%MZ")] = round(v, 1)
        t += STEP
    return out


def first_real(p: dict) -> str | None:
    """the earliest real value of the fine (or old hourly) series, the seed's end; kept from an earlier
    run once that series has rolled on. The 6-hour window holding it starts earlier and does not count."""
    keys = [min(rows) for rows in (p.get("fine"), p.get("hourly")) if rows]
    seed = p.get("seed", {}).get("until")
    return min(keys + ([seed] if seed else [])) if keys or seed else None


def seed(p: dict) -> dict:
    until = first_real(p)
    if not until:
        raise SystemExit("the NoiseNode has no real values in history.json yet, run history.py first")
    end = datetime.fromisoformat(until.replace("Z", "+00:00"))
    fine = fine_series(end)
    coarse = history.fold_windows(fine)
    return {"note": "synthetic demo data from seed_noise.py, ends at the first real value", "from": SEED_FROM.isoformat(),
            "until": until, "fine": fine, "coarse": coarse, "daily": history.fold_days(coarse, "arithmeticMean")}


def main(remove: bool):
    cache = history.load()
    box = cache["boxes"].get(NOISENODE)
    p = box and box.get("phenomena", {}).get("noise")
    if not p:
        raise SystemExit("no NoiseNode noise entry in history.json, run history.py first")
    if remove:
        p.pop("seed", None)
        print("seed removed")
    else:
        p["seed"] = seed(p)
        print(f"seed written: {len(p['seed']['fine'])} values from {SEED_FROM:%d.%m.} until {p['seed']['until']}")
    history.save()


if __name__ == "__main__":
    main("--remove" in sys.argv[1:])
