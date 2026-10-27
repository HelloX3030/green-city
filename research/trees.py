"""Baumkataster Heilbronn (opendata.heilbronn.de, shapefile) -> app/static/trees.json
as [[lon, lat, crown_m, name], ...]. Run: python3 research/trees.py"""
import io
import json
import struct
import urllib.request
import zipfile
from pathlib import Path

URL = "https://opendata.heilbronn.de/sites/default/files/SHAPE_BKA_HN20260101_EPSG4326.zip"
OUT = Path(__file__).parent.parent / "app" / "static" / "trees.json"

z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(URL).read()))
shp = z.read(next(n for n in z.namelist() if n.endswith(".shp")))
dbf = z.read(next(n for n in z.namelist() if n.endswith(".dbf")))

points = []
pos = 100
while pos < len(shp):
    length = struct.unpack(">i", shp[pos + 4 : pos + 8])[0] * 2
    rec = shp[pos + 8 : pos + 8 + length]
    points.append(struct.unpack("<2d", rec[4:20]) if struct.unpack("<i", rec[:4])[0] == 1 else None)
    pos += 8 + length

nrec, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
fields, pos = [], 32
while dbf[pos] != 0x0D:
    fields.append((dbf[pos : pos + 11].split(b"\0")[0].decode(), dbf[pos + 16]))
    pos += 32
rows = []
for i in range(nrec):
    rec, pos, d = dbf[hlen + i * rlen : hlen + (i + 1) * rlen], 1, {}
    for name, ln in fields:
        d[name] = rec[pos : pos + ln].decode("utf-8", "replace").strip()
        pos += ln
    rows.append(d)

out = []
for p, a in zip(points, rows):
    if p:
        out.append([round(p[0], 5), round(p[1], 5), round(float(a["KRONE_DM"] or 0), 1), a["DEU_TEXT"]])
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(len(out), "trees ->", OUT)
