"""The Citadella on Gellért Hill (Emanuel Zitta to Ignaz Weiss's plans, 1850-54), as renewed in 2020-26 to the designs
of Dániel Taraczky (art1st design studio): walls of Süttő limestone capped with red Tardos limestone round a park of
paths, beds and young trees, walks along the walls behind their parapets, the bastions viewing terraces. In the west
the round Rondella (now the museum A Szabadság Bástyája) with a roof terrace and a water mirror in its court, its glass
foyer on a reception square between two ranges of casemates; three cuts through the walls lined with white concrete
(the Rondella's north and south mouths, the stair down to the Liberty Statue through the east bastion). In the middle
of the park, on a grassy mound over the old observatory's rock, Hungary's largest flag on a 36.3 m mast. Outlines are
OSM's, levels come from the steps OSM counts and the 2026 street photos (docs/landmarks.md).
"""
import math

import numpy as np
import shapely
from scipy import ndimage
from shapely.geometry import LineString, Point, Polygon

from landmarks import LIBERTY_SIDES, Box, Ellipsoid, Field, Frame, Lathe, Poly, Prim, cone, cyl, rect_of, ring_segments
from landmarks_city import dist_in, grid_of
from landmarks_kossuth import flag
from landmarks_more import rect_poly
from style import GLASS, GRASS, LEAF, METAL, SOIL, WATER

FORT, MUSEUM, PARK = 829110605, 20421437, 1498073283  # the walls' outline, the Rondella (its court a pond), the park
BARRACKS = (345057628, 828709363)                      # the casemate ranges north and south of the reception square
PARTS = (828709364, 828709365, 1498073284)
SERVICE = 1497471344                                   # the low crescent round the Rondella's west
V_WALLS = (1498073285, 1498073286)                     # the cut through the east bastion
FLAGPOLE = 11331034119

NAMES = ["Citadella"]
DROP = {MUSEUM, *BARRACKS, *PARTS, SERVICE}

# Levels, metres above sea level. The park: the 2026 panoramas' GPS heights (271-275 m on the ellipsoid, less the
# ~44 m geoid) and the surface model over the open courtyard (229-233 m) put it near 229 m. The rest from the steps
# OSM counts, ~15 cm each: 22 from the reception square up to the park, 24 and 11 from the square down to the
# promenades through the north and south mouths, 52 down the east cut to the Liberty Statue (a phone's heights in the
# 2026 photos going down it: 9 m), 14-22 up to the walks.
PARK_ASL = 229.0
REC, WALK, RONDELLA, CASEMATE, STATUE = -3.3, 2.5, 5.0, 4.4, -8.3
# the promenades round the walls (grid x, y; metres asl): those steps, the 2016 and 2026 photos along the Citadella
# sétány (the south wall stands ~7 m over it), the plaza west of the Rondella a metre or two under the park
FEET = [((484, 3072), 222.1), ((458, 3040), 222.5), ((425, 3045), 224.5), ((402, 3080), 226.5), ((412, 3108), 226.0),
        ((441, 3121), 224.0), ((470, 3150), 224.0), ((490, 3180), 224.0), ((520, 3205), 223.5), ((545, 3240), 221.5),
        ((575, 3242), PARK_ASL + STATUE), ((592, 3215), 220.5), ((588, 3185), 220.5), ((570, 3140), 221.0),
        ((535, 3112), 222.0), ((505, 3092), 222.0)]
NORTH_MOUTH = ((483.4, 3078.2), (474.2, 3090.2))       # OSM's steps: foot, head
SOUTH_MOUTH = ((443.0, 3118.7), (453.4, 3110.5))
REC_STAIR = ((464.5, 3102.0), (475.5, 3112.5))         # from the square up to the park
WALK_W = 4.5                                            # the walk behind the parapet, to its railing over the park
STATUE_XY, STATUE_NODE = (575.2, 3239.7), 1488974596     # the Liberty Statue
TERRACE = (-8.0, 19.0, -12.0, 13.0)  # its terrace in its frame, level out to OSM's retaining walls and the steps down
BASTIONS = [  # bastion tops that are terraces at the walks' level (OSM's outline points; the inner edges from photos)
    [(536.3, 3139.9), (546.1, 3131.0), (556.1, 3136.5), (558.5, 3147.6), (547.6, 3155.2), (541.0, 3147.0)],
    [(566.0, 3182.8), (571.4, 3208.5), (581.3, 3206.8), (581.7, 3210.9), (581.4, 3215.0), (580.3, 3219.0),
     (578.6, 3222.8), (576.2, 3226.1), (558.0, 3200.0), (560.0, 3190.0)],
    [(563.3, 3233.7), (559.2, 3234.2), (555.1, 3233.9), (551.1, 3232.9), (547.3, 3231.2), (543.9, 3228.8),
     (550.1, 3221.1), (536.0, 3210.0), (551.0, 3203.5)],
]


def largest(g):
    return max(getattr(g, "geoms", [g]), key=lambda q: q.area)


def feet_level(x, y):
    """the promenades' level round the walls (metres asl), weighted by inverse distance to FEET."""
    num, den = 0.0, 0.0
    for (fx, fy), z in FEET:
        w = 1.0 / ((x - fx) ** 2 + (y - fy) ** 2 + 25.0)
        num, den = num + w * z, den + w
    return num / den


def statue_frame(osm):
    """the Liberty Statue's frame: u forward, down the east cut and between its two side figures."""
    st = next((p for oid, t, p in osm.nodes if oid == STATUE_NODE), Point(*STATUE_XY))
    sides = [np.array([p.x, p.y]) for oid, t, p in osm.nodes if oid in LIBERTY_SIDES]
    if len(sides) != 2:
        return None
    fwd = (sides[0] + sides[1]) / 2 - (st.x, st.y)
    return Frame(st.x, st.y, 0.0, math.atan2(fwd[1], fwd[0]))


def reception(area, fort):
    """the reception square: what the walls enclose between the Rondella, the two ranges and the park."""
    if not all(k in area for k in (MUSEUM, PARK, *BARRACKS)):
        return None
    rest = fort.difference(Polygon(largest(area[MUSEUM]).exterior)).difference(largest(area[PARK]))
    for b in BARRACKS:
        rest = rest.difference(area[b])
    p = Point(*np.mean([REC_STAIR[0], NORTH_MOUTH[1], SOUTH_MOUTH[1]], axis=0))
    parts = [g for g in getattr(rest, "geoms", [rest]) if g.area > 20]
    return min(parts, key=lambda g: g.distance(p)) if parts else None


def built(osm):
    """the fortress's outline: built over for the ground model's open-ground test, though its buildings are dropped
    (the surface model sees the walls; read as open, the slopes round it rose up to 12 m)."""
    return [largest(g) for oid, k, t, g in osm.areas if oid == FORT]


def ground(G, wlev, osm, cells_of, note):
    """voxelize.py's ground over the hilltop. FABDEM took the fortress for a building and dug it out (212 m inside
    walls round a park near 229 m), and the summit's node raised the plaza west of the Rondella over its roof. Inside
    the walls the park's level, the reception square and the Rondella's court lower; round them the promenades'
    levels, blending into the hill over ~25 m (~50 m where the ground comes down)."""
    area = {oid: g for oid, k, t, g in osm.areas if oid in (FORT, MUSEUM, PARK, *BARRACKS)}
    if FORT not in area:
        return
    fort = largest(area[FORT])
    x0, y0, x1, y1 = fort.buffer(60).bounds
    r0, r1 = max(int(y0), 0), min(int(y1) + 1, G.shape[0])
    c0, c1 = max(int(x0), 0), min(int(x1) + 1, G.shape[1])
    yy, xx = np.mgrid[r0:r1, c0:c1] + 0.5
    d = shapely.distance(fort, shapely.points(xx.ravel(), yy.ravel())).reshape(xx.shape)
    t = feet_level(xx, yy)
    sub = G[r0:r1, c0:c1]
    sub += ((t - sub) * np.where(t > sub, np.clip((30 - d) / 23, 0, 1), np.clip((55 - d) / 48, 0, 1))).astype(G.dtype)
    sf = statue_frame(osm)
    if sf is not None:  # the statue's terrace: level, where the blend left it falling away in front (3 m at its steps)
        rr, cc = cells_of(rect_poly(sf, *TERRACE))
        G[rr, cc] = PARK_ASL + STATUE
    rr, cc = cells_of(fort)
    G[rr, cc] = PARK_ASL
    rec = reception(area, fort)
    if rec is not None:
        rr, cc = cells_of(rec.buffer(1.0))
        G[rr, cc] = PARK_ASL + REC
    if MUSEUM in area:
        court = largest(Polygon(largest(area[MUSEUM]).exterior).difference(area[MUSEUM]))
        rr, cc = cells_of(court.buffer(1.0))
        G[rr, cc] = PARK_ASL + REC - 0.6
        wlev[rr, cc] = np.where(np.isfinite(wlev[rr, cc]), PARK_ASL + REC - 0.6, wlev[rr, cc])
    note(f"ground: the Citadella's park at {PARK_ASL:.1f} m, the promenades round it "
         f"{min(z for _, z in FEET):.1f}-{max(z for _, z in FEET):.1f} m")


class Mound(Prim):
    """a low elliptical mound ru x rv, rising h over w0 (frame-relative)."""

    def __init__(self, fr, ru, rv, w0, h, col, **kw):
        self.p = (ru, rv, w0, h)
        super().__init__(fr, col, (-ru, ru, -rv, rv, w0, w0 + h), **kw)

    def inside(self, u, v, w, x, y):
        ru, rv, w0, h = self.p
        r = (u / ru) ** 2 + (v / rv) ** 2
        return (r <= 1) & (w >= w0 - 1.0) & (w < w0 + h * np.sqrt(np.clip(1 - r, 0, 1)) + 0.01)


def stair(S, a, b, z0, z1, width, col, under=1.5):
    """a straight flight from a (level z0) to b (z1), metres above the base: steps of ~16 cm, solid underneath, open
    above. Returns its frame (u from a to b) and length."""
    a, b = np.array(a, float), np.array(b, float)
    L = float(np.hypot(*(b - a)))
    fr = Frame(a[0], a[1], 0.0, math.atan2(b[1] - a[1], b[0] - a[0]))
    n = max(int(round(abs(z1 - z0) / 0.16)), 1)
    hi = max(z0, z1) + 6.0
    for i in range(n):
        top = z0 + (z1 - z0) * (i + 1) / n
        S.add(Box(fr, L * i / n, L * (i + 1) / n + 0.05, -width / 2, width / 2, min(z0, z1) - under, top, col))
        S.add(Box(fr, L * i / n, L * (i + 1) / n, -width / 2, width / 2, top, hi, 0, mode="carve"))
    return fr, L


# ------------------------------------------------------------------------------------------------ the fortress
def citadella(S, ctx, plan):
    pc, area, BASE, F = ctx["P"], ctx["area"], ctx["BASE"], ctx["F"]
    fort = largest(area[FORT][3])
    mus, park = area[MUSEUM][3], largest(area[PARK][3])
    rond = Polygon(largest(mus).exterior)
    court = largest(rond.difference(mus))
    ranges = [largest(area[b][3]) for b in BARRACKS]
    P = PARK_ASL - BASE
    R, W, RT, TB = P + REC, P + WALK, P + RONDELLA, P + CASEMATE
    c = dict(stone=pc("#ddd3bd"), stone2=pc("#d2c7ae"), plinth=pc("#cbbfa4"), coping=pc("#b98f7c"),
             pave=pc("#d9d3c6"), pave2=pc("#cdc6b8"), white=pc("#eceae4"), glass=pc("#86b9b2", GLASS),
             mull=pc("#2f3436", METAL), rail=pc("#2a2d2f", METAL), win=pc("#34363c", 21), water=pc("#4f8f9c", WATER),
             mulch=pc("#6f5540", SOIL), lawn=pc("#7fae55", GRASS), roof=pc("#7a5a43", SOIL), shrub=pc("#64804a", LEAF))

    # the Rondella's east edge, on the reception square: u along it, v into the Rondella
    a, b, n = max(ring_segments(rond.simplify(0.5), 2.0), key=lambda s: np.hypot(*(s[1] - s[0])))
    fe = Frame(a[0], a[1], 0.0, math.atan2(b[1] - a[1], b[0] - a[0]))
    if (np.array([-fe.sa, fe.ca]) @ n) > 0:
        fe = Frame(b[0], b[1], 0.0, fe.ang + math.pi)
    cu, cv = fe.uv(*np.array(court.exterior.coords).T)
    near = cv < 20
    fu0, fu1 = float(cu[near].min()), float(cu[near].max())  # the court's open side: the foyer stands before it
    fdep = float(np.percentile(cv[near], 10))
    rec = reception({k: area[k][3] for k in (MUSEUM, PARK, *BARRACKS)}, fort)
    vl = {oid: ln for oid, t, ln in ctx["osm"].lines if oid in V_WALLS}
    vcut = Polygon([*vl[V_WALLS[0]].coords, *vl[V_WALLS[1]].coords]).convex_hull if len(vl) == 2 else None
    mouths = [LineString(m).buffer(3.4, cap_style="flat") for m in (NORTH_MOUTH, SOUTH_MOUTH)]

    # the walls: the outer face battered towards its foot, the parapet with its coping, the walk behind it at W, a
    # railing where the walk stands over the park; the bastions' tops are terraces at the walk's level
    x0f, y0f, X, Y = grid_of(fort, 6.0)
    d = dist_in(fort, X, Y)
    own = np.zeros(X.shape, bool)
    for g in [rond, *ranges, *mouths] + [q for q in (rec, vcut) if q is not None]:
        own |= shapely.contains_xy(g.buffer(0.3), X, Y)
    bast = np.any([shapely.contains_xy(Polygon(q), X, Y) for q in BASTIONS], axis=0)
    walk = (d > 0) & ~own & ((d < WALK_W) | bast)
    parkc = (d > 0) & ~own & ~walk
    drail = (ndimage.distance_transform_edt(~parkc) / F).astype(np.float32)
    gout = (ndimage.map_coordinates(ctx["G"], [Y.ravel() - 0.5, X.ravel() - 0.5], order=1, mode="nearest")
            .reshape(X.shape) - BASE).astype(np.float32)
    gy_, gx_ = np.gradient(d)
    A = np.where(np.abs(gx_) > np.abs(gy_), Y, X).astype(np.float32)  # a coordinate along the nearest wall
    fields = dict(d=d, walk=walk.astype(np.uint8), out=((d <= 0) & ~own).astype(np.uint8), rail=drail, g=gout, A=A)

    def walls(f, w):
        d_, wk, out, dr, g_, A_ = (f[k][None] for k in ("d", "walk", "out", "rail", "g", "A"))
        wk, out = wk > 0, out > 0
        batter = np.clip((W - 4.0 - w) * 0.09, 0, 1.4)
        face = out & (d_ > -batter - 0.01) & (w >= g_ - 1.5) & (w < W)
        body = wk & (w >= R - 6.0) & (w < W)
        para = wk & (d_ < 0.9) & (w >= W) & (w < W + 1.1)
        cap = (wk & (d_ < 1.05) | out & (d_ > -0.2)) & (w >= W + 0.8) & (w < W + 1.15)
        row = np.floor(w * 2.0)
        course = np.mod(row + np.floor(A_ / 1.3) * np.mod(row, 2), 3) == 0
        col = np.where(course, c["stone2"], c["stone"])
        col = np.where(w < g_ + 1.2 + batter * 2.5, c["plinth"], col)
        slit = (d_ < 0.9) & (np.mod(A_, 3.4) < 0.5) & (w > W - 2.6) & (w < W - 1.2)
        o = np.where(face | body | para, np.where(slit & ~(wk & (d_ >= 0.6)), c["win"], col), 0)
        o = np.where(body & (w >= W - 0.5) & (d_ >= 0.9), c["pave"], o)
        o = np.where(cap, c["coping"], o)
        rl = wk & (dr < 0.55) & (w >= W) & (w < W + 1.0) & ((np.mod(A_, 2.0) < 0.5) | (w >= W + 0.75))
        return np.where(rl, c["rail"], o).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, float(np.min(gout)) - 2.0, W + 1.2, walls))

    if rec is not None:  # the reception square, and its broad flight up to the park
        S.add(Poly(rec, R - 6.0, R, c["pave"]))
        S.add(Poly(rec.buffer(-0.2), R, R + 9.0, 0, mode="carve"))
        stair(S, *REC_STAIR, R, P, 9.0, c["pave2"])
    rondella(S, ctx, rond, court, fe, fu0, fu1, fdep, R, RT, c)
    for g in ranges:
        casemates(S, ctx, g, park, TB, c)
    if SERVICE in area:  # the service range wrapped round the Rondella's west, its roof planted, a storey lower
        casemates(S, ctx, largest(area[SERVICE][3]).difference(rond.buffer(0.3)), park, P + 1.0, c)
    for (foot, head), wide in ((NORTH_MOUTH, 4.5), (SOUTH_MOUTH, 5.0)):  # stairs between walls of white concrete
        zf = ctx["ground_m"](*foot)
        fr, L = stair(S, foot, head, zf, R, wide, c["pave2"])
        for sv in (-1, 1):
            for i in range(6):
                h = zf + 2.0 + (R + 7.0 - zf - 2.0) * (i + 1) / 6
                v0 = sv * wide / 2 if sv > 0 else -wide / 2 - 1.0
                S.add(Box(fr, L * i / 6 - 1.5, L * (i + 1) / 6 + 2.0, v0, v0 + 1.0, zf - 2.0, h, c["white"]))
    if vcut is not None:
        east_cut(S, ctx, vcut, vl, fort, P, W, c)
    sf = statue_frame(ctx["osm"])
    if sf is not None:
        statue_terrace(S, ctx, sf, P + STATUE, c)
    surrounds(S, ctx, fort, sf, P, c)
    band = park_surface(S, ctx, park, fort, P, c)
    fm = flagpole(S, ctx, fort, P, c)
    # the generated trees give way to the park's own: young ones in the beds, clear of the paths and the mound
    x0, y0, x1, y1 = fort.bounds
    leaves = np.array([pc(q, LEAF) for q in ("#4f7c3c", "#618f43", "#76a24a", "#56834c", "#8db552")], np.uint16)

    def crown(u, v, w):  # mottled like the generated trees, so the crowns read against the lawn
        h = np.floor(u * 2) * 73856093 + np.floor(v * 2) * 19349663 + np.floor(w * 2) * 83492791
        return leaves[np.mod(h.astype(np.int64), len(leaves))]
    for i, x in enumerate(np.arange(x0, x1, 8.0)):
        for j, y in enumerate(np.arange(y0, y1, 8.0)):
            if fort.contains(Point(x, y)):
                S.clear.append((float(x), float(y), 5.0))
            k = (i * 7 + j * 13) % 11
            x_, y_ = x + 4.0 + (k - 5) * 0.5, y + 4.0 + ((k * 3) % 11 - 5) * 0.5
            p = Point(x_, y_)
            if not park.contains(p) or fort.exterior.distance(p) < WALK_W + 3.0 or (band is not None and band.distance(p) < 1.6):
                continue
            if fm is not None and (fm.uv(x_, y_)[0] / 19.0) ** 2 + (fm.uv(x_, y_)[1] / 11.0) ** 2 < 1:
                continue
            h = 4.5 + k % 3
            S.add(Lathe(Frame(x_, y_, P, 0), -0.5, h - 1.6, cyl(0.2), ctx["C"]["trunk"]))
            S.add(Ellipsoid(Frame(x_, y_, P + h - 1.3), 1.5 + 0.1 * (k % 4), 1.5, 1.4, crown))
    ctx["note"](f"    Citadella: park {PARK_ASL:.1f} m asl, square {REC:+.1f}, walks {WALK:+.1f}, Rondella {RONDELLA:+.1f}")


def rondella(S, ctx, rond, court, fe, fu0, fu1, fdep, R, RT, c):
    """the round bastion: casemates round a court, the outer wall battered at the foot with two rows of embrasures, a
    parapet round the roof terrace; the court's water mirror; between the arms, on the square, the glass foyer with
    white concrete on the arms' ends, and the glass bridge across at the terrace's level."""
    x0f, y0f, X, Y = grid_of(rond, 3.0)
    dr = dist_in(rond, X, Y)
    dc = dist_in(court, X, Y)
    U = (X - fe.ox) * fe.ca + (Y - fe.oy) * fe.sa
    V = -(X - fe.ox) * fe.sa + (Y - fe.oy) * fe.ca
    neck = (V >= -0.3) & (V < fdep) & (dr > -0.3)
    foyer = neck & (U > fu0 + 1.0) & (U < fu1 - 1.0)
    gout = (ndimage.map_coordinates(ctx["G"], [Y.ravel() - 0.5, X.ravel() - 0.5], order=1, mode="nearest")
            .reshape(X.shape) - ctx["BASE"]).astype(np.float32)
    cx, cy = np.mean(np.array(court.exterior.coords), axis=0)
    arc = (np.arctan2(Y - cy, X - cx) * 30.0).astype(np.float32)  # metres round the drum, near enough
    side = (U < fu0 + 0.5) | (U > fu1 - 0.5)
    fields = dict(dr=dr, dc=dc, neck=neck.astype(np.uint8), foyer=foyer.astype(np.uint8), g=gout, arc=arc,
                  side=side.astype(np.uint8), clad=(neck & ((V < 1.2) | ((U > fu0 - 1.0) & (U < fu1 + 1.0)))).astype(np.uint8))

    def body(f, w):
        dr_, dc_, ar, g_ = f["dr"][None], f["dc"][None], f["arc"][None], f["g"][None]
        nk, fy, sd, cl = f["neck"][None] > 0, f["foyer"][None] > 0, f["side"][None] > 0, f["clad"][None] > 0
        batter = np.clip((R + 1.0 - w) * 0.16, 0, 1.6)
        top = np.where(nk, RT - 0.3, RT)
        solid = (dr_ > -batter) & (dc_ < 0) & ~fy & (w >= np.minimum(g_, R) - 2.0) & (w < top)
        para = (dr_ > 0) & (dr_ < 0.9) & (w >= RT) & (w < RT + 1.1) & ~nk
        ipara = (dc_ > -0.9) & (dc_ <= 0) & (w >= RT) & (w < RT + 1.0) & sd
        row = np.floor(w * 2)
        col = np.where(np.mod(row + np.floor(ar / 1.4) * np.mod(row, 2), 3) == 0, c["stone2"], c["stone"])
        col = np.where((w < R + 1.0) & (dr_ < 2.0), c["plinth"], col)
        emb = (dr_ < 1.2) & (np.mod(ar, 8.0) < 1.1) & (((w > R + 1.6) & (w < R + 2.8)) | ((w > R + 5.4) & (w < R + 6.6)))
        cwin = (dc_ > -1.2) & (np.mod(ar, 4.2) < 1.3) & (((w > R + 0.4) & (w < R + 2.8)) | ((w > R + 3.8) & (w < R + 6.2)))
        o = np.where(solid | para | ipara, np.where((emb | cwin) & ~nk, c["win"], col), 0)
        # the terrace: planted over brown mulch along the parapet (as on the ranges), paved round the court
        o = np.where(solid & (w >= top - 0.5) & (dr_ > 0) & ~nk, np.where((dr_ > 1.0) & (dr_ < 8.5), c["roof"], c["pave"]), o)
        o = np.where((para | ipara) & (w >= RT + 0.75), c["coping"], o)
        o = np.where(solid & cl, c["white"], o)
        return o.astype(np.uint16)
    S.add(Field(x0f, y0f, fields, float(np.min(gout)) - 2.5, RT + 1.2, body))
    shrubs(S, rond.buffer(-2.0).difference(rond.buffer(-7.5)).difference(rect_poly(fe, -5, 60, -5, fdep + 2)), RT, c["shrub"], 14.0)
    # the court: carved down to its paving round the water mirror
    S.add(Poly(court.buffer(0.2), R - 0.6, RT + 2.0, 0, mode="carve"))
    S.add(Poly(court, R - 4.0, R - 0.6, c["pave"]))
    pool = court.buffer(-3.5, join_style=2)
    if not pool.is_empty:
        S.add(Poly(pool, R - 1.0, R - 0.65, c["water"]))
    # the foyer: a glass box 8 m tall with mullions every 2.4 m, glass on the roof too; the glass bridge over it
    um, w2 = (fu0 + fu1) / 2, (fu1 - fu0) / 2 - 1.0
    ff = fe.at(um, 0, 0)
    S.add(Box(ff, -w2, w2, 0.3, fdep, R, R + 8.0, 0, mode="carve"))
    S.add(Box(ff, -w2, w2, 0.3, fdep, R - 4.0, R, c["pave"]))

    def gcol(u, v, w):
        edge = (np.abs(u) > w2 - 0.5) | (v < 0.8) | (v > fdep - 0.5) | (w > R + 7.5)
        m = (np.mod(u + w2, 2.4) < 0.3) | (np.mod(w - R, 4.0) < 0.25)
        return np.where(edge, np.where(m, c["mull"], c["glass"]), 0).astype(np.uint16)
    S.add(Box(ff, -w2, w2, 0.3, fdep, R, R + 8.0, gcol))
    S.add(Box(ff, -w2 - 1.0, w2 + 1.0, 1.0, 4.0, RT - 0.4, RT, c["glass"]))
    for v0 in (1.0, 3.5):
        S.add(Box(ff, -w2 - 1.0, w2 + 1.0, v0, v0 + 0.5, RT, RT + 1.1, c["glass"]))


def casemates(S, ctx, g, park, TB, c):
    """a range of casemates: from the square or the promenade below up to a flat roof planted over brown mulch behind a
    low parapet; towards the park one storey of arched doors and windows in stone surrounds, outside up to three."""
    segs = ring_segments(g, 1.0)
    zb = min(ctx["ground_m"](*((a + b) / 2 + n * 3.0)) for a, b, n in segs) - 1.5
    S.add(Poly(g, zb, TB, c["stone"]))
    S.add(Poly(g.buffer(-0.6, join_style=2), TB - 0.4, TB + 0.1, c["roof"]))
    S.add(Poly(g.difference(g.buffer(-0.5, join_style=2)), TB, TB + 0.75, c["stone2"]))
    S.add(Poly(g.difference(g.buffer(-0.55, join_style=2)), TB + 0.5, TB + 0.8, c["coping"]))
    for a, b, n in segs:
        if np.hypot(*(b - a)) < 4.0:
            continue
        mid = (a + b) / 2
        on_park = park.distance(Point(*(mid + n * 1.5))) < 1.0
        L = float(np.hypot(*(b - a)))
        fr = Frame(a[0], a[1], 0.0, math.atan2(b[1] - a[1], b[0] - a[0]))
        if (np.array([-fr.sa, fr.ca]) @ n) > 0:  # +v into the range
            fr = Frame(b[0], b[1], 0.0, fr.ang + math.pi)
        g0 = ctx["ground_m"](*(mid + n * 2.0))
        rows = [(g0 + 0.2, g0 + 2.6)] if on_park else [(z, z + 1.6) for z in np.arange(g0 + 1.2, TB - 1.5, 3.4)]
        k = max(int((L - 1.5) // 4.6), 1)
        for i in range(k):
            t_ = (L - (k - 1) * 4.6) / 2 + i * 4.6
            for z0, z1 in rows:
                S.add(Box(fr, t_ - 0.75, t_ + 0.75, -0.3, 0.4, z0, z1, c["win"], mode="paint", targets=[c["stone"]]))
                S.add(Box(fr, t_ - 1.05, t_ + 1.05, -0.3, 0.3, z1, z1 + 0.35, c["stone2"], mode="paint", targets=[c["stone"]]))
    shrubs(S, g.buffer(-2.0), TB, c["shrub"])


def shrubs(S, g, z, col, every=10.0):
    """low shrubs scattered over a planted roof, one per `every` m²."""
    if g.is_empty:
        return
    rng = np.random.default_rng(int(g.area))
    x0, y0, x1, y1 = g.bounds
    for _ in range(int(g.area / every)):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if g.contains(Point(x, y)):
            S.add(Lathe(Frame(x, y, z, 0), 0.0, 0.9, lambda t: 0.75 * np.sqrt(np.clip(1 - t, 0, 1)) + 0.15, col))


def statue_terrace(S, ctx, sf, zt, c):
    """the Liberty Statue's terrace, repaved in pale limestone round its beds, stone retaining walls where the hill
    falls away from it (not at the back, where the cut comes down), clear of trees."""
    C = ctx["C"]
    rect = rect_poly(sf, *TERRACE)
    walls_ = [ln for oid, t, ln in ctx["osm"].lines if t.get("barrier") == "retaining_wall" and ln.distance(Point(sf.ox, sf.oy)) < 16]
    terr = rect.union(shapely.MultiPoint([q for ln in walls_ for q in ln.coords]).convex_hull.buffer(1.5)) if walls_ else rect
    beds = [g for oid, k, t, g in ctx["osm"].areas if t.get("landuse") in ("grass", "flowerbed") and g.area < 400 and g.intersects(rect)]
    if beds:
        terr = terr.difference(shapely.unary_union(beds))
    S.add(Poly(terr, zt - 1.5, zt + 0.6, c["pave"], mode="paint", targets=[C["grass"], C["grass2"], C["garden"],
          C["paving"], C["paving2"], C["gravel"], C["dirt"], C["steps"], C["sett"], C["asphalt"]]))
    u0, u1, v0, v1 = TERRACE
    rim = rect.difference(rect.buffer(-0.6, join_style=2)).difference(rect_poly(sf, u0 - 1, u0 + 3, v0 - 1, v1 + 1))
    S.add(Poly(rim, zt - 6.0, zt - 0.01, c["stone2"]))
    for u in np.arange(u0, u1 + 0.1, 5.0):
        for v in np.arange(v0, v1 + 0.1, 5.0):
            S.clear.append((*map(float, sf.xy(u, v)), 4.0))


def surrounds(S, ctx, fort, sf, P, c):
    """round the walls: the satellite saw the building site, which the pipeline left as its default pavement. Grass
    at the walls' foot and along the promenades; on the slope towards the Danube, beyond them, young trees again."""
    C = ctx["C"]
    wb = {"footway": 2.2, "path": 2.0, "steps": 2.2, "pedestrian": 4.0, "service": 3.6, "track": 3.0}
    ways = [ln.buffer(wb.get(t["highway"], 5.5)) for oid, t, ln in ctx["osm"].lines
            if t.get("highway") and ln.distance(fort) < 40]
    band = fort.buffer(32).difference(fort.buffer(0.4))
    if ways:
        band = band.difference(shapely.unary_union(ways))
    if sf is not None:
        band = band.difference(rect_poly(sf, *TERRACE))
    S.add(Poly(band, P - 22.0, P + 1.0, C["grass"], mode="paint", targets=[C["paving2"]]))
    a = rect_of(fort)[4]
    n = np.array([math.sin(a), -math.cos(a)])
    n = n if n[0] > 0 else -n  # the side towards the Danube
    cx, cy = fort.centroid.coords[0]
    far = band.difference(fort.buffer(9.0))
    if ways:
        far = far.difference(shapely.unary_union(ways).buffer(3.3))
    leaves = np.array([ctx["P"](q, LEAF) for q in ("#4f7c3c", "#618f43", "#56834c", "#6b9446")], np.uint16)

    def crown(u, v, w):
        h = np.floor(u * 2) * 73856093 + np.floor(v * 2) * 19349663 + np.floor(w * 2) * 83492791
        return leaves[np.mod(h.astype(np.int64), len(leaves))]
    rng = np.random.default_rng(11)
    x0, y0, x1, y1 = far.bounds
    for x in np.arange(x0, x1, 7.0):
        for y in np.arange(y0, y1, 7.0):
            x_, y_ = x + rng.uniform(-2.5, 2.5), y + rng.uniform(-2.5, 2.5)
            if rng.random() > 0.7 or (x_ - cx) * n[0] + (y_ - cy) * n[1] < 0 or not far.contains(Point(x_, y_)):
                continue
            zg, h, r = ctx["ground_m"](x_, y_), rng.uniform(6.5, 10.0), rng.uniform(2.2, 3.0)
            S.add(Lathe(Frame(x_, y_, zg, 0), -0.5, h - r, cyl(0.25), C["trunk"]))
            S.add(Ellipsoid(Frame(x_, y_, zg + h - r * 0.9), r, r, r * 0.95, crown))


def east_cut(S, ctx, vcut, vl, fort, P, W, c):
    """the cut through the east bastion behind the Liberty Statue: a broad stair from the park down to the statue's
    terrace between two walls of white concrete flaring out towards the Danube, rising to points at their outer ends."""
    mid = np.array(fort.centroid.coords[0])
    ends = [sorted((np.array(ln.coords[0]), np.array(ln.coords[-1])), key=lambda q: float(np.hypot(*(q - mid))))
            for ln in vl.values()]
    inner, outer = np.mean([e[0] for e in ends], axis=0), np.mean([e[1] for e in ends], axis=0)
    ax = (outer - inner) / np.hypot(*(outer - inner))
    zs = ctx["ground_m"](*(outer + ax * 4.0))
    S.add(Poly(vcut.buffer(0.2), min(zs, P) - 0.01, W + 3.0, 0, mode="carve"))
    a, b = outer + ax * 1.5, inner - ax * 0.5
    L = float(np.hypot(*(b - a)))
    fr = Frame(a[0], a[1], 0.0, math.atan2(b[1] - a[1], b[0] - a[0]))
    n = max(int(round(abs(P - zs) / 0.16)), 1)
    for i in range(n):  # the steps as wide as the cut
        strip = vcut.buffer(0.2).intersection(rect_poly(fr, L * i / n - (2.0 if i == 0 else 0), L * (i + 1) / n + 0.05, -12, 12))
        if not strip.is_empty:
            S.add(Poly(strip, min(zs, P) - 4.0, zs + (P - zs) * (i + 1) / n, c["pave2"]))
    for e0, e1 in ends:
        dd = e1 - e0
        Ls = float(np.hypot(*dd))
        fw = Frame(e0[0], e0[1], 0.0, math.atan2(dd[1], dd[0]))
        for i in range(8):
            top = W + 1.1 + 2.4 * (i + 0.5) / 8
            S.add(Box(fw, Ls * i / 8 - 0.3, Ls * (i + 1) / 8 + 0.3, -0.6, 0.6, zs - 2.0, top, c["white"]))


def park_surface(S, ctx, park, fort, P, c):
    """the park at its level: broad paths of pale limestone along OSM's ways, the rest beds of mulch and lawn."""
    C = ctx["C"]
    tgt = [C["grass"], C["grass2"], C["garden"], C["paving"], C["paving2"], C["gravel"], C["dirt"], C["steps"]]
    S.add(Poly(park, P - 0.6, P + 0.01, lambda u, v, w: np.where(
        np.sin(u * 0.45 + np.cos(v * 0.35) * 2.0) + np.cos(v * 0.55 - u * 0.2) > 0.8, c["mulch"], c["lawn"]).astype(np.uint16),
        mode="paint", targets=tgt))
    ways = [ln for oid, t, ln in ctx["osm"].lines if t.get("highway") in ("footway", "steps", "path")
            and ln.intersects(fort) and t.get("level") in ("2", None)]
    if not ways:
        return None
    band = shapely.unary_union([ln.buffer(2.4, cap_style="flat") for ln in ways]).intersection(park)
    S.add(Poly(band, P - 0.6, P + 0.01, c["pave"], mode="paint", targets=tgt + [c["lawn"], c["mulch"]]))
    return band


def flagpole(S, ctx, fort, P, c):
    """Hungary's largest national flag (72 m², 6 x 12 m) on a 36.3 m steel mast (7.5 t, 2022), on its grassy mound
    ringed by a bed, pale dolomite stones at its foot."""
    node = next((p for oid, t, p in ctx["osm"].nodes if oid == FLAGPOLE), None)
    if node is None:
        return None
    x, y = node.x, node.y
    fm = Frame(x, y, P, rect_of(fort)[4])  # the mound lies along the fortress
    S.add(Mound(fm, 17.0, 9.5, 0.0, 0.5, c["mulch"]))
    S.add(Mound(fm, 13.5, 7.0, 0.0, 1.6, c["lawn"]))
    foot, H = 1.5, 36.3
    S.add(Lathe(Frame(x, y, P, 0), foot - 0.6, foot + 0.4, cyl(1.7), ctx["P"]("#cfc8b6")))
    steel = ctx["P"]("#dfe2e2", METAL)
    S.add(Lathe(Frame(x, y, P, 0), foot, foot + 12.0, cone(0.5, 0.36), steel))
    # the taper drops under half a voxel higher up, where a lathe draws nothing: a voxel line keeps the mast whole
    S.line(Frame(x, y, P, 0), (0, 0, foot), (0, 0, foot + H), steel)
    S.add(Lathe(Frame(x, y, P, 0), foot + H - 0.1, foot + H + 0.35, cyl(0.36), steel))
    fly = Frame(x, y, P, math.pi / 2 - 0.25)
    top, FL, FH = foot + H - 0.5, 12.0, 6.0
    flag(S, ctx, fly.at(-0.3, 0, 0), top, FL + 0.3, FH)  # flag() starts 0.3 m out along its frame
    for i, w in enumerate(np.arange(top - FH + 0.25, top, 0.5)):  # the hoist, from the mast's own voxels into the cloth
        S.line(fly, (0, 0, w), (0.8, 0, w), ctx["P"](("#3e7b4c", "#f2f1ec", "#cd2a3e")[min(int(i * 0.5 / (FH / 3)), 2)]))
    return fm


BUILDERS = [("Citadella", citadella)]
