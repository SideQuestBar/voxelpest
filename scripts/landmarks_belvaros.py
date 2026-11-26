"""Late November 2026, fifth round, the Inner City and the boulevards: the Academy of Sciences and the Gresham, the
Vigadó, the Inner City Parish Church and the Klotild Palaces, Corvinus's Customs House, the Párisi udvar with the
Franciscan and University churches, Szabadság tér's Stock Exchange, National Bank and US Embassy, Lechner's Postal
Savings Bank, the Liszt Academy, the New York Palace and the Vígszínház. Outlines from OSM; heights, colours and details
from the Esri aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np

from landmarks import WINDOW, Arch, Box, Frame, Lathe, cone, cyl, dome, onion, rect_of, zsolnay
from landmarks_city import base_under, statue
from landmarks_hosok import keep
from landmarks_kit import largest, painted, styled
from style import GLASS, METAL, ROOF

TAU = 2 * math.pi
MTA, GRESHAM, VIGADO = 11772, 11847, 24038230
PARISH, KLOTILD_N, KLOTILD_S = 24321885, 24324019, 14580
CORVINUS = 25043411
PARISI, FRANCISCAN, UNIVERSITY = 2225185, 24324325, 24711190
TOZSDE, MNB, US_EMBASSY = 11832, 11844, (24130069, 1214344426, 1214344425)
POSTA = 11846
LISZT, NEWYORK, VIG = 156392, 259011268, 24054231
RIVER = (4560.0, 3300.0)  # a point on the Pest bank, to tell the river fronts from the rest
BRIDGEHEAD = (4600.0, 4072.0)  # Elisabeth Bridge's Pest end, between the Klotild palaces

NAMES = ["Hungarian Academy of Sciences", "Gresham Palace", "Pesti Vigadó", "Inner City Parish Church",
         "Klotild Palaces", "Corvinus University main building", "Párisi udvar", "Franciscan church",
         "University Church", "Stock Exchange Palace", "Hungarian National Bank", "US Embassy",
         "Postal Savings Bank", "Liszt Academy", "New York Palace", "Vígszínház"]
DROP = {MTA, GRESHAM, VIGADO, PARISH, KLOTILD_N, KLOTILD_S, CORVINUS, PARISI, FRANCISCAN, UNIVERSITY, TOZSDE, MNB,
        *US_EMBASSY, POSTA, LISZT, NEWYORK, VIG}
KEEP = [(MTA, 26), (GRESHAM, 30), (VIGADO, 28), (PARISH, 20), (KLOTILD_N, 26), (KLOTILD_S, 26), (CORVINUS, 24),
        (PARISI, 26), (FRANCISCAN, 18), (UNIVERSITY, 18), (TOZSDE, 30), (MNB, 28), (POSTA, 24), (LISZT, 26),
        (NEWYORK, 30), (VIG, 24)]


def area(ctx, oid):
    try:
        return largest(keep(ctx, oid))
    except KeyError:
        return None


def corner_near(g, pt):
    pts = np.array(g.exterior.coords)[:-1]
    return pts[int(np.argmin(np.hypot(pts[:, 0] - pt[0], pts[:, 1] - pt[1])))]


def inward(g, p, by):
    """a point `by` m in from the corner p along the diagonal towards the centroid."""
    c = np.array(g.centroid.coords[0])
    d = c - p
    return p + d / max(np.linalg.norm(d), 1e-6) * by


def helm(S, ft, w0, r, kind, col, col2, gold, n=8):
    """a tower's crown from w0: an onion with a lantern, a needle spire, a dome with a lantern, or a tented cap."""
    rot = math.pi / n
    if kind == "onion":
        S.add(Lathe(ft, w0, w0 + r * 1.6, onion(r * 0.9, r * 1.05, 0.35), col, n=n, rot=rot))
        S.add(Lathe(ft, w0 + r * 1.6, w0 + r * 2.4, cyl(r * 0.3), col2, n=n, rot=rot))
        S.add(Lathe(ft, w0 + r * 2.4, w0 + r * 3.3, onion(r * 0.15, r * 0.35, 0.4), col, n=n, rot=rot))
        top = w0 + r * 3.3
    elif kind == "spire":
        S.add(Lathe(ft, w0, w0 + r * 4.5, cone(r, 0.08), col, n=n, rot=rot))
        top = w0 + r * 4.5
    elif kind == "dome":
        S.add(Lathe(ft, w0, w0 + r * 1.1, dome(r, 2.0, r * 0.25), col, n=0))
        S.add(Lathe(ft, w0 + r * 1.1, w0 + r * 1.6, cyl(r * 0.25), col2, n=8))
        S.add(Lathe(ft, w0 + r * 1.6, w0 + r * 2.0, cone(r * 0.3, 0.05), col, n=8))
        top = w0 + r * 2.0
    else:
        S.add(Lathe(ft, w0, w0 + r * 2.2, cone(r * 1.05, 0.15), col, n=4, rot=math.pi / 4))
        top = w0 + r * 2.2
    S.add(Box(ft, -0.08, 0.08, -0.08, 0.08, top - 0.2, top + 1.4, gold))
    return top


def tower(S, ft, a, w0, w1, wall, trim, win, tg, crown, r=None, col=None, col2=None, gold=None, round_=False):
    """a square (or round) tower a m across from w0 to w1, cornices, belfry openings in its top storey, its crown."""
    h = a / 2
    if round_:
        S.add(Lathe(ft, w0, w1, cyl(h), wall, n=16))
    else:
        S.add(Box(ft, -h, h, -h, h, w0, w1, wall))
    S.add(Box(ft, -h - 0.3, h + 0.3, -h - 0.3, h + 0.3, w1 - 0.6, w1, trim))
    for k in range(4):
        S.add(Arch(ft.at(turn=k * math.pi / 2), h - 0.5, h + 0.2, 0, min(0.9, h * 0.35), w1 - 4.6, w1 - 2.2, win,
                   mode="paint", targets=tg))
    return helm(S, ft, w1, r if r is not None else h * 0.95, crown, col, col2, gold)


def roof_statues(S, g, b0, E, col, every=None, corners=True, scale=1.0):
    pts = np.array(g.minimum_rotated_rectangle.exterior.coords)[:4]
    for p in pts if corners else []:
        q = inward(g, p, 1.2)
        statue(S, Frame(float(q[0]), float(q[1]), 0.0, 0.0), b0 + E + 0.9, col, scale)


# ------------------------------------------------------------------------------------------------ the river front
def academy(S, ctx, plan):
    """the Hungarian Academy of Sciences (Friedrich August Stüler, 1865): a Neo-Renaissance palazzo in pale sandstone,
    the great hall's tall arched windows on its piano nobile, a grey roof behind the balustrade and six scholars on its
    corners; and the Gresham Palace (Zsigmond Quittner and the Vágó brothers, 1906) on Széchenyi tér, Art Nouveau in
    pale grey stone with a gilded mosaic in its gable, its roof's two copper corner domes over the square."""
    P = ctx["P"]
    sand, sand2, white, win, slate = P("#ddcfae"), P("#cbbb95"), P("#efe8d8"), P("#33404a", WINDOW), P("#6f7477", ROOF)
    stone = P("#d9d4c8")
    g = area(ctx, MTA)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        E = 21.0

        def fn(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.9)
            bay = np.abs(np.mod(s, 4.4) - 2.2)
            noble = (hw > 7.4) & (hw < 13.6) & (bay < 0.95) & ((hw < 12.0) | (bay ** 2 + (hw - 12.0) ** 2 < 0.95 ** 2))
            low = (hw > 1.2) & (hw < 5.6) & (bay < 0.8)
            top = (hw > 15.6) & (hw < 18.6) & (bay < 0.7)
            wall = np.where(hw < 6.6, sand2, sand)
            wall = np.where((np.abs(hw - 6.8) < 0.3) | (np.abs(hw - 14.8) < 0.3) | (bay > 1.95), white, wall)
            o = np.where(edge & (hw < E), np.where(noble | low | top, win, wall), 0)
            o = np.where(inside & ~edge & (hw >= E - 0.6) & (hw < E + np.minimum(d * 0.6, 4.0)), slate, o)
            bal = edge & (hw >= E) & (hw < E + 1.0) & ((np.mod(s, 0.7) < 0.35) | (hw >= E + 0.7))
            return np.where(bal, white, o)
        painted(S, g, b0, E + 4.5, fn)
        roof_statues(S, g, b0, E, P("#e9e4d6"), scale=1.1)
    g = area(ctx, GRESHAM)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        E = 25.0
        styled(S, g, b0, E, stone, win, slate, floor=3.8, gf=5.0, bay=3.2, winw=1.6, sill=0.8, head=3.0,
               roof_kind="hip", slope=0.9, ridge=5.0, band=P("#c8c2b4"), base=P("#bdb6a6"))
        cu, cu2, gold = P("#5f9a86", ROOF), P("#4f8875", ROOF), P("#d4ad55", METAL)
        rect = np.array(g.minimum_rotated_rectangle.exterior.coords)[:4]
        near = sorted(rect, key=lambda p: math.hypot(p[0] - RIVER[0], p[1] - RIVER[1]))[:2]
        for p in near:
            q = inward(g, np.array(p), 4.5)
            ft = Frame(float(q[0]), float(q[1]), b0, 0.0)
            S.add(Lathe(ft, E - 1.0, E + 3.0, cyl(3.0), stone, n=12))
            helm(S, ft, E + 3.0, 3.1, "dome", cu, cu2, gold)
        mid = (np.array(near[0]) + np.array(near[1])) / 2
        q = inward(g, mid, 0.6)
        S.add(Box(Frame(float(q[0]), float(q[1]), b0, math.atan2(near[1][1] - near[0][1], near[1][0] - near[0][0])),
                  -4.0, 4.0, -0.6, 0.6, E - 2.0, E + 4.0, gold))


def vigado(S, ctx, plan):
    """the Pesti Vigadó (Frigyes Feszl, 1865): Romantic, its river front of tall arched windows between pillars carved
    with Hungarian motifs, in warm sandstone with darker bands, under steep grey hips."""
    P = ctx["P"]
    g = area(ctx, VIGADO)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    sand, band, white, win, slate = P("#d9bd8f"), P("#b98f63"), P("#efe2c6"), P("#33404a", WINDOW), P("#5f6468", ROOF)
    E = 20.0

    def fn(f, hw):
        d, s = f["d"], f["s"]
        inside, edge = d > 0, (d > 0) & (d < 0.9)
        bay = np.abs(np.mod(s, 4.0) - 2.0)
        tall = (hw > 8.0) & (hw < 15.5) & (bay < 0.9) & ((hw < 14.6) | (bay ** 2 + (hw - 14.6) ** 2 < 0.81))
        low = (hw > 1.0) & (hw < 5.0) & (bay < 1.1) & ((hw < 4.0) | (bay ** 2 + (hw - 4.0) ** 2 < 1.21))
        wall = np.where(np.mod(np.floor(hw / 0.8), 4) == 0, band, sand)
        wall = np.where((np.abs(hw - 6.6) < 0.4) | (np.abs(hw - 17.0) < 0.5) | (bay > 1.6), white, wall)
        o = np.where(edge & (hw < E), np.where(tall | low, win, wall), 0)
        o = np.where(inside & (hw >= E - 0.6) & (hw < E + np.minimum(d * 0.9, 9.0)), slate, o)
        crest = edge & (hw >= E) & (hw < E + 1.4) & (np.mod(s, 2.0) < 0.6)
        return np.where(crest, white, o)
    painted(S, g, b0, E + 9.5, fn)


def parish(S, ctx, plan):
    """the Inner City Parish Church (12th century; the Baroque front by György Paur, 1725-39): its two towers over
    Március 15 tér in cream and ochre with green copper helms, the Gothic choir behind under red tiles; and beside the
    bridge the twin Klotild Palaces (Flóris Korb and Kálmán Giergl, 1902), each with a tall corner tower crowned in a
    slate dome and lantern facing the bridge across Szabad sajtó út."""
    P = ctx["P"]
    cream, ochre, white, win, tile = P("#efe1bc"), P("#d7b675"), P("#f4efe2"), P("#33404a", WINDOW), P("#b25a3a", ROOF)
    cu, cu2, gold = P("#5f9a86", ROOF), P("#4f8875", ROOF), P("#d4ad55", METAL)
    g = area(ctx, PARISH)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        styled(S, g, b0, 15.0, cream, win, tile, floor=15.0, gf=3.0, bay=4.5, winw=1.6, sill=2.0, head=10.5,
               roof_kind="hip", slope=1.0, ridge=8.0, band=ochre, pier=ochre)
        cx, cy, L, W, ang = rect_of(g)
        ax = np.array([math.cos(ang), math.sin(ang)])
        if ax[0] > 0:
            ax = -ax  # the front looks west, to the square and the river
        front = np.array([cx, cy]) + ax * (L / 2 - 3.0)
        nv = np.array([-ax[1], ax[0]])
        for sv in (-1, 1):
            p = front + nv * sv * (W / 2 - 3.0)
            ft = Frame(float(p[0]), float(p[1]), b0, math.atan2(ax[1], ax[0]))
            tower(S, ft, 6.0, -2.0, 32.0, cream, white, win, [cream], "onion", r=3.0, col=cu, col2=cu2, gold=gold)
        S.clear.append((float(front[0]), float(front[1]), 12.0))
    slate, slate2 = P("#5c6266", ROOF), P("#4b5155", ROOF)
    pale, pale2 = P("#ece4d2"), P("#d8ccb2")
    for oid in (KLOTILD_N, KLOTILD_S):
        g = area(ctx, oid)
        if g is None:
            continue
        b0 = base_under(ctx, g, 0.3)
        styled(S, g, b0, 22.0, pale, win, slate, floor=3.6, gf=4.6, bay=3.2, winw=1.5, sill=0.9, head=2.9,
               roof_kind="hip", slope=0.9, ridge=5.0, band=pale2, base=pale2)
        p = inward(g, corner_near(g, BRIDGEHEAD), 3.5)
        ft = Frame(float(p[0]), float(p[1]), b0, 0.0)
        S.add(Lathe(ft, 20.0, 30.0, cyl(4.0), pale, n=8, rot=math.pi / 8))
        for k in range(8):
            S.add(Arch(ft.at(turn=k * TAU / 8), 3.5, 4.3, 0, 0.7, 24.0, 27.0, win, mode="paint", targets=[pale]))
        S.add(Lathe(ft, 30.0, 30.8, cyl(4.4), pale2, n=8, rot=math.pi / 8))
        helm(S, ft, 30.8, 4.0, "dome", slate, slate2, gold)


def corvinus(S, ctx, plan):
    """the Customs House (Miklós Ybl, 1874), Corvinus University's main building since 1951: a Neo-Renaissance block
    170 m along the river in ochre stone and red brick, arcades on its ground floor, grey hips over its three courts
    and the glazed roof of the hall between them."""
    P = ctx["P"]
    g = area(ctx, CORVINUS)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    brick, ochre, white, win, slate, glass = P("#b8714f"), P("#dcc08a"), P("#efe6d0"), P("#33404a", WINDOW), P("#6f6b68", ROOF), P("#8fb3bf", GLASS)
    E = 20.0

    def fn(f, hw):
        d, s = f["d"], f["s"]
        inside, edge = d > 0, (d > 0) & (d < 0.9)
        bay = np.abs(np.mod(s, 4.2) - 2.1)
        arc = (hw > 0.3) & (hw < 5.6) & (bay < 1.5) & ((hw < 4.6) | (bay ** 2 + (hw - 4.6) ** 2 < 2.25))
        ws = (hw > 7.4) & (np.mod(hw - 7.4, 4.2) < 2.8) & (hw < E - 1.4) & (bay < 0.75)
        wall = np.where(bay > 1.8, ochre, brick)
        wall = np.where(hw < 6.6, ochre, wall)
        wall = np.where((np.abs(hw - 6.8) < 0.3) | (np.abs(hw - (E - 0.8)) < 0.4), white, wall)
        o = np.where(edge & (hw < E), np.where(arc, P("#3e3a35"), np.where(ws, win, wall)), 0)
        hall = d > 12.0
        roof = np.where(hall, np.where(np.mod(s, 3.0) < 0.3, white, glass), slate)
        o = np.where(inside & (hw >= E - 0.6) & (hw < E + np.where(hall, 2.0, np.minimum(d * 0.8, 6.0))), roof, o)
        return o
    painted(S, g, b0, E + 6.5, fn)


# ------------------------------------------------------------------------------------------------ Ferenciek tere
def parisi(S, ctx, plan):
    """the Párisi udvar (Henrik Schmahl, 1913, a hotel since 2019): its front an eclectic dream in pale stone, Moorish
    and Gothic tracery round the arcade's mouth, the roof a crest of spiky turrets and gables over grey slate; and the
    Franciscan church of St Peter of Alcantara (1727-43) on the square, Baroque in cream under red tiles, its stone
    tower at the choir end with a tall copper spire; and down the street the University Church (1725-42), its two
    towers' copper helms over Papnövelde utca."""
    P = ctx["P"]
    pale, pale2, white, win, slate = P("#e6ddc9"), P("#cdbfa3"), P("#f2ede3"), P("#33404a", WINDOW), P("#5f6468", ROOF)
    cu, cu2, gold, tile = P("#5f9a86", ROOF), P("#4f8875", ROOF), P("#d4ad55", METAL), P("#b25a3a", ROOF)
    cream, ochre = P("#efe1bc"), P("#d7b675")
    g = area(ctx, PARISI)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        E = 22.0
        styled(S, g, b0, E, pale, win, slate, floor=3.6, gf=5.0, bay=3.0, winw=1.5, sill=0.8, head=2.9,
               roof_kind="hip", slope=1.0, ridge=6.0, band=pale2, base=pale2)
        ring = g.exterior
        for k in range(int(ring.length // 9.0)):
            p = ring.interpolate(k * 9.0 + 4.5)
            q = inward(g, np.array([p.x, p.y]), 0.8)
            fp = Frame(float(q[0]), float(q[1]), b0, 0.0)
            S.add(Lathe(fp, E - 0.5, E + 2.5, cyl(0.7), pale, n=8))
            S.add(Lathe(fp, E + 2.5, E + 6.0, cone(0.8, 0.05), slate, n=8))
            S.add(Box(fp, -0.06, 0.06, -0.06, 0.06, E + 6.0, E + 6.8, gold))
    g = area(ctx, FRANCISCAN)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        styled(S, g, b0, 14.0, cream, win, tile, floor=14.0, gf=2.5, bay=4.2, winw=1.5, sill=2.5, head=9.5,
               roof_kind="hip", slope=1.0, ridge=7.0, band=ochre, pier=ochre)
        ft = Frame(4866.0, 4153.0, b0, 0.0)  # the tower, from the aerial
        S.add(Box(ft, -3.0, 3.0, -3.0, 3.0, -2.0, 30.0, P("#e8e2d4")))
        for w in (14.0, 22.0):
            S.add(Box(ft, -3.3, 3.3, -3.3, 3.3, w, w + 0.6, white))
        for k in range(4):
            S.add(Arch(ft.at(turn=k * math.pi / 2), 2.5, 3.2, 0, 0.8, 24.5, 28.0, win, mode="paint", targets=[P("#e8e2d4")]))
        helm(S, ft, 30.0, 2.8, "spire", cu, cu2, gold)
    g = area(ctx, UNIVERSITY)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        styled(S, g, b0, 16.0, cream, win, tile, floor=16.0, gf=2.5, bay=4.5, winw=1.6, sill=3.0, head=11.0,
               roof_kind="hip", slope=1.0, ridge=8.0, band=ochre, pier=ochre)
        front, apse = np.array([4774.0, 4408.0]), np.array([4752.0, 4447.0])  # from the aerial
        ax = (front - apse) / np.linalg.norm(front - apse)
        nv = np.array([-ax[1], ax[0]])
        for sv in (-1, 1):
            p = front - ax * 2.5 + nv * sv * 6.5
            ft = Frame(float(p[0]), float(p[1]), b0, math.atan2(ax[1], ax[0]))
            tower(S, ft, 5.4, -2.0, 30.0, cream, white, win, [cream], "onion", r=2.8, col=cu, col2=cu2, gold=gold)


# ------------------------------------------------------------------------------------------------ Szabadság tér
def szabadsag(S, ctx, plan):
    """Szabadság tér's banks: the Stock Exchange Palace (Ignác Alpár, 1905), a giant order of columns along the square
    and its corner towers' copper cupolas; Alpár's Austro-Hungarian Bank opposite (1905), the National Bank since,
    in pale stone with a glazed court; and the US Embassy's Art Nouveau houses on the square's east side."""
    P = ctx["P"]
    pale, pale2, white, win, slate = P("#e3dccb"), P("#cbbfa6"), P("#f1ece0"), P("#33404a", WINDOW), P("#62676a", ROOF)
    cu, cu2, gold, glass = P("#5f9a86", ROOF), P("#4f8875", ROOF), P("#d4ad55", METAL), P("#6e9fb3", GLASS)
    g = area(ctx, TOZSDE)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        E = 26.0

        def fn(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 1.6)
            bay = np.abs(np.mod(s, 4.0) - 2.0)
            col = inside & (hw > 6.0) & (hw < E - 3.0) & (bay < 0.7) & (d < 0.9)
            recess = (hw > 6.0) & (hw < E - 3.0) & (bay >= 0.7) & (d < 0.9)
            ws = (np.mod(hw - 6.0, 4.6) > 1.0) & (np.mod(hw - 6.0, 4.6) < 3.4) & (bay > 1.0) & (bay < 1.6)
            o = np.where(edge & (hw < E) & ~recess, np.where(hw < 6.0, pale2, pale), 0)
            o = np.where(edge & recess & (d >= 0.9), np.where(ws, win, pale2), o)
            o = np.where(col, white, o)
            o = np.where(edge & (hw >= E - 3.0) & (hw < E), white, o)
            return np.where(inside & (hw >= E - 0.6) & (hw < E + np.minimum(d * 0.7, 5.0)), slate, o)
        painted(S, g, b0, E + 5.5, fn)
        rect = np.array(g.minimum_rotated_rectangle.exterior.coords)[:4]
        for p in rect:
            q = inward(g, p, 6.0)
            ft = Frame(float(q[0]), float(q[1]), b0, 0.0)
            S.add(Lathe(ft, E - 1.0, E + 5.0, cyl(3.4), pale, n=8, rot=math.pi / 8))
            helm(S, ft, E + 5.0, 3.4, "dome", cu, cu2, gold)
    g = area(ctx, MNB)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        styled(S, g, b0, 24.0, pale, win, slate, floor=4.0, gf=6.0, bay=3.6, winw=1.6, sill=0.9, head=3.0,
               roof_kind="hip", slope=0.8, ridge=4.0, band=white, base=pale2, pier=pale2)

        def court(f, hw):
            return np.where((f["d"] > 14.0) & (hw >= 21.0) & (hw < 21.6), glass, 0)
        painted(S, g, b0, 22.0, court)
    for oid in US_EMBASSY:
        g = area(ctx, oid)
        if g is not None:
            styled(S, g, base_under(ctx, g, 0.3), 21.0, P("#d5d0c4"), win, slate, floor=3.8, gf=4.6, bay=3.0,
                   winw=1.4, sill=0.9, head=3.0, roof_kind="hip", slope=0.9, ridge=4.5, band=P("#bdb6a6"))


def posta(S, ctx, plan):
    """the Postal Savings Bank (Ödön Lechner, 1901): a white front patterned in yellow and blue Zsolnay ceramics, bees
    climbing its pilasters to their hives, and its fantastical roof of green and yellow glazed tiles with gables and
    turrets crowning the crest."""
    P = ctx["P"]
    g = area(ctx, POSTA)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    white, blue, yellow, win = P("#f1eee6"), P("#3a6a9a"), P("#d9b24a"), P("#33404a", WINDOW)
    tiles = zsolnay(P, ["#3f7a4a", "#d9b24a", "#2f6a5a", "#c99a3a"], period=1.0, slope=1.0, kind="diamond")
    E = 19.0

    def fn(f, hw):
        d, s = f["d"], f["s"]
        inside, edge = d > 0, (d > 0) & (d < 0.9)
        bay = np.abs(np.mod(s, 3.4) - 1.7)
        ws = (hw > 1.0) & (np.mod(hw - 0.6, 3.8) > 0.8) & (np.mod(hw - 0.6, 3.8) < 3.0) & (bay < 0.75) & (hw < E - 2.0)
        wall = np.where((bay > 1.35) & (np.mod(hw, 1.2) < 0.4), yellow, white)
        wall = np.where(np.abs(hw - (E - 1.2)) < 0.6, np.where(np.mod(s, 1.0) < 0.5, blue, yellow), wall)
        o = np.where(edge & (hw < E), np.where(ws, win, wall), 0)
        rise = np.minimum(d * 1.3, 9.0)
        roof = inside & (hw >= E - 0.6) & (hw < E + rise)
        o = np.where(roof, tiles(s, d, hw), o)
        gable = edge & (hw >= E) & (hw < E + 4.0 - np.abs(np.mod(s, 10.0) - 5.0) * 1.2)
        return np.where(gable, np.where(np.mod(hw, 1.0) < 0.3, yellow, white), o)
    painted(S, g, b0, E + 9.5, fn)


# ------------------------------------------------------------------------------------------------ the boulevards
def liszt(S, ctx, plan):
    """the Liszt Academy (Flóris Korb and Kálmán Giergl, 1907) on Liszt Ferenc tér: Art Nouveau in pale stone, its
    front a tall portal under paired columns and Alajos Stróbl's seated Liszt in bronze, grey roofs behind."""
    P = ctx["P"]
    g = area(ctx, LISZT)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    pale, pale2, white, win, slate, bronze = P("#e9e1cf"), P("#d3c7ad"), P("#f3eee3"), P("#33404a", WINDOW), P("#5f6468", ROOF), P("#4d473d", METAL)
    E = 22.0
    styled(S, g, b0, E, pale, win, slate, floor=4.2, gf=5.2, bay=3.4, winw=1.6, sill=0.9, head=3.2,
           roof_kind="hip", slope=0.9, ridge=5.0, band=pale2, base=pale2)
    pts = np.array(g.exterior.coords)[:-1]
    west = pts[np.argsort(pts[:, 0])[:2]]
    mid = west.mean(0)
    ang = math.atan2(west[1][1] - west[0][1], west[1][0] - west[0][0])
    fr = Frame(float(mid[0]), float(mid[1]), b0, ang + math.pi / 2)
    if math.cos(ang + math.pi / 2) > 0:
        fr = Frame(float(mid[0]), float(mid[1]), b0, ang - math.pi / 2)
    for sv in (-1, 1):
        for k in (0, 1):
            S.add(Lathe(fr.at(0.8, sv * (3.6 + 1.6 * k)), 5.2, 15.0, cyl(0.45), white, n=12))
    S.add(Box(fr, -0.2, 1.4, -6.0, 6.0, 15.0, 17.0, white))
    S.add(Arch(fr, -0.4, 0.6, 0, 2.2, 0.0, 4.0, P("#4a3828")))
    statue(S, fr.at(1.6), 17.0, bronze, 1.3)


def newyork(S, ctx, plan):
    """the New York Palace (Alajos Hauszmann, Flóris Korb and Kálmán Giergl, 1894) on the Grand Boulevard: eclectic,
    its rich front in pale stone and its corner tower with a slate spire and lantern over the boulevard, smaller
    towers along it."""
    P = ctx["P"]
    g = area(ctx, NEWYORK)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    pale, pale2, win, slate, slate2, gold = P("#e8e0cd"), P("#cdbfa3"), P("#33404a", WINDOW), P("#5c6266", ROOF), P("#4b5155", ROOF), P("#d4ad55", METAL)
    E = 24.0
    styled(S, g, b0, E, pale, win, slate, floor=3.7, gf=5.2, bay=3.0, winw=1.5, sill=0.8, head=2.9,
           roof_kind="hip", slope=1.0, ridge=6.0, band=pale2, base=pale2)
    for (x, y), a, top, r in (((6033.0, 4394.0), 7.0, 34.0, 3.6), ((6027.0, 4410.0), 5.0, 29.0, 2.4)):
        ft = Frame(x, y, b0, 0.0)
        tower(S, ft, a, E - 2.0, top, pale, pale2, win, [pale], "spire", r=r, col=slate, col2=slate2, gold=gold)


def vig(S, ctx, plan):
    """the Vígszínház (Fellner and Helmer, 1896): neo-Baroque in cream and ochre, its front to the boulevard between two
    domed corner towers, the auditorium under a green copper roof behind."""
    P = ctx["P"]
    g = area(ctx, VIG)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    cream, ochre, white, win = P("#eedfb8"), P("#d4b16e"), P("#f4efe2"), P("#33404a", WINDOW)
    cu, cu2, gold = P("#5f9a86", ROOF), P("#4f8875", ROOF), P("#d4ad55", METAL)
    E = 17.0
    styled(S, g, b0, E, cream, win, cu, floor=4.0, gf=5.0, bay=3.6, winw=1.6, sill=0.9, head=3.0,
           roof_kind="hip", slope=0.9, ridge=7.0, band=white, base=ochre, pier=ochre)
    rect = np.array(g.minimum_rotated_rectangle.exterior.coords)[:4]
    front = sorted(rect, key=lambda p: math.hypot(p[0] - 5975.0, p[1] - 2310.0))[:2]  # towards the boulevard
    for p in front:
        q = inward(g, np.array(p), 4.0)
        ft = Frame(float(q[0]), float(q[1]), b0, 0.0)
        S.add(Lathe(ft, E - 1.0, E + 6.0, cyl(3.2), cream, n=8, rot=math.pi / 8))
        for k in range(8):
            S.add(Arch(ft.at(turn=k * TAU / 8), 2.7, 3.5, 0, 0.6, E + 1.5, E + 4.0, win, mode="paint", targets=[cream]))
        helm(S, ft, E + 6.0, 3.2, "dome", cu, cu2, gold)
    c = g.centroid
    fc = Frame(c.x, c.y, b0, 0.0)
    S.add(Lathe(fc, E + 6.0, E + 9.0, cyl(5.0), cu2, n=16))
    S.add(Lathe(fc, E + 9.0, E + 13.0, dome(5.2, 2.0, 1.0), cu, n=16))


BUILDERS = [("Hungarian Academy of Sciences", academy), ("Pesti Vigadó", vigado), ("Inner City Parish Church", parish),
            ("Corvinus University main building", corvinus), ("Párisi udvar", parisi), ("Stock Exchange Palace", szabadsag),
            ("Postal Savings Bank", posta), ("Liszt Academy", liszt), ("New York Palace", newyork), ("Vígszínház", vig)]
