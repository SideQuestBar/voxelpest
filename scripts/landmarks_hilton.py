"""The Hilton Budapest on Castle Hill (Béla Pintér, 1976), between Matthias Church and the Fisherman's Bastion: the
restored late Baroque front of the Jesuit college on Hess András tér, the Gothic St Nicholas tower of the Dominican
church with its 1970s octagonal top, the nave of that church as an open court between the hotel's two blocks, and
round them the 1970s wings: deep faceted cream fins with strips of bronze reflecting glass between them, small slate
hoods over each strip and steep slate mansards. Built on the frame of the OSM outline (docs/landmarks.md).
"""
import math

import numpy as np
import shapely
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.geometry.polygon import orient

from landmarks import (TAU, WINDOW, Arch, Box, Ellipsoid, Field, Frame, Lathe, Poly, Roof, TBox, cone, cyl, pinnacle,
                       ring_segments, seg_frame)
from landmarks_city import base_under, dist_in, grid_of, statue
from landmarks_more import frame_fields, front_frame, largest, rect_poly, uv_of, wall_coord
from style import GLASS, METAL, ROOF

HILTON, NICHOLAS, DOMINICAN = 5647453, 379070846, 439377979  # the hotel, the tower, the church's ruins (not a building)
NAMES = ["Hilton Budapest"]

BAY, FIN, DG = 2.6, 1.4, 0.6           # the fins' rhythm and width, the glass strips' depth behind their fronts
EB, HR = 15.3, 8.2                     # the Baroque front's eaves and its roof's rise
MAIN = dict(GF=4.2, E=17.4, n=4, RS=4.8)   # the south block: shops, four storeys of fins, the mansard to its flat top
NORTH = dict(GF=4.0, E=13.0, n=3, RS=5.2)  # the lower north block
TS, TO, TT = 18.7, 27.5, 32.5          # the tower: the medieval square shaft, the octagon, the spire's tip
STEP = 4.75                            # the Baroque front's bays: fifteen, the entrance in the sixth from the tower


def drop_ids(osm):
    return {HILTON, NICHOLAS}


def ground_keep(osm):
    """the outline the ground model still counts as a building, as tall as OSM's four levels made it: without it the
    surface model's blur of the hotel's roofs read as open ground and lifted Hess András tér 6 m."""
    return [(g, 12) for oid, k, t, g in osm.areas if oid == HILTON]


def front(g, theta):
    """the frame of the hotel: origin on the corner of Hess András tér and Szentháromság tér, +u north along the
    Baroque front, +v east into the building."""
    f0 = front_frame(g, 0.0, (math.cos(theta), math.sin(theta)))
    eu, ev = uv_of(f0, g)
    k = int(np.argmin(eu + ev))
    return Frame(*f0.xy(eu[k], ev[k]), 0.0, f0.ang)


def convex_corners(g):
    c = np.array(orient(g, 1.0).exterior.coords)[:-1]
    pts = []
    for i in range(len(c)):
        a, p, b = c[i - 1], c[i], c[(i + 1) % len(c)]
        e1, e2 = p - a, b - p
        la, lb = np.hypot(*e1), np.hypot(*e2)
        if e1[0] * e2[1] - e1[1] * e2[0] > 0.5 * la * lb and min(la, lb) > 1.5:
            pts.append(p)
    return MultiPoint(pts)


def hilton(S, ctx, plan):
    P, area, g_at = ctx["P"], ctx["area"], ctx["ground_m"]
    g = largest(area[HILTON][3])
    tw = area[NICHOLAS][3]
    church = largest(area[DOMINICAN][3]) if DOMINICAN in area else None
    fr = front(g, ctx["theta"])
    eu, ev = uv_of(fr, g)
    tu, tv = uv_of(fr, tw)
    ut0, ut1, vt1 = float(tu.min()), float(tu.max()), float(tv.max())
    if church is not None:
        cu, cv = uv_of(fr, church)
        nave = cv < float(ev.max()) - 3
        u_n, u_cn = float(cu[nave].min()), float(cu[nave].max())      # the south block's north face, the nave's north wall
        west = (cu > u_n + 1) & (cu < ut0)
        VB = float(cv[west].min()) if west.any() else 12.0
    else:
        u_n, u_cn, VB = ut0 - 5.0, ut1 + 4.0, 12.0
    v_nw = float(ev[eu > ut1 + 1].min())                                # the north block's front, proud of the old one
    b0 = float(np.median([g_at(*fr.xy(u, -3.0)) for u in np.linspace(3, ut0 - 3, 12)]))
    gmin = min(base_under(ctx, g, 0.0, 3.0), min(g_at(x, y) for x, y in g.exterior.coords))
    zb = gmin - b0 - 2.0
    fb = Frame(fr.ox, fr.oy, b0, fr.ang)
    cols = [ut0 - STEP * (k + 0.47) for k in range(14, -1, -1)]
    ue = cols[-6]

    wall, pil, trim, shade = P("#e6e3da"), P("#f2f0ea"), P("#f6f4ee"), P("#d8d4c9")
    plinth, bwin, door_c = P("#cbc6ba"), P("#5d5149", WINDOW), P("#4b4036")
    tile, tile2 = P("#83695d", ROOF), P("#7a6155", ROOF)
    cream, cream2, finj = P("#e4dfcf"), P("#dcd6c4"), P("#cdc6b1")
    glassb, spand, shopg = P("#7e6048", WINDOW), P("#a6855e"), P("#62503e", WINDOW)
    slate, slate2, flatc = P("#5b4b4c", ROOF), P("#524345", ROOF), P("#8e8b85", ROOF)
    fascia, rub, rub2 = P("#5f5b56"), P("#b4a891"), P("#a2967f")
    st1, st2, relief = P("#bdb29c"), P("#ada28b"), P("#e8e3d5")
    oct_c, oct_g, spire_c, skyw = P("#e8e4d8"), P("#4f4743", WINDOW), P("#7d6152", ROOF), P("#363238", WINDOW)
    statue_c, grey, metal = P("#e6e1d6"), P("#6d6b68"), P("#c9ccce", METAL)

    # ---------------------------------------------------------------- the 1970s blocks, from the outline's distances
    baroque = rect_poly(fr, -3.0, ut1, -6.0, VB)
    low = rect_poly(fr, ut1 - 0.01, ut1 + 8.5, v_nw - 2.0, 4.5)        # the low wing beside the tower
    M = g.difference(baroque).difference(tw.buffer(0.05)).difference(low)
    x0f, y0f, X, Y = grid_of(g, 2.0)
    U, V = frame_fields(fr, X, Y)
    d = dist_in(M, X, Y)
    pts = shapely.points(X.ravel(), Y.ravel())
    dx = shapely.distance(g.exterior, pts).reshape(X.shape).astype(np.float32)
    dx = np.where(shapely.contains_xy(g, X, Y), dx, -dx)
    cd = shapely.distance(convex_corners(g), pts).reshape(X.shape).astype(np.float32)
    north = U >= u_n + 2.0
    zone = {k: np.where(north, NORTH[k], MAIN[k]).astype(np.float32) for k in ("GF", "E", "RS")}
    ST = np.where(north, (NORTH["E"] - NORTH["GF"]) / NORTH["n"], (MAIN["E"] - MAIN["GF"]) / MAIN["n"]).astype(np.float32)
    fields = dict(d=d, ext=(dx < d + 0.25).astype(np.float32), A=wall_coord(fr, dx, U, V), cd=cd, ST=ST, **zone)

    def fn(f, wa):
        d_, A_, cd_, ST_ = f["d"][None], f["A"][None], f["cd"][None], f["ST"][None]
        GF, E, RS = f["GF"][None], f["E"][None], f["RS"][None]
        ext = f["ext"][None] > 0
        h = wa - b0
        inside = d_ > 0
        a = np.mod(A_, BAY)
        c = np.abs(a - FIN / 2)
        depth = DG * np.clip((FIN / 2 - c) / (FIN / 2 - 0.2), 0, 1)              # pointed: a flat front, raking cheeks
        rec = np.where(ext, DG, 0.0)
        s = np.mod(h - GF, ST_)
        ground = (h >= 0) & (h < GF)
        upper = (h >= GF) & (h < E)
        open_gf = ext & ground & (d_ < DG + 0.6)
        core = inside & (d_ >= rec) & (h < E) & (h >= zb) & ~open_gf
        face = core & (d_ < rec + 0.5)
        out = np.where(core, cream, 0)
        out = np.where(face & ext & upper & (a >= FIN), np.where(s < 0.9, spand, glassb), out)
        out = np.where(face & ~ext & upper & (np.mod(A_, 3.2) >= 1.0) & (np.mod(A_, 3.2) < 2.2) & (s >= 0.9) & (s < 2.5),
                       glassb, out)
        out = np.where(core & ext & ground & (d_ < DG + 1.1), shopg, out)
        old = np.mod(np.floor(h / 0.7) + np.floor(A_ / 1.3 + 0.5 * np.floor(h / 0.7)), 3) == 0
        out = np.where(core & (h < 0), np.where(old, rub2, rub), out)
        out = np.where(open_gf & inside & (c < 0.3) & (np.abs(d_ - DG) < 0.35), cream, out)    # columns under the fins
        out = np.where(ext & inside & (h >= GF - 0.6) & (h < GF) & (d_ < DG + 0.6), fascia, out)   # the soffit band
        r = np.minimum(np.maximum(d_ - rec + 0.3, 0) * 2.75, RS)
        roof = inside & (h >= E) & (h < E + r)
        flat = roof & (r >= RS - 0.01) & (h >= E + RS - 0.5)
        out = np.where(roof, np.where(flat, flatc, np.where(np.mod(np.floor(h * 2), 3) == 0, slate2, slate)), out)
        sky = roof & ~flat & ext & (cd_ >= 2.0) & (np.abs(a - (FIN + BAY) / 2) < 0.45) & (h >= E + 2.0) & (h < E + 3.1)
        out = np.where(sky, skyw, out)                                            # a roof window over each strip
        fin = ext & inside & (h >= GF) & (h < E + 0.9) & (((a < FIN) & (d_ >= DG - depth)) | ((cd_ < 2.0) & (d_ < DG + 0.1)))
        out = np.where(fin, np.where((np.mod(h - GF, ST_) < 0.25) & (h < E), finj, np.where(c < 0.3, cream, cream2)), out)
        # a slate hood over the top of each glass strip, hanging forward and narrowing to a point
        ht = E + 0.7 - (DG + 0.4 - d_) * 1.1
        mid = np.abs(a - (FIN + BAY) / 2)
        hood = ext & (a >= FIN) & (cd_ >= 2.0) & (d_ >= -0.7) & (d_ < DG + 0.4) & (h < ht) & (h >= ht - 0.9) \
            & (mid < (BAY - FIN) / 2 * np.clip((h - E + 1.8) / 2.0, 0.25, 1.0) + 0.1)
        return np.where(hood, slate2, out).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 + zb, b0 + MAIN["E"] + MAIN["RS"] + 1.0, fn))
    top = MAIN["E"] + MAIN["RS"]
    S.add(Box(fb, 40.0, 51.0, 24.0, 31.0, top - 0.5, top + 2.8, P("#b7b4ac")))   # plant rooms on the flat roof
    S.add(Box(fb, 57.0, 62.5, 33.0, 38.5, top - 0.5, top + 3.6, grey))
    holes = [Polygon(r) for r in g.interiors]
    if holes:  # the courtyard: paved at the street's level, a glass roof light along its south side
        hu_, hv_ = uv_of(fr, holes[0])
        S.add(Poly(holes[0], b0 + zb, b0, P("#b9b4aa")))
        S.add(Box(fb, float(hu_.min()) - 5.0, float(hu_.min()) - 2.0, float(hv_.min()) + 1.0, float(hv_.max()) - 1.0,
                  top - 0.5, top + 0.5, P("#86b3a9", GLASS)))

    # ---------------------------------------------------------------- the Baroque front on Hess András tér
    S.add(Box(fb, -0.4, ut0, 0.0, VB, zb, EB, wall))
    S.add(Box(fb, -0.4, ut0, -0.1, 0.4, zb, 0.9, plinth, mode="paint", targets=[wall]))
    S.add(Box(fb, -0.5, ut0, -0.5, 0.0, 12.2, 12.7, trim))                      # the entablature over the capitals
    S.add(Box(fb, -0.9, ut0, -0.5, 0.0, 14.3, 14.8, trim))                      # the cornice
    S.add(Box(fb, -1.2, ut0, -1.0, 0.0, 14.8, EB, trim))
    fs = Frame(*fb.xy(-0.4, VB), b0, fb.ang - math.pi / 2)                       # the end on Szentháromság tér
    S.add(Box(fs, 0.0, VB + 0.4, -0.5, 0.0, 12.2, 12.7, trim))
    S.add(Box(fs, 0.0, VB + 1.2, -1.0, 0.0, 14.3, EB, trim))
    canopy = (ue - 6.6, ue + 6.6)

    def window(fw, u, w0, w1, hw=0.62):
        fi = fw.at(u, 0, 0, math.pi / 2)
        S.add(Box(fi, -0.1, 0.4, -hw - 0.25, hw + 0.25, w0 - 0.25, w1 + 0.25, trim, mode="paint", targets=[wall]))
        S.add(Box(fi, -0.1, 0.4, -hw, hw, w0, w1, bwin, mode="paint", targets=[wall, trim]))

    def swag(fw, u, w0):  # a carved garland, hung between two rosettes
        fi = fw.at(u, 0, 0, math.pi / 2)
        S.add(Box(fi, -0.1, 0.4, -0.9, 0.9, w0, w0 + 0.7, lambda uu, vv, ww: np.where(
            np.abs(ww - w0 - 0.15 - 0.35 * (vv / 0.9) ** 2) < 0.2, shade, 0).astype(np.uint16), mode="paint", targets=[wall]))

    def bay(fw, u, ground=True):
        if ground:
            window(fw, u, 1.1, 3.4, 0.7)
        window(fw, u, 6.0, 7.6)
        fi = fw.at(u, 0, 0, math.pi / 2)
        S.add(Box(fi, -0.5, 0.0, -0.95, 0.95, 5.6, 6.0, trim))                # the sill
        S.add(Box(fi, -0.5, 0.0, -1.05, 1.05, 7.75, 8.1, trim))
        S.add(Roof(fi, -0.5, 0.0, -1.1, 1.1, 8.1, 0.8, trim))                  # the pediment
        window(fw, u, 9.4, 10.9)
        swag(fw, u, 11.0)
        window(fw, u, 12.9, 14.1, 0.6)

    def pilaster(fw, u, hw=0.7):
        S.add(Box(fw, u - hw - 0.15, u + hw + 0.15, -0.6, 0.0, zb, 0.9, plinth))
        S.add(Box(fw, u - hw, u + hw, -0.5, 0.0, 0.9, 11.2, pil))
        S.add(Box(fw, u - hw - 0.25, u + hw + 0.25, -0.75, 0.0, 11.2, 12.2, trim))
        S.add(Ellipsoid(fw.at(u - hw, -0.55, 11.9), 0.35, 0.3, 0.35, trim))       # the capital's volutes
        S.add(Ellipsoid(fw.at(u + hw, -0.55, 11.9), 0.35, 0.3, 0.35, trim))
        S.add(Box(fw, u - hw + 0.1, u + hw - 0.1, -0.1, 0.4, 12.9, 14.0, shade, mode="paint", targets=[wall]))

    for u in cols:
        bay(fb, u, ground=not canopy[0] < u < canopy[1])
    for u in [cols[0] - STEP / 2] + [(a_ + b_) / 2 for a_, b_ in zip(cols[:-1], cols[1:])]:
        pilaster(fb, u)
    pilaster(fb, 0.3)
    pilaster(fs, VB - 0.3)
    pilaster(fs, 0.7)
    pilaster(fs, VB / 2)
    for u in (VB / 4 + 0.2, 3 * VB / 4 - 0.2):
        bay(fs, u)
    # the north end's raised attic, its garland and statues, against the tower
    ra = cols[-2] - STEP / 2 if len(cols) > 2 else ut0 - 8.0
    S.add(Box(fb, ra, ut0, -0.5, 1.5, EB - 0.5, EB + 2.6, wall))
    S.add(Box(fb, ra - 0.3, ut0, -0.8, 1.8, EB + 2.6, EB + 3.0, trim))
    for k in range(3):
        swag(fb, ra + (ut0 - ra) * (k + 0.5) / 3, EB + 1.0)
        statue(S, fb.at(ra + (ut0 - ra) * (k + 0.5) / 3, 0.4), EB + 3.0, statue_c, 0.95)
    # the roof: steep tiles, hipped over Szentháromság tér, butting the tower in the north
    wr = VB + 1.0

    def tiles(u, v, w):
        return np.where(np.mod(np.floor(w * 2.2), 2) == 0, tile, tile2).astype(np.uint16)
    S.add(Roof(fb, -1.1, -1.1 + wr, -0.7, VB + 0.3, EB, HR, tiles, hip=True))
    S.add(Roof(fb, -1.1 + wr / 2, ut0, -0.7, VB + 0.3, EB, HR, tiles))
    # the entrance: three doors under a flat dark canopy with the name on it
    for k in (-1, 0, 1):
        S.add(Box(fb, ue + STEP * k - 0.9, ue + STEP * k + 0.9, -0.1, 0.4, 0.0, 3.2, door_c, mode="paint", targets=[wall, plinth]))
    S.add(Box(fb, canopy[0], canopy[1], -5.6, 0.0, 4.3, 4.85, P("#45484b", METAL)))
    for k in range(6):  # Hilton
        S.add(Box(fb, ue - 2.4 + k * 0.85, ue - 1.85 + k * 0.85, -5.2, -4.7, 4.85, 5.65, metal))

    # ---------------------------------------------------------------- the St Nicholas tower
    hu, hv = (ut1 - ut0) / 2, vt1 / 2
    ft = Frame(*fr.xy((ut0 + ut1) / 2, hv), b0, fr.ang)

    def ashlar(u, v, w):  # rough coursed stone, blocks of two shades at random
        row = np.floor(w / 0.6)
        blk = np.floor((u + v) / 1.2 + 0.5 * row)
        return np.where(np.mod(blk * 7 + row * 13 + np.floor(u - v) * 3, 5) < 2, st2, st1).astype(np.uint16)
    S.add(Box(ft, -hu, hu, -hv, hv, zb, TS, ashlar))
    for k in range(4):
        fk = ft.at(turn=k * math.pi / 2)
        r = hu if k % 2 == 0 else hv
        for w0 in ((13.0,) if k == 3 else (7.5, 13.0)):
            S.add(Arch(fk, r - 0.6, r + 0.1, 0, 0.55, w0, w0 + 2.6, P("#3b3733"), pointed=True, mode="paint", targets=[st1, st2]))
    fw_ = ft.at(turn=3 * math.pi / 2)  # the King Matthias memorial on the west face
    S.add(Box(fw_, hv - 0.1, hv + 0.5, -1.7, 1.7, 1.6, 7.0, relief))
    S.add(Roof(fw_.at(hv + 0.2, 0, 0, 0), -0.3, 0.3, -1.9, 1.9, 7.0, 1.2, relief))
    S.add(Box(fw_, hv + 0.2, hv + 0.6, -1.1, 1.1, 2.4, 6.2, P("#d6cfbd"), mode="paint", targets=[relief]))
    S.add(Box(ft, -hu - 0.3, hu + 0.3, -hv - 0.3, hv + 0.3, TS - 0.6, TS, st2))
    S.add(TBox(ft, hu, hv, 3.75, 3.75, TS, TS + 1.0, spire_c))                     # the skirt round the octagon
    S.add(Lathe(ft, TS, TO, cyl(3.7), oct_c, n=8))
    for k in range(8):  # tall slits of reflecting glass, one in each face
        S.add(Box(ft.at(turn=TAU * k / 8), 3.2, 3.9, -0.45, 0.45, TS + 1.4, TO - 0.9, oct_g, mode="paint", targets=[oct_c]))
    for su, sv in ((1, -1), (1, 1), (-1, -1)):
        pinnacle(S, ft.at(su * (hu - 0.6), sv * (hv - 0.6)), TS - 1.0, 7.2, 0.75, oct_c)
    fc = ft.at(-(hu - 0.9), hv - 0.9)                                            # the turret on the south-east corner
    S.add(Lathe(fc, TS - 1.0, TS + 3.2, cyl(0.9), oct_c, n=8))
    S.add(Lathe(fc, TS + 3.2, TS + 5.6, cone(1.05, 0.06), spire_c, n=8))
    S.add(Lathe(ft, TO, TT, lambda t: 4.4 * (1 - t) ** 1.12 + 0.08, spire_c, n=8))
    S.line(ft, (0, 0, TT - 0.3), (0, 0, TT + 1.3), grey)
    S.add(Ellipsoid(ft.at(0, 0, TT + 0.6), 0.3, 0.3, 0.3, grey))

    # ---------------------------------------------------------------- the low wing beside the tower, its flags
    S.add(Box(fb, ut1, ut1 + 8.5, v_nw, 4.5, zb, 8.6, cream))
    S.add(Box(fb, ut1, ut1 + 8.5, v_nw - 0.1, v_nw + 0.4, 0.0, 3.8, shopg, mode="paint", targets=[cream]))
    S.add(Box(fb, ut1, ut1 + 8.5, v_nw - 0.1, v_nw + 0.4, 3.8, 4.4, fascia, mode="paint", targets=[cream]))
    S.add(Roof(fb, ut1 - 0.4, ut1 + 8.9, v_nw - 0.5, 4.9, 8.6, 3.6, slate, hip=True))
    flags = [("#c4423a", "#efede6", "#3f7d4a"), ("#2e4f9e",) * 3, ("#c4423a", "#e3c35a", "#2e5fa6"), ("#26365e",) * 3]
    for i, cl in enumerate(flags):
        x, y = fr.xy(ut1 + 1.5 + 1.9 * i, v_nw - 2.0)
        fp = Frame(x, y, g_at(x, y), fr.ang)
        S.line(fp, (0, 0, 0), (0, 0, 9.0), grey)
        for j, col in enumerate(cl):
            S.add(Box(fp, 0.15 + 0.4 * j, 0.55 + 0.4 * j, -0.2, 0.3, 5.6, 8.6, P(col)))

    # ---------------------------------------------------------------- the Dominican church: its open nave, the ruins
    if church is not None:
        vs, ve = vt1, float(ev[eu > u_cn + 1].max()) if (eu > u_cn + 1).any() else 34.0
        vn = min(ve, float(np.max(cv[nave & (cu > u_cn - 1)]))) - 0.5
        xm, ym = fr.xy(u_cn, (vs + vn) / 2)
        fn_ = Frame(*fr.xy(u_cn, 0), g_at(xm, ym), fr.ang)

        def ruin(u, v, w):  # the nave's north wall, broken off unevenly
            top_ = 6.8 - 1.8 * np.abs(np.sin(v * 0.42)) - 1.6 * (v > vs + 0.62 * (vn - vs))
            return np.where(w < top_, np.where(np.mod(np.floor(w / 0.5) + np.floor(v / 0.9), 3) == 0, rub2, rub), 0).astype(np.uint16)
        S.add(Box(fn_, -0.6, 0.6, vs, vn, -3.0, 7.0, ruin))
        for k in range(3):
            S.add(Arch(fn_.at(0, vs + (vn - vs) * (k + 0.5) / 3, 0, 0), -0.8, 0.8, 0, 0.75, 1.5, 3.8, pointed=True, mode="carve"))
        for a_, b_, n_ in ring_segments(church, 1.0):
            mid = (a_ + b_) / 2
            if g.distance(Point(*mid)) < 0.6:
                continue
            fw2 = seg_frame(a_, b_, n_, g_at(*mid))
            L = float(np.hypot(*(b_ - a_)))
            S.add(Box(fw2, 0, L, -0.3, 0.8, -2.0, 2.0 + 1.2 * (int(L * 7) % 2), lambda u, v, w: np.where(
                np.mod(np.floor(w / 0.5) + np.floor(u / 0.9), 3) == 0, rub2, rub).astype(np.uint16)))


BUILDERS = [("Hilton Budapest", hilton)]
