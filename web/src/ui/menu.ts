// The menu over the map, made for a controller: its Menu button opens and closes it (in the desktop app Esc opens it
// too), the D-pad or the left stick moves (held, it repeats), A or ▶ opens and chooses, B or ◀ goes back, LB / RB jump
// down a long list. Places and Time & weather are submenus; then SideQuest Bar, the help box, and full screen (the
// website's where its button shows, else the desktop app's, with Quit: ui/desktop.ts). Mouse, touch and keys work on it
// as well, and the focused item is lit whatever moved the focus.
import { track } from '../analytics';
import { PAD, type Input } from '../controls/input';
import { onLang, T } from '../i18n';
import { clamp, esc, h, isTouch } from '../util';
import { fullscreenAlways, type DesktopHost } from './desktop';
import type { FullScreen } from './fullscreen';

// a row of Time & weather: its label and value, what ◀ ▶ and A do; `on` draws a switch in place of a value
export interface MenuRow { label(): string; value?(): string; on?(): boolean; step?(d: number): void; press?(): void }

export interface MenuHandlers {
  places(): [string, string][];  // key and name, in the Places list's order
  place(key: string): void;
  bar(): void;
  help(): void;
  rows: MenuRow[];
  pad(): boolean;
}

type Page = 'top' | 'places' | 'time';
type Dir = 'u' | 'd' | 'l' | 'r';

// what an Esc closes rather than opening the desktop app's menu
const POPUPS = 'dialog[open], #places-panel:not([hidden]), #time-card:not([hidden]), #mc-panel:not([hidden])';
const chev = (d: number) => `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="${d > 0 ? 'M6 3l5 5-5 5' : 'M10 3L5 8l5 5'}" fill="none"
  stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

export class Menu {
  private readonly dlg = h('dialog', { id: 'app-menu', 'aria-labelledby': 'am-title' });
  private page: Page = 'top';
  private at = 0;              // the top level's focused item, kept between openings
  private place = '';          // the place chosen last
  private full = false;        // the desktop app's window
  private next: Partial<Record<Dir, number>> | null = null;  // when a held direction repeats
  private timer = 0;
  private noteTimer = 0;

  constructor(private readonly host: DesktopHost | null, private readonly fs: FullScreen | null, private readonly on: MenuHandlers) {
    document.body.appendChild(this.dlg);
    this.dlg.addEventListener('click', (e) => this.click(e));
    this.dlg.addEventListener('pointermove', (e) => {
      const b = (e.target as Element).closest?.<HTMLElement>('.am-item');
      if (e.pointerType === 'mouse' && b && b !== document.activeElement) b.focus({ preventScroll: true });
    });
    this.dlg.addEventListener('focusin', (e) => {
      const b = e.target as HTMLElement;
      if (this.page === 'top' && b.classList.contains('am-item')) this.at = this.items().indexOf(b);
    });
    // keys stay in the menu: the map's own (controls/input.ts) listen on window
    this.dlg.addEventListener('keydown', (e) => { this.key(e); e.stopPropagation(); });
    this.dlg.addEventListener('close', () => { clearInterval(this.timer); this.page = 'top'; });
    if (host) {
      // in the capture phase, so it sees the cards as they were before this Esc closes one
      addEventListener('keydown', (e) => {
        if (e.key === 'F11') { e.preventDefault(); if (!e.repeat && !fullscreenAlways) void this.setFull(!this.full); return; }
        if (e.key !== 'Escape' || e.repeat || document.pointerLockElement || document.querySelector(POPUPS)) return;
        e.preventDefault();
        this.show();
      }, true);
      void host.fullscreen().then((f) => { this.full = f; }, () => {});
    }
    for (const ev of ['fullscreenchange', 'webkitfullscreenchange']) document.addEventListener(ev, () => this.values());
    onLang(() => { if (this.open) this.render(); });
  }

  get open() { return this.dlg.open; }

  show() {
    if (this.open) return;
    track('menu');
    document.exitPointerLock?.();
    this.page = 'top';
    this.next = null;
    this.dlg.showModal();
    this.render();
    this.timer = window.setInterval(() => this.values(), 1000);  // the live clock
    // the window may have changed under us (the compositor's own full screen key)
    if (this.host) void this.host.fullscreen().then((f) => { this.full = f; this.values(); }, () => {});
  }

  close() {
    if (this.open) this.dlg.close();
  }

  toggle() {
    if (this.open) this.close();
    else this.show();
  }

  // a controller while the menu is open (main.ts mutes it for the map afterwards)
  pad(i: Input) {
    if (i.pressed(PAD.MENU)) return this.close();
    if (i.pressed(PAD.B)) return this.back();
    if (i.pressed(PAD.A)) {
      const b = this.focused();
      return b ? this.choose(b) : this.focus(0);
    }
    if (i.pressed(PAD.RB) || i.pressed(PAD.LB)) this.step(i.pressed(PAD.RB) ? 8 : -8, false);
    const p = i.pad, held = (b: number) => !!p.held[b], v = Math.abs(p.ly) > Math.abs(p.lx);
    const dirs: [Dir, boolean][] = [['u', held(PAD.UP) || (v && p.ly < -0.5)], ['d', held(PAD.DOWN) || (v && p.ly > 0.5)],
      ['l', held(PAD.LEFT) || (!v && p.lx < -0.5)], ['r', held(PAD.RIGHT) || (!v && p.lx > 0.5)]];
    if (!this.next) this.next = Object.fromEntries(dirs.filter(([, on]) => on).map(([k]) => [k, Infinity]));  // held since before
    const now = performance.now();
    for (const [k, on] of dirs) {
      const t = this.next[k];
      if (!on) delete this.next[k];
      else if (t === undefined) { this.next[k] = now + 380; this.move(k, false); }
      else if (now >= t) { this.next[k] = now + 110; this.move(k, true); }
      if (!this.open) return;
    }
  }

  private items() { return [...this.dlg.querySelectorAll<HTMLElement>('.am-item')]; }

  private focused() {
    const a = document.activeElement as HTMLElement | null;
    return a?.classList.contains('am-item') && this.dlg.contains(a) ? a : null;
  }

  private focus(i: number) {
    const all = this.items(), b = all[clamp(i, 0, all.length - 1)];
    if (!b) return;
    b.focus({ preventScroll: true });
    b.scrollIntoView({ block: 'nearest' });
  }

  // up or down; a repeat (a held direction, LB / RB) stops at the ends rather than wrapping round
  private step(d: number, wrap = true) {
    const all = this.items(), at = all.indexOf(this.focused()!);
    if (at < 0) return this.focus(d > 0 ? 0 : all.length - 1);
    this.focus(wrap && Math.abs(d) === 1 ? (at + d + all.length) % all.length : at + d);
  }

  private move(k: Dir, repeat: boolean) {
    if (k === 'u' || k === 'd') return this.step(k === 'd' ? 1 : -1, !repeat);
    const d = k === 'r' ? 1 : -1, b = this.focused(), row = b?.dataset.row ? this.on.rows[+b.dataset.row] : null;
    if (row?.step) { row.step(d); this.values(); return; }
    if (repeat) return;
    if (d > 0 && b?.classList.contains('am-sub')) this.choose(b);
    else if (d < 0 && this.page !== 'top') this.back();
  }

  private key(e: KeyboardEvent) {
    const dir = ({ ArrowUp: 'u', ArrowDown: 'd', ArrowLeft: 'l', ArrowRight: 'r' } as Record<string, Dir>)[e.key];
    if (dir) this.move(dir, e.repeat);
    else if (e.key === 'Escape' || e.key === 'Backspace') this.back();  // a submenu goes back rather than closing
    else if (e.key === 'PageDown' || e.key === 'PageUp') this.step(e.key === 'PageDown' ? 8 : -8, false);
    else if (e.key === 'Home' || e.key === 'End') this.focus(e.key === 'Home' ? 0 : 1e4);
    else return;
    e.preventDefault();
  }

  private click(e: MouseEvent) {
    if (e.target === this.dlg) return this.close();  // the backdrop
    const t = e.target as Element;
    if (t.closest('.am-back')) return this.back();
    const b = t.closest<HTMLElement>('.am-item'), d = t.closest<HTMLElement>('[data-d]');
    if (b) this.choose(b, d ? +d.dataset.d! : 0);
  }

  private choose(b: HTMLElement, d = 0) {
    const key = b.dataset.key, row = b.dataset.row;
    if (key) {
      this.place = key;
      this.close();
      return this.on.place(key);
    }
    if (row) {
      const r = this.on.rows[+row];
      if (d) r.step?.(d);
      else r.press?.();
      return this.values();
    }
    const act = b.dataset.act;
    if (act === 'places' || act === 'time') return this.go(act);
    if (act === 'full') return void this.setFull(!this.isFull());
    this.close();
    if (act === 'bar') this.on.bar();
    if (act === 'help') this.on.help();
    if (act === 'quit') void this.host?.quit();
  }

  private go(p: Page) {
    this.page = p;
    this.render();
  }

  private back() {
    if (this.page === 'top') return this.close();
    this.go('top');
  }

  private isFull() { return this.host ? this.full : !!this.fs?.on(); }

  private async setFull(on: boolean) {
    if (this.host) {
      try { this.full = await this.host.fullscreen(on); } catch { /* the window stays as it is */ }
    } else if (this.fs && !(await this.fs.toggle())) this.note(T().fsRefused);
    this.values();
  }

  // a line under the items for a few seconds
  private note(text: string) {
    const p = this.dlg.querySelector<HTMLElement>('.am-note');
    if (!p) return;
    p.textContent = text;
    p.hidden = false;
    clearTimeout(this.noteTimer);
    this.noteTimer = window.setTimeout(() => { p.hidden = true; }, 4000);
  }

  private summary() { return this.on.rows.filter((r) => r.value).map((r) => r.value!()).join(' · '); }

  // the values that change while the menu is open: the rows, the time on the top level, the full screen switch
  private values() {
    if (!this.open) return;
    for (const b of this.dlg.querySelectorAll<HTMLElement>('[data-row]')) {
      const r = this.on.rows[+b.dataset.row!], v = b.querySelector('.am-val');
      if (r.on) b.setAttribute('aria-pressed', String(r.on()));
      if (v && r.value && v.textContent !== r.value()) v.textContent = r.value();
    }
    const time = this.dlg.querySelector('[data-act="time"] .am-val');
    if (time) time.textContent = this.summary();
    this.dlg.querySelector('[data-act="full"]')?.setAttribute('aria-pressed', String(this.isFull()));
  }

  private render() {
    const t = T(), p = this.page, kbd = (k: string) => (isTouch() ? '' : `<kbd>${k}</kbd>`), more = `<i class="am-more">${chev(1)}</i>`;
    let head = `${t.title} <em>${t.titleTail}</em>`, list: string, hint = t.menuPad, focus = 0;
    if (p === 'top') {
      const full = this.host ? !fullscreenAlways : !!this.fs;
      list = `<button class="am-item" data-act="resume">${t.menuResume}${kbd('Esc')}</button>
        <button class="am-item am-sub" data-act="places">${t.places}${more}</button>
        <button class="am-item am-sub" data-act="time">${t.menuTime}<span class="am-val"></span>${more}</button>
        <button class="am-item" data-act="bar">${t.goBar}</button>
        <button class="am-item" data-act="help">${t.menuHelp}</button>
        ${full ? `<button class="am-item" data-act="full" aria-pressed="false">${t.menuFull}<span class="am-switch" aria-hidden="true"></span>${this.host ? kbd('F11') : ''}</button>` : ''}
        ${this.host ? `<button class="am-item am-quit" data-act="quit">${t.menuQuit}</button>` : ''}`;
      focus = this.at;
    } else {
      head = `<button class="am-back" aria-label="${t.menuBack}">${chev(-1)}</button>${p === 'places' ? t.places : t.menuTime}`;
      if (p === 'places') {
        const places = this.on.places();
        list = places.map(([k, name]) => `<button class="am-item am-place" data-key="${k}">${esc(name)}</button>`).join('');
        focus = Math.max(0, places.findIndex(([k]) => k === this.place));
      } else {
        list = this.on.rows.map((r, i) => `<button class="am-item am-row" data-row="${i}"${r.on ? ' aria-pressed="false"' : ''}>${esc(r.label())}${r.on
          ? '<span class="am-switch" aria-hidden="true"></span>'
          : `<span class="am-step">${r.step ? `<i data-d="-1">${chev(-1)}</i>` : ''}<span class="am-val"></span>${r.step ? `<i data-d="1">${chev(1)}</i>` : ''}</span>`}</button>`).join('');
        hint = t.menuPadRows;
      }
    }
    this.dlg.innerHTML = `<div class="am am-${p}"><h2 id="am-title">${head}</h2><div class="am-list">${list}</div>
      <p class="am-note" hidden></p>${this.on.pad() ? `<p class="am-pad">${hint}</p>` : ''}</div>`;
    // a direction still held from the page before waits to be let go
    if (this.next) for (const k of Object.keys(this.next) as Dir[]) this.next[k] = Infinity;
    this.values();
    this.focus(focus);
  }
}
