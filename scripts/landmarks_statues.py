"""Statues, busts and sculptures from OSM's nodes, and windows on the churches nobody rebuilt by hand; both ideas from
warsaw-vibe-voxel (MIT, © 2026 Piotr Migdał), drawn here with this map's own solids.

Every statue, bust and sculpture OSM maps (tourism=artwork, historic=memorial) stands on a pedestal facing the nearest
path or street, in bronze or stone as its material tag says. The best known ones (MONUMENTS) are drawn from their
photos: their kind of figure, pedestal, colours, size and which way they face. A church's walls are the plain classic
material (no grid of office storeys), so a church left to OSM stood as a blank block: it gets tall round-headed
windows on every straight wall, a second row under the eaves when it is tall.
"""
import math

import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Point

from landmarks import WINDOW, Box, Capsule, Ellipsoid, Frame, Lathe, cone, cyl, grid_angle, rect_of
from landmarks_city import windows
from landmarks_kossuth import horseman, pedestal
from style import CLASSIC, METAL, parse_len, stable_hash

NAMES = ["Statues", "Church windows"]
RELIGIOUS = {"church", "cathedral", "chapel", "synagogue", "basilica", "mosque", "temple", "shrine"}

# drawn elsewhere: the Liberty Statue, the Kossuth tér memorials, Heroes' Square's figures
SKIP = {1488974596, 2723191611, 2723191620, 4594797273, 1656099920, 1656099972, 1656099994, 1656100010, 1656100042,
        276521334}  # (and the Little Princess, 50 cm on the embankment's railing)

BRONZE, DARK_BRONZE, PATINA = "#4d473d", "#3f3a33", "#5c7d6c"
GRANITE, PALE, MARBLE, LIMESTONE = "#8e8b85", "#cfc8b8", "#ebe7dc", "#ddd4c0"

# the best known, from their photos. kind: stand, raise (an arm up), seat, bust, ride; s: the figure's scale (1 is a
# 2.4 m standing figure); ped: the pedestal (along, across, height); face: "river" (to the Danube), "city" (away from
# it), a compass bearing, or the nearest way when left out
MONUMENTS = {
    2315294665: dict(name="Savoyai Jenő", kind="ride", s=1.4, ped=(6.4, 3.0, 5.4), ped_col=PALE, col=PATINA,
                     face="river", relief=True),
    1443594776: dict(name="Szent István", kind="ride", s=1.35, ped=(5.6, 2.8, 5.6), ped_col=MARBLE, col=DARK_BRONZE,
                     face="river", steps=True, cross=True),
    5124319122: dict(name="Hadik András", kind="ride", s=1.15, ped=(4.6, 2.2, 3.4), ped_col=PALE, col=DARK_BRONZE),
    735289674: dict(name="Sárkányölő Szent György", kind="ride", s=0.9, ped=(3.0, 1.6, 2.0), ped_col=PALE, col=BRONZE),
    260515005: dict(name="Széchenyi István", kind="stand", s=1.5, ped=(2.6, 2.6, 6.0), ped_col=GRANITE, col=DARK_BRONZE,
                    face="river", corners=True),
    260515002: dict(name="Deák Ferenc", kind="seat", s=1.6, ped=(3.4, 2.8, 4.8), ped_col=GRANITE, col=DARK_BRONZE,
                    face="river", corners=True),
    738771463: dict(name="Petőfi Sándor", kind="raise", s=1.45, ped=(2.6, 2.6, 4.0), ped_col=PALE, col=DARK_BRONZE,
                    face="city"),
    721163918: dict(name="Erzsébet királyné", kind="seat", s=1.35, ped=(2.4, 2.0, 2.8), ped_col=LIMESTONE, col=BRONZE,
                    face="river"),
    3465156641: dict(name="Anonymus", kind="seat", s=1.5, ped=(2.6, 2.4, 2.2), ped_col=PALE, col=DARK_BRONZE, hood=True),
    735732939: dict(name="Bem apó", kind="raise", s=1.3, ped=(2.4, 2.4, 3.6), ped_col=GRANITE, col=DARK_BRONZE),
    260536706: dict(name="József nádor", kind="stand", s=1.35, ped=(2.4, 2.4, 4.2), ped_col=PALE, col=DARK_BRONZE),
    260536704: dict(name="Eötvös József", kind="stand", s=1.3, ped=(2.2, 2.2, 3.4), ped_col=GRANITE, col=DARK_BRONZE),
    3152351861: dict(name="Ady Endre", kind="stand", s=1.3, ped=(1.8, 1.8, 2.2), ped_col=GRANITE, col=BRONZE),
    2993772204: dict(name="Semmelweis Ignác", kind="stand", s=1.25, ped=(2.0, 2.0, 3.0), ped_col=PALE, col=MARBLE),
    1903603572: dict(name="Baross Gábor", kind="stand", s=1.4, ped=(2.4, 2.4, 4.2), ped_col=GRANITE, col=DARK_BRONZE),
    3784548557: dict(name="Liszt Ferenc", kind="seat", s=1.25, ped=(2.2, 2.0, 2.6), ped_col=PALE, col=BRONZE),
    4595488548: dict(name="Liszt Ferenc", kind="seat", s=1.2, ped=(1.6, 1.4, 0.5), ped_col=GRANITE, col=BRONZE),
    2409211796: dict(name="Ronald Reagan", kind="stand", s=1.0, ped=None, col=BRONZE),
    6550184285: dict(name="Nagy Imre", kind="stand", s=1.0, ped=None, col=DARK_BRONZE),
    2759480062: dict(name="Columbo", kind="stand", s=0.85, ped=None, col=BRONZE),
    5333696374: dict(name="Bud Spencer", kind="stand", s=1.05, ped=None, col=BRONZE),
}
GELLERT, TURUL, VOROSMARTY = 1488905310, 2091172445, 1462072965


def material_col(t):
    m = (t.get("material") or "").lower()
    if "bronze" in m or "metal" in m or "copper" in m or "iron" in m or "steel" in m:
        return BRONZE, METAL
    if any(k in m for k in ("marble", "limestone", "stone", "sandstone", "granite", "concrete")):
        return (MARBLE if "marble" in m else LIMESTONE), CLASSIC
    return BRONZE, METAL


# ------------------------------------------------------------------------------------------------ figures
def head(S, fr, w, s, col, hood=False):
    r = max(0.26, 0.17 * s)
    S.add(Ellipsoid(fr.at(0, 0, w), r * (1.25 if hood else 1), r * (1.2 if hood else 1), r * (1.35 if hood else 1.2), col))


def stand(S, fr, w0, s, col, arm=False):
    """a standing figure facing +u, 2.4 s m: coat, shoulders, head, an arm raised to the front if arm."""
    S.add(Lathe(fr, w0, w0 + 1.55 * s, cone(max(0.42 * s, 0.4), max(0.3 * s, 0.3)), col))
    S.add(Ellipsoid(fr.at(0, 0, w0 + 1.75 * s), max(0.27 * s, 0.28), max(0.36 * s, 0.34), max(0.33 * s, 0.3), col))
    head(S, fr, w0 + 2.2 * s, s, col)
    if arm:
        S.add(Capsule(fr, (0, -0.3 * s, w0 + 1.85 * s), (0.45 * s, -0.42 * s, w0 + 2.6 * s), max(0.11 * s, 0.14), col))


def seat(S, fr, w0, s, col, chair, hood=False):
    """a seated figure facing +u on a chair of the pedestal's stone, 1.9 s m to the top of the head."""
    S.add(Box(fr, -0.55 * s, 0.25 * s, -0.5 * s, 0.5 * s, w0, w0 + 0.55 * s, chair))
    S.add(Box(fr, -0.6 * s, -0.4 * s, -0.5 * s, 0.5 * s, w0 + 0.55 * s, w0 + 1.3 * s, chair))
    S.add(Box(fr, -0.15 * s, 0.6 * s, -0.36 * s, 0.36 * s, w0 + 0.5 * s, w0 + 0.8 * s, col))
    S.add(Box(fr, 0.38 * s, 0.62 * s, -0.36 * s, 0.36 * s, w0, w0 + 0.6 * s, col))
    S.add(Ellipsoid(fr.at(-0.15 * s, 0, w0 + 1.2 * s), max(0.25 * s, 0.28), max(0.36 * s, 0.34), max(0.48 * s, 0.4), col))
    head(S, fr.at(-0.1 * s), w0 + 1.78 * s, s, col, hood)


def bust(S, fr, w0, col):
    S.add(Ellipsoid(fr.at(0, 0, w0 + 0.2), 0.3, 0.45, 0.3, col))
    head(S, fr, w0 + 0.65, 1.3, col)


def sculpture(S, fr, w0, col, h=2.0):
    S.add(Capsule(fr, (0, 0, w0 + 0.3), (0, 0, w0 + h - 0.4), 0.45, col))
    S.add(Ellipsoid(fr.at(0, 0, w0 + h * 0.6), 0.55, 0.45, 0.6, col))


# ------------------------------------------------------------------------------------------------ facing
def river_dir(ctx, x, y):
    """the grid angle from (x, y) to the nearest Danube cell, searched along 72 rays out to 1.5 km."""
    river, W, D = ctx["river"], ctx["W"], ctx["D"]
    best = (1e9, 0.0)
    for a in np.linspace(0, 2 * math.pi, 72, endpoint=False):
        for r in range(5, 1500, 8):
            c, rr = int(x + r * math.cos(a)), int(y + r * math.sin(a))
            if not (0 <= c < W and 0 <= rr < D):
                break
            if river[rr, c]:
                if r < best[0]:
                    best = (r, a)
                break
    return best[1]


def facing(ctx, spec, x, y, ways, wtree):
    f = spec.get("face")
    if f in ("river", "city"):
        return river_dir(ctx, x, y) + (math.pi if f == "city" else 0.0)
    if isinstance(f, (int, float)):
        return grid_angle(f, ctx["theta"])
    p = Point(x, y)
    k = wtree.query_nearest(p, max_distance=40)
    if len(k):
        q = shapely.ops.nearest_points(p, ways[int(k[0])])[1]
        if q.distance(p) > 0.3:
            return math.atan2(q.y - y, q.x - x)
    return river_dir(ctx, x, y)


# ------------------------------------------------------------------------------------------------ builders
def gellert(S, ctx, x, y, P):
    """Szent Gellért (Gyula Jankovits, 1904) over Elisabeth Bridge: the bishop in bronze raising his cross, on a
    pedestal before a semicircular colonnade, a waterfall below him down the hillside."""
    g_at = ctx["ground_m"]
    g = g_at(x, y)
    ang = river_dir(ctx, x, y)
    fr = Frame(x, y, g, ang)
    stone, bronze, water = P(LIMESTONE), P(DARK_BRONZE, METAL), ctx["C"]["pool"]
    S.clear += [(*fr.xy(-1.0, 0), 11.0)] + [(*fr.xy(3.0 + k, 0), 3.0) for k in range(0, 34, 4)]
    S.add(Box(fr, -9.5, 3.0, -9.0, 9.0, -1.5, 0.6, stone))
    for k in range(9):  # the colonnade, a half ring opening towards the river
        a = math.pi / 2 + math.pi * k / 8
        S.add(Lathe(fr.at(-1.0 + 7.5 * math.cos(a), 7.5 * math.sin(a)), 0.6, 8.6, cyl(0.45), stone))
    for k in range(24):
        a = math.pi / 2 + math.pi * k / 23
        S.add(Box(fr.at(-1.0 + 7.5 * math.cos(a), 7.5 * math.sin(a), 0, a), -0.7, 0.7, -0.75, 0.75, 8.6, 9.8, stone))
    pedestal(S, fr, 0.4, 2.4, 2.4, 4.4, stone)
    stand(S, fr, 4.8, 2.4, bronze)
    S.add(Capsule(fr, (0.2, -0.75, 7.5), (0.9, -0.95, 12.6), 0.16, bronze))  # the cross held high
    S.add(Capsule(fr, (0.8, -1.9, 11.4), (0.8, 0.0, 11.4), 0.16, bronze))
    for k in range(34):  # the waterfall: a channel of water down the slope in front
        xw, yw = fr.xy(2.0 + k, 0)
        gw = g_at(xw, yw)
        S.add(Box(Frame(xw, yw, gw, ang), -0.6, 0.6, -1.6, 1.6, -0.8, 0.15, water))
        S.add(Box(Frame(xw, yw, gw, ang), -0.6, 0.6, -2.2, -1.6, -0.8, 0.6, stone))
        S.add(Box(Frame(xw, yw, gw, ang), -0.6, 0.6, 1.6, 2.2, -0.8, 0.6, stone))


def turul(S, ctx, x, y, P):
    """the Turul (Gyula Donáth, 1905) over the gate to the palace by the funicular: a bronze bird with its wings
    spread and a sword in its claws, on a stone pillar."""
    g = ctx["ground_m"](x, y)
    fr = Frame(x, y, g, river_dir(ctx, x, y))
    S.clear.append((x, y, 5.0))
    stone, bronze = P(PALE), P(DARK_BRONZE, METAL)
    S.add(Box(fr, -1.1, 1.1, -1.1, 1.1, -0.5, 5.6, stone))
    S.add(Box(fr, -1.4, 1.4, -1.4, 1.4, 5.6, 6.2, stone))
    S.add(Ellipsoid(fr.at(0.1, 0, 7.3), 0.8, 0.65, 1.1, bronze))
    S.add(Capsule(fr, (0.3, 0, 8.2), (0.75, 0, 8.9), 0.32, bronze))
    S.add(Capsule(fr, (0.75, 0, 8.9), (1.25, 0, 8.6), 0.18, bronze))
    S.add(Capsule(fr, (-0.6, 0, 6.8), (-1.6, 0, 6.3), 0.3, bronze))
    for sv in (-1, 1):
        for k in range(5):  # each wing raised and swept back, its tips highest
            t = (k + 1) / 5
            S.add(Capsule(fr, (-0.1 - 0.3 * t, sv * (0.5 + 3.0 * (t - 0.2)), 7.5 + 1.6 * t),
                          (-0.6 - 0.5 * t, sv * (0.5 + 3.0 * t), 7.9 + 2.2 * t), 0.22, bronze))
    S.add(Capsule(fr, (0.7, 0, 6.3), (0.7, 0, 4.4), 0.12, P("#b9b3a5", METAL)))  # the sword


def vorosmarty(S, ctx, g_, P):
    """Mihály Vörösmarty (Ede Kallós and Ede Telcs, 1908): the poet seated in white marble over the people of the
    Szózat, a crowd of some twenty figures round the foot of the pedestal."""
    x, y = g_.centroid.x, g_.centroid.y
    g = ctx["ground_m"](x, y)
    fr = Frame(x, y, g, grid_angle(185, ctx["theta"]))
    S.clear.append((x, y, 5.0))
    marble = P(MARBLE)
    S.add(Box(fr, -3.6, 3.6, -3.6, 3.6, -0.6, 0.5, P(PALE)))
    S.add(Box(fr, -3.0, 3.0, -3.0, 3.0, 0.5, 1.0, marble))
    S.add(Box(fr, -1.4, 1.4, -1.4, 1.4, 1.0, 4.0, marble))
    for k in range(16):
        a = 2 * math.pi * k / 16
        fa = fr.at(2.2 * math.cos(a), 2.2 * math.sin(a), 0, a)
        h = 1.9 + 0.6 * ((k * 5) % 3) / 2
        S.add(Ellipsoid(fa.at(0, 0, 1.0 + h / 2), 0.4, 0.45, h / 2, marble))
        S.add(Ellipsoid(fa.at(0, 0, 1.15 + h), 0.27, 0.27, 0.3, marble))
    seat(S, fr, 4.0, 1.4, marble, marble)


def church_windows(S, ctx, plan):
    """round-headed windows on every church a landmark doesn't already window or paint."""
    P, feats = ctx["P"], ctx["feats"]
    win = P("#34363c", WINDOW)
    painted = [(p.bb, set(int(c) for c in p.targets)) for p in S.prims if p.mode == "paint" and p.targets is not None]
    outl = [f for f in feats.values() if not f["part"]]
    otree = shapely.STRtree([f["geom"] for f in outl])
    hosts = set()
    for i, f in enumerate(outl):
        if f["type"] in RELIGIOUS or f["t"].get("amenity") == "place_of_worship":
            hosts.add(i)
    todo = [outl[i] for i in hosts]
    for f in feats.values():
        if f["part"] and any(j in hosts for j in otree.query(f["geom"].centroid, predicate="within")):
            todo.append(f)
    F = ctx["F"]
    n = nb = 0
    for f in todo:
        g = f["geom"]
        if g.geom_type != "Polygon" or g.area < 30:
            continue
        E = f["E"] - f.get("minh", 0.0)
        if E < 9:
            continue
        x0, y0, x1, y1 = (v * F for v in g.bounds)
        if any(int(f["wall"]) in tg and bb[0] < x1 and bb[1] > x0 and bb[2] < y1 and bb[3] > y0 for bb, tg in painted):
            continue
        b0 = f["base"] + f.get("minh", 0.0)
        rows = [(3.0, min(10.0, E - 2.0))] + ([(E - 7.0, E - 3.0)] if E >= 20 else [])
        k0 = len(S.prims)
        windows(S, g.simplify(0.8), b0, rows, [f["wall"]], win, every=4.5, half=0.85, min_len=6.0)
        nb += len(S.prims) > k0
        n += len(S.prims) - k0
    ctx["note"](f"    church windows: {n} on {nb} churches and their parts")


def statues(S, ctx, plan):
    P, osm, g_at = ctx["P"], ctx["osm"], ctx["ground_m"]
    W, D = ctx["W"], ctx["D"]
    bld = [f["geom"] for f in ctx["feats"].values() if not f["part"]]
    btree = shapely.STRtree(bld)
    ways = [ln for oid, t, ln in osm.lines if t.get("highway") and t.get("highway") not in ("steps", "corridor")
            and t.get("tunnel") in (None, "no") and not t.get("layer", "0").startswith("-")]
    wtree = shapely.STRtree(ways)
    F = ctx["F"]
    small = [p.bb for p in S.prims if p.mode in ("fill", "under") and (p.bb[1] - p.bb[0]) < 40 * F and (p.bb[3] - p.bb[2]) < 40 * F]
    sb = np.array(small, np.int64).reshape(-1, 6)

    def modelled(x, y):  # a landmark already stands there (Heroes' Square's figures, the Kossuth tér memorials)
        X, Y = x * F, y * F
        m = 3 * F
        return bool(((sb[:, 0] - m < X) & (sb[:, 1] + m > X) & (sb[:, 2] - m < Y) & (sb[:, 3] + m > Y)).any())

    items = []
    for oid, t, p in osm.nodes:
        items.append((oid, t, p, None))
    for oid, kind, t, g in osm.areas:
        if "building" not in t and "building:part" not in t and (t.get("tourism") == "artwork" or t.get("historic") in
                                                                  ("memorial", "monument")) and g.area < 150:
            items.append((oid, t, g.centroid, g))
    counts = {}
    for oid, t, p, g in items:
        at = t.get("artwork_type") if t.get("tourism") == "artwork" else t.get("memorial") \
            if t.get("historic") in ("memorial", "monument") else None
        if oid in SKIP or (at not in ("statue", "bust", "sculpture") and oid not in MONUMENTS and oid not in (GELLERT, TURUL, VOROSMARTY)):
            continue
        if t.get("indoor") == "yes" or (t.get("level") or "0").lstrip("-").split(";")[0] not in ("0", "") or \
                (t.get("level") or "0").startswith("-"):
            continue
        x, y = p.x, p.y
        if not (20 <= x < W - 20 and 20 <= y < D - 20) or ctx["river"][int(y), int(x)]:
            continue
        if g is None and any(bld[k].buffer(0.8).contains(p) for k in btree.query(p.buffer(1.0))):
            continue  # on a facade, in a niche, inside
        if modelled(x, y) and oid not in MONUMENTS:
            continue
        if oid == GELLERT:
            gellert(S, ctx, x, y, P)
            counts["custom"] = counts.get("custom", 0) + 1
            continue
        if oid == TURUL:
            turul(S, ctx, x, y, P)
            counts["custom"] = counts.get("custom", 0) + 1
            continue
        if oid == VOROSMARTY and g is not None:
            vorosmarty(S, ctx, g, P)
            counts["custom"] = counts.get("custom", 0) + 1
            continue
        spec = MONUMENTS.get(oid)
        h_ = stable_hash(oid)
        if spec is None:
            hcol, hmat = material_col(t)
            ped_col = GRANITE if h_ % 3 else PALE
            if at == "bust":
                spec = dict(kind="bust", ped=(0.8, 0.8, 1.6), ped_col=ped_col, col=hcol, mat=hmat)
            elif at == "sculpture":
                spec = dict(kind="sculpture", ped=(1.6, 1.6, 0.6), ped_col=ped_col, col=hcol, mat=hmat)
            else:
                spec = dict(kind="ride" if "lovas" in (t.get("name") or "").lower() else "stand", s=1.15,
                            ped=(1.6, 1.6, 2.2), ped_col=ped_col, col=hcol, mat=hmat)
            ht = parse_len(t.get("height"))
            if ht and 1 < ht < 12 and spec["kind"] in ("stand", "ride"):
                spec["s"] = max(0.8, min(1.8, ht / 4.6))
        z = g_at(x, y)
        ang = facing(ctx, spec, x, y, ways, wtree)
        S.clear.append((x, y, 4.0 if oid in MONUMENTS else 1.5))
        fr = Frame(x, y, z, ang)
        col = P(spec["col"], spec.get("mat", CLASSIC if spec["col"] in (MARBLE, LIMESTONE) else METAL))
        top = 0.0
        if spec.get("ped"):
            lu, lv, ph = spec["ped"]
            if g is not None and spec["kind"] != "bust":
                _, _, a_, b_, _ = rect_of(g)
                lu, lv = max(lu, min(a_, 8.0) - 0.8), max(lv, min(b_, 8.0) - 0.8)
            pc = P(spec["ped_col"])
            if spec.get("steps"):
                S.add(Box(fr, -lu / 2 - 1.6, lu / 2 + 1.6, -lv / 2 - 1.6, lv / 2 + 1.6, -0.6, 0.4, pc))
                S.add(Box(fr, -lu / 2 - 1.0, lu / 2 + 1.0, -lv / 2 - 1.0, lv / 2 + 1.0, 0.4, 0.8, pc))
                pedestal(S, fr, 0.8, lu, lv, ph - 0.8, pc)
            elif spec["kind"] == "bust":
                S.add(Box(fr, -lu / 2, lu / 2, -lv / 2, lv / 2, -0.5, ph, pc))
            else:
                pedestal(S, fr, -0.3, lu, lv, ph + 0.3, pc)
            if spec.get("relief"):  # a bronze band of reliefs round the pedestal
                S.add(Box(fr, -lu / 2 - 0.05, lu / 2 + 0.05, -lv / 2 - 0.05, lv / 2 + 0.05, ph * 0.35, ph * 0.65,
                          lambda u, v, w: np.where((np.mod(u * 2.1 + w * 1.3, 1.0) < 0.5), col, 0).astype(np.uint16),
                          mode="paint", targets=[pc]))
            if spec.get("corners"):  # seated allegories at the pedestal's corners
                for su in (-1, 1):
                    for sv in (-1, 1):
                        fc = fr.at(su * (lu / 2 + 0.7), sv * (lv / 2 + 0.7), 0, math.atan2(sv, su))
                        S.add(Box(fc, -0.6, 0.6, -0.6, 0.6, -0.3, 0.9, pc))
                        S.add(Ellipsoid(fc.at(0, 0, 1.6), 0.45, 0.45, 0.75, col))
                        S.add(Ellipsoid(fc.at(0, 0, 2.55), 0.27, 0.27, 0.3, col))
            top = ph
        kind, s = spec["kind"], spec.get("s", 1.0)
        if kind == "ride":
            horseman(S, fr, top, s, col, col)
            if spec.get("cross"):  # the apostolic double cross in the king's right hand
                S.add(Capsule(fr, (0.3 * s, -0.5 * s, top + 3.6 * s), (0.4 * s, -0.55 * s, top + 6.0 * s), 0.13, col))
                for hh, w_ in ((5.2, 0.5), (5.7, 0.35)):
                    S.add(Capsule(fr, (0.4 * s, -0.55 * s - w_, top + hh * s), (0.4 * s, -0.55 * s + w_, top + hh * s), 0.12, col))
        elif kind in ("stand", "raise"):
            stand(S, fr, top, s, col, arm=kind == "raise")
        elif kind == "seat":
            seat(S, fr, top, s, col, P(spec.get("ped_col", PALE)), hood=spec.get("hood", False))
        elif kind == "bust":
            bust(S, fr, top, col)
        else:
            sculpture(S, fr, top, col)
        counts[kind if oid not in MONUMENTS else "curated"] = counts.get(kind if oid not in MONUMENTS else "curated", 0) + 1
    ctx["note"](f"    statues: {counts}")


BUILDERS = [("Church windows", church_windows), ("Statues", statues)]
