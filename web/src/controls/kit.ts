// A small kit for building the vehicles out of boxes, cylinders, extruded side outlines and flat panels. Every part is
// painted with a vertex colour and collected per material; build() merges each material's parts into one mesh, so a
// whole vehicle costs a handful of draw calls. Units are metres: x forward, y up, z to the right.
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export type P2 = [number, number];
export type P3 = [number, number, number];

// shared by every vehicle (only one is on screen at a time); lamp and tail glow are set by the time of day
let shared: ReturnType<typeof makeMats> | null = null;
function makeMats() {
  const S = (o: THREE.MeshStandardMaterialParameters) => new THREE.MeshStandardMaterial({ vertexColors: true, ...o });
  return {
    paint: S({ roughness: 0.38 }),
    matte: S({ roughness: 0.88 }),
    chrome: S({ roughness: 0.2 }),
    glass: S({ roughness: 0.08, emissive: 0x1a2630, emissiveIntensity: 0.35 }),
    lamp: S({ roughness: 0.3, emissive: 0xfff2d0, emissiveIntensity: 0.3 }),
    tail: S({ roughness: 0.4, emissive: 0xff1208, emissiveIntensity: 0.3 }),
    wheel: S({ roughness: 0.62 }),
  };
}
export const mats = () => (shared ??= makeMats());

// the street lamps light the vehicles as they light the street: the city's lamp-pool texture (engine/material.ts)
// read at each fragment's place on the map and added to what the surface gives back, as on the voxels. No lights: a
// real one would light (and recompile) the whole city.
type LampU = Record<'uLamps' | 'uMapSize' | 'uNight', THREE.IUniform>;
let lampU: LampU | null = null;
const waiting: THREE.Material[] = [];
export function lampLit(u: LampU) {
  lampU = u;
  for (const m of [...Object.values(mats()), ...waiting.splice(0)]) lit(m);
}

// a vehicle's material that the lamps light too (the shared ones, and each vehicle's lettering, lights and rims)
export function lit<M extends THREE.Material>(m: M): M {
  const u = lampU;
  if (!u) { waiting.push(m); return m; }
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, u);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vLampW;')
      .replace('#include <project_vertex>', `#include <project_vertex>
        vec4 lampW = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          lampW = instanceMatrix * lampW;
        #endif
        vLampW = (modelMatrix * lampW).xyz;`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vLampW; uniform sampler2D uLamps; uniform vec2 uMapSize; uniform float uNight;')
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
        if (uNight > 0.0) totalEmissiveRadiance += diffuseColor.rgb * texture2D(uLamps, vLampW.xz / uMapSize).rgb * uNight * 2.0;`);
  };
  m.needsUpdate = true;
  return m;
}

const tmpC = new THREE.Color();
function colour(g: THREE.BufferGeometry, c: number) {
  const n = g.attributes.position.count, a = new Float32Array(n * 3);
  tmpC.set(c);
  for (let i = 0; i < n; i++) { a[i * 3] = tmpC.r; a[i * 3 + 1] = tmpC.g; a[i * 3 + 2] = tmpC.b; }
  g.setAttribute('color', new THREE.BufferAttribute(a, 3));
  return g;
}

// position, normal, uv and colour only, unindexed, so that anything merges with anything
function clean(g: THREE.BufferGeometry) {
  const out = g.index ? g.toNonIndexed() : g;
  for (const k of Object.keys(out.attributes)) if (k !== 'position' && k !== 'normal' && k !== 'uv') out.deleteAttribute(k);
  if (!out.attributes.uv) out.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(out.attributes.position.count * 2), 2));
  out.clearGroups();
  return out;
}

const ONE = new THREE.Vector3(1, 1, 1);

export class Kit {
  private readonly parts = new Map<THREE.Material, THREE.BufferGeometry[]>();
  private readonly mx = new THREE.Matrix4();
  private readonly q = new THREE.Quaternion();
  private readonly e = new THREE.Euler();
  private readonly v = new THREE.Vector3();

  add(g: THREE.BufferGeometry, mat: THREE.Material, c: number, x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0) {
    const geo = clean(g);
    geo.applyMatrix4(this.mx.compose(this.v.set(x, y, z), this.q.setFromEuler(this.e.set(rx, ry, rz)), ONE));
    colour(geo, c);
    const list = this.parts.get(mat) ?? [];
    list.push(geo);
    this.parts.set(mat, list);
    return this;
  }

  // l along x, h along y, w along z, centred on (x, y, z)
  box(l: number, h: number, w: number, mat: THREE.Material, c: number, x: number, y: number, z: number, rx = 0, ry = 0, rz = 0) {
    return this.add(new THREE.BoxGeometry(l, h, w), mat, c, x, y, z, rx, ry, rz);
  }

  // a box between two points of the side view (a strut, a pillar, a tube), t thick in y, w wide in z
  bar(a: P2, b: P2, t: number, w: number, mat: THREE.Material, c: number, z = 0) {
    const dx = b[0] - a[0], dy = b[1] - a[1];
    return this.box(Math.hypot(dx, dy), t, w, mat, c, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z, 0, 0, Math.atan2(dy, dx));
  }

  // a round tube between two points in space
  tube(a: P3, b: P3, r: number, mat: THREE.Material, c: number, seg = 8) {
    const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), d = B.clone().sub(A), len = d.length();
    const g = new THREE.CylinderGeometry(r, r, len, seg, 1, true);
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
    g.applyQuaternion(q);
    return this.add(g, mat, c, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
  }

  // a cylinder of radius r and length len along an axis
  cyl(r: number, len: number, mat: THREE.Material, c: number, x: number, y: number, z: number, axis: 'x' | 'y' | 'z' = 'z', seg = 16, r2 = r) {
    const g = new THREE.CylinderGeometry(r2, r, len, seg);
    if (axis === 'x') g.rotateZ(-Math.PI / 2);
    if (axis === 'z') g.rotateX(Math.PI / 2);
    return this.add(g, mat, c, x, y, z);
  }

  // a side outline (x forward, y up) extruded w across, centred on z, its edges rounded by bevel
  profile(pts: P2[], w: number, mat: THREE.Material, c: number, z = 0, bevel = 0.04) {
    const shape = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
    const b = Math.min(bevel, w / 2 - 0.001);
    const g = new THREE.ExtrudeGeometry(shape, {
      depth: w - 2 * b, bevelEnabled: b > 0, bevelThickness: b, bevelSize: b, bevelOffset: -b, bevelSegments: 2, curveSegments: 4,
    });
    return this.add(g, mat, c, 0, 0, z - w / 2 + b);
  }

  // an outline seen from above (x forward, z right) extruded h up from y
  plan(pts: P2[], h: number, mat: THREE.Material, c: number, y = 0, bevel = 0.03) {
    const shape = new THREE.Shape(pts.map(([x, z]) => new THREE.Vector2(x, -z)));
    const b = Math.min(bevel, h / 2 - 0.001);
    const g = new THREE.ExtrudeGeometry(shape, {
      depth: h - 2 * b, bevelEnabled: b > 0, bevelThickness: b, bevelSize: b, bevelOffset: -b, bevelSegments: 2, curveSegments: 4,
    });
    g.rotateX(-Math.PI / 2);
    return this.add(g, mat, c, 0, y + b, 0);
  }

  // a flat panel in the side view at z, facing out (+z on the right side, -z on the left)
  side(pts: P2[], z: number, mat: THREE.Material, c: number) {
    const s = z >= 0 ? 1 : -1;
    const g = new THREE.ShapeGeometry(new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(s * x, y))));
    if (s < 0) g.rotateY(Math.PI);
    return this.add(g, mat, c, 0, 0, z);
  }

  // a flat quad through four points (in order round it), facing the side the winding gives
  quad(a: P3, b: P3, c: P3, d: P3, mat: THREE.Material, col: number, uv: [number, number, number, number] = [0, 0, 1, 1]) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([...a, ...b, ...c, ...a, ...c, ...d]), 3));
    const [u0, v0, u1, v1] = uv;
    g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array([u0, v0, u1, v0, u1, v1, u0, v0, u1, v1, u0, v1]), 2));
    g.computeVertexNormals();
    return this.add(g, mat, col);
  }

  // a panel w wide on the face of an extruded outline between two of its points (a windscreen, a rear window), inset
  // from the ends by i and lifted off by off; it faces up, or forwards / backwards if the face is upright
  slope(a: P2, b: P2, w: number, mat: THREE.Material, c: number, i: [number, number] = [0, 0], off = 0.006) {
    const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L;
    let nx = uy, ny = -ux;  // the normal that the winding below gives
    const flip = Math.abs(ny) > 1e-4 ? ny < 0 : nx * (a[0] + b[0]) < 0;
    if (flip) { nx = -nx; ny = -ny; }
    const p = (t: number): P2 => [a[0] + ux * t + nx * off, a[1] + uy * t + ny * off];
    const s = p(i[0]), e = p(L - i[1]), h = w / 2;
    return flip
      ? this.quad([s[0], s[1], h], [e[0], e[1], h], [e[0], e[1], -h], [s[0], s[1], -h], mat, c)
      : this.quad([s[0], s[1], -h], [e[0], e[1], -h], [e[0], e[1], h], [s[0], s[1], h], mat, c);
  }

  mirror(f: (s: 1 | -1) => void) { f(1); f(-1); }

  // one mesh per material
  build(shadow = true) {
    const g = new THREE.Group();
    for (const [mat, list] of this.parts) {
      const geo = mergeGeometries(list, false);
      if (!geo) continue;
      for (const l of list) l.dispose();
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = shadow && !(mat as THREE.Material & { userData: { noShadow?: boolean } }).userData.noShadow;
      m.frustumCulled = false;
      g.add(m);
    }
    this.parts.clear();
    return g;
  }

  // the same parts as one geometry (for instanced wheels and limbs)
  geometry() {
    const all = [...this.parts.values()].flat();
    const geo = mergeGeometries(all, false)!;
    for (const l of all) l.dispose();
    this.parts.clear();
    return geo;
  }
}

// the bottom edge of a side outline from x0 (rear) to x1 (front) at height y, with wheel arches cut into it: [x, r]
// round each axle (whose centre is at height ay)
export function archedBottom(x0: number, x1: number, y: number, ay: number, arches: [number, number][]): P2[] {
  const out: P2[] = [[x0, y]];
  for (const [ax, r] of [...arches].sort((a, b) => a[0] - b[0])) {
    const dy = y - ay, half = Math.sqrt(Math.max(r * r - dy * dy, 0)), t0 = Math.atan2(dy, -half), t1 = Math.atan2(dy, half);
    // from the rear foot of the arch over its top to the front foot (angles from t0 down to t1, through pi/2)
    const a0 = t0 < 0 ? t0 + 2 * Math.PI : t0;
    for (let k = 0; k <= 10; k++) {
      const t = a0 + (t1 - a0) * (k / 10);
      out.push([ax + r * Math.cos(t), ay + r * Math.sin(t)]);
    }
  }
  out.push([x1, y]);
  return out;
}

// a canvas cut into rectangles for a vehicle's lettering, with the uv of each
export class Atlas {
  readonly canvas = document.createElement('canvas');
  readonly ctx: CanvasRenderingContext2D;
  readonly texture: THREE.CanvasTexture;
  private x = 0;
  private y = 0;
  private row = 0;

  constructor(readonly width = 512, readonly height = 512) {
    this.canvas.width = width;
    this.canvas.height = height;
    this.ctx = this.canvas.getContext('2d')!;
    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.anisotropy = 4;
  }

  // a w × h px rectangle drawn by f (its origin at the rectangle's top left); returns its uv [u0, v0, u1, v1]
  rect(w: number, h: number, f: (g: CanvasRenderingContext2D, w: number, h: number) => void): [number, number, number, number] {
    if (this.x + w > this.width) { this.x = 0; this.y += this.row + 2; this.row = 0; }
    const g = this.ctx, x = this.x, y = this.y;
    g.save();
    g.translate(x, y);
    g.beginPath();
    g.rect(0, 0, w, h);
    g.clip();
    f(g, w, h);
    g.restore();
    this.x += w + 2;
    this.row = Math.max(this.row, h);
    const W = this.width, H = this.height;
    return [(x + 0.5) / W, 1 - (y + h - 0.5) / H, (x + w - 0.5) / W, 1 - (y + 0.5) / H];
  }
}

// text that fits a width
export function fitText(g: CanvasRenderingContext2D, text: string, x: number, y: number, maxW: number, px: number, weight = 700,
  family = 'system-ui, "Segoe UI", Roboto, Arial, sans-serif') {
  let s = px;
  do { g.font = `${weight} ${s}px ${family}`; s -= 1; } while (g.measureText(text).width > maxW && s > 6);
  g.fillText(text, x, y);
}
