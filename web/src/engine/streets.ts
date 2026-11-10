// Where a walker, a bike or a car can start: the nearest spot to a wished point that lies on the street network. Pest's
// inner courts are paved like its pavements and lie at street level, so a spot must also lead somewhere: a flood over
// the columns one can walk (or drive) from it has to spread over a few thousand square metres, or out of the loaded
// area, before it runs out. Buildings (no headroom), roofs (far above the ground), the river and pedestals fall out
// on the way.
import { MAT, type Meta } from '../meta';
import type { Tiles } from './tiles';

export type StreetKind = 'foot' | 'road' | 'bike';
export interface Spot { x: number; y: number; z: number }

const C = { NONE: 0, WATER: 1, SOFT: 2, TRACK: 3, ROAD: 4, CYCLE: 5, PAVE: 6 } as const;
type Surface = (typeof C)[keyof typeof C];

// scripts/style.py's ground colours; the palette rounds colours to 4 the way Python rounds (halves to even)
const NAMED: [string, Surface, number?][] = [
  ['#5f636b', C.ROAD], ['#8f8981', C.ROAD], ['#a49f97', C.ROAD], ['#6a6d73', C.ROAD], ['#686b70', C.ROAD],  // asphalt, sett, granite, parking
  ['#8a5a52', C.CYCLE],
  ['#a9a59c', C.TRACK], ['#8a8178', C.TRACK], ['#55575d', C.TRACK, MAT.METAL],  // tram bed, ballast, rails
  ['#62b8cc', C.WATER], ['#d9c79a', C.SOFT], ['#a58a66', C.SOFT],               // pools, sand, dirt
];
const SOFT_MATS = new Set<number>([MAT.GRASS, MAT.SOIL, MAT.LEAF, MAT.JET]);
const HEAD = 1.8, NEAR = 1.2, FAR = 30, ROOFED = 25;  // a covered spot counts as 25 m further

// per kind: what it may start on (and how much further a lesser surface counts), how far round the spot must be the
// same, the step it climbs, and the connected area (cells of 0.25 m²) that makes a street rather than a courtyard
const KIND = {
  foot: { start: { [C.PAVE]: 0, [C.CYCLE]: 2, [C.ROAD]: 4 } as Record<number, number>, clear: 1, flat: 0.35, step: 0.6, area: 20000 },
  bike: { start: { [C.ROAD]: 0, [C.CYCLE]: 0, [C.PAVE]: 3 } as Record<number, number>, clear: 2, flat: 0.3, step: 0.6, area: 20000 },
  road: { start: { [C.ROAD]: 0 } as Record<number, number>, clear: 3, flat: 0.5, step: 0.75, area: 12000 },
};

const roundHalfEven = (v: number) => { const f = Math.floor(v), d = v - f; return d > 0.5 || (d === 0.5 && f % 2) ? f + 1 : f; };
const q4 = (v: number) => Math.min(255, roundHalfEven(v / 4) * 4);

export class Streets {
  private readonly cls: Uint8Array;            // per palette entry
  private readonly soft: Uint8Array;           // leaves and fountain jets: not in the way
  private H = 0;                               // the window round the wished point, in cells each way
  private side = 0;
  private x0 = 0;
  private y0 = 0;
  private state = new Uint8Array(0);           // 0 not looked at, 1 not loaded, 2 no footing, 3 footing
  private top = new Float32Array(0);
  private surf = new Uint8Array(0);
  private roofed = new Uint8Array(0);         // something overhead (an arcade, a deck): a start prefers the open sky
  private comp = new Int32Array(0);
  private readonly queue = new Int32Array(4 * Math.max(...Object.values(KIND).map((k) => k.area)) + 8);
  private verdict: boolean[] = [];
  private tileCache = new Map<number, ReturnType<Tiles['columns']>>();

  constructor(private readonly tiles: Tiles, private readonly meta: Meta) {
    const named = new Map<string, Surface>();
    for (const [hex, c, m = MAT.SOLID] of NAMED) {
      const v = [1, 3, 5].map((i) => q4(parseInt(hex.slice(i, i + 2), 16)));
      named.set(`${v}|${m}`, c);
    }
    this.cls = new Uint8Array(meta.palette.map(([r, g, b, m]) => {
      if (m === MAT.WATER) return C.WATER;
      if (m === MAT.MARK) return C.ROAD;
      const c = named.get(`${r},${g},${b}|${m}`);
      if (c !== undefined) return c;
      return SOFT_MATS.has(m) ? C.SOFT : C.PAVE;
    }));
    this.soft = new Uint8Array(meta.palette.map((p) => +(p[3] === MAT.LEAF || p[3] === MAT.JET)));
  }

  // a carriageway's palette (for the direction a road runs in)
  isRoad(pal: number) { return pal >= 0 && this.cls[pal] === C.ROAD; }

  // The nearest spot within R metres of (x, z) where `kind` can start (metres; y is the surface's height), or null.
  // Needs the finest tiles round it loaded (main.ts: groundLoaded).
  spot(x: number, z: number, kind: StreetKind, R = 80): Spot | null {
    const k = KIND[kind], v = this.meta.vox;
    this.reset(x, z, R);
    const cx = Math.floor(x / v) - this.x0, cy = Math.floor(z / v) - this.y0;
    let best = -1, score = Infinity;
    for (let r = 0; r <= R / v && r < score / v; r += 1) {
      const n = Math.max(1, Math.ceil(2 * Math.PI * r));
      for (let i = 0; i < n; i++) {
        const a = (i / n) * 2 * Math.PI, ix = cx + Math.round(Math.cos(a) * r), iy = cy + Math.round(Math.sin(a) * r);
        const c = this.cell(ix, iy);
        if (c < 0 || this.state[c] !== 3) continue;
        const pen = k.start[this.surf[c]];
        if (pen === undefined) continue;
        const s = Math.hypot(ix - cx, iy - cy) * v + pen + this.roofed[c] * ROOFED;
        if (s >= score || !this.clear(ix, iy, k, kind) || !this.connected(ix, iy, kind)) continue;
        best = c; score = s;
      }
    }
    if (best < 0) return null;
    const bx = best % this.side, by = (best - bx) / this.side;
    return { x: (bx + this.x0 + 0.5) * v, y: this.top[best], z: (by + this.y0 + 0.5) * v };
  }

  private reset(x: number, z: number, R: number) {
    const v = this.meta.vox, H = Math.ceil((R + 60) / v);
    if (H > this.H) {
      this.H = H;
      this.side = 2 * H + 1;
      const n = this.side * this.side;
      this.state = new Uint8Array(n); this.top = new Float32Array(n); this.surf = new Uint8Array(n); this.roofed = new Uint8Array(n);
      this.comp = new Int32Array(n);
    } else {
      this.state.fill(0); this.comp.fill(0);
    }
    this.x0 = Math.floor(x / v) - this.H;
    this.y0 = Math.floor(z / v) - this.H;
    this.verdict = [false];
    this.tileCache.clear();
  }

  // a window cell's index once its footing is known, or -1 outside the window
  private cell(ix: number, iy: number) {
    if (ix < 0 || iy < 0 || ix >= this.side || iy >= this.side) return -1;
    const c = iy * this.side + ix;
    if (!this.state[c]) this.probe(c, ix + this.x0, iy + this.y0);
    return c;
  }

  // where feet stand in a column: the top of a run near the tile's ground with headroom over it (under a deck or an
  // arcade too, not on a roof, not in a building)
  private probe(c: number, gx: number, gy: number) {
    const N = this.tiles.N, tx = Math.floor(gx / N), ty = Math.floor(gy / N), key = tx * 4096 + ty;
    let t = this.tileCache.get(key);
    if (t === undefined) {
      t = this.tiles.columns((tx * N + 0.5) * this.meta.vox, (ty * N + 0.5) * this.meta.vox);
      this.tileCache.set(key, t);
    }
    if (!t) { this.state[c] = 1; return; }
    const { cols } = t, S = N + 2, i = (gy - ty * N + 1) * S + (gx - tx * N + 1), v = this.meta.vox, runs = cols.runs;
    const g = cols.ground[i], end = cols.off[i + 1];
    let found = NaN, pal = -1, over = Infinity;
    for (let k = cols.off[i]; k < end; k++) {
      const p = runs[k * 3 + 2];
      if (this.soft[p]) continue;
      const top = (runs[k * 3] + runs[k * 3 + 1]) * v;
      let above = Infinity;
      for (let j = k + 1; j < end; j++) if (!this.soft[runs[j * 3 + 2]]) { above = runs[j * 3] * v; break; }
      if (above - top < HEAD || Math.abs(top - g) > NEAR + 0.8) continue;
      if (Number.isNaN(found) || Math.abs(top - g) < Math.abs(found - g)) { found = top; pal = p; over = above; }
    }
    if (pal < 0 || this.cls[pal] === C.WATER) { this.state[c] = 2; return; }
    this.state[c] = 3;
    this.top[c] = found;
    this.roofed[c] = +(over < Infinity);
    // a start must be on the ground itself; the flood may also take a ramp or a terrace a little above it
    this.surf[c] = Math.abs(found - g) <= NEAR ? this.cls[pal] : C.SOFT;
  }

  // the same surface all round, at the same height: room for the body, not on a bench, a wall or a kerb's edge
  private clear(ix: number, iy: number, k: (typeof KIND)[StreetKind], kind: StreetKind) {
    const c0 = iy * this.side + ix, h = this.top[c0];
    for (let dy = -k.clear; dy <= k.clear; dy++) {
      for (let dx = -k.clear; dx <= k.clear; dx++) {
        const c = this.cell(ix + dx, iy + dy);
        if (c < 0 || this.state[c] !== 3 || Math.abs(this.top[c] - h) > k.flat) return false;
        if (kind === 'road' && this.surf[c] !== C.ROAD) return false;
      }
    }
    return true;
  }

  // does the spot lead out? a flood over the cells one can walk (or drive) to, four ways, a step at a time; yes once
  // it covers the kind's area or meets the unknown (unloaded or outside the window) far enough away
  private connected(ix: number, iy: number, kind: StreetKind) {
    const c0 = iy * this.side + ix;
    if (this.comp[c0]) return this.verdict[this.comp[c0]];
    const k = KIND[kind], id = this.verdict.length, q = this.queue, side = this.side;
    const pass = (s: number) => (kind === 'road' ? s === C.ROAD || s === C.TRACK : s !== C.NONE);
    this.verdict.push(false);
    let head = 0, tail = 0, ok = false;
    q[tail++] = c0;
    this.comp[c0] = id;
    flood: while (head < tail) {
      const c = q[head++];
      if (head >= k.area) { ok = true; break; }
      const cx = c % side, cy = (c - cx) / side;
      for (let d = 0; d < 4; d++) {
        const nx = cx + (d === 0 ? 1 : d === 1 ? -1 : 0), ny = cy + (d === 2 ? 1 : d === 3 ? -1 : 0);
        const n = this.cell(nx, ny);
        if (n < 0 || this.state[n] === 1) {
          if (Math.hypot(nx - ix, ny - iy) * this.meta.vox >= FAR) { ok = true; break flood; }
          continue;
        }
        if (this.state[n] !== 3 || !pass(this.surf[n]) || Math.abs(this.top[n] - this.top[c]) > k.step) continue;
        if (this.comp[n] === id) continue;
        if (this.comp[n]) { ok = this.verdict[this.comp[n]]; break flood; }
        this.comp[n] = id;
        q[tail++] = n;
      }
    }
    this.verdict[id] = ok;
    return ok;
  }
}
