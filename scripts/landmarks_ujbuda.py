"""Late November 2026, fourth round, Újbuda: the MOL Campus, the Kelenföld power station, Bikás Park, Kelenföld station,
Etele Plaza, the BME campus building by building, Allee and the Szent Margit Gimnázium; with two fixes, the gangways to
the A38 and the red lighting masts on Rákóczi Bridge. Outlines from OSM; heights, colours and details from the Esri
aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point

from landmarks import Box, Capsule, Ellipsoid, Frame, Lathe, Poly, cone, cyl, dome, rect_of
from landmarks_city import base_under
from landmarks_hosok import keep
from landmarks_kit import compass, largest, painted, styled
from style import CONCRETE, GLASS, GRASS, METAL, ROOF

MOL, MOL_TOWER, MOL_PODIUM = 743811204, 858059511, 858496628
KF_HALL, KF_SWITCH, KF_BOILER, KF_EAST, KF_SMALL, KF_SMALL2, KF_INTAKE = 459864181, 459864182, 459864188, 459864180, 459864179, 459864187, 203252193
KF_TANKS = (459864183, 459864189, 459864190)
KF_CHIMNEY = 510463639
BIKAS_PARK, BIKAS_STATION, BIKAS_EXIT, BIKAS_POND = 1609368, 180004857, 243715839, 308379213
BIKAS_DOMES = ((370207457, 370207458, 370207455), (949789045, 949789044))
KF_STATION = 184313287
KF_PLATFORMS = (287943, 9599101, 9599102, 9599103, 11778361)
ETELE = 932642500
ALLEE = 10785083
MARGIT_SCHOOL, MARGIT_PART, MARGIT_TOWER = 53040440, 767828712, 767828713
A38_WAYS, A38_PIER = (1214495653, 675681265), 1214495652
RAKOCZI_MASTS = (911018465, 911018466, 911018467, 911018468, 911018469)

# the BME's buildings: OSM id -> (name, style, eaves m, roof colour)
BME = {
    24727027: ("R", "brick", 21.0, "#6d7375"), 24726844: ("H", "brick", 22.0, "#5e6a6d"),
    24726848: ("T", "brick", 22.0, "#5e6a6d"), 198237195: ("Hö", "brick", 11.0, "#9a4a36"),
    42815845: ("MM", "brick", 13.0, "#a5523a"), 155220671: ("MG", "brick", 13.0, "#a5523a"),
    25363736: ("F", "ochre", 18.0, "#6c6f70"), 1528788208: ("Library", "ochre", 13.0, "#a8573c"),
    24727059: ("D", "white", 21.0, "#4c5256"), 24727074: ("Z", "white", 37.0, "#7d6a62"),
    24727017: ("St", "white", 18.0, "#3c4247"), 32800585: ("AE", "white", 8.0, "#3c4247"),
    476450390: ("J", "white", 21.0, "#5c6266"), 24726989: ("G", "white", 8.0, "#6b7074"),
    87620444: ("A", "white", 21.0, "#4f5559"), 87620447: ("V1", "white", 21.0, "#4f5559"),
    2662213: ("E", "tower", 50.0, "#6f7a7e"), 32801232: ("Kármán Tódor Kollégium", "dorm", 34.0, "#6b7074"),
    24727069: ("ÉL", "hall", 12.0, "#4a5054"), 42816345: ("L", "hall", 9.0, "#555b5f"),
    42816629: ("MT", "hall", 10.0, "#4a5054"), 32800582: ("Dcs", "vaults", 8.0, "#4a3e38"),
    82478999: ("Q", "redbrick", 22.0, "#c3c6c6"), 24726476: ("I", "redbrick", 18.0, "#9aa0a2"),
    24726877: ("TR", "dome", 8.0, "#9aa3a8"),
}

NAMES = ["MOL Campus", "Kelenföld power station", "Bikás Park", "Kelenföld station", "Etele Plaza", "BME campus",
         "Allee", "Szent Margit Gimnázium", "A38 gangways", "Rákóczi Bridge masts"]
DROP = {MOL, MOL_TOWER, MOL_PODIUM, KF_HALL, KF_SWITCH, KF_BOILER, KF_EAST, KF_SMALL, KF_SMALL2, KF_INTAKE, *KF_TANKS,
        BIKAS_STATION, BIKAS_EXIT, KF_STATION, ETELE, ALLEE, MARGIT_SCHOOL, MARGIT_PART, MARGIT_TOWER, *BME,
        *RAKOCZI_MASTS}
KEEP = [(MOL, 20), (KF_HALL, 28), (KF_SWITCH, 20), (KF_BOILER, 30), (KF_STATION, 12), (ETELE, 24), (ALLEE, 20),
        (MARGIT_SCHOOL, 25)]
SKIP_WAYS = {*A38_WAYS, A38_PIER}
TAU = 2 * math.pi


def hash2(a, b, k):
    h = (np.floor(a).astype(np.int64) * 73856093) ^ (np.floor(b).astype(np.int64) * 19349663)
    return np.mod(np.abs(h) >> 4, k)


# ------------------------------------------------------------------------------------------------ MOL Campus
def mol_campus(S, ctx, plan):
    """the MOL Campus (Foster + Partners with Finta Studio, 2022), Hungary's tallest building: a 28-storey tower of
    blue glass between white piers, closed in white on its west face, rising to an open crown at 143 m, and grown into
    a podium of five and six floors that steps down to the south-east in planted terraces."""
    P = ctx["P"]
    area = ctx["area"]
    glass, glass2, white, white2 = P("#5f86b0", GLASS), P("#7295bb", GLASS), P("#eef0ef"), P("#dfe2e2")
    roof, green, green2 = P("#a9adae", ROOF), P("#5c8a46", GRASS), P("#6f9a52", GRASS)
    west = compass(270)
    FL = 4.25
    tg = largest(area[MOL_TOWER][3]) if MOL_TOWER in area else None
    pg = largest(area[MOL_PODIUM][3]) if MOL_PODIUM in area else None
    b0 = base_under(ctx, keep(ctx, MOL), 0.3)
    if tg is not None:
        tc = np.array(tg.centroid.coords[0])
        TOP, CROWN = 120.0, 143.0

        def tower(f, hw):
            d, s, X, Y = f["d"], f["s"], f["X"], f["Y"]
            inside, edge = d > 0, (d > 0) & (d < 0.9)
            facing_w = ((X - tc[0]) * west[0] + (Y - tc[1]) * west[1]) > 13.0
            pier = np.mod(s, 9.0) < 1.2
            fl = np.mod(hw, FL)
            wall = np.where(fl < 0.55, white, np.where(np.mod(np.floor(hw / FL), 3) == 2, glass2, glass))
            wall = np.where(pier | facing_w, np.where(fl < 0.55, white2, white), wall)
            o = np.where(edge & (hw < TOP), wall, 0)
            o = np.where(inside & (hw >= TOP - 0.6) & (hw < TOP), roof, o)
            crown = edge & (hw >= TOP) & (hw < CROWN) & ((np.mod(hw, FL) < 0.6) | pier | (hw >= CROWN - 0.8))
            return np.where(crown, white, o)
        painted(S, tg, b0, CROWN + 0.5, tower)
        for k in range(4):  # the crown's masts
            p = tg.exterior.interpolate(tg.exterior.length * (k + 0.5) / 4)
            S.add(Lathe(Frame(p.x, p.y, b0), CROWN - 1, CROWN + 6, cone(0.45, 0.1), white2, n=6))
    if pg is not None:
        tdist = (lambda X, Y: np.reshape(shapely.distance(tg, shapely.points(X.ravel(), Y.ravel())), X.shape)) \
            if tg is not None else (lambda X, Y: np.zeros_like(X))

        def podium(f, hw):
            d, s, t = f["d"], f["s"], f["t"]
            inside = d > 0
            steps = np.clip(26.0 - np.floor(t / 22.0) * FL, 13.0, 26.0)  # terraces stepping down away from the tower
            edge = inside & (d < 0.9)
            fl = np.mod(hw, FL)
            wall = np.where(fl < 0.6, white, np.where(np.mod(s, 1.8) < 0.15, white2, glass))
            o = np.where(edge & (hw < steps), wall, 0)
            top = inside & (hw >= steps - 0.6) & (hw < steps)
            o = np.where(top, np.where(d < 3.0, np.where(np.mod(s, 2.0) < 1.0, green, green2), roof), o)
            # the step faces between terraces
            o = np.where(inside & ~edge & (hw < steps) & (hw >= steps - FL) & (np.mod(t, 22.0) > 21.0), wall, o)
            return o
        painted(S, pg, b0, 27.0, podium, extra={"t": tdist})


# ------------------------------------------------------------------------------------------------ Kelenföld power station
def kelenfold_power(S, ctx, plan):
    """the Kelenföld power station (Kálmán Reichl, 1914; extended by Virgil Borbíró to 1929, the Art Deco switch house
    1930): long halls of ochre brick on the Danube bank under brown roofs with glazed ridges, the boiler house in red
    brick, the round fuel tanks and the red and white striped chimney on its guy wires."""
    P = ctx["P"]
    area = ctx["area"]
    ochre, ochre2, brick, brick2 = P("#cfa35e"), P("#bf9452"), P("#9b4f3a"), P("#8a4433")
    win, roofb, roofg, sky = P("#3a4248", GLASS), P("#7a5b45", ROOF), P("#6c7072", ROOF), P("#7fa6c4", GLASS)
    tankc, tank2, red, white = P("#b9bcbc", METAL), P("#a7aaab", METAL), P("#c23b2e"), P("#efefec")
    halls = {KF_HALL: (26.0, ochre, ochre2, roofb, True), KF_SWITCH: (17.0, ochre, ochre2, roofg, False),
             KF_BOILER: (30.0, brick, brick2, roofg, False), KF_EAST: (24.0, brick, brick2, roofg, False),
             KF_SMALL: (14.0, ochre, ochre2, roofg, False), KF_SMALL2: (11.0, brick, brick2, roofg, False),
             KF_INTAKE: (10.0, brick, brick2, roofg, False)}
    for oid, (E, wc, wc2, rc, ridge) in halls.items():
        if oid not in area:
            continue
        g = largest(area[oid][3])
        b0 = base_under(ctx, g, 0.3)

        def fn(f, hw, E=E, wc=wc, wc2=wc2, rc=rc, ridge=ridge):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.9)
            pil = np.mod(s, 6.0) < 1.2
            tall = (np.abs(np.mod(s, 6.0) - 3.6) < 1.4) & (hw > 2.0) & (hw < E - 3.0)
            wall = np.where(pil | (hw > E - 1.6) | (hw < 1.0), wc2, np.where(tall, win, wc))
            o = np.where(edge & (hw < E), wall, 0)
            rh = np.minimum(d * 0.5, 7.0)
            roof_ = inside & (hw >= E - 0.6) & (hw < E + rh + 0.5)
            o = np.where(roof_, np.where(ridge & (rh >= 6.5) & (np.mod(f["s"], 12.0) < 9.0) & (d < 16.0), sky, rc), o)
            return o
        painted(S, g, b0, E + 8.0, fn)
    for oid in KF_TANKS:
        if oid not in area:
            continue
        g = area[oid][3]
        b0 = base_under(ctx, g, 0.3)
        r = math.sqrt(g.area / math.pi)
        c = g.centroid
        fr = Frame(c.x, c.y, b0)
        H = 12.0 if r > 9 else 14.0
        S.add(Lathe(fr, -0.5, H, cyl(r), lambda u, v, w: np.where(np.mod(w, 2.4) < 0.25, tank2, tankc).astype(np.uint16), n=24))
        S.add(Lathe(fr, H, H + r * 0.22, dome(r, 2.0), tank2, n=24))
    if KF_CHIMNEY in area:
        c = area[KF_CHIMNEY][3].centroid
        b0 = ctx["ground_m"](c.x, c.y)
        H = 72.0
        S.add(Lathe(Frame(c.x, c.y, b0), -0.5, H, cone(2.6, 1.5), lambda u, v, w: np.where(
            np.mod(np.floor((w - b0) / 6.0), 2) == 0, red, white).astype(np.uint16), n=16))
        for k in range(3):
            a = TAU * k / 3 + 0.4
            S.line(Frame(c.x, c.y, b0), (0, 0, H * 0.8), (math.cos(a) * 38, math.sin(a) * 38, 0.5), P("#55585b", METAL))


# ------------------------------------------------------------------------------------------------ Bikás Park
def bikas_park(S, ctx, plan):
    """Bikás Park: the M4 station's long oval shell of grey ribbed steel and glass over the escalators, its pyramid
    exit by the paths, and the two white air halls over the tennis courts at the park's north end."""
    P = ctx["P"]
    area = ctx["area"]
    shell, rib, glass, dark = P("#9ea4a8", METAL), P("#6f777c", METAL), P("#8fb1bf", GLASS), P("#3d4246", METAL)
    air, air2 = P("#f2f2ee", ROOF), P("#e3e4df", ROOF)
    if BIKAS_STATION in area:
        g = largest(area[BIKAS_STATION][3])
        b0 = base_under(ctx, g, 0.3)
        cx, cy, L, Wd, ang = rect_of(g)
        ca, sa = math.cos(ang), math.sin(ang)
        a_, b_ = L / 2, Wd / 2

        def egg(f, hw):
            U, V = f["U"], f["V"]
            # an egg in plan, blunt end at +U, a vault over it rising to 12 m
            k = np.where(U > 0, 1.0, 0.82)
            r = np.sqrt((U / (a_ * k)) ** 2 + (V / b_) ** 2)
            z = 12.0 * np.sqrt(np.clip(1 - r ** 2, 0, 1))
            m = (r < 1) & (hw >= z - 0.8) & (hw < z)
            ribs = np.mod(U, 2.4) < 0.5
            return np.where(m, np.where(ribs, rib, np.where(np.abs(V) < b_ * 0.4, glass, shell)), 0)
        painted(S, g.buffer(1.0), b0, 13.0, egg, extra={"U": lambda X, Y: (X - cx) * ca + (Y - cy) * sa,
                                                        "V": lambda X, Y: -(X - cx) * sa + (Y - cy) * ca})
    if BIKAS_EXIT in area:
        g = area[BIKAS_EXIT][3]
        b0 = base_under(ctx, g, 0.3)
        cx, cy, L, Wd, ang = rect_of(g)

        def pyr(f, hw):
            d = f["d"]
            return np.where((d > 0) & (hw < np.minimum(d * 1.1, 6.5)) & (hw >= np.minimum(d * 1.1, 6.5) - 0.8), dark, 0)
        painted(S, g, b0, 7.0, pyr)
    for group in BIKAS_DOMES:
        gs = [area[o][3] for o in group if o in area]
        if not gs:
            continue
        g = shapely.union_all(gs).buffer(3.0, join_style=2).minimum_rotated_rectangle
        b0 = base_under(ctx, g, 0.3)
        cx, cy, L, Wd, ang = rect_of(g)
        ca, sa = math.cos(ang), math.sin(ang)

        def hall(f, hw, L=L, Wd=Wd):
            U, V = f["U"], f["V"]
            ru, rv = L / 2, Wd / 2
            e = np.maximum(np.abs(U) - (ru - rv), 0)  # a barrel with rounded ends
            r = np.sqrt((e / rv) ** 2 + (V / rv) ** 2)
            z = min(13.0, rv * 0.75) * np.sqrt(np.clip(1 - r ** 2, 0, 1))
            m = (r < 1) & (hw >= z - 0.8) & (hw < z)
            quilt = (np.mod(U, 3.0) < 0.4) | (np.mod(V + 0.5 * U, 3.0) < 0.4)
            return np.where(m, np.where(quilt, air2, air), 0)
        painted(S, g, b0, 14.0, hall, extra={"U": lambda X, Y, cx=cx, cy=cy, ca=ca, sa=sa: (X - cx) * ca + (Y - cy) * sa,
                                             "V": lambda X, Y, cx=cx, cy=cy, ca=ca, sa=sa: -(X - cx) * sa + (Y - cy) * ca})


# ------------------------------------------------------------------------------------------------ Kelenföld station
def kelenfold_station(S, ctx, plan):
    """Kelenföld station: the 1884 building on Etele tér, two storeys of orange render with red brick pilasters and
    white window surrounds under a grey slate roof, a gabled pavilion at each end (closed since 2017; the trains run on);
    and the long canopies on slim columns over the island platforms."""
    P = ctx["P"]
    area = ctx["area"]
    orange, brick, white, slate, slate2 = P("#d69a5a"), P("#a35a42"), P("#ece6d8"), P("#5e6366", ROOF), P("#545a5d", ROOF)
    win, door, canopy, col = P("#33433f", GLASS), P("#3b5a50"), P("#4a4c4e", ROOF), P("#e4e4e0", METAL)
    if KF_STATION in area:
        g = largest(area[KF_STATION][3])
        b0 = base_under(ctx, g, 0.3)
        E = 10.5

        def fn(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.9)
            bs = np.mod(s, 4.2)
            pil = bs < 0.8
            winm = (np.abs(bs - 2.5) < 0.65) & (((hw > 1.2) & (hw < 3.9)) | ((hw > 6.2) & (hw < 8.8)))
            surround = (np.abs(bs - 2.5) < 0.85) & (((hw > 1.0) & (hw < 4.2)) | ((hw > 6.0) & (hw < 9.1)))
            wall = np.where(pil, brick, np.where(winm, np.where(hw < 4, door, win), np.where(surround, white, orange)))
            wall = np.where((np.abs(hw - 5.2) < 0.3) | (hw > E - 0.6), white, wall)
            o = np.where(edge & (hw < E), wall, 0)
            rh = np.minimum(d * 0.65, 4.5)
            o = np.where(inside & (hw >= E - 0.6) & (hw < E + rh + 0.4), np.where(np.mod(hw, 1.0) < 0.5, slate, slate2), o)
            return o
        painted(S, g, b0, E + 5.5, fn)
    hub = Point(300, 3730)
    for oid in KF_PLATFORMS:
        if oid not in area:
            continue
        pg = area[oid][3].intersection(hub.buffer(170)).buffer(-0.3)
        if pg.is_empty or pg.area < 50:
            continue
        pg = largest(pg)
        b0 = base_under(ctx, pg, 0.5)
        S.add(Poly(pg.buffer(0.8, join_style=2), b0 + 4.6, b0 + 5.2, canopy))
        cx, cy, L, Wd, ang = rect_of(pg)
        fr = Frame(cx, cy, b0, ang)
        for u in np.arange(-L / 2 + 4, L / 2 - 3, 12.0):
            if pg.buffer(-0.5).contains(Point(*fr.xy(u, 0))):
                S.add(Lathe(fr.at(u, 0), 0, 4.6, cyl(0.3), col, n=8))


# ------------------------------------------------------------------------------------------------ Etele Plaza
def etele_plaza(S, ctx, plan):
    """Etele Plaza (2021) on Etele tér: a six-storey mall in white curved panels and blocks of gold, beige and rust
    cladding, a tall glass corner curving round to the square, the car park's grey decks behind and solar panels on
    the roof."""
    P = ctx["P"]
    g = largest(keep(ctx, ETELE))
    b0 = base_under(ctx, g, 0.3)
    white, white2, gold, beige, rust = P("#ecedeb"), P("#dcdedc"), P("#c9a85a"), P("#d9c7a2"), P("#b5563c")
    glass, glass2, roof, solar, grey = P("#4e7f9a", GLASS), P("#5f90aa", GLASS), P("#b8bbbc", ROOF), P("#2c3440", GLASS), P("#8c9194", CONCRETE)
    E = 24.0
    sq = np.array([300.0, 3870.0])  # the corner on Etele tér

    def fn(f, hw):
        d, s, X, Y = f["d"], f["s"], f["X"], f["Y"]
        inside, edge = d > 0, (d > 0) & (d < 0.9)
        near = np.hypot(X - sq[0], Y - sq[1])
        block = hash2(np.floor(s / 14.0), np.floor(hw / 8.0), 7)
        clad = np.choose(np.clip(block, 0, 6), [white, white, white2, gold, beige, rust, white])
        wall = np.where(np.mod(hw, 4.0) < 0.25, white2, clad)
        wall = np.where(near < 55, np.where((np.mod(s, 2.0) < 0.2) | (np.mod(hw, 4.0) < 0.2), white2, glass), wall)
        wall = np.where(hw < 5.0, np.where(np.mod(s, 3.0) < 0.3, grey, glass2), wall)
        o = np.where(edge & (hw < E), wall, 0)
        pv = (np.mod(X + Y, 6.0) < 4.0) & (np.mod(X - Y, 9.0) < 7.0) & (d > 8) & (hash2(np.floor(X / 30), np.floor(Y / 30), 3) == 0)
        o = np.where(inside & ~edge & (hw >= E - 0.6) & (hw < E), np.where(pv, solar, roof), o)
        o = np.where(edge & (hw >= E) & (hw < E + 1.0), white, o)
        return o
    painted(S, g, b0, E + 1.5, fn)


# ------------------------------------------------------------------------------------------------ the BME campus
def bme_campus(S, ctx, plan):
    """the Budapest University of Technology and Economics beside Building K and the Chemistry building: the 1900s
    halls and wings in red brick and ochre with stone bands and tall arched windows under grey and red roofs (R, H, T,
    the boiler house and its chimney, the library with its copper lantern), the post-war blocks in white with ribbon
    windows (D, St, J, A, V1, Z), the 14-storey E tower, the laboratory halls with their rooflights, the domed TR, the
    curved Kármán Tódor hall of residence, and the 2000s Q and I buildings in red brick and blue glass."""
    P = ctx["P"]
    area = ctx["area"]
    brick, brick2, cream, ochre, ochre2 = P("#a65640"), P("#944b37"), P("#e3d6b8"), P("#d8bd86"), P("#c9ab72")
    white, white2, ribbon, win = P("#ebe9e3"), P("#d8d6d0"), P("#3d5466", GLASS), P("#33414a", GLASS)
    teal, glassb, light, redb = P("#4f8b93", GLASS), P("#3f6aa0", GLASS), P("#dfe6e8", GLASS), P("#b2533f")
    roofs = {}
    for oid, (name, style, E, rc) in BME.items():
        if oid not in area:
            continue
        g = largest(area[oid][3])
        b0 = base_under(ctx, g, 0.3)
        r_ = roofs.setdefault(rc, P(rc, ROOF))
        if style == "brick":
            styled(S, g, b0, E, brick, win, r_, floor=4.4, gf=4.6, bay=3.8, winw=1.6, roof_kind="hipped", slope=0.7,
                   ridge=6.0, band=cream, pier=brick2)
        elif style == "ochre":
            styled(S, g, b0, E, ochre, win, r_, floor=4.2, gf=4.4, bay=3.6, winw=1.5, roof_kind="hipped", slope=0.7,
                   ridge=6.0, band=cream, base=ochre2)
        elif style == "white":
            styled(S, g, b0, E, white, ribbon, r_, floor=3.6, gf=3.6, sill=1.0, head=2.6, ribbon=True, band=white2)
        elif style == "dorm":
            styled(S, g, b0, E, white2, win, r_, floor=3.1, gf=4.0, bay=2.4, winw=1.4, band=white)
        elif style == "tower":
            styled(S, g, b0, E, white, teal, r_, floor=3.5, gf=4.5, sill=0.8, head=2.9, ribbon=True, band=white2)
        elif style == "redbrick":
            def rb(f, hw, E=E, r_=r_):
                d, s = f["d"], f["s"]
                inside, edge = d > 0, (d > 0) & (d < 0.9)
                upper = hw > E - 4.5
                winm = (np.mod(hw, 3.6) > 1.0) & (np.mod(hw, 3.6) < 2.7) & (np.abs(np.mod(s, 3.0) - 1.5) < 0.8)
                wall = np.where(upper, np.where(np.mod(s, 1.6) < 0.2, white2, glassb), np.where(winm, win, np.where(np.mod(hw, 3.6) < 0.25, cream, redb)))
                o = np.where(edge & (hw < E), wall, 0)
                return np.where(inside & (hw >= E - 0.6) & (hw < E + 0.4 * np.minimum(d, 4)), r_, o)
            painted(S, g, b0, E + 2.0, rb)
        elif style in ("hall", "vaults"):
            def hl(f, hw, E=E, r_=r_, vaults=style == "vaults"):
                d, s, X, Y = f["d"], f["s"], f["X"], f["Y"]
                inside, edge = d > 0, (d > 0) & (d < 0.9)
                wall = np.where((np.abs(np.mod(s, 4.0) - 2.0) < 1.1) & (hw > 2) & (hw < E - 1.5), win, brick)
                o = np.where(edge & (hw < E), np.where(hw > E - 1.0, cream, wall), 0)
                if vaults:
                    cu, cv = np.mod(X, 9.0) - 4.5, np.mod(Y, 6.0) - 3.0
                    vz = E + 2.2 * np.sqrt(np.clip(1 - (cv / 2.6) ** 2, 0, 1))
                    lit = (np.abs(cu) < 3.6) & (np.abs(cv) < 2.6) & (d > 2)
                    o = np.where(inside & (hw >= E - 0.6) & (hw < np.where(lit, vz, E)), np.where(lit, white, r_), o)
                else:
                    strip = (np.mod(X + Y, 7.0) < 2.2) & (d > 1.5)
                    o = np.where(inside & (hw >= E - 0.6) & (hw < np.where(strip, E + 1.0, E)), np.where(strip, light, r_), o)
                return o
            painted(S, g, b0, E + 2.5, hl)
        elif style == "dome":
            c = g.centroid
            r = math.sqrt(g.area / math.pi)
            fr = Frame(c.x, c.y, b0)
            S.add(Lathe(fr, -0.5, E, cyl(r), lambda u, v, w: np.where(np.mod(np.arctan2(v, u) * 24 / TAU, 1) < 0.5, win, cream).astype(np.uint16), n=24))
            S.add(Lathe(fr, E, E + r * 0.45, dome(r, 2.0, 1.2), lambda u, v, w: np.where(np.mod(np.arctan2(v, u) * 16 / TAU, 1) < 0.12, white2, r_).astype(np.uint16), n=24))
            S.add(Lathe(fr, E + r * 0.45, E + r * 0.45 + 2.0, cyl(1.4), light, n=8))
        if name == "Hö":  # the old boiler house's chimney at its corner
            p = g.exterior.coords[int(len(g.exterior.coords) * 0.6)]
            S.add(Lathe(Frame(p[0], p[1], b0), -0.5, 42.0, cone(2.2, 1.4), brick, n=12))
        if name == "Library":  # the copper lantern over the crossing
            c = g.centroid
            S.add(Lathe(Frame(c.x, c.y, b0), E + 4, E + 10, cyl(2.6), P("#5f8a77", METAL), n=8))
            S.add(Lathe(Frame(c.x, c.y, b0), E + 10, E + 15, cone(2.8, 0.1), P("#5f8a77", METAL), n=8))


# ------------------------------------------------------------------------------------------------ Allee
def allee(S, ctx, plan):
    """Allee (2009) on Október huszonharmadika utca: a four-storey mall with offices over it in light grey panels and
    red brick, ribbon glazing, and a curving glass vault over the street of shops through its middle."""
    P = ctx["P"]
    g = largest(keep(ctx, ALLEE))
    b0 = base_under(ctx, g, 0.3)
    grey, grey2, brick, glass, glass2 = P("#c9cccc"), P("#b6baba"), P("#a3503c"), P("#4f6f80", GLASS), P("#bcd3da", GLASS)
    roof, steel = P("#9fa3a4", ROOF), P("#7d8387", METAL)
    E = 19.0
    A, C = np.array([2505.0, 4300.0]), np.array([2635.0, 4196.0])
    M = np.array([2564.0, 4304.0])
    t = np.linspace(0, 1, 40)[:, None]
    curve = LineString((1 - t) ** 2 * A + 2 * (1 - t) * t * M + t ** 2 * C)

    def vault_d(X, Y):
        return np.reshape(shapely.distance(curve, shapely.points(X.ravel(), Y.ravel())), X.shape)

    def fn(f, hw):
        d, s, vd = f["d"], f["s"], f["vd"]
        inside, edge = d > 0, (d > 0) & (d < 0.9)
        part = np.mod(np.floor(s / 32.0), 3)
        band = (np.mod(hw, 3.8) > 1.0) & (np.mod(hw, 3.8) < 2.9)
        wall = np.where(part == 1, np.where(band & (np.mod(s, 2.4) < 1.6), glass, brick), np.where(band, glass, np.where(np.mod(hw, 3.8) < 0.3, grey2, grey)))
        wall = np.where(hw < 5.0, np.where(np.mod(s, 3.0) < 0.3, steel, glass), wall)
        o = np.where(edge & (hw < E), wall, 0)
        street = vd < 8.0
        vz = E + 3.5 * np.sqrt(np.clip(1 - (vd / 8.0) ** 2, 0, 1))
        o = np.where(inside & ~edge & ~street & (hw >= E - 0.6) & (hw < E), roof, o)
        o = np.where(inside & street & (hw >= vz - 0.6) & (hw < vz), np.where(np.mod(s, 3.0) < 0.3, steel, glass2), o)
        return o
    painted(S, g, b0, E + 4.0, fn, extra={"vd": vault_d})


# ------------------------------------------------------------------------------------------------ Szent Margit Gimnázium
def margit_school(S, ctx, plan):
    """the Szent Margit Gimnázium on Villányi út (1930s): a long cream school of four floors over a stone base under a
    silver-grey hipped roof, with the round tower of its chapel rising to a small dome."""
    P = ctx["P"]
    area = ctx["area"]
    g = largest(area[MARGIT_PART][3] if MARGIT_PART in area else keep(ctx, MARGIT_SCHOOL))
    b0 = base_under(ctx, g, 0.3)
    cream, cream2, stone, win, roofc = P("#efe5c4"), P("#e2d6b1"), P("#cfc3a6"), P("#3c4650", GLASS), P("#9fa4a6", ROOF)
    styled(S, g, b0, 21.0, cream, win, roofc, floor=4.0, gf=4.6, bay=3.3, winw=1.4, roof_kind="hipped", slope=0.65,
           ridge=6.0, band=cream2, base=stone)
    if MARGIT_TOWER in area:
        c = area[MARGIT_TOWER][3].centroid
        r = math.sqrt(area[MARGIT_TOWER][3].area / math.pi) + 0.3
        fr = Frame(c.x, c.y, b0)
        S.add(Lathe(fr, -0.5, 31.0, cyl(r), lambda u, v, w: np.where((np.mod(w - b0, 4.0) > 1.2) & (np.mod(np.arctan2(v, u) * 8 / TAU, 1) < 0.3), win, cream).astype(np.uint16), n=16))
        S.add(Lathe(fr, 31.0, 36.0, dome(r, 2.0), P("#6f8d82", METAL), n=16))
        S.add(Box(fr, -0.1, 0.1, -0.1, 0.1, 36.0, 38.5, P("#d4b85a", METAL)))
        S.add(Box(fr, -0.1, 0.1, -0.6, 0.6, 37.6, 37.8, P("#d4b85a", METAL)))


# ------------------------------------------------------------------------------------------------ A38 gangways
def a38_gangways(S, ctx, plan):
    """the two steel footbridges from the Buda embankment to the A38: straight trusses with grey roofs, sloping down
    from the road along the top of the quay to the ship's upper deck."""
    P = ctx["P"]
    lines = {oid: ln for oid, t, ln in ctx["osm"].lines if oid in A38_WAYS}
    steel, steel2, deck, roof = P("#5d6266", METAL), P("#7b8085", METAL), P("#8b8f90", CONCRETE), P("#9da2a5", ROOF)
    ship = np.array([3479.0, 4836.0])
    for oid, ln in lines.items():
        a, b = np.array(ln.coords[0]), np.array(ln.coords[-1])
        if np.hypot(*(a - ship)) < np.hypot(*(b - ship)):  # a: the quay end
            a, b = b, a
        za = ctx["ground_m"](*a)
        zb = ctx["WLr"] + 5.2
        L = float(np.hypot(*(b - a)))
        fr = Frame(*a, 0, math.atan2(*(b - a)[::-1]))

        def z(u):
            return za + (zb - za) * u / L
        n = max(int(L / 1.5), 2)
        for k in range(n):
            u0, u1 = k * L / n, (k + 1) * L / n
            zm = z((u0 + u1) / 2)
            S.add(Box(fr, u0, u1, -1.4, 1.4, zm - 0.4, zm, deck))
            S.add(Box(fr, u0, u1, -1.6, 1.6, zm + 2.6, zm + 2.9, roof))
            for sv in (-1, 1):
                S.add(Box(fr, u0, u1, sv * 1.5 - 0.1, sv * 1.5 + 0.1, zm - 0.6, zm - 0.2, steel))
                S.add(Box(fr, u0, u1, sv * 1.5 - 0.1, sv * 1.5 + 0.1, zm + 2.3, zm + 2.6, steel))
        for k in range(int(L / 3.0) + 1):  # the truss's posts and diagonals
            u = min(k * 3.0, L)
            for sv in (-1, 1):
                S.line(fr, (u, sv * 1.5, z(u) - 0.4), (u, sv * 1.5, z(u) + 2.6), steel2)
                if u + 3.0 <= L:
                    S.line(fr, (u, sv * 1.5, z(u) - 0.4), (u + 3.0, sv * 1.5, z(u + 3.0) + 2.6), steel2)


# ------------------------------------------------------------------------------------------------ Rákóczi Bridge masts
def rakoczi_masts(S, ctx, plan):
    """the five red lighting masts of Rákóczi (Lágymányosi) Bridge (1995): steel spars leaning out over the roadway
    from the upstream edge of the deck, each on a pair of raked legs, with the lamp boxes and mirrors at their tips
    that light the deck from above."""
    P = ctx["P"]
    area = ctx["area"]
    red, red2, lamp = P("#c3362b", METAL), P("#a92e25", METAL), P("#e9e6dc", METAL)
    deck_top = ctx.get("deck_top")
    for oid in RAKOCZI_MASTS:
        if oid not in area:
            continue
        c = area[oid][3].centroid
        z0 = deck_top(c.x, c.y) if deck_top is not None else ctx["WLr"] + 14.0
        # the masts stand on the deck's upstream edge and lean out over the roadway
        p0 = np.array([2987.0, 5524.0])
        axis = np.array([3346 - 2987, 5864 - 5524], float)
        axis /= np.linalg.norm(axis)
        off = np.array([c.x, c.y]) - p0
        off -= (off @ axis) * axis
        lean = -off / max(np.linalg.norm(off), 1e-6)
        fr = Frame(c.x, c.y, z0, math.atan2(axis[1], axis[0]))
        lu, lv = float(lean @ axis), float(lean @ np.array([-axis[1], axis[0]]))
        top = (lu * 9.0, lv * 9.0, 24.0)
        S.add(Capsule(fr, (0, 0, 0), top, 0.55, red))
        for su in (-1, 1):  # the raked legs along the deck
            S.add(Capsule(fr, (su * 5.0, 0, 0), (lu * 3.0, lv * 3.0, 9.0), 0.35, red2))
        ft = fr.at(*top[:2], top[2])
        S.add(Box(ft, -1.2, 1.2, -0.6, 0.6, -0.4, 0.6, lamp))


BUILDERS = [("MOL Campus", mol_campus), ("Kelenföld power station", kelenfold_power), ("Bikás Park", bikas_park),
            ("Kelenföld station", kelenfold_station), ("Etele Plaza", etele_plaza), ("BME campus", bme_campus),
            ("Allee", allee), ("Szent Margit Gimnázium", margit_school), ("A38 gangways", a38_gangways),
            ("Rákóczi Bridge masts", rakoczi_masts)]
