// A page that dies (iOS kills one that takes too much memory or stalls the GPU: a reload, then "a problem repeatedly
// occurred") leaves a note behind: `alive`, refreshed while the page is visible and removed when it is hidden or
// left. A start that finds the note knows the last one crashed (main.ts reports it); a phone then comes up one level
// lighter, kept for that device, so one that can't hold the full map settles on what it can. A day without a crash
// and it tries one level up again. A computer only reports: one killed browser shouldn't cost it its graphics.
// ?lite=0..3 forces a level.
const ALIVE = 'voxelpest-alive', LITE = 'voxelpest-lite-2', MAX = 3, RETRY_MS = 24 * 3600e3;

export interface Crumb { t: number; secs: number; mode: string; mb: number; tiles: number }
export interface Lite { level: number; crashed: Crumb | null; dpr: number; shadow: number; budget: number; err: number }

const read = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const write = (k: string, v: string | null) => { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch { /* private mode */ } };

// per level: the most device pixels per CSS pixel, the shadow map's size (0: no shadows), megabytes of tile geometry,
// and how many times coarser the detail falls off
const LEVELS = [
  { dpr: 1.5, shadow: 2048, budget: 160, err: 1 },
  { dpr: 1.25, shadow: 1024, budget: 110, err: 1.2 },
  { dpr: 1, shadow: 1024, budget: 75, err: 1.45 },
  { dpr: 1, shadow: 0, budget: 50, err: 1.8 },
];

export function startLite(qs: URLSearchParams, phone: boolean): Lite {
  let crashed: Crumb | null = null;
  try { crashed = JSON.parse(read(ALIVE) ?? 'null'); } catch { /* not ours */ }
  if (crashed && typeof crashed.secs !== 'number') crashed = null;
  let kept = { level: 0, since: 0 };
  try { kept = { ...kept, ...JSON.parse(read(LITE) ?? '{}') }; } catch { /* not ours */ }
  let level = Math.min(Math.max(Math.round(+kept.level) || 0, 0), MAX), since = +kept.since || 0;
  const now = Date.now();
  if (!phone) level = 0;
  else if (crashed) { level = Math.min(level + 1, MAX); since = now; }
  else if (level > 0 && now - since > RETRY_MS) { level--; since = now; }
  if (phone) write(LITE, level ? JSON.stringify({ level, since }) : null);
  write('voxelpest-lite', null);  // the first version's level, from before the workers' memory was fixed
  if (qs.has('lite')) level = Math.min(Math.max(Math.round(+qs.get('lite')!) || 0, 0), MAX);
  return { level, crashed, ...LEVELS[level] };
}

// `state()` is what the note says: the mode and the tiles' memory, for the next start to report
export function keepAlive(state: () => Omit<Crumb, 't' | 'secs'>) {
  const t0 = Date.now();
  const beat = () => {
    if (document.visibilityState === 'visible') write(ALIVE, JSON.stringify({ t: Date.now(), secs: Math.round((Date.now() - t0) / 1000), ...state() }));
    else write(ALIVE, null);
  };
  beat();
  setInterval(beat, 3000);
  document.addEventListener('visibilitychange', beat);
  addEventListener('pagehide', () => write(ALIVE, null));
}
