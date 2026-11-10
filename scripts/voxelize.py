"""Fuse OSM, building heights and the Copernicus surface model into a 0.5 m voxel Budapest, and export it as streamable
tiles (scripts/tiles.py) plus web/public/data/meta.json.

Sources (all fetched by scripts/fetch_all.sh, put on one grid by scripts/prep.py and aoi.py):
  OSM (BBBike / Geofabrik)    footprints, building parts, heights / levels / roof shapes / colours, ground surfaces,
                              roads, rails, water, bridges, trees, street lamps, names
  GlobalBuildingAtlas         3 m building-height raster: a measured height for every footprint OSM leaves untagged
  Átló / Urban Atlas 2012     building height per OSM building (10 m raster joined to footprints)
  Copernicus DEM GLO-30       the land: a 30 m surface model, from which the buildings and the tree canopy are taken
                              back out to leave the ground (scripts/voxelize.py, section "ground")

Two grids. The analysis grid is aoi.py's 1 m grid, rasters [row, col] = [j, i]: heights, roofs, the ground and bridges
are worked out there, in metres. The render grid is 2x finer (VOX = 0.5 m): build() rasterizes footprints, roads and
decks again at 0.5 m for one window at a time, interpolates the ground and the roof surfaces, and adds the hand-built
landmarks (scripts/landmarks.py). The volume is vol[z, row, col] in 0.5 m voxels, z from the model base.
"""
import json
import math
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely
import shapely.ops
from affine import Affine
from rasterio.features import rasterize as _rz
from scipy import ndimage
import shapely.geometry
from shapely.geometry import LineString, Point, box

import landmarks
import landmarks_erkel
import landmarks_sidequest
import landmarks_westend
import sidequest
import tiles
import trees as trees_mod
from aoi import CX, CY, D, EOV_TO_WGS, THETA, W, to_world
from osm import OSM
from style import (BARK_IDS, C, CLASSIC, GLASS, LAMP, LEAF, MATERIAL_ROOF, MATERIAL_WALL, ROOF, ROOFS_FLAT, ROOFS_PITCHED,
                   TENEMENT, WALL, WALLS, hex_rgb, pal, parse_colour, parse_len, stable_hash, tame)

OUT = Path("web/public/data")
DBG = Path("data/debug")
OUT.mkdir(parents=True, exist_ok=True)
DBG.mkdir(parents=True, exist_ok=True)
report = {"notes": []}
T0 = time.time()


def note(*a):
    s = " ".join(str(x) for x in a)
    print(f"[{time.time() - T0:6.0f}s] {s}", flush=True)
    report["notes"].append(s)


ID = Affine.identity()


def raster(shapes, dtype=np.uint8, fill=0, all_touched=False):
    shapes = [(g, v) for g, v in shapes if g is not None and not g.is_empty]
    if not shapes:
        return np.full((D, W), fill, dtype)
    return _rz(shapes, out_shape=(D, W), transform=ID, fill=fill, dtype=dtype, all_touched=all_touched)


def mask_of(geoms, all_touched=False):
    return raster([(g, 1) for g in geoms], all_touched=all_touched).astype(bool)


VOX = 0.5
F = int(round(1 / VOX))  # render voxels per metre
WF, DF = W * F, D * F
FT = Affine.scale(1 / F)


def mask_f(geoms, all_touched=False):
    shapes = [(g, 1) for g in geoms if g is not None and not g.is_empty]
    if not shapes:
        return np.zeros((DF, WF), bool)
    return _rz(shapes, out_shape=(DF, WF), transform=FT, fill=0, dtype=np.uint8, all_touched=all_touched).astype(bool)


def cells_f(geom, all_touched=False):
    """the 0.5 m cells of a geometry (given in 1 m grid coordinates) -> fine (rows, cols)."""
    x0, y0, x1, y1 = geom.bounds
    c0, r0 = max(int(math.floor(x0 * F)), 0), max(int(math.floor(y0 * F)), 0)
    c1, r1 = min(int(math.ceil(x1 * F)) + 1, WF), min(int(math.ceil(y1 * F)) + 1, DF)
    if c0 >= c1 or r0 >= r1:
        return np.zeros(0, int), np.zeros(0, int)
    m = _rz([(geom, 1)], out_shape=(r1 - r0, c1 - c0), transform=Affine(1 / F, 0, c0 / F, 0, 1 / F, r0 / F), fill=0,
            dtype=np.uint8, all_touched=all_touched)
    rr, cc = np.nonzero(m)
    return rr + r0, cc + c0


def coarse(m):
    """a 0.5 m mask -> 1 m (majority)."""
    return m.reshape(D, F, W, F).mean((1, 3), dtype=np.float32) >= 0.5


def cells_of(geom, all_touched=False):
    x0, y0, x1, y1 = geom.bounds
    c0, r0 = max(int(math.floor(x0)), 0), max(int(math.floor(y0)), 0)
    c1, r1 = min(int(math.ceil(x1)) + 1, W), min(int(math.ceil(y1)) + 1, D)
    if c0 >= c1 or r0 >= r1:
        return np.zeros(0, int), np.zeros(0, int)
    m = _rz([(geom, 1)], out_shape=(r1 - r0, c1 - c0), transform=Affine.translation(c0, r0), fill=0, dtype=np.uint8,
            all_touched=all_touched)
    rr, cc = np.nonzero(m)
    return rr + r0, cc + c0


def group_pct(labels, values, n, q):
    """per-label q-quantile of values (labels 1..n, 0 ignored) -> array [n + 1] (nan where empty)."""
    m = labels > 0
    lab, v = labels[m], values[m]
    o = np.lexsort((v, lab))
    lab, v = lab[o], v[o]
    ids = np.arange(1, n + 1)
    a, b = np.searchsorted(lab, ids), np.searchsorted(lab, ids, side="right")
    out = np.full(n + 1, np.nan, np.float32)
    ok = b > a
    out[1:][ok] = v[(a + (q * (b - a - 1)).astype(int))[ok]]
    return out


def gauss(a, s):
    return ndimage.gaussian_filter(a, s, mode="nearest")


def is_off(t, k):
    return t.get(k, "no") not in ("no", "")


# ---------------------------------------------------------------- inputs
osm = OSM()
P = np.load("data/prep.npz")
dsm = P["dsm"]
dtm = P["dtm"] if "dtm" in P else None  # FABDEM bare earth
s2 = P["s2"] if "s2" in P else None     # Sentinel-2 true colour
gba = P["gba"].astype(np.float32)
ortho = P["ortho"] if "ortho" in P else None
atlo = json.load(open("data/raw/heights/atlo_heights.json"))
note("osm", osm.timestamp, len(osm.areas), "areas", len(osm.lines), "lines", len(osm.nodes), "nodes")

# ---------------------------------------------------------------- ground surfaces
LANDUSE = {"grass": "grass", "meadow": "grass", "village_green": "grass", "flowerbed": "flower", "forest": "forest",
           "cemetery": "grass2", "allotments": "garden", "recreation_ground": "grass", "construction": "dirt",
           "brownfield": "dirt", "railway": "ballast", "religious": "paving", "orchard": "grass2",
           "vineyard": "grass2", "plant_nursery": "garden", "greenfield": "grass"}
NATURAL = {"wood": "forest", "scrub": "garden", "grassland": "grass", "heath": "grass2", "sand": "sand",
           "bare_rock": "rock", "scree": "rock", "beach": "sand", "shingle": "gravel"}
LEISURE = {"park": "grass2", "garden": "garden", "pitch": "pitch", "playground": "gravel", "dog_park": "gravel",
           "sports_centre": "paving", "stadium": "paving", "track": "track", "golf_course": "grass",
           "swimming_pool": "pool", "water_park": "paving", "fitness_station": "gravel", "schoolyard": "paving"}
SURF = {"asphalt": "asphalt", "paving_stones": "paving", "sett": "sett", "cobblestone": "sett",
        "unhewn_cobblestone": "sett", "concrete": "concrete", "concrete:plates": "concrete", "gravel": "gravel",
        "fine_gravel": "gravel", "compacted": "gravel", "pebblestone": "gravel", "unpaved": "gravel", "grass": "grass",
        "dirt": "dirt", "ground": "dirt", "earth": "dirt", "mud": "dirt", "sand": "sand", "wood": "woodfloor",
        "artificial_turf": "pitch", "tartan": "track", "clay": "court", "grass_paver": "grass"}
HW = {"motorway": 20, "trunk": 14, "primary": 12, "secondary": 10, "tertiary": 8, "unclassified": 6,
      "residential": 6, "living_street": 5, "service": 4, "road": 6, "busway": 6, "motorway_link": 7, "trunk_link": 7,
      "primary_link": 7, "secondary_link": 6, "tertiary_link": 6, "pedestrian": 6, "footway": 2.5, "path": 2,
      "cycleway": 2.5, "steps": 3, "track": 3, "bridleway": 2, "corridor": 2, "platform": 3}
ROADS = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street",
         "service", "road", "busway", "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}


def underground(t):
    return is_off(t, "tunnel") or t.get("covered") == "yes" or (parse_len(t.get("layer")) or 0) < 0 \
        or t.get("location") in ("underground", "indoor") or t.get("indoor") not in (None, "no") or t.get("level", "0").startswith("-")


def on_bridge(t):
    return is_off(t, "bridge") and (parse_len(t.get("layer")) or 1) >= 1


LANE_W = {"motorway": 3.5, "trunk": 3.5, "primary": 3.3, "secondary": 3.2, "tertiary": 3.0, "unclassified": 2.9,
          "residential": 2.9, "living_street": 2.8, "service": 2.8, "road": 3.0, "busway": 3.3}
PARK_W = {"lane": 2.2, "half_on_kerb": 1.2, "on_kerb": 0.0, "street_side": 0.0, "separate": 0.0, "no": 0.0, "none": 0.0}


def road_profile(t, kind):
    """a car road's cross-section from its tags -> (lanes, lane width, parking left, parking right, cycle lanes, total):
    lanes * lane width, plus parking lanes (parking:left/right/both) and painted cycle lanes; tram tracks in the road
    (embedded_rails) add 6.5 m. Untagged streets get one lane if one-way (two otherwise, four for two-way primaries),
    and, in residential and tertiary streets, a parking lane each side -- the street canyon trims it if there's no room."""
    lw = LANE_W.get(kind.replace("_link", ""), 3.0)
    oneway = t.get("oneway") in ("yes", "1", "-1") or t.get("junction") in ("roundabout", "circular")
    n = parse_len(t.get("lanes")) or ((parse_len(t.get("lanes:forward")) or 0) + (parse_len(t.get("lanes:backward")) or 0)) or None
    if not n:
        n = 1 if oneway or kind in ("service", "living_street") else 4 if kind in ("primary", "trunk") else 2
    sides = []
    for side in ("left", "right"):
        pk = t.get(f"parking:{side}") or t.get("parking:both")
        pw = PARK_W.get(pk, 0.0) if pk else (2.0 if kind in ("residential", "tertiary", "unclassified", "living_street") else 0.0)
        cy = t.get(f"cycleway:{side}") or t.get("cycleway:both") or t.get("cycleway")
        sides.append((pw, 1.5 if cy == "lane" else 0.0))
    (pl, cl), (pr, cr) = sides
    tram = 6.5 if t.get("embedded_rails") == "tram" else 0.0
    total = n * lw + pl + pr + cl + cr + tram
    return int(n), lw, pl, pr, cl + cr, total


def width_of(t, kind):
    w = parse_len(t.get("width"))
    if w and 1 <= w <= 40:
        return w
    if kind in ROADS or kind == "busway":
        return road_profile(t, kind)[-1]
    return HW.get(kind, 3)


# areas of carriageway (after warsaw-vibe-voxel): a junction's square, bus bays, crossings
AH_ROAD = {"junction", "bus_bay", "bus", "crossing", "tram", "taxi_stop", "passing_place", "shoulder", "emergency",
           "prohibited", "busway"}
gcol = np.full((DF, WF), C["paving2"], np.uint16)  # 0.5 m; courtyards, pavements: what OSM leaves unsaid is paved
ground_areas = []
for oid, kind, t, g in osm.areas:
    if "building" in t or "building:part" in t or underground(t) or t.get("parking") in ("underground", "multi-storey", "rooftop"):
        continue
    k = None
    if t.get("landuse") in LANDUSE:
        k = LANDUSE[t["landuse"]]
    if t.get("natural") in NATURAL:
        k = NATURAL[t["natural"]]
    if t.get("leisure") in LEISURE:
        k = LEISURE[t["leisure"]]
        if k in ("pitch", "paving", "track") and t.get("surface") in SURF:
            k = SURF[t["surface"]]
    if t.get("amenity") == "parking":
        k = SURF.get(t.get("surface"), "parking")
    if t.get("amenity") == "fountain":
        k = "pool"
    if t.get("place") == "square" or t.get("highway") in ("pedestrian", "footway") or "area:highway" in t:
        ah = t.get("area:highway") or t.get("highway")
        if ah == "yes" and t.get("junction"):
            ah = "junction"
        carriage = ah in ROADS or ah in AH_ROAD
        k = SURF.get(t.get("surface"), "asphalt" if carriage else "paving")
        if carriage and k == "paving":
            k = "road_paving"
    if t.get("railway") == "platform" or t.get("public_transport") == "platform":
        k = "platform"
    if k:
        ground_areas.append((g, C[k], g.area, oid))
# flowerbeds: foliage dotted with blooms, two colours a bed (a solid pink read as paint, not flowers)
BLOOMS = [(C["bloom_red"], C["bloom_white"]), (C["bloom_yellow"], C["bloom_violet"]), (C["bloom_red"], C["bloom_yellow"]),
          (C["bloom_white"], C["bloom_violet"]), (C["bloom_orange"], C["bloom_yellow"]), (C["bloom_red"], C["bloom_orange"])]
for g, pid, _, oid in sorted(ground_areas, key=lambda a: -a[2]):  # big first: what's mapped inside them is painted later
    rr, cc = cells_f(g)
    if pid == C["flower"]:
        b1, b2 = BLOOMS[stable_hash(oid) % len(BLOOMS)]
        hh = ((rr.astype(np.int64) * 73856093) ^ (cc.astype(np.int64) * 19349663)) % 100
        gcol[rr, cc] = np.where(hh < 42, C["foliage"], np.where(hh < 60, C["grass"], np.where(hh < 82, b1, b2)))
    else:
        gcol[rr, cc] = pid
note("ground areas", len(ground_areas))

# water: one flat surface per water body; the Danube at the median of the DSM over it (Copernicus flattens rivers)
river = np.zeros((D, W), bool)
wlev = np.full((D, W), np.nan, np.float32)
waters = [a for a in osm.areas if not underground(a[2]) and (a[2].get("natural") == "water" or a[2].get("waterway") == "riverbank"
                                                             or a[2].get("landuse") in ("reservoir", "basin"))]
for oid, kind, t, g in sorted(waters, key=lambda a: -a[3].area):
    rr, cc = cells_of(g)
    if not len(rr):
        continue
    if t.get("water") == "river" or t.get("waterway") == "riverbank" or t.get("name") == "Duna":
        river[rr, cc] = True
    else:
        wlev[rr, cc] = np.percentile(dsm[rr, cc], 15)
    fr, fc = cells_f(g)
    gcol[fr, fc] = C["water"]
WL = float(np.median(dsm[river])) if river.any() else 97.0
wlev[river] = WL
note(f"water: Danube {river.sum() / 1e6:.2f} km2 at {WL:.2f} m; ponds {int(np.isfinite(wlev).sum() - river.sum())} cells")

# roads, paths, rails (lines); bridges go on their decks, tunnels nowhere
bridge_ways = []
by_pid = defaultdict(list)
order = {"footway": 0, "path": 0, "cycleway": 1, "steps": 1, "track": 1, "pedestrian": 2, "service": 3, "living_street": 3,
         "residential": 4, "unclassified": 4, "road": 4, "tertiary_link": 5, "secondary_link": 5, "primary_link": 5,
         "tertiary": 6, "secondary": 7, "primary": 8, "trunk_link": 8, "trunk": 9, "motorway_link": 9, "motorway": 10}
# a carriageway is as wide as its lanes and parking (road_profile), but never wider than the street: at every 3 m it
# keeps 2 m of pavement to the nearest building wall, and stays short of the sidewalks OSM maps as their own ways
bld_early = mask_of([g for oid, kind, t, g in osm.areas if t.get("building", "no") not in ("no", "roof", "construction")
                     and not underground(t) and g.area > 6])
d_bld = ndimage.distance_transform_edt(~bld_early).astype(np.float32)
sidewalks = [ln for oid, t, ln in osm.lines if t.get("footway") == "sidewalk" and not underground(t) and not on_bridge(t)]
d_sw = ndimage.distance_transform_edt(~mask_of([ln.buffer(0.6) for ln in sidewalks])).astype(np.float32) if sidewalks else None
del bld_early


def canyon(ln, half, step=3.0, chunk=12.0):
    """split a way into ~12 m pieces, each with the half-width the street has room for."""
    out = []
    L = ln.length
    n = max(1, int(round(L / chunk)))
    for k in range(n):
        piece = shapely.ops.substring(ln, L * k / n, L * (k + 1) / n)
        ss = np.linspace(0, piece.length, max(2, int(piece.length / step) + 1))
        pts = np.array([piece.interpolate(x).coords[0] for x in ss])
        c, r = np.clip(pts[:, 0].astype(int), 0, W - 1), np.clip(pts[:, 1].astype(int), 0, D - 1)
        room = d_bld[r, c] - 2.0
        if d_sw is not None:
            room = np.minimum(room, np.where(d_sw[r, c] < 12, d_sw[r, c] - 0.9, 99))
        out.append((piece, float(np.clip(min(half, np.median(room)), 1.6, half))))
    return out


marks = []  # (offset curve, dashed?) for lane lines
parks = []
narrowed = 0
# a service road or driveway with no surface of its own through a paved square takes the square's
_paved = [(g, t["surface"]) for oid, kind, t, g in osm.areas if t.get("surface") in SURF and not underground(t)
          and ("area:highway" in t or t.get("highway") in ("pedestrian", "footway") or t.get("place") == "square")]
_ptree = shapely.STRtree([g for g, _ in _paved]) if _paved else None


def area_surface(ln):
    if _ptree is None:
        return None
    for i in _ptree.query(ln):
        g_, s_ = _paved[i]
        if ln.intersection(g_).length > 0.6 * ln.length:
            return s_
    return None


n_inherit = 0
road_lines = []  # (osm id, centreline, its colour): checked against the finished ground below
for oid, t, ln in osm.lines:
    hw = t.get("highway")
    if hw not in HW or t.get("area") == "yes" or underground(t):
        continue
    if on_bridge(t):
        bridge_ways.append((oid, t, ln))
        continue
    k = SURF.get(t.get("surface"), "asphalt" if hw in ROADS or hw == "busway" else "paving")
    if (hw in ROADS or hw == "busway") and k == "paving":
        k = "road_paving"  # a carriageway of paving stones in the pavement's colour vanished into it: darker granite
    if hw in ("service", "living_street") and "surface" not in t:
        s_ = area_surface(ln)
        if s_ is not None:
            k = SURF[s_]
            n_inherit += 1
    if hw == "cycleway" and "surface" not in t:
        k = "cycle"
    if hw == "steps":
        k = "steps"
    if hw in ("footway", "path") and t.get("footway") == "crossing":
        continue  # painted as markings on the road
    if hw not in ROADS and hw != "busway":
        by_pid[(order.get(hw, 0), C[k])].append(ln.buffer(width_of(t, hw) / 2, cap_style="round"))
        continue
    n, lw, pl, pr, cyc, total = road_profile(t, hw)
    wt = parse_len(t.get("width"))
    half = (wt if wt and 2 <= wt <= 40 else total) / 2
    if hw not in ("service", "living_street"):
        road_lines.append((oid, ln, C[k]))
    for piece, h in canyon(ln, half):
        narrowed += h < half - 0.5
        by_pid[(order.get(hw, 0), C[k])].append(piece.buffer(h, cap_style="flat", join_style="mitre", mitre_limit=2.0))
        if k != "asphalt" or piece.length < 2:
            continue
        # parking strips along the kerbs: what is left of the half-width beyond the lanes, on a side that has parking
        lanes_half = min(h, (n * lw + cyc) / 2 + 0.2)
        if h - lanes_half > 1.0 and (pl > 0 or pr > 0):
            parks.append(piece.buffer(h, cap_style="flat").difference(piece.buffer(lanes_half, cap_style="flat")))
        # lane lines between lanes (dashed), and the line between the two directions of a two-way road
        if n >= 2 and t.get("lane_markings") != "no" and hw not in ("service", "living_street"):
            lw_eff = min(lw, 2 * lanes_half / n)
            oneway = t.get("oneway") in ("yes", "1", "-1")
            nb = 0 if oneway else int(parse_len(t.get("lanes:backward")) or n // 2)
            for j in range(1, n):
                off = -lanes_half + 0.2 + j * lw_eff
                if abs(off) > h - 0.6:
                    continue
                solid = (j == nb) and n >= 4
                marks.append((piece.offset_curve(off) if abs(off) > 0.05 else piece, not solid))
for (_, pid), gs in sorted(by_pid.items()):
    gcol[mask_f(gs)] = pid
road_now = np.isin(gcol, [C["asphalt"]])
# no lane lines across a junction (after warsaw-vibe-voxel): within the widest road's half-width plus 4 m of every node
# where three or more street segments meet (driveways and service roads don't count), and over junction areas
_deg, _jhw = defaultdict(int), defaultdict(float)
for oid, t, ln in osm.lines:
    hw = t.get("highway")
    if (hw not in ROADS and hw != "busway") or hw in ("service", "living_street") or t.get("area") == "yes" \
            or underground(t) or on_bridge(t):
        continue
    xy = [(round(x_, 1), round(y_, 1)) for x_, y_ in ln.coords]
    for j, p_ in enumerate(xy):
        _deg[p_] += (j > 0) + (j < len(xy) - 1)
        _jhw[p_] = max(_jhw[p_], min(width_of(t, hw), 30) / 2)
junctions = [Point(p_).buffer(_jhw[p_] + 4.0, 12) for p_, d_ in _deg.items() if d_ >= 3]
junctions += [g for oid, kind, t, g in osm.areas if t.get("area:highway") and t.get("junction") and not underground(t)]
road_now &= ~mask_f(junctions)
del _deg, _jhw
if parks:
    pm = mask_f(parks)
    gcol[pm & road_now] = C["parking_lane"]
    del pm
nm = 0
for ln, dashed in marks:
    if ln.is_empty or ln.length < 3:
        continue
    rr, cc = cells_f(ln.buffer(0.22, cap_style="flat"))
    if not len(rr):
        continue
    ok = road_now[rr, cc]
    if dashed:
        s = shapely.line_locate_point(ln, shapely.points((cc + 0.5) / F, (rr + 0.5) / F))
        ok &= np.mod(s, 9.0) < 3.0
    gcol[rr[ok], cc[ok]] = C["mark"]
    nm += 1
del road_now
note(f"roads: {narrowed} pieces narrowed to their street; {len(parks)} parking strips; {nm} lane lines, none over "
     f"{len(junctions)} junctions; {n_inherit} service roads take their square's surface")
rails, trams = [], []
for oid, t, ln in osm.lines:
    rw = t.get("railway")
    if rw not in ("rail", "light_rail", "narrow_gauge", "tram", "funicular", "preserved") or underground(t):
        continue
    if on_bridge(t):
        bridge_ways.append((oid, t, ln))
        continue
    (trams if rw == "tram" else rails).append(ln)
gcol[mask_f([ln.buffer(2.0) for ln in rails])] = C["ballast"]
road = np.isin(gcol, [C["asphalt"], C["sett"], C["road_paving"], C["parking"], C["parking_lane"], C["mark"]])
tb = mask_f([ln.buffer(1.4) for ln in trams])
gcol[tb & ~road] = C["trambed"]
gcol[mask_f([ln.buffer(0.95).difference(ln.buffer(0.5)) for ln in rails + trams], all_touched=True)] = C["rail"]
note("lines:", sum(len(v) for v in by_pid.values()), "ways,", len(rails), "rail,", len(trams), "tram;", len(bridge_ways), "on bridges")

# zebra crossings: stripes along the road across the crossing way, 0.8 m on, 0.8 m off
zebra = 0
for oid, t, ln in osm.lines:
    if t.get("footway") != "crossing" or t.get("crossing") in ("unmarked", "no") or underground(t) or on_bridge(t):
        continue
    rr, cc = cells_f(ln.buffer(1.6, cap_style="flat"))
    if not len(rr):
        continue
    s = shapely.line_locate_point(ln, shapely.points((cc + 0.5) / F, (rr + 0.5) / F))
    k = (np.floor(s / 0.8).astype(int) % 2 == 0) & np.isin(gcol[rr, cc], [C["asphalt"], C["road_paving"], C["parking_lane"], C["mark"], C["kerb"]])
    gcol[rr[k], cc[k]] = C["mark"]
    zebra += 1
note("zebra crossings", zebra)
# kerbstones: a 0.5 m granite line where carriageway meets pavement
kb_road = np.isin(gcol, [C["asphalt"], C["parking_lane"], C["mark"], C["sett"], C["road_paving"]])
kb_walk = np.isin(gcol, [C["paving"], C["paving2"], C["platform"], C["steps"]])
for r0 in range(0, DF, 1024):  # in bands: the 0.5 m masks are 100 MB each
    a, b = max(r0 - 1, 0), min(r0 + 1025, DF)
    walk_near = ndimage.binary_dilation(kb_walk[a:b], structure=np.ones((3, 3), bool))
    k = (kb_road[a:b] & walk_near)[r0 - a:r0 - a + min(1024, DF - r0)]
    gcol[r0:r0 + k.shape[0]][k] = C["kerb"]
del kb_road, kb_walk, walk_near, k
# every street's centreline in its own colour (after warsaw-vibe-voxel's check): a square or area drawn over a road cuts it
_ped = np.zeros(65536, bool)
_ped[[C[k_] for k_ in ("paving", "paving2", "steps", "platform", "gravel", "grass", "grass2", "garden", "dirt")]] = True
_bad = []
for oid, ln, own in road_lines:
    pts = shapely.line_interpolate_point(ln, np.arange(0.5, ln.length, 1.0))
    if not len(pts):
        continue
    xy = shapely.get_coordinates(pts)
    xy = xy[(xy[:, 0] >= 0) & (xy[:, 0] < W) & (xy[:, 1] >= 0) & (xy[:, 1] < D)]
    v_ = gcol[(xy[:, 1] * F).astype(int), (xy[:, 0] * F).astype(int)]
    off = int((_ped[v_] & (v_ != own)).sum())
    if off >= 6:
        _bad.append((off, oid))
_bad.sort(reverse=True)
note(f"carriageway check: {len(_bad)} streets with 6 m or more of their centreline painted as pavement {_bad[:8]}")
report["carriageway_cut"] = _bad[:200]
water_f = gcol == C["water"]
water = coarse(water_f)
road = coarse(np.isin(gcol, [C["asphalt"], C["sett"], C["road_paving"], C["parking"], C["rail"], C["trambed"], C["ballast"], C["mark"], C["parking_lane"], C["kerb"]]))
grassy = coarse(np.isin(gcol, [C["grass"], C["grass2"], C["garden"], C["forest"], C["pitch"]]))
gcol1 = gcol[::F, ::F]  # 1 m view, for the debug image

# ---------------------------------------------------------------- buildings: features and heights
TYPE_H = {"house": 8, "detached": 8, "semidetached_house": 8, "garage": 3, "garages": 3, "shed": 3, "kiosk": 3.5,
          "roof": 5, "carport": 3, "service": 4, "toilets": 3, "hut": 3, "greenhouse": 3, "transformer_tower": 6,
          "church": 22, "cathedral": 30, "chapel": 10, "synagogue": 20, "apartments": 20, "residential": 18,
          "commercial": 14, "retail": 8, "office": 20, "industrial": 9, "warehouse": 9, "school": 16, "university": 18,
          "hospital": 18, "hotel": 22, "public": 18, "government": 20, "train_station": 16, "civic": 15, "parking": 12,
          "stadium": 20, "grandstand": 10, "dormitory": 18, "college": 16, "museum": 18, "bunker": 3}
FLAT_TYPES = {"roof", "garage", "garages", "shed", "kiosk", "carport", "industrial", "warehouse", "retail",
              "commercial", "parking", "service", "transformer_tower", "grandstand", "stadium", "toilets", "bunker"}
RELIGIOUS = {"church", "cathedral", "chapel", "synagogue", "basilica", "mosque", "temple", "shrine"}
TENEMENTISH = {"apartments", "residential", "yes", "house", "hotel", "commercial", "office", "public", "government",
               "university", "school", "hospital", "retail", "dormitory", "college", "civic", "museum"}
SHAPE = {"flat": 0, "gabled": 1, "hipped": 1, "side_hipped": 1, "half-hipped": 1, "quadruple_saltbox": 1,
         "double_saltbox": 1, "saltbox": 1, "gambrel": 2, "mansard": 2, "dome": 3, "onion": 3, "pyramidal": 4,
         "cone": 4, "spire": 4, "skillion": 5, "round": 1, "many": 1, "crosspitched": 1}
SLOPE = 0.75  # pitched roofs at ~37°

feats = []
for oid, kind, t, g in osm.areas:
    part = is_off(t, "building:part")
    if not part and t.get("building", "no") in ("no", "demolished", "razed", "construction", "proposed", "ruins"):
        continue
    if underground(t) or g.area < 2:
        continue
    feats.append(dict(id=oid, kind=kind, t=t, geom=g, part=part, area=g.area,
                      type=t.get("building") if not part else (t.get("building") or t.get("building:part"))))
# monuments with a height but no building tag: the Millennium Monument's colonnades, the 40.8 m column of the Archangel
# Gabriel on Heroes' Square (a column on a pedestal when it is tall and its footprint is wide)
STONE = "#dcd4c2"
for oid, kind, t, g in osm.areas:
    H = parse_len(t.get("height"))
    if t.get("historic") not in ("monument", "memorial") or "building" in t or "building:part" in t or not H or underground(t):
        continue
    if H > 25 and g.area > 40:
        feats.append(dict(id=oid, kind=kind, t={"height": str(min(7.0, H * 0.18)), "roof:shape": "flat", "building:colour": STONE,
                                                 "name": t.get("name", "")}, geom=g, part=False, area=g.area, type="monument",
                          mat_override=CLASSIC))
        col = g.centroid.buffer(1.8, 12)
        feats.append(dict(id=f"{oid}c", kind="add", t={"height": str(H), "roof:shape": "pyramidal", "roof:height": "5",
                                                        "building:colour": STONE, "roof:colour": "#5a7f6a"},
                          geom=col, part=True, area=col.area, type="monument", mat_override=CLASSIC))
    else:
        feats.append(dict(id=oid, kind=kind, t={"height": str(H), "roof:shape": "flat", "building:colour": STONE, "name": t.get("name", "")},
                          geom=g, part=False, area=g.area, type="monument", mat_override=CLASSIC))
# hand-curated detail (scripts/overrides.json): tags OSM gets wrong, parts it doesn't map
OVR = json.load(open(Path(__file__).with_name("overrides.json")))
TAGMAP = {"height": "height", "min_height": "min_height", "roof_shape": "roof:shape", "roof_height": "roof:height",
          "wall_colour": "building:colour", "roof_colour": "roof:colour"}
MATS = {"wall": WALL, "tenement": TENEMENT, "classic": CLASSIC, "glass": GLASS, "solid": 0}


def apply_override(f, o):
    for k, tk in TAGMAP.items():
        if k in o:
            f["t"][tk] = str(o[k])
    if "material" in o:
        f["mat_override"] = MATS[o["material"]]


feats = [f for f in feats if not OVR["osm"].get(str(f["id"]), {}).get("drop")]
for f in feats:
    if str(f["id"]) in OVR["osm"]:
        f["t"] = dict(f["t"])
        apply_override(f, OVR["osm"][str(f["id"])])
from osm import to_grid as _tg
for k, o in enumerate(OVR["add"]):
    x, y = _tg(o["lon"], o["lat"])
    f = dict(id=f"add{k}", kind="add", t={"building:part": "yes", "name": o["name"]}, geom=Point(x, y).buffer(o["radius"], 24),
             part=True, type="yes")
    f["area"] = f["geom"].area
    apply_override(f, o)
    feats.append(f)
note("overrides:", len(OVR["osm"]), "edited,", len(OVR["add"]), "added")
# the landmarks built by hand (scripts/landmarks.py) replace what OSM maps of them
LMK = landmarks.Plan(osm)
nf = len(feats)
feats = [f for f in feats if str(f["id"]).rstrip("c") not in LMK.drop]
note("landmarks:", ", ".join(LMK.names), f"replace {nf - len(feats)} OSM buildings / parts")
hosts = [f["geom"].buffer(1) for f in feats if not f["part"] and str(f["id"]) in {str(i) for i in LMK.classic}]
for f in feats:  # the stone of the Parliament, the Basilica, Matthias Church and the palace: no office windows
    if f["id"] in LMK.classic or (f["part"] and any(h.contains(f["geom"].centroid) for h in hosts)):
        f["mat_override"] = CLASSIC
outlines = [f for f in feats if not f["part"]]
parts = [f for f in feats if f["part"]]
note("buildings", len(outlines), "outlines,", len(parts), "parts")

# measured heights: GBA (75th percentile inside the footprint: it under-reads roofs) and Átló's Urban Atlas value
lab = raster([(f["geom"], i + 1) for i, f in sorted(enumerate(outlines), key=lambda x: -x[1]["area"])], np.int32)
p_gba = group_pct(lab, gba, len(outlines), 0.75)
ncell = np.bincount(lab.ravel(), minlength=len(outlines) + 1)
for i, f in enumerate(outlines):
    f["gba"] = float(p_gba[i + 1]) if ncell[i + 1] >= 6 and np.isfinite(p_gba[i + 1]) and p_gba[i + 1] > 2.5 else None
    f["atlo"] = atlo.get(str(f["id"])) if f["kind"] == "way" else None
    f["cells"] = int(ncell[i + 1])
# roof colours from Sentinel-2: the median colour over each roof, away from its edges (the image's 10 m pixels there
# mix in the street), moved onto the palette's range (colour transfer): pitched roofs that read red in the image become
# the reddest tiles, grey ones grey sheet, with the palette's own brightness and contrast
S2N = 0
if s2 is not None:
    lab_in = np.where(ndimage.distance_transform_edt(lab > 0) >= 3.0, lab, 0)
    nin = np.bincount(lab_in.ravel(), minlength=len(outlines) + 1)
    med = np.stack([group_pct(lab_in, s2[..., k].astype(np.float32), len(outlines), 0.5) for k in range(3)], 1)
    ok = (nin >= 30) & np.all(np.isfinite(med), 1)
    ok[0] = False
    src = med[ok]
    mu, sd = src.mean(0), src.std(0) + 1e-3
    tgt = {"pitched": np.array([hex_rgb(c) for c in ROOFS_PITCHED], float), "flat": np.array([hex_rgb(c) for c in ROOFS_FLAT], float)}
    tstats = {k: (v.mean(0), v.std(0) * 1.35 + 4) for k, v in tgt.items()}
    for i, f in enumerate(outlines):
        if ok[i + 1]:
            f["s2_roof"] = ((med[i + 1] - mu) / sd, float(np.clip((nin[i + 1] - 30) / 250, 0.25, 0.9)))
            S2N += 1
    del lab_in
del lab


def fuse(f):
    t, b = f["t"], f["type"] or "yes"
    H_tag, minh = parse_len(t.get("height")), parse_len(t.get("min_height")) or 0
    lv, rlv = parse_len(t.get("building:levels")), parse_len(t.get("roof:levels")) or 0
    minlv = parse_len(t.get("building:min_level"))
    year = parse_len(t.get("start_date"))
    rs = t.get("roof:shape")
    if rs not in SHAPE:
        rs = None
    meas = [x for x in (f.get("gba"), f.get("atlo")) if x and x > 2.5]
    m = sum(meas) / len(meas) if meas else None
    fh = 3.6 if not (year and year >= 1950) else 3.1
    if lv and lv > 0 and m:  # the storeys' height from the measurement, within what storeys can be
        fh = float(np.clip(m / max(lv + 0.4 * rlv, 1), 3.0, 4.4))
    lv_from_ground = False
    if not minh and minlv:
        # Simple 3D Buildings: building:levels counts from the ground, building:min_level is the levels skipped, so
        # levels=4 + min_level=3 is one storey on top of three missing ones
        minh = minlv * fh
        lv_from_ground = bool(lv and lv > minlv)
    if b == "roof" and not minh:
        minh = 3.0
    if H_tag and H_tag > minh:
        H, src = H_tag, "tag"
    elif lv and lv > 0:
        H, src = None, "levels"
    elif m:
        H, src = m * 1.05, "measured"
    else:
        H = TYPE_H.get(b) or (3.5 if f["area"] < 30 else 7 if f["area"] < 120 else 14 if f["area"] < 400 else 18)
        src = "default"
    if rs is None:
        ref = H or lv * 3.6
        flat = (b in FLAT_TYPES or f["part"] or ref > 32 or (year and year >= 1950)
                or (b in ("office", "hotel", "hospital", "university", "school") and f["area"] > 2500))
        rs = "flat" if flat else "hipped"
    sh = SHAPE[rs]
    rh = parse_len(t.get("roof:height"))
    if rh is None:
        rh = rlv * 2.8 if rlv else (0 if sh in (0, 5) else None)
    if src == "levels":
        E = lv * fh if lv_from_ground or (minh and lv * fh > minh + 2.5) else minh + lv * fh
        if rh is None:
            rh = min(6.0, 0.3 * E) if sh != 3 else None
        H = E + (rh or 0)
    else:
        if rh is None:
            rh = min(6.0, 0.28 * (H - minh)) if sh != 3 else None
        E = H - (rh or 0)
    f.update(H=float(H), E=float(max(E, minh + 0.5)), minh=float(minh), shape=sh, rshape=rs, src=src, rh_tagged=rh is not None)
    # colours and materials
    hsh = stable_hash(f["id"])
    wc = parse_colour(t.get("building:colour") or t.get("colour")) or \
        (hex_rgb(MATERIAL_WALL[t["building:material"]]) if MATERIAL_WALL.get(t.get("building:material")) else None) or \
        hex_rgb(WALLS[hsh % len(WALLS)])
    rc = parse_colour(t.get("roof:colour")) or \
        (hex_rgb(MATERIAL_ROOF[t["roof:material"]]) if t.get("roof:material") in MATERIAL_ROOF else None)
    if rc is None:
        rc = hex_rgb("#6c9a86") if sh == 3 else hex_rgb(ROOFS_FLAT[hsh % len(ROOFS_FLAT)]) if sh in (0, 5) \
            else hex_rgb(ROOFS_PITCHED[(hsh >> 8) % len(ROOFS_PITCHED)])
        if f.get("s2_roof") is not None and sh != 3:  # what the satellite sees, blended over the palette pick
            z, wgt = f["s2_roof"]
            m_, s_ = tstats["flat" if sh in (0, 5) else "pitched"]
            rc = tame(tuple(int(v) for v in np.clip((1 - wgt) * np.array(rc) + wgt * (m_ + z * s_), 30, 235)), roof=True)
    if t.get("building:material") == "glass" or (sh == 0 and H > 28 and b in ("office", "commercial", "hotel")):
        mat = GLASS
    elif b in RELIGIOUS or t.get("amenity") == "place_of_worship":
        mat = CLASSIC
    elif b in TENEMENTISH and H >= 9 and sh != 0:
        mat = TENEMENT
    else:
        mat = WALL
    if is_off(t, "bridge:support"):  # bridge piers and pylons: dressed stone, or steel
        mat = 6 if t.get("material") in ("metal", "steel") else 0
        if not t.get("building:colour"):
            wc = hex_rgb("#4f7d62") if mat == 6 else hex_rgb("#cbbf9f")
    mat = f.get("mat_override", mat)
    f.update(wall=pal(wc, mat), roof=pal(rc, ROOF))


for f in feats:
    fuse(f)
# Nothing floats unless it should: a building or part that starts above the ground stays up only if it is a bridge
# between buildings, a roof or canopy, or a way passes under it (an arcade, a gateway); everything else is grounded
# (OSM often maps a raised storey without the one under it). Parts resting on another part keep their start (below).
_FLOAT_TYPES = {"bridge", "roof", "carport", "canopy", "balcony", "gallery"}
_under_ways = [ln for oid, t, ln in osm.lines if (t.get("highway") or t.get("railway")) and not underground(t)
               and t.get("highway") not in ("corridor", "elevator", "steps")]
_under_tree = shapely.STRtree(_under_ways) if _under_ways else None
grounded = floating = 0
for f in feats:
    if f["minh"] <= 0:
        continue
    t = f["t"]
    ok = t.get("building") in _FLOAT_TYPES or t.get("building:part") in _FLOAT_TYPES
    if not ok and _under_tree is not None:
        inner = f["geom"].buffer(-0.8)
        ok = any(_under_ways[k].intersection(inner).length > 2.0 for k in _under_tree.query(inner))
    if ok:
        f["floats"] = True
        floating += 1
    else:
        f["floats"] = False
        if not f["part"]:
            f["minh"] = 0.0
        grounded += 1
note(f"raised buildings and parts: {floating} stay up (bridges, roofs, over ways), {grounded} grounded")
# an outline mapped through its parts takes no height of its own where a part stands
part_tree = shapely.STRtree([p["geom"] for p in parts]) if parts else None
for f in outlines:
    if part_tree is None:
        continue
    hit = [parts[i] for i in part_tree.query(f["geom"], predicate="intersects")
           if parts[i]["geom"].intersection(f["geom"]).area > 0.5 * parts[i]["area"]]
    if hit:
        f["has_parts"] = True
        if f["src"] in ("measured", "default"):  # the outline's own value is a guess: its lowest part is not
            low = min(hit, key=lambda p: p["H"])
            f.update(H=low["H"], E=low["E"], shape=low["shape"], src="parts")
# parts of a church (the Basilica, Matthias Church) are stone like their church, not a grid of office windows
out_tree = shapely.STRtree([f["geom"] for f in outlines]) if outlines else None
for p in parts:
    if out_tree is None or "mat_override" in p:
        continue
    host = [outlines[i] for i in out_tree.query(p["geom"].centroid, predicate="within")]
    if host and any((h["type"] in RELIGIOUS or h["t"].get("amenity") == "place_of_worship") for h in host):
        wcol = pal.entries[p["wall"]]
        p["wall"] = pal(wcol[:3], CLASSIC)
srcs = defaultdict(int)
for f in outlines:
    srcs[f["src"]] += 1
note("outline heights by source:", dict(srcs))
dis = [(f["id"], f["t"].get("name"), round(f["H"], 1), f.get("gba"), f.get("atlo")) for f in outlines
       if f["src"] in ("tag", "levels") and f.get("gba") and f["cells"] > 80 and abs(f["H"] - f["gba"]) > max(8, 0.4 * f["H"])]
report["height_disagreements"] = dis[:300]
note("tag/levels vs GBA disagree by > 40 % on", len(dis), "buildings (data/debug/report.json)")

# ---------------------------------------------------------------- building rasters (heights relative to the ground)
NO = len(outlines)
ob = raster([(f["geom"], i + 1) for i, f in sorted(enumerate(outlines), key=lambda x: x[1]["H"])], np.int32)
pb = np.zeros((D, W), np.int32)
pu = np.zeros((D, W), np.int32)
pdist = np.zeros((D, W), np.float32)
pR = np.zeros(len(parts) + 1, np.float32)
for k, f in sorted(enumerate(parts), key=lambda x: x[1]["H"]):
    rr, cc = cells_of(f["geom"])
    if not len(rr):
        continue
    pu[rr, cc] = pb[rr, cc]
    pb[rr, cc] = k + 1
    r0, c0 = rr.min() - 1, cc.min() - 1
    m = np.zeros((rr.max() - r0 + 2, cc.max() - c0 + 2), bool)
    m[rr - r0, cc - c0] = True
    dd = ndimage.distance_transform_edt(m)
    pdist[rr, cc] = dd[rr - r0, cc - c0] - 0.5
    pR[k + 1] = dd.max()
odist = (ndimage.distance_transform_edt(ob > 0) - 0.5).astype(np.float32)
oR = np.zeros(NO + 1, np.float32)
oR[1:] = ndimage.maximum(odist, ob, np.arange(1, NO + 1)) if NO else []
note("building rasters:", int((ob > 0).sum()), "outline cells,", int((pb > 0).sum()), "part cells")


def arr(fs, k, dtype=np.float32):
    return np.array([0] + [f[k] for f in fs], dtype)


def roof_rel(shape, E, H, dist, R):
    """height of the roof surface above the building's base (vectorised over cells)."""
    rh = np.maximum(H - E, 0)
    t = np.clip(dist / np.maximum(R, 1), 0, 1)
    z = np.where(shape == 1, E + np.minimum(dist * SLOPE, rh), H)
    z = np.where(shape == 2, E + np.minimum(dist * 1.8, rh), z)
    z = np.where(shape == 3, E + rh * np.sqrt(np.clip(1 - (1 - t) ** 2, 0, 1)), z)
    z = np.where(shape == 4, E + rh * t, z)
    z = np.where(shape == 5, (E + H) / 2, z)
    return z


# domes without a roof height rise as high as they are wide
for fs, R in ((outlines, oR), (parts, pR)):
    for i, f in enumerate(fs):
        if f["shape"] == 3 and not f["rh_tagged"]:
            rh = float(min(R[i + 1] * 0.9, 0.5 * f["H"]))
            f["E"] = f["H"] - rh

bot = np.zeros((D, W), np.float32)    # building starts (above ground): overhangs, canopies
low = np.zeros((D, W), np.float32)    # top of the wall below a part that starts higher up
eav = np.zeros((D, W), np.float32)    # where the wall becomes roof
top = np.zeros((D, W), np.float32)    # roof top
wl = np.zeros((D, W), np.uint16)      # lower wall colour
wc = np.zeros((D, W), np.uint16)      # wall colour
rc = np.zeros((D, W), np.uint16)      # roof colour
fid = np.zeros((D, W), np.int32)      # outline index + 1, or -(part index + 1)
m = ob > 0
i = ob[m]
oE, oH, osh, ominh = arr(outlines, "E"), arr(outlines, "H"), arr(outlines, "shape", np.int8), arr(outlines, "minh")
top[m] = roof_rel(osh[i], oE[i], oH[i], odist[m], oR[i])
eav[m] = np.minimum(oE[i], top[m] - 1)
bot[m] = ominh[i]
wc[m] = arr(outlines, "wall", np.uint16)[i]
rc[m] = arr(outlines, "roof", np.uint16)[i]
fid[m] = i
m = pb > 0
i = pb[m]
pE, pH, psh, pminh = arr(parts, "E"), arr(parts, "H"), arr(parts, "shape", np.int8), arr(parts, "minh")
pfloat = np.array([False] + [bool(p.get("floats")) for p in parts])
pw = arr(parts, "wall", np.uint16)
ptop = roof_rel(psh[i], pE[i], pH[i], pdist[m], pR[i])
# what stands under a part that starts above the ground: the part it sits on, or its outline's walls
under = pu[m]
o_under = ob[m]
lo_wall = np.where(under > 0, pw[under], np.where(o_under > 0, arr(outlines, "wall", np.uint16)[o_under], 0))
has_support = (under > 0) | (o_under > 0)
pm = pminh[i]
low[m] = np.where(has_support & (pm > 0), pm, 0)
bot[m] = np.where(~has_support & pfloat[i], pm, 0)  # unsupported and not a bridge or canopy: grounded
wl[m] = lo_wall
top[m] = ptop
eav[m] = np.minimum(pE[i], ptop - 1)
wc[m] = pw[i]
rc[m] = arr(parts, "roof", np.uint16)[i]
fid[m] = -i
bmask = (ob > 0) | (pb > 0)
held = bmask | mask_of(LMK.ground_cover)  # and the outlines landmarks replace but keep: no green, trees or open ground
shp = np.where(pb > 0, psh[pb], osh[ob])
# flat roofs over 150 m2 get a 1 m parapet in the wall's colour
flat_edge = bmask & (shp == 0) & (top > 8)
edge = flat_edge & (np.where(pb > 0, pdist, odist) < 1.0)
big = np.zeros(NO + 1, bool)
big[1:] = [f["area"] > 150 for f in outlines]
edge &= np.where(ob > 0, big[ob], True)
top[edge] += 1
eav[edge] = top[edge]
del shp
note("roofs done; tallest", float(top.max()), "m")

# ---------------------------------------------------------------- green the satellite sees where OSM maps nothing
# unmapped ground (the default pavement) that is green in Sentinel-2 -- Pest's courtyard gardens, lawns, verges -- gets
# grass, and trees where a patch is big enough; nothing within 3 m of a road or a building's wall
gpatch = np.zeros((D, W), bool)
if s2 is not None:
    r_, g_, b_ = (s2[..., k].astype(np.int16) for k in range(3))
    green = (g_ - np.maximum(r_, b_) > 6) & (g_ > r_ + 8)
    del r_, g_, b_
    unmapped = gcol1 == C["paving2"]
    gpatch = green & unmapped & ~held & (ndimage.distance_transform_edt(~road) > 3) & (ndimage.distance_transform_edt(~held) > 1.5)
    gpatch = ndimage.binary_opening(gpatch, iterations=2)
    lbl, nlab = ndimage.label(gpatch)
    sizes = np.bincount(lbl.ravel())
    gpatch &= sizes[lbl] >= 40
    del lbl, green, unmapped
    rr, cc = np.nonzero(gpatch)
    for dy in range(F):
        for dx in range(F):
            gcol[rr * F + dy, cc * F + dx] = C["garden"]
    grassy |= gpatch
    note(f"satellite: {S2N} roofs coloured from Sentinel-2; {int(gpatch.sum() / 1e4 * 10) / 10} ha of unmapped green ground")

# ---------------------------------------------------------------- trees
# where trees stand, and how big they are to the ground model (the canopy, below); species, shapes and final sizes come
# later (scripts/trees.py), after the ground, so that they don't move it
rng = np.random.default_rng(7)
trees = []  # x, y, height, crown radius, kind (0 broadleaf, 1 conifer, 2 shrub), (source, OSM tags, OSM id)
mapped = []
for oid, t, p in osm.nodes_with("natural", ("tree",)):
    h = parse_len(t.get("height")) or float(rng.uniform(9, 16))
    r = (parse_len(t.get("diameter_crown")) or 0) / 2 or float(rng.uniform(2.5, 4.2))
    kind = 1 if t.get("leaf_type") == "needleleaved" else 0
    mapped.append((p.x, p.y, min(h, 30), min(r, 8), kind, ("osm", t, oid)))
for oid, t, ln in osm.lines_with("natural", ("tree_row",)):
    for d in np.arange(4, ln.length, 8.0):
        p = ln.interpolate(d)
        mapped.append((p.x, p.y, float(rng.uniform(9, 15)), float(rng.uniform(2.5, 3.8)), 0, ("row", t, oid)))
mp = np.array([(x, y) for x, y, *_ in mapped]) if mapped else np.zeros((0, 2))
near_mapped = np.zeros((D, W), bool)
if len(mp):
    ix = np.clip(mp.astype(int), 0, [W - 1, D - 1])
    near_mapped[ix[:, 1], ix[:, 0]] = True
    near_mapped = ndimage.binary_dilation(near_mapped, iterations=5)
free = ~held & ~water & ~road & ~ndimage.binary_dilation(held, iterations=2)


def scatter(geoms, spacing, prob, hr, rr, kind, need, src):
    out = []
    for g in geoms:
        x0, y0, x1, y1 = g.bounds
        xs, ys = np.meshgrid(np.arange(x0, x1, spacing), np.arange(y0, y1, spacing))
        pts = np.stack([xs.ravel(), ys.ravel()], 1) + rng.uniform(-0.45, 0.45, (xs.size, 2)) * spacing
        pts = pts[(pts[:, 0] >= 0) & (pts[:, 0] < W) & (pts[:, 1] >= 0) & (pts[:, 1] < D)]
        pts = pts[rng.random(len(pts)) < prob]
        if not len(pts):
            continue
        pts = pts[shapely.contains_xy(g, pts[:, 0], pts[:, 1])]
        c, r = pts[:, 0].astype(int), pts[:, 1].astype(int)
        ok = need[r, c] & ~near_mapped[r, c]
        for x, y in pts[ok]:
            out.append((x, y, float(rng.uniform(*hr)), float(rng.uniform(*rr)), kind, (src, None, None)))
    return out


woods = [g for oid, k, t, g in osm.areas if (t.get("natural") == "wood" or t.get("landuse") == "forest") and not underground(t)]
parks = [g for oid, k, t, g in osm.areas if (t.get("leisure") in ("park", "garden") or t.get("landuse") in ("cemetery", "village_green"))
         and t.get("landuse") != "flowerbed"]  # formal beds (Kossuth tér) are low planting, not a wood
scrubs = [g for oid, k, t, g in osm.areas if t.get("natural") == "scrub"]
proc = scatter(woods, 6.5, 0.85, (13, 21), (2.8, 4.5), 0, free, "wood")
proc += scatter(parks, 11, 0.45, (10, 18), (2.8, 4.6), 0, free & grassy, "park")
proc += scatter(scrubs, 4.5, 0.55, (2.0, 3.5), (1.2, 2.0), 2, free, "scrub")
if gpatch.any():  # trees in the green courtyards: on a 9 m lattice, where the patch is at least 3 m deep
    deep = ndimage.distance_transform_edt(gpatch) >= 3
    ys, xs = np.mgrid[4:D:9, 4:W:9]
    ys, xs = ys.ravel(), xs.ravel()
    k = deep[ys, xs] & (rng.random(len(xs)) < 0.55) & ~near_mapped[ys, xs]
    for x, y in zip(xs[k], ys[k]):
        proc.append((float(x) + rng.uniform(-2, 2), float(y) + rng.uniform(-2, 2), float(rng.uniform(8, 14)), float(rng.uniform(2.4, 3.8)), 0,
                     ("yard", None, None)))
    del deep
# street trees OSM doesn't map: Sentinel-2 sees the crowns over avenues (the street photos beside the renders showed
# Andrássy út's outer rows and Bartók Béla út's planes missing). On the pavement 1-3 m off a carriageway, where the 10 m
# pixels over that pavement and over the road beside it are green, one tree every 9 m
n_street = 0
if s2 is not None:
    r_, g_, b_ = (s2[..., k].astype(np.int16) for k in range(3))
    green = (g_ - np.maximum(r_, b_) > 4) & (g_ > r_ + 6)
    del r_, g_, b_
    d_road = ndimage.distance_transform_edt(~road)
    walk = np.isin(gcol1, [C["paving"], C["paving2"]]) & ~held & (ndimage.distance_transform_edt(~held) > 2.5)
    cand = walk & (d_road >= 1) & (d_road <= 3) & green & ndimage.binary_dilation(green & road, iterations=4) & ~near_mapped
    del d_road, walk
    ys, xs = np.nonzero(cand)
    del cand
    order = rng.permutation(len(xs))
    taken = {}
    for i in order:
        x, y = int(xs[i]), int(ys[i])
        bx, by = x // 9, y // 9
        if any(abs(x - qx) < 9 and abs(y - qy) < 9 and (x - qx) ** 2 + (y - qy) ** 2 < 81
               for dx_ in (-1, 0, 1) for dy_ in (-1, 0, 1) for qx, qy in taken.get((bx + dx_, by + dy_), ())):
            continue
        taken.setdefault((bx, by), []).append((x, y))
        proc.append((x + 0.5, y + 0.5, float(rng.uniform(10, 16)), float(rng.uniform(2.6, 3.8)), 0, ("street", None, None)))
        n_street += 1
    del taken, green
note(f"street trees from Sentinel-2: {n_street}")
trees = [tr for tr in mapped if 0 <= tr[0] < W and 0 <= tr[1] < D] + proc
trees = [tr for tr in trees if not held[int(tr[1]), int(tr[0])] and not water[int(tr[1]), int(tr[0])]]
note("trees:", len(mapped), "mapped (incl. rows),", len(proc), "placed in woods / parks / scrub")
canopy = np.zeros((D, W), np.float32)
for x, y, h, r, *_ in trees:
    c, rr_ = int(x), int(y)
    R = int(r)
    canopy[max(rr_ - R, 0):rr_ + R + 1, max(c - R, 0):c + R + 1] = np.maximum(
        canopy[max(rr_ - R, 0):rr_ + R + 1, max(c - R, 0):c + R + 1], h)
canopy[mask_of(woods) & ~held] = np.maximum(canopy[mask_of(woods) & ~held], 15)

# ---------------------------------------------------------------- ground: bare earth
# FABDEM (the Copernicus surface model with buildings and forests removed by machine learning) is the base. It cuts too
# deep under big buildings on hills (18 m under Buda Castle's palace) and flattens summits, so where the ground is open,
# with no building or tree within ~20 m, the surface model sees the ground itself: FABDEM is corrected there by the
# difference, and the correction spread to nearby cells. The 30 m surface model blurs a tall roof well past its walls
# (the Puskas Arena's 51 m roof raised its plaza 25 m), so open means farther still from tall buildings: 12 m + 0.8 x
# their height. OSM's surveyed summits (natural=peak, ele=) are put back last.
# Without FABDEM: the surface model minus a fitted share of the buildings and the canopy, re-interpolated from open cells.
S = 8
Ds, Ws = D // S, W // S


def bm(a):
    return a[:Ds * S, :Ws * S].reshape(Ds, S, Ws, S).mean((1, 3))


dsm8 = bm(dsm)
# bridges over land: the surface models see their decks as the ground (FABDEM removes buildings and trees, not bridges),
# which lifted the streets under the bridgeheads to the deck. Their footprints are left out and filled from around.
_brg = [ln.buffer(7, cap_style="flat") for oid, t, ln in osm.lines if t.get("bridge") not in (None, "no")
        and (t.get("highway") or t.get("railway"))] + \
       [gm_.buffer(3) for oid, k, t, gm_ in osm.areas if t.get("man_made") == "bridge"]
br8 = ndimage.binary_dilation(bm(mask_of(_brg, all_touched=True).astype(np.float32)) > 0.04) if _brg else None
del _brg
# buildings a landmark redraws but asks to keep here (LMK.ground_keep) still count, at the height OSM gave them: left
# out, the 30 m surface model's blur of their roofs reads as open ground and lifts the streets round them
kept = raster([(g_, int(h_)) for g_, h_ in LMK.ground_keep], np.uint8)
cov = gauss(bm((held | (kept > 0)).astype(np.float32)), 1.5)
kept8 = kept[:Ds * S, :Ws * S].reshape(Ds, S, Ws, S).max((1, 3))
del kept
import landmarks_citadella  # its buildings are dropped for the hand-built ones, but its walls stand: not open ground
if landmarks_citadella.built(osm):
    cov = np.maximum(cov, gauss(bm(mask_of(landmarks_citadella.built(osm)).astype(np.float32)), 1.5))
tcv = gauss(bm((canopy > 0).astype(np.float32)), 1.5)
riv8 = bm(river.astype(np.float32))
land = riv8 < 0.05
if dtm is not None:
    fab8 = bm(dtm)
    top8 = np.maximum(top[:Ds * S, :Ws * S].reshape(Ds, S, Ws, S).max((1, 3)), kept8)
    bleed = np.zeros_like(land)
    for h in (15, 25, 35, 50, 70):
        if (top8 >= h).any():
            bleed |= ndimage.distance_transform_edt(top8 < h) * S < 12 + 0.8 * h
    wo = ((cov < 0.06) & (tcv < 0.10) & land & ~bleed).astype(np.float32)
    if br8 is not None:
        wo[br8] = 0
        ok = ~br8
        fill = fab8.copy()
        for sg in (1.0, 2.0, 4.0):  # FABDEM under a bridge: from the ground beside it, widening until it is covered
            num, den = gauss(np.where(ok, fab8, 0), sg), gauss(ok.astype(np.float32), sg)
            put = ~ok & (den > 0.08)
            fill[put] = num[put] / den[put]
            ok = ok | put
        fab8 = fill
        del fill, num, den, ok
    r = np.clip(dsm8 - fab8, -6, 25)
    wA, wB = gauss(wo, 2), gauss(wo, 6)
    rA = gauss(r * wo, 2) / np.maximum(wA, 1e-6)
    rB = gauss(r * wo, 6) / np.maximum(wB, 1e-6)
    a = np.clip(wA / 0.3, 0, 1)
    corr = a * rA + (1 - a) * rB * np.clip(wB / 0.1, 0, 1)
    G8 = gauss(fab8 + corr, 0.8)
    # FABDEM's metre-scale noise on flat ground turns into rings of 0.5 m terraces across a big plaza: where the relief
    # is gentle (local spread under ~1 m) smooth over ~30 m; hills (Castle Hill, Gellért Hill) keep their shape
    sm = gauss(G8, 4)
    rel = np.sqrt(np.maximum(gauss(G8 ** 2, 3) - gauss(G8, 3) ** 2, 0))
    wf = np.clip((2.5 - rel) / 1.5, 0, 1)
    G8 = wf * sm + (1 - wf) * G8
    # Pest is a plain: OSM's surveyed points read 108-111 m from the Danube to the Városliget, while FABDEM wanders
    # 104-120 m under the dense blocks. So the Pest bank (and the island) is smoothed at ~160 m, within that bank only:
    # neither the river nor Buda's hills bleed into it. The surveyed points then set its level (below).
    from osm import to_grid as _tgp
    lab, _ = ndimage.label(riv8 < 0.5)
    xb, yb = _tgp(19.0379, 47.4993)  # Dísz tér: Buda
    buda = lab[min(max(int(yb / S), 0), Ds - 1), min(max(int(xb / S), 0), Ws - 1)]
    flat = (lab > 0) & (lab != buda)
    wfl = flat.astype(np.float32)
    G8 = np.where(flat, gauss(G8 * wfl, 20) / np.maximum(gauss(wfl, 20), 1e-3), G8)
    pest_km2 = int(flat.sum() * S * S / 1e6)
    pest8 = flat
    del lab, wfl
    how = f"FABDEM, corrected on {int(wo.sum() * S * S / 1e4)} ha of open ground (median {float(np.median(r[wo > 0])):+.1f} m), " \
          f"smoothed on {int((wf > 0.5).sum() * S * S / 1e4)} ha of flat ground; Pest's bank ({pest_km2} km2) at 160 m"
    del fab8, top8, bleed, wo, r, wA, wB, rA, rB, corr, sm, rel, wf, br8
else:
    pest8 = None
    bex = gauss(bm(np.where(bmask, top, 0)), 1.5)
    tex = gauss(bm(canopy), 1.5)
    w_open = ((cov < 0.08) & (tcv < 0.08) & land).astype(np.float32)
    g_open = gauss(dsm8 * w_open, 12) / np.maximum(gauss(w_open, 12), 1e-4)
    A = np.stack([bex[land], tex[land]], 1)
    kb, kt = np.linalg.lstsq(A, (dsm8 - g_open)[land], rcond=None)[0]
    kb, kt = float(np.clip(kb, 0.3, 1.1)), float(np.clip(kt, 0.2, 1.0))
    g0 = dsm8 - kb * bex - kt * tex
    w = np.exp(-5 * cov) * np.exp(-2.5 * tcv) * land
    nA = gauss(g0 * w, 3) / np.maximum(gauss(w, 3), 1e-6)
    nB = gauss(g0 * w, 10) / np.maximum(gauss(w, 10), 1e-6)
    wA = gauss(w, 3)
    G8 = gauss(w * g0 + (1 - w) * np.where(wA > 0.25, nA, nB), 1.2)
    how = f"surface model less {kb:.2f} of the buildings and {kt:.2f} of the canopy"
    del bex, tex, g0, w, nA, nB
G = np.empty((D, W), np.float32)
for j0 in range(0, D, 512):  # in bands: a full-size coordinate grid would take 200 MB
    jj, ii = np.mgrid[j0:min(j0 + 512, D), 0:W].astype(np.float32)
    G[j0:j0 + 512] = ndimage.map_coordinates(G8, [(jj + 0.5) / S - 0.5, (ii + 0.5) / S - 0.5], order=1, mode="nearest")
del jj, ii, dsm8, cov, tcv, G8
peaks = 0
for oid, t, p in osm.nodes:
    e = parse_len(t.get("ele"))
    if t.get("natural") not in ("peak", "hill") or e is None or not (0 <= p.x < W and 0 <= p.y < D):
        continue
    dz = e - float(G[int(p.y), int(p.x)])
    if 0 < dz < 30:  # a summit the 30 m models smoothed away: raise it, fading over ~40 m
        r0, r1, c0, c1 = max(int(p.y) - 120, 0), min(int(p.y) + 121, D), max(int(p.x) - 120, 0), min(int(p.x) + 121, W)
        yy, xx = np.mgrid[r0:r1, c0:c1]
        G[r0:r1, c0:c1] += dz * np.exp(-((xx + 0.5 - p.x) ** 2 + (yy + 0.5 - p.y) ** 2) / (2 * 40.0 ** 2))
        peaks += 1
# surveyed spot heights: OSM's RTK control points (triangulation_point / survey_point, ~5 cm) pull the ground to
# themselves, fading over ~150 m. FABDEM reads parts of Pest's dense blocks up to 11 m high (Szent István tér in front of
# the Basilica: 120 m against 109 m surveyed). Points on or next to a bridge are left out: they sit on the deck.
# A point is left out only when it is on a deck (inside a bridge's outline, or on a bridge way's carriageway): the
# squares at the bridgeheads are exactly where the ground matters. Many points mark the top of something on the
# ground (a railing, a cabinet, a plinth): their description says what, and that height comes off.
bridge_geoms = [ln.buffer(4.0) for oid, t, ln in osm.lines if t.get("bridge") not in (None, "no")] + \
               [gm_ for oid, k, t, gm_ in osm.areas if t.get("man_made") == "bridge"]
bridge_tree = shapely.STRtree(bridge_geoms) if bridge_geoms else None
RTK_ABOVE = [("felülvilágító", None), ("korlát", 1.0), ("váltóállító", 0.9), ("közműszekrény", 1.0), ("szekrény", 1.25),
             ("talapzat", 0.35), ("lábazat", 0.3), ("szökőkút", 0.45), ("ágyás", 0.4), ("teteje", 0.15)]
cps = []
for oid, t, p in osm.nodes:
    e = parse_len(t.get("ele"))
    if e is None or not (t.get("triangulation_point") == "yes" or t.get("man_made") == "survey_point" or t.get("source") == "RTK"):
        continue
    if not (0 <= p.x < W and 0 <= p.y < D) or (bridge_tree is not None and len(bridge_tree.query(p, predicate="intersects"))):
        continue
    desc = (t.get("description") or "").lower()
    off = next((o_ for k_, o_ in RTK_ABOVE if k_ in desc), 0.0)
    if off is None:  # the top of a skylight or the like: how high it stands is unknown
        continue
    e -= off
    r = e - float(G[int(p.y), int(p.x)])
    if abs(r) < 20:
        cps.append((p.x, p.y, r, e, None))
# Squares at bridgeheads with no surveyed point on them, at the level of the street the bridge lands on (estimates:
# the Pest embankment reads 108.4-109.3 m at Kálvin tér, Március 15. tér and Boráros tér; Döbrentei tér 108.3 m)
SQUARES = [((19.05707, 47.48683), 108.6, "Fővám tér", 60.0), ((19.05305, 47.48456), 108.3, "Gellért tér", 60.0)]
from osm import to_grid as _tgq
for (lon_, lat_), e_, nm_, sg_ in SQUARES:
    x_, y_ = _tgq(lon_, lat_)
    if 0 <= x_ < W and 0 <= y_ < D:
        cps.append((x_, y_, e_ - float(G[int(y_), int(x_)]), e_, sg_))
if cps:
    yy8, xx8 = (np.mgrid[0:Ds, 0:Ws] + 0.5) * S

    def spread(pts, sig):  # Shepard-style: full correction next to a point, fading to none ~2 sigma away
        num, den = np.zeros((Ds, Ws), np.float32), np.zeros((Ds, Ws), np.float32)
        for x_, y_, r_, s_ in pts:
            sg = min(sig, s_) if s_ else sig
            k = np.exp(-((xx8 - x_) ** 2 + (yy8 - y_) ** 2) / (2 * sg ** 2)).astype(np.float32)
            num += k * r_
            den += k
        return num / np.maximum(den, 1.0)

    def add8(c8):
        for j0 in range(0, D, 512):
            jj, ii = np.mgrid[j0:min(j0 + 512, D), 0:W].astype(np.float32)
            G[j0:j0 + 512] += ndimage.map_coordinates(c8, [(jj + 0.5) / S - 0.5, (ii + 0.5) / S - 0.5], order=1, mode="nearest")

    def resid():
        return [(x_, y_, e_ - float(G[int(y_), int(x_)]), s_) for x_, y_, _, e_, s_ in cps]
    rs = np.array([c[2] for c in cps])
    if pest8 is not None:  # first the Pest bank's level, from its own points, over ~600 m and within the bank
        pp = [c for c in resid() if pest8[min(int(c[1] / S), Ds - 1), min(int(c[0] / S), Ws - 1)]]
        if pp:
            add8(spread(pp, 600.0) * pest8)
        # Pest's upper embankment is as high as the streets behind it, right to its wall over the lower quay: the
        # 30 m models dip towards the river (they see the quay below), which sank Fővám tér and the bridgeheads
        d8 = ndimage.distance_transform_edt(ndimage.zoom(river.astype(np.uint8), (Ds / D, Ws / W), order=0) == 0) * S
        Gd = ndimage.zoom(G, (Ds / D, Ws / W), order=1)
        inl = (pest8 & (d8 >= 150) & (d8 <= 450)).astype(np.float32)
        Gin = gauss(Gd * inl, 25) / np.maximum(gauss(inl, 25), 1e-3)
        lift8 = np.where(pest8 & (d8 < 150) & (d8 > 0), np.maximum(Gin - Gd, 0), 0).astype(np.float32)
        lift8 = gauss(lift8, 1.5)
        add8(lift8)
        note(f"ground: Pest's riverside raised to the streets' level behind it by up to {float(lift8.max()):.1f} m")
        del d8, Gd, inl, Gin, lift8
    add8(spread(resid(), 150.0))  # then each point's neighbourhood
    ra = np.array([c[2] for c in resid()])
    note(f"ground: {len(cps)} surveyed points; off by median {np.median(np.abs(rs)):.1f} m (max {np.abs(rs).max():.1f}) "
         f"before them, {np.median(np.abs(ra)):.1f} m (max {np.abs(ra).max():.1f}) after")
    del yy8, xx8
landmarks_citadella.ground(G, wlev, osm, cells_of, note)  # the Citadella's park, square and promenades on the hilltop
# the Gellért Hotel stands at the foot of the hill, its front garden level with Szent Gellért tér: the 30 m models
# carry the hill's slope down to the square, which stood the hotel 10 m above its own entrance
gel = next((g_ for oid, k, t, g_ in osm.areas if oid == 46769968), None)
if gel is not None:
    import landmarks_more
    gel = landmarks_more.largest(gel)
    fg_ = landmarks_more.front_frame(gel, 0.0, (math.cos(THETA), math.sin(THETA)))
    us_, vm_ = landmarks_more.front_profile(gel, fg_)
    ok_ = np.isfinite(vm_)
    v_m = float(np.nanpercentile(vm_[ok_], 40))
    uf_ = us_[ok_ & (vm_ > v_m - 3)]
    court = landmarks_more.rect_poly(fg_, float(uf_.min()) - 4, float(uf_.max()) + 2, v_m - 3, v_m + 24)
    rr, cc = cells_of(court.buffer(14))
    fade = np.clip(1 - shapely.distance(court, shapely.points(cc + 0.5, rr + 0.5)) / 14, 0, 1)
    lev = 107.6  # m above sea level, like G here
    G[rr, cc] -= np.clip(G[rr, cc] - lev, 0, None) * fade
    note(f"ground: the Gellért's front garden down to Szent Gellért tér's level ({lev:.1f} m)")
# the palace's Lions' Court: shut in by the wings, the 30 m models see their roofs in it and lifted it to the eaves;
# it lies level with the Hunyadi court, through the Lions' Gate
courts_ = {t.get("name"): g_ for oid, k, t, g_ in osm.areas if t.get("name") in ("Oroszlános udvar", "Hunyadi-udvar")}
if len(courts_) == 2:
    rr, cc = cells_of(courts_["Hunyadi-udvar"])
    lev = float(np.median(G[rr, cc]))
    rr, cc = cells_of(courts_["Oroszlános udvar"].buffer(2))
    G[rr, cc] = lev
    note(f"ground: the Lions' Court at the Hunyadi court's level ({lev:.1f} m)")
d_riv = ndimage.distance_transform_edt(~river).astype(np.float32)
near_river = d_riv < 80
G = np.where(near_river & ~river, np.maximum(G, WL + 2.5), G)  # quays stand above the water

# the embankment's two levels. In 2023 Budapest named its lower quays (alsó rakpart) after rescuers of the Holocaust;
# the upper quays kept their names. The strip from the river out to a lower quay road (and the tram beside it) lies
# ~3.5 m above the mean water, a retaining wall's height under the streets behind it.
LOWER_QUAYS = {"Jane Haining rakpart", "Id. Antall József rakpart", "Carl Lutz rakpart", "Slachta Margit rakpart",
               "Friedrich Born rakpart", "Valdemar és Nina Langlet rakpart", "Angelo Rotta rakpart", "Sztehlo Gábor rakpart",
               "Henryk Sławik rakpart", "Raoul Wallenberg rakpart", "Salkaházi Sára rakpart"}
LQ = WL + 3.5


def near_water(ln, lim):
    xs, ys = np.asarray(ln.coords).T
    return bool((d_riv[np.clip(ys.astype(int), 0, D - 1), np.clip(xs.astype(int), 0, W - 1)] < lim).any())


lq_ways = [(t, ln) for oid, t, ln in osm.lines if t.get("name") in LOWER_QUAYS and t.get("highway") in ROADS
           and not t["highway"].endswith("_link") and not underground(t) and not on_bridge(t) and near_water(ln, 60)]
seed_geoms = [ln.buffer(width_of(t, t["highway"]) / 2 + 2.0) for t, ln in lq_ways]
# the hand-built bridges' bridgeheads stay at the street's level: the lower quay's road passes under them
hb_geoms = [gm_ for oid, k, t, gm_ in osm.areas if t.get("man_made") == "bridge" and t.get("name") in LMK.bridges]
hb_mask = mask_of(hb_geoms) if hb_geoms else np.zeros((D, W), bool)
if lq_ways:
    lq_union = shapely.union_all([ln for t, ln in lq_ways])
    # the tram beside a lower quay is down there with it (Pest's line 2); not the trams crossing a bridgehead square to
    # the upper streets, nor Buda's, which run on the upper quay (Szent Gellért tér)
    def on_pest(ln):
        if pest8 is None:
            return True
        p_ = ln.interpolate(0.5, normalized=True)
        return bool(pest8[min(max(int(p_.y / S), 0), Ds - 1), min(max(int(p_.x / S), 0), Ws - 1)])
    seed_geoms += [ln.buffer(3.5) for oid, t, ln in osm.lines if t.get("railway") == "tram" and not underground(t)
                   and not on_bridge(t) and near_water(ln, 60) and ln.distance(lq_union) < 14 and on_pest(ln)
                   and float(np.median(d_riv[np.clip(np.asarray(ln.coords)[:, 1].astype(int), 0, D - 1),
                                             np.clip(np.asarray(ln.coords)[:, 0].astype(int), 0, W - 1)])) < 45]
    seed = mask_of(seed_geoms)
    # the strip from the river out to the far side of the quay's road and tram, following them closely: the squares
    # behind the retaining wall (Fővám tér) stay on the upper level
    lmax = ndimage.maximum_filter(np.where(seed, d_riv, 0), size=13)
    quay_low = ~river & (d_riv <= lmax + 0.5) & (ndimage.distance_transform_edt(~seed) <= 25) & ~np.isfinite(wlev) \
        & (~hb_mask | seed)  # under a bridgehead only the quay's own road and tram stay low
    # the streets a hand-built bridge lands on stay up to where they reach the upper level: the Chain Bridge's Pest end
    # runs on over the quay's tunnels to Széchenyi István tér, and the low strip cut a trench between the two
    if hb_geoms:
        hb_union = shapely.union_all(hb_geoms)
        land = [ln.buffer(width_of(t, t["highway"]) / 2 + 2.5) for oid, t, ln in osm.lines
                if t.get("highway") in ROADS and not underground(t) and not on_bridge(t) and t.get("name") not in LOWER_QUAYS
                and ln.length < 60 and ln.distance(hb_union) < 3.0]
        if land:
            quay_low &= ~mask_of(land)
        note(f"quays: {len(land)} streets at the hand-built bridges' ends kept on the upper level")
    G = np.where(quay_low, LQ, G)
    del seed, lmax
    # roads from the lower quays up to the streets: a ramp, over at most 110 m from the quay
    ramps = 0
    for oid, t, ln in osm.lines:
        kind = t.get("highway")
        if not (kind in ROADS or (kind or "").endswith("_link")) or underground(t) or on_bridge(t) or ln.length < 10:
            continue
        (xa, ya), (xb, yb) = ln.coords[0], ln.coords[-1]
        if not (0 <= xa < W and 0 <= ya < D and 0 <= xb < W and 0 <= yb < D):
            continue
        ia, ib = quay_low[int(ya), int(xa)], quay_low[int(yb), int(xb)]
        if ia == ib:
            continue
        if ib:
            ln = LineString(ln.coords[::-1])
        L_ = min(ln.length, 110.0)
        pe = ln.interpolate(L_)
        zt = float(G[int(pe.y), int(pe.x)])
        rr, cc = cells_of(ln.buffer(width_of(t, kind) / 2 + 1.0, cap_style="flat"))
        if not len(rr):
            continue
        sc = shapely.line_locate_point(ln, shapely.points(cc + 0.5, rr + 0.5))
        k = (sc <= L_) & ~quay_low[rr, cc]
        G[rr[k], cc[k]] = LQ + (zt - LQ) * np.clip(sc[k] / L_, 0, 1)
        ramps += 1
    note(f"quays: {int(quay_low.sum() / 1e4)} ha of lower quay at {LQ:.1f} m along {len(lq_ways)} ways; {ramps} ramps up")
else:
    quay_low = np.zeros((D, W), bool)

TUNNEL_KINDS = {"cycleway": (3.2, 3.0), "tram": (3.6, 5.2)}
tunnels = []
for oid, t, ln in osm.lines:
    kind = t.get("highway") or ("tram" if t.get("railway") == "tram" else None)
    if not (t.get("tunnel") == "yes" or t.get("covered") == "yes") or kind is None or kind == "service":
        continue
    if kind not in ROADS and kind not in TUNNEL_KINDS or not near_water(ln, 160) or ln.length > 600:
        continue
    wdt, hgt = TUNNEL_KINDS.get(kind, (width_of(t, kind) + 1.0, 5.0))
    ends = [Point(ln.coords[0]), Point(ln.coords[-1])]
    if not all(4 <= p_.x < W - 5 and 4 <= p_.y < D - 5 for p_ in ends):
        continue
    za, zb = [float(G[max(int(p_.y) - 4, 0):int(p_.y) + 5, max(int(p_.x) - 4, 0):int(p_.x) + 5].min()) for p_ in ends]
    # a passage through a bridgehead from the lower quay: on the quay's level, its mouths cut down to it, and carved
    # a few metres past its ends (through the abutment's walls)
    cut = ln
    if quay_low.any() and any(quay_low[max(int(p_.y) - 25, 0):int(p_.y) + 26, max(int(p_.x) - 25, 0):int(p_.x) + 26].any()
                              for p_ in ends):
        za = zb = LQ
        tips = []
        for p_, q_ in ((ln.coords[0], ln.coords[1]), (ln.coords[-1], ln.coords[-2])):
            d_ = np.subtract(p_, q_)
            d_ = d_ / max(np.hypot(*d_), 1e-6)
            mouth = LineString([p_, tuple(np.add(p_, d_ * 10.0))]).buffer(wdt / 2 + 0.5, cap_style="flat")
            rr, cc = cells_of(mouth)
            G[rr, cc] = np.minimum(G[rr, cc], LQ)
            tips.append(tuple(np.add(p_, d_ * 4.0)))
        cut = LineString([tips[0]] + list(ln.coords) + [tips[1]])
    surf = C["trambed"] if kind == "tram" else C["asphalt"] if kind in ROADS else C["paving"]
    tunnels.append(dict(line=ln, poly=cut.buffer(wdt / 2, cap_style="flat"), za=za, zb=zb, h=hgt, surf=surf, tram=kind == "tram",
                        name=t.get("name") or kind))
tunnel_tree = shapely.STRtree([tn["poly"] for tn in tunnels]) if tunnels else None
note(f"tunnels to carve: {len(tunnels)} ({', '.join(sorted(set(tn['name'] for tn in tunnels)))})")

# roads under the hand-built bridges' approaches: dug down for headroom (4.8 m, 3 m for paths), ramps of at most 7 %.
# A way that crosses the deck (more than ~40 degrees off its axis) and is not on a bridge itself goes under it; the
# streets the deck runs on into at its ends are left alone, and so are the ways crossing a bridgehead that lies level
# with its square (past `grade`: Margaret Bridge's Pest end), which a trench would only run into its embankment.
decks = landmarks.bridge_decks(dict(osm=osm, WLr=WL, river=river, W=W, D=D,
                                    ground_m=lambda x, y: float(G[int(np.clip(y, 0, D - 1)), int(np.clip(x, 0, W - 1))])))
dug = undug = 0
for oid, t, ln in osm.lines:
    kind = t.get("highway") or ("tram" if t.get("railway") == "tram" else None)
    if kind is None or underground(t) or on_bridge(t) or kind in ("steps", "proposed", "construction") or ln.length < 3:
        continue
    ss = np.arange(0, ln.length + 0.5, 1.0)
    pts = shapely.line_interpolate_point(ln, ss)
    xs, ys = shapely.get_x(pts), shapely.get_y(pts)
    if not ((xs >= 0) & (xs < W) & (ys >= 0) & (ys < D)).all():
        continue
    xi, yi = xs.astype(int), ys.astype(int)
    gz = G[yi, xi].astype(np.float64)
    need = np.zeros(len(ss))
    zbot = np.full(len(ss), np.inf)
    head = 3.0 if kind in ("footway", "cycleway", "path", "pedestrian", "bridleway") else \
        3.8 if t.get("name") in LOWER_QUAYS else 4.8
    for dk in decks:
        u, v = dk["fr"].uv(xs, ys)
        inb = (u >= dk["u0"] + 4.0) & (u <= dk.get("grade", dk["u1"]) - 4.0) & (np.abs(v) <= dk["hw"] + 1.5)
        if not inb.any():
            continue
        du, dv = np.gradient(u), np.gradient(v)
        across = np.abs(du) < 0.75 * np.hypot(du, dv)
        zd = np.asarray(dk["zf"](u), float)
        over = inb & across & ~river[yi, xi]
        need = np.maximum(need, np.where(over, gz - (zd - dk["under"] - head), 0))
        zbot = np.where(over, np.minimum(zbot, zd - dk["under"]), zbot)
    if need.max() <= 0.2:
        continue
    target = np.maximum(gz - need, max(WL + 1.2, float(gz.min()) - 3.0))  # not far under the way's own lowest point
    under_ = np.isfinite(zbot)
    if (zbot[under_] - target[under_] < 2.5).any():
        undug += 1  # it can't get 2.5 m under the deck: a trench would only end against the bridgehead
        continue
    prof = np.min(target[None, :] + 0.07 * np.abs(ss[:, None] - ss[None, :]), axis=1)
    prof = np.minimum(prof, gz)
    rr, cc = cells_of(ln.buffer(width_of(t, kind) / 2 + 1.2 if kind in ROADS else 2.5, cap_style="flat"))
    if not len(rr):
        continue
    sc = shapely.line_locate_point(ln, shapely.points(cc + 0.5, rr + 0.5))
    G[rr, cc] = np.minimum(G[rr, cc], prof[np.clip(np.round(sc).astype(int), 0, len(prof) - 1)])
    dug += 1
note(f"under the hand-built bridges: {dug} ways dug down for headroom, {undug} left level (no room under the deck) "
     f"({len(decks)} decks)")


def hand_deck_z(x, y):
    """the top of a hand-built deck at a point (absolute metres), or None."""
    for dk in decks:
        u, v = dk["fr"].uv(x, y)
        if dk["u0"] - 4 <= u <= dk["u1"] + 4 and abs(v) <= dk["hw"] + 3:
            return float(dk["zf"](min(max(u, dk["u0"]), dk["u1"])))
    return None
G = np.where(np.isfinite(wlev), wlev, G)
pond_bank = ndimage.binary_dilation(np.isfinite(wlev) & ~river, iterations=2) & ~np.isfinite(wlev)
lv_near = ndimage.maximum_filter(np.nan_to_num(wlev, nan=0), 5)
G = np.where(pond_bank, np.maximum(G, lv_near + 0.6), G)
BASE = math.floor(min(float(G.min()), WL) - 4)
g = np.round(G - BASE).astype(np.int16)  # z of the first free voxel above the ground
for name, (lon, lat) in {"Deák tér": (19.0549, 47.4975), "Kossuth tér": (19.0450, 47.5073), "Heroes' Square": (19.0778, 47.5150),
                         "Szentháromság tér": (19.0343, 47.5017), "Dísz tér": (19.0379, 47.4993), "Szent György tér": (19.0392, 47.4977),
                         "Gellért Hill top": (19.0466, 47.4869), "Blaha": (19.0700, 47.4960), "Széll Kálmán tér": (19.0240, 47.5070),
                         "Puskás Aréna plaza": (19.0945, 47.5025), "Városliget pond": (19.0815, 47.5155),
                         "Szent István tér": (19.0526, 47.5007)}.items():
    from osm import to_grid
    x, y = to_grid(lon, lat)
    if 0 <= x < W and 0 <= y < D:
        note(f"  ground at {name}: {float(G[int(y), int(x)]):.1f} m (surface model {float(dsm[int(y), int(x)]):.1f})")
note(f"ground: {how}; {peaks} summits raised; base {BASE} m, ground {float(G.min()):.1f}-{float(G.max()):.1f} m")
for oid, kind, t, geom in osm.areas:  # the squares on Castle Hill and in Pest: median ground (surface model)
    if t.get("name") in ("Szent György tér", "Dísz tér", "Szentháromság tér", "Bécsi kapu tér", "Oroszlános udvar", "Kossuth Lajos tér",
                         "Széll Kálmán tér", "Hősök tere", "Erzsébet tér") and ("highway" in t or "place" in t or "leisure" in t):
        rr, cc = cells_of(geom)
        if len(rr) > 50:
            note(f"  ground on {t['name']}: {float(np.median(G[rr, cc])):.1f} m (surface model {float(np.median(dsm[rr, cc])):.1f})")
del canopy

# tunnels by the river: the lower quay and the trams under the bridgeheads, covered cycle paths, the Castle Hill
# tunnel; carved through the ground (and any landmark) in build(), the floor running between the ground at the portals

# subsurface: granite quay walls along the Danube, riverbed under water, soil elsewhere
sub = np.full((D, W), C["soil"], np.uint16)
sub[near_river & ~river] = C["stone"]
sub[water] = C["riverbed"]
paved_cut = ~grassy & ~water
sub[paved_cut & (ndimage.minimum_filter(g, 3) <= g - 2)] = C["stone"]

# ---------------------------------------------------------------- building z (absolute)
# a building stands on the median ground under it: its roof is level, its walls reach down to the ground on a slope
base_o = np.nan_to_num(group_pct(ob, g.astype(np.float32), len(outlines), 0.5))
base_p = np.nan_to_num(group_pct(pb, g.astype(np.float32), len(parts), 0.5))
fbase = np.where(fid > 0, base_o[np.maximum(fid, 0)], base_p[np.maximum(-fid, 0)]).astype(np.float32)
nz = fid != 0
bz1 = np.where(bmask, np.maximum(np.round(fbase + top), g + 2), 0).astype(np.int16)
bze = np.where(bmask, np.clip(np.round(fbase + eav), g, bz1 - 1), 0).astype(np.int16)
bz0 = np.where(bmask, np.clip(np.round(np.where(bot > 0, fbase + bot, g)), g, np.maximum(bze - 1, g)), 0).astype(np.int16)
# a part's lower wall (another part's colour under it) only where it has one: elsewhere the wall runs down to the
# bottom, the ground on a slope's lower side (it once stopped at the median ground and left the downhill side hanging)
bzl = np.where(bmask & (low > 0), np.clip(np.round(fbase + low), g, bze), bz0).astype(np.int16)
bzl = np.maximum(bzl, bz0)
del fbase, top, eav, low, bot, nz, fid
note("building columns done")

# ---------------------------------------------------------------- bridges
dtop = np.zeros((D, W), np.int16)   # first free voxel above the deck, metres (0: no deck)
dzf = np.zeros((D, W), np.float32)  # the same, unrounded
dsurf = np.zeros((D, W), np.uint16)
bridges = [(oid, t, geom) for oid, kind, t, geom in osm.areas if t.get("man_made") == "bridge"]
hand_bridges = [geom for oid, t, geom in bridges if t.get("name") in LMK.bridges]  # built in landmarks.py
bridges = [b for b in bridges if b[1].get("name") not in LMK.bridges]
deck_polys = []
GROUND = BASE + g.astype(np.float32)


def ground_near(x, y, r=4):
    c0, r0 = int(np.clip(x, 0, W - 1)), int(np.clip(y, 0, D - 1))
    win = GROUND[max(r0 - r, 0):r0 + r + 1, max(c0 - r, 0):c0 + r + 1]
    wm = ~water[max(r0 - r, 0):r0 + r + 1, max(c0 - r, 0):c0 + r + 1]
    return float(np.median(win[wm])) if wm.any() else None


def axis_of(rr, cc):
    pts = np.stack([cc + 0.5, rr + 0.5], 1)
    c = pts.mean(0)
    u = np.linalg.svd(pts - c, full_matrices=False)[2][0]
    s = (pts - c) @ u
    return c, u, s


def deck_profile(rr, cc, path_s, s0, s1, za, zb, over_river):
    t = np.clip((path_s - s0) / max(s1 - s0, 1), 0, 1)
    lin = za + (zb - za) * t
    if over_river:
        crest = max(WL + 12.0, max(za, zb) + 1.5)
        z = lin + (crest - (za + zb) / 2) * 4 * t * (1 - t)
    else:
        under = GROUND[rr, cc]
        z = np.maximum(lin, np.minimum(under + 5.5, lin + 7) * np.minimum(1, 8 * t * (1 - t)) + lin * (1 - np.minimum(1, 8 * t * (1 - t))))
    return z


bridge_info = []
for oid, t, geom in bridges:
    rr, cc = cells_of(geom, all_touched=True)
    if len(rr) < 20:
        continue
    c, u, s = axis_of(rr, cc)
    s0, s1 = s.min(), s.max()
    za = ground_near(*(c + u * (s0 - 10)))
    zb = ground_near(*(c + u * (s1 + 10)))
    if za is None or zb is None:
        za = zb = za or zb or WL + 8
    over = river[rr, cc].mean() > 0.2
    if over:  # a bridgehead is a street by the quay, not the hillside behind it
        za, zb = (float(np.clip(z_, WL + 6, WL + 12)) for z_ in (za, zb))
    z = deck_profile(rr, cc, s, s0, s1, za, zb, over)
    dtop[rr, cc] = np.maximum(dtop[rr, cc], np.round(z - BASE).astype(np.int16))
    dzf[rr, cc] = np.maximum(dzf[rr, cc], z - BASE)
    dsurf[rr, cc] = C["deck"]
    deck_polys.append(geom)
    bridge_info.append(dict(id=oid, name=t.get("name"), structure=t.get("bridge:structure"), c=c, u=u, s0=s0, s1=s1,
                            over=over, poly=geom, rr=rr, cc=cc))
    note(f"  bridge {t.get('name') or oid}: {s1 - s0:.0f} m, ends {za:.1f} / {zb:.1f} m, top {float(z.max()):.1f} m"
         + (" over the Danube" if over else ""))
# bridge ways outside the mapped bridge outlines get a deck of their own width; longest first, and each end starts at
# the deck it leaves (a hand-built bridge, or a viaduct already laid), so a ramp meets its viaduct


def end_z(p):
    hz = hand_deck_z(*p)
    if hz is not None:
        return hz
    x_, y_ = int(np.clip(p[0], 0, W - 1)), int(np.clip(p[1], 0, D - 1))
    win = dzf[max(y_ - 2, 0):y_ + 3, max(x_ - 2, 0):x_ + 3]
    return float(win.max()) + BASE if (win > 0).any() else ground_near(*p)


all_bridge_polys = [b["poly"] for b in bridge_info] + hand_bridges
inside_tree = shapely.STRtree(all_bridge_polys) if all_bridge_polys else None
# A viaduct mapped as several ways (the Nyugati tér flyover is three) is laid as one: one rise from each end at no more
# than 6.5 %, then level at its clearance over the ground under it, instead of a hump over every mapped piece.
free = [(oid, t, ln) for oid, t, ln in bridge_ways if ln.length >= 3 and not (
    inside_tree is not None and any(all_bridge_polys[k].buffer(2).contains(ln) for k in inside_tree.query(ln)))]
_parent = list(range(len(free)))


def _find(i):
    while _parent[i] != i:
        _parent[i] = _parent[_parent[i]]
        i = _parent[i]
    return i


_ends = defaultdict(list)
for i, (oid, t, ln) in enumerate(free):
    for q in (ln.coords[0], ln.coords[-1]):
        _ends[(round(q[0]), round(q[1]))].append(i)
for ids_ in _ends.values():
    for a_ in ids_:
        for b_ in ids_:
            ta, tb = free[a_][1], free[b_][1]
            same = (ta.get("name") == tb.get("name")) and (ta.get("layer") == tb.get("layer")) and \
                (bool(ta.get("highway")) == bool(tb.get("highway")))
            if a_ != b_ and same:
                _parent[_find(a_)] = _find(b_)
chains = defaultdict(list)
for i in range(len(free)):
    chains[_find(i)].append(free[i])
VIADUCT_MIN = 40.0
pier_pts = []


def viaduct_profile(line, za, zb):
    """the deck along a merged viaduct: (s samples, z) rising at most 6.5 % from each end to its clearance"""
    L_ = line.length
    ss_ = np.arange(0, L_ + 1.0, 1.0)
    pts_ = shapely.line_interpolate_point(line, ss_)
    gx, gy = shapely.get_x(pts_), shapely.get_y(pts_)
    gz_ = GROUND[np.clip(gy.astype(int), 0, D - 1), np.clip(gx.astype(int), 0, W - 1)]
    mid = (ss_ > 0.2 * L_) & (ss_ < 0.8 * L_)
    zt = max(float(gz_[mid].max()) + 6.2 if mid.any() else max(za, zb), max(za, zb))
    z_ = np.minimum(zt, np.minimum(za + 0.065 * ss_, zb + 0.065 * (L_ - ss_)))
    lin = za + (zb - za) * ss_ / max(L_, 1)
    return ss_, np.maximum(z_, lin)


for root, members in sorted(chains.items(), key=lambda kv: -sum(m_[2].length for m_ in kv[1])):
    merged = shapely.line_merge(shapely.MultiLineString([m_[2] for m_ in members])) if len(members) > 1 else members[0][2]
    kind0 = members[0][1].get("highway") or "rail"
    slow = kind0 in ("footway", "path", "cycleway", "pedestrian", "steps", "bridleway")
    if merged.geom_type == "LineString" and merged.length >= VIADUCT_MIN and not slow:
        za, zb = end_z(merged.coords[0]), end_z(merged.coords[-1])
        if za is None or zb is None:
            continue
        ss_, zs_ = viaduct_profile(merged, za, zb)
        for oid, t, ln in members:
            kind = t.get("highway") or "rail"
            poly = ln.buffer(width_of(t, kind) / 2 + (1 if kind in ROADS else 0.5), cap_style="flat")
            rr, cc = cells_of(poly)
            if not len(rr):
                continue
            sv = shapely.line_locate_point(merged, shapely.points(cc + 0.5, rr + 0.5))
            z = np.interp(sv, ss_, zs_)
            new = dtop[rr, cc] == 0
            dtop[rr[new], cc[new]] = np.round(z[new] - BASE).astype(np.int16)
            dzf[rr[new], cc[new]] = z[new] - BASE
            dsurf[rr[new], cc[new]] = C["deck"]
            deck_polys.append(poly)
        # columns under it where it is up in the air and not over a road: a pair across the deck every ~26 m
        if kind0 in ROADS or kind0 == "rail":
            hw_ = width_of(members[0][1], kind0) / 2
            for s_ in np.arange(13.0, merged.length - 8.0, 26.0):
                zc_ = float(np.interp(s_, ss_, zs_))
                p0 = merged.interpolate(s_)
                p1 = merged.interpolate(min(s_ + 1.0, merged.length))
                tx_, ty_ = p1.x - p0.x, p1.y - p0.y
                n_ = math.hypot(tx_, ty_) or 1.0
                nx_, ny_ = -ty_ / n_, tx_ / n_
                for off in (-0.55 * hw_, 0.55 * hw_):
                    x_, y_ = p0.x + nx_ * off, p0.y + ny_ * off
                    xi_, yi_ = int(x_), int(y_)
                    if not (0 <= xi_ < W and 0 <= yi_ < D) or road[max(yi_ - 1, 0):yi_ + 2, max(xi_ - 1, 0):xi_ + 2].any() \
                            or water[yi_, xi_]:
                        continue
                    if zc_ - GROUND[yi_, xi_] > 3.5:
                        pier_pts.append((x_, y_, zc_))
        continue
    for oid, t, ln in members:  # short or branching: each way on its own
        if ln.length < 12:
            continue
        kind = t.get("highway") or "rail"
        poly = ln.buffer(width_of(t, kind) / 2 + (1 if kind in ROADS else 0.5), cap_style="flat")
        rr, cc = cells_of(poly)
        if not len(rr):
            continue
        sv = shapely.line_locate_point(ln, shapely.points(cc + 0.5, rr + 0.5))
        za = end_z(ln.coords[0])
        zb = end_z(ln.coords[-1])
        if za is None or zb is None:
            continue
        z = deck_profile(rr, cc, sv, 0, ln.length, za, zb, False)
        new = dtop[rr, cc] == 0
        dtop[rr[new], cc[new]] = np.round(z[new] - BASE).astype(np.int16)
        dzf[rr[new], cc[new]] = z[new] - BASE
        dsurf[rr[new], cc[new]] = C["deck"]
        deck_polys.append(poly)
note(f"viaducts: {sum(1 for ms in chains.values() if len(ms) > 1)} chains of ways laid as one, {len(pier_pts)} columns")
deck = dtop > 0
# a deck stands at least a metre over the ground, except where it meets a street at its end: there it starts at the
# street's level and the metre comes over the next 8 m (a metre's lift at the end was a kerb no car could climb onto
# the Nyugati tér flyover)
lift = np.clip(ndimage.distance_transform_cdt(~(road & ~deck), metric="taxicab")[deck] / 8.0, 0, 1).astype(np.float32)
dtop[deck] = np.maximum(dtop[deck], g[deck] + np.round(lift).astype(np.int16))
dzf[deck] = np.maximum(dzf[deck], g[deck] + lift)
deck_lift = np.zeros((D, W), np.uint8)  # the same in voxels, for the 0.5 m deck in build()
deck_lift[deck] = np.round(lift * F).astype(np.uint8)
del lift
dz_fill = np.where(deck, dzf, ndimage.maximum_filter(dzf, 5))  # for interpolating the deck at its 0.5 m edge
deck_tree = shapely.STRtree(deck_polys) if deck_polys else None
# the ways on the decks, painted on them
for oid, t, ln in bridge_ways:
    kind = t.get("highway")
    if kind:
        k = SURF.get(t.get("surface"), "asphalt" if kind in ROADS else "paving")
        rr, cc = cells_of(ln.buffer(width_of(t, kind) / 2, cap_style="flat"))
    else:
        k = "ballast" if t.get("railway") != "tram" else "trambed"
        rr, cc = cells_of(ln.buffer(1.6, cap_style="flat"))
    on = deck[rr, cc]
    dsurf[rr[on], cc[on]] = C[k]
    if not kind:
        rr, cc = cells_of(ln.buffer(1.05, cap_style="flat").difference(ln.buffer(0.4)), all_touched=True)
        on = deck[rr, cc]
        dsurf[rr[on], cc[on]] = C["rail"]
note("decks:", int(deck.sum()), "cells")

# piers under the decks (bridge:support=pier), up to the deck's underside
pz1 = np.zeros((D, W), np.int16)
pcol = np.zeros((D, W), np.uint16)
deck_bot = np.where(deck, dtop - 2, 0).astype(np.int16)
db_near = ndimage.maximum_filter(deck_bot, 25)
hand_union = shapely.union_all(hand_bridges) if hand_bridges else None
for oid, kind, t, geom in osm.areas:
    if t.get("bridge:support") in ("pier", "abutment") and "building" not in t:
        if hand_union is not None and hand_union.buffer(5).contains(geom.centroid):
            continue
        rr, cc = cells_of(geom, all_touched=True)
        pz1[rr, cc] = np.maximum(db_near[rr, cc], g[rr, cc] + 1)
        pcol[rr, cc] = C["pier"]
for x_, y_, zc_ in pier_pts:  # the viaducts' columns, round, 1.6 m across
    rr, cc = cells_of(Point(x_, y_).buffer(0.85), all_touched=True)
    pz1[rr, cc] = np.maximum(int(round(zc_ - 1.6 - BASE)), g[rr, cc] + 1)
    pcol[rr, cc] = C["pier"]

# ---------------------------------------------------------------- fine ground, and point voxels: lamps
Gmin3 = ndimage.minimum_filter(G, 3)  # the water level next to a quay


def ground_fine(r0, r1, c0, c1):
    """the ground (first free 0.5 m voxel) on a fine window: the 1 m ground interpolated, water kept flat."""
    yy = (np.arange(r0, r1) + 0.5) / F - 0.5
    xx = (np.arange(c0, c1) + 0.5) / F - 0.5
    Gw = ndimage.map_coordinates(G, np.meshgrid(yy, xx, indexing="ij"), order=1, mode="nearest")
    wat = water_f[r0:r1, c0:c1]
    if wat.any():
        Gw = np.where(wat, Gmin3[np.ix_(np.arange(r0, r1) // F, np.arange(c0, c1) // F)], Gw)
    return np.round((Gw - BASE) * F).astype(np.int16)


def gfine_at(x, y):
    """fine ground z at a point given in 1 m grid coordinates."""
    xf, yf = int(np.clip(x * F, 0, WF - 1)), int(np.clip(y * F, 0, DF - 1))
    return int(ground_fine(yf, yf + 1, xf, xf + 1)[0, 0])


# pedestrian underpasses (after warsaw-vibe-voxel): every footway OSM maps one level under the street, outside a
# building, is a corridor 3 m high, its floor 4 m under the street over it; the stairs between the street and that
# level are open stairwells with a parapet round them. Deeper levels (the metro's) stay solid.
UP_DEPTH, UP_H = 4.0, 3.0
_ob_tree = shapely.STRtree([f["geom"] for f in outlines])


def _levels(t):
    out = set()
    for v in (t.get("level") or "").replace(",", ";").split(";"):
        try:
            out.add(int(float(v)))
        except ValueError:
            pass
    return out


def _inside_buildings(ln):
    return sum(ln.intersection(outlines[k]["geom"]).length for k in _ob_tree.query(ln)) / max(ln.length, 1e-6)


def _street_floor(xy):
    """the passage floor under points: the street smoothed over 21 m (never above the street right there), less 4 m"""
    c = np.clip(xy[:, 0].astype(int), 10, W - 11)
    r = np.clip(xy[:, 1].astype(int), 10, D - 11)
    sm = np.array([float(G[r_ - 10:r_ + 11, c_ - 10:c_ + 11].mean()) for r_, c_ in zip(r, c)])
    return np.minimum(sm, Gmin3[r, c]) - UP_DEPTH


up_pass, up_steps = [], []
for oid, t, ln in osm.lines:
    hw = t.get("highway")
    if hw not in ("footway", "path", "pedestrian", "corridor", "steps") or t.get("tunnel") == "building_passage":
        continue
    lay, lv = parse_len(t.get("layer")), _levels(t)
    if hw == "steps":
        if not (lv >= {-1, 0} and min(lv) >= -1) and not (lay == -1 and not lv):
            continue
    elif not ((lay == -1 and lv in (set(), {-1})) or (lay is None and lv == {-1} and is_off(t, "tunnel"))):
        continue
    ends = [Point(ln.coords[0]), Point(ln.coords[-1])]
    if not all(20 <= p_.x < W - 20 and 20 <= p_.y < D - 20 for p_ in ends) or near_water(ln, 40) or _inside_buildings(ln) > 0.5:
        continue
    (up_steps if hw == "steps" else up_pass).append((oid, t, ln))
# the concourses OSM maps as areas a level down (Astoria, Blaha, Kálvin tér): one flat floor each
up_halls = []
for oid, kind, t, hg in osm.areas:
    if "building" in t or "building:part" in t or hg.area < 20 or hg.area > 15000:
        continue
    lay, lv = parse_len(t.get("layer")), _levels(t)
    if not ((lay == -1 and lv in (set(), {-1})) or (lay is None and lv == {-1})):
        continue
    if t.get("highway") not in ("pedestrian", "footway") and t.get("indoor") not in ("corridor", "area", "room"):
        continue
    inside = sum(hg.intersection(outlines[k_]["geom"]).area for k_ in _ob_tree.query(hg)) / hg.area
    if inside > 0.5 or near_water(hg.exterior, 40) or not (20 <= hg.centroid.x < W - 20 and 20 <= hg.centroid.y < D - 20):
        continue
    up_halls.append((oid, t, hg))
underpasses = []
for oid, t, hg in up_halls:
    x0, y0, x1, y1 = hg.bounds
    gx_, gy_ = np.meshgrid(np.arange(x0, x1, 2.0), np.arange(y0, y1, 2.0))
    in_ = shapely.contains_xy(hg, gx_, gy_)
    xy = np.stack([gx_[in_], gy_[in_]], 1) if in_.any() else np.array([[hg.centroid.x, hg.centroid.y]])
    underpasses.append(dict(kind="hall", poly=hg, zc=float(np.percentile(_street_floor(xy), 20))))
for oid, t, ln in up_pass:
    ss = np.arange(0, ln.length + 1.0, 1.0)
    xy = shapely.get_coordinates(shapely.line_interpolate_point(ln, np.minimum(ss, ln.length)))
    fl = ndimage.uniform_filter1d(_street_floor(xy), 7, mode="nearest")
    wd = parse_len(t.get("width"))
    wd = wd if wd and 2 <= wd <= 20 else 5.0
    underpasses.append(dict(kind="pass", line=ln, poly=ln.buffer(wd / 2, cap_style="round"), s=ss, z=fl))
if underpasses:
    _low = [u.get("line", u["poly"]) for u in underpasses]
    _lt = shapely.STRtree(_low)

    def _below(p_):
        """(distance to the nearest passage or concourse within 3 m, its floor there)"""
        best = (99.0, None)
        for k in _lt.query(p_.buffer(3.0)):
            d_ = _low[k].distance(p_)
            if d_ < best[0]:
                u = underpasses[k]
                best = (d_, u["zc"] if u["kind"] == "hall" else float(_street_floor(np.array([[p_.x, p_.y]]))[0]))
        return best

    for oid, t, ln in up_steps:
        a, b = Point(ln.coords[0]), Point(ln.coords[-1])
        (da, za_), (db, zb_) = _below(a), _below(b)
        if min(da, db) > 3.0 or max(da, db) < 3.0:
            continue  # stairs that don't join a passage at one end only
        if da < db:
            ln = LineString(ln.coords[::-1])
            a, b, zb_ = b, a, za_
        ztop_, zbot_ = float(Gmin3[int(a.y), int(a.x)]), zb_
        if ztop_ - zbot_ < 1.5:
            continue
        wd = parse_len(t.get("width"))
        wd = wd if wd and 1.5 <= wd <= 12 else 3.0
        L = ln.length
        dx, dy = np.subtract(ln.coords[-1], ln.coords[-2])
        n_ = np.array([-dy, dx]) / max(math.hypot(dx, dy), 1e-6)
        foot = LineString([tuple(np.array(b.coords[0]) + n_ * (wd / 2 + 0.5)), tuple(np.array(b.coords[0]) - n_ * (wd / 2 + 0.5))])
        poly = ln.buffer(wd / 2, cap_style="flat")
        par = shapely.union_all([ln.offset_curve(wd / 2 + 0.25), ln.offset_curve(-wd / 2 - 0.25), foot]).buffer(0.25, cap_style="flat")
        underpasses.append(dict(kind="steps", line=ln, poly=poly, s=np.array([0.0, L]), z=np.array([ztop_, zbot_]),
                                parapet=par.difference(poly)))
up_tree = shapely.STRtree([u["poly"].buffer(1.2) for u in underpasses]) if underpasses else None
UP_WALL, UP_PARAPET = pal(hex_rgb("#cfc9bb"), CLASSIC), pal(hex_rgb("#d9d4c8"), CLASSIC)
note(f"underpasses: {sum(u['kind'] == 'hall' for u in underpasses)} concourses, "
     f"{sum(u['kind'] == 'pass' for u in underpasses)} passages, {sum(u['kind'] == 'steps' for u in underpasses)} stairwells")


def carve_underpasses(vol, r0, r1, c0, c1, gg):
    """the passages and stairwells in a fine window: walls, ceiling and floor in pale stone, stairs stepped."""
    if up_tree is None:
        return
    H = vol.shape[0]
    idx = up_tree.query(box(c0 / F, r0 / F, c1 / F, r1 / F), predicate="intersects")
    for pass_first in (True, False):
        for k in idx:
            u = underpasses[k]
            if (u["kind"] != "steps") != pass_first:
                continue
            for geom, what in ((u["poly"].buffer(1.0), "shell"), (u["poly"], "hole")):
                rr, cc = cells_f(geom)
                m = (rr >= r0) & (rr < r1) & (cc >= c0) & (cc < c1)
                rr, cc = rr[m], cc[m]
                if not len(rr):
                    continue
                if u["kind"] == "hall":
                    zf = np.full(len(rr), int(round((u["zc"] - BASE) * F)))
                else:
                    sc = shapely.line_locate_point(u["line"], shapely.points((cc + 0.5) / F, (rr + 0.5) / F))
                    zf = np.round((np.interp(sc, u["s"], u["z"]) - BASE) * F).astype(int)
                y_, x_ = rr - r0, cc - c0
                gz = gg[y_, x_]
                if u["kind"] != "steps":
                    z1 = zf + int(UP_H * F)
                else:
                    z1 = np.where(what == "hole", gz + 6, gz)
                for zz in np.unique(zf):
                    kk = zf == zz
                    lo = max(int(zz) - 1, 0)
                    if what == "shell":
                        top_ = np.max(z1[kk]) + 1 if u["kind"] != "steps" else int(np.max(gz[kk]))
                        for z_ in range(lo, min(top_, H)):
                            col_ = vol[z_, y_[kk], x_[kk]]
                            sel = (col_ != 0) & (z_ < gz[kk] - 1)
                            vol[z_, y_[kk][sel], x_[kk][sel]] = UP_WALL
                    else:
                        for z_ in range(int(zz), min(int(np.max(z1[kk])), H)):
                            sel = z_ < z1[kk]
                            vol[z_, y_[kk][sel], x_[kk][sel]] = 0
                        if 0 < zz <= H:
                            vol[zz - 1, y_[kk], x_[kk]] = C["steps"] if u["kind"] == "steps" else C["paving"]
            if u["kind"] == "steps":
                rr, cc = cells_f(u["parapet"])
                m = (rr >= r0) & (rr < r1) & (cc >= c0) & (cc < c1)
                y_, x_ = rr[m] - r0, cc[m] - c0
                for dz in range(2):
                    z_ = gg[y_, x_] + dz
                    ok = (z_ < H) & (z_ >= 0)
                    vol[z_[ok], y_[ok], x_[ok]] = UP_PARAPET


PV = []  # (x, y, z, palette) in 0.5 m voxels
lamps = []  # (x, y, z) of every lamp head in metres, for the light pools at night


def lamp_post(xf, yf, z0, height=5.0):
    n = int(round(height * F))
    PV.extend((xf, yf, z, C["pole"]) for z in range(z0, z0 + n))
    PV.append((xf, yf, z0 + n, C["lamp"]))
    lamps.append([round((xf + 0.5) / F, 1), round((yf + 0.5) / F, 1), round((z0 + n) / F, 1)])


# the Danube bridges are lit: a lamp every 28 m along each railing (OSM maps almost none on them)
dk = deck.copy()
edge = dk & ~ndimage.binary_erosion(dk, border_value=1)
er, ec = np.nonzero(edge)
lowside = ndimage.minimum_filter(np.where(dk, 32767, g).astype(np.int16), 3)[er, ec] < dtop[er, ec] - 1
for b in bridge_info:
    if not b["over"]:
        continue
    c, u = b["c"], b["u"]
    v = np.array([-u[1], u[0]])
    inb = np.zeros((D, W), bool)
    inb[b["rr"], b["cc"]] = True
    k = inb[er, ec] & lowside
    rr_, cc_ = er[k], ec[k]
    pts = np.stack([cc_ + 0.5, rr_ + 0.5], 1) - c
    s_, side = pts @ u, np.sign(pts @ v - np.median(pts @ v))
    for sd in (-1, 1):
        last = -1e9
        for i in np.argsort(s_):
            if side[i] != sd or s_[i] - last < 28 or s_[i] < b["s0"] + 8 or s_[i] > b["s1"] - 8:
                continue
            last = s_[i]
            x, y = int(cc_[i]), int(rr_[i])
            lamp_post(x * F + F // 2, y * F + F // 2, int(round(dzf[y, x] * F)))
del dk, edge
# street lamps: a 5 m pole and a head that glows at night
for oid, t, p in osm.nodes_with("highway", ("street_lamp",)):
    c, r = int(p.x), int(p.y)
    if not (0 <= c < W and 0 <= r < D) or held[r, c] or water[r, c]:
        continue
    z0 = int(round(dzf[r, c] * F)) if deck[r, c] else gfine_at(p.x, p.y)
    lamp_post(int(p.x * F), int(p.y * F), z0)
# ---------------------------------------------------------------- street furniture seen by Mapillary
# Mapillary triangulates objects from its street-level photos (scripts/fetch_mapillary.py). Where photos are dense the
# same object is found many times over (12 700 "street lights" in one km of the Belvaros; a traffic light again as its
# front, side and back), so each kind is thinned to the spacing such things really have (most recently seen kept),
# traffic lights are kept only near junctions OSM marks as signalised, anything on a carriageway or in a wall is moved
# to the nearest free cell within 4 m or dropped, and OSM's own lamps win over Mapillary's.
MLY = Path("data/raw/mapillary/features.json")
furn = defaultdict(int)
if MLY.exists():
    from scipy.spatial import cKDTree
    from aoi import WGS_TO_EOV, to_grid as grid_of
    BLUE = ("go-straight", "keep-", "turn-", "pass-on", "roundabout", "one-way", "mandatory")
    KINDS = (("object--street-light", "light", 18.0), ("object--traffic-light--pedestrians", "pedsig", 15.0),
             ("object--traffic-light--general", "signal", 15.0), ("object--bench", "bench", 6.0), ("object--trash-can", "bin", 10.0),
             ("object--bike-rack", "rack", 6.0), ("object--fire-hydrant", "hydrant", 8.0), ("regulatory--", "sign", 22.0),
             ("warning--", "sign_warn", 30.0), ("information--", "sign_blue", 30.0), ("marking--discrete--crosswalk-zebra", "zebra", 12.0))
    since = 1546300800000  # 2019-01-01: older sightings may be gone
    groups = defaultdict(list)
    for lon, lat, v, fs, ls in json.load(open(MLY)):
        if not v or (ls or 0) < since:
            continue
        for pre, kind, rad in KINDS:
            if v.startswith(pre):
                if kind == "sign" and any(b in v for b in BLUE):
                    kind = "sign_blue"
                groups[(kind, rad)].append((lon, lat, ls or 0))
                break
    blocked = held | road | water | deck | hb_mask  # hb_mask: the hand-built bridges, whose carriageways aren't in `road`
    osm_lamps = cKDTree(np.array([(x, y) for x, y, _ in lamps])) if lamps else None
    cross = [p for oid, t, p in osm.nodes if t.get("highway") == "crossing" or t.get("crossing")] + \
            [ln.interpolate(0.5, normalized=True) for oid, t, ln in osm.lines if t.get("footway") == "crossing"]
    cross_tree = cKDTree(np.array([(p.x, p.y) for p in cross])) if cross else None
    sig = [p for oid, t, p in osm.nodes if t.get("highway") == "traffic_signals" or t.get("crossing") == "traffic_signals"]
    sig_tree = cKDTree(np.array([(p.x, p.y) for p in sig])) if sig else None
    car_lines = [ln for oid, t, ln in osm.lines if t.get("highway") in ROADS and not underground(t) and not on_bridge(t)]
    car_tree = shapely.STRtree(car_lines)
    COLS = {"sign": C["sign_red"], "sign_blue": C["sign_blue"], "sign_warn": C["sign_warn"]}

    def free_spot(x, y, r=4):
        c, rw = int(x), int(y)
        if not (0 <= c < W and 0 <= rw < D):
            return None
        if not blocked[rw, c]:
            return x, y
        r0, r1, c0, c1 = max(rw - r, 0), min(rw + r + 1, D), max(c - r, 0), min(c + r + 1, W)
        yy, xx = np.nonzero(~blocked[r0:r1, c0:c1])
        if not len(yy):
            return None
        k = np.argmin((yy + r0 + 0.5 - y) ** 2 + (xx + c0 + 0.5 - x) ** 2)
        return xx[k] + c0 + 0.5, yy[k] + r0 + 0.5

    for (kind, rad), pts in groups.items():
        a_ = np.array(pts)
        xs, ys = grid_of(*WGS_TO_EOV.transform(a_[:, 0], a_[:, 1]))
        xy = np.stack([xs, ys], 1)
        tree = cKDTree(xy)
        taken = np.zeros(len(xy), bool)
        for i in np.argsort(-a_[:, 2]):
            if taken[i]:
                continue
            taken[tree.query_ball_point(xy[i], rad)] = True
            x, y = xy[i]
            if kind == "zebra":  # a crossing OSM doesn't map: stripes across the road, square to it
                if cross_tree is not None and cross_tree.query(xy[i])[0] < 12:
                    continue
                pt = Point(x, y)
                near_ = car_tree.query(pt.buffer(8))
                if not len(near_):
                    continue
                ln = car_lines[min(near_, key=lambda k: car_lines[k].distance(pt))]
                sl = ln.project(pt)
                p0, p1 = np.array(ln.interpolate(max(sl - 1, 0)).coords[0]), np.array(ln.interpolate(min(sl + 1, ln.length)).coords[0])
                u = (p1 - p0) / max(np.linalg.norm(p1 - p0), 1e-6)
                q = np.array(ln.interpolate(sl).coords[0])
                v = np.array([-u[1], u[0]])
                corners = [q + u * a + v * b for a, b in ((-2, -12), (2, -12), (2, 12), (-2, 12))]
                rr, cc = cells_f(shapely.geometry.Polygon(corners))
                if not len(rr):
                    continue
                across = ((cc + 0.5) / F - q[0]) * v[0] + ((rr + 0.5) / F - q[1]) * v[1]
                k = np.isin(gcol[rr, cc], [C["asphalt"], C["parking_lane"], C["mark"]]) & (np.floor(across / 1.0).astype(int) % 2 == 0)
                gcol[rr[k], cc[k]] = C["mark"]
                furn[kind] += 1
                continue
            spot = free_spot(x, y)
            if spot is None:
                continue
            x, y = spot
            if kind == "light" and osm_lamps is not None and osm_lamps.query((x, y))[0] < 15:
                continue
            if kind in ("signal", "pedsig") and (sig_tree is None or sig_tree.query((x, y))[0] > 30):
                continue
            xf, yf = int(x * F), int(y * F)
            z0 = gfine_at(x, y)
            if kind == "light":
                lamp_post(xf, yf, z0, 7.0)
            elif kind in ("signal", "pedsig"):
                hp = 7 if kind == "signal" else 5
                PV.extend((xf, yf, z, C["pole"]) for z in range(z0, z0 + hp))
                PV.extend([(xf, yf, z0 + hp, C["signal"]), (xf, yf, z0 + hp + 1, C["signal_red"])])
            elif kind == "bench":
                PV.extend([(xf, yf, z0, C["bench"]), (xf + 1, yf, z0, C["bench"])])
            elif kind == "bin":
                PV.append((xf, yf, z0, C["bin"]))
            elif kind == "rack":
                PV.extend([(xf, yf, z0, C["pole"]), (xf + 1, yf, z0, C["pole"])])
            elif kind == "hydrant":
                PV.append((xf, yf, z0, C["hydrant"]))
            else:  # traffic signs: a 2.5 m post and the plate
                PV.extend((xf, yf, z, C["pole"]) for z in range(z0, z0 + 5))
                PV.append((xf, yf, z0 + 5, COLS[kind]))
            furn[kind] += 1
    del blocked
    note("Mapillary street furniture:", dict(furn))
note("point voxels", len(PV), ";", len(lamps), "lamps")

# ---------------------------------------------------------------- landmarks, built by hand from photos and plans
feat_by_id = {str(f["id"]): f for f in feats}
for fs, base_ in ((outlines, base_o), (parts, base_p)):
    for i, f in enumerate(fs):
        f["base"] = float(base_[i + 1])  # metres above the model base
LMS = landmarks.build(dict(F=F, BASE=BASE, WL=WL, G=G, gfine_at=gfine_at, feats=feat_by_id, osm=osm, pal=pal, C=C,
                           W=W, D=D, note=note, lamp_post=lamp_post, plan=LMK, theta=THETA, river=river, road=road))
PVa = np.array(PV + LMS.points, np.int32).reshape(-1, 4)
pv_bin = defaultdict(list)
for k, (x, y, z, p) in enumerate(PVa):
    pv_bin[(y // 128, x // 128)].append(k)
pv_bin = {k: np.array(v) for k, v in pv_bin.items()}
note("landmarks:", len(LMS.prims), "solids,", len(LMS.points), "voxels in thin parts")

# ---------------------------------------------------------------- volume builder (0.5 m)
NO, NP = len(outlines), len(parts)
ow, orf = arr(outlines, "wall", np.uint16), arr(outlines, "roof", np.uint16)
prf = arr(parts, "roof", np.uint16)
out_tree = shapely.STRtree([f["geom"] for f in outlines]) if outlines else None
part_tree = shapely.STRtree([f["geom"] for f in parts]) if parts else None
corn_ok = np.zeros(65536, bool)  # walls that get a cornice under the eaves: plaster and stone, not glass or sheds
for i, e in enumerate(pal.entries):
    corn_ok[i] = e[3] in (TENEMENT, CLASSIC, WALL)
PADB = 16  # voxels of context around a window: roof slopes and cornices near its edge need the buildings beyond


def near(a, r0, r1, c0, c1):
    """a 1 m raster sampled at the centres of a fine window (nearest)."""
    return a[np.ix_(np.clip(np.arange(r0, r1) // F, 0, D - 1), np.clip(np.arange(c0, c1) // F, 0, W - 1))]


def bilin(a, r0, r1, c0, c1):
    yy = (np.arange(r0, r1) + 0.5) / F - 0.5
    xx = (np.arange(c0, c1) + 0.5) / F - 0.5
    return ndimage.map_coordinates(a, np.meshgrid(yy, xx, indexing="ij"), order=1, mode="nearest")


def edt_m(m):
    """distance (metres) from each cell of mask m to its edge, as odist / pdist on the 1 m grid."""
    return (ndimage.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1] * VOX - VOX / 2).astype(np.float32)


def fine_buildings(r0, r1, c0, c1, gg):
    """buildings on a (padded) fine window -> b0, bl, be, b1 (fine z), wl, wc, rc, cornice cells or None."""
    shape = (r1 - r0, c1 - c0)
    tr = Affine(1 / F, 0, c0 / F, 0, 1 / F, r0 / F)
    bx = box(c0 / F, r0 / F, c1 / F, r1 / F)
    oi = out_tree.query(bx, predicate="intersects") if out_tree is not None else []
    pi = part_tree.query(bx, predicate="intersects") if part_tree is not None else []
    if not len(oi) and not len(pi):
        return None

    def rz(items):
        return _rz(items, out_shape=shape, transform=tr, fill=0, dtype=np.int32)

    ob_f = rz([(outlines[i]["geom"], i + 1) for i in sorted(oi, key=lambda i: oH[i + 1])]) if len(oi) else np.zeros(shape, np.int32)
    pb_f = rz([(parts[i]["geom"], i + 1) for i in sorted(pi, key=lambda i: pH[i + 1])]) if len(pi) else np.zeros(shape, np.int32)
    top = np.zeros(shape, np.float32)
    eav = np.zeros(shape, np.float32)
    bot = np.zeros(shape, np.float32)
    low = np.zeros(shape, np.float32)
    fb = np.zeros(shape, np.float32)
    wl_ = np.zeros(shape, np.uint16)
    wc_ = np.zeros(shape, np.uint16)
    rc_ = np.zeros(shape, np.uint16)
    shp = np.zeros(shape, np.int8)
    dist = np.zeros(shape, np.float32)
    m = ob_f > 0
    if m.any():
        d_ = edt_m(m)
        dist = np.where(d_ < 6, d_, np.maximum(bilin(odist, r0, r1, c0, c1), 6))
        i = ob_f[m]
        top[m] = roof_rel(osh[i], oE[i], oH[i], dist[m], oR[i])
        eav[m] = np.minimum(oE[i], top[m] - 1)
        bot[m] = ominh[i]
        wc_[m], rc_[m], fb[m], shp[m] = ow[i], orf[i], base_o[i], osh[i]
    m = pb_f > 0
    if m.any():
        pd = np.zeros(shape, np.float32)
        pd_up = bilin(pdist, r0, r1, c0, c1)
        for k in np.unique(pb_f[m]):
            sel = pb_f == k
            d_ = edt_m(rz([(parts[k - 1]["geom"], 1)]) > 0)
            pd[sel] = np.where(d_[sel] < 6, d_[sel], np.maximum(pd_up[sel], 6))
        i = pb_f[m]
        ptop = roof_rel(psh[i], pE[i], pH[i], pd[m], pR[i])
        under = near(pu, r0, r1, c0, c1)[m]
        o_under = ob_f[m]
        lo_wall = np.where(under > 0, pw[under], np.where(o_under > 0, ow[o_under], 0))
        has_support = (under > 0) | (o_under > 0)
        pm = pminh[i]
        low[m] = np.where(has_support & (pm > 0), pm, 0)
        bot[m] = np.where(~has_support & pfloat[i], pm, 0)
        wl_[m] = lo_wall
        top[m] = ptop
        eav[m] = np.minimum(pE[i], ptop - 1)
        wc_[m], rc_[m], fb[m], shp[m] = pw[i], prf[i], base_p[i], psh[i]
        dist[m] = pd[m]
    bm = (ob_f > 0) | (pb_f > 0)
    # flat roofs over 150 m2 get a 1 m parapet, half a metre thick, in the wall's colour
    edge = bm & (shp == 0) & (top > 8) & (dist < VOX)
    edge &= np.where((ob_f > 0) & (pb_f == 0), big[ob_f], True)
    top[edge] += 1
    eav[edge] = top[edge]
    b1 = np.where(bm, np.maximum(np.round((fb + top) * F), gg + 2 * F), 0).astype(np.int16)
    be = np.where(bm, np.clip(np.round((fb + eav) * F), gg, b1 - 1), 0).astype(np.int16)
    b0 = np.where(bm, np.clip(np.round(np.where(bot > 0, (fb + bot) * F, gg)), gg, np.maximum(be - 1, gg)), 0).astype(np.int16)
    bl = np.where(bm & (low > 0), np.clip(np.round((fb + low) * F), gg, be), b0).astype(np.int16)
    bl = np.maximum(bl, b0)
    # a cornice under the eaves of plastered and stone buildings with pitched roofs: one voxel out from the wall
    cand = bm & ((shp == 1) | (shp == 2)) & (be - b0 >= 9 * F) & corn_ok[wc_]
    key = np.where(cand, be.astype(np.int64) * 65536 + wc_, 0)
    km = ndimage.maximum_filter(key, 3)
    ring = ~bm & (km > 0)
    cz = (km >> 16) - 1
    ring &= cz > gg + 2 * F
    corn = (np.nonzero(ring), cz[ring], (km & 0xFFFF)[ring].astype(np.uint16))
    return b0, bl, be, b1, wl_, wc_, rc_, corn


# ---------------------------------------------------------------- trees: species, shapes, the foliage grid
_xy = np.array([(tr[0], tr[1]) for tr in trees], np.float64).reshape(-1, 2)
_info = [tr[5] for tr in trees]


def _inside(geoms, xy):
    m = np.zeros(len(xy), bool)
    if geoms and len(xy):
        m[np.unique(shapely.STRtree(geoms).query(shapely.points(xy[:, 0], xy[:, 1]), predicate="intersects")[0])] = True
    return m


_w4 = water[:D // 4 * 4, :W // 4 * 4].reshape(D // 4, 4, W // 4, 4).any((1, 3))
_dw = ndimage.distance_transform_edt(~_w4).astype(np.float32) * 4
_ix, _iy = np.clip(_xy[:, 0].astype(int), 0, W - 1), np.clip(_xy[:, 1].astype(int), 0, D - 1)
_dbld, _away = trees_mod.near_mask(bmask, _xy[:, 0], _xy[:, 1], 10)
note(f"trees: {int(road[_iy, _ix].sum())} trunks on a road cell")
FOREST = trees_mod.Forest(
    _xy[:, 0], _xy[:, 1], np.array([tr[2] for tr in trees]), np.array([tr[3] for tr in trees]), [i[0] for i in _info],
    [i[1] for i in _info], [i[2] for i in _info],
    dict(island=_inside([g_ for oid, k, t, g_ in osm.areas if t.get("place") == "island" and "Margit" in t.get("name", "")], _xy),
         park=_inside(parks, _xy), wood=_inside(woods, _xy),
         buda=~pest8[np.minimum(_iy // S, Ds - 1), np.minimum(_ix // S, Ws - 1)] if pest8 is not None else np.zeros(len(_xy), bool),
         d_water=_dw[np.minimum(_iy // 4, _dw.shape[0] - 1), np.minimum(_ix // 4, _dw.shape[1] - 1)], d_bld=_dbld, away=_away),
    F, note)
del _w4, _dw, _info
if LMS.clear and FOREST.N:  # monuments stand clear of the trees generated or mapped over them
    _keep = np.ones(FOREST.N, bool)
    for cx_, cy_, cr_ in LMS.clear:
        _keep &= np.hypot(_xy[:, 0] - cx_, _xy[:, 1] - cy_) > cr_ + 0.6 * FOREST.r
    note(f"trees cleared round the monuments: {int((~_keep).sum())}")
    FOREST.take(_keep)
    _xy = _xy[_keep]
FOREST.place([gfine_at(x, y) for x, y in _xy])
tree_bin = defaultdict(list)
for k, (x, y) in enumerate(zip(FOREST.cx, FOREST.cy)):
    tree_bin[(int(y) // 128, int(x) // 128)].append(k)
tree_bin = {k: np.array(v) for k, v in tree_bin.items()}
FOL_COLS, FOL_ROWS = -(-WF // 4), -(-DF // 4)  # the foliage grid: 2 m cells
fol_cls, fol_uid = FOREST.plane(FOL_COLS, FOL_ROWS, 4)
note(f"trees: {FOREST.N}; foliage grid {FOL_COLS} x {FOL_ROWS}, {int((fol_cls > 0).sum())} cells with a class; "
     f"{len(FOREST.cache)} crown shapes ({FOREST.cache_mb():.0f} MB)")
ROADLUT = np.zeros(65536, bool)
ROADLUT[[C[k_] for k_ in ("asphalt", "sett", "road_paving", "parking", "rail", "trambed", "ballast", "mark", "parking_lane",
                          "kerb")]] = True


def build(r0, r1, c0, c1):
    """0.5 m voxels of the fine window rows r0:r1, cols c0:c1 -> uint16 (h, r1 - r0, c1 - c0)."""
    R, Cc = r1 - r0, c1 - c0
    P0, P1, Q0, Q1 = max(r0 - PADB, 0), min(r1 + PADB, DF), max(c0 - PADB, 0), min(c1 + PADB, WF)
    crop = (slice(r0 - P0, r0 - P0 + R), slice(c0 - Q0, c0 - Q0 + Cc))
    ggp = ground_fine(P0, P1, Q0, Q1)
    gg = ggp[crop]
    fbld = fine_buildings(P0, P1, Q0, Q1, ggp)
    # decks
    dt = None
    if deck_tree is not None:
        bxp = box(Q0 / F, P0 / F, Q1 / F, P1 / F)
        di = deck_tree.query(bxp, predicate="intersects")
        if len(di):
            dkp = _rz([(deck_polys[i], 1) for i in di], out_shape=(P1 - P0, Q1 - Q0),
                      transform=Affine(1 / F, 0, Q0 / F, 0, 1 / F, P0 / F), fill=0, dtype=np.uint8).astype(bool)
            if dkp.any():
                dtp = np.where(dkp, np.maximum(np.round(bilin(dz_fill, P0, P1, Q0, Q1) * F), ggp + near(deck_lift, P0, P1, Q0, Q1)), 0).astype(np.int16)
                rail = dkp & ~ndimage.binary_erosion(dkp, border_value=1)
                rail &= ndimage.minimum_filter(np.where(dkp, 32767, ggp), 3) < dtp - 2
                dt, rail = dtp[crop], rail[crop]
                ds = near(dsurf, r0, r1, c0, c1)
                ds = np.where(ds == 0, C["deck"], ds)
    pz = near(pz1, r0, r1, c0, c1).astype(np.int16) * F
    # what reaches highest: trees, points, landmarks
    M_ = FOREST.reach
    tb_ = sorted(k for by in range((r0 - M_) // 128, (r1 + M_) // 128 + 1) for bx in range((c0 - M_) // 128, (c1 + M_) // 128 + 1)
                 for k in tree_bin.get((by, bx), []))
    pb_ = np.concatenate([pv_bin.get((by, bx), np.zeros(0, int)) for by in range(r0 // 128, (r1 - 1) // 128 + 1)
                          for bx in range(c0 // 128, (c1 - 1) // 128 + 1)] or [np.zeros(0, int)]).astype(int)
    pts = PVa[pb_] if len(pb_) else np.zeros((0, 4), np.int32)
    pts = pts[(pts[:, 0] >= c0) & (pts[:, 0] < c1) & (pts[:, 1] >= r0) & (pts[:, 1] < r1)]
    hmax = int(gg.max()) + 1
    if fbld is not None:
        hmax = max(hmax, int(fbld[3][crop].max()) + 1)
    if dt is not None:
        hmax = max(hmax, int(dt.max()) + 3)
    hmax = max(hmax, int(pz.max()), int(pts[:, 2].max()) + 1 if len(pts) else 0, LMS.zmax(r0, r1, c0, c1))
    if tb_:
        hmax = max(hmax, int(FOREST.top[tb_].max()))
    H = hmax + 1
    z = np.arange(H, dtype=np.int16)[:, None, None]
    vol = np.where(z < gg - 1, near(sub, r0, r1, c0, c1), 0).astype(np.uint16)
    vol = np.where(z == gg - 1, gcol[r0:r1, c0:c1], vol)
    if fbld is not None:
        b0, bl, be, b1, wl_, wc_, rc_, corn = fbld
        a0, al, ae, a1 = b0[crop], bl[crop], be[crop], b1[crop]
        vol = np.where((z >= a0) & (z < al), wl_[crop], vol)
        vol = np.where((z >= al) & (z < ae), wc_[crop], vol)
        vol = np.where((z >= ae) & (z < a1), rc_[crop], vol)
        (cr, cc_), cz, ccol = corn
        cr, cc_ = cr - (r0 - P0), cc_ - (c0 - Q0)
        k = (cr >= 0) & (cr < R) & (cc_ >= 0) & (cc_ < Cc) & (cz < H)
        cr, cc_, cz, ccol = cr[k], cc_[k], cz[k], ccol[k]
        free_ = vol[cz, cr, cc_] == 0
        vol[cz[free_], cr[free_], cc_[free_]] = ccol[free_]
    if pz.any():
        vol = np.where((z >= gg) & (z < pz), near(pcol, r0, r1, c0, c1), vol)
    if dt is not None:
        vol = np.where((dt > 0) & (z >= dt - 3) & (z < dt - 1), C["deck_side"], vol)
        vol = np.where((dt > 0) & (z == dt - 1), ds, vol)
        rr_, cc_ = np.nonzero(rail)
        for dz_ in (0, 1):
            zz = dt[rr_, cc_] + dz_
            k = zz < H
            vol[zz[k], rr_[k], cc_[k]] = C["fence"]
    if tb_:
        FOREST.draw(vol, tb_, r0, c0, ROADLUT[gcol[r0:r1, c0:c1]])
    if len(pts):
        k = pts[:, 2] < H
        vol[pts[k, 2], pts[k, 1] - r0, pts[k, 0] - c0] = pts[k, 3]
    LMS.apply(vol, r0, r1, c0, c1)
    carve_underpasses(vol, r0, r1, c0, c1, gg)
    if tunnel_tree is not None:  # carve the tunnels, with a road (or track) floor
        for k in tunnel_tree.query(box(c0 / F, r0 / F, c1 / F, r1 / F), predicate="intersects"):
            tn = tunnels[k]
            rr, cc = cells_f(tn["poly"])
            m = (rr >= r0) & (rr < r1) & (cc >= c0) & (cc < c1)
            rr, cc = rr[m], cc[m]
            if not len(rr):
                continue
            ln = tn["line"]
            sc = shapely.line_locate_point(ln, shapely.points((cc + 0.5) / F, (rr + 0.5) / F)) / max(ln.length, 1e-6)
            zfl = np.round((tn["za"] + (tn["zb"] - tn["za"]) * sc - BASE) * F).astype(int)
            hh = int(round(tn["h"] * F))
            for zf_ in np.unique(zfl):
                kk = zfl == zf_
                y_, x_ = rr[kk] - r0, cc[kk] - c0
                vol[max(zf_, 0):max(min(zf_ + hh, H), 0), y_, x_] = 0
                if 0 < zf_ <= H:
                    solid_ = vol[zf_ - 1, y_, x_] != 0
                    vol[zf_ - 1, y_[solid_], x_[solid_]] = tn["surf"]
            if tn["tram"]:  # the rails
                d_ = shapely.distance(ln, shapely.points((cc + 0.5) / F, (rr + 0.5) / F))
                kk = (np.abs(d_ - 0.75) < 0.26) & (zfl > 0) & (zfl <= H)
                kk[kk] = vol[zfl[kk] - 1, rr[kk] - r0, cc[kk] - c0] != 0
                vol[zfl[kk] - 1, rr[kk] - r0, cc[kk] - c0] = C["rail"]
    return vol


# ---------------------------------------------------------------- export
HMAX = int(max(g.max(), bz1.max(), dtop.max() + 2, pz1.max()) * F + 40)
HMAX = max(HMAX, int(PVa[:, 2].max()) + 1 if len(PVa) else 0, LMS.zmax(0, DF, 0, WF) + 1)
note("volume height", HMAX, "voxels above base", BASE)
# debug: top-down colour of the highest voxel (no trees), shaded by height
lut = np.array([e[:3] for e in pal.entries], np.uint8)
topc = np.where(bmask, rc, np.where(deck, dsurf, gcol1))
zt = np.where(bmask, bz1, np.where(deck, dtop, g)).astype(np.float32)
img = np.clip(lut[topc] * np.clip(0.6 + zt[..., None] / 150, 0, 1.25), 0, 255).astype(np.uint8)
from PIL import Image
Image.fromarray(img[::2, ::2]).save(DBG / "topdown.png")
del img, topc, zt
leaf_ids = pal.ids({LEAF}) | {C["trunk"]} | {i for v in BARK_IDS.values() for i in v}
if os.environ.get("BENCH"):
    json.dump([list(e) for e in pal.entries], open(DBG / "palette.json", "w"))
    from osm import to_grid
    spots = {"parliament": (19.04563, 47.50709), "chain": (19.04248, 47.4988), "basilica": (19.054, 47.50079),
             "matthias": (19.03444, 47.5021), "statue": (19.04803, 47.48674), "heroes": (19.07829, 47.51522),
             "market": (19.05895, 47.4866), "city": (19.05597, 47.49457), "elisabeth": (19.04995, 47.49116),
             "liberty": (19.05492, 47.48573), "castle": (19.03955, 47.49583), "synagogue": (19.06075, 47.496),
             "varosliget": (19.084, 47.515), "puskas": (19.0981, 47.5031), "szell": (19.024, 47.507),
             "oktogon": (19.0650, 47.5052), "margit": (19.04346, 47.51474), "petofi": (19.06335, 47.4788)}  # lon, lat
    want = os.environ["BENCH"].split(",")
    at = {w_.split("@")[0]: tuple(map(float, w_.split("@")[1].split(":"))) for w_ in want if "@" in w_}  # name@x:y on the grid
    for name, (lon, lat) in list(spots.items()) + [(k, (None, None)) for k in at]:
        if name not in at and "1" not in want and name not in want:
            continue
        x, y = at[name] if name in at else to_grid(lon, lat)
        n = int(os.environ.get("BENCH_SIZE", 384))
        r, c = min(max(int(y * F) - n // 2, 0), DF - n), min(max(int(x * F) - n // 2, 0), WF - n)
        t = time.time()
        v = build(r, r + n, c, c + n)
        note(f"bench {name}: {n}^2 x {v.shape[0]} in {time.time() - t:.2f}s, {int((v > 0).sum())} voxels")
        np.save(DBG / f"bench_{name}.npy", v)
        # the foliage grid's cells over the window, to check against its leaves (cell (j0, i0) is the first)
        j0, i0 = r // 4, c // 4
        np.save(DBG / f"bench_{name}_foliage.npy", fol_cls[j0:(r + n - 1) // 4 + 1, i0:(c + n - 1) // 4 + 1])
        note(f"bench {name}: foliage grid: " + trees_mod.check(v, r, c, fol_cls, 0, 0, 4, trees_mod.leaf_lut(len(pal.entries))))
        json.dump(dict(r0=r, c0=c, F=F, base=BASE, palette=[list(e) for e in pal.entries], foliage=dict(cell=4, j0=j0, i0=i0),
                       leaf_class={int(i_): int(c_) for i_, c_ in trees_mod.LEAF_CLASS.items()}),
                  open(DBG / f"bench_{name}.json", "w"))
    import resource
    note(f"peak memory {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20:.1f} GB")
    raise SystemExit
if os.environ.get("NOTILES"):
    raise SystemExit
tile_info = tiles.export(build, g, F, WF, DF, HMAX, OUT / "tiles", note, keep_ids=pal.ids({LAMP}), skip_ids=leaf_ids,
                         low_ids=pal.ids({landmarks.WINDOW}))

# ---------------------------------------------------------------- labels and views
LANDMARK_KEYS = ("tourism", "historic", "amenity", "building", "man_made", "leisure", "place", "natural", "railway")
named = defaultdict(list)
for oid, kind, t, geom in osm.areas:
    if t.get("name") and (t.get("wikidata") or t.get("man_made") == "bridge"):
        named[t["name"]].append((geom, t))
for oid, t, p in osm.nodes:
    if t.get("name") and t.get("wikidata") and t.get("natural") in ("peak", "hill"):
        named[t["name"]].append((p.buffer(20), t))
labels = []
for name, items in named.items():
    geom = max(items, key=lambda x: x[0].area)[0]
    t = max(items, key=lambda x: x[0].area)[1]
    area = geom.area
    if area < 400 and t.get("man_made") != "bridge" and t.get("natural") not in ("peak", "hill"):
        continue
    p = geom.representative_point() if t.get("man_made") != "bridge" else geom.centroid
    x, y = int(np.clip(p.x, 0, W - 1)), int(np.clip(p.y, 0, D - 1))
    rr, cc = cells_of(geom)
    zt = int(max(bz1[rr, cc].max() if len(rr) else 0, dtop[rr, cc].max() if len(rr) else 0, g[y, x]))
    kind = t.get("tourism") or t.get("historic") or t.get("amenity") or t.get("man_made") or t.get("leisure") \
        or t.get("building") or t.get("place") or t.get("natural") or ""
    labels.append(dict(name=name, en=t.get("name:en"), kind=kind.replace("_", " "), x=x, y=y, z=zt + 3, g=int(g[y, x]),
                       far=int(min(4000, 400 + math.sqrt(area) * 18)), area=round(area)))
labels.sort(key=lambda l: -l["area"])
note("labels", len(labels))
EAST = np.array([math.cos(THETA), math.sin(THETA)])
NORTH = np.array([math.sin(THETA), -math.cos(THETA)])


def view(label, name, from_dir, dist, el, lift=0.4):
    l = next((l for l in labels if l["name"] == name), None)
    if l is None:
        return None
    tgt = np.array([l["x"] + 0.5, l["y"] + 0.5])
    h = l["z"] - l["g"]
    d = (from_dir[0] * EAST + from_dir[1] * NORTH)
    d /= np.linalg.norm(d)
    cam = tgt + d * dist * math.cos(el)
    ty = l["g"] + h * lift
    return dict(label=label, pos=[round(float(cam[0]), 1), round(ty + dist * math.sin(el), 1), round(float(cam[1]), 1)],
                target=[round(float(tgt[0]), 1), round(ty, 1), round(float(tgt[1]), 1)])


# overview: the Danube bend between the Parliament and Gellért Hill, from high over Pest to the south-east
lp = {l["name"]: l for l in labels}
mid = np.array([W / 2, D / 2])
if "Országház" in lp and "Szabadság híd" in lp:
    mid = (np.array([lp["Országház"]["x"], lp["Országház"]["y"]]) + np.array([lp["Szabadság híd"]["x"], lp["Szabadság híd"]["y"]])) / 2 \
        + 600 * EAST
d0 = 0.55 * EAST - 1.0 * NORTH
d0 /= np.linalg.norm(d0)
cam0 = mid + d0 * 2600 * math.cos(0.72)
views = {"overview": dict(label="Overview", pos=[round(float(cam0[0]), 1), round(2600 * math.sin(0.72), 1), round(float(cam0[1]), 1)],
                          target=[round(float(mid[0]), 1), 10.0, round(float(mid[1]), 1)])}
for key, args in {"parliament": ("Parliament", "Országház", (-1, 0.15), 520, 0.33),
                  "castle": ("Buda Castle", "Budavári Palota", (1, 0.15), 820, 0.2),
                  "chainbridge": ("Chain Bridge", "Széchenyi lánchíd", (0.5, -1), 330, 0.16),
                  "basilica": ("St Stephen's Basilica", "Szent István-bazilika", (-0.6, -1), 380, 0.42),
                  "gellert": ("Gellért Hill", "Gellért-hegy", (1, 0.35), 1300, 0.14),
                  "heroes": ("Heroes' Square", "Hősök tere", (-1, -0.25), 230, 0.3),
                  "fishermans": ("Fisherman's Bastion", "Halászbástya", (1, 0.1), 360, 0.3),
                  "matthias": ("Matthias Church", "Budavári Nagyboldogasszony-templom", (0.6, -1), 240, 0.35),
                  "liberty": ("Liberty Bridge", "Szabadság híd", (-0.3, -1), 420, 0.25),
                  "elisabeth": ("Elisabeth Bridge", "Erzsébet híd", (-0.4, 1), 480, 0.22),
                  "market": ("Great Market Hall", "Központi Vásárcsarnok", (-1, -0.5), 300, 0.35),
                  "rakoczi": ("Rákóczi Market Hall", "Rákóczi téri Vásárcsarnok", (-0.94, -0.34), 170, 0.33),
                  "synagogue": ("Dohány Street Synagogue", "Dohány utcai zsinagóga", (0.2, -1), 220, 0.35),
                  "varosliget": ("Városliget", "Városliget", (-0.7, -0.7), 1100, 0.45),
                  "szechenyi": ("Széchenyi Baths", "Széchenyi Gyógyfürdő és Uszoda", (-0.8, 0.5), 300, 0.4),
                  "puskas": ("Puskás Aréna", "Puskás Aréna", (-1, 0.3), 520, 0.3),
                  "szell": ("Széll Kálmán tér", "Széll Kálmán tér", (-0.6, 0.8), 320, 0.38),
                  "margaret": ("Margaret Bridge", "Margit híd", (-0.35, -1), 560, 0.16),
                  "petofi": ("Petőfi Bridge", "Petőfi híd", (0.25, -1), 430, 0.13),
                  "opera": ("Hungarian State Opera", "Magyar Állami Operaház", (0.55, -1), 210, 0.22),
                  "erkel": ("Erkel Theatre", "Erkel Színház", (-0.35, 0.94), 50, 0.1),
                  "keleti": ("Keleti Station", "Keleti pályaudvar", (-1, 0.35), 290, 0.22),
                  "nyugati": ("Nyugati Station", "Nyugati pályaudvar", (-1, -0.15), 250, 0.2),
                  "ethnography": ("Museum of Ethnography", "Néprajzi Múzeum", (1, 0.25), 330, 0.28),
                  "balna": ("Bálna", "Bálna Honvédelmi Központ", (-0.7, -1), 280, 0.25),
                  "zoo": ("Zoo", "Elefántház", (0.2, -1), 330, 0.35),
                  "eye": ("Budapest Eye", "Budapest Óriáskereke", (0.85, 0.5), 230, 0.3),  # face on
                  "gellerthotel": ("Gellért Hotel and Baths", "Hotel Gellért", (0.97, 0.22), 300, 0.18),
                  "bme": ("BME Building K", "K épület", (0.75, 0.66), 380, 0.17),
                  "museum": ("Hungarian National Museum", "Magyar Nemzeti Múzeum", (-0.98, -0.17), 230, 0.22),
                  "a38": ("A38 Ship", "A38 Hajó", (0.3, -1), 200, 0.25)}.items():
    v = view(*args)
    if v:
        views[key] = v
nep = next((g_ for oid, k, t, g_ in osm.areas if oid == 13957874), None)
if nep is not None and "ethnography" in views:  # two wings: aim between them, at the gate they frame
    c_ = np.array(nep.centroid.coords[0])
    v_ = views["ethnography"]
    off = np.array(v_["pos"]) - np.array(v_["target"])
    v_["target"] = [round(float(c_[0]), 1), v_["target"][1], round(float(c_[1]), 1)]
    v_["pos"] = [round(float(c_[0] + off[0]), 1), v_["pos"][1], round(float(c_[1] + off[2]), 1)]
fv_ = landmarks_erkel.front_view(osm)
if fv_ is not None and "erkel" in views:  # the curved front from over the street west of its axis (houses 32 m out)
    (fx_, fy_), (nx_, ny_) = fv_
    zg_ = float(g[int(fy_), int(fx_)])
    cx_, cy_ = fx_ + nx_ * 50 + ny_ * 18, fy_ + ny_ * 50 - nx_ * 18
    views["erkel"].update(pos=[round(cx_, 1), round(zg_ + 13, 1), round(cy_, 1)],
                          target=[round(fx_ - nx_ * 6, 1), round(zg_ + 10, 1), round(fy_ - ny_ * 6, 1)])
cor = next((g_ for oid, k, t, g_ in osm.areas if oid == 261801166), None)
eur = next((g_ for oid, k, t, g_ in osm.areas if oid == 308551954), None)
if cor is not None and eur is not None:  # Blaha Lujza tér: the Corvin Palace and the Europeum side by side, from the north
    cw, ce = np.array(cor.exterior.coords)[:-1], np.array(eur.exterior.coords)[:-1]
    mid = 0.45 * cw[np.argmax(cw @ (NORTH - EAST))] + 0.55 * ce[np.argmax(ce @ (NORTH + EAST))]  # east of the middle
    d = (NORTH + 0.3 * EAST) / np.linalg.norm(NORTH + 0.3 * EAST)
    zg = float(g[int(mid[1]), int(mid[0])])
    cam = mid + d * 118
    views["blaha"] = dict(label="Blaha Lujza tér", pos=[round(float(cam[0]), 1), round(zg + 24, 1), round(float(cam[1]), 1)],
                          target=[round(float(mid[0]), 1), round(zg + 9, 1), round(float(mid[1]), 1)])
st = next((p for oid, t, p in osm.nodes if t.get("wikidata") == "Q933182"), None)
if st is not None:  # the Liberty Statue is a node, without a label of its own
    zg = float(g[int(st.y), int(st.x)])  # from below, against the sky, as it is seen from the hillside
    d = 0.75 * EAST + 0.65 * NORTH
    d /= np.linalg.norm(d)
    cam = np.array([st.x, st.y]) + d * 70
    views["statue"] = dict(label="Liberty Statue", pos=[round(float(cam[0]), 1), round(zg + 8, 1), round(float(cam[1]), 1)],
                           target=[round(float(st.x), 1), round(zg + 27, 1), round(float(st.y), 1)])
cit_ = next((g_ for oid, k, t, g_ in osm.areas if oid == landmarks_citadella.FORT), None)
if cit_ is not None:  # the Citadella from over the Danube to the north-east: the walls, the park and the flag
    c_ = np.array(cit_.centroid.coords[0])
    zc_ = float(g[int(c_[1]), int(c_[0])])
    d_ = 0.55 * EAST + 0.85 * NORTH
    d_ /= np.linalg.norm(d_)
    cam = c_ + d_ * 230
    views["citadella"] = dict(label="Citadella", pos=[round(float(cam[0]), 1), round(zc_ + 95, 1), round(float(cam[1]), 1)],
                              target=[round(float(c_[0]), 1), round(zc_ + 12, 1), round(float(c_[1]), 1)])
pyl = [g_ for oid, k, t, g_ in osm.areas if oid in (197110387, 197110388)]
if len(pyl) == 2 and "Széchenyi lánchíd" in lp:  # along the Chain Bridge from Pest: its arches, the Castle behind
    pa, pb = sorted((np.array(p_.centroid.coords[0]) for p_ in pyl), key=lambda c: c[0])
    ax = (pb - pa) / np.linalg.norm(pb - pa)
    zd = lp["Széchenyi lánchíd"]["g"] + 6
    cam = pb + ax * 150
    views["chainarch"] = dict(label="Chain Bridge from Pest", pos=[round(float(cam[0]), 1), round(zd + 22, 1), round(float(cam[1]), 1)],
                              target=[round(float(pa[0]), 1), round(zd + 18, 1), round(float(pa[1]), 1)])
spawn_ = None
flag_ = next((p for oid, t, p in osm.nodes if t.get("man_made") == "flagpole" and t.get("name") == "Magyar Nemzeti Zászló"), None)
dome_ = next((g_ for oid, k, t, g_ in osm.areas if oid == 237397586), None)
if flag_ is not None and dome_ is not None:  # Kossuth tér: from over the flag, the main entrance and the dome
    fp, dp = np.array([flag_.x, flag_.y]), np.array(dome_.centroid.coords[0])
    ax_ = (fp - dp) / np.linalg.norm(fp - dp)
    zf_ = float(g[int(flag_.y), int(flag_.x)])
    cam = fp + ax_ * 45
    tg = dp + ax_ * 60
    views["kossuth"] = dict(label="Kossuth tér", pos=[round(float(cam[0]), 1), round(zf_ + 30, 1), round(float(cam[1]), 1)],
                            target=[round(float(tg[0]), 1), round(zf_ + 14, 1), round(float(tg[1]), 1)])
    # where the Minecraft server's new players start: on the square by the flag, a step aside so the mast doesn't hide
    # the dome, facing the Parliament
    sp_ = fp + ax_ * 7.0 + np.array([-ax_[1], ax_[0]]) * 3.0
    spawn_ = dict(name="Kossuth tér, by the flag", name_hu="Kossuth tér, a zászlónál", x=round(float(sp_[0]), 1),
                  z=round(float(sp_[1]), 1), g=round(float(g[int(sp_[1]), int(sp_[0])]), 1),
                  heading=round(math.atan2(dp[1] - sp_[1], dp[0] - sp_[0]), 4))
hil = next((g_ for oid, k, t, g_ in osm.areas if oid == 5647453), None)
if hil is not None:  # the Hilton from over the roofs across Hess András tér: its Baroque front, the tower on the left
    import landmarks_hilton
    fh = landmarks_hilton.front(hil, THETA)
    cam, tg = fh.xy(20.0, -40.0), fh.xy(62.0, 6.0)
    zh = float(g[int(fh.xy(50.0, -4.0)[1]), int(fh.xy(50.0, -4.0)[0])])
    views["hilton"] = dict(label="Hilton Budapest", pos=[round(cam[0], 1), round(zh + 26, 1), round(cam[1], 1)],
                           target=[round(tg[0], 1), round(zh + 13, 1), round(tg[1], 1)])
we_ = next((g_ for oid, k, t, g_ in osm.areas if oid == landmarks_westend.MALL), None)
if we_ is not None:  # WestEnd City Center: its entrance on Nyugati tér under the tilted glass canopy, from the square
    views["westend"] = landmarks_westend.view(we_, g)
promo = None
sq = sidequest.find(osm)
if sq is not None:  # SideQuest Bar, who made this map: a pin over its building for the viewer, a view of its front
    t, p = sq
    x, y = int(p.x), int(p.y)
    bld = sidequest.building_of(osm, p)
    rr, cc = cells_of(bld) if bld is not None else (np.array([y]), np.array([x]))
    zt = float(max(bz1[rr, cc].max() if len(rr) else 0, dtop[rr, cc].max() if len(rr) else 0, g[y, x]))
    dp_, dh_ = sidequest.door(osm, t, p)
    promo = dict(name=sidequest.NAME, x=round(p.x, 1), y=round(p.y, 1), z=round(zt + 2, 1), g=round(float(g[y, x]), 1),
                 door=dp_, heading=dh_)
    views["sidequest"] = sidequest.street_view(osm, t, p, float(g[y, x]), zt)
if landmarks_sidequest.INSIDE:  # its interior: a view along the room, and its light on the floor at night
    views["sidequest_inside"] = landmarks_sidequest.INSIDE["view"]
    lamps += landmarks_sidequest.INSIDE["lamps"]
VIEW_HU = {"overview": "Áttekintés", "parliament": "Országház", "kossuth": "Kossuth tér", "castle": "Budavári Palota", "chainbridge": "Széchenyi lánchíd",
           "chainarch": "A Lánchíd Pest felől", "basilica": "Szent István-bazilika", "gellert": "Gellért-hegy",
           "heroes": "Hősök tere", "fishermans": "Halászbástya", "matthias": "Mátyás-templom", "liberty": "Szabadság híd",
           "elisabeth": "Erzsébet híd", "market": "Központi Vásárcsarnok", "rakoczi": "Rákóczi téri vásárcsarnok",
           "synagogue": "Dohány utcai zsinagóga",
           "varosliget": "Városliget", "szechenyi": "Széchenyi fürdő", "puskas": "Puskás Aréna", "szell": "Széll Kálmán tér",
           "margaret": "Margit híd", "petofi": "Petőfi híd", "opera": "Magyar Állami Operaház", "keleti": "Keleti pályaudvar",
           "nyugati": "Nyugati pályaudvar", "ethnography": "Néprajzi Múzeum", "balna": "Bálna", "zoo": "Állatkert",
           "eye": "Budapest Óriáskerék", "statue": "Szabadság-szobor", "citadella": "Citadella", "sidequest": "SideQuest Bar",
           "sidequest_inside": "A SideQuest Bar belülről",
           "gellerthotel": "Gellért Szálló és fürdő", "bme": "BME K épület", "museum": "Magyar Nemzeti Múzeum",
           "a38": "A38 hajó", "hilton": "Hilton Budapest", "erkel": "Erkel Színház", "blaha": "Blaha Lujza tér",
           "westend": "WestEnd City Center"}
for k_, v_ in views.items():
    v_["label_hu"] = VIEW_HU.get(k_, v_["label"])
note("views:", list(views))

lon, lat = EOV_TO_WGS.transform(CX, CY)
meta = dict(W=WF, D=DF, H=HMAX, vox=VOX, base=BASE, water=round(WL - BASE, 2), tiles=tile_info, center=[CX, CY], center_wgs=[lon, lat],
            theta_deg=math.degrees(THETA), crs="EPSG:23700", palette=[list(e) for e in pal.entries], lamps=lamps,
            labels=labels[:400], views=views, sidequest=promo, spawn=spawn_,
            sources=dict(osm=osm.timestamp, dem="Copernicus DEM GLO-30 (ESA, 2011-2015)",
                         heights="GlobalBuildingAtlas GBA.Height (TUM, CC BY-NC 4.0); Átló / Copernicus Urban Atlas BH 2012"))
# the foliage grid for the viewer's seasons: per 2 m cell the class of the tree whose crown is there, then that tree's byte
import gzip
(OUT / "foliage.bin").write_bytes(gzip.compress(fol_cls.tobytes() + fol_uid.tobytes(), 9, mtime=0))
meta["foliage"] = dict(cell=2, cols=FOL_COLS, rows=FOL_ROWS)
json.dump(meta, open(OUT / "meta.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump(report, open(DBG / "report.json", "w"), indent=1, ensure_ascii=False, default=str)

note("done")
