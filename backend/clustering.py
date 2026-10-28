"""Group reports that are close in space. Oldest report first: it anchors a cluster,
every later report within RADIUS_M of an anchor joins that cluster, otherwise it
anchors a new one. Anchors never move and the cluster id is the anchor's report id,
so bubbles stay put and ids stay stable while reports come in. Per person and day
there is one voice, so one phone cannot grow a bubble alone; every type that
person reported that day gets the voice once, so the dominant type is the one
most people name, not the last tap. A voice halves every HALF_LIFE_DAYS, so old
reports fade out of the cluster size and the dominant type."""

import math
from collections import Counter
from datetime import datetime, timedelta, timezone

RADIUS_M = 100
HALF_LIFE_DAYS = 7


def weight(created_at: str, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    age = (now - datetime.fromisoformat(created_at)).total_seconds() / 86400
    return 0.5 ** (max(age, 0) / HALF_LIFE_DAYS)


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cluster(reports: list[dict], me: int | None = None) -> list[dict]:
    """me: the caller's user id, counted per cluster as `mine`."""
    clusters: list[dict] = []
    for rep in sorted(reports, key=lambda r: r["created_at"]):
        best, best_d = None, RADIUS_M
        for c in clusters:
            d = distance_m(rep["lat"], rep["lon"], c["lat"], c["lon"])
            if d < best_d:
                best, best_d = c, d
        if best is None:
            best = {"lat": rep["lat"], "lon": rep["lon"], "members": []}
            clusters.append(best)
        best["members"].append(rep)

    out = []
    now = datetime.now(timezone.utc)
    for c in clusters:
        members = c["members"]
        # one voice per person and day, dated by that person's latest report of the day,
        # given once to every type they named that day
        voices: dict[tuple, dict] = {}  # (person, day) -> {"at": latest created_at, "types": set}
        for r in members:
            who = r.get("user_id") or ("anon", r["id"])
            v = voices.setdefault((who, r["created_at"][:10]), {"at": r["created_at"], "types": set()})
            v["at"] = max(v["at"], r["created_at"])
            v["types"].update(r["types"])
        people = len({who for who, _ in voices})
        week = now - timedelta(days=HALF_LIFE_DAYS)
        # types: people per type (not decayed), ordered by decayed voices, the first is the dominant
        by_type = Counter()
        heads: dict[str, set] = {}
        for (who, _), v in voices.items():
            w = weight(v["at"], now)
            for t in v["types"]:
                by_type[t] += w
                heads.setdefault(t, set()).add(who)
        types = {t: len(heads[t]) for t, _ in by_type.most_common()}
        out.append(
            {
                "id": members[0]["id"],
                "lat": c["lat"],
                "lon": c["lon"],
                "count": len(members),
                "people": people,
                "recent": sum(1 for r in members if datetime.fromisoformat(r["created_at"]) >= week),
                "mine": sum(1 for r in members if me is not None and r.get("user_id") == me),
                "weight": round(sum(weight(v["at"], now) for v in voices.values()), 2),
                "types": types,
                "dominant": next(iter(types)),
                "latest": max(r["created_at"] for r in members),
                "report_ids": [r["id"] for r in members],
                "points": [[r["lat"], r["lon"], r["types"][0]] for r in members],
                "status": None,
                "reason": None,
            }
        )
    out.sort(key=lambda c: c["weight"], reverse=True)
    return out


def dominant_type(c: dict) -> str:
    return c["dominant"]
