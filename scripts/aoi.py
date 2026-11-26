"""Area of interest and the one projection every pipeline step works in.

World coords: EOV, EPSG:23700 (Hungary's national grid, the CRS Lechner data comes in), x = easting, y = northing.
Grid coords: (i, j) continuous, i = column, j = row; cell (c, r) spans [c, c+1) x [r, r+1) metres. The grid is EOV
turned by THETA about the anchor, so the walls of Pest's main street grid (Terézváros, Erzsébetváros, Józsefváros) fall
on voxel faces instead of staircases: scripts/orient.py finds 41.5° (mod 90) from OSM building walls, which puts 22 %
of all wall length within 5° of a grid axis (10 % at 0°, the Lipótváros grid at 8.5° gets 10 %). With THETA = 41.5° the
grid's +i runs towards Heroes' Square (ENE) and +j towards Petőfi Bridge (SSE).

The box, 8576 x 8576 m (67 x 67 tiles of 128 m): the whole of Margaret Island up to Árpád Bridge, Újlipótváros and
Rózsadomb at the top, Kelenföld station with its whole track field and Etele tér, the National Athletics Centre, Rákóczi
Bridge and the whole Népliget at the bottom, Kelenföld and the Buda hills on the left, Keleti, the whole Városliget and
Puskás Aréna on the right; Déli, Gellért Hill and seven Danube bridges in between.
History: 4608 x 4608 m with the anchor at (1750, 2150) until early November 2026, when 384 rows went on at the top and
768 columns on the right (5376 x 4992); on 21 November 2026 512 columns went on at the left and 1536 rows at the bottom
(5888 x 6528); on 22 November 2026 2304 columns went on at the left, 128 came off the right (outer Zugló, already cut
by the edge) and 1024 rows went on at the bottom, which kept the web build under Cloudflare Pages' 20 000 files (19 870);
on 26 November 2026 1024 rows went on at the top (all of Margaret Island) and 512 columns on the left (Kelenföld
station's track field and the M4 depot), with the site's tiles bundled four to a file (web/vite.config.js) to stay
under that limit. Columns on the left move every grid i and rows at the top every grid j: the grid coordinates written
into the landmark modules were moved with them each time (+512, then +2304 on each x; then +512 on x and +1024 on y).

AOI=core (env) switches to a 2 x 2 km box around the Chain Bridge for fast iteration.
"""
import math
import os

import numpy as np
from pyproj import Transformer

WGS_TO_EOV = Transformer.from_crs(4326, 23700, always_xy=True)
EOV_TO_WGS = Transformer.from_crs(23700, 4326, always_xy=True)

ANCHOR = (19.0535, 47.4985)  # lon, lat at grid (I0, J0): Erzsébet tér
W, D = 8576, 8576
I0, J0 = 5078, 3558
if os.environ.get("AOI") == "core":
    ANCHOR = (19.0440, 47.4990)  # the Chain Bridge
    W, D = 2048, 2048
    I0, J0 = W / 2, D / 2
THETA = math.radians(float(os.environ.get("THETA_DEG", "41.5")))
CX, CY = WGS_TO_EOV.transform(*ANCHOR)
RAW = "data/raw"

EU = np.array([math.cos(THETA), math.sin(THETA)])   # grid +i in world
EV = np.array([math.sin(THETA), -math.cos(THETA)])  # grid +j in world


def to_grid(x, y):
    dx, dy = np.asarray(x) - CX, np.asarray(y) - CY
    return I0 + dx * EU[0] + dy * EU[1], J0 + dx * EV[0] + dy * EV[1]


def to_world(i, j):
    u, v = np.asarray(i) - I0, np.asarray(j) - J0
    return CX + u * EU[0] + v * EV[0], CY + u * EU[1] + v * EV[1]


def world_bounds(margin=0):
    xs, ys = to_world(np.array([0, W, W, 0]), np.array([0, 0, D, D]))
    return xs.min() - margin, ys.min() - margin, xs.max() + margin, ys.max() + margin


def wgs_bounds(margin=0):
    """(west, south, east, north) in degrees around the grid plus `margin` metres."""
    x0, y0, x1, y1 = world_bounds(margin)
    lon, lat = EOV_TO_WGS.transform(np.array([x0, x1, x0, x1]), np.array([y0, y0, y1, y1]))
    return float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())


if __name__ == "__main__":
    w, s, e, n = wgs_bounds(150)
    print(f"{s:.5f},{w:.5f},{n:.5f},{e:.5f}")  # S,W,N,E for osm_pbf.py / Overpass
