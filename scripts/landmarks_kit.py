"""Shared pieces for the late-November 2026 landmark modules (Újbuda, Ferencváros and the Buda additions): a building
painted from its outline in one Field, its walls patterned by floor and by bay along the outline, its roof flat or
hipped; and the helpers to drop OSM's parts under a hand-built outline."""
import math

import numpy as np
import shapely

import landmarks as LM
from landmarks import Field
from landmarks_city import dist_in, grid_of


def fields(g, pad=1.0):
    """per 0.5 m cell over g: depth inside the outline (d, m), the distance along it to the nearest point (s, m)."""
    x0f, y0f, X, Y = grid_of(g, pad)
    pts = shapely.points(X.ravel(), Y.ravel())
    ring = g.exterior if g.geom_type == "Polygon" else shapely.union_all([p.exterior for p in g.geoms])
    rings = [ring] if ring.geom_type == "LinearRing" else list(getattr(ring, "geoms", [ring]))
    s = np.full(X.size, 0.0, np.float32)
    best = np.full(X.size, np.inf, np.float32)
    off = 0.0
    for r in rings:  # the arc length to the nearest point on the nearest ring, each ring after the last
        dd = shapely.distance(r, pts)
        ss = shapely.line_locate_point(shapely.LineString(r.coords), pts) + off
        m = dd < best
        best[m], s[m] = dd[m], ss[m]
        off += r.length + 50.0
    return x0f, y0f, X, Y, dict(d=dist_in(g, X, Y), s=s.reshape(X.shape).astype(np.float32),
                                X=X.astype(np.float32), Y=Y.astype(np.float32))


def painted(S, g, b0, top, fn, lower=-1.0, pad=1.0, extra=None):
    """a Field over g: fn(f, hw) -> ids, f the per-cell fields (d, s, X, Y and any extra) with a leading axis."""
    x0f, y0f, X, Y, f = fields(g, pad)
    if extra:
        f.update({k: v(X, Y).astype(np.float32) for k, v in extra.items()})

    def go(f_, wa):
        ff = {k: v[None] for k, v in f_.items()}
        hw = wa - b0
        o = np.where(hw >= lower, fn(ff, hw), 0)
        return np.broadcast_to(o, np.broadcast_shapes(np.shape(o), hw.shape)).astype(np.uint16)
    return S.add(Field(x0f, y0f, f, b0 + lower, b0 + top, go))


def styled(S, g, b0, E, wall, win, roof, *, floor=3.5, gf=None, sill=0.9, head=None, bay=3.6, winw=1.7,
           roof_kind="flat", slope=0.75, ridge=None, parapet=0.9, cap=None, base=None, shop=None, ribbon=False,
           band=None, band_every=None, pier=None, setback=None, top=None):
    """a building on outline g from b0: walls to E (m above b0), windows in rows of `floor` (the ground floor gf tall)
    and bays of `bay` along the outline (or ribbons), a flat roof behind a parapet or a hipped one (slope m per m in
    from the eaves, cut at `ridge` m over them), a base course up to gf in `base`, shop windows in `shop`."""
    gf = floor if gf is None else gf
    head = floor - 0.8 if head is None else head
    cap = wall if cap is None else cap
    rk = roof_kind

    def fn(f, hw):
        d, s = f["d"], f["s"]
        inside = d > 0
        edge = inside & (d < 0.8)
        fl = hw - gf
        hf = np.mod(fl, floor)
        in_row = (fl >= 0) & (hf >= sill) & (hf < head) & (hw < E - 0.6)
        if ribbon:
            opening = in_row
        else:
            bs = np.mod(s, bay)
            opening = in_row & (np.abs(bs - bay / 2) < winw / 2)
        w = np.where(opening, win, wall)
        if band is not None:
            w = np.where((fl >= 0) & (hf < 0.35), band, w)
        if pier is not None and not ribbon:
            w = np.where(in_row & (np.abs(np.mod(s, bay) - bay / 2) >= winw / 2), pier, w)
        if base is not None or shop is not None:
            gfl = hw < gf
            bs2 = np.abs(np.mod(s, bay) - bay / 2)
            sh = gfl & (hw >= 0.3) & (hw < gf - 0.6) & (bs2 < bay * 0.36) if shop is not None else np.zeros_like(gfl)
            w = np.where(gfl, np.where(sh, shop if shop is not None else win, base if base is not None else wall), w)
        o = np.where(edge & (hw < E), w, 0)
        if rk == "flat":
            o = np.where(inside & ~edge & (hw >= E - 0.6) & (hw < E), roof, o)
            o = np.where(edge & (hw >= E) & (hw < E + parapet), cap, o)
        else:
            rh = np.minimum(d * slope, ridge if ridge is not None else 1e9) + 0.5
            o = np.where(inside & (hw >= E - 0.6) & (hw < E + rh), roof, o)
        o = np.where(inside & (hw >= -0.6) & (hw < 0.0), base if base is not None else wall, o)
        return o
    hi = E + (parapet if rk == "flat" else (ridge if ridge is not None else 30.0) + 1.0)
    return painted(S, g, b0, top if top is not None else hi, fn)


def parts_inside(osm, outline, buffer=1.0):
    """the ids of OSM's buildings and building parts whose centroids lie in the outline."""
    gb = outline.buffer(buffer)
    return {oid for oid, kind, t, g in osm.areas
            if ("building" in t or "building:part" in t) and gb.contains(g.centroid)}


def largest(g):
    return max(g.geoms, key=lambda p: p.area) if g.geom_type == "MultiPolygon" else g


def turn_of(g):
    """the outline's long axis: the angle of its minimum rotated rectangle's long side."""
    r = g.minimum_rotated_rectangle
    c = np.array(r.exterior.coords)[:4]
    e = [c[(i + 1) % 4] - c[i] for i in range(2)]
    k = int(np.argmax([np.hypot(*v) for v in e]))
    return math.atan2(e[k][1], e[k][0])


def compass(bearing_deg):
    """a compass bearing (0 north, 90 east) as a unit vector on the grid (aoi.THETA)."""
    import aoi
    b, t = math.radians(bearing_deg), aoi.THETA
    e, n = math.sin(b), math.cos(b)
    return np.array([e * math.cos(t) + n * math.sin(t), e * math.sin(t) - n * math.cos(t)])
