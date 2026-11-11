// "Save for offline" in the About box (website only, production builds with a service worker): the whole map and the
// page's shell into Cache Storage, from the list the build writes (offline.json, vite.config.js's writeOffline), so
// the installed app or the site opens and works with no network. public/sw.js serves it: tiles from the saved map
// first, meta.json and the other data from the network first. Each file is stored as it arrives, so a stopped or
// failed download resumes where it was; data/offline-done.json marks a complete one (with its map's hash), and
// nothing in the cache is served as "the map" by the worker until then except files already there.
import { track } from './analytics';
import { onLang, T } from './i18n';
import { desktop } from './ui/desktop';

const MAP = 'voxelpest-map';  // public/sw.js's MAP
const DONE = 'data/offline-done.json';
const PARALLEL = 6;

type List = { v: string; bytes: number; shell: string[]; data: string[] };
type Done = { v: string; bytes: number; at: string };
type State = 'none' | 'partial' | 'done' | 'old' | 'busy';

const abs = (p: string) => new URL(p, document.baseURI).href;
const mb = (b: number) => `${Math.round(b / 1e6)} MB`;

export function offlineAvailable() {
  return !desktop && import.meta.env.PROD && 'serviceWorker' in navigator && 'caches' in window;
}

async function list(): Promise<List | null> {
  try {
    const r = await fetch('offline.json', { cache: 'no-cache' });
    return r.ok ? ((await r.json()) as List) : null;
  } catch { return null; }
}

async function done(c: Cache): Promise<Done | null> {
  const r = await c.match(abs(DONE));
  return r ? ((await r.json()) as Done) : null;
}

// Download everything not in the cache yet (meta.json and the other unversioned files always again), then drop what the
// list doesn't name (an older map's tiles) and mark it done.
async function save(l: List, signal: AbortSignal, progress: (f: number) => void) {
  const c = await caches.open(MAP);
  await c.delete(abs(DONE));
  const all = [...l.shell, ...l.data];
  const fresh = (p: string) => p.startsWith('data/tiles/') || p.startsWith('assets/');
  let n = 0, i = 0;
  const one = async (p: string) => {
    const url = abs(p);
    if (!(fresh(p) && (await c.match(url)))) {
      const r = await fetch(url, { signal, cache: fresh(p) ? 'default' : 'no-cache' });
      if (!r.ok) throw new Error(`${r.status} ${p}`);
      await c.put(url, r);
    }
    progress(++n / all.length);
  };
  const worker = async () => { while (i < all.length) { signal.throwIfAborted(); await one(all[i++]); } };
  await Promise.all(Array.from({ length: PARALLEL }, worker));
  const keep = new Set(all.map(abs));
  for (const k of await c.keys()) if (!keep.has(k.url)) await c.delete(k);
  const d: Done = { v: l.v, bytes: l.bytes, at: new Date().toISOString() };
  await c.put(abs(DONE), new Response(JSON.stringify(d), { headers: { 'content-type': 'application/json' } }));
}

export function initOffline(box: HTMLElement) {
  if (!offlineAvailable()) return;
  const text = box.querySelector<HTMLElement>('.off-text')!;
  const bar = box.querySelector<HTMLElement>('.off-bar')!;
  const go = box.querySelector<HTMLButtonElement>('.off-go')!;
  const del = box.querySelector<HTMLButtonElement>('.off-del')!;
  let l: List | null = null, d: Done | null = null, state: State = 'none', frac = 0, error = '';
  let ctl: AbortController | null = null;

  const render = () => {
    const t = T(), size = mb(l?.bytes ?? d?.bytes ?? 0);
    box.hidden = !l && !d;
    bar.hidden = state !== 'busy';
    bar.style.setProperty('--f', String(frac));
    del.hidden = !(state === 'done' || state === 'old' || state === 'partial');
    del.textContent = t.offDelete;
    go.hidden = state === 'done' || (!l && state !== 'busy');
    go.textContent = state === 'busy' ? t.offStop : state === 'partial' ? t.offResume : state === 'old' ? t.offUpdate : t.offSave(size);
    text.textContent = error || (state === 'busy' ? t.offBusy(Math.floor(frac * 100), size)
      : state === 'done' ? t.offDone(size) : state === 'old' ? t.offOld : state === 'partial' ? t.offPartial : t.offIntro);
  };

  const refresh = async () => {
    const c = await caches.open(MAP);
    [l, d] = await Promise.all([list(), done(c)]);
    if (state === 'busy') return render();
    state = d ? (l && l.v !== d.v ? 'old' : 'done') : (await c.keys()).length ? 'partial' : 'none';
    render();
  };

  go.onclick = async () => {
    if (ctl) { ctl.abort(); return; }
    if (!l) return;
    error = '';
    const est = await navigator.storage?.estimate?.().catch(() => null);
    if (est?.quota != null && est.usage != null && est.quota - est.usage < l.bytes * 1.05) {
      error = T().offSpace(mb(est.quota - est.usage));
      render();
      return;
    }
    await navigator.storage?.persist?.().catch(() => false);  // or the browser may evict it when space runs low
    track('offline', { step: d ? 'update' : 'save' });
    ctl = new AbortController();
    state = 'busy';
    frac = 0;
    render();
    let last = 0;
    try {
      await save(l, ctl.signal, (f) => {
        frac = f;
        const now = performance.now();
        if (now - last > 150) { last = now; render(); }
      });
      track('offline', { step: 'done' });
    } catch (e) {
      if (!ctl.signal.aborted) {
        console.warn('offline save', e);
        error = T().offFailed;
        track('offline', { step: 'failed' });
      }
    }
    ctl = null;
    state = 'none';
    await refresh();
  };

  del.onclick = async () => {
    await caches.delete(MAP);
    track('offline', { step: 'removed' });
    error = '';
    await refresh();
  };

  onLang(render);
  void refresh();
}
