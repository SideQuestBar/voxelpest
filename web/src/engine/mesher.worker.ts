// Turns one tile into faces, in a worker.
//
// The tile format is warsaw-vibe-voxel's (github.com/stared/warsaw-vibe-voxel, MIT, © 2026 Piotr Migdał), written by
// scripts/tiles.py: gzip of counts uint16[(N+2)^2] (runs per column, with a one-column apron round the tile), ground
// uint8[(N+2)^2] (metres above the base), runs (z0, length, palette) uint16 from the bottom up, then for the coarser
// levels "detail" voxels (x, y, z, palette) uint16 at full size: thin things that downsampling would lose.
// The meshing below is this project's own: faces come straight from the runs. A column's top and bottom faces are
// merged into rectangles per height; its side faces are the stretches of its runs that the neighbouring column does
// not cover, merged along the row. Corners get ambient occlusion from the voxels around them.

// see: palette ids (leaves) that hide no other voxel's faces, when trees go bare through the year (engine/foliage.ts):
// the trunk and branches inside a crown, a wall behind a tree, keep their faces
export interface MeshJob { id: number; url: string; N: number; s: number; tx: number; ty: number; keep: boolean; see?: Uint8Array }
export interface Cols { counts: Uint16Array; off: Uint32Array; runs: Uint16Array; ground: Uint8Array }
export interface MeshResult {
  id: number;
  pos: Int16Array;   // voxels: x (column), y (up), z (row)
  va: Uint8Array;    // per vertex: face (0 -x, 1 +x, 2 -z, 3 +z, 4 down, 5 up), occlusion 0-3, ground (m), level
  pal: Uint16Array;  // palette index
  quads: number;
  top: number;       // highest voxel, for the bounding box
  cols: Cols | null; // the columns themselves, for walking and driving (level 1 only)
  error?: string;
}

class Out {
  cap = 4096;
  n = 0;
  pos = new Int16Array(this.cap * 12);
  va = new Uint8Array(this.cap * 16);
  pal = new Uint16Array(this.cap * 4);

  quad(c: number[], face: number, ao: number, ground: number, s: number, pal: number) {
    if (this.n === this.cap) {
      this.cap *= 2;
      const p = new Int16Array(this.cap * 12); p.set(this.pos); this.pos = p;
      const v = new Uint8Array(this.cap * 16); v.set(this.va); this.va = v;
      const q = new Uint16Array(this.cap * 4); q.set(this.pal); this.pal = q;
    }
    const a = [ao & 3, (ao >> 2) & 3, (ao >> 4) & 3, (ao >> 6) & 3];
    // split along the brighter diagonal, so occlusion shades smoothly
    const order = a[0] + a[2] < a[1] + a[3] ? [1, 2, 3, 0] : [0, 1, 2, 3];
    for (let k = 0; k < 4; k++) {
      const i = order[k], v = this.n * 4 + k;
      this.pos[v * 3] = c[i * 3]; this.pos[v * 3 + 1] = c[i * 3 + 1]; this.pos[v * 3 + 2] = c[i * 3 + 2];
      this.va[v * 4] = face; this.va[v * 4 + 1] = a[i]; this.va[v * 4 + 2] = ground; this.va[v * 4 + 3] = s;
      this.pal[v] = pal;
    }
    this.n++;
  }
}

const occ = (s1: number, s2: number, c: number) => (s1 && s2 ? 0 : 3 - (s1 + s2 + c));

let scratchOut: Out | null = null, scratchOff: Uint32Array | null = null;

function mesh(buf: ArrayBuffer, job: MeshJob): MeshResult {
  const { N, s } = job, S = N + 2, n2 = S * S;
  // Views of the tile's bytes, copies only of what goes back with the mesh, and one output kept between tiles: a
  // worker's garbage is collected late in Safari, and tile after tile it grew to over a gigabyte on an iPhone
  const view = !job.keep && n2 % 2 === 0;
  const counts = view ? new Uint16Array(buf, 0, n2) : new Uint16Array(buf.slice(0, n2 * 2));
  const ground = view ? new Uint8Array(buf, n2 * 2, n2) : new Uint8Array(buf.slice(n2 * 2, n2 * 3));
  if (!scratchOff || scratchOff.length !== n2 + 1) scratchOff = new Uint32Array(n2 + 1);
  const off = job.keep ? new Uint32Array(n2 + 1) : scratchOff;
  for (let i = 0; i < n2; i++) off[i + 1] = off[i] + counts[i];
  const nr = off[n2];
  const runs = view ? new Uint16Array(buf, n2 * 3, nr * 3) : new Uint16Array(buf.slice(n2 * 3, n2 * 3 + nr * 6));
  const detail = view ? new Uint16Array(buf, n2 * 3 + nr * 6, (buf.byteLength - n2 * 3 - nr * 6) >> 1) : new Uint16Array(buf.slice(n2 * 3 + nr * 6));
  const X0 = job.tx * N * s, Z0 = job.ty * N * s;
  const see = job.see, hides = (p: number, by: number) => !see || !see[by] || !!see[p];  // does a voxel `by` hide `p`'s face
  const out = scratchOut ??= new Out();
  out.n = 0;
  let top = 0;

  const col = (x: number, y: number) => (y + 1) * S + (x + 1);
  const solid = (x: number, y: number, z: number) => {
    if (z < 0) return 1;
    if (x < -1 || y < -1 || x > N || y > N) return 0;
    const c = col(x, y);
    for (let k = off[c], e = off[c + 1]; k < e; k++) {
      const z0 = runs[k * 3];
      if (z < z0) return 0;
      if (z < z0 + runs[k * 3 + 1]) return 1;
    }
    return 0;
  };

  // ---- tops and bottoms: cells per height, merged into rectangles where nothing shades them
  const tops = new Map<number, number[]>(), bottoms = new Map<number, number[]>();
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const c = col(x, y);
    for (let k = off[c], e = off[c + 1]; k < e; k++) {
      const z0 = runs[k * 3], zt = z0 + runs[k * 3 + 1], p = runs[k * 3 + 2];
      if (zt > top) top = zt;
      if (!(k + 1 < e && runs[(k + 1) * 3] === zt && hides(p, runs[(k + 1) * 3 + 2]))) {
        const sx0 = solid(x - 1, y, zt), sx1 = solid(x + 1, y, zt), sy0 = solid(x, y - 1, zt), sy1 = solid(x, y + 1, zt);
        const ao = occ(sx0, sy0, solid(x - 1, y - 1, zt)) | (occ(sx0, sy1, solid(x - 1, y + 1, zt)) << 2)
          | (occ(sx1, sy1, solid(x + 1, y + 1, zt)) << 4) | (occ(sx1, sy0, solid(x + 1, y - 1, zt)) << 6);
        let a = tops.get(zt);
        if (!a) tops.set(zt, (a = []));
        a.push(x, y, p, ao);
      }
      if (z0 > 0 && !(k > off[c] && runs[(k - 1) * 3] + runs[(k - 1) * 3 + 1] === z0 && hides(p, runs[(k - 1) * 3 + 2]))) {
        let a = bottoms.get(z0);
        if (!a) bottoms.set(z0, (a = []));
        a.push(x, y, p, 255);
      }
    }
  }
  const flat = (cells: Map<number, number[]>, up: boolean) => {
    for (const [z, a] of cells) {
      const Y = z * s;
      const open = new Map<number, number[]>(); // (x0, x1, palette) -> [x0, x1, y0, y1, palette, ground]
      const emit = (q: number[], ao: number) => {
        const x0 = X0 + q[0] * s, x1 = X0 + q[1] * s, z0 = Z0 + q[2] * s, z1 = Z0 + q[3] * s;
        const c = up ? [x0, Y, z0, x0, Y, z1, x1, Y, z1, x1, Y, z0] : [x0, Y, z0, x1, Y, z0, x1, Y, z1, x0, Y, z1];
        out.quad(c, up ? 5 : 4, ao, q[5], s, q[4]);
      };
      for (let i = 0; i < a.length;) {
        const x = a[i], y = a[i + 1], p = a[i + 2], ao = a[i + 3];
        const g = ground[col(x, y)];
        if (ao !== 255) { emit([x, x + 1, y, y + 1, p, g], ao); i += 4; continue; }
        let x1 = x + 1;
        i += 4;
        while (i < a.length && a[i] === x1 && a[i + 1] === y && a[i + 2] === p && a[i + 3] === 255 && ground[col(x1, y)] === g) { x1++; i += 4; }
        const key = ((x * 256 + x1) * 4096 + p) * 256 + g, q = open.get(key);
        if (q && q[3] === y) q[3] = y + 1;
        else {
          if (q) emit(q, 255);
          open.set(key, [x, x1, y, y + 1, p, g]);
        }
      }
      for (const q of open.values()) emit(q, 255);
    }
  };
  flat(tops, true);
  flat(bottoms, false);

  // ---- sides: what a column shows towards each neighbour, merged along the row. Faces out through the tile's edge
  // are always made, since the tile next to it may be drawn at another level.
  // corner sides per face, in its corner order: [u side, top?]
  const CORNERS: Record<number, [number, number][]> = {
    0: [[-1, 0], [1, 0], [1, 1], [-1, 1]], 1: [[-1, 0], [-1, 1], [1, 1], [1, 0]],
    2: [[-1, 0], [-1, 1], [1, 1], [1, 0]], 3: [[-1, 0], [1, 0], [1, 1], [-1, 1]],
  };
  for (const face of [0, 1, 2, 3]) {
    const alongX = face >= 2, dx = face === 0 ? -1 : face === 1 ? 1 : 0, dy = face === 2 ? -1 : face === 3 ? 1 : 0;
    const corners = CORNERS[face];
    for (let p = 0; p < N; p++) {
      const open = new Map<number, number[]>(); // (a, b, palette, ao, ground) -> [u0, u1, a, b, palette, ao, ground]
      const emit = (q: number[]) => {
        const [u0, u1, a, b, pal, ao, g] = q, za = a * s, zb = b * s;
        let c: number[];
        if (!alongX) {
          const xp = X0 + (p + (dx > 0 ? 1 : 0)) * s, y0 = Z0 + u0 * s, y1 = Z0 + u1 * s;
          c = dx > 0 ? [xp, za, y0, xp, zb, y0, xp, zb, y1, xp, za, y1] : [xp, za, y0, xp, za, y1, xp, zb, y1, xp, zb, y0];
        } else {
          const zp = Z0 + (p + (dy > 0 ? 1 : 0)) * s, x0 = X0 + u0 * s, x1 = X0 + u1 * s;
          c = dy > 0 ? [x0, za, zp, x1, za, zp, x1, zb, zp, x0, zb, zp] : [x0, za, zp, x0, zb, zp, x1, zb, zp, x1, za, zp];
        }
        out.quad(c, face, ao, g, s, pal);
      };
      for (let u = 0; u < N; u++) {
        const x = alongX ? u : p, y = alongX ? p : u, fx = x + dx, fy = y + dy;
        const c = col(x, y), g = ground[c];
        const edge = fx < 0 || fy < 0 || fx >= N || fy >= N;
        const n = col(fx, fy);
        let j = off[n];
        const je = edge ? j : off[n + 1];
        const piece = (a: number, b: number, pal: number) => {
          let ao = 0;
          for (let k = 0; k < 4; k++) {
            const [us, tp] = corners[k];
            const ux = alongX ? fx + us : fx, uy = alongX ? fy : fy + us;
            const zv = tp ? b : a - 1, zh = tp ? b - 1 : a;
            const v = edge ? 0 : solid(fx, fy, zv);
            ao |= occ(v, edge ? 0 : solid(ux, uy, zh), edge ? 0 : solid(ux, uy, zv)) << (2 * k);
          }
          const key = (((a * 4096 + b) * 4096 + pal) * 256 + ao) * 256 + g, q = open.get(key);
          if (q && q[1] === u) q[1] = u + 1;
          else {
            if (q) emit(q);
            open.set(key, [u, u + 1, a, b, pal, ao, g]);
          }
        };
        for (let k = off[c], e = off[c + 1]; k < e; k++) {
          const a = runs[k * 3], b = a + runs[k * 3 + 1], pal = runs[k * 3 + 2];
          while (j < je && runs[j * 3] + runs[j * 3 + 1] <= a) j++;
          let cur = a, jj = j;
          while (cur < b) {
            if (jj >= je || runs[jj * 3] >= b) { piece(cur, b, pal); break; }
            if (!hides(pal, runs[jj * 3 + 2])) { jj++; continue; }
            const ns = runs[jj * 3], ne = ns + runs[jj * 3 + 1];
            if (ns > cur) piece(cur, ns, pal);
            cur = Math.max(cur, ne);
            jj++;
          }
        }
      }
      for (const q of open.values()) emit(q);
    }
  }

  // ---- detail voxels of the coarse levels (posts, railings, cables): stacks of one colour as boxes
  if (detail.length >= 4) {
    const order: number[] = [];
    for (let k = 0; k + 3 < detail.length; k += 4) order.push(k);
    order.sort((a, b) => detail[a] - detail[b] || detail[a + 1] - detail[b + 1] || detail[a + 2] - detail[b + 2]);
    for (let i = 0; i < order.length;) {
      const k = order[i], x = detail[k], y = detail[k + 1], z0 = detail[k + 2], p = detail[k + 3];
      let j = i + 1;
      while (j < order.length && detail[order[j]] === x && detail[order[j] + 1] === y && detail[order[j] + 2] === z0 + (j - i)
        && detail[order[j] + 3] === p) j++;
      const z1 = z0 + (j - i);
      i = j;
      const g = ground[col(Math.min(N - 1, Math.floor(x / s)), Math.min(N - 1, Math.floor(y / s)))];
      const ax = X0 + x, bx = ax + 1, az = Z0 + y, bz = az + 1;
      if (z1 > top * s) top = Math.ceil(z1 / s);
      out.quad([ax, z0, az, ax, z0, bz, ax, z1, bz, ax, z1, az], 0, 255, g, 1, p);
      out.quad([bx, z0, az, bx, z1, az, bx, z1, bz, bx, z0, bz], 1, 255, g, 1, p);
      out.quad([ax, z0, az, ax, z1, az, bx, z1, az, bx, z0, az], 2, 255, g, 1, p);
      out.quad([ax, z0, bz, bx, z0, bz, bx, z1, bz, ax, z1, bz], 3, 255, g, 1, p);
      out.quad([ax, z0, az, bx, z0, az, bx, z0, bz, ax, z0, bz], 4, 255, g, 1, p);
      out.quad([ax, z1, az, ax, z1, bz, bx, z1, bz, bx, z1, az], 5, 255, g, 1, p);
    }
  }
  const n = out.n;
  if (out.cap > 1 << 18) scratchOut = null;  // a rare huge tile's output isn't kept
  return {
    id: job.id, pos: out.pos.slice(0, n * 12), va: out.va.slice(0, n * 16), pal: out.pal.slice(0, n * 4), quads: n,
    top: top * s, cols: job.keep ? { counts, off, runs, ground } : null,
  };
}

const empty = (id: number, error?: string): MeshResult =>
  ({ id, pos: new Int16Array(0), va: new Uint8Array(0), pal: new Uint16Array(0), quads: 0, top: 0, cols: null, error });

self.onmessage = async (e: MessageEvent<MeshJob>) => {
  const job = e.data;
  let res: MeshResult;
  try {
    const r = await fetch(job.url);
    if (r.status === 404) res = empty(job.id);
    else if (!r.ok || !r.body) res = empty(job.id, `${r.status} ${job.url}`);
    else {
      const buf = await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
      res = mesh(buf, job);
    }
  } catch (err) {
    res = empty(job.id, String(err));
  }
  const tr: Transferable[] = [res.pos.buffer, res.va.buffer, res.pal.buffer];
  if (res.cols) tr.push(res.cols.counts.buffer, res.cols.off.buffer, res.cols.runs.buffer, res.cols.ground.buffer);
  (self as unknown as Worker).postMessage(res, tr);
};
