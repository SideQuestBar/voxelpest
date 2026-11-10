// The date, the time of day and the weather, tucked into a card behind the bar's clock button (the weather's icon, the
// date when it isn't today, and the time). Both sliders are drawn like the mode switch, their thumb the pressed button
// with the value on it: the date's runs over the year (month initials, a leaf in the colour of the city's trees on
// that day, a bare twig in winter, over the trees through the year), the hour's over that day's light (sunrise and
// sunset in Budapest). Below them Clear / Cloudy / Rain / Snow (snow only around dates it can fall), and in the corner
// the Live switch (Budapest's date, clock and weather, live.ts), which a slider or a weather turns off. A tap elsewhere
// or Esc closes the card; a controller's D-pad shows it for a moment.
import { flush } from '../analytics';
import { treeColour } from '../engine/foliage';
import { instant, sunAt } from '../engine/sky';
import type { Kind } from '../engine/weather';
import { onLang, T } from '../i18n';
import { budapestDay, dateOf, dayName, dayOf, yearDays } from '../season';
import { $, clamp, isTouch } from '../util';

const SNAP = 1 / 12;  // dragging moves in 5 minute steps, the arrow keys in 15
const MAX = 24 - SNAP;

export const clock = (h: number) => {
  const m = Math.round((((h % 24) + 24) % 24) * 60) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
};

// that day's light along the hour slider: night, dusk, golden hour, day
function daylight(day: number) {
  const stops: [number, number[]][] = [[-12, [40, 50, 77]], [-6, [91, 95, 143]], [-1, [217, 138, 106]], [4, [240, 174, 85]], [12, [245, 210, 122]], [25, [247, 223, 152]]];
  const colour = (deg: number) => {
    const i = stops.findIndex(([d]) => d >= deg);
    if (i <= 0) return stops[i < 0 ? stops.length - 1 : 0][1];
    const [d0, c0] = stops[i - 1], [d1, c1] = stops[i], t = (deg - d0) / (d1 - d0);
    return c0.map((c, k) => Math.round(c + (c1[k] - c) * t));
  };
  const parts: string[] = [];
  for (let h = 0; h <= 24; h += 0.5) parts.push(`rgb(${colour((sunAt(instant(h, day)).el * 180) / Math.PI).join(',')}) ${((h / 24) * 100).toFixed(1)}%`);
  return `linear-gradient(90deg, ${parts.join(', ')})`;
}

type City = { leaf: number; colour: number; fall: number } | undefined;

// the trees through the year along the date slider
function seasons(city: City) {
  const n = yearDays(), parts: string[] = [];
  for (let d = 1; d <= n; d += 4) parts.push(`rgb(${treeColour(d, city).rgb.join(',')}) ${(((d - 1) / (n - 1)) * 100).toFixed(1)}%`);
  return `linear-gradient(90deg, ${parts.join(', ')})`;
}

// a slider drawn as a .seg (ui.ts): the thumb's centre over the value, 3 px in from the padding box, as the CSS puts it
function slide(s: HTMLElement, thumb: HTMLElement, value: (f: number) => number, key: (e: KeyboardEvent) => number | undefined, set: (v: number) => void, done: () => void) {
  const at = (x: number) => {
    const r = s.getBoundingClientRect(), tw = thumb.offsetWidth, pad = 3;
    set(value(clamp((x - r.left - s.clientLeft - pad - tw / 2) / Math.max(s.clientWidth - 2 * pad - tw, 1), 0, 1)));
  };
  s.addEventListener('pointerdown', (e) => {
    if (e.button > 0) return;
    e.preventDefault();
    s.focus({ preventScroll: true });
    s.setPointerCapture(e.pointerId);
    s.classList.add('drag');
    at(e.clientX);
  });
  s.addEventListener('pointermove', (e) => { if (s.hasPointerCapture(e.pointerId)) at(e.clientX); });
  const end = (e: PointerEvent) => {
    if (s.hasPointerCapture(e.pointerId)) s.releasePointerCapture(e.pointerId);
    s.classList.remove('drag');
    done();
  };
  s.addEventListener('keyup', done);
  s.addEventListener('pointerup', end);
  s.addEventListener('pointercancel', end);
  s.addEventListener('keydown', (e) => {
    const v = key(e);
    if (v === undefined) return;
    set(v);
    e.preventDefault();
    e.stopPropagation();  // the arrows would fly the map too
  });
}

// the marks the thumb covers, or nearly, fade out (a half-hidden "24" read as "4"); the same margin for every mark
function ticks(s: HTMLElement, thumb: HTMLElement, f: number, at: (t: HTMLElement) => number) {
  const tw = thumb.offsetWidth, run = s.clientWidth - 6 - tw;
  if (run <= 0) return;  // the card is closed: open() calls this again
  for (const t of s.querySelectorAll<HTMLElement>('.tick')) t.classList.toggle('hid', Math.abs(at(t) - f) * run < tw / 2 + 5);
}

export class TimeCard {
  private readonly btn = $<HTMLButtonElement>('#time-btn');
  private readonly card = $('#time-card');
  private readonly slider = $('#hour');
  private readonly thumb = $('#hour .thumb');
  private readonly dateSlider = $('#date');
  private readonly dateThumb = $('#date .thumb');
  private readonly live = $<HTMLButtonElement>('#live');
  private hour = -1;
  private day = 0;
  private lightDay = -1;
  private city: City;
  private kind: Kind = 'clear';
  private isLive = false;
  private peeking = false;
  private peekTimer = 0;

  constructor(private readonly on: { hour(h: number): void; date(d: number): void; weather(k: Kind): void; live(on: boolean): void; opened(): void }) {
    this.btn.onclick = () => this.open(!this.isOpen);
    document.addEventListener('pointerdown', (e) => {
      if (!this.card.hidden && !$('#time-pop').contains(e.target as Node)) this.open(false);
    }, true);
    addEventListener('keydown', (e) => {
      if (e.key !== 'Escape' || this.card.hidden) return;
      const inside = this.card.contains(document.activeElement);
      this.open(false);
      if (inside) this.btn.focus();
    });
    this.card.addEventListener('pointerdown', () => this.hold());
    this.card.addEventListener('focusin', () => this.hold());
    for (const b of this.card.querySelectorAll<HTMLButtonElement>('#weather button')) b.onclick = () => on.weather(b.dataset.w as Kind);
    this.live.onclick = () => on.live(!this.isLive);
    slide(this.slider, this.thumb, (f) => Math.round((f * 24) / SNAP) * SNAP, (e) => {
      const step = e.shiftKey ? 1 : 0.25;
      const d = ({ ArrowRight: step, ArrowUp: step, ArrowLeft: -step, ArrowDown: -step, PageUp: 1, PageDown: -1 } as Record<string, number>)[e.key];
      return d !== undefined ? Math.round((this.hour + d) / SNAP) * SNAP : e.key === 'Home' ? 0 : e.key === 'End' ? MAX : undefined;
    }, (h) => {
      h = clamp(h, 0, MAX);
      if (Math.abs(h - this.hour) > 1e-6) on.hour(h);
    }, () => flush('time'));
    // a day, a week with Shift, a month with Page Up / Down
    slide(this.dateSlider, this.dateThumb, (f) => 1 + Math.round(f * (yearDays() - 1)), (e) => {
      const step = e.shiftKey ? 7 : 1;
      const d = ({ ArrowRight: step, ArrowUp: step, ArrowLeft: -step, ArrowDown: -step } as Record<string, number>)[e.key];
      if (d !== undefined) return this.day + d;
      const t = dateOf(this.day), month = (k: number) => Math.min(dayOf(t.getUTCMonth() + k, t.getUTCDate()), dayOf(t.getUTCMonth() + k + 1, 0));
      return e.key === 'PageUp' ? month(1) : e.key === 'PageDown' ? month(-1) : e.key === 'Home' ? 1 : e.key === 'End' ? yearDays() : undefined;
    }, (d) => {
      d = clamp(Math.round(d), 1, yearDays());
      if (d !== this.day) on.date(d);
    }, () => flush('date'));
    this.months();
    onLang(() => { this.months(); this.showDay(this.day); this.label(); });
  }

  get isOpen() { return !this.card.hidden; }

  open(on: boolean, peek = false) {
    clearTimeout(this.peekTimer);
    this.peeking = on && peek;
    if (on !== this.card.hidden) return;
    this.card.hidden = !on;
    this.btn.setAttribute('aria-expanded', String(on));
    if (on) {
      this.ticks();
      this.on.opened();
      if (!peek && !isTouch()) this.slider.focus({ preventScroll: true });
    }
  }

  // shown for a moment (a controller changing the hour or the date), unless it is open already
  peek() {
    if (this.isOpen && !this.peeking) return;
    this.open(true, true);
    this.peekTimer = window.setTimeout(() => { if (this.peeking) this.open(false); }, 1600);
  }

  private hold() {
    if (!this.peeking) return;
    this.peeking = false;
    clearTimeout(this.peekTimer);
  }

  show(h: number) {
    this.hour = h;
    const t = clock(h), dark = sunAt(instant(h, this.day || budapestDay())).el < (-2 * Math.PI) / 180;
    this.slider.style.setProperty('--f', String(clamp(h, 0, 24) / 24));
    this.slider.setAttribute('aria-valuenow', h.toFixed(2));
    this.slider.setAttribute('aria-valuetext', t);
    $('#hour-label').textContent = t;
    $('#time-now').textContent = t;
    this.thumb.classList.toggle('night', dark);
    this.btn.classList.toggle('night', dark);
    this.card.classList.toggle('night', dark);
    this.ticks();
    this.label();
  }

  // the month initials, at the middle of each month
  private months() {
    const s = this.dateSlider, n = yearDays();
    for (const t of s.querySelectorAll('.tick')) t.remove();
    T().months.forEach((m, i) => {
      const t = document.createElement('span');
      t.className = 'tick';
      t.textContent = m;
      t.style.setProperty('--d', String((dayOf(i, 15) - 1) / (n - 1)));
      s.insertBefore(t, this.dateThumb);
    });
    s.setAttribute('aria-valuemax', String(n));
  }

  showDay(d: number) {
    if (!d) return;
    this.day = d;
    const n = yearDays(), tree = treeColour(d, this.city), lift = tree.rgb.map((c) => Math.round(c + (255 - c) * 0.3));
    this.dateSlider.style.setProperty('--f', String((d - 1) / (n - 1)));
    this.dateSlider.setAttribute('aria-valuenow', String(d));
    this.dateSlider.setAttribute('aria-valuetext', dayName(d, true));
    $('#date-label').textContent = dayName(d);
    this.dateThumb.style.setProperty('--leaf', `rgb(${lift.join(',')})`);
    this.dateThumb.classList.toggle('bare', tree.bare);
    const other = d !== budapestDay();
    $('#time-date').textContent = other ? dayName(d) : '';
    $('#time-date').hidden = !other;
    if (d !== this.lightDay) {  // that day's light, and whether the hour is night then
      this.lightDay = d;
      $('#hour .day').style.background = daylight(d);
      if (this.hour >= 0) this.show(this.hour);
    }
    this.ticks();
    this.label();
  }

  // the city's dates (phenology.json), for the trees' colours along the year
  setCity(city: City) {
    this.city = city;
    $('#date .year').style.background = seasons(city);
    this.showDay(this.day);
  }

  private ticks() {
    ticks(this.slider, this.thumb, clamp(this.hour, 0, 24) / 24, (t) => +t.style.getPropertyValue('--h') / 24);
    ticks(this.dateSlider, this.dateThumb, (this.day - 1) / (yearDays() - 1), (t) => +t.style.getPropertyValue('--d'));
  }

  setWeather(k: Kind) {
    this.kind = k;
    for (const b of this.card.querySelectorAll<HTMLButtonElement>('#weather button')) b.setAttribute('aria-pressed', String(b.dataset.w === k));
    this.btn.dataset.w = k;
    this.label();
  }

  // snow only around dates it has fallen on in Budapest (season.ts)
  offerSnow(ok: boolean) {
    const b = $<HTMLButtonElement>('#weather button[data-w="snow"]');
    b.disabled = !ok;
    b.title = ok ? '' : T().noSnow;
  }

  setLive(on: boolean) {
    this.isLive = on;
    this.live.setAttribute('aria-pressed', String(on));
    this.btn.classList.toggle('live', on);
    this.label();
  }

  private label() {
    const t = T();
    this.btn.setAttribute('aria-label', t.timeBtn(this.day ? dayName(this.day, true) : '', clock(this.hour), t[this.kind].toLowerCase(), this.isLive));
    this.btn.title = t.dateTime;
    this.live.title = t.liveTitle;
    this.dateSlider.setAttribute('aria-label', t.date);
    this.slider.setAttribute('aria-label', t.time);
    $('#weather').setAttribute('aria-label', t.weather);
    if (!this.day) return;
    const b = $<HTMLButtonElement>('#weather button[data-w="snow"]');
    if (b.disabled) b.title = t.noSnow;
  }
}
