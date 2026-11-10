"""Streamable voxel tiles for the viewer (web/src/engine/tiles.ts), in the format of warsaw-vibe-voxel's scripts/tiles.py
(MIT, © 2026 Piotr Migdał; downsample, column_runs and thin_voxels are taken from it unchanged).

Level s in (1, 2, 4, 8, 16) has cells of s x s x s voxels (a voxel is meta.vox = 0.5 m); every node holds N x N cells
(N = 128, so a node spans 128 * s voxels) plus a 1-cell apron on each side for face culling and AO at the node edge.

Node file  tiles/{s}/{nx}_{ny}.bin, gzip of:
  counts  uint16[(N+2)^2]   runs per column (apron included, row-major, row = grid row)
  ground  uint8 [(N+2)^2]   ground level in metres above the model base, for the facade shader
  runs    uint16[3 * sum]   (z0, len, palette) per run, z in cells of the level, bottom -> top
  detail  uint16[4 * n]     (x, y, z, palette) level-1 voxels from the node's corner (levels 2, 4 and 8)

The volume is never built whole: export() asks `build(r0, r1, c0, c1)` for one 256 x 256 window at a time (with a
1-voxel apron), writes its four level-1 nodes, and keeps a compressed downsampled copy of it for every coarser level,
plus its thin voxels. The coarse nodes are then put together from those copies, so every voxel is built once.
"""
import gzip
import math
import zlib

import numpy as np

N = 128
LEVELS = (1, 2, 4, 8, 16)
WIN = 2 * N
DETAIL = (2, 4, 8)


def downsample(vol, s, face_ids=(), low=None):
    H, D, W = vol.shape
    Hs, Ds, Ws = -(-H // s), -(-D // s), -(-W // s)
    out = np.zeros((Hs, Ds, Ws), np.uint16)
    need = max(2, (s ** 3 * 3) // 8) if s == 2 else s ** 3 // 4
    band = max(1, 256 // s)  # block rows per pass: bounded memory on the 4 x 3 km volume
    for rb in range(0, Ds, band):
        r0, r1 = rb * s, min((rb + band) * s, D)
        sub = vol[:, r0:r1, :]
        pad = ((0, Hs * s - H), (0, (-(r1 - r0)) % s), (0, Ws * s - W))
        sub = np.pad(sub, pad)
        hb, db, wb = sub.shape[0] // s, sub.shape[1] // s, sub.shape[2] // s
        blk = sub.reshape(hb, s, db, s, wb, s)
        occ = (blk != 0).sum((1, 3, 5), dtype=np.int32)
        # colour: the topmost non-empty voxel in the block (scan the s layers from the top)
        col = np.zeros((hb, db, wb), np.uint16)
        for dz in range(s - 1, -1, -1):
            layer = blk[:, dz]  # (hb, db, s, wb, s)
            for dy in range(s):
                for dx in range(s):
                    v = layer[:, :, dy, :, dx]
                    if low is not None:  # window glass gives way to the wall around it in a coarse block
                        v = np.where(low[v], 0, v)
                    col = np.where((col == 0) & (v != 0), v, col)
        if low is not None:
            for dz in range(s - 1, -1, -1):
                for dy in range(s):
                    for dx in range(s):
                        v = blk[:, dz, :, dy, :, dx]
                        col = np.where((col == 0) & (v != 0), v, col)
        res = np.where(occ >= need, col, 0)
        # a thin surface (ground or roof in the block's bottom layer) is too sparse to keep its own block, which
        # left the block below showing what lies under it (brown soil along the plazas): that block wears it instead
        up = np.zeros_like(col)
        up[:-1] = np.where(res[1:] == 0, col[1:], 0)
        res = np.where((res != 0) & (up != 0), up, res)
        if len(face_ids):  # markings on a wall (the PKiN clock faces) colour the whole block, not just its top voxel
            fv = blk.max((1, 3, 5), where=np.isin(blk, face_ids), initial=0)
            res = np.where((res != 0) & (fv > 0), fv, res)
        out[:, rb:rb + db, :] = res
    return out


def column_runs(vol_win):
    """vol_win (H, R, C) -> counts (R*C,), runs (n, 3) bottom -> top, row-major columns."""
    H = vol_win.shape[0]
    cols = vol_win.reshape(H, -1).T
    n = cols.shape[0]
    b = np.zeros((n, H + 1), bool)
    b[:, 0] = True
    b[:, 1:H] = cols[:, 1:] != cols[:, :-1]
    b[:, H] = True
    fi = np.flatnonzero(b)
    ci, zi = fi // (H + 1), fi % (H + 1)
    same = ci[:-1] == ci[1:]
    s_ci, s_z0, s_z1 = ci[:-1][same], zi[:-1][same], zi[1:][same]
    val = cols[s_ci, s_z0]
    k = val != 0
    s_ci, s_z0, s_z1, val = s_ci[k], s_z0[k], s_z1[k], val[k]
    counts = np.bincount(s_ci, minlength=n)
    return counts.astype(np.uint16), np.stack([s_z0, s_z1 - s_z0, val], 1).astype(np.uint16)


def thin_voxels(vol, skip_ids, keep_ids, note, most=9, band=96):
    """Voxels of thin things -- spires, poles, cable stays: lines one voxel across -- found in 3D: at most `most` of
    the 27 voxels around them are solid (a roof edge has 12 or more), and all of `keep_ids` (lamp heads). Foliage and
    trunks (`skip_ids`) excepted: the canopy is drawn by the coarse tiles anyway. -> (z, r, c, palette) arrays."""
    H, D, W = vol.shape
    skip = np.zeros(65536, bool); skip[list(skip_ids)] = True
    keep = np.zeros(65536, bool); keep[list(keep_ids)] = True
    out = [[], [], [], []]
    for r0 in range(0, D, band):
        a, b = max(r0 - 1, 0), min(r0 + band + 1, D)
        sub = vol[:, a:b]
        solid = ((sub != 0) & ~skip[sub]).astype(np.uint8)
        p = np.pad(solid, 1)
        cnt = p[:-2] + p[1:-1] + p[2:]                          # along z
        cnt = cnt[:, :-2] + cnt[:, 1:-1] + cnt[:, 2:]           # along rows
        cnt = cnt[:, :, :-2] + cnt[:, :, 1:-1] + cnt[:, :, 2:]  # along columns
        thin = ((solid == 1) & (cnt <= most)) | keep[sub]
        thin[:, :r0 - a] = False; thin[:, r0 - a + band:] = False  # the halo rows belong to the next band
        z, r, c = np.nonzero(thin)
        out[0].append(z); out[1].append(r + a); out[2].append(c); out[3].append(sub[z, r, c])
    z, r, c, v = (np.concatenate(x) for x in out)
    note(f"thin structures: {len(z)} voxels one voxel across")
    return z.astype(np.int64), r.astype(np.int64), c.astype(np.int64), v.astype(np.uint16)



def _write(path, win, gw, det=None):
    top = int(np.nonzero(win.reshape(win.shape[0], -1).any(1))[0].max()) + 1 if win.any() else 1
    counts, runs = column_runs(win[:top])
    blob = counts.tobytes() + gw.tobytes() + runs.tobytes() + (det.tobytes() if det is not None and len(det) else b"")
    with gzip.GzipFile(path, "wb", compresslevel=9, mtime=0) as fh:
        fh.write(blob)
    return path.stat().st_size, len(runs)


def export(build, gm, F, W, D, H, out, note, keep_ids=(), skip_ids=(), low_ids=()):
    """build(r0, r1, c0, c1) -> uint16 (h, r1 - r0, c1 - c0) voxels, z from the model base; gm (D/F, W/F) ground in metres
    on the 1 m grid. Writes every node of every level; returns the manifest for meta.json."""
    import time
    t0 = time.time()
    info = dict(N=N, levels=[], bytes=0)
    nwx, nwy = -(-W // WIN), -(-D // WIN)
    for s in LEVELS:
        (out / str(s)).mkdir(parents=True, exist_ok=True)

    def ground(s, tx, ty):
        rr = np.clip((ty * N - 1 + np.arange(N + 2)) * s, 0, D - 1) // F
        cc = np.clip((tx * N - 1 + np.arange(N + 2)) * s, 0, W - 1) // F
        return np.clip(gm[rr][:, cc], 0, 255).astype(np.uint8)

    low = None
    if len(low_ids):
        low = np.zeros(65536, bool)
        low[list(low_ids)] = True
    store, thin = {}, {}
    tot1, runs1 = 0, 0
    for wy in range(nwy):
        for wx in range(nwx):
            r0, c0 = wy * WIN - 1, wx * WIN - 1
            r1, c1 = r0 + WIN + 2, c0 + WIN + 2
            a0, a1, b0, b1 = max(r0, 0), min(r1, D), max(c0, 0), min(c1, W)
            part = build(a0, a1, b0, b1)
            hh = min(part.shape[0], H)
            v = np.zeros((hh, WIN + 2, WIN + 2), np.uint16)
            v[:, a0 - r0:a1 - r0, b0 - c0:b1 - c0] = part[:hh]
            del part
            for dy in (0, 1):
                for dx in (0, 1):
                    tx, ty = wx * 2 + dx, wy * 2 + dy
                    if tx * N >= W or ty * N >= D:
                        continue
                    sz, nr = _write(out / "1" / f"{tx}_{ty}.bin", v[:, dy * N:dy * N + N + 2, dx * N:dx * N + N + 2], ground(1, tx, ty))
                    tot1 += sz
                    runs1 += nr
            inner = v[:, 1:-1, 1:-1]
            for s in LEVELS[1:]:
                vs = downsample(inner, s, low=low if s >= 4 else None)
                store[(s, wx, wy)] = (vs.shape, zlib.compress(vs.tobytes(), 1))
            tz, tr, tc, tv = thin_voxels(v, skip_ids, keep_ids, lambda *x: None)
            k = (tr >= 1) & (tr <= WIN) & (tc >= 1) & (tc <= WIN)
            thin[(wx, wy)] = (tz[k].astype(np.int32), (tr[k] - 1 + wy * WIN).astype(np.int32),
                              (tc[k] - 1 + wx * WIN).astype(np.int32), tv[k])
        note(f"  window row {wy + 1}/{nwy} ({time.time() - t0:.0f}s)")
    info["levels"].append(dict(s=1, nx=-(-W // N), ny=-(-D // N)))
    info["bytes"] += tot1
    note(f"tiles level 1: {info['levels'][0]['nx']}x{info['levels'][0]['ny']} nodes, {runs1} runs, {tot1 / 2 ** 20:.1f} MB gz")

    def window(s, wx, wy):
        if not (0 <= wx < nwx and 0 <= wy < nwy):
            return None
        shp, b = store[(s, wx, wy)]
        return np.frombuffer(zlib.decompress(b), np.uint16).reshape(shp)

    for s in LEVELS[1:]:
        cw = WIN // s
        Ws, Ds = -(-W // s), -(-D // s)
        nx, ny = -(-Ws // N), -(-Ds // N)
        tot, nruns, ndet = 0, 0, 0
        for ty in range(ny):
            for tx in range(nx):
                X0, Y0 = tx * N - 1, ty * N - 1
                wx0, wx1 = math.floor(X0 / cw), math.floor((X0 + N + 1) / cw)
                wy0, wy1 = math.floor(Y0 / cw), math.floor((Y0 + N + 1) / cw)
                tiles_ = {(a, b): window(s, a, b) for b in range(wy0, wy1 + 1) for a in range(wx0, wx1 + 1)}
                hs = max((t.shape[0] for t in tiles_.values() if t is not None), default=1)
                canvas = np.zeros((hs, (wy1 - wy0 + 1) * cw, (wx1 - wx0 + 1) * cw), np.uint16)
                for (a, b), t in tiles_.items():
                    if t is not None:
                        canvas[:t.shape[0], (b - wy0) * cw:(b - wy0) * cw + t.shape[1], (a - wx0) * cw:(a - wx0) * cw + t.shape[2]] = t
                oy, ox = Y0 - wy0 * cw, X0 - wx0 * cw
                win = canvas[:, oy:oy + N + 2, ox:ox + N + 2]
                det = None
                if s in DETAIL:
                    ds = []
                    for b in range(max(wy0, 0), min(wy1, nwy - 1) + 1):
                        for a in range(max(wx0, 0), min(wx1, nwx - 1) + 1):
                            tz, tr, tc, tv = thin[(a, b)]
                            x, y = tc - tx * N * s, tr - ty * N * s
                            k = (x >= 0) & (x < N * s) & (y >= 0) & (y < N * s)
                            if not k.any():
                                continue
                            x, y, z, pv = x[k], y[k], tz[k], tv[k]
                            zc = np.minimum(z // s, win.shape[0] - 1)
                            lost = (win[zc, y // s + 1, x // s + 1] == 0) | (z // s >= win.shape[0])
                            ds.append(np.stack([x[lost], y[lost], z[lost], pv[lost]], 1).astype(np.uint16))
                    if ds:
                        det = np.concatenate(ds)
                        ndet += len(det)
                sz, nr = _write(out / str(s) / f"{tx}_{ty}.bin", win, ground(s, tx, ty), det)
                tot += sz
                nruns += nr
        info["levels"].append(dict(s=s, nx=nx, ny=ny))
        info["bytes"] += tot
        note(f"tiles level {s}: {nx}x{ny} nodes, {nruns} runs, {ndet} detail voxels, {tot / 2 ** 20:.1f} MB gz")
    return info
