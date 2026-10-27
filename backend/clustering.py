"""Group reports that are close in space. A report joins the nearest cluster
within RADIUS_M, otherwise it starts a new one. Simple greedy pass, fine for
a few thousand reports."""

import math
from collections import Counter

RADIUS_M = 150


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
    for i, c in enumerate(clusters):
        members = c["members"]
        types = Counter(t for r in members for t in r["types"])
        out.append(
            {
                "id": i,
                "lat": round(c["lat"], 6),
                "lon": round(c["lon"], 6),
                "count": len(members),
                "types": dict(types.most_common()),
                "latest": max(r["created_at"] for r in members),
                "report_ids": [r["id"] for r in members],
                "status": None,
            }
        )
    out.sort(key=lambda c: c["count"], reverse=True)
    return out
