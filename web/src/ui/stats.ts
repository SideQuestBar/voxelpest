// ?fps=1: frames per second, the frame time (mean and worst over the last half second), draw calls, triangles and the
// tiles shown and loading, in a corner.
import type * as THREE from 'three';
import { h } from '../util';

export class Stats {
  private readonly el = h('div', { id: 'fps', 'aria-hidden': 'true' });
  private last = 0;
  private t0 = 0;
  private frames = 0;
  private worst = 0;

  constructor() { document.body.appendChild(this.el); }

  frame(now: number, info: THREE.WebGLInfo, tiles: { shown: number; loading: number; bytes: number; budget: number }, note = '') {
    if (this.last) {
      this.frames++;
      this.worst = Math.max(this.worst, now - this.last);
    } else this.t0 = now;
    this.last = now;
    if (now - this.t0 < 500 || !this.frames) return;
    const ms = (now - this.t0) / this.frames, r = info.render;
    this.el.textContent = `${(1000 / ms).toFixed(0)} fps · ${ms.toFixed(1)} ms (max ${this.worst.toFixed(0)})\n`
      + `${r.calls} draws · ${(r.triangles / 1e6).toFixed(2)} M tris\n`
      + `tiles ${tiles.shown} shown · ${tiles.loading} loading\n`
      + `${(tiles.bytes / 1e6).toFixed(0)} MB` + (isFinite(tiles.budget) ? ` of ${(tiles.budget / 1e6).toFixed(0)}` : '') + note;
    this.t0 = now;
    this.frames = 0;
    this.worst = 0;
  }
}
