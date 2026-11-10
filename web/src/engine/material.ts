// The voxels' look: one MeshStandardMaterial whose shader reads each face's palette entry (colour + material id) and
// draws the material's detail procedurally, in 0.5 m voxel steps so it stays blocky: windows and shop fronts on the
// plain OSM walls (their rhythm varies with the wall colour), curtain walls, water, lamps, lit windows at night, the
// street lamps' pools of light, snow on everything that faces up, and wet streets and roofs in the rain. Through the
// year (engine/foliage.ts fills `look.season`): lawns by month, and where the map has foliage.bin (FOLIAGE), trees
// that leaf out light green, turn their class's autumn colour, drop their leaves onto the ground under them and stand
// bare (twigs, and the branches the build draws inside the crowns) in winter.
import * as THREE from 'three';
import { MAT, type Meta } from '../meta';

export interface Look {
  night: THREE.IUniform<number>;  // 0 day .. 1 night
  lit: THREE.IUniform<number>;    // share of windows lit
  snow: THREE.IUniform<number>;   // 0 .. 1 cover
  wet: THREE.IUniform<number>;    // 0 .. 1 rain on the ground
  time: THREE.IUniform<number>;
  sky: THREE.IUniform<THREE.Color>;
  season: Season;
}

export const CLASSES = 16;  // FOLIAGE-CONTRACT: 0 none, 1-13 deciduous, 14 conifers, 15 plane

// the trees and lawns through the year, filled by engine/foliage.ts
export interface Season {
  day: THREE.IUniform<number>;                // day of the year
  on: THREE.IUniform<number>;                 // 1 once foliage.bin and phenology.json are in
  map: THREE.IUniform<THREE.Texture>;         // per 2 m cell: class, per-tree byte (RG)
  date: THREE.IUniform<THREE.Vector4[]>;      // per class: leaf-out, colouring, fall (days), spread; x < 0 evergreen
  col: THREE.IUniform<THREE.Color[]>;         // per class: autumn colour
  grass: THREE.IUniform<THREE.Color[]>;       // per month: a factor on the lawns' green
  leaf: THREE.IUniform<THREE.Color>;          // a factor on summer leaves
}

function paletteTexture(meta: Meta) {
  const data = new Uint8Array(64 * 64 * 4);
  meta.palette.forEach((p, i) => data.set(p, i * 4));
  const t = new THREE.DataTexture(data, 64, 64, THREE.RGBAFormat);
  t.magFilter = t.minFilter = THREE.NearestFilter;
  t.needsUpdate = true;
  return t;
}

// the street lamps' light on the ground: a soft warm pool round each lamp, 1 / k metres per texel
function lampTexture(meta: Meta, k: number) {
  const W = Math.ceil(meta.W * meta.vox * k), D = Math.ceil(meta.D * meta.vox * k);
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = D;
  const g = cv.getContext('2d')!;
  g.fillStyle = '#000';
  g.fillRect(0, 0, W, D);
  g.globalCompositeOperation = 'lighter';
  const r = 16 * k;
  const grad = g.createRadialGradient(0, 0, 0, 0, 0, r);
  grad.addColorStop(0, 'rgba(255,214,160,0.7)');
  grad.addColorStop(0.35, 'rgba(255,205,150,0.28)');
  grad.addColorStop(1, 'rgba(255,200,140,0)');
  g.fillStyle = grad;
  for (const [x, y] of meta.lamps) {
    g.setTransform(1, 0, 0, 1, x * k, y * k);
    g.fillRect(-r, -r, 2 * r, 2 * r);
  }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.NoColorSpace;
  t.flipY = false;
  return t;
}

const VERT_PARS = /* glsl */ `
  attribute vec4 va; attribute float vp;
  varying vec3 vW; varying float vAo; varying float vGround; flat varying int vPal; flat varying int vFace; flat varying float vS;
  vec3 faceNormal(int f) {
    if (f == 0) return vec3(-1., 0., 0.); if (f == 1) return vec3(1., 0., 0.);
    if (f == 2) return vec3(0., 0., -1.); if (f == 3) return vec3(0., 0., 1.);
    if (f == 4) return vec3(0., -1., 0.); return vec3(0., 1., 0.);
  }`;

// The seasons, after warsaw-vibe-voxel's voxelMaterial.ts (MIT, © 2026 Piotr Migdał). foliageAt: a crown cell on
// uDay: x in leaf (0 bare .. 1), y turned (0 green .. 1 autumn colour), z fresh (spring's light green, 1 .. 0), w the
// class (0: no tree's crown); each tree on its own date within its class's spread (the per-tree byte). leafGone: a
// bare voxel drops out, but for a share of twigs, more of them in a far tile's coarse blocks.
const SEASON = /* glsl */ `
  uniform float uDay; uniform vec3 uGrass[12];
  // integer hashing: a sin() hash of the map's voxel coordinates (thousands) came out 0 for one voxel in six in
  // SwiftShader, and every one of those kept its leaves in January
  float ihash(vec3 p, uint salt) {
    uvec3 q = uvec3(ivec3(p) + 65536);
    uint h = q.x * 1597334677u ^ q.y * 3812015801u ^ q.z * 2798796415u ^ salt * 2246822519u;
    h = (h ^ (h >> 15)) * 2246822519u;
    h ^= h >> 13;
    return float(h >> 8) * (1.0 / 16777216.0);
  }
  vec3 grassTint() {
    float m = mod(uDay / 30.42 - 0.5, 12.0);
    int a = int(m);
    return mix(uGrass[a], uGrass[(a + 1) % 12], fract(m));
  }
  #ifdef FOLIAGE
  uniform float uFolOn; uniform sampler2D uFolMap; uniform vec4 uFolDate[${CLASSES}]; uniform vec3 uFolCol[${CLASSES}];
  uniform vec3 uLeafTint; uniform float uFolCell;
  vec4 foliageAt(vec3 cell) {
    ivec2 sz = textureSize(uFolMap, 0), c = ivec2(floor(cell.xz / uFolCell));
    vec2 f = texelFetch(uFolMap, clamp(c, ivec2(0), sz - 1), 0).rg;
    // a crown's edge spilling into the next cell is still that tree's
    for (int i = 0; i < 4 && f.r < 0.5 / 255.0; i++) f = texelFetch(uFolMap, clamp(c + ivec2(i == 0 ? 1 : i == 1 ? -1 : 0, i == 2 ? 1 : i == 3 ? -1 : 0), ivec2(0), sz - 1), 0).rg;
    int cls = int(f.r * 255.0 + 0.5);
    vec4 d = uFolDate[cls];
    if (cls == 0 || d.x < 0.0) return vec4(1.0, 0.0, 0.0, float(cls));
    float k = f.g * 255.0;
    float t = uDay - (fract(k * 0.618034) + fract(k * 0.414214 + 0.3) - 1.0) * 2.45 * d.w;
    float leaf = t < 200.0 ? smoothstep(d.x - 3.0, d.x + 14.0, t) : 1.0 - smoothstep(d.z - 8.0, d.z + 8.0, t);
    float fresh = t < 200.0 ? 1.0 - smoothstep(d.x + 6.0, d.x + 34.0, t) : 0.0;
    return vec4(leaf, smoothstep(d.y - 10.0, d.y + 10.0, t), fresh, float(cls));
  }
  bool leafGone(vec3 lc, float leaf, float s) {
    return ihash(lc, 1u) > leaf && ihash(lc, 2u) > mix(0.22, 0.5, smoothstep(1.5, 6.0, s));
  }
  float litter(vec4 fo) {
    int cls = int(fo.w);
    if (cls == 0 || uFolDate[cls].x < 0.0) return 0.0;
    return (1.0 - fo.x) * fo.y * (1.0 - smoothstep(uFolDate[cls].z + 15.0, uFolDate[cls].z + 50.0, uDay));
  }
  #endif`;

const FRAG_PARS = /* glsl */ `
  uniform sampler2D uPal; uniform sampler2D uLamps; uniform vec2 uMapSize; uniform float uVox;
  uniform float uNight; uniform float uLit; uniform float uSnow; uniform float uTime; uniform vec3 uSky;
  uniform float uWet;
  #ifdef FADE
  uniform float uFade;
  #endif
  varying vec3 vW; varying float vAo; varying float vGround; flat varying int vPal; flat varying int vFace; flat varying float vS;
  float hash2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float hash3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
  float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash2(i), hash2(i + vec2(1, 0)), f.x), mix(hash2(i + vec2(0, 1)), hash2(i + vec2(1, 1)), f.x), f.y);
  }
  ${SEASON}
  vec3 gEmit; float gRough; float gMetal;
  // a lit room: mostly warm, some cool white, a few blue screens
  vec3 room(float r) { return r < 0.62 ? vec3(1.0, 0.68, 0.36) : r < 0.9 ? vec3(1.0, 0.9, 0.75) : vec3(0.6, 0.75, 1.0); }
  // glass: dark, with the sky in it at a grazing angle
  vec3 glassCol(vec3 base, vec3 n, float k) {
    float f = 1.0 - clamp(dot(n, normalize(cameraPosition - vW)), 0.0, 1.0);
    gEmit += uSky * (0.03 + 0.16 * f * f * f) * k * (1.0 - uNight * 0.8);
    gRough = 0.12;
    return mix(base * 0.3, vec3(0.04, 0.05, 0.07), 0.6);
  }`;

const SURFACE = /* glsl */ `
  vec4 pe = texelFetch(uPal, ivec2(vPal % 64, vPal / 64), 0);
  vec3 base = pow(pe.rgb, vec3(2.2));
  int m = int(pe.a * 255.0 + 0.5);
  vec3 N = vFace == 0 ? vec3(-1., 0., 0.) : vFace == 1 ? vec3(1., 0., 0.) : vFace == 2 ? vec3(0., 0., -1.)
    : vFace == 3 ? vec3(0., 0., 1.) : vFace == 4 ? vec3(0., -1., 0.) : vec3(0., 1., 0.);
  vec3 cell = floor(vW / uVox - N * 0.5 + 1e-3);
  bool side = vFace < 4;
  float au = vFace < 2 ? cell.z : cell.x;       // voxels along a wall
  float lv = floor((vW.y - vGround) / uVox + 1e-3);  // voxels above the ground
  float n1 = hash3(cell);
  vec3 col = base * (0.95 + 0.1 * n1);
  gEmit = vec3(0.0); gRough = 0.86; gMetal = 0.0;
  float seed = hash2(vec2(float(vPal), 3.7));
  if (side && (m == ${MAT.WALL} || m == ${MAT.TENEMENT} || m == ${MAT.CONCRETE})) {
    // a facade from the wall colour: bay, storey and shop front sizes in voxels
    float bay = m == ${MAT.CONCRETE} ? 6.0 : 4.0 + floor(seed * 3.0);
    float st = m == ${MAT.TENEMENT} ? 8.0 : m == ${MAT.CONCRETE} ? 7.0 : 7.0 + floor(seed * 1.99);
    float gf = m == ${MAT.CONCRETE} ? 9.0 : 8.0 + floor(seed * 2.0);
    float u = mod(au, bay), z = mod(lv - gf, st);
    bool win, shop = lv < gf;
    if (shop) win = lv >= 1.0 && lv <= gf - 3.0 && mod(au, bay * 2.0) >= 1.0 && mod(au, bay * 2.0) < bay * 2.0 - 1.0;
    else if (m == ${MAT.CONCRETE}) win = z >= 2.0 && z < st - 1.0 && u < bay - 1.0;
    else win = u >= 1.0 && u < 3.0 && z >= 2.0 && z < st - 2.0;
    // far away the pattern would only shimmer: it fades into the facade's average
    float fade = smoothstep(0.22, 0.7, length(fwidth(vW)));
    vec3 wall = (!shop && z == st - 1.0 && m != ${MAT.CONCRETE}) ? col * 0.88 : col;   // a string course under each storey
    vec3 e0 = gEmit;
    vec3 glass = glassCol(base, N, 1.0);
    vec3 glassEmit = gEmit - e0;
    gEmit = e0;
    float id = hash3(vec3(floor(au / bay), floor((lv - gf) / st), floor(dot(cell, abs(N))) + float(vPal) * 0.37));
    vec3 light = shop ? (id < 0.75 ? vec3(1.0, 0.82, 0.58) * 1.6 : vec3(0.0))
      : (id < uLit ? room(hash2(vec2(id, 9.1))) * (0.8 + 0.6 * fract(id * 13.7)) : vec3(0.0));
    float share = shop ? 0.45 : m == ${MAT.CONCRETE} ? 0.5 : 2.0 * (st - 4.0) / (bay * st);
    float w = mix(win ? 1.0 : 0.0, share, fade);
    col = mix(wall, glass, w);
    vec3 avg = (shop ? vec3(1.0, 0.82, 0.58) * 1.2 : vec3(1.0, 0.75, 0.45) * uLit) * share;
    gEmit += glassEmit * w + mix(win ? light : vec3(0.0), avg, fade) * uNight;
    gRough = mix(0.86, 0.12, w);
  } else if (m == ${MAT.GLASS} || m == ${MAT.RIBBON} || m == ${MAT.BRONZE}) {
    if (side) {
      bool frame = mod(au, 3.0) < 0.5 || mod(lv, 8.0) < 0.5;
      if (frame) { col = base * 0.55; gRough = 0.5; }
      else {
        col = glassCol(base * 1.4, N, 1.3);
        float id = hash3(vec3(floor(au / 6.0), floor(lv / 8.0), floor(dot(cell, abs(N)))));
        if (id < uLit * 1.2) gEmit += vec3(0.95, 0.95, 0.9) * 0.9 * uNight;
      }
    } else { col = base * 0.9 + 0.05; gRough = 0.3; }
  } else if (m == ${MAT.WINDOW}) {
    col = glassCol(base, N, 1.0);
    float id = hash3(floor(cell / vec3(2.0, 3.0, 2.0)));
    if (id < uLit) gEmit += room(fract(id * 7.3)) * 0.9 * uNight;
  } else if (m == ${MAT.CLASSIC}) {
    gRough = 0.8;
    if (side && lv < 10.0 && mod(lv, 2.0) < 1.0) col *= 0.93;
  } else if (m == ${MAT.ROOF}) {
    gRough = 0.75;
    col *= 0.92 + 0.12 * hash2(floor(cell.xz / 2.0));
  } else if (m == ${MAT.WATER}) {
    float w = sin(vW.x * 0.35 + uTime * 0.9) * sin(vW.z * 0.42 - uTime * 0.7) + 0.5 * sin((vW.x + vW.z) * 1.3 + uTime * 1.7);
    col = mix(vec3(0.015, 0.06, 0.07), vec3(0.03, 0.11, 0.12), 0.5 + 0.25 * w);
    float f = 1.0 - clamp(dot(N, normalize(cameraPosition - vW)), 0.0, 1.0);
    gEmit += uSky * (0.06 + 0.5 * pow(f, 4.0)) * (1.0 - 0.7 * uNight);
    gRough = 0.06; gMetal = 0.0;
  } else if (m == ${MAT.LEAF}) {
    col = base * (0.78 + 0.4 * n1); gRough = 0.95;
    #ifdef FOLIAGE
    if (uFolOn > 0.5) {
      vec4 fo = foliageAt(cell);
      vec3 lc = floor(cell / vS);  // a far tile's own blocks
      if (fo.w < 0.5) col *= mix(vec3(1.0), grassTint(), 0.6);  // hedges and planting off the tree map: dull with the lawns
      else if (ihash(lc, 1u) > fo.x) {
        if (leafGone(lc, fo.x, vS)) discard;
        col = vec3(0.15, 0.125, 0.1) * (0.8 + 0.4 * n1);  // twigs
      } else {
        col = mix(col * uLeafTint, vec3(0.42, 0.62, 0.12) * (0.8 + 0.35 * n1), fo.z * 0.7);
        col = mix(col, uFolCol[int(fo.w)] * (0.75 + 0.45 * n1), smoothstep(0.0, 0.3, fo.y - 0.85 * ihash(lc, 3u)));
      }
    }
    #endif
  } else if (m == ${MAT.GRASS}) {
    col = base * (0.88 + 0.22 * hash2(floor(cell.xz / 3.0))) * mix(vec3(1.0), grassTint(), smoothstep(0.02, 0.08, base.g - max(base.r, base.b)));
    gRough = 1.0;
  } else if (m == ${MAT.LAMP}) {
    col = base; gEmit += vec3(1.0, 0.8, 0.52) * (0.1 + 3.5 * uNight);
  } else if (m == ${MAT.SIGN} || m == ${MAT.CLOCK}) {
    gEmit += base * (0.05 + 1.6 * uNight); gRough = 0.4;
  } else if (m == ${MAT.SIGNBAND} || m == ${MAT.METAL}) {
    gRough = 0.38;
  } else if (m == ${MAT.CAR}) {
    gRough = 0.3;
  } else if (m == ${MAT.SOIL}) {
    col = base * (mod(cell.y, 4.0) < 1.0 ? 0.85 : 1.0); gRough = 1.0;
  } else if (m == ${MAT.JET}) {
    col = vec3(0.75, 0.85, 0.9); gEmit += vec3(0.5, 0.7, 0.9) * 0.6 * uNight;
  }
  #ifdef FOLIAGE
  float farAway = smoothstep(0.22, 0.7, length(fwidth(vW)));
  if (uFolOn > 0.5 && vFace == 5 && lv < 1.0 && m != ${MAT.WATER} && m != ${MAT.LEAF} && m != ${MAT.MARK} && m != ${MAT.JET}) {
    // fallen leaves under the crowns, thinner on paving (swept) than on lawns and soil
    vec4 fo = foliageAt(cell);
    float lit = litter(fo) * (m == ${MAT.GRASS} || m == ${MAT.SOIL} ? 0.9 : 0.3);
    if (lit > 0.0) {
      float k = mix(step(ihash(cell, 4u), lit), lit, farAway);
      col = mix(col, mix(uFolCol[int(fo.w)], vec3(0.32, 0.22, 0.12), 0.45 * ihash(cell, 5u)) * (0.7 + 0.3 * n1), k);
      gRough = mix(gRough, 1.0, k);
    }
  }
  #endif
  float cover = 0.0, glint = 0.0;
  if (uSnow > 0.0 && vFace == 5 && m != ${MAT.WATER} && m != ${MAT.LAMP} && m != ${MAT.JET} && m != ${MAT.SIGN}) {
    float lum = dot(base, vec3(0.3, 0.59, 0.11));
    bool street = lv < 1.0 && m != ${MAT.GRASS} && m != ${MAT.SOIL} && m != ${MAT.LEAF} && m != ${MAT.ROOF};
    float k = street ? 0.45 + 0.4 * hash2(floor(cell.xz / 4.0)) : m == ${MAT.LEAF} ? 0.75 : 1.0;
    cover = smoothstep(0.0, 0.5, uSnow - 0.3 * hash3(cell + 0.5)) * k;
    vec3 sc = street && lum < 0.08 ? vec3(0.55, 0.56, 0.58) : vec3(0.88, 0.9, 0.95);
    col = mix(col, sc * (0.97 + 0.05 * n1), cover);
    gRough = mix(gRough, 0.85, cover); gEmit *= 1.0 - cover;
  }
  if (uWet > 0.0 && m != ${MAT.WATER} && m != ${MAT.LEAF} && m != ${MAT.LAMP} && m != ${MAT.JET} && m != ${MAT.SIGN} && m != ${MAT.CLOCK}
      && m != ${MAT.GLASS} && m != ${MAT.RIBBON} && m != ${MAT.BRONZE} && m != ${MAT.WINDOW}) {
    // rain: darker and glossier, puddles on the streets that mirror the sky (after warsaw-vibe-voxel, MIT, © 2026
    // Piotr Migdał)
    float wet = uWet * (1.0 - cover);
    bool up = vFace == 5, soft = m == ${MAT.GRASS} || m == ${MAT.SOIL};
    vec2 blk = floor(cell.xz / 2.0);  // puddles in 1 m steps, a few metres across
    float pud = up && lv < 1.0 && !soft ? smoothstep(0.58, 0.66, 0.75 * vnoise(blk / 3.5) + 0.25 * vnoise(blk / 1.3 + 7.1)) : 0.0;
    col *= mix(1.0, up ? mix(soft ? 0.85 : 0.72, 0.42, pud) : 0.86, wet);
    gRough = mix(gRough, soft ? 0.8 : up ? mix(0.38, 0.06, pud) : 0.55, wet);
    if (up && !soft) {
      float f = 1.0 - clamp(dot(N, normalize(cameraPosition - vW)), 0.0, 1.0);
      gEmit += uSky * (0.015 + 0.4 * f * f * f * f) * mix(0.45, 1.0, pud) * wet * (1.0 - 0.75 * uNight);
      glint = wet * mix(0.35, 1.0, pud);
    }
  }
  if (uNight > 0.0) { // the street lamps' light, on what is near the ground
    vec3 lamp = texture2D(uLamps, vW.xz / uMapSize).rgb;
    float fall = clamp(1.0 - (vW.y - vGround) / 14.0, 0.0, 1.0) * (vFace == 4 ? 0.3 : 1.0);
    gEmit += (m == ${MAT.WATER} ? vec3(0.5) : col) * lamp * fall * uNight * 2.4;
    gEmit += lamp * glint * uNight * 0.5;  // a wet street shines under the lamps
  }
  float ao = mix(0.5, 1.0, vAo);
  if (side) ao *= mix(0.72, 1.0, clamp((vW.y - vGround) / 1.6, 0.0, 1.0));
  diffuseColor.rgb = col * ao;`;

// `light`: for phones, the lamp pools at 4 m per texel (a quarter of the memory)
export function makeMaterial(meta: Meta, light = false) {
  const blank = new THREE.DataTexture(new Uint8Array(2), 1, 1, THREE.RGFormat);
  blank.needsUpdate = true;
  const season: Season = {
    day: { value: 172 }, on: { value: 0 }, map: { value: blank },
    date: { value: Array.from({ length: CLASSES }, () => new THREE.Vector4(-1, 0, 0, 0)) },
    col: { value: Array.from({ length: CLASSES }, () => new THREE.Color(0.5, 0.35, 0.1)) },
    grass: { value: Array.from({ length: 12 }, () => new THREE.Color(1, 1, 1)) }, leaf: { value: new THREE.Color(1, 1, 1) },
  };
  const look: Look = {
    night: { value: 0 }, lit: { value: 0.3 }, snow: { value: 0 }, time: { value: 0 }, sky: { value: new THREE.Color(0.6, 0.7, 0.8) },
    wet: { value: 0 }, season,
  };
  const foliage = !!meta.foliage;
  const uniforms = {
    uPal: { value: paletteTexture(meta) }, uLamps: { value: lampTexture(meta, light ? 0.25 : 0.5) },
    uMapSize: { value: new THREE.Vector2(meta.W * meta.vox, meta.D * meta.vox) }, uVox: { value: meta.vox },
    uNight: look.night, uLit: look.lit, uSnow: look.snow, uTime: look.time, uSky: look.sky,
    uWet: look.wet,
    uDay: season.day, uGrass: season.grass, uFolOn: season.on, uFolMap: season.map, uFolDate: season.date, uFolCol: season.col,
    uLeafTint: season.leaf, uFolCell: { value: (meta.foliage?.cell ?? 2) / meta.vox },
  };
  const compile = (sh: THREE.WebGLProgramParametersWithUniforms, own: Record<string, THREE.IUniform>) => {
    Object.assign(sh.uniforms, own);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>\n${VERT_PARS}`)
      .replace('#include <beginnormal_vertex>', 'vec3 objectNormal = faceNormal(int(va.x + 0.5));')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vW = (modelMatrix * vec4(transformed, 1.0)).xyz; vAo = va.y / 3.0; vGround = va.z; vPal = int(vp + 0.5);
        vFace = int(va.x + 0.5); vS = max(va.w, 1.0);`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\n${FRAG_PARS}`)
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
        #ifdef FADE
        if (fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) < uFade) discard;
        #endif`)
      .replace('#include <color_fragment>', SURFACE)
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = gRough;')
      .replace('#include <metalnessmap_fragment>', 'float metalnessFactor = gMetal;')
      .replace('#include <emissivemap_fragment>', 'totalEmissiveRadiance += gEmit;')
      .replace('#include <aomap_fragment>', `#include <aomap_fragment>
        reflectedLight.indirectDiffuse *= mix(0.45, 1.0, vAo);`);
  };
  // `fade` (0..1): a copy that drops that share of its pixels in a fixed screen-space pattern, for a tile giving way to
  // another (tiles.ts). Its own program, so the opaque one has no discard in it.
  const make = (fade?: number) => {
    const m = new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0 });
    const own = fade === undefined ? uniforms : { ...uniforms, uFade: { value: fade } };
    m.onBeforeCompile = (sh) => compile(sh, own);
    if (fade !== undefined) m.defines = { ...m.defines, FADE: '' };
    if (foliage) m.defines = { ...m.defines, FOLIAGE: '' };
    m.customProgramCacheKey = () => (fade === undefined ? 'voxelpest' : 'voxelpest-fade');
    return m;
  };
  const mat = make();
  const fading = Array.from({ length: 8 }, (_, i) => make((i + 0.5) / 8));
  // the sun's shadow map: bare trees cast what is left of them (only with foliage; three's own depth material
  // otherwise)
  let depth: THREE.MeshDepthMaterial | null = null;
  if (foliage) {
    depth = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking });
    depth.defines = { FOLIAGE: '' };
    depth.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, uniforms);
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', `#include <common>
          attribute vec4 va; attribute float vp; varying vec3 vW; flat varying int vPal; flat varying int vFace; flat varying float vS;`)
        .replace('#include <begin_vertex>', `#include <begin_vertex>
          vW = (modelMatrix * vec4(transformed, 1.0)).xyz; vPal = int(vp + 0.5); vFace = int(va.x + 0.5); vS = max(va.w, 1.0);`);
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', `#include <common>
          uniform sampler2D uPal; uniform float uVox; varying vec3 vW; flat varying int vPal; flat varying int vFace; flat varying float vS;
          ${SEASON}`)
        .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
          if (uFolOn > 0.5 && int(texelFetch(uPal, ivec2(vPal % 64, vPal / 64), 0).a * 255.0 + 0.5) == ${MAT.LEAF}) {
            vec3 N = vFace == 0 ? vec3(-1., 0., 0.) : vFace == 1 ? vec3(1., 0., 0.) : vFace == 2 ? vec3(0., 0., -1.)
              : vFace == 3 ? vec3(0., 0., 1.) : vFace == 4 ? vec3(0., -1., 0.) : vec3(0., 1., 0.);
            vec3 cell = floor(vW / uVox - N * 0.5 + 1e-3);
            vec4 fo = foliageAt(cell);
            if (fo.w > 0.5 && leafGone(floor(cell / vS), fo.x, vS)) discard;
          }`);
    };
    depth.customProgramCacheKey = () => 'voxelpest-depth';
  }
  // lamps: the lamp pools' texture and its scale, for the vehicles' materials (controls/kit.ts)
  return { mat, fading, look, depth, lamps: { uLamps: uniforms.uLamps, uMapSize: uniforms.uMapSize, uNight: uniforms.uNight } };
}
