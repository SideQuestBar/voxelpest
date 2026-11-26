"""Late November 2026, fifth round, beyond the boulevards: the mausoleums and arcades of Kerepesi Cemetery, the Ludovika
(the Natural History Museum's house) in its garden, the National Theatre and its Ziggurat, the Papp László Sportaréna,
the Northern Vehicle Repair Works that will house the Transport Museum, the Cistercian church of St Emeric on Villányi
út, and Millenáris park's Ganz halls beside the Mammut malls. Outlines from OSM; heights, colours and details from the
Esri aerial and street photos (docs/landmarks.md)."""
import math

import numpy as np

from landmarks import WINDOW, Arch, Box, Ellipsoid, Frame, Lathe, Roof, cone, cyl, dome, rect_of
from landmarks_city import base_under, statue
from landmarks_hosok import keep
from landmarks_kit import largest, painted, styled
from style import GLASS, METAL, ROOF

TAU = 2 * math.pi
KOSSUTH, DEAK, BATTHYANY, ARCADES, PANTHEON = 166167090, 166167091, 188827706, (188827765, 188827766), 526250716
LUDOVIKA = 355536267
THEATRE, ZIGGURAT = 127065014, 543285043
ARENA = 25266203
WORKS = ((254600760, 14.0), (254600759, 12.0), (254600751, 12.0), (254600753, 10.0), (254600713, 9.0),
         (254600701, 9.0))
IMRE_NAVE, IMRE_AISLES, IMRE_CHOIR = 794796550, (794796544, 794796540), 794796541
IMRE_TOWERS = ((794796549, 794796542), (794796543, 794796547))
IMRE_FRONT = (794796545, 794796546, 794796548)
MILL_HALLS, MILL_OFFICE, MAMMUT = 121236768, 268362233, (156980496, 50847315)

NAMES = ["Kerepesi Cemetery mausoleums", "Ludovika", "National Theatre", "Papp László Sportaréna",
         "Northern Vehicle Repair Works", "Cistercian church of St Emeric", "Millenáris and Mammut"]
DROP = {KOSSUTH, DEAK, BATTHYANY, *ARCADES, PANTHEON, LUDOVIKA, THEATRE, ZIGGURAT, ARENA, *(i for i, _ in WORKS),
        IMRE_NAVE, *IMRE_AISLES, IMRE_CHOIR, *(i for t in IMRE_TOWERS for i in t), *IMRE_FRONT, MILL_HALLS,
        MILL_OFFICE, *MAMMUT}
KEEP = [(KOSSUTH, 14), (DEAK, 18), (LUDOVIKA, 18), (THEATRE, 24), (ARENA, 30), (254600760, 14), (MILL_HALLS, 14),
        (MILL_OFFICE, 18), (MAMMUT[0], 22), (MAMMUT[1], 22)]


def area(ctx, oid):
    try:
        return largest(keep(ctx, oid))
    except KeyError:
        return None


# ------------------------------------------------------------------------------------------------ Kerepesi
def kerepesi(S, ctx, plan):
    """Kerepesi Cemetery's monuments: Kossuth's mausoleum (Alajos Stróbl and Albert Gerster, 1909), a block of dark
    granite stepping up to the bronze Genius with a lamp between two lions; Deák's (Gerster and Stróbl, 1887), a Greek
    cross of white limestone under a dome; Batthyány's (Albert Schickedanz, 1870), a granite sarcophagus on its
    stepped base; the arcades (1908-11) in pale stone under green copper; and the Labour Movement Pantheon (1959), its
    white wall of pylons."""
    P = ctx["P"]
    granite, granite2, bronze, lime, lime2 = P("#6f6c68"), P("#5d5a56"), P("#5c7d6c", METAL), P("#ebe6da"), P("#d7d0c0")
    cu, dark = P("#5f9a86", ROOF), P("#2f2d2a", WINDOW)
    g = area(ctx, KOSSUTH)
    if g is not None:
        cx, cy, L, W, ang = rect_of(g)
        b0 = base_under(ctx, g, 0.3)
        fr = Frame(cx, cy, b0, ang)
        S.add(Box(fr, -L / 2, L / 2, -W / 2, W / 2, -1.0, 1.0, granite2))
        S.add(Box(fr, -L / 2 + 3.0, L / 2 - 3.0, -W / 2 + 2.0, W / 2 - 2.0, 1.0, 7.0, granite))
        for k, (a, b) in enumerate(((7.0, 8.5), (8.5, 10.0), (10.0, 11.5))):
            S.add(Box(fr, -L / 2 + 4.0 + 1.5 * k, L / 2 - 4.0 - 1.5 * k, -W / 2 + 3.0 + k, W / 2 - 3.0 - k, a, b, granite2))
        for su in (-1, 1):
            S.add(Arch(fr.at(su * (L / 2 - 3.0)).at(turn=0), -0.6, 0.6, 0, 1.6, 1.0, 4.0, dark))
        statue(S, fr, 11.5, bronze, 1.8)
        for sv in (-1, 1):
            S.add(Ellipsoid(fr.at(0, sv * 2.6, 12.4), 1.6, 0.7, 0.8, bronze))
            S.add(Ellipsoid(fr.at(1.2, sv * 2.6, 13.2), 0.5, 0.45, 0.55, bronze))
    g = area(ctx, DEAK)
    if g is not None:
        c = g.centroid
        _, _, L, W, ang = rect_of(g)
        b0 = base_under(ctx, g, 0.3)
        fr = Frame(c.x, c.y, b0, ang)
        a = min(L, W) / 2
        for k in range(2):
            fk = fr.at(turn=k * math.pi / 2)
            S.add(Box(fk, -a + 1.0, a - 1.0, -5.5, 5.5, -1.0, 10.0, lime))
            S.add(Roof(fk, -a + 0.6, a - 0.6, -6.0, 6.0, 10.0, 2.6, lime2))
            for su in (-1, 1):
                S.add(Arch(fk.at(su * (a - 1.0)).at(turn=0), -0.6, 0.6, 0, 1.8, 0.0, 4.5, dark))
        S.add(Box(fr, -8.0, 8.0, -8.0, 8.0, -1.0, 11.0, lime))
        S.add(Lathe(fr, 11.0, 15.0, cyl(6.0), lime, n=16))
        S.add(Lathe(fr, 15.0, 15.6, cyl(6.4), lime2, n=16))
        S.add(Lathe(fr, 15.6, 21.0, dome(6.1, 2.0, 1.0), cu, n=16))
        S.add(Lathe(fr, 21.0, 22.6, cyl(0.9), lime, n=8))
    g = area(ctx, BATTHYANY)
    if g is not None:
        cx, cy, L, W, ang = rect_of(g)
        b0 = base_under(ctx, g, 0.3)
        fr = Frame(cx, cy, b0, ang)
        W = min(W, 12.0)
        for k in range(3):
            S.add(Box(fr, -L / 2 + 2.5 + 1.2 * k, L / 2 - 2.5 - 1.2 * k, -W / 2 + 1.0 + 1.0 * k, W / 2 - 1.0 - 1.0 * k,
                      k * 1.0 - (1.0 if k == 0 else 0.0), 1.0 + k * 1.0, granite2))
        S.add(Box(fr, -4.0, 4.0, -2.2, 2.2, 3.0, 5.6, granite))
        S.add(Roof(fr, -4.3, 4.3, -2.5, 2.5, 5.6, 1.2, granite2))
    for oid in ARCADES:
        g = area(ctx, oid)
        if g is None:
            continue
        b0 = base_under(ctx, g, 0.3)

        def fn(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.8)
            bay = np.abs(np.mod(s, 4.0) - 2.0)
            arch = (bay < 1.5) & ((hw < 3.8) | (bay ** 2 + (hw - 3.8) ** 2 < 2.25)) & (hw > 0.3)
            o = np.where(edge & (hw < 6.5), np.where(arch, dark, lime), 0)
            o = np.where(edge & (hw >= 6.5) & (hw < 7.2), lime2, o)
            return np.where(inside & (hw >= 7.2) & (hw < 7.2 + np.minimum(d * 0.7, 2.6)), cu, o)
        painted(S, g, b0, 10.0, fn)
    g = area(ctx, PANTHEON)
    if g is not None:
        cx, cy, L, W, ang = rect_of(g)
        b0 = base_under(ctx, g, 0.3)
        fr = Frame(cx, cy, b0, ang)
        S.add(Box(fr, -L / 2, L / 2, -1.2, 1.2, -1.0, 6.0, lime))
        for u in np.linspace(-L / 2 + 1.5, L / 2 - 1.5, 6):
            S.add(Box(fr, u - 0.9, u + 0.9, -1.8, 1.8, -1.0, 11.0, lime2))
        S.add(Box(fr, -6.0, 6.0, 1.2, 1.4, 1.5, 5.0, bronze))


# ------------------------------------------------------------------------------------------------ the Ludovika
def ludovika(S, ctx, plan):
    """the Ludovika (Mihály Pollack, 1836), the military academy that housed the Natural History Museum and now the
    University of Public Service: a long classicist front in ochre and white, a portico of six columns under its
    pediment in the middle, grey roofs."""
    P = ctx["P"]
    g = area(ctx, LUDOVIKA)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    ochre, white, win, slate = P("#e2c37f"), P("#f3eee2"), P("#33404a", WINDOW), P("#6f7477", ROOF)
    E = 15.0
    styled(S, g, b0, E, ochre, win, slate, floor=4.0, gf=4.6, bay=3.6, winw=1.4, sill=0.9, head=3.0,
           roof_kind="hip", slope=0.6, ridge=3.5, band=white, base=white)
    pts = np.array(g.exterior.coords)[:-1]
    cx, cy, L, W, ang = rect_of(g)
    n = np.array([-math.sin(ang), math.cos(ang)])
    side = 1.0 if n @ (np.array([5650.0, 6400.0]) - np.array([cx, cy])) > 0 else -1.0  # towards Üllői út
    p = np.array([cx, cy]) + n * side * (np.max(pts @ (n * side)) - np.array([cx, cy]) @ (n * side))
    fr = Frame(float(p[0]), float(p[1]), b0, math.atan2(n[1] * side, n[0] * side))
    for k in range(6):
        S.add(Lathe(fr.at(2.4, -6.25 + k * 2.5), 1.2, E - 1.6, cyl(0.5), white, n=12))
    S.add(Box(fr, 0.0, 3.6, -8.0, 8.0, -1.0, 1.2, white))
    S.add(Box(fr, 0.0, 3.4, -7.6, 7.6, E - 1.6, E, white))
    S.add(Roof(fr.at(turn=math.pi / 2), -7.8, 7.8, -3.4, 3.4 + 0.01, E, 2.8, white))


# ------------------------------------------------------------------------------------------------ the National Theatre
def theatre(S, ctx, plan):
    """the National Theatre (Mária Siklós, 2002): the auditorium's drum under a stepped glass roof like a ship's hull,
    the foyer's glass front and pale stone wings; in the park beside it the Ziggurat, a white stepped cone the visitors
    climb."""
    P = ctx["P"]
    g = area(ctx, THEATRE)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        pale, glass, frame = P("#e6e1d6"), P("#7fa3b0", GLASS), P("#c8cccc", METAL)
        E = 18.0

        def fn(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.8)
            o = np.where(edge & (hw < E), np.where(np.mod(hw, 4.0) < 0.6, pale, np.where(np.mod(s, 2.0) < 0.3, frame, glass)), 0)
            z = E + np.minimum(d, 12.0) * 0.9
            step = np.floor(z / 1.5) * 1.5
            roof = np.where(np.mod(s, 3.0) < 0.3, frame, glass)
            return np.where(inside & (hw >= E - 0.6) & (hw < step) & (hw >= step - 1.0), roof, o)
        painted(S, g, b0, E + 12.0, fn)
    g = area(ctx, ZIGGURAT)
    if g is not None:
        c = g.centroid
        b0 = base_under(ctx, g, 0.3)
        r = rect_of(g)[3] / 2
        white, white2 = P("#efede6"), P("#d9d6cc")
        fz = Frame(c.x, c.y, b0, 0.0)
        for k in range(8):
            rk = r * (1 - k / 8.5)
            S.add(Lathe(fz, k * 1.45 - (0.6 if k == 0 else 0), (k + 1) * 1.45, cyl(rk), white if k % 2 else white2, n=0))


# ------------------------------------------------------------------------------------------------ the arena
def arena(S, ctx, plan):
    """the Papp László Sportaréna (2003): an oval drum of glass and silver panels under a shallow silver dome."""
    P = ctx["P"]
    g = area(ctx, ARENA)
    if g is None:
        return
    b0 = base_under(ctx, g, 0.3)
    silver, silver2, glass, frame = P("#c9ced1", METAL), P("#aeb4b8", METAL), P("#7f9fb0", GLASS), P("#dfe2e3", METAL)
    E = 20.0
    D = max(rect_of(g)[3] / 2, 1.0)

    def fn(f, hw):
        d, s = f["d"], f["s"]
        inside, edge = d > 0, (d > 0) & (d < 0.9)
        wall = np.where(hw < 6.0, np.where(np.mod(s, 3.0) < 0.4, frame, glass),
                        np.where(np.mod(hw, 2.5) < 0.3, silver2, silver))
        o = np.where(edge & (hw < E), wall, 0)
        t = np.clip(d / D, 0, 1)
        z = E + 12.0 * np.sqrt(t * (2 - t))
        return np.where(inside & (hw >= z - 0.8) & (hw < z), np.where(np.mod(s + d, 8.0) < 0.5, silver2, silver), o)
    painted(S, g, b0, E + 12.5, fn)


# ------------------------------------------------------------------------------------------------ the repair works
def works(S, ctx, plan):
    """the Northern Vehicle Repair Works (MÁV Északi Járműjavító, 1880s), chosen for the new Transport Museum: long
    halls of yellow and red brick with rows of arched windows, under roofs of glazed sawtooths and gables."""
    P = ctx["P"]
    brick, brick2, win, glass, roof = P("#b56a4a"), P("#d9b77c"), P("#33404a", WINDOW), P("#8fb3bf", GLASS), P("#6f6f6c", ROOF)
    for oid, E in WORKS:
        g = area(ctx, oid)
        if g is None:
            continue
        b0 = base_under(ctx, g, 0.3)
        _, _, L, W, ang = rect_of(g)
        ca, sa = math.cos(ang), math.sin(ang)

        def fn(f, hw, E=E, ca=ca, sa=sa):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.8)
            bay = np.abs(np.mod(s, 5.0) - 2.5)
            arch = (hw > 1.5) & (bay < 1.3) & ((hw < E - 3.5) | (bay ** 2 + (hw - E + 3.5) ** 2 < 1.69))
            wall = np.where((bay > 2.0) | (np.mod(hw, 3.0) < 0.3), brick2, brick)
            o = np.where(edge & (hw < E), np.where(arch, win, wall), 0)
            u = f["X"] * ca + f["Y"] * sa
            saw = E + 3.0 * np.mod(u, 8.0) / 8.0
            col = np.where(np.mod(u, 8.0) > 6.2, glass, roof)
            return np.where(inside & (hw >= E - 0.6) & (hw < saw) & (hw >= saw - 1.0), col, o)
        painted(S, g, b0, E + 3.2, fn)


# ------------------------------------------------------------------------------------------------ St Emeric
def imre(S, ctx, plan):
    """the Cistercian church of St Emeric on Villányi út (Gyula Wälder, 1938): neo-Baroque in pale yellow, its nave and
    sanctuary under red tiles, its front's two towers rising to green copper spires 54 m up."""
    P = ctx["P"]
    yellow, white, win, tile, flat = P("#f1e3b2"), P("#f6f1e3"), P("#33404a", WINDOW), P("#a9452f", ROOF), P("#b8bcbe", ROOF)
    cu, cu2, gold = P("#5f9a86", ROOF), P("#4f8875", ROOF), P("#d4ad55", METAL)
    for oid, E, roof, kind in ((IMRE_NAVE, 16.0, tile, "hip"), (IMRE_CHOIR, 15.0, tile, "hip"),
                               (IMRE_AISLES[0], 9.0, flat, "flat"), (IMRE_AISLES[1], 9.0, flat, "flat"),
                               (IMRE_FRONT[0], 8.0, flat, "flat"), (IMRE_FRONT[1], 20.0, yellow, "flat")):
        g = area(ctx, oid)
        if g is None:
            continue
        styled(S, g, base_under(ctx, g, 0.3), E, yellow, win, roof, floor=E, gf=2.5, bay=4.0, winw=1.4, sill=2.0,
               head=E - 5.0, roof_kind=kind, slope=1.1, ridge=6.0, band=white)
    for body, _ in IMRE_TOWERS:
        g = area(ctx, body)
        if g is None:
            continue
        cx, cy, L, W, ang = rect_of(g)
        b0 = base_under(ctx, g, 0.3)
        ft = Frame(cx, cy, b0, ang)
        h = min(L, W) / 2
        S.add(Box(ft, -h, h, -h, h, -1.0, 36.0, yellow))
        for w in (20.0, 28.0):
            S.add(Box(ft, -h - 0.3, h + 0.3, -h - 0.3, h + 0.3, w, w + 0.6, white))
        for k in range(4):
            S.add(Arch(ft.at(turn=k * math.pi / 2), h - 0.5, h + 0.2, 0, 0.8, 30.0, 33.5, win, mode="paint", targets=[yellow]))
        S.add(Box(ft, -h - 0.3, h + 0.3, -h - 0.3, h + 0.3, 36.0, 36.8, white))
        S.add(Lathe(ft, 36.8, 41.0, cone(h * 1.05, h * 0.5), cu2, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 41.0, 53.0, cone(h * 0.5, 0.08), cu, n=8, rot=math.pi / 8))
        S.add(Box(ft, -0.08, 0.08, -0.08, 0.08, 53.0, 54.6, gold))


# ------------------------------------------------------------------------------------------------ Millenáris and Mammut
def millenaris(S, ctx, plan):
    """Millenáris park (2001) in the Ganz works' old halls: brick halls under glazed saddle roofs, the yellow office
    range along Kis Rókus utca; and across Lövőház utca the Mammut malls (1998, 2001), five floors in pale panels and
    blue-green glass, the glazed atrium on the corner."""
    P = ctx["P"]
    brick, brick2, win, glass, frame = P("#a85c42"), P("#c98e6a"), P("#33404a", WINDOW), P("#8fb3bf", GLASS), P("#c8cccc", METAL)
    g = area(ctx, MILL_HALLS)
    if g is not None:
        b0 = base_under(ctx, g, 0.3)
        _, _, L, W, ang = rect_of(g)
        ca, sa = math.cos(ang), math.sin(ang)

        def fn(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.8)
            bay = np.abs(np.mod(s, 4.5) - 2.25)
            arch = (hw > 1.5) & (hw < 9.0) & (bay < 1.2)
            o = np.where(edge & (hw < 11.0), np.where(arch, win, np.where(bay > 1.9, brick2, brick)), 0)
            v = -f["X"] * sa + f["Y"] * ca
            ridge = 11.0 + 4.0 * (1 - np.abs(np.mod(v, 18.0) - 9.0) / 9.0)
            col = np.where(np.abs(np.mod(v, 18.0) - 9.0) < 5.0, np.where(np.mod(s, 3.0) < 0.3, frame, glass), P("#6f6f6c", ROOF))
            return np.where(inside & (hw >= 10.4) & (hw < ridge) & (hw >= ridge - 0.9), col, o)
        painted(S, g, b0, 15.5, fn)
    g = area(ctx, MILL_OFFICE)
    if g is not None:
        styled(S, g, base_under(ctx, g, 0.3), 17.0, P("#efd9a0"), win, P("#8a8d8f", ROOF), floor=3.4, gf=4.4, bay=3.2,
               winw=1.6, roof_kind="hip", slope=1.0, ridge=4.0, band=P("#f6eed8"))
    for oid in MAMMUT:
        g = area(ctx, oid)
        if g is None:
            continue
        b0 = base_under(ctx, g, 0.3)
        pale, teal = P("#dcdad3"), P("#5e8f96", GLASS)

        def fm(f, hw):
            d, s = f["d"], f["s"]
            inside, edge = d > 0, (d > 0) & (d < 0.8)
            band = np.mod(hw, 4.2) < 1.2
            wall = np.where(band, pale, teal)
            wall = np.where(np.mod(s, 30.0) < 8.0, np.where(np.mod(s, 2.0) < 0.3, frame, glass), wall)
            o = np.where(edge & (hw < 21.0), wall, 0)
            o = np.where(inside & ~edge & (hw >= 20.4) & (hw < 21.0), P("#a9aca8", ROOF), o)
            return np.where(edge & (hw >= 21.0) & (hw < 21.8), pale, o)
        painted(S, g, b0, 22.0, fm)


BUILDERS = [("Kerepesi Cemetery mausoleums", kerepesi), ("Ludovika", ludovika), ("National Theatre", theatre),
            ("Papp László Sportaréna", arena), ("Northern Vehicle Repair Works", works),
            ("Cistercian church of St Emeric", imre), ("Millenáris and Mammut", millenaris)]
