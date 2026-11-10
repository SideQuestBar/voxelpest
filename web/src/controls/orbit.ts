// The map: three.js's OrbitControls round a point on the city for the mouse (drag to turn, right-drag to move, wheel
// to zoom), keyboard flight (WASD / arrows to move, Q/E down and up, Shift faster: camera and pivot move together), a
// controller (left stick to move, right stick to turn, triggers to zoom, bumpers down and up), smooth flights to the
// places, and touch gestures of its own, as map apps have them: one finger drags the city (the spot under the finger
// stays under it, and a flick glides on), two fingers pinch to zoom and twist to turn round the point between them,
// two fingers moving up or down together tilt; double-tap zooms in, a two-finger tap out.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { V3 } from '../meta';
import { clamp, easeInOut, wrapPi } from '../util';
import { PAD, type Input } from './input';

const UP = new THREE.Vector3(0, 1, 0);
const TAP_PX = 10, TAP_MS = 300;

interface Finger { x: number; y: number; px: number; py: number; sx: number; sy: number; t: number }

export class MapControls {
  readonly ctl: OrbitControls;
  private flight: { p0: THREE.Vector3; p1: THREE.Vector3; q0: THREE.Vector3; q1: THREE.Vector3; t0: number; ms: number; arc: boolean } | null = null;
  private readonly vel = new THREE.Vector3();
  private readonly v = new THREE.Vector3();
  floor: (x: number, z: number) => number = () => 0;
  bounds: [number, number, number, number] | null = null;  // x0, z0, x1, z1: where the pivot may go
  // touch: px, py where a finger was when the camera last followed it; sx, sy where this gesture began
  private readonly fingers = new Map<number, Finger>();
  private two: 'tilt' | 'free' | null = null;
  private dragged = false;
  private readonly glide = new THREE.Vector3();
  private lastMove = 0;
  private lastTap = { t: 0, x: 0, y: 0 };
  private readonly ray = new THREE.Raycaster();
  private readonly ndc = new THREE.Vector2();

  constructor(private readonly camera: THREE.PerspectiveCamera, private readonly dom: HTMLElement, private readonly input: Input) {
    this.ctl = new OrbitControls(camera, dom);
    Object.assign(this.ctl, { enableDamping: true, dampingFactor: 0.12, rotateSpeed: 0.35, zoomSpeed: 1.6, minDistance: 8,
      maxDistance: 9000, maxPolarAngle: Math.PI * 0.49, screenSpacePanning: false, zoomToCursor: true });
    this.ctl.touches = { ONE: null, TWO: null };  // touch is handled below
    this.ctl.addEventListener('start', () => { this.flight = null; this.glide.set(0, 0, 0); });
    // on the window, so a drag that starts on a place name or the bar's pin moves the map too (a tap still clicks them)
    addEventListener('pointerdown', (e) => this.down(e));
    addEventListener('pointermove', (e) => {
      const f = this.fingers.get(e.pointerId);
      if (f) { f.x = e.clientX; f.y = e.clientY; }
    });
    addEventListener('pointerup', (e) => this.up(e));
    addEventListener('pointercancel', (e) => this.up(e, true));
  }

  set enabled(on: boolean) {
    this.ctl.enabled = on;
    if (!on) { this.fingers.clear(); this.glide.set(0, 0, 0); }
  }

  flyTo(pos: V3, target: V3, ms = 1800, arc = true) {
    this.flight = { p0: this.camera.position.clone(), p1: new THREE.Vector3(...pos), q0: this.ctl.target.clone(),
      q1: new THREE.Vector3(...target), t0: performance.now(), ms, arc };
    this.glide.set(0, 0, 0);
  }

  jump(pos: V3, target: V3) {
    this.flight = null;
    this.camera.position.set(...pos);
    this.ctl.target.set(...target);
    this.ctl.update();
  }

  private down(e: PointerEvent) {
    const t = e.target as Element | null;
    if (e.pointerType !== 'touch' || !this.ctl.enabled || !(t === this.dom || t?.closest?.('.label, #sq-pin'))) return;
    this.flight = null;
    this.glide.set(0, 0, 0);
    this.fingers.set(e.pointerId, { x: e.clientX, y: e.clientY, px: e.clientX, py: e.clientY, sx: e.clientX, sy: e.clientY, t: performance.now() });
    this.restart();
  }

  private up(e: PointerEvent, cancel = false) {
    const f = this.fingers.get(e.pointerId);
    if (!f) return;
    const now = performance.now(), n = this.fingers.size, still = (g: Finger) => Math.hypot(g.x - g.sx, g.y - g.sy) < TAP_PX;
    if (!cancel && n === 1 && !this.dragged && still(f) && now - f.t < TAP_MS) this.tap(f.x, f.y, now);
    else if (!cancel && n === 2 && !this.two && [...this.fingers.values()].every((g) => still(g) && now - g.t < TAP_MS)) {
      const [a, b] = [...this.fingers.values()];
      this.zoomAt((a.x + b.x) / 2, (a.y + b.y) / 2, 2);
    }
    this.fingers.delete(e.pointerId);
    if (!this.fingers.size && n === 1 && this.dragged && now - this.lastMove > 80) this.glide.set(0, 0, 0);
    if (n > 1) for (const g of this.fingers.values()) g.t = -Infinity;  // what is left of a two-finger gesture is no tap
    this.restart();
  }

  // a finger came or went: the gesture starts afresh from where the fingers are
  private restart() {
    for (const f of this.fingers.values()) { f.px = f.sx = f.x; f.py = f.sy = f.y; }
    this.two = null;
    this.dragged = false;
  }

  private tap(x: number, y: number, now: number) {
    const l = this.lastTap;
    if (now - l.t < TAP_MS + 50 && Math.hypot(x - l.x, y - l.y) < 30) {
      this.zoomAt(x, y, 0.45);
      l.t = 0;
    } else Object.assign(l, { t: now, x, y });
  }

  private zoomAt(x: number, y: number, k: number) {
    const cam = this.camera.position, tgt = this.ctl.target, p = this.ground(x, y), r = cam.distanceTo(tgt);
    k = clamp(k, this.ctl.minDistance / r, this.ctl.maxDistance / r);
    const to = (v: THREE.Vector3) => v.clone().sub(p).multiplyScalar(k).add(p).toArray() as V3;
    this.flyTo(to(cam), to(tgt), 380, false);
  }

  // the point on the ground plane (the pivot's height) under a point on the screen; towards the horizon, a point at a
  // bounded distance instead, so a drag up there doesn't fling the city away
  private ground(x: number, y: number) {
    const r = this.dom.getBoundingClientRect();
    this.ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
    this.ray.setFromCamera(this.ndc, this.camera);
    const { origin: o, direction: d } = this.ray.ray, h = this.ctl.target.y;
    const far = Math.max(3 * this.camera.position.distanceTo(this.ctl.target), 600);
    let t = d.y < -1e-4 ? (h - o.y) / d.y : far;
    if (!(t > 0) || t > far) t = far;
    return o.clone().addScaledVector(d, t).setY(h);
  }

  private shift(d: THREE.Vector3) {
    this.camera.position.add(d);
    this.ctl.target.add(d);
  }

  private touch(dt: number) {
    const f = [...this.fingers.values()], cam = this.camera, tgt = this.ctl.target;
    if (!f.length) {
      if (this.glide.lengthSq() > 0.01) {
        this.shift(this.v.copy(this.glide).multiplyScalar(dt));
        this.glide.multiplyScalar(Math.exp(-dt * 4));
      }
      return;
    }
    cam.updateMatrixWorld();
    const now = performance.now();
    if (f.length === 1) {
      const a = f[0];
      if (a.x === a.px && a.y === a.py) return;
      if (!this.dragged && Math.hypot(a.x - a.sx, a.y - a.sy) < TAP_PX / 2) return;
      this.dragged = true;
      const d = this.ground(a.px, a.py).sub(this.ground(a.x, a.y));
      this.shift(d);
      // the flick's speed, for the glide after the finger lifts
      const v = d.divideScalar(Math.max((now - this.lastMove) / 1000, 1 / 120)), cap = 3 * Math.max(cam.position.y - tgt.y, 40);
      this.glide.lerp(v.clampLength(0, cap), now - this.lastMove > 100 ? 1 : 0.5);
      this.lastMove = now;
      a.px = a.x; a.py = a.y;
      return;
    }
    const [a, b] = f;
    if (!this.two) {
      // which two-finger gesture: both moving up or down together (barely spreading or turning) tilts; anything else
      // pans, zooms and turns at once
      const ax = a.x - a.sx, ay = a.y - a.sy, bx = b.x - b.sx, by = b.y - b.sy, moved = Math.max(Math.hypot(ax, ay), Math.hypot(bx, by));
      if (moved < 8) return;
      const spread = Math.abs(Math.hypot(a.x - b.x, a.y - b.y) - Math.hypot(a.sx - b.sx, a.sy - b.sy));
      const vertical = ay * by > 0 && Math.abs(ay) > 1.5 * Math.abs(ax) && Math.abs(by) > 1.5 * Math.abs(bx);
      this.two = vertical && spread < 0.4 * moved ? 'tilt' : 'free';
    }
    if (this.two === 'tilt') {
      const dy = (a.y - a.py + b.y - b.py) / 2, s = new THREE.Spherical().setFromVector3(this.v.subVectors(cam.position, tgt));
      s.phi = clamp(s.phi - (dy / Math.max(this.dom.clientHeight, 1)) * 2.4, Math.max(this.ctl.minPolarAngle, 0.05), this.ctl.maxPolarAngle);
      cam.position.copy(tgt).add(this.v.setFromSpherical(s));
    } else {
      const d0 = Math.hypot(a.px - b.px, a.py - b.py), d1 = Math.hypot(a.x - b.x, a.y - b.y);
      const turn = wrapPi(Math.atan2(b.y - a.y, b.x - a.x) - Math.atan2(b.py - a.py, b.px - a.px));
      const p = this.ground((a.px + b.px) / 2, (a.py + b.py) / 2), r = cam.position.distanceTo(tgt);
      const k = clamp(d0 / Math.max(d1, 1), this.ctl.minDistance / r, this.ctl.maxDistance / r);
      // zoom and turn round the point between the fingers, then carry that point to where the fingers are now
      for (const q of [cam.position, tgt]) q.sub(p).multiplyScalar(k).applyAxisAngle(UP, turn).add(p);
      cam.lookAt(tgt);
      cam.updateMatrixWorld();
      this.shift(p.sub(this.ground((a.x + b.x) / 2, (a.y + b.y) / 2)));
    }
    cam.lookAt(tgt);
    for (const g of f) { g.px = g.x; g.py = g.y; }
  }

  update(dt: number) {
    if (this.flight) {
      const f = this.flight, t = Math.min(1, (performance.now() - f.t0) / f.ms), e = easeInOut(t);
      this.camera.position.lerpVectors(f.p0, f.p1, e);
      this.ctl.target.lerpVectors(f.q0, f.q1, e);
      // arc up over long flights, so the way there shows the city
      const span = f.p0.distanceTo(f.p1);
      if (f.arc) this.camera.position.y += Math.sin(Math.PI * e) * Math.min(span * 0.25, 600);
      if (t >= 1) this.flight = null;
    }
    this.touch(dt);
    const i = this.input, pad = i.pad;
    const { fwd, side } = i.move();
    const up = i.axis(['KeyQ'], ['KeyE']) + (pad.held[PAD.RB] ? 1 : 0) - (pad.held[PAD.LB] ? 1 : 0);
    const cam = this.camera, tgt = this.ctl.target;
    if (fwd || side || up) this.flight = null;
    if (pad.rx || pad.ry || pad.lt || pad.rt) {
      this.flight = null;
      const s = new THREE.Spherical().setFromVector3(this.v.subVectors(cam.position, tgt));
      s.theta -= pad.rx * Math.abs(pad.rx) * 2.2 * dt;
      s.phi = clamp(s.phi - pad.ry * Math.abs(pad.ry) * 1.5 * dt, 0.08, this.ctl.maxPolarAngle);
      s.radius = clamp(s.radius * Math.exp((pad.lt - pad.rt) * 1.8 * dt), this.ctl.minDistance, this.ctl.maxDistance);
      cam.position.copy(tgt).add(this.v.setFromSpherical(s));
    }
    const height = Math.max(cam.position.y - this.floor(cam.position.x, cam.position.z), 2);
    const speed = (8 + 1.2 * height) * (i.has('ShiftLeft', 'ShiftRight') || pad.held[PAD.LS] ? 3 : 1);
    const dir = new THREE.Vector3().subVectors(tgt, cam.position).setY(0).normalize();
    const right = new THREE.Vector3(-dir.z, 0, dir.x);
    const want = dir.multiplyScalar(fwd).add(right.multiplyScalar(side)).setY(up).multiplyScalar(speed);
    this.vel.lerp(want, 1 - Math.exp(-dt * 6));
    if (this.vel.lengthSq() > 1e-4) {
      const d = this.vel.clone().multiplyScalar(Math.min(dt, 0.1));
      cam.position.add(d);
      tgt.add(d);
    }
    if (this.bounds) {
      const [x0, z0, x1, z1] = this.bounds, dx = clamp(tgt.x, x0, x1) - tgt.x, dz = clamp(tgt.z, z0, z1) - tgt.z;
      if (dx || dz) {
        this.shift(this.v.set(dx, 0, dz));
        this.glide.set(0, 0, 0);
      }
    }
    this.ctl.update();
  }
}
