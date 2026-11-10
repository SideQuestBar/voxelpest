"""Copernicus DEM GLO-30 (30 m, 2011-15 TanDEM-X, free and open) tiles covering the AOI, from the AWS open-data bucket.

It is a surface model, not bare earth: over dense blocks it stands 5-15 m above the street. prep.py takes the
buildings back out using the footprints and heights.
Output: data/raw/dem/Copernicus_DSM_COG_10_N47_00_E019_00_DEM.tif (one per 1 x 1 degree tile).
"""
import math
from pathlib import Path

import requests

from aoi import wgs_bounds

URL = "https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"
out = Path("data/raw/dem")
out.mkdir(parents=True, exist_ok=True)
w, s, e, n_ = wgs_bounds(2000)
for lat in range(math.floor(s), math.floor(n_) + 1):
    for lon in range(math.floor(w), math.floor(e) + 1):
        name = f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM"
        p = out / f"{name}.tif"
        if p.exists() and p.stat().st_size > 0:
            print("have", p)
            continue
        r = requests.get(URL.format(n=name), timeout=600)
        r.raise_for_status()
        p.write_bytes(r.content)
        print("got", p, len(r.content) // 1024, "KB")
