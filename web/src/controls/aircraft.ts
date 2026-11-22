// What you can fly: an FPV racing drone (first person), a small high-wing piston plane in JizzAir's colours and a
// Bell 407-type helicopter (both seen from behind). Real sizes in metres, built from the kit (controls/kit.ts): x
// forward, y up, z to the right; the propeller and rotors are separate meshes that spin.
import * as THREE from 'three';
import { Atlas, Kit, fitText, lit, mats, type P2 } from './kit';
import { storage } from '../util';

export type AircraftKind = 'drone' | 'plane' | 'heli';
export const AIRCRAFT: AircraftKind[] = ['drone', 'plane', 'heli'];

export interface AirSpec {
  vmax: number;       // m/s, level
  start: number;      // metres over the ground when it takes over from the map
  cam: [number, number, number];  // chase camera: back, up, look ahead (0 for the drone: first person)
  fov: number;
  size: [number, number, number]; // half length, half height, half span: where it touches things
}

export const AIR: Record<AircraftKind, AirSpec> = {
  // a 5" freestyle quad: 30 km/h hovering round, 140 flat out
  drone: { vmax: 39, start: 14, cam: [0, 0, 0], fov: 104, size: [0.12, 0.04, 0.12] },
  // a Cessna 172-sized trainer: stalls at 25 m/s (49 kt), cruises at 55
  plane: { vmax: 63, start: 170, cam: [17, 4.6, 30], fov: 64, size: [4.1, 1.3, 5.5] },
  // Bell 407: 133 kt, 10.7 m rotor
  heli: { vmax: 66, start: 45, cam: [19, 6.0, 20], fov: 62, size: [5.3, 1.6, 5.3] },
};

const KEY = 'voxelpest-aircraft';
const isKind = (s: string | null): s is AircraftKind => !!s && (AIRCRAFT as string[]).includes(s);
export function startAircraft(): AircraftKind {
  const q = new URLSearchParams(location.search).get('aircraft');
  if (isKind(q)) return q;
  const s = storage(KEY);
  return isKind(s) ? s : 'plane';
}
export function saveAircraft(k: AircraftKind) { storage(KEY, k); }

export interface Craft {
  g: THREE.Group;
  spin: THREE.Object3D[];      // turned about their local y (rotors) or x (propeller) by spinAxis
  spinAxis: 'x' | 'y' | 'z';
  tail?: THREE.Object3D;       // the helicopter's tail rotor, about z
  blur: THREE.Mesh[];          // discs shown once the blades turn fast
  glow: THREE.MeshStandardMaterial[];  // navigation and strobe lights
}

const FONT = 'Arial, "Helvetica Neue", "DejaVu Sans", sans-serif';
const WHITE = 0xf5f5f2, MAGENTA = 0xc6007e, PURPLE = 0x372c84, DARK = 0x1d2024, GREY = 0x8c9196;

function decal(at: Atlas) {
  const m = new THREE.MeshStandardMaterial({ map: at.texture, vertexColors: true, roughness: 0.45, alphaTest: 0.5,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  m.userData.noShadow = true;
  return lit(m);
}

function blurDisc(r: number, col: number, axis: 'x' | 'y' | 'z') {
  const m = new THREE.Mesh(new THREE.CircleGeometry(r, 40), lit(new THREE.MeshStandardMaterial({ color: col, transparent: true,
    opacity: 0.22, depthWrite: false, side: THREE.DoubleSide, roughness: 0.6 })));
  if (axis === 'y') m.rotation.x = -Math.PI / 2;
  if (axis === 'x') m.rotation.y = Math.PI / 2;
  m.visible = false;
  return m;
}

function navLights(k: Kit, left: [number, number, number], right: [number, number, number], tail: [number, number, number]) {
  const red = lit(new THREE.MeshStandardMaterial({ color: 0xd8262a, emissive: 0xff2018, emissiveIntensity: 0.6 }));
  const green = lit(new THREE.MeshStandardMaterial({ color: 0x1fae4b, emissive: 0x20ff60, emissiveIntensity: 0.6 }));
  const white = lit(new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.6 }));
  k.box(0.12, 0.08, 0.08, red, 0xffffff, ...left);
  k.box(0.12, 0.08, 0.08, green, 0xffffff, ...right);
  k.box(0.08, 0.08, 0.08, white, 0xffffff, ...tail);
  return [red, green, white];
}

// ------------------------------------------------------------------ the small plane
function plane(): Craft {
  const k = new Kit(), M = mats();
  // the fuselage from the side: the cowling, the cabin under the wing, the tail cone rising to the fin
  const side: P2[] = [[2.2, 0.55], [2.35, 0.9], [2.3, 1.3], [1.4, 1.45], [0.95, 1.95], [-0.6, 2.05], [-1.3, 1.85],
    [-4.6, 1.55], [-4.75, 1.3], [-4.6, 1.15], [-1.4, 0.75], [-0.5, 0.45], [1.4, 0.45]];
  k.profile(side, 1.12, M.paint, WHITE, 0, 0.12);
  // the livery: a magenta band low along the fuselage sweeping up to the tail, purple under it
  const band: P2[] = [[2.32, 0.75], [1.4, 0.68], [-0.5, 0.62], [-1.6, 0.86], [-4.62, 1.22], [-4.68, 1.42], [-1.4, 1.02], [-0.4, 0.84], [1.3, 0.88], [2.34, 0.94]];
  const belly: P2[] = [[1.4, 0.47], [-0.5, 0.47], [-1.45, 0.76], [-4.6, 1.16], [-4.62, 1.22], [-1.6, 0.86], [-0.5, 0.62], [1.4, 0.68]];
  k.mirror((s) => {
    k.side(band, s * 0.567, M.paint, MAGENTA);
    k.side(belly, s * 0.567, M.paint, PURPLE);
  });
  // windows: windscreen, side windows, the little rear ones
  k.slope([1.4, 1.45], [0.95, 1.95], 1.0, M.glass, 0x22303a, [0.05, 0.05], 0.02);
  k.mirror((s) => {
    k.side([[0.92, 1.42], [0.95, 1.9], [-0.55, 1.98], [-0.6, 1.42]], s * 0.566, M.glass, 0x22303a);
    k.side([[-0.75, 1.45], [-0.75, 1.9], [-1.3, 1.78], [-1.4, 1.5]], s * 0.566, M.glass, 0x22303a);
  });
  // the high wing, its struts, the tailplane and fin
  k.box(1.5, 0.14, 11.0, M.paint, WHITE, -0.05, 2.12, 0);
  k.box(1.5, 0.02, 1.4, M.paint, MAGENTA, -0.05, 2.2, 4.7);
  k.box(1.5, 0.02, 1.4, M.paint, MAGENTA, -0.05, 2.2, -4.7);
  k.mirror((s) => k.tube([-0.15, 0.7, s * 0.52], [-0.05, 2.05, s * 2.6], 0.045, M.chrome, GREY));
  k.box(0.95, 0.08, 3.4, M.paint, WHITE, -4.3, 1.4, 0);
  k.profile([[-3.7, 1.5], [-4.75, 2.95], [-5.05, 2.95], [-4.8, 1.4]], 0.12, M.paint, MAGENTA, 0, 0.03);
  // the registration and the name, on both sides
  const at = new Atlas(1024, 256), dec = decal(at);
  const name = (flip: boolean) => at.rect(512, 96, (g, w, h) => {
    g.save();
    if (flip) { g.translate(w, 0); g.scale(-1, 1); }
    g.fillStyle = '#c6007e'; g.textBaseline = 'middle'; g.textAlign = 'center';
    g.font = `800 72px ${FONT}`;
    const t1 = 'Jizz', t2 = 'Air', w1 = g.measureText(t1).width;
    g.font = `400 72px ${FONT}`;
    const w2 = g.measureText(t2).width, x0 = w / 2 - (w1 + w2) / 2;
    g.textAlign = 'left';
    g.font = `800 72px ${FONT}`; g.fillStyle = '#c6007e'; g.fillText(t1, x0, h / 2 + 4);
    g.font = `400 72px ${FONT}`; g.fillStyle = '#372c84'; g.fillText(t2, x0 + w1, h / 2 + 4);
    g.restore();
  });
  const reg = (flip: boolean) => at.rect(256, 64, (g, w, h) => {
    g.save();
    if (flip) { g.translate(w, 0); g.scale(-1, 1); }
    g.fillStyle = '#372c84'; g.textAlign = 'center'; g.textBaseline = 'middle';
    fitText(g, 'HA-JZA', w / 2, h / 2 + 2, w - 20, 48, 700, FONT);
    g.restore();
  });
  const nR = name(false), nL = name(true), rR = reg(false), rL = reg(true);
  const z = 0.569;
  k.quad([-3.3, 1.05, z], [-0.9, 1.05, z], [-0.9, 1.5, z], [-3.3, 1.5, z], dec, 0xffffff, nR);
  k.quad([-0.9, 1.05, -z], [-3.3, 1.05, -z], [-3.3, 1.5, -z], [-0.9, 1.5, -z], dec, 0xffffff, nL);
  k.quad([-4.75, 2.15, 0.065], [-4.05, 2.15, 0.065], [-4.05, 2.35, 0.065], [-4.75, 2.35, 0.065], dec, 0xffffff, rR);
  k.quad([-4.05, 2.15, -0.065], [-4.75, 2.15, -0.065], [-4.75, 2.35, -0.065], [-4.05, 2.35, -0.065], dec, 0xffffff, rL);
  // the fixed undercarriage, spats over the main wheels
  k.tube([1.6, 0.45, 0], [1.6, 0.18, 0], 0.04, M.chrome, GREY);
  k.cyl(0.18, 0.1, M.wheel, DARK, 1.6, 0.18, 0, 'z', 14);
  k.mirror((s) => {
    k.tube([-0.3, 0.5, s * 0.5], [-0.25, 0.2, s * 1.25], 0.05, M.chrome, GREY);
    k.cyl(0.2, 0.13, M.wheel, DARK, -0.25, 0.2, s * 1.25, 'z', 14);
    k.box(0.6, 0.28, 0.2, M.paint, MAGENTA, -0.25, 0.26, s * 1.25);
  });
  k.cyl(0.16, 0.3, M.chrome, 0xd9d9d9, 2.45, 0.92, 0, 'x', 12, 0.03);  // the spinner
  const glow = navLights(k, [-0.05, 2.12, -5.52], [-0.05, 2.12, 5.52], [-5.08, 2.9, 0]);
  const g = k.build();
  const prop = new THREE.Group();
  const pk = new Kit();
  pk.box(0.06, 1.9, 0.14, M.matte, DARK, 0, 0, 0);
  prop.add(pk.build());
  prop.position.set(2.42, 0.92, 0);
  g.add(prop);
  const disc = blurDisc(0.95, 0x30343a, 'x');
  disc.position.set(2.44, 0.92, 0);
  g.add(disc);
  return { g, spin: [prop], spinAxis: 'x', blur: [disc], glow };
}

// ------------------------------------------------------------------ the helicopter
function heli(): Craft {
  const k = new Kit(), M = mats(), BODY = 0x2f5aa0, STRIPE = 0xf2c230, SKID = 0x3a3d40;
  // the cabin from the side: the nose, the cabin roof, the engine fairing, down to the boom
  const side: P2[] = [[2.6, 0.75], [2.75, 1.25], [2.4, 1.85], [1.6, 2.35], [0.2, 2.6], [-1.6, 2.6], [-2.2, 2.3], [-2.6, 1.85],
    [-2.9, 1.55], [-2.6, 0.8], [-1.4, 0.55], [1.2, 0.55]];
  k.profile(side, 1.6, M.paint, BODY, 0, 0.3);
  k.mirror((s) => {
    k.side([[2.62, 1.1], [2.72, 1.3], [-2.75, 1.38], [-2.82, 1.2]], s * 0.805, M.paint, STRIPE);
    k.side([[2.3, 1.45], [1.55, 2.2], [0.6, 2.35], [0.6, 1.45]], s * 0.805, M.glass, 0x1d2a33);
    k.side([[0.45, 1.45], [0.45, 2.3], [-0.9, 2.3], [-0.9, 1.45]], s * 0.805, M.glass, 0x1d2a33);
  });
  k.slope([2.75, 1.25], [2.4, 1.85], 1.3, M.glass, 0x1d2a33, [0.05, 0.05], 0.02);
  k.slope([2.4, 1.85], [1.6, 2.35], 1.2, M.glass, 0x1d2a33, [0.02, 0.05], 0.02);
  // the engine and the mast
  k.box(2.2, 0.55, 1.0, M.paint, BODY, -0.9, 2.82, 0);
  k.box(0.5, 0.3, 0.5, M.matte, GREY, -0.9, 3.1, 0);
  k.cyl(0.08, 0.55, M.chrome, GREY, -0.2, 3.25, 0, 'y', 8);
  // the tail boom tapering to the fin, the stabiliser with its end plates, the tail rotor's gearbox
  k.cyl(0.2, 4.6, M.paint, BODY, -5.0, 1.75, 0, 'x', 14, 0.42);
  k.cyl(0.25, 0.05, M.paint, STRIPE, -5.1, 1.75, 0, 'x', 14);
  k.box(0.55, 0.06, 2.3, M.paint, BODY, -5.8, 1.75, 0);
  k.mirror((s) => k.box(0.45, 0.5, 0.05, M.paint, BODY, -5.85, 1.75, s * 1.15));
  k.profile([[-6.6, 1.7], [-7.3, 2.95], [-7.6, 2.95], [-7.4, 1.4], [-7.05, 1.3]], 0.12, M.paint, BODY, 0, 0.03);
  // the skids
  k.mirror((s) => {
    k.tube([1.6, 0.0, s * 1.15], [-1.8, 0.0, s * 1.15], 0.06, M.matte, SKID);
    k.tube([1.6, 0.0, s * 1.15], [1.95, 0.22, s * 1.15], 0.06, M.matte, SKID);
    k.tube([1.0, 0.0, s * 1.15], [0.9, 0.62, s * 0.55], 0.055, M.matte, SKID);
    k.tube([-1.1, 0.0, s * 1.15], [-1.2, 0.6, s * 0.55], 0.055, M.matte, SKID);
  });
  // the registration on the boom
  const at = new Atlas(512, 128), dec = decal(at);
  const reg = (flip: boolean) => at.rect(256, 64, (g, w, h) => {
    g.save();
    if (flip) { g.translate(w, 0); g.scale(-1, 1); }
    g.fillStyle = '#ffffff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    fitText(g, 'HA-HBK', w / 2, h / 2 + 2, w - 20, 48, 700, FONT);
    g.restore();
  });
  const rR = reg(false), rL = reg(true);
  k.quad([-4.6, 1.62, 0.33], [-3.3, 1.62, 0.37], [-3.3, 1.9, 0.37], [-4.6, 1.9, 0.33], dec, 0xffffff, rR);
  k.quad([-3.3, 1.62, -0.37], [-4.6, 1.62, -0.33], [-4.6, 1.9, -0.33], [-3.3, 1.9, -0.37], dec, 0xffffff, rL);
  const glow = navLights(k, [-5.85, 1.75, -1.18], [-5.85, 1.75, 1.18], [-7.55, 2.9, 0]);
  const g = k.build();
  // the main rotor: four blades on the hub, turning about y
  const rotor = new THREE.Group(), rk = new Kit();
  for (let i = 0; i < 4; i++) {
    const a = (i * Math.PI) / 2;
    rk.box(5.2, 0.05, 0.27, M.matte, DARK, Math.cos(a) * 2.75, 0, Math.sin(a) * 2.75, 0, -a, 0);
  }
  rk.cyl(0.25, 0.2, M.chrome, GREY, 0, 0, 0, 'y', 10);
  rotor.add(rk.build());
  rotor.position.set(-0.2, 3.55, 0);
  g.add(rotor);
  const disc = blurDisc(5.35, 0x2a2d30, 'y');
  disc.position.set(-0.2, 3.55, 0);
  g.add(disc);
  // the tail rotor on the left of the fin, turning about z
  const tail = new THREE.Group(), tk = new Kit();
  tk.box(0.1, 1.65, 0.04, M.matte, 0xe6e6e6, 0, 0, 0);
  tail.add(tk.build());
  tail.position.set(-7.25, 2.35, -0.14);
  g.add(tail);
  const tdisc = blurDisc(0.82, 0x9a9a9a, 'z');
  tdisc.position.set(-7.25, 2.35, -0.15);
  g.add(tdisc);
  return { g, spin: [rotor], spinAxis: 'y', tail, blur: [disc, tdisc], glow };
}

// the drone is flown from its camera; its props show at the top of the picture
function drone(): Craft {
  const k = new Kit(), M = mats();
  k.box(0.16, 0.03, 0.08, M.matte, DARK, 0, 0, 0);
  for (const [x, z] of [[0.09, 0.09], [0.09, -0.09], [-0.09, 0.09], [-0.09, -0.09]]) {
    k.box(0.13, 0.012, 0.02, M.matte, 0x2a2d30, x / 2, 0, z / 2, 0, Math.atan2(z, x), 0);
    k.cyl(0.065, 0.005, M.matte, 0xe23b2e, x, 0.02, z, 'y', 16);
  }
  const g = k.build();
  return { g, spin: [], spinAxis: 'y', blur: [], glow: [] };
}

const BUILD: Record<AircraftKind, () => Craft> = { drone, plane, heli };
export const buildCraft = (k: AircraftKind) => {
  const c = BUILD[k]();
  c.g.visible = false;
  c.g.traverse((o) => { if ((o as THREE.Mesh).isMesh) (o as THREE.Mesh).frustumCulled = false; });
  return c;
};
