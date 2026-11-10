"""SideQuest Bar inside and out (Klauzál utca 26-28, the ground floor beside the gateway): the shopfront with its
black-framed windows, the door under the stepped hood and the beer-mug sign; inside, the long room with its dark plank
floor, black ceiling and beams, Edison bulbs and red pendants, the white pillars (one painted diagonally), the bar
counter and the lit back bar, the planked wall with two screens, the bare brick and the darts, the big blue screen, the
TapQuest cabinet, the steel stair to the mezzanine with the foosball table, and the corridor to the toilets.

Laid out from the owner's photos and the framed evacuation plan (Fireeng, 2018), fitted to OSM: the building's corner
on the street, the door and the gateway's entrance node, the courtyard behind (docs/landmarks.md has the plan). The
frame: u along the street from the building's corner towards the gateway, v into the building from the facade, w up
from the bar's floor. Openings and the stair sit on whole metres so they survive the 1 m Minecraft blocks.
"""
import math

import numpy as np
import shapely

import landmarks
import sidequest
from landmarks import Box, Frame
from style import CLASSIC, LAMP, METAL, SOLID

SIGN = 16       # web/src/meta.ts MAT.SIGN: glows at night (screens, lit signs, coloured glass)
WINDOW = landmarks.WINDOW

NAMES = ["SideQuest Bar"]
INSIDE = {}     # filled by the build: the inside view and the room's light, for voxelize.py's meta.json


class Within(Box):
    """a box limited to a polygon: the building's outline, or that shrunk to keep a wall to the outside"""

    def __init__(self, fr, u0, u1, v0, v1, w0, w1, poly, col, **kw):
        super().__init__(fr, u0, u1, v0, v1, w0, w1, col, **kw)
        self.poly = poly
        shapely.prepare(poly)

    def inside(self, u, v, w, x, y):
        X, Y = np.broadcast_arrays(x, y)
        return super().inside(u, v, w, x, y) & shapely.contains_xy(self.poly, X, Y)[None]


def hval(*a):
    """0..1 per integer cell"""
    h = np.int64(0)
    for k, x in zip((73856093, 19349663, 83492791), a):
        h = h ^ (np.asarray(x, np.int64) * k)
    h = h ^ (h >> 13)
    return (h & 0xFFFF) / 65535.0


def cell(a):
    return np.floor(np.asarray(a) * landmarks.F + 1e-6).astype(np.int64)


def pick(ids, *key):
    ids = np.asarray(ids, np.uint16)
    return ids[(hval(*key) * len(ids)).astype(np.int64) % len(ids)]


def layout(osm):
    """the frame on the bar's front and what OSM says about it, or None"""
    f = sidequest.find(osm)
    if f is None:
        return None
    tags, p = f
    bld = sidequest.building_of(osm, p)
    if bld is None:
        return None
    oid = next(a[0] for a in osm.areas if a[3] is bld)
    door, heading = sidequest.door(osm, tags, p)
    ang = heading - math.pi / 2  # +v faces the way the door's visitor looks: into the building
    snap = round(ang / (math.pi / 2)) * (math.pi / 2)
    if abs(ang - snap) < math.radians(3):  # Pest's grid: the street lies on voxel faces
        ang = snap
    fr = Frame(0, 0, 0, ang)
    ring = np.array(getattr(bld, "geoms", [bld])[0].exterior.coords)
    uv = np.array([fr.uv(x, y) for x, y in ring])
    du, dv = fr.uv(*door)
    # the front edge: the outline's edge nearest the door, its corner on the side away from the gateway
    k = min(range(len(uv) - 1), key=lambda i: shapely.LineString(uv[i:i + 2]).distance(shapely.Point(du, dv)))
    a, b = uv[k], uv[k + 1]
    num = tags.get("addr:housenumber")
    gate = next((q for oid_, t, q in osm.nodes if t.get("entrance") and t.get("addr:housenumber") == num
                 and bld.buffer(1.5).contains(q)), None)
    gu = fr.uv(gate.x, gate.y)[0] if gate is not None else None
    lo, hi = (a, b) if a[0] < b[0] else (b, a)
    corner = lo if gu is None or gu > lo[0] else hi
    if gu is not None and gu < corner[0]:
        return None  # the gateway on the other side: this layout would be mirrored
    u0 = math.ceil(corner[0] - 0.2)
    face = math.floor(min(a[1], b[1]) * landmarks.F) / landmarks.F
    ox, oy = fr.xy(u0, face)
    return dict(fr=Frame(ox, oy, 0, ang), bld=bld, oid=oid, door=door, gate=None if gu is None else gu - u0)


def sidequest_bar(S, ctx, plan):
    P, note = ctx["P"], ctx["note"]
    L = layout(ctx["osm"])
    if L is None:
        note("    SideQuest Bar: not found in OSM (or an unexpected layout), left out")
        return
    g = ctx["ground_m"](*L["door"])
    floor = float(math.ceil(g - 0.01))  # a whole metre: the Minecraft blocks keep the stair and the doorways
    fr = Frame(L["fr"].ox, L["fr"].oy, floor, L["fr"].ang)
    bld = L["bld"]
    inner = bld.buffer(-0.45)  # at least a voxel of wall to the street, the courtyard and the neighbours
    gate = round(L["gate"] * 2) / 2 if L["gate"] is not None else 13.0

    def add(u0, u1, v0, v1, w0, w1, col, **kw):
        S.add(Box(fr, u0, u1, v0, v1, w0, w1, col, **kw))

    def S_(c):
        return P(c, SOLID)

    def table(u0, v0, top=None, size=1.0, h=1.0):
        add(u0, u0 + 0.5, v0, v0 + 0.5, 0, h - 0.5, S_("#232323"))
        add(u0, u0 + size, v0, v0 + size, h - 0.5, h, top or S_("#9a6a3e"))

    f = ctx["feats"].get(str(L["oid"]))
    wall_rgb = ctx["pal"].entries[f["wall"]][:3] if f is not None else (227, 207, 155)
    cream = P("#%02x%02x%02x" % tuple(wall_rgb), CLASSIC)
    cream2 = P("#%02x%02x%02x" % tuple(min(255, c + 14) for c in wall_rgb), CLASSIC)
    frame_ = S_("#202022")
    white, white2 = S_("#ebe8e1"), S_("#e2dfd7")
    stone = [S_("#e6e3db"), S_("#dcd8cf"), S_("#e1ddd5")]
    grey = S_("#8d9295")
    planks = [S_("#4c3b2f"), S_("#56432f"), S_("#5f4b39"), S_("#463529")]
    ceiling = S_("#1d1d20")
    wood = S_("#c48a52")
    feature = [S_("#b9824c"), S_("#c99057"), S_("#a87442"), S_("#bd8a50")]
    brick = [S_("#d3b07c"), S_("#c8a16a"), S_("#dcbd8d"), S_("#c09862"), S_("#d6b585")]
    leather, leather2 = S_("#46301f"), S_("#3a281c")
    velvet = S_("#66605b")
    lamp = P("#ffd27a", LAMP)
    glass = P("#45525a", WINDOW)
    red_glass, orange_glass = P("#d3262c", SIGN), P("#f07a1a", SIGN)

    # ---- the unit's volume, made the bar's own: walls white, the floor dark planks, the ceiling black
    def structure(u, v, w):
        iu, iv, iw = cell(u), cell(v), cell(w)
        pl = pick(planks, iv, (iu + 3 * iv) // 5)
        # the painted stone blocks under the mezzanine, behind the stair and along the corridor
        blocks = (u >= 4.5) & (((u >= 6.5) & (v >= 5.0)) | (v >= 8.5)) & (w < 3.0)
        st = pick(stone, iw, (iu + iv + (iw % 2)) // 2)
        out = np.where(w < 0, pl, np.where(w >= 5.5, ceiling, np.where(blocks, st, white)))
        return out.astype(np.uint16)
    S.add(Within(fr, 0, 11.5, 1.0, 11.0, -0.5, 6.0, bld, structure))
    S.add(Within(fr, 0, 4.5, 11.0, 12.5, -0.5, 6.0, bld, structure))

    # ---- the street front: a rusticated base in the building's colour (CLASSIC: no shop windows painted on it)
    end = gate + 1.5
    add(0, end, 0, 1.0, -1.0, 5.0, cream)
    add(0, 11.5, 0.5, 1.0, -0.5, 5.0, white)  # its inner face
    add(0, 11.5, 0.5, 1.0, 5.0, 6.0, cream)   # above the base the facade steps back here and there: no white band
    for u0, u1, mull in ((1.0, 3.5, 2.0), (8.0, 10.5, 9.0)):  # window B (the sofa), window A (the bar)
        add(u0, u1, 0, 0.5, 0.5, 4.0, 0, mode="carve")
        add(u0, u1, 0.5, 1.0, -0.5, 0.5, S_("#33302e"))
        add(u0, u1, 0.5, 1.0, 0.5, 4.0, glass)
        add(u0, u1, 0.5, 1.0, 2.5, 3.0, frame_)
        add(mull, mull + 0.5, 0.5, 1.0, 0.5, 4.0, frame_)
    # the door unit: a side light and the door, the leaded lattice of the transom over both
    add(4.5, 7.0, 0, 0.5, 0, 3.5, 0, mode="carve")
    add(4.5, 6.0, 0.5, 1.0, 0, 0.5, frame_)
    add(4.5, 6.0, 0.5, 1.0, 0.5, 2.5, glass)

    def lattice(u, v, w):
        iu, iw = cell(u), cell(w)
        return np.where((iu + iw) % 2 == 0, glass, S_("#2a2724")).astype(np.uint16)
    add(4.5, 7.0, 0.5, 1.0, 2.5, 3.5, lattice)
    add(6.0, 7.0, 0, 1.0, 0, 2.5, 0, mode="carve")
    add(6.0, 7.0, -0.5, 1.0, -0.5, 0, S_("#b9b4aa"))  # the threshold
    # the stepped hood over the door (the corbel of the oriel above), the plaque, the sign on its pier
    add(5.5, 7.0, -0.5, 0, 3.5, 4.0, cream2)
    add(5.0, 7.5, -1.0, 0, 4.0, 4.5, cream2)
    add(4.5, 8.0, -1.5, 0, 4.5, 5.5, cream2)
    add(7.0, 7.5, 0, 0.5, 2.5, 3.5, S_("#57524b"))

    def sign(u, v, w):
        iv, iw = cell(-v), cell(w - 3.0)
        c = np.where(iw >= 1, P("#f4f3ee", SIGN), np.where(iv % 2 == 1, P("#f0bf2c", SIGN), P("#3d7bd8", SIGN)))
        return c.astype(np.uint16)
    add(3.5, 4.0, -1.0, 0, 3.0, 4.0, sign)
    # the gateway of 26-28: dark doors with octagonal lights, lit from the hallway behind, under a glazed transom
    g0, g1 = gate - 1.5, gate + 1.5
    add(g0, g1, 0, 0.5, 0, 4.0, 0, mode="carve")

    def gateway(u, v, w):
        iu = cell(u - g0)
        lit = (iu % 3 == 1) & (w >= 1.0) & (w < 2.5)
        c = np.where(w >= 3.0, P("#fbe7b8", SIGN), np.where(lit, P("#efbd4c", SIGN), S_("#2b2420")))
        return c.astype(np.uint16)
    add(g0, g1, 0.5, 1.0, 0, 4.0, gateway)

    # ---- the rooms (carved; never closer than a voxel to the outside). Where people walk the carves are on whole
    # metres, so that Minecraft's 1 m blocks keep the way open (a half-metre wall there takes its whole block)
    def carve(u0, u1, v0, v1, w0, w1):
        S.add(Within(fr, u0, u1, v0, v1, w0, w1, inner, 0, mode="carve"))
    carve(0.5, 4.0, 1.0, 12.0, 0, 5.5)     # the long room, with the darts at its far end
    carve(4.0, 7.0, 1.0, 10.0, 0, 5.5)     # the stair, the way past it and the landing over the corridor's mouth
    carve(4.5, 6.0, 10.0, 10.5, 0, 3.0)    # the sideboard's recess
    carve(7.0, 11.0, 1.0, 5.0, 0, 5.5)     # the bar
    carve(7.0, 11.0, 5.5, 10.5, 3.0, 5.5)  # the mezzanine
    carve(8.0, 10.0, 5.0, 5.5, 4.0, 5.0)   # its window onto the bar
    carve(6.0, 9.0, 9.0, 10.0, 0, 2.5)     # the corridor under it
    carve(9.0, 9.5, 9.0, 10.0, 0, 2.5)     # the toilet's doorway
    carve(9.5, 11.0, 7.0, 10.5, 0, 2.5)    # the toilet

    # ---- the pillar line (v 5-6, the plan's 5.3-6.1), with cornice capitals: the pier on the end wall, the free
    # pillar painted diagonally grey and white, the corner of the toilet block under the mezzanine (the chalkboard)
    def diagonal(u, v, w):
        return np.where(w > 1.2 + 0.9 * (u - 3.5) + 0.7 * (v - 5.0), grey, white).astype(np.uint16)
    add(0.5, 1.0, 5.0, 6.0, 0, 5.5, white)
    add(3.5, 4.5, 5.0, 6.0, 0, 5.5, diagonal)
    add(7.0, 8.0, 5.0, 6.0, 0, 5.5, white)
    for c0, c1, d0, d1 in ((0.5, 1.5, 4.5, 6.5), (3.0, 5.0, 4.5, 6.5), (6.5, 8.0, 4.5, 6.0), (1.5, 3.0, 11.0, 12.0)):
        add(c0, c1, d0, d1, 5.0, 5.5, white2)
    add(7.0, 8.0, 5.0, 5.5, 1.0, 2.5, S_("#2a2d2b"), mode="paint", targets=[white])  # the chalkboard
    add(2.0, 2.5, 11.5, 12.0, 0, 5.5, white)  # the pilaster between the brick panels
    # black beams under the black ceiling
    for v0, v1, u1 in ((3.0, 3.5, 11.0), (9.0, 9.5, 5.5)):
        add(0.5, u1, v0, v1, 5.0, 5.5, S_("#151517"))

    # ---- walls: bare cream brick at the far end and behind the mezzanine's sofa, the planked feature wall
    def brickwork(u, v, w):
        iu, iv, iw = cell(u), cell(v), cell(w)
        return pick(brick, iw, (iu + iv + iw % 2) // 2 * 7 + iw)
    add(0.5, 2.0, 12.0, 12.5, 0, 5.5, brickwork)
    add(2.5, 4.0, 12.0, 12.5, 0, 5.5, brickwork)
    add(11.0, 11.5, 5.5, 10.5, 3.0, 5.5, brickwork)

    def planked(u, v, w):
        iv, iw = cell(v), cell(w)
        batten = iv % 4 == 0
        return np.where(batten, S_("#1e1e20"), pick(feature, iw, iv // 3)).astype(np.uint16)
    add(0, 0.5, 6.0, 11.0, 0.5, 4.5, planked)
    for v0 in (7.0, 9.0):  # its two screens (racing games)
        add(0, 0.5, v0, v0 + 1.5, 1.5, 2.5, P("#4f8fd6", SIGN))

    # the projection screen at the end of the room, the SideQuest logo on blue, a speaker either side
    def screen(u, v, w):
        iv, iw = cell(v - 1.5), cell(w - 2.0)
        logo = (iw == 1) & (iv >= 1) & (iv <= 4)
        c = np.where(logo, np.where(iv == 4, P("#f08a24", SIGN), P("#f2dc86", SIGN)), P("#3f6fe0", SIGN))
        return c.astype(np.uint16)
    add(0, 0.5, 1.5, 4.5, 2.0, 3.5, screen)
    for v0 in (1.0, 4.5):
        add(0.5, 1.0, v0, v0 + 0.5, 2.5, 3.5, S_("#141416"))
    # posters: Red Dead on the diagonal pillar, the pin-up over the arcade, the bar's floor plan by the door; the
    # green exit sign over the door
    add(3.5, 4.5, 5.5, 6.0, 1.5, 2.5, S_("#a8261f"), mode="paint", targets=[white, grey])
    add(0.5, 1.0, 5.0, 6.0, 2.5, 3.5, S_("#c0392b"), mode="paint", targets=[white])
    add(7.0, 8.0, 0.5, 1.0, 2.0, 2.5, S_("#2b2b2b"), mode="paint", targets=[white])
    add(6.0, 7.0, 1.0, 1.5, 3.0, 3.5, P("#22a05a", SIGN))

    # ---- the bar: a light wood counter with an orange top, stools, taps; the back bar's lit shelves and screens.
    # The counter runs from window A; the way behind it is at the mezzanine's end
    add(8.5, 9.0, 1.0, 4.0, 0, 0.5, wood)
    add(8.5, 9.0, 1.0, 4.0, 0.5, 1.0, S_("#d8692c"))
    for v0 in (1.5, 2.5, 3.5):
        add(8.0, 8.5, v0, v0 + 0.5, 0, 0.5, S_("#18181a"))
    add(8.5, 9.0, 2.0, 2.5, 1.0, 1.5, P("#c9ccce", METAL))
    add(8.5, 9.0, 3.0, 3.5, 1.0, 1.5, P("#3fbf62", SIGN))
    add(10.0, 11.0, 1.5, 5.0, 0, 1.0, S_("#2c2723"))
    add(10.5, 11.0, 1.5, 5.0, 1.0, 1.5, P("#fff0d2", LAMP))
    bottles = [S_("#8a4f1d"), S_("#3f6b3a"), S_("#c9d6d8"), S_("#7a2430"), S_("#d9b44a"), S_("#a35d22"), S_("#e4e4dc")]

    def backbar(u, v, w):
        iv, iw = cell(v), cell(w)
        tv = (w >= 2.5) & (w < 3.5) & (((v >= 1.5) & (v < 3.0)) | ((v >= 3.5) & (v < 5.0)))
        boxes = pick([S_("#26303c"), S_("#3b4b63"), S_("#5a3e2c"), S_("#2d4a3a")], iv, iw)
        c = np.where(tv, P("#5b8fe0", SIGN), np.where(w >= 3.5, boxes, pick(bottles, iv, iw, 5)))
        return c.astype(np.uint16)
    add(10.5, 11.0, 1.5, 5.0, 1.5, 4.0, backbar)
    # the Szentkirályi fridge by window A, its glass door aglow
    add(7.0, 8.0, 1.0, 1.5, 0, 0.5, S_("#2f5ea8"))
    add(7.0, 8.0, 1.0, 1.5, 0.5, 2.0, P("#a9d8f0", SIGN))

    # ---- the stair, straight in from the door as on the plan: oak treads on a black steel stringer, one voxel up
    # each step from the pillar line to a landing at 3 m over the corridor's mouth
    tread = S_("#c99a5e")
    for k in range(5):
        v0 = 5.0 + 0.5 * k
        add(6.0, 7.0, v0, v0 + 0.5, 0.5 * k, 0.5 * k + 0.5, tread)
        add(5.5, 6.0, v0, v0 + 0.5, 0.5 * k, 0.5 * k + 0.5, frame_)
        add(5.5, 6.0, v0, v0 + 0.5, 0.5 * k + 1.0, 0.5 * k + 1.5, frame_)
        if k % 2 == 0:
            add(5.5, 6.0, v0, v0 + 0.5, 0.5 * k + 0.5, 0.5 * k + 1.0, frame_)

    def mezz(u, v, w):
        return pick(planks, cell(v), (cell(u) + 3 * cell(v)) // 5).astype(np.uint16)
    add(6.0, 7.0, 7.5, 10.0, 2.5, 3.0, mezz)
    add(7.0, 11.0, 5.5, 10.5, 2.5, 3.0, mezz)
    add(7.0, 8.0, 5.5, 6.0, 2.5, 3.0, white)  # the pillar through the mezzanine's floor
    for u0, u1, v0, v1 in ((5.5, 6.0, 7.5, 10.0), (7.0, 7.5, 6.0, 7.5)):  # railings: a top rail at 1 m, posts
        add(u0, u1, v0, v1, 3.5, 4.0, frame_)
        for vp in np.arange(v0, v1, 1.0):
            add(u0, u1, vp, vp + 0.5, 3.0, 3.5, frame_)
    add(6.0, 7.0, 8.5, 9.0, 0, 2.5, S_("#7a716b"))  # under the landing: the corridor's taupe wall

    # ---- the mezzanine: foosball (its field lit), a leather sofa against the brick, floor lamps, a high table
    # (a metre kept clear inside the railing and along the window, from the landing to the window; furniture on whole
    # metres, so that Minecraft's blocks keep it whole)
    add(9.0, 10.0, 7.0, 8.5, 3.0, 3.5, S_("#2a1d14"))
    add(9.0, 10.0, 7.0, 8.5, 3.5, 4.0, S_("#5b3a22"))
    add(9.0, 10.0, 7.5, 8.0, 3.5, 4.0, P("#d6efe6", SIGN))
    add(10.5, 11.0, 8.0, 10.0, 3.0, 4.0, leather)
    add(10.0, 10.5, 8.0, 10.0, 3.0, 3.5, leather2)
    add(10.5, 11.0, 7.5, 8.0, 3.0, 4.5, S_("#1a1a1a"))
    add(10.5, 11.0, 7.5, 8.0, 4.5, 5.0, lamp)
    add(10.5, 11.0, 10.0, 10.5, 3.0, 4.5, S_("#1a1a1a"))
    add(10.5, 11.0, 10.0, 10.5, 4.5, 5.0, orange_glass)
    add(8.0, 9.0, 10.0, 10.5, 3.0, 4.0, S_("#2e2a27"))  # a high table at the back wall

    # ---- the corridor to the toilets: the staff room's oak door on the left, a light on the wall; the tiled toilet
    add(7.0, 8.0, 8.5, 9.0, 0, 2.0, S_("#b89a72"))
    add(7.0, 8.0, 8.5, 9.0, 2.0, 2.5, S_("#8c8a86"))
    add(8.0, 8.5, 10.0, 10.5, 1.5, 2.0, lamp)
    add(9.0, 9.5, 8.5, 9.0, 0, 2.5, S_("#8c8a86"), mode="paint", targets=stone + [white])
    add(9.0, 9.5, 10.0, 10.5, 0, 2.5, S_("#8c8a86"), mode="paint", targets=stone + [white])

    def tiles_(u, v, w):
        iu, iv = cell(u), cell(v)
        return np.where(w < 0, np.where((iu + iv) % 2 == 0, S_("#a9a8a4"), S_("#b6b5b0")),
                        np.where(w < 1.5, S_("#f1f3f1"), white)).astype(np.uint16)
    S.add(Within(fr, 9.0, 11.5, 6.5, 11.0, -0.5, 2.5, inner.buffer(0.5), tiles_, mode="paint",
                 targets=stone + [white] + planks))
    add(10.5, 11.0, 7.0, 7.5, 0, 0.5, S_("#fbfbfb"))
    add(10.5, 11.0, 8.5, 9.0, 0.5, 1.0, S_("#fbfbfb"))
    add(11.0, 11.5, 9.5, 10.0, 1.5, 2.0, lamp)

    # ---- the darts at the far end: the board under its light, the oche mat; the op-art sideboard under the map,
    # the glass display cabinet, an orange dome lamp over a round table, a leather bench, a closed door
    add(3.0, 3.5, 12.0, 12.5, 1.5, 2.0, S_("#1b1b1b"))
    add(3.0, 3.5, 11.5, 12.0, 2.5, 3.0, lamp)
    add(3.0, 3.5, 9.5, 12.0, -0.5, 0, S_("#26262b"))

    def maze(u, v, w):  # the drawers on the landing's side, the black and white maze on the door
        iu, iw = cell(u), cell(w)
        c = np.where(u >= 5.5, S_("#2f4a4f"), np.where((iu + iw) % 2 == 0, S_("#151515"), S_("#ecebe6")))
        return c.astype(np.uint16)
    add(4.5, 6.0, 10.0, 10.5, 0, 1.0, maze)

    def map_(u, v, w):
        iu, iw = cell(u), cell(w)
        rim = (iw == cell(np.asarray(1.5))) | (iu == cell(np.asarray(4.5))) | (iu == cell(np.asarray(5.5)))
        return np.where(rim, S_("#8e2b22"), S_("#d6c48f")).astype(np.uint16)
    add(4.5, 6.0, 10.5, 11.0, 1.5, 2.5, map_)
    add(6.0, 6.5, 10.0, 10.5, 2.0, 2.5, P("#22a05a", SIGN))  # the exit sign by the corridor

    def cabinet(u, v, w):
        iw = cell(w)
        return np.where((iw % 2 == 0), P("#c8cacc", METAL), P("#b9cdd6", WINDOW)).astype(np.uint16)
    add(0.5, 1.0, 11.0, 12.0, 0, 2.5, cabinet)
    add(0.5, 1.0, 9.0, 11.0, 0, 1.0, leather2)
    table(1.0, 10.0, S_("#5a3a24"))
    add(4.0, 4.5, 10.5, 11.5, 0, 2.0, S_("#d9d6cf"))
    add(4.0, 4.5, 10.5, 11.5, 2.0, 2.5, S_("#9a9893"))

    # ---- seating: the Chesterfield against window B, armchairs and tables, the arcade, coat stands
    add(1.0, 3.5, 1.0, 2.0, 0, 0.5, leather)
    add(1.0, 3.5, 1.0, 1.5, 0.5, 1.0, leather2)
    add(1.0, 1.5, 1.5, 2.0, 0.5, 1.0, leather2)
    add(3.0, 3.5, 1.5, 2.0, 0.5, 1.0, leather2)

    # (chairs and stools are posts in Minecraft: none on the ways to the stair, past it and behind the counter)
    table(1.5, 2.5, S_("#5a3a24"), h=0.5)
    table(4.0, 3.0)
    table(1.0, 4.0)
    table(7.0, 3.0)  # the one by the fridge
    for u0, v0 in ((3.5, 3.0), (5.0, 3.5), (7.5, 2.5)):
        add(u0, u0 + 0.5, v0, v0 + 0.5, 0, 0.5, S_("#2c2622"))
    for u0, v0 in ((1.0, 7.0), (2.0, 8.0)):  # grey velvet armchairs facing the screens
        add(u0, u0 + 1.0, v0, v0 + 1.0, 0, 0.5, velvet)
        add(u0 + 0.5, u0 + 1.0, v0, v0 + 1.0, 0.5, 1.0, velvet)
    # TapQuest, the bar's own arcade cabinet in light wood, against the pier: screen and marquee towards the windows
    add(1.0, 1.5, 5.0, 6.0, 0, 2.5, S_("#d9b98a"))
    add(1.0, 1.5, 5.0, 5.5, 1.0, 1.5, P("#3c7ad8", SIGN))
    add(1.0, 1.5, 5.0, 5.5, 2.0, 2.5, P("#f4d36b", SIGN))
    for u0, v0 in ((3.5, 1.0), (0.5, 6.0)):
        add(u0, u0 + 0.5, v0, v0 + 0.5, 0, 2.0, S_("#f2f2ee"))

    # ---- light: dozens of Edison bulbs, red glass pendants by the windows and the screen, orange ones at the far
    # end; none by the pillars, over the stair, the landing or the mezzanine (heads). Their cords would be half-metre
    # posts: left out
    def hang(u, v, w, col):
        add(u, u + 0.5, v, v + 0.5, w, w + 0.5, col)
    n = 0
    for v0 in np.arange(1.5, 12.0, 1.0):
        for u0 in np.arange(1.0, 11.0, 1.0):
            uu, vv = float(u0 + 0.5 * (int(v0) % 2)), float(v0)
            if hval(int(uu * 2), int(vv * 2), 7) < 0.25:
                continue
            if 4.5 <= vv < 6.5 or (uu >= 5.5 and vv >= 4.5) or (uu >= 4.0 and vv >= 9.0):
                continue
            if uu < 1.0 or uu >= 10.5 or (uu < 4.0 and vv >= 12.0) or (uu >= 9.0 and vv < 3.0):
                continue
            w = 3.0 + 0.5 * int(hval(int(uu * 2), int(vv * 2)) * 4)
            hang(uu, vv, w, lamp)
            n += 1
    for u0, v0, w in ((2.0, 2.5, 3.0), (5.0, 1.5, 3.5), (1.5, 3.5, 3.0), (3.0, 4.5, 3.5), (7.5, 1.5, 3.5)):
        hang(u0, v0, w, red_glass)
    hang(1.0, 9.5, 3.0, orange_glass)
    hang(2.0, 10.0, 3.5, orange_glass)

    # for meta.json: the inside view (from behind the counter, along the room to the big screen; a little above the
    # target, which the map's orbit controls want; walk mode starts there too) and the room's light at night
    def at(u, v, w):  # a view's [column, height, row]
        x, y = fr.xy(u, v)
        return [round(x, 1), round(floor + w, 1), round(y, 1)]
    lx, ly = fr.xy(5.5, 5.0)
    INSIDE.clear()
    INSIDE.update(view=dict(label="Inside SideQuest Bar", pos=at(9.5, 2.5, 2.0), target=at(1.0, 3.0, 1.6), walk=True),
                  lamps=[[round(lx, 1), round(ly, 1), round(floor + 4.5, 1)]])
    note(f"    SideQuest Bar: floor {floor:.1f} m, front at grid ({fr.ox:.1f}, {fr.oy:.1f}), gateway {gate:.1f} m along, "
         f"{n} bulbs")


BUILDERS = [("SideQuest Bar", sidequest_bar)]
