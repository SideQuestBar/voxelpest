"""The map as a Minecraft world: 1 block = 1 m, built from the viewer's level-2 tiles (1 m cells).

    uv run python scripts/minecraft.py                 # -> build/minecraft/
    uv run python scripts/minecraft.py --only 4:6,4:6  # a few regions (rx0:rx1,rz0:rz1), for a quick look
    uv run python scripts/minecraft.py --landmarks-only  # only the teleports (after changing the viewer's views)

Reads web/public/data (meta.json, tiles/2) and scripts/minecraft_blocks.json (scripts/minecraft_blocks.py measures the
blocks' colours from the game's textures). Writes

    build/minecraft/world/dimensions/minecraft/overworld/region/r.X.Z.mca   the world (Anvil, Minecraft 26.x layout)
    build/minecraft/landmarks.yml    the plugin's teleports: every view of the web viewer, on the ground by its subject
    build/minecraft/map.yml          the map's bounds, spawn, height offset and build time (for the plugin)
    build/minecraft/preview.png      the world from above, one pixel per 4 blocks, from the chosen blocks' colours

Coordinates: x = the grid's column (metres east-north-east), z = its row (metres south-south-east), so Minecraft's
north is the grid's -row, 41.5 degrees west of true north. Heights: y = metres above sea level - 36 (the Danube's
surface at y 62, as the sea in a normal world); below the map's base, stone and deepslate down to bedrock.

Every palette colour becomes the nearest block (CIELAB) of a family chosen by its material: facades from concrete,
terracotta, stone, sandstone, planks...; roofs from terracotta, tiles, copper; leaves (persistent); lamps from
froglights and lanterns. Flat facades (OSM's walls) get windows the way the viewer's shader draws them, glass in front
of a dark interior, a few lit at night. Thin things (poles, spires, cables) become walls and iron bars.
"""
import argparse
import gzip
import io
import json
import math
import os
import struct
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "web" / "public" / "data"
BLOCKS = ROOT / "scripts" / "minecraft_blocks.json"
N, S = 128, 130          # tile cells, with the apron
RW = 512                 # blocks per region side
TPR = RW // N            # tiles per region side
Y_BOTTOM = -64
SEA = 36                 # y = metres above sea level - SEA
BIOME = "minecraft:plains"

# web/src/meta.ts MAT
SOLID, WALL, GLASS, LEAF, WATER, LAMP, METAL, PKIN, GRASS, MARK, SOIL, CAR, ROOF, CONCRETE, CLOCK, BRONZE, SIGN, JET, \
    SIGNBAND, RIBBON, CLASSIC, WINDOW, TENEMENT = range(23)
FAMILY = {LEAF: "leaf", LAMP: "lamp", GLASS: "glass", WINDOW: "window", ROOF: "roof", GRASS: "grass",
          SOIL: "soil", METAL: "metal", BRONZE: "metal"}
TOP_FACE = {ROOF, GRASS, SOIL, MARK}   # seen from above: match the block's top texture


# ------------------------------------------------------------------------------------------------ colours
def lab(rgb):
    c = np.asarray(rgb, np.float64) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


class States:
    """every block state used, interned: index -> (id, properties); index 0 is air."""

    def __init__(self):
        self.list, self.index = [], {}
        self.add("minecraft:air")

    def add(self, name, **props):
        key = (name if ":" in name else "minecraft:" + name, tuple(sorted(props.items())))
        if key not in self.index:
            self.index[key] = len(self.list)
            self.list.append(key)
        return self.index[key]


class Blocks:
    def __init__(self, meta):
        info = json.loads(BLOCKS.read_text())
        self.version, self.data_version = info["version"], info["data_version"]
        self.blocks = info["blocks"]
        self.st = States()
        st = self.st
        self.fam = {}
        for name, b in self.blocks.items():
            for g in b["groups"]:
                self.fam.setdefault(g, []).append(name)
        pal = meta["palette"]
        n = len(pal)
        self.base = np.zeros(n, np.int32)          # the block of each palette colour
        self.glass_front = np.zeros(n, np.int32)   # GLASS / WINDOW: the pane on a facade
        self.mat = np.array([e[3] for e in pal], np.int16)
        self.lantern = st.add("lantern", hanging="false", waterlogged="false")
        self.thin_kind = np.zeros(n, np.int8)      # thin things: 1 a wall (a post), 2 iron bars, 3 a lantern
        self.thin_wall = [None] * n
        self.water = st.add("water")
        self.stone, self.deep, self.bedrock = st.add("stone"), st.add("deepslate", axis="y"), st.add("bedrock")
        self.dark = st.add("black_concrete")
        self.lit = [st.add("shroomlight"), st.add("ochre_froglight", axis="y"), st.add("pearlescent_froglight", axis="y")]
        self.pane = {k: st.add(f"{k}_stained_glass") for k in ("gray", "light_gray", "black")}
        self.spandrel = st.add("gray_concrete")
        for i, (r, g, b, m) in enumerate(pal):
            if i == 0:
                continue
            fam = FAMILY.get(m, "generic")
            face = "top" if m in TOP_FACE else "side"
            name = self.nearest((r, g, b), fam, face)
            self.base[i] = self.state(name)
            if m in (GLASS, WINDOW):
                self.glass_front[i] = self.state(self.nearest((r, g, b), "glass" if m == GLASS else "window", "side"))
                self.base[i] = self.state(self.nearest((r, g, b), "generic", "top"))  # a glass building's roof
            if m in (WATER, JET):  # the river, pools, fountains' jets: still water (the plugin stops it flowing)
                self.base[i] = self.water
                self.thin_kind[i] = 4
            elif m == LAMP:
                self.thin_kind[i] = 3
            elif m == METAL and sum((r, g, b)) > 330:
                self.thin_kind[i] = 2
            else:
                self.thin_kind[i] = 1
                self.thin_wall[i] = self.nearest_wall((r, g, b))  # its state depends on its neighbours
        self.base = self.base.astype(np.uint16)
        self.glass_front = self.glass_front.astype(np.uint16)

    def state(self, name):
        if name == "water":
            return self.water
        if name.endswith("_leaves"):
            return self.st.add(name, distance="7", persistent="true", waterlogged="false")
        if name in ("deepslate", "bone_block", "ochre_froglight", "pearlescent_froglight", "verdant_froglight"):
            return self.st.add(name, axis="y")
        if name == "grass_block":
            return self.st.add(name, snowy="false")
        return self.st.add(name)

    def nearest(self, rgb, fam, face):
        names = self.fam.get(fam) or self.fam["generic"]
        if fam in ("metal", "roof", "grass", "soil"):  # a family plus the generic blocks, a bit dearer
            extra = [n for n in self.fam["generic"] if n not in names]
        else:
            extra = []
        cand = names + extra
        cols = np.array([self.blocks[n]["top" if face == "top" else "side"] for n in cand])
        d = np.linalg.norm(lab(cols) - lab(rgb), axis=1)
        d[len(names):] += 6.0
        return cand[int(np.argmin(d))]

    def nearest_wall(self, rgb):
        walls = self.fam["wall"]
        cols = np.array([self.blocks[n]["side"] for n in walls])
        return walls[int(np.argmin(np.linalg.norm(lab(cols) - lab(rgb), axis=1)))]


# ------------------------------------------------------------------------------------------------ tiles
def read_tile(path):
    """-> runs (z0, len, pal) with their column index (0 .. S*S-1), the ground, the detail voxels"""
    raw = gzip.decompress(path.read_bytes())
    counts = np.frombuffer(raw, np.uint16, S * S).astype(np.int64)
    ground = np.frombuffer(raw, np.uint8, S * S, offset=S * S * 2).reshape(S, S)
    nr = int(counts.sum())
    runs = np.frombuffer(raw, np.uint16, nr * 3, offset=S * S * 3).reshape(-1, 3).astype(np.int64)
    col = np.repeat(np.arange(S * S), counts)
    det_off = S * S * 3 + nr * 6
    det = np.frombuffer(raw, np.uint16, (len(raw) - det_off) // 2, offset=det_off).reshape(-1, 4).astype(np.int64)
    return runs, col, ground, det


def region_volume(rx, rz, H):
    """the region's cells with a one-cell apron: vol (H, RW+2, RW+2) palette ids, ground (RW+2, RW+2), thin cells"""
    vol = np.zeros((H, RW + 2, RW + 2), np.uint16)
    gr = np.zeros((RW + 2, RW + 2), np.int16)
    thin = np.zeros((H, RW + 2, RW + 2), np.uint16)
    any_tile = False
    for dty in range(-1, TPR + 1):
        for dtx in range(-1, TPR + 1):
            tx, ty = rx * TPR + dtx, rz * TPR + dty
            p = DATA / "tiles" / "2" / f"{tx}_{ty}.bin"
            if not p.exists():
                continue
            runs, col, ground, det = read_tile(p)
            # where this tile's 130 x 130 block lands in the region's 514 x 514 (apron included)
            oy, ox = dty * N, dtx * N
            ys, xs = slice(max(oy, 0), min(oy + S, RW + 2)), slice(max(ox, 0), min(ox + S, RW + 2))
            if ys.start >= ys.stop or xs.start >= xs.stop:
                continue
            inner = 0 <= dtx < TPR and 0 <= dty < TPR
            any_tile |= inner
            cr, cc = col // S + oy, col % S + ox
            keep = (cr >= ys.start) & (cr < ys.stop) & (cc >= xs.start) & (cc < xs.stop)
            if not inner:  # a neighbour: only its rows/columns in the apron
                keep &= (cr == 0) | (cr == RW + 1) | (cc == 0) | (cc == RW + 1)
            r_, c_, ru = cr[keep], cc[keep], runs[keep]
            n = ru[:, 1]
            z = np.repeat(ru[:, 0], n) + (np.arange(int(n.sum())) - np.repeat(np.cumsum(n) - n, n))
            ok = z < H
            vol[z[ok], np.repeat(r_, n)[ok], np.repeat(c_, n)[ok]] = np.repeat(ru[:, 2], n)[ok]
            g = ground[max(-oy, 0):max(-oy, 0) + (ys.stop - ys.start), max(-ox, 0):max(-ox, 0) + (xs.stop - xs.start)]
            gr[ys, xs] = np.maximum(gr[ys, xs], g)
            if inner and len(det):
                dz, dr, dc = det[:, 2] // 2, det[:, 1] // 2 + oy + 1, det[:, 0] // 2 + ox + 1
                ok = (dz < H) & (dr < RW + 2) & (dc < RW + 2)
                thin[dz[ok], dr[ok], dc[ok]] = det[ok, 3]
    thin[vol != 0] = 0
    return (vol, gr, thin) if any_tile else None


# ------------------------------------------------------------------------------------------------ blocks of a region
def hash3(a, b, c):
    h = (a.astype(np.int64) * 73856093) ^ (b.astype(np.int64) * 19349663) ^ (c.astype(np.int64) * 83492791)
    return np.abs(h) % 1000


def shifted(a, d0, d1):
    """a moved by (rows d0, columns d1): out[r, c] = a[r + d0, c + d1], False beyond the edge"""
    out = np.zeros_like(a)
    R, C = a.shape[1], a.shape[2]
    out[:, max(-d0, 0):R - max(d0, 0), max(-d1, 0):C - max(d1, 0)] = a[:, max(d0, 0):R - max(-d0, 0), max(d1, 0):C - max(-d1, 0)]
    return out


DIRS = ((0, 1), (0, -1), (1, 0), (-1, 0))   # east (+x), west, south (+z), north
SIDE = ("east", "west", "south", "north")


def region_blocks(B, vol, gr, thin):
    """palette ids -> block-state ids (uint16), with windows, glass curtain walls and thin things worked out"""
    out = B.base[vol]
    solid = vol != 0
    out[~solid] = 0
    open_ = [shifted(~solid, d0, d1) for d0, d1 in DIRS]   # the neighbour across each face is empty
    for o in open_:
        o &= solid
    exposed = open_[0] | open_[1] | open_[2] | open_[3]
    mat = B.mat[vol]
    cand = exposed & np.isin(mat, (TENEMENT, WALL, CONCRETE, GLASS, WINDOW))
    zi, ri, ci = np.nonzero(cand)
    m = mat[zi, ri, ci]
    lvl = zi - gr[ri, ci].astype(np.int64)
    # the face each cell shows (the first open one) and the coordinate along it
    face = np.full(len(zi), -1, np.int8)
    for k in range(3, -1, -1):
        face = np.where(open_[k][zi, ri, ci], k, face)
    along_x = face >= 2                    # a south or north face runs along x
    u = np.where(along_x, ci, ri)
    # windows on OSM's plain walls, as the viewer's shader draws them
    shop = (lvl >= 1) & (lvl < 4)
    win = np.zeros(len(zi), bool)
    t = m == TENEMENT
    win |= t & np.where(lvl < 4, (lvl >= 1) & (lvl < 3), (lvl % 4 >= 1) & (lvl % 4 < 3)) & (u % 3 == 1)
    w = m == WALL
    win |= w & np.where(shop, u % 5 != 0, (lvl % 3 >= 1) & (u % 3 == 1))
    win |= (m == CONCRETE) & shop & (u % 4 != 0)
    shop_win = win & (lvl < 4)
    gl = (m == GLASS) | (m == WINDOW)
    spandrel = (m == GLASS) & (lvl % 4 == 0) & (lvl > 0)
    pane = win | (gl & ~spandrel)
    out[zi[win], ri[win], ci[win]] = np.where(shop_win[win], B.pane["light_gray"], B.pane["gray"])
    g2 = gl & ~spandrel
    out[zi[g2], ri[g2], ci[g2]] = B.glass_front[vol[zi[g2], ri[g2], ci[g2]]]
    out[zi[spandrel], ri[spandrel], ci[spandrel]] = B.spandrel
    # behind every pane, a dark room; one in ten lit (most shops), glowing through the glass at night
    p = np.nonzero(pane)[0]
    d = np.array(DIRS)[face[p]]
    zr, rr_, cr = zi[p], ri[p] - d[:, 0], ci[p] - d[:, 1]
    ok = (rr_ >= 0) & (rr_ < vol.shape[1]) & (cr >= 0) & (cr < vol.shape[2])
    p, zr, rr_, cr = p[ok], zr[ok], rr_[ok], cr[ok]
    ok = solid[zr, rr_, cr] & ~exposed[zr, rr_, cr]
    p, zr, rr_, cr = p[ok], zr[ok], rr_[ok], cr[ok]
    room = hash3(u[p] // 3, lvl[p] // 3, np.where(along_x[p], ri[p], ci[p]) * 4 + face[p])
    lit = room < np.where(shop_win[p], 650, np.where(m[p] == GLASS, 140, 110))
    kind = np.where(m[p] == GLASS, 2, np.where(shop_win[p], 1, 0))
    out[zr, rr_, cr] = np.where(lit, np.array(B.lit, np.uint16)[kind], B.dark)
    # thin things: posts that join their neighbours, iron bars, lanterns
    zi, ri, ci = np.nonzero(thin)
    if len(zi):
        solid2 = solid | (thin > 0)
        for z_, r_, c_ in zip(zi.tolist(), ri.tolist(), ci.tolist()):
            pid = int(thin[z_, r_, c_])
            k = int(B.thin_kind[pid])
            sides = {}
            for (d0, d1), nm in zip(DIRS, SIDE):
                r2, c2 = r_ + d0, c_ + d1
                sides[nm] = 0 <= r2 < vol.shape[1] and 0 <= c2 < vol.shape[2] and bool(solid2[z_, r2, c2])
            if k == 4:
                out[z_, r_, c_] = B.water
            elif k == 3:
                out[z_, r_, c_] = B.lantern
            elif k == 2:
                out[z_, r_, c_] = B.st.add("iron_bars", waterlogged="false", **{n: str(v).lower() for n, v in sides.items()})
            else:
                out[z_, r_, c_] = B.st.add(B.thin_wall[pid] or "andesite_wall", up="true", waterlogged="false",
                                           **{n: ("low" if v else "none") for n, v in sides.items()})
    return out


# ------------------------------------------------------------------------------------------------ NBT and Anvil
def _s(x):
    b = x.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def nbt(tag, name, payload):
    return bytes([tag]) + _s(name) + payload


def compound(items):
    return b"".join(items) + b"\x00"


def state_nbt(key):
    name, props = key
    items = [nbt(8, "id", _s(name))]
    if props:
        items.append(nbt(10, "properties", compound([nbt(8, k, _s(v)) for k, v in props])))
    return compound(items)


BIOMES = nbt(10, "biomes", compound([nbt(9, "palette", bytes([8]) + struct.pack(">i", 1) + _s(BIOME))]))


def section_nbt(y, blocks, st_bytes):
    """blocks (16, 16, 16) state ids in y, z, x order"""
    flat = blocks.reshape(-1)
    lo, hi = int(flat.min()), int(flat.max())
    if lo == hi:
        pal = [lo]
        data = b""
    else:
        pal, idx = np.unique(flat, return_inverse=True)
        bits = max(4, int(math.ceil(math.log2(len(pal)))))
        vpl = 64 // bits
        nl = -(-4096 // vpl)
        idx = np.concatenate([idx.astype(np.uint64), np.zeros(nl * vpl - 4096, np.uint64)]).reshape(nl, vpl)
        longs = (idx << (np.arange(vpl, dtype=np.uint64) * np.uint64(bits))).sum(1, dtype=np.uint64)
        data = nbt(12, "data", struct.pack(">i", nl) + longs.astype(">u8").tobytes())
        pal = pal.tolist()
    palette = nbt(9, "palette", bytes([10]) + struct.pack(">i", len(pal)) + b"".join(st_bytes(p) for p in pal))
    return compound([nbt(1, "Y", struct.pack(">b", y)), nbt(10, "block_states", compound([palette, data])), BIOMES])


def chunk_nbt(cx, cz, column, ybase, st_bytes, data_version):
    """column (Hc, 16, 16) state ids from y = ybase up, a multiple of 16"""
    secs = []
    for i in range(column.shape[0] // 16):
        secs.append(section_nbt(ybase // 16 + i, column[i * 16:(i + 1) * 16], st_bytes))
    empty_list = bytes([0]) + struct.pack(">i", 0)
    post = bytes([9]) + struct.pack(">i", len(secs)) + b"".join(empty_list for _ in secs)
    body = compound([
        nbt(3, "DataVersion", struct.pack(">i", data_version)),
        nbt(3, "xPos", struct.pack(">i", cx)), nbt(3, "zPos", struct.pack(">i", cz)),
        nbt(3, "yPos", struct.pack(">i", ybase // 16)),
        nbt(8, "Status", _s("minecraft:full")),
        nbt(4, "LastUpdate", struct.pack(">q", 0)), nbt(4, "InhabitedTime", struct.pack(">q", 0)),
        nbt(1, "isLightOn", b"\x00"),
        nbt(9, "sections", bytes([10]) + struct.pack(">i", len(secs)) + b"".join(secs)),
        nbt(9, "block_entities", empty_list), nbt(9, "block_ticks", empty_list), nbt(9, "fluid_ticks", empty_list),
        nbt(9, "PostProcessing", post),
        nbt(10, "structures", compound([nbt(10, "References", compound([])), nbt(10, "starts", compound([]))])),
    ])
    return nbt(10, "", body)


def write_region(path, chunks):
    """chunks: {(lx, lz): compressed bytes}"""
    header, stamps, body = bytearray(4096), bytearray(4096), bytearray()
    sector = 2
    now = int(time.time())
    for (lx, lz), data in chunks.items():
        blob = struct.pack(">IB", len(data) + 1, 2) + data
        n = -(-len(blob) // 4096)
        i = 4 * (lx + 32 * lz)
        header[i:i + 4] = struct.pack(">I", (sector << 8) | n)
        stamps[i:i + 4] = struct.pack(">I", now)
        body += blob + b"\x00" * (n * 4096 - len(blob))
        sector += n
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(bytes(header) + bytes(stamps) + bytes(body))
    tmp.replace(path)


# ------------------------------------------------------------------------------------------------ the job
_B = None


def _init(meta):
    global _B
    _B = Blocks(meta)


def build_region(args):
    rx, rz, H, out_dir, y0, Wb, Db = args
    B = _B
    t0 = time.time()
    rv = region_volume(rx, rz, H)
    if rv is None:
        return rx, rz, 0, 0, None, {}
    vol, gr, thin = rv
    blocks = region_blocks(B, vol, gr, thin)[:, 1:-1, 1:-1]   # drop the apron
    inside = np.zeros((RW, RW), bool)
    inside[:max(min(Db - rz * RW, RW), 0), :max(min(Wb - rx * RW, RW), 0)] = True
    # the column under the map's base: stone, deepslate below y 0, bedrock at the bottom
    ytop = (y0 + H + 15) // 16 * 16
    full = np.zeros((ytop - Y_BOTTOM, RW, RW), np.uint16)
    full[y0 - Y_BOTTOM:y0 - Y_BOTTOM + H] = blocks
    del blocks, vol, thin
    ys = np.arange(Y_BOTTOM, y0)
    fill = np.where(ys < 0, B.deep, B.stone).astype(np.uint16)
    fill[0] = B.bedrock
    full[:y0 - Y_BOTTOM] = np.where(inside[None], fill[:, None, None], 0)
    st_bytes_cache = {}

    def st_bytes(i):
        b = st_bytes_cache.get(i)
        if b is None:
            b = st_bytes_cache[i] = state_nbt(B.st.list[i])
        return b
    chunks = {}
    for lz in range(32):
        for lx in range(32):
            if not inside[lz * 16, lx * 16]:
                continue
            col = full[:, lz * 16:(lz + 1) * 16, lx * 16:(lx + 1) * 16]
            raw = chunk_nbt(rx * 32 + lx, rz * 32 + lz, col, Y_BOTTOM, st_bytes, B.data_version)
            chunks[(lx, lz)] = zlib.compress(raw, 6)
    # what the top looks like (for the preview)
    nz = full != 0
    topi = (full.shape[0] - 1 - np.argmax(nz[::-1], axis=0))
    top = np.take_along_axis(full, topi[None], 0)[0]
    write_region(out_dir / f"r.{rx}.{rz}.mca", chunks)
    used = {int(i) for i in np.unique(full)}
    return rx, rz, len(chunks), time.time() - t0, top[::4, ::4].astype(np.int32), {i: B.st.list[i] for i in used}


# other names /lm understands (accents are optional in the game: "hosok" finds Hősök tere)
ALIASES = {
    "parliament": ["Országház", "Parlament"], "kossuth": ["Kossuth tér"], "flag": ["Zászló", "Flag", "Spawn"], "castle": ["Budavári Palota", "Vár"], "chainbridge": ["Lánchíd"],
    "basilica": ["Bazilika", "Szent István-bazilika"], "gellert": ["Gellért-hegy"], "citadella": ["Citadel", "Szabadság Bástyája"],
    "heroes": ["Hősök tere"], "fishermans": ["Halászbástya"], "matthias": ["Mátyás-templom"],
    "liberty": ["Szabadság híd"], "elisabeth": ["Erzsébet híd"], "market": ["Nagycsarnok", "Vásárcsarnok"],
    "rakoczi": ["Rákóczi téri vásárcsarnok", "Rákóczi tér"],
    "synagogue": ["Dohány utcai zsinagóga", "Zsinagóga"], "varosliget": ["City Park"],
    "szechenyi": ["Széchenyi fürdő"], "puskas": ["Stadion"], "margaret": ["Margit híd"], "petofi": ["Petőfi híd"],
    "opera": ["Operaház"], "keleti": ["Keleti pályaudvar"], "nyugati": ["Nyugati pályaudvar"],
    "ethnography": ["Néprajzi Múzeum"], "balna": ["Whale"], "zoo": ["Állatkert"],
    "eye": ["Óriáskerék", "Ferris wheel"], "statue": ["Szabadság-szobor"], "chainarch": ["Lánchíd Pest"],
    "sidequest": ["Side Quest", "Klauzál utca"], "bar": ["SideQuest Bar", "Side Quest Bar"],
    "sidequest_inside": ["SideQuest inside", "bar inside"],
    "gellerthotel": ["Gellért", "Gellért fürdő", "Gellért Szálló"], "bme": ["Műegyetem", "K épület", "BME"],
    "museum": ["Nemzeti Múzeum", "Múzeum", "National Museum"], "a38": ["A38 hajó"],
}


AERIAL = {"overview"}     # views that stay in the air: the whole city from above
REACH = 320               # metres of the map read round a view's target
STREET = 20000            # m2 of connected street-level ground that make a place "the streets" (not a court, a roof or a pitch)


class Ground:
    """where a player can stand, from the level-2 tiles, per 1 m column: `top`, the top of the highest block that
    isn't a leaf (the feet's height in cells above the base), and `low`, the lowest place to stand from the ground up
    (the deck under a bridge's tower, the road under a deck); each with whether three blocks over it are free"""

    def __init__(self, meta):
        self.mat = np.array([e[3] for e in meta["palette"]], np.int16)
        self.tiles = {}

    def tile(self, tx, ty):
        key = (tx, ty)
        if key not in self.tiles:
            p = DATA / "tiles" / "2" / f"{tx}_{ty}.bin"
            self.tiles[key] = self.surface(*read_tile(p)) if tx >= 0 and ty >= 0 and p.exists() else None
        return self.tiles[key]

    def surface(self, runs, col, ground, det):
        o = np.lexsort((runs[:, 0], col))
        runs, col = runs[o], col[o]
        m = self.mat[runs[:, 2]]
        hard = m != LEAF
        top = runs[:, 0] + runs[:, 1]
        nxt = np.full(len(runs), 1 << 20)           # the next run up the column
        same = col[1:] == col[:-1]
        nxt[:-1][same] = runs[1:, 0][same]
        free = hard & (nxt - top >= 3) & ~np.isin(m, (WATER, JET, CAR))
        if len(det):                                # posts, railings, lamps in the way
            thin = ((det[:, 1] // 2 + 1) * S + det[:, 0] // 2 + 1) * 512 + det[:, 2] // 2
            for k in range(3):
                free &= ~np.isin(col * 512 + top + k, thin)
        g = ground.reshape(-1).astype(np.int64)
        feet = np.zeros(S * S, np.int64)
        np.maximum.at(feet, col[hard], top[hard])
        ok = np.zeros(S * S, bool)
        on = hard & (top == feet[col])              # the run a player would stand on
        ok[col[on]] = free[on]
        low = np.full(S * S, 1 << 20, np.int64)
        up = free & (top >= g[col] - 1)
        np.minimum.at(low, col[up], top[up])
        lok = low < 1 << 20
        low[~lok] = 0
        cut = lambda a: a.reshape(S, S)[1:-1, 1:-1]
        return cut(feet).astype(np.int16), cut(ok), cut(g).astype(np.int16), cut(low).astype(np.int16), cut(lok)

    def window(self, x0, z0, x1, z1):
        """top, its ok, the ground, low, its ok over columns x0..x1, rows z0..z1"""
        out = [np.zeros((z1 - z0, x1 - x0), t) for t in (np.int16, bool, np.int16, np.int16, bool)]
        for ty in range(z0 // N, (z1 - 1) // N + 1):
            for tx in range(x0 // N, (x1 - 1) // N + 1):
                t = self.tile(tx, ty)
                if t is None:
                    continue
                r0, r1, c0, c1 = max(z0, ty * N), min(z1, ty * N + N), max(x0, tx * N), min(x1, tx * N + N)
                src = (slice(r0 - ty * N, r1 - ty * N), slice(c0 - tx * N, c1 - tx * N))
                dst = (slice(r0 - z0, r1 - z0), slice(c0 - x0, c1 - x0))
                for a, b in zip(out, t):
                    a[dst] = b[src]
        return out

    def floor(self, x, z, h):
        """indoors: the floor under a camera at height h (cells above the base) in column x, z"""
        tx, ty = int(x) // N, int(z) // N
        p = DATA / "tiles" / "2" / f"{tx}_{ty}.bin"
        if not p.exists():
            return None
        runs, col, _, _ = read_tile(p)
        mine = runs[col == (int(z) - ty * N + 1) * S + int(x) - tx * N + 1]
        tops = [int(z0 + n) for z0, n, pal in mine if self.mat[pal] != LEAF and z0 + n <= h]
        return max(tops) if tops else None


def standing(G, pos, target, Wb, Db):
    """a place on the ground by a view's subject: from the target towards the camera, the first open spot of the
    streets (ground under the sky that a player can walk to from the streets, so bridge decks and terraces too, but
    no court and no roof), then a few steps back for the look of it. -> x, feet (cells above the base), z, or None"""
    from scipy import ndimage
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    (px, _, pz), (tx, _, tz) = pos, target
    x0, z0 = max(int(tx) - REACH, 0), max(int(tz) - REACH, 0)
    x1, z1 = min(int(tx) + REACH, Wb), min(int(tz) + REACH, Db)
    feet, ok, gr, low, lok = G.window(x0, z0, x1, z1)
    # what can be walked: neighbours no more than a block apart in height, on either of a column's two levels
    n = feet.size
    idx = np.arange(n).reshape(feet.shape)
    lay = ((feet.astype(np.int32), ok, 0), (low.astype(np.int32), lok, n))
    i, j = [idx[ok & lok & (feet == low)]], [idx[ok & lok & (feet == low)] + n]
    for fa, oa, na in lay:
        for fb, ob, nb in lay:
            e = oa[:, :-1] & ob[:, 1:] & (np.abs(fa[:, :-1] - fb[:, 1:]) <= 1)
            i.append(idx[:, :-1][e] + na), j.append(idx[:, 1:][e] + nb)
            e = oa[:-1] & ob[1:] & (np.abs(fa[:-1] - fb[1:]) <= 1)
            i.append(idx[:-1][e] + na), j.append(idx[1:][e] + nb)
    i, j = np.concatenate(i), np.concatenate(j)
    _, lab = connected_components(coo_matrix((np.ones(len(i), bool), (i, j)), shape=(2 * n,) * 2), directed=False)
    lab = lab[:n].reshape(feet.shape)   # places are chosen under the sky only: the top level
    street = ok & (np.abs(feet - gr) <= 2)
    walk = ok & (feet >= gr - 1) & (np.bincount(lab[street], minlength=lab.max() + 1) >= STREET)[lab]
    # room to stand: the 3 x 3 round it walkable and level
    room = ndimage.minimum_filter(walk, 3) & (ndimage.maximum_filter(feet, 3) - ndimage.minimum_filter(feet, 3) <= 1)
    if not room.any():
        return None

    def at(x, z):
        r, c = int(z) - z0, int(x) - x0
        return 0 <= r < room.shape[0] and 0 <= c < room.shape[1] and (r, c)

    d = math.hypot(px - tx, pz - tz)
    ux, uz = ((px - tx) / d, (pz - tz) / d) if d > 1 else (0.0, 1.0)
    spot = None
    for t in np.arange(0, min(d, REACH - 20) + 0.5, 0.5):
        q = at(tx + ux * t, tz + uz * t)
        if q and room[q]:
            spot = q
            for back in np.arange(0.5, 12.5, 0.5):   # a few steps back, while the way stays open
                q = at(tx + ux * (t + back), tz + uz * (t + back))
                if not q or not walk[q]:
                    break
                if room[q]:
                    spot = q
            break
    if spot is None:  # nothing that way (a bridge's middle from the river): the nearest place to the target
        rr, cc = np.nonzero(room)
        k = np.argmin((rr + z0 + 0.5 - tz) ** 2 + (cc + x0 + 0.5 - tx) ** 2)
        spot = int(rr[k]), int(cc[k])
    return spot[1] + x0 + 0.5, int(feet[spot]), spot[0] + z0 + 0.5


def views_to_landmarks(meta, y0, Wb, Db, ymax=290):
    """the viewer's views as teleports: on the ground by the view's subject, on the side the view shows, looking at
    it (`standing`). A view indoors (`walk`) stands on its floor. AERIAL views keep the camera's place: one above the
    build limit or off the map slides along its line of sight towards the target until it is back"""
    G = Ground(meta)
    out = []
    for key, v in meta["views"].items():
        (px, ph, pz), (tx, th, tz) = v["pos"], v["target"]
        feet = None
        if v.get("walk"):
            feet = G.floor(px, pz, ph)
        elif key not in AERIAL:
            s = standing(G, v["pos"], v["target"], Wb, Db)
            if s:
                px, feet, pz = s
            else:
                print(f"  landmark {key}: no ground found near it, left in the air")
        if feet is not None:
            ph = feet + 1.62   # the eyes
        else:
            t = 1.0
            while t > 0.05:
                x, h, z = tx + t * (px - tx), th + t * (ph - th), tz + t * (pz - tz)
                if h + y0 <= ymax and 8 <= x <= Wb - 8 and 8 <= z <= Db - 8:
                    break
                t -= 0.02
            px, ph, pz = x, h, z
        dx, dy, dz = tx - px, th - ph, tz - pz
        if math.hypot(dx, dz) < 2:   # standing on the target itself: look the way the view does
            dx, dz = tx - v["pos"][0], tz - v["pos"][2]
        yaw = math.degrees(math.atan2(-dx, dz))
        pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
        y = ph + y0
        if feet is not None:
            y, pitch = float(feet + y0), max(-40.0, min(10.0, pitch))
        out.append(dict(id=key, name=v.get("label", key), x=round(px, 1), y=round(y, 1), z=round(pz, 1),
                        yaw=round(yaw, 1), pitch=round(pitch, 1), aliases=ALIASES.get(key, [])))
    bar = meta.get("sidequest")
    if bar and bar.get("door"):  # /bar: on the pavement at the bar's door, facing it
        h = bar.get("heading", 0.0)
        out.append(dict(id="bar", name=f"{bar['name']}, at the door", x=bar["door"][0], y=round(bar["g"] + y0 + 0.05, 1),
                        z=bar["door"][1], yaw=round(math.degrees(math.atan2(-math.cos(h), math.sin(h))), 1), pitch=0.0,
                        aliases=ALIASES["bar"]))
    sp = meta.get("spawn")
    if sp:  # /lm flag and the spawn: on Kossuth tér by the flag, looking up at the Parliament
        h = sp["heading"]
        out.append(dict(id="flag", name=sp["name"], x=sp["x"], y=round(sp["g"] + y0 + 0.05, 1), z=sp["z"],
                        yaw=round(math.degrees(math.atan2(-math.cos(h), math.sin(h))), 1), pitch=-8.0,
                        aliases=ALIASES["flag"]))
    return out


def write_meta(out, meta, version, data_version):
    """landmarks.yml and map.yml, the plugin's half of the build"""
    vox = meta["vox"]
    Wb, Db = int(round(meta["W"] * vox)), int(round(meta["D"] * vox))
    y0 = int(meta["base"]) - SEA
    lms = views_to_landmarks(meta, y0, Wb, Db)
    spawn = next((l for l in lms if l["id"] == "flag"), None) or next((l for l in lms if l["id"] == "parliament"), lms[0])
    with open(out / "landmarks.yml", "w") as f:
        f.write("# made by scripts/minecraft.py from the web viewer's views (web/public/data/meta.json)\nlandmarks:\n")
        for l in lms:
            f.write(f"  {l['id']}:\n    name: {yaml_str(l['name'])}\n    x: {l['x']}\n    y: {l['y']}\n    z: {l['z']}\n"
                    f"    yaw: {l['yaw']}\n    pitch: {l['pitch']}\n")
            if l["aliases"]:
                f.write(f"    aliases: [{', '.join(yaml_str(s) for s in l['aliases'])}]\n")
    built = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(out / "map.yml", "w") as f:
        f.write(f"# made by scripts/minecraft.py\nminecraft: {yaml_str(version)}\ndata-version: {data_version}\n"
                f"built: {yaml_str(built)}\nbounds: {{min-x: 0, min-z: 0, max-x: {Wb}, max-z: {Db}}}\n"
                f"y-offset: {-SEA}\nsea-level-y: {int(round(meta['base'] + meta.get('water', 4))) - SEA}\n"
                f"spawn: {{x: {spawn['x']}, y: {spawn['y']}, z: {spawn['z']}, yaw: {spawn['yaw']}, pitch: {spawn['pitch']}}}\n"
                f"theta-deg: {meta.get('theta_deg', 41.5)}\n")
    return len(lms)


def yaml_str(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / "minecraft"))
    ap.add_argument("--only", default="", help="rx0:rx1,rz0:rz1")
    ap.add_argument("--jobs", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--landmarks-only", action="store_true", help="only landmarks.yml and map.yml (views changed)")
    a = ap.parse_args()
    meta = json.loads((DATA / "meta.json").read_text())
    if a.landmarks_only:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        info = json.loads(BLOCKS.read_text())
        print(f"{write_meta(out, meta, info['version'], info['data_version'])} landmarks -> {out}")
        return
    vox = meta["vox"]
    Wb, Db = int(round(meta["W"] * vox)), int(round(meta["D"] * vox))
    H = int(math.ceil(meta["H"] * vox)) + 2
    y0 = int(meta["base"]) - SEA
    out = Path(a.out)
    reg_dir = out / "world" / "dimensions" / "minecraft" / "overworld" / "region"
    reg_dir.mkdir(parents=True, exist_ok=True)
    nrx, nrz = -(-Wb // RW), -(-Db // RW)
    rxs, rzs = range(nrx), range(nrz)
    if a.only:
        (x0, x1), (z0, z1) = (map(int, p.split(":")) for p in a.only.split(","))
        rxs, rzs = range(x0, x1), range(z0, z1)
    else:
        for p in reg_dir.glob("r.*.mca"):  # a full build replaces every region
            p.unlink()
    jobs = [(rx, rz, H, reg_dir, y0, Wb, Db) for rz in rzs for rx in rxs]
    t0 = time.time()
    B = Blocks(meta)
    prev = np.zeros((Db // 4 + 128, Wb // 4 + 128, 3), np.uint8)
    used = {}
    nch = 0
    with ProcessPoolExecutor(a.jobs, initializer=_init, initargs=(meta,)) as ex:
        for k, (rx, rz, n, dt, top, states) in enumerate(ex.map(build_region, jobs)):
            nch += n
            used.update(states)
            if top is not None:
                rgb = np.zeros(top.shape + (3,), np.uint8)
                for i, key in states.items():
                    nm = key[0].split(":")[1]
                    b = B.blocks.get(nm) or B.blocks.get(nm.replace("_wall", "")) or {}
                    rgb[top == i] = (63, 118, 228) if nm == "water" else (b.get("top") or b.get("side") or (120, 120, 120))
                prev[rz * 128:rz * 128 + 128, rx * 128:rx * 128 + 128] = rgb
            print(f"  region {rx},{rz}: {n} chunks in {dt:.1f} s  ({k + 1}/{len(jobs)}, {time.time() - t0:.0f} s)",
                  flush=True)
    from PIL import Image
    Image.fromarray(prev[:Db // 4, :Wb // 4]).save(out / "preview.png")
    n = write_meta(out, meta, B.version, B.data_version)
    print(f"world: {nch} chunks in {len(jobs)} regions, {len(used)} block states, {n} landmarks, "
          f"{time.time() - t0:.0f} s -> {out}")


if __name__ == "__main__":
    main()
