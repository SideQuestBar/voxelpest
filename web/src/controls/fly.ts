// Fly mode: the FPV drone, the small plane and the helicopter over the voxels, each flown on its own physics.
// - The plane: a 1,050 kg four-seater with a 16.2 m² wing and 180 hp. Lift and drag from the angle of attack, thrust
//   from a propeller that loses bite with speed, and a tail that keeps the nose in the airflow. The stick moves the
//   angle of attack the tail holds; let go, it holds the nose where it was left, as a trimmed aeroplane does: so the
//   attitude sets the speed and the throttle climbs and sinks it; banked, the lift turns it. It stalls past 15°, lands
//   and takes off from any flat ground. Seen from behind.
// - The helicopter: the rotor's thrust along its mast, so leaning it trades height for speed; translational lift above
//   about 15 kt; the collective stays where it is put; the tail weathervanes it into the airflow. Seen from behind.
// - The drone: thrust along its body and nothing holding its height: tilted, it sinks unless given throttle. The stick
//   tilts it (angle mode, up to 57°), the throttle is sprung to hover; seen from its camera, tilted up 20°.
// It lands on anything flat and dry if it touches down gently (the plane slowly, wings level, not nose first); a hard
// landing, the river or anything solid in its way is a crash: a moment's pause, then it is back in the air over where
// it last flew clear, the plane and the helicopter well above it.
// A drag (the mouse, or a finger on free screen) swings the camera round the aircraft, the wheel brings it closer or
// further; 1.5 s after the last drag it eases back behind. Dragged, the drone is seen from outside too.
// Keys: W/S and A/D pitch and roll (W pushes the nose down), Q/E yaw, Space/Shift or R/F throttle or collective up and
// down, V the next aircraft, T back in the air. A controller: the left stick pitch and roll, the right stick yaw,
// RT/LT up and down, LB/RB the aircraft, Y back in the air. Touch: the stick, the pedals up and down.
import * as THREE from 'three';
import type { World } from '../engine/world';
import { clamp, isTouch, smoothstep, wrapPi } from '../util';
import { AIR, buildCraft, type AircraftKind, type AirSpec, type Craft } from './aircraft';
import { MAT } from '../meta';
import { mats } from './kit';
import { PAD, type Input } from './input';
import { Streaks } from './streaks';

const G = 9.81;
const X = new THREE.Vector3(1, 0, 0), Y = new THREE.Vector3(0, 1, 0), Z = new THREE.Vector3(0, 0, 1);
const IDLE = 1.5;                                     // seconds after the last drag before the camera swings back
const DRONE_CAM: [number, number, number] = [3.4, 1.1, 3];   // the drone seen from outside: back, up, look ahead
const ABOVE = { drone: 0, plane: 150, heli: 90 };     // m higher than the last clear spot after a crash

// the plane's wing: dynamic pressure × area per kg, per (m/s)²; lift from the angle of attack (rad), stalling at 15°
const QS = (0.5 * 1.225 * 16.2) / 1050;
const A0 = -0.06, CLA = 5.0, ASTALL = 0.26;
const lift = (a: number) => a > ASTALL ? Math.max(1.6 - 4 * (a - ASTALL), 0.9 * Math.sin(2 * a))
  : a < -0.26 ? Math.min(-1.0 + 4 * (-0.26 - a), 0.9 * Math.sin(2 * a)) : CLA * (a - A0);
const drag = (cl: number, a: number) => 0.032 + 0.045 * cl * cl + 1.2 * Math.max(0, Math.abs(a) - ASTALL) * Math.abs(Math.sin(a));
const thrust = (p: number, v: number) => 3.0 * p * Math.max(0.15, 1 - (0.55 * v) / 70);
// level flight at v: the angle of attack and the throttle it takes
function trim(v: number) {
  const cl = G / (QS * v * v), a = cl / CLA + A0;
  return { a, p: clamp((QS * v * v * drag(cl, a)) / thrust(1, v), 0, 1) };
}

export interface Telemetry {
  kind: AircraftKind;
  speed: number;        // m/s through the air
  vs: number;           // m/s up
  alt: number;          // m above the model's base (≈ the Danube's level, 98 m above sea level: add for altitude)
  agl: number;          // m over what is under it
  heading: number;      // radians, map north = 0, clockwise
  pitch: number; roll: number;  // radians, nose up and right wing down positive
  turn: number;         // rad/s, right positive
  slip: number;         // the ball: sideways force over the weight, right positive
  aoa: number;          // the plane's angle of attack, radians
  power: number;        // throttle or collective, 0..1
  rpm: number;          // the plane's engine, the helicopter's rotor in %
  torque: number;       // the helicopter's, %
  time: number;         // seconds since take-off
  home: number;         // m to where it started
  homeDir: number;      // radians, relative to the heading
  link: number;         // the drone's video link, 0..1
  crashed: boolean;
  ground: boolean;
  stall: boolean;
}

type Sticks = { pitch: number; roll: number; yaw: number; up: number };

export class Flyer {
  readonly pos = new THREE.Vector3();
  readonly vel = new THREE.Vector3();
  readonly q = new THREE.Quaternion();
  kind: AircraftKind = 'plane';
  spec: AirSpec = AIR.plane;
  power = 0.6;
  private readonly crafts = new Map<AircraftKind, Craft>();
  private craft: Craft | null = null;
  private yaw = 0;                // the drone's and the helicopter's heading
  private tilt = { p: 0, r: 0 };  // their pitch and roll
  private thr = 0;                // the drone's sprung throttle, -1..1
  private aBase = 0;              // the plane's elevator: the angle of attack it was at when the stick moved
  private hold: number | null = 0; // the pitch it holds let go (radians), null with the stick held
  private readonly dir = new THREE.Vector3(1, 0, 0);  // the way it moved last step
  private readonly st: Sticks = { pitch: 0, roll: 0, yaw: 0, up: 0 };
  private readonly acc = new THREE.Vector3();
  private onGround = false;
  private crash = 0;              // seconds left of the crash pause
  private spin = 0;
  private t = 0;
  private flown = 0;
  private turnRate = 0;
  private lastHead = 0;
  private ball = 0;
  private home = new THREE.Vector3();
  private safe: { p: THREE.Vector3; yaw: number; t: number } = { p: new THREE.Vector3(), yaw: 0, t: 0 };
  private readonly camPos = new THREE.Vector3();
  private readonly camLook = new THREE.Vector3();
  private readonly camUp = new THREE.Vector3(0, 1, 0);
  private camSet = false;
  private active = false;
  private readonly camOff = new THREE.Vector3();
  // the camera swung round: yaw (radians round the aircraft), pitch (added elevation), zoom (× the distance)
  private orbit = { yaw: 0, pitch: 0, zoom: 1, idle: IDLE, outside: false };
  private drag: { id: number; x: number; y: number } | null = null;
  private fovKick = 0;
  // the drone's link: how much of the way home is blocked, glitches now and then
  private occl = 0;
  private linkT = 0;
  private glitch = { left: 0, k: 0 };
  link = 1;
  breakup = 0;
  private readonly streaks: Streaks;
  // the map's edges (m), and the compass: map north as a heading in the grid
  bounds: [number, number, number, number] = [-400, -400, 6300, 7000];
  north = 0;
  onKind: ((k: AircraftKind) => void) | null = null;

  constructor(private readonly scene: THREE.Scene, private readonly camera: THREE.PerspectiveCamera, private readonly world: World,
    private readonly input: Input, private readonly dom: HTMLElement) {
    addEventListener('pointerdown', (e) => {
      if (!this.active || this.drag) return;
      const t = e.target as Element | null;
      if (e.pointerType === 'mouse' ? t !== dom || e.button !== 0 : !(t === dom || t?.closest?.('.label, #sq-pin'))) return;
      this.drag = { id: e.pointerId, x: e.clientX, y: e.clientY };
      if (e.pointerType === 'mouse') { dom.setPointerCapture?.(e.pointerId); dom.style.cursor = 'grabbing'; }
    });
    addEventListener('pointermove', (e) => {
      const d = this.drag;
      if (!d || e.pointerId !== d.id) return;
      const k = e.pointerType === 'mouse' ? 0.0055 : 0.0085;
      this.swing((e.clientX - d.x) * k, (e.clientY - d.y) * k * 0.7, 1);
      d.x = e.clientX; d.y = e.clientY;
    });
    const up = (e: PointerEvent) => {
      if (this.drag?.id !== e.pointerId) return;
      this.drag = null;
      if (this.active) dom.style.cursor = 'grab';
    };
    addEventListener('pointerup', up);
    addEventListener('pointercancel', up);
    dom.addEventListener('wheel', (e) => { if (this.active) this.swing(0, 0, Math.exp(e.deltaY * 0.0012)); }, { passive: true });
    this.streaks = new Streaks(scene, isTouch() ? 140 : 280, dom, [140, 80, 140]);
    this.streaks.range = [22, 70];
    this.streaks.strength = 0.34;
    this.streaks.lift = 0;
    this.streaks.trail = 0.06;
  }

  private use(k: AircraftKind) {
    let c = this.crafts.get(k);
    if (!c) {
      c = buildCraft(k);
      this.crafts.set(k, c);
      this.scene.add(c.g);
    }
    return c;
  }

  setKind(k: AircraftKind) {
    if (this.craft && k === this.kind) return;
    const on = this.active;
    if (this.craft) this.craft.g.visible = false;
    this.kind = k;
    this.spec = AIR[k];
    this.craft = this.use(k);
    if (on) this.place(this.pos.x, this.pos.y, this.pos.z, this.heading(), true);
    this.onKind?.(k);
  }

  heading() {
    const f = X.clone().applyQuaternion(this.q);
    return Math.atan2(f.z, f.x);
  }

  // into the air over (x, z): ground is the height under it; airborne at once, flying the way the view looks
  place(x: number, ground: number, z: number, heading: number, keepHeight = false) {
    if (!this.craft) this.setKind(this.kind);
    const y = keepHeight ? ground : this.clear(x, ground + this.spec.start, z);
    this.pos.set(x, y, z);
    this.yaw = heading;
    this.tilt = { p: 0, r: 0 };
    this.thr = 0;
    if (this.kind === 'plane') {
      const v = 52, tr = trim(v);
      this.aBase = tr.a;
      this.hold = 0;
      this.power = tr.p;
      this.q.setFromEuler(new THREE.Euler(0, -heading, tr.a, 'YZX'));
      this.vel.set(Math.cos(heading) * v, 0, Math.sin(heading) * v);
    } else {
      this.q.setFromAxisAngle(Y, -heading);
      this.vel.set(0, 0, 0);
      this.power = 0.5;
    }
    this.dir.copy(this.vel).normalize();
    if (this.dir.lengthSq() < 0.5) this.dir.set(Math.cos(heading), 0, Math.sin(heading));
    this.onGround = false;
    this.crash = 0;
    this.lastHead = heading;
    this.turnRate = 0;
    if (!keepHeight) { this.home.copy(this.pos); this.flown = 0; }
    this.safe = { p: this.pos.clone(), yaw: heading, t: 0 };
    this.camSet = false;
    if (!keepHeight) this.orbit = { yaw: 0, pitch: 0, zoom: this.orbit.zoom, idle: IDLE, outside: false };
    this.pose();
    this.follow(0);
  }

  // the first height from y up with nothing solid round it
  private clear(x: number, y: number, z: number) {
    const [l, h, w] = this.spec.size;
    for (let k = 0; k < 60; k++, y += 3) {
      if (!this.hit(x, y, z, Math.max(l, w) + 1, h + 1)) return y;
    }
    return y;
  }

  private hit(x: number, y: number, z: number, r: number, h: number) {
    for (const [dx, dz] of [[0, 0], [r, 0], [-r, 0], [0, r], [0, -r]]) if (this.world.blocked(x + dx, z + dz, y - h, y + h)) return true;
    return false;
  }

  show(on: boolean, night: number) {
    if (!this.craft) this.setKind(this.kind);
    if (on !== this.active) { this.drag = null; this.dom.style.cursor = on ? 'grab' : ''; }
    this.active = on;
    this.craft!.g.visible = on && !this.fpv;
    for (const m of this.craft!.glow) m.emissiveIntensity = 0.4 + 2.2 * night;
    const M = mats();
    M.lamp.emissiveIntensity = 0.3 + 2.5 * night;
    if (!on) this.streaks.mesh.visible = false;
    else if (this.kind !== 'drone') this.streaks.update(this.camera, this.camera.position, this.vel, 0, night);
    else this.streaks.mesh.visible = false;
  }

  // the stick, keys and pedals, each -1..1; keys ease in and out as a thumb on a stick would
  private sticks(dt: number): Sticks {
    const i = this.input, pad = i.pad;
    let pitch = i.axis(['KeyW', 'ArrowUp'], ['KeyS', 'ArrowDown']);   // + pulls back: nose up, or backwards
    let roll = i.axis(['KeyA', 'ArrowLeft'], ['KeyD', 'ArrowRight']);
    let yaw = i.axis(['KeyQ'], ['KeyE']);
    let up = i.axis(['ShiftLeft', 'ShiftRight', 'KeyF'], ['Space', 'KeyR']);
    let analog = false;
    if (i.stick.active) { pitch = -i.stick.y; roll = i.stick.x; yaw = this.kind === 'plane' ? 0 : i.stick.x * 0.6; analog = true; }
    if (pad.lx || pad.ly) { pitch = pad.ly; roll = pad.lx; analog = true; }
    if (pad.rx) yaw = pad.rx;
    if (pad.rt || pad.lt) up = pad.rt - pad.lt;
    if (i.pedal.gas) up = 1;
    if (i.pedal.brake) up = -1;
    const k = 1 - Math.exp(-dt * (analog ? 25 : 4.5));
    const s = this.st;
    s.pitch += (pitch - s.pitch) * k; s.roll += (roll - s.roll) * k;
    s.yaw += (yaw - s.yaw) * (1 - Math.exp(-dt * 9)); s.up = up;
    return s;
  }

  update(dt: number) {
    if (!this.craft) return;
    const i = this.input;
    this.t += dt;
    if (i.has('KeyT') || i.pressed(PAD.Y)) { i.down.delete('KeyT'); this.respawn(true); }
    if (this.crash > 0) {
      this.crash -= dt;
      this.breakup = 0.25;
      if (this.crash <= 0) this.respawn(true);
      this.follow(dt);
      return;
    }
    const s = this.sticks(dt);
    const was = this.vel.clone();
    if (this.kind === 'plane') this.planeStep(dt, s);
    else this.rotorStep(dt, s);
    if (dt > 0) this.acc.copy(this.vel).sub(was).divideScalar(dt);
    // the map's edges: turned back
    const [x0, z0, x1, z1] = this.bounds;
    if (this.pos.x < x0 || this.pos.x > x1 || this.pos.z < z0 || this.pos.z > z1) {
      this.pos.x = clamp(this.pos.x, x0, x1); this.pos.z = clamp(this.pos.z, z0, z1);
      this.vel.multiplyScalar(0.3);
    }
    if (this.pos.y > 1500) { this.pos.y = 1500; this.vel.y = Math.min(this.vel.y, 0); }
    // anything solid round it is a crash (on the ground, only what stands higher than its wheels or skids)
    const [l, h, w] = this.spec.size;
    const f = X.clone().applyQuaternion(this.q), r = Z.clone().applyQuaternion(this.q);
    const pts = this.kind === 'drone' ? [[0, 0]] : [[l * 0.9, 0], [-l * 0.9, 0], [0, w * 0.95], [0, -w * 0.95]];
    let crashed = false;
    for (const [a, b] of pts) {
      const px = this.pos.x + f.x * a + r.x * b, pz = this.pos.z + f.z * a + r.z * b, py = this.pos.y + f.y * a + r.y * b;
      // what it would land on (the top under the point, within its height) is not in the way: the touchdown decides
      let lo = this.onGround ? py + 0.6 : py - h * 0.6;
      const fl = this.onGround ? null : this.world.floor(px, pz, py + 0.5, 0);
      if (fl && fl.top > lo) lo = fl.top + 0.3;
      const hi = py + h * 0.6;
      if (hi > lo && this.world.blocked(px, pz, lo, hi)) { crashed = true; break; }
    }
    if (crashed) {
      this.crash = 1.6;
      this.vel.set(0, 0, 0);
    } else if (!this.onGround && this.t - this.safe.t > 1.0 && this.pos.y > this.groundUnder() + 6) {
      this.safe = { p: this.pos.clone(), yaw: this.heading(), t: this.t };
    }
    // the turn needle and the ball
    const hd = this.heading();
    if (dt > 0) this.turnRate += (wrapPi(hd - this.lastHead) / dt - this.turnRate) * (1 - Math.exp(-dt * 3));
    this.lastHead = hd;
    const sf = this.acc.clone().add(new THREE.Vector3(0, G, 0)), u = Y.clone().applyQuaternion(this.q);
    const b = clamp(sf.dot(r) / Math.max(sf.dot(u), 2), -1, 1);
    this.ball += (b - this.ball) * (1 - Math.exp(-dt * 4));
    if (this.kind === 'drone') this.linkStep(dt);
    this.flown += dt;
    this.pose();
    this.follow(dt);
  }

  private groundUnder(x = this.pos.x, z = this.pos.z, y = this.pos.y) {
    const fl = this.world.floor(x, z, y + 0.5, 0);
    return fl ? fl.top : this.world.groundAt(x, z) ?? 0;
  }

  private respawn(higher = false) {
    const p = this.safe.p, y = higher ? this.clear(p.x, Math.min(p.y + ABOVE[this.kind], 1400), p.z) : p.y;
    this.place(p.x, y, p.z, this.safe.yaw, true);
  }

  // what is under it: its top, and whether that is the river
  private surface(x = this.pos.x, z = this.pos.z, y = this.pos.y) {
    const fl = this.world.floor(x, z, y + 0.5, 0);
    return fl ? { top: fl.top, water: fl.mat === MAT.WATER } : { top: this.world.groundAt(x, z) ?? 0, water: false };
  }

  // the drone flown from its camera (not swung round to be seen from outside)
  get fpv() { return this.kind === 'drone' && !this.orbit.outside; }

  private swing(dy: number, dp: number, zoom: number) {
    const o = this.orbit;
    o.yaw = wrapPi(o.yaw + dy);
    o.pitch = clamp(o.pitch + dp, -0.9, 1.2);
    o.zoom = clamp(o.zoom * zoom, 0.45, 3);
    o.idle = 0;
    if (this.kind === 'drone') o.outside = true;
  }

  // gusts: stronger low over the roofs, a slow drift of three sines in each direction
  private gust(out: THREE.Vector3, amp: number) {
    const t = this.t;
    out.set(Math.sin(t * 0.9) + 0.6 * Math.sin(t * 2.3 + 1) + 0.3 * Math.sin(t * 5.1 + 2),
      0.7 * (Math.sin(t * 1.3 + 3) + 0.5 * Math.sin(t * 3.7)) , Math.sin(t * 1.1 + 4) + 0.6 * Math.sin(t * 2.9 + 5) + 0.3 * Math.sin(t * 6.3));
    const agl = this.pos.y - Math.max(this.groundUnder(), 0);
    return out.multiplyScalar(amp * (0.35 + 0.65 * smoothstep(250, 20, agl)));
  }

  // ---------------------------------------------------------------- the plane
  private planeStep(dt: number, s: Sticks) {
    this.power = clamp(this.power + s.up * dt * 0.4, 0, 1);
    const f = X.clone().applyQuaternion(this.q), u = Y.clone().applyQuaternion(this.q), r = Z.clone().applyQuaternion(this.q);
    const V = this.vel.length();
    const vd = V > 0.5 ? this.vel.clone().divideScalar(V) : f.clone();
    const a = V > 1 ? Math.atan2(-this.vel.dot(u), this.vel.dot(f)) : 0;     // angle of attack
    const b = V > 1 ? Math.atan2(this.vel.dot(r), this.vel.dot(f)) : 0;      // sideslip, wind from the right +
    const bank = Math.atan2(-r.y, u.y);
    const pitch = Math.asin(clamp(f.y, -1, 1));
    const ctl = smoothstep(3, 30, V);                     // the controls bite with airspeed
    const stalled = smoothstep(ASTALL - 0.02, ASTALL + 0.06, a);
    // the elevator. Held, the stick moves it from where it was (the angle of attack the tail holds, more of it the
    // harder the pull); let go, it is trimmed to hold the nose where it was left, as a trimmed aeroplane does for a
    // while: so the attitude sets the speed and the throttle the climb or the sink. Not upside down or near vertical,
    // nor on the ground: there it is the stick alone
    let aCmd: number;
    const held = Math.abs(s.pitch) > 0.04, upright = Math.abs(pitch) < 1.2 && Math.abs(bank) < 1.6;
    if (this.onGround) { this.hold = null; this.aBase = 0.02; aCmd = 0.02 + s.pitch * 0.22; }
    else if (held || !upright) {
      if (this.hold !== null) { this.aBase = clamp(a + 1.2 * (this.hold - pitch), -0.1, ASTALL); this.hold = null; }
      aCmd = this.aBase + s.pitch * (s.pitch > 0 ? 0.2 : 0.15);
    } else {
      if (this.hold === null) this.hold = pitch;
      aCmd = clamp(a + 1.2 * (this.hold - pitch), -0.1, ASTALL + 0.01);
    }
    // body rates: roll (right wing down +), pitch (nose up +), yaw (nose right +); a trainer levels its wings let go
    let rr = ctl * (s.roll * 0.85 - (Math.abs(s.roll) < 0.05 && Math.abs(bank) < 2.6 ? bank * 0.3 : 0))
      + stalled * Math.sin(this.t * 1.7) * 0.9;
    let pr = ctl * 3.2 * (aCmd - a) - stalled * 0.9;
    const yr = ctl * (2.4 * b + s.yaw * 0.45);
    if (this.onGround) rr = -bank * 4;
    this.q.multiply(new THREE.Quaternion().setFromAxisAngle(X, rr * dt));
    this.q.multiply(new THREE.Quaternion().setFromAxisAngle(Z, pr * dt));
    this.q.multiply(new THREE.Quaternion().setFromAxisAngle(Y, -yr * dt));
    // the tail keeps the nose where the air comes from: as the flight path turns, the aeroplane turns with it
    if (!this.onGround && V > 2) {
      const turn = new THREE.Quaternion().setFromUnitVectors(this.dir, vd);
      this.q.premultiply(new THREE.Quaternion().slerp(turn, ctl));
    }
    this.q.normalize();
    this.dir.copy(vd);
    // the forces, per kg: thrust, lift square to the airflow, drag along it, the fuselage against sideslip, gravity
    const qs = QS * V * V, cl = lift(a), cd = drag(cl, a);
    const up = u.clone().addScaledVector(vd, -u.dot(vd));
    if (up.lengthSq() < 1e-6) up.copy(u); else up.normalize();
    const acc = f.clone().multiplyScalar(thrust(this.power, V))
      .addScaledVector(up, qs * cl).addScaledVector(vd, -qs * cd).addScaledVector(r, -qs * 0.9 * b);
    acc.y -= G;
    if (!this.onGround) acc.add(this.gust(new THREE.Vector3(), 0.55));
    this.vel.addScaledVector(acc, dt);
    // on the ground: rolling resistance, the brakes with the throttle shut, the nose wheel steering, no sliding sideways
    if (this.onGround) {
      const ff = new THREE.Vector3(f.x, 0, f.z).normalize();
      const steer = (s.roll * 0.6 + s.yaw * 0.6) * smoothstep(0.3, 5, V) * (1 - 0.75 * smoothstep(15, 30, V));
      this.q.premultiply(new THREE.Quaternion().setFromAxisAngle(Y, -steer * dt));
      ff.applyAxisAngle(Y, -steer * dt);
      const along = this.vel.x * ff.x + this.vel.z * ff.z;
      const slow = (0.25 + (s.up < 0 && this.power < 0.02 ? 4 : 0)) * dt;
      const v2 = Math.sign(along) * Math.max(0, Math.abs(along) - slow);
      this.vel.set(ff.x * v2, Math.max(this.vel.y, 0), ff.z * v2);
    }
    this.pos.addScaledVector(this.vel, dt);
    // the ground: a landing if gentle, a crash if not
    const sf = this.surface(), gy = sf.top + 0.02;
    if (this.pos.y <= gy) {
      if (!this.onGround && (sf.water || this.vel.y < -4 || Math.abs(bank) > 0.3 || pitch < -0.1 || V > 48)) { this.crash = 1.6; return; }
      this.pos.y = gy;
      this.vel.y = Math.max(this.vel.y, 0);
      this.onGround = true;
    } else if (this.onGround && this.pos.y > gy + 0.08) this.onGround = false;
    if (this.onGround) {
      const p2 = clamp(Math.asin(clamp(X.clone().applyQuaternion(this.q).y, -1, 1)), 0, 0.22);
      this.q.setFromEuler(new THREE.Euler(0, -this.heading(), p2, 'YZX'));
      this.dir.copy(X).applyQuaternion(this.q);
    }
    this.spin += (15 + 50 * this.power) * dt;
  }

  // ---------------------------------------------------------------- the drone and the helicopter
  private rotorStep(dt: number, s: Sticks) {
    const drone = this.kind === 'drone';
    const maxP = drone ? 1.0 : 0.48, maxR = drone ? 1.0 : 0.55, resp = drone ? 10 : 2.8;
    // the attitude follows the stick: forward stick (pitch < 0) noses down
    this.tilt.p += (s.pitch * maxP - this.tilt.p) * (1 - Math.exp(-dt * resp));
    this.tilt.r += (s.roll * maxR - this.tilt.r) * (1 - Math.exp(-dt * resp));
    const vh = Math.hypot(this.vel.x, this.vel.z);
    let yawRate = s.yaw * (drone ? 3.4 : 1.0);
    if (!drone && vh > 3) {  // the fin turns the nose into the airflow
      const beta = wrapPi(Math.atan2(this.vel.z, this.vel.x) - this.yaw);
      yawRate += 1.6 * beta * smoothstep(8, 28, vh) * (Math.abs(beta) < 2.4 ? 1 : 0.3);
    }
    this.yaw = wrapPi(this.yaw + yawRate * dt);
    this.q.setFromEuler(new THREE.Euler(this.tilt.r, -this.yaw, this.tilt.p, 'YZX'));
    const up = Y.clone().applyQuaternion(this.q);
    let T: number;
    if (drone) {
      this.thr += (s.up - this.thr) * (1 - Math.exp(-dt * 12));
      T = G * (this.thr >= 0 ? 1 + 2.4 * this.thr : 1 + 0.92 * this.thr);
      this.power = T / (3.4 * G);
    } else {
      this.power = clamp(this.power + s.up * dt * 0.45, 0, 1);
      T = G * (0.55 + 0.9 * this.power) * (1 + 0.12 * smoothstep(6, 20, vh));
    }
    // thrust along the mast or the body; drag; the rotor's or the props' inflow damping a climb or a sink
    const V = this.vel.length();
    const k = drone ? 0.012 : 2.7e-4 * (1 + 3 * smoothstep(65, 85, V));
    const acc = up.multiplyScalar(this.onGround && T < G ? 0 : T).addScaledVector(this.vel, -k * V);
    acc.x -= this.vel.x * (drone ? 0.04 : 0.01);
    acc.z -= this.vel.z * (drone ? 0.04 : 0.01);
    acc.y -= this.vel.y * (drone ? 0.7 : 0.55) + G;
    if (!this.onGround) acc.add(this.gust(new THREE.Vector3(), drone ? 0.5 : 0.7));
    this.vel.addScaledVector(acc, dt);
    this.pos.addScaledVector(this.vel, dt);
    const sf = this.surface(), gy = sf.top + (drone ? 0.05 : 0.02);
    if (this.pos.y <= gy) {
      if (!this.onGround && (sf.water || this.vel.y < (drone ? -7 : -3.5) || vh > (drone ? 14 : 10)
        || Math.abs(this.tilt.r) > 0.35 || Math.abs(this.tilt.p) > 0.35)) { this.crash = 1.6; return; }
      this.pos.y = gy;
      this.vel.y = Math.max(this.vel.y, 0);
      this.vel.x *= Math.exp(-dt * 4); this.vel.z *= Math.exp(-dt * 4);
      this.tilt.p *= Math.exp(-dt * 6); this.tilt.r *= Math.exp(-dt * 6);
      this.onGround = true;
    } else this.onGround = false;
    this.q.setFromEuler(new THREE.Euler(this.tilt.r, -this.yaw, this.tilt.p, 'YZX'));
    this.spin += (drone ? 0 : 7 + 6 * this.power) * dt * Math.PI * 2;
  }

  // the drone's video link: weaker with distance and with buildings between it and where it took off
  private linkStep(dt: number) {
    this.linkT -= dt;
    const hx = this.home.x, hy = this.home.y + 2, hz = this.home.z;
    const dist = this.pos.distanceTo(this.home);
    if (this.linkT <= 0) {
      this.linkT = 0.2;
      let n = 0;
      for (let i = 1; i < 10; i++) {
        const k = i / 10, x = this.pos.x + (hx - this.pos.x) * k, y = this.pos.y + (hy - this.pos.y) * k, z = this.pos.z + (hz - this.pos.z) * k;
        if (this.world.blocked(x, z, y - 0.5, y + 0.5)) n++;
      }
      this.occl = Math.min(1, n / 2);
    }
    const want = clamp(1 - 0.5 * smoothstep(300, 4000, dist) - this.occl * (0.2 + 0.55 * smoothstep(40, 500, dist)), 0, 1);
    this.link += (want - this.link) * (1 - Math.exp(-dt * 2.5));
    // the picture only glitches, slightly, now and then: every 10 s or so, a little more often on a weak link
    if (this.glitch.left > 0) this.glitch.left -= dt;
    else if (Math.random() < dt * (0.07 + 0.12 * (1 - this.link))) this.glitch = { left: 0.04 + Math.random() * 0.16, k: 0.05 + Math.random() * 0.13 };
    this.breakup = this.glitch.left > 0 ? this.glitch.k : 0;
  }

  // ---------------------------------------------------------------- the model and the camera
  private pose() {
    const c = this.craft!;
    c.g.position.copy(this.pos);
    c.g.quaternion.copy(this.q);
    const fast = this.kind === 'plane' ? this.power > 0.05 : true;
    for (const o of c.spin) {
      if (c.spinAxis === 'x') o.rotation.x = this.spin;
      else o.rotation.y = this.spin;
      o.visible = !fast;
    }
    if (c.tail) { c.tail.rotation.z = this.spin * 4.2; c.tail.visible = !fast; }
    for (const b of c.blur) b.visible = fast;
  }

  // a shake from three sines per axis, amplitude 1
  private shake(f: number, seed: number) {
    const t = this.t * f;
    return Math.sin(t * 1.0 + seed) * 0.5 + Math.sin(t * 2.31 + seed * 2.1) * 0.3 + Math.sin(t * 4.7 + seed * 3.3) * 0.2;
  }

  private follow(dt: number) {
    const cam = this.camera, o = this.orbit;
    const V = this.vel.length(), fast = smoothstep(15, 75, V);
    // after a rest from dragging the camera swings back behind; the drone back to its own camera once it is there
    if (this.drag) o.idle = 0;
    o.idle += dt;
    if (o.idle > IDLE) {
      const e = 1 - Math.exp(-dt * (1.2 + 2.5 * smoothstep(2, 30, V)) * smoothstep(IDLE, IDLE + 0.6, o.idle));
      o.yaw -= o.yaw * e; o.pitch -= o.pitch * e;
      if (o.outside && Math.abs(o.yaw) < 0.03 && Math.abs(o.pitch) < 0.03) { o.outside = false; this.camSet = false; }
    }
    let fov = this.spec.fov;
    if (this.fpv) {
      cam.up.set(0, 1, 0);
      cam.position.copy(this.pos).addScaledVector(Y, 0.03);
      cam.quaternion.copy(this.q).multiply(new THREE.Quaternion().setFromAxisAngle(Z, 0.35));
      // the camera on its soft mount: a buzz from the motors, more at full throttle and speed
      const amp = 0.0025 + 0.005 * this.power + 0.004 * smoothstep(10, 45, V);
      cam.quaternion.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(this.shake(31, 1) * amp, this.shake(27, 2) * amp, this.shake(23, 3) * amp)));
      // three.js cameras look down their -z: turn the body's +x forward onto it
      cam.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(Y, -Math.PI / 2));
      if (this.crash > 0) cam.position.y += Math.sin(this.t * 40) * 0.02;
    } else {
      const drone = this.kind === 'drone';
      const [back, up, ahead] = drone ? DRONE_CAM : this.spec.cam;
      const f = X.clone().applyQuaternion(this.q), bu = Y.clone().applyQuaternion(this.q);
      const flat = new THREE.Vector3(f.x, this.kind === 'plane' ? f.y * 0.6 : 0, f.z).normalize();
      // further back, wider and shakier the faster it goes; a kick of field of view as it speeds up
      const off = new THREE.Vector3().addScaledVector(flat, -back * (1 + 0.2 * fast)).addScaledVector(Y, up * (1 - 0.15 * fast));
      // swung round it: the same distance (times the zoom), turned about the vertical and raised or lowered
      const d = off.length() * o.zoom, el = clamp(Math.asin(clamp(off.y / off.length(), -1, 1)) + o.pitch, -0.4, 1.45);
      const yw = Math.atan2(off.z, off.x) + o.yaw;
      off.set(Math.cos(el) * Math.cos(yw) * d, Math.sin(el) * d, Math.cos(el) * Math.sin(yw) * d);
      // looking ahead of it from behind, at it once swung round
      const swung = smoothstep(0, 0.45, Math.max(Math.abs(o.yaw), Math.abs(o.pitch)));
      const look = this.pos.clone().addScaledVector(flat, ahead * (1 - swung)).addScaledVector(Y, up * 0.25 * (1 - swung));
      const k = this.camSet ? 1 - Math.exp(-dt * (4 + 3 * fast)) : 1;
      this.camOff.lerp(off, k);
      this.camLook.lerp(look, this.camSet ? 1 - Math.exp(-dt * 8) : 1);
      if (!this.camSet) { this.camOff.copy(off); this.camLook.copy(look); this.camSet = true; }
      this.camPos.copy(this.pos).add(this.camOff);
      const fl = this.world.floor(this.camPos.x, this.camPos.z, this.camPos.y + 0.5, 0);
      if (fl && this.camPos.y < fl.top + (drone ? 0.6 : 1.5)) this.camPos.y = fl.top + (drone ? 0.6 : 1.5);
      const stall = this.kind === 'plane' && !this.onGround ? this.telemetryStall() : 0;
      const agl = this.pos.y - Math.max(this.groundUnder(), 0);
      const amp = (this.onGround ? 0.02 * smoothstep(2, 30, V)
        : 0.03 + 0.16 * fast * fast + 0.12 * fast * smoothstep(80, 15, agl) + 0.35 * stall + (this.kind === 'heli' ? 0.03 : 0)) * (drone ? 0.2 : 1);
      const sh = new THREE.Vector3(this.shake(9, 1), this.shake(11, 2), this.shake(8, 3)).multiplyScalar(amp);
      cam.position.copy(this.camPos).add(sh);
      // the camera leans a little with the bank (not when swung round)
      const lean = (this.kind === 'plane' ? 0.3 : 0.18) * (1 - swung);
      this.camUp.lerp(Y.clone().lerp(bu, lean).normalize(), this.camSet ? 1 - Math.exp(-dt * 4) : 1);
      cam.up.copy(this.camUp);
      cam.lookAt(this.camLook.clone().addScaledVector(sh, 0.5));
      const fwdAcc = dt > 0 ? this.acc.dot(f) : 0;
      this.fovKick += (clamp(fwdAcc / 4, -1, 1) - this.fovKick) * (1 - Math.exp(-dt * 2));
      fov = (drone ? 70 : fov) + 10 * fast + 3 * this.fovKick;
    }
    if (Math.abs(cam.fov - fov) > 0.01) { cam.fov = fov; cam.updateProjectionMatrix(); }
  }

  private telemetryStall() {
    const f = X.clone().applyQuaternion(this.q), u = Y.clone().applyQuaternion(this.q);
    const V = this.vel.length();
    if (V < 1) return 0;
    return smoothstep(ASTALL - 0.03, ASTALL + 0.05, Math.atan2(-this.vel.dot(u), this.vel.dot(f)));
  }

  telemetry(): Telemetry {
    const f = X.clone().applyQuaternion(this.q), r = Z.clone().applyQuaternion(this.q), u = Y.clone().applyQuaternion(this.q);
    const head = Math.atan2(f.z, f.x);
    const hx = this.home.x - this.pos.x, hz = this.home.z - this.pos.z;
    const V = this.vel.length();
    const aoa = V > 1 ? Math.atan2(-this.vel.dot(u), this.vel.dot(f)) : 0;
    const plane = this.kind === 'plane';
    return {
      kind: this.kind, speed: V, vs: this.vel.y, alt: this.pos.y, agl: this.pos.y - Math.max(this.groundUnder(), 0),
      heading: wrapPi(head - this.north + Math.PI / 2), pitch: Math.asin(clamp(f.y, -1, 1)), roll: Math.atan2(-r.y, u.y),
      turn: this.turnRate, slip: this.ball, aoa,
      power: this.power,
      rpm: plane ? 500 + 1800 * Math.sqrt(this.power) + 5 * V : 100 - 2.5 * (this.power - 0.5) + 0.3 * Math.sin(this.t * 0.7),
      torque: plane ? 0 : clamp(18 + 84 * this.power * (1 - 0.1 * smoothstep(6, 20, Math.hypot(this.vel.x, this.vel.z))), 0, 125),
      time: this.flown, home: Math.hypot(hx, hz), homeDir: wrapPi(Math.atan2(hz, hx) - head), link: this.link,
      crashed: this.crash > 0, ground: this.onGround, stall: plane && !this.onGround && aoa > ASTALL - 0.03,
    };
  }
}
