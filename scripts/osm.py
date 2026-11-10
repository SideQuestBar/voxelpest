"""OSM (Overpass `out geom` JSON) parsed into shapely geometries in grid coordinates (scripts/aoi.py).

Adapted from warsaw-vibe-voxel (MIT, © 2026 Piotr Migdał).
"""
import json

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import polygonize, unary_union

from aoi import D, RAW, W, WGS_TO_EOV, to_grid as _aoi_grid

CLIP = box(-300, -300, W + 300, D + 300)


def to_grid(lon, lat):
    x, y = WGS_TO_EOV.transform(lon, lat)
    i, j = _aoi_grid(x, y)
    return float(i), float(j)


def _coords(geom):
    pts = [p for p in geom if p]
    if not pts:
        return []
    x, y = WGS_TO_EOV.transform(np.array([p["lon"] for p in pts]), np.array([p["lat"] for p in pts]))
    i, j = _aoi_grid(x, y)
    return list(zip(i.tolist(), j.tolist()))


AREA_KEYS = ("building", "building:part", "landuse", "leisure", "natural", "amenity", "area:highway",
             "man_made", "place", "parking", "water", "bridge:support", "waterway", "historic")


class OSM:
    def __init__(self, path=f"{RAW}/osm.json"):
        data = json.load(open(path))
        self.timestamp = data["osm3s"]["timestamp_osm_base"]
        self.nodes = []  # (id, tags, Point)
        self.lines = []  # (id, tags, LineString)
        self.areas = []  # (id, type, tags, Polygon|MultiPolygon)
        for e in data["elements"]:
            tags = e.get("tags", {})
            if not tags:
                continue
            if e["type"] == "node":
                self.nodes.append((e["id"], tags, Point(to_grid(e["lon"], e["lat"]))))
            elif e["type"] == "way":
                geom = e.get("geometry") or []
                c = _coords(geom)
                if len(c) < 2:
                    continue
                closed = len(c) >= 4 and geom[0] and geom[-1] and geom[0] == geom[-1] and None not in geom
                is_area = closed and (tags.get("area") == "yes" or any(k in tags for k in AREA_KEYS)) \
                    and tags.get("area") != "no" and not ("highway" in tags and tags.get("area") != "yes"
                                                           and "area:highway" not in tags) \
                    and tags.get("waterway") not in ("river", "canal", "stream")
                if is_area:
                    p = Polygon(c)
                    if not p.is_valid:
                        p = p.buffer(0)
                    if p.area > 0:
                        self.areas.append((e["id"], "way", tags, p))
                else:
                    self.lines.append((e["id"], tags, LineString(c)))
            elif e["type"] == "relation" and tags.get("type") in ("multipolygon", "building"):
                outer, inner = [], []
                for m in e.get("members", []):
                    if m["type"] != "way" or not m.get("geometry"):
                        continue
                    c = _coords(m["geometry"])
                    if len(c) < 2:
                        continue
                    (inner if m.get("role") == "inner" else outer).append(LineString(c))
                if not outer:
                    continue
                o = unary_union(list(polygonize(unary_union(outer))))
                if inner:
                    i = unary_union(list(polygonize(unary_union(inner))))
                    o = o.difference(i)
                if o.is_empty or o.area == 0:
                    continue
                if not isinstance(o, (Polygon, MultiPolygon)):
                    o = o.buffer(0)
                if not o.is_valid:
                    o = o.buffer(0)
                o = o.intersection(CLIP)  # multipolygon members come whole (osm_pbf.py): the Danube runs on for km
                if o.is_empty or o.area == 0:
                    continue
                self.areas.append((e["id"], "relation", tags, o))

    def areas_with(self, key, values=None):
        return [a for a in self.areas if key in a[2] and (values is None or a[2][key] in values)]

    def lines_with(self, key, values=None):
        return [a for a in self.lines if key in a[1] and (values is None or a[1][key] in values)]

    def nodes_with(self, key, values=None):
        return [a for a in self.nodes if key in a[1] and (values is None or a[1][key] in values)]
