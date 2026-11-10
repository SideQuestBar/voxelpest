// Walking: first person at eye height, the mouse to look (pointer lock), WASD to walk, Shift to run, Space to jump;
// on a controller the left stick walks (click it to run), the right stick looks, A jumps.
// The body is a 0.6 m wide, 1.8 m tall box against the voxels: steps up to 0.6 m are climbed (kerbs, stairs), walls
// stop you (sliding along them), gravity takes you down. Water carries you, slowly.
import * as THREE from 'three';
import type { World } from '../engine/world';
import { MAT } from '../meta';
import { clamp } from '../util';
import { PAD, type Input } from './input';

const EYE = 1.65, HEIGHT = 1.8, R = 0.3, STEP = 0.6, GRAVITY = 20, JUMP = 5.4;

export class Walker {
  readonly feet = new THREE.Vector3();
  yaw = 0;          // radians, 0 looking along +x
  pitch = 0;
  private vy = 0;
  private grounded = false;
  private eye = EYE;
  private readonly hv = new THREE.Vector2();
  swimming = false;
  private sprint = false;
  locked = false;

  constructor(private readonly camera: THREE.PerspectiveCamera, private readonly world: World, private readonly input: Input,
    private readonly dom: HTMLElement) {
    document.addEventListener('pointerlockchange', () => { this.locked = document.pointerLockElement === dom; });
    document.addEventListener('mousemove', (e) => {
      if (!this.locked) return;
      this.yaw += e.movementX * 0.0022;
      this.pitch = clamp(this.pitch - e.movementY * 0.0022, -1.45, 1.45);
    });
    input.onJump = () => this.jump();
  }

  lock() { if (!this.locked) this.dom.requestPointerLock?.(); }
  unlock() { if (this.locked) document.exitPointerLock?.(); }

  place(x: number, y: number, z: number, yaw: number) {
    this.feet.set(x, y, z);
    this.yaw = yaw;
    this.pitch = -0.05;
    this.vy = 0;
    this.eye = EYE;
  }

  private jump() { if (this.grounded) { this.vy = JUMP; this.grounded = false; } }

  // the highest floor under the body's footprint, up to a step above the feet
  private floorAt(x: number, z: number, y: number) {
    let top = -Infinity, mat: number = MAT.SOIL;
    for (const [dx, dz] of [[-R, -R], [R, -R], [-R, R], [R, R], [0, 0]]) {
      const f = this.world.floor(x + dx, z + dz, y, STEP);
      if (!f) return null;
      if (f.top > top) { top = f.top; mat = f.mat; }
    }
    return { top, mat };
  }

  private free(x: number, z: number, y: number) {
    for (const [dx, dz] of [[-R, -R], [R, -R], [-R, R], [R, R]]) {
      const b = this.world.blocked(x + dx, z + dz, y + STEP + 0.01, y + HEIGHT);
      if (b !== false) return false;
    }
    return true;
  }

  update(dt: number) {
    const i = this.input;
    const pad = i.pad;
    if (i.has('Space') || i.pressed(PAD.A)) this.jump();
    const look = i.takeLook();
    this.yaw += look.dx * 0.006 + pad.rx * Math.abs(pad.rx) * 2.8 * dt;
    this.pitch = clamp(this.pitch - look.dy * 0.006 - pad.ry * Math.abs(pad.ry) * 2.0 * dt, -1.45, 1.45);
    const { fwd, side } = i.move();
    if (i.pressed(PAD.LS) || i.pressed(PAD.LB)) this.sprint = true;
    if (Math.hypot(pad.lx, pad.ly) < 0.2) this.sprint = false;
    const run = i.has('ShiftLeft', 'ShiftRight') || Math.hypot(i.stick.x, i.stick.y) > 0.95 || this.sprint;
    const speed = (this.swimming ? 1.6 : run ? 10 : 4.2);
    const c = Math.cos(this.yaw), s = Math.sin(this.yaw);
    const want = new THREE.Vector2(c * fwd - s * side, s * fwd + c * side);
    if (want.lengthSq() > 1) want.normalize();
    want.multiplyScalar(speed);
    this.hv.lerp(want, 1 - Math.exp(-dt * (this.grounded ? 12 : 3)));
    const f = this.feet;
    // move one axis at a time, so a wall stops one and you slide along it
    for (const axis of ['x', 'z'] as const) {
      const d = (axis === 'x' ? this.hv.x : this.hv.y) * dt;
      if (Math.abs(d) < 1e-5) continue;
      const nx = axis === 'x' ? f.x + d : f.x, nz = axis === 'z' ? f.z + d : f.z;
      if (this.free(nx, nz, f.y)) { f.x = nx; f.z = nz; }
      else if (axis === 'x') this.hv.x = 0;
      else this.hv.y = 0;
    }
    const fl = this.floorAt(f.x, f.z, f.y);
    if (fl) {
      this.vy -= GRAVITY * dt;
      f.y += this.vy * dt;
      if (f.y <= fl.top) {
        const up = fl.top - f.y;
        if (up > 0.05 && up <= STEP + 0.05 && this.grounded) this.eye -= up;  // ease the eye up a step
        f.y = fl.top;
        this.vy = Math.max(this.vy, 0);
        this.grounded = true;
      } else this.grounded = f.y - fl.top < 0.05;
      this.swimming = fl.mat === MAT.WATER && this.grounded;
    }
    this.eye += (EYE - this.eye) * (1 - Math.exp(-dt * 10));
    const cp = Math.cos(this.pitch);
    this.camera.position.set(f.x, f.y + this.eye - (this.swimming ? 1.1 : 0), f.z);
    this.camera.lookAt(f.x + Math.cos(this.yaw) * cp, f.y + this.eye - (this.swimming ? 1.1 : 0) + Math.sin(this.pitch), f.z + Math.sin(this.yaw) * cp);
  }
}
