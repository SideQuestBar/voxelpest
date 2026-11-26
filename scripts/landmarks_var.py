"""Late November 2026, fifth round, the Castle Hill and the Danube front below it: the Royal Palace's copper roofs and
pavilions, the Várkert Bazár, the funicular and the tunnel's portal, the Mary Magdalene Tower, the entrance of the
Hospital in the Rock and the Cave Church on Gellért Hill. Outlines from OSM; heights, colours and details from the Esri
aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np
import shapely

from landmarks import WINDOW, Arch, Box, Frame, Lathe, Roof, Slab, cone, cyl, dome, rect_of
from landmarks_city import base_under
from landmarks_hosok import keep
from landmarks_kit import largest, painted, styled
from style import CONCRETE, METAL, ROOF, GLASS

TAU = 2 * math.pi
PALACE = 6486918
PAVILIONS = ((4013, 3060), (4058, 3066), (4091, 3034), (4091, 3066), (4013, 3156), (4058, 3160), (4091, 3160),
             (4091, 3189), (4124, 3189))  # the palace's corner pavilions, from the aerial
VK_ROWS = ((429676478, 9.0), (375466378, 9.0), (375466379, 11.0), (250256594, 10.0))
VK_STAIR, VK_GUARDS, VK_SOUTH, VK_FOUNDRY = 429676480, 6392859, 250256590, 429676509
SIKLO_TOP, SIKLO_BOTTOM = (4181.0, 2891.0), (4256.0, 2926.0)
SIKLO_UPPER, SIKLO_LOWER = 33300733, 347623537
PORTAL = 293068538
MAGDOLNA, MAGDOLNA_TOWER, MAGDOLNA_NAVE, MAGDOLNA_RUIN = 250071203, 258354256, 1554003553, 1234562712
HOSPITAL = (4027.0, 2495.0)
PAULINE = 463920374

NAMES = ["Royal Palace roofs", "Várkert Bazár", "Castle Hill Funicular", "Tunnel portal", "Mary Magdalene Tower",
         "Hospital in the Rock", "Cave Church"]
DROP = {*(i for i, _ in VK_ROWS), VK_STAIR, VK_GUARDS, VK_SOUTH, VK_FOUNDRY, SIKLO_UPPER, SIKLO_LOWER, PORTAL,
        MAGDOLNA, MAGDOLNA_TOWER, MAGDOLNA_NAVE, PAULINE}
KEEP = [(VK_GUARDS, 16), (VK_SOUTH, 16), (375466379, 11), (MAGDOLNA, 20), (PAULINE, 14)]


def area(ctx, oid):
    try:
        return largest(keep(ctx, oid))
    except KeyError:
        return None


def stone_wall(P, a="#d9cfb8", b="#c9bea5"):
    ca, cb = P(a), P(b)

    def f(u, v, w):
        return np.where(np.mod(np.floor(w / 0.5) + np.floor((u + v) / 1.2), 4) == 0, cb, ca).astype(np.uint16)
    return f, (ca, cb)


# ------------------------------------------------------------------------------------------------ the palace
def palace(S, ctx, plan):
    """the Royal Palace's roofs (Alajos Hauszmann's, 1912, as rebuilt after 1945): copper hips over every wing, the
    glazed roofs of the National Gallery's halls between them, and the corner pavilions' copper caps."""
    P = ctx["P"]
    g = area(ctx, PALACE)
    f = ctx["feats"].get(str(PALACE))
    if g is None or f is None:
        return
    b0, E = f["base"], f["E"]
    cu, cu2, glass, frame = P("#5f9a86", ROOF), P("#6eab95", ROOF), P("#4b5559", GLASS), P("#8b9496", METAL)
    from osm import to_grid
    drum = shapely.Point(*to_grid(19.03968, 47.49614)).buffer(15.0)  # castle_dome's drum
    gr = g.difference(drum)
    top = 7.0

    def carve(f_, hw):
        return np.where((f_["d"] > 0) & (hw >= 0.0), 1, 0)

    def fn(f_, hw):
        d = f_["d"]
        inside = d > 0
        roof = np.minimum(d * 0.9, top)
        court = d > 11.0
        z = np.where(court, 2.0, roof)
        col = np.where(court, np.where(np.mod(f_["s"], 4.0) < 0.4, frame, glass),
                       np.where(np.mod(np.floor(f_["s"] / 1.5), 2) == 0, cu, cu2))
        return np.where(inside & (hw >= 0.0) & (hw < z + 0.5) & (hw >= z - 0.6), col, 0)
    Sx = painted(S, gr, b0 + E, top + 6.0, carve, lower=0.4)
    Sx.mode = "carve"
    painted(S, gr, b0 + E, top + 1.0, fn, lower=-0.6)
    for x, y in PAVILIONS:
        fp = Frame(x, y, b0 + E, 0.0)
        S.add(Box(fp, -6.0, 6.0, -6.0, 6.0, -0.6, 1.2, cu2))
        S.add(Lathe(fp, 1.2, 7.5, dome(6.4, 1.4, 1.0), cu, n=4, rot=math.pi / 4))
        S.add(Lathe(fp, 7.5, 9.5, cone(1.0, 0.15), cu2, n=4, rot=math.pi / 4))


# ------------------------------------------------------------------------------------------------ the Várkert Bazár
def varkert(S, ctx, plan):
    """the Várkert Bazár (Miklós Ybl, 1875-83, restored 2014): a neo-Renaissance promenade of arcades along the river
    under the palace's garden, cream with white pilasters, its terraces behind stone balustrades; the Gloriette and its
    ramps in the middle, the stair pavilion with its glazed dome at the north end, the Guards' Palace and the southern
    palaces at the ends under grey roofs."""
    P = ctx["P"]
    cream, white, dark, slate, tile = P("#e8d9b4"), P("#f2ede0"), P("#4a4238"), P("#767a7c", ROOF), P("#9c5a3c", ROOF)
    win, glass, cu = P("#3b3f44", WINDOW), P("#8fb3bf", GLASS), P("#5f9a86", ROOF)

    def arcade(E):
        def fn(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 1.0)
            bay = np.abs(np.mod(s, 4.6) - 2.3)
            arch = (hw < 4.2 - 0.06 * bay ** 2 * 4) & (bay < 1.7) & (hw > 0)
            loggia = (hw > 5.4) & (hw < E - 1.6) & (bay < 1.3)
            wall = np.where(bay > 1.95, white, cream)
            wall = np.where((np.abs(hw - 4.9) < 0.3) | (np.abs(hw - (E - 1.2)) < 0.25), white, wall)
            o = np.where(edge & (hw < E), np.where(arch, dark, np.where(loggia, win, wall)), 0)
            o = np.where(inside & ~edge & (hw >= E - 0.6) & (hw < E), P("#cfc6b2", CONCRETE), o)
            bal = edge & (hw >= E) & (hw < E + 1.0) & ((np.mod(s, 0.8) < 0.4) | (hw >= E + 0.7))
            return np.where(bal, white, o)
        return fn
    for oid, E in VK_ROWS:
        g = area(ctx, oid)
        if g is not None:
            painted(S, g, base_under(ctx, g, 0.2), E + 1.2, arcade(E))
    g = area(ctx, VK_STAIR)
    if g is not None:
        b0 = base_under(ctx, g, 0.2)
        painted(S, g, b0, 13.2, arcade(12.0))
        cx, cy, L, W, ang = rect_of(g)
        fr = Frame(cx, cy, b0 + 12.0, ang)
        S.add(Lathe(fr, 0.0, 1.6, cyl(W * 0.36), cream, n=16))
        S.add(Lathe(fr, 1.6, 6.0, dome(W * 0.36, 2.0, 0.8), lambda u, v, w: np.where(
            np.mod(np.arctan2(v, u), TAU / 16) < 0.06, cu, glass).astype(np.uint16), n=16))
        S.add(Lathe(fr, 6.0, 7.4, cyl(0.9), cu, n=8))
    for oid, E, roof in ((VK_GUARDS, 13.0, slate), (VK_SOUTH, 14.0, slate), (VK_FOUNDRY, 6.0, tile)):
        g = area(ctx, oid)
        if g is not None:
            styled(S, g, base_under(ctx, g, 0.3), E, cream, win, roof, floor=4.2, gf=5.0, bay=3.8, winw=1.5, sill=1.0,
                   head=3.4, roof_kind="hip", slope=0.8, ridge=4.0, band=white, base=white)


# ------------------------------------------------------------------------------------------------ the funicular
def siklo(S, ctx, plan):
    """the Castle Hill Funicular (1870, rebuilt 1986): 95 m of track climbing 51 m from Clark Ádám tér to the palace,
    on a stone viaduct of stepped arches, its two cars (Margit and Gellért) in maroon and cream with their stepped
    compartments, the footbridge over the track halfway up; the green-roofed upper station by the Sándor Palace and
    the small lower station by the tunnel."""
    P = ctx["P"]
    stone, stone2 = P("#cbbfa6"), P("#b5a98f")
    rail, maroon, creamc, win = P("#3d3a37", METAL), P("#7c2a2a"), P("#efe4c8"), P("#2f3a40", WINDOW)
    green, iron, slate = P("#4f7a5f", ROOF), P("#3f4b45", METAL), P("#6f7477", ROOF)
    gm = ctx["ground_m"]
    (ax, ay), (bx, by) = SIKLO_TOP, SIKLO_BOTTOM
    Lh = math.hypot(bx - ax, by - ay)
    ang = math.atan2(by - ay, bx - ax)
    za, zb = gm(ax, ay) + 0.4, gm(bx, by) + 0.4
    fr = Frame(ax, ay, za, ang)

    def zf(u):
        return (zb - za) * np.clip(np.asarray(u, float) / Lh, 0, 1)
    lo = min(gm(*fr.xy(u, 0)) for u in np.linspace(0, Lh, 20)) - za - 2.0

    def viaduct(u, v, w):
        z = zf(u)
        step = np.mod(u, 7.0)
        arch = (np.abs(step - 3.5) < 2.4) & (w < z - 1.2 - 0.3 * np.abs(step - 3.5) ** 2) & (np.abs(v) > 2.2)
        return np.where(arch, 0, np.where(np.mod(np.floor(w / 0.5), 3) == 0, stone2, stone)).astype(np.uint16)
    S.add(Slab(fr, 0, Lh, -2.8, 2.8, zf, lo, -0.1, viaduct, mode="under"))
    S.add(Slab(fr, 0, Lh, -2.8, 2.8, zf, -0.6, -0.1, stone))
    for v in (-1.7, -0.7, 0.7, 1.7):
        S.add(Slab(fr, 0, Lh, v - 0.12, v + 0.12, zf, -0.1, 0.3, rail))
    for sv in (-1, 1):
        S.add(Slab(fr, 0, Lh, sv * 2.8 - 0.3, sv * 2.8 + 0.3, zf, -0.1, 1.0, stone2))
    for uc, vc in ((Lh * 0.18, -1.2), (Lh * 0.82, 1.2)):
        for k in range(3):  # three stepped compartments
            u0 = uc - 4.5 + k * 3.0
            z0 = float(zf(u0 + 1.5))
            fc = fr.at(u0 + 1.5, vc)
            fc = Frame(fc.ox, fc.oy, za + z0, ang)
            S.add(Box(fc, -1.5, 1.5, -1.1, 1.1, 0.3, 1.2, maroon))
            S.add(Box(fc, -1.5, 1.5, -1.1, 1.1, 1.2, 2.6, lambda u, v, w: np.where(
                (np.abs(np.mod(u, 1.5) - 0.75) < 0.5) & (w > 1.5) & (w < 2.3), win, creamc).astype(np.uint16)))
            S.add(Box(fc, -1.6, 1.6, -1.2, 1.2, 2.6, 2.9, maroon))
    um = Lh * 0.5  # the footbridge over the track
    zm = za + float(zf(um))
    fb = Frame(*fr.xy(um, 0), zm + 6.0, ang + math.pi / 2)
    S.add(Box(fb, -8.0, 8.0, -1.2, 1.2, 0.0, 0.4, iron))
    for sv in (-1, 1):
        for k in range(17):
            S.add(Box(fb, -8.0 + k, -7.85 + k, sv * 1.2 - 0.1, sv * 1.2 + 0.1, 0.4, 1.4, iron))
        S.add(Box(fb, -8.0, 8.0, sv * 1.2 - 0.1, sv * 1.2 + 0.1, 1.3, 1.5, iron))
    g = area(ctx, SIKLO_UPPER)
    if g is not None:
        c = g.centroid
        b0 = base_under(ctx, g, 0.5)
        fu = Frame(c.x, c.y, b0, ang)
        wall, _ = stone_wall(P, "#e9e0c9", "#ddd2b8")
        S.add(Lathe(fu, -1.0, 4.5, cyl(6.6), wall, n=8, rot=math.pi / 8))
        for k in range(8):
            S.add(Arch(fu.at(turn=k * TAU / 8 + math.pi / 8 + TAU / 16), 5.4, 7.0, 0, 1.1, 0.6, 2.8, win, mode="paint",
                       targets=list(_)))
        S.add(Lathe(fu, 4.5, 5.0, cyl(7.0), creamc, n=8, rot=math.pi / 8))
        S.add(Lathe(fu, 5.0, 8.0, dome(6.8, 1.2, 1.2), green, n=8, rot=math.pi / 8))
    fl = Frame(bx, by, gm(bx, by), ang)
    S.add(Box(fl, -2.0, 8.0, -5.0, 5.0, -1.0, 4.6, lambda u, v, w: np.where(
        (np.abs(np.mod(u, 2.5) - 1.25) < 0.55) & (w > 0.9) & (w < 3.4), win, creamc).astype(np.uint16)))
    S.add(Roof(fl, -2.4, 8.4, -5.4, 5.4, 4.6, 2.4, slate, hip=True))


# ------------------------------------------------------------------------------------------------ the tunnel portal
def portal(S, ctx, plan):
    """the tunnel's east portal on Clark Ádám tér (Adam Clark, 1857): a classical front in sandstone, the arched mouth
    between pairs of Doric columns under an entablature and a low attic, the hill's green behind it."""
    P = ctx["P"]
    g = area(ctx, PORTAL)
    if g is None:
        return
    cx, cy, L, W, ang = rect_of(g)
    b0 = base_under(ctx, g, 0.1)
    out = np.array([4290.0 - cx, 2900.0 - cy])  # the square lies east of it
    n = np.array([-math.sin(ang), math.cos(ang)])
    if out @ n < 0:
        ang += math.pi
    fr = Frame(cx, cy, b0, ang)
    wall, tg = stone_wall(P, "#d8c9a6", "#c8b893")
    pale, dark = P("#e7dcc2"), P("#2a2826")
    hv = W / 2
    S.add(Box(fr, -L / 2, L / 2, -hv, hv, -1.0, 13.5, wall))
    S.add(Box(fr, -L / 2 - 0.3, L / 2 + 0.3, hv - 0.6, hv + 0.4, 10.2, 11.6, pale))
    S.add(Box(fr, -L / 2, L / 2, hv - 0.4, hv + 0.2, 11.6, 14.4, wall))
    for su in (-1, 1):
        for k in (0, 1):
            fc = fr.at(su * (6.6 + 2.0 * k), hv + 0.6)
            S.add(Lathe(fc, 0.0, 10.2, cone(0.75, 0.6), pale, n=16))
            S.add(Box(fc, -0.9, 0.9, -0.9, 0.9, 9.8, 10.2, pale))
    S.add(Arch(fr.at(turn=math.pi / 2), -hv - 1.0, hv + 1.0, 0, 4.6, 0.0, 5.0, mode="carve"))
    S.add(Arch(fr.at(0, -hv + 0.5).at(turn=math.pi / 2), -0.5, 0.5, 0, 4.6, 0.0, 5.0, dark))
    S.add(Arch(fr.at(0, hv + 0.2).at(turn=math.pi / 2), -0.4, 0.4, 0, 5.2, 0.0, 5.0, pale, mode="under"))


# ------------------------------------------------------------------------------------------------ Mary Magdalene
def magdolna(S, ctx, plan):
    """the Mary Magdalene Tower: all that the war left of the Castle's 13th-century parish church, a Gothic tower of
    pale stone 50 m tall, a clock under its belfry, a steep copper roof and spire; behind it on the ruined nave's
    low walls the one rebuilt Gothic window standing alone."""
    P = ctx["P"]
    g = area(ctx, MAGDOLNA_TOWER)
    if g is None:
        return
    cx, cy, L, W, ang = rect_of(g)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(cx, cy, b0, ang)
    wall, tg = stone_wall(P, "#ddd3bd", "#cbc0a7")
    cu, cu2, gold, dark, clock = P("#5f9a86", ROOF), P("#4f8875", ROOF), P("#d4ad55", METAL), P("#343434", WINDOW), P("#f1ede2")
    h = min(L, W) / 2
    S.add(Box(fr, -h, h, -h, h, -2.0, 36.0, wall))
    for k in range(4):
        fk = fr.at(turn=k * math.pi / 2)
        for z0, z1, a in ((8.0, 12.0, 0.6), (17.0, 21.0, 0.6), (29.5, 33.5, 1.0)):
            S.add(Arch(fk.at(turn=math.pi / 2), h - 0.4, h + 0.1, 0, a, z0, z1 - a * 1.7, dark, pointed=True,
                       mode="paint", targets=list(tg)))
        S.add(Box(fk, h - 0.1, h + 0.15, -1.2, 1.2, 24.6, 27.0, clock))
        S.add(Box(fk, h + 0.15, h + 0.3, -0.1, 0.1, 25.2, 26.6, dark))
        S.add(Box(fk, -h - 0.4, -h + 0.6, -h - 0.4, -h + 0.6, -2.0, 30.0, wall))
    S.add(Box(fr, -h - 0.4, h + 0.4, -h - 0.4, h + 0.4, 35.6, 36.4, P("#e9e1cd")))
    S.add(Lathe(fr, 36.4, 48.5, cone(h * 1.3, 0.3), lambda u, v, w: np.where(
        np.mod(np.floor(w / 1.0), 2) == 0, cu, cu2).astype(np.uint16), n=4, rot=math.pi / 4))
    S.add(Box(fr, -0.1, 0.1, -0.1, 0.1, 48.5, 50.5, gold))
    S.add(Box(fr, -0.6, 0.6, -0.1, 0.1, 49.6, 49.8, gold))
    nave = area(ctx, MAGDOLNA)
    if nave is not None:
        rest = nave.difference(g.buffer(0.3))
        if rest.area > 20:
            styled(S, largest(rest) if rest.geom_type != "Polygon" else rest, b0, 9.0, P("#ddd3bd"), dark,
                   P("#a65a3e", ROOF), floor=4.5, bay=3.5, winw=1.2, roof_kind="hip", slope=0.9, ridge=4.0)
    ruin = area(ctx, MAGDOLNA_RUIN)
    if ruin is not None:
        rb = base_under(ctx, ruin, 0.3)

        def low(f, hw):
            return np.where((f["d"] > 0) & (f["d"] < 1.0) & (hw < 1.0), tg[1], 0)
        painted(S, ruin, rb, 1.2, low)
        rx, ry, rL, rW, ra = rect_of(ruin)
        far = max(((rx + math.cos(ra) * rL / 2 * s_, ry + math.sin(ra) * rL / 2 * s_) for s_ in (-1, 1)),
                  key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
        out = 1.0 if (far[0] - rx) * math.cos(ra) + (far[1] - ry) * math.sin(ra) > 0 else -1.0
        fw = Frame(far[0] - out * 1.5 * math.cos(ra), far[1] - out * 1.5 * math.sin(ra), rb, ra)
        S.add(Box(fw, -0.6, 0.6, -3.2, 3.2, 0.0, 13.0, wall))
        S.add(Arch(fw, -0.7, 0.7, 0, 1.9, 2.5, 9.0, 0, pointed=True, mode="carve"))
        S.add(Box(fw, -0.15, 0.15, -0.12, 0.12, 2.5, 11.8, tg[0]))
        S.add(Box(fw, -0.15, 0.15, -1.9, 1.9, 7.0, 7.2, tg[0]))


# ------------------------------------------------------------------------------------------------ Hospital in the Rock
def hospital(S, ctx, plan):
    """the Hospital in the Rock (1944, and the Cold War's nuclear bunker): the caves under the Castle are out of sight,
    their way in on Lovas út a concrete portal in the rock with its steel door."""
    P = ctx["P"]
    x, y = HOSPITAL
    b0 = ctx["ground_m"](x, y)
    conc, steel = P("#b9b5ac", CONCRETE), P("#4b524f", METAL)
    fr = Frame(x, y, b0, math.radians(0))
    S.add(Box(fr, -3.5, 3.5, -1.0, 1.0, -0.5, 4.2, conc))
    S.add(Box(fr, -1.4, 1.4, 1.0, 1.15, 0.0, 2.6, steel))
    S.add(Box(fr, -3.8, 3.8, -1.2, 1.6, 4.2, 4.6, conc))


# ------------------------------------------------------------------------------------------------ the Cave Church
def cave(S, ctx, plan):
    """the Cave Church in Gellért Hill (1926) and the Pauline monastery built onto the rock beside it (1932): the
    monastery a neo-Gothic range of pale stone under a dark roof, its slender tower with a pointed spire at the north
    end; the church's mouth a rough stone portal in the cliff, a white cross on the rock above."""
    P = ctx["P"]
    g = area(ctx, PAULINE)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    wall, tg = stone_wall(P, "#ddd5c3", "#cdc4ae")
    pale, dark, slate, white, cu = P("#e8e1d0"), P("#2c2b29", WINDOW), P("#5c6063", ROOF), P("#f4f2ec"), P("#5f9a86", ROOF)
    styled(S, g, b0, 12.0, tg[0], dark, slate, floor=3.6, gf=4.2, bay=3.0, winw=1.0, sill=1.0, head=3.0,
           roof_kind="hip", slope=1.2, ridge=5.0, band=tg[1])
    cx, cy, L, W, ang = rect_of(g)
    pts = np.array(g.exterior.coords)
    north = pts[np.argmin(pts[:, 1])]
    ft = Frame(north[0] + 3.0, north[1] + 3.0, base_under(ctx, g, 0.6), 0.0)
    S.add(Lathe(ft, -1.0, 20.0, cyl(2.6), wall, n=8, rot=math.pi / 8))
    for k in range(8):
        S.add(Arch(ft.at(turn=k * TAU / 8 + math.pi / 8 + TAU / 16), 2.0, 2.9, 0, 0.5, 15.5, 17.5, dark, pointed=True,
                   mode="paint", targets=list(tg)))
    S.add(Lathe(ft, 20.0, 20.6, cyl(2.9), pale, n=8, rot=math.pi / 8))
    S.add(Lathe(ft, 20.6, 29.0, cone(2.6, 0.15), cu, n=8, rot=math.pi / 8))
    S.add(Box(ft, -0.08, 0.08, -0.08, 0.08, 29.0, 30.6, P("#d4ad55", METAL)))
    south = pts[np.argmax(pts[:, 1])]
    fp = Frame(south[0], south[1] + 8.0, ctx["ground_m"](south[0], south[1] + 8.0), math.radians(-90))
    rock = P("#bdb39f")
    S.add(Box(fp, -1.5, 1.5, -5.0, 5.0, -0.5, 7.5, rock))
    S.add(Arch(fp, -1.6, 1.6, 0, 1.8, 0.0, 3.2, 0, pointed=True, mode="carve"))
    S.add(Arch(fp, 1.2, 1.6, 0, 1.8, 0.0, 3.2, P("#5b3a24")))
    S.add(Arch(fp, -1.6, -1.2, 0, 2.3, 0.0, 3.2, pale, pointed=True, mode="under"))
    top = ctx["ground_m"](south[0] + 12.0, south[1] + 8.0)
    fc = Frame(south[0] + 12.0, south[1] + 8.0, top, math.radians(-90))
    S.add(Box(fc, -0.4, 0.4, -0.4, 0.4, 0.0, 9.0, white))
    S.add(Box(fc, -0.4, 0.4, -2.6, 2.6, 5.6, 6.4, white))


BUILDERS = [("Royal Palace roofs", palace), ("Várkert Bazár", varkert), ("Castle Hill Funicular", siklo),
            ("Tunnel portal", portal), ("Mary Magdalene Tower", magdolna), ("Hospital in the Rock", hospital),
            ("Cave Church", cave)]
