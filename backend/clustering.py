"""Group reports that are close in space. A report joins the nearest cluster
within RADIUS_M, otherwise it starts a new one. Simple greedy pass, fine for
a few thousand reports. Each report has a weight that halves every HALF_LIFE_DAYS,
so old reports fade out of the cluster size and the dominant type."""

import math
from collections import Counter
from datetime import datetime, timezone

RADIUS_M = 150
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


def cluster(reports: list[dict]) -> list[dict]:
    clusters: list[dict] = []
    for rep in reports:
        best, best_d = None, RADIUS_M
        for c in clusters:
            d = distance_m(rep["lat"], rep["lon"], c["lat"], c["lon"])
            if d < best_d:
                best, best_d = c, d
        if best is None:
            best = {"lat": rep["lat"], "lon": rep["lon"], "members": []}
            clusters.append(best)
        best["members"].append(rep)
        n = len(best["members"])
        best["lat"] += (rep["lat"] - best["lat"]) / n
        best["lon"] += (rep["lon"] - best["lon"]) / n

    out = []
    now = datetime.now(timezone.utc)
    for i, c in enumerate(clusters):
        members = c["members"]
        weights = {r["id"]: weight(r["created_at"], now) for r in members}
        types = Counter(t for r in members for t in r["types"])
        weighted = Counter()
        for r in members:
            for t in r["types"]:
                weighted[t] += weights[r["id"]]
        out.append(
            {
                "id": i,
                "lat": round(c["lat"], 6),
                "lon": round(c["lon"], 6),
                "count": len(members),
                "weight": round(sum(weights.values()), 2),
                "types": dict(types.most_common()),
                "dominant": weighted.most_common(1)[0][0],
                "latest": max(r["created_at"] for r in members),
                "report_ids": [r["id"] for r in members],
                "status": None,
                "reason": None,
            }
        )
    out.sort(key=lambda c: c["weight"], reverse=True)
    return out


def dominant_type(c: dict) -> str:
    return c["dominant"]
