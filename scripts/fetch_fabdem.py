"""FABDEM V1-2: the Copernicus GLO-30 surface model with forests and buildings removed by machine learning (Hawker et al.
2022, University of Bristol, CC BY-NC-SA 4.0). A bare-earth model: the ground under Castle Hill's palace and Gellért
Hill's woods, which the surface model can only guess at.

The 1 x 1 degree GeoTIFFs come zipped by 10 x 10 degrees (~1.9 GB for N40-50 E10-20); only the needed ones are read out
of the zip with HTTP range requests (scripts/rangezip.py), ~25 MB for Budapest.
Output: data/raw/fabdem/N47E019_FABDEM_V1-2.tif
"""
import math
import shutil
import zipfile
from pathlib import Path

from aoi import wgs_bounds
from rangezip import RangeFile

BASE = "https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn"
out = Path("data/raw/fabdem")
out.mkdir(parents=True, exist_ok=True)


def deg(v, pos, neg, w):
    return f"{pos if v >= 0 else neg}{abs(v):0{w}d}"


w, s, e, n = wgs_bounds(300)
want = {}
for lat in range(math.floor(s), math.floor(n) + 1):
    for lon in range(math.floor(w), math.floor(e) + 1):
        name = f"{deg(lat, 'N', 'S', 2)}{deg(lon, 'E', 'W', 3)}_FABDEM_V1-2.tif"
        la, lo = math.floor(lat / 10) * 10, math.floor(lon / 10) * 10
        big = f"{deg(la, 'N', 'S', 2)}{deg(lo, 'E', 'W', 3)}-{deg(la + 10, 'N', 'S', 2)}{deg(lo + 10, 'E', 'W', 3)}_FABDEM_V1-2.zip"
        want.setdefault(big, []).append(name)
for big, names in want.items():
    todo = [x for x in names if not (out / x).exists()]
    if not todo:
        print("have", names)
        continue
    z = zipfile.ZipFile(RangeFile(f"{BASE}/{big}", headers={"User-Agent": "voxelpest/0.2"}, block=4 << 20))
    have = {Path(m).name: m for m in z.namelist()}
    for x in todo:
        if x not in have:
            print("not in", big, x)
            continue
        with z.open(have[x]) as src, open(out / (x + ".part"), "wb") as dst:
            shutil.copyfileobj(src, dst, 4 << 20)
        (out / (x + ".part")).rename(out / x)
        print("got", out / x, (out / x).stat().st_size // 2 ** 20, "MB")
