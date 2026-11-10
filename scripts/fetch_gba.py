"""GlobalBuildingAtlas GBA.Height (TUM, 3 m building-height raster from PlanetScope, CC BY-NC 4.0) for the AOI.

The heights come as 0.2 x 0.2 degree GeoTIFFs packed into one ~100 GB zip per 5 x 5 degree tile on TUM's data server.
Only the needed GeoTIFFs are read out of the zip with HTTP range requests (scripts/rangezip.py): ~170 MB for Budapest.
Output: data/raw/gba/<lonmin>_<latmax>_<lonmax>_<latmin>_sr_ss.tif
"""
import math
import shutil
import zipfile
from pathlib import Path

from aoi import wgs_bounds
from rangezip import RangeFile

SERVER = "https://dataserv.ub.tum.de/public.php/webdav/height"
AUTH = ("m1782307", "m1782307")  # the public share's login, as published on mediatum.ub.tum.de/1782307
out = Path("data/raw/gba")
out.mkdir(parents=True, exist_ok=True)


def five(v):
    return int(math.floor(v / 5) * 5)


def tag(v, pos, neg, w):
    return f"{pos if v >= 0 else neg}{abs(v):0{w}d}"


w, s, e, n = wgs_bounds(300)
want = {}
for lat in range(math.floor(s * 5), math.floor(n * 5) + 1):
    for lon in range(math.floor(w * 5), math.floor(e * 5) + 1):
        lo, la = lon / 5, lat / 5
        name = f"{lo:.1f}_{la + 0.2:.1f}_{lo + 0.2:.1f}_{la:.1f}_sr_ss.tif"
        big = f"{tag(five(lo), 'e', 'w', 3)}_{tag(five(la) + 5, 'n', 's', 2)}_{tag(five(lo) + 5, 'e', 'w', 3)}_{tag(five(la), 'n', 's', 2)}"
        want.setdefault(big, []).append(name)
for big, names in want.items():
    todo = [x for x in names if not (out / x).exists()]
    if not todo:
        print("have", names)
        continue
    url = f"{SERVER}/europe/{big}.zip"
    z = zipfile.ZipFile(RangeFile(url, auth=AUTH, headers={"X-Requested-With": "XMLHttpRequest"}, block=8 << 20))
    have = set(z.namelist())
    for x in todo:
        if x not in have:
            print("not in", big, x, "(no buildings there?)")
            continue
        with z.open(x) as src, open(out / (x + ".part"), "wb") as dst:
            shutil.copyfileobj(src, dst, 8 << 20)
        (out / (x + ".part")).rename(out / x)
        print("got", out / x, (out / x).stat().st_size // 2 ** 20, "MB")
