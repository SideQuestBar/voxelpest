// Driving round Budapest: arcade physics on the voxels for each vehicle of controls/vehicles.ts (the taxi, a Trabant,
// a police car, a Bubi bike, a BKK bus). Throttle, brake and reverse, steering that tightens at low speed, the body
// following the ground under its wheels (pitch and roll; the bike leans into its turns instead), kerbs taken in its
// stride, walls bounced off, gravity off quay edges. A chase camera follows (controls/chase.ts: further back for the
// bus, close behind the bike; a drag or the right stick swings it round), exhaust puffs from the pipe
// (controls/exhaust.ts), streaks flow past at speed (controls/streaks.ts); R puts it back on the nearest road. On a
// controller: RT gas, LT brake and reverse, the left stick steers, A handbrake, B boost, Y back on the road.
import * as THREE from 'three';
import type { World } from '../engine/world';
import { MAT } from '../meta';
import { clamp, isTouch, smoothstep, wrapPi } from '../util';
import { Chase } from './chase';
import { Exhaust } from './exhaust';
import { PAD, type Input } from './input';
import { mats } from './kit';
import { buildModel, type Model } from './models';
import { Streaks } from './streaks';
import { SPECS, type Spec, type VehicleKind } from './vehicles';

const GRAVITY = 22;
// how cold a day of each month is, for the exhaust's condensation (snow makes it cold whatever the month)
const WINTER = [1, 0.9, 0.6, 0.3, 0.1, 0, 0, 0, 0.1, 0.35, 0.7, 0.95];

export class Car {
  readonly head = new THREE.SpotLight(0xfff1d6, 0, 70, 0.55, 0.5, 1.2);
  readonly pos = new THREE.Vector3();
  heading = 0;          // grid angle: forward is (cos, sin) in (x, z)
  speed = 0;            // m/s along the heading
  kind: VehicleKind = 'taxi';
  spec: Spec = SPECS.taxi;
  flashing = false;     // the police car's lights
  private braking = false;
  private readonly models = new Map<VehicleKind, Model>();
  private model: Model;
  private steer = 0;
  private vy = 0;
  private pitch = 0;
  private roll = 0;
  private lean = 0;
  private spin = 0;
  private blur = 0;
  private crank = 0;
  private time = 0;
  private night = 0;
  private readonly winter = WINTER[new Date().getMonth()];
  private readonly vel = new THREE.Vector3();
  readonly chase: Chase;
  private readonly exhaust: Exhaust;
  private readonly streaks: Streaks;
  private last = { x: 0, y: 0, z: 0, h: 0 };
  onReset: (() => void) | null = null;

  // dom: the canvas (drags on it swing the camera round); levels: the weather's (snow is cold for the exhaust)
  constructor(private readonly scene: THREE.Scene, private readonly camera: THREE.PerspectiveCamera, private readonly world: World,
    private readonly input: Input, dom: HTMLElement, private readonly levels: { snow: number } = { snow: 0 }) {
    scene.add(this.head, this.head.target);
    this.model = this.use('taxi');
    this.chase = new Chase(camera, world, input, dom);
    this.exhaust = new Exhaust(scene, isTouch() ? 90 : 220);
    this.streaks = new Streaks(scene, isTouch() ? 90 : 180, dom);
  }

  get kmh() { return Math.abs(this.speed) * 3.6; }

  private use(k: VehicleKind) {
    let m = this.models.get(k);
    if (!m) {
      m = buildModel(k);
      this.models.set(k, m);
      this.scene.add(m.g);
    }
    return m;
  }

  // another vehicle where this one stands, facing the same way; back on the road if it doesn't fit there
  setKind(k: VehicleKind) {
    if (k === this.kind) return;
    const on = this.model.g.visible;
    this.model.g.visible = false;
    this.kind = k;
    this.spec = SPECS[k];
    this.model = this.use(k);
    this.model.g.visible = on;
    this.speed = clamp(this.speed, -this.spec.reverse, this.spec.vmax);
    this.steer = 0;
    this.lean = 0;
    if (on) {
      this.pose();
      if (!this.fits()) this.onReset?.();
    }
  }

  place(x: number, y: number, z: number, heading: number) {
    this.pos.set(x, y, z);
    this.heading = heading;
    this.speed = 0; this.vy = 0; this.steer = 0; this.lean = 0;
    this.last = { x, y, z, h: heading };
    this.pose();
    this.chase.reset(this);
  }

  show(on: boolean, night: number) {
    this.model.g.visible = on;
    this.night = night;
    this.chase.active = on;
    this.exhaust.mesh.visible = on;
    if (!on) { this.exhaust.clear(); this.streaks.mesh.visible = false; }
    this.head.intensity = on ? (this.kind === 'bubi' ? 20 : this.kind === 'bus' ? 80 : 60) * night : 0;
    const M = mats();
    M.lamp.emissiveIntensity = 0.3 + 2.5 * night;
    M.tail.emissiveIntensity = 0.3 + 0.9 * night + (this.braking ? 1.4 : 0);   // brighter turns orange in the tone mapping
    for (const m of this.model.glow) m.emissiveIntensity = 0.5 + 2 * night;
  }

  // a point of the vehicle (lx forward, lz to the right) on the ground plane
  private at(lx: number, lz: number, h = this.heading, x = this.pos.x, z = this.pos.z): [number, number] {
    const c = Math.cos(h), s = Math.sin(h);
    return [x + c * lx - s * lz, z + s * lx + c * lz];
  }

  private blockedAt(lx: number, lz: number, h: number, x: number, z: number) {
    const [px, pz] = this.at(lx, lz, h, x, z);
    return this.world.blocked(px, pz, this.pos.y + this.spec.step, this.pos.y + this.spec.height) !== false;
  }

  // across the bumper at lx, no more than 0.6 m apart
  private across(): number[] {
    const w = this.spec.wid, n = Math.max(2, Math.ceil(w / 0.6));
    return Array.from({ length: n + 1 }, (_, i) => -w / 2 + (w * i) / n);
  }

  // along the sides (the corners too): long vehicles cut corners when they turn
  private along(): [number, number][] {
    const { len, wid } = this.spec, n = Math.max(1, Math.ceil(len / 2.2)), out: [number, number][] = [];
    for (let i = 0; i <= n; i++) for (const s of [-1, 1]) out.push([-len / 2 + (len * i) / n, (s * wid) / 2]);
    return out;
  }

  // nothing solid in the footprint, here and now
  private fits() {
    const { x, z } = this.pos;
    return this.along().every(([lx, lz]) => !this.blockedAt(lx, lz, this.heading, x, z))
      && this.across().every((lz) => !this.blockedAt(this.spec.len / 2, lz, this.heading, x, z) && !this.blockedAt(-this.spec.len / 2, lz, this.heading, x, z));
  }

  update(dt: number) {
    const i = this.input, pad = i.pad, sp = this.spec, bike = sp.track === 0;
    this.time += dt;
    if (i.has('KeyR') || i.pressed(PAD.Y)) { i.down.delete('KeyR'); this.onReset?.(); return; }
    let throttle = i.axis(['KeyS', 'ArrowDown'], ['KeyW', 'ArrowUp']);
    let steerIn = i.axis(['KeyA', 'ArrowLeft'], ['KeyD', 'ArrowRight']);
    if (i.stick.active) steerIn = clamp(i.stick.x * 1.3, -1, 1);
    if (pad.lx) steerIn = clamp(pad.lx * 1.15, -1, 1);
    if (pad.rt || pad.lt) throttle = pad.rt - pad.lt;
    if (i.pedal.gas) throttle = 1;
    if (i.pedal.brake) throttle = -1;
    const hand = i.has('Space') || !!pad.held[PAD.A], boost = i.has('ShiftLeft', 'ShiftRight') || !!pad.held[PAD.B];
    const vmax = boost ? sp.boost : sp.vmax, th = Math.abs(throttle);
    if (throttle > 0) this.speed += (this.speed < 0 ? sp.brake : sp.accel * (1 - Math.max(this.speed, 0) / vmax)) * th * dt;
    else if (throttle < 0) this.speed -= (this.speed > 0 ? sp.brake : sp.accel * 0.65) * th * dt;
    else this.speed *= Math.exp(-dt * (bike ? 0.25 : 0.35));
    if (hand) this.speed *= Math.exp(-dt * 4);
    this.braking = (hand || (throttle < 0 && this.speed > 0.5)) && Math.abs(this.speed) > 0.1;
    if (this.speed > vmax) this.speed = Math.max(vmax, this.speed - 6 * dt);   // easing off the boost
    this.speed = clamp(this.speed, -sp.reverse, sp.boost);
    if (Math.abs(this.speed) < 0.05 && !throttle) this.speed = 0;
    const [fa, ra] = sp.axles, wb = fa - ra;
    const maxSteer = Math.atan(wb / sp.turn) / (1 + Math.abs(this.speed) / sp.grip);
    this.steer += (steerIn * maxSteer - this.steer) * (1 - Math.exp(-dt * (bike ? 10 : 8)));
    const turn = (this.speed / wb) * Math.tan(this.steer) * dt;
    const h0 = this.heading;
    this.heading = wrapPi(this.heading + turn);
    // the next position, unless something is in the way: the bumper ahead (or behind, reversing), and anything along
    // the sides or at the corners that was clear before this step
    const f = new THREE.Vector2(Math.cos(this.heading), Math.sin(this.heading)), d = this.speed * dt;
    const nx = this.pos.x + f.x * d, nz = this.pos.z + f.y * d;
    const ahead = this.speed >= 0 ? sp.len / 2 : -sp.len / 2;
    let hit = this.across().some((lz) => this.blockedAt(ahead, lz, this.heading, nx, nz));
    if (!hit && d !== 0) {
      hit = this.along().some(([lx, lz]) => this.blockedAt(lx, lz, this.heading, nx, nz) && !this.blockedAt(lx, lz, h0, this.pos.x, this.pos.z));
    }
    if (hit) {
      this.speed = -this.speed * 0.25;
      this.heading = h0;
    } else {
      this.pos.x = nx; this.pos.z = nz;
    }
    // the ground under the wheels: four, or two in line for the bike
    const t = sp.track / 2, wheels: [number, number][] = bike ? [[fa, 0], [ra, 0]] : [[fa, t], [fa, -t], [ra, t], [ra, -t]];
    const ys: number[] = [];
    let water = false;
    for (const [lx, lz] of wheels) {
      const [x, z] = this.at(lx, lz);
      const fl = this.world.floor(x, z, this.pos.y, sp.step);
      ys.push(fl ? fl.top : this.pos.y);
      if (fl?.mat === MAT.WATER) water = true;
    }
    const front = bike ? ys[0] : (ys[0] + ys[1]) / 2, rear = bike ? ys[1] : (ys[2] + ys[3]) / 2;
    const ground = Math.max(rear + ((front - rear) * -ra) / wb, Math.min(...ys));
    this.vy -= GRAVITY * dt;
    this.pos.y += this.vy * dt;
    if (this.pos.y <= ground) { this.pos.y = ground; this.vy = 0; }
    if (water && this.pos.y - ground < 0.1) { this.onReset?.(); return; }
    if (this.vy === 0 && Math.abs(this.speed) > 1) this.last = { x: this.pos.x, y: this.pos.y, z: this.pos.z, h: this.heading };
    // pitch from the axles, roll from the sides; the bike leans into the turn, the others roll out of it a little
    const pT = Math.atan2(front - rear, wb), rT = bike ? 0 : Math.atan2((ys[1] + ys[3]) / 2 - (ys[0] + ys[2]) / 2, sp.track);
    const lat = dt > 0 ? (this.speed * turn) / dt : 0;
    const leanT = bike ? clamp(Math.atan(lat / 9.81), -0.55, 0.55) : clamp(sp.lean * lat, -0.08, 0.08);
    const k = 1 - Math.exp(-dt * 10);
    this.pitch += (clamp(pT, -0.5, 0.5) - this.pitch) * k;
    this.roll += (clamp(rT, -0.4, 0.4) - this.roll) * k;
    this.lean += (leanT - this.lean) * (1 - Math.exp(-dt * (bike ? 6 : 4)));
    // the wheels roll, but never by more than about half the rim's symmetry a frame (any faster and they'd seem to
    // stand still or turn backwards, the wagon-wheel effect); past that the rim blurs into a disc
    const roll = (this.speed * dt) / sp.r, per = this.model.period;
    this.spin += clamp(roll, -0.42 * per, 0.42 * per);
    if (dt > 0) this.blur += (smoothstep(0.18 * per, 0.45 * per, Math.abs(roll)) - this.blur) * (1 - Math.exp(-dt * 10));
    if (bike && throttle > 0 && this.speed > 0.1) this.crank += ((this.speed * dt) / 4.6) * Math.PI * 2;
    this.pose();
    this.chase.update(dt, this);
    this.vel.set(f.x * this.speed, this.vy, f.y * this.speed);
    const gas = throttle > 0 ? throttle : this.speed < 0.5 && throttle < 0 ? -throttle : 0;
    const cold = Math.max(this.levels.snow, this.winter * (0.75 + 0.25 * this.night));
    this.exhaust.update(dt, sp, this.model.g, this.vel, ground, gas, this.night, cold, this.braking);
    this.streaks.update(this.camera, this.pos, this.vel, sp.boost > sp.vmax ? smoothstep(sp.vmax, sp.boost, Math.abs(this.speed)) : 0, this.night);
  }

  // the model where the vehicle is, and the headlamp ahead of it
  private pose() {
    const g = this.model.g;
    g.position.copy(this.pos);
    g.rotation.set(0, 0, 0);
    g.rotateY(-this.heading);
    g.rotateZ(this.pitch);
    g.rotateX(this.roll + this.lean);
    this.model.pose(this.spin, this.steer, this.crank, this.time, this.flashing && this.kind === 'police', this.blur);
    const [lx, ly] = this.spec.lamp, [hx, hz] = this.at(lx, 0);
    this.head.position.set(hx, this.pos.y + ly, hz);
    this.head.target.position.set(this.pos.x + Math.cos(this.heading) * 30, this.pos.y - 1.5, this.pos.z + Math.sin(this.heading) * 30);
  }

  lastSafe() { return this.last; }
}
