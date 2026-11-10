"""The Rákóczi tér market hall (II. sz. vásárcsarnok, 1897; burnt out in 1988 and rebuilt by 1991): two naves crossing
in the middle, each with lower aisles, two-storey pavilions under hipped tile roofs on the four corners and one-storey
links between them, in yellow brick with red bands and white limestone. Every arm ends in a gable with a great arched
window in blue iron; the main one, on Rákóczi tér, has the clock and the sign over the entrance, a heavy raking cornice
and the city's arms with a lion and a griffin on top, between wings with triple windows on two floors, balustrades and
stone obelisks. OSM's outline places it; the rest is measured on aerial photos and street photos (docs/landmarks.md).
"""
import math

import numpy as np
from shapely.geometry import LineString

from landmarks import WINDOW, Box, Capsule, Ellipsoid, Lathe, Roof, TBox, cone
from landmarks_city import Gable, base_under, named_near
from landmarks_more import UProfile, front_frame, largest, uv_of
from style import GLASS, LAMP, METAL, ROOF

HALL = 4514296
NAMES = ["Rákóczi Market Hall"]
KEEP_GROUND = (HALL,)  # still standing for voxelize.py's ground, green and trees (Plan.ground_cover)

NH, AH = 7.2, 13.0            # half-widths of a nave and of a whole arm (nave and aisles)
NAVE_E, NAVE_R = 15.0, 17.8   # nave walls, ridge
AISLE_E, AISLE_R = 10.8, 12.2  # aisle walls; the lean-to's top against the nave
LINK_E, PAV_E, PAV_R = 7.8, 10.8, 3.6
GLASS_A, GLASS_W0, GLASS_S, GLASS_H = 3.5, 6.3, 12.0, 2.0  # the arched window: half-width, sill, springing, rise
DOOR_A, DOOR_H = 3.5, 4.6
CORNICE, RISE = 14.5, 1.6     # the gable's entablature over its ends, and how much it rises to the middle


def drop_ids(osm):
    hall = next((g for oid, k, t, g in osm.areas if oid == HALL), None)
    if hall is None:
        return set()
    inner = hall.buffer(-1.0)
    x0, y0, x1, y1 = inner.bounds
    return {HALL} | {oid for oid, k, t, g in osm.areas if oid != HALL and ("building" in t or "building:part" in t)
                     and x0 <= g.bounds[0] and g.bounds[2] <= x1 and y0 <= g.bounds[1] and g.bounds[3] <= y1
                     and inner.contains(g.representative_point())}


def spans(fr, g, u=None, v=None):
    """the stretches [a, b] where the line u = const (along v) or v = const (along u) of the frame crosses g."""
    if u is not None:
        ln = LineString([fr.xy(u, -500), fr.xy(u, 500)])
    else:
        ln = LineString([fr.xy(-500, v), fr.xy(500, v)])
    out = []
    for s in getattr(ln.intersection(g), "geoms", [ln.intersection(g)]):
        if s.is_empty or s.length < 0.5:
            continue
        a, b = (fr.uv(*p)[1 if u is not None else 0] for p in (s.coords[0], s.coords[-1]))
        out.append(tuple(sorted((a, b))))
    return sorted(out)


def bands(brick, band, cap=None, top=None, period=2.0, th=0.5):
    """brick in horizontal bands; with a cap, the top half metre below `top` in the roof's colour (an eave seen from
    above, where a roof's thin edge leaves the wall's top showing)."""
    def f(u, v, w):
        o = np.where(np.mod(w, period) < th, band, brick)
        if cap is not None:
            o = np.where(w >= top - 0.5, cap, o)
        return o.astype(np.uint16)
    return f


def rise_of(u):
    """the entablature's rise over its flat ends: a low pediment, stepped at the ends."""
    return RISE * np.clip((NH - 0.4 - np.abs(u)) / (NH - 0.4), 0, 1)


def crest(S, fa, w0, stone):
    """the city's arms on the gable: a crowned shield held by a lion (left) and a griffin (right)."""
    S.add(Box(fa, -1.7, 1.7, -0.6, 0.5, w0, w0 + 0.3, stone))
    S.add(Ellipsoid(fa.at(0, 0.05, w0 + 1.0), 0.5, 0.28, 0.72, stone))
    S.add(Box(fa, -0.45, 0.45, -0.15, 0.3, w0 + 1.65, w0 + 1.95, stone))
    for k in (-0.35, 0.0, 0.35):
        S.add(Box(fa, k - 0.12, k + 0.12, -0.05, 0.2, w0 + 1.95, w0 + 2.25, stone))
    for s in (-1, 1):  # bodies rearing towards the shield
        S.add(Ellipsoid(fa.at(s * 1.2, -0.05, w0 + 0.6), 0.45, 0.32, 0.55, stone))
        S.add(Capsule(fa, (s * 1.15, 0, w0 + 0.7), (s * 0.85, 0.05, w0 + 1.45), 0.32, stone))
        S.add(Capsule(fa, (s * 0.9, 0.1, w0 + 1.35), (s * 0.45, 0.2, w0 + 1.5), 0.13, stone))
    S.add(Ellipsoid(fa.at(-0.8, 0.05, w0 + 1.8), 0.4, 0.34, 0.4, stone))           # the lion's maned head
    S.line(fa, (-1.55, 0, w0 + 0.35), (-1.8, 0, w0 + 1.25), stone)
    S.add(Ellipsoid(fa.at(0.8, 0.05, w0 + 1.85), 0.27, 0.25, 0.3, stone))          # the griffin's head and beak
    S.add(Capsule(fa, (0.75, 0.1, w0 + 1.85), (0.5, 0.15, w0 + 1.75), 0.1, stone))
    S.add(Capsule(fa, (1.15, -0.2, w0 + 1.2), (1.5, -0.25, w0 + 2.35), 0.22, stone))  # its raised wings
    S.add(Capsule(fa, (1.3, -0.25, w0 + 1.05), (1.75, -0.25, w0 + 1.9), 0.17, stone))


def gable(S, fa, c, gz, main):
    """the end of a nave: a frame on the facade's plane, u along it, v out of it. The arched window over the doors,
    piers with relief panels and lamps, the raking entablature; on the main front the clock, the sign and the arms."""
    walls = [c["brick"], c["band"]]
    S.add(UProfile(fa, -NH, NH, -1.0, 0.0, lambda u: np.full_like(u, NAVE_E - 0.5), lambda u: CORNICE + rise_of(u),
                   c["wall"]))

    def ent(u, v, w):  # a frieze, a row of dentils, the corona
        h = w - rise_of(u)
        corona = h >= CORNICE + 0.9
        dent = (h >= CORNICE + 0.4) & (np.mod(np.floor(u / 0.5), 2) == 0)
        o = np.where(h < CORNICE + 0.4, c["stone3"], np.where(corona & (h < CORNICE + 1.3), c["stone"], c["stone2"]))
        return np.where(corona | dent | (v <= 0.45), o, 0).astype(np.uint16)
    S.add(UProfile(fa, -NH - 0.6, NH + 0.6, -0.9, 0.9, lambda u: CORNICE - 0.3 + rise_of(u),
                   lambda u: CORNICE + 1.6 + rise_of(u), ent))
    top = CORNICE + 1.6 + RISE
    if main:
        S.add(Box(fa, -1.6, 1.6, -0.9, 0.6, top - 0.4, top + 0.5, c["stone"]))
        crest(S, fa, top + 0.5, c["sculpt"])
    for s in (-1, 1):  # stone consoles under the cornice's ends, quoins, the plinth
        S.add(Box(fa, *sorted((s * (NH - 0.6), s * (NH + 0.3))), -0.3, 0.35, CORNICE - 1.8, CORNICE - 0.3, c["stone"]))
        S.add(Box(fa, *sorted((s * (NH - 0.5), s * NH)), -0.6, 0.05, 2.0, CORNICE - 1.8, c["quoin"], mode="paint",
                  targets=walls))
        S.add(Box(fa, *sorted((s * DOOR_A, s * NH)), -0.6, 0.35, -3, 2.2, c["stone"]))
        S.add(Box(fa, *sorted((s * (DOOR_A + 0.1), s * (NH + 0.1))), -0.4, 0.3, 6.0, 6.5, c["stone"]))
        S.add(Box(fa, *sorted((s * (DOOR_A + 0.1), s * (NH + 0.1))), -0.4, 0.4, AISLE_E - 0.7, AISLE_E, c["stone"]))
        S.add(Box(fa, *sorted((s * (GLASS_A + 0.1), s * (GLASS_A + 1.0))), -0.4, 0.3, GLASS_S - 0.4, GLASS_S + 0.2,
                  c["stone"]))
        # the relief panel and the lamp on each pier
        pc = s * (GLASS_A + NH) / 2 + s * 0.2
        S.add(Box(fa, pc - 0.8, pc + 0.8, -0.2, 0.45, 7.0, 9.4, c["stone"]))
        S.add(Box(fa, pc - 0.5, pc + 0.5, 0.4, 0.6, 7.4, 9.0, c["stone2"]))
        S.add(Box(fa, pc - 1.0, pc + 1.0, -0.2, 0.7, 9.4, 9.8, c["stone"]))
        lp = s * (DOOR_A + 0.6)
        S.line(fa, (lp, 0.1, 6.9), (lp, 0.8, 6.9), c["iron2"])
        S.line(fa, (lp, 0.8, 6.9), (lp, 0.8, 8.0), c["iron2"])
        S.add(Box(fa, lp - 0.25, lp + 0.25, 0.55, 1.05, 6.2, 6.7, c["lamp"]))
    # the archivolt: a chequered band of red and white brick round a ring of brick voussoirs; the keystone
    fa90 = fa.at(turn=math.pi / 2)

    def arch_col(u, v, w):
        out_ = (v / (GLASS_A + 1.3)) ** 2 + ((w - GLASS_S) / (GLASS_H + 1.3)) ** 2 > (1 - 0.55 / (GLASS_A + 1.3)) ** 2
        chk = np.mod(np.floor(v / 0.5) + np.floor(w / 0.5), 2) == 0
        return np.where(out_, np.where(chk, c["band"], c["stone"]), c["brick"]).astype(np.uint16)
    S.add(Gable(fa90, -0.6, 0.15, GLASS_A + 1.3, GLASS_S - 0.2, GLASS_S, GLASS_H + 1.3, arch_col))
    S.add(Box(fa, -0.5, 0.5, -0.4, 0.4, GLASS_S + GLASS_H - 0.3, CORNICE + RISE - 0.2, c["stone"]))
    # the window: set back half a metre, blue iron bars over small panes
    S.add(Gable(fa90, -0.5, 0.6, GLASS_A, GLASS_W0, GLASS_S, GLASS_H, 0, mode="carve"))

    def glazing(u, v, w):
        a = np.abs(v)
        frame_ = (a > GLASS_A - 0.5) | ((a >= 1.6) & (a < 2.1)) | (np.mod(w - GLASS_W0, 2.0) < 0.5) | \
                 ((v / GLASS_A) ** 2 + ((w - GLASS_S) / GLASS_H) ** 2 > 0.72) & (w > GLASS_S)
        pane = np.mod(np.floor(v / 0.5) + np.floor(w / 0.5), 2) == 0
        return np.where(frame_, c["iron"], np.where(pane, c["glass"], c["glass2"])).astype(np.uint16)
    S.add(Gable(fa90, -1.0, -0.5, GLASS_A, GLASS_W0, GLASS_S, GLASS_H, glazing))
    # the entrance: doors under an iron frieze; the sign; the clock over it on the main front
    dd = 1.6 if main else 0.5  # open on the main front, closed iron doors elsewhere
    S.add(Box(fa, -DOOR_A, DOOR_A, -dd, 0.6, gz - 0.2, DOOR_H, 0, mode="carve"))
    S.add(Box(fa, -DOOR_A, DOOR_A, -dd - 0.4, -dd, gz - 0.2, DOOR_H, c["dark"] if main else c["iron2"]))
    S.add(Box(fa, -DOOR_A - 0.1, DOOR_A + 0.1, -0.3, 0.2, gz - 0.2, gz, c["stone"]))
    for k in (-1, 1):
        S.add(Box(fa, k * 1.9 - 0.25, k * 1.9 + 0.25, -0.4, 0.1, gz, DOOR_H, c["iron"]))
        S.add(Box(fa, *sorted((k * (DOOR_A - 0.4), k * DOOR_A)), -dd, 0.1, gz, DOOR_H, c["iron"]))
        if main:  # the iron leaves, folded back
            S.add(Box(fa, *sorted((k * (DOOR_A - 0.9), k * (DOOR_A - 0.4))), -1.6, -0.6, gz, DOOR_H - 0.6, c["iron2"]))

    def frieze(u, v, w):
        ring = (np.mod(np.floor(u / 0.5), 3) == 1) & (w < DOOR_H + 0.8) & (w >= DOOR_H + 0.3)
        letters = (w >= GLASS_W0 - 0.6) & (w < GLASS_W0 - 0.3) & (np.abs(u) < 3.2) & (np.mod(np.floor(u / 0.5), 2) == 0)
        sign = (w >= GLASS_W0 - 0.9) & (w < GLASS_W0 - 0.1) & (np.abs(u) < 3.5)
        o = np.where(ring, c["iron3"], c["iron"])
        o = np.where(sign, np.where(letters, c["iron2"], c["iron3"]), o)
        return o.astype(np.uint16)
    S.add(Box(fa, -DOOR_A - 0.1, DOOR_A + 0.1, -0.5, 0.25, DOOR_H, GLASS_W0, frieze))
    if main:
        cz = GLASS_W0 + 1.4
        S.add(Box(fa, -0.9, 0.9, -0.5, 0.45, GLASS_W0, cz - 0.6, c["iron"]))
        S.add(Ellipsoid(fa.at(0, 0.0, cz), 1.15, 0.45, 1.2, c["iron"]))
        S.add(Ellipsoid(fa.at(0, 0.2, cz), 0.8, 0.35, 0.8, c["dial"]))
        S.add(Box(fa, -0.25, 0.25, -0.3, 0.35, cz + 1.0, cz + 1.7, c["iron"]))


def wing(S, fa, s, c, main):
    """an aisle's end beside the gable, from NH to AH on side s: triple windows on two floors, a red frieze and a
    cornice; on the main front a balustrade and an obelisk at the outer end."""
    walls = [c["brick"], c["band"]]
    u0, u1 = sorted((s * NH, s * AH))
    um = s * (NH + AH) / 2
    S.add(Box(fa, u0, u1, -0.6, 0.25, -3, 1.6, c["stone"]))
    S.add(Box(fa, um - 2.3, um + 2.3, -0.6, 0.05, 1.8, 6.0, c["stone"], mode="paint", targets=walls))
    S.add(Box(fa, um - 2.0, um + 2.0, -0.6, 0.05, 6.6, 9.2, c["stone"], mode="paint", targets=walls))
    for k in (-1, 0, 1):
        x = um + k * 1.5

        def grille(u, v, w):
            return np.where(np.mod(np.floor(u / 0.5), 2) == 0, c["iron"], c["win"]).astype(np.uint16)
        S.add(Box(fa, x - 0.5, x + 0.5, -0.6, 0.05, 2.2, 4.8, grille, mode="paint", targets=[c["stone"]]))
        S.add(Box(fa, x - 0.5, x + 0.5, -0.6, 0.05, 5.3, 5.8, c["win"], mode="paint", targets=[c["stone"]]))
        S.add(Box(fa, x - 0.5, x + 0.5, -0.6, 0.05, 6.9, 8.9, c["win"], mode="paint", targets=[c["stone"]]))
        S.add(Box(fa, x - 0.75, x + 0.75, -0.6, 0.05, 9.2, 9.6, c["band"], mode="paint", targets=walls))
    S.add(Box(fa, u0, u1, -0.4, 0.25, 6.0, 6.5, c["stone"]))
    S.add(Box(fa, u0, u1, -0.6, 0.05, 6.5, 6.6, c["band"], mode="paint", targets=walls))

    def red_frieze(u, v, w):
        dent = (w >= AISLE_E - 1.0) & (np.mod(np.floor(u / 0.5), 2) == 0)
        return np.where(dent, c["band2"], c["band"]).astype(np.uint16)
    S.add(Box(fa, u0, u1, -0.6, 0.2, AISLE_E - 1.2, AISLE_E - 0.7, red_frieze))
    S.add(Box(fa, *sorted((s * NH, s * (AH + 0.3))), -0.6, 0.6, AISLE_E - 0.7, AISLE_E, c["stone"]))
    S.add(Box(fa, *sorted((s * (AH - 0.5), s * AH)), -0.6, 0.05, 1.6, AISLE_E - 1.2, c["quoin"], mode="paint",
              targets=walls))
    if main:
        def balusters(u, v, w):
            post = np.mod(np.floor(u / 0.5), 2) == 0
            return np.where((w < AISLE_E + 0.25) | (w >= AISLE_E + 0.75) | post, c["stone"], 0).astype(np.uint16)
        S.add(Box(fa, u0, u1, -0.5, 0.0, AISLE_E, AISLE_E + 1.0, balusters))
        uo = s * (AH - 0.8)
        S.add(Box(fa, uo - 0.8, uo + 0.8, -0.8, 0.6, AISLE_E, AISLE_E + 1.3, c["stone"]))
        fo = fa.at(uo, -0.1)
        S.add(TBox(fo, 0.55, 0.55, 0.28, 0.28, AISLE_E + 1.3, AISLE_E + 3.7, c["stone"]))
        S.add(Lathe(fo, AISLE_E + 3.7, AISLE_E + 4.3, cone(0.4, 0.02), c["stone"], n=4, rot=math.pi / 4))
    else:
        S.add(Box(fa, u0, u1, -0.5, 0.0, AISLE_E, AISLE_E + 0.6, c["stone"]))
    # a scroll from the cornice's end down to the link, and a lantern on the corner
    S.add(Capsule(fa, (s * (AH + 0.1), -0.3, AISLE_E - 0.8), (s * (AH + 0.6), -0.3, LINK_E + 0.3), 0.3, c["stone"]))
    S.add(Ellipsoid(fa.at(s * (AH + 0.7), -0.3, LINK_E + 0.4), 0.35, 0.3, 0.35, c["stone"]))
    S.line(fa, (s * (AH - 0.5), 0.1, 7.5), (s * (AH - 0.5), 0.9, 7.5), c["iron2"])
    S.add(Box(fa, s * (AH - 0.5) - 0.25, s * (AH - 0.5) + 0.25, 0.65, 1.15, 6.9, 7.4, c["lamp"]))


def link(S, fa, a, b, c, canopy, set_back=0.0):
    """a one-storey link between a wing (at |u| = a) and a pavilion (at |u| = b), on one side of a facade."""
    walls = [c["brick"], c["band"]]
    u0, u1 = sorted((a, b))
    v0 = -set_back
    S.add(Box(fa, u0, u1, v0 - 0.6, v0 + 0.25, -3, 1.4, c["stone"]))
    n = max(int(abs(b - a) // 2.2), 1)
    for k in range(n):
        x = u0 + (u1 - u0) * (k + 0.5) / n
        if canopy and k == n // 2:  # a loading door under a canopy of iron and glass
            S.add(Box(fa, x - 1.25, x + 1.25, v0 - 0.6, v0 + 0.05, 0, 4.2, c["iron"], mode="paint", targets=walls))
            S.add(Box(fa, x - 1.7, x + 1.7, v0, v0 + 2.4, 4.6, 4.9, c["glass_roof"]))  # over the pavement
            S.add(Box(fa, x - 1.8, x + 1.8, v0 + 2.2, v0 + 2.5, 4.4, 5.0, c["iron"]))
            for e in (-1.6, 1.6):
                S.line(fa, (x + e, v0, 3.6), (x + e, v0 + 2.3, 4.6), c["iron"])
            continue
        S.add(Box(fa, x - 0.75, x + 0.75, v0 - 0.6, v0 + 0.05, 1.4, 6.4, c["stone"], mode="paint", targets=walls))

        def grille(u, v, w):
            return np.where(np.mod(np.floor(w / 0.5), 3) == 0, c["iron"], c["win"]).astype(np.uint16)
        S.add(Box(fa, x - 0.5, x + 0.5, v0 - 0.6, v0 + 0.05, 1.8, 6.0, grille, mode="paint", targets=[c["stone"]]))
    S.add(Box(fa, u0, u1, v0 - 0.6, v0 + 0.1, LINK_E - 1.3, LINK_E - 0.7, c["band"], mode="paint", targets=walls))
    S.add(Box(fa, u0, u1, v0 - 0.5, v0 + 0.45, LINK_E - 0.7, LINK_E, c["stone"]))
    S.add(Box(fa, u0, u1, v0 - 0.5, v0, LINK_E, LINK_E + 0.5, c["stone"]))
    if not canopy:  # the small gable with scrolls over the middle of the link
        xm = (u0 + u1) / 2
        S.add(Box(fa, xm - 0.8, xm + 0.8, v0 - 0.5, v0 + 0.2, LINK_E, LINK_E + 1.3, c["stone"]))
        S.add(Roof(fa.at(xm, v0, 0, math.pi / 2), -0.5, 0.25, -1.0, 1.0, LINK_E + 1.3, 0.6, c["stone"]))
        for e in (-1, 1):
            S.add(Ellipsoid(fa.at(xm + e * 1.05, v0 - 0.15, LINK_E + 0.45), 0.3, 0.3, 0.4, c["stone"]))


def pavilion(S, fp, hu, hv, outer, c):
    """a corner pavilion, centred on frame fp: two storeys to PAV_E, windows on its street faces (outer: the
    (su, sv) signs of those faces), a brick frieze and a cornice, and a hipped roof of brown tiles."""
    walls = [c["brick"], c["band"]]
    S.add(Box(fp, -hu, hu, -hv, hv, -3, PAV_E, c["wall"]))
    S.add(Box(fp, -hu - 0.2, hu + 0.2, -hv - 0.2, hv + 0.2, -3, 1.0, c["stone"]))
    S.add(Box(fp, -hu - 0.15, hu + 0.15, -hv - 0.15, hv + 0.15, 5.0, 5.4, c["stone"]))

    def zig(u, v, w):
        a = np.floor(u / 0.5) + np.floor(v / 0.5)
        return np.where(np.mod(a + np.floor(w / 0.5), 2) == 0, c["band"], c["brick"]).astype(np.uint16)
    S.add(Box(fp, -hu - 0.05, hu + 0.05, -hv - 0.05, hv + 0.05, 5.4, 6.4, zig, mode="paint", targets=walls))
    S.add(Box(fp, -hu - 0.1, hu + 0.1, -hv - 0.1, hv + 0.1, PAV_E - 1.2, PAV_E - 0.6, c["band2"], mode="paint",
              targets=walls))
    S.add(Box(fp, -hu - 0.6, hu + 0.6, -hv - 0.6, hv + 0.6, PAV_E - 0.6, PAV_E, c["stone"]))
    for a in (-1, 1):  # quoins on the corners
        for b in (-1, 1):
            S.add(Box(fp, *sorted((a * (hu - 0.5), a * (hu + 0.05))), *sorted((b * (hv - 0.5), b * (hv + 0.05))),
                      1.0, PAV_E - 1.2, lambda u, v, w: np.where(np.mod(w, 1.0) < 0.5, c["quoin"], 0).astype(np.uint16),
                      mode="paint", targets=walls))
    for k, face in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
        if face not in outer:
            continue
        fk = fp.at(turn=k * math.pi / 2)
        r, half = (hu, hv) if k % 2 == 0 else (hv, hu)
        n = max(int((2 * half - 2.0) // 2.9), 1)
        for i in range(n):
            x = -half + 2 * half * (i + 0.5) / n
            fw = fk.at(r, x, 0, -math.pi / 2)  # u along the face, v out of it
            S.add(Box(fw, -0.9, 0.9, -0.6, 0.05, 1.0, 4.9, c["stone"], mode="paint", targets=walls))
            S.add(Box(fw, -0.75, 0.75, -0.6, 0.05, 1.0, 4.4, c["win2"], mode="paint", targets=[c["stone"]]))
            S.add(Box(fw, -0.75, 0.75, -0.6, 0.05, 6.6, 9.0, c["stone"], mode="paint", targets=walls))
            S.add(Box(fw, -0.5, 0.5, -0.6, 0.05, 6.8, 8.8, c["win"], mode="paint", targets=[c["stone"]]))
    S.add(Roof(fp, -hu - 0.6, hu + 0.6, -hv - 0.6, hv + 0.6, PAV_E, PAV_R, c["tiles"], hip=True))
    for x, y in ((-0.45, 0.3), (0.4, -0.35)):
        S.add(Box(fp, x * hu - 0.4, x * hu + 0.4, y * hv - 0.5, y * hv + 0.5, PAV_E, PAV_E + PAV_R * 0.8, c["brick"]))


def rakoczi_hall(S, ctx, plan):
    P, area = ctx["P"], ctx["area"]
    g = largest(area[HALL][3])
    b0 = base_under(ctx, g, 0.4)
    ce = g.centroid
    to = named_near(ctx, "Rákóczi tér", ce, 150.0)
    toward = (to[0] - ce.x, to[1] - ce.y) if to else (-math.cos(ctx["theta"]), -math.sin(ctx["theta"]))
    fr = front_frame(g, b0, toward)
    eu, ev = uv_of(fr, g)
    U0, U1, V0, V1 = float(eu.min()), float(eu.max()), float(ev.min()), float(ev.max())
    vr, vf = spans(fr, g, u=0.0)[0][0], spans(fr, g, u=0.0)[-1][1]   # the ends of the arms, from the outline
    un, us = spans(fr, g, v=0.0)[0][0], spans(fr, g, v=0.0)[-1][1]
    # the pavilions: where the outline steps out at the corners
    pu = next((b for a, b in spans(fr, g, v=V0 + 0.5) if a < 0 and b < -AH), None)
    pu = -pu if pu is not None else 20.0
    side = {}
    for su, uu in ((-1, U0 + 0.5), (1, U1 - 0.5)):
        st = spans(fr, g, u=uu)
        lo = next((b for a, b in st if b < -AH), -20.0)
        hi = next((a for a, b in st if a > AH), 20.0)
        side[su] = (lo, hi)

    c = dict(brick=P("#dac8a2"), band=P("#bb7f68"), band2=P("#8e4a3c"), stone=P("#e8e3d8"), stone2=P("#d2ccbf"),
             stone3=P("#bdb5a6"), quoin=P("#ece8de"), sculpt=P("#d5d1c6"), win=P("#2e3a44", WINDOW),
             win2=P("#33404a", WINDOW), glass=P("#3a4b5c", WINDOW), glass2=P("#46596c", WINDOW),
             iron=P("#46698c", METAL), iron2=P("#2f4a66", METAL), iron3=P("#7f9cb8", METAL), dark=P("#24272b"),
             dial=P("#f2f0ea"), lamp=P("#ffe6a6", LAMP), roof=P("#8a9b97", ROOF), roof2=P("#7c8d89", ROOF),
             tiles=P("#9a846c", ROOF), glass_roof=P("#a9bcc6", GLASS))
    c["wall"] = bands(c["brick"], c["band"])

    # the naves, the aisles and their roofs: vents along the ridges, clerestories over the aisles
    def roof_col(u, v, w):
        return np.where(np.mod(np.floor(u / 0.5), 6) == 0, c["roof2"], c["roof"]).astype(np.uint16)
    fv = fr.at(turn=math.pi / 2)   # u along the front-rear arm
    for f_, a0, a1 in ((fr, un, us), (fv, vr, vf)):
        S.add(Box(f_, a0, a1, -AH, AH, -3, AISLE_E, bands(c["brick"], c["band"], c["roof"], AISLE_E)))
        S.add(Box(f_, a0, a1, -NH, NH, -3, NAVE_E, bands(c["brick"], c["band"], c["roof"], NAVE_E)))
        h_a = (AISLE_R - AISLE_E) / (1 - NH / AH)
        S.add(Roof(f_, a0 + 1.0, a1 - 1.0, -AH, AH, AISLE_E, h_a, c["roof"]))
        S.add(Roof(f_, a0, a1, -NH - 0.4, NH + 0.4, NAVE_E, NAVE_R - NAVE_E, roof_col))
        for b0_, b1_ in ((a0 + 6.0, -AH - 1.0), (AH + 1.0, a1 - 6.0)):
            S.add(Box(f_, b0_, b1_, -0.75, 0.75, NAVE_R - 0.5, NAVE_R + 0.5, c["roof2"]))

        def clere(u, v, w):
            return np.where(np.mod(u, 2.0) < 1.5, c["glass"], c["iron"]).astype(np.uint16)
        for s in (-1, 1):
            for b0_, b1_ in ((a0 + 1.5, -AH), (AH, a1 - 1.5)):
                S.add(Box(f_, b0_, b1_, *sorted((s * (NH - 0.5), s * (NH + 0.05))), AISLE_R + 0.3, NAVE_E - 0.4,
                          clere, mode="paint", targets=[c["brick"], c["band"]]))
            for b0_, b1_ in ((a0 + 2.0, -AH - 1.0), (AH + 1.0, a1 - 2.0)):  # over the links' roofs
                S.add(Box(f_, b0_, b1_, *sorted((s * (AH - 0.5), s * (AH + 0.05))), LINK_E + 1.1, AISLE_E - 0.4,
                          clere, mode="paint", targets=[c["brick"], c["band"]]))

    # the links between the arms and the pavilions, with lean-to roofs glazed against the aisle walls
    def lean(end):
        def hi(u):
            t = np.clip((np.abs(u) - AH) / max(abs(end) - AH, 1.0), 0, 1)
            return LINK_E + 1.0 * (1 - t)
        return hi

    def link_roof(u, v, w):
        return np.where((np.abs(u) < AH + 1.6) & (w > LINK_E), c["glass_roof"], c["roof"]).astype(np.uint16)
    for s in (-1, 1):
        u0, u1 = sorted((s * AH, s * pu))
        for v0_, v1_ in ((AH, vf - 0.3), (vr, -AH)):
            S.add(Box(fr, u0, u1, v0_, v1_, -3, LINK_E, c["wall"]))
            S.add(UProfile(fr, u0, u1, v0_, v1_, lambda u: np.full_like(u, LINK_E - 0.5), lean(pu), link_roof))
        for su in (-1, 1):  # along the side arms: between the aisle and the front (s > 0) or rear (s < 0) pavilion
            edge = side[su][1] if s > 0 else side[su][0]
            v0_, v1_ = sorted((s * AH, edge))
            a0, a1 = (un, -pu) if su < 0 else (pu, us)
            S.add(Box(fr, a0, a1, v0_, v1_, -3, LINK_E, c["wall"]))
            S.add(UProfile(fv, v0_, v1_, *sorted((-a0, -a1)), lambda u: np.full_like(u, LINK_E - 0.5),
                           lean(edge), link_roof))

    # the four pavilions
    for su in (-1, 1):
        for sv in (-1, 1):
            ua, ub = sorted((su * pu, U0 if su < 0 else U1))
            va, vb = sorted((side[su][1] if sv > 0 else side[su][0], V1 if sv > 0 else V0))
            fp = fr.at((ua + ub) / 2, (va + vb) / 2)
            pavilion(S, fp, (ub - ua) / 2, (vb - va) / 2, {(su, 0), (0, sv)}, c)

    # the facades: the main front on Rákóczi tér, the side and rear gables
    fronts = ((fr.at(0, vf), True, (pu, pu), 0.3), (fr.at(0, vr, 0, math.pi), False, (pu, pu), 0.0),
              (fr.at(un, 0, 0, math.pi / 2), False, (-side[-1][0], side[-1][1]), 0.0),
              (fr.at(us, 0, 0, -math.pi / 2), False, (side[1][1], -side[1][0]), 0.0))
    for fa, main, (e_neg, e_pos), sb in fronts:
        gz = ctx["ground_m"](*fa.xy(0, 3.0)) - b0
        gable(S, fa, c, gz, main)
        for s, e in ((-1, e_neg), (1, e_pos)):
            wing(S, fa, s, c, main)
            link(S, fa, s * AH, s * e, c, canopy=not main, set_back=sb)


BUILDERS = [("Rákóczi Market Hall", rakoczi_hall)]
