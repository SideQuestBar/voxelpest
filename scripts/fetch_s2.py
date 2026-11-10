"""Sentinel-2 cloudless 2023 (EOX, https://s2maps.eu; contains modified Copernicus Sentinel data 2023, CC BY-NC-SA 4.0):
a cloud-free true-colour mosaic at 10 m. Fetched as web-mercator tiles at zoom 15 (~3.2 m pixels here, upsampled from
10 m) and saved as one GeoTIFF, which prep.py puts on the grid for colours: the green of each park and lawn, the tone
of the river, and of the larger roofs.

Output: data/raw/s2/s2cloudless2023_z15.tif (EPSG:3857)
"""
import io
import math
import time
from pathlib import Path

import numpy as np
import rasterio
import requests
from PIL import Image
from rasterio.transform import from_origin

from aoi import wgs_bounds

Z = 15
URL = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg"
out = Path("data/raw/s2")
out.mkdir(parents=True, exist_ok=True)
dst = out / f"s2cloudless2023_z{Z}.tif"
R = 6378137.0
SPAN = 2 * math.pi * R


def tile_of(lon, lat):
    n = 2 ** Z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return int(x), int(y)


if dst.exists():
    print("have", dst)
    raise SystemExit
w, s, e, n = wgs_bounds(300)
x0, y0 = tile_of(w, n)
x1, y1 = tile_of(e, s)
nx, ny = x1 - x0 + 1, y1 - y0 + 1
img = np.zeros((ny * 256, nx * 256, 3), np.uint8)
ses = requests.Session()
ses.headers["User-Agent"] = "voxelpest/0.2"
for ty in range(y0, y1 + 1):
    for tx in range(x0, x1 + 1):
        for attempt in range(4):
            r = ses.get(URL.format(z=Z, y=ty, x=tx), timeout=60)
            if r.status_code == 200:
                break
            time.sleep(2 + attempt * 3)
        r.raise_for_status()
        img[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = np.array(Image.open(io.BytesIO(r.content)).convert("RGB"))
res = SPAN / (256 * 2 ** Z)
left, top = -SPAN / 2 + x0 * 256 * res, SPAN / 2 - y0 * 256 * res
with rasterio.open(dst, "w", driver="GTiff", width=img.shape[1], height=img.shape[0], count=3, dtype="uint8",
                   crs="EPSG:3857", transform=from_origin(left, top, res, res), compress="deflate") as f:
    f.write(np.moveaxis(img, 2, 0))
print("got", dst, f"{nx}x{ny} tiles, {img.shape[1]}x{img.shape[0]} px at {res:.2f} m (web mercator)")
