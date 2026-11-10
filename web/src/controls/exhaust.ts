// Exhaust fumes: soft round puffs from the vehicle's pipe, one instanced quad each and one draw call for them all,
// that grow, fade and drift up and away with the breeze, left behind as the vehicle moves on. The Trabant's two-stroke
// puffs blue-grey at idle and pours it out under throttle; the taxi and the police car only breathe a little when
// pulling away or on a cold day; the bus's diesel goes dark as it pulls away. Not lit by three.js's lights (a new
// light would recompile every program): the shader takes the scene's hemisphere and sun as one colour, and the tail
// lamps' red.
import * as THREE from 'three';
import { clamp, smoothstep } from '../util';
import type { Smoke, Spec } from './vehicles';

interface Look { col: [number, number, number]; dark?: [number, number, number]; size: [number, number]; life: number; alpha: number; jet: number }

const SMOKES: Smoke[] = ['two-stroke', 'petrol', 'diesel'];
const LOOK: Look[] = [
  { col: [0.36, 0.44, 0.6], size: [0.12, 0.95], life: 2.8, alpha: 0.68, jet: 2.2 },
  { col: [0.82, 0.83, 0.86], size: [0.08, 0.6], life: 1.3, alpha: 0.22, jet: 2.5 },
  { col: [0.62, 0.62, 0.64], dark: [0.22, 0.22, 0.23], size: [0.22, 1.45], life: 2.6, alpha: 0.7, jet: 4.2 },
];
const WIND = [0.55, 0.3];   // m/s in x and z: a light breeze
const D = 8;                // per puff: age, life, seed, the road's height under it, thickness 0..1, kind, spare

const VERT = /* glsl */ `
  attribute vec2 corner;
  attribute vec3 iPos; attribute vec4 iCol; attribute vec3 iSRG;   // size, turn, the road's height
  uniform vec3 uLight; uniform vec4 uTail;
  varying vec2 vUv; varying vec4 vCol; varying float vY; varying float vFloor;
  void main() {
    float c = cos(iSRG.y), s = sin(iSRG.y);
    vec2 q = vec2(c * corner.x - s * corner.y, s * corner.x + c * corner.y) * iSRG.x;
    vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]), up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
    vec3 p = iPos + right * q.x + up * q.y, d = iPos - uTail.xyz;
    vCol = vec4(iCol.rgb * (uLight + vec3(1.0, 0.1, 0.05) * uTail.w * exp(-dot(d, d) / 0.7)), iCol.a);
    vUv = corner; vY = p.y; vFloor = iSRG.z + 0.04;
    gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
  }`;
const FRAG = /* glsl */ `
  varying vec2 vUv; varying vec4 vCol; varying float vY; varying float vFloor;
  void main() {
    float a = 1.0 - smoothstep(0.1, 1.0, length(vUv));
    a *= a * (0.8 + 0.2 * sin(vUv.x * 5.1 + 1.7) * sin(vUv.y * 4.3 + 0.6));
    a *= vCol.a * smoothstep(vFloor, vFloor + 0.25, vY);   // soft where it meets the road
    if (a < 0.004) discard;
    gl_FragColor = vec4(vCol.rgb, a);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

export class Exhaust {
  readonly mesh: THREE.Mesh;
  private n = 0;
  private acc = 0;
  private pulse = 0;
  private readonly pos: Float32Array;
  private readonly vel: Float32Array;
  private readonly dat: Float32Array;
  private readonly iPos: THREE.InstancedBufferAttribute;
  private readonly iCol: THREE.InstancedBufferAttribute;
  private readonly iSRG: THREE.InstancedBufferAttribute;
  private readonly geo = new THREE.InstancedBufferGeometry();
  private readonly u = { uLight: { value: new THREE.Color(1, 1, 1) }, uTail: { value: new THREE.Vector4() } };
  private lights: { hemi: THREE.HemisphereLight | null; dirs: THREE.DirectionalLight[] } | null = null;
  private readonly a = new THREE.Vector3();
  private readonly b = new THREE.Vector3();
  private readonly c = new THREE.Color();

  constructor(private readonly scene: THREE.Scene, private readonly max: number) {
    const g = this.geo;
    g.setAttribute('corner', new THREE.BufferAttribute(new Float32Array([-1, -1, 1, -1, 1, 1, -1, 1]), 2));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    this.iPos = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
    this.iCol = new THREE.InstancedBufferAttribute(new Float32Array(max * 4), 4);
    this.iSRG = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
    for (const [k, a] of [['iPos', this.iPos], ['iCol', this.iCol], ['iSRG', this.iSRG]] as const) {
      a.setUsage(THREE.DynamicDrawUsage);
      g.setAttribute(k, a);
    }
    g.instanceCount = 0;
    this.pos = new Float32Array(max * 3);
    this.vel = new Float32Array(max * 3);
    this.dat = new Float32Array(max * D);
    const m = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: this.u, transparent: true, depthWrite: false });
    this.mesh = new THREE.Mesh(g, m);
    this.mesh.frustumCulled = false;
    this.mesh.visible = false;
    scene.add(this.mesh);
  }

  get count() { return this.n; }

  clear() { this.n = 0; this.acc = 0; this.geo.instanceCount = 0; }

  // a puff at (x, y, z) moving (vx, vy, vz); when full, the oldest goes
  private spawn(x: number, y: number, z: number, vx: number, vy: number, vz: number, kind: number, ground: number, thick: number, age: number) {
    let i = this.n;
    if (i < this.max) this.n++;
    else {
      i = 0;
      for (let k = 1; k < this.n; k++) if (this.dat[k * D] / this.dat[k * D + 1] > this.dat[i * D] / this.dat[i * D + 1]) i = k;
    }
    this.pos[i * 3] = x; this.pos[i * 3 + 1] = y; this.pos[i * 3 + 2] = z;
    this.vel[i * 3] = vx; this.vel[i * 3 + 1] = vy; this.vel[i * 3 + 2] = vz;
    const d = this.dat, o = i * D;
    d[o] = age; d[o + 1] = LOOK[kind].life * (0.75 + 0.5 * Math.random()); d[o + 2] = Math.random(); d[o + 3] = ground;
    d[o + 4] = thick; d[o + 5] = kind;
  }

  // model: the vehicle's group (its matrix is set from its pose); vel: how it moves (m/s); ground: the road under it;
  // throttle 0..1; night, cold 0..1
  update(dt: number, spec: Spec, model: THREE.Object3D, vel: THREE.Vector3, ground: number, throttle: number, night: number,
    cold: number, braking: boolean) {
    model.updateMatrix();
    const ex = spec.exhaust;
    if (ex && dt > 0) {
      const s = vel.length(), rel = Math.min(s / spec.vmax, 1), pull = throttle * (1 - 0.6 * rel), idle = s < 0.6 && throttle < 0.05;
      const kind = SMOKES.indexOf(ex.smoke);
      let rate = 0, thick = 1;
      if (kind === 0) {
        // a steady pop-pop at idle, a thick plume under throttle
        this.pulse += dt;
        if (!idle) rate = 6 + 30 * pull + 4 * cold;
        else if (this.pulse > 0.34) { this.pulse = 0; this.acc += 2 + Math.random(); }
        thick = 0.7 + 0.3 * pull;
      } else if (kind === 1) {
        rate = 16 * pull * pull * (0.35 + 0.65 * cold) + 5 * cold * (idle ? 1 : 0.4);
        thick = 0.5 + 0.5 * Math.max(pull, cold);
      } else {
        rate = 3 + 24 * pull;
        thick = pull;
      }
      this.acc += rate * dt;
      if (this.acc >= 1) {
        const at = this.a.set(...ex.at).applyMatrix4(model.matrix), dir = this.b.set(...ex.dir).normalize().transformDirection(model.matrix);
        const jet = LOOK[kind].jet * (0.5 + 0.8 * Math.max(pull, 0.3));
        for (; this.acc >= 1; this.acc -= 1) {
          // spread along this frame's path, so a fast vehicle leaves a trail rather than clumps
          const f = Math.random() * dt, r = () => (Math.random() - 0.5) * 0.5;
          this.spawn(at.x - vel.x * f, at.y - vel.y * f, at.z - vel.z * f,
            vel.x * 0.3 + dir.x * jet + r(), vel.y * 0.3 + dir.y * jet + Math.random() * 0.3, vel.z * 0.3 + dir.z * jet + r(),
            kind, ground, thick, f);
        }
      }
    }
    this.step(dt);
    this.light(night, braking, model, spec);
  }

  private step(dt: number) {
    const P = this.pos, V = this.vel, d = this.dat, drag = 1 - Math.exp(-dt * 3.2);
    for (let i = 0; i < this.n; i++) {
      const o = i * D;
      d[o] += dt;
      if (d[o] >= d[o + 1]) {   // gone: the last one takes its place
        const j = --this.n;
        if (i < j) {
          P.copyWithin(i * 3, j * 3, j * 3 + 3); V.copyWithin(i * 3, j * 3, j * 3 + 3); d.copyWithin(o, j * D, j * D + D);
          i--;
        }
        continue;
      }
      const age = d[o], seed = d[o + 2];
      V[i * 3] += (WIND[0] - V[i * 3]) * drag + Math.sin(age * 2.7 + seed * 40) * 0.5 * dt;
      V[i * 3 + 1] += (0.6 - V[i * 3 + 1]) * drag * 0.6;     // rising slowly
      V[i * 3 + 2] += (WIND[1] - V[i * 3 + 2]) * drag + Math.cos(age * 2.3 + seed * 30) * 0.5 * dt;
      P[i * 3] += V[i * 3] * dt; P[i * 3 + 1] += V[i * 3 + 1] * dt; P[i * 3 + 2] += V[i * 3 + 2] * dt;
      if (P[i * 3 + 1] < d[o + 3] + 0.15) { P[i * 3 + 1] = d[o + 3] + 0.15; V[i * 3 + 1] = Math.max(V[i * 3 + 1], 0); }   // off the road
    }
    const ip = this.iPos.array as Float32Array, ic = this.iCol.array as Float32Array, is = this.iSRG.array as Float32Array;
    for (let i = 0; i < this.n; i++) {
      const o = i * D, age = d[o], t = age / d[o + 1], seed = d[o + 2], k = d[o + 4], L = LOOK[d[o + 5]];
      const size = (L.size[0] + (L.size[1] - L.size[0]) * (1 - Math.exp(-age * 1.5))) * (0.8 + 0.4 * seed);
      ip[i * 3] = P[i * 3]; ip[i * 3 + 1] = Math.max(P[i * 3 + 1], d[o + 3] + size * 0.45); ip[i * 3 + 2] = P[i * 3 + 2];
      is[i * 3] = size; is[i * 3 + 1] = seed * 6.283 + age * (seed - 0.5) * 0.8; is[i * 3 + 2] = d[o + 3];
      for (let c = 0; c < 3; c++) ic[i * 4 + c] = L.dark ? L.col[c] + (L.dark[c] - L.col[c]) * k : L.col[c];
      ic[i * 4 + 3] = L.alpha * (L.dark ? 0.3 + 0.7 * k : 0.55 + 0.45 * k) * smoothstep(0, 0.12, age) * (1 - smoothstep(0.2, 1, t));
    }
    this.geo.instanceCount = this.n;
    this.iPos.needsUpdate = true; this.iCol.needsUpdate = true; this.iSRG.needsUpdate = true;
  }

  // the sky's light as one colour (the hemisphere light, the sun and the moon, as three.js lights a matt surface), the
  // city's glow at night, the tail lamps (brighter braking)
  private light(night: number, braking: boolean, model: THREE.Object3D, spec: Spec) {
    if (!this.lights) {
      const dirs: THREE.DirectionalLight[] = [];
      let hemi: THREE.HemisphereLight | null = null;
      this.scene.traverse((o) => {
        if (o instanceof THREE.HemisphereLight) hemi = o;
        else if (o instanceof THREE.DirectionalLight) dirs.push(o);
      });
      this.lights = { hemi, dirs };
    }
    const L = this.u.uLight.value.setRGB(0, 0, 0), h = this.lights.hemi;
    if (h) L.add(this.c.copy(h.color).lerp(h.groundColor, 0.35).multiplyScalar(h.intensity));
    for (const dl of this.lights.dirs) if (dl.visible) L.add(this.c.copy(dl.color).multiplyScalar(dl.intensity * 0.4));
    L.multiplyScalar(1 / Math.PI).add(this.c.setRGB(0.09, 0.08, 0.065).multiplyScalar(night));
    const tail = this.a.set(-spec.len / 2 - 0.3, 0.8, 0).applyMatrix4(model.matrix);
    this.u.uTail.value.set(tail.x, tail.y, tail.z, clamp(0.08 * night + (braking ? 0.04 + 0.22 * night : 0), 0, 0.4));
  }
}
