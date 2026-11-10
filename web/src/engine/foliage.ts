// The trees and lawns through the year, after warsaw-vibe-voxel's foliage.ts (MIT, © 2026 Piotr Migdał): the classes'
// leaf-out, colouring and fall in Budapest and the lawns by month (data/phenology.json, scripts/phenology.py), and,
// where the build wrote it (meta.foliage), per 2 m cell the class of the crown over it and a per-tree byte
// (data/foliage.bin, FOLIAGE-CONTRACT) -> the voxel shader's season uniforms (material.ts). Without foliage.bin the
// trees stay as they are and only the lawns follow the months; without phenology.json nothing changes.
import * as THREE from 'three';
import type { Meta } from '../meta';
import { CLASSES, type Season } from './material';

interface Phase { day: number; sd: number }
interface Class { species: string; leaf: Phase | null; colour: Phase | null; fall: Phase | null; autumn: string | null }
export interface Phenology {
  classes: Record<string, Class>;
  city: { leaf: number; colour: number; fall: number };
  grass: [number, number, number][];
  leaf: [number, number, number];
}

async function gunzip(r: Response) {
  return new Response(r.body!.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
}

export async function loadSeasons(meta: Meta, season: Season): Promise<Phenology | null> {
  const ph = await fetch('data/phenology.json').then((r) => (r.ok ? (r.json() as Promise<Phenology>) : null)).catch(() => null);
  if (!ph) return null;
  ph.grass.forEach((t, m) => season.grass.value[m]?.setRGB(...t));
  season.leaf.value.setRGB(...ph.leaf);
  const f = meta.foliage;
  if (!f) return ph;
  try {
    const r = await fetch('data/foliage.bin');
    if (!r.ok || !r.body) throw new Error(String(r.status));
    const a = new Uint8Array(await gunzip(r)), n = f.cols * f.rows;
    if (a.length < 2 * n) throw new Error(`foliage.bin: ${a.length} bytes, ${2 * n} expected`);
    const rg = new Uint8Array(2 * n);
    for (let i = 0; i < n; i++) { rg[2 * i] = a[i]; rg[2 * i + 1] = a[n + i]; }
    const tex = new THREE.DataTexture(rg, f.cols, f.rows, THREE.RGFormat);
    tex.magFilter = tex.minFilter = THREE.NearestFilter;
    tex.unpackAlignment = 2;
    tex.needsUpdate = true;
    season.map.value = tex;
    for (let i = 0; i < CLASSES; i++) {
      const c = ph.classes[i];
      if (c?.leaf && c.colour && c.fall) season.date.value[i].set(c.leaf.day, c.colour.day, c.fall.day, (c.leaf.sd + c.colour.sd + c.fall.sd) / 3);
      else season.date.value[i].set(-1, 0, 0, 0);
      if (c?.autumn) season.col.value[i].set(c.autumn);  // sRGB hex -> the working (linear) space
    }
    season.on.value = 1;
  } catch (e) {
    console.warn('foliage', e);
  }
  return ph;
}

const BARE = [154, 145, 132], FRESH = [176, 212, 96], GREEN = [96, 152, 64], AUTUMN = [222, 160, 62], BROWN = [168, 120, 72];
const mix = (a: number[], b: number[], t: number) => a.map((c, k) => Math.round(c + (b[k] - c) * Math.min(Math.max(t, 0), 1)));
// how the city's trees look on a day (bare, fresh, green, in colour, falling), for the date slider (sRGB)
export function treeColour(day: number, city = { leaf: 102, colour: 296, fall: 314 }) {
  const { leaf, colour, fall } = city;
  const rgb = day < leaf - 8 || day >= fall + 14 ? BARE : day < leaf + 6 ? mix(BARE, FRESH, (day - leaf + 8) / 14)
    : day < leaf + 30 ? mix(FRESH, GREEN, (day - leaf - 6) / 24) : day < colour - 12 ? GREEN
    : day < colour + 4 ? mix(GREEN, AUTUMN, (day - colour + 12) / 16) : day < fall ? mix(AUTUMN, BROWN, (day - colour - 4) / Math.max(fall - colour - 4, 1))
    : mix(BROWN, BARE, (day - fall) / 14);
  return { rgb, bare: day < leaf - 2 || day > fall + 7 };
}
