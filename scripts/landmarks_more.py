"""The third batch of hand-built landmarks: the Gellért Hotel and Baths, the BME's Building K, the Hungarian National
Museum, the Kálvin tér skybridge and the boats moored on the Danube. Built with landmarks.py's solids on the frames of
their OSM outlines, like landmarks_city.py (docs/landmarks.md has the photo sources).
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon

import landmarks as LM
from landmarks import (TAU, WINDOW, Arch, Box, Capsule, Ellipsoid, Field, Frame, Lathe, Poly, Prim, Roof, TBox, cone,
                       cyl, dome, rect_of, ring_segments, seg_frame)
from landmarks_city import Vault, base_under, dist_in, grid_of, named_near, statue, windows
from style import GLASS, LEAF, METAL, ROOF, WATER, stable_hash

GELLERT = 46769968
BME_K, BME_K_BODY, BME_AULA = 24727135, 18868356, 198237185
NATMUS = 12963
KALVIN_BRIDGE = 129917689
BOAT_EXTRA = {172966675, 1153259919}  # A38's exhibition barge and the Zsófia event ship: building=yes on the water

NAMES = ["Gellért Hotel and Baths", "BME Building K", "Hungarian National Museum", "Kálvin tér skybridge",
         "Danube boats"]


def boats(osm):
    return [(oid, t, g) for oid, k, t, g in osm.areas
            if t.get("building") in ("ship", "houseboat") or oid in BOAT_EXTRA]


def drop_ids(osm):
    return {GELLERT, BME_K, BME_K_BODY, BME_AULA, NATMUS, KALVIN_BRIDGE} | {oid for oid, t, g in boats(osm)}


# ------------------------------------------------------------------------------------------------ helpers
def largest(g):
    return max(getattr(g, "geoms", [g]), key=lambda q: q.area)


def front_frame(g, oz, toward):
    """a frame on the footprint's minimum rectangle with +v the side facing `toward` (a grid direction): u runs
    along that front."""
    cx, cy, L, Wd, ang = rect_of(g)
    t = np.array(toward, float) / np.linalg.norm(toward)
    best = max((ang + k * math.pi / 2 for k in range(4)), key=lambda a: -math.sin(a) * t[0] + math.cos(a) * t[1])
    return Frame(cx, cy, oz, best)


def uv_of(fr, g):
    return fr.uv(*np.array(largest(g).exterior.coords).T)


def front_profile(g, fr, step=1.0):
    """for u across the footprint: the furthest v of the building (its front line), NaN outside."""
    eu, ev = uv_of(fr, g)
    us = np.arange(math.floor(eu.min()), math.ceil(eu.max()) + step, step)
    vmax = np.full(len(us), np.nan)
    for i, u in enumerate(us):
        ln = LineString([fr.xy(u, ev.min() - 5), fr.xy(u, ev.max() + 5)])
        s = ln.intersection(g)
        if s.is_empty:
            continue
        pts = np.array([c for part in getattr(s, "geoms", [s]) for c in part.coords])
        vmax[i] = fr.uv(pts[:, 0], pts[:, 1])[1].max()
    return us, vmax


def runs(mask):
    """the [start, end) index runs where mask is True."""
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def frame_fields(fr, X, Y):
    U = ((X - fr.ox) * fr.ca + (Y - fr.oy) * fr.sa).astype(np.float32)
    V = (-(X - fr.ox) * fr.sa + (Y - fr.oy) * fr.ca).astype(np.float32)
    return U, V


def wall_coord(fr, d, U, V):
    """per cell, the coordinate that runs along its nearest wall (U or V): for pilaster strips and bays."""
    gy, gx = np.gradient(d.astype(np.float32))
    du = gx * fr.ca + gy * fr.sa
    dv = -gx * fr.sa + gy * fr.ca
    return np.where(np.abs(dv) >= np.abs(du), U, V).astype(np.float32)


def rect_poly(fr, u0, u1, v0, v1):
    return Polygon([fr.xy(u0, v0), fr.xy(u1, v0), fr.xy(u1, v1), fr.xy(u0, v1)])


def pool_basin(S, ctx, pool, rim, water, depth=1.4, rim_w=0.9):
    """an outdoor pool as a basin: dug into the ground, water a little below a stone rim."""
    zg = ctx["ground_m"](*pool.representative_point().coords[0])
    S.add(Poly(pool, zg - depth - 0.2, zg + 0.6, 0, mode="carve"))
    S.add(Poly(pool, zg - depth - 0.2, zg - 0.3, water))
    ring = pool.buffer(rim_w, join_style=2).difference(pool)
    S.add(Poly(ring, zg - depth - 0.2, zg + 0.3, rim))


# ------------------------------------------------------------------------------------------------ Gellért
def gellert(S, ctx, plan):
    """the Gellért Hotel and Baths (Ármin Hegedűs, Artúr Sebestyén, Izidor Sterk, 1912-1918) at the foot of Gellért
    Hill: Art Nouveau in pale stone, five storeys under brown-red tiled roofs. On the front to the Danube a tower over
    the middle (its attic with the hotel's name, a steep red roof, a green copper lantern) between two corner pavilions
    under green copper domes; on the corner of Kelenhegyi út the baths' entrance rotunda under a dark ribbed dome. In
    the back, the swimming hall's glass vault; behind the building the wave pool and the warm adventure pool."""
    P, C, area = ctx["P"], ctx["C"], ctx["area"]
    g = largest(area[GELLERT][3])
    th = ctx["theta"]
    fr = front_frame(g, 0.0, (math.cos(th), math.sin(th)))  # +v: the Danube, to the east
    eu, ev = uv_of(fr, g)
    u0, u1, v0, v1 = float(eu.min()), float(eu.max()), float(ev.min()), float(ev.max())
    stone, stone2, rust, trim = P("#d8c8a4"), P("#cdbc96"), P("#c0ae88"), P("#e8dec6")
    tile, tile2 = P("#8d4a36", ROOF), P("#7d4231", ROOF)
    redtile = P("#a24b31", ROOF)
    copper, copper2 = P("#6fa28b", ROOF), P("#5d8f79", ROOF)
    ribc, ribl = P("#55605d", ROOF), P("#76807b", ROOF)
    flat = P("#8d8a84", ROOF)
    glass, gmetal = P("#a9c2c8", GLASS), P("#5b6468", METAL)
    win = P("#2f3540", WINDOW)
    gold = P("#c9a34e", METAL)
    E, WING = 22.5, 15.0

    us, vmax = front_profile(g, fr)
    ok = np.isfinite(vmax)
    v_main = float(np.nanpercentile(vmax[ok & (us > u0 + 6) & (us < u1 - 6)], 40))
    proj = ok & (vmax > v_main + 2.0) & (np.abs(us - (u0 + u1) / 2) < (u1 - u0) * 0.3)
    u_c = float(us[proj].mean()) if proj.any() else (u0 + u1) / 2 - 6
    v_t = float(vmax[proj].max()) if proj.any() else v_main
    front_u = us[ok & (vmax > v_main - 3)]
    uf0, uf1 = float(front_u.min()), float(front_u.max())
    # it stands at the foot of the hill, its entrance level with the square: the ground just in front of it
    b0 = float(np.quantile([ctx["ground_m"](*fr.xy(u, v_main + 3.0)) for u in np.linspace(uf0 + 3, uf1 - 3, 15)], 0.3))
    fr = Frame(fr.ox, fr.oy, b0, fr.ang)

    # the walls and the tiled roofs over every range, from the distance to the outline
    x0f, y0f, X, Y = grid_of(g, 1.5)
    d = dist_in(g, X, Y)
    U, V = frame_fields(fr, X, Y)
    A = wall_coord(fr, d, U, V)
    Eh = np.where(V < v0 + 16, E - 2.0, E).astype(np.float32)  # the range against the hill is lower
    HALL = 15.5
    fields = dict(d=d, U=U, A=A, Eh=Eh)

    def fn(f, wa):
        d_, A_, E_, U_ = f["d"][None], f["A"][None], f["Eh"][None], f["U"][None]
        h = wa - b0
        wing = d_ < WING
        top = np.where(wing, E_, HALL)
        body = (d_ > 0) & (h < top)
        rus = (h < 5.2) & (np.mod(h, 0.9) < 0.22)
        bay = (d_ < 1.0) & (np.mod(A_, 7.6) < 1.1) & (h > 5.2)
        band = ((h > 5.0) & (h < 5.6)) | ((h > E_ - 1.4) & (h < E_ - 0.4))
        col = np.where(band, trim, np.where(rus, rust, np.where(bay, stone2, stone)))
        cornice = (d_ > -0.6) & (d_ <= 0.2) & (h > E_ - 0.9) & (h < E_ - 0.2)
        rise = np.clip(np.minimum(d_ - 0.2, WING - d_), 0, None) * 0.88
        roof = (d_ > 0) & wing & (h >= E_) & (h < E_ + rise)
        roofc = np.where(np.mod(h, 1.0) < 0.5, tile, tile2)
        hr = np.clip(d_ - WING, 0, 7.0) * 0.32  # the halls inside: low zinc roofs with rows of skylights
        lid = (d_ >= WING) & (h >= HALL) & (h < HALL + 0.5 + hr)
        sky = lid & (np.mod(U_, 9.0) < 2.4) & (hr > 0.6) & (h >= HALL + 0.5 + hr - 0.6)
        out = np.where(body, col, 0)
        out = np.where(cornice, trim, out)
        out = np.where(roof, roofc, out)
        out = np.where(lid, np.where(sky, glass, flat), out)
        return out.astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 4, b0 + E + 8, fn))
    windows(S, g, b0, [(1.4, 4.6)], [stone, stone2, rust], win, every=3.8, half=0.85, min_len=5.0)
    windows(S, g, b0, [(6.4, 9.0), (10.2, 12.8), (14.0, 16.6)], [stone, stone2], win, every=3.8, half=0.7,
            min_len=5.0, arch=False)
    windows(S, g, b0, [(17.8, 20.4)], [stone, stone2], win, every=3.8, half=0.7, min_len=5.0)

    # the middle tower: an attic storey with a great arched window and the name, a steep red roof, a copper lantern
    ft = fr.at(u_c, v_t - 8.0)
    S.add(Box(ft, -11.0, 11.0, -8.0, 8.0, -4, E + 8.5, stone))
    S.add(Box(ft, -11.5, 11.5, -8.5, 8.5, E + 7.6, E + 8.6, trim))
    S.add(Box(ft, -11.0, 11.0, -8.0, 8.4, E - 0.8, E + 0.2, trim))
    S.add(Arch(ft.at(0, 8.0, 0, math.pi / 2), -0.5, 0.6, 0, 3.0, E + 0.6, E + 4.5, win, mode="paint", targets=[stone]))
    for su in (-1, 1):
        S.add(Arch(ft.at(su * 6.5, 8.0, 0, math.pi / 2), -0.5, 0.6, 0, 1.2, E + 0.8, E + 4.4, win, mode="paint",
                   targets=[stone]))
    S.add(Box(ft, -5.5, 5.5, 7.9, 8.5, E + 5.9, E + 7.2, P("#3b3a36")))
    for k in range(7):  # the gilt letters of GELLÉRT
        S.add(Box(ft, -4.8 + k * 1.5, -4.2 + k * 1.5, 8.3, 8.6, E + 6.1, E + 7.0, gold))
    S.add(Roof(ft, -11.0, 11.0, -8.0, 8.0, E + 8.5, 12.5, redtile, hip=True))
    zl = E + 8.5 + 11.2
    S.add(Lathe(ft, zl, zl + 4.2, cyl(2.5), copper2, n=8, rot=math.pi / 8))
    for k in range(8):
        S.add(Arch(ft.at(turn=TAU * k / 8), 2.0, 2.8, 0, 0.5, zl + 0.8, zl + 2.9, win, mode="paint", targets=[copper2]))
    S.add(Lathe(ft, zl + 4.2, zl + 4.8, cyl(2.9), copper, n=8, rot=math.pi / 8))
    S.add(Lathe(ft, zl + 4.8, zl + 8.0, dome(2.6, 1.6, 0.3), copper, n=8, rot=math.pi / 8))
    S.add(Lathe(ft, zl + 7.8, zl + 10.2, cyl(0.15), gold))

    # the corner pavilions' green copper domes, at the two ends of the hotel's front
    def copper_dome(u, r=5.6):
        fd = fr.at(u, v_main - 7.0)
        S.add(Box(fd, -r - 0.8, r + 0.8, -r - 0.8, r + 0.8, -4, E + 4.0, stone))
        S.add(Box(fd, -r - 1.2, r + 1.2, -r - 1.2, r + 1.2, E + 3.4, E + 4.2, trim))
        for k in range(4):
            fk = fd.at(turn=k * math.pi / 2)
            S.add(Arch(fk, r + 0.3, r + 1.0, 0, 1.0, E + 0.6, E + 2.4, win, mode="paint", targets=[stone]))
        S.add(Lathe(fd, E + 4.2, E + 5.4, cyl(r), copper2, n=8, rot=math.pi / 8))
        S.add(Lathe(fd, E + 5.4, E + 5.4 + r * 1.25, dome(r, 1.55, r * 0.24), copper, n=8, rot=math.pi / 8))
        for k in range(8):
            fk = fd.at(turn=TAU * k / 8 + math.pi / 8)
            S.add(Capsule(fk, (r * 0.95, 0, E + 5.6), (r * 0.3, 0, E + 5.2 + r * 1.15), 0.2, copper2))
        zq = E + 5.4 + r * 1.2
        S.add(Lathe(fd, zq, zq + 1.8, cyl(r * 0.26), copper2, n=8))
        S.add(Lathe(fd, zq + 1.8, zq + 2.9, dome(r * 0.3, 1.8), copper, n=8))
        S.add(Lathe(fd, zq + 2.7, zq + 4.2, cyl(0.12), gold))
    us_ = uf0 + 7.5
    copper_dome(us_)
    copper_dome(min(2 * u_c - us_, uf1 - 7.5))

    # the baths' entrance rotunda on the corner of Kelenhegyi út, set back beyond the hotel's front, under a dark
    # ribbed dome
    beyond = ok & (us > uf1 + 1.0)
    if beyond.sum() >= 6:
        ur0, ur1 = uf1 + 1.0, float(us[beyond].max())
        R = min((ur1 - ur0) / 2, 8.0)
        corner = ((ur0 + ur1) / 2, float(np.nanmax(vmax[beyond])) - R + 0.8)
    else:
        R = 7.6
        corner = (uf1 - R, v_main - R)
    fc = fr.at(*corner)
    S.add(Lathe(fc, -4, E + 3.5, cyl(R), stone))
    for k in range(10):
        fk = fc.at(turn=TAU * k / 10)
        S.add(Arch(fk, R - 0.6, R + 0.3, 0, 0.9, 6.0, 16.0, win, mode="paint", targets=[stone]))
        S.add(Arch(fk, R - 0.6, R + 0.3, 0, 0.8, E - 2.8, E + 1.2, win, mode="paint", targets=[stone]))
    S.add(Lathe(fc, E + 3.5, E + 4.5, cyl(R + 0.6), trim))
    S.add(Lathe(fc, E + 4.5, E + 5.5, cyl(R - 0.3), stone2))
    nr = 16

    def ribs(u, v, w):
        a = np.arctan2(v, u)
        return np.where(np.mod(a * nr / TAU, 1.0) < 0.2, ribl, ribc).astype(np.uint16)
    S.add(Lathe(fc, E + 5.5, E + 5.5 + R * 1.45, dome(R - 0.3, 1.45, 1.4), ribs))
    zq = E + 5.5 + R * 1.38
    S.add(Lathe(fc, zq, zq + 2.2, cyl(1.5), stone2, n=8))
    S.add(Lathe(fc, zq + 2.2, zq + 3.6, dome(1.7, 1.8), ribc, n=8))
    S.add(Lathe(fc, zq + 3.4, zq + 5.0, cyl(0.12), gold))

    # the swimming hall's glass vault and the thermal hall's glass dome, in the back
    inner = d > WING + 1.0
    if inner.sum() > 400:
        iu, iv = U[inner], V[inner]
        uc, vc = float(np.median(iu)), float(np.median(iv))
        span = float(np.percentile(iu, 92) - np.percentile(iu, 8))
        hl, hw = min(span * 0.36, 24.0), min(float(np.percentile(iv, 92) - np.percentile(iv, 8)) * 0.3, 9.0)
        fh = fr.at(uc, vc)

        def vault_col(u, v, w):
            return np.where((np.mod(u, 2.4) < 0.35) | (np.abs(v) < 0.4), gmetal, glass).astype(np.uint16)
        S.add(Box(fh, -hl - 0.6, hl + 0.6, -hw - 0.6, hw + 0.6, HALL - 0.4, HALL + 0.8, trim))
        S.add(Vault(fh, -hl, hl, hw, HALL, 6.5, 0.6, vault_col))
        for su in (-1, 1):
            S.add(Box(fh, su * hl - 0.3, su * hl + 0.3, -hw, hw, HALL, HALL + 5.5, glass))
        fg = fr.at(float(corner[0]) - 22.0, float(corner[1]) - 24.0)
        pg_ = Point(fg.ox, fg.oy)
        if g.contains(pg_) and g.exterior.distance(pg_) > WING + 5.0:
            S.add(Lathe(fg, HALL, HALL + 1.2, cyl(5.6), trim, n=12))
            S.add(Lathe(fg, HALL + 1.2, HALL + 5.8, dome(5.2, 2.0), vault_col, n=12))

    # the outdoor pools behind the baths: basins in white stone
    rim, water = P("#efece4"), P("#4fb0c6", WATER)
    wave = None
    for oid, k, t, pg in ctx["osm"].areas:
        if t.get("leisure") == "swimming_pool" and pg.distance(g) < 80 and t.get("location") != "indoor":
            pool_basin(S, ctx, pg, rim, water)
            if t.get("name") == "Hullámmedence" or (wave is None and pg.area > 300):
                wave = pg
    gellert_garden(S, ctx, g, wave, rim, water)


# the open-air baths up the hill behind the Gellért, placed from aerial photos (grid metres): the sun terrace's arc
# round the half-moon garden, open towards the baths, and the stepped curve at the wave pool's far end
GARDEN_C, GARDEN_R, ARC_R = (548.5, 3665.5), 14.0, (18.5, 27.0)
ARC_FROM, ARC_TO = math.radians(70), math.radians(270)
STEPS_C, STEPS_R = (501.0, 3631.5), (8.0, 12.0)
KIDS_POOL = ((505.0, 3654.0), 3.2)


def gellert_garden(S, ctx, hotel, wave, rim, water):
    """the open-air baths: a one-storey arcade bent round the half-moon garden, its roof a sun terrace in terracotta
    tiles behind a white balustrade, a lower promenade inside the arc, clipped shrubs in the garden; the wave pool's
    terracotta deck, the stepped curve at its far end, the round children's pool."""
    P, g_at = ctx["P"], ctx["ground_m"]
    white, terra, shade = P("#ece7da"), P("#b9694e"), P("#7d766a")
    leaf = P("#4f7a3c", LEAF)
    cx, cy = GARDEN_C
    b = g_at(cx, cy)
    x0f, y0f, X, Y = grid_of(Polygon([(cx - 30, cy - 30), (cx + 30, cy - 30), (cx + 30, cy + 30), (cx - 30, cy + 30)]), 1.0)
    R = np.hypot(X - cx, Y - cy).astype(np.float32)
    th = np.mod(np.arctan2(Y - cy, X - cx), TAU).astype(np.float32)
    arc = ((th >= ARC_FROM) & (th <= ARC_TO)).astype(np.float32)
    keep = not hotel.buffer(0.5).contains(Point(cx, cy))
    if keep:
        H = 5.0
        r0, r1 = ARC_R

        def body(fd, w):
            r, a, t = fd["r"], fd["arc"] > 0, fd["th"]
            z = w - b
            ring = a & (r >= r0) & (r < r1)
            edge = ring & ((r < r0 + 0.6) | (r >= r1 - 0.6))
            bay = np.mod(t * r / 3.6, 1.0)
            opening = edge & (np.abs(bay - 0.5) < 0.3) & (z < 3.4) & (z > -0.2)
            out = np.where(ring & (z < H) & (z >= -1.5) & ~opening, white, 0)
            out = np.where(ring & (z >= H - 0.5) & (z < H), terra, out)
            rail = ring & (edge & (np.mod(t * r, 0.7) < 0.35) | (edge & (z >= H + 0.8))) & (z >= H) & (z < H + 1.0)
            out = np.where(rail, white, out)
            prom = a & (r >= GARDEN_R) & (r < r0) & (z >= -1.0) & (z < 0.5)
            return np.where(prom, terra, out).astype(np.uint16)
        S.add(Field(x0f, y0f, {"r": R, "th": th, "arc": arc}, b - 1.5, b + H + 1.0, body))
        for k in range(9):  # clipped shrubs in the garden
            a = ARC_FROM + (ARC_TO - ARC_FROM) * (k + 0.5) / 9
            S.add(Ellipsoid(Frame(cx + math.cos(a) * 9.5, cy + math.sin(a) * 9.5, b + 0.9), 1.1, 1.1, 1.0, leaf))
        for k in range(4):
            a = ARC_FROM + (ARC_TO - ARC_FROM) * (k + 0.5) / 4
            S.add(Ellipsoid(Frame(cx + math.cos(a) * 4.5, cy + math.sin(a) * 4.5, b + 0.8), 0.9, 0.9, 0.9, leaf))
    if wave is not None:
        zw = g_at(*wave.representative_point().coords[0])
        deck = wave.buffer(4.0, join_style=2).difference(wave.buffer(0.9, join_style=2))
        S.add(Poly(deck, zw - 1.2, zw + 0.3, terra))
        out = wave.buffer(4.0, join_style=2)
        rail = out.buffer(0.35, join_style=2).difference(out)
        S.add(Poly(rail, zw + 0.3, zw + 1.3, white, mode="under"))
        sx, sy = STEPS_C
        zs = g_at(sx, sy)
        for i in range(3):  # the stepped curve at the far end, rising away from the water
            ring_ = Point(sx, sy).buffer(STEPS_R[0] + i * 1.4 + 1.4).difference(Point(sx, sy).buffer(STEPS_R[0] + i * 1.4))
            half = ring_.difference(wave.buffer(2.0))
            S.add(Poly(half, zs - 1.0, zs + 0.5 * (i + 1), terra if i < 2 else white))
        (kx, ky), kr = KIDS_POOL
        zk = g_at(kx, ky)
        S.add(Poly(Point(kx, ky).buffer(kr), zk - 1.2, zk + 0.6, 0, mode="carve"))
        S.add(Poly(Point(kx, ky).buffer(kr), zk - 1.2, zk - 0.3, water))
        S.add(Poly(Point(kx, ky).buffer(kr + 0.6).difference(Point(kx, ky).buffer(kr)), zk - 1.2, zk + 0.9, white))


# ------------------------------------------------------------------------------------------------ BME K
def bme_k(S, ctx, plan):
    """Building K of the Budapest University of Technology (Alajos Hauszmann, Győző Czigler, Samu Pecz, 1909): a
    ladder of ranges round light courts along the Danube, red-brown brick over a rusticated stone ground floor under
    steep slate roofs. On the river front the main entrance: a stone pavilion with three arched doors, six giant
    columns, a balustrade and a high hipped roof with an iron crest, two spired turrets at its corners; the ends of
    the cross wings come forward as pavilions under tall pyramid roofs. Over the central court, the aula's glass roof."""
    P, area = ctx["P"], ctx["area"]
    out = largest(area[BME_K][3])
    body = largest(area[BME_K_BODY][3]) if BME_K_BODY in area else out
    b0 = base_under(ctx, out, 0.4)
    th = ctx["theta"]
    fr = front_frame(out, b0, (math.cos(th), math.sin(th)))
    eu, ev = uv_of(fr, out)
    brick, brick2 = P("#9a5a45"), P("#8c5140")
    stone, stone2, rust, sand = P("#b9b0a0"), P("#a8a090"), P("#a39a8a"), P("#9b927f")
    trim = P("#cbc2b0")
    slate, slate2, slate3 = P("#59606a", ROOF), P("#6a717a", ROOF), P("#4c535c", ROOF)
    iron, gold = P("#3c4247", METAL), P("#c9a34e", METAL)
    win = P("#2c323b", WINDOW)
    glass, gmetal = P("#a9c2c8", GLASS), P("#5b6468", METAL)
    E = 22.0

    us, vmax = front_profile(out, fr)
    ok = np.isfinite(vmax)
    v_base = float(np.nanpercentile(vmax[ok], 30))
    pav = [(us[a], us[b - 1], float(vmax[a:b].max())) for a, b in runs(ok & (vmax > v_base + 4.0)) if us[b - 1] - us[a] > 8]
    mid = (float(eu.min()) + float(eu.max())) / 2
    centre = min(pav, key=lambda p: abs((p[0] + p[1]) / 2 - mid)) if pav else None
    ends = [p for p in pav if p is not centre]

    x0f, y0f, X, Y = grid_of(body, 1.5)
    d = dist_in(body, X, Y)
    U, V = frame_fields(fr, X, Y)
    A = wall_coord(fr, d, U, V)
    fields = dict(d=d, A=A, U=U)
    pat = np.array([slate, slate2, slate3], np.uint16)

    def fn(f, wa):
        d_, A_, U_ = f["d"][None], f["A"][None], f["U"][None]
        h = wa - b0
        body_ = (d_ > 0) & (h < E)
        socle = h < 5.6
        rus = socle & (np.mod(h, 0.85) < 0.2)
        pil = (d_ < 1.2) & (np.mod(A_, 7.2) < 1.2)
        band = ((h > 5.6) & (h < 6.3)) | (h > E - 1.3) | ((h > 14.6) & (h < 15.1))
        col = np.where(socle, np.where(rus, rust, stone), np.where(band | pil, trim,
                       np.where(np.mod(np.floor(h * 2) + np.floor(A_ * 2), 7) == 0, brick2, brick)))
        cornice = (d_ > -0.7) & (d_ <= 0.2) & (h > E - 1.0) & (h < E - 0.2)
        rise = np.clip(d_ - 0.3, 0, 7.5) * 1.15
        roof = (d_ > 0) & (h >= E) & (h < E + rise)
        a = np.floor((U_ + h) / 1.4).astype(np.int64)
        b = np.floor((U_ - h) / 1.4).astype(np.int64)
        roofc = pat[np.mod(a + 2 * b, 3)]
        o = np.where(body_, col, 0)
        o = np.where(cornice, trim, o)
        o = np.where(roof, roofc, o)
        return o.astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 2, b0 + E + 9, fn))
    walls = [stone, rust, brick, brick2, trim]
    windows(S, body, b0, [(1.3, 4.5), (11.6, 14.4)], walls, win, every=3.6, half=0.75, min_len=5.0)
    windows(S, body, b0, [(7.0, 10.8), (16.2, 19.8)], walls, win, every=3.6, half=0.75, min_len=5.0, arch=False)

    # the cross wings' river ends: pavilions under pyramid roofs with a spirelet
    for pu0, pu1, pv in ends:
        uc = (pu0 + pu1) / 2
        hw = min((pu1 - pu0) / 2, 11.0)
        fp = fr.at(uc, pv - hw)
        S.add(Box(fp, -hw, hw, -hw, hw, -2, E + 1.5, brick))
        S.add(Box(fp, -hw - 0.5, hw + 0.5, -hw - 0.5, hw + 0.5, E + 0.5, E + 1.5, trim))
        for su in (-1, 1):
            for sv in (-1, 1):
                S.add(Box(fp.at(su * (hw - 0.6), sv * (hw - 0.6)), -0.8, 0.8, -0.8, 0.8, 5.6, E + 0.5, trim, mode="under"))
        S.add(TBox(fp, hw, hw, 0.9, 0.9, E + 1.5, E + 15.0, slate))
        S.add(Lathe(fp, E + 14.0, E + 17.0, cyl(0.9), iron, n=8))
        S.add(Lathe(fp, E + 17.0, E + 20.5, cone(1.0, 0.05), slate3, n=8))
        S.add(Lathe(fp, E + 20.3, E + 21.8, cyl(0.12), gold))

    # the main entrance pavilion
    if centre is not None:
        cu0, cu1, cv = centre
        uc = (cu0 + cu1) / 2
        half = (cu1 - cu0) / 2
        Ec = E + 3.5
        fc = fr.at(uc, cv)
        S.add(Box(fc, -half, half, -26.0, 0.0, -2, Ec, lambda u, v, w: np.where(
            w < 5.6, np.where(np.mod(w, 0.85) < 0.2, stone2, rust), sand).astype(np.uint16)))
        for k in (-1, 0, 1):  # three arched doors
            S.add(Arch(fc.at(k * 4.6, 0, 0, math.pi / 2), -1.0, 0.4, 0, 1.6, 0, 3.6, P("#3d3128"), mode="paint",
                       targets=[sand, rust, stone2]))
        for k in range(6):  # six giant columns and tall windows between them
            uk = (k - 2.5) * 4.6
            fk = fc.at(uk, 1.3)
            S.add(Lathe(fk, 5.6, 6.6, cyl(1.05), trim, n=8))
            S.add(Lathe(fk, 6.6, Ec - 3.6, cyl(0.78), stone))
            S.add(Lathe(fk, Ec - 3.6, Ec - 2.6, cone(0.85, 1.15), trim, n=8))
        for k in range(5):
            uk = (k - 2) * 4.6
            S.add(Arch(fc.at(uk, 0, 0, math.pi / 2), -0.6, 0.4, 0, 1.3, 7.2, 13.0, win, mode="paint", targets=[sand]))
            S.add(Box(fc.at(uk, 0, 0, math.pi / 2), -0.6, 0.4, -1.1, 1.1, 15.6, 19.2, win, mode="paint", targets=[sand]))
        for su in (-1, 1):  # the corner bays: windows in pairs
            for k in (-1, 1):
                S.add(Box(fc.at(su * (half - 3.6) + k * 1.0, 0, 0, math.pi / 2), -0.6, 0.4, -0.45, 0.45, 7.2, 11.6,
                          win, mode="paint", targets=[sand]))
                S.add(Box(fc.at(su * (half - 3.6) + k * 1.0, 0, 0, math.pi / 2), -0.6, 0.4, -0.45, 0.45, 13.6, 18.0,
                          win, mode="paint", targets=[sand]))
        S.add(Box(fc, -14.4, 14.4, -1.0, 2.6, Ec - 2.6, Ec, trim))
        S.add(Box(fc, -half - 0.4, half + 0.4, -26.0, 0.6, Ec - 1.0, Ec, trim))
        for k in range(int(half * 2 / 0.75)):  # the balustrade
            uk = -half + 0.4 + k * 0.75
            S.add(Box(fc, uk, uk + 0.35, 1.6, 2.4, Ec, Ec + 1.0, trim))
        S.add(Box(fc, -14.4, 14.4, 1.4, 2.6, Ec + 1.0, Ec + 1.4, trim))
        S.add(Roof(fc.at(0, -13.0), -half + 1.0, half - 1.0, -12.0, 12.0, Ec, 12.0, slate, hip=True))
        rl = max(half - 1.0 - 12.0, 0.5)
        S.line(fc.at(0, -13.0), (-rl, 0, Ec + 12.2), (rl, 0, Ec + 12.2), iron, thick=1)
        for k in range(-int(rl), int(rl) + 1, 2):
            S.line(fc.at(0, -13.0), (k, 0, Ec + 12.0), (k, 0, Ec + 13.4), iron)
        for su in (-1, 1):  # dormers on the roof's front
            fd = fc.at(su * 7.0, -3.0)
            S.add(Box(fd, -1.2, 1.2, -1.0, 1.0, Ec + 1.0, Ec + 4.2, trim))
            S.add(Roof(fd.at(0, 0, 0, math.pi / 2), -1.6, 1.0, -1.4, 1.4, Ec + 4.2, 1.6, slate3))
            S.add(Box(fd, -0.6, 0.6, 0.6, 1.2, Ec + 1.6, Ec + 3.6, win, mode="paint", targets=[trim]))
        for su in (-1, 1):  # the turrets on the pavilion's corners
            ft = fc.at(su * (half - 1.8), -1.8)
            S.add(Lathe(ft, Ec - 6.0, Ec + 4.0, cyl(2.0), sand, n=8, rot=math.pi / 8))
            S.add(Lathe(ft, Ec + 3.4, Ec + 4.2, cyl(2.4), trim, n=8, rot=math.pi / 8))
            for k in range(8):
                S.add(Arch(ft.at(turn=TAU * k / 8 + math.pi / 8), 1.5, 2.4, 0, 0.4, Ec, Ec + 2.8, win, mode="paint",
                           targets=[sand]))
            S.add(Lathe(ft, Ec + 4.2, Ec + 13.0, cone(2.3, 0.08), slate3, n=8, rot=math.pi / 8))
            S.add(Lathe(ft, Ec + 12.8, Ec + 14.3, cyl(0.12), gold))

    # the aula's glass roof over the central court
    if BME_AULA in area:
        ag = largest(area[BME_AULA][3])
        acx, acy, aL, aW, aang = rect_of(ag)
        fa = Frame(acx, acy, b0, aang)

        def gl(u, v, w):
            return np.where(np.mod(u, 2.2) < 0.4, gmetal, glass).astype(np.uint16)
        S.add(Roof(fa, -aL / 2 - 0.5, aL / 2 + 0.5, -aW / 2 - 0.5, aW / 2 + 0.5, E - 0.6, 5.5, gl, hip=True))


# ------------------------------------------------------------------------------------------------ the National Museum
def national_museum(S, ctx, plan):
    """the Hungarian National Museum (Mihály Pollack, 1837-1847), Classicist: a block round two courts, cream walls
    over a grey rusticated ground floor, pedimented windows on the main floor, giant Corinthian pilasters on the
    corners and a heavy cornice under low zinc roofs. On Múzeum körút the portico: eight Corinthian columns on a
    podium reached by a broad stair, a pediment with Raffaele Monti's figures of Pannonia and the arts; behind it the
    low dome over the Dome Hall."""
    P, area = ctx["P"], ctx["area"]
    g = largest(area[NATMUS][3])
    b0 = base_under(ctx, g, 0.4)
    c = g.centroid
    to = named_near(ctx, "Múzeum körút", c, 200.0)
    toward = (to[0] - c.x, to[1] - c.y) if to else (-math.cos(ctx["theta"]), -math.sin(ctx["theta"]))
    fr = front_frame(g, b0, toward)
    eu, ev = uv_of(fr, g)
    u0, u1, v0, v1 = float(eu.min()), float(eu.max()), float(ev.min()), float(ev.max())
    cream, cream2, grey, rust = P("#efe7d3"), P("#e6dcc4"), P("#d3cdc0"), P("#c3bdb0")
    trim, trim2 = P("#f6f1e4"), P("#ddd5c2")
    zinc, zinc2 = P("#7f868c", ROOF), P("#737a80", ROOF)
    win = P("#2f3540", WINDOW)
    door = P("#4a3b2c")
    gold = P("#c9a34e", METAL)
    E, hp = 20.6, 4.4

    us, vmax = front_profile(g, fr)
    ok = np.isfinite(vmax)
    v_main = float(np.nanpercentile(vmax[ok], 35))
    pr = ok & (vmax > v_main + 3.0)
    if pr.any():
        pu0, pu1 = float(us[pr].min()), float(us[pr].max())
    else:
        pu0, pu1 = (u0 + u1) / 2 - 17.0, (u0 + u1) / 2 + 17.0
    u_c, ph = (pu0 + pu1) / 2, min((pu1 - pu0) / 2, 19.0)
    v_front = float(vmax[pr].max()) if pr.any() else v_main + 14.0
    depth = v_front - v_main
    portico = rect_poly(fr, u_c - ph - 0.5, u_c + ph + 0.5, v_main + 0.4, v_front + 3.0)
    bodyg = g.difference(portico)

    x0f, y0f, X, Y = grid_of(g, 1.5)
    d = dist_in(bodyg, X, Y)
    U, V = frame_fields(fr, X, Y)
    A = wall_coord(fr, d, U, V)
    fields = dict(d=d, A=A)

    def fn(f, wa):
        d_, A_ = f["d"][None], f["A"][None]
        h = wa - b0
        body = (d_ > 0) & (h < E)
        ground = h < 5.6
        rus = ground & ((np.mod(h, 0.8) < 0.18) | ((np.mod(A_ + np.floor(h / 0.8) * 0.9, 1.8) < 0.15) & (d_ < 0.8)))
        string = (h >= 5.6) & (h < 6.4)
        frieze = (h >= E - 3.0) & (h < E - 1.8)
        col = np.where(ground, np.where(rus, rust, grey), np.where(string | frieze, trim, cream))
        cornice = (d_ > -0.8) & (d_ <= 0.3) & (h >= E - 1.6) & (h < E - 0.4)
        dent = (d_ > -0.4) & (d_ <= 0.3) & (h >= E - 1.8) & (h < E - 1.6) & (np.mod(A_, 0.9) < 0.45)
        attic = (d_ > 0) & (d_ < 0.6) & (h >= E) & (h < E + 0.7)
        rise = np.clip(d_ - 0.6, 0, 9.0) * 0.4
        roof = (d_ > 0.6) & (h >= E - 0.4) & (h < E - 0.4 + rise)
        o = np.where(body, col, 0)
        o = np.where(cornice | dent, trim2, o)
        o = np.where(attic, trim, o)
        o = np.where(roof, np.where(np.mod(np.floor(A_ / 0.9), 2) == 0, zinc, zinc2), o)
        return o.astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0 - 2, b0 + E + 5, fn))

    # windows: plain on the ground floor, pedimented on the main floor, smaller above
    walls = [cream, grey, rust]
    for a, b, n in ring_segments(bodyg, 6.0):
        fw = seg_frame(a, b, n, 0)
        Ls = float(np.hypot(*(b - a)))
        k = max(int((Ls - 3.0) // 4.4), 1)
        for i in range(k):
            t_ = (Ls - (k - 1) * 4.4) / 2 + i * 4.4
            fi = fw.at(t_, 0, 0, math.pi / 2)
            S.add(Box(fi, -0.3, 0.5, -0.8, 0.8, b0 + 1.4, b0 + 4.0, win, mode="paint", targets=walls))
            S.add(Box(fi, -0.3, 0.5, -0.9, 0.9, b0 + 7.6, b0 + 11.4, win, mode="paint", targets=walls))
            S.add(Box(fi, -0.6, -0.0, -1.3, 1.3, b0 + 11.6, b0 + 12.1, trim, mode="under"))
            S.add(Roof(fi, -0.6, 0.0, -1.4, 1.4, b0 + 12.1, 0.7, trim, mode="under"))
            S.add(Box(fi, -0.6, -0.0, -1.1, 1.1, b0 + 7.2, b0 + 7.6, trim, mode="under"))
            S.add(Box(fi, -0.3, 0.5, -0.8, 0.8, b0 + 13.4, b0 + 16.0, win, mode="paint", targets=walls))
        # giant pilasters with their capitals on both ends of every long wall
        if Ls > 14:
            for t_ in (0.9, Ls - 0.9):
                fpl = fw.at(t_, 0, 0)
                S.add(Box(fpl, -0.8, 0.8, -0.45, 0.0, b0 + 6.4, b0 + E - 3.0, trim2, mode="under"))
                S.add(Box(fpl, -1.0, 1.0, -0.6, 0.0, b0 + E - 4.0, b0 + E - 3.0, trim, mode="under"))

    # the portico
    fp = fr.at(u_c, v_main)
    S.add(Box(fp, -ph, ph, -0.5, 8.4, -2, hp, grey))
    n_st = 12
    for k in range(n_st):
        S.add(Box(fp, -ph + 0.6, ph - 0.6, 8.4, 8.4 + (depth - 8.0) * (k + 1) / n_st, -2, hp * (1 - (k + 0.5) / n_st), grey))
    for ua, ub in ((-ph, -ph + 1.2), (ph - 1.2, ph)):  # the stair's side walls
        S.add(Box(fp, ua, ub, 8.4, depth, -2, hp + 0.9, rust))
    S.add(Box(fp, -ph, ph, -0.5, 0.3, hp, E, cream))
    for k in (-1, 0, 1):
        S.add(Box(fp.at(k * 6.2, 0, 0, math.pi / 2), -0.4, 0.6, -1.4, 1.4, hp, hp + 6.0, door, mode="paint", targets=[cream]))
        S.add(Roof(fp.at(k * 6.2, 0.6, 0, math.pi / 2), -0.3, 0.3, -1.8, 1.8, hp + 6.2, 0.8, trim))
        S.add(Box(fp.at(k * 6.2, 0, 0, math.pi / 2), -0.4, 0.6, -0.9, 0.9, hp + 8.6, hp + 11.6, win, mode="paint",
                  targets=[cream]))
    n_col, cv = 8, 6.8
    sp = (2 * ph - 3.0) / (n_col - 1)
    ct = E - 2.9
    for k in range(n_col):
        fk = fp.at(-ph + 1.5 + k * sp, cv)
        S.add(Box(fk, -1.0, 1.0, -1.0, 1.0, hp, hp + 0.6, trim2))
        S.add(Lathe(fk, hp + 0.6, hp + 1.0, cyl(0.95), trim))
        S.add(Lathe(fk, hp + 1.0, ct - 1.6, cone(0.82, 0.7), trim))
        S.add(Lathe(fk, ct - 1.6, ct, cone(0.72, 1.15), trim2, n=8))
        S.add(Box(fk, -1.15, 1.15, -1.15, 1.15, ct - 0.25, ct, trim))
    S.add(Box(fp, -ph, ph, -0.5, cv + 1.4, ct, E - 0.4, trim))
    S.add(Box(fp, -ph, ph, cv + 0.6, cv + 1.4, ct + 0.9, ct + 1.6, trim2, mode="paint", targets=[trim]))
    S.add(Box(fp, -ph - 0.4, ph + 0.4, -0.5, cv + 1.8, E - 1.2, E - 0.2, trim))
    fpd = fp.at(0, 0, 0, math.pi / 2)  # the pediment: its ridge along v
    rise = ph * 0.3
    S.add(Roof(fpd, -0.5, cv + 1.8, -ph - 0.4, ph + 0.4, E - 0.2, rise, trim))
    S.add(Roof(fpd, cv + 0.7, cv + 1.5, -ph + 0.6, ph - 0.6, E + 0.3, rise - 1.3, trim2, mode="paint", targets=[trim]))
    for k in range(-4, 5):  # the tympanum's figures
        hk = (rise - 1.4) * (1 - abs(k) / 5.0)
        if hk > 1.2:
            statue(S, fp.at(k * ph / 5.2, cv + 1.75, 0), E + 0.1, trim2, scale=min(hk / 2.5, 1.2))
    S.add(Lathe(fp.at(0, cv + 1.2), E - 0.2 + rise, E + rise + 1.6, cone(0.5, 0.1), trim))

    # the dome over the Dome Hall, between the two courts
    holes = [Polygon(r) for r in g.interiors]
    if len(holes) >= 2:
        hu, hv = zip(*(fr.uv(*h.centroid.coords[0]) for h in holes[:2]))
        du, dv = float(np.mean(hu)), float(np.mean(hv))
    else:
        du, dv = u_c, v_main - 25.0
    fd = fr.at(du, dv)
    S.add(Lathe(fd, E - 2.0, E + 2.6, cyl(8.6), cream, n=16))
    for k in range(16):
        S.add(Arch(fd.at(turn=TAU * k / 16), 8.0, 8.9, 0, 0.55, E + 0.3, E + 1.7, win, mode="paint", targets=[cream]))
    S.add(Lathe(fd, E + 2.6, E + 3.2, cyl(9.2), trim, n=16))
    S.add(Lathe(fd, E + 3.2, E + 7.6, dome(8.7, 2.0, 2.0), zinc, n=16))
    S.add(Lathe(fd, E + 7.2, E + 9.0, cyl(1.9), cream, n=8))
    S.add(Lathe(fd, E + 9.0, E + 10.0, dome(2.2, 2.0), zinc, n=8))
    S.add(Lathe(fd, E + 9.8, E + 11.0, cyl(0.12), gold))


# ------------------------------------------------------------------------------------------------ Kálvin tér
class UProfile(Prim):
    """[u0, u1] x [v0, v1] between two heights that vary along u: lo(u) <= w < hi(u). A flat arch, a paddle box."""

    def __init__(self, fr, u0, u1, v0, v1, lo, hi, col, **kw):
        self.p, self.lo, self.hi = (u0, u1, v0, v1), lo, hi
        t = np.linspace(u0, u1, 65)
        super().__init__(fr, col, (u0, u1, v0, v1, float(np.min(lo(t))), float(np.max(hi(t)))), **kw)

    def inside(self, u, v, w, x, y):
        u0, u1, v0, v1 = self.p
        return (u >= u0) & (u < u1) & (v >= v0) & (v < v1) & (w >= self.lo(u)) & (w < self.hi(u))


def flat_arch(a, ws, wc):
    return lambda u: wc - (wc - ws) * (np.asarray(u, float) / a) ** 2


def kalvin_bridge(S, ctx, plan):
    """the Mercure Korona's skybridge over Kecskeméti utca on Kálvin tér (1990): a glazed gallery one storey high on a
    flat beige arch, from one wing of the hotel to the other, with planters along its roof."""
    P, area = ctx["P"], ctx["area"]
    g = area[KALVIN_BRIDGE][3]
    cx, cy, L, Wd, ang = rect_of(g)
    zg = ctx["ground_m"](cx, cy)
    fr = Frame(cx, cy, zg, ang)
    beige, beige2 = P("#dcc7a3"), P("#cbb48f")
    glass, frame_c = P("#7f9ea8", GLASS), P("#e6dccb")
    rail = P("#4a4f52", METAL)
    green = P("#5f8a45", ROOF)
    a, hv = L / 2 + 1.0, Wd / 2
    fl, top = 10.6, 14.0
    soffit = flat_arch(a, 6.4, fl - 1.0)
    S.add(UProfile(fr, -a, a, -hv, hv, soffit, lambda u: np.full_like(np.asarray(u, float), fl), beige))
    S.add(UProfile(fr, -a, a, -hv + 0.6, hv - 0.6, soffit, lambda u: np.full_like(np.asarray(u, float), fl - 0.5),
                   beige2, mode="paint", targets=[beige]))
    S.add(Box(fr, -a, a, -hv, hv, fl - 0.5, fl, beige))

    def gal(u, v, w):
        mull = (np.mod(u + a, 1.8) < 0.3) | (w < fl + 0.9) | (w > top - 0.5)
        return np.where(mull, frame_c, glass).astype(np.uint16)
    S.add(Box(fr, -a, a, -hv, hv, fl, top, gal))
    S.add(Box(fr, -a, a, -hv + 0.5, hv - 0.5, fl + 0.5, top - 0.5, 0, mode="carve"))
    S.add(Box(fr, -a, a, -hv - 0.2, hv + 0.2, top, top + 0.6, beige))
    for sv in (-1, 1):
        S.add(Box(fr, -a + 1.0, a - 1.0, sv * (hv - 0.4) - 0.4, sv * (hv - 0.4) + 0.4, top + 0.6, top + 1.1, green))
        S.line(fr, (-a, sv * (hv + 0.1), top + 1.6), (a, sv * (hv + 0.1), top + 1.6), rail)
        for k in range(int(2 * a / 1.8) + 1):
            uk = -a + k * 1.8
            S.line(fr, (uk, sv * (hv + 0.1), top + 0.6), (uk, sv * (hv + 0.1), top + 1.6), rail)


# ------------------------------------------------------------------------------------------------ boats
class Hull(Prim):
    """a ship's hull over its frame (+u to the bow): full beam amidships, a pointed bow, a rounded stern, sides that
    tuck in towards the keel, a deck that rises towards the bow. col(u, v, w) colours it."""

    def __init__(self, fr, L, B, draft, fb, col, bow=0.2, stern=0.08, sheer=0.7, **kw):
        self.p = (L, B, draft, fb, bow, stern, sheer)
        super().__init__(fr, col, (-L / 2, L / 2, -B / 2, B / 2, -draft, fb + sheer), **kw)

    def half_width(self, u, w):
        L, B, draft, fb, bow, stern, sheer = self.p
        lb, ls = L * bow, L * stern
        sb = np.clip((u - (L / 2 - lb)) / lb, 0, 1)
        ss = np.clip(((-L / 2 + ls) - u) / ls, 0, 1)
        hw = B / 2 * (1 - sb ** 1.9) ** 0.62 * (0.8 + 0.2 * np.sqrt(np.clip(1 - ss ** 2, 0, 1)))
        tuck = 0.84 + 0.16 * np.clip((w + draft) / (draft + 0.8), 0, 1)
        return hw * tuck

    def deck(self, u):
        L, B, draft, fb, bow, stern, sheer = self.p
        return fb + sheer * np.clip((u - L / 8) / (L * 3 / 8), 0, 1) ** 2

    def inside(self, u, v, w, x, y):
        L, B, draft, fb, bow, stern, sheer = self.p
        return (np.abs(u) <= L / 2) & (w >= -draft) & (w < self.deck(u)) & (np.abs(v) <= self.half_width(u, w))


def boat(S, ctx, oid, t, g):
    P = ctx["P"]
    g = largest(g)
    cx, cy, L, B, ang = rect_of(g)
    if L < 8:
        return
    th = ctx["theta"]
    fr = Frame(cx, cy, ctx["WLr"], ang)

    def width_at(u):
        ln = LineString([fr.xy(u, -B), fr.xy(u, B)])
        return ln.intersection(g).length
    wa, wb = width_at(-L / 2 + 0.06 * L), width_at(L / 2 - 0.06 * L)
    if abs(wa - wb) > 0.15 * B:
        bow = 1 if wb < wa else -1
    else:  # moored bow upstream: the Danube flows south
        bow = 1 if fr.ca * math.sin(th) - fr.sa * math.cos(th) > 0 else -1
    if bow < 0:
        fr = Frame(cx, cy, ctx["WLr"], ang + math.pi)
    name = (t.get("name") or "").lower()
    h = stable_hash(oid)
    white, white2 = P("#eef0ef"), P("#dfe2e2")
    win = P("#23303d", WINDOW)
    cargo = t.get("ship:type") == "cargo_ship" or "a38 hajó" in name
    paddle = "kossuth" in name
    barge = oid in BOAT_EXTRA and "a38" in name
    accents = ["#22324a", "#20403a", "#5a2a2b", "#24272b", "#2c4a6e"]
    dark = P("#3a4044") if cargo else P(accents[h % len(accents)])
    deckc = P("#8a8e8f") if cargo else P("#8f7356")
    rustc = P("#6b3a2c")
    beam = B * (0.56 if paddle else 0.96)
    draft, fb = 1.6, (2.4 if cargo else 1.5 if barge else 1.9)
    hull = Hull(fr, L, beam, draft, fb, None, bow=0.12 if barge else 0.2, stern=0.06 if barge else 0.1,
                sheer=0.3 if barge else 0.8)

    def hull_col(u, v, w):
        hw = hull.half_width(u, w)
        top = hull.deck(u)
        side = np.abs(v) > hw - 0.55
        band = w < 0.45 if not cargo else w < top - 0.5
        c = np.where(side, np.where(band, dark, np.where(w > top - 0.5, dark if not cargo else white2, white)), deckc)
        if cargo:
            c = np.where(side & (w <= 0.0), rustc, c)
        return np.broadcast_to(c, np.broadcast_shapes(np.shape(u), np.shape(v), np.shape(w))).astype(np.uint16)
    hull.col = hull_col
    S.add(hull)

    def rail(fr2, u0, u1, hv, w0, col=white):
        for sv in (-1, 1):
            S.line(fr2, (u0, sv * hv, w0 + 1.0), (u1, sv * hv, w0 + 1.0), col)
            for k in range(int((u1 - u0) / 1.5) + 1):
                S.line(fr2, (u0 + k * 1.5, sv * hv, w0), (u0 + k * 1.5, sv * hv, w0 + 1.0), col)

    def house(u0, u1, hv, w0, ht, wcol=white, round_front=True):
        def col(u, v, w):
            z = w - w0
            glaze = (z > 0.8) & (z < ht - 0.5) & (np.mod(u, 2.4) > 0.35)
            return np.where(glaze, win, wcol).astype(np.uint16)
        S.add(Box(fr, u0, u1 - (hv if round_front else 0), -hv, hv, w0, w0 + ht, col))
        if round_front:
            S.add(Lathe(fr.at(u1 - hv), w0, w0 + ht, cyl(hv), col))
        S.add(Box(fr, u0 - 0.2, u1 + 0.2, -hv - 0.2, hv + 0.2, w0 + ht - 0.25, w0 + ht, white2))

    if cargo:  # A38: a Ukrainian stone carrier, its wheelhouse block aft, a glass pavilion on the hold
        S.add(Box(fr, -L / 2 + 3, L / 2 - 6, -beam / 2 + 0.6, beam / 2 - 0.6, fb, fb + 0.9, dark))
        S.add(Box(fr, -L / 2 + 3, L / 2 - 6, -beam / 2 + 1.0, beam / 2 - 1.0, fb + 0.4, fb + 1.0, 0, mode="carve"))
        S.add(Box(fr, -L / 2 + 3.5, L / 2 - 7, -beam / 2 + 1.0, beam / 2 - 1.0, fb, fb + 0.4, deckc))
        au0 = -L / 2 + 2.0
        for k, (ht, inset) in enumerate(((2.8, 0.8), (2.6, 1.4), (2.6, 2.4))):
            house(au0, au0 + 13.0 - k * 2.5, beam / 2 - inset, fb + k * 2.8, ht, round_front=False)
        S.add(Box(fr, au0 + 3, au0 + 4.4, -0.7, 0.7, fb + 8.4, fb + 12.0, P("#c8452f")))
        S.add(Box(fr, au0 + 3, au0 + 4.4, -0.7, 0.7, fb + 11.2, fb + 12.0, P("#24272b")))

        def pav(u, v, w):
            z = w - fb
            m = (np.mod(u, 2.0) < 0.3) | (z < 0.5) | (z > 3.2)
            return np.where(m, P("#3d4448", METAL), P("#7ea0ac", GLASS)).astype(np.uint16)
        pu0 = au0 + 16.0
        S.add(Box(fr, pu0, pu0 + 22.0, -beam / 2 + 1.6, beam / 2 - 1.6, fb + 0.4, fb + 3.6, pav))
        S.add(Box(fr, pu0 - 0.3, pu0 + 22.3, -beam / 2 + 1.3, beam / 2 - 1.3, fb + 3.6, fb + 4.0, P("#3d4448", METAL)))
        rail(fr, pu0, pu0 + 22.0, beam / 2 - 1.5, fb + 4.0, P("#3d4448", METAL))
        S.line(fr, (L / 2 - 8, 0, fb), (L / 2 - 8, 0, fb + 9.0), P("#3d4448", METAL), thick=1)
        return
    if barge:  # the exhibition barge alongside A38: a long low pavilion
        hv = beam / 2 - 0.8
        house(-L / 2 + 2.5, L / 2 - 4.0, hv, fb, 3.2, round_front=False)
        rail(fr, -L / 2 + 2.5, L / 2 - 4.0, hv, fb + 3.2)
        return

    n = 1 if L < 35 else 3 if t.get("tourism") == "hotel" else 2
    w0 = fb + 0.1
    ub0, ub1 = -L / 2 + 2.0, L / 2 - L * 0.2
    for k in range(n):
        hv = beam / 2 - 0.7 - k * 0.5
        house(ub0 + k * 1.5, ub1 - k * 3.0, hv, w0 + k * 2.7, 2.7)
    top = w0 + n * 2.7
    rail(fr, ub0 + (n - 1) * 1.5, ub1 - (n - 1) * 3.0 - 1, beam / 2 - 0.9 - (n - 1) * 0.5, top)
    S.line(fr, (L / 2 - 0.8, 0, fb + 0.8), (L / 2 - 0.8, 0, fb + 3.6), P("#d8d8d8", METAL))
    S.line(fr, (-L / 2 + 0.8, 0, fb + 0.6), (-L / 2 + 0.8, 0, fb + 4.5), P("#d8d8d8", METAL))
    for z, c in ((4.5, "#c8302c"), (4.0, "#f2f0ea"), (3.5, "#3d7d3f")):  # the stern flag
        S.line(fr, (-L / 2 + 0.8, 0, fb + z), (-L / 2 - 0.6, 0, fb + z), P(c))
    hv_top = beam / 2 - 1.0 - (n - 1) * 0.5
    ut = ub1 - (n - 1) * 3.0
    S.add(Box(fr, ut - 6.0, ut - 1.0, -min(hv_top, 2.6), min(hv_top, 2.6), top, top + 2.4,
              lambda u, v, w: np.where((w - top > 0.8) & (w - top < 2.0), win, white).astype(np.uint16)))
    if "spoon" in name or "boatanic" in name or t.get("amenity") in ("bar", "restaurant", "nightclub"):
        awn = P(["#e9e1cf", "#b8433b", "#2f5d7c"][h % 3])
        au0, au1 = ub0 + 2.0, ut - 8.0
        if au1 - au0 > 6:
            S.add(Box(fr, au0, au1, -hv_top + 0.3, hv_top - 0.3, top + 2.5, top + 2.8, awn))
            for uk in np.arange(au0, au1 + 0.1, 4.0):
                for sv in (-1, 1):
                    S.line(fr, (uk, sv * (hv_top - 0.5), top), (uk, sv * (hv_top - 0.5), top + 2.5), P("#d8d8d8", METAL))
    if paddle:  # the paddle steamer: paddle boxes amidships and a funnel
        pdark = P("#2a2c2e")
        for sv in (-1, 1):
            vb = sv * (beam / 2 + 1.3)
            S.add(UProfile(fr.at(-L * 0.05, vb), -3.6, 3.6, -1.4, 1.4, lambda u: np.full_like(np.asarray(u, float), 0.3),
                           lambda u: 0.3 + 3.3 * np.sqrt(np.clip(1 - (np.asarray(u, float) / 3.6) ** 2, 0, 1)),
                           lambda u, v, w: np.where(w > 2.6, pdark, white).astype(np.uint16)))
        fu = fr.at(-L * 0.05, 0)
        S.add(Lathe(fu, top, top + 5.0, cyl(1.0), P("#d6a637")))
        S.add(Lathe(fu, top + 4.2, top + 5.0, cyl(1.05), P("#24272b")))


def danube_boats(S, ctx, plan):
    """the ships moored along the quays, from their OSM outlines: restaurant, hotel and party boats with a white
    superstructure of one to three decks on a hull with a pointed bow (moored bow upstream), the A38 (a former
    Ukrainian stone carrier, dark grey, its wheelhouse aft and a glass pavilion on deck) and its exhibition barge, and
    the Kossuth paddle steamer with its paddle boxes and yellow funnel."""
    for oid, t, g in boats(ctx["osm"]):
        x, y = g.centroid.coords[0]
        if 0 <= x < ctx["W"] and 0 <= y < ctx["D"]:
            boat(S, ctx, oid, t, g)


BUILDERS = [("Gellért Hotel and Baths", gellert), ("BME Building K", bme_k), ("Hungarian National Museum", national_museum),
            ("Kálvin tér skybridge", kalvin_bridge), ("Danube boats", danube_boats)]
