"""Resample the raster sources onto the AOI grid (scripts/aoi.py), 1 m cells, row 0 = grid row 0.

  dsm  float32  Copernicus DEM GLO-30, metres above sea level (bilinear; a surface model, with roofs and treetops)
  dtm  float32  FABDEM V1-2, the same with forests and buildings removed: the bare ground (bilinear)
  s2   uint8    Sentinel-2 cloudless 2023 true colour (EOX), 10 m, for colours (bilinear)
  gba  float16  GlobalBuildingAtlas building height, metres above ground (nearest; 3 m source pixels)
  ortho uint8   optional: any EOV GeoTIFFs dropped into data/raw/ortho/ (e.g. Lechner orthophotos older than
                10 years, free on request), mosaicked at 1 m -- used for roof and ground colours when present

Output: data/prep.npz
"""
import glob

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.merge import merge
from scipy import ndimage

from aoi import D, RAW, W, to_world

BAND = 256


def sample(arr, transform, crs, order, nodata=None, fill=0):
    """arr (bands, rows, cols) in `crs` with `transform` -> (D, W[, bands]) on the grid."""
    t = Transformer.from_crs(23700, crs, always_xy=True)
    inv = ~transform
    nb = arr.shape[0]
    out = np.zeros((D, W) if nb == 1 else (D, W, nb), np.float32)
    jj0, ii0 = np.mgrid[0:BAND, 0:W].astype(np.float64)
    for j0 in range(0, D, BAND):
        n = min(BAND, D - j0)
        x, y = to_world(ii0[:n] + 0.5, jj0[:n] + j0 + 0.5)
        sx, sy = t.transform(x, y)
        col, row = inv * (sx, sy)
        for b in range(nb):
            v = ndimage.map_coordinates(arr[b], [row - 0.5, col - 0.5], order=order, mode="constant", cval=fill)
            if nb == 1:
                out[j0:j0 + n] = v
            else:
                out[j0:j0 + n, :, b] = v
    return out


srcs = [rasterio.open(p) for p in sorted(glob.glob(f"{RAW}/dem/*.tif"))]
dem, tr = merge(srcs)
dem = dem.astype(np.float32)
dsm = sample(dem, tr, srcs[0].crs, order=1)
print("dsm", dsm.shape, float(dsm.min()), float(dsm.max()))

with rasterio.open(glob.glob(f"{RAW}/gba/*.tif")[0]) as r:
    g = r.read(1).astype(np.float32)
    g[g < 0] = 0
    gba = sample(g[None], r.transform, r.crs, order=0).astype(np.float16)
print("gba", gba.shape, float(gba.max()), "m tallest,", round(float((gba > 2).mean()) * 100, 1), "% over 2 m")

out = dict(dsm=dsm, gba=gba)
fab = sorted(glob.glob(f"{RAW}/fabdem/*.tif"))
if fab:
    srcs = [rasterio.open(p) for p in fab]
    t, tr = merge(srcs)
    t = t.astype(np.float32)
    t[t < -100] = np.nan
    out["dtm"] = sample(np.nan_to_num(t, nan=float(np.nanmedian(t))), tr, srcs[0].crs, order=1)
    print("dtm", float(out["dtm"].min()), float(out["dtm"].max()))
s2 = sorted(glob.glob(f"{RAW}/s2/*.tif"))
if s2:
    with rasterio.open(s2[0]) as r:
        out["s2"] = np.clip(sample(r.read().astype(np.float32), r.transform, r.crs, order=1), 0, 255).astype(np.uint8)
    print("s2", out["s2"].shape)
orthos = sorted(glob.glob(f"{RAW}/ortho/*.tif"))
if orthos:
    srcs = [rasterio.open(p) for p in orthos]
    o, tr = merge(srcs, res=1.0, indexes=[1, 2, 3])
    out["ortho"] = np.clip(sample(o.astype(np.float32), tr, srcs[0].crs, order=1), 0, 255).astype(np.uint8)
    print("ortho", out["ortho"].shape)
np.savez_compressed("data/prep.npz", **out)
