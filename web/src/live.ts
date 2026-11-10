// Budapest right now: its clock (Europe/Budapest) and its weather from Open-Meteo, refreshed every 12 minutes while
// the viewer runs live. The request carries the city's fixed coordinates and nothing else (no referrer, no
// cookies). Offline, or when Open-Meteo fails, the last reading holds for an hour, then the sky clears.
import type { Kind } from './engine/weather';
import { budapestOffset, clamp } from './util';

const API = 'https://api.open-meteo.com/v1/forecast?latitude=47.4979&longitude=19.0402'
  + '&current=weather_code,cloud_cover,precipitation,rain,showers,snowfall&timezone=Europe%2FBudapest';
const EVERY = 12 * 60e3, KEEP = 60 * 60e3;

export const budapestHour = (now = new Date()) => {
  const b = new Date(now.getTime() + budapestOffset(now) * 3600e3);
  return b.getUTCHours() + b.getUTCMinutes() / 60 + b.getUTCSeconds() / 3600;
};

type Current = { weather_code?: number; cloud_cover?: number; rain?: number; showers?: number; snowfall?: number };
export type Reading = { kind: Kind; cover: number };

// WMO codes to the four skies: fog counts as cloudy, drizzle, showers and thunderstorms as rain, snow grains as snow
export function reading(c: Current): Reading {
  const w = c.weather_code ?? -1, cover = clamp((c.cloud_cover ?? (w >= 3 ? 100 : Math.max(w, 0) * 30)) / 100, 0, 1);
  const kind: Kind = (w >= 71 && w <= 77) || w === 85 || w === 86 ? 'snow'
    : (w >= 51 && w <= 67) || (w >= 80 && w <= 82) || w >= 95 ? 'rain'
    : w === 3 || w === 45 || w === 48 ? 'cloudy'
    : w >= 0 && w <= 2 ? 'clear'
    : (c.snowfall ?? 0) > 0 ? 'snow' : (c.rain ?? 0) + (c.showers ?? 0) > 0 ? 'rain' : cover > 0.8 ? 'cloudy' : 'clear';
  return { kind, cover };
}

export class Live {
  on = false;
  private last: (Reading & { at: number }) | null = null;
  private timer = 0;
  private busy = false;

  constructor(private readonly onWeather: (r: Reading) => void) {
    addEventListener('online', () => void this.refresh());
    document.addEventListener('visibilitychange', () => { if (!document.hidden && this.stale()) void this.refresh(); });
  }

  set(on: boolean) {
    this.on = on;
    clearInterval(this.timer);
    if (!on) return;
    if (this.stale()) void this.refresh();
    else this.onWeather(this.last!);
    this.timer = window.setInterval(() => { if (!document.hidden) void this.refresh(); }, EVERY);
  }

  private stale() { return !this.last || Date.now() - this.last.at > EVERY - 5e3; }

  async refresh() {
    if (!this.on || this.busy) return;
    this.busy = true;
    const ctl = new AbortController(), give = setTimeout(() => ctl.abort(), 10e3);
    try {
      const r = await fetch(API, { signal: ctl.signal, credentials: 'omit', referrerPolicy: 'no-referrer', cache: 'no-store' });
      const cur = r.ok ? ((await r.json()) as { current?: Current }).current : null;
      if (!cur) throw new Error(String(r.status));
      this.last = { ...reading(cur), at: Date.now() };
    } catch {
      if (this.last && Date.now() - this.last.at > KEEP) this.last = null;
    } finally {
      clearTimeout(give);
      this.busy = false;
    }
    if (this.on) this.onWeather(this.last ?? { kind: 'clear', cover: 0 });
  }
}
