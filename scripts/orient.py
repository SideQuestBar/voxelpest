"""The dominant wall direction of the core, to turn the voxel grid onto it (aoi.THETA): a length-weighted histogram of
OSM building edge bearings mod 90 degrees, within R metres of the grid centre. Run with THETA_DEG=0.

usage: PYTHONPATH=scripts uv run python scripts/orient.py [R]
"""
import math
import sys

import numpy as np

from aoi import I0, J0
from osm import OSM

R = float(sys.argv[1]) if len(sys.argv) > 1 else 1500
osm = OSM()
ang, wt = [], []
for oid, kind, tags, poly in osm.areas_with("building"):
    if poly.centroid.distance(type(poly.centroid)(I0, J0)) > R:
        continue
    for p in getattr(poly, "geoms", [poly]):
        c = np.asarray(p.exterior.coords)
        d = np.diff(c, axis=0)
        L = np.hypot(d[:, 0], d[:, 1])
        k = L > 3
        # grid j grows south: a world bearing measured counter-clockwise from east is atan2(-dj, di)
        ang.append(np.degrees(np.arctan2(-d[k, 1], d[k, 0])) % 90)
        wt.append(L[k])
ang, wt = np.concatenate(ang), np.concatenate(wt)
h, edges = np.histogram(ang, bins=90, range=(0, 90), weights=wt)
hs = np.convolve(np.r_[h[-3:], h, h[:3]], np.ones(5) / 5, "same")[3:-3]  # circular smoothing
best = (np.argmax(hs) + 0.5) % 90
share = hs.max() / hs.mean()
print(f"dominant wall bearing {best:.1f} deg (mod 90), peak {share:.2f}x the mean; top bins:",
      [(round(float(edges[i]), 0), round(float(hs[i] / hs.mean()), 2)) for i in np.argsort(-hs)[:6]])
print(f"THETA_DEG={best if best < 45 else best - 90:.1f}")
