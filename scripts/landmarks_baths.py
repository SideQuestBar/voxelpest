"""Late November 2026, fifth round, Buda's baths: the Rudas and the Király with their Ottoman domes, the Lukács and the
Komjádi pool beside it, and the tomb of Gül Baba on Rózsadomb. Outlines from OSM; heights, colours and details from the
Esri aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np

from landmarks import WINDOW, Arch, Box, Frame, Lathe, cyl, dome, rect_of
from landmarks_city import base_under
from landmarks_hosok import keep
from landmarks_kit import largest, painted, styled
from style import GLASS, METAL, ROOF

TAU = 2 * math.pi
RUDAS_DOME_PART = 345055301
RUDAS_WINGS = ((345055302, 9.0), (345055304, 9.0), (345055305, 9.0), (345055308, 9.0), (9096453, 9.0))
RUDAS_DOME = (4054.0, 4021.0)
KIRALY_TURKISH, KIRALY_WING = 481583655, 481583656
LUKACS, KOMJADI = 165810, 207583882
GULBABA = 37126204

NAMES = ["Rudas Baths", "Király Baths", "Lukács Baths and Komjádi pool", "Tomb of Gül Baba"]
DROP = {RUDAS_DOME_PART, *(i for i, _ in RUDAS_WINGS), KIRALY_TURKISH, KIRALY_WING, LUKACS, KOMJADI, GULBABA}
KEEP = [(RUDAS_DOME_PART, 8), (KIRALY_TURKISH, 8), (KIRALY_WING, 12), (LUKACS, 16), (KOMJADI, 18), (GULBABA, 6)]


def area(ctx, oid):
    try:
        return largest(keep(ctx, oid))
    except KeyError:
        return None


def ottoman(S, fr, r, h_drum, col_wall, col_dome, gold, n=8, lantern=True):
    """an Ottoman bath's dome: an octagonal drum, a low copper dome studded with the round skylights (left to the
    dome's colour pattern) and a crescent finial."""
    S.add(Lathe(fr, -1.0, h_drum, cyl(r + 0.4), col_wall, n=n, rot=math.pi / n))
    S.add(Lathe(fr, h_drum, h_drum + r * 0.75, dome(r, 2.0, 0.5 if lantern else 0.0), col_dome, n=0))
    z = h_drum + r * 0.75
    S.add(Box(fr, -0.08, 0.08, -0.08, 0.08, z - 0.2, z + 1.2, gold))
    S.add(Box(fr, -0.45, 0.45, -0.08, 0.08, z + 1.0, z + 1.25, gold))


# ------------------------------------------------------------------------------------------------ the Rudas
def rudas(S, ctx, plan):
    """the Rudas (1566, the front 1896): the Ottoman octagon's green copper dome over its pool, starred with round
    skylights, rising from the flat roofs of the north end; the baths' wings along the river front in white with
    tall windows under red tile hips."""
    P = ctx["P"]
    white, cream, win, tile = P("#f0ece2"), P("#e6dcc5"), P("#33404a", WINDOW), P("#a5573c", ROOF)
    cu, cu2, gold, flat = P("#5f9a86", ROOF), P("#e9efe8", GLASS), P("#d4ad55", METAL), P("#b7b3a8", ROOF)
    g = area(ctx, RUDAS_DOME_PART)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        styled(S, g, b0, 7.0, cream, win, flat, floor=4.0, gf=4.0, bay=3.4, winw=1.6)
        x, y = RUDAS_DOME
        fr = Frame(x, y, b0 + 7.0, 0.0)

        def dcol(u, v, w):
            a = np.arctan2(v, u)
            star = (np.abs(np.mod(a * 12 / TAU, 1.0) - 0.5) < 0.12) & (np.abs(np.mod(w * 1.6, 1.0) - 0.5) < 0.18)
            return np.where(star, cu2, cu).astype(np.uint16)
        ottoman(S, fr, 6.5, 2.6, cream, dcol, gold)
        for k in range(4):
            fk = fr.at(turn=k * TAU / 4 + TAU / 8).at(8.5)
            S.add(Lathe(fk, -0.6, 1.2, cyl(2.0), cream, n=8))
            S.add(Lathe(fk, 1.2, 2.6, dome(1.9), cu, n=0))
    for oid, E in RUDAS_WINGS:
        g = area(ctx, oid)
        if g is not None:
            styled(S, g, base_under(ctx, g, 0.3), E, white, win, tile, floor=4.3, gf=4.7, bay=3.2, winw=1.5, sill=1.0,
                   head=3.6, roof_kind="hip", slope=0.7, ridge=4.0, band=cream)


# ------------------------------------------------------------------------------------------------ the Király
def kiraly(S, ctx, plan):
    """the Király (1565-70): the Ottoman bath behind a classicist wing in ochre; its octagon under a green copper dome
    with a crescent, three small domes over the side rooms."""
    P = ctx["P"]
    ochre, white, win, slate = P("#dcb96f"), P("#f0eadb"), P("#33404a", WINDOW), P("#7b7f80", ROOF)
    stone, cu, gold = P("#cfc4ad"), P("#5f9a86", ROOF), P("#d4ad55", METAL)
    g = area(ctx, KIRALY_WING)
    if g is not None:
        styled(S, g, base_under(ctx, g, 0.3), 11.0, ochre, win, slate, floor=3.6, gf=4.0, bay=3.2, winw=1.3, sill=1.0,
               head=3.0, roof_kind="hip", slope=0.8, ridge=4.0, band=white)
    g = area(ctx, KIRALY_TURKISH)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    styled(S, g, b0, 5.5, stone, stone, P("#a9a49a", ROOF), floor=5.5, bay=6.0, winw=0.1)
    cx, cy, L, W, ang = rect_of(g)
    fr = Frame(cx, cy, b0 + 5.5, ang)
    ottoman(S, fr, min(L, W) * 0.34, 1.8, stone, cu, gold)
    for su, sv in ((-1, -1), (-1, 1), (1, -1)):
        fk = fr.at(su * L * 0.36, sv * W * 0.33)
        S.add(Lathe(fk, -0.6, 0.8, cyl(1.6), stone, n=8))
        S.add(Lathe(fk, 0.8, 2.0, dome(1.5), cu, n=0))


# ------------------------------------------------------------------------------------------------ the Lukács and the Komjádi
def lukacs(S, ctx, plan):
    """the Lukács (1894, its spa hotel wings 1921): a long cream building in three and four storeys round its court,
    tall windows and red tile hips; beside it the Komjádi pool (1976, its hall rebuilt in 2018), a long white hall
    under a vaulted roof with glazed ends, the roof's middle opening over the pool in summer."""
    P = ctx["P"]
    cream, white, win, tile = P("#e8d6a8"), P("#f2ecdc"), P("#33404a", WINDOW), P("#a85a3e", ROOF)
    g = area(ctx, LUKACS)
    if g is not None:
        styled(S, g, base_under(ctx, g, 0.3), 15.0, cream, win, tile, floor=3.7, gf=4.4, bay=3.4, winw=1.5, sill=1.0,
               head=3.0, roof_kind="hip", slope=0.75, ridge=4.5, band=white, base=white)
    g = area(ctx, KOMJADI)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    wh, wh2, glass, frame = P("#eef0ef", ROOF), P("#d9dcdc", ROOF), P("#7fa3b0", GLASS), P("#c8cccc", METAL)
    cx, cy, L, W, ang = rect_of(g)
    E, R = 9.0, 9.0
    ca, sa = math.cos(ang), math.sin(ang)

    def fn(f, hw):
        d, s = f["d"], f["s"]
        inside, edge = d > 0, (d > 0) & (d < 0.8)
        v = -(f["X"] - cx) * sa + (f["Y"] - cy) * ca
        u = (f["X"] - cx) * ca + (f["Y"] - cy) * sa
        t = np.clip(np.abs(v) / (W / 2), 0, 1)
        z = E + R * np.sqrt(1 - t ** 2)
        o = np.where(edge & (hw < E), np.where(np.mod(s, 3.0) < 0.35, frame, glass), 0)
        band = np.abs(u) < L * 0.28
        roof = np.where(band & (t < 0.45), np.where(np.mod(u, 2.0) < 0.3, frame, wh2), np.where(np.mod(u, 6.0) < 0.4, wh2, wh))
        o = np.where(inside & (hw >= E - 0.4) & (hw < z) & (hw >= z - 0.8), roof, o)
        end = inside & (np.abs(np.abs(u) - (L / 2 - 0.4)) < 0.5) & (hw >= E) & (hw < z)
        return np.where(end, np.where(np.mod(v, 2.5) < 0.3, frame, glass), o)
    painted(S, g, b0, E + R + 0.5, fn)


# ------------------------------------------------------------------------------------------------ Gül Baba
def gulbaba(S, ctx, plan):
    """the tomb of Gül Baba (1543-48): the northernmost Islamic shrine in Europe, a small octagon of rough stone under a
    ribbed lead-grey dome and its crescent, on the terrace of its rose garden."""
    P = ctx["P"]
    g = area(ctx, GULBABA)
    if g is None:
        return
    c = g.centroid
    b0 = base_under(ctx, g, 0.3)
    stone, stone2, lead, gold, dark = P("#cfc6b3"), P("#b9b09b"), P("#7f8a87", ROOF), P("#d4ad55", METAL), P("#35332f", WINDOW)
    r = max(rect_of(g)[3] / 2, 3.2)
    fr = Frame(c.x, c.y, b0, 0.0)

    def wall(u, v, w):
        return np.where(np.mod(np.floor(w / 0.5), 2) == 0, stone, stone2).astype(np.uint16)
    S.add(Lathe(fr, -0.6, 5.2, cyl(r), wall, n=8, rot=math.pi / 8))
    for k in range(8):
        S.add(Arch(fr.at(turn=k * TAU / 8 + math.pi / 8 + TAU / 16), r - 0.4, r + 0.1, 0, 0.5, 1.4, 2.8, dark,
                   pointed=True, mode="paint", targets=[stone, stone2]))
    S.add(Lathe(fr, 5.2, 5.8, cyl(r + 0.3), stone2, n=8, rot=math.pi / 8))

    def ribs(u, v, w):
        a = np.mod(np.arctan2(v, u), TAU / 16)
        return np.where(a < 0.08, stone2, lead).astype(np.uint16)
    S.add(Lathe(fr, 5.8, 5.8 + r * 0.95, dome(r * 0.95, 2.0, 0.3), ribs, n=0))
    z = 5.8 + r * 0.95
    S.add(Box(fr, -0.08, 0.08, -0.08, 0.08, z - 0.2, z + 1.4, gold))
    S.add(Box(fr, -0.4, 0.4, -0.08, 0.08, z + 1.2, z + 1.45, gold))


BUILDERS = [("Rudas Baths", rudas), ("Király Baths", kiraly), ("Lukács Baths and Komjádi pool", lukacs), ("Tomb of Gül Baba", gulbaba)]
