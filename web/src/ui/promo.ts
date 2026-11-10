// The two overlays: "Play in Minecraft" (the number of players on the server, and how to join) and SideQuest Bar,
// who made the map (its card, and a pin over the bar). The Minecraft card is behind a feature flag: VITE_MINECRAFT at
// build time (web.env's MINECRAFT), ?minecraft=1 or ?minecraft=0 in the URL to override it. Addresses come from the
// build's environment (scripts/publish_web.sh passes web.env's MC_ADDRESS, MC_STATUS_URL and BAR_URL), with the real
// ones as defaults.
import { track } from '../analytics';
import * as THREE from 'three';
import { onLang, T } from '../i18n';
import type { Bar } from '../meta';
import { esc } from '../util';

const env = import.meta.env;
export const MC_ADDRESS: string = env.VITE_MC_ADDRESS || 'mc.side-quest.bar';
const MC_PORT_BEDROCK = 19132;
const BAR_URL: string = env.VITE_BAR_URL || 'https://side-quest.bar';
// the server's own count when its status URL is known (or, in bun run dev, a server on this machine through Vite's
// proxy), else mcstatus.io
const STATUS_URLS = [env.VITE_MC_STATUS, env.DEV ? 'api/minecraft' : '', `https://api.mcstatus.io/v2/status/java/${MC_ADDRESS}`]
  .filter((u): u is string => !!u);

const on = (v: string | null | undefined) => v === '1' || v === 'true' || v === 'on';
export function minecraftEnabled() {
  const q = new URLSearchParams(location.search).get('minecraft');
  return q !== null ? on(q) : on(env.VITE_MINECRAFT);
}

interface Status { online: boolean; players: number; max: number; version?: string }

async function fetchStatus(): Promise<Status | null> {
  for (const url of STATUS_URLS) {
    try {
      const r = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(10000) });
      if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) continue;
      const j = await r.json();
      if (typeof j.online === 'number') return { online: true, players: j.online, max: j.max, version: j.version };
      if (typeof j.online === 'boolean') {
        return { online: j.online, players: j.players?.online ?? 0, max: j.players?.max ?? 0, version: j.version?.name_clean };
      }
    } catch { /* the next one */ }
  }
  return null;
}

export class Promo {
  private readonly count: HTMLElement;
  private readonly panel: HTMLElement;
  private readonly pin: HTMLButtonElement | null = null;
  private readonly at = new THREE.Vector3();
  private status: Status | null | undefined;
  private timer = 0;

  private readonly mc = minecraftEnabled();

  constructor(bar: Bar | null | undefined, goBar: () => void) {
    const mc = document.getElementById('mc')!;
    this.count = document.getElementById('mc-count')!;
    this.panel = document.getElementById('mc-panel')!;
    (document.getElementById('sq') as HTMLAnchorElement).href = BAR_URL;
    document.getElementById('sq')!.addEventListener('click', () => track('bar-site'));
    if (this.mc) {
      mc.onclick = () => { const on = this.panel.hasAttribute('hidden'); if (on) track('minecraft'); this.open(on); };
      addEventListener('keydown', (e) => { if (e.key === 'Escape') this.open(false); });
    } else {
      mc.remove();
      this.panel.remove();
    }
    if (bar) {
      this.at.set(bar.x, bar.z, bar.y);
      const pin = document.createElement('button');
      pin.id = 'sq-pin';
      pin.innerHTML = `<img src="sidequest/mug.png" alt="" /><span>${esc(bar.name)}</span>`;
      pin.onclick = goBar;
      document.body.appendChild(pin);
      this.pin = pin;
      const where = document.getElementById('sq-where')!;
      where.hidden = false;
      where.onclick = goBar;
    }
    this.text();
    onLang(() => this.text());
    if (this.mc) {
      this.refresh();
      document.addEventListener('visibilitychange', () => { if (!document.hidden) this.refresh(); });
    }
  }

  private open(on: boolean) {
    this.panel.hidden = !on;
    document.getElementById('mc')!.setAttribute('aria-expanded', String(on));
    if (on) this.refresh();
  }

  private text() {
    const t = T(), addr = esc(MC_ADDRESS);
    const deep = `minecraft://?addExternalServer=Budapest|${MC_ADDRESS}:${MC_PORT_BEDROCK}`;
    document.querySelector('#sq small')!.textContent = t.sqMadeBy;
    document.querySelector('#sq em')!.textContent = t.sqWhere;
    document.querySelector('#sq-where span')!.textContent = t.onMap;
    if (this.pin) this.pin.title = `${this.pin.textContent}, Klauzál utca 26-28`;
    if (!this.mc) return;
    document.querySelector('#mc .mc-text b')!.textContent = t.mcPlay;
    this.panel.innerHTML = `
      <header><b>${t.mcTitle}</b><button class="x" aria-label="${t.close}">×</button></header>
      <p class="lead">${t.mcLead}</p>
      <section>
        <h3>${t.java} <small>${t.javaSmall}</small></h3>
        <div class="addr"><code>${addr}</code><button class="copy" data-copy="${addr}">${t.copy}</button></div>
        <p class="how">${t.howJava} <span class="ver"></span></p>
      </section>
      <section>
        <h3>${t.bedrock} <small>${t.bedrockSmall}</small></h3>
        <div class="addr"><code>${addr}</code><span class="port">${t.port} <code>${MC_PORT_BEDROCK}</code></span>
          <a class="open" href="${esc(deep)}">${t.addToMc}</a></div>
        <p class="how">${t.howBedrock}</p>
      </section>
      <section>
        <h3>${t.inGame}</h3>
        <ul>
          <li><code>/lm</code> ${t.cmdLm}</li>
          <li><code>/fly</code>, ${t.cmdFly}; <code>/flyspeed 1-10</code></li>
          <li><code>/bar</code> ${t.cmdBar}</li>
        </ul>
      </section>
      <p class="legal">${t.mcLegal}</p>`;
    this.panel.querySelector<HTMLButtonElement>('.x')!.onclick = () => this.open(false);
    for (const b of this.panel.querySelectorAll<HTMLButtonElement>('.copy')) {
      b.onclick = async () => {
        try { await navigator.clipboard.writeText(b.dataset.copy!); b.textContent = T().copied; }
        catch { getSelection()?.selectAllChildren(b.previousElementSibling!); b.textContent = 'Ctrl+C'; }
        setTimeout(() => { b.textContent = T().copy; }, 1800);
      };
    }
    this.show();
  }

  private show() {
    const s = this.status, t = T();
    const ver = this.panel.querySelector('.ver');
    if (!s) { this.count.textContent = t.mcSub; this.count.className = ''; }
    else if (!s.online) { this.count.textContent = t.offline; this.count.className = 'off'; }
    else {
      this.count.textContent = t.players(s.players);
      this.count.className = 'on';
      if (ver && s.version) ver.textContent = t.version(s.version);
    }
  }

  async refresh() {
    clearTimeout(this.timer);
    this.status = await fetchStatus();
    this.show();
    if (!document.hidden) this.timer = window.setTimeout(() => this.refresh(), this.panel.hasAttribute('hidden') ? 30000 : 10000);
  }

  update(camera: THREE.PerspectiveCamera, w: number, h: number) {
    if (!this.pin) return;
    const d = this.at.distanceTo(camera.position);
    const v = this.at.clone().project(camera);
    const ok = v.z < 1 && Math.abs(v.x) < 1.02 && Math.abs(v.y) < 1.02 && d < 5000 && d > 12;
    this.pin.style.display = ok ? '' : 'none';
    if (ok) {
      this.pin.style.transform = `translate(${(((v.x + 1) / 2) * w).toFixed(1)}px, ${(((1 - v.y) / 2) * h).toFixed(1)}px) translate(-50%, -100%)`;
      this.pin.classList.toggle('far', d > 1800);
    }
  }
}
