"""Quick look at a BENCH window without the browser: a shaded orthographic view of the voxels.

  BENCH=parliament PYTHONPATH=scripts uv run python scripts/voxelize.py   # -> data/debug/bench_parliament.npy
  uv run python scripts/preview.py data/debug/bench_parliament.npy out.png --az 220 --el 18 --zmin 20

--az turns the view about the vertical (220 looks at the Parliament from the river); --el 89.9 is a plan view;
--crop r0:r1,c0:c1 cuts the window (rows, cols in 0.5 m voxels); --scale is pixels per voxel. Voxels are splatted, not
meshed, so thin things look noisier than in the viewer; use it for shapes and proportions, the viewer for the look.
"""
import argparse
import json
import math

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("vol")
ap.add_argument("out")
ap.add_argument("--palette", default="data/debug/palette.json")
ap.add_argument("--az", type=float, default=30)
ap.add_argument("--el", type=float, default=30)
ap.add_argument("--zmin", type=int, default=0)
ap.add_argument("--crop")
ap.add_argument("--scale", type=int, default=3)
a = ap.parse_args()

vol = np.load(a.vol)
pal = json.load(open(a.palette))
pal = np.array(pal["palette"] if isinstance(pal, dict) else pal, np.float32)[:, :3]  # a bench window's .json carries its own
if a.crop:
    rs, cs = a.crop.split(",")
    r0, r1 = map(int, rs.split(":"))
    c0, c1 = map(int, cs.split(":"))
    vol = vol[:, r0:r1, c0:c1]
vol = vol[a.zmin:]
H, R, C = vol.shape
occ = np.pad(vol != 0, 1)
z, r, c = np.nonzero(vol)
v = vol[z, r, c]
up = ~occ[z + 2, r + 1, c + 1]
sides = [~occ[z + 1, r + 1, c], ~occ[z + 1, r + 1, c + 2], ~occ[z + 1, r, c + 1], ~occ[z + 1, r + 2, c + 1]]
shown = up | sides[0] | sides[1] | sides[2] | sides[3]
z, r, c, v, up = z[shown], r[shown], c[shown], v[shown], up[shown]
sides = [s[shown] for s in sides]
L = np.array([-0.5, -0.6, 0.62])
L /= np.linalg.norm(L)
shade = np.full(len(z), 0.55)
for s, (nx, ny) in zip(sides, [(-1, 0), (1, 0), (0, -1), (0, 1)]):
    shade = np.where(s, np.maximum(shade, 0.62 + 0.35 * max(0.0, nx * L[0] + ny * L[1])), shade)
shade = np.where(up, 1.0, shade)
az, el = math.radians(a.az), math.radians(a.el)
x, y = c - C / 2, r - R / 2
sx = x * math.cos(az) - y * math.sin(az)
depth = x * math.sin(az) + y * math.cos(az)
sy = -z * math.cos(el) + depth * math.sin(el)
near = depth * math.cos(el) + z * math.sin(el)
S = a.scale
px = ((sx - sx.min()) * S).astype(int)
py = ((sy - sy.min()) * S).astype(int)
img = np.full((py.max() + 2 * S, px.max() + 2 * S, 3), 238, np.float32)
order = np.argsort(near)  # far first, near last
col = pal[v] * shade[:, None]
for dy in range(S):
    for dx in range(S):
        img[py[order] + dy, px[order] + dx] = col[order]
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(a.out)
print(a.out, img.shape[1], "x", img.shape[0])
