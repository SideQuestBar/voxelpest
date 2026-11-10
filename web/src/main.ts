// Budapest in voxels: the viewer. A map to fly over, a walk at street level and a taxi (or a Trabant, a police car, a
// Bubi, a bus) to drive, at any hour of the day or live, rain or shine, in English or Hungarian. The rendering engine
// is in engine/, the three ways of moving in controls/, the page round it in ui/.
import * as THREE from 'three';
import { Input, PAD } from './controls/input';
import { initAnalytics, track, trackSoon } from './analytics';
import { keepAlive, startLite } from './recover';
import { initPwa } from './pwa';
import { Car } from './controls/drive';
import { lampLit } from './controls/kit';
import { MapControls } from './controls/orbit';
import { Walker } from './controls/walk';
import { loadSeasons } from './engine/foliage';
import { makeMaterial } from './engine/material';
import { Sky } from './engine/sky';
import { Streets, type StreetKind } from './engine/streets';
import { Tiles } from './engine/tiles';
import { isKind, Weather, type Kind } from './engine/weather';
import { World } from './engine/world';
import { lang, onLang, T, viewName } from './i18n';
import { budapestHour, Live } from './live';
import { loadMeta, MAT, type Label, type V3, type View } from './meta';
import { budapestDay, dateOf, dayName, loadClimate, parseDay, snowy, yearDays } from './season';
import { desktop, noLinks, stripLinks } from './ui/desktop';
import { fullscreenButton } from './ui/fullscreen';
import { Labels } from './ui/labels';
import { Locate } from './ui/locate';
import { Menu, type MenuRow } from './ui/menu';
import { Promo } from './ui/promo';
import { Stats } from './ui/stats';
import { clock } from './ui/time';
import { Tutorial } from './ui/tutorial';
import { Ui, type Mode } from './ui/ui';
import { VehiclePicker } from './ui/vehicles';
import { $, clamp, isTouch } from './util';
import './style.css';

declare global {
  interface Window {
    __ready?: boolean;
    __three?: Record<string, unknown>;
    // the loading screen (index.html)
    bvLoader?: { progress(p: number, text?: string): void; done(then?: () => void): void; fail(text: string): void };
  }
}

const qs = new URLSearchParams(location.search);
if (qs.get('ui') === '0') document.body.classList.add('noui');
if (qs.get('promo') === '0') document.body.classList.add('nopromo');
// iOS Safari ignores user-scalable=no: a pinch anywhere would zoom the page rather than the map
for (const ev of ['gesturestart', 'gesturechange']) document.addEventListener(ev, (e) => e.preventDefault(), { passive: false });
// no pull-to-refresh: a drag that starts on the title, the cards or the bar must not scroll (or reload) the page; the
// lists and dialogs that do scroll keep theirs. Buttons and links are left alone (style.css: touch-action none, so
// nothing scrolls from them either): a finger wobbles as it taps, and a cancelled touchmove can cost iOS the click
document.addEventListener('touchmove', (e) => {
  if (!(e.target as Element | null)?.closest?.('#places-list, dialog, .am-list, #mc-panel, button, a')) e.preventDefault();
}, { passive: false });

const loader = window.bvLoader;
const failed = (e: unknown): never => { loader?.fail(T().loadFailed); throw e; };
loader?.progress(0.12, T().loadingMeta);
const meta = await loadMeta().catch(failed);
loader?.progress(0.2, T().loadingCity(0, 1));
// the canvas fills #app, the whole screen under the notch and the home bar (index.html: viewport-fit=cover); its size
// follows #app's, which follows the dynamic viewport (Safari's toolbar coming and going)
const app = $('#app');
let vw = app.clientWidth || innerWidth, vh = app.clientHeight || innerHeight;
const renderer = (() => {
  try {
    return new THREE.WebGLRenderer({ antialias: !isTouch(), powerPreference: 'high-performance', preserveDrawingBuffer: qs.has('shot') });
  } catch (e) { return failed(e); }
})();
// the last start died on this device: lighter this time (recover.ts); ?dpr=, ?shadow=, ?budget= (MB), ?err= to try by hand
const lite = startLite(qs, isTouch());
const light = isTouch() || lite.level > 0;
renderer.setPixelRatio(Math.min(devicePixelRatio, +(qs.get('dpr') ?? (light ? lite.dpr : 2))));
renderer.setSize(vw, vh, false);
const shadowSize = +(qs.get('shadow') ?? (light ? lite.shadow : 4096));
renderer.shadowMap.enabled = shadowSize > 0;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.outputColorSpace = THREE.SRGBColorSpace;
$('#app').appendChild(renderer.domElement);
// a lost WebGL context (iOS takes it from a page left in the background): the tiles' data went to the GPU and
// nowhere else, so start again once the browser gives one back
renderer.domElement.addEventListener('webglcontextlost', (e) => { e.preventDefault(); renderer.setAnimationLoop(null); track('contextlost'); });
renderer.domElement.addEventListener('webglcontextrestored', () => location.reload());
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, vw / vh, 0.3, 40000);

const { mat, fading, look, depth, lamps } = makeMaterial(meta, light);
lampLit(lamps);
const tiles = new Tiles(meta, mat, fading);
if (depth) {  // trees that go bare: their trunks and branches, and what stands behind them, keep their faces
  tiles.depth = depth;
  tiles.see = Uint8Array.from(meta.palette, (p) => +(p[3] === MAT.LEAF));
}
// phones: a little coarser and quicker to forget tiles. An iPhone reloads a page that takes too much memory, and the
// map with its trees and seasons did while moving round
if (light) { tiles.err = 2.9 * lite.err; tiles.keepMs = 4000; tiles.recycle = 16; tiles.budget = lite.budget * 1e6; }
if (qs.has('err')) tiles.err = +qs.get('err')!;
if (qs.has('budget')) tiles.budget = +qs.get('budget')! * 1e6;
scene.add(tiles.group);
const world = new World(tiles, meta);
const sky = new Sky(scene, look, meta, shadowSize);
const weather = new Weather(scene, isTouch());
const input = new Input($('#touch'));
const map = new MapControls(camera, renderer.domElement, input);
map.floor = (x, z) => world.groundAt(x, z) ?? 8;
map.bounds = [-400, -400, meta.W * meta.vox + 400, meta.D * meta.vox + 400];
const walker = new Walker(camera, world, input, renderer.domElement);
const car = new Car(scene, camera, world, input, renderer.domElement, weather.levels);

// ---------------------------------------------------------------- state
let mode: Mode = 'map';
let hour = qs.has('hour') ? +qs.get('hour')! : 12;
let day = parseDay(qs.get('date')) ?? budapestDay();
let switching = false;

// what the analytics record of the time and the date chosen: 14:30 and its hour, 11-10 and its month
const two = (n: number) => String(n).padStart(2, '0');
const timeData = () => ({ time: `${two(Math.floor(hour) % 24)}:${two(Math.round((hour % 1) * 60) % 60)}`, hour: Math.floor(hour) % 24 });
const dateData = () => { const d = dateOf(day); return { date: `${two(d.getUTCMonth() + 1)}-${two(d.getUTCDate())}`, month: d.getUTCMonth() + 1 }; };
const ui = new Ui(meta, {
  mode: (m) => setMode(m),
  place: (k) => goView(k),
  bar: () => goBar(),
  hour: (h) => { manual(); hour = h; ui.setHour(h); trackSoon('time', timeData(), 8000); },
  date: (d) => { manual(); setDay(d); trackSoon('date', dateData(), 8000); },
  weather: (k) => { manual(); setWeather(k); track('weather', { weather: k }); },
  live: (on) => { setLive(on); track('live', { on }); },
  names: (on) => { labels.on = on; track('names', { on }); },
  tutorial: () => { tutorial.show(mode); track('help', { tab: mode }); },
});
ui.setHour(hour);
// live unless the URL sets the hour or the weather (?snow=1 from older links), or says live=0
const wq = qs.get('weather') ?? (qs.get('snow') === '1' ? 'snow' : null);
const live = new Live((r) => setWeather(r.kind, r.cover, !window.__ready));
let liveMinute = -1;
setWeather(isKind(wq) ? wq : 'clear', undefined, true);
setLive(qs.get('live') !== '0' && !qs.has('hour') && !isKind(wq) && !qs.has('date'));
setDay(day);
void loadClimate().then(() => setDay(day));
void loadSeasons(meta, look.season).then((ph) => ui.setCity(ph?.city));

function setWeather(k: Kind, cover?: number, now = false) {
  weather.set(k, cover, now);
  ui.setWeather(k);
  ui.offerSnow(snowy(day) || k === 'snow');
}
// the date drives the sun, the trees and the lawns; snow only around dates it can fall (live weather is what it is)
function setDay(d: number) {
  day = clamp(Math.round(d), 1, yearDays());
  sky.day = day;
  look.season.day.value = day;
  ui.setDay(day);
  if (!snowy(day) && weather.kind === 'snow' && !live.on) setWeather('rain');
  else ui.offerSnow(snowy(day) || weather.kind === 'snow');
}
function setLive(on: boolean) {
  live.set(on);
  ui.setLive(on);
  liveMinute = -1;
  if (on) liveClock();
}
const manual = () => { if (live.on) setLive(false); };
function liveClock() {
  hour = budapestHour();
  const m = Math.floor(hour * 60);
  if (m !== liveMinute) {  // the card shows the minute begun, as a clock does; Budapest's date turns at its midnight
    liveMinute = m;
    if (budapestDay() !== day) setDay(budapestDay());
    ui.setHour(m / 60);
  }
}
const labels = new Labels($('#labels'), meta.labels, (l) => goLabel(l));
const promo = new Promo(meta.sidequest, () => { track('bar', { from: 'map' }); goBar(); });
const tutorial = new Tutorial(() => input.pad.on);
const stats = qs.get('fps') === '1' ? new Stats() : null;
// the website's full-screen button; the desktop app has its own full screen, in its menu
const fs = desktop ? null : fullscreenButton($<HTMLButtonElement>('#fs-btn'), (text) => ui.toast(text));
// the menu (the controller's Menu button; Esc in the desktop app). Time & weather's rows: label, value, ◀ ▶, A
const KINDS: Kind[] = ['clear', 'cloudy', 'rain', 'snow'];
const timeRows: MenuRow[] = [
  // a week a press, round the year
  { label: () => T().date, value: () => dayName(day), step: (d) => { manual(); setDay(((day - 1 + 7 * d + yearDays()) % yearDays()) + 1); trackSoon('date', dateData()); } },
  { label: () => T().menuHour, value: () => clock(hour), step: (d) => stepHour(d) },
  { label: () => T().weather, value: () => T()[weather.kind], step: (d) => {
    manual();
    const kinds = snowy(day) ? KINDS : KINDS.slice(0, 3);  // no snow on dates it can't fall
    setWeather(kinds[(Math.max(kinds.indexOf(weather.kind), 0) + d + kinds.length) % kinds.length]);
    trackSoon('weather', { weather: weather.kind }, 1500);
  } },
  { label: () => T().live, on: () => live.on, press: () => { setLive(!live.on); track('live', { on: live.on }); } },
];
function stepHour(d: number) {
  manual();
  hour = ((d > 0 ? Math.floor(hour + 1e-6) + 1 : Math.ceil(hour - 1e-6) - 1) + 24) % 24;
  ui.setHour(hour);
  trackSoon('time', timeData());
}
const menu = new Menu(desktop, fs, {
  places: () => ui.placeKeys().map((k) => [k, viewName(meta.views[k])]),
  place: (k) => goView(k),
  bar: () => { track('bar', { from: 'menu' }); goBar(); },
  help: () => { tutorial.show(mode); track('help', { tab: mode, from: 'menu' }); },
  rows: timeRows,
  pad: () => input.pad.on,
});
if (noLinks) stripLinks();
// the dot for where you are: the map flies over it from the side it's seen from; tapping it walks from the street
const locate = new Locate(meta, scene, {
  ground: async (x, z) => {
    const s = tiles.levels[tiles.levels.length - 1], L = tiles.N * s * meta.vox;
    await tiles.ready(s, Math.floor(x / L), Math.floor(z / L));
    return world.groundAt(x, z) ?? 8;
  },
  fly: (x, y, z, r) => {
    if (mode !== 'map') return;
    const d = new THREE.Vector3().subVectors(camera.position, map.ctl.target).setY(0).normalize(), k = Math.max(160, r * 3);
    map.flyTo([x + d.x * k, y + k * 0.75, z + d.z * k], [x, y, z]);
  },
  walk: (x, z) => { void setMode('walk', { x, z, heading: Math.atan2(z - camera.position.z, x - camera.position.x) }); },
  toast: (t) => ui.toast(t),
});
const vehicles = new VehiclePicker(car, input, (text) => ui.toast(text));

// ---------------------------------------------------------------- places
// a spot at street level in front of what a camera looks at: part of the way back towards the camera
function before(pos: V3 | THREE.Vector3, target: V3 | THREE.Vector3) {
  const [px, pz] = Array.isArray(pos) ? [pos[0], pos[2]] : [pos.x, pos.z];
  const [tx, tz] = Array.isArray(target) ? [target[0], target[2]] : [target.x, target.z];
  const d = Math.hypot(px - tx, pz - tz), k = Math.min(0.35 * d, 120) / Math.max(d, 1e-3);
  return { x: tx + (px - tx) * k, z: tz + (pz - tz) * k, heading: Math.atan2(tz - pz, tx - px) };
}

// on foot or by car towards a view: from its camera if that stands indoors, else in front of what it looks at; the
// Parliament and Kossuth tér from the square by the flag, facing the Parliament (meta.spawn)
function towards(v: View): At {
  const sp = meta.spawn;
  if (sp && (v === meta.views.parliament || v === meta.views.kossuth)) return { x: sp.x, z: sp.z, heading: sp.heading, exact: true };
  if (!v.walk) return before(v.pos, v.target);
  return { x: v.pos[0], z: v.pos[2], y: v.pos[1], heading: Math.atan2(v.target[2] - v.pos[2], v.target[0] - v.pos[0]), exact: true };
}

function goView(key: string) {
  track('place', { place: key });
  const v = meta.views[key];
  if (!v) return;
  if (mode !== 'map') {
    void setMode(mode, towards(v));
    return;
  }
  map.flyTo(v.pos, v.target);
}

function goLabel(l: Label) {
  const v = Object.entries(meta.views).find(([, w]) => w.label === l.en || w.label_hu === l.name || viewName(w) === l.name);
  if (v) return goView(v[0]);
  if (mode !== 'map') return;
  const t: V3 = [l.x + 0.5, l.g + Math.min((l.z - l.g) * 0.5, 40), l.y + 0.5];
  const d = new THREE.Vector3().subVectors(camera.position, map.ctl.target).setY(0).normalize();
  map.flyTo([t[0] + d.x * 330, t[1] + 220, t[2] + d.z * 330], t);
}

// in front of the bar: on foot a few steps back from the door, across the pavement, looking at its front; by car on
// the street outside
function atBar(m: Mode): At | undefined {
  const bar = meta.sidequest;
  if (!bar) return undefined;
  const h = bar.heading ?? 0, [dx, dz] = bar.door ?? [bar.x, bar.y];
  if (m === 'drive') return { x: dx, z: dz, heading: h + Math.PI / 2 };
  return { x: dx - Math.cos(h) * 7, z: dz - Math.sin(h) * 7, heading: h, exact: true, look: [bar.x, bar.y] };
}

function goBar() {
  if (!meta.sidequest) return;
  if (mode === 'map') {
    const v = meta.views.sidequest;
    if (v) map.flyTo(v.pos, v.target);
    return;
  }
  void setMode(mode, atBar(mode));
}

// ---------------------------------------------------------------- finding a place to stand or drive
const streets = new Streets(tiles, meta);

async function groundLoaded(x: number, z: number, r: number) {
  const s = tiles.levels[tiles.levels.length - 1], L = tiles.N * s * meta.vox, waits: Promise<void>[] = [];
  for (let tx = Math.floor((x - r) / L); tx <= Math.floor((x + r) / L); tx++) {
    for (let ty = Math.floor((z - r) / L); ty <= Math.floor((z + r) / L); ty++) {
      if (tx >= 0 && ty >= 0 && tx < tiles.dims[s].nx && ty < tiles.dims[s].ny) waits.push(tiles.ready(s, tx, ty));
    }
  }
  await Promise.all(waits);
}

// The nearest spot within R m of (x, z) to start on foot (a pavement, square, footway or road), by bike (a road, cycle
// lane or pavement) or by car (a carriageway), on the street network: never in a building, on a roof, in the river or
// in a closed courtyard (engine/streets.ts). Needs the finest tiles round it: `await groundLoaded(x, z, r)` first.
function streetSpot(x: number, z: number, kind: StreetKind, R = 80) {
  return streets.spot(x, z, kind, R);
}
const findSpot = (x: number, z: number, road: boolean, R = 120) => streetSpot(x, z, road ? 'road' : 'foot', R);
// on foot a pavement; a vehicle where it may go (the bike also on cycle lanes and pavements)
const kindFor = (m: Mode): StreetKind => (m === 'walk' ? 'foot' : car.spec.ground);

// along the road: the direction in which it runs furthest, the nearer the wished one the better
function roadHeading(x: number, z: number, wish: number) {
  let best = wish, score = -1;
  for (let k = 0; k < 24; k++) {
    const a = (k / 24) * 2 * Math.PI;
    let n = 0;
    while (n < 40 && streets.isRoad(world.topPalette(x + Math.cos(a) * n, z + Math.sin(a) * n))) n++;
    const s = n + 6 * Math.cos(a - wish);
    if (s > score) { score = s; best = a; }
  }
  return best;
}

function here() {
  if (mode === 'walk') return { x: walker.feet.x, z: walker.feet.z, heading: walker.yaw };
  if (mode === 'drive') return { x: car.pos.x, z: car.pos.z, heading: car.heading };
  return before(camera.position, map.ctl.target);
}

// leaving the map: the street nearest to the point it looks at, facing the way it looks; from far out, the bar
function mapStart(m: Mode): At | undefined {
  const t = map.ctl.target, c = camera.position;
  if (c.distanceTo(t) > 1500) return atBar(m);
  return { x: t.x, z: t.z, heading: Math.atan2(t.z - c.z, t.x - c.x) };
}

// y: a height to stand below, for a spot indoors
type At = { x: number; z: number; heading: number; exact?: boolean; look?: [number, number]; y?: number };
let pending: [Mode, At | undefined] | null = null;

async function setMode(m: Mode, at?: At) {
  if (switching) { pending = [m, at]; return; }  // the last request wins, once the current switch is done
  if (m === mode && !at) return;
  switching = true;
  // from the map, walks and drives start on the street nearest to what it looks at (from far out, at the bar);
  // between walking and driving you stay where you are
  if (!at && mode === 'map') at = mapStart(m);
  const p = at ?? here(), from = mode;
  const was = mode === 'walk' ? walker.feet.y : mode === 'drive' ? car.pos.y : null;
  try {
    if (m === 'map') {
      ui.hint(null);
      walker.unlock();
      car.show(false, 0);
      tiles.setFocus(0, 0, 0);
      mode = 'map';
      camera.fov = 40;
      camera.updateProjectionMatrix();
      const y = was ?? world.groundAt(p.x, p.z) ?? 10;
      map.enabled = true;
      map.jump([p.x - Math.cos(p.heading) * 60, y + 45, p.z - Math.sin(p.heading) * 60], [p.x, y, p.z]);
      map.flyTo([p.x - Math.cos(p.heading) * 260, y + 190, p.z - Math.sin(p.heading) * 260], [p.x, y, p.z], 1400);
    } else {
      ui.hint(T().loading);
      tiles.setFocus(p.x, p.z, 90);
      await groundLoaded(p.x, p.z, 60);
      const open = (x: number, z: number) => {  // open ground right there (not a roof, a post or the river)
        const f = world.floor(x, z, 1e4, 0), g = world.groundAt(x, z);
        return f && g !== null && f.mat !== MAT.WATER && Math.abs(f.top - g) < 1.2 ? { x, z, y: f.top } : null;
      };
      const indoors = (x: number, z: number, y: number) => {  // the floor under a spot inside, not far below it
        const f = world.floor(x, z, y, 0);
        return f && f.mat !== MAT.WATER && f.top > y - 3 ? { x, z, y: f.top } : null;
      };
      let spot = (m === 'walk' && at?.y !== undefined ? indoors(p.x, p.z, at.y) : null)
        ?? (at?.exact && m === 'walk' ? open(p.x, p.z) ?? findSpot(p.x, p.z, false, 6) : null) ?? streetSpot(p.x, p.z, kindFor(m), 120);
      if (!spot) {  // in the river, say: further out
        await groundLoaded(p.x, p.z, 200);
        spot = streetSpot(p.x, p.z, kindFor(m), 200);
      }
      ui.hint(null);
      if (!spot) return;
      map.enabled = false;
      mode = m;
      if (m === 'walk') {
        car.show(false, 0);
        const yaw = at?.look ? Math.atan2(at.look[1] - spot.z, at.look[0] - spot.x) : p.heading;
        walker.place(spot.x, spot.y, spot.z, yaw);
        if (at?.look) walker.pitch = 0.12;
        camera.fov = 72;
        if (!isTouch() && !input.pad.on) ui.hint(T().clickToWalk);
      } else {
        walker.unlock();
        const h = roadHeading(spot.x, spot.z, p.heading);
        car.place(spot.x, spot.y, spot.z, h);
        car.show(true, sky.night);
        camera.fov = 62;
      }
      camera.updateProjectionMatrix();
    }
  } finally {
    switching = false;
    ui.setMode(mode);
    if (mode === m && m !== 'map' && !document.body.classList.contains('noui')) tutorial.first(m);
    if (mode !== from) track('mode', { mode });
    if (pending) {
      const [pm, pa] = pending;
      pending = null;
      void setMode(pm, pa);
    }
  }
}

car.onReset = () => {
  const l = car.lastSafe(), spot = streetSpot(l.x, l.z, car.spec.ground, 80) ?? streetSpot(l.x, l.z, car.spec.ground, 200);
  if (spot) car.place(spot.x, spot.y, spot.z, roadHeading(spot.x, spot.z, l.h));
  // no street found (its tiles not in yet): back where it last drove, rather than falling on and asking every frame
  else car.place(l.x, Math.max(l.y, world.groundAt(l.x, l.z) ?? 0), l.z, l.h);
};
// fallen through the map (a hole in the ground, a tile's seam): the lowest floors, underpasses and the quays, are
// above the base, so anything FELL under it has nothing below; back to the nearest street to where it last stood
const FELL = -6;
const stood = { x: 0, z: 0, set: false };
let rescued = -1e9;
function rescue() {
  const under = mode === 'walk' ? walker.feet.y <= FELL : mode === 'drive' && car.pos.y < FELL;
  // the search for a street floods hundreds of metres of columns: not every frame while something keeps falling
  if (under && performance.now() - rescued < 1000) return;
  if (under) rescued = performance.now();
  if (mode === 'walk') {
    const f = walker.feet;
    if (f.y > FELL) {
      const fl = world.floor(f.x, f.z, f.y, 0.6);
      if (fl && fl.mat !== MAT.WATER && f.y - fl.top < 0.1) Object.assign(stood, { x: f.x, z: f.z, set: true });
      return;
    }
    const [x, z] = stood.set ? [stood.x, stood.z] : [f.x, f.z];
    const spot = streetSpot(x, z, 'foot', 80) ?? streetSpot(x, z, 'foot', 200);
    if (spot) walker.place(spot.x, spot.y, spot.z, walker.yaw);
    else walker.place(x, (world.groundAt(x, z) ?? 0) + 0.1, z, walker.yaw);
  } else if (mode === 'drive' && car.pos.y < FELL) car.onReset?.();
}

renderer.domElement.addEventListener('click', () => {
  if (mode === 'walk' && !isTouch()) { walker.lock(); ui.hint(null); }
});
document.addEventListener('pointerlockchange', () => {
  if (mode === 'walk' && !switching && !document.pointerLockElement && !isTouch() && !input.pad.on) ui.hint(T().clickToWalk);
});
input.onPad = (on) => {
  if (on) track('controller');
  ui.setPad(on);
  if (on && mode === 'walk') ui.hint(null);
  tutorial.refresh();
};

// the controller's buttons that work in every mode: View cycles the modes, Menu opens the menu (places, time and
// weather, the bar, help), which then has the controller to itself for the frame
const MODES: Mode[] = ['map', 'walk', 'drive'];
function padButtons() {
  if (!input.pad.on) return;
  if (menu.open) {
    menu.pad(input);
    input.mute();
    return;
  }
  if (tutorial.open) {
    if (input.pressed(PAD.A) || input.pressed(PAD.B)) tutorial.close();
    const tab = (input.pressed(PAD.RIGHT) || input.pressed(PAD.RB) ? 1 : 0) - (input.pressed(PAD.LEFT) || input.pressed(PAD.LB) ? 1 : 0);
    if (tab) tutorial.step(tab);
    input.mute();
    return;
  }
  if (input.pressed(PAD.VIEW)) void setMode(MODES[(MODES.indexOf(mode) + 1) % 3]);
  if (input.pressed(PAD.MENU)) menu.show();
}
addEventListener('keydown', (e) => {
  if ((e.target as HTMLElement)?.tagName === 'INPUT' && (e.target as HTMLInputElement).type === 'text') return;
  if (e.code === 'Digit1') void setMode('map');
  if (e.code === 'Digit2') void setMode('walk');
  if (e.code === 'Digit3') void setMode('drive');
});
function fit() {
  const w = app.clientWidth, h = app.clientHeight;
  if (!w || !h || (w === vw && h === vh)) return;
  vw = w; vh = h;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h, false);
}
new ResizeObserver(fit).observe(app);
addEventListener('resize', fit);

// ---------------------------------------------------------------- start
const first = meta.views[qs.get('view') ?? ''] ?? meta.views.overview;
map.jump(first.pos, first.target);
ui.setMode('map');
let last = performance.now(), shown = false, sunUp = -1;

function frame(now: number) {
  const dt = clamp((now - last) / 1000, 0, 0.1);
  last = now;
  look.time.value += dt;
  input.poll();
  padButtons();
  // the sticks, triggers and buttons don't move the map or the vehicle behind the menu
  if (menu.open) input.mute();
  let focus: THREE.Vector3, radius: number;
  if (mode === 'map') {
    map.update(dt);
    focus = map.ctl.target;
    radius = camera.position.distanceTo(focus) * 0.9;
  } else if (mode === 'walk') {
    walker.update(dt);
    rescue();
    tiles.setFocus(walker.feet.x, walker.feet.z, 70);
    focus = walker.feet;
    radius = 90;
  } else {
    car.update(dt);
    rescue();
    vehicles.poll();
    car.show(true, sky.night);
    tiles.setFocus(car.pos.x, car.pos.z, 110);
    ui.speed(car.kmh);
    focus = car.pos;
    radius = 130;
  }
  camera.updateMatrixWorld();
  tiles.update(camera, vh);
  if (live.on) liveClock();
  weather.update(dt, camera, vw, vh, renderer.getPixelRatio(), sky.night, look);
  sky.set(hour, weather.levels, renderer);
  if (+sky.sun.visible !== sunUp) { sunUp = +sky.sun.visible; tiles.warm(renderer, camera, scene); }
  sky.follow(focus, radius);
  sky.dome.position.copy(camera.position);
  labels.update(camera, vw, vh, mode === 'map' ? 1 : 0.3);
  promo.update(camera, vw, vh);
  locate.update(camera, vw, vh);
  if (shown) ui.tiles(tiles.loading, tiles.meshed);
  else loader?.progress(0.2 + 0.8 * (tiles.meshed / Math.max(tiles.meshed + tiles.loading, 1)), T().loadingCity(tiles.meshed, tiles.meshed + tiles.loading));
  renderer.render(scene, camera);
  stats?.frame(now, renderer.info, tiles, ` · lite ${lite.level}` + (lite.crashed ? `\nlast start died after ${lite.crashed.secs} s: ${lite.crashed.mode}, ${lite.crashed.mb} MB` : ''));
  if (!shown && tiles.shown > 0 && tiles.loading < 4) {
    shown = true;
    window.__ready = true;
    initAnalytics();
    initPwa($<HTMLButtonElement>('#install-btn'));
    keepAlive(() => ({ mode, mb: Math.round(tiles.bytes / 1e6), tiles: tiles.shown }));
    if (lite.crashed) {
      console.warn('the last start died', lite.crashed, 'lite', lite.level);
      track('crash', { level: lite.level, mode: lite.crashed.mode, mb: Math.min(lite.crashed.mb, 1000), secs: Math.min(lite.crashed.secs, 1000), tiles: lite.crashed.tiles });
      if (lite.level > 0) ui.toast(T().lighter);
    }
    track('start', { lang: lang(), input: isTouch() ? 'touch' : 'mouse', app: !!desktop, mode });
    onLang((l) => track('lang', { lang: l }));
    const m = qs.get('mode'), v = meta.views[qs.get('view') ?? ''];
    const walking = m === 'walk' || m === 'drive';
    if (walking) void setMode(m, v ? towards(v) : undefined);
    const then = () => { if (!walking && !document.body.classList.contains('noui')) tutorial.auto(); };
    if (loader) loader.done(then);
    else then();
  }
}
renderer.setAnimationLoop(frame);

window.__three = {
  renderer, scene, camera, tiles, world, sky, car, walker, vehicles,
  lod: { get loading() { return tiles.loading; }, get shown() { return tiles.shown; }, update: () => tiles.update(camera, vh, true) },
  render: () => renderer.render(scene, camera),
  setMode, goBar, frame, map, tutorial, menu, streetSpot, groundLoaded,
  jump: (k: string) => { const v = meta.views[k]; if (v) map.jump(v.pos, v.target); },
  weather, live,
  setHour: (h: number) => { manual(); hour = h; ui.setHour(h); },
  setDay: (d: number) => { manual(); setDay(d); }, day: () => day, season: look.season,
  setWeather: (k: Kind, now = true) => { manual(); setWeather(k, undefined, now); },
  setSnow: (on: boolean, now = true) => { manual(); setWeather(on ? 'snow' : 'clear', undefined, now); },
  setLive,
};
