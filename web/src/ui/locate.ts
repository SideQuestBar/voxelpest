// Where you are, on phones: the locate button asks for the position (only when pressed; it stays on the device), and
// if it falls on the map puts a dot there with the accuracy round it and flies the map over; tapping the dot walks
// from the nearest street. GPS is WGS84; geo.ts turns it into the map's grid.
import { track } from '../analytics';
import * as THREE from 'three';
import { wgsToGrid } from '../geo';
import { onLang, T } from '../i18n';
import type { Meta } from '../meta';
import { isTouch } from '../util';

export interface LocateHandlers {
  ground(x: number, z: number): Promise<number>;
  fly(x: number, y: number, z: number, r: number): void;
  walk(x: number, z: number): void;
  toast(text: string): void;
}

export class Locate {
  private readonly btn = document.getElementById('locate') as HTMLButtonElement;
  private readonly pin = document.createElement('button');
  private readonly at = new THREE.Vector3();
  private readonly v = new THREE.Vector3();
  private ring: THREE.Group | null = null;
  private found = false;
  private asking = false;

  constructor(private readonly meta: Meta, private readonly scene: THREE.Scene, private readonly on: LocateHandlers) {
    if (!isTouch() || !('geolocation' in navigator)) return;
    this.btn.hidden = false;
    this.btn.onclick = () => this.ask();
    this.pin.id = 'me-pin';
    this.pin.style.display = 'none';
    this.pin.onclick = () => this.on.walk(this.at.x, this.at.z);
    document.getElementById('labels')!.after(this.pin);
    this.text();
    onLang(() => this.text());
  }

  private text() {
    const t = T();
    this.btn.setAttribute('aria-label', t.locate);
    this.pin.setAttribute('aria-label', t.youHere);
  }

  private ask() {
    if (this.asking) return;
    this.asking = true;
    this.btn.classList.add('busy');
    this.on.toast(T().locating);
    navigator.geolocation.getCurrentPosition((p) => void this.place(p.coords), (e) => {
      this.done();
      this.on.toast(e.code === e.PERMISSION_DENIED ? T().locDenied : T().locFailed);
      track('locate', { result: e.code === e.PERMISSION_DENIED ? 'denied' : 'failed' });
    }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 15000 });
  }

  private done() {
    this.asking = false;
    this.btn.classList.remove('busy');
  }

  private async place(c: GeolocationCoordinates) {
    const [x, z] = wgsToGrid(c.longitude, c.latitude), m = this.meta;
    if (!(x >= 0 && z >= 0 && x <= m.W * m.vox && z <= m.D * m.vox)) {
      this.done();
      this.on.toast(T().outside);
      track('locate', { result: 'outside' });
      return;
    }
    const y = await this.on.ground(x, z);
    this.done();
    this.at.set(x, y, z);
    this.found = true;
    this.btn.classList.add('found');
    const r = Math.min(Math.max(c.accuracy || 0, 3), 400);
    const ring = this.ring ??= this.makeRing();
    ring.position.set(x, y + 0.7, z);
    ring.scale.setScalar(r);
    ring.visible = true;
    this.on.fly(x, y, z, r);
    this.on.toast(T().located);
    track('locate', { result: 'found' });   // the outcome only, never where
  }

  // the accuracy: a pale disc with a rim, on the ground round the dot
  private makeRing() {
    const g = new THREE.Group(), blue = 0x1f6fd1;
    const disc = new THREE.Mesh(new THREE.CircleGeometry(1, 64), new THREE.MeshBasicMaterial({ color: blue, transparent: true, opacity: 0.16, depthWrite: false }));
    const rim = new THREE.Mesh(new THREE.RingGeometry(0.97, 1, 64), new THREE.MeshBasicMaterial({ color: blue, transparent: true, opacity: 0.5, depthWrite: false }));
    for (const o of [disc, rim]) { o.rotation.x = -Math.PI / 2; o.renderOrder = 2; g.add(o); }
    this.scene.add(g);
    return g;
  }

  update(camera: THREE.PerspectiveCamera, w: number, h: number) {
    if (!this.found) return;
    const d = this.at.distanceTo(camera.position), v = this.v.copy(this.at).project(camera);
    const ok = v.z < 1 && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05 && d < 6000;
    this.pin.style.display = ok ? '' : 'none';
    if (ok) this.pin.style.transform = `translate(${(((v.x + 1) / 2) * w).toFixed(1)}px, ${(((1 - v.y) / 2) * h).toFixed(1)}px) translate(-50%, -50%)`;
  }
}
