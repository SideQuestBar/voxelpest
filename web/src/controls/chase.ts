// Drive mode's chase camera. It sits behind the vehicle and follows its heading with a little lag; a drag (the mouse,
// or a finger on free screen: not the stick, the pedals or a button) or the controller's right stick swings it round
// the vehicle and up or down, and after 1.5 s without any of that it eases back behind (faster when moving). Speed
// shows as driving games show it: the view widens, the camera comes lower and closer, hangs back a little under
// acceleration (and closes in braking). A wall between it and the vehicle
// brings it in; it never goes into the ground.
import * as THREE from 'three';
import type { World } from '../engine/world';
import { clamp, smoothstep, wrapPi } from '../util';
import type { Input } from './input';
import type { Spec } from './vehicles';

export const FOV = 62;
const IDLE = 1.5;               // seconds without camera input before it recentres
const LOW = 0.04, HIGH = 1.25;  // the camera's elevation round the vehicle, radians

export interface Followed { readonly pos: THREE.Vector3; readonly heading: number; readonly speed: number; readonly spec: Spec }

export class Chase {
  yaw = 0;                // the swing round the vehicle: positive takes the camera to its left, looking right
  pitch = 0;              // added to the chase camera's elevation
  private on = false;
  private idle = IDLE;
  private follow = 0;     // the heading the camera follows, lagging the vehicle's
  private lookY = 0;
  private lag = 0;        // metres further back under acceleration (negative: closer, braking)
  private reach = 1e3;    // how far out it may go: a wall's distance, eased back out
  private fov = FOV;
  private lastSpeed = 0;
  private t = 0;
  private drag: { id: number; x: number; y: number } | null = null;
  private readonly p = new THREE.Vector3();
  private readonly look = new THREE.Vector3();

  constructor(private readonly camera: THREE.PerspectiveCamera, private readonly world: World, private readonly input: Input,
    private readonly dom: HTMLElement) {
    addEventListener('pointerdown', (e) => {
      if (!this.on || this.drag) return;
      const t = e.target as Element | null;
      if (e.pointerType === 'mouse' ? t !== dom || e.button !== 0 : !(t === dom || t?.closest?.('.label, #sq-pin'))) return;
      this.drag = { id: e.pointerId, x: e.clientX, y: e.clientY };
      if (e.pointerType === 'mouse') { dom.setPointerCapture?.(e.pointerId); dom.style.cursor = 'grabbing'; }
    });
    addEventListener('pointermove', (e) => {
      const d = this.drag;
      if (!d || e.pointerId !== d.id) return;
      const k = e.pointerType === 'mouse' ? 0.0055 : 0.0085;
      this.turn((e.clientX - d.x) * k, (e.clientY - d.y) * k * 0.7);
      d.x = e.clientX; d.y = e.clientY;
    });
    const up = (e: PointerEvent) => {
      if (this.drag?.id !== e.pointerId) return;
      this.drag = null;
      if (this.on) dom.style.cursor = 'grab';
    };
    addEventListener('pointerup', up);
    addEventListener('pointercancel', up);
  }

  set active(on: boolean) {
    if (on === this.on) return;
    this.on = on;
    this.drag = null;
    this.dom.style.cursor = on ? 'grab' : '';
  }

  get active() { return this.on; }

  private turn(dy: number, dp: number) {
    this.yaw = wrapPi(this.yaw + dy);
    this.pitch += dp;
    this.idle = 0;
  }

  // straight behind, at once (a new start, back on the road)
  reset(v: Followed) {
    this.follow = v.heading;
    this.lookY = v.pos.y + v.spec.cam[2];
    this.yaw = 0; this.pitch = 0; this.idle = IDLE;
    this.lag = 0; this.reach = 1e3; this.fov = FOV; this.lastSpeed = v.speed;
    this.update(0, v);
  }

  update(dt: number, v: Followed) {
    const sp = v.spec, [back, up, lookY, ahead] = sp.cam, pad = this.input.pad, cam = this.camera;
    this.t += dt;
    if (this.on && (pad.rx || pad.ry)) this.turn(pad.rx * Math.abs(pad.rx) * 2.6 * dt, pad.ry * Math.abs(pad.ry) * 1.5 * dt);
    if (this.drag) this.idle = 0;
    this.idle += dt;
    const s = Math.abs(v.speed), rel = Math.min(s / sp.vmax, 1), fast = smoothstep(0.08, 1, rel);
    // back behind once the camera controls rest, smoothly, quicker when moving
    if (this.idle > IDLE) {
      const k = (0.8 + 3.2 * smoothstep(0.5, 12, s)) * smoothstep(IDLE, IDLE + 0.6, this.idle);
      const e = 1 - Math.exp(-dt * k);
      this.yaw -= this.yaw * e; this.pitch -= this.pitch * e;
    }
    this.follow += wrapPi(v.heading - this.follow) * (1 - Math.exp(-dt * 4.5));
    // hanging back as it pulls away, closing in as it brakes
    const acc = dt > 0 ? (v.speed - this.lastSpeed) / dt : 0;
    this.lastSpeed = v.speed;
    this.lag += (clamp(acc * 0.13, -0.7, 1.1) - this.lag) * (1 - Math.exp(-dt * 3));
    // lower and closer at speed
    const d0 = Math.hypot(back, up - lookY), e0 = Math.atan2(up - lookY, back) * (1 - 0.22 * fast);
    this.pitch = clamp(this.pitch, LOW - e0, HIGH - e0);
    const el = e0 + this.pitch, yaw = this.follow + this.yaw;
    let d = d0 * (1 - 0.13 * fast) + this.lag;
    this.lookY += (v.pos.y + lookY - this.lookY) * (dt > 0 ? 1 - Math.exp(-dt * 12) : 1);   // kerbs don't jolt the view
    const dx = -Math.cos(yaw) * Math.cos(el), dy = Math.sin(el), dz = -Math.sin(yaw) * Math.cos(el);
    // a wall in the way (not a post: three samples in a row, 0.8 m of it): come in in front of it at once, go back out
    // slowly
    let free = d + 4, run = 0;
    for (let t = 0.8; t < d + 1.2; t += 0.4) {
      run = this.world.blocked(v.pos.x + dx * t, v.pos.z + dz * t, this.lookY + dy * t - 0.3, this.lookY + dy * t + 0.3) ? run + 1 : 0;
      if (run === 3) {
        free = Math.max(t - 1.4, sp.wid / 2 + 0.5);
        break;
      }
    }
    this.reach = free < this.reach ? free : this.reach + (free - this.reach) * (1 - Math.exp(-dt * 2));
    d = Math.min(d, this.reach);
    const p = this.p.set(v.pos.x + dx * d, this.lookY + dy * d, v.pos.z + dz * d);
    const fl = this.world.floor(p.x, p.z, p.y + 0.5, 0);
    if (fl && p.y < fl.top + 0.9) p.y = fl.top + 0.9;
    const over = sp.boost > sp.vmax ? smoothstep(sp.vmax, sp.boost, s) : 0;
    // the point looked at: ahead of the vehicle from straight behind it, the vehicle's middle (the orbit's pivot) as
    // soon as the camera swings round: looking ahead of it then, the vehicle turned about a point off its centre
    const a = ahead * (1 - smoothstep(0, 0.45, Math.abs(this.yaw)));
    this.look.set(v.pos.x + Math.cos(v.heading) * a, this.lookY, v.pos.z + Math.sin(v.heading) * a);
    cam.position.copy(p);
    cam.lookAt(this.look);
    // the view widens with speed
    const fov = FOV + sp.feel.fov * smoothstep(0.1, 1, rel) + 6 * over;
    this.fov += (fov - this.fov) * (dt > 0 ? 1 - Math.exp(-dt * 2.5) : 1);
    if (Math.abs(cam.fov - this.fov) > 0.01) { cam.fov = this.fov; cam.updateProjectionMatrix(); }
  }
}
