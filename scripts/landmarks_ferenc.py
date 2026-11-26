"""Late November 2026, fourth round, Pest side: the Ludovika Arena, Budapest Park, the Groupama Aréna and the Telekom
Campus beside it, the MVM Dome by Népliget, and Müpa (the Palace of Arts). Outlines from OSM; heights, colours and
details from the Esri aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np
import shapely
from shapely.geometry import Point

from landmarks import Box, Frame, Lathe, Poly, Roof, cyl, rect_of
from landmarks_city import base_under
from landmarks_hosok import keep
from landmarks_kit import compass, largest, painted
from style import CONCRETE, GLASS, GRASS, METAL, ROOF

ARENA, ARENA_PARTS = 594329719, (684152394, 684152396, 684152397)
PARK_AREA = 1123422916
PARK_STAGE, PARK_VIP, PARK_DANCE = 354887433, 354887434, 354887429
PARK_ROOFS = (354887430, 354887431, 354887432, 354887435, 354887436, 354887437, 354887439, 354887441)
PARK_BOXES = (1123422911, 1123422912, 1123422913, 1123422914, 1123422915)
GROUPAMA, GROUPAMA_PITCH = 3346783, 82620337
TELEKOM = 8246543
TELEKOM_PARTS = {583513323: (0, 5), 1548208894: (9, 10), 21203982: (0, 3), 21203983: (0, 8), 21203984: (0, 9),
                 21203985: (0, 2), 21203986: (6, 9)}
DOME = 1013593495
MUPA = 35779030
MUPA_PARTS = {1381325372: 20.0, 1381325373: 21.0, 1381325374: 37.0, 1381325375: 33.0, 1381325376: 31.0,
              1381325377: 41.0, 1381325378: 25.0, 1381325379: 25.0, 1381325380: 25.0}

NAMES = ["Ludovika Arena", "Budapest Park", "Groupama Aréna", "Telekom Campus", "MVM Dome", "Müpa"]
DROP = {ARENA, *ARENA_PARTS, PARK_STAGE, PARK_VIP, PARK_DANCE, *PARK_ROOFS, *PARK_BOXES, GROUPAMA, TELEKOM,
        *TELEKOM_PARTS, DOME, MUPA, *MUPA_PARTS}
KEEP = [(ARENA, 15), (GROUPAMA, 22), (TELEKOM, 39), (DOME, 40), (MUPA, 30)]
TAU = 2 * math.pi


def uv_of(cx, cy, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return {"U": lambda X, Y: (X - cx) * ca + (Y - cy) * sa, "V": lambda X, Y: -(X - cx) * sa + (Y - cy) * ca}


def hash2(a, b, k):
    h = (np.floor(a).astype(np.int64) * 73856093) ^ (np.floor(b).astype(np.int64) * 19349663)
    return np.mod(np.abs(h) >> 4, k)


# ------------------------------------------------------------------------------------------------ Ludovika Arena
def ludovika_arena(S, ctx, plan):
    """the Ludovika Arena (2019), the sports hall of the University of Public Service on Ludovika tér: a long white
    box whose roofline rises in a shallow arch from the ends, a steel lattice girder along the top of its long sides,
    climbers on wires up the white panels, and a tall glass front at its northern end."""
    P = ctx["P"]
    g = keep(ctx, ARENA)
    b0 = base_under(ctx, g, 0.3)
    cx, cy, L, Wd, ang = rect_of(g)
    white, white2, glass, mull = P("#eeefec"), P("#e1e3df"), P("#556b74", GLASS), P("#9aa2a6", METAL)
    steel, green, green2, roof, light = P("#c9cdd0", METAL), P("#4f7a3a", GRASS), P("#62894a", GRASS), P("#b5b7b4", ROOF), P("#d8dde0", GLASS)
    north = 1 if compass(0) @ np.array([math.cos(ang), math.sin(ang)]) > 0 else -1

    def fn(f, hw):
        d, s, U, V = f["d"], f["s"], f["U"], f["V"]
        t = np.clip(2 * np.abs(U) / L, 0, 1)
        top = 12.0 + 3.2 * (1 - t ** 2)
        inside = d > 0
        edge = inside & (d < 0.9)
        under = hw < top
        panel = np.where(np.mod(hw, 1.5) < 0.12, white2, white)
        vine = (np.abs(np.mod(s, 7.2) - 3.6) < 0.45) & (hw > 0.5) & (hw < top - 3.8)
        wall = np.where(vine, np.where(np.mod(hw, 2.0) < 1.0, green, green2), panel)
        band = hw >= top - 3.6
        lat = (np.abs(np.mod(s + (hw - top) * 1.1, 3.6) - 1.8) < 0.3) | (np.abs(np.mod(s - (hw - top) * 1.1, 3.6) - 1.8) < 0.3) \
            | (hw < top - 3.3) | (hw >= top - 0.35)
        wall = np.where(band, np.where(lat & (d < 0.5), steel, white2), wall)
        front = (north * U > L / 2 - 1.2) | ((north * U > L / 2 - 26) & (np.abs(V) > Wd / 2 - 1.2) & (hw < 9.5))
        wall = np.where(front & ~band, np.where(np.mod(s, 1.8) < 0.18, mull, glass), wall)
        o = np.where(edge & under, wall, 0)
        sky = (np.mod(U, 12.0) < 4.0) & (np.abs(V) < Wd / 2 - 8)
        o = np.where(inside & ~edge & (hw >= top - 0.7) & (hw < top), np.where(sky, light, roof), o)
        return o
    painted(S, g, b0, 16.0, fn, extra=uv_of(cx, cy, ang))


# ------------------------------------------------------------------------------------------------ Budapest Park
CONTAINERS = ["#2b5fa6", "#3d8c4a", "#e2e2de", "#d9822b", "#c33b2f", "#2f3337", "#e6c229"]


def budapest_park(S, ctx, plan):
    """Budapest Park (since 2014), the open-air concert ground at the Pest end of Rákóczi Bridge: the main stage, a
    black steel box of trusses with its roof and sound wings, facing the crowd across the arena; the VIP and sky boxes
    in glass along the south edge; the dance tent; and bars built from stacked shipping containers in many colours."""
    P = ctx["P"]
    area = ctx["area"]
    site = area[PARK_AREA][3] if PARK_AREA in area else None
    black, black2, deck, grey = P("#26282b", METAL), P("#36393d", METAL), P("#1f2022"), P("#5a5e62", METAL)
    white, glass, canvas = P("#efefec"), P("#4b5d66", GLASS), P("#f2f1ec", ROOF)
    cont = [P(c, METAL) for c in CONTAINERS]
    to_crowd = np.array(site.centroid.coords[0]) if site is not None else None
    if PARK_STAGE in area:
        g = area[PARK_STAGE][3]
        b0 = base_under(ctx, g, 0.3)
        cx, cy, L, Wd, ang = rect_of(g)
        fr = Frame(cx, cy, b0, ang)
        if to_crowd is not None:  # turn the frame so +u faces the crowd
            du, dv = fr.uv(*to_crowd)
            fr = fr.at(turn=[0, math.pi / 2, math.pi, -math.pi / 2][int(np.argmax([du, dv, -du, -dv]))])
            hu, hv = (L / 2, Wd / 2) if abs(du) >= abs(dv) else (Wd / 2, L / 2)
        else:
            hu, hv = L / 2, Wd / 2
        S.add(Box(fr, -hu, hu, -hv, hv, -0.5, 1.8, deck))
        for su in (-1, 1):
            for sv in (-1, 1):
                S.add(Box(fr, su * hu - 0.9 * (su > 0) - 0.0, su * hu + 0.9 * (su < 0), sv * hv - 0.9 * (sv > 0), sv * hv + 0.9 * (sv < 0), 0, 17.0, black2))
        S.add(Box(fr, -hu - 0.6, hu + 0.6, -hv - 0.6, hv + 0.6, 15.6, 17.2, black))
        S.add(Box(fr, -hu, -hu + 1.2, -hv, hv, 1.8, 15.6, black))
        for sv in (-1, 1):  # side screens and the sound wings flown beside the stage
            S.add(Box(fr, hu - 4.0, hu - 2.8, sv * (hv - 1.0) - 0.6, sv * (hv - 1.0) + 0.6, 1.8, 15.6, black))
            S.add(Box(fr, hu - 1.0, hu + 1.0, sv * (hv + 2.8) - 1.1, sv * (hv + 2.8) + 1.1, 6.0, 14.5, black2))
        for u in np.arange(-hu + 2, hu - 1, 3.0):  # lighting trusses under the roof
            S.add(Box(fr, u - 0.2, u + 0.2, -hv + 1, hv - 1, 14.6, 15.2, grey))
    if PARK_VIP in area:
        g = area[PARK_VIP][3]
        b0 = base_under(ctx, g, 0.3)

        def vip(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.8)
            wall = np.where((np.mod(hw, 3.6) < 0.45) | (np.mod(s, 4.0) < 0.3), black2, glass)
            o = np.where(edge & (hw < 7.2), np.where(hw < 3.6, np.where(np.mod(s, 6.0) < 3.0, cont[0], cont[2]), wall), 0)
            o = np.where(inside & (hw >= 3.4) & (hw < 3.7), deck, o)
            o = np.where(inside & (hw >= 7.2) & (hw < 8.0), white, o)
            return o
        painted(S, g, b0, 8.5, vip)
    if PARK_DANCE in area:  # the dance tent: a white membrane roof peaked over its posts
        g = area[PARK_DANCE][3]
        b0 = base_under(ctx, g, 0.3)

        def tent(f, hw):
            d = f["d"]
            roof_at = 6.0 + np.minimum(d, 8.0) * 0.45
            o = np.where((d > 0) & (hw >= roof_at - 0.5) & (hw < roof_at), canvas, 0)
            return np.where((d > 0) & (d < 0.7) & (np.mod(f["s"], 6.0) < 0.5) & (hw < roof_at), grey, o)
        painted(S, g, b0, 11.0, tent)
    for oid in PARK_ROOFS:  # bar canopies on posts
        if oid not in area:
            continue
        g = area[oid][3]
        b0 = base_under(ctx, g, 0.3)
        S.add(Poly(g, b0 + 3.2, b0 + 3.7, cont[oid % len(cont)]))
        cx, cy, L, Wd, ang = rect_of(g)
        fr = Frame(cx, cy, b0, ang)
        for su in (-1, 1):
            for sv in (-1, 1):
                S.add(Box(fr, su * (L / 2 - 0.5) - 0.12, su * (L / 2 - 0.5) + 0.12, sv * (Wd / 2 - 0.5) - 0.12, sv * (Wd / 2 - 0.5) + 0.12, 0, 3.2, grey))
    for oid in PARK_BOXES:  # bars of stacked shipping containers
        if oid not in area:
            continue
        g = area[oid][3]
        b0 = base_under(ctx, g, 0.3)
        tiers = 2 if g.area > 60 else 1

        def boxes(f, hw, oid=oid, tiers=tiers):
            d, s = f["d"], f["s"]
            k = hash2(np.floor(s / 6.1) + oid, np.floor(hw / 2.6), len(cont))
            pal = np.array(cont, np.uint16)[k]
            rib = np.mod(s, 0.6) < 0.2
            wall = np.where(rib & (np.mod(hw, 2.6) > 0.3), pal, np.where(np.mod(hw, 2.6) < 0.3, black2, pal))
            o = np.where((d > 0) & (d < 0.8) & (hw < 2.6 * tiers), wall, 0)
            return np.where((d > 0) & (hw >= 2.6 * tiers - 0.5) & (hw < 2.6 * tiers), pal, o)
        painted(S, g, b0, 2.6 * tiers + 0.5, boxes)


# ------------------------------------------------------------------------------------------------ Groupama Aréna
GL = {"F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
      "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
      "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"]}


def word_mask(X, Y, cx, cy, up, word, px):
    """cells of block letters (5 x 7 glyphs, px metres a pixel) centred at (cx, cy), their tops pointing along `up`
    (a unit vector on the grid), read to the right of `up` as seen from above."""
    rx, ry = -up[1], up[0]
    a = (X - cx) * rx + (Y - cy) * ry  # along the reading direction
    b = (X - cx) * up[0] + (Y - cy) * up[1]  # up the letters
    step = 6.5 * px
    m = np.zeros(X.shape, bool)
    for k, ch in enumerate(word):
        a0 = (k - (len(word) - 1) / 2) * step
        col = np.floor((a - a0) / px + 2.5).astype(int)
        row = np.floor(3.5 - b / px).astype(int)
        ok = (col >= 0) & (col < 5) & (row >= 0) & (row < 7)
        bm = np.array([[c == "1" for c in line] for line in GL[ch]])
        m |= ok & bm[np.clip(row, 0, 6), np.clip(col, 0, 4)]
    return m


def groupama(S, ctx, plan):
    """the Groupama Aréna (Ferencváros, 2014): a rounded box of green stands under a ring of silver roof, wrapped in a
    translucent grey skin behind a lattice of silver steel ribs, with the open band of the upper concourse under the
    eaves; FTC written in white on black solar panels on the roof's west and south sides."""
    P = ctx["P"]
    area = ctx["area"]
    g = largest(keep(ctx, GROUPAMA))
    b0 = base_under(ctx, g, 0.3)
    pitch = area[GROUPAMA_PITCH][3] if GROUPAMA_PITCH in area else g.buffer(-30)
    cx, cy, Lo, Wo, ang = rect_of(g)
    pcx, pcy, Lp, Wp, pang = rect_of(pitch)
    ca, sa = math.cos(ang), math.sin(ang)
    gr, gr2, run, line = P("#4f8f3c", GRASS), P("#5f9c48", GRASS), P("#3f7a34", GRASS), P("#f1efe6")
    seat, seat2, conc = P("#1f6b3e"), P("#27784a"), P("#bdb9b0", CONCRETE)
    silver, silver2, steel = P("#cfd3d5", ROOF), P("#c1c6c9", ROOF), P("#dfe2e3", METAL)
    skin, skin2, dark, solar, letter = P("#a8b0b3", GLASS), P("#98a1a4", GLASS), P("#3a3f43"), P("#25292e", GLASS), P("#f4f4f2", ROOF)
    pu = lambda X, Y: np.abs((X - pcx) * math.cos(pang) + (Y - pcy) * math.sin(pang)) - Lp / 2
    pv = lambda X, Y: np.abs(-(X - pcx) * math.sin(pang) + (Y - pcy) * math.cos(pang)) - Wp / 2
    marks = [(5656.5, 7581.0), (5762.0, 7609.0)]

    def letters(X, Y):
        m = np.zeros(X.shape, np.float32)
        panel = np.zeros(X.shape, bool)
        for mx, my in marks:
            du, dv = (mx - cx) * ca + (my - cy) * sa, -(mx - cx) * sa + (my - cy) * ca
            if abs(du) / Lo > abs(dv) / Wo:  # on an end: tops point back along u
                up = (-ca * np.sign(du), -sa * np.sign(du))
            else:
                up = (sa * np.sign(dv), -ca * np.sign(dv))
            w = word_mask(X, Y, mx, my, up, "FTC", 3.3)
            a = (X - mx) * -up[1] + (Y - my) * up[0]
            b = (X - mx) * up[0] + (Y - my) * up[1]
            panel |= (np.abs(a) < 33) & (np.abs(b) < 15)
            m = np.maximum(m, w.astype(np.float32))
        return np.where(m > 0, 2.0, np.where(panel, 1.0, 0.0))
    ext = {"pu": pu, "pv": pv, "lt": letters, **uv_of(cx, cy, ang)}
    H = 22.5

    def fn(f, hw):
        d, s, du, dv, lt = f["d"], f["s"], f["pu"], f["pv"], f["lt"]
        inside = d > 0
        o = np.zeros(np.broadcast_shapes(d.shape, hw.shape), np.uint16)
        e = np.maximum(du, dv)  # metres outside the pitch's rectangle (negative inside)
        floor = inside & (e < 7.0) & (hw >= -0.6) & (hw < 0.0)
        stripe = np.mod(np.floor((f["U"]) / 5.5), 2) == 0
        border = (np.abs(du) < 0.12) | (np.abs(dv) < 0.12) | (np.abs(f["U"]) < 0.1)
        o = np.where(floor, np.where(e > 0, run, np.where(border, line, np.where(stripe, gr, gr2))), o)
        # the stands rise from 7 m off the touchlines to the back of the bowl
        rake = 1.0 + (e - 7.0) * 0.62
        stand = inside & (e >= 7.0) & (d > 2.0) & (hw >= rake - 1.0) & (hw < rake) & (rake < 19.0)
        o = np.where(stand, np.where(np.mod(rake, 0.85) < 0.42, seat, seat2), o)
        o = np.where(inside & (e >= 7.0) & (d > 2.0) & (hw < rake - 1.0) & (hw >= rake - 1.6), conc, o)
        # the roof, from the back of the stands to 10 m over the field's edge
        roof = inside & (e >= 3.0) & (hw >= H - 1.4) & (hw < H)
        seam = np.mod(s, 4.0) < 0.35
        tone = np.where(lt > 1.5, letter, np.where(lt > 0.5, solar, np.where(seam, silver2, silver)))
        o = np.where(roof, tone, o)
        o = np.where(inside & (e >= 3.0) & (e < 3.6) & (hw >= H - 3.0) & (hw < H), steel, o)
        # the skin and its ribs
        shell = inside & (d < 1.0) & (hw < H)
        rib = (np.mod(s, 9.0) < 0.6) | (np.abs(np.mod(s + hw * 0.9, 18.0) - 9.0) < 0.35) | (np.mod(hw, 7.2) < 0.4)
        open_band = (hw >= 14.5) & (hw < 18.0) & (np.mod(s, 9.0) > 0.6)
        ground = hw < 4.0
        wall = np.where(rib & (d < 0.5), steel, np.where(open_band, dark, np.where(np.mod(s, 1.5) < 0.2, skin2, skin)))
        wall = np.where(ground & ~rib, np.where(np.mod(s, 3.0) < 0.3, steel, dark), wall)
        o = np.where(shell, wall, o)
        return o
    painted(S, g, b0, H + 0.5, fn, extra=ext)
    S.clear.append((cx, cy, Lo / 2 + 4))


# ------------------------------------------------------------------------------------------------ Telekom Campus
def telekom(S, ctx, plan):
    """the Telekom Campus (2022) on Könyves Kálmán körút: blue-green glass on a grid of slim mullions, wings of eight
    and nine floors round courts under glass, bays of gold glass tilted out of the facade, and a wing that bridges the
    entrance at its top three floors on a row of slender white columns."""
    P = ctx["P"]
    area = ctx["area"]
    glass, glass2, mull, gold, gold2 = P("#4f7f88", GLASS), P("#5d8d95", GLASS), P("#38474d", METAL), P("#c8a65a", GLASS), P("#b6934a", GLASS)
    roof, white, atrium = P("#9ea2a3", ROOF), P("#f0f0ee"), P("#c9dbe0", GLASS)
    FL = 4.3
    b0 = base_under(ctx, keep(ctx, TELEKOM), 0.3)
    for oid, (l0, l1) in TELEKOM_PARTS.items():
        if oid not in area:
            continue
        g = area[oid][3]
        z0, z1 = l0 * FL, l1 * FL
        low = l1 <= 3

        def fn(f, hw, z0=z0, z1=z1, low=low, oid=oid):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.9)
            band = (hw >= z0) & (hw < z1)
            fl = np.floor(hw / FL)
            bay = hash2(np.floor(s / 6.0) + oid, np.floor(fl / 2), 9) == 0
            wall = np.where((np.mod(s, 1.6) < 0.18) | (np.mod(hw, FL) < 0.3), mull, np.where(np.mod(fl, 2) == 0, glass, glass2))
            wall = np.where(bay & (fl >= 1), np.where(np.mod(s, 1.6) < 0.18, gold2, gold), wall)
            o = np.where(edge & band, wall, 0)
            top = inside & (hw >= z1 - 0.6) & (hw < z1)
            o = np.where(top, atrium if low else roof, o)
            o = np.where(edge & (hw >= z1) & (hw < z1 + 1.1), glass2, o)
            o = np.where(inside & (z0 > 0) & (hw >= z0) & (hw < z0 + 0.6), white, o)
            return o
        painted(S, g, b0, z1 + 1.2, fn)
        if l0 > 0:  # the bridge wing's columns, along its edge every 6 m
            ring = largest(g).exterior
            for t in np.arange(1.5, ring.length, 6.0):
                p = ring.interpolate(t)
                q = largest(g).buffer(-1.2)
                pp = q.exterior.interpolate(q.exterior.project(p))
                inside_other = any(area[o2][3].buffer(-0.5).contains(pp) for o2, (a, b) in TELEKOM_PARTS.items()
                                   if o2 in area and a == 0 and o2 != oid)
                if not inside_other:
                    S.add(Lathe(Frame(pp.x, pp.y, b0), 0, z0, cyl(0.45), white, n=8))


# ------------------------------------------------------------------------------------------------ MVM Dome
def mvm_dome(S, ctx, plan):
    """the MVM Dome (György Skardelli, 2021), the handball arena by Népliget: an oval leaning outwards as it rises,
    wrapped in broad white bands that cross each other on the slant over dark glass, an LED band round the top; a
    flat beige roof over the hall inside a ring of plant on the roof's rim, 40.5 m at its highest."""
    P = ctx["P"]
    g = largest(keep(ctx, DOME))
    b0 = base_under(ctx, g, 0.3)
    cx, cy, L, Wd, ang = rect_of(g)
    a, b = L / 2, Wd / 2
    white, white2, glass, glass2, led = P("#f0f0ec"), P("#e2e3df"), P("#3c4b54", GLASS), P("#4a5a63", GLASS), P("#7a4f86", GLASS)
    roof, roof2, plant, plant2 = P("#d8cdb6", ROOF), P("#cfc3aa", ROOF), P("#8a8f92", METAL), P("#a6abae", METAL)
    H = 34.0
    fams = [(9.0, 6.0, 0.0, 1), (18.5, 5.5, 2.1, 2), (27.0, 4.5, 4.0, 1)]
    ca, sa = math.cos(ang), math.sin(ang)

    def ext_r(X, Y):
        u, v = (X - cx) * ca + (Y - cy) * sa, -(X - cx) * sa + (Y - cy) * ca
        return np.sqrt((u / a) ** 2 + (v / b) ** 2)

    def ext_t(X, Y):
        u, v = (X - cx) * ca + (Y - cy) * sa, -(X - cx) * sa + (Y - cy) * ca
        return np.arctan2(v / b, u / a)
    g2 = g.buffer(4.0)

    def fn(f, hw):
        r, th = f["r"], f["th"]
        rout = 1.0 + 0.045 * np.clip(hw / H, 0, 1)
        shell = (r <= rout) & (r > rout - 1.3 / a) & (hw < H)
        bands = np.zeros(np.broadcast_shapes(r.shape, hw.shape), bool)
        for c, A, ph, k in fams:
            bands |= np.abs(hw - (c + A * np.sin(k * th + ph))) < 3.4
        wall = np.where(bands, np.where(np.mod(th * 40, 1) < 0.08, white2, white), np.where(np.mod(th * 120, 1) < 0.1, glass2, glass))
        wall = np.where(hw >= H - 3.2, np.where((np.cos(th - 1.4) > 0.55) & (hw < H - 0.6), led, white), wall)
        wall = np.where(hw < 4.5, np.where(np.mod(th * 120, 1) < 0.1, white2, glass), wall)
        o = np.where(shell, wall, 0)
        inner = 0.86
        rz = H + 6.5 * np.clip(1 - (r / inner) ** 2, 0, 1)
        o = np.where((r < inner) & (hw >= rz - 0.8) & (hw < rz), np.where(np.mod(np.floor(th * 18 / math.pi), 2) == 0, roof, roof2), o)
        ring = (r >= inner) & (r < rout - 1.3 / a)
        o = np.where(ring & (hw >= H - 1.5) & (hw < H - 0.7), plant, o)
        o = np.where(ring & (hw >= H - 0.7) & (hw < H + 1.2) & (np.mod(th * 60, 1) < 0.35) & (np.mod(r * a, 4.0) < 2.2), plant2, o)
        return o
    painted(S, g2, b0, H + 7.0, fn, extra={"r": ext_r, "th": ext_t})
    S.clear.append((cx, cy, L / 2 + 6))


# ------------------------------------------------------------------------------------------------ Müpa
def mupa(S, ctx, plan):
    """Müpa, the Palace of Arts (Zoboki, Demeter and Partners, 2005): a long podium in pale limestone with a high
    glass front under a projecting roof on slender columns on its north-east side, and over it the dark grey boxes of
    the Bartók concert hall and the Festival Theatre's fly tower, the Ludwig Museum's sawtooth skylights at the
    north-western end."""
    P = ctx["P"]
    area = ctx["area"]
    g = largest(keep(ctx, MUPA))
    b0 = base_under(ctx, g, 0.3)
    cx, cy, L, Wd, ang = rect_of(g)
    stone, stone2, glass, mull = P("#e2dccb"), P("#d3ccb9"), P("#5a6e76", GLASS), P("#c9cbc8", METAL)
    dark, dark2, roof, sky, white = P("#55595c"), P("#4a4e51"), P("#a4a6a4", ROOF), P("#b9d0d8", GLASS), P("#efeeea")
    E = 18.0
    ca, sa = math.cos(ang), math.sin(ang)
    ne = 1.0 if compass(45) @ np.array([-math.sin(ang), math.cos(ang)]) > 0 else -1.0  # the side facing north-east

    def fn(f, hw):
        d, s, V = f["d"], f["s"], f["V"]
        inside, edge = d > 0, (d > 0) & (d < 0.9)
        front = ne * V > Wd / 2 - 6.0
        lime = np.where(np.mod(hw, 1.2) < 0.12, stone2, stone)
        slit = (np.mod(hw, 4.5) > 2.6) & (np.mod(hw, 4.5) < 3.0) & (np.mod(s, 30.0) < 22.0)
        wall = np.where(slit, dark2, lime)
        wall = np.where(front, np.where((np.mod(s, 2.0) < 0.2) | (np.mod(hw, 4.5) < 0.25), mull, glass), wall)
        o = np.where(edge & (hw < E), wall, 0)
        o = np.where(inside & ~edge & (hw >= E - 0.6) & (hw < E), roof, o)
        o = np.where(edge & (hw >= E) & (hw < E + 0.8), stone2, o)
        return o
    painted(S, g, b0, E + 1.0, fn, extra=uv_of(cx, cy, ang))
    fr = Frame(cx, cy, b0, ang)
    v_out = ne * (Wd / 2 + 5.0)
    S.add(Box(fr, -L / 2 + 6, L / 2 - 6, min(ne * (Wd / 2 - 1), v_out), max(ne * (Wd / 2 - 1), v_out), E - 0.2, E + 0.8, white))
    for u in np.arange(-L / 2 + 8, L / 2 - 6, 7.5):  # the slender columns under the canopy
        S.add(Lathe(fr.at(u, v_out - ne * 0.8), 0, E - 0.2, cyl(0.35), white, n=8))
    for oid, H in MUPA_PARTS.items():
        if oid not in area or H <= E:
            continue
        pg = largest(area[oid][3])
        saw = oid == 1381325379
        hall = H >= 33

        def up(f, hw, H=H, saw=saw, hall=hall):
            d, s, U = f["d"], f["s"], f["U"]
            inside, edge = d > 0, (d > 0) & (d < 0.9)
            band = (hw >= E - 1) & (hw < H)
            clad = np.where(np.mod(hw, 1.2) < 0.12, stone2, stone)
            if hall:  # the halls' stone boxes, slit windows in their upper courses
                clad = np.where((hw > H - 6.0) & (hw < H - 3.5) & (np.mod(s, 4.0) < 2.2), dark2, clad)
            o = np.where(edge & band, clad, 0)
            if saw:
                tooth = np.mod(U, 6.0)
                ztop = H + tooth * 0.55
                o = np.where(inside & (hw >= H - 0.6) & (hw < ztop), np.where(tooth > 4.8, sky, roof), o)
            else:
                o = np.where(inside & (hw >= H - 0.6) & (hw < H), roof, o)
                o = np.where(edge & (hw >= H) & (hw < H + 0.8), dark if hall else stone2, o)
            return o
        painted(S, pg, b0, H + 4.0, up, extra=uv_of(cx, cy, ang))


BUILDERS = [("Ludovika Arena", ludovika_arena), ("Budapest Park", budapest_park), ("Groupama Aréna", groupama),
            ("Telekom Campus", telekom), ("MVM Dome", mvm_dome), ("Müpa", mupa)]
