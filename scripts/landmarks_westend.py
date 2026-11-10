"""WestEnd City Center (József Finta and Partners, 1997-1999, opened on 12 November 1999), between Váci út and the
tracks out of Nyugati: the mall with the hotel (the Hilton, the Crowne Plaza since 2023) and the office block in red-brown
brick along Váci út, the cinema hall in silver panels at the far end, the Semiramis roof garden on the mall, the
Millennium garden on a deck over a car park beside it, the multi-storey car park with its solar roof, and on Nyugati tér
the main entrance under a tilted glass canopy on a steel lattice, held up by a steel tree. Same hooks as
landmarks_more.py: NAMES, DROP, BUILDERS. Positions were measured on Esri's imagery and Mapillary panoramas in the
2026-10 grid (docs/landmarks.md); they follow the outline's west corner if OSM moves it.
"""
import math

import numpy as np
import shapely
from scipy import ndimage
from shapely.geometry import LineString, Point, Polygon

import landmarks as LM
from landmarks import WINDOW, Box, Ellipsoid, Field, Frame, Lathe, Prim, Roof, Slab, cone, cyl, rect_of
from landmarks_city import base_under, dist_in, grid_of
from style import GLASS, GRASS, LEAF, METAL, ROOF, WATER, stable_hash

MALL, DECK, DECK_PARK, PARKING, GARDEN, PASSAGE = 24000485, 219155023, 496677116, 187873332, 461137234, 1200632263
NAMES = ["WestEnd City Center"]
DROP = {MALL, DECK, PARKING, PASSAGE}

NW0 = (2941.3, 1598.3)  # the outline's corner on Váci út and Nyugati tér, which the positions below are measured from
CANOPY = ((2937.0, 1602.0, 25.0), (2978.0, 1586.0, 23.5), (2944.0, 1626.0, 15.5))  # NW, NE, SW corners: x, y, height
HUB = (2957.6, 1597.2, 13.6)  # the steel tree's crown
HOTEL = [(2990, 1572), (3121, 1524), (3128, 1553), (3024, 1592), (3024, 1625), (2990, 1625)]
OFFICE_BAR = [(3126, 1525), (3243, 1480), (3252, 1503), (3133, 1548)]
OFFICE_WINGS = [(3136, 3164, 1570), (3186, 3212, 1562), (3240, 3264, 1552)]  # x0, x1, south end
HALL_ARC = ((3173.3, 1496.3), 111.0)  # the cinema hall's curved wall round the roof garden: centre, radius
SKYLIGHTS = [  # glazed roofs over the malls' galleries and atria (centre, long side, short side, angle deg, rise)
    ((3076, 1572.5), 104, 26, -20.6, 5.0), ((3145, 1575), 28, 26, -20, 5.0), ((3175, 1585), 24, 10, 23, 3.0),
    ((3210, 1588), 37, 10.5, -10, 3.0), ((3244, 1566), 28, 8, -50, 3.0), ((3181, 1557), 26, 9, -14, 2.5),
    ((3228, 1547), 27, 10, -13, 2.5), ((3257.3, 1546.8), 22, 8, -59, 3.0), ((3267, 1525), 22, 8, -73, 3.0)]
OVAL = ((3207.5, 1567.0), 9.0, 4.5)  # the pond in the roof garden: centre, half-axes along x and y
FOUNTAINS = [(3023.0, 1634.5), (3033.0, 1635.0), (3042.0, 1636.0)]  # OSM's, on the Millennium deck
PAVILION = ((2998.5, 1648.0), 17.0)  # the round terrace (Laza Tető) on the deck
# across the entrance, in metres from the canopy's edge on Váci út: the left granite pier, the end of the glass front
# and of the right pier; the glass wedge leaning on the pier from Váci út: its height, its length along the street
PIER, GLASS_TO, PIER2_TO, WEDGE = (1.0, 3.0), 19.0, 21.0, (7.0, 22.0)

PODIUM, ENTRANCE_H, NORTH_H, HOTEL_H, HOTEL_ATT, OFFICE_H, OFFICE_ATT, HALL_H = 15.0, 13.0, 9.0, 22.5, 26.0, 25.0, 28.5, 24.0
DECK_H, PARK_LV = 9.0, (4.8, 9.6, 14.4)


class Quad(Prim):
    """a parallelogram plate p0, p0 + e1, p0 + e2 (grid x, y and metres above the model base), th thick under it:
    a tilted glass roof. col: an id, or f(s, t, w) with s, t the plate's own coordinates (0..1)."""

    def __init__(self, p0, e1, e2, th, col, **kw):
        self.p0, self.e1, self.e2, self.th = np.array(p0, float), np.array(e1, float), np.array(e2, float), th
        m = np.array([[self.e1[0], self.e2[0]], [self.e1[1], self.e2[1]]])
        self.inv = np.linalg.inv(m)
        cs = [self.p0, self.p0 + self.e1, self.p0 + self.e2, self.p0 + self.e1 + self.e2]
        xs, ys, zs = zip(*cs)
        self.fcol = col
        super().__init__(Frame(0, 0, 0, 0), self._col if callable(col) else col,
                         (min(xs), max(xs), min(ys), max(ys), min(zs) - th, max(zs) + 0.5), **kw)

    def st(self, x, y):
        dx, dy = x - self.p0[0], y - self.p0[1]
        return self.inv[0, 0] * dx + self.inv[0, 1] * dy, self.inv[1, 0] * dx + self.inv[1, 1] * dy

    def inside(self, u, v, w, x, y):
        s, t = self.st(u, v)
        z = self.p0[2] + s * self.e1[2] + t * self.e2[2]
        return (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1) & (w < z) & (w >= z - self.th)

    def _col(self, u, v, w):
        s, t = self.st(u, v)
        return self.fcol(s, t, w)


def leafy(ids, holes=0.18):
    """a tree crown's colour: the greens by a hash of the voxel, with gaps."""
    ids = np.array(ids, np.uint16)

    def f(u, v, w):
        h = (np.floor(u * 2).astype(np.int64) * 73856093) ^ (np.floor(v * 2).astype(np.int64) * 19349663) \
            ^ (np.floor(w * 2).astype(np.int64) * 83492791)
        h = (h ^ (h >> 13)) & 0xFFFF
        return np.where(h < holes * 65535, 0, ids[h % len(ids)]).astype(np.uint16)
    return f


def tree(S, x, y, z, h, r, leaves, trunk):
    """a deciduous tree on a roof: trunk from z (metres above the base), crown r across at h."""
    S.add(Lathe(Frame(x, y, z), 0, h - r * 0.6, cyl(0.25), trunk))
    S.add(Ellipsoid(Frame(x, y, z + h), r, r, r * 0.85, leafy(leaves)))


def ground_index(ctx, X, Y):
    """the first free 0.5 m voxel over the ground at cell centres X, Y (as voxelize.ground_fine does)."""
    g = ndimage.map_coordinates(ctx["G"], [Y.ravel() - 0.5, X.ravel() - 0.5], order=1, mode="nearest")
    return np.round((g.reshape(X.shape) - ctx["BASE"]) * LM.F).astype(np.int16)


def westend(S, ctx, plan):
    """the whole complex, drawn by three fields (the mall, the Millennium deck, the car park), the canopy as a glass
    plate over a lattice of voxel lines, and the smaller pieces as solids."""
    P, area = ctx["P"], ctx["area"]
    mall = area[MALL][3]
    deck = area[DECK][3]
    park = area[PARKING][3]
    nw = min(np.array(mall.exterior.coords), key=lambda c: c[0])
    off = np.array([nw[0] - NW0[0], nw[1] - NW0[1]])

    def at(p):
        return (p[0] + off[0], p[1] + off[1])

    def poly(pts):
        return Polygon([at(p) for p in pts])
    b0 = base_under(ctx, mall, 0.3)
    F = LM.F

    brick, brick2, salmon, salmon2 = P("#a5543c"), P("#954b36"), P("#bb6e57"), P("#ad634e")
    granite, granite2, cream, white = P("#3d3e41"), P("#2f3033"), P("#e1d8c5"), P("#e6e6e1")
    metal, metal2, attic = P("#ccd0d3", METAL), P("#b3b8bc", METAL), P("#7a8186", METAL)
    win, shop, poster = P("#2f3a42", WINDOW), P("#3d5260", WINDOW), P("#c4d0d8")
    roof_g, roof_h, roof_p = P("#a19e97", ROOF), P("#b7b5af", ROOF), P("#a8a59c", ROOF)
    grass, grass2 = P("#7aa553", GRASS), P("#6c9a4a", GRASS)
    paving, pavers, water = P("#cfc6b4"), P("#c28a72"), P("#4f7d8f", WATER)
    leaves = [P(c, LEAF) for c in ("#76a24a", "#618f43", "#8db552", "#4f7c3c")]
    trunk = P("#6b4f3a")
    glass, glass_dark, rib = P("#a9c6cf", GLASS), P("#6d93a0", GLASS), P("#d8dcdc", METAL)
    steel, steel_light, fascia = P("#6b737a", METAL), P("#c3c8cc", METAL), P("#a7adb1", METAL)
    bars = P("#8c959b", METAL)

    # the canopy's frame: +u along its north edge (Váci út), +v across it towards the tracks. It and the entrance stand
    # on the square (be), a metre or so under the mall's base: Váci út climbs from there
    q1, q4 = at(CANOPY[0][:2]), at(CANOPY[2][:2])
    be = float(ctx["ground_m"]((q1[0] + q4[0]) / 2, (q1[1] + q4[1]) / 2))
    c1, c2, c4 = (np.array([*at(c[:2]), be + c[2]]) for c in CANOPY)
    e1, e2 = c2 - c1, c4 - c1
    ang = math.atan2(e1[1], e1[0])
    E = Frame(c1[0], c1[1], be, ang)
    hub = np.array([*at(HUB[:2]), be + HUB[2]])

    # ------------------------------------------------------------------ the mall: zones on the 0.5 m grid
    def euv(x, y):
        return E.uv(x, y)
    west = mall.intersection(Polygon([E.xy(u, v) for u, v in ((8, -30), (200, -30), (200, 60), (8, 60))]))
    uw = 8.0 + WEDGE[1]  # the wedge and the pier cut out of the block's corner
    west = west.difference(Polygon([E.xy(u, v) for u, v in ((0, -30), (uw, -30), (uw, PIER[0]), (19, PIER[0]),
                                                                (19, PIER[1]), (0, PIER[1]))]))
    hotel = mall.intersection(poly(HOTEL))
    office = shapely.union_all([poly(OFFICE_BAR)] + [poly([(a, 1470), (b, 1470), (b, e), (a, e)]) for a, b, e in OFFICE_WINGS])
    office = mall.intersection(office).difference(hotel)
    ac, ar = HALL_ARC
    hall = mall.difference(Point(at(ac)).buffer(ar, 128)).intersection(
        Polygon([at(p) for p in ((3205, 1450), (3400, 1450), (3400, 1595), (3205, 1595))]))
    raised = shapely.union_all([hotel, office, hall])
    entrance = west.intersection(Polygon([at(p) for p in ((2900, 1500), (2996, 1500), (2996, 1700), (2900, 1700))]))
    nblock = entrance.intersection(Polygon([E.xy(u, v) for u, v in ((19, -30), (200, -30), (200, 6), (19, 6))]))
    entrance = entrance.difference(nblock)  # the lower block along Váci út, under the canopy's high side
    podium = mall.difference(raised).difference(Polygon([at(p) for p in ((2900, 1500), (2996, 1500), (2996, 1700), (2900, 1700))]))
    garden = area[GARDEN][3] if GARDEN in area else Polygon()

    x0f, y0f, X, Y = grid_of(mall, 2.0)
    zone = np.zeros(X.shape, np.uint8)
    top = np.zeros(X.shape, np.float32)
    att = np.zeros(X.shape, np.float32)
    for k, (g, h, a) in enumerate(((entrance, ENTRANCE_H + be - b0, 0), (podium, PODIUM, 0),
                                   (hotel, HOTEL_H, HOTEL_ATT), (office, OFFICE_H, OFFICE_ATT), (hall, HALL_H, 0),
                                   (nblock, NORTH_H, 0)), start=1):
        m = shapely.contains_xy(g, X, Y)
        zone[m], top[m], att[m] = k, h, a
    inz = zone > 0
    dm = dist_in(mall, X, Y)
    dz = np.full(X.shape, -9.0, np.float32)
    for k, g in enumerate((entrance, podium, hotel, office, hall, nblock), start=1):
        m = zone == k
        dz[m] = shapely.distance(g.boundary, shapely.points(X[m], Y[m]))
    gy, gx = np.gradient(dm)
    north = (gy > 0.35)  # the wall faces Váci út: the distance grows towards the tracks
    U, V = euv(X, Y)
    du = gx * E.ca + gy * E.sa
    dv = -gx * E.sa + gy * E.ca
    A = np.where(np.abs(dv) >= np.abs(du), U, V).astype(np.float32)  # along the nearest wall: bays and piers
    # the roof surfaces: the Semiramis garden (lawn, paths, the promenade, the pond) on the podium
    surf = np.zeros(X.shape, np.uint8)
    gm = shapely.contains_xy(garden, X, Y) & ((zone == 1) | (zone == 2))
    surf[gm] = 1
    paths = shapely.union_all([LineString([at(OVAL[0]), at(p)]).buffer(1.8) for p in
                               ((3150, 1560), (3160, 1610), (3195, 1612), (3240, 1600), (3262, 1556), (3214, 1552))]
                              + [LineString([at(p) for p in ((2988, 1592), (3110, 1602), (3166, 1600))]).buffer(1.6)])
    surf[gm & (shapely.contains_xy(paths, X, Y) | (shapely.contains_xy(raised.buffer(2.0), X, Y)))] = 2
    surf[gm & (dm < 6.5) & (Y > 1600 + off[1])] = 3  # the promenade along the edge over the service street
    ox, oy = at(OVAL[0])
    ell = ((X - ox) / OVAL[1]) ** 2 + ((Y - oy) / OVAL[2]) ** 2
    surf[gm & (ell < 1.6)] = 2
    surf[gm & (ell < 1.0)] = 4
    gzi = ground_index(ctx, X, Y)
    fields = dict(zone=zone, top=top, att=att, dm=dm.astype(np.float32), dz=dz, north=north, A=A, surf=surf, gzi=gzi)

    def body(f, wa):
        z, tp, at_, dm_, dz_ = f["zone"][None], f["top"][None], f["att"][None], f["dm"][None], f["dz"][None]
        nth, A_, sf, gi = f["north"][None], f["A"][None], f["surf"][None], f["gzi"][None]
        zi = np.floor(wa * F)
        h = wa - b0
        main = (z > 0) & (zi >= gi - 2) & (h < tp)
        upper = (at_ > 0) & (dz_ > 1.6) & (h >= tp) & (h < at_)
        plate = (at_ > 0) & (dz_ > 1.0) & (h >= at_) & (h < at_ + 0.5)
        low = (z == 1) | (z == 2) | (z == 6)
        para = low & (dm_ < 0.6) & (h >= tp) & (h < tp + 1.1)
        st = np.mod(h - 5.5, 3.25)
        # facades
        ground = h < 5.5
        gl = np.mod(A_, 6.0) > 1.2
        out = np.where(ground & nth, np.where(gl, shop, granite), 0)
        hot_w = (np.mod(A_, 3.0) > 1.6) & (st > 0.9) & (st < 2.6)
        hot = np.where(ground, np.where(nth, out, brick2), np.where(hot_w | (np.mod(A_, 15.0) < 1.0), win, brick))
        off_w = (np.mod(A_, 7.2) > 1.2) & (st > 1.0) & (st < 2.5)
        offc = np.where(ground, np.where(nth, out, brick2), np.where(off_w, win, brick))
        hall_lo = np.where(ground & nth, out, np.where(h > 13.8, cream, salmon))
        hall_up = np.where(np.mod(h, 1.5) < 0.25, metal2, metal)
        hal = np.where(h < 15.0, hall_lo, hall_up)
        hal = np.where(nth & ~ground, np.where(hot_w, win, brick), hal)  # its front on Váci út: brick like the hotel
        band = h > tp - 1.3
        strip = ((h > 9.6) & (h < 11.0) & (np.mod(A_, 6.0) > 1.0)) | ((h > 1.0) & (h < 3.6) & (np.mod(A_, 6.0) > 2.5))
        pod = np.where(nth, np.where(np.mod(A_, 3.0) < 0.4, granite, shop),
                       np.where(band, cream, np.where(strip, win, np.where(np.mod(h, 6.0) < 0.3, salmon2, salmon))))
        pod = np.where(nth & band, cream, pod)
        ent = np.where(band, cream, granite)
        nbl = np.where(nth & (h > 1.5) & (h < 7.8) & (np.mod(A_ - 20.0, 24.0) < 17.0), poster, granite)
        col = np.select([z == 1, z == 2, z == 3, z == 4, z == 5, z == 6], [ent, pod, hot, offc, hal, nbl], 0)
        # roofs: the top layer away from the walls
        is_top = h >= tp - 0.5
        roofc = np.select([z == 5, (z == 3) | (z == 4)], [roof_h, roof_g], roof_p)
        sc = np.select([sf == 1, sf == 2, sf == 3, sf == 4],
                       [np.where(np.mod(np.floor(A_ * 0.5), 7) == 0, grass2, grass), paving, pavers, water], roofc)
        col = np.where(is_top & (dz_ > 0.6) & ~low | (is_top & low & (dm_ > 0.6)), sc, col)
        col = np.where(main, col, 0)
        col = np.where(upper, np.where((h - tp > 0.8) & (h - tp < 2.7), win, attic), col)
        col = np.where(plate, attic, col)
        col = np.where(para & ~main, cream, col)
        return col.astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 6, b0 + OFFICE_ATT + 1, body))

    # glazed roofs over the galleries and atria, a glass drum over the Niagara fountain
    def sky_col(u, v, w):
        return np.where(np.mod(u, 1.8) < 0.3, rib, glass_dark).astype(np.uint16)
    for (cx, cy), L, Wd, a, rise in SKYLIGHTS:  # "under": the half of the gallery's roof inside the hotel stays brick
        fr = Frame(*at((cx, cy)), b0 + PODIUM - 0.5, math.radians(a))
        S.add(Roof(fr, -L / 2, L / 2, -Wd / 2, Wd / 2, 0, rise + 0.5, sky_col, hip=L < 30, mode="under"))
    nx_, ny_ = at((2991, 1598))
    S.add(Lathe(Frame(nx_, ny_, be + ENTRANCE_H - 0.5), 0, 4.5, cone(5.0, 3.6), lambda u, v, w: np.where(
        np.mod(np.arctan2(v, u) * 8 / math.pi, 1) < 0.2, rib, glass_dark).astype(np.uint16)))
    # trees in the roof garden: on the lawn, a hash of the place deciding
    gx0, gy0, gx1, gy1 = garden.bounds if not garden.is_empty else (0, 0, 0, 0)
    for tx in np.arange(gx0 + 4, gx1, 9.0):
        for ty in np.arange(gy0 + 4, gy1, 9.0):
            hsh = stable_hash("westend", int(tx), int(ty))
            px, py = tx + (hsh % 5) - 2, ty + (hsh // 5 % 5) - 2
            i, j = int((py * F) - y0f), int((px * F) - x0f)
            if not (0 <= i < X.shape[0] and 0 <= j < X.shape[1]) or surf[i, j] != 1 or hsh % 3 == 0:
                continue
            if raised.distance(Point(px, py)) < 3.5 or any(
                    Point(px, py).distance(Point(*at(s[0]))) < max(s[1], s[2]) / 2 + 2 for s in SKYLIGHTS):
                continue
            tree(S, px, py, b0 + PODIUM, 4.5 + hsh % 3, 2.2 + (hsh % 7) * 0.12, leaves, trunk)

    # ------------------------------------------------------------------ the entrance on Nyugati tér
    # the glass wedge leaning on the granite pier's north side, its slope to Váci út, its end a triangle to the square;
    # the glass front from that pier to the right one, its posters, the WESTEND sign and the doors under a glass canopy
    vn = float(E.uv(*nw)[1]) - 0.5
    (p0, p1), (wh, wl) = PIER, WEDGE

    def wedge_col(u, v, w):
        return np.where(np.mod(u - 8.0, 1.8) < 0.3, rib, P("#a8c4d6", GLASS)).astype(np.uint16)

    class Wedge(Prim):
        def __init__(self):
            super().__init__(E, wedge_col, (8.0, 8.0 + wl, vn, p0, -3, wh))

        def inside(self, u, v, w, x, y):
            return (u >= 8.0) & (u < 8.0 + wl) & (v >= vn) & (v < p0) & (w >= -3) & (w < wh * (v - vn) / (p0 - vn))
    S.add(Wedge())
    S.add(Box(E, 8.0, 19.0, p0, p1, -3, 13.5, granite))
    S.add(Box(E, 10.0, 15.0, p0 - 0.3, p0, 9.4, 11.0, P("#d23b2e")))  # H&M, over the wedge
    S.add(Box(E, 8.0, 12.0, GLASS_TO, PIER2_TO, -3, 13.5, granite))
    sw = mall.exterior.coords
    vs = max(float(E.uv(*c)[1]) for c in sw if E.uv(*c)[0] < 30)

    def front_col(u, v, w):
        mull = (np.mod(v - p1, 2.0) < 0.25) | (np.mod(w, 3.0) < 0.25)
        return np.where(mull, steel, shop).astype(np.uint16)
    S.add(Box(E, 7.6, 8.4, p1, GLASS_TO, -3, ENTRANCE_H, front_col))
    # (the panels stand 0.8 m deep, so the turned frame leaves no holes; each one paints over the one before)
    S.add(Box(E, 7.0, 7.8, 4.0, 12.2, 0.0, 2.7, P("#1f2a30", WINDOW)))  # the doors, their glass canopy
    S.add(Box(E, 6.0, 7.6, 3.9, 12.3, 2.7, 3.3, lambda u, v, w: np.where(
        np.mod(v, 1.5) < 0.3, steel, glass).astype(np.uint16)))
    S.add(Box(E, 7.0, 7.8, p1 + 0.2, 13.2, 6.2, 12.6, white))  # the left poster: a white panel, a photo
    S.add(Box(E, 7.0, 7.8, 6.4, 13.0, 6.4, 12.4, lambda u, v, w: np.select(
        [np.mod(v * 0.9 + w * 0.5, 3.0) < 0.9, np.mod(v * 0.9 + w * 0.5, 3.0) < 1.8], [P("#b8473a"), P("#5a4a44")],
        P("#d9b896")).astype(np.uint16)))
    S.add(Box(E, 7.0, 7.8, 4.2, 5.2, 10.2, 11.4, P("#3b3b3d")))
    S.add(Box(E, 7.0, 7.8, 13.4, GLASS_TO - 0.1, 0.4, 12.6, white))  # the right ones, blue, to the ground
    for z0, z1 in ((0.6, 5.4), (5.6, 10.6)):
        S.add(Box(E, 7.0, 7.8, 13.7, GLASS_TO - 0.4, z0, z1, lambda u, v, w: np.where(
            np.mod(v + w * 0.4, 2.2) < 0.8, P("#2f62a0"), P("#1d3f73")).astype(np.uint16)))
    S.add(Box(E, 7.0, 7.8, 13.8, 14.4, 11.2, 11.9, P("#d23b2e")))
    S.add(Box(E, 7.0, 7.8, 4.0, 12.2, 3.4, 5.9, granite2))  # the WESTEND sign: the W, then the letters
    S.add(Box(E, 6.8, 7.6, 4.0, 6.7, 3.5, 5.8, white))
    S.add(Box(E, 6.8, 7.6, 4.4, 6.3, 3.9, 5.4, lambda u, v, w: np.where(
        np.mod(v - w * 0.5, 1.0) < 0.5, P("#e0663c"), P("#c2335a")).astype(np.uint16)))
    S.add(Box(E, 6.8, 7.6, 6.9, 12.2, 4.0, 5.0, lambda u, v, w: np.where(
        np.mod(v - 6.9, 0.75) < 0.5, white, 0).astype(np.uint16)))

    # the canopy: a glass plate on a grid of steel beams (plates too, so their lines stay straight), a steel edge,
    # trusses along its long sides (a deep one under the low side), bracing in some bays
    L1, L2 = float(np.hypot(*e1[:2])), float(np.hypot(*e2[:2]))
    ns, nt = 10, 5

    def grid(s, t):
        ds = np.abs(np.mod(s * ns + 0.5, 1) - 0.5) * L1 / ns
        dt = np.abs(np.mod(t * nt + 0.5, 1) - 0.5) * L2 / nt
        return (ds < 0.3) | (dt < 0.3)
    S.add(Quad(c1, e1, e2, 0.75, lambda s, t, w: np.where(grid(s, t), bars, glass).astype(np.uint16)))
    S.add(Quad(c1 - np.array([0, 0, 0.75]), e1, e2, 0.6,
               lambda s, t, w: np.where(grid(s, t), steel, 0).astype(np.uint16)))

    def edge_col(s, t, w):
        return np.where((s * L1 < 0.7) | ((1 - s) * L1 < 0.7) | (t * L2 < 0.7) | ((1 - t) * L2 < 0.7), fascia, 0) \
            .astype(np.uint16)
    S.add(Quad(c1 + np.array([0, 0, 0.25]), e1, e2, 1.3, edge_col))
    Z = Frame(0, 0, 0, 0)

    def pt(s, t, dz=0.0):
        p = c1 + s * e1 + t * e2
        return (float(p[0]), float(p[1]), float(p[2] - b0 + dz) + b0)
    S.line(Z, pt(0, 0, -2.6), pt(1, 0, -2.6), steel)  # the truss under the high side, its webs meeting the beams
    for i in range(ns):
        S.line(Z, pt(i / ns, 0, -1.3), pt((i + 0.5) / ns, 0, -2.6), steel)
        S.line(Z, pt((i + 0.5) / ns, 0, -2.6), pt((i + 1) / ns, 0, -1.3), steel)
    for i in range(ns):  # diagonal bracing in some bays
        for j in range(nt):
            if (i + 2 * j) % 3 == 0:
                S.line(Z, pt(i / ns, j / nt, -1.4), pt((i + 1) / ns, (j + 1) / nt, -1.4), steel)
    for k in range(16):  # the deep truss under the low side
        s0, s1 = k / 16, (k + 1) / 16
        S.line(Z, pt(s0, 1, -3.2), pt(s1, 1, -3.2), steel, 1)
        S.line(Z, pt(s0, 1, -0.8), pt(s0, 1, -3.2), steel)
        S.line(Z, pt(s0, 1, -3.2), pt(s1, 1, -0.8), steel)
    # the steel tree on its granite base: a bundle of rods rising from the hub and branching under the plate
    hx, hy, hz = (float(v) for v in hub)
    S.add(Lathe(Frame(hx, hy, b0), NORTH_H - 0.5, hz - b0 - 0.6, cone(1.6, 0.9), granite))
    S.add(Ellipsoid(Frame(hx, hy, hz), 1.0, 1.0, 0.7, steel_light))
    hs, ht = (float(v) for v in np.linalg.solve(np.array([[e1[0], e2[0]], [e1[1], e2[1]]]), hub[:2] - c1[:2]))
    for k in range(16):
        phi = 2 * math.pi * (k + 0.5) / 16
        rs, rt = 13.0 * math.cos(phi) / L1, 13.0 * math.sin(phi) * 0.55 / L2
        s_, t_ = min(max(hs + rs, 0.03), 0.97), min(max(ht + rt, 0.02), 0.6)
        top = pt(s_, t_, -1.35)
        mid = (hx + (top[0] - hx) * 0.55, hy + (top[1] - hy) * 0.55, hz + (top[2] - hz) * 0.45)
        S.line(Z, (hx, hy, hz + 0.3), mid, steel_light)
        for ds in (-0.03, 0.03):
            S.line(Z, mid, pt(min(max(s_ + ds, 0.0), 1.0), t_, -1.35), steel_light)

    # the glazed canopy over the passage along the station side, from the square past the entrance: a steel beam along
    # its inner edge, the glass rising outwards, a brick pylon holding it on the square
    su0, su1, sw_, sz, sr = -12.0, 45.0, 7.0, 8.0, 5.6

    def side_col(s, t, w):
        return np.where(np.mod(s * 24, 1) < 0.12, steel, glass).astype(np.uint16)
    q0 = np.array([*E.xy(su0, vs), be + sz])
    S.add(Quad(q0, np.array([*(np.array(E.xy(su1, vs)) - q0[:2]), 0.0]),
               np.array([*(np.array(E.xy(su0, vs + sw_)) - q0[:2]), sr]), 0.6, side_col))
    S.line(E, (su0, vs + 0.6, sz - 0.9), (su1, vs + 0.6, sz - 0.9), steel, 1)
    for uu in np.arange(su0 + 1.0, su1, 6.0):
        S.line(E, (uu, vs, sz - 0.7), (uu, vs + sw_, sz + sr - 0.7), steel)
    S.add(Box(E, -6.8, -5.2, vs + 0.6, vs + 2.2, -3, sz - 0.9, P("#b07f45")))

    # ------------------------------------------------------------------ the Millennium deck and its garden
    dx0, dy0, DX, DY = grid_of(deck, 1.5)
    dd = dist_in(deck, DX, DY)
    dgi = ground_index(ctx, DX, DY)
    colm = (np.mod(DX - 2.0, 8.0) < 0.8) & (np.mod(DY - 2.0, 8.0) < 0.8) & (dd > 0.8)
    dsurf = np.zeros(DX.shape, np.uint8)  # 0 lawn, 1 path, 2 the terrace, 3 its pattern, 4 water
    pc, pr = at(PAVILION[0]), PAVILION[1]
    rr = np.hypot(DX - pc[0], DY - pc[1])
    walk = shapely.union_all([LineString([at(p) for p in ((2975, 1652), (3150, 1660))]).buffer(1.8),
                              LineString([at(p) for p in ((3020, 1618), (3020, 1676))]).buffer(1.5),
                              LineString([at(p) for p in ((3085, 1631), (3085, 1678))]).buffer(1.5)])
    dsurf[shapely.contains_xy(walk, DX, DY)] = 1
    dsurf[rr < pr] = 2
    dia = np.abs(DX - pc[0]) + np.abs(DY - pc[1])
    dsurf[(rr < pr - 6) & (dia < 8.5) & (dia > 7.0)] = 3
    fx = [at(p) for p in FOUNTAINS]
    pool = Polygon([(fx[0][0] - 3, fx[0][1] - 1.2), (fx[-1][0] + 3, fx[-1][1] - 1.2),
                    (fx[-1][0] + 3, fx[-1][1] + 1.6), (fx[0][0] - 3, fx[0][1] + 1.6)])
    dsurf[shapely.contains_xy(pool, DX, DY)] = 4
    dfields = dict(dd=dd, gi=dgi, colm=colm, s=dsurf)
    cream2, red_base, parking, rail = P("#ddd3bf"), P("#a8513a"), P("#6a6d73"), P("#5d6569", METAL)
    terrace, inlay, soffit = P("#d8d2c4"), P("#8a8378"), P("#bdb7aa")

    def deckfn(f, wa):
        d_, gi, cm, s_ = f["dd"][None], f["gi"][None], f["colm"][None], f["s"][None]
        zi = np.floor(wa * F)
        h = wa - b0
        inside = d_ > 0
        out = np.where(inside & (zi == gi - 1), parking, 0)
        col_ = inside & cm & (zi >= gi) & (h < DECK_H - 1.0)
        out = np.where(col_, np.where(zi < gi + 3, red_base, cream2), out)
        slab = inside & (h >= DECK_H - 1.0) & (h < DECK_H)
        top_ = h >= DECK_H - 0.5
        lawn = np.where(np.mod(np.floor(f["dd"][None] * 1.3), 5) == 0, grass2, grass)
        sc = np.select([s_ == 1, s_ == 2, s_ == 3, s_ == 4], [paving, terrace, inlay, water], lawn)
        out = np.where(slab, np.where(d_ < 0.7, cream2, np.where(top_, sc, soffit)), out)
        out = np.where(inside & (d_ < 0.7) & (h >= DECK_H - 1.8) & (h < DECK_H - 1.0), cream2, out)
        out = np.where(inside & (d_ < 0.35) & (h >= DECK_H) & (h < DECK_H + 1.1), rail, out)
        return out.astype(np.uint16)
    S.add(Field(dx0, dy0, dfields, b0 - 6, b0 + DECK_H + 1.2, deckfn))
    # the round terrace's ring roof on posts, the fountains, a playground, the kiosk, the trees
    fp = Frame(pc[0], pc[1], b0 + DECK_H)
    S.add(Lathe(fp, 3.2, 3.8, cyl(pr - 0.5), P("#4a4f54", METAL), inner=6.0))
    for k in range(16):
        a = 2 * math.pi * k / 16
        for r_ in (pr - 6.0, pr - 1.0):
            S.add(Box(fp.at(r_ * math.cos(a), r_ * math.sin(a)), -0.2, 0.2, -0.2, 0.2, 0, 3.3, steel))
    for x_, y_ in fx:
        S.add(Lathe(Frame(x_, y_, b0 + DECK_H - 0.3), 0, 1.6, cone(0.35, 0.1), P("#e9f1f2", WATER)))
    pg = Frame(*at((3006, 1630)), b0 + DECK_H, 0)
    S.add(Box(pg, -1.2, 1.2, -1.2, 1.2, 0, 2.6, P("#d8b040")))
    S.add(Roof(pg, -1.5, 1.5, -1.5, 1.5, 2.6, 1.2, P("#c98a2e"), hip=True))
    S.add(Box(pg, 1.2, 4.0, -0.6, 0.6, 0, 1.4, P("#7d4f8a")))
    kf = Frame(*at((3118, 1649)), b0 + DECK_H, 0)
    S.add(Box(kf, -13.0, 13.0, -5.0, 5.0, 0, 3.4, white))
    S.add(Box(kf, -13.3, 13.3, -5.3, 5.3, 3.4, 3.8, P("#8d8f92")))
    S.add(Box(kf, -12.0, 12.0, -5.2, 5.2, 0.4, 2.8, win, mode="paint", targets=[white]))
    for row, y_ in enumerate((1635.0, 1643.5)):
        for x_ in np.arange(3024.0 + row * 3.5, 3152.0, 7.0):
            if abs(x_ - 3085) < 2.5 or abs(x_ - 3118) < 15 and y_ > 1640:
                continue
            hsh = stable_hash("deck", int(x_), int(y_))
            tree(S, *at((x_, y_)), b0 + DECK_H, 6.0 + hsh % 3, 3.0 + (hsh % 5) * 0.15, leaves, trunk)
    for x_, y_ in ((2976, 1634), (2975, 1664), (2981, 1674), (3045, 1668), (3060, 1672), (3140, 1670), (3100, 1672)):
        hsh = stable_hash("deck2", x_, y_)
        tree(S, *at((x_, y_)), b0 + DECK_H, 5.5 + hsh % 3, 2.8 + (hsh % 4) * 0.2, leaves, trunk)

    # ------------------------------------------------------------------ the car park: three decks, the solar roof
    drum_c, drum_r = at((3332.5, 1650.5)), 13.0
    pk = park.difference(Point(drum_c).buffer(drum_r + 0.3, 64))
    px0, py0, PX, PY = grid_of(park, 1.5)
    dp = dist_in(pk, PX, PY)
    pgi = ground_index(ctx, PX, PY)
    pcol = (np.mod(PX - 1.0, 8.0) < 0.8) & (np.mod(PY - 1.0, 8.0) < 0.8) & (dp > 0.8)
    lines_ = np.mod(PX, 2.6) < 0.25
    pfields = dict(dp=dp, gi=pgi, colm=pcol, ln=lines_)
    asphalt2, mark = P("#8d8f93"), P("#e8e6df")

    def parkfn(f, wa):
        d_, gi, cm, ln = f["dp"][None], f["gi"][None], f["colm"][None], f["ln"][None]
        zi = np.floor(wa * F)
        h = wa - b0
        inside = d_ > 0
        out = np.where(inside & (zi == gi - 1), parking, 0)
        out = np.where(inside & cm & (zi >= gi) & (h < PARK_LV[-1]), np.where(zi < gi + 3, red_base, cream2), out)
        for lv in PARK_LV:
            slab = inside & (h >= lv - 0.5) & (h < lv)
            out = np.where(slab, np.where(d_ < 0.7, cream2, np.where(ln & (lv == PARK_LV[-1]), mark, asphalt2)), out)
            out = np.where(inside & (d_ < 0.4) & (h >= lv) & (h < lv + 1.1), np.where(h > lv + 0.8, red_base, cream2), out)
        return out.astype(np.uint16)
    S.add(Field(px0, py0, pfields, b0 - 6, b0 + PARK_LV[-1] + 1.2, parkfn))
    fd = Frame(drum_c[0], drum_c[1], b0)
    S.add(Lathe(fd, -3, PARK_LV[-1] + 1.6, cyl(5.0), cream2))
    for k, lv in enumerate(PARK_LV):  # the ramp's drum: a deck and a parapet with a red rail on each level
        S.add(Lathe(fd, lv - 0.5, lv, cyl(drum_r), asphalt2, inner=8.0))
        S.add(Lathe(fd, lv, lv + 1.1, cyl(drum_r), lambda u, v, w, lv=lv: np.where(
            w > lv + 0.8, red_base, white).astype(np.uint16), inner=0.5))
        if k:
            S.add(Lathe(fd, lv - 2.4, lv - 0.5, cyl(drum_r), white, inner=0.5))
    # rows of solar panels on frames over the top deck, sloping to the south
    pxa, pya, pxb, pyb = pk.bounds
    panel = P("#2c3c58", METAL)

    def pv_col(u, v, w):
        return np.where(np.mod(v, 1.7) < 0.2, rib, panel).astype(np.uint16)
    for y_ in np.arange(pya + 4.0, pyb - 6.0, 8.5):
        xs = [x_ for x_ in np.arange(pxa + 4.0, pxb - 4.0, 1.0) if pk.buffer(-3.0).contains(Point(x_, y_ + 2.75))]
        if len(xs) < 10:
            continue
        xa, xb = xs[0], xs[-1]
        fr = Frame(xa, y_, b0 + PARK_LV[-1], math.pi / 2)
        S.add(Slab(fr, 0.0, 5.5, -(xb - xa), 0.0, lambda u: 3.3 - 0.12 * u, -0.6, 0.0, pv_col))
        for x_ in np.arange(xa + 2.0, xb, 9.0):
            S.add(Box(Frame(x_, y_ + 2.75, b0 + PARK_LV[-1]), -0.2, 0.2, -0.2, 0.2, 0, 2.8, steel))

    # the glass roof over the passage from the station
    if PASSAGE in area:
        pgx, pgy, pL, pW, pa = rect_of(area[PASSAGE][3])
        fr = Frame(pgx, pgy, b0, pa)

        def pass_col(u, v, w):
            return np.where(np.mod(u, 3.0) < 0.4, steel, glass).astype(np.uint16)
        S.add(Roof(fr, -pL / 2, pL / 2, -pW / 2 - 0.4, pW / 2 + 0.4, DECK_H - 1.0, 3.0, pass_col))
        S.add(Roof(fr, -pL / 2 + 0.5, pL / 2 - 0.5, -pW / 2 + 0.3, pW / 2 - 0.3, DECK_H - 1.0, 2.4, 0, mode="carve"))
        for uu in np.arange(-pL / 2 + 1, pL / 2, 8.0):
            for sv in (-1, 1):
                S.add(Box(fr.at(uu, sv * (pW / 2 - 0.3)), -0.2, 0.2, -0.2, 0.2, -1, DECK_H - 1.0, steel))

    # no generated trees in the complex or the service street through it (the street's trees are the deck's, above)
    whole = shapely.union_all([mall, deck, park]).buffer(9.0, join_style=2).buffer(-9.0, join_style=2)
    for cx_ in np.arange(whole.bounds[0], whole.bounds[2], 4.0):
        for cy_ in np.arange(whole.bounds[1], whole.bounds[3], 4.0):
            p = Point(cx_, cy_)
            if whole.contains(p):
                r_ = whole.boundary.distance(p) - 0.5
                if r_ > 0.5:
                    S.clear.append((float(cx_), float(cy_), float(r_)))


def view(mall, g):
    """the entrance on Nyugati tér from the square, the canopy over it (for voxelize.py's views)."""
    nw = min(np.array(mall.exterior.coords), key=lambda c: c[0])
    off = np.array([nw[0] - NW0[0], nw[1] - NW0[1]])
    c1, c2, c4 = (np.array(c[:2]) + off for c in CANOPY)
    mid = (c1 + c2 + c4 + (c2 + c4 - c1)) / 4
    ax = (c1 - c2) / np.linalg.norm(c1 - c2)
    side = (c4 - c1) / np.linalg.norm(c4 - c1)
    cam = mid + ax * 62 - side * 6
    zg = float(g[int(mid[1]), int(mid[0])])
    return dict(label="WestEnd City Center", pos=[round(float(cam[0]), 1), round(zg + 6, 1), round(float(cam[1]), 1)],
                target=[round(float(mid[0]), 1), round(zg + 16, 1), round(float(mid[1]), 1)])


BUILDERS = [("WestEnd City Center", westend)]
