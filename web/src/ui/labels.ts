// Place names over the map, in the chosen language: the biggest places first, each shown within its own distance,
// never two overlapping. Names already on screen keep their place over newcomers, so turning the map doesn't make them
// flicker as they cross.
import * as THREE from 'three';
import { onLang, placeName } from '../i18n';
import type { Label } from '../meta';
import { esc } from '../util';

export class Labels {
  on = true;
  private readonly items: { l: Label; el: HTMLButtonElement; w: number; shown: boolean; x: number; y: number }[] = [];
  private readonly v = new THREE.Vector3();

  constructor(root: HTMLElement, labels: Label[], onClick: (l: Label) => void) {
    for (const l of labels.slice(0, 240)) {
      const el = document.createElement('button');
      el.className = 'label';
      el.style.display = 'none';
      el.onclick = () => onClick(l);
      root.appendChild(el);
      this.items.push({ l, el, w: 0, shown: false, x: 0, y: 0 });
    }
    this.text();
    onLang(() => this.text());
  }

  private text() {
    for (const it of this.items) {
      const main = placeName(it.l), other = main === it.l.name ? it.l.en : it.l.name;
      it.el.innerHTML = `<b>${esc(main)}</b>${other && other !== main ? `<i>${esc(other)}</i>` : ''}`;
      it.w = 10 + 6.6 * main.length;
    }
  }

  // call with the camera's matrices up to date for this frame (camera.updateMatrixWorld()), or the names lag a frame
  // behind the city and shake while it turns
  update(camera: THREE.PerspectiveCamera, w: number, h: number, far = 1) {
    const taken: number[][] = [], wants: typeof this.items = [];
    for (const it of this.items) {
      const l = it.l;
      this.v.set(l.x + 0.5, l.z, l.y + 0.5);
      const d = this.v.distanceTo(camera.position);
      this.v.project(camera);
      it.x = ((this.v.x + 1) / 2) * w; it.y = ((1 - this.v.y) / 2) * h;
      if (this.on && this.v.z < 1 && Math.abs(this.v.x) < 1.05 && Math.abs(this.v.y) < 1.05 && d < l.far * far && d > 25) wants.push(it);
    }
    const show = new Set<(typeof this.items)[number]>();
    for (const pass of [true, false]) {
      for (const it of wants) {
        if (it.shown !== pass) continue;
        const r = [it.x - it.w / 2, it.y - 30, it.x + it.w / 2, it.y];
        if (taken.some((q) => r[0] < q[2] && r[2] > q[0] && r[1] < q[3] && r[3] > q[1])) continue;
        taken.push(r);
        show.add(it);
      }
    }
    for (const it of this.items) {
      const ok = show.has(it);
      if (ok !== it.shown) it.el.style.display = ok ? '' : 'none';
      it.shown = ok;
      if (ok) it.el.style.transform = `translate3d(${it.x.toFixed(1)}px, ${it.y.toFixed(1)}px, 0) translate(-50%, -100%)`;
    }
  }
}
