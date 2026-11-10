"""Blaha Lujza tér: the Corvin Palace, the old Corvin department store (Zoltán Reiss, 1926), whose stone front came
back when its 1960s aluminium cladding was taken down (2018-2023), and the Europeum, a shopping centre with the
Courtyard by Marriott on its upper floors (2003). Both stand on the frames of their OSM outlines; heights, bays and roofs
come from street photos and aerial imagery (docs/landmarks.md).
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, MultiLineString

from landmarks import WINDOW, Arch, Box, Ellipsoid, Field, Frame, TBox, ring_segments, seg_frame
from landmarks_city import base_under, dist_in, grid_of
from landmarks_more import frame_fields, largest, rect_poly
from style import GLASS, METAL, ROOF

CORVIN, EUROPEUM = 261801166, 308551954
NAMES = ["Corvin Palace", "Europeum"]
DROP = {CORVIN, EUROPEUM}


# ------------------------------------------------------------------------------------------------ helpers
def straight_runs(g, tol=4.0):
    """the outline's walls, collinear edges merged: [(a, b, outward normal)] in ring order."""
    c = np.array(largest(g).exterior.coords)[:-1]
    n = len(c)
    ang = [math.atan2(*(c[(i + 1) % n] - c[i])[::-1]) for i in range(n)]
    turn = [abs((ang[i] - ang[i - 1] + math.pi) % (2 * math.pi) - math.pi) > math.radians(tol) for i in range(n)]
    start = turn.index(True) if any(turn) else 0
    out, first = [], start
    for k in range(1, n + 1):
        i = (start + k) % n
        if turn[i] or k == n:
            a, b = c[first], c[i]
            d = (b - a) / np.linalg.norm(b - a)
            nrm = np.array([d[1], -d[0]])
            if g.contains(shapely.Point(*((a + b) / 2 + nrm * 0.5))):
                nrm = -nrm
            out.append((a, b, nrm))
            first = i
    return out


def north_front(walls, theta):
    """the longest wall facing north, from its western end: (index, a, b)."""
    north = np.array([math.sin(theta), -math.cos(theta)])
    east = np.array([math.cos(theta), math.sin(theta)])
    k = max(range(len(walls)), key=lambda i: np.linalg.norm(walls[i][1] - walls[i][0]) * (walls[i][2] @ north > 0.85))
    a, b, _ = walls[k]
    return (k, a, b) if (b - a) @ east > 0 else (k, b, a)


def side_wall(walls, k, corner):
    """the wall next to wall k at one of its corners: (unit direction away from the corner, its far end)."""
    for j in ((k - 1) % len(walls), (k + 1) % len(walls)):
        a, b, _ = walls[j]
        for p, q in ((a, b), (b, a)):
            if np.linalg.norm(p - corner) < 0.5:
                return (q - p) / np.linalg.norm(q - p), q
    raise KeyError(f"corner {corner}")


def wall_frame(c, t, inside, oz):
    """a frame at corner c, v into the building, u along direction t or against it: (frame, sign) with
    frame.at(sign * s) s metres from the corner."""
    ang = math.atan2(t[1], t[0])
    f = Frame(c[0], c[1], oz, ang)
    if f.uv(*inside)[1] < 0:
        return Frame(c[0], c[1], oz, ang + math.pi), -1
    return f, 1


def unit(p):
    return p / np.linalg.norm(p)


# ------------------------------------------------------------------------------------------------ the Corvin Palace
E_C, E_R = 19.8, 19.0          # the stone front's cornice top; the back ranges' cornice
WS = 5.7                       # the arcade's springing, the top of the balustrades in the arches
CORNER, ARCH, PIER, MIDPIER, END = 2.5, 4.1, 1.7, 3.5, 2.6
BAY_R = 5.4                    # the back ranges' window bays


def front_layout(L):
    """the square front from one corner: corner pier, four arches, the pier with paired pilasters, the portal, and
    the same mirrored -> [(kind, s0, s1)]."""
    out, s = [("corner", 0.0, CORNER)], CORNER
    for i in range(4):
        out.append(("arch", s, s + ARCH))
        s += ARCH
        if i < 3:
            out.append(("pier", s, s + PIER))
            s += PIER
    out.append(("pair", s, s + MIDPIER))
    s += MIDPIER
    return out + [("portal", s, L - s)] + [(k, L - b, L - a) for k, a, b in reversed(out)]


def return_layout():
    """the stone front's return into a side street, from the corner: two arches, a pier with the candelabrum."""
    s = CORNER
    out = [("corner", 0.0, CORNER)]
    for kind, w in (("arch", ARCH), ("pier", PIER), ("arch", ARCH), ("end", END)):
        out.append((kind, s, s + w))
        s += w
    return out


def corvin(S, ctx, plan):
    """the Corvin Palace (Zoltán Reiss, 1926), on the square between Márkus Emília and Somogyi Béla utca, in pale
    beige stone. The front to the square and its returns into the side streets: a rusticated arcade of round arches
    over shop fronts, balustrades at the springing, medallions between the arches, a square portal in the middle; a
    Greek-key band; giant fluted pilasters two storeys high, paired at the corners and by the portal, with tall
    dark-framed windows between them; small square windows in the frieze, a dentilled cornice, a balustrade along the
    roof with candelabra on its corners and ends, a relief figure on each corner. Behind: the back ranges along the
    side streets and Stáhly utca, five storeys rendered greige with banded shop fronts, windows in pairs between
    pilaster strips and rounded corners, flat roofs round a court over the glass-roofed hall."""
    P, area = ctx["P"], ctx["area"]
    g0 = largest(area[CORVIN][3])
    b0 = base_under(ctx, g0, 0.4)
    walls = straight_runs(g0)
    k, a, b = north_front(walls, ctx["theta"])
    L = float(np.linalg.norm(b - a))
    t = (b - a) / L
    inside = np.array(g0.representative_point().coords[0])
    fr, _ = wall_frame(a, t, inside, b0)          # u: along the square front from its western corner, v: inwards
    VF = CORNER + 2 * ARCH + PIER + END           # how far the stone front returns along the side streets

    C = dict(stone=P("#d3ccbc"), upper=P("#c6bfaf"), rust=P("#bbb3a3"), trim=P("#e7e2d6"), trim2=P("#d6cfbf"),
             plinth=P("#aea798"), win=P("#2e3640", WINDOW), shop=P("#46494c", WINDOW), brown=P("#4a3628"),
             dark=P("#2b2927"), frame=P("#3d3f42"), fan=P("#9fb3bd", GLASS))
    render, render2, lesene = P("#d5d0c5"), P("#c7c1b5"), P("#e0dcd3")
    roofc, roofc2 = P("#9c988f", ROOF), P("#8b8880", ROOF)
    glass = P("#a3b8c0", GLASS)
    faces_c = [C["stone"], C["upper"], C["rust"], C["trim2"]]

    # the back ranges' corners on Stáhly utca are rounded; the stone front keeps its sharp ones
    zone = rect_poly(fr, -40, L + 40, -40, VF + 1.0)
    rounded = g0.buffer(-5.0, join_style=1).buffer(5.0, join_style=1)
    g = largest(g0.intersection(zone).union(rounded.difference(zone)).buffer(0.01).buffer(-0.01))
    court = rect_poly(fr, 20.0, L - 14.0, VF + 4.0, VF + 38.0).intersection(g.buffer(-8.0))
    hall = rect_poly(fr, 26.0, L - 18.0, VF + 7.0, VF + 22.0).intersection(court)

    x0f, y0f, X, Y = grid_of(g, 2.0)
    d = dist_in(g, X, Y)
    U, V = frame_fields(fr, X, Y)
    dc = dist_in(court, X, Y) if not court.is_empty else np.full_like(d, -99.0)
    hl = shapely.contains_xy(hall, X, Y).astype(np.float32) if not hall.is_empty else np.zeros_like(d)
    fields = dict(d=d, U=U, V=V, dc=dc, hl=hl)

    def fn(f, wa):
        d_, U_, V_, dc_, hl_ = f["d"][None], f["U"][None], f["V"][None], f["dc"][None], f["hl"][None] > 0
        h = wa - b0
        front = V_ < VF
        face = d_ < 1.0
        incourt = dc_ > 0
        top = np.where(front, E_C, np.where(incourt, 10.5, E_R))
        body = (d_ > 0) & (h < top)
        # the stone front: plinth, rusticated arcade storey, string course, key band, architrave, flat roof
        rus = (h < 8.8) & face & (np.mod(h, 1.2) < 0.4)
        key = (h >= 9.1) & (h < 9.9) & face
        keyc = np.where(np.mod(np.floor(U_ + V_) + np.floor(h * 2), 2) == 0, C["trim"], C["stone"])
        cf = np.where(h < 0.6, C["plinth"], np.where(rus, C["rust"], np.where(h < 9.9, C["stone"], C["upper"])))
        cf = np.where((h >= 8.8) & (h < 9.1), C["trim"], np.where(key, keyc, cf))
        cf = np.where((h >= 17.1) & (h < 17.5) & face, C["trim"], cf)
        cf = np.where((h >= E_C - 0.5) & (d_ > 1.0), roofc, cf)
        # the back ranges: banded ground floor, string course, render; the court's walls with rows of windows
        band = (h < 5.2) & face & (np.mod(h, 0.9) < 0.3)
        cr = np.where(h < 0.5, C["plinth"], np.where(band, render2, render))
        cr = np.where((h >= 5.2) & (h < 5.6), lesene, cr)
        z = np.mod(h - 10.5, 3.3)
        cwin = (dc_ > -0.6) & (h >= 10.5) & (h < E_R - 0.6) & (z > 1.0) & (z < 2.6) & (np.mod(U_ + V_, 2.7) < 1.3)
        cr = np.where(cwin, C["win"], cr)
        cr = np.where((h >= top - 0.5) & (d_ > 0.6), np.where(incourt & hl_, glass, roofc2), cr)
        out = np.where(body, np.where(front, cf, cr), 0)
        cornice = ~front & (d_ > -0.6) & (d_ <= 0) & (h >= E_R - 0.7) & (h < E_R)
        parapet = ~front & (d_ > 0) & (d_ < 0.5) & (h >= E_R) & (h < E_R + 0.6)
        return np.where(cornice | parapet, lesene, out).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 3.0, b0 + E_C + 1.0, fn))

    # the stone front and its two returns, cornice and balustrade, candelabra and the corner figures
    ends = []
    faces = [(wall_frame(a, t, inside, b0), front_layout(L))]
    for c, toward in ((a, t), (b, -t)):
        td, _ = side_wall(walls, k, c)
        faces.append((wall_frame(c, td, inside, b0), return_layout()))
        out = unit(-(toward + td))
        figure = Frame(*(c + out * 0.35), b0, math.atan2(out[1], out[0]))
        S.add(Box(figure, -0.5, 0.2, -0.5, 0.5, 6.6, 7.0, C["trim"]))
        S.add(Ellipsoid(figure.at(0, 0, 7.85), 0.32, 0.36, 0.85, C["trim"]))
        S.add(Ellipsoid(figure.at(0, 0, 8.9), 0.2, 0.2, 0.24, C["trim"]))
        corner = Frame(*(c - out * 1.25), b0, 0)
        candelabrum(S, corner, C)
        ends.append(c + td * (VF - 1.3) + unit(toward) * 0.9)
    for x, y in ends:
        candelabrum(S, Frame(x, y, b0, 0), C)
    for (f, sg), layout in faces:
        stone_face(S, f, sg, layout, C, faces_c)
    for i, ((f, sg), layout) in enumerate(faces):
        ext = 1.4 if i == 0 else 0.0              # the front's cornice runs on round both corners
        u0, u1 = sorted((-ext * sg, sg * (layout[-1][2] + ext)))
        cornice_run(S, f, u0, u1, C)
        balustrade(S, f, sg, layout, C)

    rear_windows(S, g, b0, fr, VF, [render, render2], C["win"], C["shop"], C["frame"], lesene)
    # on the front range's roof: two skylights and the stair house (as aerial photos show them)
    for uc in (10.0, L - 9.0):
        fs = fr.at(uc, 13.5)
        S.add(Box(fs, -2.3, 2.3, -2.3, 2.3, E_C - 0.5, E_C + 0.6, roofc2))
        S.add(TBox(fs, 2.0, 2.0, 0.5, 0.5, E_C + 0.6, E_C + 1.9, glass))
    S.add(Box(fr.at(L / 2 - 1.0, 14.0), -1.8, 1.8, -2.6, 2.6, E_C - 0.5, E_C + 2.2, render))
    S.add(Box(fr.at(L / 2 - 1.0, 14.0), -2.0, 2.0, -2.8, 2.8, E_C + 2.2, E_C + 2.5, roofc2))


def pilaster(S, fc, u0, u1, C):
    """a fluted giant pilaster between the key band and the frieze, on base and capital."""
    def fluted(u, v, w):
        return np.where(np.abs(u - (u0 + u1) / 2) < 0.22, C["trim2"], C["trim"]).astype(np.uint16)
    S.add(Box(fc, u0 - 0.2, u1 + 0.2, -0.7, 0.0, 9.9, 10.5, C["trim"], mode="under"))
    S.add(Box(fc, u0, u1, -0.55, 0.0, 10.5, 16.4, fluted, mode="under"))
    S.add(Box(fc, u0 - 0.25, u1 + 0.25, -0.75, 0.0, 16.4, 17.3, C["trim"], mode="under"))


def tall_window(S, fa, v0, v1, C, faces):
    """one of the tall windows of the giant order: dark brown frames, the wooden band of the floor behind them, a
    carved panel above."""
    def col(u, v, w):
        fr_ = (np.abs(v - (v0 + v1) / 2) < 0.25) | ((w > 12.3) & (w < 12.9)) | (np.mod(w - 10.3, 1.5) < 0.3)
        return np.where(fr_, C["brown"], C["win"]).astype(np.uint16)
    S.add(Box(fa, -0.1, 0.6, v0, v1, 10.3, 14.9, 0, mode="carve"))
    S.add(Box(fa, 0.6, 1.1, v0, v1, 10.3, 14.9, col))
    S.add(Box(fa, -0.4, 0.5, v0 + 0.1, v1 - 0.1, 15.2, 16.2, C["rust"], mode="paint", targets=faces))
    if v1 - v0 > 2:
        S.add(Box(fa, -0.5, 0.0, (v0 + v1) / 2 - 0.3, (v0 + v1) / 2 + 0.3, 15.45, 15.95, C["trim"], mode="under"))


def stone_face(S, f, sg, layout, C, faces):
    """one wall of the stone front, element by element from the corner."""
    def balus(u, v, w):
        rail = (w >= WS - 0.3) | (w < 4.9)
        return np.where(rail | (np.mod(v, 1.0) < 0.5), C["trim"], 0).astype(np.uint16)

    def shopfront(u, v, w):
        sign = (w >= 3.9) & (w < 4.6)
        bars = (np.abs(v) < 0.25) | (w < 0.3)
        glass = np.where(w >= 4.6, C["fan"], C["shop"])    # the arch's glazed head over the shop front
        return np.where(sign, C["dark"], np.where(bars, C["frame"], glass)).astype(np.uint16)

    def portal_glass(u, v, w):
        bars = (np.mod(v + 10.0, 1.4) < 0.25) | (np.abs(w - 3.3) < 0.2)
        return np.where(bars, C["frame"], C["shop"]).astype(np.uint16)
    for kind, s0, s1 in layout:
        fc = f.at(sg * (s0 + s1) / 2, 0)
        fa = fc.at(turn=math.pi / 2)              # u: into the wall, v: along it
        half = (s1 - s0) / 2
        if kind == "arch":
            S.add(Arch(fa, -0.4, 0.5, 0, half + 0.5, 0.6, WS, C["trim"], mode="paint", targets=faces))
            S.add(Arch(fa, -0.1, 1.0, 0, half, 0.25, WS, mode="carve"))
            S.add(Arch(fa, 1.0, 1.6, 0, half, 0.0, WS, shopfront))
            S.add(Box(fa, 0.3, 0.8, -half, half, 4.6, WS, balus))
            S.add(Box(fa, -0.4, 0.5, -1.85, 1.85, 9.95, 16.8, C["trim2"], mode="paint", targets=faces))
            tall_window(S, fa, -1.5, 1.5, C, faces)
            S.add(Box(fa, -0.1, 0.5, -0.7, 0.7, 17.6, 18.5, 0, mode="carve"))
            S.add(Box(fa, 0.5, 1.0, -0.7, 0.7, 17.6, 18.5, C["win"]))
            for sv in (-1, 1):  # the consoles either side of the frieze window
                S.add(Box(fa, -0.5, 0.0, sv * 1.0 - 0.25, sv * 1.0 + 0.25, 17.4, 18.5, C["trim"], mode="under"))
        elif kind == "pier":
            pilaster(S, fc, -0.75, 0.75, C)
            S.add(Ellipsoid(fc.at(0, 0, 7.15), 0.8, 0.35, 0.8, C["trim"]))
        elif kind in ("corner", "pair", "end"):
            g_ = 0.25 if kind != "end" else 0.15
            pilaster(S, fc, -half + 0.05, -g_, C)
            pilaster(S, fc, g_, half - 0.05, C)
            if kind == "pair":  # poster frames on the portal's piers, the market's banners hung between the pilasters
                S.add(Box(fa, -0.3, 0.3, -0.7, 0.7, 1.0, 3.4, C["dark"], mode="paint", targets=faces))
                S.add(Box(fc, -0.5, 0.5, -1.0, -0.6, 10.9, 16.2, C["dark"]))
        elif kind == "portal":
            S.add(Box(fa, -0.4, 0.5, -half - 0.5, half + 0.5, 0.6, 7.6, C["trim"], mode="paint", targets=faces))
            S.add(Box(fa, -0.1, 2.0, -half, half, 0.25, 7.1, 0, mode="carve"))
            S.add(Box(fa, 2.0, 2.6, -half, half, 0.0, 7.1, portal_glass))
            S.add(Box(fa, -0.5, 0.0, -2.4, 2.4, 7.5, 8.4, C["dark"]))   # the CORVIN-PALACE board
            S.add(Box(fa, -0.6, -0.4, -1.9, 1.9, 7.8, 8.1, C["trim"]))
            S.add(Box(fa, -0.4, 0.5, -3.1, 3.1, 9.95, 16.8, C["trim2"], mode="paint", targets=faces))
            tall_window(S, fa, -1.25, 1.25, C, faces)
            for sv in (-1, 1):
                tall_window(S, fa, sv * 2.35 - 0.45, sv * 2.35 + 0.45, C, faces)
                S.add(Box(fa, -0.35, 0.0, sv * 1.58 - 0.3, sv * 1.58 + 0.3, 10.3, 15.2, C["trim"], mode="under"))
                S.add(Box(fa, -0.1, 0.5, sv * 1.6 - 0.7, sv * 1.6 + 0.7, 17.6, 18.5, 0, mode="carve"))
                S.add(Box(fa, 0.5, 1.0, sv * 1.6 - 0.7, sv * 1.6 + 0.7, 17.6, 18.5, C["win"]))


def cornice_run(S, f, u0, u1, C):
    """the dentil course, the corona and its top member, overhanging the wall by 1.3 m."""
    def dentils(u, v, w):
        return np.where(np.mod(u, 1.0) < 0.5, C["trim2"], 0).astype(np.uint16)
    S.add(Box(f, u0, u1, -0.6, 0.0, 18.5, 18.95, dentils))
    S.add(Box(f, u0, u1, -1.2, 0.0, 18.95, 19.5, C["trim"]))
    S.add(Box(f, u0, u1, -1.35, 0.0, 19.5, E_C, C["trim2"]))


def balustrade(S, f, sg, layout, C):
    """the balustrade along the roof's edge over the wall, a pedestal over every pilaster."""
    def balusters(u, v, w):
        return np.where(np.mod(u, 1.0) < 0.5, C["trim"], 0).astype(np.uint16)
    u0, u1 = sorted((0.0, sg * layout[-1][2]))
    S.add(Box(f, u0, u1, -0.55, 0.15, E_C, E_C + 0.3, C["trim"]))
    S.add(Box(f, u0, u1, -0.45, 0.05, E_C + 0.3, E_C + 0.95, balusters))
    S.add(Box(f, u0, u1, -0.55, 0.15, E_C + 0.95, E_C + 1.25, C["trim"]))
    for kind, s0, s1 in layout:
        if kind in ("pier", "pair", "corner", "end"):
            hw = 0.55 if kind == "pier" else 1.1
            S.add(Box(f.at(sg * (s0 + s1) / 2), -hw, hw, -0.65, 0.25, E_C, E_C + 1.45, C["trim"]))


def candelabrum(S, fc, C):
    """a corner candelabrum: a pedestal on the balustrade and a stone obelisk with a ball."""
    S.add(Box(fc, -0.95, 0.95, -0.95, 0.95, E_C, E_C + 1.9, C["trim"]))
    S.add(Box(fc, -1.1, 1.1, -1.1, 1.1, E_C + 1.7, E_C + 2.0, C["trim2"]))
    S.add(TBox(fc, 0.55, 0.55, 0.15, 0.15, E_C + 2.0, E_C + 4.8, C["trim"]))
    S.add(Ellipsoid(fc.at(0, 0, E_C + 5.0), 0.3, 0.3, 0.32, C["trim"]))


def rear_windows(S, g, b0, fr, VF, targets, win, shop, frame, lesene):
    """the back ranges' fronts: per bay a shop window on the ground floor and pairs of windows above, flat pilaster
    strips between the bays."""
    for a, b, n in ring_segments(g, 4.0):
        va, vb = fr.uv(*a)[1], fr.uv(*b)[1]
        lo = VF + 0.8
        if max(va, vb) <= lo:
            continue
        if min(va, vb) < lo:  # the part of the wall behind the stone front's return
            cut = a + (b - a) * (lo - va) / (vb - va)
            a, b = (cut, b) if va < vb else (a, cut)
        Ls = float(np.hypot(*(b - a)))
        nb = int(Ls // BAY_R)
        if nb < 1:
            continue
        fw = seg_frame(a, b, n, 0)
        su, eu = fw.uv(*a)[0], fw.uv(*b)[0]
        s0 = min(su, eu) + (Ls - nb * BAY_R) / 2
        for i in range(nb + 1):
            S.add(Box(fw.at(s0 + i * BAY_R), -0.5, 0.5, -0.45, 0.0, b0 + 5.6, b0 + E_R - 0.7, lesene, mode="under"))
        for i in range(nb):
            fi = fw.at(s0 + (i + 0.5) * BAY_R, 0, 0, math.pi / 2)
            S.add(Box(fi, -0.1, 0.45, -1.8, 1.8, b0 + 0.6, b0 + 4.6, 0, mode="carve"))
            S.add(Box(fi, 0.45, 0.95, -1.8, 1.8, b0 + 0.6, b0 + 4.6, lambda u, v, w: np.where(
                (np.abs(v) < 0.25) | (w > b0 + 3.9), frame, shop).astype(np.uint16)))
            for w0, w1 in ((6.0, 8.3), (9.4, 11.7), (12.8, 15.1), (16.3, 17.8)):
                for sv in (-0.85, 0.85):
                    S.add(Box(fi, -0.1, 0.45, sv - 0.55, sv + 0.55, b0 + w0, b0 + w1, 0, mode="carve"))
                    S.add(Box(fi, 0.45, 0.95, sv - 0.55, sv + 0.55, b0 + w0, b0 + w1, win))


# ------------------------------------------------------------------------------------------------ the Europeum
E_E, E_T = 20.2, 23.6          # the Europeum's main roof; the top storey's
BAY_E = 5.25
NOTCH, NOTCH_D = 6.3, 4.6      # the corner frame's opening along each front, and its depth
CPIER = 2.0                    # the corner pier
GLYPHS = {"e": (".##", "###", "#..", ".##", "..."), "u": ("#.#", "#.#", "#.#", "###", "..."),
          "r": ("#.#", "##.", "#..", "#..", "..."), "o": ("###", "#.#", "#.#", "###", "..."),
          "p": ("###", "#.#", "###", "#..", "#.."), "m": ("####.", "#.#.#", "#.#.#", "#.#.#", ".....")}
SIGN = np.array([[c == "#" for c in ".".join(GLYPHS[k][r] for k in "europeum")] for r in range(5)])  # on the roof


def europeum(S, ctx, plan):
    """the Europeum (2003) on the corner of the square and József körút, faced in pale cream stone. A retail base of
    two storeys, square stone piers in front of recessed shop windows and big panes above them; three hotel storeys
    with windows in pairs, a narrow one beside a wide one; on top, behind the front, a glazed storey set back over
    the western half and an open stone frame with a loggia behind it over the eastern half and the körút. The
    corner to the square is cut away the full height into a glazed recess behind an open stone frame (the corner pier,
    two beams, the roof slab), with the red europeum letters on top. Inside, a court over the mall's glass roof; a
    lift tower."""
    P, area = ctx["P"], ctx["area"]
    g = largest(area[EUROPEUM][3])
    b0 = base_under(ctx, g, 0.4)
    walls = straight_runs(g)
    k, a, b = north_front(walls, ctx["theta"])
    LN = float(np.linalg.norm(b - a))
    tN = (b - a) / LN
    inside = np.array(g.representative_point().coords[0])
    fe, _ = wall_frame(a, tN, inside, b0)         # u: along the square front from the Somogyi Béla utca corner
    tE, eE = side_wall(walls, k, b)               # the körút front from the corner
    tW, eW = side_wall(walls, k, a)               # the Somogyi Béla utca front
    streets = [LineString([a, b]), LineString([b, eE]), LineString([a, eW])]
    rest = g.exterior.difference(MultiLineString(streets).buffer(0.3))

    stone, stone_l = P("#e2dbc9"), P("#ece6d7")
    win, shop = P("#33404b", WINDOW), P("#3c4a55", WINDOW)
    cglass, tglass = P("#5f7684", GLASS), P("#8aa2ae", GLASS)
    mullion, slab = P("#5b6064", METAL), P("#c9c2b2")
    roofc, roofc2, inner = P("#7b7d74", ROOF), P("#5f6265", ROOF), P("#a39d90")
    red = P("#c62a3b")

    x0f, y0f, X, Y = grid_of(g, 2.0)
    d = dist_in(g, X, Y)
    U, V = frame_fields(fe, X, Y)
    pts = shapely.points(X.ravel(), Y.ravel())
    dist = [shapely.distance(s, pts).reshape(X.shape) for s in streets]
    dist.append(shapely.distance(rest, pts).reshape(X.shape) if not rest.is_empty else np.full(X.shape, 99.0))
    fac = np.argmin(np.stack(dist), 0).astype(np.float32)          # 0 square, 1 körút, 2 Somogyi, 3 party walls
    sN = U
    sE = ((X - b[0]) * tE[0] + (Y - b[1]) * tE[1]).astype(np.float32)
    sW = ((X - a[0]) * tW[0] + (Y - a[1]) * tW[1]).astype(np.float32)
    s = np.where(fac == 1, sE, np.where(fac == 2, sW, sN)).astype(np.float32)
    LE, LW = float(np.linalg.norm(eE - b)), float(np.linalg.norm(eW - a))
    court = rect_poly(fe, 18.0, 50.0, 17.0, 31.0).intersection(g.buffer(-12.0))
    dc = dist_in(court, X, Y) if not court.is_empty else np.full_like(d, -99.0)
    fields = dict(d=d, fac=fac, s=s, dc=dc, U=U, V=V)
    entry = 1.2 + BAY_E * (round(0.36 * LN / BAY_E) + 0.5)

    def fn(f, wa):
        d_, fac_, s_, dc_, U_, V_ = (f[q][None] for q in ("d", "fac", "s", "dc", "U", "V"))
        h = wa - b0
        street = fac_ < 3
        end = np.where(fac_ == 0, LN, np.where(fac_ == 1, LE, LW))
        off = np.where(fac_ == 1, NOTCH, 0.0)
        ph = np.mod(s_ - off - 0.6, BAY_E)                          # the bay's phase, a pier at 0..1.2
        pier = (ph < 1.2) | (s_ < 1.4) | (s_ > end - 1.4)
        notch = ((fac_ == 0) & (s_ > LN - NOTCH)) | ((fac_ == 1) & (s_ < NOTCH))
        sc = np.where(fac_ == 0, LN - s_, s_)                       # metres from the corner along either front
        cpier = notch & (d_ < CPIER) & (sc < CPIER)
        mpier = notch & (d_ < 1.0) & (np.abs(sc - (NOTCH + CPIER) / 2) < 0.55) & (h >= 5.6) & (h < 9.6)
        frame_top = (((fac_ == 1) & (d_ < 12.0)) | ((U_ > LN / 2) & (V_ < 12.0))) & (d_ > 0)
        glass_top = (U_ >= 2.5) & (U_ <= LN / 2) & (V_ < 11.0) & (d_ > 0)
        incourt = dc_ > 0

        top = np.where(incourt, 10.0, E_E)
        top = np.where(frame_top, E_T, np.where(glass_top & (V_ >= 1.6), E_T - 0.2, top))
        body = (d_ > 0) & (h < top)
        out = np.where(body, stone, 0)
        out = np.where(body & (h >= top - 0.5) & (d_ > 0.6), np.where(incourt, cglass, roofc), out)
        out = np.where(body & (top > E_E) & (h >= top - 0.4) & (d_ > 0.6), roofc2, out)
        sf = street & ~pier
        # the retail base: the arcade's shop windows set back behind the piers, a fascia, big panes above
        gf = sf & (h < 5.0)
        out = np.where(gf & (d_ < 1.2), 0, np.where(gf & (d_ < 1.7), np.where(np.mod(s_, 2.6) < 0.3, mullion, shop), out))
        ff = sf & (h >= 5.6) & (h < 9.6)
        out = np.where(ff & (d_ < 0.5), 0, np.where(ff & (d_ < 1.0), np.where((h > 8.3) & (h < 8.6), mullion, win), out))
        ent = (fac_ == 0) & (np.abs(s_ - entry) < BAY_E / 2 - 0.6) & (h < 9.6)   # the double-height entrance
        out = np.where(ent & (d_ < 2.2), 0, np.where(ent & (d_ < 2.7), np.where(np.mod(s_, 1.6) < 0.3, mullion, shop), out))
        out = np.where(street & body & (d_ < 0.5) & (((h >= 5.0) & (h < 5.6)) | ((h >= 9.6) & (h < 10.0))), stone_l, out)
        # the hotel: a narrow and a wide window in every bay
        z = np.mod(h - 10.0, 3.2)
        hw = street & (h >= 10.0) & (h < 19.6) & (z >= 0.8) & (z < 2.75) & (((ph >= 1.6) & (ph < 2.6)) | ((ph >= 3.0) & (ph < 5.1)))
        out = np.where(hw & (d_ < 0.5), 0, np.where(hw & (d_ < 1.0), win, out))
        out = np.where(street & body & (d_ < 0.5) & (h >= E_E - 0.3) & (h < E_E) & (top <= E_E), stone_l, out)
        # the parapet over the main roof
        par = (d_ > 0) & (d_ < 0.5) & (h >= E_E) & (h < E_E + 0.4) & (top <= E_E + 0.1)
        par |= glass_top & (V_ < 0.5) & (h >= E_E) & (h < E_E + 0.4)
        out = np.where(par, stone_l, out)
        # the top storey: an open stone frame with a loggia behind it, or glass set back from the front
        ft = frame_top & (h >= E_E) & (h < E_T)
        opening = ft & (d_ < 0.6) & ~pier & (h >= 20.6) & (h < 22.8)
        loggia = ft & (d_ >= 0.6) & (d_ < 3.0) & (h < E_T - 0.6)
        out = np.where(opening | loggia, 0, out)
        out = np.where(ft & (d_ >= 3.0) & (d_ < 3.5) & (h < E_T - 0.6),
                       np.where(np.mod(s_, 1.5) < 0.3, mullion, tglass), out)
        gt = glass_top & (h >= E_E) & (h < E_T - 0.2) & (V_ >= 1.6) & ((V_ < 2.1) | (U_ < 3.0))
        out = np.where(gt & (h < E_T - 0.6), np.where(np.mod(s_, 1.5) < 0.3, mullion, tglass), out)
        # the corner cut away the full height behind an open stone frame: the corner pier, beams over the shops and
        # the first floor with a pier between them on each front, the roof slab across the top; glass walls behind
        nb = notch & (d_ < NOTCH_D)
        beam = ((d_ < 1.0) & (((h >= 5.0) & (h < 5.6)) | ((h >= 9.6) & (h < 10.4)))) | (h >= E_T - 0.9)
        frame = beam | cpier | mpier
        out = np.where(nb & ~frame & (h < E_T), 0, out)
        out = np.where(nb & frame & (h < E_T) & (d_ > 0), np.where(h >= E_T - 0.9, slab, stone), out)
        out = np.where(notch & (d_ >= NOTCH_D) & (d_ < NOTCH_D + 0.5) & (h < E_T - 0.6),
                       np.where((np.mod(s_, 1.5) < 0.3) | (np.mod(h, 3.2) < 0.3), mullion, cglass), out)
        # the court's walls: hotel windows in rows
        cw = (dc_ > -0.6) & (dc_ <= 0) & (h >= 10.0) & (h < E_E - 0.6) & (z >= 0.9) & (z < 2.7) \
            & (np.mod(U_ + V_, 2.6) < 1.3)
        out = np.where(cw & body, win, out)
        return out.astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 3.0, b0 + E_T + 0.5, fn))

    # the shops' signs stacked up the corner pier, on both fronts
    signs = [P(c_) for c_ in ("#f2f0ea", "#c62a3b", "#2f7d52", "#f2f0ea", "#3b6f8f")]
    fk, sk = wall_frame(b, tE, inside, b0)
    for i, c_ in enumerate(signs):
        w0 = 11.0 + i * 2.0
        S.add(Box(fe, LN - CPIER + 0.3, LN - 0.3, -0.3, 0.6, w0, w0 + 1.4, c_, mode="paint", targets=[stone]))
        S.add(Box(fk, *sorted((sk * 0.3, sk * (CPIER - 0.3))), -0.3, 0.6, w0, w0 + 1.4, c_, mode="paint", targets=[stone]))

    # the lift tower over the roof, and the red letters over the corner
    ft = fe.at(35.0, 12.0)
    S.add(Box(ft, -4.0, 4.0, -4.5, 4.5, E_T - 1.0, E_T + 2.8, stone))
    S.add(Box(ft, -4.2, 4.2, -4.7, 4.7, E_T + 2.8, E_T + 3.1, inner))

    def letters(u, v, w):  # read from the square, so from the eastern end westwards
        c = np.clip(((u0 - u) / PX).astype(int), 0, SIGN.shape[1] - 1)
        r = np.clip(((E_T + SIGN.shape[0] * PX - w) / PX).astype(int), 0, SIGN.shape[0] - 1)
        return np.where(SIGN[r, c], red, 0).astype(np.uint16)
    PX, u0 = 0.55, LN - 2.4
    S.add(Box(fe, u0 - SIGN.shape[1] * PX, u0, 0.3, 1.1, E_T, E_T + SIGN.shape[0] * PX, letters))


BUILDERS = [("Corvin Palace", corvin), ("Europeum", europeum)]
