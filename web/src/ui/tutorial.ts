// The first-run overlay and the help box, in three tabs: how to move round the map, as small looping animations for
// what is in hand (touch, mouse and keys, or a controller once one is connected), walking, and the vehicles (their
// controls as a list). The first walk and the first drive open their tab once (flags in localStorage). "Got it"
// (A or B on a controller: main.ts), Esc or a tap outside dismisses it for good (a flag in localStorage); the ? button
// in the bottom bar brings it back. ?tutorial=1 forces it, ?tutorial=0 hides it.
import { onLang, T } from '../i18n';
import { h, isTouch, storage } from '../util';
import { desktop } from './desktop';

const KEY = 'voxelpest-tutorial';
export type HelpTab = 'map' | 'walk' | 'drive';
const TABS: HelpTab[] = ['map', 'walk', 'drive'];
const INK = '#1d2328';

// a patch of the city seen from above, larger than its tile so it can slide, turn and zoom without showing an edge
const CITY = (() => {
  const blocks = [[14, 30, 14, 20, '#ece0c2'], [34, 32, 16, 18, '#c9a77a'], [58, 30, 34, 20, '#b5513f'], [100, 32, 22, 18, '#ece0c2'],
    [128, 30, 20, 20, '#c9a77a'], [14, 64, 12, 30, '#b5513f'], [34, 64, 16, 30, '#ece0c2'], [58, 64, 14, 14, '#6aa893'], [58, 82, 14, 12, '#c9a77a'],
    [80, 64, 14, 30, '#c9a77a'], [100, 64, 22, 30, '#73925a'], [128, 64, 20, 26, '#b5513f'], [14, 140, 18, 14, '#c9a77a'], [40, 142, 22, 14, '#ece0c2'],
    [100, 136, 18, 16, '#ece0c2'], [126, 132, 22, 20, '#c9a77a'], [2, 2, 22, 18, '#c9a77a'], [34, 4, 26, 16, '#ece0c2'], [72, 2, 20, 18, '#c9a77a'],
    [104, 4, 18, 16, '#b5513f'], [134, 2, 22, 18, '#ece0c2']] as const;
  const rects = blocks.map(([x, y, w, hh, c]) => `<rect x="${x + 2}" y="${y + 2}" width="${w}" height="${hh}" fill="rgba(0,0,0,.13)"/><rect x="${x}" y="${y}" width="${w}" height="${hh}" fill="${c}"/>`).join('');
  return `<svg viewBox="0 0 160 160" aria-hidden="true"><rect width="160" height="160" fill="#e3ddcd"/>
    <path d="M0 24h160M0 57h160M0 100h160M30 0v160M54 0v160M96 0v160M124 0v160" stroke="#f4f0e7" stroke-width="5"/>
    <path d="M0 112C40 104 80 124 160 100v18C80 142 40 122 0 130z" fill="#8fb5c9"/>
    <rect x="74" y="100" width="8" height="34" fill="#cdb994" transform="rotate(-14 78 117)"/>${rects}
    <circle cx="65" cy="71" r="5" fill="#4e8a75"/></svg>`;
})();

const finger = (x: number, y: number) =>
  `<g transform="translate(${x} ${y})"><circle r="9.5" fill="rgba(255,255,255,.45)"/><circle r="5.5" fill="#fff" stroke="${INK}" stroke-width="1.5"/></g>`;

// a mouse with one part lit: the left or right button, or the wheel
const mouse = (lit: 'l' | 'r' | 'w') => `<g transform="translate(76 66)">
  <rect x="-10" y="-14" width="20" height="28" rx="10" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
  ${lit === 'w' ? '' : `<path d="${lit === 'l' ? 'M0 -14A10 10 0 0 0 -10 -4V-2H0z' : 'M0 -14A10 10 0 0 1 10 -4V-2H0z'}" fill="var(--accent)"/>`}
  <path d="M-10 -2H10M0 -14V-2" stroke="${INK}" stroke-width="1.2"/>
  <rect x="-1.6" y="-10" width="3.2" height="6" rx="1.6" fill="${lit === 'w' ? 'var(--accent)' : INK}"/></g>`;

const key = (x: number, y: number, k: string, lit = -1) => `<g transform="translate(${x} ${y})"${lit >= 0 ? ` class="key" style="animation-delay: ${lit * 0.85}s"` : ''}>
  <rect x="-6.5" y="-6.5" width="13" height="13" rx="2.5" stroke="${INK}" stroke-width="1.3"/><text y="3.2" text-anchor="middle">${k}</text></g>`;

// a controller with one part lit: an Xbox pad's layout and proportions (about 3 : 2 with the grips), the sticks
// offset, ABXY in their colours; View and Menu are the two dots between the sticks
const controller = (lit: 'ls' | 'rs' | 'tr' | 'menu', move = '') => {
  const on = (p: string) => (p === lit ? 'var(--accent)' : '#fff');
  const blink = (p: string) => (p === lit ? ' class="blink"' : '');
  const stick = (p: 'ls' | 'rs', x: number, y: number) => `<circle cx="${x}" cy="${y}" r="5.4" fill="#e6e3dc" stroke="${INK}" stroke-width="1.1"/>
    <g${p === lit ? ` class="go" style="${move}"` : ''}><circle cx="${x}" cy="${y}" r="3.6" fill="${on(p)}" stroke="${INK}" stroke-width="1.1"/></g>`;
  const face = ([x, y, c]: [number, number, string]) => `<circle cx="${x}" cy="${y}" r="2" fill="${c}" stroke="${INK}" stroke-width=".6"/>`;
  return `<g transform="translate(50 69)">
    <path d="M-27.2 -6C-27 -13.5-21.5 -19.5-13.5 -19.5H-10V-10Z" fill="${on('tr')}" stroke="${INK}" stroke-width="1.2"${blink('tr')}/>
    <path d="M27.2 -6C27 -13.5 21.5 -19.5 13.5 -19.5H10V-10Z" fill="${on('tr')}" stroke="${INK}" stroke-width="1.2"${blink('tr')}/>
    <path d="M-16 -15C-6 -17.5 6 -17.5 16 -15C23 -14 26.5 -10 28 -4C30 4 31.5 13 30 20C28.5 25.5 21.5 26 19 21C17 16.5 14 12 9 12H-9C-14 12-17 16.5-19 21C-21.5 26-28.5 25.5-30 20C-31.5 13-30 4-28 -4C-26.5 -10-23 -14-16 -15Z" fill="#fff" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"/>
    <circle cy="-10.5" r="2.6" fill="#e6e3dc" stroke="${INK}" stroke-width=".9"/>
    <circle cx="-5" cy="-4.5" r="1.2" fill="${INK}"/><circle cx="5" cy="-4.5" r="1.2" fill="${lit === 'menu' ? 'var(--accent)' : INK}"/>
    ${lit === 'menu' ? `<circle cx="5" cy="-4.5" r="2.7" fill="none" stroke="var(--accent)" stroke-width="1.1" class="blink"/>` : ''}
    ${stick('ls', -17, -4.5)}${stick('rs', 9, 4.5)}
    <path d="M-10.2 0.7H-7.8V3.3H-5.2V5.7H-7.8V8.3H-10.2V5.7H-12.8V3.3H-10.2Z" fill="${INK}" stroke="${INK}" stroke-width=".6" stroke-linejoin="round"/>
    ${([[17, -8.6, '#e2b23a'], [20.6, -5, '#c8463a'], [13.4, -5, '#3a6fc8'], [17, -1.4, '#4f9a3a']] as [number, number, string][]).map(face).join('')}</g>`;
};

// the menu over the map, its lit row stepping down
const MENU = `<rect x="29" y="9" width="42" height="33" rx="4" fill="#faf7f1" stroke="${INK}" stroke-width="1.2"/>
  <g class="go" style="--a: translate(0, 0); --b: translate(0, 7px)"><rect x="32" y="12.5" width="36" height="6" rx="1.6" fill="${INK}"/></g>
  <path d="M35.5 15.5h17M35.5 22.5h22M35.5 29.5h14M35.5 36.5h19" stroke="#a3a8ab" stroke-width="1.6" stroke-linecap="round"/>`;

const TILT = 'perspective(260px) rotateX(46deg)';
type Tile = { cap: string; map: string; hand: string; cls?: string };

function tiles(kind: 'touch' | 'mouse' | 'pad'): Tile[] {
  const t = T();
  if (kind === 'touch') return [
    { cap: t.tDrag, map: '--a: translate(0, 0); --b: translate(18%, -12%)',
      hand: `<g class="fing"><g class="go" style="--a: translate(0, 0); --b: translate(18px, -12px)">${finger(40, 60)}</g></g>` },
    { cap: t.tPinch, map: '--a: scale(1); --b: scale(1.75)',
      hand: `<g class="fing"><g class="go" style="--a: translate(-7px, -7px); --b: translate(-22px, -22px)">${finger(50, 50)}</g>
        <g class="go" style="--a: translate(7px, 7px); --b: translate(22px, 22px)">${finger(50, 50)}</g></g>` },
    { cap: t.tTwist, map: '--a: rotate(0deg); --b: rotate(65deg)',
      hand: `<g class="fing"><g class="go spin" style="--a: rotate(0deg); --b: rotate(65deg)">${finger(30, 50)}${finger(70, 50)}</g></g>` },
    { cap: t.tTilt, map: '--a: perspective(260px) rotateX(0deg); --b: perspective(260px) rotateX(52deg)',
      hand: `<g class="fing"><g class="go" style="--a: translate(0, 0); --b: translate(0, -26px)">${finger(38, 74)}${finger(62, 74)}</g></g>` },
  ];
  if (kind === 'mouse') return [
    { cap: t.mTurn, map: `--a: ${TILT} rotate(0deg); --b: ${TILT} rotate(70deg)`,
      hand: `<g class="go" style="--a: translate(-12px, 0); --b: translate(10px, 0)">${mouse('l')}</g>` },
    { cap: t.mMove, map: `--a: ${TILT} translate(0, 0); --b: ${TILT} translate(-16%, 14%)`,
      hand: `<g class="go" style="--a: translate(0, 0); --b: translate(-12px, 9px)">${mouse('r')}</g>` },
    { cap: t.mZoom, map: `--a: ${TILT} scale(1); --b: ${TILT} scale(1.7)`,
      hand: `${mouse('w')}<g class="go" style="--a: translate(0, 4px); --b: translate(0, -4px)"><path d="M72 46l4-4 4 4M72 51l4-4 4 4" fill="none" stroke="${INK}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></g>` },
    { cap: t.mKeys, cls: 'keys', map: `--k0: ${TILT} translate(0, 0); --k1: ${TILT} translate(0, 14%); --k2: ${TILT} translate(-14%, 14%); --k3: ${TILT} translate(-14%, 0)`,
      hand: `<g class="caps">${key(34, 66, 'Q')}${key(50, 66, 'W', 0)}${key(66, 66, 'E')}${key(34, 82, 'A', 3)}${key(50, 82, 'S', 2)}${key(66, 82, 'D', 1)}</g>` },
  ];
  return [
    { cap: t.pMove, map: '--a: translate(0, 0); --b: translate(-14%, 12%)', hand: controller('ls', '--a: translate(0, 0); --b: translate(0, -2.5px)') },
    { cap: t.pTurn, map: `--a: ${TILT} rotate(0deg); --b: ${TILT} rotate(-60deg)`, hand: controller('rs', '--a: translate(0, 0); --b: translate(2.5px, 0)') },
    { cap: t.pZoom, map: `--a: ${TILT} scale(1); --b: ${TILT} scale(1.6)`, hand: controller('tr') },
    { cap: t.padMenu, map: '--a: translate(0, 0); --b: translate(16%, 10%)', hand: `${MENU}${controller('menu')}` },
  ];
}

// a mode's controls as rows of [what to press, what it does]: keycaps (the WASD and arrow clusters as on a keyboard),
// a controller's buttons in their colours, sticks and triggers as pills, touch gestures as words
function controls(kind: 'touch' | 'mouse' | 'pad', mode: 'walk' | 'drive'): [string, string][] {
  const a = T().act;
  const k = (s: string, cls = '') => `<kbd class="${cls}">${s}</kbd>`;
  const cluster = (up: string, l: string, d: string, r: string) => `<span class="kc"><i></i>${k(up)}<i></i>${k(l)}${k(d)}${k(r)}</span>`;
  const or = `<em>${a.or}</em>`;
  const btn = (b: 'A' | 'B' | 'X' | 'Y') => `<kbd class="pb pb-${b}">${b}</kbd>`, pill = (s: string) => k(s, 'pill'), word = (s: string) => k(s, 'word');
  if (kind === 'mouse') return mode === 'walk'
    ? [[cluster('W', 'A', 'S', 'D'), a.walk], [word(a.mouse), a.look], [k('Shift', 'wide'), a.run], [k('Space', 'wide'), a.jump], [k('Esc'), a.free]]
    : [[`${k('W')}${k('S')}${or}${k('↑')}${k('↓')}`, a.gasBrake], [`${k('A')}${k('D')}${or}${k('←')}${k('→')}`, a.steer], [k('Space', 'wide'), a.hand],
      [word(a.mouse), a.lookDrag], [k('R'), a.road], [k('V'), a.next], [k('L'), a.blue]];
  if (kind === 'pad') return mode === 'walk'
    ? [[pill('LS'), a.walk], [pill('RS'), a.look], [pill('LS') , a.runPad], [btn('A'), a.jump]]
    : [[pill('RT'), a.gas], [pill('LT'), a.brake], [pill('LS'), a.steer], [pill('RS'), a.cam], [btn('A'), a.hand], [btn('B'), a.boost], [btn('Y'), a.road],
      [`${pill('LB')}${pill('RB')}`, a.nextPad], [btn('X'), a.blue]];
  return mode === 'walk'
    ? [[word(a.stick), a.walk], [word(a.side), a.look], [word(a.dtap), a.jump]]
    : [[word(a.stick), a.steer], [word(a.pedals), a.gasBrake], [word(a.drag), a.look]];
}

export class Tutorial {
  private readonly dlg = h('dialog', { id: 'tutorial', 'aria-labelledby': 'tut-title' });

  constructor(private readonly pad: () => boolean) {
    document.body.appendChild(this.dlg);
    this.dlg.addEventListener('close', () => storage(KEY, '1'));  // Esc too
    this.dlg.addEventListener('click', (e) => { if (e.target === this.dlg) this.close(); });
    onLang(() => this.refresh());
  }

  get open() { return this.dlg.open; }
  private tab: HelpTab = 'map';

  // the first time on foot or in a vehicle: that tab, once
  first(tab: 'walk' | 'drive') {
    const q = new URLSearchParams(location.search).get('tutorial'), k = `${KEY}-${tab}`;
    if (q === '0' || storage(k) === '1') return;
    storage(k, '1');
    this.show(tab);
  }

  // the next or previous tab (a controller's LB / RB or D-pad)
  step(d: number) { this.pick(TABS[(TABS.indexOf(this.tab) + d + TABS.length) % TABS.length]); }

  private pick(tab: HelpTab) {
    this.tab = tab;
    this.render();
    this.dlg.querySelector<HTMLButtonElement>('#tut-ok')?.focus();
  }

  // once the map is in: unless dismissed before (or ?tutorial=0); ?tutorial=1 shows it every time
  auto() {
    const q = new URLSearchParams(location.search).get('tutorial');
    if (q === '0' || (q !== '1' && storage(KEY) === '1')) return;
    this.show();
  }

  show(tab: HelpTab = 'map') {
    this.tab = tab;
    this.render();
    if (!this.dlg.open) this.dlg.showModal();
    this.dlg.querySelector<HTMLButtonElement>('#tut-ok')?.focus();
  }

  close() {
    storage(KEY, '1');
    if (this.dlg.open) this.dlg.close();
  }

  // the language changed, or a controller came or went
  refresh() {
    if (!this.dlg.open) return;
    this.render();
    this.dlg.querySelector<HTMLButtonElement>('#tut-ok')?.focus();
  }

  private render() {
    const t = T(), touch = isTouch(), kind = this.pad() ? 'pad' : touch ? 'touch' : 'mouse';
    this.dlg.dataset.kind = kind;
    const tab = this.tab, names = { map: t.tutTabMap, walk: t.tutTabWalk, drive: t.tutTabDrive };
    const list = (m: 'walk' | 'drive') => `<ul class="tut-list">${controls(kind, m).map(([keys, what]) => `<li><span class="keys">${keys}</span><span>${what}</span></li>`).join('')}</ul>`;
    // the controller's View button (its Menu button has a tile); Esc opens the desktop app's menu
    const more = kind === 'pad' ? t.tutPad : t.tutMore(touch) + (desktop && !touch ? ` · ${t.escMenu}` : '');
    this.dlg.innerHTML = `<div class="tut">
      <div class="tut-head"><h2 id="tut-title">${t.tutTitle}</h2>
        <div class="seg tut-tabs" role="tablist">${TABS.map((k) => `<button role="tab" data-tab="${k}" aria-pressed="${k === tab}" aria-selected="${k === tab}">${names[k]}</button>`).join('')}</div></div>
      ${tab === 'map' ? `<div class="tut-grid">${tiles(kind).map((x) => `<figure>
        <div class="tv ${x.cls ?? ''}"><div class="mw" style="${x.map}">${CITY}</div><svg class="hand" viewBox="0 0 100 100" aria-hidden="true">${x.hand}</svg></div>
        <figcaption>${x.cap}</figcaption></figure>`).join('')}</div>` : list(tab)}
      <div class="tut-foot"><p>${tab === 'map' ? more : kind === 'pad' ? t.tutPad : ''}</p><button id="tut-ok" class="primary">${kind === 'pad' ? '<span class="pad-a" aria-hidden="true">A</span>' : ''}${t.tutOk}</button></div></div>`;
    this.dlg.querySelector<HTMLButtonElement>('#tut-ok')!.onclick = () => this.close();
    for (const b of this.dlg.querySelectorAll<HTMLButtonElement>('.tut-tabs button')) b.onclick = () => this.pick(b.dataset.tab as HelpTab);
  }
}
