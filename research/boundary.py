"""City limit of Heilbronn from opendata.heilbronn.de -> app/src/lib/boundary.json (one ring, 5 decimals)."""
import json
import urllib.request

URL = "https://opendata.heilbronn.de/sites/default/files/Heilbronn_Stadtkreisgrenzen_Gen_0.geojson"
OUT = "app/src/lib/boundary.json"

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
g = json.load(urllib.request.urlopen(req, timeout=60))
ring = g["features"][0]["geometry"]["coordinates"][0]
ring = [[round(x, 5), round(y, 5)] for x, y in ring]
json.dump({"ring": ring}, open(OUT, "w"), separators=(",", ":"))
print(len(ring), "points ->", OUT)
