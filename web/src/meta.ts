// What scripts/voxelize.py writes to public/data/meta.json. Grid coordinates: x = column (towards the east-north-east),
// y = row; the scene uses metres with three.js axes (x = column, y = height above meta.base, z = row).
export type V3 = [number, number, number];

// walk: the camera stands on a floor indoors (inside SideQuest Bar), and walking starts right there
export interface View { label: string; label_hu?: string; pos: V3; target: V3; walk?: boolean }

export interface Label {
  name: string;   // Hungarian, as in OSM
  en?: string;
  kind: string;
  x: number;
  y: number;
  z: number;
  g: number;
  far: number;
  area: number;
}

export interface Bar { name: string; x: number; y: number; z: number; g: number; door?: [number, number]; heading?: number }

export interface Meta {
  W: number;
  D: number;
  H: number;
  vox: number;
  base: number;
  water: number;
  theta_deg: number;
  center_wgs?: [number, number];
  // v: a hash of the tiles, added by the build (vite.config.js) and sent as ?v= with every tile: a new map, new URLs
  tiles: { N: number; levels: { s: number; nx: number; ny: number }[]; v?: string };
  palette: [number, number, number, number][];
  lamps: V3[];
  labels: Label[];
  views: Record<string, View>;
  sidequest?: Bar | null;
  spawn?: { name: string; name_hu?: string; x: number; z: number; g: number; heading: number } | null;  // Kossuth tér, by the flag
  sources?: Record<string, string>;
  // data/foliage.bin: per `cell` m, cols × rows, the tree class and a per-tree byte (FOLIAGE-CONTRACT; engine/foliage.ts)
  foliage?: { cell: number; cols: number; rows: number };
}

// material ids: scripts/style.py
export const MAT = {
  SOLID: 0, WALL: 1, GLASS: 2, LEAF: 3, WATER: 4, LAMP: 5, METAL: 6, PKIN: 7, GRASS: 8, MARK: 9, SOIL: 10, CAR: 11,
  ROOF: 12, CONCRETE: 13, CLOCK: 14, BRONZE: 15, SIGN: 16, JET: 17, SIGNBAND: 18, RIBBON: 19, CLASSIC: 20, WINDOW: 21,
  TENEMENT: 22,
} as const;

export async function loadMeta(url = 'data/meta.json'): Promise<Meta> {
  // always asked of the server (a 304 when unchanged): it names the tiles' version, so it must never be stale
  const r = await fetch(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}
