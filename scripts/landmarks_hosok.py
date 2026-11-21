"""Hősök tere and the City Park's edge: the Millennium Monument redone from the OSM statue nodes and the aerial (its
colonnades on one circle round the column, kings between the columns, the chariots and groups on the end piers, the
square's paving pattern), the Museum of Fine Arts, the Műcsarnok and Vajdahunyad Castle.

Shared helpers for temple fronts and classical blocks live here too (`kit` below); landmarks_buda / _pest / _misc use
them. Positions are measured on the aerial resampled onto the grid (docs/landmarks.md) and OSM's outlines.
"""
import math

import numpy as np
import shapely
from shapely.geometry import Point

import landmarks as LM
from landmarks import (TAU, WINDOW, Arch, Box, Capsule, Ellipsoid, Field, Frame, Lathe, Poly, Roof, TBox, cone, cyl,
                       dome)
from landmarks_city import base_under, dist_in, grid_of, statue
from style import CLASSIC, GLASS, METAL, ROOF

MILLENNIUM, HOSOK_TERE, HEROES_STONE = 6932527, 6411893, 152833102
FINE_ARTS, MUCSARNOK = 25216718, 25216715
VAJDA = {"knights": 496365726, "jak": 25221552, "cloister": 19016, "renaissance": 131749460, "baroque": 18446911,
         "main": 1344462345, "gothic": 1344462344, "nyebojsza": 1070741271, "apostles": 1070741272,
         "gate": 1070741274, "tompa": 1344462346, "nemet": 1344462348, "katalin": 1344462350}

NAMES = ["Museum of Fine Arts", "Műcsarnok", "Vajdahunyad Castle"]
DROP = {FINE_ARTS, MUCSARNOK, *VAJDA.values()}
# (outline id, height): outlines the ground model and the green / trees / lamps still treat as buildings
KEEP = [(FINE_ARTS, 22), (MUCSARNOK, 16), (VAJDA["baroque"], 18), (VAJDA["main"], 18), (VAJDA["knights"], 14),
        (VAJDA["jak"], 14), (VAJDA["gothic"], 14), (VAJDA["renaissance"], 14), (VAJDA["cloister"], 6)]


# ------------------------------------------------------------------------------------------------ kit
def column(S, fr, w0, w1, r, col, cap=None, base=None, n=0):
    """a classical column standing at the frame's origin: a base, a slightly tapering shaft, a capital."""
    cap = cap if cap is not None else col
    base = base if base is not None else col
    h = w1 - w0
    S.add(Lathe(fr, w0, w0 + 0.12 * h / 1.2 * 0.5, cyl(r * 1.35), base, n=4, rot=math.pi / 4))
    S.add(Lathe(fr, w0 + 0.05 * h, w1 - 0.1 * h, cone(r, r * 0.86), col, n=n))
    S.add(Lathe(fr, w1 - 0.1 * h, w1, cone(r * 0.95, r * 1.35), cap))


def row(S, fr, u, v0, v1, n, w0, w1, r, col, cap=None, base=None):
    """n columns along v from v0 to v1 at u (frame metres)."""
    for k in range(n):
        v = v0 + (v1 - v0) * k / max(n - 1, 1)
        column(S, fr.at(u, v), w0, w1, r, col, cap, base)


def temple_front(S, fr, hw, depth, n, w0, wc, col, stone, trim, roofc, steps=0.0, gable=True, r=None):
    """a portico on the frame: +u outwards, columns from w0 to wc across v in [-hw, hw], `depth` deep (the cella wall
    at u = 0), an entablature and a pediment (`gable`), steps in front."""
    r = r if r is not None else min(0.55, 0.42 * 2 * hw / max(n - 1, 1) / 2.2)
    u1 = depth
    S.add(Box(fr, -0.5, u1, -hw - 0.4, hw + 0.4, w0 - 1.5, w0, stone))
    for k in range(int(steps / 0.5)):
        S.add(Box(fr, u1, u1 + 0.45 * (int(steps / 0.5) - k), -hw + 0.6, hw - 0.6, w0 - 1.5, w0 - k * 0.5, stone))
    row(S, fr, u1 - r - 0.3, -hw + r + 0.2, hw - r - 0.2, n, w0, wc, r, col, trim)
    if depth > 4:
        for sv in (-1, 1):
            for k in range(1, max(int((depth - 2 * r) / (2 * hw / max(n - 1, 1))), 1)):
                uu = u1 - r - 0.3 - k * 2 * hw / max(n - 1, 1)
                if uu > r + 0.5:
                    column(S, fr.at(uu, sv * (hw - r - 0.2)), w0, wc, r, col, trim)
    e = 0.11 * (wc - w0) + 0.5
    S.add(Box(fr, -0.5, u1 + 0.1, -hw - 0.2, hw + 0.2, wc, wc + e, trim))
    S.add(Box(fr, -0.5, u1 + 0.35, -hw - 0.45, hw + 0.45, wc + e, wc + e + 0.45, stone))
    if gable:
        S.add(Roof(fr.at(turn=0), -0.5, u1 + 0.2, -hw - 0.3, hw + 0.3, wc + e + 0.45, 0.24 * 2 * hw, trim))
        S.add(Roof(fr, -0.5, u1 + 0.1, -hw - 0.5, hw + 0.5, wc + e + 0.9, 0.24 * 2 * hw, roofc))
        S.add(Roof(fr, u1 - 0.6, u1 + 0.05, -hw + 0.6, hw - 0.6, wc + e + 0.55, 0.22 * 2 * hw - 0.6, roofc, mode="carve"))
        S.add(Roof(fr, u1 - 0.8, u1 - 0.55, -hw + 0.6, hw - 0.6, wc + e + 0.55, 0.22 * 2 * hw - 0.6, stone))
    return wc + e + 0.45


def windows_on(S, fr, u, v0, v1, every, rows, half, col, targets, arch=True, depth=0.6):
    """windows painted into a wall whose face is at u (the frame's +u outwards): rows of (sill, head) heights."""
    n = max(int((v1 - v0) / every), 1)
    for k in range(n):
        v = v0 + (v1 - v0) * (k + 0.5) / n
        for w0, w1 in rows:
            if arch:
                S.add(Arch(fr.at(turn=0), u - depth, u + 0.3, v, half, w0, w1 - half, col, mode="paint", targets=targets))
            else:
                S.add(Box(fr, u - depth, u + 0.3, v - half, v + half, w0, w1, col, mode="paint", targets=targets))


def side(fr, k):
    """the frame turned by k quarter turns (k = 1: +u becomes the old +v)."""
    return fr.at(turn=k * math.pi / 2)


def facades(S, fr, u0, u1, v0, v1, every, rows, half, col, targets, sides=(0, 1, 2, 3), arch=True):
    """windows on the four walls of the box [u0, u1] x [v0, v1] of frame fr (sides: 0 +u, 1 +v, 2 -u, 3 -v)."""
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    c = fr.at(cu, cv)
    for k in sides:
        f = side(c, k)
        hu, hv = ((u1 - u0) / 2, (v1 - v0) / 2) if k % 2 == 0 else ((v1 - v0) / 2, (u1 - u0) / 2)
        windows_on(S, f, hu, -hv + 1.0, hv - 1.0, every, rows, half, col, targets, arch)


def massing(S, g, z0, h, wall, roof, pitch=0.0, rmax=0.0, cornice=None, base=None, lower=-2.0, roof_top=None):
    """a building on an outline of any shape: walls to z0 + h, then a hipped roof rising `pitch` m per m inwards from
    the eaves to at most `rmax` (a flat roof when 0), a cornice band under the eaves, a darker base; colours may be
    f(d, along, hw) -> ids with d the distance inside the outline, hw the height over z0. Returns the Field."""
    x0f, y0f, X, Y = grid_of(g, 1.0)
    d = dist_in(g, X, Y)
    fields = dict(d=d, a=(X + Y).astype(np.float32))

    def pick(c, d_, a_, hw):
        return c(d_, a_, hw) if callable(c) else c

    def fn(f, wa):
        d_, a_ = f["d"][None], f["a"][None]
        hw = wa - z0
        body = (d_ > 0) & (hw >= lower) & (hw < h)
        rf = np.minimum(d_ * pitch, rmax) if pitch else np.zeros_like(d_)
        top = (d_ > 0) & (hw >= h) & (hw < h + rf)
        out = np.where(body, pick(wall, d_, a_, hw), 0)
        if cornice is not None:
            out = np.where(body & (hw > h - 0.7) & (d_ < 1.2), cornice, out)
        if base is not None:
            out = np.where(body & (hw < 1.2), base, out)
        if roof_top is not None and pitch:
            out = np.where(top & (rf >= rmax - 0.01) & (hw >= h + rmax - 0.6), roof_top, np.where(top, roof, out))
        else:
            out = np.where(top, roof, out)
        return np.broadcast_to(out, np.broadcast_shapes(out.shape, hw.shape)).astype(np.uint16)
    top = h + (rmax if pitch else 0)
    return S.add(Field(x0f, y0f, fields, z0 + lower, z0 + top + 0.5, fn))


def spire(S, fr, w0, h, r, col, n=4, rot=math.pi / 4):
    S.add(Lathe(fr, w0, w0 + h, cone(r, 0.05), col, n=n, rot=rot))


def keep(ctx, oid):
    a = ctx["area"].get(oid)
    if a is None:
        raise KeyError(oid)
    return a[3]


def bronze_group(S, fr, w0, col, kind="figure", s=1.0):
    """a bronze group on a skyline: a chariot with horses, or two figures."""
    if kind == "chariot":
        for k in (-1, 1):
            for j in (0, 1):
                fh = fr.at(1.4 * s - j * 1.2 * s, k * 0.55 * s, w0)
                S.add(Ellipsoid(fh.at(0, 0, 1.45 * s), 0.95 * s, 0.32 * s, 0.42 * s, col))
                S.add(Capsule(fh, (0.75 * s, 0, 1.6 * s), (1.1 * s, 0, 2.3 * s), 0.2 * s, col))
                for du in (-0.6, 0.6):
                    S.add(Capsule(fh, (du * s, 0, 1.2 * s), (du * s + (0.35 if du > 0 and j == 0 else 0) * s, 0, 0.1), 0.1 * s, col))
        S.add(Box(fr.at(-1.6 * s, 0, w0), -0.7 * s, 0.7 * s, -0.8 * s, 0.8 * s, 0.6 * s, 1.5 * s, col))
        S.add(Lathe(fr.at(-1.6 * s, 0, 0), w0 + 1.5 * s, w0 + 3.2 * s, cone(0.35 * s, 0.22 * s), col))
        S.add(Ellipsoid(fr.at(-1.6 * s, 0, w0 + 3.45 * s), 0.18 * s, 0.18 * s, 0.22 * s, col))
        S.add(Capsule(fr.at(-1.6 * s, 0, w0), (0, 0, 3.0 * s), (0.6 * s, 0.1, 4.0 * s), 0.1 * s, col))
    else:
        for dv in (-0.6, 0.6):
            statue(S, fr.at(0, dv * s), w0, col, 1.15 * s)


# ------------------------------------------------------------------------------------------------ Heroes' Square
def heroes(S, ctx, plan):
    """the Millennium Monument (Albert Schickedanz, György Zala; 1896-1929). The two colonnades are arcs of one circle
    round the column (centre and radii fitted to OSM's outlines: 46 and 52 m), each with seven kings between the
    front columns, at the nodes OSM gives them; on the inner end piers the chariots of War and Peace, on the outer ends
    Work and Prosperity, Knowledge and Glory. The column carries Gabriel 36 m up, the seven chieftains ride on the
    plinth in front, the Heroes' Memorial Stone lies before them. The square is paved in light lines on grey granite:
    rectangles, two bands of meander along the axis."""
    P, area, osm = ctx["P"], ctx["area"], ctx["osm"]
    keep(ctx, MILLENNIUM)
    st, st2, st3 = P("#e3dccb"), P("#d2c9b4"), P("#bfb6a1")
    bronze, dark = P("#4d7564", METAL), P("#3e4a42", METAL)
    gold = P("#d4ad55", METAL)
    C = (4363.6, 2379.8)
    ang = math.radians(-2.5)
    fc = Frame(C[0], C[1], 0, ang)
    z0 = ctx["ground_m"](4370, 2380)
    R0, R1 = 46.0, 51.8  # inner and outer radius of the colonnades
    nodes = {t.get("name"): (p.x, p.y) for oid, t, p in osm.nodes
             if Point(p.x, p.y).distance(Point(*C)) < 60 and t.get("name")}

    def at_polar(r, a, w=0.0, out=True):
        x, y = fc.xy(r * math.cos(a), r * math.sin(a))
        return Frame(x, y, z0 + w, ang + a + (0 if out else math.pi))

    # the colonnades: podium, two rows of columns, entablature and attic, piers at both ends
    for sgn in (-1, 1):
        a_in, a_out = sgn * math.radians(20.6), sgn * math.radians(59.8)
        lo, hi = min(a_in, a_out), max(a_in, a_out)
        x0f, y0f, X, Y = grid_of(Point(*C).buffer(R1 + 3), 0)
        U = ((X - C[0]) * fc.ca + (Y - C[1]) * fc.sa).astype(np.float32)
        V = (-(X - C[0]) * fc.sa + (Y - C[1]) * fc.ca).astype(np.float32)
        Rr, Aa = np.hypot(U, V).astype(np.float32), np.arctan2(V, U).astype(np.float32)
        fields = dict(R=Rr, A=Aa)
        pod_hi = 1.8

        def fn(f, wa, lo=lo, hi=hi):
            R_, A_ = f["R"][None], f["A"][None]
            h = wa - z0
            inarc = (A_ >= lo) & (A_ <= hi)
            ring = inarc & (R_ >= R0 - 1.2) & (R_ <= R1 + 0.6)
            podium = ring & (h < pod_hi) & (h > -2.0)
            steps = inarc & (R_ >= R0 - 2.8) & (R_ < R0 - 1.2) & (h < (R_ - (R0 - 2.8)) / 1.6 * pod_hi) & (h > -2.0)
            ent = inarc & (R_ >= R0 - 0.5) & (R_ <= R1 + 0.3) & (h >= 11.0) & (h < 12.6)
            cor = inarc & (R_ >= R0 - 0.8) & (R_ <= R1 + 0.6) & (h >= 12.6) & (h < 13.1)
            attic = inarc & (R_ >= R0 - 0.3) & (R_ <= R1 + 0.1) & (h >= 13.1) & (h < 14.2)
            back = inarc & (R_ >= R1 - 0.6) & (R_ <= R1) & (h >= pod_hi) & (h < 2.8)  # a low wall between the back columns
            col = np.where(ent, st2, np.where(cor | attic, st, np.where(podium | back, st3, np.where(steps, st2, 0))))
            # a frieze band of darker panels on the entablature
            panel = ent & (h > 11.35) & (h < 12.2) & (np.mod(A_ * R1 / 3.0, 1.0) < 0.75) & (R_ > R1 - 0.2)
            return np.where(panel, st3, col).astype(np.uint16)
        S.add(Field(x0f, y0f, fields, z0 - 2.0, z0 + 14.3, fn))
        # columns: front row on the inner circle, back row on the outer, 8 per row; kings between the front ones
        n = 8
        for k in range(n):
            a = lo + (hi - lo) * (k + 0.5) / n
            for rr in (R0 + 0.3, R1 - 0.9):
                column(S, at_polar(rr, a, 0), pod_hi, 11.0, 0.5, st, st2, st2)
        # end piers: solid blocks with a niche, a cornice and the bronze group on top
        for a, kind in ((a_in, "chariot"), (a_out, "figure")):
            fp = at_polar((R0 + R1) / 2, a, 0)
            hu = 3.6 if kind == "chariot" else 3.2
            S.add(Box(fp, -hu - 0.6, hu + 0.6, -3.2, 3.2, -2.0, pod_hi, st3))
            S.add(Box(fp, -hu, hu, -2.8, 2.8, pod_hi, 14.6, st))
            S.add(Box(fp, -hu - 0.4, hu + 0.4, -3.2, 3.2, 12.8, 13.4, st2))
            S.add(Box(fp, -hu - 0.2, hu + 0.2, -3.0, 3.0, 14.6, 15.4, st2))
            for k in (0, 2):
                fk = side(fp, k)
                S.add(Arch(fk, hu - 0.5, hu + 0.3, 0, 1.0, pod_hi + 1.5, pod_hi + 6.5, mode="carve"))
            gl = Frame(*fp.xy(0, 0), z0 + 15.4, ang + a + sgn * math.pi / 2)
            bronze_group(S, gl, 0, bronze if kind == "chariot" else dark, kind, 1.3)
    # the fourteen rulers between the front columns, on pedestals, facing the square
    kings = ["Szent István", "Szent László", "Könyves Kálmán", "II. András", "IV. Béla", "Károly Róbert", "Nagy Lajos",
             "Hunyadi János", "I. Mátyás", "Bocskai István", "Bethlen Gábor", "Thököly Imre", "II. Rákóczi Ferenc",
             "Kossuth Lajos"]
    for name in kings:
        if name not in nodes:
            continue
        x, y = nodes[name]
        u, v = fc.uv(x, y)
        a = math.atan2(v, u)
        fk = at_polar(R0 + 1.6, a, 0, out=False)
        S.add(Box(fk, -0.9, 0.9, -0.9, 0.9, 1.8, 4.2, st2))
        S.add(Box(fk, 0.85, 0.95, -0.7, 0.7, 2.1, 3.9, dark))  # the relief under each
        statue(S, fk, 4.2, dark, 1.7)
    # Gabriel's column on its stepped base, the chieftains' plinth in front of it
    gx, gy = nodes.get("Gábriel arkangyal", (4369.0, 2378.8))
    fcol = Frame(gx, gy, z0, ang)
    S.add(Box(fcol, -2.9, 2.9, -2.9, 2.9, 6.6, 7.2, st2))
    S.add(Lathe(fcol, 7.2, 8.4, cone(1.6, 1.25), st2))
    S.add(Lathe(fcol, 8.4, 30.2, cone(1.2, 0.95), st, n=24))
    for k in range(24):  # flutes
        a = TAU * (k + 0.5) / 24
        S.add(Lathe(fcol.at(1.12 * math.cos(a), 1.12 * math.sin(a)), 9.0, 29.8, cyl(0.16), st2, mode="carve"))
    S.add(Lathe(fcol, 30.2, 32.0, cone(1.0, 1.75), bronze))
    S.add(Box(fcol, -1.9, 1.9, -1.9, 1.9, 32.0, 32.6, st2))
    S.add(Ellipsoid(fcol.at(0, 0, 33.3), 0.8, 0.8, 0.8, gold))
    S.add(Lathe(fcol, 33.9, 36.7, lambda t: 0.5 - 0.22 * t, bronze))
    S.add(Ellipsoid(fcol.at(0, 0, 37.0), 0.26, 0.26, 0.32, bronze))
    for sv in (-1, 1):  # wings
        S.add(Capsule(fcol, (-0.3, sv * 0.25, 35.6), (-0.9, sv * 1.9, 38.6), 0.28, bronze))
        S.add(Capsule(fcol, (-0.9, sv * 1.9, 38.6), (-1.2, sv * 1.4, 36.2), 0.2, bronze))
    S.add(Capsule(fcol, (0.2, 0.35, 36.0), (0.6, 0.5, 37.6), 0.14, bronze))  # the arm with the crown
    S.add(Ellipsoid(fcol.at(0.65, 0.5, 37.9), 0.22, 0.22, 0.18, gold))
    S.add(Capsule(fcol, (0.2, -0.35, 36.0), (0.5, -0.5, 38.4), 0.1, gold))  # the double cross
    S.add(Capsule(fcol, (0.5, -0.8, 37.9), (0.5, -0.2, 37.9), 0.08, gold))
    # the chieftains' plinth (OSM's 12.5 x 16 m rectangle round the column's foot): Árpád in front, three on each side
    fpl = Frame(gx - 1.2 * math.cos(ang), gy - 1.2 * math.sin(ang), z0, ang)
    S.add(Box(fpl, -6.6, 6.6, -8.0, 8.0, -1.5, 1.0, st3))
    S.add(Box(fpl, -6.0, 6.0, -7.4, 7.4, 1.0, 3.6, st))
    S.add(Box(fpl, -6.3, 6.3, -7.7, 7.7, 3.6, 4.0, st2))
    for k, (u, v, a) in enumerate(((-4.6, 0.0, math.pi), (-3.0, -3.6, math.pi * 0.8), (-3.0, 3.6, -math.pi * 0.8),
                                    (-0.4, -5.4, -math.pi * 0.62), (-0.4, 5.4, math.pi * 0.62), (2.6, -5.6, -math.pi / 2),
                                    (2.6, 5.6, math.pi / 2))):
        fh = fpl.at(u + 1.2, v, 4.0, a)
        S.add(Ellipsoid(fh.at(0, 0, 1.75), 1.25, 0.42, 0.55, dark))
        S.add(Capsule(fh, (1.0, 0, 1.95), (1.45, 0, 2.9), 0.27, dark))
        S.add(Ellipsoid(fh.at(1.6, 0, 2.95), 0.42, 0.18, 0.2, dark))
        for du, lift in ((-0.8, 0), (0.85, 0.5 if k == 0 else 0)):
            for dv in (-0.22, 0.22):
                S.add(Capsule(fh, (du, dv, 1.4), (du + lift, dv, 0.1 + lift), 0.13, dark))
        S.add(Capsule(fh, (-1.2, 0, 1.9), (-1.6, 0, 1.0), 0.12, dark))
        statue(S, fh.at(-0.1, 0, 0), 2.1, dark, 0.95 if k else 1.1)
    # the column's pedestal stands on the plinth
    S.add(Box(fcol, -2.6, 2.6, -2.6, 2.6, 4.0, 6.6, st))
    # the Heroes' Memorial Stone: a dark slab in a low frame of bollards and chains
    if HEROES_STONE in area:
        g = area[HEROES_STONE][3]
        S.add(Poly(g, z0 - 1.0, z0 + 0.4, st3))
        S.add(Poly(g.buffer(-1.6), z0 + 0.4, z0 + 0.9, P("#4b4d4c")))
        for p in np.array(g.exterior.coords)[:-1]:
            S.add(Lathe(Frame(p[0], p[1], z0, 0), 0.4, 1.3, cyl(0.25), dark))
    # the paving: light lines on grey granite, in the axis' frame
    if HOSOK_TERE in area:
        ring = Point(*C).buffer(R1 + 6).difference(Point(*C).buffer(R0 - 2.9)).intersection(
            shapely.box(C[0] + 5, C[1] - 80, C[0] + 80, C[1] + 80))
        sq = area[HOSOK_TERE][3].difference(ring)
        x0f, y0f, X, Y = grid_of(sq, 0)
        inside = shapely.contains_xy(sq, X, Y)
        U = ((X - C[0]) * fc.ca + (Y - C[1]) * fc.sa).astype(np.float32)
        V = (-(X - C[0]) * fc.sa + (Y - C[1]) * fc.ca).astype(np.float32)
        zs = [ctx["ground_m"](x_, y_) for x_ in range(4275, 4405, 20) for y_ in range(2320, 2440, 20) if sq.contains(Point(x_, y_))]
        base, line = P("#62675f"), P("#cbc7b9")

        def pave(f, wa):
            U_, V_, I_ = f["U"][None], f["V"][None], f["I"][None]
            av = np.abs(V_)
            # rectangles: 7 x 6 m along the axis, 7 x 12.5 m beyond the meander bands; each with an inner outline
            ch = np.where(av < 6.0, 6.0, 12.5)
            vv = np.where(av < 6.0, V_ + 3.0, av - 8.5)
            cu, cv = np.mod(U_ + 3.5, 7.0), np.mod(vv, ch)
            border = (cu < 0.5) | (cv < 0.5)
            iu, iv = np.abs(cu - 3.75), np.abs(cv - (ch + 0.5) / 2)
            hu, hv = 2.25, ch / 2 - 1.5
            inner = ((iu > hu - 0.5) & (iu <= hu) & (iv <= hv)) | ((iv > hv - 0.5) & (iv <= hv) & (iu <= hu))
            # the meander bands either side of the axis
            band = (av >= 6.0) & (av < 8.5)
            mu, mv = np.floor(np.mod(U_, 2.5) / 0.5).astype(np.int64), np.floor((av - 6.0) / 0.5).astype(np.int64)
            key = np.array([[1, 1, 1, 1, 1], [1, 0, 0, 0, 0], [1, 0, 1, 1, 0], [1, 0, 0, 1, 0], [1, 1, 1, 1, 0]])
            meander = band & (key[np.clip(mv, 0, 4), np.clip(mu, 0, 4)] == 1)
            light = np.where(band, meander, border | (inner & (av < 6.0)))
            return np.where(I_, np.where(light, line, base), 0).astype(np.uint16)
        S.add(Field(x0f, y0f, dict(U=U, V=V, I=inside), min(zs) - 1.5, max(zs) + 1.0, pave,
                    mode="paint", targets=[ctx["C"][k] for k in ("paving", "paving2", "road_paving", "concrete", "sett",
                                                                   "asphalt", "kerb", "mark", "grass", "grass2")]))
    S.clear.append((C[0], C[1], 58.0))


# ------------------------------------------------------------------------------------------------ Museum of Fine Arts
def fine_arts(S, ctx, plan):
    """the Museum of Fine Arts (Albert Schickedanz, Fülöp Herzog, 1906): the octastyle Corinthian portico to Heroes'
    Square with the Olympia pediment, the tall basilica hall behind it, the two side wings with Ionic temple fronts and
    the links between, the rear block round two glass-roofed courts with the high pyramid roof over its middle.
    Frame: origin on the portico's front, +u east along the front, +v towards the square (measured on OSM's outline,
    4.2 deg off the grid)."""
    P = ctx["P"]
    g = keep(ctx, FINE_ARTS)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(4344.0, 2266.0, b0, math.radians(4.2))
    stone, base, trim = P("#cdbb96"), P("#b19c78"), P("#ddd0b2")
    col = P("#d9cdb0")
    roofc, glass = P("#66716c", ROOF), P("#8fa5aa", GLASS)
    win = P("#4a5458", WINDOW)
    walls = [stone]
    # the rear block, round its two courts, and its high middle
    S.add(Box(fr, -63.6, 66.0, -108.8, -52.4, -2, 1.6, base))
    S.add(Box(fr, -63.4, 65.8, -108.6, -52.6, 1.6, 18.0, stone))
    S.add(Box(fr, -63.8, 66.2, -109.0, -52.2, 17.2, 18.6, trim))
    S.add(Box(fr, -11.2, 18.5, -112.3, -52.6, -2, 21.5, stone))
    S.add(Box(fr, -11.6, 18.9, -112.7, -52.2, 20.6, 22.0, trim))
    S.add(Roof(side(fr.at(3.65, -82.5), 1), -30.0, 30.0, -15.0, 15.0, 22.0, 10.5, roofc, hip=True))
    for cu in (-33.0, 41.0):  # the courts: a glass roof low over each, the wings round them under grey roofs
        S.add(Box(fr, cu - 18.5, cu + 18.5, -102.5, -60.0, 8.0, 18.7, 0, mode="carve"))
        S.add(Roof(fr.at(cu, -81.25), -18.5, 18.5, -21.25, 21.25, 8.0, 4.5, glass, hip=True))
    for v0, v1 in ((-108.8, -102.5), (-60.0, -52.4)):
        S.add(Roof(fr, -63.6, 66.0, v0, v1, 18.6, 2.6, roofc))
    for u0, u1 in ((-63.6, -51.5), (-14.5, -11.2), (18.5, 22.5), (59.5, 66.0)):
        S.add(Roof(side(fr.at((u0 + u1) / 2, -80.6), 1), -28.2, 28.2, -(u1 - u0) / 2, (u1 - u0) / 2, 18.6, 2.6, roofc))
    windows_on(S, side(fr.at(0, -80.6), 2), 63.6, -27, 27, 4.2, [(2.5, 6.0), (9.0, 14.5)], 0.9, win, walls)
    windows_on(S, fr.at(0, -80.6), 66.0, -27, 27, 4.2, [(2.5, 6.0), (9.0, 14.5)], 0.9, win, walls)
    windows_on(S, side(fr.at(0, -80.6), 3), 28.2, -60, 63, 4.4, [(2.5, 6.0), (9.0, 14.5)], 0.9, win, walls)
    # the basilica hall behind the portico: tall, its roof along the axis
    S.add(Box(fr, -15.1, 15.1, -54.0, -13.0, -2, 21.0, stone))
    S.add(Box(fr, -15.5, 15.5, -54.0, -13.0, 20.2, 21.6, trim))
    S.add(Roof(side(fr.at(0, -33.5), 1), -20.5, 20.5, -15.5, 15.5, 21.6, 7.0, roofc))
    for k in (-1, 1):
        S.add(Box(fr, -9.0 if k < 0 else 3.0, -3.0 if k < 0 else 9.0, -46, -21, 27.0, 28.6, glass))
    # the portico: eight columns, three bays deep, steps down to the square
    top = temple_front(S, side(fr.at(0, -14.0), 1), 14.6, 14.0, 8, 1.6, 16.2, col, base, trim, roofc, steps=1.6, r=0.75)
    # the side wings and their Ionic fronts; the lower links with colonnades between them and the portico
    for sgn, (u0, u1, vf) in ((-1, (-53.4, -35.9, -8.5)), (1, (34.4, 51.9, -10.4))):
        S.add(Box(fr, u0, u1, -52.5, vf - 6.0, -2, 15.5, stone))
        S.add(Box(fr, u0 - 0.3, u1 + 0.3, -52.8, vf - 5.7, 14.8, 16.0, trim))
        S.add(Roof(side(fr.at((u0 + u1) / 2, (-52.5 + vf - 6.0) / 2), 1), -(vf - 6.0 + 52.5) / 2, (vf - 6.0 + 52.5) / 2,
                   -(u1 - u0) / 2 - 0.3, (u1 - u0) / 2 + 0.3, 16.0, 4.0, roofc))
        temple_front(S, side(fr.at((u0 + u1) / 2, vf - 6.0), 1), (u1 - u0) / 2 - 0.4, 6.0, 4, 1.4, 12.6, col, base, trim,
                     roofc, steps=1.0)
        windows_on(S, side(fr.at((u0 + u1) / 2, -30), 2 if sgn < 0 else 0), (u1 - u0) / 2, -16, 14, 4.4,
                   [(3.0, 7.5), (9.5, 13.0)], 0.9, win, walls, arch=False)
        lu0, lu1 = (u1, -15.1) if sgn < 0 else (15.1, u0)
        lv = -14.3 if sgn < 0 else -13.8
        S.add(Box(fr, lu0, lu1, -52.4, lv - 3.5, -2, 11.0, stone))
        S.add(Box(fr, lu0, lu1, lv - 3.5, lv, -2, 1.4, base))
        row(S, side(fr, 1), lv - 0.6, -lu1 + 0.8, -lu0 - 0.8, 6, 1.4, 10.2, 0.42, col, trim)
        S.add(Box(fr, lu0, lu1, lv - 3.5, lv, 10.2, 11.4, trim))
        S.add(Roof(fr.at((lu0 + lu1) / 2, (lv - 52.4) / 2), -(lu1 - lu0) / 2, (lu1 - lu0) / 2, -(lv + 52.4) / 2,
                   (lv + 52.4) / 2, 11.4, 2.2, glass))
    # the rustication on the base and the windows of the hall's flanks
    windows_on(S, side(fr.at(0, -33.5), 0), 15.1, -18, 18, 4.5, [(12.5, 19.0)], 1.0, win, walls)
    windows_on(S, side(fr.at(0, -33.5), 2), 15.1, -18, 18, 4.5, [(12.5, 19.0)], 1.0, win, walls)
    S.clear.append((4344.0, 2200.0, 75.0))


# ------------------------------------------------------------------------------------------------ Műcsarnok
def mucsarnok(S, ctx, plan):
    """the Palace of Art (Albert Schickedanz, Fülöp Herzog, 1896): a hexastyle Corinthian portico with a gold mosaic
    in the pediment, red brick walls framed in yellow terracotta and polychrome friezes, a cross plan (front transept,
    the nave lit from its glass roof, a rear transept, the apse round the back), side halls with saw-tooth
    skylights. Frame: origin on the front's middle, +v south into the building, 3 deg off the grid."""
    P = ctx["P"]
    g = keep(ctx, MUCSARNOK)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(4313.0, 2462.5, b0, math.radians(-3.0))
    brick, terra, terra2 = P("#a5523d"), P("#d7b06a"), P("#c39552")
    base, col = P("#c8bba0"), P("#ddd2b6")
    gold, blue = P("#cfa64a", METAL), P("#37578a")
    roofc, glass = P("#59705f", ROOF), P("#8fa9ad", GLASS)
    win = P("#3e4a50", WINDOW)

    def wall(h):
        # brick panels framed by terracotta pilasters, string courses and a frieze under the cornice
        def c(u, v, w):
            w_ = w - 0.0
            frieze = (w_ > h - 2.2) & (w_ < h - 0.6)
            band = (np.abs(w_ - 4.8) < 0.35)
            pil = np.mod(u + v, 6.0) < 0.9
            pat = np.mod(np.floor(u * 2) + np.floor(v * 2) + np.floor(w_ * 2), 3) == 0
            return np.where(frieze, np.where(pat, blue, terra), np.where(band | pil | (w_ < 1.4), terra2, brick))
        return c
    # the apse first (a half-round hall; the carve that halves it must not cut what comes after): its conical roof
    fa = fr.at(0.5, 83.0)
    S.add(Lathe(fa, -2, 1.4, cyl(20.2), base))
    S.add(Lathe(fa, 1.4, 13.0, cyl(19.8), wall(13.0)))
    S.add(Lathe(fa, 13.0, 13.7, cyl(20.2), terra))
    S.add(Lathe(fa, 13.7, 18.5, cone(20.0, 3.5), roofc))
    S.add(Box(fa, -20.4, 20.4, -20.4, 0.0, 1.4, 20, 0, mode="carve"))
    # the front block and the transepts
    for u0, u1, v0, v1, h in ((-11.8, 11.6, 6.3, 11.2, 15.0), (-25.0, 26.4, 11.1, 24.5, 14.0),
                              (-24.0, 25.6, 67.6, 83.0, 14.0), (-20.0, 21.6, 24.0, 68.0, 11.0)):
        S.add(Box(fr, u0, u1, v0, v1, -2, 1.4, base))
        S.add(Box(fr, u0, u1, v0, v1, 1.4, h, wall(h)))
        S.add(Box(fr, u0 - 0.3, u1 + 0.3, v0 - 0.3, v1 + 0.3, h, h + 0.7, terra))
    # the nave over the middle: a clerestory and a glass ridge
    S.add(Box(fr, -9.5, 10.5, 11.2, 83.0, 1.4, 16.5, wall(16.5)))
    S.add(Box(fr, -9.9, 10.9, 10.8, 83.4, 16.5, 17.2, terra))
    S.add(Roof(side(fr.at(0.5, 47.0), 1), -36.0, 36.0, -10.2, 10.2, 17.2, 4.6, roofc))
    S.add(Roof(side(fr.at(0.5, 47.0), 1), -33.0, 33.0, -3.0, 3.0, 20.5, 1.5, glass))
    windows_on(S, side(fr.at(0.5, 47.0), 0), 10.0, -34, 34, 4.0, [(12.0, 15.8)], 1.1, win, [brick, terra2])
    windows_on(S, side(fr.at(0.5, 47.0), 2), 10.0, -34, 34, 4.0, [(12.0, 15.8)], 1.1, win, [brick, terra2])
    # the side halls' saw-tooth skylights
    for u0, u1 in ((-20.0, -9.5), (10.5, 21.6)):
        for v in np.arange(25.0, 67.0, 3.5):
            S.add(Roof(fr.at((u0 + u1) / 2, v + 1.75), -(u1 - u0) / 2, (u1 - u0) / 2, -1.75, 1.75, 11.7, 1.6, glass))
    for u0, u1, v0, v1, h in ((-11.8, 11.6, 6.3, 11.2, 15.7), (-25.0, 26.4, 11.1, 24.5, 14.7), (-24.0, 25.6, 67.6, 83.0, 14.7)):
        S.add(Roof(fr.at((u0 + u1) / 2, (v0 + v1) / 2), u0 - (u0 + u1) / 2, u1 - (u0 + u1) / 2, -(v1 - v0) / 2 - 0.3,
                   (v1 - v0) / 2 + 0.3, h, 3.2, roofc, hip=True))
    # the small rear porch
    S.add(Box(fr, -7.6, 7.9, 99.0, 110.6, -2, 9.0, wall(9.0)))
    S.add(Box(fr, -7.9, 8.2, 98.7, 110.9, 9.0, 9.6, terra))
    for k in range(10):
        a = math.pi * (k + 0.5) / 10
        S.add(Arch(fa.at(turn=a), 19.4, 20.4, 0, 1.3, 4.0, 10.0, win, mode="paint", targets=[brick, terra2]))
    # big arched windows on the transepts' ends and the side walls
    for v0, v1 in ((11.1, 24.5), (67.6, 83.0)):
        for k, uu in ((0, 26.4), (2, 25.0)):
            windows_on(S, side(fr.at(0, (v0 + v1) / 2), k), uu if k == 0 else 25.0, -(v1 - v0) / 2 + 1.5,
                       (v1 - v0) / 2 - 1.5, (v1 - v0) - 3, [(4.0, 11.5)], 2.6, win, [brick, terra2])
    windows_on(S, side(fr.at(0.8, 46.0), 0), 20.8, -20, 20, 5.0, [(3.0, 8.5)], 1.2, win, [brick, terra2])
    windows_on(S, side(fr.at(0.8, 46.0), 2), 19.2, -20, 20, 5.0, [(3.0, 8.5)], 1.2, win, [brick, terra2])
    # the portico: six Corinthian columns, the gold pediment
    pf = side(fr.at(0, 6.3), 3)
    S.add(Box(pf, -0.3, 5.5, -11.0, 11.0, -2.0, 1.4, base))
    for k in range(4):
        S.add(Box(pf, 5.5, 5.5 + 0.5 * (4 - k), -9.5, 9.5, -2.0, -0.2 + 0.4 * k, base))
    row(S, pf, 4.7, -8.9, 8.9, 6, 1.4, 12.2, 0.55, col, terra)
    for sv in (-1, 1):
        column(S, pf.at(2.2, sv * 8.9), 1.4, 12.2, 0.55, col, terra)
    S.add(Box(pf, -0.3, 5.5, -10.0, 10.0, 12.2, 13.8, terra))
    S.add(Box(pf, -0.3, 5.8, -10.3, 10.3, 13.8, 14.3, col))
    S.add(Roof(pf, -0.3, 5.8, -10.3, 10.3, 14.3, 4.2, terra))
    S.add(Roof(pf, 4.9, 5.9, -9.2, 9.2, 14.6, 3.4, gold))
    S.add(Roof(pf, 5.4, 5.9, -6.0, 6.0, 15.2, 2.2, blue))
    S.add(Roof(pf, -0.3, 5.5, -10.5, 10.5, 14.9, 4.2, roofc))
    windows_on(S, pf, 0.0, -9, 9, 6.0, [(2.0, 9.5)], 1.3, win, [brick, terra2, terra])
    S.clear.append((4313.0, 2515.0, 60.0))




# ------------------------------------------------------------------------------------------------ Vajdahunyad Castle
def vajdahunyad(S, ctx, plan):
    """Vajdahunyad Castle (Ignác Alpár, 1896 in timber, 1904-08 in stone): a catalogue of Hungarian styles round a
    court on the City Park's lake. On OSM's outlines: the Baroque wing (the Agricultural Museum; cream stone, slate
    mansards, domed corner pavilions), the Gothic wing after the castle at Hunedoara (rough stone, steep tiled roofs)
    with its towers (Nyebojsza, the Apostles', the gate tower over the bridge, the round Tompa, German and Catherine
    bastion towers), the Renaissance house, the Romanesque knights' castle and the chapel after Ják with its two west
    towers, apse and cloister."""
    P, area = ctx["P"], ctx["area"]
    for k, i in VAJDA.items():
        keep(ctx, i)
    g_ = {k: area[i][3] for k, i in VAJDA.items()}
    b0 = base_under(ctx, g_["main"], 0.4)
    stone, stone2, rough = P("#bcae94"), P("#a7987c"), P("#958670")
    brick, tile, tile2, slate = P("#a65c44"), P("#9d503b", ROOF), P("#7f4134", ROOF), P("#5f656b", ROOF)
    cream, cream2, copper = P("#e3d1a6"), P("#cbb68a"), P("#6f9d88", METAL)
    glazed = P("#c8a64a", ROOF)
    win = P("#43494c", WINDOW)

    def rubble(d, a, hw):
        k = np.mod(np.floor(a * 1.3) * 3 + np.floor(hw * 1.7) * 7, 5)
        return np.where(k == 0, stone2, np.where(k == 1, rough, stone))

    def cream_wall(d, a, hw):
        band = (np.abs(np.mod(hw, 5.2) - 0.2) < 0.25) | (hw < 1.4)
        win_ = (np.mod(a, 4.6) < 1.6) & (np.mod(hw - 1.6, 5.2) > 1.2) & (np.mod(hw - 1.6, 5.2) < 4.0) & (d < 0.6) & (hw > 1.6)
        return np.where(win_, win, np.where(band, cream2, cream))

    def gothic_wall(d, a, hw):
        win_ = (np.mod(a, 5.5) < 1.3) & (np.mod(hw - 2.0, 6.0) > 1.5) & (np.mod(hw - 2.0, 6.0) < 4.6) & (d < 0.6) & (hw > 2)
        return np.where(win_, win, rubble(d, a, hw))
    # the Baroque wing and its domed pavilions
    massing(S, g_["baroque"], b0, 17.0, cream_wall, slate, pitch=1.3, rmax=6.5, cornice=cream2, base=cream2, roof_top=slate)
    for (x, y), r, h in (((4637.0, 2597.0), 5.2, 19.5), ((4673.0, 2650.5), 5.5, 19.5), ((4652.0, 2621.0), 6.5, 21.0),
                         ((4618.0, 2650.0), 5.0, 19.5)):
        fd = Frame(x, y, b0, 0)
        S.add(Lathe(fd, -2, h, cyl(r), cream))
        S.add(Lathe(fd, h - 0.8, h + 0.4, cyl(r + 0.4), cream2))
        S.add(Lathe(fd, h + 0.4, h + 0.4 + r * 0.95, dome(r, 2.0, 0.9), slate))
        S.add(Lathe(fd, h + 0.3 + r * 0.95, h + 2.6 + r * 0.95, cyl(0.9), cream))
        S.add(Lathe(fd, h + 2.6 + r * 0.95, h + 4.2 + r * 0.95, cone(1.1, 0.1), slate))
        for k in range(8):
            a = TAU * k / 8
            S.add(Arch(Frame(x, y, b0, a), r - 0.5, r + 0.2, 0, 0.8, 7.0, 10.5, win, mode="paint", targets=[cream]))
    # the Gothic wing: rough stone and steep tiles, the Renaissance house, the knights' castle, the cloister
    massing(S, g_["main"], b0, 15.0, gothic_wall, tile, pitch=1.5, rmax=8.5, base=rough)
    massing(S, g_["gothic"], b0, 12.0, gothic_wall, tile2, pitch=1.6, rmax=6.0, base=rough)
    massing(S, g_["renaissance"], b0, 14.0, cream_wall, tile, pitch=1.0, rmax=5.0, cornice=cream2, base=cream2)
    massing(S, g_["knights"], b0, 13.0, rubble, tile2, pitch=1.4, rmax=6.5, base=rough)
    massing(S, g_["cloister"], b0, 5.0, rubble, tile, pitch=0.6, rmax=1.8)
    cx, cy, L, Wd, ang = LM.rect_of(g_["cloister"])
    for k in range(6):
        S.add(Arch(Frame(cx, cy, b0, ang + math.pi / 2), -Wd, Wd, -L / 2 + 1.6 + k * (L - 3.2) / 5, 1.0, 0.8, 2.9, mode="carve"))
    # the chapel after Ják: nave, two west towers with stone spires, the apse; its axis from OSM's outline
    gj = g_["jak"]
    cx, cy, L, Wd, ang = LM.rect_of(gj)
    fj = Frame(cx, cy, b0, ang)
    pts = np.array(gj.exterior.coords)
    apse_east = max(pts, key=lambda p: fj.uv(*p)[0])[0] > 4670  # the round end lies east (high x)
    fj = fj if apse_east else Frame(cx, cy, b0, ang + math.pi)
    S.add(Box(fj, -L / 2, L / 2 - 4.0, -Wd / 2, Wd / 2, -2, 11.5, stone))
    S.add(Roof(fj, -L / 2 + 4.0, L / 2 - 4.0, -Wd / 2 - 0.3, Wd / 2 + 0.3, 11.5, Wd * 0.55, tile))
    fa = fj.at(L / 2 - 4.0)
    S.add(Lathe(fa, -2, 9.0, cyl(3.8), stone))
    S.add(Lathe(fa, 9.0, 12.0, cone(4.1, 0.5), tile))
    S.add(Box(fa, -4.5, 0.0, -4.5, 4.5, -2, 13, 0, mode="carve"))
    S.add(Box(fj, L / 2 - 4.5, L / 2 - 4.0, -Wd / 2, Wd / 2, -2, 11.5, stone))
    for sv in (-1, 1):
        ft = fj.at(-L / 2 + 2.0, sv * (Wd / 2 - 2.0))
        S.add(Box(ft, -2.2, 2.2, -2.2, 2.2, -2, 21.0, stone))
        S.add(Box(ft, -2.4, 2.4, -2.4, 2.4, 20.6, 21.2, stone2))
        S.add(Lathe(ft, 21.2, 29.0, cone(2.3, 0.1), stone2, n=8, rot=math.pi / 8))
        for w in (12.5, 16.5):
            for k in range(4):
                S.add(Arch(ft.at(turn=k * math.pi / 2), 1.6, 2.6, 0, 0.5, w, w + 2.0, win, mode="paint", targets=[stone]))
    S.add(Arch(fj.at(-L / 2, 0, 0, math.pi), -0.6, 1.6, 0, 1.6, 0.0, 4.2, mode="carve"))  # the deep west portal
    S.add(Arch(fj.at(-L / 2, 0, 0, math.pi), 1.6, 2.4, 0, 2.6, 0.0, 4.8, stone2))
    for k in range(4):
        S.add(Arch(fj.at(-L / 2 + 6 + k * 3.4, Wd / 2, 0, math.pi / 2), -0.3, 0.6, 0, 0.6, 5.0, 8.4, win, mode="paint", targets=[stone]))
    # the towers, on their OSM outlines
    def tower(key, h, roof_h, wallc, roofc, round_=False, n=4, cap=None):
        g = g_[key]
        cx, cy, L, Wd, ang = LM.rect_of(g)
        fr = Frame(cx, cy, b0, ang)
        if round_:
            r = math.sqrt(g.area / math.pi)
            S.add(Lathe(fr, -2, h, cyl(r), wallc))
            S.add(Lathe(fr, h, h + 0.6, cyl(r + 0.4), stone2))
            S.add(Lathe(fr, h + 0.6, h + 0.6 + roof_h, cone(r + 0.5, 0.1), roofc))
        else:
            S.add(Box(fr, -L / 2, L / 2, -Wd / 2, Wd / 2, -2, h, wallc))
            S.add(Box(fr, -L / 2 - 0.4, L / 2 + 0.4, -Wd / 2 - 0.4, Wd / 2 + 0.4, h - 0.6, h + 0.4, stone2))
            S.add(TBox(fr, L / 2 + 0.3, Wd / 2 + 0.3, 0.15, 0.15, h + 0.4, h + 0.4 + roof_h, roofc))
            for sx in (-1, 1):  # corner turrets
                for sy in (-1, 1):
                    ft = fr.at(sx * (L / 2 - 0.2), sy * (Wd / 2 - 0.2))
                    S.add(Lathe(ft, h - 3.5, h + 0.8, cyl(0.9), wallc))
                    S.add(Lathe(ft, h + 0.8, h + 4.0, cone(1.0, 0.05), roofc))
        for k in range(4):
            for w in np.arange(6.0, h - 3, 6.0):
                rr = math.sqrt(g.area / math.pi) if round_ else (L / 2 if k % 2 == 0 else Wd / 2)
                S.add(Arch(fr.at(turn=k * math.pi / 2), rr - 0.5, rr + 0.3, 0, 0.55, w, w + 1.8, win, mode="paint", targets=[stone, stone2, brick]))
        return fr
    def brick_top(h0):
        return lambda u, v, w: np.where(w > h0, brick, np.where(np.mod(np.floor(w * 1.5) + np.floor((u + v) * 0.8), 4) == 0, stone2, stone))
    tower("gate", 27.0, 10.0, brick_top(16.0), tile2)
    tower("apostles", 25.0, 14.0, brick_top(12.0), glazed)
    tower("nyebojsza", 24.0, 7.0, stone, tile)
    tower("tompa", 15.0, 6.5, stone2, tile, round_=True)
    tower("nemet", 18.0, 6.0, stone, tile2)
    tower("katalin", 14.0, 6.0, stone2, tile, round_=True)
    S.clear.append((4625.0, 2600.0, 70.0))


BUILDERS = [("Museum of Fine Arts", fine_arts), ("Műcsarnok", mucsarnok), ("Vajdahunyad Castle", vajdahunyad)]
