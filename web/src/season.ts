// The day of the year: Budapest's today, a date from the URL (`date=MM-DD` or a day of the year), its name in the
// current language, and whether snow can fall then (data/climate.json from scripts/climate.py: ERA5 1995-2024, any
// snow within ten days of the date in thirty years).
import { lang } from './i18n';
import { budapestOffset } from './util';

const wall = (now = new Date()) => new Date(now.getTime() + budapestOffset(now) * 3600e3);  // Budapest's clock, read as UTC
export const budapestYear = (now = new Date()) => wall(now).getUTCFullYear();
export const yearDays = (y = budapestYear()) => (y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0) ? 366 : 365);

export function budapestDay(now = new Date()) {
  const b = wall(now), y = b.getUTCFullYear();
  return Math.round((Date.UTC(y, b.getUTCMonth(), b.getUTCDate()) - Date.UTC(y, 0, 0)) / 864e5);
}

// a day of Budapest's year as a date (midnight UTC), and back
export const dateOf = (day: number, y = budapestYear()) => new Date(Date.UTC(y, 0, day));
export const dayOf = (month: number, date: number, y = budapestYear()) => Math.round((Date.UTC(y, month, date) - Date.UTC(y, 0, 0)) / 864e5);

// MM-DD (or YYYY-MM-DD, the year ignored) or a day of the year
export function parseDay(s: string | null): number | null {
  if (!s) return null;
  const md = s.match(/^(?:\d{4}-)?(\d{1,2})-(\d{1,2})$/);
  if (md) {
    const m = +md[1], d = +md[2];
    return m >= 1 && m <= 12 && d >= 1 && d <= 31 ? Math.min(dayOf(m - 1, d), yearDays()) : null;
  }
  return /^\d{1,3}$/.test(s) && +s >= 1 ? Math.min(+s, yearDays()) : null;
}

const fmt = new Map<string, Intl.DateTimeFormat>();
export function dayName(day: number, long = false) {
  const key = `${lang()}${long}`;
  let f = fmt.get(key);
  if (!f) fmt.set(key, (f = new Intl.DateTimeFormat(lang() === 'hu' ? 'hu-HU' : 'en-GB', { day: 'numeric', month: long ? 'long' : 'short', timeZone: 'UTC' })));
  return f.format(dateOf(day));
}

export interface Climate { snowy: boolean[]; clear?: number[]; cloudy?: number[]; rain?: number[]; snow?: number[]; cover?: number[] }
let climate: Climate | null = null;

export async function loadClimate() {
  try {
    const r = await fetch('data/climate.json');
    if (r.ok) climate = (await r.json()) as Climate;
  } catch { /* the window below */ }
}

// without climate.json: 13 October to 3 May, as ERA5 gives
export const snowy = (day: number) => climate?.snowy[Math.min(day, 365) - 1] ?? (day < 124 || day > 285);
