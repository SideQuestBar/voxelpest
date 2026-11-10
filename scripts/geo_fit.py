"""WGS84 lon/lat -> the map's grid (metres) as a quadratic in lon and lat, for the viewer's "you are here" (web/src/geo.ts).

The grid is EOV (EPSG:23700, HD72 datum: pyproj's datum shift moves a point by ~100 m) turned by THETA (aoi.py). The
fit covers the map and a 1 km margin round it, so a position just outside is placed well enough to say so. Writes
web/src/geo.ts and prints the residuals at random points against pyproj (the run fails above 0.5 m; it is under 1 mm):

    PYTHONPATH=scripts uv run python scripts/geo_fit.py
"""
import sys

import numpy as np

import aoi

MARGIN = 1000  # metres round the map


def terms(u, v):  # the order geo.ts evaluates them in
    return np.stack([np.ones_like(u), v, v * v, u, u * v, u * u], axis=-1)


def grid_of(lon, lat):
    return aoi.to_grid(*aoi.WGS_TO_EOV.transform(lon, lat))


def main():
    lon0, lat0 = aoi.ANCHOR
    w, s, e, n = aoi.wgs_bounds(MARGIN)
    ku, kv = round(2 / (e - w), 6), round(2 / (n - s), 6)  # u, v about -1..1 over the fitted box
    lon, lat = (a.ravel() for a in np.meshgrid(np.linspace(w, e, 80), np.linspace(s, n, 80)))
    A = terms((lon - lon0) * ku, (lat - lat0) * kv)
    gx, gy = grid_of(lon, lat)
    cx = np.linalg.lstsq(A, gx, rcond=None)[0].round(6)  # rounded as written below
    cz = np.linalg.lstsq(A, gy, rcond=None)[0].round(6)

    rng = np.random.default_rng(1)
    tl, ta = rng.uniform(w, e, 20000), rng.uniform(s, n, 20000)
    tx, ty = grid_of(tl, ta)
    B = terms((tl - lon0) * ku, (ta - lat0) * kv)
    err = np.hypot(B @ cx - tx, B @ cz - ty)
    inside = (tx >= 0) & (tx <= aoi.W) & (ty >= 0) & (ty <= aoi.D)
    print(f"residuals over the map: max {err[inside].max() * 1000:.2f} mm, mean {err[inside].mean() * 1000:.2f} mm;"
          f" with the {MARGIN} m margin: max {err.max() * 1000:.2f} mm", file=sys.stderr)
    if err.max() > 0.5:
        sys.exit("fit too coarse")

    fmt = lambda c: ", ".join(f"{x:.6f}" for x in c)
    src = f"""// WGS84 (GPS) -> the map's grid in metres (x = column, z = row, as the scene's x and z): a quadratic fitted to pyproj's
// EPSG:4326 -> 23700 turned by THETA (scripts/aoi.py) by scripts/geo_fit.py; under 1 mm off over the map and 1 km round it.
const LON0 = {lon0}, LAT0 = {lat0}, KU = {ku}, KV = {kv};
const CX = [{fmt(cx)}];
const CZ = [{fmt(cz)}];

export function wgsToGrid(lon: number, lat: number): [number, number] {{
  const u = (lon - LON0) * KU, v = (lat - LAT0) * KV;
  const f = (c: number[]) => c[0] + v * (c[1] + v * c[2]) + u * (c[3] + v * c[4] + u * c[5]);
  return [f(CX), f(CZ)];
}}
"""
    with open("web/src/geo.ts", "w") as f:
        f.write(src)
    print("Kossuth tér (19.0457, 47.5070) ->", *(round(float(c), 3) for c in grid_of(19.0457, 47.5070)), file=sys.stderr)


if __name__ == "__main__":
    main()
