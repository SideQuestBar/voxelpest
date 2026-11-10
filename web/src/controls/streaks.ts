// Speed streaks: faint lines in the air round the vehicle, still in the world, each drawn as the trail a point leaves
// on a moving camera's picture in a moment's exposure, so they flow past and stretch with speed. Only towards the
// screen's edges and above 45 km/h or so; one draw call, all on the GPU (the box wraps round the camera, as the rain's).
// Each is a thin quad two CSS pixels wide at its head, tapering to its tail, so that it shows on any pixel ratio.
import * as THREE from 'three';
import { smoothstep } from '../util';

const VERT = /* glsl */ `
  attribute vec4 seed; attribute vec2 corner;   // x: 0 at the head, 1 at the tail; y: the side, -1 or 1
  uniform vec3 uCentre; uniform vec3 uBox; uniform vec3 uTrail; uniform vec2 uPx;
  varying float vA;
  void main() {
    vec3 p = mod(seed.xyz * uBox - uCentre + 0.5 * uBox, uBox) + uCentre - 0.5 * uBox;
    vec4 a = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
    vec4 b = projectionMatrix * modelViewMatrix * vec4(p + uTrail * (0.4 + 0.6 * seed.w), 1.0);
    vec4 c = mix(a, b, corner.x);
    vec2 s = (b.xy / max(b.w, 0.01) - a.xy / max(a.w, 0.01)) / uPx;
    vec2 n = normalize(vec2(-s.y, s.x) + vec2(1e-5, 0.0));
    c.xy += n * uPx * corner.y * (1.0 - 0.7 * corner.x) * max(c.w, 0.0);
    vec2 ndc = c.xy / max(c.w, 0.01) * vec2(uPx.y / uPx.x, 1.0);
    vA = smoothstep(0.55, 1.15, length(ndc)) * smoothstep(1.5, 4.0, c.w) * smoothstep(0.5 * uBox.x, 0.2 * uBox.x, c.w) * (1.0 - corner.x);
    gl_Position = c;
  }`;
const FRAG = /* glsl */ `
  uniform vec3 uCol; uniform float uOpacity;
  varying float vA;
  void main() { gl_FragColor = vec4(uCol, vA * uOpacity); }`;

export class Streaks {
  readonly mesh: THREE.Mesh;
  private readonly u = { uCentre: { value: new THREE.Vector3() }, uBox: { value: new THREE.Vector3(44, 4.5, 44) },
    uTrail: { value: new THREE.Vector3() }, uPx: { value: new THREE.Vector2(0.002, 0.002) }, uCol: { value: new THREE.Color() },
    uOpacity: { value: 0 } };

  // dom: the canvas, for the width in CSS pixels
  constructor(scene: THREE.Scene, n: number, private readonly dom: HTMLElement) {
    const seed = new Float32Array(n * 16), corner = new Float32Array(n * 8), index: number[] = [];
    for (let i = 0; i < n; i++) {
      const s = [Math.random(), Math.random(), Math.random(), Math.random()];
      for (let k = 0; k < 4; k++) {
        seed.set(s, (i * 4 + k) * 4);
        corner.set([k >> 1, k & 1 ? 1 : -1], (i * 4 + k) * 2);
      }
      index.push(i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 2, i * 4 + 1, i * 4 + 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 12), 3));
    g.setAttribute('seed', new THREE.BufferAttribute(seed, 4));
    g.setAttribute('corner', new THREE.BufferAttribute(corner, 2));
    g.setIndex(index);
    const m = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: this.u, transparent: true, depthWrite: false,
      side: THREE.DoubleSide });
    this.mesh = new THREE.Mesh(g, m);
    this.mesh.frustumCulled = false;
    this.mesh.visible = false;
    scene.add(this.mesh);
  }

  // where the vehicle is and how it moves (m/s), the boost's share 0..1
  update(camera: THREE.PerspectiveCamera, pos: THREE.Vector3, vel: THREE.Vector3, over: number, night: number) {
    const s = vel.length(), o = smoothstep(12, 30, s) * 0.42 + over * 0.15;
    this.u.uOpacity.value = o * (1 - 0.55 * night);
    this.mesh.visible = o > 0.005;
    if (!this.mesh.visible) return;
    this.u.uCentre.value.set(camera.position.x, pos.y + 1.7, camera.position.z);
    this.u.uTrail.value.copy(vel).multiplyScalar(0.09);
    this.u.uPx.value.set(2 / Math.max(this.dom.clientWidth, 1), 2 / Math.max(this.dom.clientHeight, 1));
    this.u.uCol.value.setRGB(0.93, 0.95, 0.98);
  }
}
