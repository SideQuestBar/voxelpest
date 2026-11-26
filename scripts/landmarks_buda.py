"""Buda: the Sándor Palace on Szent György tér and the CH building of the Technical University at Szent Gellért tér,
placed on OSM's outlines and detailed from the aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np
import shapely
from shapely.geometry import Point

from landmarks import WINDOW, Box, Ellipsoid, Field, Frame, Lathe, Poly, Roof, cone, cyl
from landmarks_city import base_under, dist_in, grid_of, windows
from landmarks_hosok import column, keep, massing, side, windows_on
from style import CLASSIC, METAL, ROOF

SANDOR, CH = 165910, 7009471

NAMES = ["Sándor Palace", "BME CH building"]
DROP = {SANDOR, CH}
KEEP = [(SANDOR, 17), (CH, 21)]


def edge_frame(a, b, z):
    """a frame on the wall from a to b: +u along it (+v is +u turned a quarter towards grid +y)."""
    return Frame((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z, math.atan2(b[1] - a[1], b[0] - a[0]))


# ------------------------------------------------------------------------------------------------ Sándor Palace
def sandor(S, ctx, plan):
    """the Sándor Palace (Mihály Pollack, János Aman, 1806; the President's seat): a white Neoclassical block round a
    court, rusticated ground floor, the piano nobile's windows under little pediments, a five-bay centre with a relief
    frieze and a pediment dated MDCCCVI, the entrance porch below carrying the balcony, guards' boxes either side; a
    red-brown tiled hipped roof. The ground falls away towards the Danube, so the east side shows more storeys."""
    P = ctx["P"]
    g = keep(ctx, SANDOR)
    a, b = (4138.3, 2854.7), (4179.2, 2866.6)
    fr = edge_frame(a, b, 0)
    gx, gy = fr.ox - 6 * math.sin(fr.ang), fr.oy + 6 * math.cos(fr.ang)
    b0 = ctx["ground_m"](gx, gy)
    fr = Frame(fr.ox, fr.oy, b0, fr.ang)
    white, white2, rust, trim = P("#efede6"), P("#e2ded2"), P("#d6d1c3"), P("#f6f4ee")
    stone, relief = P("#d9cfb8"), P("#cfc8b6")
    roof, roof2 = P("#7e4b3e", ROOF), P("#6f4136", ROOF)
    win, green = P("#3b4744", WINDOW), P("#6f7d70", METAL)
    E = 15.6

    def wall(d, a_, hw):
        r = (hw < 5.2) & (np.mod(hw, 0.75) < 0.16)
        band = ((hw > 5.2) & (hw < 5.9)) | ((hw > 10.3) & (hw < 10.7))
        return np.where(r, rust, np.where(band, white2, np.where(hw < 5.2, white2, white)))

    massing(S, g, b0, E, wall, roof, pitch=0.8, rmax=6.2, cornice=trim, base=rust, lower=-14.0)
    targets = [white, white2, rust]
    windows(S, g, b0, [(1.6, 4.2)], targets, win, every=3.7, half=0.65, min_len=6.0, arch=True)
    windows(S, g, b0, [(6.6, 9.6), (11.6, 14.0)], targets, win, every=3.7, half=0.7, min_len=6.0, arch=False)
    # the river side: the storeys below the square's level
    windows(S, g, b0 - 7.0, [(1.4, 4.0), (4.6, 6.4)], targets, win, every=3.7, half=0.6, min_len=6.0, arch=False)

    ff = side(fr, 1)  # +u out of the front, +v along it towards the west
    L = float(np.hypot(b[0] - a[0], b[1] - a[1]))
    # the centre comes forward by 0.6 m, five bays wide
    S.add(Box(ff, -1.0, 0.6, -8.6, 8.6, -1.5, E, white))
    S.add(Box(ff, -1.0, 0.6, -8.6, 8.6, -1.5, 5.2, white2))
    for k in range(7):
        S.add(Box(ff, 0.6, 0.75, -8.6, 8.6, 0.6 + k * 0.75, 0.75 + k * 0.75, rust))
    S.add(Box(ff, -1.0, 0.85, -8.9, 8.9, E - 0.7, E, trim))
    S.add(Box(ff, 0.6, 0.7, -6.8, 6.8, 10.0, 11.3, relief))  # the relief frieze
    windows_on(S, ff, 0.6, -8.6, 8.6, 3.44, [(6.6, 9.6)], 0.7, win, [white], arch=False, depth=0.5)
    windows_on(S, ff, 0.6, -8.6, 8.6, 3.44, [(11.6, 14.0)], 0.6, win, [white], arch=False, depth=0.5)
    # the pediment, its tympanum set back
    S.add(Roof(ff, -6.0, 0.9, -9.0, 9.0, E, 3.9, trim))
    S.add(Roof(ff, 0.55, 0.95, -8.2, 8.2, E + 0.35, 3.2, white2, mode="carve"))
    S.add(Roof(ff, 0.3, 0.55, -8.2, 8.2, E + 0.35, 3.2, white2))
    S.add(Box(ff, 0.4, 0.6, -2.4, 2.4, E + 0.9, E + 1.5, relief))  # MDCCCVI
    # little pediments over the piano nobile's windows on the front
    n = int(L // 3.7)
    for k in range(n):
        v = -L / 2 + (L - (n - 1) * 3.7) / 2 + k * 3.7
        uo = 0.6 if abs(v) < 8.6 else 0.0
        S.add(Box(ff, uo, uo + 0.3, v - 0.95, v + 0.95, 9.75, 9.95, trim))
        S.add(Roof(ff.at(0, 0, 0), uo, uo + 0.35, v - 1.0, v + 1.0, 9.95, 0.55, trim))
    # the corners' quoins
    for v in (-L / 2 + 0.6, L / 2 - 0.6):
        for k in range(int(E / 0.9)):
            w = 0.2 + k * 0.9
            S.add(Box(ff, -0.3, 0.15, v - (0.7 if k % 2 else 0.45), v + (0.7 if k % 2 else 0.45), w, w + 0.6, trim))
    # the porch: four stone piers, the balcony on top with its iron railing
    S.add(Box(ff, 0.6, 4.4, -5.2, 5.2, -1.2, 0.3, stone))
    for v in (-4.6, -1.6, 1.6, 4.6):
        S.add(Box(ff, 3.3, 4.2, v - 0.45, v + 0.45, 0.3, 5.0, stone))
        S.add(Box(ff, 3.2, 4.3, v - 0.55, v + 0.55, 4.6, 5.0, trim))
    S.add(Box(ff, 0.6, 4.5, -5.3, 5.3, 5.0, 5.7, stone))
    S.add(Box(ff, 4.25, 4.45, -5.2, 5.2, 5.7, 6.7, green))
    S.add(Box(ff, 0.6, 4.45, 5.0, 5.2, 5.7, 6.7, green))
    S.add(Box(ff, 0.6, 4.45, -5.2, -5.0, 5.7, 6.7, green))
    S.add(Box(ff, 0.3, 0.7, -1.4, 1.4, 0.3, 4.4, win))  # the gate
    # the guards' boxes
    for v in (-6.6, 6.6):
        S.add(Box(ff, 4.8, 6.0, v - 0.6, v + 0.6, 0.0, 2.5, green))
        S.add(Lathe(ff.at(5.4, v, 0), 2.5, 3.4, cone(0.9, 0.05), green, n=4, rot=math.pi / 4))
        S.add(Box(ff, 5.9, 6.05, v - 0.3, v + 0.3, 0.8, 2.1, win))
    S.clear.append((fr.ox, fr.oy, 12.0))


# ------------------------------------------------------------------------------------------------ BME CH
def ch(S, ctx, plan):
    """the CH building of the Technical University (Győző Czigler, 1904-09; chemistry): four storeys of orange-red
    brick over a stone ground floor, cream stone bands and window frames, arched windows above; the curved corner on
    Szent Gellért tér in cream stone with an attic of urns, a dark hipped roof over it, red tile roofs on the wings;
    the hall roof in the court."""
    P = ctx["P"]
    g = keep(ctx, CH)
    b0 = base_under(ctx, g, 0.3)
    brick, brick2 = P("#b8664a"), P("#a8583f")
    cream, cream2, socle = P("#e6d8bb"), P("#d6c6a5"), P("#c3b597")
    tile, tile2 = P("#b4563d", ROOF), P("#9f4a35", ROOF)
    slate = P("#5f6f6a", ROOF)
    win = P("#34393b", WINDOW)
    hallr, glass = P("#c9cdcc", METAL), P("#9fb4b8", METAL)
    E = 20.5
    pav = (3956.0, 4929.0)  # the south front's centre pavilion under its dark hipped roof

    def wall(d, a_, hw):
        x = (a_ - 8872.0)
        stone = (hw < 5.0)
        band = ((hw > 5.0) & (hw < 5.6)) | ((hw > 15.4) & (hw < 15.9))
        pil = np.mod(x, 7.4) < 1.0
        br = np.where(np.mod(np.floor(hw * 3) + np.floor(x * 1.5), 9) == 0, brick2, brick)
        rus = stone & (np.mod(hw, 0.8) < 0.18)
        return np.where(rus, cream2, np.where(stone, socle, np.where(band | pil, cream, br)))
    x0f, y0f, X, Y = grid_of(g, 1.0)
    d = dist_in(g, X, Y)
    near = (Y > 4917.0).astype(np.float32)  # the south front and the curved corner, in cream stone
    fields = dict(d=d, a=(X + Y).astype(np.float32), c=near)
    pat = np.array([tile, tile2], np.uint16)

    def fn(f, wa):
        d_, a_, c_ = f["d"][None], f["a"][None], f["c"][None] > 0
        hw = wa - b0
        body = (d_ > 0) & (hw >= -3) & (hw < E)
        col = np.where(c_ & (hw >= 5.0), np.where(np.mod(hw, 5.2) < 0.5, cream2, cream), wall(d_, a_, hw))
        cornice = (d_ > 0) & (d_ < 1.2) & (hw > E - 0.8) & (hw < E)
        attic = c_ & (d_ > 0) & (d_ < 0.7) & (hw >= E) & (hw < E + 1.3) & ((np.mod(a_, 2.4) < 1.0) | (hw > E + 0.9))
        rise = np.minimum(d_ * 0.9, 5.5)
        roof = (d_ > 0) & (hw >= E + 0.9 * c_) & (hw < E + rise)
        o = np.where(body, col, 0)
        o = np.where(cornice, cream, o)
        o = np.where(attic, cream, o)
        o = np.where(roof, pat[np.mod(np.floor(hw * 2).astype(np.int64), 2)], o)
        return o.astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 3, b0 + E + 6.5, fn))
    targets = [brick, brick2, cream, cream2, socle]
    windows(S, g, b0, [(1.4, 4.2)], targets, win, every=3.7, half=0.7, min_len=5.0, arch=False)
    windows(S, g, b0, [(6.4, 9.8), (11.2, 14.6)], targets, win, every=3.7, half=0.7, min_len=5.0, arch=False)
    windows(S, g, b0, [(16.4, 19.6)], targets, win, every=3.7, half=0.7, min_len=5.0, arch=True)
    # the pavilion's dark hipped roof with a lantern; red hips over the cream front either side
    fc = Frame(*pav, b0, 0)
    S.add(Lathe(fc, E, E + 7.0, cone(8.5, 1.6), slate, n=4, rot=math.pi / 4 + math.radians(5)))
    S.add(Lathe(fc, E + 7.0, E + 8.6, cyl(1.2), cream, n=8))
    S.add(Lathe(fc, E + 8.6, E + 10.0, cone(1.4, 0.1), slate, n=8))
    # the hall in the court: a long low roof of metal and glass
    if g.interiors:
        hole = shapely.Polygon(g.interiors[0]).buffer(-1.5)
        if not hole.is_empty:
            S.add(Poly(hole, b0 - 1, b0 + 9.0, cream2))
            S.add(Poly(hole.buffer(-1.0), b0 + 9.0, b0 + 10.2, hallr))
            S.add(Poly(hole.buffer(-3.5), b0 + 10.2, b0 + 11.0, glass))


BUILDERS = [("Sándor Palace", sandor), ("BME CH building", ch)]
