"""Budapest's landmarks, built by hand at 0.5 m from reference photos and measured dimensions (docs/landmarks.md).

OSM places each one: footprints, part outlines and their heights, the pylons of the bridges. On that frame each
landmark is drawn as a list of solids (a tiny CSG): boxes, lathes (any n-gon or round profile turned about an axis:
drums, domes, spires, onion domes, columns), roofs, arches, slabs that follow a deck, capsules for limbs, and OSM
polygons extruded. A solid fills, carves, paints the voxels of given colours (windows on a wall) or fills only empty
voxels. Long thin things (chains, cables, hangers, truss members) are voxel lines instead.

voxelize.py drops the OSM buildings a landmark replaces (Plan), then calls build(ctx) once the ground and the buildings
are known; Scene.apply() draws the solids into each 0.5 m window as it is built.
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point

from style import CLASSIC, GLASS, LAMP, METAL, ROOF, SOLID, hex_rgb, parse_colour, parse_len

WINDOW = 21  # web/src/meta.ts MAT.WINDOW: dark glass, lit at night
F = 2        # voxels per metre (set by build)
TAU = 2 * math.pi


# ------------------------------------------------------------------------------------------------ toolkit
class Frame:
    """a local frame: origin (ox, oy) on the 1 m grid, oz in metres above the model base, +u at angle `ang` on the
    grid, +v at ang + 90 deg, +w up."""

    def __init__(self, ox, oy, oz=0.0, ang=0.0):
        self.ox, self.oy, self.oz, self.ang = float(ox), float(oy), float(oz), float(ang)
        self.ca, self.sa = math.cos(ang), math.sin(ang)

    def xy(self, u, v):
        return self.ox + u * self.ca - v * self.sa, self.oy + u * self.sa + v * self.ca

    def at(self, u=0.0, v=0.0, w=0.0, turn=0.0):
        x, y = self.xy(u, v)
        return Frame(x, y, self.oz + w, self.ang + turn)

    def uv(self, x, y):
        dx, dy = x - self.ox, y - self.oy
        return dx * self.ca + dy * self.sa, -dx * self.sa + dy * self.ca


def ngon(u, v, n, rot=0.0):
    """distance metric of a regular n-gon (inradius 1 at distance 1); n = 0: a circle."""
    if n == 0:
        return np.hypot(u, v)
    d = None
    for k in range(n):
        a = rot + TAU * k / n
        p = u * math.cos(a) + v * math.sin(a)
        d = p if d is None else np.maximum(d, p)
    return d


class Prim:
    """a solid. mode: fill | carve | paint (recolour voxels whose colour is in `targets`) | under (fill empty only).
    col: a palette id, or f(u, v, w) -> ids (0 leaves the voxel alone)."""

    def __init__(self, fr, col, box, mode="fill", targets=None):
        self.fr, self.col, self.mode = fr, col, mode
        self.targets = np.array(sorted(targets), np.uint16) if targets is not None else None
        u0, u1, v0, v1, w0, w1 = box
        xs, ys = zip(*(fr.xy(u, v) for u in (u0, u1) for v in (v0, v1)))
        self.bb = (int(math.floor(min(xs) * F)), int(math.ceil(max(xs) * F)) + 1,
                   int(math.floor(min(ys) * F)), int(math.ceil(max(ys) * F)) + 1,
                   int(math.floor((fr.oz + w0) * F)), int(math.ceil((fr.oz + w1) * F)) + 1)

    def inside(self, u, v, w, x, y):
        raise NotImplementedError


class Box(Prim):
    def __init__(self, fr, u0, u1, v0, v1, w0, w1, col, **kw):
        self.p = (u0, u1, v0, v1, w0, w1)
        super().__init__(fr, col, self.p, **kw)

    def inside(self, u, v, w, x, y):
        u0, u1, v0, v1, w0, w1 = self.p
        return (u >= u0) & (u < u1) & (v >= v0) & (v < v1) & (w >= w0) & (w < w1)


class TBox(Prim):
    """a box tapering from half-widths (hu0, hv0) at w0 to (hu1, hv1) at w1, centred on the frame."""

    def __init__(self, fr, hu0, hv0, hu1, hv1, w0, w1, col, **kw):
        self.p = (hu0, hv0, hu1, hv1, w0, w1)
        super().__init__(fr, col, (-max(hu0, hu1), max(hu0, hu1), -max(hv0, hv1), max(hv0, hv1), w0, w1), **kw)

    def inside(self, u, v, w, x, y):
        hu0, hv0, hu1, hv1, w0, w1 = self.p
        t = (w - w0) / (w1 - w0)
        return (w >= w0) & (w < w1) & (np.abs(u) <= hu0 + (hu1 - hu0) * t) & (np.abs(v) <= hv0 + (hv1 - hv0) * t)


class Lathe(Prim):
    """a profile turned about the frame's w axis: radius prof(t), t = 0..1 from w0 to w1, of a regular n-gon
    (n = 0: round); `inner` hollows it to a ring of that thickness."""

    def __init__(self, fr, w0, w1, prof, col, n=0, rot=0.0, inner=None, **kw):
        self.w0, self.w1, self.prof, self.n, self.rot, self.inner = w0, w1, prof, n, rot, inner
        r = max(float(np.max(prof(np.linspace(0, 1, 65)))), 0.01) / (math.cos(math.pi / n) if n else 1)
        super().__init__(fr, col, (-r, r, -r, r, w0, w1), **kw)

    def inside(self, u, v, w, x, y):
        t = (w - self.w0) / (self.w1 - self.w0)
        r = self.prof(np.clip(t, 0, 1))
        d = ngon(u, v, self.n, self.rot)
        m = (t >= 0) & (t < 1) & (d <= r)
        if self.inner is not None:
            m &= d > r - self.inner
        return m


def cyl(r):
    return lambda t: np.full_like(t, r, dtype=float)


def cone(r0, r1=0.0):
    return lambda t: r0 + (r1 - r0) * t


def dome(r, p=2.0, top=0.0):
    """elliptic (p = 2) or pointed (p < 2) dome profile, ending in radius `top` (for a lantern ring)."""
    return lambda t: np.maximum(r * np.clip(1 - t ** p, 0, 1) ** (1 / p), top)


def onion(r_neck, r_bulge, t_bulge=0.38):
    def f(t):
        a = np.clip(t / t_bulge, 0, 1)
        b = np.clip((t - t_bulge) / (1 - t_bulge), 0, 1)
        lower = r_neck + (r_bulge - r_neck) * np.sin(a * math.pi / 2)
        upper = r_bulge * (1 - b) ** 1.6 * (1 + 0.35 * np.sin(b * math.pi))
        return np.where(t < t_bulge, lower, upper)
    return f


class Roof(Prim):
    """a pitched roof over [u0, u1] x [v0, v1], ridge along u, rising h from w0; hip: the ends slope too."""

    def __init__(self, fr, u0, u1, v0, v1, w0, h, col, hip=False, **kw):
        self.p = (u0, u1, v0, v1, w0, h, hip)
        super().__init__(fr, col, (u0, u1, v0, v1, w0, w0 + h), **kw)

    def inside(self, u, v, w, x, y):
        u0, u1, v0, v1, w0, h, hip = self.p
        t = (w - w0) / h
        hv = (v1 - v0) / 2
        m = (t >= 0) & (t < 1) & (np.abs(v - (v0 + v1) / 2) <= hv * (1 - t)) & (u >= u0) & (u < u1)
        if hip:
            m &= np.abs(u - (u0 + u1) / 2) <= (u1 - u0) / 2 - hv * t
        return m


class Arch(Prim):
    """an arched opening through [u0, u1], centred at v = vc, half-width a, springing at ws: round or pointed."""

    def __init__(self, fr, u0, u1, vc, a, w0, ws, col=0, pointed=False, **kw):
        self.p = (u0, u1, vc, a, w0, ws, pointed)
        top = ws + (a * math.sqrt(3) if pointed else a)
        super().__init__(fr, col, (u0, u1, vc - a, vc + a, w0, top), **kw)

    def inside(self, u, v, w, x, y):
        u0, u1, vc, a, w0, ws, pointed = self.p
        dv = np.abs(v - vc)
        if pointed:
            head = (dv + a) ** 2 + (w - ws) ** 2 <= (2 * a) ** 2
        else:
            head = dv ** 2 + (w - ws) ** 2 <= a ** 2
        return (u >= u0) & (u < u1) & (dv <= a) & (w >= w0) & ((w <= ws) | head)


class Ellipsoid(Prim):
    def __init__(self, fr, ru, rv, rw, col, **kw):
        self.p = (ru, rv, rw)
        super().__init__(fr, col, (-ru, ru, -rv, rv, -rw, rw), **kw)

    def inside(self, u, v, w, x, y):
        ru, rv, rw = self.p
        return (u / ru) ** 2 + (v / rv) ** 2 + (w / rw) ** 2 <= 1


class Capsule(Prim):
    """a segment p0 -> p1 (local u, v, w) with radius r: limbs, struts, short bars."""

    def __init__(self, fr, p0, p1, r, col, **kw):
        self.a, self.b, self.r = np.array(p0, float), np.array(p1, float), r
        lo, hi = np.minimum(self.a, self.b) - r, np.maximum(self.a, self.b) + r
        super().__init__(fr, col, (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]), **kw)

    def inside(self, u, v, w, x, y):
        d = self.b - self.a
        L2 = max(float(d @ d), 1e-9)
        t = np.clip(((u - self.a[0]) * d[0] + (v - self.a[1]) * d[1] + (w - self.a[2]) * d[2]) / L2, 0, 1)
        return (u - self.a[0] - t * d[0]) ** 2 + (v - self.a[1] - t * d[1]) ** 2 + (w - self.a[2] - t * d[2]) ** 2 <= self.r ** 2


class Slab(Prim):
    """[u0, u1] x [v0, v1] between zf(u) + a and zf(u) + b: a deck, a girder or a railing that follows a road's
    profile zf (metres, frame-relative)."""

    def __init__(self, fr, u0, u1, v0, v1, zf, a, b, col, **kw):
        self.p = (u0, u1, v0, v1, a, b)
        self.zf = zf
        zs = zf(np.linspace(u0, u1, 64))
        super().__init__(fr, col, (u0, u1, v0, v1, float(zs.min()) + a, float(zs.max()) + b), **kw)

    def inside(self, u, v, w, x, y):
        u0, u1, v0, v1, a, b = self.p
        z = self.zf(u)
        return (u >= u0) & (u < u1) & (v >= v0) & (v < v1) & (w >= z + a) & (w < z + b)


class Poly(Prim):
    """an OSM polygon (1 m grid coordinates), extruded between z0 and z1 metres above the model base."""

    def __init__(self, poly, z0, z1, col, **kw):
        self.poly = poly
        shapely.prepare(poly)
        x0, y0, x1, y1 = poly.bounds
        super().__init__(Frame(0, 0, 0, 0), col, (x0, x1, y0, y1, z0, z1), **kw)
        self.z0, self.z1 = z0, z1

    def inside(self, u, v, w, x, y):
        X, Y = np.broadcast_arrays(x, y)
        m = shapely.contains_xy(self.poly, X, Y)
        return m[None] & (w >= self.z0) & (w < self.z1)


class Field(Prim):
    """a solid drawn from 2D fields sampled on the 0.5 m grid (distances to rings, arc length, angle...) and height:
    fn(fields, w) -> palette ids (0 = empty), with fields cut to the window and w in metres above the model base.
    For shapes that follow an outline rather than a frame: a stadium bowl, a facade that leans along a curve."""

    def __init__(self, x0f, y0f, fields, z0, z1, fn, **kw):
        self.x0f, self.y0f, self.fields, self.fn = x0f, y0f, fields, fn
        ny, nx = next(iter(fields.values())).shape
        super().__init__(Frame(0, 0, 0, 0), self._col, (x0f / F, (x0f + nx - 1) / F, y0f / F, (y0f + ny - 1) / F, z0, z1), **kw)
        self._ids = None

    def inside(self, u, v, w, x, y):
        ix0, iy0 = int(round(float(np.min(x)) * F - 0.5)) - self.x0f, int(round(float(np.min(y)) * F - 0.5)) - self.y0f
        nx, ny = np.shape(x)[-1], np.shape(y)[0]
        fd = {k: a[iy0:iy0 + ny, ix0:ix0 + nx] for k, a in self.fields.items()}
        self._ids = np.asarray(self.fn(fd, w), np.uint16)
        return self._ids != 0

    def _col(self, u, v, w):
        return self._ids


class Scene:
    def __init__(self):
        self.prims, self.points = [], []
        self.clear = []  # (x, y, r): no tree stands within r m (plus part of its crown) of a monument
        self.bb = np.zeros((0, 6), np.int64)

    def add(self, p):
        self.prims.append(p)
        return p

    def line(self, fr, p0, p1, col, thick=0, step=0.2):
        """voxels along a segment (local metres); thick 1: 2 x 2 voxels across."""
        a, b = np.array(p0, float), np.array(p1, float)
        n = max(2, int(np.linalg.norm(b - a) / step) + 1)
        t = np.linspace(0, 1, n)[:, None]
        p = a + (b - a) * t
        x, y = fr.xy(p[:, 0], p[:, 1])
        X, Y, Z = np.floor(np.asarray(x) * F), np.floor(np.asarray(y) * F), np.floor((fr.oz + p[:, 2]) * F)
        pts = np.stack([X, Y, Z], 1).astype(np.int64)
        if thick:
            pts = np.concatenate([pts + d for d in ([0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0], [1, 0, 1], [0, 1, 1])])
        pts = np.unique(pts, axis=0)
        self.points.extend((int(x_), int(y_), int(z_), int(col)) for x_, y_, z_ in pts)

    def polyline(self, fr, pts, col, thick=0):
        for a, b in zip(pts[:-1], pts[1:]):
            self.line(fr, a, b, col, thick)

    def finish(self):
        self.bb = np.array([p.bb for p in self.prims], np.int64).reshape(-1, 6)

    def zmax(self, r0, r1, c0, c1):
        if not len(self.bb):
            return 0
        b = self.bb
        k = (b[:, 1] > c0) & (b[:, 0] < c1) & (b[:, 3] > r0) & (b[:, 2] < r1)
        return int(b[k, 5].max()) if k.any() else 0

    def apply(self, vol, r0, r1, c0, c1):
        if not len(self.bb):
            return
        H = vol.shape[0]
        b = self.bb
        for k in np.nonzero((b[:, 1] > c0) & (b[:, 0] < c1) & (b[:, 3] > r0) & (b[:, 2] < r1) & (b[:, 4] < H))[0]:
            p = self.prims[k]
            x0, x1, y0, y1, z0, z1 = p.bb
            x0, x1, y0, y1, z0, z1 = max(x0, c0), min(x1, c1), max(y0, r0), min(y1, r1), max(z0, 0), min(z1, H)
            if x0 >= x1 or y0 >= y1 or z0 >= z1:
                continue
            X = ((np.arange(x0, x1) + 0.5) / F)[None, :]
            Y = ((np.arange(y0, y1) + 0.5) / F)[:, None]
            fr = p.fr
            dx, dy = X - fr.ox, Y - fr.oy
            u = (dx * fr.ca + dy * fr.sa)[None]
            v = (-dx * fr.sa + dy * fr.ca)[None]
            w = ((np.arange(z0, z1) + 0.5) / F - fr.oz)[:, None, None]
            m = np.broadcast_to(p.inside(u, v, w, X, Y), (z1 - z0, y1 - y0, x1 - x0))
            if not m.any():
                continue
            sub = vol[z0:z1, y0 - r0:y1 - r0, x0 - c0:x1 - c0]
            if p.mode == "carve":
                sub[m] = 0
                continue
            if p.mode == "paint":
                m = m & np.isin(sub, p.targets)
            elif p.mode == "under":
                m = m & (sub == 0)
            if callable(p.col):
                col = np.broadcast_to(p.col(u, v, w), m.shape)
                m = m & (col != 0)
                sub[m] = col[m]
            else:
                sub[m] = p.col


# ------------------------------------------------------------------------------------------------ helpers
def rect_of(g):
    """minimum rotated rectangle -> centre (x, y), long side, short side, angle of the long side."""
    r = g.minimum_rotated_rectangle
    c = np.array(r.exterior.coords)[:4]
    e = [np.linalg.norm(c[(k + 1) % 4] - c[k]) for k in range(4)]
    k = int(np.argmax(e[:2]))
    d = c[(k + 1) % 4] - c[k]
    cen = c.mean(0)
    return float(cen[0]), float(cen[1]), float(e[k]), float(e[1 - k]), math.atan2(d[1], d[0])


def tags_h(t):
    H = parse_len(t.get("height")) or 0.0
    minh = parse_len(t.get("min_height")) or 0.0
    rh = parse_len(t.get("roof:height")) or 0.0
    return minh, H - rh, H


def grid_angle(bearing_deg, theta):
    """a compass bearing (0 north, 90 east) as an angle on the grid (aoi.py: +x is EOV (cos t, sin t))."""
    b = math.radians(bearing_deg)
    e, n = math.sin(b), math.cos(b)
    gx = e * math.cos(theta) + n * math.sin(theta)
    gy = e * math.sin(theta) - n * math.cos(theta)
    return math.atan2(gy, gx)


def zsolnay(P, colours, period=1.5, slope=1.0, kind="chevron"):
    """Zsolnay glazed tiles on a roof, as f(u, v, w) on a lattice of diamonds `period` metres across:
    chevron -- zigzag bands, one colour per band (the market hall);
    diamond -- each diamond a colour, outlined in the first one."""
    ids = np.array([P(c, ROOF) for c in colours], np.uint16)

    def f(u, v, w):
        a = np.floor((u + slope * w) / period).astype(np.int64)
        b = np.floor((u - slope * w) / period).astype(np.int64)
        if kind == "chevron":
            return ids[np.mod(a - b, len(ids))]
        fa, fb = np.mod((u + slope * w) / period, 1), np.mod((u - slope * w) / period, 1)
        edge = (fa < 0.22) | (fb < 0.22)
        return np.where(edge, ids[0], ids[1 + np.mod(a + 2 * b, len(ids) - 1)]).astype(np.uint16)
    return f


# ------------------------------------------------------------------------------------------------ plan
PARLIAMENT, BASILICA, MATTHIAS, PALACE = 3199085, 20593057, 37135081, 6486918
BASTION, MARKET, SYNAGOGUE, MILLENNIUM = 17948384, 24323859, 223530620, 6932527
CHAIN, LIBERTY_BR, ELISABETH = "Széchenyi lánchíd", "Szabadság híd", "Erzsébet híd"
PUSKAS, PUSKAS_LOW = 8766354, 10981440  # the Puskás Aréna's grandstand ring and its lower tier
MARGIT, PETOFI = "Margit híd", "Petőfi híd"
MARGIT_PIERS, MARGIT_ISLAND = (197175603, 197175602, 197175600, 197175601), 197175887  # Buda to Pest; the bend
PETOFI_PIERS = (675676766, 675676767)


class Plan:
    """what the hand-built landmarks replace in OSM, decided before voxelize.py fuses the buildings."""

    def __init__(self, osm):
        self.osm = osm
        self.area = {(a[0]): a for a in osm.areas}
        self.names = ["Parliament", "Chain Bridge", "Liberty Bridge", "Elisabeth Bridge", "Fisherman's Bastion",
                      "Matthias Church", "St Stephen's Basilica", "Buda Castle dome", "Liberty Statue",
                      "Heroes' Square", "Great Market Hall", "Dohány Street Synagogue", "Puskás Aréna",
                      "Margaret Bridge", "Petőfi Bridge"]
        import landmarks_city  # the second batch, away from the river front
        import landmarks_more  # the third: Gellért, BME K, the National Museum, the boats, the Kálvin tér skybridge
        import landmarks_kossuth  # the square in front of the Parliament
        import landmarks_hilton  # the Hilton on Castle Hill
        import landmarks_citadella  # the fortress on Gellért Hill
        import landmarks_erkel  # the Erkel Theatre
        import landmarks_rakoczi  # the Rákóczi tér market hall
        import landmarks_blaha  # Blaha Lujza tér: the Corvin Palace and the Europeum
        import landmarks_sidequest  # the bar that made the map, inside and out
        import landmarks_westend  # the WestEnd City Center by Nyugati
        self.names += landmarks_city.NAMES + landmarks_more.NAMES + landmarks_kossuth.NAMES + landmarks_hilton.NAMES
        self.names += landmarks_citadella.NAMES + landmarks_erkel.NAMES + landmarks_rakoczi.NAMES + landmarks_blaha.NAMES
        self.names += landmarks_sidequest.NAMES + landmarks_westend.NAMES
        self.bridges = {CHAIN, LIBERTY_BR, ELISABETH, MARGIT, PETOFI}
        self.classic = {PARLIAMENT, BASILICA, MATTHIAS, PALACE}
        drop = {237397585, 1503074602, 237397586,                       # the Parliament's spire, lantern, dome
                *range(1503074697, 1503074713),                          # and the 16 buttresses round its drum
                197110387, 197110388, 197315955, 197315956,              # the Chain and Liberty bridges' pylons
                BASTION, MARKET, 223530621, 223530622,                    # bastion, market hall, synagogue towers
                *matthias_parts(osm),                                    # Matthias Church: all its parts
                443384185, 1504216917, 1504216920, 1504216921,           # the Basilica's dome, lantern, tower caps
                MILLENNIUM, PUSKAS, PUSKAS_LOW}
        drop |= landmarks_city.DROP | landmarks_more.drop_ids(osm) | landmarks_hilton.drop_ids(osm)
        drop |= landmarks_citadella.DROP | landmarks_erkel.DROP | landmarks_rakoczi.drop_ids(osm) | landmarks_blaha.DROP
        drop |= landmarks_westend.DROP
        self.ground_keep = landmarks_hilton.ground_keep(osm)  # (outline, height) the ground model still sees
        # outlines that still stand for green, trees, lamps, furniture and the ground model (voxelize.py's `held`)
        self.ground_cover = [self.area[i][3] for i in landmarks_rakoczi.KEEP_GROUND if i in self.area]
        # the baths' and the Opera's own building parts inside the outlines they replace
        for big in (landmarks_city.SZECHENYI, landmarks_city.OPERA):
            if big in self.area:
                hg = self.area[big][3].buffer(1)
                for oid, kind, t, g in osm.areas:
                    if "building:part" in t and hg.contains(g.centroid) and oid not in landmarks_city.KEEP_PARTS:
                        drop.add(oid)
        # the Parliament's turrets: its small parts with pyramidal roofs become Gothic spires
        self.parl_towers = []
        if PARLIAMENT in self.area:
            hg = self.area[PARLIAMENT][3].buffer(2)
            for oid, kind, t, g in osm.areas:
                if "building:part" in t and t.get("roof:shape") == "pyramidal" and g.area < 90 and hg.contains(g.centroid) \
                        and oid not in drop:
                    self.parl_towers.append((oid, t, g))
                    drop.add(oid)
        # the Archangel Gabriel's column on Heroes' Square
        self.gabriel = None
        if MILLENNIUM in self.area:
            mg = self.area[MILLENNIUM][3]
            for oid, kind, t, g in osm.areas:
                if t.get("historic") in ("monument", "memorial") and (parse_len(t.get("height")) or 0) > 25 and g.distance(mg) < 80:
                    self.gabriel = (oid, t, g)
                    drop.add(oid)
        self.drop = {str(i) for i in drop}


# ------------------------------------------------------------------------------------------------ build
def build(ctx):
    global F
    F = ctx["F"]
    S = Scene()
    pal, note = ctx["pal"], ctx["note"]

    def P(c, mat=CLASSIC):
        return pal(hex_rgb(c), mat)
    ctx = dict(ctx, P=P, area={a[0]: a for a in ctx["osm"].areas}, WLr=ctx["WL"] - ctx["BASE"])
    ctx["ground_m"] = lambda x, y: ctx["gfine_at"](x, y) / F
    plan = ctx["plan"]
    import landmarks_citadella
    import landmarks_city
    import landmarks_hilton
    import landmarks_erkel
    import landmarks_blaha
    import landmarks_kossuth
    import landmarks_more
    import landmarks_rakoczi
    import landmarks_sidequest
    import landmarks_westend
    import landmarks_statues  # last: it looks at what the others drew
    for name, fn in (("Parliament", parliament), ("Chain Bridge", chain_bridge), ("Liberty Bridge", liberty_bridge),
                     ("Elisabeth Bridge", elisabeth_bridge), ("Fisherman's Bastion", bastion),
                     ("Matthias Church", matthias), ("St Stephen's Basilica", basilica), ("Buda Castle dome", castle_dome),
                     ("Liberty Statue", liberty_statue), ("Heroes' Square", heroes_square),
                     ("Great Market Hall", market_hall), ("Dohány Street Synagogue", synagogue),
                     ("Puskás Aréna", puskas_arena), ("Margaret Bridge", margaret_bridge), ("Petőfi Bridge", petofi_bridge),
                     *landmarks_city.BUILDERS, *landmarks_more.BUILDERS, *landmarks_kossuth.BUILDERS,
                     *landmarks_hilton.BUILDERS, *landmarks_citadella.BUILDERS, *landmarks_erkel.BUILDERS,
                     *landmarks_rakoczi.BUILDERS, *landmarks_blaha.BUILDERS, *landmarks_sidequest.BUILDERS,
                     *landmarks_westend.BUILDERS, *landmarks_statues.BUILDERS):
        n0, p0 = len(S.prims), len(S.points)
        try:
            fn(S, ctx, plan)
        except KeyError as e:  # an OSM id the build depends on is gone: leave the landmark out, say so
            note(f"  landmark {name}: skipped, OSM feature {e} missing")
            continue
        note(f"  landmark {name}: {len(S.prims) - n0} solids, {len(S.points) - p0} line voxels")
    S.finish()
    return S


def feat_base(ctx, fid):
    f = ctx["feats"].get(str(fid))
    return f["base"] if f is not None else ctx["ground_m"](*ctx["area"][fid][3].centroid.coords[0])


def ring_segments(poly, min_len=2.0):
    """the edges of a polygon's rings -> (p, q, outward normal) in grid coordinates."""
    out = []
    polys = getattr(poly, "geoms", [poly])
    for pg in polys:
        for ring in [pg.exterior, *pg.interiors]:
            c = np.array(ring.coords)
            for a, b in zip(c[:-1], c[1:]):
                d = b - a
                L = float(np.hypot(*d))
                if L < min_len:
                    continue
                n = np.array([d[1], -d[0]]) / L
                mid = (a + b) / 2
                if pg.contains(Point(*(mid + n * 0.6))):
                    n = -n
                out.append((a, b, n))
    return out


def seg_frame(a, b, n, oz):
    """frame on a wall: u along it from a, v into the building, w up."""
    d = (b - a) / np.hypot(*(b - a))
    ang = math.atan2(d[1], d[0])
    fr = Frame(a[0], a[1], oz, ang)
    if (np.array([-math.sin(ang), math.cos(ang)]) @ -n) < 0:  # make +v point inwards
        fr = Frame(b[0], b[1], oz, ang + math.pi)
    return fr


def gothic_windows(bay=4.2, width=2.0, storey=4.5, sill=1.0, head=3.6):
    """a wall pattern: pointed windows in bays; f(u, w) -> True where glass."""
    def f(u, w):
        x = np.mod(u, bay) - bay / 2
        z = np.mod(w, storey)
        hw = width / 2
        tip = np.clip((z - (head - hw * 1.2)) / (hw * 1.2), 0, 1)
        return (np.abs(x) <= hw * (1 - tip)) & (z >= sill) & (z < head)
    return f


def spire(S, fr, w0, w1, r0, col, n=8, finial=None, rot=0.0):
    S.add(Lathe(fr, w0, w1, lambda t: r0 * (1 - t) ** 1.08 + 0.12, col, n=n, rot=rot))
    if finial is not None:
        S.add(Lathe(fr, w1 - 0.2, w1 + 1.0, cyl(0.22), finial))


def pinnacle(S, fr, w0, h, r, col, finial=None):
    S.add(Lathe(fr, w0, w0 + h * 0.45, cyl(r), col, n=4, rot=math.pi / 4))
    S.add(Lathe(fr, w0 + h * 0.45, w0 + h, cone(r * 1.05, 0.08), col, n=4, rot=math.pi / 4))
    if finial is not None:
        S.add(Box(fr, -0.25, 0.25, -0.25, 0.25, w0 + h, w0 + h + 0.5, finial))


def gothic_tower(S, ctx, g, b0, minh, E, H, wall, roof, win, gold, roof_col=None):
    """a turret from its OSM outline: the shaft, belfry windows, four corner pinnacles and an octagonal spire."""
    cx, cy, L1, L2, ang = rect_of(g)
    half = min(L1, L2) / 2
    fr = Frame(cx, cy, b0, ang)
    S.add(Poly(g, b0 + minh, b0 + E, wall))
    for k in range(4):
        f2 = fr.at(turn=k * math.pi / 2)
        S.add(Arch(f2, half - 0.45, half + 0.1, 0, min(0.75, half * 0.3), E - 6.5, E - 2.6, win, pointed=True,
                   mode="paint", targets=[wall]))
    S.add(TBox(fr, half + 0.35, half + 0.35, half + 0.35, half + 0.35, E - 0.6, E, wall))
    for su in (-1, 1):
        for sv in (-1, 1):
            pinnacle(S, fr.at(su * (half - 0.25), sv * (half - 0.25)), E, min(6.0, 0.5 * (H - E)), 0.55, wall)
    spire(S, fr, E, H, half * 0.82, roof_col or roof, finial=gold, rot=math.pi / 8)


# ------------------------------------------------------------------------------------------------ the Parliament
# the parts whose roofs are green copper in aerial photos (the chambers' great roofs, the end pavilions, the strips
# along the courts); the rest are red-brown tiles. The two needle towers on the river front flank the dome.
PARL_COPPER = {237599084, 237599085, 1308786810, 1308786814, 1503074603, 1503074604, 1503074605, 1503074610,
               1503074614, 1503074623, 1503074627, 1503074628, 1503074629, 1503074630, 1503074631, 1503074632,
               1503074634, 1503074635, 1503074636, 1503074637, 1503074639, 1503074640, 1503074641, 1503074645,
               1503074646, 1503074647, 1503074649, 1503074650, 1503074657, 1503074658, 1503074677, 1503074680,
               1503074688, 1503074691, 1503074696, 1503074706, 1503074707, 1503074618, 1503074619, 1503074620}
PARL_SPIRES = {237520075, 237520079}


def parl_windows(u, z, bay=4.2):
    """the Parliament's storeys, z metres above the part's foot: round-headed windows on the ground floor, tall
    pointed ones on the main floor, shorter pointed ones above, small square ones in the attic."""
    x = np.abs(np.mod(u, bay) - bay / 2)

    def pointed(hw, sill, spring):
        a = hw
        head = (x + a) ** 2 + (z - spring) ** 2 <= (2 * a) ** 2
        return (x <= hw) & (z >= sill) & ((z < spring) | head)

    def round_(hw, sill, spring):
        return (x <= hw) & (z >= sill) & ((z < spring) | (x ** 2 + (z - spring) ** 2 <= hw ** 2))
    return (round_(0.8, 1.4, 4.6) | pointed(1.1, 8.3, 12.4) | pointed(0.9, 16.2, 19.4)
            | ((x <= 0.6) & (z >= 22.6) & (z < 24.6)))


def needle(S, g, b0, minh, wall, rib, win, gold):
    """one of the two needle towers on the river front: a square shaft with tall belfry lancets and corner
    pinnacles, an octagonal lantern, and a crocketed stone needle to 72 m."""
    cx, cy, L1, L2, ang = rect_of(g)
    half = min(L1, L2) / 2
    fr = Frame(cx, cy, b0, ang)
    S.add(Poly(g, b0 + minh, b0 + 52.0, wall))
    for k in range(4):
        f2 = fr.at(turn=k * math.pi / 2)
        S.add(Arch(f2, half - 0.45, half + 0.1, 0, min(0.8, half * 0.3), 44.5, 49.5, win, pointed=True,
                   mode="paint", targets=[wall]))
    S.add(TBox(fr, half + 0.3, half + 0.3, half + 0.3, half + 0.3, 51.4, 52.0, rib))
    for su in (-1, 1):
        for sv in (-1, 1):
            pinnacle(S, fr.at(su * (half - 0.3), sv * (half - 0.3)), 52.0, 7.5, 0.6, wall, finial=gold)
    r8 = half * 0.72
    S.add(Lathe(fr, 52.0, 57.5, cyl(r8), wall, n=8, rot=math.pi / 8))
    for k in range(8):
        S.add(Arch(fr.at(turn=k * TAU / 8), r8 - 0.5, r8 + 0.1, 0, 0.45, 53.0, 56.0, win, pointed=True,
                   mode="paint", targets=[wall]))
    spire(S, fr, 57.5, 72.0, r8 * 0.95, wall, n=8, finial=gold, rot=math.pi / 8)
    for w_ in (61.0, 65.0, 68.5):
        r_ = r8 * 0.95 * (1 - (w_ - 57.5) / 14.5) ** 1.08 + 0.45
        S.add(Lathe(fr, w_, w_ + 0.5, cyl(r_), rib, n=8, rot=math.pi / 8))


def parliament(S, ctx, plan):
    """Országház (Imre Steindl, 1885-1904): 268 x 123 m, the dome 96 m. OSM maps it in 132 parts; the dome, its
    16 buttresses and the turrets are drawn here, and every remaining part gets Gothic bays, pinnacles and gables."""
    P, area = ctx["P"], ctx["area"]
    wall = P("#ece4cf")
    rib = P("#f2ecdc")
    red = P("#a8584a", ROOF)
    dark = P("#5a4a46", ROOF)
    win = P("#3a3b40", WINDOW)
    gold = P("#d4ad55", METAL)
    b0 = feat_base(ctx, PARLIAMENT)
    host = area[PARLIAMENT][3]
    hx, hy, _, _, hang = rect_of(host)
    dg = area[237397586][3]
    cx, cy = dg.centroid.x, dg.centroid.y
    R = 12.6
    fr = Frame(cx, cy, b0, hang)
    rot = math.pi / 16
    # drum, its gallery and windows
    S.add(Lathe(fr, 26, 55, cyl(R), wall, n=16, rot=rot))
    S.add(Lathe(fr, 54.5, 55.5, cyl(R + 0.5), rib, n=16, rot=rot))
    for k in range(16):
        a = rot + TAU * k / 16
        fk = fr.at(turn=a)
        S.add(Arch(fk, R - 0.6, R + 0.1, 0, 1.0, 42.5, 50.0, win, pointed=True, mode="paint", targets=[wall]))
        S.add(Arch(fk, R - 0.6, R + 0.1, 0, 0.9, 33.5, 38.0, win, mode="paint", targets=[wall]))
        c = a + math.pi / 16  # a corner of the drum
        fc = fr.at(turn=c)
        pinnacle(S, fc.at(R / math.cos(math.pi / 16) + 0.2), 55, 6.5, 0.6, rib, finial=gold)
        # the buttress against the drum, stepped, with a pinnacle on it
        S.add(Box(fc, R - 0.5, R + 4.4, -0.95, 0.95, 20, 44.2, wall))
        S.add(Box(fc, R - 0.5, R + 2.0, -0.8, 0.8, 44.2, 49.0, wall))
        pinnacle(S, fc.at(R + 3.2), 44.2, 8.0, 0.8, wall, finial=gold)
        S.add(Arch(fc.at(turn=math.pi / 2), -1.0, 1.0, R + 2.2, 1.0, 22, 30, win, pointed=True, mode="paint", targets=[wall]))
    # the dome: 16 red panels between pale ribs, a ring of dormers, then the lantern and the spire
    hw = 0.42

    def dome_col(u, v, w):
        th = np.arctan2(v, u) - rot - math.pi / 16
        ph = np.mod(th, TAU / 16)
        r = np.hypot(u, v)
        ribm = np.minimum(ph, TAU / 16 - ph) * r < hw
        return np.where(ribm | (w < 56.3), rib, red).astype(np.uint16)
    S.add(Lathe(fr, 55, 75.5, dome(R - 0.2, p=1.75, top=3.3), dome_col, n=16, rot=rot))
    for k in range(16):
        fk = fr.at(turn=rot + TAU * k / 16)
        S.add(Box(fk, R - 2.6, R - 0.9, -0.55, 0.55, 58.5, 61.0, rib))
        S.add(Box(fk, R - 1.0, R - 0.6, -0.35, 0.35, 59.0, 60.5, win))
    S.add(Lathe(fr, 75, 80, cyl(3.3), rib, n=16, rot=rot))
    for k in range(8):
        fk = fr.at(turn=TAU * k / 8)
        S.add(Box(fk, 2.6, 3.4, -0.45, 0.45, 76, 79, win))
        pinnacle(S, fk.at(3.6, 0, 0, 0), 79.5, 3.5, 0.35, rib)
    S.add(Lathe(fr, 80, 81.2, cone(3.6, 2.6), dark, n=16, rot=rot))
    spire(S, fr, 81.2, 95.4, 2.4, dark, n=8, finial=gold)
    for w_ in (84.0, 88.5):
        S.add(Lathe(fr, w_, w_ + 0.5, lambda t, w_=w_: 2.4 * (1 - (w_ - 81.2) / 14.2) ** 1.08 + 0.55, rib, n=8))
    # turrets
    wall_ids = {wall}
    for f in ctx["feats"].values():
        if not f.get("geom") or not host.buffer(2).contains(f["geom"].centroid):
            continue
        wall_ids.add(f["wall"])
    roof_ids = {f["roof"] for f in ctx["feats"].values() if f.get("geom") is not None and host.buffer(2).contains(f["geom"].centroid)}
    ctx["parl_walls"] = sorted(wall_ids)
    tile, copper = P("#9c5547", ROOF), P("#6b9886", ROOF)
    S.add(Poly(host.buffer(3), b0 - 2, b0 + 60, tile, mode="paint", targets=roof_ids - {wall, rib}))
    for oid in PARL_COPPER:
        f = ctx["feats"].get(str(oid))
        if f and f.get("geom") is not None:
            S.add(Poly(f["geom"].buffer(0.6), b0 + f["E"] - 0.6, b0 + f["H"] + 0.6, copper, mode="paint",
                       targets=(roof_ids - {wall, rib}) | {tile}))
    for oid, t, g in plan.parl_towers:
        minh, E, H = tags_h(t)
        if E <= minh:
            E = minh + 4
        if oid in PARL_SPIRES:
            needle(S, g, b0, minh, wall, rib, win, gold)
            continue
        roof_c = copper if oid in PARL_COPPER else tile
        gothic_tower(S, ctx, g, b0, minh, E, H, wall, roof_c, win, gold)
    # every remaining part: buttresses with pinnacles every bay, pointed windows between them, gables on the eaves
    nb = 0
    parts = [f for f in ctx["feats"].values() if f.get("geom") is not None and host.buffer(2).contains(f["geom"].centroid)]
    hfr = Frame(hx, hy, 0, hang)
    river = np.array([-math.sin(hang), math.cos(hang)])  # +v of the host's rectangle: towards the Danube
    shade = P("#8a8478", CLASSIC)
    for f in parts:
        if f["H"] < 9 or f["area"] < 60:
            continue
        E = b0 + f["E"]
        w_lo = b0 + f["minh"]
        for a, b, n in ring_segments(f["geom"], 3.0):
            fr2 = seg_frame(a, b, n, 0)
            L = float(np.hypot(*(b - a)))
            mid = (a + b) / 2
            front = f["minh"] < 1 and float(np.dot(n, river)) > 0.9 and hfr.uv(*mid)[1] > 44 and L > 8
            S.add(Box(fr2, 0, L, -0.05, 0.55, w_lo, E - 0.8,
                      lambda u, v, w, w_lo=w_lo, front=front: np.where(
                          parl_windows(u, w - w_lo) & ~(front & (w - w_lo < 7.0)), win, 0).astype(np.uint16),
                      mode="paint", targets=wall_ids))
            if front:  # the riverside arcade: pointed arches 2.4 m deep along the ground floor
                for t_ in np.arange(2.1, L - 1.0, 4.2):
                    fa = fr2.at(t_, 0, 0, math.pi / 2)
                    S.add(Arch(fa, -0.1, 2.4, 0, 1.45, b0, b0 + 4.4, mode="carve"))
                    S.add(Arch(fa, 2.4, 2.9, 0, 1.45, b0, b0 + 4.4, shade, mode="paint", targets=wall_ids))
            for k, t_ in enumerate(np.arange(0.0, L + 0.01, 4.2)):
                if t_ < 0.4 or t_ > L - 0.4:
                    continue
                S.add(Box(fr2, t_ - 0.3, t_ + 0.3, -0.5, 0.0, w_lo, E - 0.4, wall, mode="under"))
                pinnacle(S, fr2.at(t_, -0.25), E - 0.5, 3.6, 0.32, rib, finial=None)
                if k % 2 == 1 and t_ + 2.1 < L - 0.5:
                    S.add(Roof(fr2.at(t_ + 2.1, 0, 0, math.pi / 2), -0.4, 2.2, -1.5, 1.5, E - 0.4, 2.8, wall))
                nb += 1
    ctx["note"](f"    Parliament: {nb} bays, {len(plan.parl_towers)} turrets")


# ------------------------------------------------------------------------------------------------ bridges
def bridge_poly(ctx, name):
    for oid, kind, t, g in ctx["osm"].areas:
        if t.get("man_made") == "bridge" and t.get("name") == name:
            return g
    raise KeyError(name)


def lane_marks(u, av, lines, w=0.26):
    """lane markings on a deck: lines = [(|v|, 'solid' | 'dash')], 3 m dashes every 9 m."""
    m = np.zeros(np.broadcast(u, av).shape, bool)
    for pos, kind in lines:
        on = np.abs(av - pos) < w
        if kind == "dash":
            on &= np.mod(u, 9.0) < 3.0
        m |= on
    return m


def held_ends(ctx, fr, s0, s1, poly):
    """at which ends OSM carries the road on as a bridge (a viaduct past the outline): there the deck stays up."""
    out = []
    for u in (s0, s1):
        p = Point(*fr.xy(u, 0))
        near_ = [ln for oid, t, ln in ctx["osm"].lines if t.get("bridge") not in (None, "no") and t.get("highway")
                 and ln.distance(p) < 10 and not poly.buffer(3).contains(ln)]
        out.append(bool(near_))
    return tuple(out)


def deck_fn(ctx, fr, s0, s1, lift=1.2, lo=5.0, hi=16.0, hold=(False, False)):
    """the deck's top (metres above the model base) along the bridge: from bridgehead to bridgehead, a gentle rise;
    an end where a viaduct carries on stays at the river crossing's height."""
    WLr = ctx["WLr"]
    gm = ctx["ground_m"]  # the street beyond each end (a lower quay or a tunnel mouth beside the bridgehead doesn't count)
    za = float(np.clip(max(gm(*fr.xy(s0 - 3, 0)), gm(*fr.xy(s0 - 10, 0))), WLr + lo, WLr + hi))
    zb = float(np.clip(max(gm(*fr.xy(s1 + 3, 0)), gm(*fr.xy(s1 + 10, 0))), WLr + lo, WLr + hi))
    if hold[0]:
        za = WLr + 12.0
    if hold[1]:
        zb = WLr + 12.0

    def zf(u):
        t = np.clip((np.asarray(u, float) - s0) / (s1 - s0), 0, 1)
        return za + (zb - za) * t + lift * 4 * t * (1 - t)
    return zf


def axis_extent(fr, poly):
    c = np.array(poly.exterior.coords if poly.geom_type == "Polygon" else poly.convex_hull.exterior.coords)
    u, _ = fr.uv(c[:, 0], c[:, 1])
    return float(u.min()), float(u.max())


def cutwater_pier(S, fr, hu, hv, w0, w1, col):
    """a river pier: a block with pointed ends upstream and downstream (along v)."""
    S.add(Box(fr, -hu, hu, -hv, hv, w0, w1, col))
    for sv in (-1, 1):
        S.add(Lathe(fr.at(0, sv * hv), w0, w1, cyl(hu / math.sqrt(2)), col, n=4, rot=math.pi / 4))


def chain_geom(ctx):
    area = ctx["area"]
    p1 = np.array(area[197110387][3].centroid.coords[0])
    p2 = np.array(area[197110388][3].centroid.coords[0])
    if p1[0] > p2[0]:
        p1, p2 = p2, p1
    c, d = (p1 + p2) / 2, p2 - p1
    half = float(np.hypot(*d)) / 2
    fr = Frame(c[0], c[1], 0, math.atan2(d[1], d[0]))
    s0, s1 = axis_extent(fr, bridge_poly(ctx, CHAIN))
    A = half + 88.7  # where the chains are anchored
    # the deck runs to the outline's ends (some 35-40 m past the anchorages): the ways on the outline aren't painted,
    # and a deck cut short of it left a strip of bare paving between the bridge and the squares' carriageways
    s0, s1 = max(s0, -A - 45), min(s1, A + 45)
    return dict(fr=fr, s0=s0, s1=s1, zf=deck_fn(ctx, fr, s0, s1, lift=1.3, hold=held_ends(ctx, fr, s0, s1, bridge_poly(ctx, CHAIN))), half=half, A=A, hw=7.4, under=2.1)


def liberty_geom(ctx):
    area = ctx["area"]
    p1 = np.array(area[197315956][3].centroid.coords[0])
    p2 = np.array(area[197315955][3].centroid.coords[0])
    if p1[0] > p2[0]:
        p1, p2 = p2, p1
    c, d = (p1 + p2) / 2, p2 - p1
    half = float(np.hypot(*d)) / 2
    fr = Frame(c[0], c[1], 0, math.atan2(d[1], d[0]))
    A = half + 79.0
    s0, s1 = axis_extent(fr, bridge_poly(ctx, LIBERTY_BR))
    s0, s1 = max(s0, -A - 25), min(s1, A + 25)
    return dict(fr=fr, s0=s0, s1=s1, zf=deck_fn(ctx, fr, s0, s1, lift=1.0, hold=held_ends(ctx, fr, s0, s1, bridge_poly(ctx, LIBERTY_BR))), half=half, A=A, hw=10.0, under=2.0)


def elisabeth_geom(ctx):
    poly = bridge_poly(ctx, ELISABETH)
    cx, cy, L, Wd, ang = rect_of(poly)
    # the deck's axis is the road's: the outline takes in the pylons' platforms unevenly, and its rectangle's axis
    # ran 7 m south of the road at the Buda end, which left the lanes off the streets they land on
    pts = [np.array(ln.coords) for oid, t, ln in ctx["osm"].lines if t.get("name") == ELISABETH and t.get("highway")
           and poly.buffer(5).contains(ln.interpolate(0.5, normalized=True))]
    if pts:
        c = np.concatenate(pts)
        mu = c.mean(0)
        d = np.linalg.svd(c - mu, full_matrices=False)[2][0]
        if d @ np.array([math.cos(ang), math.sin(ang)]) < 0:
            d = -d
        cx, cy, ang = float(mu[0]), float(mu[1]), math.atan2(d[1], d[0])
    fr = Frame(cx, cy, 0, ang)
    us = np.arange(-L / 2, L / 2, 1.0)
    xs, ys = fr.xy(us, 0 * us)
    xi, yi = np.clip(np.asarray(xs).astype(int), 0, ctx["W"] - 1), np.clip(np.asarray(ys).astype(int), 0, ctx["D"] - 1)
    wet = us[ctx["river"][yi, xi]]
    if not len(wet):
        raise KeyError("Danube under Erzsébet híd")
    ua, ub = float(wet.min()) + 3.0, float(wet.max()) - 3.0
    mid = (ua + ub) / 2
    fr = fr.at(mid)
    ua, ub = ua - mid, ub - mid
    s0, s1 = axis_extent(fr, poly)
    return dict(fr=fr, s0=s0, s1=s1, zf=deck_fn(ctx, fr, s0, s1, lift=1.6, hold=held_ends(ctx, fr, s0, s1, poly)), ua=ua, ub=ub, poly=poly, hw=13.8, under=2.6)


def margaret_geom(ctx):
    """the two halves (from the bend at the island pier outwards) and the branch to the island."""
    area = ctx["area"]
    WLr = ctx["WLr"]
    poly = bridge_poly(ctx, MARGIT)
    parts = sorted(poly.geoms, key=lambda q: -q.area) if poly.geom_type == "MultiPolygon" else [poly]
    main, branches = parts[0], parts[1:]
    cs = [np.array(area[i][3].centroid.coords[0]) for i in MARGIT_PIERS]
    dB = (cs[0] - cs[1]) / np.linalg.norm(cs[0] - cs[1])  # towards Buda
    dP = (cs[3] - cs[2]) / np.linalg.norm(cs[3] - cs[2])  # towards Pest
    k = np.linalg.solve(np.array([dB, -dP]).T, cs[2] - cs[1])
    K = cs[1] + dB * k[0]                                 # the bend, at the island pier
    zc = WLr + 11.0
    halves = []
    for d, ps in ((dB, cs[1::-1]), (dP, cs[2:])):
        fr = Frame(K[0], K[1], 0, math.atan2(d[1], d[0]))
        up = [float((c - K) @ d) for c in ps]                 # the two river piers, from the bend outwards
        u_end = axis_extent(fr, main)[1]
        u_ab = up[1] + (up[1] - up[0])                       # the bank pier, one more span out, at most at the bank
        bank = wet_extent(ctx, fr, 0.0, u_end)
        if bank is not None:
            u_ab = min(u_ab, bank + 2.0)
        z_end = float(np.clip(ctx["ground_m"](*fr.xy(u_end + 3, 0)), WLr + 4, zc + 6.0))
        # the bank pier high enough for the ramp on to the street to clear the ground beside it (Jászai Mari tér stands
        # 2.5 m above the river spans); lifted, the bridgehead lies level with the square: the ways across it meet it at grade
        us = np.arange(u_ab + 3.0, u_ab + 0.75 * (u_end - u_ab), 2.0)
        r = (us - u_ab) / max(u_end - u_ab, 1)
        gs = np.array([max(ctx["ground_m"](*fr.xy(u, v)) for v in (-10.0, 0.0, 10.0)) for u in us])
        z_ab = max([zc - 0.8] + list((gs - 0.25 - z_end * r) / (1 - r)))
        grade = u_ab + 3.0 if z_ab > zc - 0.8 else u_end

        def zf(u, u_ab=u_ab, u_end=u_end, z_ab=z_ab, z_end=z_end):
            u = np.asarray(u, float)
            t = np.clip(u / u_ab, 0, 1)
            r = np.clip((u - u_ab) / max(u_end - u_ab, 1), 0, 1)
            return np.where(u <= u_ab, zc - (zc - z_ab) * t * t, z_ab + (z_end - z_ab) * r)
        halves.append(dict(fr=fr, up=up, u_end=u_end, u_ab=u_ab, zf=zf, hw=12.6, under=1.9, grade=grade))
    brs = []
    for br in branches:
        pts = np.array(br.exterior.coords)
        far = pts[np.argmax(np.linalg.norm(pts - K, axis=1))]
        ue0 = float(np.linalg.norm(far - K))
        # the branch follows its road: the mapped bridge way on it, from the main deck down to the island's road
        roads = [ln for oid, t, ln in ctx["osm"].lines if t.get("bridge") not in (None, "no")
                 and t.get("highway") not in (None, "footway", "cycleway", "path") and ln.intersects(br.buffer(1))
                 and br.buffer(3).intersection(ln).length > 0.6 * min(ln.length, 40)]
        if roads:
            ln = max(roads, key=lambda q: br.buffer(3).intersection(q).length)
            c0, c1 = np.array(ln.coords[0]), np.array(ln.coords[-1])
            if np.linalg.norm(c0 - K) > np.linalg.norm(c1 - K):
                c0, c1 = c1, c0
            db = (c1 - c0) / np.linalg.norm(c1 - c0)
            O = c0 + db * float((K - c0) @ db)            # K's foot on the road's line
            ends = [float((p - O) @ db) for p in (*pts, c1)]
            far = O + db * max(ends)
        else:
            db = (far - K) / np.linalg.norm(far - K)
            O = K
        frb = Frame(O[0], O[1], 0, math.atan2(db[1], db[0]))
        ue = float(np.linalg.norm(far - O))
        ub = 12.0
        wb = float(np.clip(br.area / max(ue0 - ub, 1) / 2, 4.0, 8.0))
        us = np.arange(ub, ue + 8.0, 1.0)
        gs = np.array([ctx["ground_m"](*frb.xy(u, 0)) for u in us])
        z1 = float(np.clip(ctx["ground_m"](*frb.xy(ue + 3, 0)), WLr + 3, zc))

        def zfb(u, ue=ue, z1=z1, us=us, gs=gs):  # down to the island, never under its ground
            u = np.asarray(u, float)
            t = np.clip((u - ub) / (ue - ub), 0, 1)
            return np.maximum(zc + (z1 - zc) * t, np.interp(u, us, gs) + 0.2)
        brs.append(dict(fr=frb, ub=ub, ue=ue, wb=wb, zf=zfb, z1=z1))
    return dict(K=K, zc=zc, halves=halves, branches=brs, isl=area[MARGIT_ISLAND][3])


def petofi_geom(ctx):
    area = ctx["area"]
    WLr = ctx["WLr"]
    poly = bridge_poly(ctx, PETOFI)
    p1, p2 = (np.array(area[i][3].centroid.coords[0]) for i in PETOFI_PIERS)
    c, d = (p1 + p2) / 2, p2 - p1
    half = float(np.linalg.norm(d)) / 2
    fr = Frame(c[0], c[1], 0, math.atan2(d[1], d[0]))
    side = 112.0 * half / 77.0                     # the outer spans, in proportion to the mapped centre span
    A = half + side
    s0, s1 = axis_extent(fr, poly)
    zc, z_ab = WLr + 17.0, WLr + 15.5  # high over the river; the Pest approach clears Közraktár utca and the HÉV
    za = float(np.clip(ctx["ground_m"](*fr.xy(s0 - 3, 0)), WLr + 4, z_ab))
    zb = float(np.clip(ctx["ground_m"](*fr.xy(s1 + 3, 0)), WLr + 4, z_ab))

    def zf(u):
        u = np.asarray(u, float)
        au = np.abs(u)
        t = np.clip(au / A, 0, 1)
        zend = np.where(u < 0, za, zb)
        lim = np.where(u < 0, -s0, s1)
        r = np.clip((au - A) / np.maximum(lim - A, 1), 0, 1)
        return np.where(au <= A, zc - (zc - z_ab) * t * t, z_ab + (zend - z_ab) * r)
    return dict(fr=fr, s0=s0, s1=s1, zf=zf, half=half, side=side, A=A, hw=12.8, under=1.8)


def bridge_decks(ctx):
    """the hand-built decks, for voxelize.py to keep the roads under them clear: [dict(fr, zf, u0, u1, hw, under)]
    (u along the deck in its frame, zf the deck's top in metres on ctx's scale, hw its half-width; past an optional
    `grade` the deck lies on the street's level and the ways crossing it are not dug under it)."""
    ctx = dict(ctx, area={a[0]: a for a in ctx["osm"].areas})
    out = []
    for geom in (chain_geom, liberty_geom, elisabeth_geom, petofi_geom):
        try:
            g = geom(ctx)
        except KeyError:
            continue
        out.append(dict(fr=g["fr"], zf=g["zf"], u0=g["s0"], u1=g["s1"], hw=g["hw"], under=g["under"]))
    try:
        m = margaret_geom(ctx)
        out += [dict(fr=h["fr"], zf=h["zf"], u0=0.0, u1=h["u_end"], hw=h["hw"], under=h["under"], grade=h["grade"])
                for h in m["halves"]]
        out += [dict(fr=b["fr"], zf=b["zf"], u0=b["ub"], u1=b["ue"], hw=b["wb"], under=2.2) for b in m["branches"]]
    except KeyError:
        pass
    return out


def approach(S, ctx, fr, u0, u1, zf, hw, col, under=1.6, step=14.0, clear=2.5):
    """a deck's approach over land from u0 to u1: wherever less than `clear` metres of headroom would be left under it,
    a solid embankment (a stone wall where it faces an opening); over the roads dug down beneath it (voxelize.py),
    open, with rows of columns across it every `step` m, none standing on a road or a tram line."""
    a, b = sorted((float(u0), float(u1)))
    if b - a < 1:
        return
    road, gm, G, BASE = ctx.get("road"), ctx["ground_m"], ctx["G"], ctx["BASE"]
    D_, W_ = G.shape

    def fill(u, v, w):
        x, y = fr.xy(u, v)
        xi = np.clip(np.asarray(x, float).astype(int), 0, W_ - 1)
        yi = np.clip(np.asarray(y, float).astype(int), 0, D_ - 1)
        gap = zf(u) - under - (G[yi, xi] - BASE)
        return np.where(gap < clear, col, 0).astype(np.uint16)
    S.add(Slab(fr, a, b, -hw, hw, zf, -14, -under, fill))
    for u in np.arange(a + step / 2, b, step):
        top = float(zf(u)) - under
        for v in np.arange(-hw + 1.6, hw - 1.5, 5.2):
            x, y = fr.xy(u, v)
            xi, yi = int(x), int(y)
            if road is not None and road[max(yi - 2, 0):min(yi + 3, D_), max(xi - 2, 0):min(xi + 3, W_)].any():
                continue
            g0 = gm(x, y)
            if top - g0 < clear:
                continue
            S.add(Box(fr.at(u, v), -0.7, 0.7, -0.7, 0.7, g0 - 2.0, top, col))


def bank_pier(S, ctx, fr, u, zf, hw, col, under=1.6, thick=3.0):
    """the pier on the bank a river span lands on; if a road runs along the bank through it, an arch over the road."""
    top = float(zf(u)) - under
    WLr = ctx["WLr"]
    S.add(Box(fr.at(u), -thick, thick, -hw - 0.8, hw + 0.8, WLr - 4, top, col))
    road = ctx.get("road")
    if road is None:
        return
    hit = []
    for v in np.arange(-hw, hw + 0.1, 1.0):
        for du in (-thick, 0.0, thick):
            x, y = fr.xy(u + du, v)
            if 0 <= int(y) < road.shape[0] and 0 <= int(x) < road.shape[1] and road[int(y), int(x)]:
                hit.append(ctx["ground_m"](x, y))
    if hit and top - min(hit) >= 4.0:  # the road runs along the river, across the deck: open the pier over it
        g0 = min(hit)
        clear = min(top - 1.2 - g0, 9.0)
        S.add(Box(fr.at(u), -thick - 0.1, thick + 0.1, -hw + 1.2, hw - 1.2, g0, g0 + clear, 0, mode="carve"))


def lion(S, fr, w0, col):
    """a reclining stone lion facing +u (Marschalkó's, 1852), on its pedestal."""
    S.add(Box(fr, -2.4, 2.4, -1.1, 1.1, w0, w0 + 2.4, col))
    S.add(Box(fr, -2.6, 2.6, -1.3, 1.3, w0 + 2.4, w0 + 2.7, col))
    b = w0 + 2.7
    S.add(Ellipsoid(fr.at(-0.3, 0, b + 0.7), 1.9, 0.75, 0.75, col))
    S.add(Ellipsoid(fr.at(1.15, 0, b + 1.15), 0.75, 0.9, 1.0, col))
    S.add(Ellipsoid(fr.at(1.75, 0, b + 1.3), 0.6, 0.55, 0.65, col))
    S.add(Box(fr, 1.0, 2.4, -0.65, 0.65, b, b + 0.45, col))
    S.add(Capsule(fr, (-2.1, 0.3, b + 0.3), (-2.6, 0.9, b + 0.25), 0.22, col))


def chain_bridge(S, ctx, plan):
    """Széchenyi lánchíd (W. T. Clark, A. Clark, 1849; rebuilt 1949, restored 2021-23): 380 m, spans 88.7 + 202.6
    + 88.7 m, 14.8 m wide; triumphal-arch pylons on cutwater piers, two chains a side, Marschalkó's four lions."""
    P, C, area = ctx["P"], ctx["C"], ctx["area"]
    geo = chain_geom(ctx)
    fr, s0, s1, zf, half, A = geo["fr"], geo["s0"], geo["s1"], geo["zf"], geo["half"], geo["A"]
    WLr = ctx["WLr"]
    stone, stone2, lionc = P("#cbbfa3"), P("#bcb094"), P("#aaa08b")
    iron = P("#55625c", METAL)
    asphalt, paving = C["asphalt"], C["paving"]

    def deck_col(u, v, w):
        av = np.abs(v)
        road = np.where(lane_marks(u, av, [(0.0, "solid"), (2.95, "solid")], 0.25), C["mark"], asphalt)
        span = np.where(av < 3.2, road, np.where(av < 4.4, iron, np.where(av < 7.1, paving, iron)))
        # past the anchorages the carriageways part towards the squares' streets: all of it road
        return np.where(np.abs(u) > A + 8, np.where(av < 7.0, asphalt, paving), span).astype(np.uint16)
    S.add(Slab(fr, s0, s1, -7.4, 7.4, zf, -0.7, 0, deck_col))
    S.add(Slab(fr, s0, s1, -4.6, 4.6, zf, -2.1, -0.7, iron))
    for a, b in ((s0, -A + 2), (A - 2, s1)):  # the bridgeheads: solid, but open over the quay roads that pass under
        if b > a:
            approach(S, ctx, fr, a, b, zf, 7.4, stone2, under=0.7, clear=3.0)

    def lattice(u, v, w):
        h = w - zf(u)
        m = (h < 0.4) | (h > 1.3) | (np.mod(u + h * 1.5, 2.6) < 0.55) | (np.mod(u - h * 1.5, 2.6) < 0.55)
        return np.where(m, iron, 0).astype(np.uint16)

    def railing(u, v, w):
        h = w - zf(u)
        return np.where((h < 0.25) | (h > 0.85) | (np.mod(u, 0.7) < 0.25), iron, 0).astype(np.uint16)
    for sv in (-1, 1):
        # the trusses end at the anchorages and the railings a little further: the ways cross both lines beyond
        S.add(Slab(fr, max(s0, -A - 8), min(s1, A + 8), *sorted((sv * 4.0, sv * 4.5)), zf, 0, 1.7, lattice))
        S.add(Slab(fr, max(s0, -A - 22), min(s1, A + 22), *sorted((sv * 7.0, sv * 7.4)), zf, 0, 1.15, railing))
    # pylons
    for up in (-half, half):
        zd = float(zf(up))
        fp = fr.at(up)
        cutwater_pier(S, fp, 5.45, 10.5, WLr - 7, zd - 0.7, stone2)
        S.add(Box(fp, -7.0, 7.0, -12.9, 12.9, zd - 0.7, zd, paving))
        for su in (-1, 1):  # the platform's railing, not across the deck (it barred the carriageway)
            for sv in (-1, 1):
                S.add(Box(fp, *sorted((su * 6.6, su * 7.0)), *sorted((sv * 7.4, sv * 12.9)), zd, zd + 1.15, railing))
        for sv in (-1, 1):
            S.add(Box(fp, -7.0, 7.0, *sorted((sv * 12.5, sv * 12.9)), zd, zd + 1.15, railing))

        def rust(u, v, w, zd=zd):
            return np.where(np.mod(np.floor((w - zd) / 1.0), 2) == 0, stone, stone2).astype(np.uint16)
        S.add(Box(fp, -5.5, 5.5, -10.8, 10.8, zd - 0.7, zd + 3.0, stone2))
        S.add(TBox(fp, 5.0, 10.0, 4.7, 9.6, zd + 3.0, zd + 24.0, rust))
        S.add(Box(fp, -5.4, 5.4, -10.3, 10.3, zd + 24.0, zd + 25.5, stone))
        S.add(Box(fp, -4.8, 4.8, -9.6, 9.6, zd + 25.5, zd + 28.0, stone2))
        S.add(Box(fp, -5.2, 5.2, -10.0, 10.0, zd + 28.0, zd + 28.8, stone))
        S.add(Box(fp, -4.4, 4.4, -9.1, 9.1, zd + 28.8, zd + 30.3, stone2))
        for su in (-1, 1):
            for sv in (-1, 1):
                S.add(Box(fp, *sorted((su * 4.6, su * 5.4)), *sorted((sv * 7.6, sv * 9.7)), zd + 3, zd + 24, stone))
                S.add(Box(fp, *sorted((su * 4.6, su * 5.4)), *sorted((sv * 3.9, sv * 5.3)), zd + 3, zd + 24, stone))
        S.add(Arch(fp, -5.7, 5.7, 0, 4.3, zd, zd + 8.4, stone))
        S.add(Arch(fp, -6.0, 6.0, 0, 3.4, zd, zd + 8.4, mode="carve"))
        # the carriageway goes on through the archway, on the deck's own line (the pier's stone left a step there)
        S.add(Slab(fr, up - 7.0, up + 7.0, -3.4, 3.4, zf, 0, 0.6, 0, mode="carve"))
        S.add(Slab(fr, up - 7.0, up + 7.0, -3.4, 3.4, zf, -0.7, 0, deck_col))
        crest = (P("#b8382f"), P("#efeee8"), P("#2f7a46"), P("#d4ad55", METAL))

        def arms(u, v, w, zd=zd):
            h = w - zd - 14.0
            col = np.where(v < 0, np.where(np.mod(np.floor(h / 0.5), 2) == 0, crest[0], crest[1]), crest[0])
            col = np.where(h > 2.6, crest[3], np.where(h < 0.6, crest[2], col))
            return col.astype(np.uint16)
        for su in (-1, 1):
            S.add(Box(fp, *sorted((su * 4.7, su * 5.3)), -1.2, 1.2, zd + 14.0, zd + 17.0, arms))
        for su in (-1, 1):
            for sv in (-1, 1):
                x, y = fp.xy(su * 6.3, sv * 12.2)
                ctx["lamp_post"](int(x * F), int(y * F), int(round(zd * F)), 4.5)
    # chains: two a side, over the pylons' saddles into the anchorages; hangers every 3.55 m; bulbs along the top chain
    lamp = C["lamp"]
    for sv in (-1, 1):
        v = sv * 4.25
        for dz in (0.0, -1.5):
            zt = float(zf(-half)) + 26.0 + dz
            zl = float(zf(0)) + 2.6 + dz
            us = np.linspace(-half, half, 160)
            main = [(u, v, zl + (zt - zl) * (u / half) ** 2) for u in us]
            sides = []
            for sgn in (-1, 1):
                us2 = np.linspace(half, A, 50)
                s = (us2 - half) / (A - half)
                za = float(zf(sgn * A)) + 0.4 + dz * 0.3
                sides.append([(sgn * u, v, zt + (za - zt) * s_ - 4.0 * s_ * (1 - s_)) for u, s_ in zip(us2, s)])
            for line in [main] + sides:
                S.polyline(fr, line, iron)
                S.polyline(fr, [(a, b, z_ + 0.5) for a, b, z_ in line], iron)
            if dz == 0:
                for line in [main] + sides:
                    for a, b, z_ in line[::3]:
                        S.line(fr, (a, b, z_ + 1.0), (a, b, z_ + 1.0), lamp)
                for u in np.arange(-half + 3.5, half - 3.0, 3.55):
                    zc = zl - 1.5 + (zt - zl) * (u / half) ** 2
                    S.line(fr, (u, v, float(zf(u)) + 1.7), (u, v, zc), iron)
                for sgn in (-1, 1):
                    for u in np.arange(half + 4.0, A - 4.0, 3.55):
                        s_ = (u - half) / (A - half)
                        za = float(zf(sgn * A)) + 0.4
                        zc = zt - 1.5 + (za - zt) * s_ - 4.0 * s_ * (1 - s_)
                        if zc - float(zf(sgn * u)) > 2.2:
                            S.line(fr, (sgn * u, v, float(zf(sgn * u)) + 1.7), (sgn * u, v, zc), iron)
    # the abutments, and the lions on them, two at each end facing out
    for sgn in (-1, 1):
        ua = sgn * A
        za = float(zf(ua))
        for sv in (-1, 1):
            S.add(Box(fr, *sorted((ua - sgn * 9, ua + sgn * 5)), *sorted((sv * 7.4, sv * 11.5)), za - 12, za + 1.2, stone2))
            S.add(Box(fr, *sorted((ua - sgn * 9, ua + sgn * 5)), *sorted((sv * 7.4, sv * 11.8)), za + 1.2, za + 1.6, stone))
            lion(S, fr.at(ua - sgn * 3.5, sv * 9.5, 0, 0 if sgn > 0 else math.pi), za + 1.6, lionc)
        # a road along the bank passes through the abutment (Buda's lower quay): a portal over it, 4.6 m high
        lo, hi = sorted((ua - sgn * 9, ua + sgn * 5))
        for oid, t, ln in ctx["osm"].lines:
            if t.get("highway") not in ("primary", "secondary", "tertiary", "residential", "unclassified") or t.get("bridge") or t.get("tunnel"):
                continue
            cs = np.array(ln.segmentize(1.0).coords)
            u_, v_ = fr.uv(cs[:, 0], cs[:, 1])
            m = (u_ > lo) & (u_ < hi) & (np.abs(v_) < 12.5)
            if m.sum() < 6 or np.ptp(v_[m]) < 8:
                continue
            uc = float(np.clip(np.median(u_[m]), lo + 5.5, hi - 5.5))
            zg = min(ctx["ground_m"](*fr.xy(uc, sv_ * 9.5)) for sv_ in (-1, 1))
            if za - zg > 5.5:  # through the lions' pedestals only: under the deck the approach is open already
                for sv_ in (-1, 1):
                    S.add(Box(fr, uc - 4.5, uc + 4.5, *sorted((sv_ * 7.3, sv_ * 12.0)), zg, min(zg + 4.6, za - 0.5), 0, mode="carve"))


def liberty_bridge(S, ctx, plan):
    """Szabadság híd (János Feketeházy, 1896): a cantilever truss, 333.6 m in spans of 79 + 175.6 + 79 m, 20 m wide,
    green; its four masts carry the bronze Turul birds."""
    P, C, area = ctx["P"], ctx["C"], ctx["area"]
    geo = liberty_geom(ctx)
    fr, s0, s1, zf, half, A = geo["fr"], geo["s0"], geo["s1"], geo["zf"], geo["half"], geo["A"]
    WLr = ctx["WLr"]
    green, green2 = P("#4f8c63", METAL), P("#3e7352", METAL)
    stone, bronze = P("#c4b89e"), P("#6e5b2c", METAL)
    asphalt, paving, rail = C["asphalt"], C["paving"], C["rail"]

    def deck_col(u, v, w):
        av = np.abs(v)
        trk = ((av > 0.55) & (av < 0.95)) | ((av > 1.95) & (av < 2.35))
        col = np.where(av < 6.0, np.where(trk, rail, asphalt), np.where(av < 7.0, green, np.where(av < 9.6, paving, green)))
        return col.astype(np.uint16)
    S.add(Slab(fr, s0, s1, -10.0, 10.0, zf, -0.7, 0, deck_col))
    S.add(Slab(fr, s0, s1, -7.0, 7.0, zf, -2.0, -0.7, green2))
    for sgn, a, b in ((-1, s0, -A), (1, A, s1)):  # the abutments, then the approaches on columns clear of the roads
        bank_pier(S, ctx, fr, sgn * (A - 2.0), zf, 10.0, stone, under=2.0, thick=2.5)
        approach(S, ctx, fr, a, b, zf, 10.0, stone, under=2.0)

    def hz(u):
        au = abs(u)
        if au <= half:
            return 1.9 + (15.5 - 1.9) * (au / half) ** 2
        s = min((au - half) / (A - half), 1.0)
        return 15.5 * (1 - s) ** 1.5 + 1.2 * s
    us = np.concatenate([np.linspace(-A, -half, 60), np.linspace(-half, half, 140)[1:], np.linspace(half, A, 60)[1:]])
    for sv in (-1, 1):
        v = sv * 6.5
        top = [(u, v, float(zf(u)) + hz(u)) for u in us]
        for dz in (0.0, -0.5):
            S.polyline(fr, [(a, b, z_ + dz) for a, b, z_ in top], green)
        S.add(Slab(fr, -A, A, *sorted((sv * 6.25, sv * 6.75)), zf, 0, 0.9, green))
        verts = np.arange(-A + 2.0, A - 1.0, 5.5)
        for i, u in enumerate(verts):
            zb, zt = float(zf(u)) + 0.9, float(zf(u)) + hz(u)
            if zt - zb < 0.5:
                continue
            S.line(fr, (u, v, zb), (u, v, zt), green)
            if i + 1 < len(verts):
                u2 = verts[i + 1]
                toward = abs(u2) < abs(u)
                a_, b_ = (u, u2) if toward else (u2, u)
                S.line(fr, (b_, v, float(zf(b_)) + 0.9), (a_, v, float(zf(a_)) + hz(a_) - 0.3), green)
            if hz(u) > 7.5:
                S.line(fr, (u, -6.5, zt - 0.3), (u, 6.5, zt - 0.3), green2)
    for up in (-half, half):
        zd = float(zf(up))
        fp = fr.at(up)
        cutwater_pier(S, fp, 2.7, 10.6, WLr - 7, zd - 0.7, stone)
        S.add(Box(fp, -1.0, 1.0, -6.9, 6.9, zd + 11.6, zd + 16.6, green))
        S.add(Arch(fp, -1.2, 1.2, 0, 6.0, zd, zd + 10.0, mode="carve"))
        S.add(Box(fp, -1.3, 1.3, -1.6, 1.6, zd + 14.0, zd + 16.2, P("#b8382f")))
        for sv in (-1, 1):
            fm = fp.at(0, sv * 6.5)
            S.add(Lathe(fm, zd, zd + 15.5, cyl(0.8), green, n=4))
            S.add(Lathe(fm, zd + 15.5, zd + 24.0, cone(0.8, 0.3), green, n=4))
            S.add(Ellipsoid(fm.at(0, 0, zd + 24.4), 0.55, 0.55, 0.55, green))
            # the Turul, wings raised, facing out along the bridge
            ft = fm.at(0, 0, zd + 25.6, 0 if up > 0 else math.pi)
            S.add(Ellipsoid(ft, 0.85, 0.38, 0.45, bronze))
            S.add(Ellipsoid(ft.at(0.75, 0, 0.35), 0.32, 0.22, 0.25, bronze))
            S.add(Box(ft, -0.25, 0.45, -1.9, 1.9, 0.0, 0.3, bronze))
            for sw in (-1, 1):
                S.add(Capsule(ft, (0.1, sw * 0.4, 0.2), (0.0, sw * 2.2, 1.25), 0.22, bronze))
            S.add(Capsule(ft, (-0.7, 0, -0.1), (-1.3, 0, -0.35), 0.2, bronze))
        for su in (-1, 1):
            for sv in (-1, 1):
                x, y = fp.xy(su * 3.5, sv * 9.0)
                ctx["lamp_post"](int(x * F), int(y * F), int(round(zd * F)), 5.0)
    for u in np.arange(-A + 12, A - 6, 22.0):
        if min(abs(u - half), abs(u + half)) < 6:
            continue
        for sv in (-1, 1):
            x, y = fr.xy(u, sv * 9.3)
            ctx["lamp_post"](int(x * F), int(y * F), int(round(float(zf(u)) * F)), 5.0)


def elisabeth_bridge(S, ctx, plan):
    """Erzsébet híd (Pál Sávoly, 1964): a white suspension bridge, a single 290 m span between the pylons on the
    banks, 27.6 m wide; two cable bundles hanging between white steel pylons, anchored in the bridgeheads."""
    P, C = ctx["P"], ctx["C"]
    geo = elisabeth_geom(ctx)
    fr, s0, s1, zf, ua, ub = geo["fr"], geo["s0"], geo["s1"], geo["zf"], geo["ua"], geo["ub"]
    WLr = ctx["WLr"]
    white, white2 = P("#efefeb", METAL), P("#d6d6d1", METAL)
    stone = P("#bdb39d")
    asphalt, paving = C["asphalt"], C["paving"]

    mark = C["mark"]
    marks = [(0.4, "solid"), (3.25, "dash"), (6.4, "solid"), (9.25, "solid")]

    def deck_col(u, v, w):
        av = np.abs(v)
        road = np.where(lane_marks(u, av, marks), mark, asphalt)
        return np.where(av < 9.6, road, np.where(av < 10.8, white, np.where(av < 13.4, paving, white))).astype(np.uint16)
    S.add(Slab(fr, s0, s1, -13.8, 13.8, zf, -0.7, 0, deck_col))
    S.add(Slab(fr, s0, s1, -11.6, 11.6, zf, -2.6, -0.7, white2))
    for sv in (-1, 1):
        S.add(Slab(fr, s0, s1, *sorted((sv * 13.4, sv * 13.8)), zf, 0, 1.1,
                   lambda u, v, w: np.where((w - zf(u) > 0.8) | (np.mod(u, 2.0) < 0.5), white, 0).astype(np.uint16)))
    for a, b in ((s0, ua - 6.5), (ub + 6.5, s1)):  # over the quays: on columns clear of the roads and the tram
        approach(S, ctx, fr, a, b, zf, 13.8, stone, under=2.6)
    tops = {}
    for up in (ua, ub):
        zd = float(zf(up))
        fp = fr.at(up)
        S.add(Box(fp, -6.0, 6.0, -15.0, 15.0, WLr - 6, zd - 2.6, stone))
        S.add(Box(fp, -1.3, 1.3, -11.6, 11.6, zd - 5.0, zd - 0.7, white2))
        for sv in (-1, 1):
            S.add(TBox(fp.at(0, sv * 11.6), 1.5, 1.9, 1.05, 1.35, zd - 2.6, zd + 28.0, white))
            S.add(Box(fp.at(0, sv * 11.6), -1.5, 1.5, -1.0, 1.0, zd + 27.5, zd + 29.0, white2))
        tops[up] = zd + 28.0
    lamp = C["lamp"]
    span = ub - ua
    for sv in (-1, 1):
        v = sv * 11.6
        zl = float(zf(0)) + 1.6
        main = [(u, v, zl + (tops[ua] - zl) * ((u - (ua + ub) / 2) / (span / 2)) ** 2) for u in np.linspace(ua, ub, 220)]
        S.polyline(fr, main, white)
        S.polyline(fr, [(a, b, z_ + 0.5) for a, b, z_ in main], white)
        for up, end in ((ua, max(s0 + 6, ua - 70)), (ub, min(s1 - 6, ub + 70))):
            back = [(up + (end - up) * s, v, tops[up] + (float(zf(end)) + 0.8 - tops[up]) * s - 2.0 * s * (1 - s))
                    for s in np.linspace(0, 1, 60)]
            S.polyline(fr, back, white)
            S.polyline(fr, [(a, b, z_ + 0.5) for a, b, z_ in back], white)
        for u in np.arange(ua + 6.0, ub - 3.0, 6.0):
            zc = zl + (tops[ua] - zl) * ((u - (ua + ub) / 2) / (span / 2)) ** 2
            S.line(fr, (u, v, float(zf(u))), (u, v, zc), white)
    for u in np.arange(s0 + 10, s1 - 5, 30.0):
        for sv in (-1, 1):
            x, y = fr.xy(u, sv * 10.2)
            ctx["lamp_post"](int(x * F), int(y * F), int(round(float(zf(u)) * F)), 7.0)


def wet_extent(ctx, fr, u0, u1):
    """the farthest u (from u0 towards u1) at which the bridge axis is over the river."""
    us = np.arange(u0, u1, np.sign(u1 - u0) * 1.0)
    xs, ys = fr.xy(us, 0 * us)
    xi = np.clip(np.asarray(xs).astype(int), 0, ctx["W"] - 1)
    yi = np.clip(np.asarray(ys).astype(int), 0, ctx["D"] - 1)
    wet = us[ctx["river"][yi, xi]]
    return float(wet[np.argmax(np.abs(wet - u0))]) if len(wet) else None


def circ_arch(a, b, zs, f):
    """a segmental arch springing at zs from u = a to u = b, rising f: z(u)."""
    L = b - a
    R = (L * L / 4 + f * f) / (2 * f)
    m = (a + b) / 2

    def z(u):
        du = np.clip(np.asarray(u, float) - m, -L / 2, L / 2)
        return zs + np.sqrt(np.maximum(R * R - du * du, 0)) - (R - f)
    return z


def figure(S, fr, w0, col, wings=True):
    """a standing allegorical figure, ~2.6 m, facing +u: draped body, head, raised wings."""
    S.add(Lathe(fr, w0, w0 + 1.7, cone(0.55, 0.3), col))
    S.add(Ellipsoid(fr.at(0, 0, w0 + 1.95), 0.3, 0.32, 0.38, col))
    S.add(Ellipsoid(fr.at(0, 0, w0 + 2.45), 0.2, 0.2, 0.24, col))
    if wings:
        for sw in (-1, 1):
            S.add(Capsule(fr, (-0.2, sw * 0.3, w0 + 1.9), (-0.5, sw * 1.1, w0 + 2.9), 0.2, col))


def margaret_bridge(S, ctx, plan):
    """Margit híd (Ernest Goüin, 1876; rebuilt 1948, renovated 2011): six segmental deck arches of ochre steel on
    limestone piers, 25 m wide, bent by 30 degrees at the island pier, from which a branch dips to Margaret Island.
    Each river pier carries Adolphe Thabard's galley prows and allegorical figures above the deck at both ends; the
    island pier, two obelisks round the Hungarian crown."""
    P, C, area = ctx["P"], ctx["C"], ctx["area"]
    WLr = ctx["WLr"]
    geo = margaret_geom(ctx)
    K, isl, zc = geo["K"], geo["isl"], geo["zc"]
    ochre, ochre2 = P("#c9b06a", METAL), P("#a48d4f", METAL)
    stone, stone2 = P("#c7bfac"), P("#a9a190")
    figc, gold = P("#8d887c"), P("#b8913a", METAL)
    asphalt, paving, rail, tramb = C["asphalt"], C["paving"], C["rail"], C["trambed"]
    hw = 12.6

    def deck_col(u, v, w):
        av = np.abs(v)
        trk = ((av > 0.5) & (av < 0.95)) | ((av > 2.05) & (av < 2.5))
        road = np.where(lane_marks(u, av, [(3.25, "solid"), (6.1, "dash"), (8.95, "solid")]), C["mark"], asphalt)
        col = np.where(av < 3.0, np.where(trk, rail, tramb), np.where(av < 9.2, road, paving))
        return col.astype(np.uint16)

    def balustrade(zf):
        def f(u, v, w):
            h = w - zf(u)
            return np.where((h > 0.85) | (h < 0.2) | (np.mod(u, 0.9) < 0.45), ochre, 0).astype(np.uint16)
        return f
    for h in geo["halves"]:
        fr, up, u_end, u_ab, zf = h["fr"], h["up"], h["u_end"], h["u_ab"], h["zf"]
        S.add(Slab(fr, -4.0, u_end, -hw, hw, zf, -0.7, 0, deck_col))
        S.add(Slab(fr, 0, u_end, -hw, hw, zf, -1.6, -0.7, ochre2))
        for sv in (-1, 1):
            S.add(Slab(fr, 0, u_end, *sorted((sv * (hw - 0.5), sv * hw)), zf, 0, 1.1, balustrade(zf)))
            S.add(Slab(fr, 0, u_ab, *sorted((sv * hw, sv * (hw + 0.4))), zf, -1.9, 0.1, ochre))  # the edge girder
        # six arches: spans from the island pier's face to the piers and the bank abutment; six ribs across
        faces = [(12.8, up[0] - 4.6), (up[0] + 4.6, up[1] - 4.6), (up[1] + 4.6, u_ab - 3.0)]
        zs = WLr + 0.8
        for a, b in faces:
            if b - a < 10:
                continue
            f = float(min(7.3, zf((a + b) / 2) - 2.8 - zs))
            az = circ_arch(a, b, zs, f)
            for v in (-11.0, -6.6, -2.2, 2.2, 6.6, 11.0):
                S.add(Slab(fr, a, b, v - 0.45, v + 0.45, az, 0, 1.4, ochre))
                S.add(Slab(fr, a, b, v - 0.4, v + 0.4, zf, -1.9, -1.6, ochre2))
                outer = abs(v) > 10
                posts = np.arange(a + 1.8, b - 1.0, 3.6)
                for i, u in enumerate(posts):
                    zb, zt = float(az(u)) + 1.4, float(zf(u)) - 1.9
                    if zt - zb < 0.4:
                        continue
                    S.line(fr, (u, v, zb), (u, v, zt), ochre)
                    if outer and i + 1 < len(posts):
                        u2 = posts[i + 1]
                        z2b, z2t = float(az(u2)) + 1.4, float(zf(u2)) - 1.9
                        if z2t - z2b >= 0.4:
                            S.line(fr, (u, v, zb), (u2, v, z2t), ochre)
                            S.line(fr, (u, v, zt), (u2, v, z2b), ochre)
        # the river piers: limestone cutwaters, rising above the deck at both ends as pedestals with figures
        for u in up:
            zd = float(zf(u))
            fp = fr.at(u)
            cutwater_pier(S, fp, 4.6, 13.8, WLr - 6, zd - 1.9, stone)
            S.add(Box(fp, -4.8, 4.8, -14.0, 14.0, zs - 0.4, zs + 0.4, stone2))
            for sv in (-1, 1):
                S.add(Box(fp, -3.0, 3.0, *sorted((sv * (hw + 0.4), sv * 17.0)), zd - 1.9, zd + 2.6, stone))
                S.add(Box(fp, -3.3, 3.3, *sorted((sv * (hw + 0.2), sv * 17.3)), zd + 2.6, zd + 3.1, stone2))
                S.add(Lathe(fp.at(0, sv * 18.0), zd - 6.0, zd + 1.0, cone(1.6, 0.7), stone, n=4, rot=math.pi / 4))
                figure(S, fp.at(0, sv * 14.9, 0, math.pi / 2 if sv > 0 else -math.pi / 2), zd + 3.1, figc)
        # the bank pier the last arch lands on (open over a quay road), then the approach on columns clear of the roads
        bank_pier(S, ctx, fr, u_ab, zf, hw, stone, under=1.9)
        approach(S, ctx, fr, u_ab + 3.0, u_end, zf, hw, stone, under=1.9)
        for u in np.arange(8.0, u_end - 4, 21.0):
            for sv in (-1, 1):
                x, y = fr.xy(u, sv * (hw - 0.9))
                ctx["lamp_post"](int(x * F), int(y * F), int(round(float(zf(u)) * F)), 6.5)
    # the island pier: under the bend, its top level with the deck; two obelisks round the crown on the downstream side
    S.add(Poly(isl, WLr - 6, zc - 0.7, stone, mode="under"))
    S.add(Poly(isl, zc - 0.7, zc, paving, mode="under"))  # the decks' lanes and tracks run on over it
    ic = np.array(isl.centroid.coords[0])
    _, _, Li, Wi, ai = rect_of(isl)
    ui = np.array([math.cos(ai), math.sin(ai)])
    up_side = 1.0
    if geo["branches"]:
        bfr = geo["branches"][0]["fr"]
        bc = np.array(bfr.xy(30.0, 0))
        up_side = 1.0 if (bc - ic) @ ui > 0 else -1.0
    fo = Frame(ic[0], ic[1], 0, ai).at(-up_side * (Li / 2 - 2.5))
    for sv in (-1, 1):
        fb = fo.at(0, sv * 5.0)
        S.add(Box(fb, -1.5, 1.5, -1.5, 1.5, zc, zc + 2.2, stone2))
        S.add(TBox(fb, 0.9, 0.9, 0.45, 0.45, zc + 2.2, zc + 11.0, stone))
        S.add(Lathe(fb, zc + 11.0, zc + 12.0, cone(0.64, 0.0), stone, n=4, rot=math.pi / 4))
    S.add(Box(fo, -1.0, 1.0, -2.0, 2.0, zc, zc + 3.0, stone2))
    S.add(Ellipsoid(fo.at(0, 0, zc + 3.6), 0.9, 0.9, 0.7, gold))
    S.add(Lathe(fo, zc + 4.1, zc + 4.9, cyl(0.15), gold))
    # the branch to Margaret Island: from the pier, dipping to the island and meeting its road at the island's level
    for br in geo["branches"]:
        frb, ub, ue, wb, zfb = br["fr"], br["ub"], br["ue"], br["wb"], br["zf"]

        def bcol(u, v, w, wb=wb):
            av = np.abs(v)
            road = np.where(lane_marks(u, av, [(0.0, "dash"), (wb - 2.9, "solid")]), C["mark"], asphalt)
            return np.where(av < wb - 2.6, road, paving).astype(np.uint16)
        S.add(Slab(frb, ub - 2, ue, -wb, wb, zfb, -0.7, 0, bcol))
        for sv in (-1, 1):
            S.add(Slab(frb, ub, ue, *sorted((sv * (wb - 0.5), sv * wb)), zfb, 0, 1.1, balustrade(zfb)))
            S.add(Slab(frb, ub, ue, *sorted((sv * (wb - 1.5), sv * (wb - 0.6))), zfb, -2.2, -0.7, ochre))
        shore = wet_extent(ctx, frb, ub, ue)
        approach(S, ctx, frb, (shore if shore is not None else ub) + 2.0, ue, zfb, wb, stone, under=2.2, step=10.0)


def petofi_bridge(S, ctx, plan):
    """Petőfi híd (Pál Álgyay Hubert, 1937; rebuilt 1952, 1980): 112 + 154 + 112 m over the river on four steel lattice
    girders, deepest over the two river piers, grey since 1952; 25.6 m wide: 20.4 m of carriageway with the tram in
    the middle, 2.6 m pavements."""
    P, C, area = ctx["P"], ctx["C"], ctx["area"]
    WLr = ctx["WLr"]
    geo = petofi_geom(ctx)
    fr, s0, s1, zf, half, side, A = geo["fr"], geo["s0"], geo["s1"], geo["zf"], geo["half"], geo["side"], geo["A"]
    grey, grey2 = P("#5f6866", METAL), P("#4a5250", METAL)
    stone, stone2 = P("#c1b49c"), P("#a59a85")
    asphalt, paving, rail, tramb = C["asphalt"], C["paving"], C["rail"], C["trambed"]
    hw = 12.8

    def depth(u):  # the girders' depth: 8 m over the piers, 4.8 m mid-river (1/32 of the span), 3.5 m at the abutments
        au = np.abs(np.asarray(u, float))
        mid = 4.8 + 3.2 * (au / half) ** 2
        s = np.clip((au - half) / side, 0, 1)
        out = 8.0 - 4.5 * (1 - (1 - s) ** 2.2)
        return np.where(au <= half, mid, out)

    def bottom(u):
        return zf(u) - 0.9 - depth(u)

    def deck_col(u, v, w):
        av = np.abs(v)
        trk = ((av > 0.5) & (av < 0.95)) | ((av > 2.05) & (av < 2.5))
        road = np.where(lane_marks(u, av, [(3.45, "solid"), (6.7, "dash"), (9.95, "solid")]), C["mark"], asphalt)
        col = np.where(av < 3.2, np.where(trk, rail, tramb), np.where(av < 10.2, road, paving))
        return col.astype(np.uint16)
    S.add(Slab(fr, s0, s1, -hw, hw, zf, -0.9, 0, deck_col))
    for sv in (-1, 1):
        S.add(Slab(fr, s0, s1, *sorted((sv * (hw - 0.4), sv * hw)), zf, 0, 1.1,
                   lambda u, v, w: np.where((w - zf(u) > 0.85) | (np.mod(u, 2.0) < 0.5), grey, 0).astype(np.uint16)))
    # four lattice girders: chords, verticals every 6 m, Warren diagonals (drawn on the two outer ones)
    for v in (-10.8, -3.6, 3.6, 10.8):
        S.add(Slab(fr, -A, A, v - 0.45, v + 0.45, zf, -1.8, -0.9, grey))
        S.add(Slab(fr, -A, A, v - 0.5, v + 0.5, bottom, 0, 1.0, grey))
        outer = abs(v) > 10
        nodes = np.arange(-A, A + 0.1, A / round(A / 6.0))
        for i, u in enumerate(nodes):
            zb_, zt_ = float(bottom(u)) + 1.0, float(zf(u)) - 1.8
            S.line(fr, (u, v, zb_), (u, v, zt_), grey)
            if outer and i + 1 < len(nodes):
                u2 = nodes[i + 1]
                if i % 2 == 0:
                    S.line(fr, (u, v, zb_), (u2, v, float(zf(u2)) - 1.8), grey)
                else:
                    S.line(fr, (u, v, zt_), (u2, v, float(bottom(u2)) + 1.0), grey)
    for u in np.arange(-A, A + 0.1, 12.0):  # cross girders under the deck
        S.add(Box(fr.at(u), -0.3, 0.3, -11.2, 11.2, float(zf(u)) - 1.8, float(zf(u)) - 0.9, grey2))
    # the river piers and the bank abutments; beyond them the approaches on columns
    for up in (-half, half):
        fp = fr.at(up)
        zb_ = float(bottom(up))
        cutwater_pier(S, fp, 2.8, 12.7, WLr - 6, zb_, stone)
        S.add(Box(fp, -3.2, 3.2, -15.6, 15.6, zb_ - 1.2, zb_, stone2))
    for sgn, a, b in ((-1, s0, -A - 3.0), (1, A + 3.0, s1)):  # the abutments, then the approaches on columns clear of the roads
        bank_pier(S, ctx, fr, sgn * A, zf, hw, stone, under=0.9)
        approach(S, ctx, fr, a, b, zf, hw, stone, under=0.9)
    for u in np.arange(s0 + 10, s1 - 5, 26.0):
        for sv in (-1, 1):
            x, y = fr.xy(u, sv * (hw - 0.9))
            ctx["lamp_post"](int(x * F), int(y * F), int(round(float(zf(u)) * F)), 8.0)


# ------------------------------------------------------------------------------------------------ Castle Hill
BASTION_TOWERS = [  # lon, lat, radius, body, cone (m): read off the outline's round bastions and the photos
    (19.034981, 47.502048, 5.0, 10.0, 14.5),  # the main tower, by St Stephen's statue
    (19.034971, 47.501676, 3.3, 6.5, 9.0),
    (19.035326, 47.501805, 3.6, 7.0, 9.5),
    (19.034790, 47.502228, 3.0, 6.0, 8.5),
    (19.034730, 47.502396, 3.2, 6.0, 8.5),
    (19.034596, 47.502838, 3.6, 7.0, 9.5),
    (19.034727, 47.502941, 3.4, 6.5, 9.0),
]


def bastion(S, ctx, plan):
    """Halászbástya (Frigyes Schulek, 1895-1902): a white limestone terrace wall on the east edge of Castle Hill,
    arcaded and crenellated, with seven conical towers, the largest by St Stephen's statue."""
    from osm import to_grid
    P, area = ctx["P"], ctx["area"]
    g = area[BASTION][3]
    church = area[MATTHIAS][3].centroid
    T = feat_base(ctx, MATTHIAS) + 0.5
    xs, ys = np.array(g.exterior.coords).T
    gmin = min(ctx["ground_m"](x, y) for x, y in zip(xs[::3], ys[::3]))
    white, white2 = P("#efeadc"), P("#e0d9c7")
    conec = P("#d3ccba", ROOF)
    S.add(Poly(g, gmin - 3, T, white2))
    S.add(Poly(g, T - 0.5, T, P("#cbc4b4")))
    for a, b, n in ring_segments(g, 1.5):
        fr2 = seg_frame(a, b, n, 0)
        L = float(np.hypot(*(b - a)))
        mid = (a + b) / 2
        outer = (n @ (mid - np.array([church.x, church.y]))) > 0
        if outer and L >= 4:
            S.add(Box(fr2, 0, L, 0, 1.0, T, T + 5.5, white))
            for t_ in np.arange(1.6, L - 1.0, 3.2):
                fa = fr2.at(t_, 0, 0, math.pi / 2)
                S.add(Arch(fa, -0.2, 1.3, 0, 1.05, T, T + 3.2, mode="carve"))
            for t_ in np.arange(0.25, L - 0.4, 1.0):
                S.add(Box(fr2, t_, t_ + 0.5, 0, 1.0, T + 5.5, T + 6.5, white))
            S.add(Box(fr2, 0, L, -0.4, 0, T + 5.0, T + 5.5, white2, mode="under"))
        else:
            S.add(Box(fr2, 0, L, 0, 0.5, T, T + 1.1, white))
    for lon, lat, r, hb, hc in BASTION_TOWERS:
        x, y = to_grid(lon, lat)
        fr = Frame(x, y, 0, 0)
        S.add(Lathe(fr, gmin - 3, T + hb, cyl(r), white))
        S.add(Lathe(fr, T + hb - 0.7, T + hb, cyl(r + 0.5), white2))
        nwin = 8 if r > 4 else 6
        for k in range(nwin):
            fk = fr.at(turn=TAU * (k + 0.5) / nwin)
            S.add(Arch(fk, r - 0.6, r + 0.2, 0, 0.75 if r > 4 else 0.6, T + hb - 4.6, T + hb - 2.4, mode="carve"))
            if r > 4:
                S.add(Arch(fk, r - 0.6, r + 0.2, 0, 0.9, T + 0.0, T + 2.4, mode="carve"))
        S.add(Lathe(fr, T + hb, T + hb + hc, lambda t, r=r: (r + 0.25) * (1 - t) ** 1.12 + 0.1, conec))
        S.add(Lathe(fr, T + hb + hc - 0.2, T + hb + hc + 0.9, cyl(0.25), white2))
        if r > 4:  # turrets round the main tower, and dormers on its cone
            for k in range(4):
                ft = fr.at(turn=TAU * k / 4 + math.pi / 4).at(r + 0.4)
                S.add(Lathe(ft, T, T + hb - 1.5, cyl(1.15), white))
                S.add(Lathe(ft, T + hb - 1.5, T + hb + 3.5, cone(1.3, 0.1), conec))
                fd = fr.at(turn=TAU * k / 4)
                S.add(Roof(fd.at(r - 1.6, 0, 0, 0), 0, 1.8, -0.8, 0.8, T + hb + 2.0, 1.6, white2))
                S.add(Box(fd, r - 1.4, r + 0.1, -0.8, 0.8, T + hb + 0.6, T + hb + 2.0, white2))


def matthias(S, ctx, plan):
    """Mátyás-templom (rebuilt by Frigyes Schulek, 1874-96): built whole in landmarks_matthias.py."""
    import landmarks_matthias
    landmarks_matthias.build(S, ctx, plan)


def matthias_parts(osm):
    import landmarks_matthias
    return landmarks_matthias.parts(osm)


# ------------------------------------------------------------------------------------------------ domes
def basilica(S, ctx, plan):
    """Szent István-bazilika (Hild, Ybl, Kauser; 1851-1905): the dome on a colonnaded drum, 96 m to the cross, two bell
    towers with clock stages and green copper cupolas, and between them the pedimented west front."""
    P, area = ctx["P"], ctx["area"]
    b0 = feat_base(ctx, BASILICA)
    stone, stone2 = P("#efe6d0"), P("#ded3ba")
    cu, cu2 = P("#4f7062", ROOF), P("#6e8f80", ROOF)
    win = P("#34363c", WINDOW)
    gold = P("#d4ad55", METAL)
    dg = area[443384185][3]
    fr = Frame(dg.centroid.x, dg.centroid.y, b0, 0)
    S.add(Lathe(fr, 36, 58.5, cyl(13.4), stone))
    for k in range(32):
        a = TAU * k / 32
        S.add(Lathe(fr.at(turn=a).at(14.6), 40, 53.5, cyl(0.5), stone2))
    S.add(Lathe(fr, 39, 40, cyl(15.5), stone2))
    S.add(Lathe(fr, 53.5, 55.5, cyl(15.6), stone, inner=1.6))
    S.add(Lathe(fr, 55.5, 56.6, cyl(15.3), stone2, inner=0.5))
    for k in range(16):
        fk = fr.at(turn=TAU * (k + 0.5) / 16)
        S.add(Arch(fk, 12.8, 13.5, 0, 1.0, 44.0, 50.0, win, mode="paint", targets=[stone]))
    S.add(Lathe(fr, 58.5, 59.5, cyl(13.8), stone2))

    def dcol(u, v, w):
        th = np.mod(np.arctan2(v, u), TAU / 16)
        r = np.hypot(u, v)
        return np.where(np.minimum(th, TAU / 16 - th) * r < 0.45, cu2, cu).astype(np.uint16)
    S.add(Lathe(fr, 59.5, 79.5, dome(13.6, p=2.0, top=3.4), dcol))
    for k in range(8):
        fk = fr.at(turn=TAU * (k + 0.5) / 8)
        S.add(Box(fk, 11.0, 12.9, -0.7, 0.7, 63.0, 65.2, stone))
        S.add(Box(fk, 12.6, 13.0, -0.4, 0.4, 63.4, 64.8, win))
    S.add(Lathe(fr, 79.5, 80.5, cyl(3.9), stone2))
    S.add(Lathe(fr, 80.5, 86.0, cyl(2.4), win))
    for k in range(8):
        S.add(Lathe(fr.at(turn=TAU * k / 8).at(3.2), 80.5, 86.0, cyl(0.42), stone))
    S.add(Lathe(fr, 86.0, 87.3, cyl(3.9), stone2))
    S.add(Lathe(fr, 87.3, 91.0, dome(3.4, p=2.0), cu))
    S.add(Ellipsoid(fr.at(0, 0, 91.6), 0.7, 0.7, 0.7, gold))
    S.add(Lathe(fr, 92.0, 96.0, cyl(0.25), gold))
    S.add(Box(fr, -0.2, 0.2, -1.1, 1.1, 94.6, 95.0, gold))
    for oid in (1504216920, 1504216921):
        g = area[oid][3]
        ft = Frame(g.centroid.x, g.centroid.y, b0, rect_of(g)[4])
        S.add(Box(ft, -4.6, 4.6, -4.6, 4.6, 64.5, 66.5, stone2))
        S.add(Lathe(ft, 66.5, 71.5, cyl(3.9), stone, n=8, rot=math.pi / 8))
        for k in range(8):
            fk = ft.at(turn=math.pi / 8 + TAU * k / 8)
            S.add(Arch(fk, 3.1, 4.0, 0, 0.75, 67.2, 69.6, mode="carve"))
        S.add(Lathe(ft, 71.5, 72.3, cyl(4.2), stone2, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 72.3, 77.0, lambda t: 4.0 * (1 - t) ** 0.7 * (1 + 0.12 * np.sin(t * math.pi)) + 0.3, cu, n=8, rot=math.pi / 8))
        S.add(Lathe(ft, 77.0, 78.6, cyl(0.7), cu2))
        S.add(Lathe(ft, 78.6, 80.4, cyl(0.2), gold))
        S.add(Box(ft, -0.15, 0.15, -0.6, 0.6, 79.5, 79.8, gold))
        for k in range(4):  # the clock faces
            fk = ft.at(turn=TAU * k / 4)
            S.add(Box(fk, 4.5, 4.9, -1.2, 1.2, 58.5, 60.9, P("#2f3a35")))
            S.add(Box(fk, 4.8, 5.0, -0.25, 0.25, 59.4, 60.4, gold))
    # the west front between the towers: granite steps up from Szent István tér, engaged Corinthian columns in pairs
    # round the deep arched entrance with its gold mosaic, the entablature with "EGO SUM VIA VERITAS ET VITA" and the
    # pediment with its relief, which is the nave's gable (the towers stand 46 m apart; read off the photo, allowing
    # for its upward perspective: columns to ~30 m, the pediment between 34 and 41 m)
    t1, t2 = (np.array(area[i][3].centroid.coords[0]) for i in (1504216920, 1504216921))
    dc = np.array(dg.centroid.coords[0])
    wv = (t1 + t2) / 2 - dc
    wv /= np.linalg.norm(wv)
    fw = Frame(dc[0], dc[1], b0, math.atan2(wv[1], wv[0]))
    uf = float(((np.array(area[BASILICA][3].exterior.coords) - dc) @ wv).max())
    granite, dark, door = P("#b9958a"), P("#2f3a35"), P("#4a3424")
    for k in range(8):
        S.add(Box(fw, uf - 1.0, uf + 4.8 - k * 0.6, -17.0, 17.0, -1.5, (k + 1) * 0.375, granite))
    S.add(Arch(fw, uf - 3.0, uf + 0.5, 0, 4.4, 3.0, 22.0, mode="carve"))
    S.add(Box(fw, uf - 3.2, uf - 2.9, -2.4, 2.4, 3.0, 12.0, door))
    S.add(Box(fw, uf - 3.2, uf - 2.9, -2.8, 2.8, 13.0, 18.5, stone2))
    S.add(Arch(fw, uf - 3.4, uf - 2.9, 0, 4.4, 22.0, 22.0, gold))
    for v in (-13.2, -8.4, -6.0, 6.0, 8.4, 13.2):
        fc = fw.at(uf, v)
        S.add(Box(fc, -1.1, 1.1, -1.1, 1.1, 3.0, 4.2, stone2))
        S.add(Lathe(fc, 4.2, 28.5, cyl(0.85), stone2))
        S.add(Lathe(fc, 28.5, 30.0, cone(0.9, 1.3), stone))
    S.add(Box(fw, uf - 2.0, uf + 1.0, -16.5, 16.5, 30.0, 33.5, stone))
    S.add(Box(fw, uf - 2.0, uf + 1.4, -17.0, 17.0, 33.5, 34.2, stone2))
    S.add(Box(fw, uf + 1.0, uf + 1.1, -10.0, 10.0, 31.2, 32.4,
              lambda u, v, w: np.where((np.mod(v, 1.0) < 0.5) & (np.abs(w - 31.8) < 0.35), gold, dark).astype(np.uint16)))
    S.add(Roof(fw, uf - 6.0, uf + 1.4, -17.0, 17.0, 34.2, 6.8, stone))
    S.add(Roof(fw, uf + 0.5, uf + 1.5, -15.0, 15.0, 34.8, 5.2, 0, mode="carve"))
    for v in (-7.5, -3.8, 0.0, 3.8, 7.5):
        figure(S, fw.at(uf + 0.9, v), 34.9 + (0.4 if v == 0 else 0.0), stone2, wings=False)
    # the towers' west faces: a statue in a niche, then paired windows, each under a small pediment
    for oid in (444306851, 444306852):
        tg = area[oid][3]
        tc = np.array(tg.centroid.coords[0]) - dc
        ut = float(((np.array(tg.exterior.coords) - dc) @ wv).max())
        vt = float(tc @ np.array([-wv[1], wv[0]]))
        S.add(Arch(fw, ut - 0.6, ut + 0.1, vt, 1.1, 9.0, 13.0, dark))
        figure(S, fw.at(ut - 0.3, vt), 9.0, stone2, wings=False)
        for dv in (-0.85, 0.85):
            S.add(Arch(fw, ut - 0.5, ut + 0.1, vt + dv, 0.55, 19.0, 22.5, P("#34363c", WINDOW)))
        for wb in (13.8, 23.4):
            S.add(Roof(fw, ut - 0.2, ut + 0.5, vt - 1.9, vt + 1.9, wb, 1.0, stone2))
    for sv in (-1, 1):
        x, y = fw.xy(uf + 4.0, sv * 18.5)
        ctx["lamp_post"](int(x * F), int(y * F), int(round(ctx["ground_m"](x, y) * F)), 5.0)


def castle_dome(S, ctx, plan):
    """the dome of Buda Castle's central wing (rebuilt after 1945 by István Janáky): a drum with paired columns,
    a green copper dome and lantern over the National Gallery."""
    from osm import to_grid
    from landmarks_city import windows
    P = ctx["P"]
    b0 = feat_base(ctx, PALACE)
    win = P("#34363c", WINDOW)
    f = ctx["feats"].get(str(PALACE))
    if f is not None:  # the palace's storeys: rows of tall windows on every wall, the court's included
        rows = [(-3.6, -0.8), (1.6, 4.8), (6.6, 10.6), (12.4, 15.8), (17.6, 20.6), (22.2, 24.4)]
        windows(S, f["geom"], b0, rows, [f["wall"]], win, every=3.8, half=0.7, min_len=5.0, arch=False)
    x, y = to_grid(19.03968, 47.49614)
    fr = Frame(x, y, b0 + 8.0, 0)  # the drum stands clear of the wings' roofs (33 m over the palace's foot)
    stone, stone2 = P("#e7e0cd"), P("#d8d0bb")
    cu, cu2 = P("#5f8f7c", ROOF), P("#7aa694", ROOF)
    gold = P("#d4ad55", METAL)
    S.add(Lathe(fr, 18, 34.5, cyl(10.6), stone))
    for k in range(16):
        a = TAU * k / 16
        for da in (-0.045, 0.045):
            S.add(Lathe(fr.at(turn=a + da).at(11.5), 22.5, 32.0, cyl(0.45), stone2))
        fk = fr.at(turn=a + TAU / 32)
        S.add(Arch(fk, 10.0, 10.7, 0, 0.9, 24.5, 29.5, win, mode="paint", targets=[stone]))
    S.add(Lathe(fr, 21.5, 22.5, cyl(12.2), stone2))
    S.add(Lathe(fr, 32.0, 34.0, cyl(12.3), stone))
    S.add(Lathe(fr, 34.0, 34.8, cyl(11.4), stone2))

    def dcol(u, v, w):
        th = np.mod(np.arctan2(v, u), TAU / 16)
        r = np.hypot(u, v)
        return np.where(np.minimum(th, TAU / 16 - th) * r < 0.42, cu2, cu).astype(np.uint16)
    S.add(Lathe(fr, 34.8, 50.0, dome(11.0, p=1.9, top=2.4), dcol))
    for k in range(4):
        fk = fr.at(turn=TAU * k / 4 + math.pi / 4)
        S.add(Box(fk, 8.4, 10.4, -0.8, 0.8, 38.0, 40.6, stone))
        S.add(Lathe(fk.at(10.3, 0, 0, 0).at(turn=0), 38.4, 40.2, cyl(0.5), win))
    S.add(Lathe(fr, 50.0, 54.5, cyl(2.4), stone))
    for k in range(8):
        fk = fr.at(turn=TAU * k / 8 + math.pi / 8)
        S.add(Arch(fk, 1.7, 2.5, 0, 0.5, 50.8, 53.0, mode="carve"))
    S.add(Lathe(fr, 54.5, 55.2, cyl(2.8), stone2))
    S.add(Lathe(fr, 55.2, 57.4, dome(2.5), cu))
    S.add(Lathe(fr, 57.2, 59.2, cyl(0.22), gold))
    S.add(Ellipsoid(fr.at(0, 0, 59.4), 0.45, 0.45, 0.45, gold))


LIBERTY_SIDES = (4548957054, 4548957055)  # the Liberty Statue's two side figures


def liberty_statue(S, ctx, plan):
    """Szabadság-szobor (Zsigmond Kisfaludi Strobl, 1947) on Gellért Hill: a 14 m bronze woman holding a palm leaf
    over her head, on a 26 m limestone pedestal, with two bronze figures at its foot."""
    P = ctx["P"]
    node = next(p for oid, t, p in ctx["osm"].nodes if t.get("wikidata") == "Q933182" or t.get("name") == "Szabadság-szobor")
    z0 = ctx["ground_m"](node.x, node.y)
    # it faces down the Citadella's east cut, between its two side figures (OSM's nodes)
    sides = [np.array([p.x, p.y]) for oid, t, p in ctx["osm"].nodes if oid in LIBERTY_SIDES]
    if len(sides) == 2:
        fwd = (sides[0] + sides[1]) / 2 - (node.x, node.y)
        ang = math.atan2(fwd[1], fwd[0])
    else:
        ang = grid_angle(113, ctx["theta"])
    fr = Frame(node.x, node.y, z0, ang)
    st, st2 = P("#ddd4bf"), P("#cbc1a9")
    br = P("#56665b", METAL)
    # the base: a sheer back 3.5 m behind the centre (OSM's retaining wall), steps down to the front and the sides
    S.add(Box(fr, -3.5, 7.5, -7.5, 7.5, -5, 0.5, st2))
    S.add(Box(fr, -3.5, 6.0, -6.5, 6.5, 0.5, 1.1, st))
    S.add(Box(fr, -3.5, 4.8, -5.2, 5.2, 1.1, 1.7, st2))
    S.add(TBox(fr, 2.4, 3.3, 1.9, 2.6, 1.7, 26.5, st))
    S.add(Box(fr, -2.2, 2.2, -2.9, 2.9, 26.5, 27.2, st2))
    # the shaft's broad foot, the block in front that held the Soviet soldier (the 1990 inscription), and on the shaft
    # above it the white cross of 2025
    S.add(Box(fr, -2.3, 2.1, -4.6, 4.6, 1.7, 12.0, st))
    S.add(Box(fr, 1.5, 4.2, -2.2, 2.2, 1.7, 10.0, st))
    S.add(Box(fr, 1.8, 2.7, -0.45, 0.45, 10.0, 22.0, P("#f1efe9")))
    S.add(Box(fr, 1.8, 2.65, -2.0, 2.0, 18.6, 19.4, P("#f1efe9")))
    f = fr.at(0, 0, 27.2)  # the figure faces +u; her robe blows back (-u)
    S.add(Lathe(f, 0, 8.4, lambda t: 1.75 - 0.8 * t, br))
    S.add(Lathe(f.at(-0.9, 0, 0), 0, 7.6, lambda t: 1.3 - 0.85 * t, br))
    S.add(Lathe(f.at(-1.6, 0.4, 0), 0, 4.0, lambda t: 0.8 - 0.5 * t, br))
    S.add(TBox(f, 0.75, 1.05, 0.6, 0.98, 8.4, 11.2, br))
    S.add(Lathe(f, 11.2, 11.7, cyl(0.32), br))
    S.add(Ellipsoid(f.at(0.05, 0, 12.25), 0.55, 0.52, 0.66, br))
    for sv in (-1, 1):  # arms raised in a Y, the hands holding the leaf
        S.add(Capsule(f, (0, sv * 0.9, 10.8), (0.15, sv * 1.35, 12.9), 0.36, br))
        S.add(Capsule(f, (0.15, sv * 1.35, 12.9), (0.25, sv * 1.6, 14.2), 0.3, br))
    # the palm leaf: a long frond held level over her head, its tips drooping, leaflets along both edges
    S.add(Capsule(f, (0.3, -4.6, 13.9), (0.3, -1.6, 14.45), 0.3, br))
    S.add(Capsule(f, (0.3, -1.6, 14.45), (0.3, 1.8, 14.45), 0.32, br))
    S.add(Capsule(f, (0.3, 1.8, 14.45), (0.3, 3.4, 14.0), 0.28, br))
    for k in np.arange(-4.2, 3.2, 0.55):
        for su in (-1, 1):
            z0 = 14.45 - 0.12 * max(0.0, abs(k + 0.6) - 2.5)
            S.add(Capsule(f, (0.3, k, z0), (0.3 + su * 0.95, k - 0.35, z0 - 0.5), 0.17, br))
    feet = [fr.uv(*p_) for p_ in sides] if len(sides) == 2 else [(9.1, -9.2), (9.1, 9.2)]
    for u_, v_ in feet:  # the two bronze figures on their own plinths at the foot of the front steps
        sv = 1 if v_ > 0 else -1
        zf = ctx["ground_m"](*fr.xy(u_, v_)) - fr.oz
        S.add(Box(fr.at(u_, v_, 0), -1.2, 1.2, -1.2, 1.2, zf - 1.5, zf + 2.8, st))
        g_ = fr.at(u_, v_, zf + 2.8)
        S.add(Lathe(g_, 0, 4.2, lambda t: 0.8 - 0.25 * t, br))
        S.add(Ellipsoid(g_.at(0, 0, 4.6), 0.4, 0.38, 0.47, br))
        S.add(Capsule(g_, (0, sv * 0.45, 3.9), (0.35, sv * 0.7, 6.0), 0.36, br))


def heroes_square(S, ctx, plan):
    """Hősök tere's Millennium Monument (Albert Schickedanz, György Zala; 1896-1929): the Archangel Gabriel on a
    36 m column over the seven chieftains, and two quadrant colonnades with statues, chariots on their ends."""
    P, area = ctx["P"], ctx["area"]
    mon = area[MILLENNIUM][3]
    st, st2 = P("#e2dccb"), P("#d0c8b3")
    br = P("#3f5a4c", METAL)
    gold = P("#d4ad55", METAL)
    polys = sorted(getattr(mon, "geoms", [mon]), key=lambda g: -g.length / max(g.area, 1))
    col_xy = plan.gabriel[2].centroid if plan.gabriel else min(polys, key=lambda g: g.length / g.area).centroid
    z0 = ctx["ground_m"](col_xy.x, col_xy.y)
    for g in polys:
        cx, cy, L1, L2, ang = rect_of(g)
        if L1 < 25:  # the chieftains' plinth
            fr = Frame(cx, cy, z0, ang)
            S.add(Poly(g, z0 - 2, z0 + 1.2, st2))
            S.add(Poly(g.buffer(-1.0), z0 + 1.2, z0 + 4.0, st))
            for k in range(7):
                a = TAU * k / 7
                fh = fr.at(math.cos(a) * 4.2, math.sin(a) * 4.8, 4.0, a)
                S.add(Ellipsoid(fh.at(0, 0, 1.3), 1.4, 0.55, 0.75, br))
                S.add(Capsule(fh, (0.9, 0, 1.4), (1.6, 0, 2.4), 0.35, br))
                S.add(Capsule(fh, (0, 0, 1.8), (0, 0, 3.2), 0.38, br))
                S.add(Ellipsoid(fh.at(0, 0, 3.45), 0.28, 0.28, 0.32, br))
            continue
        S.add(Poly(g, z0 - 2, z0 + 2.4, st2))
        S.add(Poly(g.buffer(-0.5), z0 + 10.6, z0 + 12.4, st))
        S.add(Poly(g, z0 + 12.4, z0 + 13.0, st2))
        for a, b, n in ring_segments(g, 2.0):
            fr2 = seg_frame(a, b, n, 0)
            L = float(np.hypot(*(b - a)))
            for t_ in np.arange(1.2, L - 0.6, 3.0):
                S.add(Lathe(fr2.at(t_, 0.9), z0 + 2.4, z0 + 10.6, lambda t: 0.5 + 0.12 * (t > 0.92), st))
            if L > 6:
                for t_ in np.arange(2.7, L - 1.5, 6.0):
                    fs = fr2.at(t_, 2.2, z0 + 2.4)
                    S.add(Lathe(fs, 0, 1.0, cyl(0.6), st2))
                    S.add(Lathe(fs, 1.0, 3.0, lambda t: 0.45 - 0.12 * t, br))
                    S.add(Ellipsoid(fs.at(0, 0, 3.3), 0.25, 0.25, 0.3, br))
        # the pavilions at the colonnade's ends, each with a bronze group on top
        c = np.array(g.exterior.coords)
        far = max(((i, j) for i in range(len(c)) for j in range(i)), key=lambda ij: np.hypot(*(c[ij[0]] - c[ij[1]])))
        for e in far:
            pv = g.intersection(Point(*c[e]).buffer(6.5))
            if pv.is_empty:
                continue
            S.add(Poly(pv, z0 + 2.4, z0 + 14.5, st))
            S.add(Poly(pv.buffer(0.4), z0 + 14.5, z0 + 15.2, st2))
            pc = pv.centroid
            fh = Frame(pc.x, pc.y, z0 + 15.2, ang)
            S.add(Box(fh, -2.0, 2.0, -1.0, 1.0, 0, 1.6, br))
            S.add(Ellipsoid(fh.at(1.2, 0, 2.2), 1.3, 0.5, 0.8, br))
            S.add(Capsule(fh, (-0.8, 0, 1.6), (-0.6, 0, 4.0), 0.4, br))
            S.add(Capsule(fh, (-0.6, 0, 3.4), (0.4, 0.9, 4.6), 0.2, br))
    # Gabriel's column: a Corinthian shaft on a stepped base, the globe and the archangel with the holy crown
    fc = Frame(col_xy.x, col_xy.y, z0, 0)
    S.add(Lathe(fc, 4.0, 6.0, cyl(2.4), st2, n=4, rot=math.pi / 4))
    S.add(Lathe(fc, 6.0, 33.0, lambda t: 1.15 - 0.22 * t, st))
    S.add(Lathe(fc, 6.0, 8.5, cyl(1.5), br))
    S.add(Lathe(fc, 33.0, 34.6, cone(1.0, 1.7), br))
    S.add(Lathe(fc, 34.6, 35.2, cyl(1.8), st2, n=4, rot=math.pi / 4))
    S.add(Ellipsoid(fc.at(0, 0, 35.9), 0.75, 0.75, 0.75, gold))
    S.add(Lathe(fc, 36.4, 39.2, lambda t: 0.55 - 0.2 * t, br))
    S.add(Ellipsoid(fc.at(0, 0, 39.5), 0.28, 0.28, 0.33, br))
    for sv in (-1, 1):
        S.add(Capsule(fc, (0, sv * 0.3, 38.6), (-0.35, sv * 1.6, 40.6), 0.3, br))
    S.add(Capsule(fc, (0, 0.4, 38.8), (0.35, 0.6, 40.4), 0.15, br))
    S.add(Ellipsoid(fc.at(0.4, 0.6, 40.6), 0.25, 0.25, 0.2, gold))


# ------------------------------------------------------------------------------------------------ Pest
def market_hall(S, ctx, plan):
    """the Great Market Hall (Samu Pecz, 1897): yellow brick in red bands, a long hall under a roof of Zsolnay
    tiles with a glazed ridge, and a gabled front with two turreted corner towers on Fővám tér."""
    P, area = ctx["P"], ctx["area"]
    g = area[MARKET][3]
    cx, cy, L, Wd, ang = rect_of(g)
    b0 = ctx["ground_m"](cx, cy)
    fr = Frame(cx, cy, b0, ang)
    brick, band = P("#cfa868"), P("#9e4a33")
    win = P("#34363c", WINDOW)
    tiles = zsolnay(P, ["#7a4a2a", "#d98a2e", "#e8c440", "#3d8a4c", "#e8c440", "#d98a2e"], period=1.0, slope=1.0)

    def walls(u, v, w):  # in a frame on the ground (oz 0)
        return np.where(np.mod(w - b0, 3.0) < 0.5, band, brick).astype(np.uint16)

    def walls_rel(u, v, w):  # in a frame standing on b0
        return np.where(np.mod(w, 3.0) < 0.5, band, brick).astype(np.uint16)
    S.add(Poly(g, b0 - 2, b0 + 16.0, walls))
    for a, b, n in ring_segments(g, 6.0):
        fr2 = seg_frame(a, b, n, 0)
        Ls = float(np.hypot(*(b - a)))
        for t_ in np.arange(3.0, Ls - 2.0, 6.0):
            S.add(Arch(fr2.at(t_, 0, 0, math.pi / 2), -0.2, 0.6, 0, 1.3, b0 + 3.0, b0 + 10.0, win, mode="paint", targets=[brick, band]))
    front = 1 if ctx["ground_m"](*fr.xy(L / 2 + 15, 0)) <= ctx["ground_m"](*fr.xy(-L / 2 - 15, 0)) else -1
    glass = P("#a9bcc6", GLASS)

    def roof(u, v, w):
        return np.where(np.abs(v) < 2.6, glass, tiles(u, v, w)).astype(np.uint16)
    S.add(Roof(fr, -L / 2 + 0.5, L / 2 - 0.5, -Wd / 2 + 0.5, Wd / 2 - 0.5, 16.0, 13.5, roof))
    # the front: a brick gable, and two towers at its corners (the gable end facing Fővám tér)
    uf = front * (L / 2 - 1.5)
    S.add(Roof(fr, *sorted((uf, uf + front * 1.6)), -Wd / 2 + 0.5, Wd / 2 - 0.5, 16.0, 14.5, walls_rel))
    S.add(Arch(fr.at(uf + front * 0.8, 0, 0, 0), -1.5, 1.5, 0, 4.0, 13.0, 21.0, win, mode="paint", targets=[brick, band]))
    for sv in (-1, 1):
        ft = fr.at(uf, sv * (Wd / 2 - 3.5))
        S.add(Box(ft, -3.6, 3.6, -3.6, 3.6, -2, 24.0, walls_rel))
        S.add(Lathe(ft, 24.0, 36.0, cone(3.9, 0.15), tiles, n=4, rot=math.pi / 4))
        for su in (-1, 1):
            for sw in (-1, 1):
                pinnacle(S, ft.at(su * 3.4, sw * 3.4), 24.0, 4.0, 0.45, brick)


def synagogue(S, ctx, plan):
    """the Dohány Street Synagogue (Ludwig Förster, 1859): Moorish, in yellow and red brick stripes, with two 43 m
    octagonal towers under gilded onion domes."""
    P, area = ctx["P"], ctx["area"]
    g = area[SYNAGOGUE][3]
    b0 = feat_base(ctx, SYNAGOGUE)
    yellow, red = P("#d9b77c"), P("#a8503a")
    gold = P("#c9a34e", METAL)

    def stripes(u, v, w):
        return np.where(np.mod(w - b0, 1.0) < 0.5, red, yellow).astype(np.uint16)
    f = ctx["feats"].get(str(SYNAGOGUE))
    if f is not None:
        S.add(Poly(g.buffer(0.6), b0 - 2, b0 + 40, stripes, mode="paint", targets=[f["wall"]]))
    for oid in (223530621, 223530622):
        tg = area[oid][3]
        fr = Frame(tg.centroid.x, tg.centroid.y, b0, 0)
        S.add(Lathe(fr, -2, 31.0, cyl(2.4), stripes, n=8, rot=math.pi / 8))
        S.add(Lathe(fr, 26.0, 26.6, cyl(2.9), yellow, n=8, rot=math.pi / 8))
        for k in range(8):
            S.add(Arch(fr.at(turn=math.pi / 8 + TAU * k / 8), 1.7, 2.6, 0, 0.55, 27.2, 29.8, mode="carve"))
        S.add(Lathe(fr, 31.0, 31.6, cyl(2.7), yellow, n=8, rot=math.pi / 8))
        S.add(Lathe(fr, 31.6, 40.6, onion(1.9, 2.9, 0.4), gold))
        S.add(Lathe(fr, 40.4, 43.0, cyl(0.2), gold))
        S.add(Ellipsoid(fr.at(0, 0, 42.0), 0.4, 0.4, 0.4, gold))


def puskas_arena(S, ctx, plan):
    """the Puskás Aréna (György Skardelli, 2019): a 316 x 259 m oval, 51 m high. A stainless-steel mesh facade leans
    out as it rises, between 30 white lattice pylons that echo the 1953 Népstadion's; above it a dark gap with white
    brackets, then the thin white edge of a roof that covers all but the lower tier and the pitch. Inside, three tiers
    of red seats (28, 22 and 25 rows) with rows of glazed boxes between them; a glazed ground floor."""
    P, area = ctx["P"], ctx["area"]
    gs, low = area[PUSKAS][3], area[PUSKAS_LOW][3]
    ext = shapely.Polygon(gs.exterior)
    hole = shapely.Polygon(gs.interiors[0])
    pitch = shapely.Polygon(low.interiors[0])
    b0 = feat_base(ctx, PUSKAS)
    x0, y0, x1, y1 = ext.bounds
    x0f, y0f = int(math.floor(x0 * F)) - 2, int(math.floor(y0 * F)) - 2
    nx, ny = int(math.ceil(x1 * F)) + 2 - x0f, int(math.ceil(y1 * F)) + 2 - y0f
    X, Y = np.meshgrid((np.arange(nx) + x0f + 0.5) / F, (np.arange(ny) + y0f + 0.5) / F)
    pts = shapely.points(X.ravel(), Y.ravel())
    ring = LineString(ext.exterior.coords)

    def dist(b):
        return shapely.distance(b, pts).reshape(ny, nx).astype(np.float32)
    inn = shapely.contains_xy(ext, X, Y)
    d_out = np.where(inn, dist(ring), -1).astype(np.float32)             # in from the roof edge
    in_hole = shapely.contains_xy(hole, X, Y)
    d_low = np.where(in_hole, -1, 1) * dist(hole.exterior)              # out from the grandstand's inner edge
    in_pitch = shapely.contains_xy(pitch, X, Y)
    d_pitch = np.where(in_pitch, -1, 1) * dist(pitch.exterior)          # out from the pitch
    s_ = np.zeros_like(d_out)
    near = inn & (d_out < 14)
    s_[near] = shapely.line_locate_point(ring, pts.reshape(ny, nx)[near])
    cx, cy = ext.centroid.coords[0]
    th = np.arctan2(Y - cy, X - cx).astype(np.float32)
    L = ring.length
    pyl = L / 30
    pc = pitch.centroid.coords[0]
    pang = rect_of(pitch)[4]
    pu = ((X - pc[0]) * math.cos(pang) + (Y - pc[1]) * math.sin(pang)).astype(np.float32)  # along the pitch
    fields = dict(d_out=d_out, d_low=d_low, d_pitch=d_pitch, s=s_, th=th, pu=pu)

    mesh, mesh_band = P("#979b9c", METAL), P("#7a7f81", METAL)
    grass, grass2 = P("#4f8a3c"), P("#5e9a46")
    white, lattice_dk = P("#ecebe6"), P("#a3a5a3")
    fascia, roof_c, roof_in, truss = P("#f1f0eb"), P("#cfcac2", ROOF), P("#b7b9b8", ROOF), P("#8e9294", METAL)
    glass = P("#2f3a44", WINDOW)
    conc = P("#b9b4aa")
    seat, seat2, aisle = P("#a8282d"), P("#922227"), P("#8f8c86")

    def fac(w):  # the mesh's distance in from the roof edge: it leans out as it rises, 6.4 m at 7 m to 3 m at 41 m
        return 3.0 + (41.0 - np.clip(w, 7.0, 41.0)) * 0.10

    def fn(f, wa):
        w = wa - b0
        do, dl, dp, sv, t = f["d_out"][None], f["d_low"][None], f["d_pitch"][None], f["s"][None], f["th"][None]
        out = np.zeros(np.broadcast_shapes(w.shape, do.shape), np.uint16)

        def put(m, val):
            out[m] = np.broadcast_to(val, out.shape)[m]
        wt = 51.0 - 4.0 * np.clip(do / 70.0, 0, 1)                      # roof top: 51 m at the edge, 47 m inside
        # stands: the lower tier between pitch and grandstand, then middle and upper tiers with boxes between them
        q_l = dp / np.maximum(dp - dl, 1e-3)                              # 0 at the pitch, 1 at the grandstand
        ws = np.where(dl < 0, 1.0 + 11.0 * np.clip(q_l, 0, 1),
             np.where(dl < 3, 16.0,
             np.where(dl < 21, 16.0 + (dl - 3) * 0.58,
             np.where(dl < 24, 30.0, np.minimum(30.0 + (dl - 24) * 0.62, 43.6)))))
        stand = (dp > 0) & (do > 0) & (w >= -1) & (w < ws) & (do > fac(w) + 1.0)
        turf = (dp <= 0) & (w >= -1) & (w < 0)                            # the pitch and its run-off, mown in stripes
        put(turf, np.where(np.mod(f["pu"][None], 11.0) < 5.5, grass, grass2))
        rows = np.mod(np.floor(w * 2), 2) == 0
        ais = np.mod(t * 140.0, 15.0) < 1.2
        top = stand & (w >= ws - 0.75) & (((dl < 0) & (dp > 1.5)) | ((dl >= 3) & (dl < 21)) | ((dl >= 24) & (dl < 46)))
        out[stand] = conc
        put(top, np.where(ais, aisle, np.where(rows, seat, seat2)))
        boxes = stand & (((dl >= 0) & (dl < 1) & (w >= 12)) | ((dl >= 21) & (dl < 22) & (w >= 26.4)))
        out[boxes] = glass
        # the roof: over the grandstand and 6 m out over the lower tier; a lighter, translucent band at its inner edge
        roof = (do >= 0) & (dl > -6) & (w < wt) & (w >= wt - 2.5)
        rc = np.where(dl < 14, roof_in, roof_c)
        rc = np.where((np.mod(t * 140.0, 9.0) < 0.6) & (w >= wt - 0.5), truss, rc)
        rc = np.where(dl < -5, truss, rc)
        put(roof, rc)
        edge = (do >= 0) & (do < 2.5) & (w >= wt - 4.5) & (w < wt)
        out[edge] = fascia
        # under the roof edge: an open gap with white brackets every 8 m
        brk = (do >= 0) & (do < fac(41) + 1) & (w >= 41) & (w < wt - 4.5) & (np.mod(sv, 8.0) < 1.0)
        out[brk] = white
        # the facade: steel mesh with floor lines, and the lattice pylons standing proud of it
        f0 = fac(w)
        msh = (do >= f0) & (do < f0 + 1.0) & (w >= 7) & (w < 41)
        put(msh, np.where(np.mod(w, 4.5) < 0.5, mesh_band, mesh))
        a = np.mod(sv + pyl / 2, pyl) - pyl / 2
        pyl_m = (np.abs(a) < 3.5) & (do >= f0 - 0.6) & (do < f0 + 1.0) & (w >= 0) & (w < 40) & (do > 0)
        diag = (np.abs(np.mod(a + w, 2.4) - 1.2) < 0.45) | (np.abs(np.mod(a - w, 2.4) - 1.2) < 0.45) | (np.abs(a) > 2.9) | (w >= 38.5)
        put(pyl_m, np.where(diag, white, lattice_dk))
        # the glazed ground floor, set back under the mesh
        base = (do >= 8) & (do < 9) & (w >= 0) & (w < 7) & ~pyl_m
        out[base] = glass
        behind = (do >= 9) & (w >= -1) & (w < 7) & (dl > 0) & ~stand
        out[behind] = conc
        mass = (do >= f0 + 1.0) & (w >= 7) & (w < 41) & (dl >= 46)    # concourses between the upper tier and the facade
        out[mass & (out == 0)] = conc
        return out

    def level(f, wa):  # the bowl is flat: clear the ground (and anything on it) that stands above the pitch
        return np.broadcast_to(((f["d_low"] < 0) & ((wa - b0) >= 0))[None] if np.ndim(wa) == 0 else
                               (f["d_low"][None] < 0) & ((wa - b0) >= 0), np.broadcast_shapes(np.shape(wa), (1,) + f["d_low"].shape)).astype(np.uint16)
    S.add(Field(x0f, y0f, fields, b0, b0 + 6, level, mode="carve"))
    S.add(Field(x0f, y0f, fields, b0 - 1, b0 + 52, fn))

