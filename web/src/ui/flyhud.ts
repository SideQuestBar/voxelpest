// Fly mode's screen: the aircraft picker (a .seg under the switches, like drive mode's vehicles) and what is drawn
// over the picture on a canvas: for the FPV drone a Betaflight-style OSD (the crosshair, an artificial horizon and its
// ladder, battery, link quality, timer, throttle, speed, altitude, the way home), for the plane and the helicopter a
// panel of round instruments drawn like the real ones: the plane's six-pack (airspeed, attitude, altimeter, turn
// coordinator, heading, vertical speed) and tachometer; the helicopter's with torque and rotor rpm instead. Their dials
// are drawn once per size and kept; the needles lag as real ones do.
import { track } from '../analytics';
import { AIRCRAFT, saveAircraft, startAircraft, type AircraftKind } from '../controls/aircraft';
import type { Flyer, Telemetry } from '../controls/fly';
import { PAD, type Input } from '../controls/input';
import { onLang, T } from '../i18n';
import { $ } from '../util';

const NAME = { drone: 'aDrone', plane: 'aPlane', heli: 'aHeli' } as const;
const KT = 1.94384, FT = 3.28084, ASL = 98;   // m/s to knots, m to feet; the model's base above sea level
const TAU = Math.PI * 2, DEG = Math.PI / 180;
const SANS = '"Helvetica Neue", Arial, "DejaVu Sans", sans-serif';
const INK = '#eef0f1', DIM = '#a9adb1', FACE = '#141518';

type Inst = 'asi' | 'ai' | 'alt' | 'tc' | 'hi' | 'vsi' | 'rpm' | 'trq' | 'nr';
type Ctx = CanvasRenderingContext2D;

// a point at angle a (clockwise from 12 o'clock) and radius d
const pt = (a: number, d: number): [number, number] => [Math.sin(a) * d, -Math.cos(a) * d];
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
// piecewise linear through [value, angle in degrees] pairs
function scale(pts: [number, number][]) {
  return (v: number) => {
    if (v <= pts[0][0]) return pts[0][1] * DEG;
    for (let i = 1; i < pts.length; i++) {
      const [v0, a0] = pts[i - 1], [v1, a1] = pts[i];
      if (v <= v1) return lerp(a0, a1, (v - v0) / (v1 - v0)) * DEG;
    }
    return pts[pts.length - 1][1] * DEG;
  };
}
const ASI_PLANE = scale([[0, 0], [40, 30], [170, 340]]);
const ASI_HELI = scale([[0, 0], [20, 22], [150, 340]]);
const VSI = (fpm: number) => -Math.PI / 2 + Math.sign(fpm) * scale([[0, 0], [500, 52], [1000, 98], [1500, 138], [2000, 170]])(Math.abs(fpm));
const ARC = (v0: number, v1: number) => (v: number) => (-130 + ((v - v0) / (v1 - v0)) * 260) * DEG;
const RPM = ARC(0, 3500), PCT = ARC(0, 120);

export class FlyHud {
  private readonly root = $('#aircraft');
  private readonly buttons = [...this.root.querySelectorAll<HTMLButtonElement>('button[data-aircraft]')];
  private readonly canvas = $<HTMLCanvasElement>('#flyhud');
  private readonly g = this.canvas.getContext('2d')!;
  private on = false;
  private readonly cache = new Map<string, HTMLCanvasElement>();
  private readonly sm = { speed: 0, vs: 0, rpm: 0, torque: 0, turn: 0, slip: 0, alt: 0 };
  private last = 0;

  constructor(private readonly flyer: Flyer, private readonly input: Input, private readonly toast: (text: string) => void) {
    for (const b of this.buttons) b.onclick = (e) => { this.pick(b.dataset.aircraft as AircraftKind); if (e.detail) b.blur(); };
    addEventListener('keydown', (e) => {
      if (document.body.dataset.mode !== 'fly' || e.repeat || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.code === 'KeyV') this.step(e.shiftKey ? -1 : 1);
    });
    flyer.setKind(startAircraft());
    this.sync();
    this.text();
    onLang(() => this.text());
  }

  poll() {
    if (this.input.pressed(PAD.RB)) this.step(1);
    if (this.input.pressed(PAD.LB)) this.step(-1);
  }

  step(d: number) {
    const n = AIRCRAFT.length;
    this.pick(AIRCRAFT[(AIRCRAFT.indexOf(this.flyer.kind) + d + n) % n]);
  }

  pick(k: AircraftKind) {
    this.flyer.setKind(k);
    saveAircraft(k);
    track('aircraft', { aircraft: k });
    this.sync();
    this.toast(T()[NAME[k]]);
  }

  private sync() {
    for (const b of this.buttons) b.setAttribute('aria-pressed', String(b.dataset.aircraft === this.flyer.kind));
  }

  private text() {
    const t = T();
    this.root.setAttribute('aria-label', t.aircraft);
    for (const b of this.buttons) b.title = t[NAME[b.dataset.aircraft as AircraftKind]];
  }

  show(on: boolean) {
    this.on = on;
    this.canvas.hidden = !on;
    if (!on) this.g.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  draw() {
    if (!this.on) return;
    const c = this.canvas, dpr = Math.min(devicePixelRatio || 1, 2), w = c.clientWidth, h = c.clientHeight;
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
    const g = this.g;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    const now = performance.now() / 1000, dt = Math.min(0.1, Math.max(0, now - this.last));
    this.last = now;
    const t = this.flyer.telemetry();
    // the needles' lag: the vertical speed's is the longest, as on a real one
    const s = this.sm, ease = (k: keyof typeof s, v: number, tau: number) => { s[k] += (v - s[k]) * (1 - Math.exp(-dt / tau)); };
    ease('speed', t.speed, 0.15); ease('vs', t.vs, 0.7); ease('rpm', t.rpm, 0.25); ease('torque', t.torque, 0.3);
    ease('turn', t.turn, 0.35); ease('slip', t.slip, 0.25); ease('alt', t.alt, 0.12);
    if (t.kind === 'drone') this.osd(g, w, h, t);
    else this.panel(g, w, h, t, dpr, now);
  }

  // ---------------------------------------------------------------- the FPV OSD
  private osd(g: Ctx, w: number, h: number, t: Telemetry) {
    const s = Math.max(0.75, Math.min(w, h * 1.4) / 900), fs = Math.round(17 * s);
    // on a breaking link the OSD tears with the picture
    const tear = this.flyer.breakup > 0.3 ? (Math.random() - 0.5) * 14 * this.flyer.breakup : 0;
    g.save();
    g.translate(tear, 0);
    const txt = (str: string, x: number, y: number, align: CanvasTextAlign = 'left', size = fs, col = '#ffffff') => {
      g.font = `700 ${size}px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace`;
      g.textAlign = align; g.textBaseline = 'middle';
      g.lineWidth = Math.max(2, size / 5); g.lineJoin = 'round'; g.strokeStyle = 'rgba(0,0,0,0.85)'; g.strokeText(str, x, y);
      g.fillStyle = col; g.fillText(str, x, y);
    };
    const cx = w / 2, cy = h / 2, m = 22 * s;
    // the artificial horizon and its ladder, round the middle (not with the drone seen from outside)
    const fpv = this.flyer.fpv;
    g.save();
    if (!fpv) g.globalAlpha = 0;
    g.translate(cx, cy);
    g.rotate(-t.roll);
    const ppd = (h * 0.5) / 30;
    const off = (t.pitch * 180) / Math.PI * ppd;
    // white on a black outline, as the OSD's text
    const line = (x0: number, x1: number, y: number) => { g.beginPath(); g.moveTo(-x1, y); g.lineTo(-x0, y); g.moveTo(x0, y); g.lineTo(x1, y); };
    for (const [col, lw] of [['rgba(0,0,0,0.85)', 4.4 * s], ['#ffffff', 2.2 * s]] as const) {
      g.strokeStyle = col; g.lineWidth = lw;
      line(40 * s, 150 * s, off); g.stroke();
      for (const d of [-20, -10, 10, 20]) {
        g.setLineDash(d < 0 ? [6 * s, 5 * s] : []);
        line(30 * s, 70 * s, off - d * ppd); g.stroke();
      }
      g.setLineDash([]);
    }
    g.restore();
    // the crosshair
    if (!fpv) g.globalAlpha = 0;
    for (const [col, lw] of [['rgba(0,0,0,0.85)', 4 * s], ['#ffffff', 2 * s]] as const) {
      g.strokeStyle = col; g.lineWidth = lw;
      g.beginPath(); g.moveTo(cx - 14 * s, cy); g.lineTo(cx - 5 * s, cy); g.moveTo(cx + 5 * s, cy); g.lineTo(cx + 14 * s, cy);
      g.moveTo(cx, cy - 8 * s); g.lineTo(cx, cy - 3 * s); g.stroke();
    }
    g.globalAlpha = 1;
    // the corners: battery and drawn capacity, link quality, timer, mode, throttle; speed and altitude at the sides
    const volt = Math.max(14.4, 16.8 - t.time * 0.004 - (t.power - 0.3) * 0.9);
    const mah = Math.round(t.time * 9 + t.power * 30);
    txt(`${volt.toFixed(1)}V`, m, m + fs);
    txt(`${String(mah).padStart(4, '0')}MAH`, m, m + fs * 2.3);
    txt(`LQ ${String(Math.round(t.link * 100)).padStart(3, ' ')}`, w - m, m + fs, 'right', fs, t.link < 0.4 ? '#ffd23f' : '#ffffff');
    const mm = Math.floor(t.time / 60), ss = Math.floor(t.time % 60);
    txt(`${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`, w - m, m + fs * 2.3, 'right');
    txt('ANGL', cx, m + fs, 'center');
    txt(`THR ${String(Math.round(t.power * 100)).padStart(3, ' ')}`, m, h - m - fs * 1.9);
    txt(`${Math.round(t.speed * 3.6)}KM/H`, cx - 190 * s, cy, 'right');
    txt(`${Math.round(t.agl)}M`, cx + 190 * s, cy, 'left');
    txt(`${t.vs >= 0 ? '+' : ''}${t.vs.toFixed(1)}`, cx + 190 * s, cy + fs * 1.3, 'left', Math.round(fs * 0.8));
    // the way home: an arrow and the distance
    g.save();
    g.translate(cx, h - m - fs * 2.2);
    g.rotate(t.homeDir + Math.PI / 2);
    g.fillStyle = '#ffffff'; g.strokeStyle = 'rgba(0,0,0,0.85)'; g.lineWidth = 2;
    g.beginPath(); g.moveTo(0, -10 * s); g.lineTo(7 * s, 8 * s); g.lineTo(0, 4 * s); g.lineTo(-7 * s, 8 * s); g.closePath(); g.stroke(); g.fill();
    g.restore();
    txt(`${Math.round(t.home)}M`, cx, h - m - fs * 0.6, 'center');
    const dir = Math.round(((t.heading * 180) / Math.PI + 360) % 360);
    txt(`${String(dir).padStart(3, '0')}°`, m, h - m - fs * 0.6);
    if (t.crashed) txt(T().crashed, cx, cy - 60 * s, 'center', Math.round(fs * 1.6), '#ff5b4f');
    g.restore();
  }

  // ---------------------------------------------------------------- the instrument panel
  private panel(g: Ctx, w: number, h: number, t: Telemetry, dpr: number, now: number) {
    const plane = t.kind === 'plane';
    let set: Inst[] = plane ? ['asi', 'ai', 'alt', 'tc', 'hi', 'vsi', 'rpm'] : ['asi', 'ai', 'alt', 'trq', 'hi', 'vsi', 'nr'];
    if (w < 560) set = ['asi', 'ai', 'alt', 'vsi'];
    else if (w < 800) set = ['asi', 'ai', 'alt', 'hi', 'vsi'];
    const n = set.length, small = w < 700 || h < 500;
    const r = Math.max(24, Math.min(54, (w - 24) / (n * 2.32)));
    const side = 2.2 * r, gap = 0.1 * r, total = n * side + (n - 1) * gap;
    const y = h - r * 1.1 - (small ? 62 : 74), x0 = w / 2 - total / 2 + side / 2;
    // the panel behind them
    const grd = g.createLinearGradient(0, y - r * 1.2, 0, y + r * 1.2);
    grd.addColorStop(0, 'rgba(38, 41, 45, 0.92)'); grd.addColorStop(1, 'rgba(22, 24, 27, 0.92)');
    g.fillStyle = grd;
    round(g, x0 - side / 2 - r * 0.12, y - r * 1.22, total + r * 0.24, r * 2.44, r * 0.22);
    g.fill();
    g.strokeStyle = 'rgba(255,255,255,0.07)'; g.lineWidth = 1; g.stroke();
    const asi = plane ? ASI_PLANE : ASI_HELI;
    set.forEach((k, i) => {
      const x = x0 + i * (side + gap);
      this.blit(g, `plate`, x, y, r, dpr, (c) => plateFace(c, r));
      switch (k) {
        case 'asi':
          this.blit(g, `asi-${t.kind}`, x, y, r, dpr, (c) => asiFace(c, r, plane));
          needle(g, x, y, r * 0.8, asi(Math.min(this.sm.speed * KT, plane ? 175 : 155)), r);
          break;
        case 'ai': this.attitude(g, x, y, r, t.pitch, t.roll, dpr); break;
        case 'alt': {
          this.blit(g, 'alt', x, y, r, dpr, (c) => altFace(c, r));
          const ft = Math.max(0, (this.sm.alt + ASL) * FT);
          pointer10k(g, x, y, r, ((ft / 100000) % 1) * TAU);
          needle(g, x, y, r * 0.5, ((ft / 10000) % 1) * TAU, r, 2.2);
          needle(g, x, y, r * 0.82, ((ft / 1000) % 1) * TAU, r);
          break;
        }
        case 'tc': this.turnCoord(g, x, y, r, dpr); break;
        case 'hi': this.headingInd(g, x, y, r, t.heading, dpr); break;
        case 'vsi':
          this.blit(g, 'vsi', x, y, r, dpr, (c) => vsiFace(c, r));
          needle(g, x, y, r * 0.8, VSI(Math.max(-2100, Math.min(2100, this.sm.vs * FT * 60))), r);
          break;
        case 'rpm':
          this.blit(g, 'rpm', x, y, r, dpr, (c) => gaugeFace(c, r, 'RPM', '×100', RPM, 3500, 100, 500, 500, (v) => String(v / 100),
            [[2100, 2700, '#38b354']], [2700], true));
          hourMeter(g, x, y + r * 0.42, r, 1287.3 + t.time / 3600);
          needle(g, x, y, r * 0.8, RPM(Math.min(3550, this.sm.rpm)), r);
          break;
        case 'trq':
          this.blit(g, 'trq', x, y, r, dpr, (c) => gaugeFace(c, r, 'TORQUE', '%', PCT, 120, 5, 10, 20, String,
            [[0, 93, '#38b354'], [93, 100, '#e3b72e']], [100]));
          needle(g, x, y, r * 0.8, PCT(Math.min(122, this.sm.torque)), r);
          break;
        case 'nr':
          this.blit(g, 'nr', x, y, r, dpr, (c) => gaugeFace(c, r, 'ROTOR', '% RPM', PCT, 120, 5, 10, 20, String,
            [[95, 107, '#38b354']], [85, 107]));
          needle(g, x, y, r * 0.8, PCT(t.crashed ? 0 : Math.min(122, t.rpm)), r);
          break;
      }
      this.blit(g, 'glass', x, y, r, dpr, (c) => glassFace(c, r));
    });
    // the annunciators over the panel
    const tt = T();
    const warn = t.crashed ? tt.crashed : t.stall ? tt.stall : t.ground ? tt.onGround : '';
    if (warn && (!t.stall || t.crashed || now % 0.5 < 0.32)) {
      g.font = `800 ${Math.round(r * 0.3)}px ${SANS}`; g.textAlign = 'center'; g.textBaseline = 'middle';
      const tw = g.measureText(warn).width + r * 0.6, th = r * 0.48, cy = y - r * 1.22 - th * 0.75;
      g.fillStyle = t.crashed || t.stall ? '#c8231c' : 'rgba(30, 32, 35, 0.85)';
      round(g, w / 2 - tw / 2, cy - th / 2, tw, th, r * 0.08); g.fill();
      g.strokeStyle = t.crashed || t.stall ? '#ff8a80' : 'rgba(255,255,255,0.25)'; g.lineWidth = 1; g.stroke();
      g.fillStyle = '#ffffff'; g.fillText(warn, w / 2, cy + 1);
    }
  }

  // a dial drawn once for its size, then copied
  private blit(g: Ctx, key: string, x: number, y: number, r: number, dpr: number, paint: (c: Ctx) => void) {
    const size = Math.ceil(r * 2.3 * dpr), id = `${key}:${size}`;
    let cv = this.cache.get(id);
    if (!cv) {
      cv = document.createElement('canvas');
      cv.width = cv.height = size;
      const c = cv.getContext('2d')!;
      c.setTransform(dpr, 0, 0, dpr, size / 2, size / 2);
      paint(c);
      this.cache.set(id, cv);
    }
    g.drawImage(cv, x - size / dpr / 2, y - size / dpr / 2, size / dpr, size / dpr);
  }

  private attitude(g: Ctx, x: number, y: number, r: number, pitch: number, roll: number, dpr: number) {
    const R = r * 0.94, ppd = r * 0.022, off = Math.max(-40, Math.min(40, pitch / DEG)) * ppd;
    g.save();
    g.translate(x, y);
    g.beginPath(); g.arc(0, 0, R, 0, TAU); g.clip();
    g.rotate(-roll);
    // the inner sphere: sky and ground, the horizon, the pitch ladder
    const sky = g.createLinearGradient(0, -2 * r, 0, off);
    sky.addColorStop(0, '#1d5fa6'); sky.addColorStop(1, '#4c93d8');
    g.fillStyle = sky; g.fillRect(-2 * r, -3 * r + off, 4 * r, 3 * r);
    const gr = g.createLinearGradient(0, off, 0, 2 * r);
    gr.addColorStop(0, '#8a5530'); gr.addColorStop(1, '#4e2f17');
    g.fillStyle = gr; g.fillRect(-2 * r, off, 4 * r, 3 * r);
    g.strokeStyle = '#ffffff'; g.lineWidth = Math.max(1.2, r * 0.03);
    g.beginPath(); g.moveTo(-2 * r, off); g.lineTo(2 * r, off); g.stroke();
    g.fillStyle = '#ffffff'; g.font = `600 ${Math.round(r * 0.14)}px ${SANS}`; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.lineWidth = Math.max(1, r * 0.022);
    for (const d of [-20, -15, -10, -5, 5, 10, 15, 20]) {
      const yy = off - d * ppd, hw = d % 10 === 0 ? r * 0.26 : r * 0.11;
      if (Math.abs(yy) > R * 0.7) continue;
      g.beginPath(); g.moveTo(-hw, yy); g.lineTo(hw, yy); g.stroke();
      if (d % 10 === 0) { g.fillText(String(Math.abs(d)), -hw - r * 0.12, yy); g.fillText(String(Math.abs(d)), hw + r * 0.12, yy); }
    }
    // the outer ring: rolls but does not pitch, with the sky pointer
    g.beginPath(); g.arc(0, 0, R, 0, TAU); g.arc(0, 0, R * 0.76, 0, TAU, true); g.closePath();
    g.save(); g.clip();
    g.fillStyle = '#2f73bb'; g.fillRect(-r, -r, 2 * r, r);
    g.fillStyle = '#6b4223'; g.fillRect(-r, 0, 2 * r, r);
    g.strokeStyle = '#ffffff'; g.lineWidth = Math.max(1.2, r * 0.03);
    g.beginPath(); g.moveTo(-r, 0); g.lineTo(r, 0); g.stroke();
    g.restore();
    g.fillStyle = '#ffffff';
    g.beginPath(); g.moveTo(0, -R * 0.76); g.lineTo(-r * 0.07, -R * 0.62); g.lineTo(r * 0.07, -R * 0.62); g.closePath(); g.fill();
    g.restore();
    this.blit(g, 'aicase', x, y, r, dpr, (c) => aiCase(c, r));
  }

  private turnCoord(g: Ctx, x: number, y: number, r: number, dpr: number) {
    this.blit(g, 'tc', x, y, r, dpr, (c) => tcFace(c, r));
    // the ball in its tube, then the little aeroplane: wings on the lower marks at a standard-rate turn (3°/s)
    const bx = Math.max(-1, Math.min(1, -this.sm.slip * 3)) * r * 0.3;
    const by = r * 0.5 + (bx / r) * (bx / r) * r * 0.25;
    const ball = g.createRadialGradient(x + bx - r * 0.02, y + by - r * 0.02, r * 0.01, x + bx, y + by, r * 0.07);
    ball.addColorStop(0, '#5a5d61'); ball.addColorStop(1, '#050506');
    g.fillStyle = ball; g.beginPath(); g.arc(x + bx, y + by, r * 0.065, 0, TAU); g.fill();
    g.strokeStyle = '#d9dcde'; g.lineWidth = Math.max(1, r * 0.02);
    g.beginPath(); g.moveTo(x - r * 0.085, y + r * 0.4); g.lineTo(x - r * 0.085, y + r * 0.62); g.moveTo(x + r * 0.085, y + r * 0.4); g.lineTo(x + r * 0.085, y + r * 0.62); g.stroke();
    const bank = Math.max(-38, Math.min(38, (this.sm.turn / DEG / 3) * 20)) * DEG;
    g.save(); g.translate(x, y); g.rotate(bank);
    g.fillStyle = '#ffffff'; g.strokeStyle = '#ffffff'; g.lineCap = 'round';
    g.lineWidth = r * 0.07; g.beginPath(); g.moveTo(-r * 0.62, 0); g.lineTo(r * 0.62, 0); g.stroke();
    g.lineWidth = r * 0.045; g.beginPath(); g.moveTo(-r * 0.16, -r * 0.2); g.lineTo(r * 0.16, -r * 0.2); g.stroke();
    g.beginPath(); g.moveTo(0, -r * 0.3); g.lineTo(0, -r * 0.08); g.stroke();
    g.beginPath(); g.arc(0, 0, r * 0.1, 0, TAU); g.fill();
    g.restore();
  }

  private headingInd(g: Ctx, x: number, y: number, r: number, heading: number, dpr: number) {
    const size = Math.ceil(r * 2.3 * dpr);
    this.blit(g, 'plain', x, y, r, dpr, (c) => { dialBase(c, r); });
    let card = this.cache.get(`hicard:${size}`);
    if (!card) {
      card = document.createElement('canvas');
      card.width = card.height = size;
      const c = card.getContext('2d')!;
      c.setTransform(dpr, 0, 0, dpr, size / 2, size / 2);
      hiCard(c, r);
      this.cache.set(`hicard:${size}`, card);
    }
    g.save(); g.translate(x, y); g.rotate(-heading);
    g.drawImage(card, -size / dpr / 2, -size / dpr / 2, size / dpr, size / dpr);
    g.restore();
    this.blit(g, 'hicase', x, y, r, dpr, (c) => hiCase(c, r));
  }
}

// ------------------------------------------------------------------ the dials, drawn about (0, 0)
function plateFace(c: Ctx, r: number) {
  const s = r * 1.1;
  const grd = c.createLinearGradient(-s, -s, s, s);
  grd.addColorStop(0, '#2c2f33'); grd.addColorStop(1, '#1a1c1f');
  c.fillStyle = grd; round(c, -s, -s, 2 * s, 2 * s, r * 0.14); c.fill();
  for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const px = sx * s * 0.83, py = sy * s * 0.83, sr = r * 0.06;
    const sg = c.createRadialGradient(px - sr * 0.3, py - sr * 0.3, sr * 0.1, px, py, sr);
    sg.addColorStop(0, '#8d9196'); sg.addColorStop(1, '#3b3e42');
    c.fillStyle = sg; c.beginPath(); c.arc(px, py, sr, 0, TAU); c.fill();
    c.strokeStyle = '#1b1d20'; c.lineWidth = Math.max(1, r * 0.015);
    c.beginPath(); c.moveTo(px - sr * 0.7, py - sr * 0.2); c.lineTo(px + sr * 0.7, py + sr * 0.2); c.stroke();
  }
  // the bezel
  const bz = c.createLinearGradient(0, -r, 0, r);
  bz.addColorStop(0, '#53575c'); bz.addColorStop(0.5, '#1f2124'); bz.addColorStop(1, '#3f4246');
  c.fillStyle = bz; c.beginPath(); c.arc(0, 0, r * 1.03, 0, TAU); c.fill();
  c.fillStyle = '#070708'; c.beginPath(); c.arc(0, 0, r * 0.96, 0, TAU); c.fill();
}

function dialBase(c: Ctx, r: number) {
  const f = c.createRadialGradient(0, -r * 0.3, r * 0.1, 0, 0, r);
  f.addColorStop(0, '#1d1f23'); f.addColorStop(1, FACE);
  c.fillStyle = f; c.beginPath(); c.arc(0, 0, r * 0.94, 0, TAU); c.fill();
}

function glassFace(c: Ctx, r: number) {
  c.save();
  c.beginPath(); c.arc(0, 0, r * 0.95, 0, TAU); c.clip();
  const gl = c.createLinearGradient(-r, -r, r * 0.3, r * 0.4);
  gl.addColorStop(0, 'rgba(255,255,255,0.16)'); gl.addColorStop(0.45, 'rgba(255,255,255,0.03)'); gl.addColorStop(1, 'rgba(255,255,255,0)');
  c.fillStyle = gl; c.beginPath(); c.ellipse(-r * 0.25, -r * 0.35, r * 0.95, r * 0.6, -0.6, 0, TAU); c.fill();
  c.restore();
  const sh = c.createRadialGradient(0, 0, r * 0.8, 0, 0, r * 0.96);
  sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,0.45)');
  c.fillStyle = sh; c.beginPath(); c.arc(0, 0, r * 0.96, 0, TAU); c.fill();
}

function ticks(c: Ctx, r: number, at: (v: number) => number, from: number, to: number, step: number, major: number, col = INK) {
  c.strokeStyle = col; c.lineCap = 'butt';
  for (let v = from; v <= to + 1e-6; v += step) {
    const big = Math.abs(v % major) < 1e-6 || Math.abs((v % major) - major) < 1e-6;
    const a = at(v), [x0, y0] = pt(a, r * 0.9), [x1, y1] = pt(a, r * (big ? 0.74 : 0.82));
    c.lineWidth = big ? Math.max(1.4, r * 0.035) : Math.max(1, r * 0.018);
    c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke();
  }
}

function arcBand(c: Ctx, r: number, at: (v: number) => number, v0: number, v1: number, col: string, rad = 0.865, wd = 0.07) {
  c.strokeStyle = col; c.lineWidth = r * wd; c.lineCap = 'butt';
  c.beginPath(); c.arc(0, 0, r * rad, at(v0) - Math.PI / 2, at(v1) - Math.PI / 2); c.stroke();
}

function redLine(c: Ctx, r: number, a: number) {
  const [x0, y0] = pt(a, r * 0.93), [x1, y1] = pt(a, r * 0.74);
  c.strokeStyle = '#e0362c'; c.lineWidth = Math.max(2, r * 0.05);
  c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke();
}

function label(c: Ctx, s: string, x: number, y: number, size: number, col = DIM, weight = 600) {
  c.fillStyle = col; c.font = `${weight} ${Math.max(6, Math.round(size))}px ${SANS}`; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillText(s, x, y);
}

function numbers(c: Ctx, r: number, at: (v: number) => number, vals: number[], text: (v: number) => string, rad = 0.6, size = 0.19) {
  for (const v of vals) { const [x, y] = pt(at(v), r * rad); label(c, text(v), x, y + r * 0.01, r * size, INK, 700); }
}

function asiFace(c: Ctx, r: number, plane: boolean) {
  dialBase(c, r);
  const at = plane ? ASI_PLANE : ASI_HELI;
  if (plane) {
    arcBand(c, r, at, 33, 85, '#f2f2f2', 0.79, 0.06);
    arcBand(c, r, at, 44, 129, '#38b354');
    arcBand(c, r, at, 129, 163, '#e3b72e');
    ticks(c, r, at, 40, 170, 5, 10);
    numbers(c, r, at, [40, 60, 80, 100, 120, 140, 160], String);
    redLine(c, r, at(163));
  } else {
    arcBand(c, r, at, 20, 130, '#38b354');
    ticks(c, r, at, 20, 150, 5, 10);
    numbers(c, r, at, [20, 40, 60, 80, 100, 120, 140], String);
    redLine(c, r, at(140));
  }
  label(c, 'AIRSPEED', 0, -r * 0.28, r * 0.12);
  label(c, 'KNOTS', 0, r * 0.32, r * 0.12);
}

function altFace(c: Ctx, r: number) {
  dialBase(c, r);
  const at = (v: number) => (v / 1000) * TAU;
  ticks(c, r, at, 0, 980, 20, 100);
  numbers(c, r, at, [0, 100, 200, 300, 400, 500, 600, 700, 800, 900], (v) => String(v / 100), 0.6, 0.21);
  // the pressure window at three o'clock
  c.fillStyle = '#000'; round(c, r * 0.24, -r * 0.1, r * 0.36, r * 0.2, r * 0.03); c.fill();
  c.strokeStyle = '#55595e'; c.lineWidth = 1; c.stroke();
  label(c, '1013', r * 0.42, 0, r * 0.13, INK, 700);
  label(c, 'ALT', 0, -r * 0.3, r * 0.13);
  label(c, '100 FT', 0, r * 0.3, r * 0.1);
}

function vsiFace(c: Ctx, r: number) {
  dialBase(c, r);
  for (const sgn of [1, -1]) {
    const at = (v: number) => VSI(sgn * v);
    ticks(c, r, at, 0, 1000, 100, 500);
    ticks(c, r, at, 1000, 2000, 250, 500);
    numbers(c, r, at, [500, 1000, 1500, 2000], (v) => String(v / 100), 0.6, 0.18);
  }
  label(c, '0', ...pt(-Math.PI / 2, r * 0.6), r * 0.19, INK, 700);
  label(c, 'UP', -r * 0.26, -r * 0.24, r * 0.12);
  label(c, 'DOWN', -r * 0.26, r * 0.24, r * 0.12);
  label(c, 'VERTICAL SPEED', r * 0.12, -r * 0.26, r * 0.075);
  label(c, '100 FT/MIN', r * 0.12, r * 0.26, r * 0.075);
}

function gaugeFace(c: Ctx, r: number, name: string, unit: string, at: (v: number) => number, max: number, minor: number, major: number,
  every: number, text: (v: number) => string, bands: [number, number, string][], reds: number[], tach = false) {
  dialBase(c, r);
  for (const [a, b, col] of bands) arcBand(c, r, at, a, b, col);
  ticks(c, r, at, 0, max, minor, major);
  const vals: number[] = [];
  for (let v = 0; v <= max; v += every) vals.push(v);
  numbers(c, r, at, vals, text, 0.58, tach ? 0.17 : 0.16);
  for (const v of reds) redLine(c, r, at(v));
  label(c, name, 0, -r * 0.3, r * 0.12);
  label(c, unit, 0, tach ? r * 0.22 : r * 0.34, r * 0.11);
}

function hourMeter(g: Ctx, x: number, y: number, r: number, hours: number) {
  const s = hours.toFixed(1).padStart(6, '0');
  g.fillStyle = '#000'; round(g, x - r * 0.24, y - r * 0.08, r * 0.48, r * 0.16, r * 0.02); g.fill();
  g.fillStyle = '#e8e8e8'; g.font = `600 ${Math.max(6, Math.round(r * 0.12))}px ui-monospace, Menlo, Consolas, monospace`;
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(s, x, y + 1);
}

function aiCase(c: Ctx, r: number) {
  // the bank marks on the case, the fixed base and the little aeroplane
  c.strokeStyle = INK; c.fillStyle = INK;
  for (const d of [-60, -30, -20, -10, 10, 20, 30, 60]) {
    const a = d * DEG, big = Math.abs(d) === 30 || Math.abs(d) === 60;
    const [x0, y0] = pt(a, r * 0.95), [x1, y1] = pt(a, r * (big ? 0.8 : 0.86));
    c.lineWidth = big ? Math.max(1.5, r * 0.035) : Math.max(1, r * 0.022);
    c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke();
  }
  for (const d of [-45, 45]) {
    const [x, y] = pt(d * DEG, r * 0.9);
    c.save(); c.translate(x, y); c.rotate(d * DEG);
    c.beginPath(); c.moveTo(0, r * 0.04); c.lineTo(-r * 0.035, -r * 0.03); c.lineTo(r * 0.035, -r * 0.03); c.closePath(); c.fill();
    c.restore();
  }
  c.fillStyle = '#ff8a1e';
  c.beginPath(); c.moveTo(0, -r * 0.8); c.lineTo(-r * 0.06, -r * 0.93); c.lineTo(r * 0.06, -r * 0.93); c.closePath(); c.fill();
  c.fillStyle = '#16171a';
  c.beginPath(); c.moveTo(-r * 0.12, r * 0.52); c.lineTo(r * 0.12, r * 0.52); c.lineTo(r * 0.42, r * 0.85); c.arc(0, 0, r * 0.95, 0.94, Math.PI - 0.94); c.closePath(); c.fill();
  c.strokeStyle = '#ff8a1e'; c.fillStyle = '#ff8a1e'; c.lineCap = 'round'; c.lineWidth = Math.max(2, r * 0.055);
  c.beginPath(); c.moveTo(-r * 0.56, 0); c.lineTo(-r * 0.2, 0); c.lineTo(-r * 0.1, r * 0.09);
  c.moveTo(r * 0.56, 0); c.lineTo(r * 0.2, 0); c.lineTo(r * 0.1, r * 0.09); c.stroke();
  c.beginPath(); c.arc(0, 0, r * 0.045, 0, TAU); c.fill();
}

function tcFace(c: Ctx, r: number) {
  dialBase(c, r);
  c.strokeStyle = INK; c.lineWidth = Math.max(1.5, r * 0.04);
  for (const [a, b] of [[-90, -90], [90, 90], [-110, -110], [110, 110]]) {
    const [x0, y0] = pt(a * DEG, r * 0.9), [x1, y1] = pt(b * DEG, r * 0.72);
    c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke();
  }
  label(c, 'L', ...pt(-118 * DEG, r * 0.62), r * 0.15, INK, 700);
  label(c, 'R', ...pt(118 * DEG, r * 0.62), r * 0.15, INK, 700);
  label(c, 'TURN COORDINATOR', 0, -r * 0.55, r * 0.085);
  label(c, '2 MIN', 0, r * 0.8, r * 0.09);
  // the inclinometer's tube
  c.fillStyle = '#d9d2b8';
  c.beginPath();
  c.moveTo(-r * 0.4, r * 0.53); c.quadraticCurveTo(0, r * 0.38, r * 0.4, r * 0.53);
  c.lineTo(r * 0.4, r * 0.7); c.quadraticCurveTo(0, r * 0.55, -r * 0.4, r * 0.7); c.closePath();
  c.save(); c.clip();
  const tb = c.createLinearGradient(0, r * 0.4, 0, r * 0.7);
  tb.addColorStop(0, '#f1ead2'); tb.addColorStop(1, '#a9a28a');
  c.fillStyle = tb; c.fillRect(-r, -r, 2 * r, 2 * r);
  c.restore();
}

function hiCard(c: Ctx, r: number) {
  dialBase(c, r);
  const at = (v: number) => v * DEG;
  ticks(c, r, at, 0, 355, 5, 10);
  const name: Record<number, string> = { 0: 'N', 90: 'E', 180: 'S', 270: 'W' };
  for (let d = 0; d < 360; d += 30) {
    c.save(); c.rotate(d * DEG);
    label(c, name[d] ?? String(d / 10), 0, -r * 0.6, r * (name[d] ? 0.22 : 0.17), name[d] === 'N' ? '#ff8a1e' : INK, 700);
    c.restore();
  }
}

function hiCase(c: Ctx, r: number) {
  c.fillStyle = '#ff8a1e';
  c.beginPath(); c.moveTo(0, -r * 0.76); c.lineTo(-r * 0.06, -r * 0.94); c.lineTo(r * 0.06, -r * 0.94); c.closePath(); c.fill();
  c.fillStyle = INK;
  for (const d of [45, 90, 135, 180, 225, 270, 315]) {
    const [x, y] = pt(d * DEG, r * 0.93);
    c.save(); c.translate(x, y); c.rotate(d * DEG);
    c.beginPath(); c.moveTo(0, r * 0.05); c.lineTo(-r * 0.03, -r * 0.01); c.lineTo(r * 0.03, -r * 0.01); c.closePath(); c.fill();
    c.restore();
  }
  // the aeroplane in the middle
  c.fillStyle = '#ff8a1e';
  c.beginPath();
  c.moveTo(0, -r * 0.36); c.lineTo(r * 0.035, -r * 0.28); c.lineTo(r * 0.035, -r * 0.1); c.lineTo(r * 0.3, r * 0.02); c.lineTo(r * 0.3, r * 0.07);
  c.lineTo(r * 0.035, r * 0.03); c.lineTo(r * 0.03, r * 0.2); c.lineTo(r * 0.12, r * 0.27); c.lineTo(r * 0.12, r * 0.31); c.lineTo(0, r * 0.28);
  c.lineTo(-r * 0.12, r * 0.31); c.lineTo(-r * 0.12, r * 0.27); c.lineTo(-r * 0.03, r * 0.2); c.lineTo(-r * 0.035, r * 0.03);
  c.lineTo(-r * 0.3, r * 0.07); c.lineTo(-r * 0.3, r * 0.02); c.lineTo(-r * 0.035, -r * 0.1); c.lineTo(-r * 0.035, -r * 0.28); c.closePath();
  c.fill();
}

// a needle: white, tapered, with a counterweight and a black hub
function needle(g: Ctx, x: number, y: number, len: number, a: number, r: number, wide = 1) {
  const w = r * 0.035 * wide;
  g.save(); g.translate(x, y); g.rotate(a);
  g.shadowColor = 'rgba(0,0,0,0.55)'; g.shadowBlur = r * 0.06; g.shadowOffsetX = r * 0.02; g.shadowOffsetY = r * 0.03;
  g.fillStyle = '#f4f4f2';
  g.beginPath(); g.moveTo(-w, 0); g.lineTo(-w * 0.45, -len * 0.92); g.lineTo(0, -len); g.lineTo(w * 0.45, -len * 0.92); g.lineTo(w, 0);
  g.lineTo(w * 1.3, len * 0.2); g.lineTo(-w * 1.3, len * 0.2); g.closePath(); g.fill();
  g.shadowColor = 'transparent';
  g.fillStyle = '#1b1c1e'; g.beginPath(); g.arc(0, 0, r * 0.08, 0, TAU); g.fill();
  g.fillStyle = '#4a4d51'; g.beginPath(); g.arc(0, 0, r * 0.035, 0, TAU); g.fill();
  g.restore();
}

// the altimeter's 10,000 ft pointer: a thin hand with a wedge near its tip
function pointer10k(g: Ctx, x: number, y: number, r: number, a: number) {
  g.save(); g.translate(x, y); g.rotate(a);
  g.fillStyle = '#f4f4f2';
  g.fillRect(-r * 0.01, -r * 0.88, r * 0.02, r * 0.88);
  g.beginPath(); g.moveTo(0, -r * 0.92); g.lineTo(-r * 0.05, -r * 0.8); g.lineTo(r * 0.05, -r * 0.8); g.closePath(); g.fill();
  g.restore();
}

function round(g: Ctx, x: number, y: number, w: number, h: number, r: number) {
  g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}
