"""More hand-built landmarks, away from the river front: the Opera, the two great stations, the Széchenyi Baths, the
Zoo's rock and Elephant House, the Ethnographic Museum, the Bálna, the Ferencváros church, the Budapest Eye and the
Soviet memorial. Built with landmarks.py's solids, on the frames of their OSM outlines (docs/landmarks.md).
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point

import landmarks as LM
from landmarks import (TAU, WINDOW, Arch, Box, Capsule, Ellipsoid, Field, Frame, Lathe, Poly, Prim, Roof, TBox, cone,
                       cyl, dome, figure, onion, pinnacle, rect_of, ring_segments, seg_frame, zsolnay)
from style import CLASSIC, GLASS, GRASS, METAL, ROOF, stable_hash

EYE, SOVIET, FERENC = 386319234, 310824694, 54246264
BALNA, BALNA_GLASS, BALNA_EAST = 1214545019, 236483267, 236483269
OPERA, OPERA_PARTS = 24000390, (1345994568, 1345994569, 1345994570)
ROCK, ROCK_SMALL, ELEPHANT, ZOO_GATE = 419586780, 838292028, 25225154, 6221648
SZECHENYI, NEPRAJZI = 19023, 13957874
KELETI, KELETI_SHED, NYUGATI, NYUGATI_SHED = 9906133, 1512257036, 24000268, 497219029
KELETI_HEAD, KELETI_PAV = 1512257035, (1512257038, 1512257039, 1512257040, 1512257041, 1512257042)
NYUGATI_CANOPY = 1510924479

DROP = {EYE, SOVIET, FERENC, BALNA, BALNA_GLASS, BALNA_EAST, OPERA, *OPERA_PARTS, ROCK, ROCK_SMALL, ELEPHANT, ZOO_GATE,
        SZECHENYI, NEPRAJZI, KELETI, KELETI_SHED, KELETI_HEAD, *KELETI_PAV, NYUGATI, NYUGATI_SHED, NYUGATI_CANOPY}
KEEP_PARTS = set()  # parts inside the Opera's and the baths' outlines that stay OSM's
NAMES = ["Budapest Eye", "Soviet War Memorial", "Ferencváros Church", "Bálna", "Hungarian State Opera",
         "Zoo: Great Rock and Elephant House", "Széchenyi Baths", "Museum of Ethnography", "Keleti Station",
         "Nyugati Station"]


# ------------------------------------------------------------------------------------------------ helpers
def base_under(ctx, g, q=0.5, step=4.0):
    """the ground under a footprint (metres above the model base): a quantile of samples on a grid inside it."""
    x0, y0, x1, y1 = g.bounds
    xs, ys = np.meshgrid(np.arange(x0 + step / 2, x1, step), np.arange(y0 + step / 2, y1, step))
    m = shapely.contains_xy(g, xs, ys)
    pts = list(zip(xs[m], ys[m])) or [g.representative_point().coords[0]]
    return float(np.quantile([ctx["ground_m"](x, y) for x, y in pts], q))


def facing(fr, pt):
    """the frame turned so that +u points towards pt (grid coordinates)."""
    u, _ = fr.uv(*pt)
    return fr if u >= 0 else Frame(fr.ox, fr.oy, fr.oz, fr.ang + math.pi)


def entrance_of(ctx, g, kinds=("main",)):
    """the main entrance mapped on a building's outline (a node with entrance=main within 1.5 m of it), or None"""
    best = None
    for oid, t, p in ctx["osm"].nodes:
        if t.get("entrance") in kinds and g.exterior.distance(p) < 1.5:
            d = g.centroid.distance(p)
            best = (d, (p.x, p.y)) if best is None or d > best[0] else best
    return None if best is None else best[1]


def named_near(ctx, name, p, r=400.0):
    """the nearest OSM feature (area or line) with this name, as a point, or None."""
    best = None
    for oid, k, t, g in ctx["osm"].areas:
        if t.get("name") == name and g.distance(p) < r:
            d = g.distance(p)
            best = (d, g.centroid) if best is None or d < best[0] else best
    for oid, t, ln in ctx["osm"].lines:
        if t.get("name") == name and ln.distance(p) < r:
            d = ln.distance(p)
            best = (d, ln.interpolate(ln.project(p))) if best is None or d < best[0] else best
    return None if best is None else (best[1].x, best[1].y)


def grid_of(g, pad=2.0):
    """the 0.5 m cells over a footprint's bounds: origin (x0f, y0f) in voxels, and their centres X, Y (grid metres)."""
    F = LM.F
    x0, y0, x1, y1 = g.bounds
    x0f, y0f = int(math.floor((x0 - pad) * F)), int(math.floor((y0 - pad) * F))
    nx, ny = int(math.ceil((x1 + pad) * F)) - x0f, int(math.ceil((y1 + pad) * F)) - y0f
    X, Y = np.meshgrid((np.arange(nx) + x0f + 0.5) / F, (np.arange(ny) + y0f + 0.5) / F)
    return x0f, y0f, X.astype(np.float32), Y.astype(np.float32)


def dist_in(g, X, Y):
    """distance from each cell centre to g's boundary, positive inside, negative outside."""
    pts = shapely.points(X.ravel(), Y.ravel())
    d = shapely.distance(g.boundary, pts).reshape(X.shape).astype(np.float32)
    return np.where(shapely.contains_xy(g, X, Y), d, -d)


def windows(S, g, b0, rows, targets, win, every=3.6, half=0.75, min_len=6.0, arch=True):
    """windows painted on every outer wall of a footprint: rows of (sill, head) heights above b0, one every `every` m."""
    for a, b, n in ring_segments(g, min_len):
        fr2 = seg_frame(a, b, n, 0)
        Ls = float(np.hypot(*(b - a)))
        k = max(int((Ls - 2.0) // every), 1)
        for i in range(k):
            t_ = (Ls - (k - 1) * every) / 2 + i * every
            for w0, w1 in rows:
                if arch:
                    S.add(Arch(fr2.at(t_, 0, 0, math.pi / 2), -0.3, 0.5, 0, half, b0 + w0, b0 + w1 - half, win,
                               mode="paint", targets=targets))
                else:
                    S.add(Box(fr2.at(t_, 0, 0, math.pi / 2), -0.3, 0.5, -half, half, b0 + w0, b0 + w1, win,
                              mode="paint", targets=targets))


def statue(S, fr, w0, col, scale=1.0):
    """a standing figure on the skyline, ~2.4 m: a body, a head, an arm raised."""
    s = scale
    S.add(Lathe(fr, w0, w0 + 1.6 * s, cone(0.42 * s, 0.26 * s), col))
    S.add(Ellipsoid(fr.at(0, 0, w0 + 1.85 * s), 0.27 * s, 0.3 * s, 0.34 * s, col))
    S.add(Ellipsoid(fr.at(0, 0, w0 + 2.3 * s), 0.17 * s, 0.17 * s, 0.21 * s, col))
    S.add(Capsule(fr, (0, 0.25 * s, w0 + 1.8 * s), (0.25 * s, 0.45 * s, w0 + 2.5 * s), 0.1 * s, col))


def rails_of(ctx, pt, r):
    """how many railway tracks pass within r m of a point."""
    p = Point(pt)
    return sum(1 for oid, t, ln in ctx["osm"].lines if t.get("railway") == "rail" and ln.distance(p) < r)


class Vault(Prim):
    """a barrel vault over [u0, u1] x [-hv, hv] springing at w0, rising h: the shell between two half-ellipses, `th`
    thick. col may be f(u, v, w)."""

    def __init__(self, fr, u0, u1, hv, w0, h, th, col, **kw):
        self.p = (u0, u1, hv, w0, h, th)
        super().__init__(fr, col, (u0, u1, -hv, hv, w0, w0 + h), **kw)

    def inside(self, u, v, w, x, y):
        u0, u1, hv, w0, h, th = self.p
        a = (v / hv) ** 2 + ((w - w0) / h) ** 2
        b = (v / (hv - th)) ** 2 + ((w - w0) / (h - th)) ** 2
        return (u >= u0) & (u < u1) & (w >= w0) & (a <= 1) & (b > 1)


# ------------------------------------------------------------------------------------------------ the Budapest Eye
def big_wheel(S, ctx, plan):
    """the Budapest Eye (Óriáskerék) on Erzsébet tér: a 65 m transportable wheel, white, with 42 closed gondolas on
    the rim, spokes from a hub on two A-frame pairs of legs, and lights along the rim at night."""
    P, C, area = ctx["P"], ctx["C"], ctx["area"]
    g = area[EYE][3]
    cx, cy, L, Wd, ang = rect_of(g)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(cx, cy, b0, ang)  # u in the wheel's plane, v along the axle
    white, white2, grey = P("#f1f1ec", METAL), P("#d8dadb", METAL), P("#9a9fa3", METAL)
    deck, deck2 = P("#bdb8ae"), P("#a9a49a")
    glass, cab, cab_roof = P("#6f93a8", GLASS), P("#f4f3ee"), P("#d0dfe8", METAL)
    lamp = C["lamp"]
    R, hz = 29.5, 34.6
    S.add(Box(fr, -L / 2, L / 2, -Wd / 2, Wd / 2, -1.5, 1.0, deck2))
    S.add(Box(fr, -L / 2 + 1, L / 2 - 1, -Wd / 2 + 1, Wd / 2 - 1, 1.0, 1.4, deck))
    S.add(Box(fr, -4.5, 4.5, -Wd / 2 + 1.5, -3.0, 1.4, 4.2, P("#3d4a55", WINDOW)))   # the boarding hut
    S.add(Box(fr, -4.8, 4.8, -Wd / 2 + 1.2, -2.7, 4.2, 4.6, white))
    # two pairs of legs, splayed in the wheel's plane, braced, up to the axle's ends
    for sv in (-1, 1):
        for su in (-1, 1):
            S.add(Capsule(fr, (su * 16.5, sv * 8.2, 1.4), (su * 0.8, sv * 3.4, hz - 0.6), 0.6, white))
        S.add(Capsule(fr, (-9.0, sv * 6.3, 15.0), (9.0, sv * 6.3, 15.0), 0.35, white2))
        S.add(Capsule(fr, (-4.6, sv * 4.9, 25.0), (4.6, sv * 4.9, 25.0), 0.3, white2))
    S.add(Capsule(fr, (0, -4.4, hz), (0, 4.4, hz), 0.9, grey))
    S.add(Capsule(fr, (0, -2.6, hz), (0, 2.6, hz), 1.9, white2))
    # the rim: two rings 3.2 m apart, an inner chord ring, laced; spokes from the hub's flanges
    n_g = 42
    th = np.linspace(0, TAU, 721)
    for sv in (-1, 1):
        S.polyline(fr, [(R * math.sin(t), sv * 1.6, hz + R * math.cos(t)) for t in th], white, thick=1)
        S.polyline(fr, [((R - 1.8) * math.sin(t), sv * 1.6, hz + (R - 1.8) * math.cos(t)) for t in th], white2)
    for k in range(n_g * 2):
        t0, t1 = TAU * k / (n_g * 2), TAU * (k + 1) / (n_g * 2)
        a = (R * math.sin(t0), -1.6, hz + R * math.cos(t0))
        b = ((R - 1.8) * math.sin(t1), 1.6, hz + (R - 1.8) * math.cos(t1))
        S.line(fr, a, b, white2)
        S.line(fr, (a[0], 1.6, a[2]), (b[0], -1.6, b[2]), white2)
    for k in range(n_g):
        t = TAU * (k + 0.5) / n_g
        for sv in (-1, 1):
            S.line(fr, (0, sv * 2.6, hz), ((R - 1.8) * math.sin(t), sv * 1.6, hz + (R - 1.8) * math.cos(t)), grey)
    # gondolas, hanging from the rim between its rings; lights round the rim
    for k in range(n_g):
        t = TAU * k / n_g
        pu, pw = (R + 0.4) * math.sin(t), hz + (R + 0.4) * math.cos(t)
        fg = fr.at(pu, 0, pw)
        S.add(Box(fg, -1.25, 1.25, -1.15, 1.15, -3.3, -2.5, cab))
        S.add(Box(fg, -1.25, 1.25, -1.15, 1.15, -2.5, -1.2, glass))
        S.add(Box(fg, -1.35, 1.35, -1.25, 1.25, -1.2, -0.75, cab_roof))
        S.line(fg, (0, 0, -0.75), (0, 0, 0.2), grey)
    for t in np.linspace(0, TAU, 160, endpoint=False):
        for sv in (-1, 1):
            S.line(fr, (R * math.sin(t) * 1.012, sv * 1.6, hz + R * math.cos(t) * 1.012),
                   (R * math.sin(t) * 1.012, sv * 1.6, hz + R * math.cos(t) * 1.012), lamp)


# ------------------------------------------------------------------------------------------------ Soviet memorial
def soviet_memorial(S, ctx, plan):
    """the Soviet War Memorial on Szabadság tér (Károly Antal, 1946): a white limestone obelisk with the Soviet arms
    in gilt bronze and a gilded star on top, on a pedestal with a bronze relief, between two low wings of reliefs."""
    P, area = ctx["P"], ctx["area"]
    g = area[SOVIET][3]
    cx, cy, L, Wd, ang = rect_of(g)
    b0 = base_under(ctx, g)
    fr = Frame(cx, cy, b0, ang)
    lime, lime2 = P("#ebe5d7"), P("#d5cebd")
    bronze, gold = P("#6a5a3f", METAL), P("#d2a94c", METAL)
    S.add(Box(fr, -L / 2, L / 2, -Wd / 2, Wd / 2, -1.0, 0.3, lime2))
    S.add(Box(fr, -L / 2 + 1.0, L / 2 - 1.0, -Wd / 2 + 1.2, Wd / 2 - 1.2, 0.3, 0.6, lime2))
    for su in (-1, 1):
        a, b = sorted((su * 4.8, su * (L / 2 - 1.6)))
        S.add(Box(fr, a, b, -1.5, 1.5, 0.6, 2.3, lime))
        S.add(Box(fr, a - 0.2, b + 0.2, -1.7, 1.7, 2.3, 2.6, lime2))
        S.add(Box(fr, *sorted((su * (L / 2 - 2.4), su * (L / 2 - 1.2))), -1.7, 1.7, 0.6, 3.2, lime))
        for sv in (-1, 1):
            S.add(Box(fr, a + 0.8, b - 0.8, *sorted((sv * 1.5, sv * 1.62)), 0.9, 2.0, bronze))
    S.add(Box(fr, -4.4, 4.4, -3.5, 3.5, 0.6, 1.2, lime2))
    S.add(Box(fr, -3.5, 3.5, -2.7, 2.7, 1.2, 3.8, lime))
    S.add(Box(fr, -3.7, 3.7, -2.9, 2.9, 3.8, 4.2, lime2))
    for sv in (-1, 1):
        S.add(Box(fr, -2.5, 2.5, *sorted((sv * 2.7, sv * 2.86)), 1.6, 3.5, bronze))
        S.add(Ellipsoid(fr.at(0, sv * 2.95, 2.55), 0.7, 0.25, 0.7, bronze))  # the wreath
    S.add(TBox(fr, 1.6, 1.2, 1.05, 0.8, 4.2, 13.6, lime))
    S.add(TBox(fr, 1.05, 0.8, 0.08, 0.08, 13.6, 14.5, lime2))
    for sv in (-1, 1):
        S.add(Ellipsoid(fr.at(0, sv * 0.98, 9.6), 0.75, 0.18, 0.78, gold))
        for wl in (6.0, 6.6, 7.2):
            S.add(Box(fr, -0.85, 0.85, *sorted((sv * 1.0, sv * 1.12)), wl, wl + 0.25, gold))
    for k in range(5):
        a = math.pi / 2 + TAU * k / 5
        S.add(Capsule(fr, (0, 0, 15.4), (1.0 * math.cos(a), 0, 15.4 + 1.0 * math.sin(a)), 0.24, gold))
    S.add(Box(fr, -0.2, 0.2, -0.2, 0.2, 14.4, 15.0, gold))


# ------------------------------------------------------------------------------------------------ Ferencváros church
def ferencvaros_church(S, ctx, plan):
    """Assisi Szent Ferenc-templom on Bakáts tér (Miklós Ybl, 1867-79): neo-Romanesque, in yellow brick with red bands
    and stone dressings; a basilica with aisles and an apse, and a 66.7 m tower over the west portal with clocks on its
    four faces, a belfry of twin arches and a copper spire, between two stair turrets."""
    P, area = ctx["P"], ctx["area"]
    g = area[FERENC][3]
    cx, cy, L, Wd, ang = rect_of(g)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(cx, cy, b0, ang)
    door = entrance_of(ctx, g)  # the west front, with the tower: OSM's main entrance on the outline
    sq = door if door is not None else named_near(ctx, "Bakáts tér", Point(cx, cy))
    if sq is not None:
        fr = facing(fr, sq)
    brick, band, trim = P("#d6ab68"), P("#a95f3e"), P("#e7dec7")
    slate, copper = P("#55585e", ROOF), P("#5e8577", ROOF)
    win, louvre, door = P("#2d3138", WINDOW), P("#3b3733"), P("#4d3a2b")
    white, dark, gold = P("#efede6"), P("#24262a"), P("#c9a34e", METAL)

    def walls(u, v, w):
        return np.where(np.mod(w - b0, 2.4) < 0.4, band, brick).astype(np.uint16)
    uf, ub = L / 2, -L / 2
    hn, ha = 6.6, Wd / 2
    ua = ub + hn + 1.0                     # where the apse meets the nave
    u_t = uf - 4.3                         # the tower's centre
    S.add(Box(fr, ua, uf - 6.0, -ha, ha, -2, 10.5, walls))
    S.add(Roof(fr, ua, uf - 6.0, -ha - 0.5, ha + 0.5, 10.5, 9.0, slate))
    S.add(Box(fr, ua, uf - 6.0, -hn, hn, 10.0, 19.5, walls))
    S.add(Box(fr, ua, uf - 6.0, -hn - 0.3, hn + 0.3, 19.5, 20.1, trim))
    S.add(Roof(fr, ua - 0.4, uf - 5.6, -hn - 0.7, hn + 0.7, 20.1, 9.5, slate))
    fa = fr.at(ua)
    S.add(Lathe(fa, -2, 17.5, cyl(hn), walls, n=12))
    S.add(Lathe(fa, 17.5, 24.5, cone(hn + 0.6, 0.4), slate, n=12))
    for k in range(5):  # the apse's windows
        t = math.pi / 2 + math.pi * (k + 0.5) / 5
        fk = fa.at(turn=t)
        S.add(Arch(fk, hn - 0.6, hn + 0.3, 0, 0.7, 6.0, 11.5, win, mode="paint", targets=[brick, band]))
    for u in np.arange(ua + 3.5, uf - 8.0, 4.4):  # aisle and clerestory windows, round-arched
        for sv in (-1, 1):
            fw = fr.at(u, 0, 0, sv * math.pi / 2)
            S.add(Arch(fw, ha - 0.5, ha + 0.3, 0, 0.75, 3.2, 8.0, win, mode="paint", targets=[brick, band]))
            S.add(Arch(fw, hn - 0.5, hn + 0.3, 0, 0.75, 12.5, 17.5, win, mode="paint", targets=[brick, band]))
    # the west front: the nave's gable and the aisles' fronts, with the tower before them; two stair turrets
    fg = fr.at(uf - 6.6, 0, 0, math.pi / 2)
    S.add(Roof(fg, -hn - 0.3, hn + 0.3, -0.6, 0.6, 19.5, 9.0, walls))
    for sv in (-1, 1):
        ft = fr.at(uf - 6.4, sv * (hn + 1.6))
        S.add(Lathe(ft, -2, 22.0, cyl(1.75), walls, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 22.0, 22.6, cyl(2.0), trim, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 22.6, 27.5, cone(1.9, 0.12), copper, n=8, rot=math.pi / 8))
        for wl in (6.0, 12.0, 17.5):
            S.add(Arch(ft.at(turn=0), 1.2, 1.9, 0, 0.35, wl, wl + 1.6, win, mode="paint", targets=[brick, band]))
        fd = fr.at(uf - 6.0, sv * (ha - 3.5), 0)
        S.add(Arch(fd, -0.4, 0.4, 0, 1.0, 0, 3.0, door, mode="paint", targets=[brick, band]))
    ft = fr.at(u_t)
    S.add(Box(ft, -4.3, 4.3, -4.3, 4.3, -2, 34.0, walls))
    for su in (-1, 1):
        for sv in (-1, 1):
            S.add(Box(ft, *sorted((su * 3.7, su * 4.7)), *sorted((sv * 3.7, sv * 4.7)), -2, 31.0, walls))
    S.add(Box(ft, -4.5, 4.5, -4.5, 4.5, 33.4, 34.0, trim))
    S.add(Box(ft, -3.9, 3.9, -3.9, 3.9, 34.0, 45.0, walls))
    S.add(Box(ft, -4.4, 4.4, -4.4, 4.4, 45.0, 45.8, trim))
    for k in range(4):
        fk = ft.at(turn=k * math.pi / 2)
        for vc in (-1.35, 1.35):
            S.add(Arch(fk, 3.2, 4.1, vc, 0.85, 37.0, 42.0, louvre, mode="paint", targets=[brick, band]))
        fc = fk.at(4.35, 0, 29.0)
        S.add(Ellipsoid(fc, 0.18, 1.55, 1.55, white))
        S.add(Ellipsoid(fc.at(0.1), 0.12, 1.7, 1.7, trim, mode="under"))
        S.line(fk, (4.6, 0, 29.0), (4.6, 0, 30.2), dark)
        S.line(fk, (4.6, 0, 29.0), (4.6, 0.8, 29.0), dark)
        S.add(Arch(fk, 3.8, 4.5, 0, 1.0, 20.5, 24.5, win, mode="paint", targets=[brick, band]))
        S.add(Roof(fk.at(3.6, 0, 0, math.pi / 2), -3.0, 3.0, -0.6, 0.6, 45.8, 3.0, copper))
    S.add(Ellipsoid(fr.at(uf - 0.05, 0, 15.0), 0.3, 1.9, 1.9, win, mode="paint", targets=[brick, band]))
    S.add(Arch(fr.at(uf - 0.6), -0.6, 1.0, 0, 2.4, -0.5, 4.6, trim))
    S.add(Arch(fr.at(uf - 0.6), -0.7, 1.1, 0, 1.6, 0, 4.2, door))
    for su in (-1, 1):
        for sv in (-1, 1):
            pinnacle(S, ft.at(su * 3.9, sv * 3.9), 45.8, 5.5, 0.6, copper)
    S.add(Lathe(ft, 45.8, 66.0, cone(3.9, 0.12), copper, n=8, rot=math.pi / 8))
    S.add(Ellipsoid(ft.at(0, 0, 66.2), 0.3, 0.3, 0.3, gold))
    S.add(Box(ft, -0.1, 0.1, -0.1, 0.1, 66.3, 68.0, gold))
    S.add(Box(ft, -0.1, 0.1, -0.6, 0.6, 67.2, 67.4, gold))


# ------------------------------------------------------------------------------------------------ the Bálna
def balna(S, ctx, plan):
    """the Bálna (Kas Oosterhuis, 2013): a whale of glass and steel between two of the 1881 Közraktárak warehouses,
    red brick in yellow bands under gabled roofs. Its triangulated shell rises from the warehouses' eaves and swells
    into a head that curves down to the riverside promenade; frosted and clear triangles over a green glass base."""
    P, area = ctx["P"], ctx["area"]
    whole, gl, east = area[BALNA][3], area[BALNA_GLASS][3], area[BALNA_EAST][3]
    rest = whole.difference(gl.buffer(0.3)).difference(east.buffer(0.3))
    pieces = sorted(getattr(rest, "geoms", [rest]), key=lambda q: -q.area)
    houses = [east] + ([pieces[0]] if pieces and pieces[0].area > 300 else [])
    b0 = base_under(ctx, whole, 0.3)
    brick, band, trim = P("#b4603f"), P("#dcb46a"), P("#e2d3b2")
    slate, win = P("#5d5753", ROOF), P("#2f3438", WINDOW)
    EAVE = 15.5

    def bands(u, v, w):
        h = w - b0
        return np.where((np.mod(h, 3.8) < 0.5) | (h < 1.0), band, brick).astype(np.uint16)
    for hp in houses:
        hx, hy, hL, hW, ha = rect_of(hp)
        fh = Frame(hx, hy, b0, ha)
        S.add(Poly(hp, b0 - 2, b0 + EAVE, bands))
        S.add(Box(fh, -hL / 2 - 0.3, hL / 2 + 0.3, -hW / 2 - 0.3, hW / 2 + 0.3, EAVE - 0.6, EAVE, trim))
        S.add(Roof(fh, -hL / 2 - 0.4, hL / 2 + 0.4, -hW / 2 - 0.6, hW / 2 + 0.6, EAVE, 5.5, slate))
        windows(S, hp, b0, [(1.2, 3.6), (5.2, 7.4), (9.0, 11.2), (12.4, 14.4)], [brick, band], win, every=3.4, half=0.65)
    # the shell, as a height field: from the warehouses' eaves (or the ground) up a quarter ellipse to the crest
    shell_p = gl.difference(shapely.union_all([h.buffer(0.2) for h in houses]))
    x0f, y0f, X, Y = grid_of(gl, 3.0)
    d = dist_in(shell_p, X, Y)
    hs = shapely.union_all(houses)
    dh = np.maximum(shapely.distance(hs, shapely.points(X.ravel(), Y.ravel())).reshape(X.shape), 0).astype(np.float32)
    gx, gy, gL, gW, gang = rect_of(gl)
    fg = Frame(gx, gy, 0, gang)
    if houses[0].centroid.distance(Point(fg.xy(gL / 2, 0))) < houses[0].centroid.distance(Point(fg.xy(-gL / 2, 0))):
        fg = Frame(gx, gy, 0, gang + math.pi)  # +u towards the head, away from the warehouses
    U = ((X - gx) * fg.ca + (Y - gy) * fg.sa).astype(np.float32)
    V = (-(X - gx) * fg.sa + (Y - gy) * fg.ca).astype(np.float32)
    t = np.clip((U + gL / 2) / gL, 0, 1)
    H = 22.5 + 4.0 * np.sin(np.clip(t / 0.8, 0, 1) * math.pi / 2)
    zb = EAVE * np.exp(-dh / 5.0)
    Rr = 15.0
    q = np.clip(d / Rr, 0, 1)
    zs = np.where(d > 0, zb + (H - zb) * np.sqrt(1 - (1 - q) ** 2), 0).astype(np.float32)
    gzy, gzx = np.gradient(zs * LM.F)
    slope = np.hypot(gzx, gzy).astype(np.float32)
    fields = dict(zs=zs, d=d, slope=slope, U=U, V=V)
    steel, steel2 = P("#d5d8d8", METAL), P("#9ea5a7", METAL)
    clear, frost, green = P("#8fb3b8", GLASS), P("#e3e8e6"), P("#3d6a64", GLASS)

    def fn(f, wa):
        z = f["zs"][None] + b0
        d_, sl = f["d"][None], f["slope"][None]
        th = np.clip(0.7 * np.sqrt(1 + sl ** 2), 0.7, 8.0)
        edge = (d_ > 0) & (d_ < 0.8) & (wa >= b0 - 1) & (wa <= z)
        skin = (d_ > 0) & (wa <= z) & (wa >= z - th)
        m = edge | skin
        uq = f["U"][None] + 0 * wa
        qv = np.where(sl > 1.2, (wa - b0) * np.sign(f["V"][None]), f["V"][None] + 0 * wa)
        a_, b_ = (uq + qv) / 3.3, (uq - qv) / 3.3
        line = (np.mod(a_, 1) < 0.14) | (np.mod(b_, 1) < 0.14)
        tri = np.floor(a_) + 5 * np.floor(b_)
        pane = np.where(np.mod(tri, 3) == 0, frost, clear)
        col = np.where(wa - b0 < 5.0, green, pane)
        col = np.where(line, np.where(wa - b0 < 5.0, steel2, steel), col)
        return np.where(m, col, 0).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 1, b0 + 28.0, fn))


# ------------------------------------------------------------------------------------------------ the Opera
def opera(S, ctx, plan):
    """the Hungarian State Opera on Andrássy út (Miklós Ybl, 1884), neo-Renaissance in warm grey stone. A carriage porch
    of three arches before a five-bay centre: a loggia of tall arches on the first floor, an attic, a balustrade of
    composers' statues and a slate mansard; corner pavilions with Muses in arched niches and their own roofs. Behind:
    the auditorium and the stage under one long hipped roof of pale zinc with two round lanterns on its ridge (as
    aerial photos show it), low roofs either side with rows of zinc-framed skylights, carriage drives on both sides
    (the royal one on Hajós utca), a pale hipped roof across the back. Over the front range a steep slate mansard
    and a hipped roof with iron cresting; square domes over the corner pavilions."""
    P, area = ctx["P"], ctx["area"]
    g = area[OPERA][3]
    cx, cy, L, Wd, ang = rect_of(g)
    b0 = base_under(ctx, g, 0.4)
    porch = area[OPERA_PARTS[2]][3] if OPERA_PARTS[2] in area else None
    fr = Frame(cx, cy, b0, ang)
    if porch is not None:
        fr = facing(fr, porch.centroid.coords[0])
    cu, cv = fr.uv(*np.array(g.exterior.coords).T)
    u_front, u_back, vh = float(cu.max()), float(cu.min()), float(np.abs(cv).max())
    side = np.abs(cv) > vh - 4
    u_main = float(cu[side].max())                                   # the corner pavilions' front
    vp = float(np.abs(cv[cu > u_main + 2]).max()) if (cu > u_main + 2).any() else vh * 0.6   # the centre's half-width
    stone, stone2, rust = P("#d2c7b1"), P("#d5cab4"), P("#bdb198")
    trim, trim2 = P("#e3dbc9"), P("#c9bea7")
    slate, slate2, metal = P("#4c535b", ROOF), P("#454c54", ROOF), P("#8e9993", METAL)
    zinc = P("#6e7780", ROOF)
    win, dark, glass = P("#2e3238", WINDOW), P("#3a3633"), P("#3b4752", WINDOW)
    statue_c, bronze, gold = P("#cfc6b4"), P("#6f6047", METAL), P("#c9a34e", METAL)

    def ashlar(u, v, w):  # rusticated below the first floor's sill, smooth above
        h = w
        return np.where((h < 8.6) & (np.mod(h, 0.9) < 0.18), rust, stone).astype(np.uint16)

    def ashlar2(u, v, w):
        h = w
        return np.where((h < 8.6) & (np.mod(h, 0.9) < 0.18), rust, stone2).astype(np.uint16)
    # the masses: front pavilions, the centre, the auditorium, the stage house, the back
    u_aud0, u_aud1 = -12.0, u_main - 14.0
    S.add(Box(fr, u_aud1, u_main, -vh, vh, -2, 22.6, ashlar))            # the front range behind the pavilions
    S.add(Box(fr, u_aud0, u_aud1, -vh, vh, -2, 22.6, ashlar))            # round the auditorium
    S.add(Box(fr, u_back, u_aud0, -vh, vh, -2, 21.0, ashlar))            # the stage's side wings and the back
    S.add(Box(fr, u_main - 2, u_front, -vp, vp, -2, 22.6, ashlar2))     # the centre, projecting
    for a, b, v0, v1 in ((u_back, u_main, -vh - 0.3, vh + 0.3), (u_main - 2, u_front + 0.3, -vp - 0.3, vp + 0.3)):
        S.add(Box(fr, a - 0.3, b + 0.3, v0, v1, 8.4, 9.0, trim2))       # the string course over the ground floor
        S.add(Box(fr, a - 0.4, b + 0.4, v0 - 0.1, v1 + 0.1, 21.8, 22.6, trim))   # the main cornice
    # attic over the centre and the pavilions, balustrade and the composers
    S.add(Box(fr, u_main - 2, u_front, -vp, vp, 22.6, 25.0, stone2))
    S.add(Box(fr, u_main - 2, u_front + 0.2, -vp - 0.2, vp + 0.2, 25.0, 25.4, trim))

    def balus(u, v, w):
        return np.where((w > 26.2) | (w < 25.6) | (np.mod(u + v, 0.7) < 0.32), trim, 0).astype(np.uint16)
    S.add(Box(fr, u_front - 0.6, u_front, -vp, vp, 25.4, 26.5, balus))
    for v in np.linspace(-vp + 0.8, vp - 0.8, 8):
        S.add(Box(fr, u_front - 0.7, u_front + 0.1, v - 0.45, v + 0.45, 25.4, 26.6, trim))
        statue(S, fr.at(u_front - 0.3, v), 26.6, statue_c, 1.05)
    for k in range(5):  # the attic's windows
        vb = -vp + (k + 0.5) * 2 * vp / 5
        S.add(Box(fr.at(u_front, vb), -0.3, 0.2, -1.0, 1.0, 23.1, 24.5, win, mode="paint", targets=[stone2]))
    # the first-floor loggia: five tall arches between paired columns, a balcony before them
    bay = 2 * vp / 5
    shade = P("#9b927f")
    for k in range(5):
        vb = -vp + (k + 0.5) * bay
        S.add(Arch(fr.at(u_front), 0.0, 0.55, vb, bay * 0.33 + 0.4, 10.2, 16.4, trim))         # the archivolt
        S.add(Arch(fr.at(u_front), -2.6, 0.6, vb, bay * 0.33, 10.2, 16.4, mode="carve"))
        S.add(Arch(fr.at(u_front), -2.8, -1.9, vb, bay * 0.33, 10.2, 16.4, glass))  # thicker than a voxel: never lost
        S.add(Arch(fr.at(u_front), -2.6, -0.1, vb, bay * 0.33, 10.2, 16.4, shade, mode="paint", targets=[stone2]))
        S.add(Ellipsoid(fr.at(u_front, vb + bay / 2, 19.9), 0.2, 0.55, 0.45, win))             # oculi between
        for dv in (-0.5, 0.5):
            vc = vb + dv * bay
            if abs(vc) < vp - 0.3:
                for o in (-0.45, 0.45):
                    S.add(Lathe(fr.at(u_front + 0.35, vc + o), 9.6, 19.6, cyl(0.32), trim))
    S.add(Box(fr, u_front - 0.2, u_front + 0.6, -vp, vp, 9.0, 9.6, trim))
    S.add(Box(fr, u_front + 0.2, u_front + 0.6, -vp, vp, 9.6, 10.6, balus2 := (lambda u, v, w: np.where(
        (w > 10.3) | (np.mod(v, 0.6) < 0.25), trim, 0).astype(np.uint16))))
    S.add(Box(fr, u_front + 0.1, u_front + 0.7, -vp - 0.2, vp + 0.2, 19.6, 21.0, trim2))
    # the porch: three arches in front, one each side, a terrace on top
    if porch is not None:
        pu0 = u_front
        pu1, pv = fr.uv(*porch.centroid.coords[0])[0] + 2.5, max(rect_of(porch)[2] / 2, 6.0)
    else:
        pu0, pu1, pv = u_front, u_front + 5.0, 7.8
    S.add(Box(fr, pu0 - 0.5, pu1, -pv, pv, -1.0, 8.4, ashlar2))
    S.add(Box(fr, pu0 - 0.5, pu1 + 0.3, -pv - 0.3, pv + 0.3, 8.4, 9.0, trim))
    S.add(Box(fr, pu1 - 0.4, pu1 + 0.1, -pv, pv, 9.0, 10.0, balus2))
    for k in (-1, 0, 1):
        S.add(Arch(fr.at(pu1, k * pv * 0.66, 0, 0), -(pu1 - pu0) - 1.0, 0.5, 0, pv * 0.25, 0, 5.4, mode="carve"))
    for sv in (-1, 1):
        S.add(Arch(fr.at((pu0 + pu1) / 2, sv * pv, 0, sv * math.pi / 2), -1.0, 1.0, 0, 1.6, 0, 5.2, mode="carve"))
        for su in (-1, 1):
            S.add(Lathe(fr.at(pu1 + 0.5, sv * (pv - 0.6) * (0.33 if su < 0 else 1.0)), 0, 8.4, cyl(0.4), trim))
    S.add(Box(fr, pu0 - 0.6, pu0 - 0.1, -pv + 0.6, pv - 0.6, 0, 5.0, P("#5a4634"), mode="under"))  # the doors
    for sv in (-1, 1):  # Liszt and Erkel, seated, in their niches either side of the porch
        fn_ = fr.at(u_front, sv * (pv + 2.6))
        S.add(Arch(fn_, -0.8, 0.3, 0, 1.2, 0.8, 4.4, mode="carve"))
        S.add(Box(fn_, -0.8, -0.2, -0.6, 0.6, 0.8, 2.0, trim))
        S.add(Ellipsoid(fn_.at(-0.4, 0, 2.7), 0.45, 0.45, 0.75, bronze))
        S.add(Ellipsoid(fn_.at(-0.4, 0, 3.6), 0.22, 0.22, 0.26, bronze))
        S.add(Box(fr, u_front + 2.0, u_front + 8.0, sv * (pv + 0.6) - 0.6, sv * (pv + 0.6) + 0.6, 0, 1.4, trim2))  # ramp walls
        S.add(Ellipsoid(fr.at(u_front + 7.0, sv * (pv + 0.6), 2.0), 1.3, 0.45, 0.6, statue_c))       # the sphinxes
        S.add(Ellipsoid(fr.at(u_front + 7.9, sv * (pv + 0.6), 2.6), 0.35, 0.35, 0.45, statue_c))
    # the corner pavilions: an arched niche with a Muse on the first floor, a door under a pediment, their own roofs
    for sv in (-1, 1):
        vc = sv * (vp + vh) / 2
        fp = fr.at(u_main, vc)
        hwp = (vh - vp) / 2
        S.add(Arch(fp, 0.0, 0.55, 0, 2.1, 10.0, 16.0, trim))
        S.add(Arch(fp, -1.4, 0.6, 0, 1.7, 10.2, 16.0, mode="carve"))
        S.add(Arch(fp, -1.6, -0.9, 0, 1.7, 10.2, 16.0, shade))
        S.add(Box(fp, -1.2, -0.2, -0.9, 0.9, 10.2, 10.6, trim))
        statue(S, fp.at(-0.7), 10.6, statue_c, 1.25)
        S.add(Box(fp, -0.3, 0.3, -1.0, 1.0, 17.6, 20.4, win, mode="paint", targets=[stone, stone2]))
        S.add(Box(fp, 0.0, 0.35, -1.3, 1.3, 20.4, 20.8, trim))
        S.add(Box(fp, -0.1, 0.5, -1.4, 1.4, 0, 3.8, P("#5a4634"), mode="paint", targets=[stone, rust]))
        S.add(Roof(fp.at(0.3, 0, 0, math.pi / 2), -2.0, 2.0, -0.3, 0.3, 4.0, 1.4, trim))
        S.add(Box(fr, u_main - 2 * hwp, u_main, vc - hwp, vc + hwp, 22.6, 25.2, stone))
        S.add(Box(fr, u_main - 2 * hwp - 0.2, u_main + 0.2, vc - hwp - 0.2, vc + hwp + 0.2, 25.2, 25.6, trim))
        fpc = fr.at(u_main - hwp, vc)
        prof = [(25.6, 1.0), (27.4, 0.97), (29.0, 0.86), (30.4, 0.66), (31.5, 0.42), (32.2, 0.22)]
        for (wa, ka), (wb, kb) in zip(prof[:-1], prof[1:]):  # a square dome, steep at the foot, rounding over
            S.add(TBox(fpc, hwp * ka, hwp * ka, hwp * kb, hwp * kb, wa, wb, slate))
        for su in (-1, 1):  # ribs down the four corners
            for sw in (-1, 1):
                S.line(fpc, (su * hwp * 0.98, sw * hwp * 0.98, 25.7), (su * hwp * 0.62, sw * hwp * 0.62, 30.5), metal)
        S.add(Box(fpc, -0.7, 0.7, -0.7, 0.7, 32.2, 33.4, zinc))
        S.add(Lathe(fpc, 33.4, 34.6, dome(0.75, 2.0, 0.1), metal, n=4, rot=math.pi / 4))
        S.add(Box(fpc, -0.1, 0.1, -0.1, 0.1, 34.6, 36.0, gold))
        for su in (-1, 1):
            for sw in (-1, 1):
                S.add(Box(fr.at(u_main - hwp + su * (hwp - 0.4), vc + sw * (hwp - 0.4)), -0.3, 0.3, -0.3, 0.3, 25.6, 27.4, metal))
        for k in (-1, 1):
            statue(S, fr.at(u_main - 0.3, vc + k * hwp * 0.6), 25.6, statue_c, 1.0)
    # the mansard over the front range, dormers, the crest
    hu_f, hv_f = (u_front - u_aud1) / 2 - 1.5, vp - 0.8
    fm = fr.at((u_aud1 + u_front) / 2 - 1.0, 0)
    S.add(TBox(fm, hu_f, hv_f, hu_f - 1.6, hv_f - 1.6, 25.4, 29.2, slate))    # the mansard's steep lower slope
    rise = min(hu_f - 1.6, 5.0)
    S.add(Roof(fm.at(0, 0, 0, math.pi / 2), -(hv_f - 1.6), hv_f - 1.6, -(hu_f - 1.6), hu_f - 1.6, 29.2, rise, slate2, hip=True))
    rl = max(hv_f - hu_f, 0.5)  # the ridge's half-length (the hips slope as steeply as the sides)
    S.line(fm, (0, -rl, 29.2 + rise), (0, rl, 29.2 + rise), metal)  # the iron crest
    for vv in (-rl, rl):
        S.add(Box(fm.at(0, vv), -0.15, 0.15, -0.15, 0.15, 29.2 + rise, 29.2 + rise + 1.6, metal))
    for k in range(5):
        vb = -vp + (k + 0.5) * bay
        S.add(Box(fr.at(u_front - 2.4, vb), -0.6, 0.6, -0.7, 0.7, 26.0, 28.2, trim2))
        S.add(Box(fr.at(u_front - 2.4, vb), -0.2, 0.7, -0.45, 0.45, 26.3, 27.7, win))
        S.add(Box(fr.at(u_front - 3.2, vb), -0.15, 0.15, -0.15, 0.15, 31.0, 33.0, metal))
    S.add(Roof(fr, u_aud1, u_main - 2, -vh + 0.3, vh - 0.3, 22.6, 6.0, slate2))
    # behind the front range, as aerial photos show it: one long hipped roof of pale zinc over the auditorium and the
    # stage together, as wide as the centre, two round lanterns on its ridge; low roofs either side with rows of
    # skylights framed in zinc; a pale hipped roof across the back
    u_c0, u_c1 = u_back + 12.0, u_main - 8.6
    zinc_l = P("#9ea4a7", ROOF)
    S.add(Box(fr, u_c0, u_c1, -vp, vp, -2, 26.0, stone))
    S.add(Box(fr, u_c0 - 0.3, u_c1 + 0.3, -vp - 0.3, vp + 0.3, 25.4, 26.0, trim))
    S.add(Roof(fr, u_c0 - 0.4, u_c1 + 0.4, -vp - 0.4, vp + 0.4, 26.0, 10.0, zinc_l, hip=True))
    ridge = 36.0
    for ul in (u_c0 + 22.5, u_c0 + 48.8):
        fl = fr.at(ul)
        S.add(Lathe(fl, ridge - 1.5, ridge + 1.8, cyl(2.1), trim, n=8, rot=math.pi / 8))
        for k in range(8):
            S.add(Box(fl.at(turn=TAU * k / 8), 1.7, 2.2, -0.35, 0.35, ridge + 0.2, ridge + 1.4, win, mode="paint", targets=[trim]))
        S.add(Lathe(fl, ridge + 1.8, ridge + 3.2, dome(2.3, 2.0, 0.3), zinc, n=8, rot=math.pi / 8))
        S.add(Box(fl, -0.12, 0.12, -0.12, 0.12, ridge + 3.2, ridge + 4.4, gold))
    frame_c = P("#b9bfc1", ROOF)

    def skylights(u0):
        return lambda u, v, w: np.where(np.mod(u - u0, 8.4) < 1.1, frame_c, slate2).astype(np.uint16)
    for sv in (-1, 1):
        a, b = sorted((sv * vp, sv * (vh - 0.3)))
        S.add(Roof(fr, u_aud0, u_c1 + 0.3, a, b, 22.6, 2.4, skylights(u_aud0)))
        S.add(Roof(fr, u_back + 0.3, u_aud0 + 0.5, a, b, 21.0, 2.4, skylights(u_back)))
    S.add(Roof(fr.at(turn=math.pi / 2), -vh + 0.3, vh - 0.3, -u_c0 - 0.5, -u_back - 0.3, 21.0, 3.6, zinc_l, hip=True))
    for sv in (-1, 1):
        a, b = sorted((sv * vh, sv * (vh + 5.2)))
        S.add(Box(fr, -11.0, 4.5, a, b, -1, 8.4, ashlar))
        S.add(Box(fr, -11.3, 4.8, a - 0.2, b + 0.2, 8.4, 9.0, trim))
        S.add(Box(fr, -11.3, 4.8, *sorted((sv * (vh + 4.8), sv * (vh + 5.4))), 9.0, 10.0, balus2))
        S.add(Arch(fr.at(-11.5), 0, 16.5, sv * (vh + 2.6), 1.9, 0, 4.4, mode="carve"))   # the drive, under the arcade
        for uc in (-7.0, -3.2, 0.6):
            S.add(Arch(fr.at(uc, sv * (vh + 5.2), 0, sv * math.pi / 2), -1.0, 0.6, 0, 1.5, 0, 4.6, mode="carve"))
    # windows on the side and back walls: arched on the ground floor, square above
    for a, b, n in ring_segments(g, 8.0):
        fr2 = seg_frame(a, b, n, 0)
        Ls = float(np.hypot(*(b - a)))
        if (fr.uv(*((a + b) / 2))[0]) > u_main - 1:
            continue
        for t_ in np.arange(2.5, Ls - 1.5, 3.9):
            f3 = fr2.at(t_, 0, 0, math.pi / 2)
            S.add(Arch(f3, -0.3, 0.5, 0, 0.75, b0 + 1.8, b0 + 5.4, win, mode="paint", targets=[stone, rust]))
            S.add(Box(f3, -0.3, 0.5, -0.75, 0.75, b0 + 10.4, b0 + 14.0, win, mode="paint", targets=[stone]))
            S.add(Box(f3, -0.3, 0.5, -0.65, 0.65, b0 + 16.4, b0 + 19.2, win, mode="paint", targets=[stone]))
    for sv in (-1, 1):  # the central block's upper windows over the side roofs
        for su in np.arange(u_c0 + 3.0, u_c1 - 1.0, 4.2):
            S.add(Box(fr.at(su, sv * vp, 0, sv * math.pi / 2), -0.3, 0.4, -0.7, 0.7, 23.2, 25.0, win, mode="paint", targets=[stone]))
    for sv in (-1, 1):  # the candelabra on the pavement
        for k in (0, 1):
            x, y = fr.xy(u_front + 3.5 + k * 9.0, sv * (pv + 4.5))
            ctx["lamp_post"](int(x * LM.F), int(y * LM.F), int(round(b0 * LM.F)), 5.5)


# ------------------------------------------------------------------------------------------------ the Zoo
def rock(S, ctx, g, H, seed):
    """an artificial mountain over an outline: a rounded mass up to H m, broken into ledges and crags, grey concrete
    rock with green on the gentler ledges."""
    P = ctx["P"]
    b0 = base_under(ctx, g, 0.3)
    x0f, y0f, X, Y = grid_of(g, 1.0)
    d = dist_in(g, X, Y)
    dm = max(float(d.max()), 1.0)
    rng = np.random.default_rng(seed)
    nz = np.zeros_like(X)
    for k in range(7):  # a few octaves of waves at random angles: crags and gullies
        a, f, ph = rng.uniform(0, TAU), 0.05 * 1.7 ** k, rng.uniform(0, TAU)
        nz += np.sin((X * math.cos(a) + Y * math.sin(a)) * f + ph) / 1.5 ** k
    q = np.clip(d / dm, 0, 1)
    z = H * (1 - (1 - q) ** 1.8) + 3.2 * nz * np.clip(d / 6, 0, 1)
    z = np.where(d > 0, np.maximum(z, 0.8), -5).astype(np.float32)
    z = np.round(z / 1.2) * 1.2 + np.mod(np.floor(X / 3) + np.floor(Y / 3), 2) * 0.5  # ledges
    gy, gx = np.gradient(z * LM.F)
    fields = dict(z=z.astype(np.float32), sl=np.hypot(gx, gy).astype(np.float32), X=X, Y=Y)
    greys = np.array([P("#8b867d"), P("#7c776f"), P("#9b968c"), P("#6e6a64"), P("#a39e93")], np.uint16)
    green, green2 = P("#5f7d43", GRASS), P("#4f6c3a", GRASS)

    def fn(f, wa):
        top = f["z"][None] + b0
        m = wa <= top
        a_ = np.floor(f["X"][None] / 1.4).astype(np.int64)
        b_ = np.floor(f["Y"][None] / 1.4).astype(np.int64)
        c_ = np.floor((wa - b0) / 1.1).astype(np.int64)
        h = (a_ * 73856093) ^ (b_ * 19349663) ^ (c_ * 83492791)  # a block hash: no stripes
        h = np.abs(h) >> 3
        col = greys[np.mod(h, len(greys))]
        veg = (wa > top - 0.6) & (f["sl"][None] < 0.9) & (np.mod(h >> 4, 3) != 0)
        col = np.where(veg, np.where(np.mod(h >> 6, 2) == 0, green, green2), col)
        return np.where(m, col, 0).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 2, b0 + H + 6, fn))


def elephant(S, fr, w0, col, s=1.0):
    """a stone elephant standing on w0, facing +u: body, head, ears, trunk, four legs."""
    S.add(Ellipsoid(fr.at(0, 0, w0 + 2.2 * s), 1.7 * s, 1.05 * s, 1.1 * s, col))
    S.add(Ellipsoid(fr.at(1.8 * s, 0, w0 + 2.7 * s), 0.75 * s, 0.7 * s, 0.75 * s, col))
    for sv in (-1, 1):
        S.add(Ellipsoid(fr.at(1.5 * s, sv * 0.75 * s, w0 + 2.7 * s), 0.25 * s, 0.6 * s, 0.7 * s, col))
        for su in (-1, 1):
            S.add(Capsule(fr, (su * 1.0 * s, sv * 0.55 * s, w0 + 0.2), (su * 1.0 * s, sv * 0.55 * s, w0 + 1.8 * s), 0.38 * s, col))
    S.add(Capsule(fr, (2.4 * s, 0, w0 + 2.5 * s), (2.7 * s, 0, w0 + 1.0 * s), 0.25 * s, col))
    S.add(Capsule(fr, (2.7 * s, 0, w0 + 1.0 * s), (3.0 * s, 0, w0 + 0.6 * s), 0.18 * s, col))


def zoo(S, ctx, plan):
    """the Budapest Zoo (1912 rebuild, Kornél Neuschloss and Károly Kós): the Great Rock (Nagyszikla), a 34 m concrete
    mountain, and the Little Rock; the Elephant House, an Ottoman pavilion whose dome and minaret are clad in Zsolnay
    ceramic; and the main gate on Állatkerti körút, its pylons carrying stone elephants, with a mosaic frieze."""
    P, area = ctx["P"], ctx["area"]
    if ROCK in area:
        rock(S, ctx, area[ROCK][3], 33.0, 7)
    if ROCK_SMALL in area:
        rock(S, ctx, area[ROCK_SMALL][3], 13.0, 11)
    cream, ochre, red = P("#ece2ca"), P("#d7b26e"), P("#a8553b")
    win = P("#2f3238", WINDOW)
    tiles = zsolnay(P, ["#e7d9b5", "#2e8f8a", "#4f9a6a", "#d9b24a", "#2a6f86"], period=0.9, slope=1.0, kind="diamond")
    gold = P("#d2ac4e", METAL)
    stone_c = P("#cfcac0")
    if ELEPHANT in area:
        g = area[ELEPHANT][3]
        cx, cy, L, Wd, ang = rect_of(g)
        b0 = base_under(ctx, g, 0.3)
        fr = Frame(cx, cy, b0, ang)

        def bands(u, v, w):
            return np.where(np.mod(w, 1.6) < 0.5, ochre, cream).astype(np.uint16)
        S.add(Box(fr, -L / 2 + 1, L / 2 - 1, -Wd / 2 + 1, Wd / 2 - 1, -1, 8.5, bands))
        S.add(Box(fr, -L / 2 + 0.7, L / 2 - 0.7, -Wd / 2 + 0.7, Wd / 2 - 0.7, 8.5, 9.3, red))
        r = min(Wd / 2 - 2.0, 8.0)
        S.add(Lathe(fr, 8.5, 12.5, cyl(r), bands, n=16))
        for k in range(16):
            S.add(Arch(fr.at(turn=TAU * k / 16), r - 0.6, r + 0.3, 0, 0.45, 10.0, 11.6, win, mode="paint", targets=[cream, ochre]))
        S.add(Lathe(fr, 12.5, 13.0, cyl(r + 0.4), red, n=16))
        S.add(Lathe(fr, 13.0, 13.0 + r * 1.05, dome(r, 2.0), tiles))
        S.add(Lathe(fr, 13.0 + r * 1.0, 14.6 + r * 1.05, cone(0.6, 0.1), gold))
        S.add(Ellipsoid(fr.at(0, 0, 15.0 + r * 1.05), 0.45, 0.12, 0.45, gold))
        for su in (-1, 1):  # half domes over the ends, horseshoe-arched portals
            fe = fr.at(su * (L / 2 - 5.5))
            S.add(Lathe(fe, 8.5, 9.5, cyl(3.8), bands, n=12))
            S.add(Lathe(fe, 9.5, 13.4, dome(3.8, 2.0), tiles, n=12))
            S.add(Lathe(fe, 13.2, 14.3, cone(0.35, 0.05), gold))
        for sv in (-1, 1):
            for u in np.arange(-L / 2 + 3.5, L / 2 - 3.0, 3.6):
                fw = fr.at(u, 0, 0, sv * math.pi / 2)
                S.add(Arch(fw, Wd / 2 - 1.4, Wd / 2 - 0.6, 0, 0.8, 2.5, 6.4, win, mode="paint", targets=[cream, ochre]))
            fd = fr.at(0, sv * (Wd / 2 - 1.0), 0, sv * math.pi / 2)
            S.add(Arch(fd, -0.4, 0.6, 0, 2.6, 0, 5.2, P("#4b3b2c"), mode="paint", targets=[cream, ochre]))
            S.add(Arch(fd, 0.0, 0.7, 0, 3.3, 0, 5.4, tiles, mode="under"))
        fm = fr.at(L / 2 - 2.5, Wd / 2 - 2.5)  # the minaret
        S.add(Lathe(fm, -1, 21.0, cone(1.6, 1.3), bands, n=8, rot=math.pi / 8))
        S.add(Lathe(fm, 18.6, 19.2, cyl(2.1), red, n=8, rot=math.pi / 8))
        S.add(Lathe(fm, 19.2, 20.2, cyl(2.0), lambda u, v, w: np.where(np.mod(np.arctan2(v, u) * 8 / TAU, 1) < 0.3, red, 0).astype(np.uint16), n=8, rot=math.pi / 8))
        S.add(Lathe(fm, 21.0, 26.5, cone(1.4, 0.1), tiles, n=8, rot=math.pi / 8))
        S.add(Lathe(fm, 26.3, 27.8, cyl(0.12), gold))
        S.add(Ellipsoid(fm.at(0, 0, 27.6), 0.35, 0.1, 0.35, gold))
    if ZOO_GATE in area:
        g = area[ZOO_GATE][3]
        cx, cy, L, Wd, ang = rect_of(g)
        b0 = base_under(ctx, g, 0.3)
        fr = Frame(cx, cy, b0, ang)
        st = named_near(ctx, "Állatkerti körút", Point(cx, cy))
        if st is not None:  # +v towards the street
            if fr.uv(*st)[1] < 0:
                fr = Frame(cx, cy, b0, ang + math.pi)
        stone, stone2, mosaic = P("#d9d2c2"), P("#bdb5a4"), P("#c99b3b", METAL)
        teal = P("#2d8a86")

        def frieze(u, v, w):
            return np.where((w > 5.0) & (w < 6.0), np.where(np.mod(u, 1.2) < 0.6, mosaic, teal),
                            np.where(np.mod(w, 1.0) < 0.15, stone2, stone)).astype(np.uint16)
        S.add(Poly(g, b0 - 1, b0 + 6.6, lambda u, v, w: frieze(u, v, w - b0)))
        for sv in (-1, 1):  # the pylons, an elephant on each, facing the street
            fp = fr.at(sv * 4.6, 0)
            S.add(Box(fp, -1.8, 1.8, -1.8, 1.8, -1, 11.0, stone))
            S.add(Box(fp, -2.1, 2.1, -2.1, 2.1, 11.0, 11.6, stone2))
            S.add(Box(fp, -1.9, 1.9, -2.0, -1.7, 6.5, 8.5, teal))
            elephant(S, fp.at(0, 0, 0, math.pi / 2), 11.6, stone_c, 0.9)
        S.add(Arch(fr.at(0, 0, 0, math.pi / 2), -Wd / 2 - 1.0, Wd / 2 + 1.0, 0, 2.6, -0.5, 4.2, mode="carve"))
        S.add(Box(fr, -2.8, 2.8, -1.2, 1.2, 6.6, 8.0, frieze))
        S.add(Ellipsoid(fr.at(0, 0.6, 8.9), 0.9, 0.55, 0.65, P("#f2f0ea")))   # the polar bear over the gate
        S.add(Ellipsoid(fr.at(0, 1.3, 9.2), 0.35, 0.4, 0.35, P("#f2f0ea")))


# ------------------------------------------------------------------------------------------------ the Széchenyi Baths
def szechenyi(S, ctx, plan):
    """the Széchenyi Baths (Győző Czigler, Ede Dvorák, 1913; Imre Francsek, 1927): the 1913 bath house in grey-white
    stone on Állatkerti körút, its entrance hall under a ribbed dome and its corners under two more; round the pool
    court the yellow 1927 wings with white dressings, arched windows and a balustrade. In the court, three pools: the
    50 m swimming pool between two warm pools with rounded ends."""
    P, C, area = ctx["P"], ctx["C"], ctx["area"]
    g = area[SZECHENYI][3]
    polys = sorted(getattr(g, "geoms", [g]), key=lambda q: -q.area)
    g = polys[0]
    ext = shapely.Polygon(g.exterior)
    holes = sorted([shapely.Polygon(r) for r in g.interiors], key=lambda q: -q.area)
    b0 = base_under(ctx, g, 0.3)
    cx, cy, L, Wd, ang = rect_of(ext)
    fr = Frame(cx, cy, b0, ang)
    court = holes[0] if holes else None
    if court is not None and fr.uv(*court.centroid.coords[0])[1] > 0:
        fr = Frame(cx, cy, b0, ang + math.pi)   # +v: away from the court, towards the 1913 front
    ev = fr.uv(*np.array(ext.exterior.coords).T)
    v_front = float(ev[1].max())
    split = (float(fr.uv(*np.array(court.exterior.coords).T)[1].max()) + 3.0) if court is not None else 0.0
    stone, stone2, rust = P("#d9d4c7"), P("#c8c1b2"), P("#bdb5a5")
    yel, yel2, white = P("#e4b94f"), P("#d7a940"), P("#f0ebdf")
    slate, slate2, copper = P("#4f565d", ROOF), P("#646a6f", ROOF), P("#6f9c8a", ROOF)
    win = P("#2f3540", WINDOW)
    HW = 14.5

    def walls(x, y, w):
        vv = -(x - fr.ox) * fr.sa + (y - fr.oy) * fr.ca
        h = w - b0
        st = vv > split
        base = np.where(st, np.where((h < 5.0) & (np.mod(h, 0.9) < 0.18), rust, stone), yel)
        band = (h > HW - 0.7) | ((h > 5.0) & (h < 5.5))
        return np.where(band, np.where(st, stone2, white), base).astype(np.uint16)
    S.add(Poly(g, b0 - 2, b0 + HW, walls))
    windows(S, g, b0, [(1.2, 4.6), (6.6, 11.6)], [stone, yel], win, every=3.8, half=0.85, min_len=5.0)
    # roofs: hipped over every range, from the distance to the walls
    x0f, y0f, X, Y = grid_of(g, 1.0)
    d = dist_in(g, X, Y)
    V = (-(X - fr.ox) * fr.sa + (Y - fr.oy) * fr.ca).astype(np.float32)
    fields = dict(d=d, V=V)

    def roof_fn(f, wa):
        d_, vv = f["d"][None], f["V"][None]
        zt = b0 + HW + np.minimum(d_ - 0.4, 6.5) * 0.75
        m = (d_ > 0.4) & (wa >= b0 + HW) & (wa < zt)
        par = (d_ > 0) & (d_ <= 0.6) & (wa >= b0 + HW) & (wa < b0 + HW + 1.1) & ((np.mod(wa * 2, 2) < 1) | (wa > b0 + HW + 0.8))
        col = np.where(vv > split, slate, slate2)
        return np.where(m, col, np.where(par, np.where(vv > split, stone2, white), 0)).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 + HW, b0 + HW + 6.0, roof_fn))

    def dome_at(u, v, r, top_r=None, col=slate):
        fd = fr.at(u, v)
        S.add(Lathe(fd, HW - 1.0, HW + 3.4, cyl(r), stone, n=16))
        for k in range(8):
            S.add(Arch(fd.at(turn=TAU * k / 8), r - 0.6, r + 0.3, 0, 0.55, HW + 0.4, HW + 2.2, win, mode="paint", targets=[stone]))
        S.add(Lathe(fd, HW + 3.4, HW + 4.0, cyl(r + 0.4), stone2, n=16))
        S.add(Lathe(fd, HW + 4.0, HW + 4.0 + r * 1.3, dome(r, 1.7, r * 0.22), col, n=16))
        for k in range(8):
            fk = fd.at(turn=TAU * k / 8)
            S.add(Capsule(fk, (r - 0.1, 0, HW + 4.2), (r * 0.3, 0, HW + 3.9 + r * 1.2), 0.22, stone2))
        zl = HW + 4.0 + r * 1.25
        S.add(Lathe(fd, zl, zl + r * 0.35, cyl(r * 0.22), stone, n=8))
        S.add(Lathe(fd, zl + r * 0.35, zl + r * 0.6, dome(r * 0.27, 2.0), col, n=8))
        S.add(Lathe(fd, zl + r * 0.55, zl + r * 0.55 + 2.0, cyl(0.12), P("#c9a34e", METAL)))
    # the 1913 front: the entrance hall's dome in the middle, a dome over each corner pavilion
    us = ev[0][ev[1] > v_front - 6]
    u0, u1 = (float(us.min()), float(us.max())) if len(us) else (-L / 2, L / 2)
    dome_at((u0 + u1) / 2, v_front - 13.0, 8.5)
    for uc in (u0 + 10.0, u1 - 10.0):
        dome_at(uc, v_front - 10.0, 5.8)
    if court is not None:  # two small domes over the court's corners, the yellow side
        cu, cvv = fr.uv(*np.array(court.exterior.coords).T)
        for uc in (float(cu.min()) - 4.0, float(cu.max()) + 4.0):
            dome_at(uc, float(cvv.min()) - 5.0, 3.6, col=copper)
    # the portico before the entrance
    fe = fr.at((u0 + u1) / 2, v_front)
    for k in range(-2, 3):
        if k:
            S.add(Lathe(fe.at(0, 1.2, 0).at(k * 2.6, 0), 0, 10.5, cyl(0.45), stone))
    S.add(Box(fe, -6.4, 6.4, -0.2, 2.0, 10.5, 11.8, stone2))
    S.add(Box(fe, -6.4, 6.4, -0.2, 2.0, 11.8, 13.0, stone))
    S.add(Roof(fe.at(0, 1.0, 0, math.pi / 2), -1.3, 1.3, -6.8, 6.8, 13.0, 2.6, stone))
    S.add(Arch(fe.at(0, 0, 0, math.pi / 2), -1.0, 0.8, 0, 1.8, 0, 4.8, P("#4f3d2e"), mode="paint", targets=[stone, rust]))
    # the pools: a 50 m swimming pool between two warm pools, in white stone rims
    if court is not None:
        pcx, pcy, pL, pW, pang = rect_of(court)
        fp = Frame(pcx, pcy, b0, pang)
        rim, water, pave = P("#eeebe3"), C["pool"], P("#cfc9bd")
        S.add(Poly(court, b0 - 0.6, b0, pave))
        a = min(pL * 0.19, 26.0)
        bw = min(pW * 0.22, 11.0)
        for (pu, hu, hv, rnd) in ((0.0, a, bw, False), (-(a + pL * 0.15), pL * 0.12, bw * 0.85, True),
                                  (a + pL * 0.15, pL * 0.12, bw * 0.85, True)):
            fq = fp.at(pu)
            S.add(Box(fq, -hu - 0.6, hu + 0.6, -hv - 0.6, hv + 0.6, -0.6, 0.25, rim))
            S.add(Box(fq, -hu, hu, -hv, hv, -1.6, 0.4, 0, mode="carve"))
            S.add(Box(fq, -hu, hu, -hv, hv, -1.6, -0.25, water))
            if rnd:
                for su in (-1, 1):
                    fc = fq.at(su * hu)
                    S.add(Lathe(fc, -0.6, 0.25, cyl(hv + 0.6), rim))
                    S.add(Lathe(fc, -1.6, 0.4, cyl(hv), 0, mode="carve"))
                    S.add(Lathe(fc, -1.6, -0.25, cyl(hv), water))
                    S.add(Lathe(fq.at(su * hu * 0.2), -0.3, 0.6, cyl(1.2), rim))


# ------------------------------------------------------------------------------------------------ the Ethnography museum
def neprajzi(S, ctx, plan):
    """the Museum of Ethnography in the City Park (Marcel Ferencz, Napur Architect, 2022): two wings that dip towards
    the gap between them, where the park's path passes through onto 56-osok tere, and rise outwards like ramps, their
    curved roofs a public garden. The raised outer ends are clad in a white metal grille whose pixels draw folk motifs;
    glass under them."""
    P, area = ctx["P"], ctx["area"]
    g = area[NEPRAJZI][3]
    wings = sorted(getattr(g, "geoms", [g]), key=lambda q: -q.area)[:2]
    b0 = base_under(ctx, g, 0.4)
    mid = shapely.union_all(wings).centroid if len(wings) < 2 else LineString([w.centroid for w in wings]).centroid
    grass, grass2, gravel = P("#6f9a4c", GRASS), P("#628c43", GRASS), P("#cfc8b6")
    px = np.array([P("#e6e5df"), P("#cfcdc6"), P("#a9a79f"), P("#7f7d77")], np.uint16)
    glass, parapet, conc = P("#56707e", WINDOW), P("#f1f0ec"), P("#bdb9b0")
    for wp in wings:
        cx, cy, L, Wd, ang = rect_of(wp)
        fw = Frame(cx, cy, b0, ang)
        if len(wings) > 1:  # each wing rises away from the gap between them, its high end at the building's outer edge
            fw = facing(fw, (2 * cx - mid.x, 2 * cy - mid.y))
        x0f, y0f, X, Y = grid_of(wp, 1.5)
        d = dist_in(wp, X, Y)
        U = ((X - cx) * fw.ca + (Y - cy) * fw.sa).astype(np.float32)
        V = (-(X - cx) * fw.sa + (Y - cy) * fw.ca).astype(np.float32)
        t = np.clip((U + L / 2) / L, 0, 1)
        z = (1.0 + 21.5 * t ** 2.6).astype(np.float32)
        fields = dict(d=d, U=U, V=V, z=z, t=t.astype(np.float32))

        def fn(f, wa, L=L):
            d_, U_, V_, z_, t_ = (f[k][None] for k in ("d", "U", "V", "z", "t"))
            h = wa - b0
            body = (d_ > 0) & (h <= z_)
            top = body & (h > z_ - 0.9)
            rail = (d_ > 0) & (d_ < 0.5) & (h > z_) & (h <= z_ + 1.1)
            side = body & (d_ < 1.0)
            along = np.where(np.abs(U_) > L / 2 - 1.2, V_, U_)
            pix = np.floor(along / 1.0).astype(np.int64) * 7 + np.floor(h / 1.0).astype(np.int64) * 3
            motif = np.mod(np.abs(np.floor(along / 1.0)).astype(np.int64) * 2 + np.floor(h / 1.0).astype(np.int64) * 3
                           + (np.mod(np.floor(along / 4.0) + np.floor(h / 4.0), 2) * 2).astype(np.int64), 4)
            facade = px[np.where(np.mod(pix, 5) == 0, 3, motif)]
            low = side & (h < 6.5) & (t_ > 0.6)
            end = side & (U_ > L / 2 - 1.2) & (h < 8.0)
            path = np.mod(U_ * 0.45 + V_ * 0.8, 10.0) < 1.6
            roofc = np.where(path, gravel, np.where(np.mod(np.floor(U_ / 2) + np.floor(V_ / 2), 2) == 0, grass, grass2))
            col = np.where(top & ~side, roofc, np.where(low | end, glass, np.where(side, facade, conc)))
            col = np.where(rail, parapet, np.where(body, col, 0))
            return col.astype(np.uint16)
        S.add(Field(x0f, y0f, fields, b0 - 1, b0 + 24.5, fn))


# ------------------------------------------------------------------------------------------------ the stations
class Gable(Prim):
    """a wall over [u0, u1] x [-a, a]: a rectangle up to w0 and a half-ellipse h high above it (an arched gable)."""

    def __init__(self, fr, u0, u1, a, wb, w0, h, col, **kw):
        self.p = (u0, u1, a, wb, w0, h)
        super().__init__(fr, col, (u0, u1, -a, a, wb, w0 + h), **kw)

    def inside(self, u, v, w, x, y):
        u0, u1, a, wb, w0, h = self.p
        top = w0 + h * np.sqrt(np.clip(1 - (v / a) ** 2, 0, 1))
        return (u >= u0) & (u < u1) & (np.abs(v) <= a) & (w >= wb) & (w < top)


def pavilion(S, fr, hu, hv, H, wall, trim, roofc, metal, win):
    """a corner pavilion: walls to H with a cornice, windows, a mansard and a lantern."""
    S.add(Box(fr, -hu, hu, -hv, hv, -1, H, wall))
    S.add(Box(fr, -hu - 0.3, hu + 0.3, -hv - 0.3, hv + 0.3, H - 0.8, H, trim))
    S.add(TBox(fr, hu, hv, hu * 0.55, hv * 0.55, H, H + 6.0, roofc))
    S.add(Box(fr, -hu * 0.55, hu * 0.55, -hv * 0.55, hv * 0.55, H + 6.0, H + 6.4, metal))
    S.add(Lathe(fr, H + 6.4, H + 8.4, cone(0.8, 0.1), metal, n=4, rot=math.pi / 4))
    for k in range(4):
        fk = fr.at(turn=k * math.pi / 2)
        r = hu if k % 2 == 0 else hv
        for wl in (3.0, 9.5, 15.5):
            if wl + 3.5 < H - 1:
                S.add(Arch(fk, r - 0.4, r + 0.3, 0, 0.9, wl, wl + 2.8, win, mode="paint", targets=[wall]))


def keleti(S, ctx, plan):
    """Keleti pályaudvar (Gyula Rochlitz, János Feketeházy, 1884): a 180 m iron and glass train shed under a round
    roof, 44 m across; its end on Baross tér a great arched window framed by pilasters, a clock and a sculpture group
    on top, between two pavilions with James Watt and George Stephenson in niches; the far end glazed over the
    tracks."""
    P, area = ctx["P"], ctx["area"]
    shed = area[KELETI_SHED][3]
    cx, cy, L, Wd, ang = rect_of(shed)
    b0 = base_under(ctx, shed, 0.4)
    fr = Frame(cx, cy, b0, ang)
    if rails_of(ctx, fr.xy(L / 2 + 40, 0), 30) > rails_of(ctx, fr.xy(-L / 2 - 40, 0), 30):
        fr = Frame(cx, cy, b0, ang + math.pi)   # +u: the head, on Baross tér; the tracks leave at -u
    hv, WALL, RISE = Wd / 2, 18.0, 13.0
    cream, cream2, trim = P("#e5d09d"), P("#d6bf88"), P("#f1e9d3")
    roofc, iron, glass = P("#6f6a5e", ROOF), P("#4a5458", METAL), P("#b9c6ca", GLASS)
    win, metal, statue_c = P("#2f3439", WINDOW), P("#9aa6a2", METAL), P("#d9d2c1")

    def vault_col(u, v, w):
        rib = np.mod(u, 6.5) < 0.6
        sky = np.abs(v) < hv * 0.42
        return np.where(rib, iron, np.where(sky, glass, roofc)).astype(np.uint16)
    for sv in (-1, 1):
        S.add(Box(fr, -L / 2, L / 2, *sorted((sv * (hv - 1.0), sv * hv)), -1, WALL, cream))
        S.add(Box(fr, -L / 2, L / 2, *sorted((sv * (hv - 1.2), sv * (hv + 0.3))), WALL - 0.8, WALL, trim))
    S.add(Vault(fr, -L / 2 + 1.0, L / 2 - 1.0, hv + 0.3, WALL, RISE, 0.7, vault_col))

    def window_col(u, v, w):
        mull = (np.mod(v + 0.6, 2.6) < 0.35) | (np.mod(w - WALL, 3.2) < 0.3)
        return np.where(mull, iron, glass).astype(np.uint16)
    # the head on Baross tér
    uh = L / 2
    S.add(Gable(fr, uh - 1.4, uh + 0.6, hv + 1.0, -1, WALL, RISE + 3.0, cream))
    S.add(Gable(fr, uh - 1.5, uh, hv - 3.5, 7.5, WALL - 4.0, RISE + 1.5, 0, mode="carve"))
    S.add(Gable(fr, uh + 0.0, uh + 0.7, hv - 3.5, 7.5, WALL - 4.0, RISE + 1.5, window_col))
    S.add(Gable(fr, uh + 0.6, uh + 1.0, hv - 2.5, 7.0, WALL - 4.0, RISE + 2.5, trim, mode="under"))
    S.add(Gable(fr, uh + 0.6, uh + 1.1, hv - 3.5, 7.5, WALL - 4.0, RISE + 1.5, 0, mode="carve"))
    for vc in (-9.0, 0.0, 9.0):
        S.add(Arch(fr.at(uh), -1.6, 1.2, vc, 2.3, -0.5, 4.2, mode="carve"))
        S.add(Box(fr, uh - 1.6, uh - 1.3, vc - 2.3, vc + 2.3, 0, 6.5, P("#5b4836"), mode="under"))
    for sv in (-1, 1):
        S.add(Box(fr, uh - 0.2, uh + 1.4, *sorted((sv * (hv - 3.3), sv * (hv - 1.0))), -1, WALL + 2.0, trim))
        S.add(Box(fr, uh - 0.2, uh + 1.6, *sorted((sv * (hv - 3.5), sv * (hv - 0.8))), WALL + 2.0, WALL + 3.0, cream2))
        statue(S, fr.at(uh + 0.6, sv * (hv - 2.2)), WALL + 3.0, statue_c, 1.3)
    S.add(Box(fr, uh - 1.0, uh + 1.2, -4.5, 4.5, WALL + RISE + 1.0, WALL + RISE + 5.0, cream))
    S.add(Roof(fr.at(uh, 0, 0, math.pi / 2), -4.8, 4.8, -1.3, 1.5, WALL + RISE + 5.0, 2.2, trim))
    S.add(Ellipsoid(fr.at(uh + 1.25, 0, WALL + RISE + 2.6), 0.15, 1.5, 1.5, P("#f4f2ea")))
    S.line(fr, (uh + 1.4, 0, WALL + RISE + 2.6), (uh + 1.4, 0, WALL + RISE + 3.7), P("#222428"))
    S.line(fr, (uh + 1.4, 0, WALL + RISE + 2.6), (uh + 1.4, 0.8, WALL + RISE + 2.6), P("#222428"))
    for k in (-1, 0, 1):
        statue(S, fr.at(uh + 0.2, k * 2.0), WALL + RISE + 7.2, statue_c, 1.2 if k == 0 else 1.0)
    # the far end, glazed over the tracks
    S.add(Gable(fr, -uh - 0.4, -uh + 0.6, hv - 0.5, WALL - 2.0, WALL, RISE - 0.5, window_col))
    S.add(Box(fr, -uh - 0.4, -uh + 0.6, -hv, hv, WALL - 2.0, WALL, trim))
    # the corner pavilions (OSM's parts, drawn here with their mansards and lanterns)
    for pid in KELETI_PAV:
        if pid in area:
            pc = area[pid][3]
            px_, py_, pL, pW, pa = rect_of(pc)
            fp = Frame(px_, py_, b0, pa)
            pavilion(S, fp, pL / 2, pW / 2, 22.0, cream, trim, roofc, metal, win)
            pu, pv = fr.uv(*np.array(pc.exterior.coords).T)
            if pu.max() > uh - 3:  # Watt and Stephenson in niches, facing the square
                fs = fr.at(float(pu.max()), float(pv.mean()))
                S.add(Arch(fs, -1.0, 0.4, 0, 1.4, 5.5, 10.5, mode="carve"))
                statue(S, fs.at(-0.6), 5.6, P("#7a6c55", METAL), 1.4)


def nyugati(S, ctx, plan):
    """Nyugati pályaudvar (August de Serres for the Eiffel company, 1877): the iron train shed opens onto Teréz körút
    through a great glazed gable in a blue-grey iron frame, between two stone towers with domed caps; inside it the
    tracks run up to the street. A gabled roof of slate with a glazed ridge."""
    P, area = ctx["P"], ctx["area"]
    shed = area[NYUGATI_SHED][3]
    cx, cy, L, Wd, ang = rect_of(shed)
    b0 = base_under(ctx, shed, 0.4)
    fr = Frame(cx, cy, b0, ang)
    if rails_of(ctx, fr.xy(L / 2 + 40, 0), 30) > rails_of(ctx, fr.xy(-L / 2 - 40, 0), 30):
        fr = Frame(cx, cy, b0, ang + math.pi)   # +u: the street end
    hv, EAVE, RISE = Wd / 2, 16.0, 13.5
    iron, iron2, glass = P("#7d909c", METAL), P("#5f727e", METAL), P("#a7bcc6", GLASS)
    slate, stone, stone2 = P("#5d666e", ROOF), P("#e8dcc2"), P("#cdbd9c")
    win, metal, statue_c = P("#2f3439", WINDOW), P("#a3aeb3", METAL), P("#d9d2c1")

    def roof_col(u, v, w):
        rib = np.mod(u, 7.5) < 0.6
        sky = np.abs(v) < hv * 0.36
        return np.where(rib, iron2, np.where(sky, glass, slate)).astype(np.uint16)
    for sv in (-1, 1):
        S.add(Box(fr, -L / 2, L / 2, *sorted((sv * (hv - 1.0), sv * hv)), -1, EAVE, stone))
    S.add(Roof(fr, -L / 2, L / 2, -hv - 0.6, hv + 0.6, EAVE, RISE, roof_col))
    S.add(Roof(fr, -L / 2 + 1.0, L / 2 - 1.0, -hv + 0.4, hv - 0.4, EAVE, RISE - 1.0, 0, mode="carve"))

    def front_col(u, v, w):
        frame_ = (np.abs(v) > hv - 1.4) | (w < 1.0)
        mull = (np.mod(v + 0.4, 3.0) < 0.4) | (np.mod(w, 3.6) < 0.35)
        big = (np.mod(v + 7.5, 15.0) < 0.9) | (np.abs(w - EAVE) < 0.6)
        return np.where(frame_ | big, iron2, np.where(mull, iron, glass)).astype(np.uint16)
    uh = L / 2
    S.add(Box(fr, uh - 1.0, uh, -hv, hv, -1, EAVE, front_col))
    S.add(Roof(fr, uh - 1.0, uh, -hv, hv, EAVE, RISE, front_col))
    S.add(Roof(fr, uh - 0.3, uh + 0.6, -hv - 0.8, hv + 0.8, EAVE + 0.2, RISE + 0.4, iron2))
    S.add(Roof(fr, uh - 0.4, uh + 0.7, -hv + 0.4, hv - 0.4, EAVE - 0.3, RISE - 0.6, 0, mode="carve"))
    for vc in (-6.0, 0.0, 6.0):
        S.add(Box(fr, uh - 1.2, uh + 0.2, vc - 2.0, vc + 2.0, 0, 4.6, 0, mode="carve"))
    S.add(Box(fr, uh - 0.2, uh + 1.4, -hv, hv, 4.6, 5.4, iron2))
    S.add(Box(fr, -uh, -uh + 1.0, -hv, hv, EAVE - 3.0, EAVE, front_col))
    S.add(Roof(fr, -uh, -uh + 1.0, -hv, hv, EAVE, RISE, front_col))
    # the towers either side of the gable, with domed caps, and statues on the corners
    for sv in (-1, 1):
        ft = fr.at(uh - 3.6, sv * (hv + 3.8))
        S.add(Box(ft, -3.6, 3.6, -3.6, 3.6, -1, 24.0, stone))
        S.add(Box(ft, -3.9, 3.9, -3.9, 3.9, 23.2, 24.0, stone2))
        for wl in (3.0, 9.0, 15.0):
            S.add(Arch(ft, 3.3, 4.0, 0, 1.0, wl, wl + 3.2, win, mode="paint", targets=[stone]))
        S.add(Lathe(ft, 24.0, 25.6, cyl(3.4), stone, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 25.6, 30.6, dome(3.5, 2.0, 0.4), metal, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 30.4, 32.6, cone(0.5, 0.08), metal))
        for su in (-1, 1):
            statue(S, ft.at(su * 3.2, sv * 3.2), 24.0, statue_c, 1.1)
    S.add(Box(fr, uh - 0.8, uh + 0.8, -2.0, 2.0, EAVE + RISE - 0.5, EAVE + RISE + 2.2, iron2))
    S.add(Ellipsoid(fr.at(uh + 0.9, 0, EAVE + RISE - 4.0), 0.15, 1.6, 1.6, P("#f4f2ea")))
    S.line(fr, (uh + 1.05, 0, EAVE + RISE - 4.0), (uh + 1.05, 0, EAVE + RISE - 2.8), P("#222428"))
    S.line(fr, (uh + 1.05, 0, EAVE + RISE - 4.0), (uh + 1.05, 0.9, EAVE + RISE - 4.0), P("#222428"))


# ------------------------------------------------------------------------------------------------ registry
BUILDERS = [("Budapest Eye", big_wheel), ("Soviet War Memorial", soviet_memorial),
            ("Ferencváros Church", ferencvaros_church), ("Bálna", balna), ("Hungarian State Opera", opera),
            ("Zoo: Great Rock and Elephant House", zoo), ("Széchenyi Baths", szechenyi),
            ("Museum of Ethnography", neprajzi), ("Keleti Station", keleti), ("Nyugati Station", nyugati)]
