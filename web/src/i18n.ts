// English and Hungarian. The language comes from ?lang=, then the last choice (localStorage), then the browser's
// languages: Hungarian if any of them is Hungarian, English otherwise.
import { storage } from './util';

export type Lang = 'en' | 'hu';

const en = {
  title: 'Budapest', titleTail: 'in voxels',
  loading: 'Loading the map…', loadingTiles: (n: number) => `loading ${n} tiles`,
  loadingMeta: 'Fetching the map…', loadingCity: (done: number, all: number) => `Building the city · ${done} / ${all} tiles`,
  loadFailed: 'The map didn’t load. Check the connection and reload the page.',
  modeMap: 'Map', modeWalk: 'Walk', modeDrive: 'Drive',
  places: 'Places', search: 'Search places…', goBar: 'Go to SideQuest Bar',
  time: 'Time of day', snow: 'Snow', clear: 'Clear', weather: 'Weather', names: 'Names', about: 'About', close: 'Close',
  cloudy: 'Cloudy', rain: 'Rain', live: 'Live', liveTitle: 'Budapest’s date, time and weather, right now',
  timeBtn: (d: string, t: string, w: string, live: boolean) => `Date and time ${d}, ${t}, ${w}${live ? ', live' : ''}`,
  dateTime: 'Date and time', date: 'Date', months: ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'],
  noSnow: 'It doesn’t snow in Budapest around this date',
  clickToWalk: 'Click to look around', clickToDrive: 'Click the map to drive',
  helpMap: 'Drag to turn · right-drag to move · scroll to zoom · WASD/QE to fly',
  helpTouchMap: 'one finger: move · pinch: zoom · twist: turn · two fingers up/down: tilt · tap a name to fly there',
  helpWalk: 'WASD walk · Shift run · Space jump · mouse to look · Esc to let go',
  helpDrive: 'W/S or ↑/↓ speed · A/D or ←/→ steer · Space brake · drag to look round · R back on the road · V vehicle · L blue lights',
  helpTouchWalk: 'left: walk · right: look · double-tap: jump',
  helpTouchDrive: 'left: steer · right pedals: gas and brake · drag the view to look round',
  helpPadMap: 'left stick move · right stick turn · triggers zoom · LB/RB down/up',
  helpPadWalk: 'left stick walk (click: run) · right stick look · A jump',
  helpPadDrive: 'RT gas · LT brake/reverse · left stick steer · right stick camera · A handbrake · B boost · Y back on the road · LB/RB vehicle · X blue lights',
  padLabel: 'Controller', padView: 'View: mode',
  padOn: 'Controller connected', lighter: 'The map stopped last time: lighter graphics now',
  padMenu: 'Menu: places, time and weather', escMenu: 'Esc: menu',
  menuResume: 'Resume', menuFull: 'Full screen', menuQuit: 'Quit', menuPad: 'A: choose · B: back',
  menuTime: 'Date, time & weather', menuHour: 'Hour', menuHelp: 'Help', menuBack: 'Back', menuPadRows: '◀ ▶: change · A: choose · B: back',
  fsRefused: 'The browser only goes full screen on a click or a key',
  act: { walk: 'Walk', run: 'Run', runPad: 'Run (press the stick)', jump: 'Jump', look: 'Look round', lookDrag: 'Look round (drag)', free: 'Let go of the mouse',
    gas: 'Speed up', brake: 'Brake, reverse', gasBrake: 'Speed up, brake', steer: 'Steer', hand: 'Handbrake', boost: 'Boost', road: 'Back on the road', next: 'Next vehicle',
    nextPad: 'Previous, next vehicle', blue: 'Blue lights (police)', cam: 'Swing the camera', or: 'or',
    stick: 'Left stick', side: 'Right side', dtap: 'Double-tap', pedals: 'Pedals', drag: 'Drag the view', mouse: 'Mouse' },
  install: 'Install as an app',
  tutTitle: 'Getting around', tutTabMap: 'Map', tutTabWalk: 'On foot', tutTabDrive: 'Vehicles', tutOk: 'Got it', tutAgain: 'How to move round',
  tutMore: (touch: boolean) => `${touch ? 'Tap' : 'Click'} a name to fly there · Walk and Drive are at the top · ☀ sets the date and time`,
  tutPad: 'View: map, walk or drive',
  credits: 'Data: © OpenStreetMap contributors · Copernicus DEM · FABDEM · GlobalBuildingAtlas · Urban Atlas (Átló) · Sentinel-2 cloudless by EOX · Mapillary · Wikidata · BKK GTFS',
  tDrag: 'Drag to move', tPinch: 'Pinch to zoom', tTwist: 'Twist to turn', tTilt: 'Two fingers up or down to tilt',
  mTurn: 'Drag to turn', mMove: 'Right-drag or Shift-drag to move', mZoom: 'Scroll to zoom', mKeys: 'W A S D to fly, Q / E down and up',
  pMove: 'Left stick: move', pTurn: 'Right stick: turn', pZoom: 'Triggers: zoom · LB / RB: down, up',
  kmh: 'km/h', reset: 'Back on the road', swimming: 'in the Danube',
  aboutHtml: `<p>Central Budapest, 5.4 × 5 km, in half-metre voxels, built from free data: OpenStreetMap, the Copernicus and
    FABDEM elevation models, GlobalBuildingAtlas and Urban Atlas building heights, Sentinel-2 imagery, Mapillary street
    furniture and Wikidata. Thirty-nine landmarks are modelled by hand from photos. Live weather by
    <a href="https://open-meteo.com" target="_blank" rel="noopener">Open-Meteo</a>. The trees follow the year:
    warsaw-vibe-voxel’s phenology (the German Weather Service’s observations, iNaturalist), moved to Budapest’s climate.</p>
    <p>Made by <a href="https://side-quest.bar" target="_blank" rel="noopener">SideQuest Bar</a>. Inspired by
    <a href="https://github.com/stared/warsaw-vibe-voxel" target="_blank" rel="noopener">warsaw-vibe-voxel</a> by Piotr
    Migdał, whose tile format this map uses. The source is on
    <a href="https://github.com/SideQuestBar/voxelpest" target="_blank" rel="noopener">GitHub</a>.</p>
    <p class="legal"><a href="https://side-quest.bar/privacy" target="_blank" rel="noopener">Privacy Policy</a> ·
    <a href="https://side-quest.bar/terms" target="_blank" rel="noopener">Terms of Service</a></p>`,
  mcPlay: 'Play in Minecraft', mcSub: 'Java & Bedrock', mcTitle: 'Budapest in Minecraft',
  mcLead: 'The same city, block for block: 1 block is 1 metre. Fly over it, teleport to the landmarks; nobody can break anything.',
  java: 'Java Edition', javaSmall: 'PC, Mac, Linux', bedrock: 'Bedrock Edition', bedrockSmall: 'phone, tablet, Windows',
  copy: 'Copy', copied: 'Copied', howJava: 'Multiplayer → Add Server → paste the address.',
  howBedrock: 'Play → Servers → Add Server, with that address and port.', addToMc: 'Add to Minecraft', port: 'port',
  inGame: 'In the game', cmdLm: 'lists the landmarks; <code>/lm opera</code> takes you there',
  cmdFly: 'then double-jump to take off', cmdBar: 'takes you to SideQuest Bar',
  mcLegal: `By joining you accept our <a href="https://side-quest.bar/terms" target="_blank" rel="noopener">Terms of Service</a> and
    <a href="https://side-quest.bar/privacy" target="_blank" rel="noopener">Privacy Policy</a>.`,
  players: (n: number) => (n === 0 ? 'nobody on yet: be the first' : n === 1 ? '1 player online' : `${n} players online`),
  offline: 'offline right now', version: (v: string) => `Minecraft ${v}; other versions work too.`,
  sqMadeBy: 'made by', sqWhere: 'gaming bar · Klauzál u. 26-28', onMap: 'on the map',
  fullscreen: 'Full screen', fullscreenExit: 'Leave full screen', fullscreenHow: 'For full screen: Share, then Add to Home Screen, and open it from there',
  locate: 'Show where I am', locating: 'Finding you…', located: 'You are here · tap the dot to walk from there',
  youHere: 'You are here: walk from here', outside: 'You’re outside the map: it shows central Budapest',
  locDenied: 'Location is turned off for this page', locFailed: 'Couldn’t find where you are',
  vehicle: 'Vehicle', vTaxi: 'Taxi', vTrabant: 'Trabant 601', vPolice: 'Police', vBubi: 'Bubi', vBus: 'BKK bus', flashers: 'Blue lights',
};
type Strings = typeof en;

const hu: Strings = {
  title: 'Budapest', titleTail: 'voxelekben',
  loading: 'Töltődik a térkép…', loadingTiles: (n: number) => `${n} csempe töltődik`,
  loadingMeta: 'Érkeznek a térkép adatai…', loadingCity: (done: number, all: number) => `Épül a város · ${done} / ${all} csempe`,
  loadFailed: 'A térkép nem töltődött be. Ellenőrizd a kapcsolatot, és töltsd újra az oldalt.',
  modeMap: 'Térkép', modeWalk: 'Séta', modeDrive: 'Autó',
  places: 'Helyek', search: 'Hely keresése…', goBar: 'Irány a SideQuest Bar',
  time: 'Napszak', snow: 'Hó', clear: 'Derült', weather: 'Időjárás', names: 'Nevek', about: 'Névjegy', close: 'Bezárás',
  cloudy: 'Felhős', rain: 'Eső', live: 'Élő', liveTitle: 'Budapest dátuma, ideje és időjárása, élőben',
  timeBtn: (d: string, t: string, w: string, live: boolean) => `Dátum és idő: ${d}, ${t}, ${w}${live ? ', élő' : ''}`,
  dateTime: 'Dátum és idő', date: 'Dátum', months: ['J', 'F', 'M', 'Á', 'M', 'J', 'J', 'A', 'Sz', 'O', 'N', 'D'],
  noSnow: 'Ilyenkor nem szokott havazni Budapesten',
  clickToWalk: 'Kattints a körbenézéshez', clickToDrive: 'Kattints a térképre a vezetéshez',
  helpMap: 'Húzás: forgatás · jobb gomb: mozgatás · görgő: nagyítás · WASD/QE: repülés',
  helpTouchMap: 'egy ujj: mozgatás · csippentés: nagyítás · két ujj forgatása: fordulás · két ujj fel-le: döntés · koppints egy névre: odarepülsz',
  helpWalk: 'WASD: séta · Shift: futás · Szóköz: ugrás · egér: nézelődés · Esc: elengedés',
  helpDrive: 'W/S vagy ↑/↓: gáz és fék · A/D vagy ←/→: kormány · Szóköz: fék · húzás: körbenézés · R: vissza az útra · V: jármű · L: villogó',
  helpTouchWalk: 'bal: séta · jobb: nézelődés · dupla koppintás: ugrás',
  helpTouchDrive: 'bal: kormány · jobb pedálok: gáz és fék · húzd a képet: körbenézés',
  helpPadMap: 'bal kar mozgatás · jobb kar forgatás · ravaszok nagyítás · LB/RB le/fel',
  helpPadWalk: 'bal kar séta (benyomva: futás) · jobb kar nézelődés · A ugrás',
  helpPadDrive: 'RT gáz · LT fék/hátramenet · bal kar kormány · jobb kar kamera · A kézifék · B turbó · Y vissza az útra · LB/RB jármű · X villogó',
  padLabel: 'Kontroller', padView: 'View: mód',
  padOn: 'Kontroller csatlakoztatva', lighter: 'A térkép legutóbb leállt: most könnyebb grafikával fut',
  padMenu: 'Menu: helyek, napszak és időjárás', escMenu: 'Esc: menü',
  menuResume: 'Folytatás', menuFull: 'Teljes képernyő', menuQuit: 'Kilépés', menuPad: 'A: kiválasztás · B: vissza',
  menuTime: 'Dátum, idő és időjárás', menuHour: 'Óra', menuHelp: 'Súgó', menuBack: 'Vissza', menuPadRows: '◀ ▶: állítás · A: kiválasztás · B: vissza',
  fsRefused: 'A böngésző csak kattintásra vagy billentyűre vált teljes képernyőre',
  act: { walk: 'Séta', run: 'Futás', runPad: 'Futás (a kar benyomva)', jump: 'Ugrás', look: 'Nézelődés', lookDrag: 'Körbenézés (húzás)', free: 'Egér elengedése',
    gas: 'Gáz', brake: 'Fék, hátramenet', gasBrake: 'Gáz, fék', steer: 'Kormány', hand: 'Kézifék', boost: 'Turbó', road: 'Vissza az útra', next: 'Következő jármű',
    nextPad: 'Előző, következő jármű', blue: 'Villogó (rendőrautó)', cam: 'Kamera forgatása', or: 'vagy',
    stick: 'Bal kar', side: 'Jobb oldal', dtap: 'Dupla koppintás', pedals: 'Pedálok', drag: 'Húzd a képet', mouse: 'Egér' },
  install: 'Telepítés alkalmazásként',
  tutTitle: 'Így mozoghatsz', tutTabMap: 'Térkép', tutTabWalk: 'Gyalog', tutTabDrive: 'Járművek', tutOk: 'Értem', tutAgain: 'Irányítás',
  tutMore: (touch: boolean) => `${touch ? 'Koppints' : 'Kattints'} egy névre, és odarepülsz · Séta és Autó fent · ☀: dátum és idő`,
  tutPad: 'View: térkép, séta vagy autó',
  credits: 'Adatok: © OpenStreetMap-közreműködők · Copernicus DEM · FABDEM · GlobalBuildingAtlas · Urban Atlas (Átló) · Sentinel-2 cloudless (EOX) · Mapillary · Wikidata · BKK GTFS',
  tDrag: 'Húzás egy ujjal: mozgatás', tPinch: 'Csippentés: nagyítás', tTwist: 'Két ujj forgatása: fordulás', tTilt: 'Két ujj fel vagy le: döntés',
  mTurn: 'Húzás: forgatás', mMove: 'Jobb gombbal vagy Shifttel húzva: mozgatás', mZoom: 'Görgő: nagyítás', mKeys: 'W A S D: repülés, Q / E: le és fel',
  pMove: 'Bal kar: mozgatás', pTurn: 'Jobb kar: forgatás', pZoom: 'Ravaszok: nagyítás · LB / RB: le, fel',
  kmh: 'km/h', reset: 'Vissza az útra', swimming: 'a Dunában',
  aboutHtml: `<p>Belső-Budapest 5,4 × 5 km-en, fél méteres voxelekből, szabad adatokból: OpenStreetMap, Copernicus és
    FABDEM domborzat, GlobalBuildingAtlas és Urban Atlas épületmagasságok, Sentinel-2 felvételek, Mapillary utcabútorok és
    Wikidata. Harminckilenc nevezetességet kézzel modelleztünk fényképek alapján. Az élő időjárás forrása az
    <a href="https://open-meteo.com" target="_blank" rel="noopener">Open-Meteo</a>. A fák követik az évszakokat: a
    warsaw-vibe-voxel fenológiája (a Német Meteorológiai Szolgálat megfigyelései, iNaturalist), Budapest éghajlatára igazítva.</p>
    <p>A <a href="https://side-quest.bar" target="_blank" rel="noopener">SideQuest Bar</a> készítette. Ihlette: Piotr Migdał <a href="https://github.com/stared/warsaw-vibe-voxel" target="_blank"
    rel="noopener">warsaw-vibe-voxel</a> projektje, amelynek csempeformátumát ez a térkép is használja. A forráskód a
    <a href="https://github.com/SideQuestBar/voxelpest" target="_blank" rel="noopener">GitHubon</a> érhető el.</p>
    <p class="legal"><a href="https://side-quest.bar/hu/privacy" target="_blank" rel="noopener">Adatvédelmi tájékoztató</a> ·
    <a href="https://side-quest.bar/hu/terms" target="_blank" rel="noopener">Felhasználási feltételek</a></p>`,
  mcPlay: 'Játssz Minecraftban', mcSub: 'Java és Bedrock', mcTitle: 'Budapest Minecraftban',
  mcLead: 'Ugyanez a város, blokkról blokkra: egy blokk egy méter. Repüld körbe, teleportálj a nevezetességekhez; semmit nem lehet lerombolni.',
  java: 'Java Edition', javaSmall: 'PC, Mac, Linux', bedrock: 'Bedrock Edition', bedrockSmall: 'telefon, tablet, Windows',
  copy: 'Másolás', copied: 'Kimásolva', howJava: 'Többjátékos → Szerver hozzáadása → illeszd be a címet.',
  howBedrock: 'Játék → Szerverek → Szerver hozzáadása, ezzel a címmel és porttal.', addToMc: 'Hozzáadás a Minecrafthoz', port: 'port',
  inGame: 'A játékban', cmdLm: 'kilistázza a nevezetességeket; a <code>/lm opera</code> odavisz',
  cmdFly: 'aztán dupla ugrással felszállsz', cmdBar: 'és már a SideQuest Barnál vagy',
  mcLegal: `A csatlakozással elfogadod a <a href="https://side-quest.bar/hu/terms" target="_blank" rel="noopener">Felhasználási feltételeket</a> és az
    <a href="https://side-quest.bar/hu/privacy" target="_blank" rel="noopener">Adatvédelmi tájékoztatót</a>.`,
  players: (n: number) => (n === 0 ? 'még senki: légy az első' : `${n} játékos online`),
  offline: 'most nem elérhető', version: (v: string) => `Minecraft ${v}; más verziókkal is működik.`,
  sqMadeBy: 'készítette', sqWhere: 'gamer bár · Klauzál u. 26-28', onMap: 'a térképen',
  fullscreen: 'Teljes képernyő', fullscreenExit: 'Kilépés a teljes képernyőből', fullscreenHow: 'Teljes képernyőhöz: Megosztás, majd Főképernyőhöz adás, és onnan nyisd meg',
  locate: 'Mutasd, hol vagyok', locating: 'Keresem, hol vagy…', located: 'Itt vagy · koppints a pöttyre, és onnan sétálhatsz',
  youHere: 'Itt vagy: séta innen', outside: 'Nem vagy a térképen: ez Belső-Budapestet mutatja',
  locDenied: 'Ennél az oldalnál ki van kapcsolva a helymeghatározás', locFailed: 'Nem sikerült megtalálni, hol vagy',
  vehicle: 'Jármű', vTaxi: 'Taxi', vTrabant: 'Trabant 601', vPolice: 'Rendőrség', vBubi: 'Bubi', vBus: 'BKK busz', flashers: 'Villogó',
};

const STRINGS: Record<Lang, Strings> = { en, hu };
const KEY = 'voxelpest-lang';

export function detectLang(): Lang {
  const q = new URLSearchParams(location.search).get('lang');
  if (q === 'en' || q === 'hu') return q;
  const saved = storage(KEY);
  if (saved === 'en' || saved === 'hu') return saved;
  const langs = navigator.languages?.length ? navigator.languages : [navigator.language];
  return langs.some((l) => l?.toLowerCase().startsWith('hu')) ? 'hu' : 'en';
}

let current: Lang = detectLang();
const listeners: ((l: Lang) => void)[] = [];

export const lang = () => current;
export const T = () => STRINGS[current];
export function onLang(f: (l: Lang) => void) { listeners.push(f); }
export function setLang(l: Lang) {
  if (l === current) return;
  current = l;
  storage(KEY, l);
  document.documentElement.lang = l;
  for (const f of listeners) f(l);
}
document.documentElement.lang = current;

// a place's name in the current language: OSM's name is Hungarian, name:en the English one
export const placeName = (p: { name: string; en?: string }) => (current === 'hu' ? p.name : p.en ?? p.name);
export const viewName = (v: { label: string; label_hu?: string }) => (current === 'hu' ? v.label_hu ?? v.label : v.label);
