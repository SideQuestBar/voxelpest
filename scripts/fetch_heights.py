"""Building heights per OSM building, from Átló's Budapest Open Data Atlas (atlo.team/boda, "Épületmagasság"):
2023 OSM footprints joined with the Copernicus Urban Atlas Building Height 2012 raster (10 m), field DN = metres.
The file sits on Google Drive (~190 MB GeoJSON); only the AOI's buildings are kept.

Output: data/raw/heights/atlo_heights.json = {osm way id: height m}, plus the raw GeoJSON (cached).
"""
import json
from pathlib import Path

import requests

from aoi import wgs_bounds

DRIVE_ID = "1CuAFuUlsTtrBdUXxnKdcoM3-dMyCslEi"
out = Path("data/raw/heights")
out.mkdir(parents=True, exist_ok=True)
raw = out / "epuletmagassag.geojson"
if not raw.exists() or raw.stat().st_size < 1_000_000:
    url = f"https://drive.usercontent.google.com/download?id={DRIVE_ID}&export=download&confirm=t"
    with requests.get(url, stream=True, timeout=900) as r:
        r.raise_for_status()
        with open(str(raw) + ".part", "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    Path(str(raw) + ".part").rename(raw)
print("have", raw, raw.stat().st_size // 2 ** 20, "MB")

w, s, e, n = wgs_bounds(300)
heights = {}
for f in json.load(open(raw))["features"]:
    ring = f["geometry"]["coordinates"][0] if f["geometry"]["type"] == "Polygon" else f["geometry"]["coordinates"][0][0]
    lon, lat = ring[0]
    if w <= lon <= e and s <= lat <= n and f["properties"].get("osm_id"):
        heights[f["properties"]["osm_id"]] = f["properties"]["DN"]
json.dump(heights, open(out / "atlo_heights.json", "w"))
print(len(heights), "buildings with a height in the AOI")
