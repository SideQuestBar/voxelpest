// Which tiles to draw, and loading them. The tiles form a quadtree per level (meta.tiles: a cell is s voxels, s = 16,
// 8, 4, 2, 1): the whole map is always there at the coarsest level, and a tile is replaced by its four children once
// they are all meshed, wherever one of its cells would cover more than `err` pixels on screen. Walking and driving
// pin the finest tiles round the player and keep their columns for collisions. A tile giving way to others dissolves
// over them for a moment instead of vanishing.
import * as THREE from 'three';
import type { Meta } from '../meta';
import type { Cols, MeshJob, MeshResult } from './mesher.worker';
import MesherWorker from './mesher.worker?worker';

const FADE_MS = 450;

function dropArray(this: THREE.BufferAttribute) { (this as { array: unknown }).array = null; }

export interface Tile {
  key: string;
  s: number;
  tx: number;
  ty: number;
  state: 'new' | 'queued' | 'loading' | 'ready';
  prio: number;
  wanted: number;
  mesh: THREE.Mesh | null;
  cols: Cols | null;
  waiters: (() => void)[];
}

export class Tiles {
  readonly N: number;
  readonly levels: number[];               // coarse to fine
  private readonly query: string;          // ?v=<the tiles' hash> in a build (meta.ts), so a new map has new URLs
  readonly dims: Record<number, { nx: number; ny: number }>;
  readonly group = new THREE.Group();
  readonly tiles = new Map<string, Tile>();
  err = 2.2;
  keepMs = 10000;  // how long a tile nobody shows is kept
  // Bytes of geometry to stay under (phones: iOS kills a page that holds too much, "a problem repeatedly occurred").
  // Over it, tiles nobody shows go at once and the detail falls off sooner with distance (`tight` scales `err`).
  budget = Infinity;
  bytes = 0;
  private tight = 1;
  loading = 0;
  shown = 0;
  meshed = 0;                              // tiles meshed since the start, for the loading screen and the tile bar
  see: Uint8Array | null = null;           // seasons (engine/foliage.ts): leaves hide no other faces (mesher.worker.ts)
  depth: THREE.Material | null = null;     // and the shadow pass drops bare leaves (material.ts)
  private readonly workers: { w: Worker; busy: boolean; jobs: number }[] = [];
  recycle = Infinity;                      // a worker is replaced after this many tiles (phones: its heap goes with it)
  private readonly jobs = new Map<number, Tile>();
  private nextId = 1;
  private index: THREE.BufferAttribute | null = null;   // the quads' index, shared by every tile (indexFor)
  private readonly users = new Map<THREE.BufferAttribute, number>();  // tiles drawing with each index (free)
  private readonly frustum = new THREE.Frustum();
  private readonly box = new THREE.Box3();
  private readonly mtx = new THREE.Matrix4();
  private readonly focus: { x: number; z: number; r: number } = { x: 0, z: 0, r: 0 };
  private lastUpdate = 0;
  private readonly fading = new Map<Tile, number>();  // tiles on their way out, since when
  private probe: THREE.Mesh | null = null;

  // `fades`: the material at rising shares of pixels dropped (material.ts)
  constructor(private readonly meta: Meta, private readonly material: THREE.Material, private readonly fades: THREE.Material[] = []) {
    this.N = meta.tiles.N;
    this.query = meta.tiles.v ? `?v=${encodeURIComponent(meta.tiles.v)}` : '';
    this.levels = meta.tiles.levels.map((l) => l.s).sort((a, b) => b - a);
    this.dims = Object.fromEntries(meta.tiles.levels.map((l) => [l.s, { nx: l.nx, ny: l.ny }]));
    this.group.scale.setScalar(meta.vox);
    // two on phones: each worker holds a tile's data and its growing mesh while it works
    const n = matchMedia('(pointer: coarse)').matches ? 2 : Math.min(Math.max((navigator.hardwareConcurrency || 4) - 1, 2), 8);
    for (let i = 0; i < n; i++) this.workers.push({ w: this.spawn(i), busy: false, jobs: 0 });
  }

  private spawn(i: number) {
    const w = new MesherWorker();
    w.onmessage = (e: MessageEvent<MeshResult>) => this.done(e.data, i);
    return w;
  }

  key(s: number, tx: number, ty: number) { return `${s}/${tx}_${ty}`; }

  private get(s: number, tx: number, ty: number) {
    const key = this.key(s, tx, ty);
    let t = this.tiles.get(key);
    if (!t) {
      t = { key, s, tx, ty, state: 'new', prio: 0, wanted: 0, mesh: null, cols: null, waiters: [] };
      this.tiles.set(key, t);
    }
    return t;
  }

  private want(t: Tile, prio: number, now: number) {
    t.wanted = now;
    t.prio = Math.max(t.prio * 0.5, prio);
    if (t.state === 'new') t.state = 'queued';
  }

  // the finest tiles within r metres of (x, z) stay loaded with their columns: the walker's and the car's ground
  setFocus(x: number, z: number, r: number) { Object.assign(this.focus, { x, z, r }); }

  ready(s: number, tx: number, ty: number): Promise<void> {
    const t = this.get(s, tx, ty);
    if (t.state === 'ready') return Promise.resolve();
    this.want(t, 1e9, performance.now());
    return new Promise((res) => t.waiters.push(res));
  }

  // finest-level columns under a point in metres (grid x, z), or null while not loaded
  columns(x: number, z: number): { cols: Cols; cx: number; cy: number; s: number } | null {
    const v = this.meta.vox, gx = Math.floor(x / v), gy = Math.floor(z / v), s = this.levels[this.levels.length - 1];
    const tx = Math.floor(gx / (this.N * s)), ty = Math.floor(gy / (this.N * s));
    const t = this.tiles.get(this.key(s, tx, ty));
    if (!t?.cols) return null;
    return { cols: t.cols, cx: Math.floor(gx / s) - tx * this.N, cy: Math.floor(gy / s) - ty * this.N, s };
  }

  private bounds(s: number, tx: number, ty: number) {
    const L = this.N * s * this.meta.vox;
    this.box.min.set(tx * L, -2, ty * L);
    this.box.max.set(Math.min((tx + 1) * L, this.meta.W * this.meta.vox), this.meta.H * this.meta.vox, Math.min((ty + 1) * L, this.meta.D * this.meta.vox));
    return this.box;
  }

  update(camera: THREE.PerspectiveCamera, viewH: number, force = false) {
    const now = performance.now();
    this.dissolve(now);
    if (!force && now - this.lastUpdate < 100) return;
    this.lastUpdate = now;
    camera.updateMatrixWorld();
    this.frustum.setFromProjectionMatrix(this.mtx.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    const px = viewH / (2 * Math.tan((camera.fov * Math.PI) / 360));
    const cam = camera.position, f = this.focus, fine = this.levels[this.levels.length - 1];
    const show = new Set<Tile>();
    let loading = 0;
    const over = this.bytes / this.budget;
    if (over > 1) this.tight = Math.min(this.tight * (over > 1.25 ? 1.25 : 1.08), 6);
    else if (over < 0.85 && this.loading === 0) this.tight = Math.max(this.tight / 1.04, 1);
    const err = this.err * this.tight;
    const focusAt = new THREE.Vector3(f.x, 0, f.z);  // on the ground: from high over the map the camera's height put every tile out of reach
    const visit = (s: number, tx: number, ty: number): Tile[] | null => {
      const t = this.get(s, tx, ty), b = this.bounds(s, tx, ty);
      const dist = Math.max(b.distanceToPoint(cam), 1), seen = this.frustum.intersectsBox(b);
      const near = f.r > 0 && b.distanceToPoint(focusAt) < f.r;
      this.want(t, (seen ? 1e6 : 0) - dist + (near && s === fine ? 1e8 : 0) - s, now);
      if (t.state !== 'ready') { loading++; return null; }
      const finer = this.levels[this.levels.indexOf(s) + 1];
      if (finer !== undefined && ((seen && (s * this.meta.vox * px) / dist > err) || near)) {
        const d = this.dims[finer], kids: Tile[] = [];
        let ok = true;
        for (const [dx, dy] of [[0, 0], [1, 0], [0, 1], [1, 1]]) {
          const cx = tx * 2 + dx, cy = ty * 2 + dy;
          if (cx >= d.nx || cy >= d.ny) continue;
          const r = visit(finer, cx, cy);
          if (r) kids.push(...r);
          else ok = false;
        }
        if (ok) return kids;
      }
      return [t];
    };
    const top = this.levels[0], d = this.dims[top];
    for (let ty = 0; ty < d.ny; ty++) for (let tx = 0; tx < d.nx; tx++) for (const t of visit(top, tx, ty) ?? []) show.add(t);
    for (const t of [...this.tiles.values()]) {
      if (t.mesh) this.show(t, show.has(t), now);
      // forget what nobody asked for in 10 s (never the coarsest level)
      if (t.state === 'ready' && t.s !== top && !show.has(t) && !this.fading.has(t) && (now - t.wanted > this.keepMs || (over > 1 && t.wanted !== now))) this.free(t);
      // (not one somebody waits for: a frame longer than that, on a slow phone, and walking or driving never started)
      else if (t.state === 'queued' && !t.waiters.length && now - t.wanted > 1500) t.state = 'new';
    }
    this.shown = show.size;
    this.loading = loading;
    this.pump();
  }

  // a tile leaving the view (its children or its parent have taken its place) stays a moment, dissolving; it is drawn
  // after the others, so where the two coincide it is what shows until it has gone
  private show(t: Tile, on: boolean, now: number) {
    const m = t.mesh!;
    if (on) {
      if (this.fading.delete(t)) this.solid(m);
      m.visible = true;
    } else if (m.visible && this.fades.length && !this.fading.has(t)) {
      this.fading.set(t, now);
      m.renderOrder = 1;
      m.castShadow = false;
    } else if (!this.fading.has(t)) m.visible = false;
  }

  // the dissolving tiles' program, compiled ahead (at the start, and when the lights change: the sun setting), so the
  // first tile to dissolve after that doesn't stall its frame
  warm(renderer: THREE.WebGLRenderer, camera: THREE.Camera, scene: THREE.Scene) {
    if (!this.fades.length) return;
    // a geometry like a tile's (three.js keys programs on its attributes, a position among them)
    this.probe ??= new THREE.Mesh(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Int16Array(3), 3)), this.fades[0]);
    // compileAsync only gains anything with KHR_parallel_shader_compile, and without it (Firefox) three.js warns; the
    // driver compiles in the background either way until something asks for the program's status
    if (renderer.extensions.has('KHR_parallel_shader_compile')) renderer.compileAsync(this.probe, camera, scene).catch(() => {});
    else renderer.compile(this.probe, camera, scene);
  }

  private dissolve(now: number) {
    for (const [t, t0] of this.fading) {
      const k = (now - t0) / FADE_MS, m = t.mesh!;
      if (k < 1) m.material = this.fades[Math.floor(k * this.fades.length)];
      else {
        this.fading.delete(t);
        this.solid(m);
        m.visible = false;
      }
    }
  }

  private solid(m: THREE.Mesh) {
    m.material = this.material;
    m.renderOrder = 0;
    m.castShadow = true;
  }

  private pump() {
    const queued = [...this.tiles.values()].filter((t) => t.state === 'queued').sort((a, b) => b.prio - a.prio);
    for (const wk of this.workers) {
      if (wk.busy) continue;
      const t = queued.shift();
      if (!t) break;
      const id = this.nextId++;
      t.state = 'loading';
      this.jobs.set(id, t);
      wk.busy = true;
      const job: MeshJob = { id, url: new URL(`data/tiles/${t.s}/${t.tx}_${t.ty}.bin${this.query}`, document.baseURI).href, N: this.N, s: t.s, tx: t.tx, ty: t.ty,
        keep: t.s === this.levels[this.levels.length - 1], see: this.see ?? undefined };
      wk.w.postMessage(job);
    }
  }

  private done(r: MeshResult, wi: number) {
    const wk = this.workers[wi];
    wk.busy = false;
    if (++wk.jobs >= this.recycle) {
      wk.w.terminate();
      wk.w = this.spawn(wi);
      wk.jobs = 0;
    }
    const t = this.jobs.get(r.id);
    this.jobs.delete(r.id);
    if (t) {
      if (r.error) console.warn(r.error);
      t.state = 'ready';
      this.meshed++;
      t.cols = r.cols;
      if (r.quads > 0) t.mesh = this.makeMesh(t, r);
      for (const w of t.waiters) w();
      t.waiters = [];
    }
    this.pump();
  }

  private indexFor(quads: number) {
    if (!this.index || this.index.count < quads * 6) {
      let n = 1 << 14;
      while (n < quads) n *= 2;
      const idx = new Uint32Array(n * 6);
      for (let q = 0; q < n; q++) idx.set([q * 4, q * 4 + 1, q * 4 + 2, q * 4, q * 4 + 2, q * 4 + 3], q * 6);
      this.index = new THREE.BufferAttribute(idx, 1);
    }
    return this.index;
  }

  private makeMesh(t: Tile, r: MeshResult) {
    const g = new THREE.BufferGeometry();
    // once on the GPU the arrays go: nothing reads them again, and they would double the map's memory
    const attr = (a: Int16Array | Uint8Array | Uint16Array, n: number) => new THREE.BufferAttribute(a, n).onUpload(dropArray);
    g.setAttribute('position', attr(r.pos, 3));
    g.setAttribute('va', attr(r.va, 4));
    g.setAttribute('vp', attr(r.pal, 1));
    g.userData.bytes = r.quads * 48;
    this.bytes += g.userData.bytes;
    const idx = this.indexFor(r.quads);
    this.users.set(idx, (this.users.get(idx) ?? 0) + 1);
    g.setIndex(idx);
    g.setDrawRange(0, r.quads * 6);
    const L = this.N * t.s;
    g.boundingBox = new THREE.Box3(new THREE.Vector3(t.tx * L, 0, t.ty * L), new THREE.Vector3((t.tx + 1) * L, r.top + 2, (t.ty + 1) * L));
    g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
    const m = new THREE.Mesh(g, this.material);
    m.castShadow = m.receiveShadow = true;
    if (this.depth) m.customDepthMaterial = this.depth;
    m.matrixAutoUpdate = false;
    m.visible = false;
    this.group.add(m);
    return m;
  }

  private free(t: Tile) {
    this.fading.delete(t);
    if (t.mesh) {
      this.group.remove(t.mesh);
      // three.js deletes a geometry's index buffer with it, and the other tiles' vertex arrays kept pointing at the
      // deleted one ("drawElementsInstanced: Index buffer not bound": they weren't drawn). The shared index goes only
      // with the last tile using it, and never while it is the current one.
      const g = t.mesh.geometry, idx = g.index!, n = (this.users.get(idx) ?? 1) - 1;
      if (n > 0) this.users.set(idx, n);
      else this.users.delete(idx);
      if (n > 0 || idx === this.index) g.setIndex(null);
      this.bytes -= g.userData.bytes;
      g.dispose();
    }
    this.tiles.delete(t.key);
  }
}
