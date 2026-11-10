// The vehicle picker of drive mode (a .seg under the switches: the chosen one shows its name), and the police car's
// blue lights beside it. V / Shift+V cycle the vehicles and L switches the lights; on a controller RB / LB and X.
// ?vehicle= picks one for this visit; a choice made here is kept (localStorage).
import { track } from '../analytics';
import type { Car } from '../controls/drive';
import { PAD, type Input } from '../controls/input';
import { KINDS, saveKind, startKind, type VehicleKind } from '../controls/vehicles';
import { onLang, T } from '../i18n';
import { $ } from '../util';

const NAME = { taxi: 'vTaxi', trabant: 'vTrabant', police: 'vPolice', bubi: 'vBubi', bus: 'vBus' } as const;

export class VehiclePicker {
  private readonly root = $('#vehicles');
  private readonly flashBtn = $<HTMLButtonElement>('#flash-btn');
  private readonly buttons = [...this.root.querySelectorAll<HTMLButtonElement>('button[data-vehicle]')];

  constructor(private readonly car: Car, private readonly input: Input, private readonly toast: (text: string) => void) {
    // a click leaves no focus behind: Space (the brake) would press the button again
    for (const b of this.buttons) b.onclick = (e) => { this.pick(b.dataset.vehicle as VehicleKind); if (e.detail) b.blur(); };
    this.flashBtn.onclick = (e) => { this.flash(); if (e.detail) this.flashBtn.blur(); };
    addEventListener('keydown', (e) => {
      if (document.body.dataset.mode !== 'drive' || e.repeat || e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' && (t as HTMLInputElement).type === 'text' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.code === 'KeyV') this.step(e.shiftKey ? -1 : 1);
      if (e.code === 'KeyL') this.flash();
    });
    car.setKind(startKind());
    this.sync();
    this.text();
    onLang(() => this.text());
  }

  // the controller's buttons, once a frame while driving
  poll() {
    if (this.input.pressed(PAD.RB)) this.step(1);
    if (this.input.pressed(PAD.LB)) this.step(-1);
    if (this.input.pressed(PAD.X)) this.flash();
  }

  step(d: number) {
    const n = KINDS.length;
    this.pick(KINDS[(KINDS.indexOf(this.car.kind) + d + n) % n]);
  }

  pick(k: VehicleKind) {
    this.car.setKind(k);
    saveKind(k);
    track('vehicle', { vehicle: k });
    this.sync();
    this.toast(T()[NAME[k]]);
  }

  flash() {
    if (this.car.kind !== 'police') return;
    this.car.flashing = !this.car.flashing;
    this.sync();
  }

  private sync() {
    for (const b of this.buttons) b.setAttribute('aria-pressed', String(b.dataset.vehicle === this.car.kind));
    this.flashBtn.hidden = this.car.kind !== 'police';
    this.flashBtn.setAttribute('aria-pressed', String(this.car.flashing));
  }

  private text() {
    const t = T();
    this.root.setAttribute('aria-label', t.vehicle);
    for (const b of this.buttons) b.title = t[NAME[b.dataset.vehicle as VehicleKind]];
    this.flashBtn.title = t.flashers;
    this.flashBtn.setAttribute('aria-label', t.flashers);
  }
}
