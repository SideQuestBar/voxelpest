"""Kossuth tér, the square in front of the Parliament: the national flag on its 33 m mast, the main entrance's
staircase with its two lions, the equestrian statues of Ferenc Rákóczi II and Gyula Andrássy, the Tisza and Kossuth
memorials, Attila József on the embankment steps, and the dark granite square on the dome's axis. Positions are OSM's
nodes; sizes are estimated from photos (docs/landmarks.md).
"""
import math

import numpy as np

from landmarks import Arch, Box, Capsule, Ellipsoid, Frame, Lathe, cone, feat_base, rect_of
from landmarks_city import statue
from style import METAL

PARLIAMENT, DOME = 3199085, 237397586
FLAG = (2030.1, 1524.4)          # man_made=flagpole, height 33
RAKOCZI = (1962.7, 1565.3)
ANDRASSY = (1810.0, 1539.5)
TISZA = (2077.8, 1297.1)
KOSSUTH = (2117.7, 1404.5)
JOZSEF_ATTILA = (1751.0, 1560.7)

NAMES = ["Kossuth tér"]


def horseman(S, fr, w0, s, horse, rider, step=True):
    """a rider on a horse walking towards +u, s = 1 about 4.7 m to the rider's head."""
    b = w0
    S.add(Ellipsoid(fr.at(0, 0, b + 2.3 * s), 1.55 * s, 0.62 * s, 0.72 * s, horse))
    for su in (-1, 1):
        for sv in (-1, 1):
            top = (1.05 * su * s, 0.32 * sv * s, b + 2.0 * s)
            if step and su > 0 and sv > 0:  # a foreleg raised
                S.add(Capsule(fr, top, (1.55 * s, 0.32 * s, b + 1.25 * s), 0.17 * s, horse))
                S.add(Capsule(fr, (1.55 * s, 0.32 * s, b + 1.25 * s), (1.45 * s, 0.32 * s, b + 0.75 * s), 0.15 * s, horse))
            else:
                S.add(Capsule(fr, top, (1.05 * su * s, 0.32 * sv * s, b + 0.15 * s), 0.17 * s, horse))
    S.add(Capsule(fr, (1.15 * s, 0, b + 2.55 * s), (1.85 * s, 0, b + 3.55 * s), 0.36 * s, horse))
    S.add(Capsule(fr, (1.9 * s, 0, b + 3.6 * s), (2.4 * s, 0, b + 3.05 * s), 0.24 * s, horse))
    S.add(Capsule(fr, (-1.45 * s, 0, b + 2.5 * s), (-1.85 * s, 0, b + 1.3 * s), 0.16 * s, horse))
    S.add(Capsule(fr, (0.05 * s, 0, b + 2.85 * s), (-0.05 * s, 0, b + 4.05 * s), 0.34 * s, rider))
    S.add(Ellipsoid(fr.at(-0.02 * s, 0, b + 4.45 * s), 0.22 * s, 0.22 * s, 0.27 * s, rider))
    for sv in (-1, 1):
        S.add(Capsule(fr, (0.1 * s, 0.3 * sv * s, b + 2.95 * s), (0.35 * s, 0.68 * sv * s, b + 2.1 * s), 0.16 * s, rider))
        S.add(Capsule(fr, (0.0, 0.36 * sv * s, b + 3.9 * s), (0.45 * s, 0.42 * sv * s, b + 3.2 * s), 0.12 * s, rider))


def lion(S, fr, b, col):
    """a lying lion on top of a pedestal at height b, facing +u."""
    S.add(Ellipsoid(fr.at(-0.3, 0, b + 0.7), 1.9, 0.75, 0.75, col))
    S.add(Ellipsoid(fr.at(1.15, 0, b + 1.15), 0.75, 0.9, 1.0, col))
    S.add(Ellipsoid(fr.at(1.75, 0, b + 1.3), 0.6, 0.55, 0.65, col))
    S.add(Box(fr, 1.0, 2.4, -0.65, 0.65, b, b + 0.45, col))
    S.add(Capsule(fr, (-2.1, 0.3, b + 0.3), (-2.6, 0.9, b + 0.25), 0.22, col))


def flag(S, ctx, fr, w_top, length, height):
    """the national flag flying from a mast along +u, waving: red, white and green in three bands."""
    P = ctx["P"]
    red, white, green = P("#cd2a3e"), P("#f2f1ec"), P("#3e7b4c")
    band = height / 3

    def col(u, v, w):
        wave = 0.7 * np.sin(u * 1.25 - 0.6) * (u / length) + 0.35 * np.sin(w * 0.8 + u * 0.5) * (u / length)
        on = np.abs(v - wave) < 0.28
        z = w_top - w
        c = np.where(z < band, red, np.where(z < 2 * band, white, green))
        return np.where(on, c, 0).astype(np.uint16)
    S.add(Box(fr, 0.3, length, -1.6, 1.6, w_top - height, w_top, col))


def pedestal(S, fr, w0, lu, lv, h, col, cap=None):
    S.add(Box(fr, -lu / 2 - 0.4, lu / 2 + 0.4, -lv / 2 - 0.4, lv / 2 + 0.4, w0, w0 + 0.6, col))
    S.add(Box(fr, -lu / 2, lu / 2, -lv / 2, lv / 2, w0 + 0.6, w0 + h - 0.4, col))
    S.add(Box(fr, -lu / 2 - 0.25, lu / 2 + 0.25, -lv / 2 - 0.25, lv / 2 + 0.25, w0 + h - 0.4, w0 + h, cap or col))


def kossuth_square(S, ctx, plan):
    P, area, g_at = ctx["P"], ctx["area"], ctx["ground_m"]
    host, dg = area[PARLIAMENT][3], area[DOME][3]
    b0 = feat_base(ctx, PARLIAMENT)
    hang = rect_of(host)[4]
    ax = np.array([math.cos(hang), math.sin(hang)])
    sq = np.array([ax[1], -ax[0]])  # from the dome out to the square (the river lies the other way)
    dome = np.array([dg.centroid.x, dg.centroid.y])
    if float(sq @ (np.array(FLAG) - dome)) < 0:
        sq = -sq
    out_ang = math.atan2(sq[1], sq[0])
    axis = Frame(dome[0], dome[1], 0, out_ang)  # u: out to the square, v: along the building

    stone, granite, marble = P("#d9d3c4"), P("#7b4b40"), P("#ebe7dc")
    bronze, patina = P("#3f3a33", METAL), P("#5f8b78", METAL)
    steel = P("#c4c7c9", METAL)

    # the dark granite square on the axis, between the lawns, from the stairs to the water
    gq = g_at(*axis.xy(115, 0))
    S.add(Box(axis, 89, 139, -37, 36, gq - 1.6, gq + 1.0, P("#5d5f62"), mode="paint",
              targets=[ctx["C"]["paving"], ctx["C"]["paving2"]]))

    # the main entrance: steps up to the porch, its three pointed arches, two lions at the foot
    g_foot = g_at(*axis.xy(88, 0))
    floor = max(b0 + 2.4, g_foot + 1.5)
    n = max(int(round((floor - g_foot) / 0.5)), 1)
    run = 6.4 / n
    for i in range(n):
        S.add(Box(axis, 80.0, 87.0 - i * run, -9.0, 9.0, g_foot - 1.0, g_foot + (i + 1) * (floor - g_foot) / n, stone))
    for vc in (-5.3, 0.0, 5.3):
        fa = axis.at(81.2, vc, 0, math.pi)
        S.add(Arch(fa, -0.2, 3.0, 0, 1.7, floor, floor + 6.2, mode="carve"))
        if ctx.get("parl_walls"):
            S.add(Arch(fa, 3.0, 3.5, 0, 1.7, floor, floor + 6.2, P("#6d675d"), mode="paint", targets=ctx["parl_walls"]))
    for sv in (-1, 1):
        fl = axis.at(88.5, sv * 10.2, g_foot)
        S.add(Box(fl, -2.4, 2.4, -1.1, 1.1, -0.5, 1.9, stone))
        S.add(Box(fl, -2.6, 2.6, -1.3, 1.3, 1.9, 2.2, stone))
        lion(S, fl, 2.2, bronze)

    # the national flag: a 33 m steel mast on a stone foot, the flag flying with the wind (from the north-west)
    gf = g_at(*FLAG)
    S.add(Box(Frame(FLAG[0], FLAG[1], gf, out_ang), -1.6, 1.6, -1.6, 1.6, -0.5, 0.7, stone))
    S.add(Lathe(Frame(FLAG[0], FLAG[1], gf, 0), 0.7, 33.0, cone(0.42, 0.16), steel))
    # the taper drops under half a voxel near the top, where the lathe draws nothing: a voxel line keeps the mast whole
    S.line(Frame(FLAG[0], FLAG[1], gf, 0), (0, 0, 0.7), (0, 0, 33.0), steel)
    S.add(Ellipsoid(Frame(FLAG[0], FLAG[1], gf + 33.2, 0), 0.32, 0.32, 0.32, P("#d4ad55", METAL)))
    flag(S, ctx, Frame(FLAG[0], FLAG[1], gf, math.pi / 2 - 0.25), 32.6, 9.0, 4.5)

    # Ferenc Rákóczi II (János Pásztor, 1937): green bronze on red granite, in the southern lawn
    g = g_at(*RAKOCZI)
    fr = Frame(RAKOCZI[0], RAKOCZI[1], g, out_ang + math.pi / 2)
    pedestal(S, fr, -0.3, 5.0, 2.4, 4.6, granite)
    horseman(S, fr, 4.3, 1.1, patina, patina)

    # Gyula Andrássy (György Zala, 1906, recast 2016): dark bronze on white marble, bronze groups round the foot
    g = g_at(*ANDRASSY)
    fr = Frame(ANDRASSY[0], ANDRASSY[1], g, hang)
    S.add(Box(fr, -5.0, 5.0, -2.8, 2.8, -0.4, 1.0, marble))
    pedestal(S, fr, 0.6, 5.4, 2.6, 4.8, marble)
    for sv in (-1, 1):
        S.add(Ellipsoid(fr.at(0, sv * 2.2, 2.2), 2.6, 0.55, 1.3, bronze))
    horseman(S, fr, 5.4, 1.15, bronze, bronze)

    # István Tisza (Zala, 1934, rebuilt 2014): a white pylon of two fluted piers with a sculpture group on top, the
    # bronze figure in front between two bronze groups, all on a broad white plinth
    g = g_at(*TISZA)
    fr = Frame(TISZA[0], TISZA[1], g, hang)
    S.add(Box(fr, -4.0, 4.0, -6.5, 6.5, -0.4, 1.2, marble))
    for sv in (-1, 1):
        S.add(Box(fr, -3.2, -1.6, sv * 1.0, sv * 2.6, 1.2, 8.4, marble))
    S.add(Box(fr, -3.4, -1.4, -2.9, 2.9, 8.4, 9.6, marble))
    S.add(Ellipsoid(fr.at(-2.3, 0, 10.4), 0.9, 2.2, 0.9, marble))
    S.add(Ellipsoid(fr.at(-2.3, 0.6, 11.2), 0.6, 0.8, 0.8, marble))
    S.add(Box(fr, -0.2, 1.6, -1.0, 1.0, 1.2, 2.4, marble))
    statue(S, fr.at(0.7, 0, 0, 0), 2.4, bronze, scale=1.25)
    for sv in (-1, 1):
        S.add(Ellipsoid(fr.at(0.6, sv * 4.3, 2.4), 1.0, 1.4, 1.2, bronze))
        S.add(Ellipsoid(fr.at(0.6, sv * 4.6, 3.6), 0.5, 0.5, 0.6, bronze))

    # Lajos Kossuth (János Horvay, 1927, rebuilt 2014): a long white wall, the figure groups of 1848 and 1849 before
    # it, Kossuth on a tall pedestal in the middle
    g = g_at(*KOSSUTH)
    fr = Frame(KOSSUTH[0], KOSSUTH[1], g, hang)
    S.add(Box(fr, -4.5, 5.5, -13.0, 13.0, -0.4, 0.9, marble))
    S.add(Box(fr, -3.6, -2.0, -11.5, 11.5, 0.9, 6.6, marble))
    S.add(Box(fr, -3.8, -1.8, -11.8, 11.8, 6.6, 7.2, marble))
    for sv in (-1, 1):
        for k in range(5):
            vv = sv * (3.2 + k * 1.6)
            S.add(Ellipsoid(fr.at(-0.9, vv, 2.3), 0.65, 0.6, 1.5, marble))
            S.add(Ellipsoid(fr.at(-0.9, vv, 4.0), 0.3, 0.3, 0.36, marble))
    S.add(Box(fr, -1.6, 1.6, -1.6, 1.6, 0.9, 6.0, marble))
    S.add(Box(fr, -1.8, 1.8, -1.8, 1.8, 6.0, 6.5, marble))
    statue(S, fr, 6.5, marble, scale=1.45)

    # Attila József sitting on the embankment steps, looking at the Danube
    g = g_at(*JOZSEF_ATTILA)
    fr = Frame(JOZSEF_ATTILA[0], JOZSEF_ATTILA[1], g, out_ang + math.pi)
    for i in range(3):
        S.add(Box(fr, -1.5, 1.5 - i * 0.5, -2.5, 2.5, -0.4, 0.5 * (i + 1) - 0.2, stone))
    S.add(Capsule(fr, (-0.15, 0, 1.3), (-0.05, 0, 2.0), 0.26, bronze))
    S.add(Ellipsoid(fr.at(-0.05, 0, 2.3), 0.15, 0.15, 0.19, bronze))
    for sv in (-1, 1):
        S.add(Capsule(fr, (-0.1, sv * 0.18, 1.35), (0.45, sv * 0.2, 1.3), 0.12, bronze))
        S.add(Capsule(fr, (0.45, sv * 0.2, 1.3), (0.55, sv * 0.2, 0.85), 0.11, bronze))
    ctx["note"]("    Kossuth tér: flag, steps and lions, five monuments")


BUILDERS = [("Kossuth tér", kossuth_square)]
