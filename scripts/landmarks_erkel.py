"""The Erkel Theatre (Erkel Színház) on II. János Pál pápa tér: the Népopera of Marcell Komor, Dezső Jakab and Géza
Márkus (1911), the Opera's second house from 1951, its front rebuilt in the 1950s, renovated in 2013. Built on the
circle OSM's outline draws for its convex front (docs/landmarks.md has the sources).
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from landmarks import WINDOW, Box, Field, Frame, Lathe, Prim, cyl, ring_segments, seg_frame
from landmarks_city import grid_of, windows
from landmarks_more import frame_fields, largest, rect_poly
from style import GLASS, METAL, ROOF

ERKEL = 26829510
NAMES = ["Erkel Theatre"]
# The outline is not dropped: without it the ground model reads the surface model's roofs there as open ground and
# lifts the square round it by up to 1 m. erkel() clears the generic building drawn from it instead.
DROP = set()

FONT = {"E": ("####", "#...", "###.", "#...", "####"), "R": ("###.", "#..#", "###.", "#.#.", "#..#"),
        "K": ("#..#", "#.#.", "##..", "#.#.", "#..#"), "L": ("#...", "#...", "#...", "#...", "####")}


class Ring(Prim):
    """an annular sector about the frame's w axis: r0 <= r < r1, a0 <= a < a1 (radians from +v towards +u),
    w0 <= w < w1. The Erkel's curved front and everything on it."""

    def __init__(self, fr, r0, r1, a0, a1, w0, w1, col, **kw):
        self.p = (r0, r1, a0, a1, w0, w1)
        t = np.linspace(a0, a1, 33)
        us = np.concatenate([r0 * np.sin(t), r1 * np.sin(t)])
        vs = np.concatenate([r0 * np.cos(t), r1 * np.cos(t)])
        super().__init__(fr, col, (us.min(), us.max(), vs.min(), vs.max(), w0, w1), **kw)

    def inside(self, u, v, w, x, y):
        r0, r1, a0, a1, w0, w1 = self.p
        r, a = np.hypot(u, v), np.arctan2(u, v)
        return (r >= r0) & (r < r1) & (a >= a0) & (a < a1) & (w >= w0) & (w < w1)


def front_arc(g, tol=0.35):
    """the longest run of the outline's corners on one circle (radius 30-200 m, centre inside the building): its centre
    (x, y), radius, the direction from the centre to the arc's middle and its half-angle."""
    g = largest(g)
    c = np.array(g.exterior.coords)[:-1]
    n, best = len(c), None
    for i in range(n):
        for k in range(4, n):
            p = c[[(i + j) % n for j in range(k)]]
            sol = np.linalg.lstsq(np.c_[2 * p, np.ones(k)], (p ** 2).sum(1), rcond=None)[0]
            cen = sol[:2]
            R = math.sqrt(max(sol[2] + cen @ cen, 0.0))
            if not 30 < R < 200 or np.abs(np.hypot(*(p - cen).T) - R).max() > tol:
                break
            L = float(np.hypot(*np.diff(p, axis=0).T).sum())
            if (best is None or L > best[0]) and g.contains(Point(*cen)):
                a0, a1 = (math.atan2(q[1] - cen[1], q[0] - cen[0]) for q in (p[0], p[-1]))
                da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                best = (L, float(cen[0]), float(cen[1]), R, a0 + da / 2, abs(da) / 2)
    return None if best is None else best[1:]


def areal(geom):
    """the polygons of a shapely result (intersections and differences leave slivers and lines)."""
    return MultiPolygon([p for p in shapely.get_parts(geom) if p.geom_type == "Polygon" and p.area > 1.0])


def plain_front_windows(S, poly, b0, rows, targets, win, front, every=4.5, half=0.45, min_len=4.0):
    """windows() on every wall of poly except those facing `front` (a grid direction)."""
    for a, b, n in ring_segments(poly, min_len):
        if n @ front > 0.5:
            continue
        fw = seg_frame(a, b, n, 0)
        Ls = float(np.hypot(*(b - a)))
        k = max(int((Ls - 2.0) // every), 1)
        for i in range(k):
            fi = fw.at((Ls - (k - 1) * every) / 2 + i * every, 0, 0, math.pi / 2)
            for w0, w1 in rows:
                S.add(Box(fi, -0.3, 0.5, -half, half, b0 + w0, b0 + w1, win, mode="paint", targets=targets))


def front_view(osm):
    """the middle of the curved front and its outward direction (grid), for the viewer's view."""
    g = next((g_ for oid, k, t, g_ in osm.areas if oid == ERKEL), None)
    fa = front_arc(g) if g is not None else None
    if fa is None:
        return None
    cx, cy, R, am, half = fa
    n = (math.cos(am), math.sin(am))
    return (cx + R * n[0], cy + R * n[1]), n


def erkel(S, ctx, plan):
    """The convex front in pale travertine: a thin white canopy over a ground floor of glass doors between piers, seven
    tall glazed bays with blue frames, the blue letters ERKEL, seven recessed window strips under a plain parapet;
    lower stepped blocks at both ends, travertine at the front and white render behind. The fan-shaped auditorium under
    a pale metal vault rounded off towards the stage, a flat roof between it and the front, a one-storey ring of rooms
    round its narrow end; the white stage house with a glazed top storey, rounded corners, a half-round stair tower on
    its west side and a box on its roof; the service wing behind (sizes from the photos and the aerial)."""
    P, area = ctx["P"], ctx["area"]
    g = largest(area[ERKEL][3])
    fa = front_arc(g)
    if fa is None:
        raise KeyError(ERKEL)
    cx, cy, R, am, half = fa
    fr0 = Frame(cx, cy, 0.0, am - math.pi / 2)  # +v out through the front's middle, +u right seen from the square
    b0 = float(np.median([ctx["ground_m"](*fr0.xy((R + 6) * math.sin(a), (R + 6) * math.cos(a)))
                          for a in np.linspace(-half, half, 9)]))
    fr = Frame(cx, cy, b0, fr0.ang)

    trav, trav2, coping = P("#e6dfcf"), P("#ded6c5"), P("#bdb7ab")
    white, trim, plinth = P("#eeede8"), P("#f6f6f2"), P("#d4d2cb")
    canopy, soffit = P("#f4f4f1"), P("#d2d2cd")
    glass, mull, letter_c = P("#3b6494", WINDOW), P("#4a86c9", METAL), P("#5a98dc", METAL)
    door_g, door_f = P("#4b5966", WINDOW), P("#c4c9cc", METAL)
    win, clear = P("#2f3540", WINDOW), P("#b4c4ca", GLASS)
    roof_f, roof_s, roof_r, roof_l = P("#6a706c", ROOF), P("#626a66", ROOF), P("#6d7670", ROOF), P("#5f6466", ROOF)
    vault, vault2, gravel, box_c = P("#c4c9cb", ROOF), P("#a9b0b3", ROOF), P("#a89c86", ROOF), P("#8c9190")

    # heights above the pavement, from the photos: the front, its end blocks, the auditorium's eaves and ridge, the
    # stage house, the wing behind it, the stair blocks by the stage, the ring round the auditorium
    H_FRONT, H_STONE, H_WHITE = 20.5, 14.6, 11.0
    E_HALL, R_HALL, H_FOY = 17.0, 23.0, 17.5
    H_STAGE, H_REAR, H_CORNER, H_LOW = 26.5, 13.0, 9.0, 5.5
    R_IN = R - 12.5                     # the front range is 12.5 m deep
    V_SF, V_SB = 13.5, -9.5            # the stage house, between the auditorium and the service wing
    V_STONE = 52.5                      # the end blocks are travertine this far back
    HV0, HW0, HE = 29.0, 16.0, 14.5     # the auditorium: half-width 16 m where its rounded end begins, 14.5 m deep
    HV1, HW1 = R_IN - 5.0, 21.5         # widening to 43 m, 5 m behind the front range (a flat roof between)

    def hall_hw(v):
        return HW0 + (np.minimum(np.asarray(v, float), HV1) - HV0) * (HW1 - HW0) / (HV1 - HV0)

    def poly_uv(pts):
        return Polygon([fr.xy(u, v) for u, v in pts])

    t = np.linspace(-half, half, 49)
    front_p = poly_uv([(R * math.sin(a), R * math.cos(a)) for a in t] +
                      [(R_IN * math.sin(a), R_IN * math.cos(a)) for a in t[::-1]])
    vs = np.linspace(R_IN + 3, HV0, 16)
    hall_p = poly_uv([(float(hall_hw(v)), v) for v in vs] +
                     [(HW0 * math.cos(a), HV0 - HE * math.sin(a)) for a in np.linspace(0, math.pi, 25)] +
                     [(-float(hall_hw(v)), v) for v in vs[::-1]]).intersection(g)
    eu, ev = fr.uv(*np.array(g.exterior.coords).T)
    ur0, ur1 = float(eu[ev < 0].min()), float(eu[ev < 0].max())  # the stage block's sides
    stage_p = largest(g.intersection(rect_poly(fr, ur0 - 0.5, ur1 + 0.5, V_SB, V_SF)).buffer(-2.5).buffer(2.5))
    rear_p = areal(g.intersection(rect_poly(fr, ur0 - 1, ur1 + 1, -200, V_SB + 3)).difference(stage_p))
    corner_p = g.intersection(rect_poly(fr, -200, -13, V_SF - 3, 22).union(rect_poly(fr, 13, 200, V_SF - 3, 22)))
    corner_p = areal(corner_p.difference(stage_p).difference(hall_p))
    low_p = areal(g.intersection(rect_poly(fr, -200, 200, V_SF - 3, 35)).difference(stage_p).difference(hall_p)
                  .difference(corner_p))
    side_p = g.difference(front_p).difference(hall_p).difference(stage_p).difference(rear_p).difference(corner_p) \
        .difference(low_p)
    stone_p = areal(side_p.intersection(rect_poly(fr, -200, 200, V_STONE, 200)))
    white_p = areal(side_p.difference(stone_p))

    # first clear the generic building voxelize.py drew from the outline (its walls reach 1 m outside it), down to the
    # ground round it and to under the pavement inside it
    x0f, y0f, X, Y = grid_of(g.union(front_p), 1.5)
    gz = np.full(X.shape, np.inf, np.float32)
    ring = shapely.contains_xy(g.buffer(1.2), X, Y) & ~shapely.contains_xy(g, X, Y)
    gz[ring] = [ctx["ground_m"](x, y) for x, y in zip(X[ring], Y[ring])]
    gz[shapely.contains_xy(g, X, Y)] = b0 - 3.0
    feat = ctx["feats"].get(str(ERKEL)) or {}
    S.add(Field(x0f, y0f, dict(gz=gz), b0 - 3.0, b0 + float(feat.get("H", 30.0)) + 3.0,
                lambda f, wa: (wa > f["gz"][None]).astype(np.uint16), mode="carve"))

    # the masses: one Field over the outline, a zone and a roof height per 0.5 m cell
    U, V = frame_fields(fr, X, Y)
    r, phi = np.hypot(U, V), np.arctan2(U, V)
    zone = np.zeros(X.shape, np.uint8)
    zone[(r >= R_IN) & (r < R) & (np.abs(phi) <= half)] = 1
    nominal = np.zeros(X.shape, np.float32)
    for zid, pg, H in ((5, stage_p, H_STAGE), (6, rear_p, H_REAR), (4, hall_p, E_HALL), (7, corner_p, H_CORNER),
                       (8, low_p, H_LOW), (2, stone_p, H_STONE), (3, g, H_WHITE)):
        m = shapely.contains_xy(pg, X, Y) & (zone == 0)
        zone[m] = zid
        nominal[m] = H
    nominal[zone == 1] = H_FRONT
    foyer = (zone == 4) & (V > HV1)
    zone[foyer], nominal[foyer] = 9, H_FOY
    # a parapet wherever a flat roof ends: at the outline or above a lower neighbour
    pad = np.pad(np.where(zone > 0, nominal, 0), 1)
    lower = np.min([pad[1 + dy:pad.shape[0] - 1 + dy, 1 + dx:pad.shape[1] - 1 + dx]
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)], axis=0) < nominal - 0.5
    flat = (zone > 0) & (zone != 4)
    par = flat & lower
    top = np.where(par, nominal, nominal - 0.8).astype(np.float32)
    hall = zone == 4
    rho = np.where(V >= HV0, np.abs(U) / np.maximum(hall_hw(V), 1.0),
                   np.sqrt((U / HW0) ** 2 + (np.clip(HV0 - V, 0, None) / HE) ** 2))
    vz = E_HALL + (R_HALL - E_HALL) * np.sqrt(np.clip(1 - rho ** 2, 0, 1))
    top[hall] = vz[hall]
    gy, gx = np.gradient(np.where(hall, vz, E_HALL))
    skin = np.where(hall, np.clip(0.5 + 2.0 * np.hypot(gx, gy), 0.5, 2.5), 0.5).astype(np.float32)
    fields = dict(zone=zone, top=top, par=par.astype(np.uint8), skin=skin, U=U, V=V)
    roofs = np.array([0, roof_f, roof_s, roof_s, vault, gravel, roof_r, roof_l, roof_l, roof_f], np.uint16)

    def fn(f, wa):
        z, tp, pr, sk, U_, V_ = (f[k][None] for k in ("zone", "top", "par", "skin", "U", "V"))
        h = wa - b0
        stone = (z == 1) | (z == 2)
        wall = np.where(stone, np.where(np.mod(h, 1.5) < 0.5, trav2, trav), np.where(h < 0.6, plinth, white))
        wall = np.where((z == 4) & (h >= E_HALL - 0.7), trim, wall)
        rc = roofs[z]
        rc = np.where((z == 4) & ((np.abs(U_) < 0.6) | (np.mod(V_, 10.5) < 0.5)), vault2, rc)
        cap = np.where(pr > 0, np.where(stone, coping, trim), rc)
        col = np.where(h >= tp - sk, cap, wall)
        return np.where((z > 0) & (h >= -3.0) & (h < tp), col, 0).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 3.0, b0 + R_HALL + 4.0, fn))

    # the front: seven bays along the arc, 5.7 m apart, symmetric about the axis
    BAY = 5.7
    sk_ = [(k - 3) * BAY for k in range(7)]

    def arc(s, w):  # angle of an arc length s on the front, and its half-width w
        return (s - w) / R, (s + w) / R

    def s_of(u, v):
        return R * np.arctan2(u, v)

    def doors(s_c):
        def f(u, v, w):
            s = s_of(u, v)
            m = (np.mod(s - s_c + 1.05, 2.1) < 0.3) | ((w > 3.2) & (w < 3.7)) | (w > 4.6)
            return np.where(m, door_f, door_g).astype(np.uint16)
        return f

    def bay(s_c, w0):
        def f(u, v, w):
            m = (np.abs(s_of(u, v) - s_c) < 0.26) | (np.mod(w - w0, 2.0) < 0.5)
            return np.where(m, mull, glass).astype(np.uint16)
        return f

    def strip(s_c):
        def f(u, v, w):
            return np.where(np.mod(s_of(u, v) - s_c + 2.0, 1.33) < 0.5, mull, glass).astype(np.uint16)
        return f

    for s_c in sk_:  # (glass and banners 0.75 m thick: a thinner shell at 21 degrees to the grid misses voxels)
        a0, a1 = arc(s_c, 2.1)  # the ground floor: glass doors set back between the piers, up to the canopy
        S.add(Ring(fr, R - 1.2, R + 0.5, a0, a1, 0.0, 5.0, 0, mode="carve"))
        S.add(Ring(fr, R - 1.95, R - 1.2, a0, a1, -0.5, 5.0, doors(s_c)))
        a0, a1 = arc(s_c, 1.1)  # the tall glazed bays
        S.add(Ring(fr, R - 0.5, R + 0.3, a0, a1, 6.4, 14.5, 0, mode="carve"))
        S.add(Ring(fr, R - 1.25, R - 0.5, a0, a1, 6.4, 14.5, bay(s_c, 6.4)))
        a0, a1 = arc(s_c, 2.1)  # the window strips under the parapet
        S.add(Ring(fr, R - 0.5, R + 0.3, a0, a1, 18.0, 19.5, 0, mode="carve"))
        S.add(Ring(fr, R - 1.25, R - 0.5, a0, a1, 18.0, 19.5, strip(s_c)))
    for sg in (-1, 1):  # a single door in each end wall
        a0, a1 = arc(sg * (R * half - 1.7), 0.8)
        S.add(Ring(fr, R - 0.5, R + 0.5, a0, a1, 0.0, 2.8, 0, mode="carve"))
        S.add(Ring(fr, R - 1.25, R - 0.5, a0, a1, -0.5, 2.8, door_f))
    # the opera's banners hang on the piers between the bays (their pictures change with the season)
    for k, c in enumerate(("#6a5aa8", "#44503f", "#4b3b30", "#c23a33", "#a9b9cc", "#5a2a2e")):
        a0, a1 = arc((sk_[k] + sk_[k + 1]) / 2, 1.4)
        S.add(Ring(fr, R - 0.25, R + 0.5, a0, a1, 7.0, 14.4, P(c)))
    # the canopy: along the whole front and 3 m on past its ends, in front of the end blocks
    S.add(Ring(fr, R - 4.0, R + 4.0, -half - 3.0 / R, half + 3.0 / R, 5.0, 6.4,
               lambda u, v, w: np.where(w < 5.5, soffit, canopy).astype(np.uint16), mode="under"))
    # ERKEL over the five middle bays: blue letters on the stone, a 0.55 x 0.5 m pixel font, rows on the voxel grid
    w_top = math.floor((b0 + 17.5) * 2) / 2 - b0
    for ch, s_c in zip("ERKEL", sk_[1:6]):
        rows = FONT[ch]
        bm = np.array([[c == "#" for c in row] for row in rows])
        nw, px = bm.shape[1], 0.55
        s0 = s_c - nw * px / 2

        def lt(u, v, w, bm=bm, s0=s0):
            i = np.floor((s_of(u, v) - s0) / px).astype(np.int64)
            j = np.floor((w_top - w) / 0.5).astype(np.int64)
            i, j = np.broadcast_arrays(i, j)
            ok = (i >= 0) & (i < bm.shape[1]) & (j >= 0) & (j < bm.shape[0])
            on = np.zeros(i.shape, bool)
            on[ok] = bm[j[ok], i[ok]]
            return np.where(on, letter_c, 0).astype(np.uint16)
        S.add(Ring(fr, R - 0.2, R + 0.55, s0 / R, (s0 + nw * px) / R, w_top - 0.5 * len(rows), w_top, lt))

    # the stage house: windows in five rows, a glazed top storey, the stair tower, the box on the roof
    walls = [white, plinth]
    windows(S, stage_p, b0, [(2.2, 3.6), (6.2, 7.6), (10.0, 11.4), (13.8, 15.2), (17.6, 19.0)], walls, win,
            every=2.7, half=0.45, min_len=5.0, arch=False)
    windows(S, stage_p, b0, [(22.2, 25.6)], walls + [trim], clear, every=1.0, half=0.38, min_len=5.0, arch=False)
    ln = LineString([fr.xy(0, -2.0), fr.xy(80, -2.0)]).intersection(g.exterior)
    if not ln.is_empty:
        ue = min(fr.uv(q.x, q.y)[0] for q in getattr(ln, "geoms", [ln]))
        ft = fr.at(ue, -2.0)
        S.add(Lathe(ft, -3.0, H_STAGE, cyl(2.6), white))
        S.add(Box(ft.at(2.3), -0.3, 0.6, -0.45, 0.45, 8.0, 24.5, win, mode="paint", targets=[white]))
    S.add(Box(fr, 0.0, 14.0, 0.0, 11.0, H_STAGE - 0.8, H_STAGE + 2.2, box_c))
    S.add(Box(fr, -0.2, 14.2, -0.2, 11.2, H_STAGE + 0.6, H_STAGE + 1.6,
              lambda u, v, w: np.where(np.mod(u + v, 1.2) < 0.8, win, box_c).astype(np.uint16), mode="paint",
              targets=[box_c]))

    # windows on the wings: four storeys behind the stage, small ones on the end blocks, barred ones round the hall
    windows(S, rear_p, b0, [(1.4, 3.0), (4.6, 6.2), (7.8, 9.4), (10.6, 12.0)], walls, win, every=3.0, half=0.5,
            min_len=5.0, arch=False)
    windows(S, corner_p, b0, [(2.0, 3.6), (5.4, 7.0)], walls, win, every=3.2, half=0.5, min_len=3.0, arch=False)
    windows(S, low_p, b0, [(2.0, 3.8)], walls, win, every=4.2, half=0.6, min_len=4.0, arch=False)
    windows(S, white_p, b0, [(2.0, 3.6), (5.4, 7.0), (8.4, 9.8)], walls, win, every=3.6, half=0.5, min_len=4.0,
            arch=False)
    plain_front_windows(S, stone_p, b0, [(7.0, 8.4), (10.6, 12.0)], [trav, trav2], win, (-fr.sa, fr.ca))
    windows(S, front_p, b0, [(16.0, 17.4)], [trav, trav2], win, every=4.0, half=0.45, min_len=6.0, arch=False)


BUILDERS = [("Erkel Theatre", erkel)]
