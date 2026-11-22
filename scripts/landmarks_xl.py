"""November 2026, third round: the Great Rock and the Palm House in the Zoo and Botanical Garden, the House of Music,
the two churches of Rózsák tere (St Elizabeth's and the Greek Catholic church), St Joseph's in Józsefváros, Déli
station with its platform canopies, and the National Athletics Centre in the strip added south of the map. Outlines
from OSM; heights, colours and details from the Esri aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon

import landmarks as LM
from landmarks import WINDOW, Arch, Box, Capsule, Ellipsoid, Field, Frame, Lathe, Poly, Roof, cone, cyl, dome, rect_of, zsolnay
from landmarks_city import base_under, dist_in, grid_of, windows
from landmarks_hosok import keep, side, windows_on
from landmarks_pest import block
from style import GLASS, GRASS, METAL, ROOF

ROCK, PALM = 419586780, 25225151
MUSIC = 759007872
ERZSEBET, GOROG = 25277227, 106278410
JOZSEF = 164704143
DELI, DELI_ROOF = 706621044, 706621031
NAC_BOWL, NAC_ROOF, NAC_TRACK, NAC_PITCH = 17534030, 950165269, 17534029, 17534028

NAMES = ["Zoo: Great Rock and Palm House", "House of Music", "St Elizabeth's, Rózsák tere", "Greek Catholic church, Rózsák tere",
         "St Joseph's, Józsefváros", "Déli Station", "National Athletics Centre"]
DROP = {PALM, MUSIC, ERZSEBET, GOROG, JOZSEF, DELI, DELI_ROOF, NAC_BOWL}
KEEP = [(PALM, 14), (MUSIC, 14), (ERZSEBET, 30), (GOROG, 14), (JOZSEF, 24), (DELI, 13), (NAC_BOWL, 30)]
TAU = 2 * math.pi


def hashed(X, Y, Z, k):
    """a block hash per cell: no stripes."""
    h = (np.floor(X).astype(np.int64) * 73856093) ^ (np.floor(Y).astype(np.int64) * 19349663) ^ (np.floor(Z).astype(np.int64) * 83492791)
    return np.mod(np.abs(h) >> 3, k)


# ------------------------------------------------------------------------------------------------ the Zoo
def great_rock(S, ctx, g):
    """the Great Rock (Nagyszikla, 1912; rebuilt 2013 with the Magic Mountain inside): a concrete mountain of pale
    grey-beige crags over OSM's outline, its summit (34 m) over the eastern lobe, a lower ridge over the western one and
    a saddle between them; sheer faces broken into ledges, dark clefts, shrubs on the ledges."""
    P = ctx["P"]
    b0 = base_under(ctx, g, 0.3)
    x0f, y0f, X, Y = grid_of(g, 1.0)
    d = dist_in(g, X, Y)
    rng = np.random.default_rng(1912)
    nz = np.zeros_like(X)
    for k in range(6):
        a, f, ph = rng.uniform(0, TAU), 0.07 * 1.8 ** k, rng.uniform(0, TAU)
        nz += np.sin((X * math.cos(a) + Y * math.sin(a)) * f + ph) / 1.6 ** k
    peaks = ((7575.0, 2058.0, 34.0, 19.0), (7566.0, 2036.0, 26.0, 14.0), (7530.0, 2041.0, 22.0, 15.0),
             (7512.0, 2052.0, 15.0, 9.0), (7584.0, 2075.0, 24.0, 10.0))
    z = np.zeros_like(X)
    for px, py, h, r in peaks:
        z = np.maximum(z, h * np.exp(-((X - px) ** 2 + (Y - py) ** 2) / (2 * r * r)))
    z = z + 2.6 * nz
    cliff = 5.0 + np.maximum(d, 0) * 2.6  # the faces rise steeply from the paths
    z = np.where(d > 0, np.clip(np.minimum(z, cliff), 1.0, 36.0), -5).astype(np.float32)
    z = np.round(z / 1.5) * 1.5 + np.mod(np.floor(X / 4) + np.floor(Y / 4), 2) * 0.5  # ledges
    gy, gx = np.gradient(z * LM.F)
    fields = dict(z=z.astype(np.float32), sl=np.hypot(gx, gy).astype(np.float32), X=X, Y=Y)
    greys = np.array([P("#b8b09f"), P("#aaa190"), P("#c4bdae"), P("#9d9586"), P("#b2ab9c"), P("#cfc8b9")], np.uint16)
    cleft, green, green2 = P("#6f685d"), P("#5d7a40", GRASS), P("#4b6634", GRASS)

    def fn(f, wa):
        top = f["z"][None] + b0
        h = hashed(f["X"][None] / 1.3, f["Y"][None] / 1.3, (wa - b0) / 1.1, 997)
        col = greys[np.mod(h, len(greys))]
        steep = f["sl"][None] > 2.2
        col = np.where(steep & (np.mod(h, 7) == 0), cleft, col)
        veg = (wa > top - 0.6) & (f["sl"][None] < 1.0) & (np.mod(h >> 3, 3) != 0)
        col = np.where(veg, np.where(np.mod(h, 2) == 0, green, green2), col)
        return np.where(wa <= top, col, 0).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 2, b0 + 38, fn))


def palm_house(S, ctx, g):
    """the Palm House (1912, iron and glass by the Eiffel company's Budapest office): a domed central hall facing the
    lake, and parallel glazed wings reaching back from it, each under a curved glass roof on white iron ribs."""
    P = ctx["P"]
    b0 = base_under(ctx, g, 0.3)
    glass, glass2, rib, base = P("#9db8bc", GLASS), P("#87a5aa", GLASS), P("#eceee9", METAL), P("#cfc9bb")
    fr = Frame(7162.0, 2062.0, b0, math.radians(47.5))  # +u along the wings

    def fn(d, U, V, a, hw):
        inside = d > 0
        top = 5.5 + 3.2 * np.sqrt(np.clip(d, 0, 6) / 6)  # each wing's barrel vault
        o = np.where(inside & (hw < 0.8), base, 0)
        shell = inside & (hw >= 0.8) & (hw < top) & ((d < 0.7) | (hw > top - 0.6))
        ribs = np.mod(V, 3.0) < 0.5
        o = np.where(shell, np.where(ribs | (hw > top - 0.3) & (np.mod(U, 3.0) < 0.5), rib, np.where(np.mod(a, 6) < 3, glass, glass2)), o)
        return o
    block(S, g, fr, b0, 10.5, fn)
    # the central hall: a glass drum and dome over the front, facing the lake
    fc = Frame(7174.5, 2049.5, b0, 0)
    S.add(Lathe(fc, -0.5, 8.0, cyl(8.2), lambda u, v, w: np.where(np.mod(np.arctan2(v, u) * 24 / TAU, 1) < 0.18, rib, glass).astype(np.uint16), n=24))
    S.add(Lathe(fc, 8.0, 8.6, cyl(8.6), rib, n=24))
    S.add(Lathe(fc, 8.6, 16.5, dome(8.4, 2.0), lambda u, v, w: np.where(np.mod(np.arctan2(v, u) * 16 / TAU, 1) < 0.15, rib, glass2).astype(np.uint16), n=24))
    S.add(Lathe(fc, 16.2, 18.2, cyl(1.4), rib, n=8))
    S.add(Lathe(fc, 18.2, 19.6, cone(1.6, 0.1), rib, n=8))


def zoo_xl(S, ctx, plan):
    great_rock(S, ctx, keep(ctx, ROCK))
    palm_house(S, ctx, keep(ctx, PALM))
    S.clear.append((7554.0, 2052.0, 40.0))


# ------------------------------------------------------------------------------------------------ House of Music
def house_of_music(S, ctx, plan):
    """the House of Music (Sou Fujimoto, 2022): a white roof of rolling hills and some ninety round holes, floating
    on slender columns 12 m over a ring of full-height glass; under the roof a gilded ceiling of leaves. Trees grow up
    through the largest holes; the raised middle covers the concert hall."""
    P = ctx["P"]
    g = keep(ctx, MUSIC)
    b0 = base_under(ctx, g, 0.3)
    c = g.centroid
    cx, cy = c.x, c.y
    white, white2, edge = P("#f1efe9"), P("#e3e0d8"), P("#d8d4ca")
    gold, gold2 = P("#c9a24f", METAL), P("#b38b3e", METAL)
    glass, mull = P("#8ea2a6", GLASS), P("#f4f4f0", METAL)
    floor = P("#d7d3c8")
    rng = np.random.default_rng(2022)
    holes = []
    while len(holes) < 92:  # big ones in the outer band, small ones over the middle
        t, rr = rng.uniform(0, TAU), 40.0 * math.sqrt(rng.uniform(0.02, 1.0))
        r = rng.uniform(1.0, 2.2) if rr < 20 else rng.uniform(1.4, 4.2)
        x, y = cx + rr * math.cos(t), cy + rr * math.sin(t)
        if not g.buffer(-r - 1.5).contains(Point(x, y)):
            continue
        if all(math.hypot(x - a, y - b) > r + q + 1.4 for a, b, q in holes):
            holes.append((x, y, r))
    x0f, y0f, X, Y = grid_of(g, 1.0)
    d = dist_in(g, X, Y)
    R = np.hypot(X - cx, Y - cy)
    hole = np.zeros_like(X, dtype=bool)
    rim = np.zeros_like(X, dtype=bool)
    for x, y, r in holes:
        q = np.hypot(X - x, Y - y)
        hole |= q < r
        rim |= (q >= r) & (q < r + 0.6)
    hills = 1.2 * np.sin(X * 0.21 + 1.3) * np.sin(Y * 0.17 + 0.4) + 0.7 * np.sin((X + Y) * 0.09)
    under = (11.5 + np.clip(1 - R / 22.0, 0, 1) * 4.0 + hills).astype(np.float32)  # the ceiling over the ground
    thick = (1.3 + np.clip(1 - R / 22.0, 0, 1) * 1.6).astype(np.float32)
    fields = dict(d=d, under=under, thick=thick, hole=hole.astype(np.float32), rim=rim.astype(np.float32), X=X, Y=Y)

    def fn(f, wa):
        hw = wa - b0
        d_, un, th = f["d"][None], f["under"][None], f["thick"][None]
        ho, ri = f["hole"][None] > 0, f["rim"][None] > 0
        roof = (d_ > 0) & ~ho & (hw >= un) & (hw < un + th)
        leaf = hashed(f["X"][None] / 1.6, f["Y"][None] / 1.6, 0 * hw, 5) == 0
        col = np.where(hw < un + 0.5, np.where(leaf, gold2, gold), np.where(ri | (d_ < 0.8), edge, np.where(np.mod(np.floor(f["X"][None] * 0.5) + np.floor(f["Y"][None] * 0.5), 9) == 0, white2, white)))
        o = np.where(roof, col, 0)
        # the glass ring, 8 to 12 m in from the roof's edge, and the floor inside it
        ring = (d_ > 8.0) & (d_ < 8.6) & (hw >= 0) & (hw < un)
        o = np.where(ring, np.where((np.mod(f["X"][None] + f["Y"][None], 2.4) < 0.3) | (np.mod(hw, 4.0) < 0.25), mull, glass), o)
        o = np.where((d_ > 8.0) & (hw >= -0.6) & (hw < 0.0), floor, o)
        return o.astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 1, b0 + 21, fn))
    # the slender columns that carry the roof outside the glass
    for k in range(28):
        t = TAU * k / 28
        p = Point(cx + 32 * math.cos(t), cy + 32 * math.sin(t))
        if not g.buffer(-3.0).contains(p):
            continue
        S.add(Lathe(Frame(p.x, p.y, b0), -0.5, 12.0, cyl(0.3), mull, n=8))
    S.clear.append((cx, cy, 34.0))


# ------------------------------------------------------------------------------------------------ Rózsák tere
def erzsebet(S, ctx, plan):
    """St Elizabeth of Hungary at Rózsák tere (Imre Steindl, 1895-1901): Neo-Gothic in cream brick and stone, two
    76 m west towers whose stone spires are pierced, a nave and aisles under a steep roof of patterned Zsolnay tiles, a
    transept and a polygonal apse; pinnacles and flying buttresses along the sides."""
    P = ctx["P"]
    g = keep(ctx, ERZSEBET)
    b0 = base_under(ctx, g, 0.3)
    front, apse = np.array([6050.0, 3422.0]), np.array([6041.5, 3486.5])
    ang = math.atan2(*(apse - front)[::-1])
    fr = Frame(*front, b0, ang)  # +u from the west front to the apse
    cream, cream2, stone = P("#e2d6b8"), P("#d3c4a1"), P("#ece4cf")
    tiles = zsolnay(P, ["#3f5a4a", "#c9a64a", "#5b4636", "#2f4a5a"], period=1.1, slope=1.0, kind="diamond")
    win, door, gold = P("#303a44", WINDOW), P("#4a3828"), P("#cfa94c", METAL)

    def wall(u, v, w):
        return np.where(np.mod(w - b0, 3.0) < 0.35, cream2, cream).astype(np.uint16)
    ut0, ut1 = 31.5, 46.0  # the transept
    # aisles, nave, clerestory
    S.add(Box(fr, 7.0, ut0, -12.0, 12.0, -2, 11.0, wall))
    S.add(Roof(fr, 7.0, ut0, -12.4, 12.4, 11.0, 5.0, tiles))
    S.add(Box(fr, 7.0, ut0, -6.0, 6.0, 10.0, 21.0, wall))
    S.add(Box(fr, 6.8, ut0, -6.4, 6.4, 20.6, 21.3, stone))
    S.add(Roof(fr, 7.0, ut1 + 2.0, -6.6, 6.6, 21.3, 13.0, tiles))
    for sv in (-1, 1):
        for u in np.arange(9.5, ut0 - 1.0, 4.6):
            fw = fr.at(u, 0, 0, sv * math.pi / 2)
            S.add(Arch(fw, 11.6, 12.4, 0, 0.9, 2.5, 8.0, win, pointed=True, mode="paint", targets=[cream, cream2]))
            S.add(Arch(fw, 5.6, 6.4, 0, 0.9, 13.0, 18.0, win, pointed=True, mode="paint", targets=[cream, cream2]))
            fb = fr.at(u + 2.3, sv * 11.0)
            S.add(Box(fb, -0.6, 0.6, -0.9, 0.9, -2, 13.5, stone))
            S.add(Lathe(fb, 13.5, 16.5, cone(0.7, 0.05), stone, n=4, rot=math.pi / 4))
    # the transept and its gables
    S.add(Box(fr, ut0, ut1, -19.5, 19.5, -2, 19.0, wall))
    S.add(Roof(side(fr.at((ut0 + ut1) / 2, 0), 1), -19.8, 19.8, -(ut1 - ut0) / 2 - 0.3, (ut1 - ut0) / 2 + 0.3, 19.0, 11.0, tiles))
    for sv in (-1, 1):
        fg = fr.at((ut0 + ut1) / 2, 0, 0, sv * math.pi / 2)
        S.add(Arch(fg, 19.0, 19.8, 0, 3.2, 6.0, 14.5, win, pointed=True, mode="paint", targets=[cream, cream2]))
        for vv in (-6.8, 6.8):
            S.add(Lathe(fr.at((ut0 + ut1) / 2 + vv, sv * 19.2), 17.0, 25.5, cone(0.9, 0.05), stone, n=4, rot=math.pi / 4))
    # the apse
    fa = fr.at(ut1)
    S.add(Lathe(fa, -2, 19.0, cyl(8.5), wall, n=7, rot=math.pi / 14))
    S.add(Lathe(fa, 19.0, 28.0, cone(9.0, 0.3), tiles, n=7, rot=math.pi / 14))
    for k in range(5):
        t = -math.pi / 2 + math.pi * (k + 0.5) / 5
        S.add(Arch(fa.at(turn=t), 7.6, 8.8, 0, 1.0, 5.0, 14.0, win, pointed=True, mode="paint", targets=[cream, cream2]))
    # the crossing's flèche
    S.add(Lathe(fr.at((ut0 + ut1) / 2), 33.5, 47.0, cone(1.6, 0.05), tiles, n=8, rot=math.pi / 8))
    # the west front: two towers and the gable with the rose window and the portal
    for sv in (-1, 1):
        ft = fr.at(3.8, sv * 9.2)
        S.add(Box(ft, -4.2, 4.2, -4.0, 4.0, -2, 44.0, wall))
        for w in (12.0, 22.0, 33.0):
            S.add(Box(ft, -4.5, 4.5, -4.3, 4.3, w, w + 0.6, stone))
        for k in range(4):
            fk = ft.at(turn=k * math.pi / 2)
            S.add(Arch(fk, 3.6, 4.5, 0, 0.9, 35.0, 41.0, win, pointed=True, mode="paint", targets=[cream, cream2]))
            S.add(Arch(fk, 3.6, 4.5, 0, 0.7, 24.0, 29.5, win, pointed=True, mode="paint", targets=[cream, cream2]))
        S.add(Lathe(ft, 44.0, 46.0, cyl(4.0), stone, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 46.0, 75.0, lambda t: 3.5 * (1 - t) ** 1.1 + 0.15, lambda u, v, w: np.where(
            (np.mod(w - b0, 2.6) < 0.7) & (np.abs(np.mod(np.arctan2(v, u) * 8 / TAU, 1) - 0.5) < 0.18), win, stone).astype(np.uint16), n=8, rot=math.pi / 8))
        S.add(Box(ft, -0.12, 0.12, -0.12, 0.12, 75.0, 77.4, gold))
        S.add(Box(ft, -0.12, 0.12, -0.7, 0.7, 76.4, 76.6, gold))
        for su in (-1, 1):
            for sw in (-1, 1):
                S.add(Lathe(ft.at(su * 3.6, sw * 3.4), 44.0, 51.0, cone(0.7, 0.05), stone, n=4, rot=math.pi / 4))
    S.add(Box(fr, 0.0, 7.0, -5.2, 5.2, -2, 24.0, wall))
    S.add(Roof(fr.at(0, 0, 0, math.pi / 2), -5.4, 5.4, -0.6, 0.6, 24.0, 7.0, stone))
    fw = side(fr, 2)  # +u out of the west front
    S.add(Ellipsoid(fw.at(0.1, 0, 15.5), 0.4, 3.0, 3.0, win, mode="paint", targets=[cream, cream2]))
    for k in range(3):
        S.add(Arch(fw, -0.4 + k * 0.4, 0.4 + k * 0.4, 0, 2.8 - k * 0.5, 0, 5.6, stone if k % 2 else cream2))
    S.add(Arch(fw, -0.6, 1.8, 0, 1.6, 0, 4.4, door, pointed=True))
    S.clear.append((6044.0, 3452.0, 26.0))


def gorog(S, ctx, plan):
    """the Greek Catholic church of the Protection of the Mother of God at Rózsák tere (1784): a late Baroque hall in
    white and ochre, its tower over the west front facing the square with a curved copper helm and lantern."""
    P = ctx["P"]
    g = keep(ctx, GOROG)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(6094.2, 3405.0, b0, math.radians(7.8))  # +u from the west front into the church
    ochre, white, tile = P("#e2c37d"), P("#f2eee4"), P("#8d4f3b", ROOF)
    copper, win, door = P("#5f8a77", METAL), P("#2f3438", WINDOW), P("#4b3527")

    def wall(u, v, w):
        return np.where((np.abs(np.mod(u, 4.2) - 2.1) > 1.65) | (w - b0 < 1.0), white, ochre).astype(np.uint16)
    S.add(Box(fr, 0.5, 23.0, -6.6, 6.6, -2, 11.0, wall))
    S.add(Box(fr, 0.3, 23.2, -6.9, 6.9, 10.6, 11.4, white))
    S.add(Roof(fr, 0.5, 24.5, -7.1, 7.1, 11.4, 6.0, tile))
    S.add(Lathe(fr.at(23.0), -2, 10.0, cyl(5.5), wall, n=12))
    for sv in (-1, 1):
        for u in np.arange(6.0, 22.0, 4.2):
            S.add(Arch(fr.at(u, 0, 0, sv * math.pi / 2), 6.2, 7.0, 0, 0.8, 4.0, 8.5, win, mode="paint", targets=[ochre, white]))
    ft = fr.at(2.6)
    S.add(Box(ft, -2.6, 2.6, -3.4, 3.4, -2, 22.5, wall))
    S.add(Box(ft, -2.9, 2.9, -3.7, 3.7, 22.5, 23.2, white))
    for k in range(4):
        S.add(Arch(ft.at(turn=k * math.pi / 2), 2.2, 3.5 if k % 2 else 2.7, 0, 0.7, 17.5, 20.5, win, mode="paint", targets=[ochre, white]))
    S.add(Lathe(ft, 23.2, 27.0, lambda t: 3.0 * (1 - 0.6 * t) + 0.6 * np.sin(math.pi * t), copper, n=8, rot=math.pi / 8))
    S.add(Lathe(ft, 27.0, 29.0, cyl(0.9), copper, n=8, rot=math.pi / 8))
    S.add(Lathe(ft, 29.0, 31.5, cone(1.0, 0.05), copper, n=8, rot=math.pi / 8))
    S.add(Box(ft, -0.08, 0.08, -0.08, 0.08, 31.5, 33.0, P("#cfa94c", METAL)))
    fw = side(fr, 2)
    S.add(Arch(fw, -0.6, 0.4, 0, 1.0, 0, 3.0, door))
    S.add(Roof(fw.at(0, 0, 0, 0), -0.8, 0.0, -2.0, 2.0, 4.2, 1.0, white))


# ------------------------------------------------------------------------------------------------ St Joseph's
def jozsef(S, ctx, plan):
    """St Joseph's at Horváth Mihály tér (1797-1814, Baroque-Classicist): a cream church with two towers over the
    north-west front facing the square, each with a curved helm and lantern in dark copper; a nave and transept under
    a grey roof, a rounded east end."""
    P = ctx["P"]
    g = keep(ctx, JOZSEF)
    b0 = base_under(ctx, g, 0.3)
    front = np.array([5154.0, 4344.7])
    back = np.array([5194.6, 4375.3])
    fr = Frame(*front, b0, math.atan2(*(back - front)[::-1]))  # +u from the front to the east end
    cream, white, ochre = P("#ece2c8"), P("#f6f2e8"), P("#dcc79a")
    slate, helm = P("#5d6869", ROOF), P("#3f4d4b", METAL)
    win, door, gold = P("#2f3438", WINDOW), P("#4b3527"), P("#cfa94c", METAL)

    def wall(u, v, w):
        pil = np.abs(np.mod(u, 5.0) - 2.5) > 2.0
        return np.where(pil | (w - b0 < 1.2), white, cream).astype(np.uint16)
    L = float(np.hypot(*(back - front)))
    S.add(Box(fr, 3.5, L - 6.0, -8.3, 8.3, -2, 16.0, wall))
    S.add(Box(fr, 3.3, L - 5.8, -8.7, 8.7, 15.4, 16.4, white))
    S.add(Roof(fr, 3.5, L - 4.0, -9.0, 9.0, 16.4, 8.5, slate))
    # the transept
    S.add(Box(fr, 16.0, 32.0, -14.0, 14.0, -2, 16.0, wall))
    S.add(Roof(side(fr.at(24.0, 0), 1), -14.3, 14.3, -8.3, 8.3, 16.4, 8.2, slate))
    S.add(Lathe(fr.at(L - 6.0), -2, 15.0, cyl(8.0), wall, n=14))
    S.add(Lathe(fr.at(L - 6.0), 15.0, 21.0, dome(8.3, 2.0), slate, n=14))
    for sv in (-1, 1):
        for u in np.arange(6.0, L - 6.0, 5.0):
            fw = fr.at(u, 0, 0, sv * math.pi / 2)
            S.add(Arch(fw, 7.9, 8.7, 0, 1.0, 5.0, 11.5, win, mode="paint", targets=[cream, white]))
            if 16.0 <= u <= 32.0:
                S.add(Arch(fw, 13.6, 14.4, 0, 1.0, 5.0, 11.5, win, mode="paint", targets=[cream, white]))
    # the front: the towers and between them the pedimented centre
    S.add(Box(fr, -0.4, 4.0, -5.0, 5.0, -2, 20.0, wall))
    S.add(Roof(fr.at(0, 0, 0, math.pi / 2), -5.4, 5.4, -0.6, 1.0, 20.0, 3.6, white))
    for sv in (-1, 1):
        ft = fr.at(2.8, sv * 7.6)
        S.add(Box(ft, -3.2, 3.2, -3.0, 3.0, -2, 31.0, wall))
        for w in (15.4, 24.0, 31.0):
            S.add(Box(ft, -3.5, 3.5, -3.3, 3.3, w, w + 0.7, white))
        for k in range(4):
            fk = ft.at(turn=k * math.pi / 2)
            S.add(Arch(fk, 2.6, 3.6, 0, 0.9, 25.5, 29.0, win, mode="paint", targets=[cream, white]))
            S.add(Ellipsoid(fk.at(3.2, 0, 20.0), 0.25, 1.1, 1.1, ochre))
        S.add(Lathe(ft, 31.7, 36.0, lambda t: 3.0 * (1 - 0.55 * t) + 0.8 * np.sin(math.pi * t), helm, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 36.0, 38.2, cyl(0.9), helm, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 38.2, 41.5, onion_like(1.1), helm, n=8, rot=math.pi / 8))
        S.add(Box(ft, -0.1, 0.1, -0.1, 0.1, 41.5, 43.5, gold))
        S.add(Box(ft, -0.1, 0.1, -0.5, 0.5, 42.6, 42.8, gold))
    fw = side(fr, 2)
    S.add(Arch(fw, -0.6, 0.6, 0, 1.4, 0, 3.8, door))
    S.add(Box(fw, -0.9, 0.4, -2.4, 2.4, 0, 6.6, white, mode="under"))
    S.add(Arch(fw, 0.0, 0.6, 0, 1.3, 9.0, 13.0, win, mode="paint", targets=[cream, white]))
    S.clear.append((5174.0, 4360.0, 24.0))


def onion_like(r):
    return lambda t: r * (0.35 + 0.65 * np.sin(math.pi * np.minimum(t * 1.15, 1.0))) * (1 - t) ** 0.3 + 0.08


# ------------------------------------------------------------------------------------------------ Déli Station
def deli(S, ctx, plan):
    """Déli pályaudvar (György Kővári, 1975): the concourse a low steel-framed hall, glass walls under a deep fascia
    of rust-brown weathering steel, a flat roof and the drum of the metro's rotunda on the square in front; long
    canopies on slim columns over the platforms."""
    P = ctx["P"]
    g = keep(ctx, DELI)
    b0 = base_under(ctx, g, 0.2)
    rust, rust2, glass, mull = P("#7a4a30", METAL), P("#6a3f29", METAL), P("#5d6e74", GLASS), P("#3c3a37", METAL)
    roof, roof2, conc = P("#a8a7a2", ROOF), P("#a2a19c", ROOF), P("#c9c5bb")
    E = 13.0

    def fn(d, U, V, a, hw):
        inside = d > 0
        edge = d < 0.8
        walls = np.where(hw < 7.5, np.where(np.mod(a, 3.0) < 0.35, mull, glass), np.where(np.mod(a, 1.4) < 0.25, rust2, rust))
        o = np.where(inside & edge & (hw < E), walls, 0)
        o = np.where(inside & ~edge & (hw >= E - 0.8) & (hw < E), np.where(np.mod(np.floor(U / 6) + np.floor(V / 6), 2) == 0, roof, roof2), o)
        o = np.where(inside & (hw >= -0.6) & (hw < 0.0), conc, o)
        return o
    fr = Frame(3058.7, 914.1, b0, math.radians(-47.6))
    block(S, g, fr, b0, E + 1.0, fn)
    # the metro's rotunda on the square
    frt = Frame(3057.0, 929.0, b0, 0)
    S.add(Lathe(frt, -0.5, E + 2.5, cyl(5.8), lambda u, v, w: np.where(np.mod(w - b0, 2.0) < 0.5, rust, glass).astype(np.uint16), n=20))
    S.add(Lathe(frt, E + 2.5, E + 3.1, cyl(6.2), rust2, n=20))
    # canopies over the platforms: OSM's roof, and one over each platform A-G, on columns every 9 m
    canopy, col = P("#d9d7d0", ROOF), P("#4c5053", METAL)
    plats = [keep(ctx, DELI_ROOF)] + [a[3] for a in ctx["osm"].areas if a[2].get("railway") == "platform"
                                      and a[2].get("ref") in ("A", "B", "C", "D", "E", "F", "G")
                                      and a[3].distance(Point(3004, 1100)) < 260]
    for pg in plats:
        pg = pg.buffer(0.8, join_style=2)
        zb = base_under(ctx, pg, 0.3)
        S.add(Poly(pg, zb + 5.0, zb + 5.6, canopy))
        cx_, cy_, Lp, Wp, ap = rect_of(pg)
        fp = Frame(cx_, cy_, zb, ap)
        for u in np.arange(-Lp / 2 + 3, Lp / 2 - 2, 9.0):
            if pg.buffer(-0.5).contains(Point(*fp.xy(u, 0))):
                S.add(Box(fp, u - 0.18, u + 0.18, -0.18, 0.18, 0.0, 5.0, col))
    S.clear.append((3061.0, 966.0, 60.0))


# ------------------------------------------------------------------------------------------------ the athletics stadium
def nac(S, ctx, plan):
    """the Zsivotzky Gyula National Athletics Centre (NAPUR Architect, 2023): the track and field in a bowl of stands,
    under a ring of white membrane roof on a cable net between an inner tension ring and an outer compression truss,
    which leans outwards on 48 pairs of slanted columns; since the championships the outer ring is open, a pergola
    over a running loop."""
    P = ctx["P"]
    area = ctx["area"]
    outline = keep(ctx, NAC_ROOF)
    track = area[NAC_TRACK][3] if NAC_TRACK in area else None
    pitch = area[NAC_PITCH][3] if NAC_PITCH in area else None
    b0 = base_under(ctx, outline, 0.3)
    cx, cy, Lo, Wo, ang = rect_of(outline)
    a_, b_ = Lo / 2, Wo / 2
    fr = Frame(cx, cy, b0, ang)
    red, red2, green, green2, line = P("#bf4f36"), P("#b04630"), P("#4e8a3c", GRASS), P("#457d35", GRASS), P("#f2efe6")
    seat, seat2, seat3, conc = P("#c75a3a"), P("#8c8f93"), P("#d68a3e"), P("#bdb8ad")
    memb, memb2, steel, steel2 = P("#f4f4f1"), P("#e6e7e4"), P("#f1f2ef", METAL), P("#d6d8d6", METAL)
    pave = P("#cdc8bd")
    x0f, y0f, X, Y = grid_of(outline, 14.0)
    U = ((X - cx) * fr.ca + (Y - cy) * fr.sa).astype(np.float32)
    V = (-(X - cx) * fr.sa + (Y - cy) * fr.ca).astype(np.float32)
    s = (((np.abs(U) / a_) ** 2.4 + (np.abs(V) / b_) ** 2.4) ** (1 / 2.4)).astype(np.float32)  # 1 on the outline
    tr = shapely.contains_xy(track, X, Y) if track is not None else np.zeros_like(X, bool)
    pi_ = shapely.contains_xy(pitch, X, Y) if pitch is not None else np.zeros_like(X, bool)
    th = np.arctan2(V / b_, U / a_).astype(np.float32)
    fields = dict(s=s, tr=tr.astype(np.float32), pi=pi_.astype(np.float32), th=th, U=U, V=V)
    s_bowl, s_top, s_in = 0.50, 0.80, 0.60  # the stands from the track's edge to s_top; the roof from s_in out

    def fn(f, wa):
        hw = wa - b0
        s_, tr_, pi_, th_ = f["s"][None], f["tr"][None] > 0, f["pi"][None] > 0, f["th"][None]
        U_, V_ = f["U"][None], f["V"][None]
        o = np.zeros(np.broadcast_shapes(s_.shape, hw.shape), np.uint16)
        # the arena floor: field, track, aprons
        floor = (s_ < s_bowl) & (hw >= -0.6) & (hw < 0.0)
        lanes = np.mod(np.hypot(U_, V_) * 0.82, 1.22) < 0.12
        o = np.where(floor, np.where(pi_, np.where(np.mod(np.floor(U_ / 6.0), 2) == 0, green, green2),
                                     np.where(tr_, np.where(lanes, line, np.where(np.mod(np.floor(U_), 11) == 0, red2, red)), red2)), o)
        # the stands: a bowl rising from the track to s_top, rows of seats, vomitories
        rise = np.clip((s_ - s_bowl) / (s_top - s_bowl), 0, 1)
        top = 0.8 + rise * 17.0
        stand = (s_ >= s_bowl) & (s_ < s_top) & (hw >= -0.6) & (hw < top)
        tier = np.mod(np.floor(hw / 0.5), 2) == 0
        sect = np.mod(np.floor((th_ + math.pi) * 48 / TAU), 6)
        sc = np.where(sect == 0, seat2, np.where(rise > 0.55, seat3, seat))
        o = np.where(stand, np.where(hw > top - 0.5, np.where(tier, sc, conc), conc), o)
        # behind the stands: the open ring under the roof, paved
        o = np.where((s_ >= s_top) & (s_ < 1.04) & (hw >= -0.6) & (hw < 0.0), pave, o)
        # the roof: membrane between the tension ring (s_in) and the compression truss (s 1.0..1.06), a slight fall
        # inwards, ridges over the 48 radial cables; the whole ring tilted up towards the river (north-west)
        tilt = 4.0 * (-(U_ * 0.42 + V_ * 0.91) / max(a_, b_))
        zr = 31.0 + tilt + (s_ - s_in) / (1.0 - s_in) * 4.0
        rib = np.abs(np.mod((th_ + math.pi) * 48 / TAU, 1) - 0.5) > 0.44
        roof = (s_ >= s_in) & (s_ < 1.0) & (hw >= zr) & (hw < zr + np.where(rib, 1.4, 0.8))
        o = np.where(roof, np.where(rib, memb2, memb), o)
        # the compression truss: two chords and the lattice between them, leaning outwards
        chord = (s_ >= 1.0) & (s_ < 1.06)
        lo = zr + 0.5
        tr_c = chord & (((hw >= lo) & (hw < lo + 0.9)) | ((hw >= lo + 4.5) & (hw < lo + 5.4))
                        | ((hw >= lo) & (hw < lo + 5.4) & (np.abs(np.mod((th_ + math.pi) * 96 / TAU + (hw - lo) / 5.4, 1) - 0.5) > 0.42)))
        o = np.where(tr_c, steel, o)
        # the tension ring at the inner edge
        o = np.where((s_ >= s_in - 0.008) & (s_ < s_in + 0.006) & (hw >= zr - 0.6) & (hw < zr + 1.4), steel2, o)
        return o
    S.add(Field(x0f, y0f, fields, b0 - 1, b0 + 45, fn))
    # 48 pairs of slanted columns from the ground out to the truss
    colw = P("#e9eae7", METAL)
    for k in range(48):
        t = TAU * (k + 0.5) / 48
        ct, st = math.cos(t), math.sin(t)
        sup = (abs(ct) ** 2.4 + abs(st) ** 2.4) ** (1 / 2.4)
        u, v = a_ * ct / sup, b_ * st / sup
        tilt = 4.0 * (-(u * 0.42 + v * 0.91) / max(a_, b_))
        top = 31.0 + tilt + 4.0 + 0.5
        for dk in (-0.12, 0.12):
            t2 = t + dk * TAU / 48
            c2, s2 = math.cos(t2), math.sin(t2)
            sp = (abs(c2) ** 2.4 + abs(s2) ** 2.4) ** (1 / 2.4)
            ub, vb = 0.93 * a_ * c2 / sp, 0.93 * b_ * s2 / sp
            S.add(Capsule(fr, (ub, vb, 0.0), (u * 1.02, v * 1.02, top), 0.45, colw))
    S.clear.append((cx, cy, max(a_, b_) + 12))


BUILDERS = [("Zoo: Great Rock and Palm House", zoo_xl), ("House of Music", house_of_music),
            ("St Elizabeth's, Rózsák tere", erzsebet), ("Greek Catholic church, Rózsák tere", gorog),
            ("St Joseph's, Józsefváros", jozsef), ("Déli Station", deli), ("National Athletics Centre", nac)]
