"""SideQuest Bar, who made this map (Klauzál utca 26-28): found in OSM by its website, with a view of its street front.

voxelize.py adds the view ("sidequest", which the Minecraft server turns into /lm sidequest) and a pin for the web
viewer (meta["sidequest"]). Standalone, this patches an existing web/public/data/meta.json without a rebuild:

    PYTHONPATH=scripts uv run python scripts/sidequest.py
"""
import json
import math
from pathlib import Path

import numpy as np

SITE = "side-quest.bar"
NAME = "SideQuest Bar"


def find(osm):
    """-> (tags, Point) of the bar's OSM node, or None"""
    return next(((t, p) for oid, t, p in osm.nodes if SITE in t.get("website", "") or t.get("name") == NAME), None)


def street_view(osm, tags, p, ground, roof=None):
    """from across the street, 50 m above the bar's cornice and a little along the street, looking at its building"""
    street = tags.get("addr:street")
    ways = [l for i, t, l in osm.lines if "highway" in t and t.get("name") == street] \
        or [l for i, t, l in osm.lines if t.get("highway") in ("residential", "secondary", "tertiary", "pedestrian")]
    w = min(ways, key=lambda l: l.distance(p))
    s = w.project(p)
    q = w.interpolate(s)
    out = np.array([q.x - p.x, q.y - p.y])
    out /= max(float(np.linalg.norm(out)), 1e-6)
    a, b = w.interpolate(min(w.length, s + 5)), w.interpolate(max(0.0, s - 5))
    along = np.array([a.x - b.x, a.y - b.y])
    along /= max(float(np.linalg.norm(along)), 1e-6)
    cam = np.array([p.x, p.y]) + out * 70 + along * 35
    th = max(ground + 8, (roof or 0) - 6)
    return dict(label=NAME, pos=[round(float(cam[0]), 1), round(th + 50, 1), round(float(cam[1]), 1)],
                target=[round(float(p.x), 1), round(th, 1), round(float(p.y), 1)])


def door(osm, tags, p):
    """the pavement in front of the bar: [x, y] a few metres out from its front towards the street, and the heading
    (radians on the grid) that faces the door; the viewer's walk mode starts there"""
    street = tags.get("addr:street")
    ways = [l for i, t, l in osm.lines if "highway" in t and t.get("name") == street] \
        or [l for i, t, l in osm.lines if t.get("highway") in ("residential", "secondary", "tertiary", "pedestrian")]
    w = min(ways, key=lambda l: l.distance(p))
    q = w.interpolate(w.project(p))
    out = np.array([q.x - p.x, q.y - p.y])
    d = max(float(np.linalg.norm(out)), 1e-6)
    out /= d
    bld = building_of(osm, p)
    edge = np.array([p.x, p.y])
    if bld is not None:  # from the building's face, not the node inside it
        for t_ in np.arange(0, d + 0.01, 0.25):
            c = np.array([p.x, p.y]) + out * t_
            if not bld.contains(type(p)(*c)):
                edge = c
                break
    at = edge + out * min(2.5, max(d - float(np.linalg.norm(edge - [p.x, p.y])), 0) * 0.5 + 0.8)
    return [round(float(at[0]), 1), round(float(at[1]), 1)], round(math.atan2(-out[1], -out[0]), 3)


def building_of(osm, p):
    return next((geom for oid, k, t, geom in osm.areas if "building" in t and geom.contains(p)), None)


def patch_meta():
    """add the bar to a built meta.json, its roof height read from the level-2 tiles"""
    from osm import OSM
    from minecraft import DATA, N, S, read_tile
    meta_p = DATA / "meta.json"
    meta = json.loads(meta_p.read_text())
    osm = OSM()
    f = find(osm)
    if f is None:
        print("SideQuest Bar is not in the OSM data")
        return
    tags, p = f
    bld = building_of(osm, p)
    pts = [(p.x, p.y)]
    if bld is not None:
        x0, y0, x1, y1 = bld.bounds
        pts += [(x, y) for x in np.arange(math.floor(x0), x1) for y in np.arange(math.floor(y0), y1)
                if bld.contains(type(p)(x + 0.5, y + 0.5))]
    top, ground = 0.0, None
    tiles = {}
    for x, y in pts:
        tx, ty = int(x) // N, int(y) // N
        if (tx, ty) not in tiles:
            tiles[(tx, ty)] = read_tile(DATA / "tiles" / "2" / f"{tx}_{ty}.bin")
        runs, col, gr, det = tiles[(tx, ty)]
        r, c = int(y) - ty * N + 1, int(x) - tx * N + 1
        k = r * S + c
        sel = runs[col == k]
        if len(sel):
            top = max(top, float((sel[:, 0] + sel[:, 1]).max()))
        if ground is None:
            ground = float(gr[r, c])
    dp, dh = door(osm, tags, p)
    meta["sidequest"] = dict(name=NAME, x=round(p.x, 1), y=round(p.y, 1), z=round(top + 2, 1), g=round(ground, 1),
                             door=dp, heading=dh)
    meta["views"]["sidequest"] = street_view(osm, tags, p, ground, top)
    meta["views"]["sidequest"]["label_hu"] = NAME
    meta_p.write_text(json.dumps(meta, separators=(",", ":")))
    print("meta.json:", meta["sidequest"], meta["views"]["sidequest"])


if __name__ == "__main__":
    patch_meta()
