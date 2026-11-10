// Falling snow: flakes in a box that travels with the camera, each drifting down with its own speed and sway. The box
// wraps round, so there is always snow round the viewer, whether on the street or flying over the roofs.
import * as THREE from 'three';

const VERT = /* glsl */ `
  attribute vec4 seed;
  uniform float uTime; uniform vec3 uCam; uniform float uBox; uniform float uScale;
  varying float vA;
  void main() {
    vec3 p = seed.xyz * uBox;
    p.y -= uTime * (0.9 + seed.w * 0.9);
    p.x += sin(uTime * 0.6 + seed.w * 40.0) * 0.8;
    p.z += cos(uTime * 0.5 + seed.w * 23.0) * 0.8;
    p = mod(p - uCam + 0.5 * uBox, uBox) + uCam - 0.5 * uBox;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    float d = -mv.z;
    gl_PointSize = clamp(uScale * (0.05 + 0.04 * seed.w) / max(d, 0.1), 1.0, 14.0);
    vA = smoothstep(uBox * 0.5, uBox * 0.3, d) * smoothstep(0.2, 1.5, d);
    gl_Position = projectionMatrix * mv;
  }`;
const FRAG = /* glsl */ `
  uniform float uOpacity;
  varying float vA;
  void main() {
    vec2 c = gl_PointCoord - 0.5;
    float a = smoothstep(0.5, 0.15, length(c)) * vA * uOpacity;
    if (a < 0.01) discard;
    gl_FragColor = vec4(vec3(0.95, 0.97, 1.0), a);
  }`;

export class Snow {
  readonly points: THREE.Points;
  private readonly u = { uTime: { value: 0 }, uCam: { value: new THREE.Vector3() }, uBox: { value: 120 }, uScale: { value: 800 },
    uOpacity: { value: 0 } };
  level = 0;      // 0 .. 1, eased towards `on`
  on = false;

  constructor(scene: THREE.Scene, n = 24000) {
    const seed = new Float32Array(n * 4);
    for (let i = 0; i < seed.length; i++) seed[i] = Math.random();
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('seed', new THREE.BufferAttribute(seed, 4));
    const m = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: this.u, transparent: true,
      depthWrite: false, fog: false });
    this.points = new THREE.Points(g, m);
    this.points.frustumCulled = false;
    this.points.visible = false;
    scene.add(this.points);
  }

  update(dt: number, camera: THREE.PerspectiveCamera, heightPx: number) {
    this.level = THREE.MathUtils.clamp(this.level + (this.on ? dt / 6 : -dt / 3), 0, 1);
    this.points.visible = this.level > 0.001;
    this.u.uTime.value += dt;
    this.u.uCam.value.copy(camera.position);
    this.u.uScale.value = heightPx / (2 * Math.tan((camera.fov * Math.PI) / 360));
    this.u.uOpacity.value = Math.min(1, this.level * 1.5);
  }
}
