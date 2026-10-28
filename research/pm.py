"""All-time PM2.5 of the Heilbronn senseBox:bike boxes (openSenseMap) -> app/static/pm.json
as {step: [dlon, dlat], cells: [[lon, lat, pm25, n], ...]} on a ~25 m grid, cells with 3+ readings. Run: python3 research/pm.py"""
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

OSEM = "https://api.opensensemap.org"
OUT = Path(__file__).parent.parent / "app" / "static" / "pm.json"
BBOX = (9.04, 49.09, 9.31, 49.21)
STEP_LAT, STEP_LON = 0.000225, 0.000345  # ~25 m
MIN_N = 3
CAP = 10000  # openSenseMap rows per request


def get(url, **params):
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=120) as r:
        return json.load(r)


def rows(box_id, sensor_id, start, end):
    """All readings in [start, end), splitting windows that hit the row cap."""
    r = get(f"{OSEM}/boxes/{box_id}/data/{sensor_id}", **{
        "from-date": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "to-date": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "format": "json"})
    if len(r) < CAP:
        return r
    mid = start + (end - start) / 2
    return rows(box_id, sensor_id, start, mid) + rows(box_id, sensor_id, mid, end)


now = datetime.now(timezone.utc)
cells = defaultdict(lambda: [0.0, 0])
boxes = get(f"{OSEM}/boxes", grouptag="heilbronn", format="json")
for b in boxes:
    sensor = next((s["_id"] for s in b["sensors"] if s["title"] == "Finedust PM2.5"), None)
    if b.get("exposure") != "mobile" or not sensor or not b.get("lastMeasurementAt"):
        continue
    t = datetime.fromisoformat(b["createdAt"].replace("Z", "+00:00"))
    n = 0
    while t < now:
        for r in rows(b["_id"], sensor, t, min(now, t + timedelta(days=31))):
            if not r.get("location"):
                continue
            lon, lat = r["location"][:2]
            if not (BBOX[0] < lon < BBOX[2] and BBOX[1] < lat < BBOX[3]):
                continue
            c = cells[(round(lon / STEP_LON), round(lat / STEP_LAT))]
            c[0] += float(r["value"])
            c[1] += 1
            n += 1
        t += timedelta(days=31)
    print(f"{b['name']}: {n} readings", file=sys.stderr)

out = [[round(i * STEP_LON, 5), round(j * STEP_LAT, 5), round(s / n, 1), n] for (i, j), (s, n) in cells.items() if n >= MIN_N]
OUT.write_text(json.dumps({"step": [STEP_LON, STEP_LAT], "cells": out}, separators=(",", ":")))
print(f"{len(out)} cells, {sum(c[3] for c in out)} readings -> {OUT} ({OUT.stat().st_size // 1024} KB)", file=sys.stderr)
