"""Street furniture seen in Mapillary's street-level photos (CC BY-SA 4.0): street lights, traffic lights, benches, bins,
bike racks, bollards, catenary poles, zebra crossings and traffic signs, each a point Mapillary has triangulated from
the photos. Read from its vector tiles at zoom 14 over the AOI.

Needs a Mapillary access token (free, mapillary.com/dashboard/developers) in the environment as MAPILLARY_TOKEN; it is
never written to disk here. Without one, this step is skipped and voxelize.py uses OSM's furniture alone.
Output: data/raw/mapillary/features.json  [[lon, lat, value, first_seen, last_seen], ...]
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import requests

from aoi import wgs_bounds

LAYERS = ("mly_map_feature_point", "mly_map_feature_traffic_sign")
URL = "https://tiles.mapillary.com/maps/vtp/{layer}/2/{z}/{x}/{y}"
Z = 14
out = Path("data/raw/mapillary")
dst = out / "features.json"
tok = os.environ.get("MAPILLARY_TOKEN")
if dst.exists():
    print("have", dst)
    raise SystemExit
if not tok:
    print("no MAPILLARY_TOKEN: skipping Mapillary street furniture")
    raise SystemExit
try:
    import mapbox_vector_tile as mvt
except ImportError:
    sys.exit("pip install mapbox-vector-tile (or: uv run --with mapbox-vector-tile python scripts/fetch_mapillary.py)")
out.mkdir(parents=True, exist_ok=True)


def tile_of(lon, lat):
    n = 2 ** Z
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


def lonlat(tx, ty, px, py, extent):
    n = 2 ** Z
    x = (tx + px / extent) / n
    y = (ty + 1 - py / extent) / n  # tile y grows down, MVT y grows up
    return x * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y))))


w, s, e, n = wgs_bounds(100)
x0, y0 = tile_of(w, n)
x1, y1 = tile_of(e, s)
ses = requests.Session()
ses.headers["User-Agent"] = "voxelpest/0.2"
feats, seen = [], set()
for layer in LAYERS:
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            for attempt in range(4):
                r = ses.get(URL.format(layer=layer, z=Z, x=tx, y=ty), params={"access_token": tok}, timeout=120)
                if r.status_code == 200:
                    break
                time.sleep(2 + 3 * attempt)
            r.raise_for_status()
            for name, lay in mvt.decode(r.content).items():
                ext = lay.get("extent", 4096)
                for f in lay["features"]:
                    p = f["properties"]
                    if p.get("id") in seen or f["geometry"]["type"] != "Point":
                        continue
                    seen.add(p.get("id"))
                    lon, lat = lonlat(tx, ty, *f["geometry"]["coordinates"], ext)
                    if w <= lon <= e and s <= lat <= n:
                        feats.append([round(lon, 7), round(lat, 7), p.get("value"), p.get("first_seen_at"), p.get("last_seen_at")])
            print(layer, tx, ty, len(feats), flush=True)
json.dump(feats, open(dst, "w"))
print("got", dst, len(feats), "features")
