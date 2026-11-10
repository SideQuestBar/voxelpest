"""Matthias Church (Mátyás-templom, Budavári Nagyboldogasszony-templom) as Frigyes Schulek rebuilt it in 1874-96,
drawn whole in place of OSM's 36 parts: the hall with its four bays, the choir and apse, the chapels and annexes, the
Matthias tower, the Béla tower, the west front with its portal, rose and openwork gable, and the Zsolnay roofs (rows
of V's on the nave and the aisles' cross roofs, diamonds on the apse, rosettes on the side chapels). OSM gives the
outline and the parts' footprints; heights and details come from photos and published dimensions (docs/landmarks.md).

Everything is laid out in the nave frame: u along the axis (west front -30.2, apse 30.6), v across it towards the
square (south +), heights above the church's base (the Matthias tower's above the pavement at its foot).
"""
import math

import numpy as np
from shapely.geometry import Point

from landmarks import (MATTHIAS, TAU, WINDOW, Arch, Box, Capsule, Frame, Lathe, Poly, Prim, Roof, cone, cyl,
                       feat_base, pinnacle, rect_of, ring_segments, seg_frame)
from style import CLASSIC, METAL, ROOF

NAVE, TOWER = 1547492618, 1456696049
NW_STAIR, NORTH_CHAPELS, NORTH_GABLE = 1547492612, 1547492616, 1547492597
SACRISTY, ST_STEPHEN, SOUTH_CHAPEL, MARY_PORCH = 1547492614, 1547492615, 1547492613, 1547492619

E, RIDGE, CROSS_RIDGE = 16.3, 25.5, 23.0   # eaves, the main ridge, the aisles' cross roofs
WALL_N, WALL_S = -13.3, 13.0               # the hall's side walls (OSM; 24.15 m inside, Szablyár)
BAYS = (-21.1, -12.73, -4.35, 4.03, 12.4)  # the hall's four bays, west to east
CHOIR, APSE, APSE_R = 6.35, 24.3, 6.3      # choir half-width; the apse is half an octagon round u = 24.3
WEST = -30.2
MT = (-25.6, 8.4)                          # the Matthias tower's axis: 76.57 m to the cross from the pavement
BT = (-25.7, -9.6)                         # the Béla tower's spire
TURRET = (11.0, -0.4)                      # the wooden ridge turret (huszártorony)

TILES = dict(o="#d8802c", y="#e3b43e", b="#62301f", r="#b8402c", t="#5cc0bb", w="#ebe5d6", g="#2f8a4e",
             u="#3d6fb0", c="#cf7426", d="#7a3424")


def parts(osm):
    """the church's building parts: all replaced by build()."""
    ch = next((g for oid, kind, t, g in osm.areas if oid == MATTHIAS), None)
    if ch is None:
        return set()
    hull = ch.buffer(1.0)
    return {oid for oid, kind, t, g in osm.areas if "building:part" in t and hull.contains(g.centroid)}


def nave_frame(area, b0):
    x, y, _, _, ang = rect_of(area[NAVE][3])
    fr = Frame(x, y, b0, ang)
    if fr.uv(*area[TOWER][3].centroid.coords[0])[0] > 0:  # the tower stands at the west end
        fr = Frame(x, y, b0, ang + math.pi)
    return fr


class Disc(Prim):
    """a cylinder along u: [u0, u1], radius r round (vc, wc). Rose windows, roundels."""

    def __init__(self, fr, u0, u1, vc, wc, r, col, **kw):
        self.p = (u0, u1, vc, wc, r)
        super().__init__(fr, col, (u0, u1, vc - r, vc + r, wc - r, wc + r), **kw)

    def inside(self, u, v, w, x, y):
        u0, u1, vc, wc, r = self.p
        return (u >= u0) & (u < u1) & (np.hypot(v - vc, w - wc) <= r)


def ids(a, *like):
    """a palette-id array broadcast to the shape of the coordinate arrays."""
    for x in like:
        a = a + 0 * x
    return np.asarray(a).astype(np.uint16)


# ------------------------------------------------------------------------------------------------ patterns
def ashlar(a, b, foot):
    """stone courses, every fourth block a shade darker, on a grey plinth (w < 0.9)."""
    def f(u, v, w):
        k = np.floor(w * 2) * 3 + np.floor((u + v) * 0.8)
        return ids(np.where(w < 0.9, foot, np.where(np.mod(k, 4) == 0, b, a)))
    return f


def chevrons(T, vent, amp=2.5, period=5.0):
    """the nave's and the cross roofs' Zsolnay tiles, f(s, z, h) with s along the eaves and z above them: rows of V's
    in orange and yellow lined in turquoise, white and brown, a band of rosettes along the eaves and under the ridge,
    an orange crest, and the small dormer vents."""
    seq = np.array([T[c] for c in "tooyywoyyb"], np.uint16)

    def f(s, z, h):
        tri = np.abs(np.mod(s / period, 1.0) - 0.5) * 2
        col = seq[np.mod(np.floor((z - tri * amp) * 2).astype(np.int64), len(seq))]
        dots = np.mod(np.floor(s * 2), 3) == 1
        col = np.where(z < 0.5, np.where(dots, T["g"], T["w"]), col)
        col = np.where((z > h - 1.0) & (z < h - 0.5), np.where(dots, T["r"], T["w"]), col)
        col = np.where(z >= h - 0.5, T["c"], col)
        dz, ds = z - 2.4, np.abs(np.mod(s, 6.0) - 3.0)  # dormer vents every 6 m, 2.4 m above the eaves
        edge = 0.8 * (1.2 - dz)
        col = np.where((dz >= 0) & (dz < 1.2) & (ds < edge), np.where(ds < edge - 0.5, vent, T["t"]), col)
        return ids(col)
    return f


def rosettes(T):
    """the side chapels' and the annexes' tiles: small rosettes of white, turquoise, green and blue on brown."""
    dots = np.array([T["t"], T["g"], T["u"], T["o"]], np.uint16)

    def f(s, z, h):
        i, j = np.floor(s * 2).astype(np.int64), np.floor(z * 2).astype(np.int64)
        k = np.mod(i + 2 * j, 4)
        col = np.where(k == 0, T["w"], np.where(k == 2, dots[np.mod(i // 2 + j, 4)], T["b"]))
        col = np.where(z < 0.5, np.where(np.mod(i, 3) == 1, T["r"], T["w"]), col)
        return ids(np.where(z >= h - 0.5, T["c"], col))
    return f


def apse_diamonds(T):
    """the apse's facets: a big diamond on each, outlined in turquoise and yellow, the Árpád stripes (red and white)
    in the east one, zigzags in the others, on orange with brown."""
    def f(s, z, h, k):
        zc, hz, hs = h * 0.39, h * 0.28, 1.7
        d = np.abs(s) / hs + np.abs(z - zc) / hz
        stripes = np.where(np.mod(np.floor(z * 2), 2) == 0, T["r"], T["w"])
        zigzag = np.where(np.mod(np.floor((z - np.abs(s)) * 2), 3) == 0, T["r"], T["y"])
        ground = np.where(np.mod(np.floor((z + np.abs(s) * 0.7) * 2), 4) == 0, T["b"], T["o"])
        col = np.where(d < 0.78, np.where(k == 0, stripes, zigzag), np.where(d < 1.05, T["t"], np.where(d < 1.3, T["y"], ground)))
        return ids(np.where(z < 0.5, T["w"], col))
    return f


def bela_tiles(T):
    """the Béla tower's spire: on each face a column of diamonds outlined in green, a white cross in each on red,
    the ground orange with dark red zigzags."""
    def f(s, z, h, k):
        zl = np.mod(z - 1.4, 3.4) - 1.7
        d = np.abs(s) / 1.0 + np.abs(zl) / 1.6
        cross = ((np.abs(s) < 0.26) & (np.abs(zl) < 0.85)) | ((np.abs(zl - 0.2) < 0.26) & (np.abs(s) < 0.55))
        ground = np.where(np.mod(np.floor((z - np.abs(s)) * 2), 3) == 0, T["d"], T["o"])
        col = np.where(d < 0.9, np.where(cross, T["w"], T["r"]), np.where(d < 1.2, T["g"], ground))
        return ids(np.where(z < 0.5, T["w"], col))
    return f


def small_chevrons(T):
    """the Béla tower's corner spirelets and the Mary porch: small zigzags in orange, turquoise, yellow and green."""
    seq = np.array([T["o"], T["t"], T["y"], T["g"], T["o"], T["w"]], np.uint16)

    def f(s, z, h, k=None):
        tri = np.abs(np.mod(s / 2.0, 1.0) - 0.5) * 2
        col = seq[np.mod(np.floor((z - tri) * 2).astype(np.int64), 6)]
        return ids(np.where(z >= h - 0.5, T["c"], col))
    return f


def roof_tiles(args, pattern):
    """colour a Roof(u0, u1, v0, v1, w0, h, hip) with pattern(s, z, h): s runs along the eaves of whichever face the
    voxel lies on (u on the long slopes, v on the hipped ends)."""
    u0, u1, v0, v1, w0, h, hip = args
    uc, vc, hu, hv = (u0 + u1) / 2, (v0 + v1) / 2, (u1 - u0) / 2, (v1 - v0) / 2

    def f(u, v, w):
        t = (w - w0) / h
        s = u + 0 * v
        if hip:
            s = np.where(hv * (1 - t) - np.abs(v - vc) <= hu - hv * t - np.abs(u - uc), s, v + 0 * u)
        return pattern(s, w - w0 + 0 * s, h)
    return f


def facet_tiles(n, w0, h, pattern, rot=0.0):
    """colour an n-gon pyramid (a Lathe) facet by facet: pattern(s, z, h, k), s across facet k."""
    def f(u, v, w):
        k = np.round((np.arctan2(v, u) - rot) / (TAU / n))
        th = rot + k * TAU / n
        s = -u * np.sin(th) + v * np.cos(th)
        return pattern(s, w - w0 + 0 * s, h, np.mod(k, n).astype(np.int64))
    return f


def lancet(hw, sill, spring, glass, stone, lights=3, rose=True, pointed=True):
    """a traceried window as f(s, z) -> ids (0 outside): `lights` lights below the springing, a ring in the head."""
    def f(s, z):
        a = np.abs(s)
        if pointed:
            head = (a + hw) ** 2 + (z - spring) ** 2 <= (2 * hw) ** 2
        else:
            head = a ** 2 + (z - spring) ** 2 <= hw ** 2
        inside = (a <= hw) & (z >= sill) & ((z < spring) | head)
        mull = np.zeros(np.broadcast(s, z).shape, bool)
        for k in range(1, lights):
            mull |= np.abs(s + hw - 2 * hw * k / lights) < 0.25
        mull &= z < spring
        if rose and hw >= 0.9:
            mull |= np.abs(np.hypot(s, z - spring - hw * 0.55) - hw * 0.42) < 0.22
        return ids(np.where(inside, np.where(mull, stone, glass), 0))
    return f


def window(S, fr, s0, hw, sill, spring, glass, stone, targets, depth=0.45, **kw):
    """a recessed window on a wall: fr's u runs along the wall, +v out of it, the face at v = 0."""
    fa = fr.at(s0, 0, 0, math.pi / 2)  # u: out of the wall, v: along it
    pointed = kw.get("pointed", True)
    S.add(Arch(fa, -depth, 0.3, 0, hw, sill, spring, pointed=pointed, mode="carve"))
    pat = lancet(hw, sill, spring, glass, stone, **kw)
    S.add(Arch(fa, -depth - 0.6, -depth + 0.05, 0, hw, sill, spring, col=lambda u, v, w: pat(v + 0 * u, w + 0 * u),
               pointed=pointed, mode="paint", targets=targets))


def out_frame(fr):
    """seg_frame's frame (v into the building) turned so that +v points out of it."""
    return Frame(fr.ox, fr.oy, fr.oz, fr.ang + math.pi)


def balustrade(S, fr, L, top, col, rail):
    """a pierced parapet along a wall (fr: u along it, v into the building)."""
    S.add(Box(fr, 0, L, -0.15, 0.35, top, top + 0.75, lambda u, v, w: ids(np.where(np.mod(u, 0.9) < 0.45, col, 0), v, w)))
    S.add(Box(fr, 0, L, -0.2, 0.4, top + 0.75, top + 1.0, rail))


def buttress(S, fr, top, out, wid, col, cap, pin=5.0, base=-6.0):
    """a stepped buttress (fr: +u out of the wall, v along it) and its pinnacle."""
    for o, w1 in ((out, top * 0.42), (out * 0.72, top * 0.78), (out * 0.48, top)):
        S.add(Box(fr, -0.6, o, -wid / 2, wid / 2, base, w1, col))
        S.add(Box(fr, o - 0.25, o, -wid / 2 - 0.05, wid / 2 + 0.05, w1 - 0.35, w1, cap))
    if pin:
        pinnacle(S, fr.at(out * 0.24), top, pin, wid * 0.42, col, finial=cap)


def cross(S, fr, w0, h, arm, col):
    """a cross (a finial when arm = 0) on fr's axis, its arm along v: 0.6 m thick, so that it keeps a voxel whatever
    the frame's angle to the grid (a 0.3 m post falls between the voxel centres two times in three)."""
    S.add(Box(fr, -0.3, 0.3, -0.3, 0.3, w0, w0 + h, col))
    if arm:
        S.add(Box(fr, -0.3, 0.3, -arm, arm, w0 + h * 0.62, w0 + h * 0.62 + 0.5, col))


def gable_wall(S, fr, out, half, w0, h, col, cap, finial):
    """a stone gable across a cross roof's end (fr: +u outwards along its ridge, face at u = out): coping, cross,
    pinnacles at its feet."""
    S.add(Roof(fr, out - 0.9, out, -half, half, w0, h, col))
    S.add(Roof(fr, out - 1.0, out + 0.1, -half - 0.1, half + 0.1, w0 + h - 0.9, 1.0, cap))
    cross(S, fr.at(out - 0.45), w0 + h - 0.2, 1.8, 0.6, cap)
    for sv in (-1, 1):
        pinnacle(S, fr.at(out - 0.45, sv * (half - 0.1)), w0 - 0.5, 4.2, 0.42, col, finial=finial)


def exposed(church, a, b, n):
    """is this edge of a part an outside wall of the church (not shared with another part)?"""
    m = (a + b) / 2 + n * 0.8
    return not church.contains(Point(*m))


# ------------------------------------------------------------------------------------------------ build
def build(S, ctx, plan):
    P, area, feats = ctx["P"], ctx["area"], ctx["feats"]
    church = area[MATTHIAS][3]
    b0 = feat_base(ctx, MATTHIAS)
    fn = nave_frame(area, b0)
    T = {k: P(c, ROOF) for k, c in TILES.items()}
    white, white2, shade = P("#e9e5d9"), P("#dad4c5"), P("#c3bcab")
    old, old2 = P("#d5c9ad"), P("#c4b799")
    plinth, door = P("#b3ac9c"), P("#4d3426")
    glass = P("#34363c", WINDOW)
    copper, slate, slate2 = P("#62b5a2", ROOF), P("#3b3f4a", ROOF), P("#4b5263", ROOF)
    gold, iron = P("#d4ad55", METAL), P("#3c3a38", CLASSIC)
    stone = [white, white2, old, old2, shade]
    wallc, oldc = ashlar(white, white2, plinth), ashlar(old, old2, plinth)
    tiles = chevrons(T, glass)

    # OSM's outline is still drawn by voxelize.py (its base sets the Bastion's terrace): clear it, keep its foot
    S.add(Poly(church, b0 + 0.5, b0 + 45, 0, mode="carve"))
    S.add(Poly(church.buffer(1.2), b0 + 5, b0 + 45, 0, mode="carve"))
    own = feats.get(str(MATTHIAS))
    S.add(Poly(church.buffer(1.5), b0 - 6, b0 + 1, plinth, mode="paint", targets=[own["wall"]] if own else [plinth]))
    S.add(Poly(church.buffer(0.4), b0 - 6, b0 + 0.9, plinth))

    def bay(k):
        return (BAYS[k] + BAYS[k + 1]) / 2, (BAYS[k + 1] - BAYS[k]) / 2

    def frieze(u, v, w):
        return ids(np.where(np.mod(np.floor(u * 2) + np.floor(v * 2), 2) == 0, shade, 0), w)

    # ---------------------------------------------------------------- the masses
    S.add(Box(fn, BAYS[0], BAYS[-1], WALL_N, 0, -6, E, oldc))            # the north side: older, warmer stone
    S.add(Box(fn, BAYS[0], BAYS[-1], 0, WALL_S, -6, E, wallc))
    S.add(Box(fn, WEST, BAYS[0], -4.4, 3.6, -6, 17.5, oldc))            # the west bay between the towers
    S.add(Box(fn, BAYS[-1], APSE, -CHOIR, CHOIR, -6, E, wallc))
    S.add(Lathe(fn.at(APSE, 0), -6, E, cyl(APSE_R), wallc, n=8))
    for oid, top, col in ((NORTH_CHAPELS, 10.0, oldc), (NORTH_GABLE, E, oldc), (SACRISTY, 10.5, wallc),
                          (ST_STEPHEN, 12.5, wallc), (SOUTH_CHAPEL, 10.8, wallc), (MARY_PORCH, 9.4, wallc)):
        if oid in area:
            S.add(Poly(area[oid][3], b0 - 6, b0 + top, col))
    # eaves: a corbel table under a moulded cornice, the copper gutter on top
    for vw, vs in ((WALL_N, -1), (WALL_S, 1)):
        S.add(Box(fn, BAYS[0], BAYS[-1], vw - 0.3, vw + 0.3, E - 1.4, E - 0.9, frieze, mode="paint", targets=stone))
        S.add(Box(fn, BAYS[0], BAYS[-1], min(vw, vw + vs * 0.3), max(vw, vw + vs * 0.3), E - 0.9, E - 0.2, white2))
        S.add(Box(fn, BAYS[0], BAYS[-1], min(vw, vw + vs * 0.5), max(vw, vw + vs * 0.5), E - 0.2, E + 0.1, copper))
    for vs in (-1, 1):
        a, b = sorted((vs * CHOIR, vs * (CHOIR + 0.3)))
        S.add(Box(fn, BAYS[-1], APSE, a, b, E - 0.9, E - 0.2, white2))
        a, b = sorted((vs * CHOIR, vs * (CHOIR + 0.5)))
        S.add(Box(fn, BAYS[-1], APSE, a, b, E - 0.2, E + 0.1, copper))
    S.add(Lathe(fn.at(APSE, 0), E - 0.9, E - 0.2, cyl(APSE_R + 0.3), white2, n=8))
    S.add(Lathe(fn.at(APSE, 0), E - 0.2, E + 0.1, cyl(APSE_R + 0.5), copper, n=8))

    # ---------------------------------------------------------------- buttresses and windows
    south = fn.at(0, WALL_S)   # u along the south wall, +v out of it
    for u in BAYS[1:4]:
        buttress(S, fn.at(u, WALL_S, 0, math.pi / 2), E - 0.3, 1.9, 1.3, white, white2, pin=5.2)
        buttress(S, fn.at(u, WALL_N, 0, -math.pi / 2), E - 0.3, 1.2, 1.2, old, white2, pin=5.2, base=9.5)
    for k in range(4):
        window(S, south, bay(k)[0], 1.7, 7.0 if k == 3 else 5.0, 11.8, glass, white2, stone)
    c4 = bay(3)[0]   # the south door under the gabled bay, with its hood
    window(S, south, c4, 1.0, 0.0, 3.6, door, white2, stone, depth=0.9, lights=1, rose=False, pointed=False)
    S.add(Roof(fn.at(c4, WALL_S + 0.35, 0, math.pi / 2), -0.4, 0.4, -1.5, 1.5, 3.6, 2.4, white2))
    # the choir: windows over the annexes, two tiers round the apse, buttresses at the apse's corners
    window(S, fn.at(0, CHOIR), 22.3, 1.0, 5.0, 12.4, glass, white2, stone, lights=2)
    window(S, fn.at(0, -CHOIR, 0, math.pi), -21.2, 1.0, 11.8, 13.6, glass, white2, stone, lights=2)
    for j in (-1, 0, 1):
        fa = fn.at(APSE, 0, 0, j * math.pi / 4).at(APSE_R, 0, 0, -math.pi / 2)
        window(S, fa, 0, 1.0, 9.6, 13.2, glass, white2, stone, lights=2)
        window(S, fa, 0, 0.6, 2.6, 7.2, glass, white2, stone, lights=1, rose=False)
    for j in (-3, -1, 1, 3):   # they end under the cornice, no pinnacles (photos)
        fb = fn.at(APSE, 0, 0, j * math.pi / 8).at(APSE_R / math.cos(math.pi / 8) - 0.2)
        buttress(S, fb, E - 1.5, 1.8, 1.1, white, white2, pin=0)

    # ---------------------------------------------------------------- roofs
    main = (WEST + 0.4, APSE, -CHOIR - 0.5, CHOIR + 0.5, E, RIDGE - E)
    S.add(Roof(fn, *main, roof_tiles((*main, False), tiles)))
    S.add(Lathe(fn.at(APSE, 0), E, RIDGE, cone(APSE_R + 0.5, 0.0), facet_tiles(8, E, RIDGE - E, apse_diamonds(T)), n=8))
    S.add(Box(fn, WEST + 0.4, APSE, -0.25, 0.25, RIDGE - 0.3, RIDGE + 0.3, T["c"]))
    cross(S, fn.at(APSE, 0), RIDGE, 2.2, 0.6, iron)   # over the apse
    for k in range(3):       # the aisles' cross roofs, hipped (the fourth bay has gables)
        c, hb = bay(k)
        for side in (1, -1):
            ft = fn.at(c, 0, 0, side * math.pi / 2)   # u: outwards across the aisle, v: along the nave
            out = (WALL_S if side > 0 else -WALL_N) + 0.5
            args = (-1.0, out, -hb - 0.05, hb + 0.05, E, CROSS_RIDGE - E)
            S.add(Roof(ft, *args, roof_tiles((*args, True), tiles), hip=True))
            cross(S, ft.at(out - hb - 0.1), CROSS_RIDGE - 0.4, 1.8, 0, iron)
    c, hb = bay(3)           # the south gable: two lancets and a roundel, the stair turret at its east corner
    ft = fn.at(c, 0, 0, math.pi / 2)
    out = WALL_S + 0.6
    args = (-1.0, out, -hb - 0.05, hb + 0.05, E, CROSS_RIDGE - E)
    S.add(Roof(ft, *args, roof_tiles((*args, False), tiles)))
    gable_wall(S, ft, out, hb + 0.15, E, CROSS_RIDGE - E + 0.4, white, white2, iron)
    fg = ft.at(out, 0, 0, -math.pi / 2)   # the gable's face: u along it, +v out
    for dv in (-0.9, 0.9):
        window(S, fg, dv, 0.4, 17.3, 19.9, glass, white2, stone, depth=0.3, lights=1, rose=False)
    S.add(Disc(ft, out - 0.6, out + 0.1, 0, 21.4, 0.6, glass, mode="paint", targets=stone))
    tt, rt = fn.at(BAYS[-1] + 0.2, WALL_S + 0.2), 1.75   # a stage of lancets over the eaves, gablets, a stone spire
    S.add(Lathe(tt, -6, 20.3, cyl(rt), wallc, n=8))
    for w0 in (15.9, 20.0):
        S.add(Lathe(tt, w0, w0 + 0.4, cyl(rt + 0.2), white2, n=8))
    for j in range(8):
        fj = tt.at(turn=j * math.pi / 4)
        if j in (7, 0, 1, 2, 3):   # the faces clear of the gable's roof
            window(S, fj.at(rt, 0, 0, -math.pi / 2), 0, 0.35, 16.9, 19.1, glass, white2, stone, depth=0.3, lights=1,
                   rose=False)
        S.add(Roof(fj, rt - 0.1, rt + 0.25, -0.62, 0.62, 20.4, 1.1, white2))
        pinnacle(S, fj.at(turn=math.pi / 8).at(rt / math.cos(math.pi / 8) - 0.1), 20.4, 2.0, 0.22, white)
    S.add(Lathe(tt, 20.4, 28.0, cone(rt - 0.2, 0.08), white, n=8))
    S.add(Lathe(tt, 27.9, 28.3, cyl(0.3), gold))
    cross(S, tt, 28.3, 0.8, 0, iron)   # Matthias's raven

    # ---------------------------------------------------------------- the ridge turret
    fh = fn.at(*TURRET)
    S.add(Lathe(fh, 21.0, 27.8, cyl(1.5), slate, n=8))
    S.add(Lathe(fh, 27.8, 28.2, cyl(1.7), gold, n=8))
    S.add(Lathe(fh, 28.2, 31.2, cyl(1.35), lambda u, v, w: ids(np.where(np.mod(np.floor(w * 2), 2) == 0, slate2, slate), u), n=8))
    S.add(Lathe(fh, 31.2, 31.5, cyl(1.55), gold, n=8))
    for k in range(8):
        cross(S, fh.at(turn=math.pi / 8 + TAU * k / 8).at(1.45), 31.5, 0.8, 0, gold)
    S.add(Lathe(fh, 31.5, 40.4, lambda t: 1.4 * (1 - t) + 0.08, slate, n=8))
    S.add(Lathe(fh, 40.2, 40.8, cyl(0.3), gold))
    cross(S, fh, 40.8, 1.4, 0.6, gold)

    # ---------------------------------------------------------------- the west front
    # the portal porch: a pointed doorway in two orders, the door and the tympanum
    S.add(Box(fn, WEST - 1.5, WEST + 0.1, -3.6, 2.8, -6, 9.2, white2))
    S.add(Box(fn, WEST - 1.7, WEST + 0.1, -3.8, 3.0, 9.2, 9.55, copper))
    S.add(Box(fn, WEST - 1.6, WEST - 1.4, -3.0, 2.2, 8.0, 8.6, frieze, mode="paint", targets=stone))
    fw = fn.at(WEST - 1.5, -0.4)
    step = max(ctx["ground_m"](fw.ox, fw.oy) - b0, 0.0)   # the doorway opens at the pavement (steps go down inside)
    S.add(Arch(fw, -0.3, 0.7, 0, 2.15, step, 4.7, pointed=True, mode="carve"))
    S.add(Arch(fw, 0.7, 1.4, 0, 1.6, step, 4.4, pointed=True, mode="carve"))
    S.add(Box(fw, 1.4, 1.9, -1.6, 1.6, -0.5, 3.3, door))
    S.add(Arch(fw, 1.4, 1.9, 0, 1.6, 3.3, 4.4, pointed=True,
               col=lambda u, v, w: ids(np.where(np.hypot(v, w - 4.3) < 0.7, gold, shade), u)))
    # the rose window
    rv, rw = -0.4, 13.3

    def rose(u, v, w):
        d = np.hypot(v - rv, w - rw)
        spoke = np.abs(np.mod(np.arctan2(w - rw, v - rv) / TAU * 8, 1.0) - 0.5) > 0.36
        tr = (np.abs(d - 1.25) < 0.24) | (d < 0.45) | ((d > 1.25) & spoke)
        return ids(np.where(d < 2.5, np.where(tr, white2, glass), np.where(d < 3.0, shade, 0)), u)
    S.add(Disc(fn, WEST - 0.5, WEST + 0.4, rv, rw, 2.5, 0, mode="carve"))
    S.add(Disc(fn, WEST + 0.35, WEST + 0.9, rv, rw, 2.5, rose, mode="paint", targets=stone))
    S.add(Disc(fn, WEST - 0.3, WEST + 0.05, rv, rw, 3.0, rose, mode="paint", targets=stone))
    # the cornice under the gable, and the openwork gable (Schulek's "áttört oromzat"): an arcade, five lancets
    S.add(Box(fn, WEST - 0.35, WEST + 0.5, -4.6, 3.8, 16.9, 17.5, white2))
    S.add(Roof(fn, WEST - 0.25, WEST + 0.6, rv - 4.6, rv + 4.6, 17.5, 13.0, white))
    fg = fn.at(WEST - 0.25, rv, 0, -math.pi / 2)   # u along the gable (northwards), +v into the church
    for dv in (-3.0, -1.8, -0.6, 0.6, 1.8, 3.0):
        S.add(Arch(fg.at(dv, 0, 0, math.pi / 2), -0.4, 0.3, 0, 0.3, 17.8, 19.6, glass, pointed=True, mode="paint",
                   targets=stone))
    fgo = fn.at(WEST - 0.25, rv, 0, math.pi / 2)   # the same face, +v out
    for dv, apex in ((-2.2, 22.6), (-1.1, 25.6), (0.0, 28.6), (1.1, 25.6), (2.2, 22.6)):
        window(S, fgo, dv, 0.38, 20.6, apex - 0.66, glass, white2, stone, depth=0.35, lights=1, rose=False)
    for k in range(1, 9):   # crockets up the slopes
        for sv in (-1, 1):
            dv = sv * k * 0.55
            top = 17.5 + (4.6 - abs(dv)) * 13.0 / 4.6
            S.add(Box(fg, dv - 0.2, dv + 0.2, -0.1, 0.5, top, top + 0.45, white2))
    cross(S, fn.at(WEST, rv), 30.4, 1.8, 0.7, white2)
    for dv in (-4.4, 4.4):
        pinnacle(S, fg.at(dv, 0.3), 17.5, 6.5, 0.45, white, finial=white2)

    # ---------------------------------------------------------------- the Béla tower (north-west)
    S.add(Box(fn, WEST + 0.1, BAYS[0], -14.6, -4.4, -6, 21.0,
              lambda u, v, w: np.where(w < 16.6, oldc(u, v, w), wallc(u, v, w)).astype(np.uint16)))
    for uu in (WEST + 0.1, BAYS[0] - 0.25):
        for vv in (-14.6, -4.65):
            S.add(Box(fn, uu - 0.25, uu + 0.25, vv - 0.25, vv + 0.25, 1.0, 20.4, white2))
    for w0 in (16.2, 20.0):
        S.add(Box(fn, WEST - 0.3, BAYS[0], -14.9, -4.4, w0, w0 + 0.5, frieze, mode="paint", targets=stone))
    S.add(Box(fn, WEST - 0.3, BAYS[0] + 0.1, -14.9, -4.3, 20.5, 21.0, white2))
    S.add(Box(fn, WEST - 0.35, BAYS[0] + 0.15, -14.95, -4.25, 21.0, 21.2, copper))
    bw = fn.at(WEST + 0.1, BT[1], 0, math.pi / 2)   # its west face: u along it (southwards), +v out
    bn = fn.at(BT[0], -14.6, 0, math.pi)            # its north face
    for fb in (bw, bn):
        window(S, fb, 0, 2.0, 17.6, 19.3, glass, white2, stone, lights=4, rose=False, pointed=False, depth=0.4)
        for dv in (-3.7, 3.7):
            window(S, fb, dv, 0.4, 17.7, 19.1, glass, white2, stone, lights=1, rose=False, pointed=False, depth=0.3)
        window(S, fb, -1.5, 0.5, 8.6, 12.2, glass, white2, stone, lights=1, rose=False, pointed=False, depth=0.4)
    S.add(Disc(fn, WEST - 0.3, WEST + 0.5, BT[1] + 1.0, 3.2, 0.7, glass, mode="paint", targets=stone))
    # its helm: the octagonal tiled spire, four tiled corner spirelets, a dormer on each face, iron crosses
    fbt = fn.at(*BT)
    S.add(Lathe(fbt, 21.0, 35.2, cone(3.0, 0.06), facet_tiles(8, 21.0, 14.2, bela_tiles(T)), n=8))
    cross(S, fbt, 35.0, 3.2, 0.7, iron)
    S.add(Lathe(fbt, 35.5, 35.9, cyl(0.3), gold))
    for k in range(4):
        fd = fbt.at(turn=k * math.pi / 2)
        S.add(Box(fd, 2.6, 4.3, -0.8, 0.8, 21.0, 22.7, white))
        S.add(Roof(fd, 2.4, 4.4, -0.95, 0.95, 22.7, 1.3, white2))
        S.add(Box(fd, 4.0, 4.5, -0.55, 0.55, 21.5, 22.4, glass, mode="paint", targets=stone))
    for uu in (-28.6, -22.6):   # square, flush with the tower's faces, tiled like the helm
        for vv in (-13.1, -5.9):
            fs = fn.at(uu, vv)
            S.add(Lathe(fs, 21.0, 27.6, cone(1.3, 0.05), facet_tiles(4, 21.0, 6.6, bela_tiles(T)), n=4))
            cross(S, fs, 27.4, 1.4, 0, iron)
    if NW_STAIR in area:   # the stair turret on its north side
        fst = Frame(*area[NW_STAIR][3].centroid.coords[0], b0)
        S.add(Lathe(fst, -6, 19.5, cyl(1.75), oldc, n=8))
        S.add(Lathe(fst, 19.3, 19.8, cyl(2.0), white2, n=8))
        S.add(Lathe(fst, 19.8, 24.0, cone(1.9, 0.1), white2, n=8))

    # ---------------------------------------------------------------- the Matthias tower (south-west)
    tx, ty = fn.xy(*MT)
    gt = ctx["ground_m"](tx, ty)
    tw = Frame(tx, ty, gt, fn.ang)
    h0, foot = 4.6, b0 - gt - 6
    S.add(Box(tw, -h0, h0, -h0, h0, foot, 17.5, wallc))
    for k in range(4):   # diagonal buttresses at the corners, rising into pinnacle clusters round the octagon
        fc = tw.at(turn=math.pi / 4 + k * math.pi / 2).at(h0 * math.sqrt(2) - 0.8)
        for o, w1 in ((1.8, 7.5), (1.4, 17.5), (1.0, 25.5)):
            S.add(Box(fc, -1.0, o, -0.85, 0.85, foot, w1, wallc))
            S.add(Box(fc, o - 0.3, o, -0.9, 0.9, w1 - 0.35, w1, white2))
        pinnacle(S, fc.at(0.5), 25.5, 5.5, 0.6, white, finial=white2)
        for sv in (-1, 1):
            pinnacle(S, fc.at(-0.2, sv * 1.0), 22.0, 4.5, 0.38, white, finial=white2)
    for k in (1, 2):   # the two square storeys' windows on the free faces (south, west)
        ff = tw.at(turn=k * math.pi / 2).at(h0, 0, 0, -math.pi / 2)
        window(S, ff, 0, 0.6, 3.0, 5.9, glass, white2, stone, lights=1, rose=False)
        window(S, ff, 0, 0.75, 9.6, 14.2, glass, white2, stone, lights=2, rose=False)
    S.add(Box(tw, -h0 - 0.3, h0 + 0.3, -h0 - 0.3, h0 + 0.3, 7.3, 7.7, white2))
    S.add(Box(tw, -h0 - 0.35, h0 + 0.35, -h0 - 0.35, h0 + 0.35, 17.5, 18.1, white2))
    # three octagonal storeys (the fourth holds King Matthias's arms of 1470), each with lancets under gablets, corner
    # shafts, a cornice, and a little narrower
    for w0, w1, r, hw, sill, spring, faces in ((17.5, 27.5, 4.1, 0.85, 18.8, 23.2, (0, 2, 4, 6)),
                                               (27.5, 37.5, 3.95, 0.8, 28.8, 33.4, range(8)),
                                               (37.5, 46.7, 3.8, 0.75, 38.6, 42.9, range(8))):
        S.add(Lathe(tw, w0, w1, cyl(r), wallc, n=8))
        S.add(Lathe(tw, w1 - 0.5, w1, cyl(r + 0.3), white2, n=8))
        for j in range(8):
            fj = tw.at(turn=j * math.pi / 4)
            S.add(Box(fj.at(turn=math.pi / 8).at(r / math.cos(math.pi / 8) - 0.15), 0, 0.5, -0.3, 0.3, w0, w1 - 0.5, white2))
            if j in faces:   # a lancet in a blind arch
                ff = fj.at(r, 0, 0, -math.pi / 2)
                S.add(Arch(ff.at(0, 0, 0, math.pi / 2), -0.3, 0.3, 0, hw + 0.45, sill - 0.5, spring, shade, pointed=True,
                           mode="paint", targets=stone))
                window(S, ff, 0, hw, sill, spring, glass, white2, stone, lights=2, rose=False, depth=0.35)
                S.add(Roof(fj, r - 0.05, r + 0.3, -hw - 0.35, hw + 0.35, spring + hw * math.sqrt(3) + 0.1, 1.2, white2))
    # the balcony at 46.73 m on its corbels, the closed storey with four corner bays and gargoyles
    S.add(Lathe(tw, 45.9, 46.7, cone(3.8, 4.5), white2, n=8))
    S.add(Lathe(tw, 46.7, 47.0, cyl(4.55), white2, n=8))

    def posts(r, rail):
        return lambda u, v, w: ids(np.where((np.mod(np.arctan2(v, u) * r, 0.8) < 0.4) | (w > rail), white2, 0))
    S.add(Lathe(tw, 47.0, 48.0, cyl(4.55), posts(4.55, 47.75), n=8, inner=0.35))
    S.add(Lathe(tw, 47.0, 54.0, cyl(3.45), wallc, n=8))
    for j in range(8):
        fj = tw.at(turn=j * math.pi / 4)
        window(S, fj.at(3.45, 0, 0, -math.pi / 2), 0, 0.35, 49.0, 51.8, glass, white2, stone, lights=1, rose=False,
               depth=0.3)
        S.add(Capsule(fj, (3.3, 0, 53.4), (5.0, 0, 53.0), 0.25, white2))
    for k in range(4):
        fb = tw.at(turn=math.pi / 4 + k * math.pi / 2).at(3.7)
        S.add(Lathe(fb, 45.8, 47.5, cone(0.25, 1.0), white2, n=8))
        S.add(Lathe(fb, 47.5, 53.2, cyl(1.0), wallc, n=8))
        for j in range(3):
            S.add(Box(fb.at(turn=(j - 1) * math.pi / 4), 0.75, 1.1, -0.25, 0.25, 49.0, 51.6, glass, mode="paint",
                      targets=stone))
        S.add(Lathe(fb, 53.0, 53.4, cyl(1.15), white2, n=8))
        S.add(Lathe(fb, 53.4, 55.9, cone(1.0, 0.06), white, n=8))
        cross(S, fb, 55.8, 0.7, 0, white2)
    S.add(Lathe(tw, 53.9, 54.5, cyl(3.8), white2, n=8))
    S.add(Lathe(tw, 54.5, 55.3, cyl(3.7), posts(3.7, 55.05), n=8, inner=0.3))
    # the open lantern: eight tall pointed arches under gablets, a ring of pinnacles
    S.add(Lathe(tw, 54.5, 61.3, cyl(2.75), wallc, n=8, inner=0.55))
    for j in range(8):
        fj = tw.at(turn=j * math.pi / 4)
        S.add(Arch(fj, 2.0, 3.0, 0, 0.72, 55.2, 59.3, pointed=True, mode="carve"))
        S.add(Roof(fj, 2.5, 3.05, -0.9, 0.9, 59.6, 1.9, white2))
        pinnacle(S, fj.at(turn=math.pi / 8).at(3.45), 55.3, 6.0, 0.32, white, finial=white2)
    S.add(Lathe(tw, 61.0, 61.5, cyl(3.0), white2, n=8))
    # the crocketed stone spire, its knob and cross
    def sp(t):
        return 2.3 * (1 - t) ** 1.05 + 0.12
    S.add(Lathe(tw, 61.5, 75.0, sp, white, n=8))
    for wq in np.arange(62.6, 74.2, 1.15):
        r_ = sp((wq - 61.5) / 13.5) / math.cos(math.pi / 8)
        for j in range(8):
            S.add(Box(tw.at(turn=math.pi / 8 + j * math.pi / 4), r_ - 0.15, r_ + 0.4, -0.3, 0.3, wq, wq + 0.5, white2))
    for wq in (65.6, 69.6):
        S.add(Lathe(tw, wq, wq + 0.4, cyl(sp((wq - 61.5) / 13.5) + 0.25), white2, n=8))
    S.add(Lathe(tw, 74.6, 75.6, cyl(0.5), white2, n=8))
    cross(S, tw, 75.6, 1.0, 0.5, copper)

    # ---------------------------------------------------------------- the south side's porch and chapel
    if MARY_PORCH in area:   # Schulek's porch before the 14th-century Mary portal
        fa = fn.at(-17.85, 19.3, 0, math.pi / 2)   # u: out of its south face
        S.add(Arch(fa, -1.6, 0.3, 0, 1.9, 0, 5.2, pointed=True, mode="carve"))
        S.add(Arch(fa, -1.9, -1.5, 0, 1.6, 0, 5.0, pointed=True,
                   col=lambda u, v, w: ids(np.where(w < 3.4, door, np.where(np.hypot(v, w - 4.6) < 0.6, gold, shade)), u)))
        S.add(Roof(fa, -0.1, 0.4, -2.3, 2.3, 6.6, 3.3, white2))
        cross(S, fa.at(0.15), 9.6, 1.3, 0, white2)
        for su in (-1, 1):
            buttress(S, fn.at(-17.85 + su * 3.55, 19.3, 0, math.pi / 2 - su * math.pi / 4), 9.4, 1.1, 1.0, white,
                     white2, pin=4.0)
        for a, b, n in ring_segments(area[MARY_PORCH][3], 2.0):
            if exposed(church, a, b, n):
                balustrade(S, seg_frame(a, b, n, b0), float(np.hypot(*(b - a))), 9.4, white, white2)
        args = (-21.2, -14.5, WALL_S - 0.5, 19.5, 9.4, 3.4)
        S.add(Roof(fn, *args, roof_tiles((*args, True), small_chevrons(T)), hip=True))
    if SOUTH_CHAPEL in area:
        for a, b, n in ring_segments(area[SOUTH_CHAPEL][3], 2.0):
            if not exposed(church, a, b, n):
                continue
            L = float(np.hypot(*(b - a)))
            fr2 = seg_frame(a, b, n, b0)
            balustrade(S, fr2, L, 10.8, white, white2)
            for s0 in np.arange(1.5, L - 1.0, 2.6):
                if np.hypot(*(a + (b - a) * s0 / L - (tt.ox, tt.oy))) > rt + 1.0:   # not into the stair turret
                    window(S, out_frame(fr2), -s0, 0.75, 3.4, 8.2, glass, white2, stone, lights=2, rose=False)
        fc = fn.at(18.3, 12.3, 0, math.pi / 4)
        S.add(Box(fc, -0.5, 1.2, -0.55, 0.55, -6, 10.6, white))
        pinnacle(S, fc.at(0.5), 10.6, 4.2, 0.42, white, finial=white2)
        S.add(Poly(area[SOUTH_CHAPEL][3], b0 + 10.3, b0 + 10.8, shade))   # a flat roof behind the balustrade (photos)

    # ---------------------------------------------------------------- the north side
    fo = fn.at(0, -21.0, 0, math.pi)   # the north faces: u reversed, +v out
    if NORTH_CHAPELS in area:   # Schulek's neo-Gothic row of chapels on the north aisle
        for k in range(4):
            c = BAYS[0] + (k + 0.5) * 5.85
            window(S, fo.at(0, 0.2), -c, 0.7, 4.6, 8.0, glass, white2, stone, lights=2, rose=False)
            S.add(Disc(fn.at(c, -21.6, 0, math.pi / 2), -0.1, 0.8, 0, 2.4, 0.6, glass, mode="paint", targets=stone))
        for k in range(5):
            c = BAYS[0] + k * 5.85
            S.add(Box(fn, c - 0.45, c + 0.45, -21.9, -21.0, -6, 10.0, old))
            pinnacle(S, fn.at(c, -21.45), 10.0, 3.6, 0.4, white, finial=white2)
        S.add(Box(fn, BAYS[0], 2.3, -21.45, -20.9, 10.0, 10.7, white2))
        args = (BAYS[0], 2.3, -21.2, -5.4, 10.0, 3.0)
        S.add(Roof(fn, *args, roof_tiles((*args, False), rosettes(T))))
    if NORTH_GABLE in area:   # the north gable over the fourth bay: a big window, two roundels, its cross roof
        window(S, fo, -6.9, 1.6, 6.0, 12.2, glass, white2, stone)
        for c in (5.0, 8.8):
            S.add(Disc(fn.at(c, -21.4, 0, math.pi / 2), -0.1, 0.8, 0, 3.0, 0.6, glass, mode="paint", targets=stone))
        ftn = fn.at(6.95, 0, 0, -math.pi / 2)
        args = (-1.0, 21.4, -4.75, 4.75, E, 7.4)
        S.add(Roof(ftn, *args, roof_tiles((*args, False), tiles)))
        gable_wall(S, ftn, 21.5, 4.85, E, 7.8, old, white2, iron)
        fg = ftn.at(21.5, 0, 0, -math.pi / 2)
        for dv in (-1.0, 1.0):
            window(S, fg, dv, 0.42, 17.2, 20.3, glass, white2, stone, depth=0.3, lights=1, rose=False)
        S.add(Disc(ftn, 20.9, 21.6, 0, 22.0, 0.55, glass, mode="paint", targets=stone))
        S.add(Box(fn.at(11.5, -21.0, 0, -math.pi / 4), -0.5, 1.4, -0.6, 0.6, -6, 14.5, old))
        tt = fn.at(11.9, -21.4)   # its tall corner turret
        S.add(Lathe(tt, 14.0, 20.5, cyl(1.1), wallc, n=8, rot=math.pi / 8))
        S.add(Lathe(tt, 20.3, 20.7, cyl(1.3), white2, n=8, rot=math.pi / 8))
        S.add(Lathe(tt, 20.7, 26.5, cone(1.15, 0.08), white, n=8, rot=math.pi / 8))
    if SACRISTY in area:   # the sacristy and the north door: a balustrade, a low dark roof, the tiled one behind
        for a, b, n in ring_segments(area[SACRISTY][3], 2.0):
            if exposed(church, a, b, n):
                balustrade(S, seg_frame(a, b, n, b0), float(np.hypot(*(b - a))), 10.5, white, white2)
        window(S, fo, -14.4, 0.9, 0.0, 3.4, door, white2, stone, depth=0.8, lights=1, rose=False, pointed=False)
        S.add(Roof(fn.at(14.4, -21.3, 0, -math.pi / 2), -0.4, 0.4, -1.3, 1.3, 3.4, 2.4, white2))
        window(S, fo, -14.4, 0.7, 6.0, 8.6, glass, white2, stone, lights=2, rose=False)
        S.add(Roof(fn, 11.3, 17.4, -21.2, -14.5, 10.5, 1.8, slate, hip=True))
        args = (17.0, 24.5, -15.0, -6.1, 10.5, 4.2)
        S.add(Roof(fn, *args, roof_tiles((*args, True), rosettes(T)), hip=True))
    if ST_STEPHEN in area:   # Schulek's St Stephen chapel, where the Garai chapel stood
        g = area[ST_STEPHEN][3]
        corners = set()
        for a, b, n in ring_segments(g, 1.2):
            if not exposed(church, a, b, n):
                continue
            L = float(np.hypot(*(b - a)))
            fr2 = seg_frame(a, b, n, b0)
            balustrade(S, fr2, L, 12.5, white, white2)
            for s0 in np.arange(1.6, L - 1.0, 2.8):
                window(S, out_frame(fr2), -s0, 0.8, 4.0, 9.8, glass, white2, stone, lights=2, rose=False)
            corners |= {(round(a[0], 1), round(a[1], 1)), (round(b[0], 1), round(b[1], 1))}
        for x, y in sorted(corners):   # buttress shafts and pinnacles at its corners
            fv = Frame(x, y, b0)
            S.add(Lathe(fv, -6, 12.5, cyl(0.5), wallc, n=4, rot=math.pi / 4))
            pinnacle(S, fv, 12.5, 4.0, 0.42, white, finial=white2)
        x, y, L1, L2, ang = rect_of(g)
        args = (-L1 / 2 - 0.3, L1 / 2 + 0.3, -L2 / 2 - 0.3, L2 / 2 + 0.3, 12.5, 4.4)
        S.add(Roof(Frame(x, y, b0, ang), *args, roof_tiles((*args, True), rosettes(T)), hip=True))
        st = fn.at(17.0, -15.0)   # the stair turret between the chapel and the sacristy
        S.add(Lathe(st, -6, 19.5, cyl(1.4), wallc, n=8))
        S.add(Lathe(st, 19.3, 19.8, cyl(1.65), white2, n=8))
        S.add(Lathe(st, 19.8, 26.8, cone(1.45, 0.06), white, n=8))
        cross(S, st, 26.7, 0.8, 0, white2)
