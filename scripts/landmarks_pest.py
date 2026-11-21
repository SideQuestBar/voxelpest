"""Pest: Józsefváros (the Corvin Cinema, Corvin Plaza, the Museum of Applied Arts, Semmelweis University's building on
Üllői út, the former Slovak Lutheran church in its court behind Rákóczi út 57 with the gateway to it), St Margaret's
at Lehel tér, Arena Mall and the MTK Sportpark hall. Outlines from OSM; heights, colours and details from the aerial
and street photos (docs/landmarks.md)."""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon

from landmarks import WINDOW, Arch, Box, Ellipsoid, Field, Frame, Lathe, Poly, Roof, cone, cyl, dome
from landmarks_city import base_under, dist_in, grid_of, windows
from landmarks_hosok import column, keep, side, spire, windows_on
from style import CLASSIC, CONCRETE, GLASS, METAL, ROOF

CORVIN_MOZI, CORVIN_PLAZA, IPARMU, SEMMELWEIS = 26734077, 83180446, 240902171, 249341406
SLOVAK, SLOVAK_GATE_HOUSE, MARGIT, ARENA, MTK = 260409218, 260409225, 25081122, 25268421, 1426371705

NAMES = ["Corvin Cinema", "Corvin Plaza", "Museum of Applied Arts", "Semmelweis University", "Slovak Lutheran Church",
         "St Margaret's Church", "Arena Mall", "MTK Sportpark"]
DROP = {CORVIN_MOZI, CORVIN_PLAZA, IPARMU, SEMMELWEIS, SLOVAK, MARGIT, ARENA, MTK}
KEEP = [(CORVIN_MOZI, 20), (CORVIN_PLAZA, 20), (IPARMU, 20), (SEMMELWEIS, 21), (SLOVAK, 14), (MARGIT, 18),
        (ARENA, 20), (MTK, 18)]


def fields_of(g, fr, pad=1.0):
    """per cell of g's grid: the distance inside the outline and the frame coordinates."""
    x0f, y0f, X, Y = grid_of(g, pad)
    U = ((X - fr.ox) * fr.ca + (Y - fr.oy) * fr.sa).astype(np.float32)
    V = (-(X - fr.ox) * fr.sa + (Y - fr.oy) * fr.ca).astype(np.float32)
    return x0f, y0f, dict(d=dist_in(g, X, Y), U=U, V=V, a=(X + Y).astype(np.float32))


def block(S, g, fr, b0, top, fn, lower=-3.0, pad=1.0):
    """a Field over the outline g: fn(d, U, V, a, hw) -> ids for each cell and height hw over b0 (0 outside)."""
    x0f, y0f, f = fields_of(g, fr, pad)

    def go(f_, wa):
        d_, U_, V_, a_ = (f_[k][None] for k in ("d", "U", "V", "a"))
        hw = wa - b0
        o = np.where(hw >= lower, fn(d_, U_, V_, a_, hw), 0)
        return np.broadcast_to(o, np.broadcast_shapes(o.shape, hw.shape)).astype(np.uint16)
    return S.add(Field(x0f, y0f, f, b0 + lower, b0 + top, go))


def axis_frame(g, ang, oz, at="min"):
    """a frame turned by ang whose u = 0 lies on the outline's extreme point along u (min: the near end)."""
    c = g.centroid
    fr = Frame(c.x, c.y, oz, ang)
    u, v = fr.uv(*np.array(g.exterior.coords).T)
    u0 = u.min() if at == "min" else u.max()
    vc = (v.min() + v.max()) / 2
    x, y = fr.xy(u0, vc)
    return Frame(x, y, oz, ang), float(u.max() - u.min()), float((v.max() - v.min()) / 2)


GLYPHS = {  # 5 x 7 bitmaps, top row first
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "N": ["10001", "11001", "10101", "10101", "10011", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "V": ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
}


def letters(S, fr, u, v0, w0, word, h, col, step=None, depth=0.5):
    """a sign of block letters on a wall facing +u, centred at v0, h tall from w0: each a 5 x 7 bitmap of slabs."""
    px = h / 7
    step = step or px * 6.5
    v = v0 + (len(word) - 1) * step / 2  # +v runs to the reader's left when facing the wall
    for k, ch in enumerate(word):
        vc = v - k * step
        for r, line in enumerate(GLYPHS[ch]):
            for c, on in enumerate(line):
                if on == "1":
                    vv = vc + (2 - c) * px
                    ww = w0 + (6 - r) * px
                    S.add(Box(fr, u, u + depth, vv - px / 2, vv + px / 2, ww, ww + px, col))


# ------------------------------------------------------------------------------------------------ Corvin Cinema
def corvin_mozi(S, ctx, plan):
    """the Corvin Cinema (Emil Vidor's 1923 hall, rebuilt in the 1990s) in the ring of houses off Üllői út: a long hall
    under a pale green gabled roof, its rounded front facing the passage from Corvin köz in cream render, pilaster
    strips between tall windows, the canopy over the doors and the red CORVIN letters on the parapet."""
    P = ctx["P"]
    g = keep(ctx, CORVIN_MOZI)
    b0 = base_under(ctx, g, 0.3)
    fr, L, hw_ = axis_frame(g, math.radians(46.6), b0)
    cream, cream2, plinth = P("#e6dcc2"), P("#d3c6a6"), P("#a59a83")
    roof, roof2 = P("#97ab73", ROOF), P("#869a64", ROOF)
    red, win, glass = P("#c4232b", METAL), P("#38403f", WINDOW), P("#7d949a", GLASS)
    E, F = 15.5, 13.0  # the hall's eaves; the front part's depth

    def fn(d, U, V, a, hw):
        inside = d > 0
        front = U < F
        top = np.where(front, E + 3.0, E)
        wall = np.where(hw < 1.2, plinth, np.where(np.mod(a, 4.2) < 0.9, cream2, cream))
        o = np.where(inside & (hw < top), wall, 0)
        o = np.where(inside & front & (d < 0.8) & (hw >= top - 0.8) & (hw < top + 1.0), cream2, o)
        o = np.where(inside & (hw >= top - 0.6) & (hw < top) & (d < 0.6), cream2, o)
        rise = np.minimum(d * 0.42, 5.0)
        rf = inside & ~front & (hw >= E) & (hw < E + rise)
        return np.where(rf, np.where(np.mod(np.floor(U / 1.2), 2) == 0, roof, roof2), o)
    block(S, g, fr, b0, E + 6.0, fn)
    tg = [cream, cream2]
    windows(S, g, b0, [(4.8, 12.5)], tg, glass, every=4.2, half=0.9, min_len=3.0, arch=False)
    windows(S, g, b0, [(1.0, 3.6)], tg + [plinth], win, every=4.2, half=1.2, min_len=3.0, arch=False)
    # the canopy over the doors and the letters over the front, facing the passage
    ff = Frame(fr.ox, fr.oy, b0, fr.ang + math.pi)  # +u out of the front
    S.add(Box(ff, -0.5, 3.2, -9.0, 9.0, 4.0, 4.6, cream2))
    S.add(Box(ff, 2.9, 3.3, -9.0, 9.0, 3.4, 4.6, red))
    letters(S, ff, -3.0, 0.0, E + 3.0, "CORVIN", 4.9, red, step=4.3, depth=1.0)  # on the roof over the front
    S.clear.append((fr.ox, fr.oy, 10.0))


# ------------------------------------------------------------------------------------------------ Corvin Plaza
def corvin_plaza(S, ctx, plan):
    """Corvin Plaza (2010): the mall of the Corvin quarter bridging its streets, travertine-clad walls with long
    bands of glass, the glazed entrance at the corner on Futó utca with the purple dots, green roofs over the shops."""
    P = ctx["P"]
    g = keep(ctx, CORVIN_PLAZA)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(1909.0, 4462.8, b0, math.radians(44.0))
    trav, trav2, glass, glass2 = P("#ddd2bb"), P("#cbbfa5"), P("#7d97a2", GLASS), P("#6a8590", GLASS)
    roofg, roofp, roofc = P("#6f7f4e", ROOF), P("#b8ae98", ROOF), P("#a8a9a5", ROOF)
    purple, gold = P("#6d2a6e", METAL), P("#e0a43a", METAL)
    E = 19.5

    def fn(d, U, V, a, hw):
        inside = d > 0
        bands = (np.mod(hw - 4.6, 4.6) < 2.6) & (hw > 4.6)
        fin = np.mod(a, 6.0) < 1.2
        wall = np.where(hw < 4.6, np.where(np.mod(a, 6.0) < 1.6, trav2, glass2),
                        np.where(bands & ~fin, glass, np.where(fin, trav2, trav)))
        o = np.where(inside & (hw < E), wall, 0)
        o = np.where(inside & (d < 0.7) & (hw >= E) & (hw < E + 1.1), trav2, o)  # the parapet
        path = (np.mod(U - V, 23.0) < 1.4) | (np.mod(U + V, 31.0) < 1.4)
        roofs = inside & (d >= 0.7) & (hw >= E - 0.5) & (hw < E)
        o = np.where(roofs, np.where(d > 5.0, np.where(path, roofp, roofg), roofc), o)
        return o
    block(S, g, fr, b0, E + 2.0, fn)
    # the glass corner on Futó utca: a faceted glass prism over the entrance, the logo's dots on it
    fc = Frame(1907.5, 4467.0, b0, math.radians(-111.4))  # +u out of the corner
    S.add(Lathe(Frame(1907.5, 4467.0, b0), 0.0, E + 3.0, cyl(5.0), glass, n=6))
    for k, (dv, dw) in enumerate(((0, 0), (1.3, 0.8), (-1.3, 0.8), (1.3, -0.8), (-1.3, -0.8), (0, 1.6), (0, -1.6))):
        S.add(Ellipsoid(fc.at(5.1, dv, E - 3.0 + dw), 0.25, 0.55, 0.55, gold if k == 0 else purple))
    S.clear.append((1950.0, 4560.0, 70.0))


# ------------------------------------------------------------------------------------------------ Museum of Applied Arts
def iparmu(S, ctx, plan):
    """the Museum of Applied Arts (Ödön Lechner and Gyula Pártos, 1896): pale yellow brick trimmed with Zsolnay
    ceramics, steep roofs of green and yellow glazed tiles in a diamond pattern, the main dome over the entrance on
    Üllői út in the same tiles with a lantern, a spired tower over the north range and little domed turrets at the
    corners; in the court, the great hall under a glass roof."""
    P = ctx["P"]
    g = keep(ctx, IPARMU)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(1640.0, 4300.0, b0, math.radians(3.0))
    brick, brick2, cream = P("#e2cf98"), P("#d4bd80"), P("#efe5cc")
    zg, zy, zb, zr = P("#3e8b5a", ROOF), P("#d5b54b", ROOF), P("#3a6f95", ROOF), P("#b2553c", ROOF)
    win, glass = P("#323b3d", WINDOW), P("#a6bec2", GLASS)
    gold, steel = P("#d9b24c", METAL), P("#59605f", METAL)
    E = 19.0

    W0 = 7.5  # the ranges are ~15 m deep; past them, the court's hall

    def fn(d, U, V, a, hw):
        inside = d > 0
        wing = d < 2 * W0
        socle = hw < 4.2
        band = ((hw > 4.2) & (hw < 4.8)) | ((hw > 11.4) & (hw < 11.9))
        frieze = (hw > E - 1.6) & (hw < E - 0.4)
        fz = np.where(np.mod(np.floor(a / 0.9), 3) == 0, zb, np.where(np.mod(np.floor(a / 0.9), 3) == 1, zy, zg))
        wall = np.where(socle, np.where(np.mod(hw, 0.7) < 0.15, brick2, cream), np.where(band, cream,
                        np.where(frieze, fz, np.where(np.mod(np.floor(hw * 3) + np.floor(a * 1.5), 7) == 0, brick2,
                                                      brick))))
        o = np.where(inside & wing & (hw < E), wall, 0)
        rise = np.clip(np.minimum(d, 2 * W0 - d) * 1.15, 0, 8.0)
        rf = inside & wing & (hw >= E) & (hw < E + rise)
        diamond = (np.mod(np.abs(np.mod(a, 3.0) - 1.5) + np.abs(np.mod(hw, 3.0) - 1.5), 3.0) < 0.9)
        o = np.where(rf, np.where(diamond, zy, zg), o)
        hall = inside & ~wing
        o = np.where(hall & (hw < 15.0), cream, o)
        o = np.where(hall & (hw >= 15.0) & (hw < 15.6), steel, o)
        glazed = hall & (hw >= 15.6) & (hw < 15.6 + np.minimum((d - 2 * W0) * 0.35, 4.0))
        return np.where(glazed, np.where(np.mod(a, 2.4) < 0.3, steel, glass), o)
    block(S, g, fr, b0, E + 8.5, fn)
    tg = [brick, brick2, cream]
    windows(S, g, b0, [(1.2, 3.6)], tg, win, every=3.4, half=0.6, min_len=4.0, arch=False)
    windows(S, g, b0, [(5.8, 10.6), (12.6, 16.6)], tg, win, every=3.4, half=0.75, min_len=4.0, arch=True)
    # the main dome over the entrance on Üllői út, striped in green and yellow tiles, a lantern on top
    fd = Frame(1686.0, 4296.0, b0, 0)
    S.add(Lathe(fd, E - 2.0, E + 4.0, cyl(6.4), brick, n=8))
    S.add(Lathe(fd, E + 4.0, E + 4.8, cyl(6.8), cream, n=8))
    S.add(Lathe(fd, E + 4.8, E + 12.5, dome(6.6, 1.6, 1.2), zg, n=8))
    for k in range(8):
        t = (k + 0.5) * math.pi / 4
        S.add(Box(Frame(1686.0 + 3.4 * math.cos(t), 4296.0 + 3.4 * math.sin(t), b0, t), -2.6, 2.6, -0.5, 0.5,
                  E + 4.8, E + 10.5, zy, mode="paint", targets=[zg]))
    S.add(Lathe(fd, E + 12.0, E + 14.5, cyl(1.3), zy, n=8))
    S.add(Lathe(fd, E + 14.5, E + 17.0, cone(1.5, 0.08), zg, n=8))
    S.add(Ellipsoid(fd.at(0, 0, E + 17.2), 0.3, 0.3, 0.3, gold))
    # the entrance's portal under it: a tall arch in cream ceramic
    fe = Frame(1693.5, 4300.0, b0, math.radians(-77.0 + 90))
    S.add(Box(fe, -0.3, 1.2, -4.8, 4.8, 0.0, 13.0, cream))
    S.add(Arch(fe, 0.2, 1.3, 0.0, 2.6, 0.0, 7.0, win))
    S.add(Arch(fe, 1.0, 1.3, 0.0, 3.2, 0.0, 7.6, zy, mode="paint", targets=[cream]))
    # the tower over the north range and the corner turrets
    ft = Frame(1641.0, 4276.0, b0, math.radians(5.0))
    S.add(Box(ft, -3.2, 3.2, -3.2, 3.2, -1.0, E + 7.0, brick))
    S.add(Box(ft, -3.5, 3.5, -3.5, 3.5, E + 6.4, E + 7.4, cream))
    for k in range(4):
        windows_on(S, side(ft, k), 3.2, -2.0, 2.0, 2.0, [(E + 1.5, E + 5.5)], 0.6, win, [brick])
    S.add(Lathe(ft, E + 7.4, E + 19.0, cone(4.4, 0.1), zg, n=4, rot=math.pi / 4))
    S.add(Lathe(ft, E + 7.4, E + 9.0, cyl(4.0), zy, n=4, rot=math.pi / 4, mode="paint", targets=[zg]))
    for x, y in ((1615.0, 4266.0), (1667.0, 4266.0), (1610.0, 4294.0), (1690.0, 4346.0), (1627.0, 4347.0)):
        S.add(Lathe(Frame(x, y, b0), E - 2.0, E + 3.0, cyl(2.2), brick, n=8))
        S.add(Lathe(Frame(x, y, b0), E + 3.0, E + 6.5, dome(2.4, 1.6, 0.3), zg, n=8))
        S.add(Lathe(Frame(x, y, b0), E + 6.3, E + 7.8, cone(0.4, 0.05), gold))
    S.clear.append((1650.0, 4305.0, 30.0))


# ------------------------------------------------------------------------------------------------ Semmelweis
def semmelweis(S, ctx, plan):
    """Semmelweis University's building at Üllői út 26: the street front a Neo-Renaissance palazzo in red brick over a
    rusticated stone ground floor, paired arched windows, stone cornices and a tiled hipped roof; behind it the
    cream range under a grey roof."""
    P = ctx["P"]
    g = keep(ctx, SEMMELWEIS)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(1694.35, 4160.6, b0, math.radians(-12.9))  # +u from the front on Üllői út into the block
    brick, brick2, stone, stone2 = P("#b25a40"), P("#9f4e37"), P("#ddd5c3"), P("#c9c0ad")
    cream, cream2 = P("#e9dcb8"), P("#d8c9a2")
    tile, slate = P("#9c4a36", ROOF), P("#7b8287", ROOF)
    win = P("#30383a", WINDOW)
    E, D = 20.5, 24.0

    def fn(d, U, V, a, hw):
        inside = d > 0
        palazzo = U < D
        socle = hw < 6.0
        band = ((hw > 6.0) & (hw < 6.8)) | ((hw > 13.0) & (hw < 13.5))
        quoin = (np.abs(np.abs(V) - 16.0) < 1.2) | (np.abs(U - D) < 0.6)
        pw = np.where(socle, np.where(np.mod(hw, 0.85) < 0.18, stone2, stone),
                      np.where(band | quoin, stone, np.where(np.mod(np.floor(hw * 3) + np.floor(a * 1.4), 6) == 0,
                                                              brick2, brick)))
        cw = np.where(socle, cream2, np.where(np.mod(hw, 3.6) < 0.35, cream2, cream))
        o = np.where(inside & (hw < E), np.where(palazzo, pw, cw), 0)
        o = np.where(inside & (d < 1.0) & (hw >= E - 1.0) & (hw < E), stone, o)
        rise = np.minimum(d * 0.75, 5.5)
        rf = inside & (hw >= E) & (hw < E + rise)
        return np.where(rf, np.where(palazzo, tile, slate), o)
    block(S, g, fr, b0, E + 6.5, fn)
    tg = [brick, brick2, stone, stone2, cream, cream2]
    windows(S, g, b0, [(1.6, 4.8)], tg, win, every=3.9, half=0.8, min_len=4.0, arch=True)
    windows(S, g, b0, [(8.0, 12.0), (14.6, 18.6)], tg, win, every=3.9, half=0.55, min_len=4.0, arch=True)
    ff = side(fr, 2)  # +u out of the front
    S.add(Box(ff, -0.2, 0.9, -3.0, 3.0, 0.0, 6.6, stone))  # the portal
    S.add(Arch(ff, 0.3, 1.0, 0.0, 1.6, 0.0, 3.6, win))
    S.add(Box(ff, -0.2, 1.4, -3.4, 3.4, 6.6, 7.1, stone))  # its balcony
    S.clear.append((1718.0, 4155.0, 22.0))


# ------------------------------------------------------------------------------------------------ Slovak church
def slovak(S, ctx, plan):
    """the former Slovak Lutheran church (1863-67) in the court behind Rákóczi út 57: a small Romantic hall church in
    ochre render with white trim, its tower over the north front with a green copper spire, a crossing under hipped
    tile roofs and a polygonal apse; reached from Rákóczi út through the house's tall arched gateway and across the
    court, both carved and paved here."""
    P = ctx["P"]
    g = keep(ctx, SLOVAK)
    b0 = base_under(ctx, g, 0.4)
    ang = math.radians(108.9)
    fr, L, hw_ = axis_frame(g, ang, b0)  # +u from the north front to the apse
    ochre, ochre2, white = P("#d8bf8e"), P("#c7ab78"), P("#efe9dc")
    tile, tile2, copper = P("#a65a3e", ROOF), P("#8f4d36", ROOF), P("#5f9a82", METAL)
    zinc = P("#a9adab", ROOF)
    win, door = P("#2f3536", WINDOW), P("#4b3527")
    pave = P("#9c968b")
    E = 11.0

    def fn(d, U, V, a, hw):
        inside = d > 0
        band = (np.mod(hw, 5.5) < 0.4) | (hw < 0.8)
        o = np.where(inside & (hw < E), np.where(band, white, ochre), 0)
        o = np.where(inside & (d < 0.8) & (hw >= E - 0.6) & (hw < E), white, o)
        rise = np.minimum(d * 0.95, 8.5)
        rf = inside & (hw >= E) & (hw < E + rise)
        return np.where(rf, np.where(U > L - 7, zinc, np.where(np.mod(np.floor(hw * 2), 3) == 0, tile2, tile)), o)
    block(S, g, fr, b0, E + 9.5, fn)
    windows(S, g, b0, [(3.0, 8.8)], [ochre, white], win, every=4.0, half=0.8, min_len=4.0, arch=True)
    # the tower over the north front, its spire in green copper
    ft = fr.at(3.6, 0.0)
    S.add(Box(ft, -3.4, 3.4, -3.4, 3.4, -1.0, 24.0, ochre))
    for w in (E, 18.0):
        S.add(Box(ft, -3.6, 3.6, -3.6, 3.6, w - 0.4, w + 0.2, white))
    S.add(Box(ft, -3.8, 3.8, -3.8, 3.8, 23.4, 24.2, white))
    for k in range(4):
        windows_on(S, side(ft, k), 3.4, -1.0, 1.0, 2.0, [(19.0, 22.6)], 0.55, win, [ochre])
    S.add(Lathe(ft, 24.2, 25.4, cyl(3.0), copper, n=8))
    S.add(Lathe(ft, 25.4, 36.0, cone(2.8, 0.06), copper, n=8))
    S.add(Lathe(ft, 36.0, 37.6, cyl(0.07), P("#d6b04e", METAL)))
    fn_ = side(fr, 2)  # +u out of the north front
    S.add(Arch(fn_, -0.6, 0.4, 0.0, 1.3, 0.0, 3.0, door))
    S.add(Arch(fn_, 0.0, 0.5, 0.0, 1.9, 0.0, 3.3, white, mode="paint", targets=[ochre, white]))
    # the gateway through Rákóczi út 57 along OSM's passage, then the court's paving to the church door
    gate = LineString([(2918.3, 3614.5), (2911.6, 3633.0)])
    (x0, y0), (x1, y1) = gate.coords
    fg = Frame(x0, y0, 0, math.atan2(y1 - y0, x1 - x0))
    zg = ctx["ground_m"](x0 - 2 * fg.ca, y0 - 2 * fg.sa)
    fg = Frame(x0, y0, zg, fg.ang)
    Lg = gate.length
    S.add(Arch(fg, -0.6, Lg + 0.6, 0.0, 2.3, 0.0, 4.6, 0, mode="carve"))
    S.add(Box(fg, -0.6, Lg + 0.6, -2.3, 2.3, -0.6, 0.0, pave))
    for u in (-0.6, Lg + 0.1):  # the stone frames of the arch at both ends
        S.add(Arch(fg, u, u + 0.5, 0.0, 2.9, 0.0, 4.6, white))
        S.add(Arch(fg, u - 0.1, u + 0.6, 0.0, 2.3, 0.0, 4.6, 0, mode="carve"))
    dx, dy = fr.xy(-0.5, 0.0)
    court = LineString([(x1, y1), (dx, dy)]).buffer(1.8, cap_style=2)
    zc = min(zg, b0)
    S.add(Poly(court, zc - 0.6, b0 + 0.05, pave))
    S.clear.append((2910.0, 3640.0, 12.0))
    S.clear.append((2903.0, 3662.0, 20.0))


# ------------------------------------------------------------------------------------------------ St Margaret, Lehel tér
def margit(S, ctx, plan):
    """St Margaret's at Lehel tér (Aladár and Bertalan Árkay, 1933), modelled on the Romanesque abbey church of
    Zsámbék: a basilica in pale yellow limestone, two square west towers under steep stone pyramids, a high nave with
    round-arched clerestory windows over lean-to aisles, a transept and a round apse, grey roofs."""
    P = ctx["P"]
    g = keep(ctx, MARGIT)
    b0 = base_under(ctx, g, 0.4)
    fr = Frame(3478.15, 1367.7, b0, math.radians(-17.5))  # +u from the west front towards the apse
    stone, stone2, stone3 = P("#dccb9f"), P("#cbb98b"), P("#b9a679")
    slate, slate2 = P("#5c6168", ROOF), P("#6a7077", ROOF)
    win, door = P("#2f3436", WINDOW), P("#4a3a2c")
    tg = [stone, stone2]

    def wall(u, v, w):
        return np.where(np.mod(np.floor(w * 2) + np.floor((u + v) * 1.2), 9) == 0, stone2, stone)
    # the aisles, the nave and its clerestory
    S.add(Box(fr, 5.0, 33.5, -10.4, 10.4, -2.0, 8.5, wall))
    for k in range(6):  # the aisles' lean-to roofs, stepped
        S.add(Box(fr, 5.0, 33.5, -10.6 + k * 0.6, 10.6 - k * 0.6, 8.5 + k * 0.45, 8.95 + k * 0.45, slate))
    S.add(Box(fr, 5.0, 33.5, -5.8, 5.8, 8.5, 17.0, wall))
    S.add(Box(fr, 4.8, 33.7, -6.1, 6.1, 16.6, 17.2, stone3))
    S.add(Roof(fr, 5.0, 33.5, -6.4, 6.4, 17.2, 6.4, slate))
    for k, (v0, v1) in ((1, (-33.0, -6.0)), (3, (6.0, 33.0))):  # side 1 faces +v, its v runs along -u
        windows_on(S, side(fr, k), 5.8, v0, v1, 3.4, [(11.0, 15.2)], 0.65, win, tg)
        windows_on(S, side(fr, k), 10.4, v0, v1, 3.4, [(3.0, 6.6)], 0.55, win, tg)
    # the transept and the apse
    S.add(Box(fr, 33.5, 44.5, -16.5, 16.5, -2.0, 15.5, wall))
    S.add(Box(fr, 33.3, 44.7, -16.8, 16.8, 15.1, 15.7, stone3))
    S.add(Roof(side(fr.at(39.0, 0.0), 1), -16.8, 16.8, -5.7, 5.7, 15.7, 5.6, slate2))
    S.add(Roof(fr, 33.5, 44.5, -6.4, 6.4, 17.2, 6.4, slate))
    for k in (1, 3):
        windows_on(S, side(fr.at(39.0, 0.0), k), 16.5, -3.5, 3.5, 3.5, [(5.0, 12.0)], 0.9, win, tg)
    fa = fr.at(44.5, 0.0)
    S.add(Lathe(fa, -2.0, 13.5, cyl(6.6), wall, n=24))
    S.add(Box(fr, 37.0, 44.5, -6.6, 6.6, -2.0, 13.5, wall))
    S.add(Lathe(fa, 13.5, 18.0, cone(6.9, 0.3), slate2, n=24))
    for k in range(5):
        t = math.radians(-60 + k * 30)
        S.add(Arch(Frame(*fr.xy(44.5 + 6.2 * math.cos(t), 6.2 * math.sin(t)), b0, fr.ang + t), -0.6, 0.8, 0.0, 0.6,
                   4.0, 9.0, win, mode="paint", targets=tg))
    # the west front: the towers, the gable between them, the stepped portal
    S.add(Box(fr, 0.0, 5.5, -6.0, 6.0, -2.0, 19.0, wall))
    S.add(Roof(side(fr.at(2.75, 0.0), 0), -2.75, 2.75, -6.2, 6.2, 19.0, 5.5, slate))
    for sv in (-1, 1):
        ft = fr.at(3.6, sv * 8.6)
        S.add(Box(ft, -3.6, 3.6, -3.6, 3.6, -2.0, 33.0, wall))
        for w in (10.0, 19.0, 26.0):
            S.add(Box(ft, -3.8, 3.8, -3.8, 3.8, w - 0.5, w, stone3))
        for k in range(4):
            windows_on(S, side(ft, k), 3.6, -1.6, 1.6, 1.6, [(27.5, 31.5)], 0.45, win, tg)
            windows_on(S, side(ft, k), 3.6, -0.8, 0.8, 1.6, [(20.5, 24.5)], 0.5, win, tg)
        S.add(Box(ft, -3.9, 3.9, -3.9, 3.9, 32.6, 33.4, stone3))
        S.add(Lathe(ft, 33.4, 45.0, cone(5.4, 0.1), stone2, n=4, rot=math.pi / 4))
        S.add(Lathe(ft, 45.0, 46.4, cyl(0.08), P("#c9a24a", METAL)))
    fw = side(fr, 2)  # +u out of the west front
    for k in range(4):
        S.add(Arch(fw, -0.2 + k * 0.0, 0.5 + k * 0.45, 0.0, 3.2 - k * 0.5, 0.0, 4.4, stone3 if k % 2 else stone))
    S.add(Arch(fw, -0.6, 2.4, 0.0, 1.5, 0.0, 3.4, door))
    S.add(Arch(fw, -0.6, 0.3, 0.0, 1.8, 10.0, 11.8, win, mode="paint", targets=tg))  # the rose window's place
    S.clear.append((3500.0, 1360.0, 32.0))


# ------------------------------------------------------------------------------------------------ Arena Mall
def arena(S, ctx, plan):
    """Arena Mall (2007) along Kerepesi út: a long white box banded in glass, the taller dark block of the cinema at
    its north-west end, a flat roof with three elliptical glass domes over the mall's courts."""
    P = ctx["P"]
    g = keep(ctx, ARENA)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(3728.4, 4379.6, b0, math.radians(41.6))  # +u along Kerepesi út from the north-west end
    white, white2, grey = P("#e8e8e4"), P("#d5d6d2"), P("#8b9094")
    glass, glass2 = P("#7a93a3", GLASS), P("#5f7584", GLASS)
    roof, roof2, dark = P("#b9bcbc", ROOF), P("#b1b4b4", ROOF), P("#4f5559", ROOF)
    E, Ec = 19.0, 25.0

    def fn(d, U, V, a, hw):
        inside = d > 0
        cine = U < 62.0
        top = np.where(cine, Ec, E)
        bands = (hw > 4.5) & (np.mod(hw - 4.5, 5.0) < 2.4)
        wall = np.where(hw < 4.5, np.where(np.mod(a, 7.5) < 1.0, white2, glass2),
                        np.where(cine, np.where(np.mod(a, 3.0) < 0.4, grey, glass2),
                                 np.where(bands & (np.mod(a, 9.0) > 1.0), glass, white)))
        o = np.where(inside & (hw < top), wall, 0)
        o = np.where(inside & (d < 0.8) & (hw >= top) & (hw < top + 1.0), np.where(cine, grey, white2), o)
        rf = inside & (d >= 0.8) & (hw >= top - 0.5) & (hw < top)
        return np.where(rf, np.where(cine, dark, np.where(np.mod(np.floor(U / 6.0) + np.floor(V / 6.0), 2) == 0,
                                                           roof, roof2)), o)
    block(S, g, fr, b0, Ec + 1.5, fn)
    # the three domes over the courts
    for x, y in ((3855.4, 4413.9), (3903.3, 4456.0), (3951.2, 4499.7)):
        e = shapely.affinity.rotate(shapely.affinity.scale(Point(x, y).buffer(1.0, 32), 8.0, 6.4), 41.6, origin=(x, y))
        S.add(Poly(e, b0 + E - 0.5, b0 + E + 1.6, white2))
        S.add(Ellipsoid(Frame(x, y, b0 + E + 1.6, fr.ang), 7.4, 5.8, 2.2, glass2))
    # the main entrance on Kerepesi út: a glass bay through the box's height with the name over it
    fe = Frame(3903.15, 4372.2, b0, math.radians(41.7 - 90.0))  # +u out of the wall facing the stairs
    S.add(Box(fe, -2.5, 0.8, -9.0, 9.0, 0.0, E - 1.0, glass))
    letters(S, fe, 0.8, 0.0, E - 6.5, "ARENA", 3.4, white, step=3.6)
    S.clear.append((3900.0, 4455.0, 120.0))


# ------------------------------------------------------------------------------------------------ MTK Sportpark
def mtk(S, ctx, plan):
    """the MTK Sportpark hall (2023) on Kerepesi út: a box of pale ribbed panels on a glazed ground floor, set on a
    lower podium that wraps its south and east sides, the roof striped with long skylights."""
    P = ctx["P"]
    g = keep(ctx, MTK)
    b0 = base_under(ctx, g, 0.3)
    fr = Frame(4199.6, 4689.9, b0, math.radians(109.0))  # +u along the long west side from the north
    panel, panel2, white = P("#d6d0c2"), P("#c3bcab"), P("#ecebe6")
    glass, glass2 = P("#7f97a1", GLASS), P("#647b86", GLASS)
    roof, sky, plinth = P("#c7bea8", ROOF), P("#3c4a52", GLASS), P("#9b9488")
    E, Ep = 19.0, 8.0

    def fn(d, U, V, a, hw):
        inside = d > 0
        bd = np.minimum(np.minimum(U + 3.0, 110.0 - U), np.minimum(V + 64.0, -3.5 - V))
        box = inside & (bd > 0)
        top = np.where(box, E, Ep)
        shell = np.where(box, bd < 0.8, d < 0.8)
        wall = np.where(hw < 4.6, np.where(np.mod(a, 6.0) < 0.6, plinth, glass2),
                        np.where(box, np.where(np.mod(a, 1.6) < 0.5, panel2, panel), white))
        o = np.where(inside & (hw < top), np.where(shell, wall, white), 0)
        rf = inside & ~shell & (hw >= top - 0.6) & (hw < top)
        stripes = box & (np.mod(V, 6.2) < 1.4) & (bd > 6.0)
        o = np.where(rf, np.where(stripes, sky, roof), o)
        return np.where(inside & shell & (hw >= top) & (hw < top + 0.9), white, o)
    block(S, g, fr, b0, E + 1.5, fn)
    S.clear.append((4213.0, 4755.0, 70.0))


BUILDERS = [("Corvin Cinema", corvin_mozi), ("Corvin Plaza", corvin_plaza), ("Museum of Applied Arts", iparmu),
            ("Semmelweis University", semmelweis), ("Slovak Lutheran Church", slovak),
            ("St Margaret's Church", margit), ("Arena Mall", arena), ("MTK Sportpark", mtk)]
