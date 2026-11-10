// What you can drive: the taxi, a Trabant 601, a Hungarian police Škoda, a MOL Bubi bike and a BKK bus. Sizes are
// the real ones in metres (x forward from the body's centre, z to the right); the handling is arcade, but each keeps its
// character: the Trabant is slow to get going, the police car quick, the bike slow and nimble, the bus wide-turning.
import { storage } from '../util';

export type VehicleKind = 'taxi' | 'trabant' | 'police' | 'bubi' | 'bus';
export const KINDS: VehicleKind[] = ['taxi', 'trabant', 'police', 'bubi', 'bus'];

export interface Spec {
  len: number;               // bumper to bumper
  wid: number;
  height: number;            // what must be clear above the step for it to pass
  axles: [number, number];   // front and rear axle, x
  track: number;             // between the wheels' centres; 0 for the bike (its two wheels in line)
  r: number;                 // wheel radius
  step: number;              // kerbs and steps taken in its stride
  vmax: number;              // m/s, and with boost (Shift, B)
  boost: number;
  accel: number;             // m/s² from rest
  brake: number;
  reverse: number;           // top speed backwards
  turn: number;              // tightest turn at a crawl: the radius at the rear axle, m
  grip: number;              // the speed (m/s) at which the steering lock is halved
  lean: number;              // body roll per m/s² sideways (negative: outwards); the bike leans in by physics
  cam: [number, number, number, number];  // chase camera: back, up, look-at height, look ahead
  feel: { fov: number; shake: number };   // the view's widening at top speed (degrees), the camera's shake there
  lamp: [number, number];    // the headlamp: x, y
  ground: 'road' | 'bike';   // where it is put back (R): a road, or a road, pavement or cycle lane for the bike
  exhaust: { at: [number, number, number]; dir: [number, number, number]; smoke: Smoke } | null;  // the pipe's end
}

export type Smoke = 'two-stroke' | 'petrol' | 'diesel';

export const SPECS: Record<VehicleKind, Spec> = {
  // a Budapest taxi, an Octavia-sized saloon
  taxi: { len: 4.69, wid: 1.83, height: 1.5, axles: [1.42, -1.27], track: 1.54, r: 0.32, step: 0.75, vmax: 25, boost: 38, accel: 7.5,
    brake: 16, reverse: 8, turn: 4.1, grip: 9, lean: -0.006, cam: [7.4, 2.75, 1.1, 5], feel: { fov: 13, shake: 1 }, lamp: [2.3, 0.7],
    ground: 'road', exhaust: { at: [-2.39, 0.27, -0.52], dir: [-1, -0.12, 0], smoke: 'petrol' } },
  // 3.56 × 1.50 m, 26 hp two-stroke: 0-100 in 21 s, 107 km/h flat out
  trabant: { len: 3.56, wid: 1.50, height: 1.44, axles: [1.03, -0.99], track: 1.23, r: 0.285, step: 0.7, vmax: 26, boost: 30, accel: 4.2,
    brake: 12, reverse: 6, turn: 3.7, grip: 8, lean: -0.009, cam: [6.5, 2.5, 1.0, 4.5], feel: { fov: 13, shake: 1.7 }, lamp: [1.75, 0.66],
    ground: 'road', exhaust: { at: [-1.87, 0.3, -0.45], dir: [-1, -0.08, 0], smoke: 'two-stroke' } },
  // Škoda Octavia IV: 4.69 × 1.83 m
  police: { len: 4.69, wid: 1.83, height: 1.6, axles: [1.42, -1.27], track: 1.54, r: 0.32, step: 0.75, vmax: 30, boost: 45, accel: 9,
    brake: 18, reverse: 9, turn: 4.4, grip: 10, lean: -0.005, cam: [7.6, 2.75, 1.1, 5], feel: { fov: 15, shake: 0.9 }, lamp: [2.3, 0.68],
    ground: 'road', exhaust: { at: [-2.39, 0.27, -0.52], dir: [-1, -0.12, 0], smoke: 'petrol' } },
  // MOL Bubi: 26" wheels, 1.12 m wheelbase, about 20 km/h pedalling, 30 with a sprint
  bubi: { len: 1.8, wid: 0.62, height: 1.75, axles: [0.56, -0.56], track: 0, r: 0.33, step: 0.6, vmax: 5.8, boost: 8.4, accel: 2.4,
    brake: 7, reverse: 1.3, turn: 1.9, grip: 3.5, lean: 1, cam: [3.7, 1.9, 1.25, 3], feel: { fov: 8, shake: 0.4 }, lamp: [0.82, 0.8],
    ground: 'bike', exhaust: null },
  // Mercedes-Benz Citaro C2, 12.1 × 2.55 m, three doors; no smoke from it
  bus: { len: 12.14, wid: 2.55, height: 3.0, axles: [3.26, -2.58], track: 2.0, r: 0.48, step: 0.7, vmax: 15, boost: 20, accel: 2.3,
    brake: 7, reverse: 4, turn: 8.6, grip: 6, lean: -0.012, cam: [16, 5.8, 2.4, 8], feel: { fov: 9, shake: 1.1 }, lamp: [6.05, 0.62],
    ground: 'road', exhaust: null },
};

const KEY = 'voxelpest-vehicle';
const isKind = (s: string | null): s is VehicleKind => !!s && (KINDS as string[]).includes(s);

// ?vehicle= first, then the last choice, then the taxi
export function startKind(): VehicleKind {
  const q = new URLSearchParams(location.search).get('vehicle');
  if (isKind(q)) return q;
  const s = storage(KEY);
  return isKind(s) ? s : 'taxi';
}

export function saveKind(k: VehicleKind) { storage(KEY, k); }
