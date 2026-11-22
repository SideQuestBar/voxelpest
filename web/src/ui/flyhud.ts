// Fly mode's screen: the aircraft picker (a .seg under the switches, like drive mode's vehicles) and what is drawn
// over the picture on a canvas: for the FPV drone a Betaflight-style OSD (the crosshair, an artificial horizon and its
// ladder, battery, timer, speed, altitude, the way home), for the plane and the helicopter a panel of round gauges
// (airspeed, attitude, altimeter, heading, vertical speed; the plane's throttle, the helicopter's torque).
import { track } from '../analytics';
import { AIRCRAFT, saveAircraft, startAircraft, type AircraftKind } from '../controls/aircraft';
import type { Flyer, Telemetry } from '../controls/fly';
import { PAD, type Input } from '../controls/input';
import { onLang, T } from '../i18n';
import { $ } from '../util';

const NAME = { drone: 'aDrone', plane: 'aPlane', heli: 'aHeli' } as const;
const KT = 1.94384, FT = 3.28084, ASL = 98;   // m/s to knots, m to feet; the model's base above sea level
const TAU = Math.PI * 2;

export class FlyHud {
  private readonly root = $('#aircraft');
  private readonly buttons = [...this.root.querySelectorAll<HTMLButtonElement>('button[data-aircraft]')];
  private readonly canvas = $<HTMLCanvasElement>('#flyhud');
  private readonly g = this.canvas.getContext('2d')!;
  private on = false;

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
    const t = this.flyer.telemetry();
    if (t.kind === 'drone') this.osd(g, w, h, t);
    else this.panel(g, w, h, t);
  }

  // ---------------------------------------------------------------- the FPV OSD
  private osd(g: CanvasRenderingContext2D, w: number, h: number, t: Telemetry) {
    const s = Math.max(0.75, Math.min(w, h * 1.4) / 900), fs = Math.round(17 * s);
    const txt = (str: string, x: number, y: number, align: CanvasTextAlign = 'left', size = fs, col = '#ffffff') => {
      g.font = `700 ${size}px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace`;
      g.textAlign = align; g.textBaseline = 'middle';
      g.lineWidth = Math.max(2, size / 5); g.lineJoin = 'round'; g.strokeStyle = 'rgba(0,0,0,0.85)'; g.strokeText(str, x, y);
      g.fillStyle = col; g.fillText(str, x, y);
    };
    const cx = w / 2, cy = h / 2, m = 22 * s;
    // the artificial horizon and its ladder, round the middle
    g.save();
    g.translate(cx, cy);
    g.rotate(-t.roll);
    const ppd = (h * 0.5) / 30;                        // pixels per degree of pitch
    const off = (t.pitch * 180) / Math.PI * ppd;
    g.strokeStyle = '#ffffff'; g.lineWidth = 2.2 * s; g.shadowColor = 'rgba(0,0,0,0.9)'; g.shadowBlur = 3;
    g.beginPath(); g.moveTo(-150 * s, off); g.lineTo(-40 * s, off); g.moveTo(40 * s, off); g.lineTo(150 * s, off); g.stroke();
    for (const d of [-20, -10, 10, 20]) {
      const y = off - d * ppd;
      g.setLineDash(d < 0 ? [6 * s, 5 * s] : []);
      g.beginPath(); g.moveTo(-70 * s, y); g.lineTo(-30 * s, y); g.moveTo(30 * s, y); g.lineTo(70 * s, y); g.stroke();
    }
    g.setLineDash([]);
    g.restore();
    g.shadowBlur = 0;
    // the crosshair
    g.strokeStyle = '#ffffff'; g.lineWidth = 2 * s;
    g.beginPath(); g.moveTo(cx - 14 * s, cy); g.lineTo(cx - 5 * s, cy); g.moveTo(cx + 5 * s, cy); g.lineTo(cx + 14 * s, cy);
    g.moveTo(cx, cy - 8 * s); g.lineTo(cx, cy - 3 * s); g.stroke();
    // the corners: battery and current, link quality, timer, mode; speed and altitude at the sides
    const volt = Math.max(13.2, 16.8 - t.time * 0.008 - (1 - t.power) * 0.0 + (t.power - 0.5) * -0.4);
    const mah = Math.round(t.time * 9 + t.power * 30);
    txt(`${volt.toFixed(1)}V`, m, m + fs, 'left', fs, volt < 14 ? '#ff5b4f' : '#ffffff');
    txt(`${String(mah).padStart(4, '0')}mAh`, m, m + fs * 2.3);
    txt(`RSSI ${Math.round(99 - Math.min(t.home / 40, 60))}`, w - m, m + fs, 'right');
    const mm = Math.floor(t.time / 60), ss = Math.floor(t.time % 60);
    txt(`${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`, w - m, m + fs * 2.3, 'right');
    txt('ANGL', cx, m + fs, 'center');
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
    else if (volt < 14) txt('LOW BATTERY', cx, cy - 60 * s, 'center', fs, '#ff5b4f');
  }

  // ---------------------------------------------------------------- the gauges
  private panel(g: CanvasRenderingContext2D, w: number, h: number, t: Telemetry) {
    const n = 6, small = w < 700 || h < 500;
    const r = Math.min(small ? 34 : 50, (w - 40) / (n * 2.3));
    const gap = r * 2.3, y = h - r - (small ? 64 : 76), x0 = w / 2 - (gap * (n - 1)) / 2;
    g.fillStyle = 'rgba(18, 20, 23, 0.55)';
    const pw = gap * n + r * 0.2, ph = r * 2 + 22;
    round(g, w / 2 - pw / 2, y - r - 11, pw, ph, 12);
    g.fill();
    const kind = t.kind;
    const gauges: ((x: number) => void)[] = [
      (x) => this.dial(g, x, y, r, 'KT', t.speed * KT, 0, kind === 'plane' ? 160 : 160, kind === 'plane' ? [[0, 47, '#2b2f33'], [47, 85, '#ffffff'], [50, 125, '#3dbb5a'], [125, 160, '#e8c43a']] : [[0, 130, '#3dbb5a'], [130, 160, '#e8c43a']]),
      (x) => this.attitude(g, x, y, r, t.pitch, t.roll),
      (x) => this.altimeter(g, x, y, r, (t.alt + ASL) * FT),
      (x) => this.compass(g, x, y, r, t.heading),
      (x) => this.dial(g, x, y, r, 'VS', t.vs * FT * 60 / 100, -20, 20, [], 'ft/min ×100', true),
      (x) => this.dial(g, x, y, r, kind === 'plane' ? 'RPM' : 'TRQ', kind === 'plane' ? 700 + t.power * 2000 : t.power * 100, 0, kind === 'plane' ? 3000 : 120,
        kind === 'plane' ? [[2100, 2700, '#3dbb5a'], [2700, 3000, '#d9443a']] : [[0, 100, '#3dbb5a'], [100, 120, '#d9443a']], kind === 'plane' ? '×100' : '%'),
    ];
    gauges.forEach((f, i) => f(x0 + i * gap));
    const tt = T();
    const warn = t.crashed ? tt.crashed : t.stall ? tt.stall : t.ground ? tt.onGround : '';
    if (warn) {
      g.font = `800 ${Math.round(r * 0.42)}px system-ui, sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillStyle = t.crashed || t.stall ? '#ff5b4f' : '#ffffff'; g.fillText(warn, w / 2, y - r - 26);
    }
  }

  private face(g: CanvasRenderingContext2D, x: number, y: number, r: number) {
    g.fillStyle = '#16181b'; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill();
    g.strokeStyle = '#6b7075'; g.lineWidth = Math.max(1.5, r * 0.06); g.beginPath(); g.arc(x, y, r, 0, TAU); g.stroke();
  }

  private needle(g: CanvasRenderingContext2D, x: number, y: number, len: number, a: number, wd: number, col = '#ffffff') {
    g.save(); g.translate(x, y); g.rotate(a);
    g.fillStyle = col; g.beginPath(); g.moveTo(-wd, len * 0.12); g.lineTo(0, -len); g.lineTo(wd, len * 0.12); g.closePath(); g.fill();
    g.restore();
  }

  // a round dial from v0 to v1 over 300°, coloured arcs, a needle; centred zero if `zero`
  private dial(g: CanvasRenderingContext2D, x: number, y: number, r: number, label: string, v: number, v0: number, v1: number,
    arcs: [number, number, string][], unit = '', zero = false) {
    this.face(g, x, y, r);
    const a0 = zero ? -Math.PI : -Math.PI * 5 / 6, a1 = zero ? 0 : Math.PI * 5 / 6;
    const ang = (u: number) => (zero ? -Math.PI / 2 + ((u - v0) / (v1 - v0) - 0.5) * Math.PI * 1.6 : a0 + ((u - v0) / (v1 - v0)) * (a1 - a0));
    for (const [p, q, col] of arcs) {
      g.strokeStyle = col; g.lineWidth = r * 0.09;
      g.beginPath(); g.arc(x, y, r * 0.84, ang(p) - Math.PI / 2, ang(q) - Math.PI / 2); g.stroke();
    }
    g.strokeStyle = '#d9dcde'; g.lineWidth = Math.max(1, r * 0.03);
    for (let k = 0; k <= 10; k++) {
      const a = ang(v0 + ((v1 - v0) * k) / 10) - Math.PI / 2;
      g.beginPath(); g.moveTo(x + Math.cos(a) * r * 0.72, y + Math.sin(a) * r * 0.72); g.lineTo(x + Math.cos(a) * r * 0.92, y + Math.sin(a) * r * 0.92); g.stroke();
    }
    g.fillStyle = '#c9ccce'; g.font = `600 ${Math.round(r * 0.24)}px system-ui, sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(label, x, y + r * 0.42);
    g.fillStyle = '#ffffff'; g.font = `700 ${Math.round(r * 0.3)}px ui-monospace, Menlo, Consolas, monospace`;
    g.fillText(String(Math.round(zero ? v * 100 / 100 : v)), x, y - r * 0.34);
    if (unit) { g.fillStyle = '#8f9498'; g.font = `500 ${Math.round(r * 0.16)}px system-ui, sans-serif`; g.fillText(unit, x, y + r * 0.66); }
    this.needle(g, x, y, r * 0.8, ang(Math.max(v0, Math.min(v1, v))), r * 0.06);
  }

  private attitude(g: CanvasRenderingContext2D, x: number, y: number, r: number, pitch: number, roll: number) {
    g.save();
    g.beginPath(); g.arc(x, y, r, 0, TAU); g.clip();
    g.translate(x, y); g.rotate(-roll);
    const off = (pitch * 180 / Math.PI) * (r / 35);
    g.fillStyle = '#3d7fc6'; g.fillRect(-2 * r, -2 * r + off, 4 * r, 2 * r);
    g.fillStyle = '#8a5a32'; g.fillRect(-2 * r, off, 4 * r, 2 * r);
    g.strokeStyle = '#ffffff'; g.lineWidth = Math.max(1, r * 0.03);
    g.beginPath(); g.moveTo(-2 * r, off); g.lineTo(2 * r, off); g.stroke();
    for (const d of [-20, -10, 10, 20]) {
      const yy = off - d * (r / 35), hw = Math.abs(d) === 10 ? r * 0.25 : r * 0.4;
      g.beginPath(); g.moveTo(-hw, yy); g.lineTo(hw, yy); g.stroke();
    }
    g.restore();
    g.strokeStyle = '#6b7075'; g.lineWidth = Math.max(1.5, r * 0.06); g.beginPath(); g.arc(x, y, r, 0, TAU); g.stroke();
    // the little aeroplane, fixed
    g.strokeStyle = '#f1c232'; g.lineWidth = Math.max(2, r * 0.07);
    g.beginPath(); g.moveTo(x - r * 0.55, y); g.lineTo(x - r * 0.18, y); g.lineTo(x - r * 0.08, y + r * 0.1); g.moveTo(x + r * 0.55, y);
    g.lineTo(x + r * 0.18, y); g.lineTo(x + r * 0.08, y + r * 0.1); g.stroke();
    g.fillStyle = '#f1c232'; g.beginPath(); g.arc(x, y, r * 0.05, 0, TAU); g.fill();
  }

  private altimeter(g: CanvasRenderingContext2D, x: number, y: number, r: number, ft: number) {
    this.face(g, x, y, r);
    g.fillStyle = '#d9dcde'; g.font = `600 ${Math.round(r * 0.22)}px system-ui, sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
    for (let k = 0; k < 10; k++) {
      const a = (k / 10) * TAU - Math.PI / 2;
      g.fillText(String(k), x + Math.cos(a) * r * 0.74, y + Math.sin(a) * r * 0.74);
    }
    g.fillStyle = '#ffffff'; g.font = `700 ${Math.round(r * 0.22)}px ui-monospace, Menlo, Consolas, monospace`;
    g.fillText(`${Math.round(ft / 10) * 10}`, x, y + r * 0.38);
    g.fillStyle = '#8f9498'; g.font = `500 ${Math.round(r * 0.15)}px system-ui, sans-serif`; g.fillText('ALT ft', x, y - r * 0.32);
    this.needle(g, x, y, r * 0.5, ((ft / 10000) % 1) * TAU, r * 0.08);
    this.needle(g, x, y, r * 0.82, ((ft / 1000) % 1) * TAU, r * 0.045);
  }

  private compass(g: CanvasRenderingContext2D, x: number, y: number, r: number, heading: number) {
    this.face(g, x, y, r);
    g.save(); g.translate(x, y); g.rotate(-heading);
    g.fillStyle = '#d9dcde'; g.strokeStyle = '#d9dcde'; g.lineWidth = Math.max(1, r * 0.03);
    g.font = `700 ${Math.round(r * 0.22)}px system-ui, sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
    for (let k = 0; k < 36; k++) {
      const a = (k / 36) * TAU;
      g.save(); g.rotate(a);
      g.beginPath(); g.moveTo(0, -r * 0.92); g.lineTo(0, -r * (k % 3 ? 0.84 : 0.78)); g.stroke();
      if (k % 9 === 0) { g.fillStyle = k === 0 ? '#ff6a5c' : '#d9dcde'; g.fillText('NESW'[k / 9], 0, -r * 0.6); }
      else if (k % 3 === 0) { g.font = `600 ${Math.round(r * 0.16)}px system-ui, sans-serif`; g.fillText(String(k), 0, -r * 0.62); g.font = `700 ${Math.round(r * 0.22)}px system-ui, sans-serif`; }
      g.restore();
    }
    g.restore();
    g.strokeStyle = '#f1c232'; g.lineWidth = Math.max(2, r * 0.06);
    g.beginPath(); g.moveTo(x, y - r * 0.4); g.lineTo(x, y + r * 0.3); g.moveTo(x - r * 0.25, y - r * 0.05); g.lineTo(x + r * 0.25, y - r * 0.05);
    g.moveTo(x - r * 0.12, y + r * 0.25); g.lineTo(x + r * 0.12, y + r * 0.25); g.stroke();
    g.fillStyle = '#ffffff'; g.font = `700 ${Math.round(r * 0.2)}px ui-monospace, Menlo, Consolas, monospace`; g.textAlign = 'center';
    g.fillText(String(Math.round(((heading * 180) / Math.PI + 360) % 360)).padStart(3, '0'), x, y + r * 0.62);
  }
}

function round(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}
