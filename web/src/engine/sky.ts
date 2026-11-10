// Light and sky for an hour of the day: the sun's real position over Budapest on the chosen date, the sky's colours
// from its height (day, golden hour, dusk, night with stars and a moon), the sunlight with shadows that follow the
// camera, a hemisphere light for the sky's own light, and haze. Clouds and rain (engine/weather.ts) bring a cloud deck,
// a grey sky lit orange by the city at night, soft weak shadows and thicker haze; snow turns it all overcast.
import * as THREE from 'three';
import type { Meta } from '../meta';
import { budapestDay, dateOf } from '../season';
import { budapestOffset, clamp, smoothstep } from '../util';
import type { Look } from './material';
import type { Weather } from './weather';

type Levels = Weather['levels'];

const LAT = 47.497, LON = 19.054;
const rad = Math.PI / 180;

// the sun's azimuth (from north, clockwise) and elevation, in radians, at a UTC instant (a low-precision solar
// ephemeris, good to a fraction of a degree)
export function sunAt(t: Date) {
  const d = t.getTime() / 86400000 - 10957.5;  // days since J2000.0
  const g = (357.529 + 0.98560028 * d) * rad, q = 280.459 + 0.98564736 * d;
  const L = (q + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * rad, e = (23.439 - 0.00000036 * d) * rad;
  const ra = Math.atan2(Math.cos(e) * Math.sin(L), Math.cos(L)), dec = Math.asin(Math.sin(e) * Math.sin(L));
  const gmst = (18.697374558 + 24.06570982441908 * d) % 24;
  const H = (gmst * 15 + LON) * rad - ra, la = LAT * rad;
  const el = Math.asin(Math.sin(la) * Math.sin(dec) + Math.cos(la) * Math.cos(dec) * Math.cos(H));
  const az = Math.atan2(-Math.sin(H), Math.tan(dec) * Math.cos(la) - Math.sin(la) * Math.cos(H));
  return { az, el };
}

// an hour on Budapest's clock on a day of Budapest's year (its today unless given: not the browser's, it may be
// tomorrow there), as a UTC instant
export function instant(hour: number, day = budapestDay()) {
  const b = dateOf(day), y = b.getUTCFullYear(), m = b.getUTCMonth(), d = b.getUTCDate();
  return new Date(Date.UTC(y, m, d) + (hour - budapestOffset(new Date(Date.UTC(y, m, d, 12)))) * 3600e3);
}

const C = (r: number, g: number, b: number) => new THREE.Color(r, g, b);
const UP = new THREE.Vector3(0, 1, 0);
const mix = (a: THREE.Color, b: THREE.Color, t: number) => a.clone().lerp(b, clamp(t, 0, 1));

const SKY_VERT = /* glsl */ `
  varying vec3 vDir;
  void main() {
    vDir = normalize((modelMatrix * vec4(position, 1.0)).xyz - cameraPosition);
    vec4 p = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0);
    gl_Position = p.xyww;
  }`;
const SKY_FRAG = /* glsl */ `
  uniform vec3 uZenith; uniform vec3 uHorizon; uniform vec3 uSun; uniform vec3 uSunCol; uniform float uNight; uniform vec3 uMoon;
  uniform float uOvercast; uniform float uCloud; uniform float uCover; uniform vec3 uCloudLit; uniform vec3 uCloudDark; uniform float uTime;
  varying vec3 vDir;
  float hash(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
  // the cloud deck's noise, after warsaw-vibe-voxel's sky.ts (MIT, © 2026 Piotr Migdał)
  float h2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
    return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y);
  }
  float fbm(vec2 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++) { s += a * noise(p); p = p * 2.03 + 3.1; a *= 0.5; } return s; }
  void main() {
    vec3 d = normalize(vDir);
    float t = max(d.y, 0.0);
    vec3 c = mix(uHorizon, uZenith, pow(t, 0.55));
    if (d.y < 0.0) c = uHorizon * (1.0 - 0.25 * smoothstep(0.0, -0.3, d.y));
    float s = max(dot(d, uSun), 0.0);
    c += uSunCol * (pow(s, 8.0) * 0.25 + pow(s, 120.0) * 0.6) * (1.0 - uOvercast * 0.8);
    c += uSunCol * smoothstep(0.9993, 0.9996, s) * 6.0 * (1.0 - uOvercast);
    if (uNight > 0.0 && d.y > 0.0) {
      vec3 g = floor(d * 300.0);
      float h = hash(g);
      float star = step(0.9985, h) * smoothstep(0.0, 0.25, d.y) * (0.5 + 0.5 * sin(h * 900.0));
      c += vec3(0.85, 0.9, 1.0) * star * uNight * (1.0 - uOvercast);
      float m = dot(d, uMoon);
      c += vec3(0.9, 0.92, 0.85) * smoothstep(0.99955, 0.9997, m) * uNight * (1.0 - uOvercast * 0.7);
      c += vec3(0.25, 0.3, 0.4) * pow(max(m, 0.0), 40.0) * 0.15 * uNight;
    }
    if (uCloud > 0.0) {
      // a deck seen from below, flattened towards the horizon, drifting with the wind; thicker parts darker, the sun
      // glowing through the thin ones
      vec2 uv = d.xz / (t + 0.12) * 1.3 + vec2(0.006, 0.0025) * uTime;
      float f = fbm(uv);
      float cov = smoothstep(0.62 - 0.5 * uCover, 0.8 - 0.42 * uCover, f);
      cov = mix(cov, 1.0, smoothstep(0.3, 0.0, t)) * smoothstep(-0.03, 0.03, d.y);
      vec3 cl = mix(uCloudLit, uCloudDark, smoothstep(0.35, 0.85, f));
      cl += uSunCol * (pow(s, 6.0) * 0.22 + pow(s, 60.0) * 0.25) * (1.0 - smoothstep(0.3, 0.75, f)) * (1.0 - uNight);
      cl = mix(cl, uHorizon, smoothstep(0.18, 0.0, t) * 0.75);
      c = mix(c, cl, cov * uCloud);
    }
    gl_FragColor = vec4(c, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

export class Sky {
  readonly sun = new THREE.DirectionalLight(0xffffff, 3);
  readonly moon = new THREE.DirectionalLight(0x9db4ff, 0);
  readonly hemi = new THREE.HemisphereLight(0xbfd4ea, 0x6b6150, 1);
  readonly dome: THREE.Mesh;
  readonly sunDir = new THREE.Vector3(0, 1, 0);
  private readonly lightDir = new THREE.Vector3(0, 1, 0);  // the sun's, drawn towards the zenith under clouds
  night = 0;
  day = budapestDay();  // the day of the year whose sun this is
  private readonly u;
  private readonly east: THREE.Vector2;
  private readonly north: THREE.Vector2;
  private shadowR = 400;

  constructor(private readonly scene: THREE.Scene, private readonly look: Look, meta: Meta, shadowSize: number) {
    const th = meta.theta_deg * rad;
    this.east = new THREE.Vector2(Math.cos(th), Math.sin(th));
    this.north = new THREE.Vector2(Math.sin(th), -Math.cos(th));
    this.u = {
      uZenith: { value: C(0.2, 0.4, 0.75) }, uHorizon: { value: C(0.7, 0.8, 0.9) }, uSun: { value: new THREE.Vector3(0, 1, 0) },
      uSunCol: { value: C(1, 0.9, 0.7) }, uNight: { value: 0 }, uMoon: { value: this.dir(140 * rad, 35 * rad) }, uOvercast: { value: 0 },
      uCloud: { value: 0 }, uCover: { value: 0 }, uCloudLit: { value: C(1, 1, 1) }, uCloudDark: { value: C(0.5, 0.5, 0.5) }, uTime: { value: 0 },
    };
    const mat = new THREE.ShaderMaterial({ vertexShader: SKY_VERT, fragmentShader: SKY_FRAG, uniforms: this.u, side: THREE.BackSide,
      depthWrite: false, fog: false });
    this.dome = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 24), mat);
    this.dome.frustumCulled = false;
    this.dome.renderOrder = -1;
    this.dome.scale.setScalar(20000);
    scene.add(this.dome, this.sun, this.sun.target, this.moon, this.moon.target, this.hemi);
    this.sun.castShadow = true;
    const sh = this.sun.shadow;
    sh.mapSize.set(shadowSize, shadowSize);
    sh.bias = -0.0004;
    sh.normalBias = 0.35;
    sh.camera.near = 10;
    sh.camera.far = 6000;
    scene.fog = new THREE.FogExp2(0xc9d3dc, 0.0001);
  }

  // a direction in the scene from azimuth (from north, clockwise) and elevation
  dir(az: number, el: number) {
    const h = this.east.clone().multiplyScalar(Math.sin(az)).add(this.north.clone().multiplyScalar(Math.cos(az))).multiplyScalar(Math.cos(el));
    return new THREE.Vector3(h.x, Math.sin(el), h.y).normalize();
  }

  // w: engine/weather.ts's levels
  set(hour: number, w: Levels, renderer: THREE.WebGLRenderer) {
    const { cloud, rain, snow } = w;
    const { az, el } = sunAt(instant(hour, this.day));
    const deg = el / rad;
    this.sunDir.copy(this.dir(az, el));
    const day = smoothstep(-4, 8, deg), gold = smoothstep(18, 2, deg) * smoothstep(-6, 1, deg), night = smoothstep(-2, -12, deg);
    this.night = night;
    let zen = mix(mix(C(0.05, 0.09, 0.2), C(0.16, 0.34, 0.7), day), C(0.008, 0.012, 0.03), night);
    let hor = mix(mix(C(0.52, 0.66, 0.82), C(0.98, 0.66, 0.42), gold), C(0.03, 0.045, 0.08), night);
    if (deg < 0 && deg > -10) hor = mix(hor, C(0.55, 0.38, 0.42), smoothstep(-10, -3, deg) * smoothstep(1, -3, deg) * 0.6);
    const grey = mix(C(0.66, 0.68, 0.71), C(0.05, 0.05, 0.06), night);
    zen = mix(zen, grey.clone().multiplyScalar(0.9), snow * 0.85);
    hor = mix(hor, grey, snow * 0.85);
    // under the cloud deck: grey by day, darker in the rain, the city's sodium orange from below at night
    const deck = mix(mix(C(0.6, 0.62, 0.65), C(0.42, 0.44, 0.47), rain).multiplyScalar(0.35 + 0.65 * day), C(0.066, 0.05, 0.038), night);
    zen = mix(zen, deck.clone().multiplyScalar(0.82), cloud * (0.55 + 0.45 * rain));
    hor = mix(hor, deck, cloud * 0.85);
    const lit = mix(mix(C(1, 1, 1), C(0.8, 0.82, 0.85), cloud), C(0.62, 0.64, 0.67), rain).multiplyScalar(0.3 + 0.7 * day);
    const dark = mix(mix(C(0.7, 0.74, 0.8), C(0.5, 0.52, 0.56), cloud), C(0.33, 0.35, 0.38), rain).multiplyScalar(0.3 + 0.7 * day);
    this.u.uCloudLit.value.copy(mix(lit, C(0.08, 0.061, 0.047), night));
    this.u.uCloudDark.value.copy(mix(dark, C(0.034, 0.03, 0.027), night));
    this.u.uCloud.value = w.deck; this.u.uCover.value = w.cover; this.u.uTime.value = this.look.time.value;
    const sunCol = mix(C(1, 0.96, 0.9), C(1, 0.62, 0.32), gold * (1 - 0.6 * cloud));
    Object.assign(this.u.uZenith.value, zen); Object.assign(this.u.uHorizon.value, hor);
    this.u.uSun.value.copy(this.sunDir); this.u.uSunCol.value.copy(sunCol);
    this.u.uNight.value = night; this.u.uOvercast.value = Math.max(snow, cloud);
    // clouds: weaker, softer light from higher up, so short faint shadows
    this.sun.color.copy(sunCol);
    this.sun.intensity = 3.4 * day * (1 - 0.75 * snow) * (1 - 0.35 * gold) * (1 - 0.72 * cloud - 0.13 * rain);
    this.sun.visible = this.sun.intensity > 0.01;
    this.sun.shadow.intensity = 1 - 0.6 * cloud - 0.25 * rain;
    this.sun.shadow.radius = 1 + 2.5 * cloud;
    this.lightDir.copy(this.sunDir).lerp(UP, 0.45 * cloud).normalize();
    this.moon.intensity = 0.35 * night * (1 - 0.6 * snow) * (1 - 0.75 * cloud);
    this.hemi.color.copy(mix(zen.clone().lerp(hor, 0.5), C(0.7, 0.72, 0.75), snow * 0.5));
    this.hemi.groundColor.copy(mix(C(0.42, 0.38, 0.32), C(0.03, 0.03, 0.04), night));
    this.hemi.intensity = (0.3 + 1.1 * day) * (1 + 0.45 * snow) * (1 + 0.4 * cloud);
    (this.scene.fog as THREE.FogExp2).color.copy(hor);
    (this.scene.fog as THREE.FogExp2).density = 0.00009 + 0.00028 * snow + 0.00006 * cloud + 0.00026 * rain;
    renderer.toneMappingExposure = 1.0 + 0.5 * night;
    this.look.night.value = night;
    this.look.sky.value.copy(hor.clone().lerp(zen, 0.3));
    const h = ((hour % 24) + 24) % 24;
    this.look.lit.value = h >= 17 || h < 1 ? 0.55 : h < 5 ? 0.14 : h < 9 ? 0.32 : 0.25;
  }

  // the shadows cover a square round what the camera looks at, wider the further away it is
  follow(target: THREE.Vector3, radius: number) {
    const r = clamp(radius, 60, 2200);
    if (Math.abs(r - this.shadowR) / this.shadowR > 0.15) this.shadowR = r;
    const R = this.shadowR, cam = this.sun.shadow.camera;
    if (cam.right !== R) {
      cam.left = -R; cam.right = R; cam.top = R; cam.bottom = -R;
      cam.updateProjectionMatrix();
    }
    const texel = (2 * R) / this.sun.shadow.mapSize.x;
    const t = target.clone();
    t.x = Math.round(t.x / texel) * texel; t.z = Math.round(t.z / texel) * texel;
    const light = this.lightDir.y > 0.02 ? this.lightDir : UP;
    this.sun.target.position.copy(t);
    this.sun.position.copy(t).addScaledVector(light, 3000);
    this.moon.target.position.copy(t);
    this.moon.position.copy(t).addScaledVector(this.u.uMoon.value, 3000);
  }
}
