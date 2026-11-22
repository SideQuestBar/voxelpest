"""Late November 2026, fourth round, Buda and Terézváros: MOM Park, the Reformed church on Szilágyi Dezső tér,
Batthyány tér (St Anne's and the market hall), and St Teresa of Avila in Terézváros. Outlines from OSM; heights,
colours and details from the Esri aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np

from landmarks import WINDOW, Arch, Box, Ellipsoid, Frame, Lathe, Roof, cone, cyl, dome, onion, rect_of, zsolnay
from landmarks_city import base_under
from landmarks_hosok import keep, side
from landmarks_kit import largest, painted
from style import GLASS, METAL, ROOF

MOM = 197546072
SZILAGYI = 249932064
ANNA, ANNA_HOUSE, BATTHYANY_HALL = 243689215, 549685951, 50880840
TERESA, TERESA_TOWER, TERESA_SACRISTY = 25215160, 259204131, 472745558

NAMES = ["MOM Park", "Szilágyi Dezső tér Reformed Church", "St Anne's, Batthyány tér", "Batthyány tér market hall",
         "St Teresa of Avila, Terézváros"]
DROP = {MOM, SZILAGYI, ANNA, BATTHYANY_HALL, TERESA, TERESA_TOWER, TERESA_SACRISTY}
KEEP = [(MOM, 20), (SZILAGYI, 18), (ANNA, 18), (BATTHYANY_HALL, 14), (TERESA, 18)]
TAU = 2 * math.pi


# ------------------------------------------------------------------------------------------------ MOM Park
def mom_park(S, ctx, plan):
    """MOM Park (2001) on Alkotás utca: a mall and offices of five floors in pale travertine with grids of square
    windows, bands of blue-green glass between the stone blocks and over the entrances, deep canopies on steel posts,
    and the rounded glass corner on Csörsz utca with its louvred crown."""
    P = ctx["P"]
    g = largest(keep(ctx, MOM))
    b0 = base_under(ctx, g, 0.3)
    trav, trav2, glass, glass2, win = P("#e3d9c4"), P("#d5cab3"), P("#3f6a74", GLASS), P("#4f7c86", GLASS), P("#2f3a40", GLASS)
    roof, green, steel = P("#a9aca8", ROOF), P("#3f8a6c", ROOF), P("#4b5257", METAL)
    E = 20.0
    corner = np.array([2350.0, 1718.0])

    def fn(f, hw):
        d, s, X, Y = f["d"], f["s"], f["X"], f["Y"]
        inside, edge = d > 0, (d > 0) & (d < 0.9)
        zone = np.mod(np.floor(s / 26.0), 3)
        fl = np.mod(hw, 3.8)
        squares = (fl > 1.0) & (fl < 2.6) & (np.abs(np.mod(s, 2.6) - 1.3) < 0.7)
        stone = np.where(squares, win, np.where(np.mod(hw, 1.9) < 0.12, trav2, trav))
        band = np.where((np.mod(s, 1.5) < 0.15) | (fl < 0.25), steel, np.where(np.mod(np.floor(hw / 3.8), 2) == 0, glass, glass2))
        wall = np.where(zone == 1, band, stone)
        near = np.hypot(X - corner[0], Y - corner[1]) < 18.0
        wall = np.where(near, band, wall)
        wall = np.where(hw < 4.5, np.where(np.mod(s, 3.0) < 0.3, steel, glass), wall)
        o = np.where(edge & (hw < E), wall, 0)
        o = np.where(inside & ~edge & (hw >= E - 0.6) & (hw < E), np.where(d < 6.0, green, roof), o)
        o = np.where(edge & (hw >= E) & (hw < E + 1.0), trav2, o)
        crown = near & edge & (hw >= E) & (hw < E + 8.0) & ((np.mod(hw, 1.0) < 0.35) | (np.mod(s, 2.0) < 0.3))
        o = np.where(crown, steel, o)
        o = np.where(near & inside & (hw >= E + 7.6) & (hw < E + 8.0), steel, o)
        return o
    painted(S, g, b0, E + 8.5, fn)


# ------------------------------------------------------------------------------------------------ Szilágyi Dezső tér
def szilagyi(S, ctx, plan):
    """the Reformed church on Szilágyi Dezső tér (Samu Pecz, 1893-96): Neo-Gothic in red brick with stone dressings,
    a hall on a Greek cross with three polygonal arms to the south-west, a big gable with a rose window to the Danube,
    and the tall tower at the north-eastern corner with its slender stone spire; the roofs in brown, yellow and green
    glazed Zsolnay tiles."""
    P = ctx["P"]
    g = keep(ctx, SZILAGYI)
    b0 = base_under(ctx, g, 0.3)
    brick, brick2, stone, win = P("#b0583f"), P("#9c4b35"), P("#ddd2bb"), P("#2f3a44", WINDOW)
    tiles = zsolnay(P, ["#6a4a32", "#c9a14a", "#3f6a4a", "#8a5a36"], period=1.0, slope=1.0, kind="diamond")
    spire = P("#a35b44", ROOF)
    front, cross = np.array([4157.0, 1372.0]), np.array([4132.0, 1362.0])
    ang = math.atan2(*(cross - front)[::-1])
    fr = Frame(*front, b0, ang)  # +u from the Danube gable to the crossing among the three apses

    def wall(u, v, w):
        return np.where(np.mod(w - b0, 2.4) < 0.3, brick2, brick).astype(np.uint16)
    L = float(np.hypot(*(cross - front)))
    S.add(Box(fr, 0.0, L + 4.0, -8.0, 8.0, -2, 13.0, wall))
    S.add(Roof(fr, -0.5, L + 4.5, -8.5, 8.5, 13.0, 9.5, tiles))
    S.add(Box(fr, L - 5.0, L + 5.0, -11.0, 11.0, -2, 13.0, wall))
    S.add(Roof(side(fr.at(L, 0), 1), -11.5, 11.5, -5.3, 5.3, 13.0, 8.0, tiles))
    for fa, out in ((fr.at(L, -10.0), -math.pi / 2), (fr.at(L, 10.0), math.pi / 2), (fr.at(L + 5.0, 0), 0.0)):
        S.add(Lathe(fa, -2, 12.0, cyl(5.0), wall, n=6, rot=math.pi / 6))  # three polygonal apses
        S.add(Lathe(fa, 12.0, 18.5, cone(5.4, 0.3), tiles, n=6, rot=math.pi / 6))
        for k in (-1, 0, 1):
            S.add(Arch(fa.at(turn=out + k * math.pi / 3), 4.2, 5.4, 0, 0.8, 4.0, 9.5, win, pointed=True, mode="paint",
                       targets=[brick, brick2]))
    S.add(Lathe(fr.at(L, 0), 22.0, 30.0, cone(1.4, 0.05), tiles, n=8, rot=math.pi / 8))  # the flèche over the crossing
    fw = side(fr, 2)  # +u out of the Danube gable
    S.add(Ellipsoid(fw.at(0.1, 0, 9.0), 0.4, 3.2, 3.2, win, mode="paint", targets=[brick, brick2]))
    S.add(Arch(fw, -0.4, 0.6, 0, 1.6, 0, 3.4, P("#4a3426"), pointed=True))
    S.add(Box(fr, -0.6, 0.6, -9.0, 9.0, 13.0, 14.0, stone))
    for sv in (-1, 1):
        for u in np.arange(3.0, L - 6.0, 4.5):
            S.add(Arch(fr.at(u, 0, 0, sv * math.pi / 2), 8.0, 9.0, 0, 0.8, 4.0, 10.0, win, pointed=True, mode="paint", targets=[brick, brick2]))
    # the tower at the north-eastern corner
    north = 1.0 if (-math.sin(ang) * 0.663 + math.cos(ang) * -0.749) > 0 else -1.0  # the side towards north
    ft = fr.at(3.0, north * 8.0)
    S.add(Box(ft, -3.2, 3.2, -3.2, 3.2, -2, 30.0, wall))
    for w in (10.0, 20.0, 30.0):
        S.add(Box(ft, -3.4, 3.4, -3.4, 3.4, w, w + 0.6, stone))
    for k in range(4):
        fk = ft.at(turn=k * math.pi / 2)
        S.add(Arch(fk, 2.6, 3.4, 0, 0.7, 23.0, 28.0, win, pointed=True, mode="paint", targets=[brick, brick2]))
        S.add(Arch(fk, 2.6, 3.4, 0, 0.5, 13.0, 17.0, win, pointed=True, mode="paint", targets=[brick, brick2]))
    S.add(Lathe(ft, 30.6, 33.5, cyl(3.0), brick2, n=8, rot=math.pi / 8))
    S.add(Lathe(ft, 33.5, 56.0, cone(2.9, 0.12), spire, n=8, rot=math.pi / 8))
    for su in (-1, 1):
        for sv in (-1, 1):
            S.add(Lathe(ft.at(su * 2.9, sv * 2.9), 30.6, 36.0, cone(0.6, 0.05), stone, n=4, rot=math.pi / 4))
    S.add(Box(ft, -0.1, 0.1, -0.1, 0.1, 56.0, 58.0, P("#cfa94c", METAL)))
    S.clear.append((float(cross[0]), float(cross[1]), 18.0))


# ------------------------------------------------------------------------------------------------ Batthyány tér
def anna(S, ctx, plan):
    """St Anne's on Batthyány tér (Kristóf Hamon and Máté Nöpauer, 1740-61): Baroque, its two-towered front in cream
    and ochre facing the square and the Danube, the towers' green copper helms with lanterns, an oval nave under a red
    tile roof with a drum and dome over the sanctuary, the parish house round its court beside it."""
    P = ctx["P"]
    g = keep(ctx, ANNA)
    b0 = base_under(ctx, g, 0.3)
    cream, ochre, white, tile = P("#efe3c2"), P("#d9b878"), P("#f4f1e6"), P("#b5583a", ROOF)
    copper, copper2, win, door, gold = P("#5f8f7c", METAL), P("#4d7b69", METAL), P("#33404a", WINDOW), P("#4a3828"), P("#cfa94c", METAL)
    front, apse = np.array([4245.0, 1163.0]), np.array([4218.0, 1206.0])
    ang = math.atan2(*(apse - front)[::-1])
    fr = Frame(*front, b0, ang)
    L = float(np.hypot(*(apse - front)))

    def wall(u, v, w):
        pil = np.abs(np.mod(u, 4.5) - 2.25) > 1.8
        return np.where(pil | (w - b0 < 1.2), ochre, cream).astype(np.uint16)
    S.add(Box(fr, 4.0, L - 8.0, -8.0, 8.0, -2, 16.0, wall))
    S.add(Box(fr, 3.8, L - 7.8, -8.3, 8.3, 15.6, 16.4, white))
    S.add(Roof(fr, 4.0, L - 7.0, -8.6, 8.6, 16.4, 8.5, tile))
    fs = fr.at(L - 8.0)  # the sanctuary: drum and dome
    S.add(Lathe(fs, -2, 16.0, cyl(7.5), wall, n=16))
    S.add(Lathe(fs, 16.0, 21.0, cyl(5.0), cream, n=16))
    S.add(Lathe(fs, 21.0, 26.0, dome(5.3, 2.0, 1.0), tile, n=16))
    S.add(Lathe(fs, 26.0, 29.0, cyl(1.0), copper, n=8))
    for sv in (-1, 1):
        for u in np.arange(7.0, L - 10.0, 4.5):
            S.add(Arch(fr.at(u, 0, 0, sv * math.pi / 2), 7.6, 8.4, 0, 0.9, 5.0, 11.0, win, mode="paint", targets=[cream, ochre]))
    # the front: the towers and the gable between them
    S.add(Box(fr, 0.0, 4.5, -6.5, 6.5, -2, 20.0, wall))
    S.add(Box(fr, -0.3, 4.5, -6.8, 6.8, 19.6, 20.4, white))
    S.add(Lathe(side(fr, 2).at(0.0, 0, 20.4), 0, 5.5, cone(4.0, 0.6), cream, n=3, rot=math.pi / 2))
    fw = side(fr, 2)
    S.add(Arch(fw, -0.4, 0.6, 0, 1.4, 0, 4.0, door))
    S.add(Box(fw.at(0, 0, 9.0), -0.3, 0.4, -1.0, 1.0, 0, 3.6, win, mode="paint", targets=[cream, ochre]))
    for sv in (-1, 1):
        ft = fr.at(2.5, sv * 9.0)
        S.add(Box(ft, -3.0, 3.0, -3.0, 3.0, -2, 33.0, wall))
        for w in (16.0, 24.0):
            S.add(Box(ft, -3.2, 3.2, -3.2, 3.2, w, w + 0.6, white))
        for k in range(4):
            S.add(Arch(ft.at(turn=k * math.pi / 2), 2.5, 3.2, 0, 0.8, 26.5, 30.5, win, mode="paint", targets=[cream, ochre]))
            S.add(Ellipsoid(ft.at(turn=k * math.pi / 2).at(3.0, 0, 33.8), 0.4, 1.0, 1.0, P("#f1efe6"), mode="paint", targets=[copper]))
        S.add(Lathe(ft, 33.0, 37.5, onion(3.0, 3.4, 0.35), copper, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 37.5, 40.5, cyl(1.0), copper2, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 40.5, 44.0, onion(0.5, 1.1, 0.4), copper, n=8, rot=math.pi / 8))
        S.add(Box(ft, -0.08, 0.08, -0.08, 0.08, 44.0, 46.0, gold))
        S.add(Box(ft, -0.08, 0.08, -0.5, 0.5, 45.0, 45.2, gold))
    S.clear.append((float(front[0] - 8), float(front[1] + 10), 16.0))


def batthyany_hall(S, ctx, plan):
    """the Batthyány tér market hall (Samu Pecz, 1902; a supermarket since the 1970s): a long two-storey hall in red
    brick with yellow brick bands, rows of tall round-arched windows, stepped gables at the ends and a grey roof with a
    raised glazed ridge."""
    P = ctx["P"]
    g = largest(keep(ctx, BATTHYANY_HALL))
    b0 = base_under(ctx, g, 0.3)
    brick, yellow, win, slate, sky = P("#a9543d"), P("#d6b16a"), P("#36434a", WINDOW), P("#6b7072", ROOF), P("#a8c3cc", GLASS)
    cx, cy, L, Wd, ang = rect_of(g)
    fr = Frame(cx, cy, b0, ang)
    E = 11.0

    def wall(u, v, w):
        return np.where(np.mod(w - b0, 1.8) < 0.3, yellow, brick).astype(np.uint16)
    S.add(Box(fr, -L / 2, L / 2, -Wd / 2, Wd / 2, -2, E, wall))
    RH = min(Wd * 0.22, 9.0)
    S.add(Roof(fr, -L / 2 + 0.3, L / 2 - 0.3, -Wd / 2 - 0.4, Wd / 2 + 0.4, E, RH, slate))
    S.add(Roof(fr, -L / 2 + 4, L / 2 - 4, -2.2, 2.2, E + RH - 1.0, 2.0, sky))
    for sv in (-1, 1):
        for u in np.arange(-L / 2 + 3, L / 2 - 2, 4.2):
            fs = fr.at(u, sv * Wd / 2, 0, sv * math.pi / 2)
            S.add(Arch(fs, -0.6, 0.3, 0, 1.1, 1.2, 4.4, win, mode="paint", targets=[brick, yellow]))
            S.add(Arch(fs, -0.6, 0.3, 0, 1.1, 6.0, 8.8, win, mode="paint", targets=[brick, yellow]))
    for su in (-1, 1):  # stepped gables over the ends
        fe = fr.at(su * (L / 2 - 0.4), 0, 0, (0 if su > 0 else math.pi) + math.pi / 2)
        for k in range(5):
            hw_ = Wd / 2 - k * Wd / 10
            S.add(Box(fe, -hw_, hw_, -0.5, 0.5, E + k * RH / 5, E + (k + 1) * RH / 5 + 0.6, wall))
        S.add(Arch(fr.at(su * L / 2, 0, 0, 0 if su > 0 else math.pi), -0.6, 0.3, 0, 2.2, 1.0, 6.5, win, mode="paint", targets=[brick, yellow]))


# ------------------------------------------------------------------------------------------------ St Teresa of Avila
def teresa(S, ctx, plan):
    """the parish church of St Teresa of Avila in Terézváros (Fidél Kasselik, 1801-11; the tower's helm by Miklós Ybl,
    1871): Neoclassical in white and pale ochre, the tower rising from the middle of the front on Nagymező utca with
    paired pilasters, a clock and a tall copper helm and lantern; the nave under a red tile roof with a transept."""
    P = ctx["P"]
    g = keep(ctx, TERESA)
    b0 = base_under(ctx, g, 0.3)
    white, ochre, tile, copper = P("#f2ede0"), P("#e0cc9c"), P("#a9563b", ROOF), P("#5c8a78", METAL)
    win, door, clock, gold = P("#33404a", WINDOW), P("#4a3828"), P("#f4f1e6"), P("#cfa94c", METAL)
    front, apse = np.array([5336.0, 2683.0]), np.array([5389.0, 2683.0])
    ang = math.atan2(*(apse - front)[::-1])
    fr = Frame(*front, b0, ang)
    L = float(np.hypot(*(apse - front)))

    def wall(u, v, w):
        pil = np.abs(np.mod(u, 5.0) - 2.5) > 2.0
        return np.where(pil | (w - b0 < 1.2), white, ochre).astype(np.uint16)
    S.add(Box(fr, 2.0, L, -9.5, 9.5, -2, 17.0, wall))
    S.add(Box(fr, 1.8, L, -9.8, 9.8, 16.6, 17.4, white))
    S.add(Roof(fr, 2.0, L + 0.5, -10.0, 10.0, 17.4, 8.0, tile, hip=True))
    S.add(Roof(side(fr.at(L * 0.55, 0), 1), -12.5, 12.5, -5.0, 5.0, 17.4, 7.5, tile))
    S.add(Box(fr, L * 0.55 - 5.0, L * 0.55 + 5.0, -12.0, 12.0, -2, 17.0, wall))
    for sv in (-1, 1):
        for u in np.arange(6.0, L - 2.0, 5.0):
            if abs(u - L * 0.55) < 6:
                continue
            S.add(Arch(fr.at(u, 0, 0, sv * math.pi / 2), 9.1, 9.9, 0, 1.0, 5.5, 12.5, win, mode="paint", targets=[white, ochre]))
    # the front and the tower over its middle
    S.add(Box(fr, 0.0, 2.5, -9.5, 9.5, -2, 17.0, wall))
    fw = side(fr, 2)
    S.add(Arch(fw, -0.4, 0.6, 0, 1.6, 0, 4.6, door))
    ft = fr.at(2.0, 0)
    S.add(Box(ft, -3.6, 3.6, -3.6, 3.6, -2, 34.0, wall))
    for w in (17.0, 27.0):
        S.add(Box(ft, -3.8, 3.8, -3.8, 3.8, w, w + 0.7, white))
    for k in range(4):
        fk = ft.at(turn=k * math.pi / 2)
        S.add(Arch(fk, 2.9, 3.8, 0, 0.9, 20.0, 25.0, win, mode="paint", targets=[white, ochre]))
        S.add(Ellipsoid(fk.at(3.7, 0, 30.5), 0.3, 1.3, 1.3, clock, mode="paint", targets=[white, ochre]))
    S.add(Lathe(ft, 34.0, 38.0, cone(3.5, 2.0), copper, n=8, rot=math.pi / 8))
    S.add(Lathe(ft, 38.0, 40.5, cyl(1.4), copper, n=8, rot=math.pi / 8))
    S.add(Lathe(ft, 40.5, 46.0, cone(1.6, 0.1), copper, n=8, rot=math.pi / 8))
    S.add(Box(ft, -0.08, 0.08, -0.08, 0.08, 46.0, 48.0, gold))
    S.add(Box(ft, -0.08, 0.08, -0.5, 0.5, 47.0, 47.2, gold))


BUILDERS = [("MOM Park", mom_park), ("Szilágyi Dezső tér Reformed Church", szilagyi), ("St Anne's, Batthyány tér", anna),
            ("Batthyány tér market hall", batthyany_hall), ("St Teresa of Avila, Terézváros", teresa)]
