// The FPV drone's picture as its pilot sees it: an analogue 5.8 GHz video feed. The scene is drawn small (about 576
// lines) and put on the screen through a pass that adds the feed's look: grain, colour bleeding to the right of the
// brightness, faint scan lines, a dark rim from the wide lens and a slow interference band. As the link weakens
// (`breakup`, 0..1) lines tear sideways, snow comes through, the colour goes and whole lines drop out.
import * as THREE from 'three';

const FRAG = /* glsl */ `
  uniform sampler2D tMap; uniform float uTime; uniform float uBreak; uniform float uGrain;
  varying vec2 vUv;
  float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
  vec3 tex(vec2 uv) {
    vec3 c = texture2D(tMap, uv).rgb;
  #ifdef TONE_MAPPING
    c = toneMapping(c);
  #endif
    return c;
  }
  void main() {
    vec2 uv = vUv;
    float field = floor(uTime * 60.0);
    float line = floor(uv.y * 288.0);
    float r1 = h(vec2(line * 0.37, field)), r2 = h(vec2(floor(line / 7.0), field * 1.7)), r3 = h(vec2(floor(line / 23.0), floor(field / 3.0)));
    float tear = step(1.0 - uBreak * 0.55, r2) + step(1.0 - uBreak * 0.3, r3);
    uv.x += (r1 - 0.5) * 0.0015 + (r1 - 0.5) * 0.035 * uBreak * tear + (r3 - 0.5) * 0.02 * uBreak * step(0.5, uBreak);
    float bleed = 0.0022 + 0.006 * uBreak;
    vec3 c = tex(uv);
    vec3 cc = 0.5 * (tex(uv + vec2(bleed, 0.0)) + tex(uv + vec2(bleed * 2.0, 0.0)));
    const vec3 L = vec3(0.299, 0.587, 0.114);
    float y = dot(c, L);
    vec3 col = vec3(y) + (cc - vec3(dot(cc, L))) * (1.0 - 0.8 * uBreak);
    col = mix(col, vec3(y), 0.12);
    // snow through the picture, heavier in the torn bands; now and then a whole line drops out
    float snow = h(gl_FragCoord.xy * 0.71 + vec2(field * 3.1, field * 1.3));
    col = mix(col, vec3(snow), clamp(pow(uBreak, 1.5) * (0.3 + 0.55 * tear), 0.0, 0.85));
    float drop = h(vec2(line * 1.3, field * 2.9));
    if (drop > 1.0 - uBreak * uBreak * 0.05) col = vec3(step(0.5, h(vec2(line, field))) * 0.85 + 0.05);
    // the interference band rolling up, the scan lines, the lens's dark rim
    float roll = fract(vUv.y - uTime * 0.11);
    col *= 1.0 + 0.06 * exp(-pow((roll - 0.5) * 18.0, 2.0)) - 0.03;
    col *= 0.95 + 0.05 * cos(vUv.y * 288.0 * 6.2832);
    vec2 d = vUv - 0.5;
    col *= 1.0 - 0.45 * pow(clamp(length(d * vec2(1.15, 1.0)) * 1.35, 0.0, 1.0), 2.6);
    gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
  #include <colorspace_fragment>
    gl_FragColor.rgb += (h(gl_FragCoord.xy + fract(uTime) * 97.0) - 0.5) * uGrain;
  }`;

export class Feed {
  private readonly rt = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, depthBuffer: true });
  private readonly cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private readonly scene = new THREE.Scene();
  private readonly size = new THREE.Vector2();
  private readonly u = { tMap: { value: this.rt.texture }, uTime: { value: 0 }, uBreak: { value: 0 }, uGrain: { value: 0.07 } };

  constructor() {
    const m = new THREE.ShaderMaterial({ uniforms: this.u, fragmentShader: FRAG, depthTest: false, depthWrite: false,
      vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }' });
    const q = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), m);
    q.frustumCulled = false;
    this.scene.add(q);
  }

  render(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera, time: number, breakup: number) {
    renderer.getDrawingBufferSize(this.size);
    const k = Math.min(1, 576 / Math.max(this.size.y, 1));
    const w = Math.max(1, Math.round(this.size.x * k)), h = Math.max(1, Math.round(this.size.y * k));
    if (this.rt.width !== w || this.rt.height !== h) this.rt.setSize(w, h);
    this.u.uTime.value = time;
    this.u.uBreak.value = breakup;
    this.u.uGrain.value = 0.06 + 0.1 * breakup;
    renderer.setRenderTarget(this.rt);
    renderer.render(scene, camera);
    renderer.setRenderTarget(null);
    renderer.render(this.scene, this.cam);
  }

  dispose() { this.rt.dispose(); }
}
