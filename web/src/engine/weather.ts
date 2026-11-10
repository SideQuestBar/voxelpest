// The weather: clear, cloudy, rain or snow, each eased into the next. Snow falls in engine/snow.ts and rain in
// engine/rain.ts; engine/sky.ts turns the levels into sky and light, and the voxel shader into snow cover and wet
// streets (which dry more slowly than they get wet).
import * as THREE from 'three';
import { clamp } from '../util';
import type { Look } from './material';
import { Rain } from './rain';
import { Snow } from './snow';

export const KINDS = ['clear', 'cloudy', 'rain', 'snow'] as const;
export type Kind = (typeof KINDS)[number];
export const isKind = (s: string | null | undefined): s is Kind => KINDS.includes(s as Kind);

const ease = (v: number, to: number, dt: number, up: number, down: number) => (v < to ? Math.min(to, v + dt / up) : Math.max(to, v - dt / down));

export class Weather {
  kind: Kind = 'clear';
  readonly snow: Snow;
  readonly rain: Rain;
  // what engine/sky.ts reads, 0 .. 1 each: overcast light, rain, snow, the cloud deck drawn and how much of the sky
  // it covers
  readonly levels = { cloud: 0, rain: 0, snow: 0, deck: 0, cover: 0 };
  private cover = 0;  // the sky's cloud cover, 0 .. 1 (Open-Meteo's, live)
  private wet = 0;

  constructor(scene: THREE.Scene, touch: boolean) {
    this.snow = new Snow(scene, touch ? 12000 : 24000);
    this.rain = new Rain(scene, touch ? 10000 : 16000);
  }

  // cover: a clear sky may carry some clouds (live); a cloudy one has a few breaks unless told otherwise
  set(k: Kind, cover?: number, now = false) {
    this.kind = k;
    this.cover = clamp(cover ?? (k === 'rain' ? 1 : k === 'cloudy' ? 0.7 : 0), 0, 1);
    this.snow.on = k === 'snow';
    this.rain.on = k === 'rain';
    if (!now) return;
    const t = this.target();
    this.snow.level = +this.snow.on;
    this.rain.level = +this.rain.on;
    Object.assign(this.levels, t, { rain: this.rain.level, snow: this.snow.level });
    this.wet = this.rain.level;
  }

  private target() {
    const k = this.kind, c = this.cover, over = k === 'cloudy' || k === 'rain';
    return {
      cloud: over ? 1 : 0,
      deck: over ? 1 : k === 'clear' ? clamp((c - 0.1) * 3, 0, 1) : 0,
      cover: over ? 0.55 + 0.45 * c : 0.45 * c,
    };
  }

  update(dt: number, camera: THREE.PerspectiveCamera, vw: number, vh: number, pixelRatio: number, night: number, look: Look) {
    const L = this.levels, t = this.target();
    L.cloud = ease(L.cloud, t.cloud, dt, 5, 5);
    L.deck = ease(L.deck, t.deck, dt, 4, 6);
    L.cover = ease(L.cover, t.cover, dt, 8, 8);
    this.snow.update(dt, camera, vh);
    // fewer drops on a small screen, and at a low pixel ratio, where each streak is wider: they look as dense
    this.rain.update(dt, camera, night, clamp(Math.sqrt((vw * vh) / (1440 * 900)), 0.45, 1) * (pixelRatio < 1.25 ? 0.8 : 1));
    this.wet = ease(this.wet, +this.rain.on, dt, 10, 40);
    L.rain = this.rain.level;
    L.snow = this.snow.level;
    look.snow.value = this.snow.level;
    look.wet.value = this.wet;
  }
}
