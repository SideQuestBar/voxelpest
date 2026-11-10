// The page round the map: the mode switch (map, walk, drive), the language switch, the places menu with its search,
// the time of day and the weather (ui/time.ts), names, the help line for the current mode, the tiles still loading, the
// speedometer, the about box.
import { appVersion } from './desktop';
import { lang, onLang, setLang, T, viewName, type Lang } from '../i18n';
import type { Kind } from '../engine/weather';
import type { Meta, View } from '../meta';
import { $, esc, isTouch } from '../util';
import { TimeCard } from './time';

export type Mode = 'map' | 'walk' | 'drive';

const viewOf = (views: [string, View][], k: string) => views.find(([key]) => key === k)![1];

export interface UiHandlers {
  mode(m: Mode): void;
  place(key: string): void;
  bar(): void;
  hour(h: number): void;
  date(d: number): void;
  weather(k: Kind): void;
  live(on: boolean): void;
  names(on: boolean): void;
  tutorial(): void;
}

export class Ui {
  private mode: Mode = 'map';
  private pad = false;
  private toastTimer = 0;
  private readonly views: [string, View][];
  private readonly names = $<HTMLButtonElement>('#names');
  private readonly time: TimeCard;
  private readonly tileFill = $('#tilebar i');
  private readonly tileText = $('#status .txt');
  private busy = false;
  private burst = 0;
  private idleSince = 0;
  private lastTiles = '';

  constructor(meta: Meta, private readonly on: UiHandlers) {
    this.views = Object.entries(meta.views).filter(([k]) => k !== 'sidequest');
    for (const b of document.querySelectorAll<HTMLButtonElement>('#modes button')) b.onclick = () => {
      // pressed at once: walking and driving start once the streets round the spot have loaded
      if (b.getAttribute('aria-pressed') !== 'true') b.classList.add('going');
      on.mode(b.dataset.mode as Mode);
    };
    for (const b of document.querySelectorAll<HTMLButtonElement>('#lang button')) b.onclick = () => setLang(b.dataset.lang as Lang);
    this.time = new TimeCard({ hour: on.hour, date: on.date, weather: on.weather, live: on.live, opened: () => this.closePlaces() });
    this.names.onclick = () => {
      const show = this.names.getAttribute('aria-pressed') !== 'true';
      this.setNames(show);
      on.names(show);
    };
    // the tiles chip sits over the bar, however tall that is
    const bar = $('#bar');
    new ResizeObserver(() => document.documentElement.style.setProperty('--bar-h', `${bar.offsetHeight}px`)).observe(bar);
    $('#bar-go').onclick = () => { on.bar(); this.closePlaces(); };
    $('#tut-btn').onclick = () => on.tutorial();
    const toggle = $('#places-toggle'), panel = $('#places-panel'), search = $<HTMLInputElement>('#places-search');
    toggle.onclick = () => {
      panel.hidden = !panel.hidden;
      toggle.setAttribute('aria-expanded', String(!panel.hidden));
      if (!panel.hidden) {
        this.time.open(false);
        if (!isTouch()) search.focus();
      }
    };
    search.oninput = () => this.list(search.value);
    search.onkeydown = (e) => {
      if (e.key === 'Enter') document.querySelector<HTMLButtonElement>('#places-list button')?.click();
    };
    document.addEventListener('pointerdown', (e) => { if (!panel.hidden && !$('#places').contains(e.target as Node)) this.closePlaces(); }, true);
    addEventListener('keydown', (e) => {
      if (e.key !== 'Escape' || panel.hidden) return;
      const inside = $('#places').contains(document.activeElement);
      this.closePlaces();
      if (inside) toggle.focus();
    });
    const about = $<HTMLDialogElement>('#about');
    $('#about-btn').onclick = () => about.showModal();
    about.onclick = (e) => { if (e.target === about) about.close(); };
    $('#about-close').onclick = () => about.close();
    void appVersion().then((v) => { $('#version').textContent = `v${v}`; });
    this.text();
    onLang(() => this.text());
  }

  private closePlaces() {
    $('#places-panel').hidden = true;
    $('#places-toggle').setAttribute('aria-expanded', 'false');
  }

  private list(q = '') {
    const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
    const n = norm(q);
    const ul = $('#places-list');
    ul.innerHTML = '';
    const order = this.placeKeys();
    const items = order.map((k) => [k, viewOf(this.views, k)] as const)
      .filter(([, v]) => !n || norm(v.label).includes(n) || norm(v.label_hu ?? '').includes(n));
    for (const [k, v] of items) {
      const li = document.createElement('li'), b = document.createElement('button');
      b.textContent = viewName(v);
      b.onclick = () => { this.on.place(k); this.closePlaces(); };
      li.appendChild(b);
      ul.appendChild(li);
    }
  }

  private text() {
    const t = T();
    for (const e of document.querySelectorAll<HTMLElement>('[data-t]')) {
      const v = t[e.dataset.t as keyof typeof t];
      if (typeof v === 'string') e.textContent = v;
    }
    $<HTMLInputElement>('#places-search').placeholder = t.search;
    $('#about-text').innerHTML = t.aboutHtml;
    $('#about-btn').setAttribute('aria-label', t.about);
    $('#tut-btn').setAttribute('aria-label', t.tutAgain);
    $('#tut-btn').title = t.tutAgain;
    this.names.setAttribute('aria-label', t.names);
    document.title = `${t.title} ${t.titleTail}`;
    $('#credits').textContent = t.credits;
    for (const b of document.querySelectorAll<HTMLButtonElement>('#lang button')) b.setAttribute('aria-pressed', String(b.dataset.lang === lang()));
    this.list($<HTMLInputElement>('#places-search').value);
    this.setMode(this.mode);
    this.lastTiles = '';
  }

  setMode(m: Mode) {
    this.mode = m;
    document.body.dataset.mode = m;
    for (const b of document.querySelectorAll<HTMLButtonElement>('#modes button')) {
      b.setAttribute('aria-pressed', String(b.dataset.mode === m));
      b.classList.remove('going');
    }
    const touch = isTouch();
    $('#touch').hidden = !touch || m === 'map';
    $('#touch').dataset.mode = m;
    $('#hud').hidden = m !== 'drive';
  }

  setPad(on: boolean) {
    if (on === this.pad) return;
    this.pad = on;
    this.setMode(this.mode);
    if (on) this.toast(T().padOn);
  }

  toast(text: string) {
    const e = $('#toast');
    e.textContent = text;
    e.hidden = false;
    clearTimeout(this.toastTimer);
    this.toastTimer = window.setTimeout(() => { e.hidden = true; }, 2200);
  }

  // the places in the Places list's order, for the menu (ui/menu.ts)
  placeKeys() {
    return [...this.views].sort((a, b) => (a[0] === 'overview' ? -1 : b[0] === 'overview' ? 1 : viewName(a[1]).localeCompare(viewName(b[1]), lang())))
      .map(([k]) => k);
  }

  setHour(h: number) { this.time.show(h); }
  peekHour() { this.time.peek(); }
  setDay(d: number) { this.time.showDay(d); }
  setCity(city: { leaf: number; colour: number; fall: number } | undefined) { this.time.setCity(city); }
  offerSnow(ok: boolean) { this.time.offerSnow(ok); }
  get timeOpen() { return this.time.isOpen; }
  setWeather(k: Kind) { this.time.setWeather(k); }
  setLive(on: boolean) { this.time.setLive(on); }
  setNames(on: boolean) { this.names.setAttribute('aria-pressed', String(on)); }

  // tiles on their way: a chip at the bottom in the middle, with how much of this batch has arrived along its edge; it
  // fades once nothing has been loading for a moment
  tiles(loading: number, meshed: number) {
    if (loading > 0) {
      this.idleSince = 0;
      if (!this.busy) {
        this.busy = true;
        this.burst = meshed;
        this.tileFill.style.transition = 'none';
        this.tileFill.style.transform = 'scaleX(0)';
        void this.tileFill.offsetWidth;
        this.tileFill.style.transition = '';
        document.body.classList.add('tiles-loading');
      }
    } else if (this.busy) {
      const now = performance.now();
      if (!this.idleSince) this.idleSince = now;
      else if (now - this.idleSince > 400) {
        this.busy = false;
        document.body.classList.remove('tiles-loading');
      }
    }
    const key = `${loading}/${meshed}`;
    if (key === this.lastTiles) return;
    this.lastTiles = key;
    const got = meshed - this.burst;
    this.tileFill.style.transform = `scaleX(${loading ? Math.max(0.06, got / (got + loading)) : 1})`;
    if (loading) this.tileText.textContent = T().loadingTiles(loading);
  }

  speed(kmh: number) { $('#speed').textContent = String(Math.round(kmh)); }

  hint(text: string | null) {
    const e = $('#hint');
    e.hidden = !text;
    if (text) e.innerHTML = esc(text);
  }
}
