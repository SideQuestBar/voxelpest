// The city as solid matter, for the walker and the car: queries on the finest tiles' columns (metres; null while the
// tile is not loaded). Leaves and fountain jets are not in the way; water is a floor you swim on.
import { MAT, type Meta } from '../meta';
import type { Tiles } from './tiles';

export interface Hit { top: number; mat: number }

export class World {
  private readonly mats: Uint8Array;

  constructor(private readonly tiles: Tiles, private readonly meta: Meta) {
    this.mats = new Uint8Array(meta.palette.map((p) => p[3]));
  }

  private soft(pal: number) {
    const m = this.mats[pal];
    return m === MAT.LEAF || m === MAT.JET;
  }

  // runs of a column as [bottom, top, material] in metres
  column(x: number, z: number): number[] | null {
    const c = this.tiles.columns(x, z);
    if (!c) return null;
    const { cols, cx, cy, s } = c, S = this.tiles.N + 2, i = (cy + 1) * S + (cx + 1), u = this.meta.vox * s;
    const out: number[] = [];
    for (let k = cols.off[i]; k < cols.off[i + 1]; k++) {
      const pal = cols.runs[k * 3 + 2];
      if (this.soft(pal)) continue;
      const z0 = cols.runs[k * 3] * u, z1 = z0 + cols.runs[k * 3 + 1] * u, m = this.mats[pal];
      const last = out.length - 3;
      if (last >= 0 && Math.abs(out[last + 1] - z0) < 1e-4 && out[last + 2] !== MAT.WATER && m !== MAT.WATER) out[last + 1] = z1;
      else out.push(z0, z1, m);
    }
    return out;
  }

  // the highest surface at or below y + step under (x, z): where feet or wheels come to rest
  floor(x: number, z: number, y: number, step = 0.6): Hit | null {
    const r = this.column(x, z);
    if (!r) return null;
    let best: Hit = { top: -50, mat: MAT.SOIL };
    for (let k = 0; k < r.length; k += 3) if (r[k + 1] <= y + step + 1e-3 && r[k + 1] > best.top) best = { top: r[k + 1], mat: r[k + 2] };
    return best;
  }

  // is anything solid between heights y0 and y1 at (x, z)?
  blocked(x: number, z: number, y0: number, y1: number): boolean | null {
    const r = this.column(x, z);
    if (!r) return null;
    for (let k = 0; k < r.length; k += 3) if (r[k] < y1 && r[k + 1] > y0 && r[k + 2] !== MAT.WATER) return true;
    return false;
  }

  // the palette under a point's top surface: for finding a road to put the car on
  topPalette(x: number, z: number): number {
    const c = this.tiles.columns(x, z);
    if (!c) return -1;
    const { cols, cx, cy } = c, S = this.tiles.N + 2, i = (cy + 1) * S + (cx + 1);
    const n = cols.off[i + 1] - cols.off[i];
    return n ? cols.runs[(cols.off[i + 1] - 1) * 3 + 2] : -1;
  }

  groundAt(x: number, z: number): number | null {
    const c = this.tiles.columns(x, z);
    if (!c) return null;
    const S = this.tiles.N + 2;
    return c.cols.ground[(c.cy + 1) * S + (c.cx + 1)];
  }
}
