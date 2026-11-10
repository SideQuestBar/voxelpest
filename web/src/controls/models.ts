// The five vehicles, built in code from the kit (controls/kit.ts) to their real sizes (controls/vehicles.ts): a few
// meshes each (one per material, the wheels instanced, the lettering on one small canvas), so recognisable at a glance
// without costing draw calls. References: docs in README's "Drive" section.
import * as THREE from 'three';
import { Atlas, Kit, archedBottom, fitText, lit, mats, type P2, type P3 } from './kit';
import { SPECS, type VehicleKind } from './vehicles';

export interface WheelSpot { x: number; z: number; r: number; front: boolean; w: number }

const BLACK = 0x15181b, TYRE = 0x1b1c1e, WHITE = 0xf4f5f2, PLATE = 0xf2f2ee;
const ROUTE = '7', DEST = 'Újpalota, Nyírpalota út';   // the 7's north-eastern terminus
const FONT = 'Arial, "Helvetica Neue", "DejaVu Sans", sans-serif';

// the bike's rider: hips on the saddle, feet on the pedals (a two-bone leg follows each pedal round), the cranks and
// pedals, all of it one instanced box
class Rider {
  readonly limbs: THREE.InstancedMesh;
  private readonly m = new THREE.Matrix4();
  private readonly q = new THREE.Quaternion();
  private readonly v = new THREE.Vector3();
  private readonly s = new THREE.Vector3();
  private readonly z = new THREE.Vector3(0, 0, 1);

  constructor(private readonly bb: P2, private readonly hip: P2, colours: number[]) {
    const k = new Kit();
    k.box(1, 1, 1, mats().matte, 0xffffff, 0, 0, 0);
    this.limbs = new THREE.InstancedMesh(k.geometry(), mats().matte, colours.length);
    const c = new THREE.Color();
    colours.forEach((col, i) => this.limbs.setColorAt(i, c.set(col)));
    this.limbs.castShadow = true;
    this.limbs.frustumCulled = false;
    this.limbs.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  }

  private seg(i: number, a: P2, b: P2, z: number, t: number, w: number) {
    const dx = b[0] - a[0], dy = b[1] - a[1];
    this.q.setFromAxisAngle(this.z, Math.atan2(dy, dx));
    this.m.compose(this.v.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z), this.q, this.s.set(Math.hypot(dx, dy), t, w));
    this.limbs.setMatrixAt(i, this.m);
  }

  // the cranks at angle a (0: the right one forward, turning backwards over the top as the bike moves on)
  pose(a: number) {
    const [bx, by] = this.bb, CR = 0.17, L1 = 0.46, L2 = 0.47;
    for (const [n, s] of [[0, 1], [1, -1]] as const) {
      const t = -a + (s < 0 ? Math.PI : 0), p: P2 = [bx + CR * Math.cos(t), by + CR * Math.sin(t)], z = s * 0.1;
      this.seg(n * 5, [bx, by], p, s * 0.075, 0.03, 0.025);                       // crank
      this.seg(n * 5 + 1, [p[0] - 0.05, p[1]], [p[0] + 0.05, p[1]], s * 0.11, 0.025, 0.08);  // pedal
      const f: P2 = [p[0] + 0.01, p[1] + 0.06], h = this.hip;
      const dx = f[0] - h[0], dy = f[1] - h[1], d = Math.min(Math.hypot(dx, dy), L1 + L2 - 0.005);
      const A = Math.acos((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)), base = Math.atan2(dy, dx) + A;
      const knee: P2 = [h[0] + L1 * Math.cos(base), h[1] + L1 * Math.sin(base)];
      this.seg(n * 5 + 2, h, knee, z, 0.13, 0.13);                                  // thigh
      this.seg(n * 5 + 3, knee, f, z, 0.1, 0.1);                                    // shin
      this.seg(n * 5 + 4, [f[0] - 0.07, f[1] - 0.025], [f[0] + 0.16, f[1] - 0.035], s * 0.1, 0.075, 0.1);  // shoe
    }
    this.limbs.instanceMatrix.needsUpdate = true;
  }
}

export interface Wheel { geo: THREE.BufferGeometry; blur: THREE.BufferGeometry; col: number; max: number; period: number }

export class Model {
  readonly g = new THREE.Group();
  readonly wheels: THREE.InstancedMesh;
  readonly blur: THREE.InstancedMesh;            // discs over the rims that hide the holes or spokes at speed
  readonly period: number;                       // the rim's symmetry: a turn of this much looks the same
  glow: THREE.MeshStandardMaterial[] = [];       // signs and displays, brighter at night
  flash: THREE.MeshStandardMaterial[] = [];      // the police car's blue and red lights
  rider: Rider | null = null;
  private readonly blurMax: number;
  private readonly m = new THREE.Matrix4();
  private readonly q = new THREE.Quaternion();
  private readonly e = new THREE.Euler();
  private readonly v = new THREE.Vector3();
  private readonly s = new THREE.Vector3();

  constructor(readonly kind: VehicleKind, body: THREE.Group, wheel: Wheel, readonly spots: WheelSpot[]) {
    this.g.add(body);
    this.g.add(underShadow(SPECS[kind].len, SPECS[kind].wid));
    this.wheels = new THREE.InstancedMesh(wheel.geo, mats().wheel, spots.length);
    this.wheels.castShadow = true;
    this.wheels.frustumCulled = false;
    this.wheels.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.g.add(this.wheels);
    const bm = lit(new THREE.MeshStandardMaterial({ color: wheel.col, roughness: 0.5, transparent: true, opacity: 0, depthWrite: false }));
    this.blur = new THREE.InstancedMesh(wheel.blur, bm, spots.length);
    this.blur.instanceMatrix = this.wheels.instanceMatrix;
    this.blur.frustumCulled = false;
    this.blur.visible = false;
    this.g.add(this.blur);
    this.blurMax = wheel.max;
    this.period = wheel.period;
    this.g.visible = false;
  }

  // wheels turned by spin (radians rolled) and steer, blurred by blur 0..1, the cranks at crank, the lights flashing
  // at time t if on
  pose(spin: number, steer: number, crank: number, t: number, flashing: boolean, blur = 0) {
    this.spots.forEach((w, i) => {
      this.e.set(0, w.front ? -steer : 0, -spin * (this.spots[0].r / w.r), 'YZX');
      this.m.compose(this.v.set(w.x, w.r, w.z), this.q.setFromEuler(this.e), this.s.set(1, 1, w.w));
      this.wheels.setMatrixAt(i, this.m);
    });
    this.wheels.instanceMatrix.needsUpdate = true;
    (this.blur.material as THREE.MeshStandardMaterial).opacity = blur * this.blurMax;
    this.blur.visible = blur > 0.02;
    this.rider?.pose(crank);
    if (this.flash.length) {
      // a double flash, blue then red, 1.6 times a second
      const p = (t * 1.6) % 1, on = (a: number) => flashing && ((p > a && p < a + 0.09) || (p > a + 0.15 && p < a + 0.24));
      this.flash[0].emissiveIntensity = on(0) ? 3 : 0;
      this.flash[1].emissiveIntensity = on(0.5) ? 1.6 : 0;
    }
  }
}

function decalMat(atlas: Atlas, glow = false) {
  const m = new THREE.MeshStandardMaterial({ map: atlas.texture, vertexColors: true, roughness: 0.45, alphaTest: 0.5,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  if (glow) { m.emissiveMap = atlas.texture; m.emissive.set(0xffffff); m.emissiveIntensity = 0.5; }
  m.userData.noShadow = true;
  return lit(m);
}

// a picture on the flat side of a body at z, between x0 (rear) and x1 (front), y0 and y1, the right way round from
// outside on either side
function sideDecal(k: Kit, mat: THREE.Material, uv: [number, number, number, number], x0: number, x1: number, y0: number, y1: number, z: number) {
  if (z > 0) k.quad([x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z], mat, 0xffffff, uv);
  else k.quad([x1, y0, z], [x0, y0, z], [x0, y1, z], [x1, y1, z], mat, 0xffffff, uv);
}

// on a face across the body at x (or from x[0] at y0 to x[1] at y1, if it leans), facing forward (dir 1) or back (-1)
function endDecal(k: Kit, mat: THREE.Material, uv: [number, number, number, number], x: number | [number, number], w: number, y0: number, y1: number,
  dir: 1 | -1, zc = 0) {
  const [x0, x1] = typeof x === 'number' ? [x, x] : x, a = zc + (dir * w) / 2, b = zc - (dir * w) / 2;
  k.quad([x0, y0, a], [x0, y0, b], [x1, y1, b], [x1, y1, a], mat, 0xffffff, uv);
}

// the soft dark patch under a vehicle: what the sky and the lamps don't reach. The sun's shadow map is too coarse for
// the gap under a car and there is none at night, when a vehicle seemed to float over the lit street
let shadeTex: THREE.CanvasTexture | null = null;
function underShadow(len: number, wid: number) {
  if (!shadeTex) {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const g = c.getContext('2d')!, im = g.createImageData(64, 64);
    for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
      // a rounded box's falloff: full under the body, gone at the patch's edge
      const dx = Math.max(Math.abs(x - 31.5) / 31.5 - 0.62, 0) / 0.38, dy = Math.max(Math.abs(y - 31.5) / 31.5 - 0.5, 0) / 0.5;
      const a = Math.max(1 - Math.hypot(dx, dy), 0);
      im.data[(y * 64 + x) * 4 + 3] = 255 * a * a * (3 - 2 * a);
    }
    g.putImageData(im, 0, 0);
    shadeTex = new THREE.CanvasTexture(c);
  }
  const m = new THREE.Mesh(new THREE.PlaneGeometry(len * 1.16, wid * 1.5),
    new THREE.MeshBasicMaterial({ map: shadeTex, color: 0x000000, transparent: true, opacity: 0.5, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.03;
  m.renderOrder = 1;
  return m;
}

// a wheel: tyre, rim with holes or spokes that show it turning, hub; and the discs that blur the rim at speed, in its
// colour mixed with the holes' (see-through for the spokes)
function wheelGeo(r: number, w: number, rimR: number, rim: number, opts: { cap?: number; holes?: number; dark?: number; spokes?: number } = {}): Wheel {
  const k = new Kit(), m = mats().wheel;
  const disc = (rd: number, z: number) => {
    const b = new Kit();
    b.add(new THREE.CircleGeometry(rd, 28), m, 0xffffff, 0, 0, z);
    b.add(new THREE.CircleGeometry(rd, 28), m, 0xffffff, 0, 0, -z, 0, Math.PI, 0);
    return b.geometry();
  };
  if (opts.spokes) {
    k.add(new THREE.TorusGeometry(r - 0.022, 0.022, 6, 28), m, TYRE);
    k.add(new THREE.TorusGeometry(rimR, 0.012, 4, 28), m, rim);
    for (let i = 0; i < opts.spokes; i++) {
      const a = (i / opts.spokes) * Math.PI * 2, rr = rimR / 2;
      k.box(rimR, 0.005, 0.005, m, 0xc8ccd0, Math.cos(a) * rr, Math.sin(a) * rr, (i % 2 ? 1 : -1) * 0.012, 0, 0, a);
    }
    k.cyl(0.03, 0.09, m, 0x9aa0a6, 0, 0, 0, 'z', 10);
    return { geo: k.geometry(), blur: disc(rimR - 0.01, 0.02), col: 0xb4b9be, max: 0.55, period: (Math.PI * 2) / opts.spokes };
  }
  k.cyl(r, w, m, TYRE, 0, 0, 0, 'z', 22);
  k.cyl(r * 0.94, w + 0.004, m, 0x232426, 0, 0, 0, 'z', 22);   // the sidewall's edge, so the tread reads apart
  k.cyl(rimR, w + 0.012, m, rim, 0, 0, 0, 'z', 18);
  const n = opts.holes ?? 5;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2, rr = rimR * 0.62;
    k.cyl(rimR * 0.2, w + 0.02, m, opts.dark ?? 0x2b2e31, Math.cos(a) * rr, Math.sin(a) * rr, 0, 'z', 8);
  }
  if (opts.cap) k.cyl(opts.cap, w + 0.03, m, 0xe4e6e8, 0, 0, 0, 'z', 12);
  const col = new THREE.Color(rim).lerp(new THREE.Color(opts.dark ?? 0x2b2e31), 0.22).getHex();
  return { geo: k.geometry(), blur: disc(rimR * 0.97, w / 2 + 0.013), col, max: 0.92, period: (Math.PI * 2) / n };
}

// rear > 1: twin tyres at the back, that much wider and a little further in
function fourWheels(kind: VehicleKind, rear = 1): WheelSpot[] {
  const s = SPECS[kind], [f, b] = s.axles, t = s.track / 2, tb = rear > 1 ? t * 0.93 : t;
  return [
    { x: f, z: t, r: s.r, front: true, w: 1 }, { x: f, z: -t, r: s.r, front: true, w: 1 },
    { x: b, z: tb, r: s.r, front: false, w: rear }, { x: b, z: -tb, r: s.r, front: false, w: rear },
  ];
}

// ------------------------------------------------------------------ the saloon: the taxi and the police Škoda
function saloon(k: Kit, body: number, opts: { roofBody?: boolean } = {}) {
  const M = mats(), s = SPECS.police, [fa, ra] = s.axles, ay = s.r, ar = 0.4, W = s.wid;
  const lower: P2[] = [
    ...archedBottom(-2.3, 2.3, 0.3, ay, [[ra, ar], [fa, ar]]),
    [2.345, 0.42], [2.35, 0.6], [2.3, 0.72], [2.12, 0.8], [1.0, 0.97], [-1.6, 1.0], [-2.0, 1.02], [-2.28, 0.98], [-2.345, 0.86], [-2.35, 0.45],
  ];
  k.profile(lower, W, M.paint, body, 0, 0.05);
  k.box(4.4, 0.42, 1.2, M.matte, 0x202326, 0, 0.5, 0);                       // under the body, between the wheels
  const gh: P2[] = [[1.06, 0.93], [0.02, 1.44], [-0.55, 1.475], [-1.12, 1.44], [-2.04, 1.03], [-2.02, 0.93]];
  k.profile(gh, W - 0.2, M.paint, opts.roofBody === false ? BLACK : body, 0, 0.06);
  // glass
  k.slope([0.98, 0.98], [0.02, 1.44], W - 0.34, M.glass, 0x1d272e, [0.03, 0.05]);
  k.slope([-1.12, 1.44], [-2.0, 1.04], W - 0.46, M.glass, 0x1d272e, [0.08, 0.04]);
  k.mirror((sd) => {
    const z = sd * ((W - 0.2) / 2 + 0.004);
    k.side([[0.86, 0.99], [0.1, 1.37], [-1.1, 1.375], [-1.84, 1.04]], z, M.glass, 0x1d272e);
    k.side([[-0.26, 0.99], [-0.33, 0.99], [-0.35, 1.375], [-0.28, 1.375]], z + sd * 0.002, M.matte, BLACK);   // B pillar
    k.box(0.11, 0.1, 0.2, M.paint, body, 0.86, 1.05, sd * (W / 2 + 0.08));           // mirror
    k.box(0.05, 0.05, 0.1, M.matte, BLACK, 0.9, 1.0, sd * (W / 2 + 0.01));
    k.box(0.14, 0.025, 0.012, M.chrome, 0xd0d4d8, 0.62, 0.9, sd * (W / 2 + 0.004));  // door handles
    k.box(0.14, 0.025, 0.012, M.chrome, 0xd0d4d8, -0.62, 0.91, sd * (W / 2 + 0.004));
    k.box(fa - ra - 2 * ar - 0.04, 0.07, 0.03, M.matte, BLACK, (fa + ra) / 2, 0.33, sd * (W / 2 - 0.005));   // sill, between the arches
    for (const [x, y0] of [[0.97, 0.37], [-0.32, 0.37], [-1.36, 0.74]]) k.side([[x - 0.006, y0], [x + 0.006, y0], [x + 0.006, 0.91], [x - 0.006, 0.91]], sd * (W / 2 + 0.002), M.matte, 0x50565c);
    // lamps
    k.box(0.06, 0.07, 0.4, M.lamp, 0xf4f6ff, 2.32, 0.66, sd * 0.6, 0, sd * 0.25, 0);
    k.box(0.05, 0.075, 0.38, M.tail, 0xc0181b, -2.33, 0.88, sd * 0.6, 0, -sd * 0.2, 0);
    k.box(0.03, 0.05, 0.12, M.paint, 0x7a0f12, -2.34, 0.46, sd * 0.7);
  });
  // the front: a black grille between the lamps, an intake under it; the plates
  k.box(0.03, 0.16, 0.84, M.matte, BLACK, 2.345, 0.58, 0);
  k.box(0.03, 0.1, 1.3, M.matte, 0x24282c, 2.34, 0.4, 0);
  k.box(0.012, 0.11, 0.52, M.paint, PLATE, 2.36, 0.47, 0);
  k.box(0.014, 0.11, 0.05, M.paint, 0x1f45a8, 2.361, 0.47, 0.235);
  k.box(0.012, 0.11, 0.52, M.paint, PLATE, -2.36, 0.62, 0);
  k.box(0.03, 0.12, 1.5, M.matte, 0x24282c, -2.345, 0.4, 0);
  k.cyl(0.035, 0.16, M.chrome, 0x8a8f94, -2.31, 0.27, -0.52, 'x', 10);   // the tailpipe (SPECS' exhaust)
  k.cyl(0.024, 0.162, M.matte, 0x111214, -2.31, 0.27, -0.52, 'x', 10);
}

function taxi() {
  const k = new Kit(), M = mats(), Y = 0xf3c316;
  saloon(k, Y);
  // the black and yellow check along the doors
  k.mirror((sd) => {
    for (let i = 0; i < 16; i++) for (let row = 0; row < 2; row++) {
      if ((i + row) % 2) continue;
      k.box(0.12, 0.07, 0.01, M.matte, 0x141414, -1.05 + i * 0.125, 0.77 + row * 0.07, sd * (SPECS.taxi.wid / 2 + 0.003));
    }
  });
  // the roof sign, lit at night
  const at = new Atlas(256, 64), glow = decalMat(at, true);
  const uv = at.rect(256, 64, (g, w, h) => {
    g.fillStyle = '#fff3b0'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#1b1b1b'; g.textAlign = 'center'; g.textBaseline = 'middle';
    fitText(g, 'TAXI', w / 2, h / 2 + 2, w - 40, 52, 800, FONT);
  });
  k.box(0.34, 0.2, 0.72, M.paint, 0xfff3b0, -0.5, 1.58, 0);
  k.box(0.36, 0.03, 0.74, M.matte, BLACK, -0.5, 1.485, 0);
  endDecal(k, glow, uv, -0.5 + 0.172, 0.64, 1.5, 1.66, 1);
  endDecal(k, glow, uv, -0.5 - 0.172, 0.64, 1.5, 1.66, -1);
  const m = new Model('taxi', k.build(), wheelGeo(0.32, 0.22, 0.2, 0xb8bcc0, { holes: 5 }), fourWheels('taxi'));
  m.glow.push(glow);
  return m;
}

function police() {
  const k = new Kit(), M = mats(), s = SPECS.police, W = s.wid;
  saloon(k, WHITE);
  // the livery: a 1024 × 512 canvas, the two sides (front on the right for the right side), the bonnet and the boot
  const at = new Atlas(1024, 512), dec = decalMat(at);
  const X0 = -2.3, X1 = 2.3, Y0 = 0.34, Y1 = 0.98, BLUE = '#2d5aa8', CHECK = '#d6e01f';
  const side = (frontRight: boolean) => at.rect(1000, 140, (g, w, h) => {
    const px = (x: number) => (frontRight ? (x - X0) / (X1 - X0) : (X1 - x) / (X1 - X0)) * w, py = (y: number) => ((Y1 - y) / (Y1 - Y0)) * h;
    // the check: two rows of squares, yellow-green on the white
    g.fillStyle = CHECK;
    const sq = 0.072;
    for (let i = 0; X0 + 0.08 + i * sq < 2.12; i++) for (let row = 0; row < 2; row++) {
      if ((i + row) % 2) continue;
      const x = X0 + 0.08 + i * sq, a = px(x), b = px(x + sq);
      g.fillRect(Math.min(a, b), py(0.84 - row * sq), Math.abs(b - a) + 0.5, py(0.84 - (row + 1) * sq) - py(0.84 - row * sq) + 0.5);
    }
    // the blue panel on the front doors, leaning forwards, and the word
    const panel: P2[] = [[-0.3, 0.92], [0.69, 0.92], [1.0, 0.37], [0.03, 0.37]];
    g.fillStyle = BLUE;
    g.beginPath();
    panel.forEach(([x, y], i) => (i ? g.lineTo(px(x), py(y)) : g.moveTo(px(x), py(y))));
    g.fill();
    g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    fitText(g, 'RENDŐRSÉG', px(0.36), py(0.64), Math.abs(px(0.78) - px(-0.06)), 30, 800, FONT);
    // the wheel arches stay clear
    g.globalCompositeOperation = 'destination-out';
    for (const ax of s.axles) { g.beginPath(); g.arc(px(ax), py(s.r), (0.42 / (X1 - X0)) * w, 0, Math.PI * 2); g.fill(); }
    g.globalCompositeOperation = 'source-over';
  });
  const band = (pad: number) => at.rect(480, 56, (g, w, h) => {
    g.fillStyle = BLUE; g.fillRect(0, pad, w, h - 2 * pad);
    g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    fitText(g, 'RENDŐRSÉG', w / 2, h / 2 + 1, w - 60, h - 2 * pad - 8, 800, FONT);
  });
  sideDecal(k, dec, side(true), X0, X1, Y0, Y1, W / 2 + 0.004);
  sideDecal(k, dec, side(false), X0, X1, Y0, Y1, -W / 2 - 0.004);
  // on the bonnet, readable from in front (the slope from (2.12, 0.8) to (1.0, 0.97))
  const bon = band(4), lerp = (t: number): P2 => [2.12 + (1.0 - 2.12) * t, 0.8 + (0.97 - 0.8) * t + 0.008];
  const [b0, b1] = [lerp(0.08), lerp(0.2)], hw = 0.62;
  k.quad([b0[0], b0[1], hw], [b0[0], b0[1], -hw], [b1[0], b1[1], -hw], [b1[0], b1[1], hw], dec, 0xffffff, bon);
  endDecal(k, dec, band(8), -2.352, 0.9, 0.67, 0.77, -1);
  // the light bar: blue on the driver's side, red on the other, dark until switched on
  const blue = lit(new THREE.MeshStandardMaterial({ color: 0x2c4fd8, emissive: 0x3a66ff, emissiveIntensity: 0, roughness: 0.25 }));
  const red = lit(new THREE.MeshStandardMaterial({ color: 0xc62026, emissive: 0xff1a12, emissiveIntensity: 0, roughness: 0.25 }));
  k.box(0.3, 0.05, 1.2, M.matte, 0x202326, -0.48, 1.51, 0);
  k.box(0.26, 0.09, 0.5, blue, 0xffffff, -0.48, 1.58, -0.31);
  k.box(0.26, 0.09, 0.5, red, 0xffffff, -0.48, 1.58, 0.31);
  k.box(0.27, 0.07, 0.12, M.chrome, 0xe8eaec, -0.48, 1.575, 0);
  for (const z of [-0.45, 0.45]) k.box(0.1, 0.06, 0.06, M.matte, BLACK, -0.48, 1.47, z);
  const m = new Model('police', k.build(), wheelGeo(0.32, 0.225, 0.21, 0x3a3e43, { holes: 5, dark: 0x111315 }), fourWheels('police'));
  m.flash.push(blue, red);
  return m;
}

// ------------------------------------------------------------------ Trabant 601: pale blue with a white roof
function trabant() {
  const k = new Kit(), M = mats(), s = SPECS.trabant, [fa, ra] = s.axles, W = s.wid, BODY = 0x9cbcd2, ROOF = 0xf1efe6, CH = 0xd9dcdc;
  const lower: P2[] = [
    ...archedBottom(-1.74, 1.73, 0.27, s.r, [[ra, 0.37], [fa, 0.37]]),
    [1.775, 0.38], [1.78, 0.6], [1.745, 0.77], [1.63, 0.83], [0.72, 0.9], [-1.25, 0.93], [-1.68, 0.9], [-1.77, 0.8], [-1.775, 0.4],
  ];
  k.profile(lower, W, M.paint, BODY, 0, 0.06);
  k.box(3.3, 0.42, 0.98, M.matte, 0x24262a, 0, 0.48, 0);
  const gw = W - 0.14;
  k.profile([[0.79, 0.86], [0.17, 1.4], [-0.9, 1.415], [-1.37, 0.86]], gw, M.paint, BODY, 0, 0.06);
  k.profile([[0.24, 1.365], [0.13, 1.425], [-0.88, 1.44], [-0.98, 1.37]], gw + 0.03, M.paint, ROOF, 0, 0.05);   // the white roof
  // big glass, thin pillars
  const GL = 0x2c3a44;
  k.slope([0.734, 0.9], [0.17, 1.4], gw - 0.12, M.glass, GL, [0.02, 0.05]);
  k.slope([-0.9, 1.415], [-1.305, 0.93], gw - 0.16, M.glass, GL, [0.05, 0.03]);
  k.mirror((sd) => {
    const z = sd * (gw / 2 + 0.004), zs = sd * (W / 2 + 0.003);
    k.side([[0.59, 0.95], [0.14, 1.345], [-0.24, 1.35], [-0.24, 0.95]], z, M.glass, GL);
    k.side([[-0.31, 0.95], [-0.31, 1.35], [-0.88, 1.345], [-1.2, 0.95]], z, M.glass, GL);
    for (const x of [0.68, -0.3]) k.side([[x - 0.006, 0.33], [x + 0.006, 0.33], [x + 0.006, 0.86], [x - 0.006, 0.86]], zs, M.matte, 0x4e5a62);
    k.box(0.1, 0.022, 0.012, M.chrome, CH, -0.2, 0.84, zs);                         // door handle
    k.box(1.2, 0.018, 0.008, M.chrome, CH, 0.02, 0.62, zs);                          // the strip along the door
    // round headlamps in the wings, a chrome ring round each
    k.cyl(0.118, 0.14, M.paint, BODY, 1.69, 0.66, sd * 0.56, 'x', 18);
    k.cyl(0.1, 0.03, M.chrome, CH, 1.765, 0.66, sd * 0.56, 'x', 18);
    k.cyl(0.085, 0.03, M.lamp, 0xf6f4ea, 1.775, 0.66, sd * 0.56, 'x', 18);
    k.box(0.03, 0.045, 0.1, M.paint, 0xf09a1c, 1.775, 0.5, sd * 0.56);              // indicators
    // tail lamps at the corners, the indicator above
    k.box(0.04, 0.15, 0.12, M.tail, 0xb8191b, -1.775, 0.62, sd * 0.6);
    k.box(0.04, 0.05, 0.12, M.paint, 0xf09a1c, -1.775, 0.73, sd * 0.6);
    k.box(0.06, 0.12, 0.06, M.matte, 0x1d1d1d, 1.83, 0.4, sd * 0.3);                // bumper overriders
    k.box(0.06, 0.12, 0.06, M.matte, 0x1d1d1d, -1.83, 0.4, sd * 0.3);
  });
  // the slatted grille between the lamps
  k.box(0.02, 0.18, 0.74, M.matte, 0x1c2024, 1.772, 0.64, 0);
  for (let i = 0; i < 6; i++) k.box(0.03, 0.014, 0.72, M.paint, BODY, 1.782, 0.565 + i * 0.03, 0);
  // chrome bumpers, plates
  k.box(0.07, 0.085, 1.44, M.chrome, CH, 1.8, 0.38, 0);
  k.box(0.07, 0.085, 1.44, M.chrome, CH, -1.8, 0.38, 0);
  k.box(0.012, 0.11, 0.52, M.paint, PLATE, 1.842, 0.41, 0);
  k.box(0.012, 0.11, 0.34, M.paint, PLATE, -1.78, 0.56, 0);
  // the wing mirror, the driver's side only; the exhaust under the back
  k.cyl(0.05, 0.03, M.chrome, CH, 0.6, 1.0, -(W / 2 + 0.07), 'x', 12);
  k.box(0.02, 0.02, 0.08, M.chrome, CH, 0.6, 0.97, -(W / 2 + 0.03));
  k.cyl(0.025, 0.2, M.matte, 0x2a2a2a, -1.75, 0.3, -0.45, 'x', 8);
  return new Model('trabant', k.build(), wheelGeo(s.r, 0.145, 0.19, 0xb7bbbd, { holes: 4, cap: 0.085, dark: 0x5b6064 }), fourWheels('trabant'));
}

// ------------------------------------------------------------------ MOL Bubi: the lime 2021 bike, and its rider
function bubi() {
  const k = new Kit(), M = mats(), LIME = 0x96d21c, CH = 0xc4c9cd, BB: P2 = [-0.1, 0.28];
  const T = (a: P3, b: P3, r = 0.022, c = LIME, m: THREE.Material = M.paint) => k.tube(a, b, r, m, c);
  // the step-through frame: a curved down tube from the head tube to the bottom bracket
  T([0.36, 0.95, 0], [0.42, 0.76, 0], 0.03);
  const down: P2[] = [[0.4, 0.82], [0.29, 0.6], [0.17, 0.44], [0.03, 0.33], [-0.1, 0.28]];
  for (let i = 0; i < down.length - 1; i++) T([...down[i], 0] as P3, [...down[i + 1], 0] as P3, 0.03);
  T([-0.1, 0.28, 0], [-0.24, 0.82, 0], 0.024);
  k.mirror((s) => {
    T([-0.1, 0.28, s * 0.05], [-0.56, 0.33, s * 0.065], 0.013);   // chain stays
    T([-0.22, 0.74, s * 0.03], [-0.56, 0.33, s * 0.065], 0.012);  // seat stays
    T([0.42, 0.76, s * 0.04], [0.56, 0.33, s * 0.055], 0.016);    // fork
  });
  T([-0.24, 0.82, 0], [-0.27, 0.93, 0], 0.016, CH, M.chrome);     // seat post
  k.box(0.27, 0.06, 0.15, M.matte, 0x1c1d1f, -0.29, 0.955, 0);    // saddle
  k.box(0.1, 0.05, 0.19, M.matte, 0x1c1d1f, -0.38, 0.95, 0);
  // the bars: a stem up from the head tube, swept back, black grips
  T([0.36, 0.95, 0], [0.33, 1.06, 0], 0.018, CH, M.chrome);
  k.mirror((s) => {
    T([0.33, 1.06, 0], [0.3, 1.07, s * 0.14], 0.012, 0x2a2d30, M.matte);
    T([0.3, 1.07, s * 0.14], [0.2, 1.08, s * 0.29], 0.012, 0x2a2d30, M.matte);
    T([0.21, 1.08, s * 0.27], [0.17, 1.085, s * 0.33], 0.02, 0x161616, M.matte);
  });
  // the front carrier, a lime tube frame on the head tube, and its MOL Bubi plate
  k.mirror((s) => {
    T([0.42, 0.8, s * 0.04], [0.5, 0.86, s * 0.16], 0.014);
    T([0.48, 0.86, s * 0.17], [0.79, 0.86, s * 0.17], 0.014);
    T([0.79, 0.86, s * 0.17], [0.81, 1.0, s * 0.17], 0.014);
  });
  for (const x of [0.48, 0.64, 0.79]) T([x, 0.86, -0.17], [x, 0.86, 0.17], 0.012);
  k.box(0.025, 0.18, 0.38, M.paint, LIME, 0.81, 0.94, 0);
  k.box(0.04, 0.05, 0.08, M.matte, 0x1c1d1f, 0.83, 0.8, 0);
  k.box(0.01, 0.035, 0.06, M.lamp, 0xf6f6f0, 0.852, 0.8, 0);
  // the rear unit over the back wheel: lime, its lower part black like the chain case, a red reflector
  k.profile([[-0.17, 0.5], [-0.2, 0.78], [-0.27, 0.83], [-0.64, 0.83], [-0.71, 0.75], [-0.71, 0.6], [-0.62, 0.52]], 0.16, M.paint, LIME, 0, 0.03);
  k.profile([[-0.13, 0.4], [-0.16, 0.55], [-0.66, 0.58], [-0.6, 0.47], [-0.42, 0.42]], 0.17, M.matte, 0x1f2124, 0.02, 0.02);
  k.box(0.012, 0.05, 0.1, M.tail, 0xc0181b, -0.716, 0.7, 0);
  k.cyl(0.09, 0.012, M.chrome, CH, BB[0], BB[1], 0.07, 'z', 18);   // chainring
  // mudguards
  const guard = (cx: number, a0: number, a1: number) => {
    for (let i = 0; i < 6; i++) {
      const t0 = a0 + ((a1 - a0) * i) / 6, t1 = a0 + ((a1 - a0) * (i + 1)) / 6, R = 0.37;
      k.bar([cx + R * Math.cos(t0), 0.33 + R * Math.sin(t0)], [cx + R * Math.cos(t1), 0.33 + R * Math.sin(t1)], 0.008, 0.06, M.chrome, 0x9ea5ab);
    }
  };
  guard(0.56, 0.35, 2.1);
  guard(-0.56, 1.6, 2.9);
  // the logos: the plate in front, both sides of the rear unit (a honeycomb on the lime)
  const at = new Atlas(512, 256), dec = decalMat(at);
  const logo = (g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number) => {
    g.fillStyle = '#e3231b';
    g.beginPath(); g.roundRect(x, y, w, h, h * 0.22); g.fill();
    g.fillStyle = '#fff'; g.textBaseline = 'middle'; g.textAlign = 'left';
    fitText(g, 'MOL', x + w * 0.07, y + h * 0.53, w * 0.26, h * 0.42, 800, FONT);
    g.beginPath(); g.arc(x + w * 0.44, y + h / 2, h * 0.26, 0, Math.PI * 2); g.lineWidth = h * 0.07; g.strokeStyle = '#fff'; g.stroke();
    fitText(g, 'BUBI', x + w * 0.56, y + h * 0.54, w * 0.4, h * 0.6, 900, FONT);
  };
  const plate = at.rect(256, 120, (g, w, h) => {
    g.fillStyle = '#96d21c'; g.fillRect(0, 0, w, h);
    logo(g, w * 0.1, h * 0.24, w * 0.8, h * 0.52);
  });
  const panel = at.rect(240, 160, (g, w, h) => {
    g.fillStyle = '#96d21c'; g.fillRect(0, 0, w, h);
    g.strokeStyle = 'rgba(255,255,255,.28)'; g.lineWidth = 1.5;
    const r = 9;
    for (let row = 0; row * r * 1.5 < h + r; row++) for (let col = 0; col * r * 1.73 < w + r; col++) {
      const cx = col * r * 1.73 + (row % 2) * r * 0.866, cy = row * r * 1.5;
      g.beginPath();
      for (let i = 0; i < 6; i++) { const a = Math.PI / 6 + (i * Math.PI) / 3; g.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a)); }
      g.closePath(); g.stroke();
    }
    logo(g, w * 0.14, h * 0.2, w * 0.72, h * 0.3);
    g.fillStyle = '#fff'; g.textAlign = 'center';
    fitText(g, 'BUDAPEST', w / 2, h * 0.7, w * 0.6, h * 0.12, 700, FONT);
  });
  endDecal(k, dec, plate, 0.824, 0.36, 0.86, 1.02, 1);
  sideDecal(k, dec, panel, -0.67, -0.24, 0.58, 0.79, 0.083);
  sideDecal(k, dec, panel, -0.67, -0.24, 0.58, 0.79, -0.083);
  // the rider, after the mayor, who cycles to work: dark short hair, glasses, a navy blazer worn open over a white
  // shirt, no tie. Hips on the saddle, leaning to the bars (the legs and cranks move: Rider); the neck runs from inside
  // the shoulders into the head, so the head sits on the body from every side
  const SKIN = 0xd9a487, JACKET = 0x1f2a44, SHIRT = 0xf1f1ee, TROUSERS = 0x2a2e37, HAIR = 0x2e221b, HIP: P2 = [-0.25, 1.01];
  k.box(0.24, 0.17, 0.32, M.matte, TROUSERS, -0.24, 1.05, 0);
  k.bar([-0.24, 1.08], [-0.02, 1.5], 0.22, 0.36, M.matte, JACKET);
  k.box(0.2, 0.1, 0.4, M.matte, JACKET, -0.03, 1.47, 0, 0, 0, -0.45);           // shoulders
  // the blazer worn open: the white shirt shows down the whole front between its edges, which stand a little proud
  k.box(0.45, 0.02, 0.13, M.matte, SHIRT, -0.035, 1.24, 0, 0, 0, 1.088);
  k.mirror((s) => k.box(0.46, 0.035, 0.035, M.matte, 0x18213a, -0.03, 1.238, s * 0.082, 0, 0, 1.088));
  k.cyl(0.055, 0.2, M.matte, SKIN, 0.02, 1.57, 0, 'y', 10);                     // neck
  k.box(0.13, 0.035, 0.15, M.matte, SHIRT, 0.015, 1.535, 0, 0, 0, -0.2);        // collar
  k.add(new THREE.SphereGeometry(0.105, 14, 10), M.matte, SKIN, 0.04, 1.69, 0);
  // hair: a cap over the top and the back, short at the sides
  k.add(new THREE.SphereGeometry(0.112, 14, 8, 0, Math.PI * 2, 0, Math.PI * 0.46), M.matte, HAIR, 0.03, 1.695, 0, 0, 0, 0.28);
  k.mirror((s) => k.box(0.03, 0.045, 0.02, M.matte, SKIN, 0.03, 1.69, s * 0.105));
  // glasses: dark rims, the bridge and the arms
  k.mirror((s) => {
    k.box(0.012, 0.045, 0.06, M.matte, 0x15171a, 0.142, 1.705, s * 0.042);
    k.box(0.008, 0.03, 0.045, M.glass, 0x9fb4c4, 0.146, 1.705, s * 0.042);
    k.box(0.1, 0.01, 0.01, M.matte, 0x15171a, 0.09, 1.712, s * 0.098);
  });
  k.box(0.012, 0.01, 0.03, M.matte, 0x15171a, 0.142, 1.712, 0);
  k.box(0.03, 0.03, 0.025, M.matte, 0xcf9a7e, 0.15, 1.675, 0);                  // nose
  k.mirror((s) => {
    k.tube([-0.03, 1.46, s * 0.18], [0.09, 1.27, s * 0.24], 0.045, M.matte, JACKET);
    k.tube([0.09, 1.27, s * 0.24], [0.19, 1.1, s * 0.29], 0.04, M.matte, JACKET);
    k.box(0.07, 0.05, 0.05, M.matte, SKIN, 0.19, 1.09, s * 0.3);
  });
  const spots: WheelSpot[] = [{ x: 0.56, z: 0, r: 0.33, front: true, w: 1 }, { x: -0.56, z: 0, r: 0.33, front: false, w: 1 }];
  const m = new Model('bubi', k.build(), wheelGeo(0.33, 0.045, 0.3, 0xc9ced2, { spokes: 18 }), spots);
  m.rider = new Rider(BB, HIP, [CH, 0x1d1d1d, TROUSERS, TROUSERS, 0xe9e9e6, CH, 0x1d1d1d, TROUSERS, TROUSERS, 0xe9e9e6]);
  m.g.add(m.rider.limbs);
  return m;
}

// ------------------------------------------------------------------ BKK bus: a blue Citaro C2, route 7
function bus() {
  const k = new Kit(), M = mats(), s = SPECS.bus, [fa, ra] = s.axles, W = s.wid, BLUE = 0x2b93d9, DARK = 0x141b20, z = W / 2;
  const body: P2[] = [
    ...archedBottom(-6.02, 6.02, 0.3, s.r, [[ra, 0.6], [fa, 0.58]]),
    [6.07, 0.45], [6.08, 1.0], [6.05, 2.7], [5.98, 2.93], [5.84, 2.99], [-5.9, 2.99], [-6.03, 2.92], [-6.07, 2.6], [-6.08, 0.45],
  ];
  k.profile(body, W, M.paint, BLUE, 0, 0.12);
  k.box(11.6, 0.8, 1.3, M.matte, 0x1e2226, 0, 0.7, 0);
  // the roof: air conditioning in front, a smaller hatch behind
  k.plan([[3.6, -0.9], [3.6, 0.9], [-0.9, 0.9], [-0.9, -0.9]], 0.2, M.paint, 0x3a9ddc, 2.95, 0.08);
  k.plan([[-3.2, -0.6], [-3.2, 0.6], [-4.6, 0.6], [-4.6, -0.6]], 0.1, M.paint, 0x3a9ddc, 2.95, 0.04);
  // the black window band, pane lines on it; the doors on the right: double leaves of dark glass
  const doors: [number, number][] = [[4.55, 5.75], [0.0, 1.2], [-4.45, -3.25]];
  k.mirror((sd) => {
    const zz = sd * (z + 0.004);
    const x1 = sd > 0 ? 4.4 : 5.6;
    k.side([[-5.78, 1.12], [x1, 1.12], [x1 + 0.12, 2.64], [-5.78, 2.64]], zz, M.glass, DARK);
    for (let x = -4.9; x < x1 - 0.4; x += 1.45) {
      if (sd > 0 && doors.some(([a, b]) => x > a - 0.1 && x < b + 0.1)) continue;
      k.side([[x - 0.02, 1.12], [x + 0.02, 1.12], [x + 0.02, 2.64], [x - 0.02, 2.64]], zz + sd * 0.002, M.matte, 0x34404a);
    }
    // the skirt, between the arches
    for (const [a, b] of [[-5.95, ra - 0.62], [ra + 0.62, fa - 0.6], [fa + 0.6, 5.95]]) k.box(b - a, 0.1, 0.02, M.matte, 0x1d2226, (a + b) / 2, 0.36, sd * (z - 0.005));
    k.box(0.5, 0.03, 0.02, M.chrome, 0xb0b8c0, -5.0, 0.95, zz);
    k.box(0.04, 0.2, 0.3, M.lamp, 0xf2f4f8, 6.075, 0.62, sd * 0.93);                       // headlamps
    k.box(0.04, 0.08, 0.2, M.paint, 0xf09a1c, 6.075, 0.8, sd * 0.98);
    k.box(0.04, 0.85, 0.14, M.tail, 0xc0181b, -6.08, 1.0, sd * 1.12);                      // tail lamps
    // the mirrors on stalks over the windscreen corners
    k.tube([5.9, 2.82, sd * 1.15], [6.35, 2.75, sd * 1.32], 0.025, M.matte, BLACK);
    k.tube([6.35, 2.75, sd * 1.32], [6.42, 2.45, sd * 1.34], 0.025, M.matte, BLACK);
    k.box(0.08, 0.42, 0.24, M.matte, BLACK, 6.44, 2.25, sd * 1.34);
  });
  for (const [a, b] of doors) {
    k.side([[a, 0.34], [b, 0.34], [b, 2.64], [a, 2.64]], z + 0.006, M.matte, 0x22292f);
    const m = (a + b) / 2;
    k.side([[a + 0.05, 0.4], [m - 0.02, 0.4], [m - 0.02, 2.58], [a + 0.05, 2.58]], z + 0.009, M.glass, 0x24323c);
    k.side([[m + 0.02, 0.4], [b - 0.05, 0.4], [b - 0.05, 2.58], [m + 0.02, 2.58]], z + 0.009, M.glass, 0x24323c);
    k.box(b - a - 0.14, 0.03, 0.02, M.chrome, 0xb0b8c0, m, 1.5, z + 0.012);
  }
  // the front: a big windscreen, the destination display over it, the bumper
  k.slope([6.08, 1.0], [6.05, 2.7], 2.24, M.glass, DARK, [0.02, 0.02]);
  k.box(0.1, 0.3, 2.5, M.matte, 0x24282c, 6.07, 0.42, 0);
  k.box(0.012, 0.11, 0.52, M.paint, PLATE, 6.125, 0.5, 0);
  // the back: the engine bay, a window over it, a display, the bumper
  k.slope([-6.07, 2.6], [-6.08, 1.7], 2.0, M.glass, DARK, [0.05, 0.02]);
  k.box(0.03, 0.62, 1.7, M.matte, 0x1f262c, -6.08, 1.05, 0);
  for (let i = 0; i < 5; i++) k.box(0.03, 0.03, 1.6, M.matte, 0x0f1316, -6.095, 0.82 + i * 0.11, 0);
  k.box(0.1, 0.3, 2.5, M.matte, 0x24282c, -6.07, 0.42, 0);
  k.box(0.012, 0.11, 0.52, M.paint, PLATE, -6.125, 0.62, 0);
  // the LED displays (the 7 to Újpalota: the number, then the destination where there's room) and the white
  // BUDAPEST on the front and the sides
  const at = new Atlas(512, 256), glow = decalMat(at, true), dec = decalMat(at);
  const led = (w: number, h: number, dest: string | null) => at.rect(w, h, (g) => {
    g.fillStyle = '#0b0c0d'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#ffae2a'; g.textBaseline = 'middle';
    const nw = dest ? h * 1.9 : w - 12;
    g.textAlign = dest ? 'left' : 'center';
    fitText(g, ROUTE, dest ? 8 : w / 2, h / 2 + 1, nw, h * 0.8, 800, FONT);
    g.textAlign = 'left';
    if (dest) fitText(g, dest, 8 + nw + h * 0.3, h / 2 + 1, w - nw - h * 0.3 - 16, h * 0.55, 700, FONT);
    g.fillStyle = 'rgba(0,0,0,.55)';                                  // the dots of the matrix
    for (let x = 0; x < w; x += 3) g.fillRect(x, 0, 1, h);
    for (let y = 0; y < h; y += 3) g.fillRect(0, y, w, 1);
  });
  const front = led(400, 50, DEST), sideD = led(220, 34, DEST), rear = led(150, 48, null);
  endDecal(k, glow, front, [6.056, 5.998], 1.94, 2.71, 2.91, 1);
  sideDecal(k, glow, sideD, 3.05, 4.15, 2.36, 2.57, z + 0.008);
  endDecal(k, glow, rear, -6.08, 0.62, 2.66, 2.86, -1, 0.4);
  const word = at.rect(300, 48, (g, w, h) => {
    g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    fitText(g, 'BUDAPEST', w / 2, h / 2 + 1, w - 8, h * 0.75, 800, FONT);
  });
  endDecal(k, dec, word, 6.09, 0.9, 0.84, 0.98, 1);
  sideDecal(k, dec, word, -2.1, -0.7, 0.62, 0.84, z + 0.004);
  sideDecal(k, dec, word, -2.1, -0.7, 0.62, 0.84, -z - 0.004);
  const m = new Model('bus', k.build(), wheelGeo(s.r, 0.3, 0.3, 0xc5cacf, { holes: 8, cap: 0.11, dark: 0x6c7277 }), fourWheels('bus', 1.75));
  m.glow.push(glow);
  return m;
}

const BUILD: Record<VehicleKind, () => Model> = { taxi, trabant, police, bubi, bus };
export const buildModel = (k: VehicleKind) => BUILD[k]();
