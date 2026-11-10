// Umami analytics, off unless the build is given a server and a website id (VITE_UMAMI_URL, VITE_UMAMI_ID; ./bv reads
// UMAMI_URL and UMAMI_ID from web.env). Umami's own script records the visits; track() records what people do: a
// short event name and a few plain values (a mode, a vehicle, a place's key, an hour). Never a position: the page's
// query string and hash are kept out of what is sent, the locate button reports only how it ended (found, outside,
// denied, failed), and track() drops any value that isn't a short word, a small whole number or a yes/no, so
// coordinates can't slip through it.
const env = import.meta.env;
const HOST = String(env.VITE_UMAMI_URL ?? '').trim().replace(/\/+$/, ''), ID = String(env.VITE_UMAMI_ID ?? '').trim();
export const analyticsOn = !!(HOST && ID);

type Value = string | number | boolean;
type Umami = { track(name: string, data?: Record<string, Value>): void };
const queue: [string, Record<string, Value> | undefined][] = [];
const umami = () => (window as { umami?: Umami }).umami;

function clean(data?: Record<string, unknown>) {
  if (!data) return undefined;
  const out: Record<string, Value> = {};
  for (const [k, v] of Object.entries(data)) {
    if (typeof v === 'boolean') out[k] = v;
    else if (typeof v === 'number' && Number.isInteger(v) && Math.abs(v) <= 1000) out[k] = v;
    else if (typeof v === 'string' && /^[\w:-]{1,40}$/.test(v)) out[k] = v;
  }
  return out;
}

export function initAnalytics() {
  if (!analyticsOn || document.querySelector('script[data-website-id]')) return;
  const s = document.createElement('script');
  s.defer = true;
  s.src = `${HOST}/script.js`;
  s.dataset.websiteId = ID;
  s.dataset.excludeSearch = 'true';
  s.dataset.excludeHash = 'true';
  s.dataset.doNotTrack = 'true';
  s.onload = () => { for (const [n, d] of queue.splice(0)) umami()?.track(n, d); };
  document.head.appendChild(s);
}

export function track(name: string, data?: Record<string, unknown>) {
  if (!analyticsOn) return;
  const d = clean(data), u = umami();
  if (u) u.track(name, d);
  else if (queue.length < 50) queue.push([name, d]);
}

// for sliders and steppers: one event with the last value, sent when the slider is let go (flush) or, for a
// controller's steps, once it has rested
const held = new Map<string, { data?: Record<string, unknown>; timer: number }>();
export function trackSoon(name: string, data?: Record<string, unknown>, ms = 2500) {
  if (!analyticsOn) return;
  clearTimeout(held.get(name)?.timer);
  held.set(name, { data, timer: window.setTimeout(() => flush(name), ms) });
}
export function flush(name: string) {
  const h = held.get(name);
  if (!h) return;
  clearTimeout(h.timer);
  held.delete(name);
  track(name, h.data);
}
