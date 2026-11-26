"""Late November 2026, fifth round, Margaret Island (on the map since it grew to the north): the Water Tower and the
open-air stage, the Palatinus's 1937 entrance building, the Hajós Alfréd pool, the Musical Fountain and the Centenary
Monument, the Premonstratensian chapel, the Bodor musical well, the Japanese Garden, the Thermal and Grand hotels, and
the girders and piers of Árpád Bridge. Outlines from OSM; heights, colours and details from the Esri aerial and street
photos (docs/landmarks.md)."""
import math

import numpy as np
import shapely
from scipy import ndimage

from landmarks import Box, Capsule, Ellipsoid, Frame, Lathe, Roof, cone, cyl, dome, rect_of
from landmarks_city import base_under
from landmarks_hosok import keep
from landmarks_kit import largest, painted, styled
from style import CONCRETE, GLASS, METAL, ROOF, WATER
from landmarks import WINDOW

TOWER, STAGE, STAGE_SHELL, STAGE_WALK = 135302046, 47427584, 813395900, 1330598328
PALATINUS = 1061197388
HAJOS_HALL, HAJOS_1937, HAJOS_SMALL, HAJOS_POOL = 48456825, 904458843, 1228624128, 48456801
HAJOS_STANDS = (904458841, 904458842, 679081744, 904458839)
HAJOS_DOMES = (196947633, 207583997, 48456808)
FOUNTAIN, MONUMENT = (6083.0, 1435.0), (6024.0, 1487.0)
CHAPEL = 47428762
BODOR = 204319255
POND = 265323814
HOTEL, HOTEL_SLAB, GRAND = 47425748, 1421698057, 196947632
THERMAL = ((1421698057, 30.0), (1421698058, 10.0), (343640562, 8.0), (1432414671, 5.0), (1421698059, 5.0), (19451507, 4.0))
ARPAD = 197112157

NAMES = ["Margaret Island Water Tower", "Palatinus Baths", "Hajós Alfréd pool", "Musical Fountain and Centenary Monument",
         "Premonstratensian chapel", "Bodor musical well", "Japanese Garden", "Thermal and Grand hotels", "Árpád Bridge"]
DROP = {TOWER, STAGE, STAGE_SHELL, STAGE_WALK, PALATINUS, HAJOS_HALL, HAJOS_1937, HAJOS_SMALL, *HAJOS_STANDS, CHAPEL,
        BODOR, HOTEL, GRAND, *(i for i, _ in THERMAL)}
KEEP = [(TOWER, 20), (STAGE, 14), (PALATINUS, 12), (HAJOS_HALL, 16), (HOTEL, 30), (GRAND, 20), (CHAPEL, 12)]
TAU = 2 * math.pi


def area(ctx, oid):
    try:
        return largest(keep(ctx, oid))
    except KeyError:
        return None


# ------------------------------------------------------------------------------------------------ the Water Tower
def tower(S, ctx, plan):
    """the Water Tower (Szilárd Zielinski and Rezső Ray, 1911): 57 m of reinforced concrete, an octagonal shaft in cream
    with ochre pilasters at its corners and slit windows, widening at the top into the tank storey with eight bay
    windows round the lookout, under a green copper roof and lantern; beside it the open-air stage (1938, rebuilt):
    a fan of seats rising from the stage under its white shell towards the tower, a roofed walk round the tower's foot."""
    P = ctx["P"]
    g = keep(ctx, TOWER)
    c = g.centroid
    b0 = base_under(ctx, g, 0.3)
    cream, ochre, win, copper, copper2 = P("#ece3cf"), P("#c98a4b"), P("#33404a", WINDOW), P("#5f8f7c", METAL), P("#4d7b69", METAL)
    white = P("#f2f1ec")
    ft = Frame(c.x, c.y, b0, 0.0)
    rot = math.pi / 8

    def shaft(u, v, w):
        a = np.mod(np.arctan2(v, u) - rot, TAU / 8)
        corner = np.minimum(a, TAU / 8 - a) < 0.09
        z = w
        slit = (np.abs(a - TAU / 16) < 0.05) & (np.mod(z, 7.0) > 2.0) & (np.mod(z, 7.0) < 5.5) & (z > 4)
        return np.where(corner, ochre, np.where(slit, win, cream)).astype(np.uint16)
    S.add(Lathe(ft, -2, 38.0, cone(6.6, 6.0), shaft, n=8, rot=rot))
    S.add(Lathe(ft, 38.0, 40.0, cone(6.0, 7.6), ochre, n=8, rot=rot))  # the corbel under the tank storey

    def tank(u, v, w):
        a = np.mod(np.arctan2(v, u) - rot, TAU / 8)
        z = w
        bay = (np.abs(a - TAU / 16) < 0.22) & (z > 43.5) & (z < 48.5)
        return np.where(bay, win, np.where(np.minimum(a, TAU / 8 - a) < 0.08, ochre, cream)).astype(np.uint16)
    S.add(Lathe(ft, 40.0, 50.0, cyl(7.6), tank, n=8, rot=rot))
    S.add(Lathe(ft, 50.0, 50.8, cyl(8.1), ochre, n=8, rot=rot))
    S.add(Lathe(ft, 50.8, 54.5, cone(7.9, 2.6), copper, n=8, rot=rot))
    S.add(Lathe(ft, 54.5, 56.2, cyl(1.7), copper2, n=8, rot=rot))
    S.add(Lathe(ft, 56.2, 57.6, cone(1.9, 0.1), copper, n=8, rot=rot))
    for k in range(8):  # the eight balconies of the lookout
        fk = ft.at(turn=rot + TAU / 16 + k * TAU / 8)
        S.add(Box(fk, 7.4, 8.6, -1.6, 1.6, 43.0, 43.4, white))
        S.add(Box(fk, 8.4, 8.6, -1.6, 1.6, 43.4, 44.4, white))
    S.clear.append((c.x, c.y, 10.0))
    # the open-air stage
    gs = area(ctx, STAGE)
    shell = area(ctx, STAGE_SHELL)
    if gs is not None and shell is not None:
        stage = shell.centroid
        sb = base_under(ctx, gs, 0.2)
        seat, riser, aisle = P("#bdb9b0", CONCRETE), P("#8f8b84", CONCRETE), P("#d9d4c8", CONCRETE)
        seats = gs.difference(shell.buffer(1.5))

        def fn(f, hw):
            r = np.hypot(f["X"] - stage.x, f["Y"] - stage.y)
            k = np.floor(np.maximum(r - 17.0, 0) / 0.9)
            top = np.minimum(k * 0.42, 11.0)
            inside = f["d"] > 0
            ang = np.arctan2(f["Y"] - stage.y, f["X"] - stage.x)
            col = np.where(np.mod(k, 2) == 0, seat, riser)
            col = np.where(np.abs(np.mod(ang * 9.0, 1.0) - 0.5) < 0.05, aisle, col)
            o = np.where(inside & (hw < top + 0.2), col, 0)
            return np.where(inside & (f["d"] < 0.6) & (hw < top + 1.2), aisle, o)
        painted(S, largest(seats) if seats.geom_type == "MultiPolygon" else seats, sb, 13.0, fn)
        dmax = max(rect_of(shell)[3] / 2, 6.0)

        def fs(f, hw):
            z = 3.5 + 11.0 * np.sqrt(np.clip(f["d"] / dmax, 0, 1))
            o = np.where((f["d"] > 0) & (np.abs(hw - z) < 0.45), white, 0)
            return np.where((f["d"] > 0) & (hw < 1.2), riser, o)
        painted(S, shell, sb, 15.5, fs)
    walk = area(ctx, STAGE_WALK)
    if walk is not None:
        wb = base_under(ctx, walk, 0.3)

        def fw(f, hw):
            o = np.where((f["d"] > 0) & (hw >= 4.4) & (hw < 5.0), white, 0)
            col = (f["d"] > 0) & (f["d"] < 0.6) & (np.mod(f["s"], 6.0) < 0.6) & (hw < 4.4)
            return np.where(col, cream, o)
        painted(S, walk.difference(g.buffer(1.0)), wb, 5.2, fw)


# ------------------------------------------------------------------------------------------------ the Palatinus
def palatinus(S, ctx, plan):
    """the Palatinus's entrance and changing block (István Janáky and Károly Szőke, 1937): long and white, two storeys
    of ribbon windows under roof terraces glazed in a sawtooth, bending at its eastern end; restored in 2017-19."""
    P = ctx["P"]
    g = area(ctx, PALATINUS)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    white, white2, win, glass, frame = P("#f3f1ea"), P("#dedbd2"), P("#3a4a52", WINDOW), P("#8fb3bf", GLASS), P("#c9cbc8", METAL)
    _, _, _, _, ang = rect_of(g)
    E = 8.5

    def fn(f, hw):
        d, s = f["d"], f["s"]
        inside, edge = d > 0, (d > 0) & (d < 0.8)
        u = f["X"] * math.cos(ang) + f["Y"] * math.sin(ang)
        rib = np.mod(hw, 4.0)
        wall = np.where((rib > 1.1) & (rib < 3.2) & (hw < E - 0.8), win, np.where(np.mod(hw, 4.0) < 0.3, white2, white))
        wall = np.where((hw < 3.2) & (np.mod(s, 6.0) < 0.7), white2, wall)
        o = np.where(edge & (hw < E), wall, 0)
        saw = E - 0.4 + 1.6 * np.mod(u, 3.0) / 3.0
        roof = np.where(np.mod(u, 3.0) < 0.3, frame, glass)
        o = np.where(inside & ~edge & (hw >= E - 0.6) & (hw < saw), roof, o)
        return np.where(edge & (hw >= E) & (hw < E + 1.0), white, o)
    painted(S, g, b0, E + 1.6, fn)


# ------------------------------------------------------------------------------------------------ the Hajós pool
def hajos(S, ctx, plan):
    """the Alfréd Hajós National Swimming Stadium: Hajós's indoor hall (1930) behind a brown clinker-brick front with
    tall windows over its concrete arches, the clinker-brick colonnade of the outdoor pool (1937), the 50 m pool's
    stands in blue seats on both sides, and the white air domes over the training pools."""
    P = ctx["P"]
    brick, brick2, win, slate = P("#8a4a36"), P("#a35b42"), P("#33404a", WINDOW), P("#7d8082", ROOF)
    blue, white, step = P("#2f6db5"), P("#f1f1ee"), P("#b9b6ae", CONCRETE)
    g = area(ctx, HAJOS_HALL)
    if g is not None:
        styled(S, g, base_under(ctx, g, 0.3), 15.0, brick, win, slate, floor=5.0, gf=5.0, bay=4.2, winw=2.6, sill=0.8,
               head=4.6, roof_kind="hip", slope=0.35, ridge=4.0, band=brick2, band_every=None)
    for oid, E in ((HAJOS_1937, 8.0), (HAJOS_SMALL, 5.0)):
        g = area(ctx, oid)
        if g is not None:
            styled(S, g, base_under(ctx, g, 0.3), E, brick, win, step, floor=4.0, gf=4.0, bay=3.2, winw=1.8, pier=brick2)
    pool = area(ctx, HAJOS_POOL)
    for oid in HAJOS_STANDS:
        g = area(ctx, oid)
        if g is None:
            continue
        sb = base_under(ctx, g, 0.3)
        near = pool if pool is not None else g.centroid.buffer(1)

        def fn(f, hw, near=near):
            r = shapely.distance(near, shapely.points(f["X"][0].ravel(), f["Y"][0].ravel())).reshape(f["X"].shape)
            k = np.floor(np.maximum(r - 2.0, 0) / 0.85)
            top = np.minimum(k * 0.45, 8.0)
            inside = f["d"] > 0
            return np.where(inside & (hw < top), np.where(np.mod(k, 2) == 0, blue, step), 0)
        painted(S, g, sb, 9.0, fn)
    for oid in HAJOS_DOMES:
        g = area(ctx, oid)
        if g is None:
            continue
        db = base_under(ctx, g, 0.3)
        half = rect_of(g)[3] / 2
        H = min(12.0, half * 0.65)

        def fd(f, hw, H=H, half=half):
            z = H * np.sqrt(np.clip(f["d"] / half, 0, 1) * (2 - np.clip(f["d"] / half, 0, 1)))
            return np.where((f["d"] > 0) & (hw < z) & (hw > z - 0.6), white, 0)
        painted(S, g, db, H + 0.5, fd)


# ------------------------------------------------------------------------------------------------ fountain and monument
def fountain(S, ctx, plan):
    """the Musical Fountain (1962, rebuilt 2013): a round basin 36 m across, a ring of jets round a tall middle one and
    four nozzle pods; in the lawn to its south-west the Centenary Monument (István Kiss, 1972): open bronze flames
    twisted into a tall calyx."""
    P = ctx["P"]
    stone, water, jet, bronze = P("#d6d1c4"), P("#5b9bb0", WATER), P("#d8eef2", WATER), P("#7a5a3a", METAL)
    x, y = FOUNTAIN
    b0 = ctx["ground_m"](x, y)
    ff = Frame(x, y, b0, 0.0)
    S.add(Lathe(ff, -0.3, 0.6, cyl(18.2), stone, n=48, inner=0.8))
    S.add(Lathe(ff, -0.3, 0.2, cyl(17.4), water, n=48))
    S.add(Lathe(ff, -0.3, 0.7, cyl(8.2), stone, n=40, inner=0.7))
    for k in range(16):
        fk = ff.at(turn=k * TAU / 16).at(7.6)
        S.add(Lathe(fk, 0.2, 3.5 + 1.5 * (k % 2), cone(0.25, 0.1), jet, n=6))
    S.add(Lathe(ff, 0.2, 8.0, cone(0.6, 0.15), jet, n=8))
    for k in range(4):
        fk = ff.at(turn=math.pi / 4 + k * math.pi / 2).at(11.5)
        S.add(Lathe(fk, -0.3, 0.9, cyl(1.4), stone, n=12))
        S.add(Lathe(fk, 0.9, 3.0, cone(0.4, 0.1), jet, n=6))
    mx, my = MONUMENT
    fm = Frame(mx, my, ctx["ground_m"](mx, my), 0.0)
    S.add(Lathe(fm, -0.3, 0.8, cyl(2.0), stone, n=12))
    S.add(Lathe(fm, 0.8, 1.6, cyl(1.5), bronze, n=12))
    for k in range(8):  # eight bronze ribs swelling into a calyx 13 m tall, twisting as they rise
        a0 = k * TAU / 8
        pts = []
        for i in range(12):
            t = i / 11
            r = 1.1 + 1.7 * math.sin(math.pi * min(t / 0.8, 1.0)) ** 0.8 - 0.4 * t
            a = a0 + t * 0.9
            pts.append((r * math.cos(a), r * math.sin(a), 1.6 + t * 11.4))
        for p0, p1 in zip(pts, pts[1:]):
            S.add(Capsule(fm, p0, p1, 0.42, bronze))
    S.clear.append((mx, my, 5.0))


# ------------------------------------------------------------------------------------------------ the chapel
def chapel(S, ctx, plan):
    """the Premonstratensian chapel of St Michael: rebuilt in 1930-32 on its 12th-century walls, a small Romanesque nave
    of rough grey stone under a red tile roof, with the little belfry on the west gable whose bell is the country's
    oldest."""
    P = ctx["P"]
    g = area(ctx, CHAPEL)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    stone, stone2, tile, win = P("#cbc3b2"), P("#b2a996"), P("#a9563b", ROOF), P("#3a3a36", WINDOW)
    cx, cy, L, Wd, ang = rect_of(g)
    fr = Frame(cx, cy, b0, ang)
    Wd = min(Wd, 8.0)

    def wall(u, v, w):
        return np.where(np.mod(np.floor(w / 0.5) + np.floor(u / 0.9), 3) == 0, stone2, stone).astype(np.uint16)
    S.add(Box(fr, -L / 2, L / 2, -Wd / 2, Wd / 2, -2, 6.0, wall))
    S.add(Roof(fr, -L / 2 - 0.3, L / 2 + 0.3, -Wd / 2 - 0.4, Wd / 2 + 0.4, 6.0, Wd * 0.45, tile))
    fb = fr.at(-L / 2 + 0.8)
    S.add(Box(fb, -0.8, 0.8, -1.2, 1.2, 6.0, 9.5, wall))
    S.add(Roof(fb.at(turn=math.pi / 2), -1.4, 1.4, -1.0, 1.0, 9.5, 1.6, tile))
    for u in np.arange(-L / 2 + 3, L / 2 - 1, 3.5):
        for sv in (-1, 1):
            S.add(Box(fr.at(u, sv * Wd / 2), -0.3, 0.3, -0.4, 0.4, 3.0, 4.6, win, mode="paint", targets=[stone, stone2]))


# ------------------------------------------------------------------------------------------------ the Bodor well
def bodor(S, ctx, plan):
    """the Bodor musical well (a 1936 copy of Péter Bodor's 1820 well in Marosvásárhely): an octagonal pavilion of
    columns round the well, its green copper dome and lantern carrying a small spire."""
    P = ctx["P"]
    g = area(ctx, BODOR)
    if g is None:
        return
    c = g.centroid
    b0 = base_under(ctx, g, 0.3)
    stone, white, copper, gold = P("#d9d2c2"), P("#f1eee6"), P("#5f8f7c", METAL), P("#cfa94c", METAL)
    fr = Frame(c.x, c.y, b0, 0.0)
    S.add(Lathe(fr, -0.3, 0.6, cyl(4.6), stone, n=8, rot=math.pi / 8))
    for k in range(8):
        S.add(Lathe(fr.at(turn=k * TAU / 8).at(3.9), 0.6, 4.4, cyl(0.28), white, n=8))
    S.add(Lathe(fr, 4.4, 5.0, cyl(4.4), white, n=8, rot=math.pi / 8))
    S.add(Lathe(fr, 5.0, 8.5, dome(4.3, 1.6, 1.0), copper, n=8, rot=math.pi / 8))
    S.add(Lathe(fr, 8.5, 10.0, cyl(1.0), white, n=8, rot=math.pi / 8))
    S.add(Lathe(fr, 10.0, 12.0, cone(1.2, 0.1), copper, n=8, rot=math.pi / 8))
    S.add(Box(fr, -0.06, 0.06, -0.06, 0.06, 12.0, 13.0, gold))
    S.add(Lathe(fr, 0.6, 1.5, cyl(1.3), stone, n=8, inner=0.3))


# ------------------------------------------------------------------------------------------------ the Japanese Garden
def japanese(S, ctx, plan):
    """the Japanese Garden at the island's north end: a red wooden footbridge over the fish pond, grey rocks round it and
    stone lanterns along the paths."""
    P = ctx["P"]
    g = area(ctx, POND)
    if g is None:
        return
    red, rock, rock2, lant = P("#a8382c"), P("#8d8a83"), P("#a7a39a"), P("#b8b3a6")
    cx, cy, L, Wd, ang = rect_of(g)
    b0 = max(ctx["ground_m"](*g.exterior.coords[0]), ctx["ground_m"](cx, cy))
    ring = g.exterior
    pts = [ring.interpolate(ring.length * k / 80) for k in range(80)]
    best = None
    for i in range(80):  # the bridge spans the pond's narrowest neck
        for j in range(i + 8, 80):
            if min(j - i, 80 - (j - i)) < 8:
                continue
            seg = shapely.LineString([pts[i], pts[j]])
            if not 4.0 < seg.length < 18.0 or not g.buffer(0.5).contains(seg):
                continue
            if best is None or seg.length < best.length:
                best = seg
    if best is not None:
        (ax, ay), (bx, by) = best.coords
        span = best.length + 2.0
        fb = Frame((ax + bx) / 2, (ay + by) / 2, b0, math.atan2(by - ay, bx - ax))
        n = 8
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            z0, z1 = 1.2 * math.sin(math.pi * t0), 1.2 * math.sin(math.pi * t1)
            u0, u1 = -span / 2 + span * t0, -span / 2 + span * t1
            S.add(Box(fb, u0, u1 + 0.1, -0.8, 0.8, min(z0, z1) - 0.4, max(z0, z1) + 0.3, red))
            for sv in (-1, 1):
                S.add(Box(fb, u0, u1 + 0.1, sv * 0.8 - 0.25, sv * 0.8 + 0.25, max(z0, z1) + 0.3, max(z0, z1) + 1.2, red))
    rng = np.random.default_rng(1921)
    for k in range(14):
        p = ring.interpolate(rng.uniform(0, ring.length))
        h = rng.uniform(0.5, 1.4)
        S.add(Ellipsoid(Frame(p.x, p.y, ctx["ground_m"](p.x, p.y) + h * 0.3, rng.uniform(0, TAU)), rng.uniform(0.7, 1.4),
                        rng.uniform(0.5, 1.0), h, rock if k % 2 else rock2))
    for k in range(4):
        p = ring.buffer(4.0).exterior.interpolate(ring.buffer(4.0).exterior.length * (k + 0.3) / 4)
        fl = Frame(p.x, p.y, ctx["ground_m"](p.x, p.y), 0.0)
        S.add(Lathe(fl, 0, 0.9, cyl(0.25), lant, n=6))
        S.add(Box(fl, -0.35, 0.35, -0.35, 0.35, 0.9, 1.4, lant))
        S.add(Lathe(fl, 1.4, 1.9, cone(0.6, 0.1), lant, n=6))


# ------------------------------------------------------------------------------------------------ the hotels
def hotels(S, ctx, plan):
    """the hotels at the north end: the Thermal (1979), a nine-storey slab in cream with brown glass behind balcony bands
    that step down to the river on its south side, over its low treatment wings and roof gardens; and Miklós Ybl's
    Grand Hotel (1873) beside it, four storeys in cream with white bands under grey roofs with gabled dormers, a
    glazed one-storey veranda along its garden front."""
    P = ctx["P"]
    cream, white, brown, win = P("#e9dcc0"), P("#f3efe6"), P("#5a4a3e", GLASS), P("#33404a", WINDOW)
    roof, green, glass2, slate = P("#a9aca8", ROOF), P("#6f8a4e"), P("#7f9aa4", GLASS), P("#7b7f80", ROOF)
    for oid, E in THERMAL:
        g = area(ctx, oid)
        if g is None:
            continue
        b0 = base_under(ctx, g, 0.3)
        if oid == HOTEL_SLAB:
            def fn(f, hw, E=E):
                d, s = f["d"], f["s"]
                inside = d > 0
                fl = np.mod(hw, 3.2)
                slab = fl < 0.45
                rail = (d < 0.4) & (fl < 1.4)
                fin = (d < 1.6) & (np.mod(s, 7.2) < 0.4)
                o = np.where(inside & (d < 1.6) & (slab | rail | fin) & (hw < E), np.where(slab | fin, cream, white), 0)
                o = np.where(inside & (d >= 1.6) & (d < 2.2) & (hw < E), brown, o)
                o = np.where(inside & (hw >= E - 0.6) & (hw < E), roof, o)
                return np.where(inside & (d < 0.5) & (hw >= E) & (hw < E + 1.0), cream, o)
            painted(S, g, b0, E + 1.2, fn)
        elif E <= 5.0:
            def fn(f, hw, E=E):
                d, s = f["d"], f["s"]
                inside, edge = d > 0, (d > 0) & (d < 0.8)
                o = np.where(edge & (hw < E), np.where((hw > 0.6) & (hw < E - 1.2) & (np.mod(s, 3.0) > 0.4), glass2, cream), 0)
                o = np.where(inside & ~edge & (hw >= E - 0.6) & (hw < E), np.where(d > 2.0, green, roof), o)
                return np.where(edge & (hw >= E) & (hw < E + 0.8), white, o)
            painted(S, g, b0, E + 1.0, fn)
        else:
            styled(S, g, b0, E, cream, brown, roof, floor=3.2, bay=3.0, winw=2.2, sill=0.3, head=2.7, band=white, ribbon=True)
    g = area(ctx, GRAND)
    if g is not None:
        styled(S, g, base_under(ctx, g, 0.3), 16.0, cream, win, slate, floor=3.6, gf=4.4, bay=3.4, winw=1.5, sill=1.0,
               head=3.0, roof_kind="hip", slope=0.9, ridge=4.5, band=white, base=white)


# ------------------------------------------------------------------------------------------------ Árpád Bridge
def arpad(S, ctx, plan):
    """Árpád Bridge (1950, widened 1984): under the deck the steel box girders in grey-green along both edges, and the
    concrete piers in the river every 100 m or so."""
    P = ctx["P"]
    deck_top = ctx.get("deck_top")
    g = area(ctx, ARPAD)
    if g is None or deck_top is None:
        return
    steel, pier = P("#5f6e6a", METAL), P("#a9a59b", CONCRETE)
    wl = ctx["WLr"]
    from landmarks_city import grid_of
    x0f, y0f, X, Y = grid_of(g, 1.0)
    Z = np.zeros(X.shape, np.float32)
    river = ctx["river"]
    yi, xi = np.clip(Y.astype(int), 0, river.shape[0] - 1), np.clip(X.astype(int), 0, river.shape[1] - 1)
    wet = shapely.contains_xy(g, X, Y) & river[yi, xi]
    for j, i in zip(*np.nonzero(wet)):
        t = deck_top(float(X[j, i]), float(Y[j, i]))
        if t is not None:
            Z[j, i] = t
    deck = Z > 0
    if not deck.any():
        return
    edge = deck & ~ndimage.binary_erosion(deck, iterations=3)
    cx, cy, L, Wd, ang = rect_of(g)
    u = (X - cx) * math.cos(ang) + (Y - cy) * math.sin(ang)
    piers = deck & (np.abs(np.mod(u + 20.0, 102.0) - 51.0) > 48.0) & ndimage.binary_erosion(deck, iterations=4)
    fields = dict(z=Z, e=edge.astype(np.float32), p=piers.astype(np.float32))
    from landmarks import Field

    def go(f, w):
        z, e, p = f["z"][None], f["e"][None] > 0, f["p"][None] > 0
        o = np.where(e & (w >= z - 3.4) & (w < z - 0.2), steel, 0)
        return np.where(p & (w >= wl - 6.0) & (w < z - 3.4), pier, o).astype(np.uint16)
    zt = float(Z[deck].max())
    S.add(Field(x0f, y0f, fields, wl - 6.0, zt, go))


BUILDERS = [("Margaret Island Water Tower", tower), ("Palatinus Baths", palatinus), ("Hajós Alfréd pool", hajos),
            ("Musical Fountain and Centenary Monument", fountain), ("Premonstratensian chapel", chapel),
            ("Bodor musical well", bodor), ("Japanese Garden", japanese), ("Thermal and Grand hotels", hotels),
            ("Árpád Bridge", arpad)]
