// Fly mode: the FPV drone, the small plane and the helicopter over the voxels, with arcade physics.
// - The drone flies in angle mode: the stick tilts it (up to 55°) and it accelerates the way it leans, holding its
//   height with the throttle centred; Space climbs, Shift sinks. Seen from its camera, tilted up 20° as FPV cameras are.
// - The plane: throttle, pitch, roll and rudder; turns as it banks, sinks and drops its nose below 25 m/s, lands and
//   takes off from any flat ground. Seen from behind.
// - The helicopter: the cyclic tilts it and it moves that way, the collective climbs and sinks, the pedals turn it;
//   it hovers hands off. Seen from behind.
// Anything solid where it flies is a crash: a moment's pause, then it is back where it last flew clear.
// Keys: W/S and A/D pitch and roll (the plane: W pushes the nose down), Q/E yaw, Space/Shift or R/F up and down
// (throttle, collective), V the next aircraft, T back in the air. A controller: the left stick pitch and roll, the
// right stick yaw, RT/LT up and down, LB/RB the aircraft, Y back in the air. Touch: the stick, the pedals up and down.
import * as THREE from 'three';
import type { World } from '../engine/world';
import { clamp, smoothstep, wrapPi } from '../util';
import { AIR, buildCraft, type AircraftKind, type AirSpec, type Craft } from './aircraft';
import { mats } from './kit';
import { PAD, type Input } from './input';

const G = 9.81;
const X = new THREE.Vector3(1, 0, 0), Y = new THREE.Vector3(0, 1, 0), Z = new THREE.Vector3(0, 0, 1);

export interface Telemetry {
  kind: AircraftKind;
  speed: number;        // m/s through the air
  vs: number;           // m/s up
  alt: number;          // m above the model's base (≈ the Danube's level, 98 m above sea level: add for altitude)
  agl: number;          // m over what is under it
  heading: number;      // radians, map north = 0, clockwise
  pitch: number; roll: number;  // radians, nose up and right wing down positive
  power: number;        // throttle or collective, 0..1
  time: number;         // seconds since take-off
  home: number;         // m to where it started
  homeDir: number;      // radians, relative to the heading
  crashed: boolean;
  ground: boolean;
  stall: boolean;
}

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
  private speed = 0;              // the plane's airspeed
  private onGround = false;
  private crash = 0;              // seconds left of the crash pause
  private spin = 0;
  private t = 0;
  private flown = 0;
  private home = new THREE.Vector3();
  private safe: { p: THREE.Vector3; yaw: number; t: number } = { p: new THREE.Vector3(), yaw: 0, t: 0 };
  private readonly camPos = new THREE.Vector3();
  private readonly camLook = new THREE.Vector3();
  private camSet = false;
  // the map's edges (m), and the compass: map north as a heading in the grid
  bounds: [number, number, number, number] = [-400, -400, 6300, 7000];
  north = 0;
  onKind: ((k: AircraftKind) => void) | null = null;

  constructor(private readonly scene: THREE.Scene, private readonly camera: THREE.PerspectiveCamera, private readonly world: World,
    private readonly input: Input) {}

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
    const on = !!this.craft?.g.visible;
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
    this.q.setFromAxisAngle(Y, -heading);
    this.speed = this.kind === 'plane' ? 46 : 0;
    this.vel.set(Math.cos(heading) * this.speed, 0, Math.sin(heading) * this.speed);
    this.power = this.kind === 'plane' ? 0.62 : 0.5;
    this.onGround = false;
    this.crash = 0;
    if (!keepHeight) { this.home.copy(this.pos); this.flown = 0; }
    this.safe = { p: this.pos.clone(), yaw: heading, t: 0 };
    this.camSet = false;
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

    this.craft!.g.visible = on && this.kind !== 'drone';
    for (const m of this.craft!.glow) m.emissiveIntensity = 0.4 + 2.2 * night;
    const M = mats();
    M.lamp.emissiveIntensity = 0.3 + 2.5 * night;
  }

  // the stick, keys and pedals, each -1..1
  private sticks() {
    const i = this.input, pad = i.pad;
    let pitch = i.axis(['KeyW', 'ArrowUp'], ['KeyS', 'ArrowDown']);   // + pulls back: nose up, or backwards
    let roll = i.axis(['KeyA', 'ArrowLeft'], ['KeyD', 'ArrowRight']);
    let yaw = i.axis(['KeyQ'], ['KeyE']);
    let up = i.axis(['ShiftLeft', 'ShiftRight', 'KeyF'], ['Space', 'KeyR']);
    if (i.stick.active) { pitch = -i.stick.y; roll = i.stick.x; yaw = i.stick.x * 0.7; }
    if (pad.lx || pad.ly) { pitch = pad.ly; roll = pad.lx; }
    if (pad.rx) yaw = pad.rx;
    if (pad.rt || pad.lt) up = pad.rt - pad.lt;
    if (i.pedal.gas) up = 1;
    if (i.pedal.brake) up = -1;
    return { pitch, roll, yaw, up };
  }

  update(dt: number) {
    if (!this.craft) return;
    const i = this.input;
    this.t += dt;
    if (i.has('KeyT') || i.pressed(PAD.Y)) { i.down.delete('KeyT'); this.respawn(); }
    if (this.crash > 0) {
      this.crash -= dt;
      if (this.crash <= 0) this.respawn();
      this.follow(dt);
      return;
    }
    const s = this.sticks();
    if (this.kind === 'plane') this.planeStep(dt, s);
    else this.rotorStep(dt, s);
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
      const lo = this.onGround ? py + 0.6 : py - h * 0.6, hi = py + h * 0.6;
      if (this.world.blocked(px, pz, lo, hi)) { crashed = true; break; }
    }
    if (crashed) {
      this.crash = 1.6;
      this.vel.set(0, 0, 0); this.speed = 0;
    } else if (!this.onGround && this.t - this.safe.t > 1.0 && this.pos.y > this.groundUnder() + 6) {
      this.safe = { p: this.pos.clone(), yaw: this.heading(), t: this.t };
    }
    this.flown += dt;
    this.pose();
    this.follow(dt);
  }

  private groundUnder(x = this.pos.x, z = this.pos.z, y = this.pos.y) {
    const fl = this.world.floor(x, z, y + 0.5, 0);
    return fl ? fl.top : this.world.groundAt(x, z) ?? -1e3;
  }

  private respawn() {
    const p = this.safe.p;
    this.place(p.x, p.y, p.z, this.safe.yaw, true);
  }

  // ---------------------------------------------------------------- the plane
  private planeStep(dt: number, s: { pitch: number; roll: number; yaw: number; up: number }) {
    this.power = clamp(this.power + s.up * dt * 0.5, 0, 1);
    const f = X.clone().applyQuaternion(this.q), up = Y.clone().applyQuaternion(this.q);
    const pitch = Math.asin(clamp(f.y, -1, 1));
    const bank = Math.atan2(-Z.clone().applyQuaternion(this.q).y, up.y);  // right wing down positive
    const v = this.speed;
    // thrust against drag and the climb
    const T = 9.2 * this.power, kd = 9.2 / (this.spec.vmax * this.spec.vmax);
    this.speed = Math.max(0, v + (T - kd * v * v - G * Math.sin(pitch) - (this.onGround ? 0.6 + (s.up < 0 && this.power < 0.05 ? 4 : 0) : 0)) * dt);
    const ctl = smoothstep(4, 30, v);  // the controls bite with airspeed
    const stall = smoothstep(27, 21, v) * (this.onGround ? 0 : 1);
    // rates about the body: roll, pitch (nose up +), yaw (nose right +)
    // the stick asks for a bank (up to 60°) and, let go, it levels its wings and slowly its nose
    let rr = clamp((s.roll * 1.05 - bank) * 2.2, -1.3, 1.3) * ctl;
    let pr = s.pitch * 0.75 * ctl - stall * 0.7 - pitch * 0.35 * (1 - Math.abs(s.pitch)) * ctl;
    const yr = s.yaw * 0.35 * ctl;
    if (this.onGround) { rr = -bank * 3; pr = Math.min(pr, v > 25 ? pr : -pitch * 2); }
    this.q.multiply(new THREE.Quaternion().setFromAxisAngle(X, rr * dt));
    this.q.multiply(new THREE.Quaternion().setFromAxisAngle(Z, pr * dt));
    this.q.multiply(new THREE.Quaternion().setFromAxisAngle(Y, -yr * dt));
    // the turn a bank makes: a yaw about the world's up, g tan(bank) / v
    if (v > 5 && !this.onGround) this.q.premultiply(new THREE.Quaternion().setFromAxisAngle(Y, -(G * Math.tan(clamp(bank, -1.3, 1.3)) / v) * dt));
    if (this.onGround) this.q.premultiply(new THREE.Quaternion().setFromAxisAngle(Y, -s.roll * 0.5 * smoothstep(0.5, 6, v) * dt));
    this.q.normalize();
    const f2 = X.clone().applyQuaternion(this.q);
    // lift short of the weight below the stall: it sinks
    const sink = stall * 12 + (this.onGround ? 0 : smoothstep(30, 24, v) * 3 + (1 - Math.cos(bank)) * 4);
    this.vel.copy(f2).multiplyScalar(this.speed);
    this.vel.y -= sink;
    this.pos.addScaledVector(this.vel, dt);
    // the ground: a landing if gentle, a crash if not
    const gy = this.groundUnder() + 0.25;
    if (this.pos.y <= gy) {
      const hard = this.vel.y < -4.5 || Math.abs(bank) > 0.35 || pitch < -0.25 || this.speed > 45;
      if (hard && !this.onGround) { this.crash = 1.6; this.speed = 0; return; }
      this.pos.y = gy;
      this.onGround = true;
      const level = new THREE.Quaternion().setFromAxisAngle(Y, -this.heading());
      this.q.slerp(level.multiply(new THREE.Quaternion().setFromAxisAngle(Z, Math.max(pitch, 0))), 1 - Math.exp(-dt * 6));
    } else if (this.onGround && this.pos.y > gy + 0.4) this.onGround = false;
    this.spin += (15 + 50 * this.power) * dt;
  }

  // ---------------------------------------------------------------- the drone and the helicopter
  private rotorStep(dt: number, s: { pitch: number; roll: number; yaw: number; up: number }) {
    const drone = this.kind === 'drone';
    const maxT = drone ? 0.96 : 0.45, yawR = drone ? 3.2 : 1.1, resp = drone ? 9 : 2.6;
    // the attitude follows the stick: forward stick (pitch < 0) noses down
    this.tilt.p += (s.pitch * maxT - this.tilt.p) * (1 - Math.exp(-dt * resp));
    this.tilt.r += (s.roll * maxT - this.tilt.r) * (1 - Math.exp(-dt * resp));
    this.yaw = wrapPi(this.yaw + s.yaw * yawR * dt + (drone ? 0 : s.roll * 0.35 * dt));
    this.power = clamp(0.5 + s.up * 0.5, 0, 1);
    // accelerating the way it leans, against drag
    const c = Math.cos(this.yaw), sn = Math.sin(this.yaw);
    const ax = -Math.tan(this.tilt.p) * G, az = Math.tan(this.tilt.r) * G;   // forward, right
    const drag = drone ? 0.0065 : 0.0024;
    const hv = new THREE.Vector2(this.vel.x, this.vel.z), sp = hv.length();
    this.vel.x += (c * ax - sn * az) * dt - this.vel.x * sp * drag * dt * G / 1.5;
    this.vel.z += (sn * ax + c * az) * dt - this.vel.z * sp * drag * dt * G / 1.5;
    // up and down: a climb rate the throttle or collective asks for, reached quickly
    const want = s.up * (drone ? 14 : 8);
    this.vel.y += (want - this.vel.y) * (1 - Math.exp(-dt * (drone ? 4 : 1.6)));
    if (!drone) {
      const vmax = this.spec.vmax;
      const hs = Math.hypot(this.vel.x, this.vel.z);
      if (hs > vmax) { this.vel.x *= vmax / hs; this.vel.z *= vmax / hs; }
    }
    this.pos.addScaledVector(this.vel, dt);
    const gy = this.groundUnder() + (drone ? 0.05 : 0.02);
    if (this.pos.y <= gy) {
      if (this.vel.y < -7 || Math.hypot(this.vel.x, this.vel.z) > 14) { this.crash = 1.6; return; }
      this.pos.y = gy;
      this.vel.y = Math.max(this.vel.y, 0);
      this.vel.x *= Math.exp(-dt * 4); this.vel.z *= Math.exp(-dt * 4);
      this.tilt.p *= Math.exp(-dt * 6); this.tilt.r *= Math.exp(-dt * 6);
      this.onGround = true;
    } else this.onGround = false;
    this.q.setFromEuler(new THREE.Euler(this.tilt.r, -this.yaw, this.tilt.p, 'YZX'));
    this.spin += (drone ? 0 : 7 + 6 * this.power) * dt * Math.PI * 2;
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

  private follow(dt: number) {
    const cam = this.camera;
    if (this.kind === 'drone') {
      cam.position.copy(this.pos).addScaledVector(Y, 0.03);
      cam.quaternion.copy(this.q).multiply(new THREE.Quaternion().setFromAxisAngle(Z, 0.35));
      // three.js cameras look down their -z: turn the body's +x forward onto it
      cam.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(Y, -Math.PI / 2));
      if (this.crash > 0) cam.position.y += Math.sin(this.t * 40) * 0.02;
    } else {
      const [back, up, ahead] = this.spec.cam;
      const f = X.clone().applyQuaternion(this.q);
      const flat = new THREE.Vector3(f.x, this.kind === 'plane' ? f.y * 0.6 : 0, f.z).normalize();
      const want = this.pos.clone().addScaledVector(flat, -back).addScaledVector(Y, up);
      const look = this.pos.clone().addScaledVector(flat, ahead).addScaledVector(Y, up * 0.25);
      const k = this.camSet ? 1 - Math.exp(-dt * 5) : 1;
      this.camPos.lerp(want, k);
      this.camLook.lerp(look, this.camSet ? 1 - Math.exp(-dt * 8) : 1);
      if (!this.camSet) { this.camPos.copy(want); this.camLook.copy(look); this.camSet = true; }
      const fl = this.world.floor(this.camPos.x, this.camPos.z, this.camPos.y + 0.5, 0);
      if (fl && this.camPos.y < fl.top + 1.5) this.camPos.y = fl.top + 1.5;
      cam.position.copy(this.camPos);
      cam.up.set(0, 1, 0);
      cam.lookAt(this.camLook);
    }
    if (Math.abs(cam.fov - this.spec.fov) > 0.01) { cam.fov = this.spec.fov; cam.updateProjectionMatrix(); }
  }

  telemetry(): Telemetry {
    const f = X.clone().applyQuaternion(this.q), r = Z.clone().applyQuaternion(this.q), u = Y.clone().applyQuaternion(this.q);
    const head = Math.atan2(f.z, f.x);
    const hx = this.home.x - this.pos.x, hz = this.home.z - this.pos.z;
    const speed = this.kind === 'plane' ? this.speed : this.vel.length();
    return {
      kind: this.kind, speed, vs: this.vel.y, alt: this.pos.y, agl: this.pos.y - Math.max(this.groundUnder(), 0),
      heading: wrapPi(head - this.north + Math.PI / 2), pitch: Math.asin(clamp(f.y, -1, 1)), roll: Math.atan2(-r.y, u.y),
      power: this.power, time: this.flown, home: Math.hypot(hx, hz), homeDir: wrapPi(Math.atan2(hz, hx) - head),
      crashed: this.crash > 0, ground: this.onGround, stall: this.kind === 'plane' && !this.onGround && this.speed < 25,
    };
  }
}
