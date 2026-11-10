// Keys held down, the on-screen sticks for touch screens (a stick on the left to move or steer, a look pad on the right
// when walking, pedals when driving) and game controllers (the standard layout: Xbox, PlayStation, Switch Pro). Keys
// typed into a text field don't count.

export const PAD = { A: 0, B: 1, X: 2, Y: 3, LB: 4, RB: 5, LT: 6, RT: 7, VIEW: 8, MENU: 9, LS: 10, RS: 11, UP: 12, DOWN: 13, LEFT: 14, RIGHT: 15 };

export interface Pad { on: boolean; lx: number; ly: number; rx: number; ry: number; lt: number; rt: number; held: boolean[] }

// a stick with a round dead zone, rescaled so it starts from 0 at its edge
function stick(x: number, y: number, dead = 0.16): [number, number] {
  const m = Math.hypot(x, y);
  if (m < dead) return [0, 0];
  const k = Math.min((m - dead) / (1 - dead), 1) / m;
  return [x * k, y * k];
}

export class Input {
  readonly down = new Set<string>();
  readonly stick = { x: 0, y: 0, active: false };       // -1 .. 1; y up is forward
  look = { dx: 0, dy: 0 };                               // touch look, pixels since the last read
  pedal = { gas: false, brake: false };
  onJump: (() => void) | null = null;
  readonly pad: Pad = { on: false, lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0, held: [] };
  onPad: ((on: boolean) => void) | null = null;
  private prevHeld: boolean[] = [];
  private real: boolean[] = [];  // the buttons as read, which mute() hides from pad.held for a frame
  private stickId: number | null = null;
  private lookId: number | null = null;
  private origin = { x: 0, y: 0 };
  private last = { x: 0, y: 0 };
  private lastTap = 0;

  constructor(touchRoot: HTMLElement) {
    addEventListener('keydown', (e) => {
      if (this.typing(e)) return;
      if (e.code === 'Space' && (e.target as HTMLElement | null)?.matches?.('button:focus-visible')) return;  // Tab to a button, Space presses it
      this.down.add(e.code);
      if (e.code === 'Space' || e.code.startsWith('Arrow')) e.preventDefault();
    });
    addEventListener('keyup', (e) => this.down.delete(e.code));
    addEventListener('blur', () => this.down.clear());
    addEventListener('gamepadconnected', () => this.onPad?.(true));
    addEventListener('gamepaddisconnected', () => { if (!this.gamepad()) { this.pad.on = false; this.onPad?.(false); } });
    const stick = touchRoot.querySelector<HTMLElement>('.stick')!, knob = stick.querySelector<HTMLElement>('.knob')!;
    const pad = touchRoot.querySelector<HTMLElement>('.look')!;
    stick.addEventListener('touchstart', (e) => {
      const t = e.changedTouches[0];
      this.stickId = t.identifier;
      const r = stick.getBoundingClientRect();
      this.origin = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      this.moveStick(t.clientX, t.clientY, knob);
      e.preventDefault();
    }, { passive: false });
    pad.addEventListener('touchstart', (e) => {
      const t = e.changedTouches[0];
      this.lookId = t.identifier;
      this.last = { x: t.clientX, y: t.clientY };
      const now = performance.now();
      if (now - this.lastTap < 300) this.onJump?.();
      this.lastTap = now;
      e.preventDefault();
    }, { passive: false });
    addEventListener('touchmove', (e) => {
      for (const t of Array.from(e.changedTouches)) {
        if (t.identifier === this.stickId) this.moveStick(t.clientX, t.clientY, knob);
        if (t.identifier === this.lookId) {
          this.look.dx += t.clientX - this.last.x; this.look.dy += t.clientY - this.last.y;
          this.last = { x: t.clientX, y: t.clientY };
        }
      }
    }, { passive: true });
    const end = (e: TouchEvent) => {
      for (const t of Array.from(e.changedTouches)) {
        if (t.identifier === this.stickId) {
          this.stickId = null;
          Object.assign(this.stick, { x: 0, y: 0, active: false });
          knob.style.transform = '';
        }
        if (t.identifier === this.lookId) this.lookId = null;
      }
    };
    addEventListener('touchend', end);
    addEventListener('touchcancel', end);
    for (const [sel, k] of [['.gas', 'gas'], ['.brake', 'brake']] as const) {
      const b = touchRoot.querySelector<HTMLElement>(sel)!;
      b.addEventListener('touchstart', (e) => { this.pedal[k] = true; e.preventDefault(); }, { passive: false });
      b.addEventListener('touchend', () => { this.pedal[k] = false; });
    }
  }

  private typing(e: KeyboardEvent) {
    const t = e.target as HTMLElement | null;
    return !!t && (t.tagName === 'INPUT' && (t as HTMLInputElement).type === 'text' || t.tagName === 'TEXTAREA' || t.isContentEditable);
  }

  private moveStick(x: number, y: number, knob: HTMLElement) {
    const R = 46;
    let dx = x - this.origin.x, dy = y - this.origin.y;
    const d = Math.hypot(dx, dy);
    if (d > R) { dx *= R / d; dy *= R / d; }
    Object.assign(this.stick, { x: dx / R, y: -dy / R, active: true });
    knob.style.transform = `translate(${dx}px, ${dy}px)`;
  }

  private gamepad() {
    let best: Gamepad | null = null;
    for (const g of navigator.getGamepads?.() ?? []) if (g?.connected && (!best || g.timestamp > best.timestamp)) best = g;
    return best;
  }

  // read the controller once a frame (the browser only reports one after a button has been pressed on it)
  poll() {
    const p = this.pad, g = this.gamepad();
    this.prevHeld = this.real;
    if (!g) {
      Object.assign(p, { on: false, lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0, held: (this.real = []) });
      return;
    }
    const ax = (i: number) => g.axes[i] ?? 0, btn = (i: number) => g.buttons[i];
    [p.lx, p.ly] = stick(ax(0), ax(1));
    [p.rx, p.ry] = stick(ax(2), ax(3));
    const trig = (i: number) => { const v = btn(i)?.value ?? 0; return v < 0.06 ? 0 : v; };
    p.lt = trig(PAD.LT); p.rt = trig(PAD.RT);
    p.held = this.real = g.buttons.map((b) => b.pressed);
    if (!p.on) { p.on = true; this.onPad?.(true); }
  }

  // a controller button that went down since the last frame
  pressed(b: number) { return !!this.pad.held[b] && !this.prevHeld[b]; }

  // nothing from the controller for the rest of this frame (a menu has it); a button still held after is no new press
  mute() { Object.assign(this.pad, { lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0, held: [] }); }

  // forward / sideways from the keys, the touch stick or the left stick, -1..1
  move() {
    let fwd = this.axis(['KeyS', 'ArrowDown'], ['KeyW', 'ArrowUp']), side = this.axis(['KeyA', 'ArrowLeft'], ['KeyD', 'ArrowRight']);
    if (this.stick.active) { fwd = this.stick.y; side = this.stick.x; }
    if (this.pad.lx || this.pad.ly) { fwd = -this.pad.ly; side = this.pad.lx; }
    return { fwd, side };
  }

  has(...codes: string[]) { return codes.some((c) => this.down.has(c)); }

  axis(neg: string[], pos: string[]) { return (this.has(...pos) ? 1 : 0) - (this.has(...neg) ? 1 : 0); }

  takeLook() { const l = this.look; this.look = { dx: 0, dy: 0 }; return l; }
}
