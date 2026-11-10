"""Draw a bench window (voxelize.py BENCH=..., data/debug/bench_*.npy and its .json) square-on: an orthographic view
along +v of a frame on the 1 m grid, the first voxel hit wins, darker with depth. The check for bridges and facades,
where preview.py's splats blur thin lattice work.

  uv run python scripts/elevation.py data/debug/bench_margit.npy out.png --at 2379.6,680.6 --ang 0.6849 --u=-260:20
  --at   frame origin x,y on the 1 m grid (OSM coordinates from osm.py; a landmark's Frame)
  --ang  angle of +u on the grid (radians); the picture's x is u, the viewer stands at --v's first value
  --u=a:b, --v=a:b   ranges in metres (write them with =, they start with a minus); --step the sampling; --scale
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("vol")
ap.add_argument("out")
ap.add_argument("--at", required=True)
ap.add_argument("--ang", type=float, default=0.0)
ap.add_argument("--u", default="-100:100")
ap.add_argument("--v", default="-60:60")
ap.add_argument("--step", type=float, default=0.25)
ap.add_argument("--scale", type=int, default=2)
ap.add_argument("--palette", default="data/debug/palette.json")
a = ap.parse_args()
meta = json.load(open(Path(a.vol).with_suffix(".json")))
r0, c0, F = meta["r0"], meta["c0"], meta["F"]
vol = np.load(a.vol)
H, ny, nx = vol.shape
pal = np.array([e[:3] for e in meta.get("palette") or json.load(open(a.palette))], np.float32)  # ids differ between runs
x0, y0 = map(float, a.at.split(","))
u0, u1 = map(float, a.u.split(":"))
v0, v1 = map(float, a.v.split(":"))
us = np.arange(u0, u1, a.step)
vs = np.arange(v0, v1, a.step if v1 > v0 else -a.step)
ca, sa = math.cos(a.ang), math.sin(a.ang)
rep = max(1, int(round(1 / (F * a.step))))  # rows per voxel, so the picture keeps the voxels' proportions
img = np.full((H * rep, len(us), 3), 235, np.float32)
hit = np.zeros((H * rep, len(us)), bool)
for k, v in enumerate(vs):
    xi = np.floor((x0 + us * ca - v * sa) * F).astype(int) - c0
    yi = np.floor((y0 + us * sa + v * ca) * F).astype(int) - r0
    ok = (xi >= 0) & (xi < nx) & (yi >= 0) & (yi < ny)
    col = np.zeros((H, len(us)), np.int64)
    col[:, ok] = vol[:, yi[ok], xi[ok]]
    col = np.repeat(col[::-1], rep, axis=0)
    new = (col > 0) & ~hit
    img[new] = pal[col[new]] * (1.0 - 0.45 * k / len(vs))
    hit |= new
rows = np.nonzero(hit.any(1))[0]
if len(rows):
    img = img[max(rows[0] - 4, 0):]
out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
out = out.resize((out.width * a.scale, out.height * a.scale), Image.NEAREST)
out.save(a.out)
print(a.out, out.width, "x", out.height)
