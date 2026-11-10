// Falling rain: drops in a box that travels with the camera, as the snow's flakes do, each drawn as a line from where
// it is to where it was a moment ago, so perspective slants and stretches the streaks. After warsaw-vibe-voxel's
// weather.ts (MIT, © 2026 Piotr Migdał).
import * as THREE from 'three';
import { clamp } from '../util';

const VERT = /* glsl */ `
  attribute vec4 seed; attribute float tail;
  uniform float uTime; uniform vec3 uCam; uniform float uBox;
  varying float vA;
  void main() {
    vec3 vel = vec3(1.2, -8.5 - 2.5 * seed.w, 0.4);  // metres a second, with a little wind
    vec3 p = seed.xyz * uBox + vel * uTime;
    p = mod(p - uCam + 0.5 * uBox, uBox) + uCam - 0.5 * uBox;
    p -= vel * 0.07 * tail;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    float d = -mv.z;
    vA = smoothstep(uBox * 0.5, uBox * 0.2, d) * smoothstep(0.8, 3.0, d) * (1.0 - 0.75 * tail);
    gl_Position = projectionMatrix * mv;
  }`;
const FRAG = /* glsl */ `
  uniform vec3 uCol; uniform float uOpacity;
  varying float vA;
  void main() { gl_FragColor = vec4(uCol, vA * uOpacity); }`;

export class Rain {
  readonly lines: THREE.LineSegments;
  private readonly u = { uTime: { value: 0 }, uCam: { value: new THREE.Vector3() }, uBox: { value: 70 }, uCol: { value: new THREE.Color() },
    uOpacity: { value: 0.42 } };
  level = 0;      // 0 .. 1, eased towards `on`
  on = false;

  constructor(scene: THREE.Scene, private readonly n: number) {
    const seed = new Float32Array(n * 8), tail = new Float32Array(n * 2);
    for (let i = 0; i < n; i++) {
      const s = [Math.random(), Math.random(), Math.random(), Math.random()];
      seed.set(s, i * 8);
      seed.set(s, i * 8 + 4);
      tail[i * 2 + 1] = 1;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 6), 3));
    g.setAttribute('seed', new THREE.BufferAttribute(seed, 4));
    g.setAttribute('tail', new THREE.BufferAttribute(tail, 1));
    const m = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: this.u, transparent: true,
      depthWrite: false, fog: false });
    this.lines = new THREE.LineSegments(g, m);
    this.lines.frustumCulled = false;
    this.lines.visible = false;
    scene.add(this.lines);
  }

  // share: the part of the drops to draw (fewer on small screens)
  update(dt: number, camera: THREE.Camera, night: number, share: number) {
    this.level = clamp(this.level + (this.on ? dt / 2.5 : -dt / 2), 0, 1);
    const n = Math.round(this.n * share * this.level);
    this.lines.visible = n > 0;
    this.lines.geometry.setDrawRange(0, 2 * n);
    this.u.uTime.value += dt;
    this.u.uCam.value.copy(camera.position);
    this.u.uCol.value.setRGB(0.78, 0.82, 0.88).multiplyScalar(1 - 0.7 * night);
  }
}
